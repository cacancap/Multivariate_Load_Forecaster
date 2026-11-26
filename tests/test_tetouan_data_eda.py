"""Tests for Role A: schema normalization, 3-zone observations, audit, and dev-only EDA."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from load_forecaster.tetouan.data_eda.eda import run_eda
from load_forecaster.tetouan.data_eda.observations import MEMBER, prepare_observations, table_from_zip
from load_forecaster.tetouan.evaluation.splits import make_splits


def _synthetic_zip_bytes(n_hours: int = 240) -> bytes:
    stamps = pd.date_range("2017-01-01 00:00", periods=n_hours * 6, freq="10min")
    idx = np.arange(len(stamps), dtype=float)
    df = pd.DataFrame({
        "DateTime": stamps.strftime("%m/%d/%Y %H:%M"),
        "Temperature": 15.0 + 5.0 * np.sin(2 * np.pi * idx / 144.0),
        "Humidity": 60.0 + 10.0 * np.cos(2 * np.pi * idx / 144.0),
        "Wind Speed": 3.0 + 0.5 * np.sin(idx / 20.0),
        "general diffuse flows": 120.0 + 80.0 * np.maximum(0, np.sin(2 * np.pi * idx / 144.0)),
        "diffuse flows": 50.0 + 30.0 * np.maximum(0, np.sin(2 * np.pi * idx / 144.0)),
        "Zone 1 Power Consumption": 30000.0 + 5000.0 * np.sin(2 * np.pi * idx / 144.0),
        # Deliberately include double spaces matching the real UCI CSV header
        "Zone 2  Power Consumption": 20000.0 + 3000.0 * np.sin(2 * np.pi * idx / 144.0),
        "Zone 3  Power Consumption": 15000.0 + 2500.0 * np.sin(2 * np.pi * idx / 144.0),
    })
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MEMBER, df.to_csv(index=False))
    return buf.getvalue()


class _FakeDownloader:
    def __init__(self, payload: bytes):
        self.payload = payload

    def fetch(self, url, path, validate, params=None):
        validate(self.payload)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.payload)
        return self.payload


def test_table_from_zip_normalizes_double_spaces():
    payload = _synthetic_zip_bytes(24)
    table = table_from_zip(payload)
    assert "Zone 2 Power Consumption" in table.columns
    assert "Zone 3 Power Consumption" in table.columns


def test_prepare_observations_and_dev_only_eda(tmp_path: Path):
    payload = _synthetic_zip_bytes(25 * 24)
    obs = prepare_observations(tmp_path, downloader=_FakeDownloader(payload))
    assert {"zone1", "zone2", "zone3", "temperature", "humidity"}.issubset(obs.columns)
    audit = json.loads((tmp_path / "data/tetouan/audit.json").read_text(encoding="utf-8"))
    assert audit["rows"] == 25 * 24 * 6
    assert audit["duplicate_rows_quarantined"] == 0

    summary = run_eda(tmp_path)
    for fig_name in ("eda_hourly_zones.png", "eda_weekday_weekend.png", "eda_temp_load.png", "eda_ramp_window.png"):
        assert (tmp_path / "reports/tetouan/eda" / fig_name).is_file()
    assert pd.Timestamp(summary["dev_end"]) < obs.index.max()
