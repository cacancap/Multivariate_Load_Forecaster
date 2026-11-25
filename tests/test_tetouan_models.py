"""A synthetic 12:00 origin can exercise modelling before the UCI data arrives."""
import joblib
import numpy as np
import pandas as pd
import pytest

from load_forecaster.tetouan_models import predict_saved, train


def example():
    hours = pd.date_range("2017-01-01", periods=160, freq="h")
    load = 200 + 11 * np.sin(np.arange(len(hours)) / 6)
    sample = pd.DataFrame({
        "origin_time": hours, "target_time": hours + pd.Timedelta(hours=1),
        "horizon": 1, "load_now": load, "weather_past": np.arange(len(hours)) % 7,
        "y_true": np.r_[load[1:], np.nan], "day_lag": 199., "week_lag": 198.,
    })
    ranges = dict(train_start=str(hours[0]), train_end=str(hours[78]),
                  eval_start=str(hours[103]), eval_end=str(hours[150]))
    return sample, {"base": ["load_now"], "weather": ["weather_past"]}, {"folds": [ranges] * 3, "test": ranges}


def test_smoke_reload_uses_training_scaler_and_stays_in_order(tmp_path):
    sample, features, splits = example()
    train(sample, features, splits, tmp_path, smoke=True)
    p = pd.read_parquet(tmp_path / "predictions.parquet")
    assert set(zip(p.split, p.fold, p.model)) == {("validation", 3, "ridge")}
    chosen = p.iloc[[6, 0, 3]]
    inputs = sample.set_index("origin_time").loc[chosen.origin_time].reset_index()
    np.testing.assert_allclose(predict_saved(tmp_path, inputs), chosen.y_pred, rtol=1e-10)
    state = joblib.load(tmp_path / "models" / "ridge-h1.joblib")
    scaler = state["estimator"].steps[0][1]
    np.testing.assert_allclose(scaler.mean_, sample.iloc[:79][features["base"] + features["weather"]].mean())
    with pytest.raises(ValueError):
        predict_saved(tmp_path, sample.iloc[:1])


def test_malformed_training_boundary_is_rejected(tmp_path):
    rows, features, splits = example()
    splits["folds"][-1]["train_end"] = splits["folds"][-1]["eval_start"]
    with pytest.raises(ValueError):
        train(rows, features, splits, tmp_path, smoke=True)
