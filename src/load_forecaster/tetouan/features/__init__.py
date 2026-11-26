"""Role B: Sample construction, causal feature extraction, and train/inference parity."""

from .samples import (
    BASE,
    FEATURE_DESCRIPTIONS,
    WEATHER,
    WEATHER_SOURCE_COLS,
    build_samples,
    forecast_features,
    prepare_samples,
)

__all__ = [
    "BASE",
    "FEATURE_DESCRIPTIONS",
    "WEATHER",
    "WEATHER_SOURCE_COLS",
    "build_samples",
    "forecast_features",
    "prepare_samples",
]
