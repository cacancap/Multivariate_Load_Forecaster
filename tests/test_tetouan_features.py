"""Tests for Role B: 20-feature layout, 1h weather delay, and strict future-mutation invariance."""
from __future__ import annotations

import numpy as np
import pandas as pd

from load_forecaster.tetouan.features.samples import BASE, WEATHER, build_samples, forecast_features


def _make_obs(hours: int = 240) -> pd.DataFrame:
    idx = pd.date_range("2017-01-01 00:00", periods=hours, freq="h")
    i = np.arange(hours, dtype=float)
    return pd.DataFrame(
        {
            "zone1": 30000.0 + i * 10.0 + 1000.0 * np.sin(2 * np.pi * i / 24.0),
            "zone2": 20000.0 + i * 5.0,
            "zone3": 15000.0 + i * 3.0,
            "temperature": 15.0 + 0.1 * i,
            "humidity": 65.0 + 0.05 * i,
            "wind_speed": 2.5 + 0.01 * i,
            "general_diffuse": 100.0 + i,
            "diffuse": 40.0 + 0.5 * i,
        },
        index=idx,
    )


def test_feature_order_and_weather_delay():
    obs = _make_obs(220)
    origin = pd.Timestamp("2017-01-09 12:00")
    rows = forecast_features(obs, origin, zone="zone1")
    assert len(rows) == 24
    assert rows["horizon"].tolist() == list(range(1, 25))
    assert len(BASE) == 15 and len(WEATHER) == 5
    # Weather must come from T - 1h (11:00), NOT T (12:00)
    expected_temp = obs.loc[origin - pd.Timedelta(hours=1), "temperature"]
    assert np.allclose(rows["temperature_lag1h"].to_numpy(), expected_temp)
    # y_true must be NaN in live inference mode
    assert rows["y_true"].isna().all()


def test_future_mutation_invariance():
    obs = _make_obs(240)
    origin = pd.Timestamp("2017-01-09 12:00")
    before = forecast_features(obs, origin, zone="zone1")

    mutated = obs.copy()
    mutated.loc[mutated.index > origin, "zone1"] = -999999.0
    for col in ("temperature", "humidity", "wind_speed", "general_diffuse", "diffuse"):
        mutated.loc[mutated.index >= origin, col] = -999999.0

    after = forecast_features(mutated, origin, zone="zone1")
    pd.testing.assert_frame_equal(before[BASE + WEATHER], after[BASE + WEATHER])

    # Training sample builder and live forecast_features must agree identically on features
    train_row = build_samples(obs, [origin], zone="zone1", include_labels=True)
    pd.testing.assert_frame_equal(before[BASE + WEATHER], train_row[BASE + WEATHER])
