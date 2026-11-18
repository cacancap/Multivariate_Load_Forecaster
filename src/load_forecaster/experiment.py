"""End-to-end experiment, selection before holdout, and saved inference artifacts."""
from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from .acquisition import fetch_load, fetch_weather, sha256, write_json
from .evaluation import common_predictions, metrics, summarize_predictions, temporal_folds, window_peaks
from .features import SampleBuilder
from .models import build_model, candidates
from .resources import ResourceRecorder
from .temporal import audit_load, join_weather, prepare_load


def boundary(value, index):
    stamp = pd.Timestamp(value)
    if index.tz is None:
        if stamp.tz is not None:
            raise ValueError("Cannot map a timezone-aware timestamp to unconfirmed native time labels")
        return stamp
    return stamp.tz_localize(index.tz) if stamp.tz is None else stamp.tz_convert(index.tz)


def choose_features(X, order):
    return X if order == 2 else X.drop(columns=[c for c in X if c.startswith(("sin_", "cos_")) and c.endswith("_2")])


def prepare(root, config, with_weather=False, recorder=None):
    root = Path(root)
    recorder = recorder or ResourceRecorder()
    out = root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    with recorder.stage("acquisition_load"):
        raw = fetch_load(root, config)
    with recorder.stage("preprocessing"):
        audit = audit_load(raw, config["timezone"])
        load, quarantine, quality = prepare_load(raw, config)
        write_json(out / "data_audit.json", audit)
        write_json(out / "data_quality.json", quality)
        quarantine.to_csv(out / "quarantined_rows.csv", index=False)
        processed = root / "data/processed"
        processed.mkdir(parents=True, exist_ok=True)
        load.to_parquet(processed / "load.parquet")
        interpretations = audit["time_semantics_candidates"]
        lines = ["# Kiểm toán dữ liệu PJME", "",
                 f"Nguồn: {config['source_url']}", "",
                 "| Kiểm tra | Kết quả |", "|---|---:|",
                 f"| Dòng gốc | {audit['rows']:,} |",
                 f"| Dòng lặp timestamp (sau lần đầu) | {audit['duplicate_timestamp_rows']} |",
                 f"| Dòng trùng hoàn toàn | {audit['exact_duplicate_rows']} |",
                 f"| Mốc thiếu theo lịch giờ địa phương chưa gắn timezone | {audit['missing_naive_hours']} |",
                 f"| Phụ tải nhỏ nhất/lớn nhất (MW) | {audit['minimum_mw']:,.0f} / {audit['maximum_mw']:,.0f} |",
                 f"| Dòng nguồn cách ly | {quality['quarantined_source_rows']} |",
                 f"| Giờ đầu vào điền tiến tối đa hai giờ | {quality['imputed_input_hours']} |", "",
                 "## Cách diễn giải thời gian", "",
                 f"Giả thuyết giờ bắt đầu: {interpretations['hour_starting']['ambiguous_or_nonexistent_rows']} dòng mơ hồ/không tồn tại khi gắn timezone.",
                 f"Giả thuyết giờ kết thúc: {interpretations['hour_ending']['ambiguous_or_nonexistent_rows']} dòng mơ hồ/không tồn tại sau khi dịch nhãn một giờ.",
                 "Khác biệt này là dấu hiệu để điều tra, chưa phải bằng chứng xác nhận quy ước của nguồn.",
                 f"Cách xử lý hiện tại: {quality['time_basis']}. Cho phép ghép thời tiết: {quality['weather_join_allowed']}.", "",
                 "Các giờ cao tải vẫn được giữ. Không xóa theo IQR, không nội suy nhãn và không gộp hai timestamp DST khác giá trị.",
                 "Báo cáo trên mô tả toàn bộ nguồn thô. Thực nghiệm chính dùng 2014–2017; độ phủ sau tạo mẫu được ghi riêng theo horizon.", "",
                 "## Số dòng theo năm", "", "| Năm | Dòng nguồn |", "|---|---:|"]
        lines += [f"| {year} | {count} |" for year, count in audit["rows_per_year"].items()]
        (out / "DATA_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if with_weather:
        with recorder.stage("acquisition_weather"):
            weather = fetch_weather(root, config)
            weather.to_parquet(root / "data/processed/weather.parquet")
        if quality["weather_join_allowed"]:
            with recorder.stage("weather_join"):
                load, missing = join_weather(load, weather, quality)
                write_json(out / "weather_missing_by_month.json", missing)
                load.to_parquet(root / "data/processed/load_weather.parquet")
        else:
            write_json(out / "weather_status.json", {
                "status": "downloaded_but_join_blocked",
                "reason": "Unconfirmed PJME time convention. No weather model is trained.",
                "hours": len(weather), "required": "Document time_convention_evidence and explicitly confirm the convention.",
            })
    write_json(out / "preparation_resources.json", recorder.rows)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    write_json(out / f"preparation_runs/{stamp}.json", {"with_weather": with_weather, "resources": recorder.rows})
    return load, quality


def prediction_rows(name, horizon, X, y, prediction, branch, delay, fold=None):
    result = pd.DataFrame({
        "model": name, "horizon": horizon, "origin_time": X.index,
        "target_time": X.index + pd.Timedelta(hours=horizon), "load_mw": y.to_numpy(),
        "prediction_mw": np.asarray(prediction), "branch": branch, "delay_hours": delay,
    })
    if fold is not None:
        result["fold"] = fold
    return result


def _fit(name, params, X, y, config):
    model = build_model(name, params, config["seed"], config["threads"])
    model.fit(X, y)
    return model


def _training_samples(builder, origins, horizon, cutoff, name, order):
    if name == "svr" or name.endswith("_365"):
        origins = origins[origins >= cutoff - pd.Timedelta(days=365)]
    X, y = builder.samples(origins, horizon, label_cutoff=cutoff)
    if len(y) < 100:
        raise ValueError(f"Insufficient training samples: {name}, h={horizon}, n={len(y)}")
    if (X.index + pd.Timedelta(hours=horizon) >= cutoff).any():
        raise AssertionError("Training label is not observed before cutoff")
    return choose_features(X, order), y


def _validation(builder, all_builders, origins, horizon, cutoff):
    X, y = builder.samples(origins, horizon, label_cutoff=cutoff)
    # Common availability across delay scenarios; do not drop difficult rows per model.
    common = X.index
    for other in all_builders:
        other_X, _ = other.samples(origins, horizon, label_cutoff=cutoff)
        common = common.intersection(other_X.index, sort=False)
    for other in all_builders:
        for period in (24, 168):
            valid = np.isfinite(other.baseline(common, horizon, period))
            common = common[valid]
    return X.loc[common], y.loc[common]


def evaluate_cv(name, params, order, horizons, builder, all_builders, folds, config, recorder, branch):
    predictions, scores = [], []
    for h in horizons:
        for fold, (train_origins, val_origins) in enumerate(folds):
            cutoff = val_origins[0]
            X, y = _training_samples(builder, train_origins, h, cutoff, name, order)
            Xv, yv = _validation(builder, all_builders, val_origins, h, val_origins[-1] + pd.Timedelta(hours=1))
            Xv = choose_features(Xv, order)
            if Xv.empty:
                raise ValueError("No validation labels remain after quarantine")
            with recorder.stage(f"cv_fit/{branch}/{name}/h{h}/fold{fold}"):
                model = _fit(name, params, X, y, config)
            with recorder.stage(f"cv_predict/{branch}/{name}/h{h}/fold{fold}"):
                prediction = model.predict(Xv)
            train_start = boundary(config["train_start"], builder.load.index)
            threshold = float(builder.load.load_observed.loc[(builder.load.index >= train_start) & (builder.load.index < cutoff)].quantile(0.9))
            scores.append({"horizon": h, "fold": fold, **metrics(yv, prediction, threshold)})
            predictions.append(prediction_rows(name, h, Xv, yv, prediction, branch, builder.delay, fold))
        print(f"CV {branch} {name}: h={h} done", flush=True)
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(scores)


def select_candidate(records):
    best = min(row["mape_percent"] for row in records)
    eligible = [row for row in records if row["mape_percent"] <= best + 0.1]
    return min(eligible, key=lambda row: row["fit_predict_seconds"])


def _ensemble_selection(cv, ranked):
    if len(ranked) < 2:
        return None
    names = [row["model"] for row in ranked[:2]]
    keys = ["fold", "origin_time", "target_time", "horizon"]
    a = cv[cv.model == names[0]]
    b = cv[cv.model == names[1]]
    joined = a.merge(b, on=keys, suffixes=("_a", "_b"), validate="one_to_one")
    if len(joined) != len(a) or len(joined) != len(b):
        raise ValueError("Ensemble validation predictions are not aligned")
    weights = []
    for weight in np.linspace(0, 1, 11):
        p = weight * joined.prediction_mw_a + (1 - weight) * joined.prediction_mw_b
        # Equal fold/horizon weighting, as used for individual-model selection.
        errors = joined.assign(error=np.abs((joined.load_mw_a - p) / joined.load_mw_a) * 100)
        score = float(errors.groupby(["fold", "horizon"]).error.mean().mean())
        weights.append({"weight": float(weight), "mape_percent": score})
    chosen = min(weights, key=lambda row: row["mape_percent"])
    return {"models": names, **chosen, "grid": weights}


def _ablation(builder, all_builders, folds, config, recorder, branch):
    rows = []
    groups = ["lags_only", "calendar", "fourier_order_1", "fourier_order_2"]
    if builder.weather_mode == "oracle":
        groups.append("fourier_and_oracle_weather")
    for group in groups:
        for h in config["representative_horizons"]:
            for fold, (tr, va) in enumerate(folds):
                X, y = _training_samples(builder, tr, h, va[0], "ridge", 2)
                V, v = _validation(builder, all_builders, va, h, va[-1] + pd.Timedelta(hours=1))
                load_columns = [c for c in X if c.startswith(("origin_lag", "target_lag", "rolling_", "imputed_", "same_local"))]
                calendar_columns = [c for c in X if c.startswith("target_") and not c.startswith("target_lag")]
                fourier = [c for c in X if c.startswith(("sin_", "cos_")) and (group in ("fourier_order_2", "fourier_and_oracle_weather") or c.endswith("_1"))]
                columns = load_columns + (calendar_columns if group != "lags_only" else []) + (fourier if group.startswith("fourier") else [])
                if group == "fourier_and_oracle_weather":
                    columns += [c for c in X if c.startswith("oracle_") or c in ("cooling_demand", "heating_demand", "temperature_squared")]
                with recorder.stage(f"ablation/{branch}/{group}/h{h}/fold{fold}"):
                    model = _fit("ridge", {"alpha": 100}, X[columns], y, config)
                    p = model.predict(V[columns])
                rows.append({"feature_group": group, "horizon": h, "fold": fold, **metrics(v, p)})
    return pd.DataFrame(rows)


def _run_experiment(root, config, load, quality, profile="full", branch="none"):
    root = Path(root)
    recorder = ResourceRecorder()
    token = sha256(json.dumps(config, sort_keys=True).encode())[:10]
    run_dir = root / "outputs" / f"{profile}-{branch}-{token}"
    run_dir.mkdir(parents=True, exist_ok=True)
    if (run_dir / "COMPLETE.json").exists():
        provenance = json.loads((run_dir / "input_provenance.json").read_text())
        current_raw = sha256((root / "data/raw/PJME_hourly.csv").read_bytes())
        current_processed = hashlib.sha256(pd.util.hash_pandas_object(load, index=True).values.tobytes()).hexdigest()
        if current_raw != provenance["load_sha256"] or current_processed != provenance["processed_hash"]:
            raise ValueError("Completed run input checksum differs; do not reuse results")
        print(f"Completed run exists; returning saved report: {run_dir}", flush=True)
        return run_dir
    if (run_dir / "HOLDOUT_STARTED.json").exists():
        raise RuntimeError("Interrupted holdout run exists. Use --resume-holdout with the same frozen configuration; never retune against partial holdout results.")
    if branch == "oracle" and not quality["weather_join_allowed"]:
        raise ValueError("Oracle branch requires confirmed time semantics")
    write_json(run_dir / "config.json", config)
    write_json(run_dir / "environment.json", {"python": platform.python_version(), "platform": platform.platform(), "packages": {package: version(package) for package in ("pandas", "numpy", "scipy", "scikit-learn", "requests", "pyyaml", "pyarrow", "psutil", "joblib", "matplotlib", "threadpoolctl")}, "seed": config["seed"], "threads": min(config["threads"], 4)})
    write_json(run_dir / "data_quality.json", quality)
    raw_path = root / "data/raw/PJME_hourly.csv"
    write_json(run_dir / "input_provenance.json", {"load_sha256": sha256(raw_path.read_bytes()), "processed_hash": hashlib.sha256(pd.util.hash_pandas_object(load, index=True).values.tobytes()).hexdigest(), "weather_mode": branch})
    start = boundary(config["train_start"], load.index)
    dev_end = boundary(config["development_end"], load.index)
    test_end = boundary(config["test_end"], load.index)
    development = load.index[(load.index >= start) & (load.index < dev_end)]
    test = load.index[(load.index >= dev_end) & (load.index < test_end)]
    folds = list(temporal_folds(development, config["n_splits"], config["validation_hours"], max(config["gap_hours"], max(config["horizons"])), max(config["horizons"])))
    write_json(run_dir / "folds.json", [{"fold": i, "train_start": tr[0], "train_last_origin": tr[-1], "validation_start": va[0], "validation_last_origin": va[-1], "canonical_validation_hours": len(va)} for i, (tr, va) in enumerate(folds)])
    with recorder.stage("feature_construction"):
        builders = [SampleBuilder(load, config["timezone"], branch, delay, 2) for delay in (0, 1)]
    builder = builders[0]
    cv_parts, choices, searches, default_scores = [], [], [], []
    with threadpool_limits(limits=min(config["threads"], 4)):
        for name in config["models"]:
            pool = candidates(name, config["max_candidates"], config["seed"])
            records = []
            default_predictions = None
            for candidate_id, params in enumerate(pool):
                order = 2 if candidate_id == len(pool) - 1 and candidate_id > 0 else 1
                horizons = config["horizons"] if candidate_id == 0 else config["representative_horizons"]
                tick = time.perf_counter()
                pred, score = evaluate_cv(name, params, order, horizons, builder, builders, folds, config, recorder, branch)
                elapsed = time.perf_counter() - tick
                representative = score[score.horizon.isin(config["representative_horizons"])]
                records.append({"candidate_id": candidate_id, "params": params, "fourier_order": order,
                                "mape_percent": float(representative.mape_percent.mean()),
                                "fit_predict_seconds": elapsed * len(config["representative_horizons"]) / len(horizons)})
                score.assign(model=name, candidate_id=candidate_id, fourier_order=order).to_csv(run_dir / f"cv_{name}_candidate_{candidate_id}.csv", index=False)
                if candidate_id == 0:
                    default_predictions = pred
                    default_scores.append(score.assign(model=name))
            selected = select_candidate(records)
            searches.extend({"model": name, **row} for row in records)
            if selected["candidate_id"] == 0:
                selected_predictions = default_predictions
            else:
                # Re-evaluate selected params on ALL horizons for aligned ensemble selection.
                selected_predictions, _ = evaluate_cv(name, selected["params"], selected["fourier_order"], config["horizons"], builder, builders, folds, config, recorder, branch)
            errors = selected_predictions.assign(error=np.abs((selected_predictions.load_mw - selected_predictions.prediction_mw) / selected_predictions.load_mw) * 100)
            full_score = float(errors.groupby(["fold", "horizon"]).error.mean().mean())
            choices.append({"model": name, **selected, "all_horizon_cv_mape_percent": full_score})
            cv_parts.append(selected_predictions)
            write_json(run_dir / "search_results.json", searches)
            write_json(run_dir / "selected_models.json", choices)
            write_json(run_dir / "resources.json", recorder.rows)
        cv = pd.concat(cv_parts, ignore_index=True)
        cv.to_parquet(run_dir / "validation_predictions.parquet", index=False)
        pd.concat(default_scores).to_csv(run_dir / "default_cv_metrics.csv", index=False)
        ranked = sorted(choices, key=lambda row: row["all_horizon_cv_mape_percent"])
        ensemble = _ensemble_selection(cv, ranked)
        write_json(run_dir / "ensemble_selection.json", ensemble)
        _ablation(builder, builders, folds, config, recorder, branch).to_csv(run_dir / "feature_ablation.csv", index=False)
        # Final choices are persisted BEFORE accessing holdout metrics.
        selection_files = ["config.json", "selected_models.json", "ensemble_selection.json", "input_provenance.json", "validation_predictions.parquet", "feature_ablation.csv", "search_results.json"]
        write_json(run_dir / "HOLDOUT_STARTED.json", {"selected_before_test": True, "best_model": ranked[0]["model"], "ensemble": ensemble,
                                                     "selection_files_sha256": {name: sha256((run_dir / name).read_bytes()) for name in selection_files}})
    # Predictions used for selection are already on disk; release them before
    # allocating the much larger final-evaluation table.
    del cv, cv_parts, default_predictions, pred, selected_predictions, errors
    return _finish_holdout(run_dir, config, load, quality, choices, ensemble, profile, branch, recorder, builders)


def _finish_holdout(run_dir, config, load, quality, choices, ensemble, profile, branch, recorder, builders=None, verify_contract=None):
    start = boundary(config["train_start"], load.index)
    dev_end = boundary(config["development_end"], load.index)
    test_end = boundary(config["test_end"], load.index)
    development = load.index[(load.index >= start) & (load.index < dev_end)]
    test = load.index[(load.index >= dev_end) & (load.index < test_end)]
    ranked = sorted(choices, key=lambda row: row["all_horizon_cv_mape_percent"])
    if builders is None:
        builders = [SampleBuilder(load, config["timezone"], branch, delay, 2) for delay in (0, 1)]
    with threadpool_limits(limits=min(config["threads"], 4)):
        threshold = float(load.load_observed.loc[(load.index >= start) & (load.index < dev_end)].quantile(0.9))
        predictions = []
        artifacts = run_dir / "models"
        artifacts.mkdir(exist_ok=True)
        save_names = set(ensemble["models"] if ensemble else [ranked[0]["model"]])
        coverage = []
        checkpoints = run_dir / "holdout_checkpoints"
        checkpoints.mkdir(exist_ok=True)
        for delay, current in enumerate(builders):
            for h in config["horizons"]:
                Xtest, ytest = _validation(current, builders, test, h, test_end)
                coverage.append({"delay_hours": delay, "horizon": h, "canonical_test_origins": len(test), "evaluated_origins": len(Xtest), "fraction": len(Xtest) / len(test)})
                if Xtest.empty:
                    raise ValueError("No holdout observations remain")
                checkpoint = checkpoints / f"delay{delay}-h{h}.parquet"
                if checkpoint.exists():
                    cached = pd.read_parquet(checkpoint)
                    expected_models = {"seasonal_24", "seasonal_168"} | {row["model"] for row in choices}
                    if set(cached.model) != expected_models or cached.duplicated(["model", "origin_time"]).any():
                        raise ValueError("Incomplete or duplicate holdout checkpoint")
                    for _, part in cached.groupby("model"):
                        if not pd.DatetimeIndex(part.origin_time).equals(Xtest.index) or not np.array_equal(part.load_mw.to_numpy(), ytest.to_numpy()):
                            raise ValueError("Checkpoint does not match current observed labels/origins")
                    if not np.isfinite(cached.prediction_mw).all():
                        raise ValueError("Checkpoint has nonfinite predictions")
                    if any(not (artifacts / f"{name}-delay{delay}-h{h}.joblib").exists() for name in save_names):
                        raise ValueError("Checkpoint is missing its saved inference artifacts")
                    predictions.append(cached)
                    print(f"HOLDOUT checkpoint reused delay={delay} h={h}", flush=True)
                    continue
                head_start = len(predictions)
                for period in (24, 168):
                    predictions.append(prediction_rows(f"seasonal_{period}", h, Xtest, ytest, current.baseline(Xtest.index, h, period), branch, delay))
                for selection in choices:
                    name, params, order = selection["model"], selection["params"], selection["fourier_order"]
                    X, y = _training_samples(current, development, h, dev_end, name, order)
                    with recorder.stage(f"final_fit/{branch}/delay{delay}/{name}/h{h}"):
                        model = _fit(name, params, X, y, config)
                    with recorder.stage(f"final_predict/{branch}/delay{delay}/{name}/h{h}"):
                        p = model.predict(choose_features(Xtest, order))
                    predictions.append(prediction_rows(name, h, Xtest, ytest, p, branch, delay))
                    if name in save_names:
                        artifact = artifacts / f"{name}-delay{delay}-h{h}.joblib"
                        temporary = artifact.with_suffix(".joblib.part")
                        joblib.dump({"model": model, "columns": list(X.columns), "horizon": h, "delay_hours": delay, "weather_mode": branch,
                                     "timezone": config["timezone"], "time_basis": quality["time_basis"], "config": config}, temporary, compress=3)
                        temporary.replace(artifact)
                head = pd.concat(predictions[head_start:], ignore_index=True)
                temporary = checkpoint.with_suffix(".part.parquet")
                head.to_parquet(temporary, index=False)
                temporary.replace(checkpoint)
                print(f"HOLDOUT {branch} delay={delay} h={h}: {len(Xtest)} origins", flush=True)
        frame = pd.concat(predictions, ignore_index=True)
        del predictions
        if ensemble:
            a, b = ensemble["models"]
            keys = ["branch", "delay_hours", "origin_time", "target_time", "horizon"]
            first = frame[frame.model == a]
            second = frame[frame.model == b]
            joined = first.merge(second[keys + ["prediction_mw"]], on=keys, suffixes=("", "_b"), validate="one_to_one")
            joined["prediction_mw"] = ensemble["weight"] * joined.prediction_mw + (1 - ensemble["weight"]) * joined.prediction_mw_b
            joined["model"] = "weighted_ensemble"
            frame = pd.concat([frame, joined[frame.columns]], ignore_index=True)
            del first, second, joined
        frame, common_coverage = common_predictions(frame)
        frame.to_parquet(run_dir / "test_predictions.parquet", index=False)
        summary = []
        for delay, part in frame.groupby("delay_hours"):
            summary.append(summarize_predictions(part, threshold).assign(delay_hours=delay, branch=branch))
            peaks = window_peaks(part, config["horizons"])
            peaks.to_csv(run_dir / f"window_peaks_delay{delay}.csv", index=False)
            if not peaks.empty:
                peaks.groupby("model")[["peak_magnitude_error_mw", "peak_hour_error"]].mean().to_csv(run_dir / f"peak_summary_delay{delay}.csv")
        pd.concat(summary, ignore_index=True).to_csv(run_dir / "metrics.csv", index=False)
        write_json(run_dir / "coverage.json", {"per_horizon": coverage, "common_models": common_coverage, "peak_threshold_train_mw": threshold})
    write_json(run_dir / "resources.json", recorder.rows)
    write_report(run_dir, quality, config, branch)
    if verify_contract is not None:
        verify_contract()
    write_json(run_dir / "COMPLETE.json", {"status": "complete", "profile": profile, "branch": branch, "holdout_evaluated_after_selection": True})
    return run_dir


def run_experiment(root, config, load, quality, profile="full", branch="none"):
    """Measure the complete experiment, including serialization and reporting."""
    token = sha256(json.dumps(config, sort_keys=True).encode())[:10]
    expected = Path(root) / "outputs" / f"{profile}-{branch}-{token}"
    cached_before = (expected / "COMPLETE.json").exists()
    recorder = ResourceRecorder()
    with recorder.stage("experiment_total_including_reporting"):
        result = _run_experiment(root, config, load, quality, profile, branch)
    name = "cache_replay_resources.json" if cached_before else "overall_resources.json"
    write_json(result / name, {"cache_replay": cached_before, **recorder.rows[0]})
    return result


def resume_holdout(root, config, load, quality, profile="full", branch="none"):
    """Recover evaluation with immutable pre-test choices; NEVER rerun selection."""
    root = Path(root)
    token = sha256(json.dumps(config, sort_keys=True).encode())[:10]
    run_dir = root / "outputs" / f"{profile}-{branch}-{token}"
    if (run_dir / "COMPLETE.json").exists():
        return run_experiment(root, config, load, quality, profile, branch)
    frozen_names = ["config.json", "selected_models.json", "ensemble_selection.json", "input_provenance.json", "HOLDOUT_STARTED.json", "validation_predictions.parquet", "feature_ablation.csv"]
    contract = {name: sha256((run_dir / name).read_bytes()) for name in frozen_names}
    saved_config = json.loads((run_dir / "config.json").read_text())
    if config != saved_config:
        raise ValueError("Recovery requires the original configuration")
    provenance = json.loads((run_dir / "input_provenance.json").read_text())
    processed_hash = hashlib.sha256(pd.util.hash_pandas_object(load, index=True).values.tobytes()).hexdigest()
    if provenance["load_sha256"] != sha256((root / "data/raw/PJME_hourly.csv").read_bytes()) or provenance["processed_hash"] != processed_hash:
        raise ValueError("Recovery input data differs from the frozen experiment")
    old_quality = json.loads((run_dir / "data_quality.json").read_text())
    if old_quality["time_basis"] != quality["time_basis"]:
        raise ValueError("Recovery time semantics differ")
    choices = json.loads((run_dir / "selected_models.json").read_text())
    ensemble = json.loads((run_dir / "ensemble_selection.json").read_text())
    started = json.loads((run_dir / "HOLDOUT_STARTED.json").read_text())
    if not started["selected_before_test"] or started["ensemble"] != ensemble or set(row["model"] for row in choices) != set(config["models"]):
        raise ValueError("Pre-test choices are incomplete or inconsistent")
    for name, digest in started.get("selection_files_sha256", {}).items():
        if sha256((run_dir / name).read_bytes()) != digest:
            raise ValueError("Pre-test selection checksum differs")
    journal_path = run_dir / "recovery.json"
    if journal_path.exists():
        old_journal = json.loads(journal_path.read_text())
        if old_journal["frozen_sha256"] != contract:
            raise ValueError("Frozen choices changed since the previous recovery")
    write_json(journal_path, {"status": "running", "frozen_sha256": contract, "selection_rerun": False, "reason": "Execution interrupted; recover holdout only with fixed pre-test choices."})
    recorder = ResourceRecorder()
    existing = run_dir / "resources.json"
    if existing.exists():
        recorder.rows = json.loads(existing.read_text())
        if not (run_dir / "resources_before_recovery.json").exists():
            write_json(run_dir / "resources_before_recovery.json", recorder.rows)
    def verify():
        if any(sha256((run_dir / name).read_bytes()) != digest for name, digest in contract.items()):
            raise ValueError("Frozen choices changed during recovery")
    total = ResourceRecorder()
    with total.stage("holdout_recovery_total"):
        result = _finish_holdout(run_dir, config, load, old_quality, choices, ensemble, profile, branch, recorder, verify_contract=verify)
    write_json(run_dir / "recovery_resources.json", {"scope": "recovered holdout only; CV was not repeated", **total.rows[0]})
    write_json(journal_path, {"status": "complete", "frozen_sha256": contract, "selection_rerun": False, "contract_unchanged": True})
    return result


def write_report(run_dir, quality, config, branch):
    score = pd.read_csv(run_dir / "metrics.csv")
    overall = score[score.slice == "overall"].sort_values(["delay_hours", "mape_percent"])
    resources = json.loads((run_dir / "resources.json").read_text())
    lines = ["# Báo cáo thực nghiệm dự báo phụ tải", "", f"Nhánh: **{branch}**. Cơ sở thời gian: **{quality['time_basis']}**.", "",
             f"Huấn luyện/lựa chọn: {config['train_start']} đến trước {config['development_end']}. Kiểm thử: {config['development_end']} đến trước {config['test_end']}. Mỗi bước dự báo dùng mô hình riêng.", "",
             "## Kết quả trên cùng tập thời điểm", "", "| Mô hình | Chậm dữ liệu (giờ) | MAPE (%) | MAE (MW) | RMSE (MW) | MAPE tải cao (%) |", "|---|---:|---:|---:|---:|---:|"]
    for row in overall.itertuples():
        lines.append(f"| {row.model} | {row.delay_hours} | {row.mape_percent:.3f} | {row.mae_mw:.1f} | {row.rmse_mw:.1f} | {row.peak_mape_percent:.3f} |")
    for delay in (0, 1):
        rows = overall[overall.delay_hours == delay]
        baseline = rows[rows.model.str.startswith("seasonal_")].mape_percent.min()
        learned = rows[~rows.model.str.startswith("seasonal_")].sort_values("mape_percent").iloc[0]
        lines.extend(["", f"Chậm {delay} giờ: {learned.model} đạt MAPE {learned.mape_percent:.3f}%; đối chứng mùa vụ tốt nhất {baseline:.3f}%. " + ("ML vượt đối chứng." if learned.mape_percent < baseline else "ML chưa vượt đối chứng.")])
    lines.extend(["", "## Tài nguyên và giới hạn", "",
                  f"Tổng thời gian các khâu được đo riêng: {sum(x['seconds'] for x in resources):.1f} giây; RAM RSS đỉnh lấy mẫu tại các khâu này: {max(x['peak_rss_mb'] for x in resources):.1f} MiB.",
                  "Đây là thống kê theo khâu; RAM đỉnh và thời gian hoạt động của toàn phiên được tổng hợp riêng trong resource_summary.json của báo cáo bàn giao.",
                  "Thời gian này gồm CV, tìm tham số, ablation và hai kịch bản độ trễ; chi phí thu thập được ghi riêng trong preparation_resources.json.",
                  "Các giờ DST không rõ nghĩa được cách ly. Xem coverage.json để biết tỷ lệ mẫu còn lại; không diễn giải kết quả như kiểm thử đầy đủ mọi giờ trong năm.",
                  "Kết quả gộp đánh giá từng lần phát hành dự báo: một giờ đích có thể xuất hiện ở nhiều khoảng cách dự báo.",
                  "Quy ước phụ tải vừa kết thúc đã có sẵn là giả định; dữ liệu đã sửa hồi tố chưa được khôi phục theo từng phiên bản.",
                  "Thời tiết Philadelphia chỉ đại diện một điểm; nhánh oracle (nếu chạy) giả định biết trước thời tiết, không phải độ chính xác vận hành.",
                  "Tập kiểm thử không được dùng để thay đổi cấu hình. Mục tiêu MAPE 3,5% không phải ngưỡng ép nghiệm thu.", ""])
    lines.extend(quality["limitations"])
    (run_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    # A portable figure; import plotting only when needed.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    horizon = score[(score.delay_hours == 0) & score.slice.str.startswith("horizon_")].copy()
    horizon["h"] = horizon.slice.str.removeprefix("horizon_").astype(int)
    fig, ax = plt.subplots(figsize=(10, 5))
    for model, group in horizon.groupby("model"):
        group = group.sort_values("h")
        ax.plot(group.h, group.mape_percent, label=model)
    ax.set(xlabel="Forecast horizon (hours)", ylabel="MAPE (%)", title=f"Holdout {config['development_end']} - same evaluation rows")
    ax.legend(fontsize=8, ncols=2)
    fig.tight_layout()
    fig.savefig(run_dir / "mape_by_horizon.png", dpi=150)
    plt.close(fig)


def predict_saved(run_dir, load, origin, model_name=None, delay=0):
    run_dir = Path(run_dir)
    if not (run_dir / "COMPLETE.json").exists():
        raise ValueError("Inference requires a completed experiment; partial model files are not a complete forecast")
    choices = json.loads((run_dir / "selected_models.json").read_text())
    config = json.loads((run_dir / "config.json").read_text())
    if origin < boundary(config["development_end"], load.index):
        raise ValueError("Saved model was trained after this origin; retrospective inference would leak future training data")
    best = min(choices, key=lambda row: row["all_horizon_cv_mape_percent"])
    ensemble_path = run_dir / "ensemble_selection.json"
    ensemble = json.loads(ensemble_path.read_text()) if ensemble_path.exists() else None
    use_ensemble = model_name == "weighted_ensemble" or (model_name is None and ensemble is not None and ensemble["mape_percent"] < best["all_horizon_cv_mape_percent"] - 0.1)
    if use_ensemble:
        if ensemble is None:
            raise ValueError("No validation-selected ensemble is available")
        a = predict_saved(run_dir, load, origin, ensemble["models"][0], delay)
        b = predict_saved(run_dir, load, origin, ensemble["models"][1], delay)
        if not a.horizon.equals(b.horizon):
            raise ValueError("Saved ensemble components have different horizons")
        a["prediction_mw"] = ensemble["weight"] * a.prediction_mw + (1 - ensemble["weight"]) * b.prediction_mw
        a["model"] = "weighted_ensemble"
        return a
    name = model_name or best["model"]
    files = sorted((run_dir / "models").glob(f"{name}-delay{delay}-h*.joblib"))
    if not files:
        raise ValueError("Only the two validation-leading models have saved inference artifacts")
    if len(files) != len(config["horizons"]):
        raise ValueError("Saved model artifacts do not cover all configured horizons")
    rows = []
    builder = None
    for path in files:
        bundle = joblib.load(path)
        if load.attrs.get("time_basis") != bundle["time_basis"]:
            raise ValueError("Inference time semantics differ from the trained model")
        if builder is None:
            builder = SampleBuilder(load, bundle["timezone"], bundle["weather_mode"], delay, 2)
        X = builder.features(pd.DatetimeIndex([origin]), bundle["horizon"])[bundle["columns"]]
        if X.isna().any().any():
            raise ValueError("Insufficient safe history at requested origin")
        with threadpool_limits(limits=min(bundle["config"]["threads"], 4)):
            prediction = bundle["model"].predict(X)[0]
        rows.append({"origin_time": origin, "target_time": origin + pd.Timedelta(hours=bundle["horizon"]), "horizon": bundle["horizon"], "model": name, "prediction_mw": float(prediction)})
    return pd.DataFrame(rows).sort_values("horizon")
