"""Role A: Download, validate, clean, and audit UCI 849 Tetouan 3-zone observations."""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from load_forecaster.acquisition import CachedDownloader, sha256, write_json

URL = "https://archive.ics.uci.edu/static/public/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity.zip"
MEMBER = "Tetuan City power consumption.csv"
EXPECTED_ZIP_SHA256 = "3c4bf684161180937043a9fb65701a83d44b740b0d42f0492b6e7aec57ddbbfe"

SOURCE_COLUMNS = {
    "Zone 1 Power Consumption": "zone1",
    "Zone 2 Power Consumption": "zone2",
    "Zone 3 Power Consumption": "zone3",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Wind Speed": "wind_speed",
    "general diffuse flows": "general_diffuse",
    "diffuse flows": "diffuse",
}

COLUMN_DICTIONARY = [
    {"column": "observation_time", "source": "DateTime", "type": "datetime64[ns]", "role": "Chỉ số thời gian", "unit": "Giờ gốc địa phương (10 phút/mốc, chưa xác nhận múi giờ/DST)"},
    {"column": "zone1", "source": "Zone 1 Power Consumption", "type": "float64", "role": "Phụ tải Zone 1 (thực nghiệm chính)", "unit": "Đơn vị nguồn (metadata UCI chưa xác nhận kW/MW)"},
    {"column": "zone2", "source": "Zone 2  Power Consumption", "type": "float64", "role": "Phụ tải Zone 2 (mở rộng so sánh)", "unit": "Đơn vị nguồn"},
    {"column": "zone3", "source": "Zone 3  Power Consumption", "type": "float64", "role": "Phụ tải Zone 3 (mở rộng so sánh)", "unit": "Đơn vị nguồn"},
    {"column": "temperature", "source": "Temperature", "type": "float64", "role": "Nhiệt độ môi trường", "unit": "°C (theo mô tả UCI)"},
    {"column": "humidity", "source": "Humidity", "type": "float64", "role": "Độ ẩm tương đối", "unit": "%"},
    {"column": "wind_speed", "source": "Wind Speed", "type": "float64", "role": "Tốc độ gió", "unit": "m/s (theo mô tả UCI)"},
    {"column": "general_diffuse", "source": "general diffuse flows", "type": "float64", "role": "Bức xạ khuếch tán chung", "unit": "W/m² (theo mô tả UCI)"},
    {"column": "diffuse", "source": "diffuse flows", "type": "float64", "role": "Bức xạ khuếch tán", "unit": "W/m² (theo mô tả UCI)"},
]


def _normalize_col(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip())


