"""Role B: Causal 24-horizon sample builder shared across training and live inference."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from load_forecaster.acquisition import write_json
from load_forecaster.tetouan import ZONES

WEATHER_SOURCE_COLS = (
    "temperature",
    "humidity",
    "wind_speed",
    "general_diffuse",
    "diffuse",
)

BASE = [
    "load_now",
    "load_lag1h",
    "load_lag2h",
    "load_lag24h",
    "load_lag168h",
    "load_mean24h",
    "load_max24h",
    "day_lag",
    "week_lag",
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "year_sin",
    "year_cos",
]

WEATHER = [f"{col}_lag1h" for col in WEATHER_SOURCE_COLS]

FEATURE_DESCRIPTIONS = {
    "load_now": "Phụ tải của vùng tại đúng giờ phát hành T (origin_time)",
    "load_lag1h": "Phụ tải tại T - 1 giờ",
    "load_lag2h": "Phụ tải tại T - 2 giờ",
    "load_lag24h": "Phụ tải tại T - 24 giờ (cùng giờ phát hành hôm trước)",
    "load_lag168h": "Phụ tải tại T - 168 giờ (cùng giờ phát hành tuần trước)",
    "load_mean24h": "Trung bình phụ tải 24 giờ gần nhất (T-23h đến T)",
    "load_max24h": "Cực đại phụ tải 24 giờ gần nhất (T-23h đến T)",
    "day_lag": "Phụ tải tại (giờ đích - 24 giờ), luôn sẵn có trước T với h=1..24",
    "week_lag": "Phụ tải tại (giờ đích - 168 giờ), luôn sẵn có trước T với h=1..24",
    "hour_sin": "Sin chu kỳ giờ trong ngày của target_time",
    "hour_cos": "Cos chu kỳ giờ trong ngày của target_time",
    "weekday_sin": "Sin chu kỳ thứ trong tuần của target_time",
    "weekday_cos": "Cos chu kỳ thứ trong tuần của target_time",
    "year_sin": "Sin chu kỳ ngày trong năm của target_time",
    "year_cos": "Cos chu kỳ ngày trong năm của target_time",
    "temperature_lag1h": "Nhiệt độ quan sát tại T - 1 giờ (giả định trễ 1 giờ)",
    "humidity_lag1h": "Độ ẩm quan sát tại T - 1 giờ",
    "wind_speed_lag1h": "Tốc độ gió quan sát tại T - 1 giờ",
    "general_diffuse_lag1h": "Bức xạ khuếch tán chung tại T - 1 giờ",
    "diffuse_lag1h": "Bức xạ khuếch tán tại T - 1 giờ",
}


def build_samples(
    obs: pd.DataFrame,
    origins,
    zone: str = "zone1",
    include_labels: bool = True,
) -> pd.DataFrame:
    """Build 24-horizon samples using exact timestamp lookups. Shared by train & inference."""
    if zone not in obs.columns:
        raise ValueError(f"Zone column {zone!r} not found in observations")
    origins = pd.DatetimeIndex(origins)
    hour = pd.Timedelta(hours=1)
    load_series = obs[zone]

    history = pd.DataFrame(index=origins)
    for lag, key in [
        (0, "load_now"),
        (1, "load_lag1h"),
        (2, "load_lag2h"),
        (24, "load_lag24h"),
        (168, "load_lag168h"),
    ]:
        history[key] = load_series.reindex(origins - lag * hour).to_numpy()

    past_day = pd.DataFrame(
        {lag: load_series.reindex(origins - lag * hour).to_numpy() for lag in range(24)},
        index=origins,
    )
    history["load_mean24h"] = past_day.mean(axis=1, skipna=False)
    history["load_max24h"] = past_day.max(axis=1, skipna=False)

    # Weather observations arrive with a 1-hour delay relative to origin T.
    for col in WEATHER_SOURCE_COLS:
        history[f"{col}_lag1h"] = obs[col].reindex(origins - hour).to_numpy()

    frames = []
    for h in range(1, 25):
        target = origins + h * hour
        frame = history.copy()
        frame["zone"] = zone
        frame["origin_time"] = origins
        frame["target_time"] = target
        frame["horizon"] = h
        frame["day_lag"] = load_series.reindex(target - 24 * hour).to_numpy()
        frame["week_lag"] = load_series.reindex(target - 168 * hour).to_numpy()
        for key, phase in [
            ("hour", target.hour / 24.0),
            ("weekday", target.dayofweek / 7.0),
            ("year", (target.dayofyear - 1) / 365.25),
        ]:
            frame[f"{key}_sin"] = np.sin(2.0 * np.pi * phase)
            frame[f"{key}_cos"] = np.cos(2.0 * np.pi * phase)
        frame["y_true"] = load_series.reindex(target).to_numpy() if include_labels else np.nan
        frames.append(frame)

    ordered_cols = ["zone", "origin_time", "target_time", "horizon", *BASE, *WEATHER, "y_true"]
    out = pd.concat(frames, ignore_index=True)
    return out[ordered_cols].sort_values(["origin_time", "horizon"], ignore_index=True)


def forecast_features(obs: pd.DataFrame, origin, zone: str = "zone1") -> pd.DataFrame:
    """Create the 24-row feature matrix for a single exact-hour origin T."""
    origin_ts = pd.Timestamp(origin)
    if origin_ts != origin_ts.floor("h") or origin_ts.tz is not None:
        raise ValueError("Origin must be an exact hour in the naive source clock")
    return build_samples(obs, [origin_ts], zone=zone, include_labels=False)


def prepare_samples(root: Path, zones: tuple[str, ...] = ZONES) -> dict[str, pd.DataFrame]:
    """Create and persist samples_{zone}.parquet for all requested zones and features.json."""
    root = Path(root)
    dest = root / "data/tetouan"
    obs = pd.read_parquet(dest / "observations.parquet")
    origins = pd.date_range(obs.index.min().ceil("h"), obs.index.max().floor("h"), freq="h")

    result = {}
    for zone in zones:
        samples = build_samples(obs, origins, zone=zone, include_labels=True)
        samples.to_parquet(dest / f"samples_{zone}.parquet", index=False)
        result[zone] = samples

    write_json(
        dest / "features.json",
        {
            "base": BASE,
            "weather": WEATHER,
            "all": BASE + WEATHER,
            "descriptions": FEATURE_DESCRIPTIONS,
        },
    )
    return result
