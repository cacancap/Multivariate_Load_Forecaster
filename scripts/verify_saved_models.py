"""Compare reloaded inference to holdout predictions and test future invariance."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from load_forecaster.experiment import predict_saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if not (run / "COMPLETE.json").exists():
        raise ValueError("Wait for the experiment to complete before verifying saved models")
    root = Path(__file__).resolve().parents[1]
    config = json.loads((run / "config.json").read_text())
    quality = json.loads((run / "data_quality.json").read_text())
    choices = json.loads((run / "selected_models.json").read_text())
    ensemble = json.loads((run / "ensemble_selection.json").read_text())
    chosen = min(choices, key=lambda row: row["all_horizon_cv_mape_percent"])
    model_name = chosen["model"]
    if ensemble and ensemble["mape_percent"] < chosen["all_horizon_cv_mape_percent"] - 0.1:
        model_name = "weighted_ensemble"
    branch = json.loads((run / "COMPLETE.json").read_text())["branch"]
    path = root / ("data/processed/load_weather.parquet" if branch == "oracle" else "data/processed/load.parquet")
    load = pd.read_parquet(path)
    load.attrs["time_basis"] = quality["time_basis"]
    checks = []
    for delay in (0, 1):
        stored = pd.read_parquet(run / "test_predictions.parquet", filters=[("model", "=", model_name), ("delay_hours", "=", delay)])
        counts = stored.groupby("origin_time").horizon.nunique()
        complete = counts[counts == len(config["horizons"])].index
        origin = complete[len(complete) // 2]
        expected = stored[stored.origin_time == origin].sort_values("horizon")
        actual = predict_saved(run, load, origin, delay=delay)
        np.testing.assert_array_equal(actual.horizon, expected.horizon)
        np.testing.assert_allclose(actual.prediction_mw, expected.prediction_mw, rtol=1e-7, atol=0.02)
        changed = load.copy()
        changed.loc[changed.index > origin, ["load_input", "load_observed"]] = 999999
        counterfactual = predict_saved(run, changed, origin, delay=delay)
        np.testing.assert_array_equal(actual.prediction_mw, counterfactual.prediction_mw)
        checks.append({"delay_hours": delay, "origin_time": str(origin), "horizon_count": len(actual), "model": model_name,
                       "maximum_reload_difference_mw": float(np.abs(actual.prediction_mw.to_numpy() - expected.prediction_mw.to_numpy()).max()),
                       "reload_matches_holdout": True, "future_load_invariant": True})
    (run / "model_reload_verification.json").write_text(json.dumps({"status": "passed", "checks": checks}, indent=2), encoding="utf-8")
    print(json.dumps(checks), flush=True)


if __name__ == "__main__":
    main()
