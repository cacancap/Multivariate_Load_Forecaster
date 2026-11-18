"""Common rows, temporal label embargo and interpretable peak metrics."""
import math

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit


def metrics(y, prediction, peak_threshold=None):
    y, prediction = np.asarray(y, float), np.asarray(prediction, float)
    if len(y) == 0 or not np.isfinite(y).all() or not np.isfinite(prediction).all() or (y <= 0).any():
        raise ValueError("Metrics require positive finite observed labels and finite predictions")
    result = {
        "n": len(y), "mae_mw": float(mean_absolute_error(y, prediction)),
        "rmse_mw": float(math.sqrt(mean_squared_error(y, prediction))),
        "mape_percent": float(np.mean(np.abs((y - prediction) / y)) * 100),
        "r2": float(r2_score(y, prediction)) if len(y) > 1 and np.var(y) > 0 else None,
    }
    peak = y >= peak_threshold if peak_threshold is not None else np.zeros(len(y), bool)
    result["peak_n"] = int(peak.sum())
    result["peak_mape_percent"] = float(np.mean(np.abs((y[peak] - prediction[peak]) / y[peak])) * 100) if peak.any() else None
    return result


def temporal_folds(origins, n_splits=5, test_size=1440, gap=24, max_horizon=24):
    if gap < max_horizon:
        raise ValueError("Gap must cover the maximum horizon")
    origins = pd.DatetimeIndex(origins)
    if not origins.is_unique or not origins.is_monotonic_increasing or not np.all(np.diff(origins.as_unit("ns").asi8) == pd.Timedelta(hours=1).value):
        raise ValueError("Split on the full unique regular hourly origin grid before filtering")
    for train, validation in TimeSeriesSplit(n_splits=n_splits, test_size=test_size, gap=gap).split(origins):
        if origins[train[-1]] + pd.Timedelta(hours=max_horizon) >= origins[validation[0]]:
            raise AssertionError("Training labels overlap the validation origin")
        yield origins[train], origins[validation]


def common_predictions(frame):
    keys = ["branch", "delay_hours", "origin_time", "target_time", "horizon"]
    expected_models = frame.model.nunique()
    counts = frame.groupby(keys, dropna=False).model.transform("nunique")
    common = frame.loc[counts == expected_models].copy()
    coverage = {
        "model_count": expected_models, "prediction_rows_before": len(frame),
        "prediction_rows_common": len(common),
        "common_pairs": len(common[keys].drop_duplicates()),
    }
    if common.duplicated(keys + ["model"]).any():
        raise ValueError("Duplicate prediction keys")
    if common.groupby(keys).load_mw.nunique().gt(1).any():
        raise ValueError("Models disagree on observed labels")
    return common, coverage


def summarize_predictions(frame, peak_threshold):
    rows = []
    local = pd.to_datetime(frame.target_time)
    if local.dt.tz is not None:
        local = local.dt.tz_convert("America/New_York")
    frame = frame.assign(month=local.dt.month.to_numpy())
    frame["season"] = frame.month.map({12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"})
    for model, group in frame.groupby("model"):
        rows.append({"model": model, "slice": "overall", **metrics(group.load_mw, group.prediction_mw, peak_threshold)})
        for horizon, part in group.groupby("horizon"):
            rows.append({"model": model, "slice": f"horizon_{horizon}", **metrics(part.load_mw, part.prediction_mw, peak_threshold)})
        for season, part in group.groupby("season"):
            rows.append({"model": model, "slice": season, **metrics(part.load_mw, part.prediction_mw, peak_threshold)})
    return pd.DataFrame(rows)


def window_peaks(frame, horizons):
    rows = []
    for (model, origin), group in frame.groupby(["model", "origin_time"]):
        if set(group.horizon) != set(horizons):
            continue
        group = group.sort_values("horizon")
        actual = group.loc[group.load_mw.idxmax()]
        predicted = group.loc[group.prediction_mw.idxmax()]
        rows.append({"model": model, "origin_time": origin,
                     "peak_magnitude_error_mw": abs(float(predicted.prediction_mw - actual.load_mw)),
                     "peak_hour_error": abs(int(predicted.horizon - actual.horizon))})
    return pd.DataFrame(rows)