def table_from_zip(payload: bytes) -> pd.DataFrame:
    """Read and validate the Tetouan CSV inside the UCI ZIP payload."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        with archive.open(MEMBER) as stream:
            table = pd.read_csv(stream, encoding="utf-8-sig")
    table = table.rename(columns={c: _normalize_col(c) for c in table.columns})
    required = {"DateTime", *SOURCE_COLUMNS}
    if table.empty or not required.issubset(table.columns):
        missing = sorted(required.difference(table.columns))
        raise ValueError(f"Unexpected Tetouan CSV schema or empty file; missing={missing}")
    return table


def _traceback_example(raw: pd.DataFrame, stamps: pd.Series) -> dict:
    """Provide concrete 1-based CSV row traceback examples for Role D verification."""
    examples = {}
    for label, target in [("origin_example", "2017-03-01 12:00:00"), ("target_example", "2017-03-01 13:00:00")]:
        ts = pd.Timestamp(target)
        mask = stamps == ts
        if mask.any():
            idx = int(np.flatnonzero(mask.to_numpy())[0])
            row = raw.iloc[idx]
            examples[label] = {
                "csv_data_row_1based": idx + 1,
                "csv_line_with_header": idx + 2,
                "DateTime": str(row["DateTime"]),
                "zone1": float(row["Zone 1 Power Consumption"]),
                "zone2": float(row["Zone 2 Power Consumption"]),
                "zone3": float(row["Zone 3 Power Consumption"]),
                "temperature": float(row["Temperature"]),
            }
    return examples


def prepare_observations(root: Path, downloader: CachedDownloader | None = None) -> pd.DataFrame:
    """Download UCI 849, clean all 3 zones + weather, and write observations, audit, and dictionary."""
    root = Path(root)
    dest = root / "data/tetouan"
    dest.mkdir(parents=True, exist_ok=True)
    raw_path = dest / "raw/uci849.zip"

    payload = (downloader or CachedDownloader()).fetch(URL, raw_path, table_from_zip)
    archive_hash = sha256(payload)
    raw = table_from_zip(payload)
    stamps = pd.to_datetime(raw["DateTime"], format="%m/%d/%Y %H:%M", errors="raise")

    obs = raw[list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS).apply(pd.to_numeric, errors="coerce")
    obs.index = pd.DatetimeIndex(stamps, name="observation_time")

    duplicate_rows = obs.index.duplicated(keep=False)
    unique = obs.loc[~duplicate_rows].sort_index()
    expected = pd.date_range(stamps.min(), stamps.max(), freq="10min")
    hourly = pd.date_range(stamps.min().ceil("h"), stamps.max().floor("h"), freq="h")

    stats = {}
    for col in obs.columns:
        values = obs[col].replace([np.inf, -np.inf], np.nan)
        stats[col] = {
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": float(values.mean()),
            "negative": int(values.lt(0).sum()),
            "zero": int(values.eq(0).sum()),
            "missing_or_nonfinite": int(values.isna().sum()),
        }

    cleaned = unique.replace([np.inf, -np.inf], np.nan).copy()
    for zcol in ("zone1", "zone2", "zone3"):
        cleaned.loc[cleaned[zcol].lt(0), zcol] = np.nan

    largest_jumps = {
        zcol: {str(k): float(v) for k, v in cleaned[zcol].diff().abs().nlargest(5).items()}
        for zcol in ("zone1", "zone2", "zone3")
    }

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        raw_csv = archive.read(MEMBER)

    valid_hourly = hourly.intersection(cleaned.index)
    audit = {
        "source_url": URL,
        "doi": "10.24432/C5B034",
        "license": "CC BY 4.0",
        "expected_zip_sha256": EXPECTED_ZIP_SHA256,
        "archive_sha256": archive_hash,
        "sha256_matches_official": archive_hash == EXPECTED_ZIP_SHA256,
        "csv_sha256": sha256(raw_csv),
        "csv_member": MEMBER,
        "raw_columns": list(raw.columns),
        "rows": int(len(raw)),
        "unique_timestamps": int(stamps.nunique()),
        "start": str(stamps.min()),
        "end": str(stamps.max()),
        "interval_counts_minutes": {
            str(float(k.total_seconds() / 60)): int(v)
            for k, v in stamps.sort_values().diff().value_counts().items()
        },
        "missing_ten_minute_timestamps": int(len(expected.difference(obs.index))),
        "off_grid_rows": int((~obs.index.isin(expected)).sum()),
        "missing_hourly_timestamps": int(len(hourly.difference(obs.index))),
        "duplicate_rows_quarantined": int(duplicate_rows.sum()),
        "hourly_grid_size": int(len(hourly)),
        "valid_hourly_timestamps": int(len(valid_hourly)),
        "raw_null_counts": {k: int(v) for k, v in raw.isna().sum().items()},
        "value_stats": stats,
        "largest_abs_load_changes": largest_jumps,
        "unit": "source units (physical unit unconfirmed in UCI metadata)",
        "time_basis": "naive source clock; UTC offset, DST handling and publication history unconfirmed",
        "availability": "load at T assumed available; weather delayed one hour; no label imputation",
        "quarantine_rule": "Duplicate timestamps (keep=False), non-finite values, and negative load values (<0) are set to NaN/quarantined.",
        "traceback_examples": _traceback_example(raw, stamps),
    }

    cleaned.to_parquet(dest / "observations.parquet")
    pd.DataFrame({"valid_hourly_time": valid_hourly}).to_parquet(dest / "valid_hours.parquet", index=False)
    write_json(dest / "audit.json", audit)
    write_json(dest / "column_dictionary.json", COLUMN_DICTIONARY)
    return cleaned
