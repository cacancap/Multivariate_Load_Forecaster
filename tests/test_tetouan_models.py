"""Tests for Role C: multi-horizon training, exact reload, and retrospective forecast blocking."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from load_forecaster.tetouan.evaluation.splits import make_splits
from load_forecaster.tetouan.features.samples import BASE, WEATHER, build_samples
from load_forecaster.tetouan.models.predict import predict_saved
from load_forecaster.tetouan.models.train import train_zone


def _synthetic_samples(hours: int = 140 * 24) -> tuple[pd.DataFrame, pd.DataFrame]:
    idx = pd.date_range("2017-01-01 00:00", periods=hours, freq="h")
    i = np.arange(hours, dtype=float)
    obs = pd.DataFrame(
        {
            "zone1": 30000.0 + 4000.0 * np.sin(2 * np.pi * i / 24.0) + 10.0 * np.sin(i / 50.0),
            "temperature": 18.0 + 4.0 * np.sin(2 * np.pi * i / 24.0),
            "humidity": 60.0 + 5.0 * np.cos(2 * np.pi * i / 24.0),
            "wind_speed": 2.0 + 0.2 * np.sin(i / 10.0),
            "general_diffuse": 100.0 + 20.0 * np.sin(i / 12.0),
            "diffuse": 40.0 + 10.0 * np.cos(i / 12.0),
        },
        index=idx,
    )
    samples = build_samples(obs, idx, zone="zone1", include_labels=True)
    return obs, samples


def test_smoke_train_reload_and_block_retrospective(tmp_path: Path):
    _, samples = _synthetic_samples()
    splits = make_splits(samples)
    features = {"base": BASE, "weather": WEATHER}
    out = tmp_path / "smoke_run"

    preds = train_zone(samples, features, splits, out, zone="zone1", smoke=True)
    assert (out / "models/ridge-h1.joblib").is_file()
    assert (out / "selection.json").is_file()

    # Reloaded prediction must match predictions.parquet
    val_origins = preds["origin_time"].iloc[:5]
    rows = samples[(samples["horizon"] == 1) & (samples["origin_time"].isin(val_origins))].copy()
    reloaded = predict_saved(out, rows, model="ridge", zone="zone1")
    expected = preds.loc[preds["origin_time"].isin(val_origins), "y_pred"].to_numpy()
    np.testing.assert_allclose(reloaded, expected, rtol=1e-9, atol=1e-6)

    # Retrospective origin (inside training set) must raise ValueError
    early_origin = samples[samples["horizon"] == 1].iloc[200:201]
    with pytest.raises(ValueError, match="precedes availability"):
        predict_saved(out, early_origin, model="ridge", zone="zone1")

    # Wrong zone request must raise ValueError
    with pytest.raises(ValueError, match="belongs to"):
        predict_saved(out, rows, model="ridge", zone="zone2")
