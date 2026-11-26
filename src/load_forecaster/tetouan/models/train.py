"""Role C: Direct multi-horizon training, CV tuning, selection freezing, and model saving."""
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

from load_forecaster.models import build_model
from load_forecaster.resources import ResourceRecorder

SEED = 42
RF_THREADS = 4
KEY = ["origin_time", "target_time", "horizon"]
IDENTITY = KEY + ["y_true"]
SEARCH_HORIZONS = (1, 6, 12, 24)
GRID = {
    "ridge": [{"alpha": a} for a in (0.1, 1.0, 10.0, 100.0)],
    "random_forest": [
        {
            "n_estimators": 24,
            "min_samples_leaf": leaf,
            "max_depth": depth,
            "max_features": 0.7,
            "max_samples": 0.8,
        }
        for leaf, depth in ((2, 8), (6, 8), (2, 14), (6, 14))
    ],
    "svr": [
        {"C": c, "epsilon": e, "gamma": g}
        for c, e, g in ((1.0, 0.1, "scale"), (3.0, 0.05, 0.03), (5.0, 0.08, 0.05))
    ],
}


def _save_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def _write_predictions(predictions: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    predictions.to_parquet(tmp, index=False)
    tmp.replace(path)


def _fold_data(by_horizon: dict[int, pd.DataFrame], horizons: list[int], ranges: dict, columns: list[str]) -> dict:
    start, end, first, last = [
        pd.Timestamp(ranges[name]) for name in ("train_start", "train_end", "eval_start", "eval_end")
    ]
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
        blocks[h] = (
            train[columns].to_numpy(dtype=float),
            train["y_true"].to_numpy(dtype=float),
            valid[columns].to_numpy(dtype=float),
            valid[IDENTITY].reset_index(drop=True),
            train["target_time"].max(),
        )
    return blocks


def _fit_predict(model: str, params: dict, block: tuple, ncols: int):
    x, y, xv, keys, _ = block
    family = "ridge" if model == "ridge_no_weather" else model
    estimator = build_model(family, params, seed=SEED, threads=RF_THREADS)
    estimator.fit(x[:, :ncols], y)
    pred = estimator.predict(xv[:, :ncols])
    yv = keys["y_true"].to_numpy()
    nz = yv != 0
    if not nz.any() or not np.isfinite(pred).all():
        raise ValueError("No finite percentage error available")
    mape = 100.0 * np.mean(np.abs((yv[nz] - pred[nz]) / yv[nz]))
    return estimator, pred, float(mape)


def _choose(trials: list[dict]) -> dict:
    minimum = min(row["mape"] for row in trials)
    return min(
        (row for row in trials if row["mape"] - minimum < 0.1),
        key=lambda row: (row["seconds"], row["mape"]),
    )


def _search(folds: dict[int, dict], columns: list[str], out: Path) -> dict[str, dict]:
    best = {}
    trial_log = []
    ncols = len(columns)
    for model, candidates in GRID.items():
        summary = []
        for idx, params in enumerate(candidates):
            t0 = time.perf_counter()
            mapes = []
            for fold_blocks in folds.values():
                for h in SEARCH_HORIZONS:
                    _, _, mape = _fit_predict(model, params, fold_blocks[h], ncols)
                    mapes.append(mape)
            elapsed = time.perf_counter() - t0
            row = {
                "model": model,
                "candidate_id": idx,
                "params": json.dumps(params, sort_keys=True),
                "mape": float(np.mean(mapes)),
                "seconds": float(elapsed),
                "_raw_params": params,
            }
            summary.append(row)
            trial_log.append({k: v for k, v in row.items() if k != "_raw_params"})
        chosen = _choose(summary)
        best[model] = chosen["_raw_params"]
    pd.DataFrame(trial_log).to_csv(out / "tuning.csv", index=False)
    return best


def _run_models(
    folds: dict[int, dict],
    split_name: str,
    models: list[str],
    params: dict[str, dict],
    columns: list[str],
    base: list[str],
    zone: str,
    out: Path,
    recorder: ResourceRecorder,
    save: bool = False,
):
    parts = []
    ranking = []
    models_dir = out / "models"
    if save:
        models_dir.mkdir(parents=True, exist_ok=True)

    for model in models:
        family = "ridge" if model == "ridge_no_weather" else model
        used_cols = base if model == "ridge_no_weather" else columns
        ncols = len(used_cols)
        mapes = []
        t0 = time.perf_counter()
        with recorder.stage(f"{split_name}/{model}"):
            for fold_id, fold_blocks in folds.items():
                for h, block in fold_blocks.items():
                    estimator, pred, mape = _fit_predict(model, params[family], block, ncols)
                    mapes.append(mape)
                    keys = block[3].copy()
                    keys["zone"] = zone
                    keys["split"] = split_name
                    keys["fold"] = fold_id
                    keys["model"] = model
                    keys["y_pred"] = pred
                    parts.append(keys)
                    if save:
                        state = {
                            "estimator": estimator,
                            "model": model,
                            "horizon": h,
                            "zone": zone,
                            "columns": list(used_cols),
                            "latest_train_target": block[4],
                        }
                        joblib.dump(state, models_dir / f"{model}-h{h}.joblib")
        ranking.append(
            {
                "model": model,
                "mape": float(np.mean(mapes)),
                "seconds": float(time.perf_counter() - t0),
            }
        )
    return pd.concat(parts, ignore_index=True), ranking


def train_zone(
    samples: pd.DataFrame,
    features: dict,
    splits: dict,
    out: Path,
    zone: str = "zone1",
    smoke: bool = False,
) -> pd.DataFrame:
    """Train 24 direct models per algorithm for one zone, freeze selection on CV, and predict holdout."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    base = list(features["base"])
    columns = base + list(features["weather"])
    if not base or not features["weather"] or len(set(columns)) != len(columns):
        raise ValueError("Expect distinct base and extra weather columns")
    if set(columns).intersection(IDENTITY):
        raise ValueError("Prediction keys or labels in feature columns")

    horizons = [1] if smoke else list(range(1, 25))
    f = samples.loc[samples["horizon"].isin(horizons)].copy()
    if f.duplicated(KEY).any() or not (
        f["origin_time"] + pd.to_timedelta(f["horizon"], unit="h")
    ).eq(f["target_time"]).all():
        raise ValueError("Sample keys must have unique, exact hourly horizons")

    # Identical eligible rows for every model, baseline, and weather ablation arm.
    required = list(dict.fromkeys(columns + ["y_true", "day_lag", "week_lag"]))
    f = f.loc[np.isfinite(f[required].to_numpy(dtype=float)).all(axis=1)]
    by_horizon = {
        int(h): group.set_index("origin_time", drop=False).sort_index()
        for h, group in f.groupby("horizon")
    }
    folds = {
        i: _fold_data(by_horizon, horizons, bounds, columns)
        for i, bounds in enumerate(splits["folds"], 1)
        if not smoke or i == len(splits["folds"])
    }

    profile = "smoke" if smoke else "full"
    digest = hashlib.sha256(
        pd.util.hash_pandas_object(f[KEY + required], index=False).to_numpy().tobytes()
    ).hexdigest()
    contract = {
        "zone": zone,
        "profile": profile,
        "seed": SEED,
        "grid": GRID,
        "columns": columns,
        "base": base,
        "splits": json.loads(json.dumps(splits, default=str)),
        "sklearn_version": sklearn.__version__,
        "samples_sha256": digest,
        "threads_rf": RF_THREADS,
        "threads_blas": 1,
    }

    selection_path = out / "selection.json"
    frozen = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.is_file() else None
    if frozen and frozen["inputs"] != contract:
        raise ValueError("Existing selection belongs to different data, zone, or settings.")

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

        val, ranking = _run_models(
            folds, "validation", models, params, columns, base, zone, out, recorder, save=smoke
        )
        if not frozen:
            winner = _choose([r for r in ranking if r["model"] != "ridge_no_weather"])
            frozen = {
                "zone": zone,
                "inputs": contract,
                "seed": SEED,
                "params": params,
                "best_model": winner["model"],
                "validation_mape": {r["model"]: r["mape"] for r in ranking},
                "ranking": ranking,
            }
            _save_json(selection_path, frozen)

        if smoke:
            predictions = val
        else:
            holdout = {0: _fold_data(by_horizon, horizons, splits["test"], columns)}
            test, _ = _run_models(
                holdout, "test", models, params, columns, base, zone, out, recorder, save=True
            )
            predictions = pd.concat([val, test], ignore_index=True)

    _write_predictions(predictions, out / "predictions.parquet")
    res_name = (
        "training_resources_replay.csv"
        if frozen and (out / "training_resources.csv").exists()
        else "training_resources.csv"
    )
    pd.DataFrame(recorder.rows).to_csv(out / res_name, index=False)
    return predictions
