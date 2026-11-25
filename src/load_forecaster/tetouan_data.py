"""Prepare UCI 849 and issue forecasts on the local-clock hourly grid."""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .acquisition import CachedDownloader, sha256, write_json

URL = "https://archive.ics.uci.edu/static/public/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity.zip"
MEMBER = "Tetuan City power consumption.csv"
SOURCE_COLUMNS = {
    "Zone 1 Power Consumption": "load",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Wind Speed": "wind_speed",
    "general diffuse flows": "general_diffuse",
    "diffuse flows": "diffuse",
}
BASE = [
    "load_now", "load_lag1h", "load_lag2h", "load_lag24h", "load_lag168h",
    "load_mean24h", "load_max24h", "day_lag", "week_lag", "hour_sin", "hour_cos",
    "weekday_sin", "weekday_cos", "year_sin", "year_cos",
]
WEATHER = [name + "_lag1h" for name in SOURCE_COLUMNS.values() if name != "load"]


def table_from_zip(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        with archive.open(MEMBER) as stream:
            table = pd.read_csv(stream, encoding="utf-8-sig")
    required = {"DateTime", *SOURCE_COLUMNS}
    if table.empty or not required.issubset(table):
        raise ValueError("Unexpected Tetouan CSV schema or empty file")
    return table


def prepare_observations(root: Path):
    dest = Path(root) / "data/tetouan"
    raw_path = dest / "raw/uci849.zip"
    payload = CachedDownloader().fetch(URL, raw_path, table_from_zip)
    raw = table_from_zip(payload)
    stamps = pd.to_datetime(raw["DateTime"], format="%m/%d/%Y %H:%M", errors="raise")
    obs = raw[list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS).apply(pd.to_numeric, errors="coerce")
    obs.index = pd.DatetimeIndex(stamps, name="observation_time")
    duplicate_rows = obs.index.duplicated(keep=False)
    unique = obs.loc[~duplicate_rows].sort_index()
    expected = pd.date_range(stamps.min(), stamps.max(), freq="10min")
    hourly = pd.date_range(stamps.min().ceil("h"), stamps.max().floor("h"), freq="h")
    stats = {}
    for col in obs:
        values = obs[col].replace([np.inf, -np.inf], np.nan)
        stats[col] = {"min": float(values.min()), "max": float(values.max()),
                      "negative": int(values.lt(0).sum()), "zero": int(values.eq(0).sum()),
                      "missing_or_nonfinite": int(values.isna().sum())}
    cleaned = unique.replace([np.inf, -np.inf], np.nan).copy()
    cleaned.loc[cleaned.load.lt(0), "load"] = np.nan
    jumps = cleaned.load.diff().abs().nlargest(5)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        raw_csv = archive.read(MEMBER)
    audit = {
        "source_url": URL, "doi": "10.24432/C5B034", "license": "CC BY 4.0",
        "archive_sha256": sha256(payload), "csv_sha256": sha256(raw_csv), "csv_member": MEMBER,
        "raw_columns": list(raw.columns), "rows": len(raw), "unique_timestamps": stamps.nunique(),
        "start": str(stamps.min()), "end": str(stamps.max()),
        "interval_counts_minutes": {str(float(k.total_seconds()/60)): int(v)
                                    for k, v in stamps.sort_values().diff().value_counts().items()},
        "missing_ten_minute_timestamps": len(expected.difference(obs.index)),
        "off_grid_rows": int((~obs.index.isin(expected)).sum()),
        "missing_hourly_timestamps": len(hourly.difference(obs.index)),
        "duplicate_rows_quarantined": int(duplicate_rows.sum()), "hourly_grid_size": len(hourly),
        "raw_null_counts": {k:int(v) for k,v in raw.isna().sum().items()},
        "value_stats": stats, "largest_abs_load_changes": {str(k):float(v) for k,v in jumps.items()},
        "unit": "source units (physical unit unconfirmed in UCI metadata)",
        "time_basis": "naive source clock; UTC offset, DST handling and publication history unconfirmed",
        "availability": "load at T assumed available; weather delayed one hour; no label imputation",
    }
    cleaned.to_parquet(dest / "observations.parquet")
    write_json(dest / "audit.json", audit)
    return cleaned


def _samples(obs, origins, include_labels):
    """Train and inference share all feature lookups. Lookups use exact timestamps."""
    origins = pd.DatetimeIndex(origins)
    hour = pd.Timedelta(hours=1)
    history = pd.DataFrame(index=origins)
    for lag, key in [(0,"load_now"),(1,"load_lag1h"),(2,"load_lag2h"),(24,"load_lag24h"),(168,"load_lag168h")]:
        history[key] = obs.load.reindex(origins - lag*hour).to_numpy()
    past_day = pd.DataFrame({lag: obs.load.reindex(origins - lag*hour).to_numpy()
                             for lag in range(24)}, index=origins)
    history["load_mean24h"] = past_day.mean(axis=1, skipna=False)
    history["load_max24h"] = past_day.max(axis=1, skipna=False)
    for name in SOURCE_COLUMNS.values():
        if name != "load":
            history[name + "_lag1h"] = obs[name].reindex(origins-hour).to_numpy()
    frames = []
    for h in range(1,25):
        target = origins + h*hour
        frame = history.copy()
        frame["origin_time"], frame["target_time"], frame["horizon"] = origins, target, h
        frame["day_lag"] = obs.load.reindex(target-24*hour).to_numpy()
        frame["week_lag"] = obs.load.reindex(target-168*hour).to_numpy()
        for key, phase in [("hour",target.hour/24),("weekday",target.dayofweek/7),
                           ("year",(target.dayofyear-1)/365.25)]:
            frame[key+"_sin"] = np.sin(2*np.pi*phase)
            frame[key+"_cos"] = np.cos(2*np.pi*phase)
        frame["y_true"] = obs.load.reindex(target).to_numpy() if include_labels else np.nan
        frames.append(frame)
    return pd.concat(frames,ignore_index=True).sort_values(["origin_time","horizon"],ignore_index=True)


def forecast_features(observations, origin):
    origin = pd.Timestamp(origin)
    if origin != origin.floor("h") or origin.tz is not None:
        raise ValueError("Origin must be an exact hour in the naive source clock")
    return _samples(observations, [origin], include_labels=False)


def prepare_samples(root: Path):
    dest = Path(root) / "data/tetouan"
    obs = pd.read_parquet(dest / "observations.parquet")
    # Keep every candidate origin including missing measurements and incomplete final targets.
    origins = pd.date_range(obs.index.min().ceil("h"), obs.index.max().floor("h"), freq="h")
    samples = _samples(obs, origins, include_labels=True)
    samples.to_parquet(dest / "samples.parquet", index=False)
    write_json(dest / "features.json", {"base":BASE, "weather":WEATHER})
    return samples


def prepare_data(root: Path):
    prepare_observations(root)
    return prepare_samples(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=["observations","samples","all"], default="all")
    args = parser.parse_args()
    {"observations":prepare_observations,"samples":prepare_samples,"all":prepare_data}[args.stage](args.root)
