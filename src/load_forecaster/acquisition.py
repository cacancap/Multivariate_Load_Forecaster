"""Validated, cached downloads with immutable provenance sidecars."""
from __future__ import annotations

import hashlib
import io
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

CONFIG_VERSION = 1


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str, allow_nan=False), encoding="utf-8")


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def retry_delay(value, attempt):
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError):
                pass
    return float(2 ** attempt)


class CachedDownloader:
    def __init__(self, timeout=30, attempts=3, session=None, sleep=time.sleep):
        self.timeout, self.attempts = timeout, attempts
        self.session = session or requests.Session()
        self.sleep = sleep

    def fetch(self, url, path, validate, params=None):
        path = Path(path)
        sidecar = path.with_suffix(path.suffix + ".manifest.json")
        params = params or {}
        if path.exists():
            payload = path.read_bytes()
            validate(payload)
            manifest = json.loads(sidecar.read_text(encoding="utf-8"))
            if manifest["sha256"] != sha256(payload) or manifest["url"] != url or manifest["params"] != params:
                raise ValueError(f"Cache provenance mismatch: {path}")
            return payload
        for attempt in range(self.attempts):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                payload = response.content
                validate(payload)
                # Invalid responses never become cache entries.
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(path.suffix + ".part")
                temporary.write_bytes(payload)
                temporary.replace(path)
                write_json(sidecar, {
                    "url": url, "resolved_url": response.url, "params": params,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "sha256": sha256(payload), "bytes": len(payload),
                    "config_version": CONFIG_VERSION,
                })
                return payload
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (401, 403, 404) or attempt == self.attempts - 1:
                    raise
                retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
                self.sleep(retry_delay(retry_after, attempt))


def validate_load(payload):
    frame = pd.read_csv(io.BytesIO(payload))
    if not {"Datetime", "PJME_MW"}.issubset(frame.columns) or len(frame) == 0:
        raise ValueError("PJM CSV has missing columns or no records")
    if pd.to_datetime(frame.Datetime, errors="coerce").isna().any():
        raise ValueError("PJM CSV contains unparseable timestamps")
    if pd.to_numeric(frame.PJME_MW, errors="coerce").notna().sum() == 0:
        raise ValueError("PJM CSV has no numeric load observations")


def validate_weather(payload, params):
    obj = json.loads(payload)
    if obj.get("error"):
        raise ValueError(str(obj))
    if obj.get("utc_offset_seconds") != 0:
        raise ValueError("Weather must be requested in UTC")
    times = pd.to_datetime(obj["hourly"]["time"], unit="s", utc=True)
    expected = pd.date_range(params["start_date"], pd.Timestamp(params["end_date"]) + pd.Timedelta(days=1), freq="h", inclusive="left", tz="UTC")
    if not times.equals(expected):
        raise ValueError("Weather hourly timestamps do not cover the complete requested interval")
    for key in params["hourly"].split(","):
        values = np.asarray(obj["hourly"][key], dtype=float)
        if len(values) != len(expected) or not np.isfinite(values).all():
            raise ValueError(f"Weather variable {key} has missing/nonfinite data")
    units = obj["hourly_units"]
    if units.get("temperature_2m") != "°C" or units.get("relative_humidity_2m") != "%" or units.get("direct_normal_irradiance") != "W/m²":
        raise ValueError("Unexpected weather measurement units")
    humidity = np.asarray(obj["hourly"]["relative_humidity_2m"], dtype=float)
    if ((humidity < 0) | (humidity > 100)).any():
        raise ValueError("Humidity outside physical range")
    return obj


def fetch_load(root, config, downloader=None):
    path = Path(root) / "data/raw/PJME_hourly.csv"
    payload = (downloader or CachedDownloader()).fetch(config["source_url"], path, validate_load)
    return pd.read_csv(io.BytesIO(payload))


def fetch_weather(root, config, downloader=None):
    weather = config["weather"]
    downloader = downloader or CachedDownloader()
    frames = []
    # The final interval's mean solar radiation is labelled at its end.
    padded_end = pd.Timestamp(weather["end"]) + pd.Timedelta(days=1)
    for month in pd.period_range(weather["start"], padded_end, freq="M"):
        start = max(pd.Timestamp(weather["start"]), month.start_time)
        end = min(padded_end, month.end_time.normalize())
        params = {
            "latitude": weather["latitude"], "longitude": weather["longitude"],
            "start_date": start.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d"),
            "hourly": ",".join(weather["hourly"]), "models": weather["model"],
            "timezone": "UTC", "timeformat": "unixtime",
        }
        token = sha256(json.dumps(params, sort_keys=True).encode())[:12]
        path = Path(root) / f"data/raw/weather/{month}-{token}.json"
        payload = downloader.fetch("https://archive-api.open-meteo.com/v1/archive", path, lambda body: validate_weather(body, params), params)
        obj = validate_weather(payload, params)
        frame = pd.DataFrame(obj["hourly"])
        frame.index = pd.to_datetime(frame.pop("time"), unit="s", utc=True)
        frames.append(frame)
        print(f"weather {month}: {len(frame)} validated hours", flush=True)
    result = pd.concat(frames).sort_index()
    if not result.index.is_unique:
        raise ValueError("Duplicate UTC weather timestamps")
    result.index.name = "time"
    return result
