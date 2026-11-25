"""Direct hourly forecasts for Tetouan. One fitted estimator per horizon and model."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from .models import build_model
from .resources import ResourceRecorder


SEED = 42
RF_THREADS = 4
KEY = ["origin_time", "target_time", "horizon"]
IDENTITY = KEY + ["y_true"]
SEARCH_HORIZONS = (1, 6, 12, 24)
GRID = {
    "ridge": [{"alpha": a} for a in (0.1, 1.0, 10.0, 100.0)],
    "random_forest": [
        {"n_estimators": 24, "min_samples_leaf": leaf, "max_depth": depth,
         "max_features": 0.7, "max_samples": 0.8}
        for leaf, depth in ((2, 8), (6, 8), (2, 14), (6, 14))
    ],
    "svr": [{"C": c, "epsilon": e, "gamma": g}
            for c, e, g in ((1., .1, "scale"), (3., .05, .03), (5., .08, .05))],
}


def _save_json(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def _write_predictions(predictions, path):
    tmp = path.with_suffix(".tmp")
    predictions.to_parquet(tmp, index=False)
    tmp.replace(path)


def _fold_data(by_horizon, horizons, ranges, columns):
    start, end, first, last = [pd.Timestamp(ranges[name]) for name in
                               ("train_start", "train_end", "eval_start", "eval_end")]
    if first - end < pd.Timedelta(hours=24) or start > end or first > last:
        raise ValueError("Invalid temporal fold or gap below 24 hours")
    blocks = {}
    for h in horizons:
        frame = by_horizon[h]
        train = frame.loc[start:end]
        if train.target_time.ge(first).any():
            raise ValueError(f"Training label reaches evaluation for horizon {h}")
        valid = frame.loc[first:last]
        valid = valid.loc[valid.target_time <= last]
        if valid.empty or train.empty:
            raise ValueError(f"No complete train/evaluation rows for horizon {h}")
        blocks[h] = (train[columns].to_numpy(dtype=float), train.y_true.to_numpy(dtype=float),
                     valid[columns].to_numpy(dtype=float), valid[IDENTITY].reset_index(drop=True),
                     train.target_time.max())
    return blocks


def _fit_predict(model, params, block, ncols):
    x, y, xv, keys, _ = block
    family = "ridge" if model == "ridge_no_weather" else model
    estimator = build_model(family, params, seed=SEED, threads=RF_THREADS)
    estimator.fit(x[:, :ncols], y)
    pred = estimator.predict(xv[:, :ncols])
    yv = keys.y_true.to_numpy()
    nz = yv != 0
    if not nz.any() or not np.isfinite(pred).all():
        raise ValueError("No finite percentage error available")
    mape = 100 * np.mean(np.abs((yv[nz] - pred[nz]) / yv[nz]))
    return estimator, pred, float(mape)


def _choose(trials):
    minimum = min(row["mape"] for row in trials)
    return min((row for row in trials if row["mape"] - minimum < .1),
               key=lambda row: (row["seconds"], row["mape"]))


def _search(folds, columns, out):
    best = {}
    trial_log = []
    for model, candidates in GRID.items():
        results = []
        print(f"Tetouan: searching {len(candidates)} {model} configurations", flush=True)
        for candidate, params in enumerate(candidates):
            started = time.perf_counter()
            errors = []
            for fold, blocks in folds.items():
                for h in SEARCH_HORIZONS:
                    fit_start = time.perf_counter()
                    _, _, error = _fit_predict(model, params, blocks[h], len(columns))
                    errors.append(error)
                    trial_log.append(dict(model=model, candidate=candidate, params=json.dumps(params),
                                          fold=fold, horizon=h, mape=error,
                                          seconds=time.perf_counter()-fit_start))
            results.append(dict(params=params, mape=float(np.mean(errors)), seconds=time.perf_counter()-started))
        best[model] = _choose(results)["params"]
        pd.DataFrame(trial_log).to_csv(out / "tuning.csv", index=False)
    return best


def _run_models(folds, split, models, params, columns, base, out, recorder, save=False):
    rows = []
    ranking = []
    for model in models:
        print(f"Tetouan: {split} {model}", flush=True)
        used = base if model == "ridge_no_weather" else columns
        settings = params["ridge" if model == "ridge_no_weather" else model]
        errors = []
        started = time.perf_counter()
        with recorder.stage(f"{split}/{model}"):
            for fold, blocks in folds.items():
                for h, block in blocks.items():
                    estimator, pred, error = _fit_predict(model, settings, block, len(used))
                    errors.append(error)
                    rows.append(block[3].assign(model=model, y_pred=pred, split=split, fold=fold))
                    if save:
                        state = dict(estimator=estimator, columns=used, model=model,
                                     horizon=h, latest_train_target=block[4])
                        dest = out / "models" / f"{model}-h{h}.joblib"
                        tmp = dest.with_suffix(".tmp")
                        joblib.dump(state, tmp, compress=1)
                        tmp.replace(dest)
        ranking.append(dict(model=model, seconds=time.perf_counter()-started, mape=float(np.mean(errors))))
    return pd.concat(rows, ignore_index=True), ranking


def train(samples, features, splits, out: Path, smoke=False):
    """Write fitted heads, frozen validation choices, predictions and measured costs."""
    out = Path(out)
    (out / "models").mkdir(exist_ok=True, parents=True)
    base = list(features["base"])
    columns = base + list(features["weather"])
    if not base or not features["weather"] or len(set(columns)) != len(columns):
        raise ValueError("Expect distinct base and extra weather columns")
    if set(columns).intersection(IDENTITY):
        raise ValueError("Prediction keys or labels in feature columns")
    horizons = [1] if smoke else list(range(1, 25))
    f = samples.loc[samples.horizon.isin(horizons)]
    if f.duplicated(KEY).any() or not (f.origin_time + pd.to_timedelta(f.horizon, unit="h")).eq(f.target_time).all():
        raise ValueError("Sample keys must have unique, exact hourly horizons")
    # Use identical eligible rows for every candidate, baseline comparison, and both Ridge arms.
    required = list(dict.fromkeys(columns + ["y_true", "day_lag", "week_lag"]))
    f = f.loc[np.isfinite(f[required].to_numpy(dtype=float)).all(axis=1)]
    by_horizon = {h: group.set_index("origin_time", drop=False).sort_index()
                  for h, group in f.groupby("horizon")}
    folds = {i: _fold_data(by_horizon, horizons, bounds, columns)
             for i, bounds in enumerate(splits["folds"], 1)
             if not smoke or i == len(splits["folds"])}
    profile = "smoke" if smoke else "full"
    # Materialize an identity to keep reruns from choosing again after observing holdout.
    digest = hashlib.sha256(pd.util.hash_pandas_object(f[KEY + required], index=False).to_numpy().tobytes()).hexdigest()
    contract = dict(profile=profile, seed=SEED, grid=GRID, columns=columns, base=base,
                    splits=json.loads(json.dumps(splits, default=str)), sklearn_version=sklearn.__version__,
                    samples_sha256=digest, threads_rf=RF_THREADS, threads_blas=1)
    selection_path = out / "selection.json"
    frozen = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.is_file() else None
    if frozen and frozen["inputs"] != contract:
        raise ValueError("Existing selection belongs to different data or settings. Choose a fresh output directory.")
    recorder = ResourceRecorder()
    models = ["ridge"] if smoke else [*GRID, "ridge_no_weather"]
    with threadpool_limits(limits=1):
        if frozen:
            params = frozen["params"]
        elif smoke:
            params = {"ridge": {"alpha": 1.0}}
        else:
            with recorder.stage("validation/search"):
                params = _search(folds, columns, out)
        val, ranking = _run_models(folds, "validation", models, params, columns, base,
                                   out, recorder, save=smoke)
        if not frozen:
            winner = _choose([r for r in ranking if r["model"] != "ridge_no_weather"])
            frozen = dict(inputs=contract, seed=SEED, params=params, best_model=winner["model"],
                          validation_mape={r["model"]:r["mape"] for r in ranking}, ranking=ranking)
            _save_json(selection_path, frozen)
        if smoke:
            predictions = val
        else:
            holdout = {0: _fold_data(by_horizon, horizons, splits["test"], columns)}
            test, _ = _run_models(holdout, "test", models, params, columns, base,
                                  out, recorder, save=True)
            predictions = pd.concat([val, test], ignore_index=True)
    _write_predictions(predictions, out / "predictions.parquet")
    pd.DataFrame(recorder.rows).to_csv(out / ("training_resources_replay.csv" if frozen and
                                      (out / "training_resources.csv").exists() else "training_resources.csv"), index=False)
    return predictions


def predict_saved(out, rows, model="ridge"):
    """Return raw-unit predictions ordered exactly like the input rows."""
    if model not in {*GRID, "ridge_no_weather"}:
        raise ValueError(f"Unknown model {model!r}")
    rows = rows.reset_index(drop=True)
    if not (rows.target_time == rows.origin_time + pd.to_timedelta(rows.horizon, unit="h")).all():
        raise ValueError("Incorrect horizon or missing origin/target")
    result = np.empty(len(rows))
    with threadpool_limits(limits=1):
        for h, group in rows.groupby("horizon"):
            if h not in range(1,25):
                raise ValueError("Horizon outside 1..24")
            state = joblib.load(Path(out) / "models" / f"{model}-h{h}.joblib")
            if state["horizon"] != h or state["model"] != model:
                raise ValueError("Saved model does not match requested model or horizon")
            if group.origin_time.le(state["latest_train_target"]).any():
                raise ValueError("Requested forecast precedes availability of training labels")
            x = group[state["columns"]].to_numpy(dtype=float)
            if not np.isfinite(x).all():
                raise ValueError("Insufficient feature history")
            result[group.index] = state["estimator"].predict(x)
    return result
