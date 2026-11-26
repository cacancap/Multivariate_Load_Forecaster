"""Tests for Role E: end-to-end smoke + verification + demo plotting."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from load_forecaster.tetouan.data_eda.observations import MEMBER, prepare_observations
from load_forecaster.tetouan.features.samples import prepare_samples
from load_forecaster.tetouan.integration.pipeline import main


def _write_synthetic_uci_zip(root: Path, n_days: int = 135) -> None:
    stamps = pd.date_range("2017-01-01 00:00", periods=n_days * 24 * 6, freq="10min")
    idx = np.arange(len(stamps), dtype=float)
    df = pd.DataFrame({
        "DateTime": stamps.strftime("%m/%d/%Y %H:%M"),
        "Temperature": 18.0 + 4.0 * np.sin(2 * np.pi * idx / 144.0),
        "Humidity": 60.0 + 5.0 * np.cos(2 * np.pi * idx / 144.0),
        "Wind Speed": 2.5 + 0.3 * np.sin(idx / 30.0),
        "general diffuse flows": 100.0 + 40.0 * np.maximum(0, np.sin(2 * np.pi * idx / 144.0)),
        "diffuse flows": 50.0 + 20.0 * np.maximum(0, np.sin(2 * np.pi * idx / 144.0)),
        "Zone 1 Power Consumption": 30000.0 + 4000.0 * np.sin(2 * np.pi * idx / 144.0),
        "Zone 2  Power Consumption": 22000.0 + 3000.0 * np.sin(2 * np.pi * idx / 144.0),
        "Zone 3  Power Consumption": 16000.0 + 2000.0 * np.sin(2 * np.pi * idx / 144.0),
    })
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MEMBER, df.to_csv(index=False))
    payload = buf.getvalue()

    raw_path = root / "data/tetouan/raw/uci849.zip"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)

    from load_forecaster.acquisition import sha256, write_json
    from load_forecaster.tetouan.data_eda.observations import URL

    write_json(
        raw_path.with_suffix(".zip.manifest.json"),
        {"url": URL, "params": {}, "sha256": sha256(payload)},
    )


def test_end_to_end_smoke_pipeline(tmp_path: Path):
    _write_synthetic_uci_zip(tmp_path)
    prepare_observations(tmp_path)
    prepare_samples(tmp_path, zones=("zone1",))
    main(["split"], root=tmp_path)
    main(["smoke", "--zone", "zone1"], root=tmp_path)

    latest = (tmp_path / "outputs/tetouan/zone1/smoke/latest.txt").read_text(encoding="utf-8").strip()
    run_dir = tmp_path / "outputs/tetouan/zone1/smoke" / latest
    ver = json.loads((run_dir / "verification.json").read_text(encoding="utf-8"))
    assert ver["future_mutation_invariant"] is True
    assert (run_dir / "scores.csv").is_file()
    assert (run_dir / "weather_ablation.csv").is_file()
