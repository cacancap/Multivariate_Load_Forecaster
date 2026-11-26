"""Role D: Independent scoring, baselines, weather ablation, peak-hour & 95% ramp-hour evaluation."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

KEY = ["origin_time", "target_time", "horizon"]
SEASONS = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}


def compute_metrics(y_true, y_pred) -> dict[str, float | int]:
    """Independent scoring function returning MAE, RMSE, MAPE, signed error, and under-prediction rate."""
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if len(y) == 0:
        return {
            "n": 0,
            "n_mape": 0,
            "mae": np.nan,
            "rmse": np.nan,
            "mape_percent": np.nan,
            "mean_signed_error": np.nan,
            "under_prediction_rate": np.nan,
        }
    signed = p - y
    nz = y != 0
    return {
        "n": int(len(y)),
        "n_mape": int(nz.sum()),
        "mae": float(np.abs(signed).mean()),
        "rmse": float(np.sqrt(np.square(signed).mean())),
        "mape_percent": float(100.0 * np.abs(signed[nz] / y[nz]).mean()) if nz.any() else np.nan,
        "mean_signed_error": float(signed.mean()),
        "under_prediction_rate": float((p < y).mean()),
    }


def _train_thresholds(samples: pd.DataFrame, b: dict[str, str], horizons: list[int], fit_cols: list[str]) -> dict:
    tr = samples[
        samples.origin_time.between(b["train_start"], b["train_end"])
        & samples.horizon.isin(horizons)
    ]
    if (tr.target_time >= pd.Timestamp(b["eval_start"])).any():
        raise ValueError("Train label crosses evaluation boundary")
    eligible = np.isfinite(tr[fit_cols].to_numpy(dtype=float)).all(axis=1)
    measured = (
        tr.loc[eligible, ["target_time", "y_true"]]
        .drop_duplicates()
        .sort_values("target_time")
    )
    if measured.empty or measured.target_time.duplicated().any():
        raise ValueError("Missing or conflicting training labels")

    load_q90 = float(measured["y_true"].quantile(0.90))

    # Positive hourly ramp threshold (95th percentile) strictly on training targets.
    series = measured.set_index("target_time")["y_true"]
    prev = series.reindex(series.index - pd.Timedelta(hours=1)).to_numpy()
    inc = series.to_numpy() - prev
    pos_inc = inc[np.isfinite(inc) & (inc > 0)]
    ramp_q95 = float(np.quantile(pos_inc, 0.95)) if len(pos_inc) > 0 else np.nan
    return {
        "load_q90": load_q90,
        "ramp_q95": ramp_q95,
        "train_targets": int(len(measured)),
        "train_positive_ramps": int(len(pos_inc)),
    }


def _peak_hour_metrics(common: pd.DataFrame, model_col: str, horizons: list[int]) -> dict:
    """Evaluate prediction vs actual AT the true peak hour of each complete 24h window."""
    truth = common.pivot(index="origin_time", columns="horizon", values="y_true").reindex(columns=horizons)
    pred = common.pivot(index="origin_time", columns="horizon", values=model_col).reindex(columns=horizons)
    valid = truth.notna().all(axis=1) & pred.notna().all(axis=1)
    truth, pred = truth.loc[valid], pred.loc[valid]
    if truth.empty:
        return {
            "n_windows": 0,
            "n_distinct_targets": 0,
            "mae": np.nan,
            "mean_signed_error": np.nan,
            "under_prediction_rate": np.nan,
            "peak_timing_abs_hours_mean": np.nan,
        }
    # Columns are sorted 1..24, so idxmax resolves ties to the earliest hour.
    true_peak_h = truth.idxmax(axis=1)
    pred_peak_h = pred.idxmax(axis=1)
    y_at_true_peak = np.array([truth.loc[o, h] for o, h in true_peak_h.items()], dtype=float)
    p_at_true_peak = np.array([pred.loc[o, h] for o, h in true_peak_h.items()], dtype=float)
    target_times = pd.DatetimeIndex(
        [pd.Timestamp(o) + pd.Timedelta(hours=int(h)) for o, h in true_peak_h.items()]
    )
    m = compute_metrics(y_at_true_peak, p_at_true_peak)
    return {
        "n_windows": int(len(truth)),
        "n_distinct_targets": int(target_times.nunique()),
        "mae": m["mae"],
        "mean_signed_error": m["mean_signed_error"],
        "under_prediction_rate": m["under_prediction_rate"],
        "peak_timing_abs_hours_mean": float((pred_peak_h - true_peak_h).abs().mean()),
    }


def _ramp_hour_metrics(
    eval_df: pd.DataFrame,
    hourly_delta: pd.Series,
    model_col: str,
    ramp_q95: float,
) -> dict:
    """Evaluate predictions on evaluation target hours whose hourly load increase >= ramp_q95."""
    deltas = hourly_delta.reindex(eval_df["target_time"]).to_numpy()
    mask = np.isfinite(deltas) & (deltas >= ramp_q95)
    sub = eval_df.loc[mask]
    if sub.empty:
        return {
            "n_rows": 0,
            "n_distinct_targets": 0,
            "mae": np.nan,
            "mean_signed_error": np.nan,
            "under_prediction_rate": np.nan,
        }
    m = compute_metrics(sub["y_true"], sub[model_col])
    return {
        "n_rows": int(len(sub)),
        "n_distinct_targets": int(sub["target_time"].nunique()),
        "mae": m["mae"],
        "mean_signed_error": m["mean_signed_error"],
        "under_prediction_rate": m["under_prediction_rate"],
    }


def _extract_case_studies(
    test_common: pd.DataFrame,
    hourly_delta: pd.Series,
    best_model: str,
    zone: str,
) -> pd.DataFrame:
    """Extract 2 concrete test windows (1 peak-hour window + 1 steepest ramp-hour window) for defense."""
    if test_common.empty or best_model not in test_common.columns:
        return pd.DataFrame()
    peak_origin = test_common.loc[test_common["y_true"].idxmax(), "origin_time"]
    deltas = hourly_delta.reindex(test_common["target_time"]).to_numpy()
    ramp_idx = int(np.nanargmax(deltas)) if np.isfinite(deltas).any() else 0
    ramp_origin = test_common.iloc[ramp_idx]["origin_time"]

    rows = []
    for case_name, origin in [("peak_example", peak_origin), ("ramp_example", ramp_origin)]:
        win = test_common[test_common["origin_time"] == origin].sort_values("horizon")
        if case_name == "peak_example":
            focus = win.loc[win["y_true"].idxmax()]
        else:
            win_deltas = hourly_delta.reindex(win["target_time"]).to_numpy()
            focus = win.iloc[int(np.nanargmax(win_deltas))] if np.isfinite(win_deltas).any() else win.iloc[0]
        signed = float(focus[best_model] - focus["y_true"])
        rows.append(
            {
                "zone": zone,
                "case_type": case_name,
                "model": best_model,
                "origin_time": focus["origin_time"],
                "target_time": focus["target_time"],
                "horizon": int(focus["horizon"]),
                "y_true": float(focus["y_true"]),
                "y_pred": float(focus[best_model]),
                "day_prior": float(focus["day_prior"]),
                "week_prior": float(focus["week_prior"]),
                "abs_error": abs(signed),
                "signed_error": signed,
                "hourly_ramp_delta": float(hourly_delta.get(focus["target_time"], np.nan)),
            }
        )
    return pd.DataFrame(rows)


def score_run(
    samples: pd.DataFrame,
    splits: dict,
    out: Path,
    zone: str = "zone1",
    smoke: bool = False,
) -> dict:
    """Compute common-window scores, weather ablation, critical-hour metrics, and case studies."""
    out = Path(out)
    learned = pd.read_parquet(out / "predictions.parquet")
    if learned.empty or learned.duplicated(["split", "fold", "model", *KEY]).any():
        raise ValueError("Empty or duplicate learned predictions")
    if samples.duplicated(KEY).any() or not samples.target_time.eq(
        samples.origin_time + pd.to_timedelta(samples.horizon, unit="h")
    ).all():
        raise ValueError("Invalid sample keys")

    horizons = [1] if smoke else list(range(1, 25))
    all_models = sorted(learned["model"].unique().tolist())
    compare_models = [*all_models, "day_prior", "week_prior"]

    # Hourly delta series for ramp-hour identification
    hourly_obs = (
        samples.loc[samples["horizon"] == 1, ["origin_time", "load_now"]]
        .drop_duplicates()
        .set_index("origin_time")["load_now"]
        .sort_index()
    )
    hourly_delta = hourly_obs - hourly_obs.reindex(hourly_obs.index - pd.Timedelta(hours=1)).to_numpy()

    selection_path = out / "selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.is_file() else {}
    fit_cols = selection.get("inputs", {}).get("columns", ["day_lag", "week_lag"])
    best_model = selection.get("best_model", all_models[0])

    # Pivot learned predictions onto common keys and join ground truth + baselines
    base_keys = samples.loc[samples["horizon"].isin(horizons), [*KEY, "y_true", "day_lag", "week_lag"]].copy()
    base_keys = base_keys.rename(columns={"day_lag": "day_prior", "week_lag": "week_prior"})

    blocks = [("validation", i, b) for i, b in enumerate(splits["folds"], 1) if not smoke or i == len(splits["folds"])]
    if not smoke:
        blocks.append(("test", 0, splits["test"]))

    all_preds_parts = []
    score_rows = []
    ablation_rows = []
    threshold_rows = []
    critical_rows = []
    coverage_rows = []
    test_common_df = pd.DataFrame()

    for split_name, fold_id, b in blocks:
        sub_learned = learned[(learned["split"] == split_name) & (learned["fold"] == fold_id)]
        wide = sub_learned.pivot(index=KEY, columns="model", values="y_pred").reset_index()
        joined = wide.merge(base_keys, on=KEY, how="inner")

        req_cols = ["y_true", *compare_models]
        eligible_mask = np.isfinite(joined[req_cols].to_numpy(dtype=float)).all(axis=1)
        eligible = joined.loc[eligible_mask].copy()

        # Restrict to complete 24-hour windows (or 1-hour for smoke)
        win_counts = eligible.groupby("origin_time")["horizon"].transform("nunique")
        common = eligible.loc[win_counts == len(horizons)].copy()
        common["split"] = split_name
        common["fold"] = fold_id
        common["season"] = pd.to_datetime(common["target_time"]).dt.month.map(SEASONS)

        # Scheduled windows count
        scheduled_origins = pd.date_range(b["eval_start"], b["eval_end"], freq="h")
        expected_n = len(scheduled_origins) * len(horizons)
        n_windows = int(common["origin_time"].nunique())
        cov = float(len(common) / expected_n) if expected_n else 0.0
        coverage_rows.append(
            {
                "zone": zone,
                "split": split_name,
                "fold": fold_id,
                "expected_n": expected_n,
                "common_n": int(len(common)),
                "n_windows": n_windows,
                "coverage": cov,
            }
        )

        thresh = _train_thresholds(samples, b, horizons, fit_cols)
        threshold_rows.append({"zone": zone, "split": split_name, "fold": fold_id, **thresh})

        for model_name in compare_models:
            m_all = compute_metrics(common["y_true"], common[model_name])
            score_rows.append(
                {
                    "zone": zone,
                    "split": split_name,
                    "fold": fold_id,
                    "slice": "overall",
                    "horizon": 0,
                    "season": "all",
                    "model": model_name,
                    "n_windows": n_windows,
                    "expected_n": expected_n,
                    "coverage": cov,
                    **m_all,
                }
            )
            for h, h_grp in common.groupby("horizon"):
                mh = compute_metrics(h_grp["y_true"], h_grp[model_name])
                score_rows.append(
                    {
                        "zone": zone,
                        "split": split_name,
                        "fold": fold_id,
                        "slice": "horizon",
                        "horizon": int(h),
                        "season": "all",
                        "model": model_name,
                        "n_windows": n_windows,
                        "expected_n": expected_n // len(horizons),
                        "coverage": cov,
                        **mh,
                    }
                )
            for season_name, s_grp in common.groupby("season"):
                ms = compute_metrics(s_grp["y_true"], s_grp[model_name])
                score_rows.append(
                    {
                        "zone": zone,
                        "split": split_name,
                        "fold": fold_id,
                        "slice": "season",
                        "horizon": 0,
                        "season": season_name,
                        "model": model_name,
                        "n_windows": int(s_grp["origin_time"].nunique()),
                        "expected_n": expected_n,
                        "coverage": cov,
                        **ms,
                    }
                )

            if not smoke:
                pk = _peak_hour_metrics(common, model_name, horizons)
                critical_rows.append(
                    {
                        "zone": zone,
                        "split": split_name,
                        "fold": fold_id,
                        "event_type": "peak_hour",
                        "model": model_name,
                        "threshold": np.nan,
                        **pk,
                    }
                )
                rm = _ramp_hour_metrics(common, hourly_delta, model_name, thresh["ramp_q95"])
                critical_rows.append(
                    {
                        "zone": zone,
                        "split": split_name,
                        "fold": fold_id,
                        "event_type": "ramp_hour",
                        "model": model_name,
                        "threshold": thresh["ramp_q95"],
                        "n_windows": np.nan,
                        **rm,
                        "peak_timing_abs_hours_mean": np.nan,
                    }
                )

        if "ridge" in common.columns and "ridge_no_weather" in common.columns:
            mw = compute_metrics(common["y_true"], common["ridge"])
            mn = compute_metrics(common["y_true"], common["ridge_no_weather"])
            ablation_rows.append(
                {
                    "zone": zone,
                    "split": split_name,
                    "fold": fold_id,
                    "slice": "overall",
                    "n": mw["n"],
                    "ridge_mape_percent": mw["mape_percent"],
                    "ridge_no_weather_mape_percent": mn["mape_percent"],
                    "delta_mape_pp": mw["mape_percent"] - mn["mape_percent"],
                    "ridge_mae": mw["mae"],
                    "ridge_no_weather_mae": mn["mae"],
                    "delta_mae": mw["mae"] - mn["mae"],
                    "delta_rmse": mw["rmse"] - mn["rmse"],
                }
            )

        if split_name == "test":
            test_common_df = common.copy()

        # Long-format combined predictions
        melted = common.melt(
            id_vars=["split", "fold", *KEY, "y_true"],
            value_vars=compare_models,
            var_name="model",
            value_name="y_pred",
        )
        all_preds_parts.append(melted)

    pd.concat(all_preds_parts, ignore_index=True).to_parquet(out / "all_predictions.parquet", index=False)
    scores_df = pd.DataFrame(score_rows)
    scores_df.to_csv(out / "scores.csv", index=False)
    pd.DataFrame(ablation_rows).to_csv(out / "weather_ablation.csv", index=False)
    pd.DataFrame(threshold_rows).to_csv(out / "thresholds.csv", index=False)
    pd.DataFrame(coverage_rows).to_csv(out / "coverage.csv", index=False)
    if critical_rows:
        pd.DataFrame(critical_rows).to_csv(out / "critical_hours.csv", index=False)
    if not smoke and not test_common_df.empty:
        _extract_case_studies(test_common_df, hourly_delta, best_model, zone).to_csv(
            out / "case_studies.csv", index=False
        )

    return {
        "zone": zone,
        "scores_rows": len(scores_df),
        "best_model": best_model,
    }
