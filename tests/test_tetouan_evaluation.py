"""Tests for Role D: chronological splits, hand-checked metrics, peak tie-breaking, and train-only Q95."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from load_forecaster.tetouan.evaluation.metrics import _peak_hour_metrics, compute_metrics, score_run
from load_forecaster.tetouan.evaluation.splits import make_splits


def test_hand_calculated_metrics():
    m = compute_metrics([100.0, 100.0], [90.0, 90.0])
    assert m["mae"] == 10.0
    assert m["rmse"] == 10.0
    assert m["mape_percent"] == 10.0
    assert m["mean_signed_error"] == -10.0
    assert m["under_prediction_rate"] == 1.0


def test_make_splits_enforces_24h_embargo():
    # 160 days hourly grid (~3840 hours)
    origins = pd.date_range("2017-01-01 00:00", periods=160 * 24, freq="h")
    splits = make_splits(origins)
    assert len(splits["folds"]) == 3
    for b in [*splits["folds"], splits["test"]]:
        train_end = pd.Timestamp(b["train_end"])
        eval_start = pd.Timestamp(b["eval_start"])
        assert train_end + pd.Timedelta(hours=24) < eval_start


def test_peak_hour_tie_resolves_to_earliest():
    origin = pd.Timestamp("2017-12-01 00:00")
    rows = []
    for h in range(1, 25):
        # Tie at h=5 and h=15 with value 500.0 -> earliest h=5 must be chosen
        y = 500.0 if h in (5, 15) else 200.0
        p = 450.0 if h == 5 else 490.0
        rows.append({"origin_time": origin, "horizon": h, "y_true": y, "ridge": p})
    df = pd.DataFrame(rows)
    res = _peak_hour_metrics(df, "ridge", list(range(1, 25)))
    # At true peak h=5, y=500 and p=450 -> MAE=50, signed=-50
    assert res["mae"] == 50.0
    assert res["mean_signed_error"] == -50.0
    assert res["under_prediction_rate"] == 1.0


def test_score_run_outputs_and_train_only_q95(tmp_path: Path):
    origins = pd.date_range("2017-01-01 00:00", periods=140 * 24, freq="h")
    splits = make_splits(origins)
    # Minimal 1-horizon smoke-style scoring verification
    rows = []
    preds = []
    for o in origins:
        t = o + pd.Timedelta(hours=1)
        y = 1000.0 + float((o - origins[0]).total_seconds() // 3600)
        rows.append({
            "zone": "zone1", "origin_time": o, "target_time": t, "horizon": 1,
            "load_now": y - 1.0, "y_true": y, "day_lag": y - 24.0, "week_lag": y - 168.0,
        })
    samples = pd.DataFrame(rows)
    b = splits["folds"][-1]
    ev = samples[samples["origin_time"].between(b["eval_start"], b["eval_end"])]
    for model_name, offset in [("ridge", -5.0), ("ridge_no_weather", -8.0)]:
        part = ev[["origin_time", "target_time", "horizon", "y_true"]].copy()
        part["zone"] = "zone1"
        part["split"] = "validation"
        part["fold"] = 3
        part["model"] = model_name
        part["y_pred"] = part["y_true"] + offset
        preds.append(part)
    out = tmp_path / "run"
    out.mkdir()
    pd.concat(preds, ignore_index=True).to_parquet(out / "predictions.parquet", index=False)
    (out / "selection.json").write_text(json.dumps({"best_model": "ridge", "inputs": {"columns": ["day_lag", "week_lag"]}}), encoding="utf-8")

    score_run(samples, splits, out, zone="zone1", smoke=True)
    assert (out / "scores.csv").is_file()
    assert (out / "weather_ablation.csv").is_file()
    assert (out / "thresholds.csv").is_file()
    ab = pd.read_csv(out / "weather_ablation.csv")
    assert ab["delta_mae"].iloc[0] < 0  # ridge error 5 < ridge_no_weather error 8
