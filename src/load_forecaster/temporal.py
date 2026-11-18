"""Time semantics, quarantine and strictly causal input repair."""
from __future__ import annotations

import numpy as np
import pandas as pd


def transition_days(start, end, timezone):
    days = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize() + pd.Timedelta(days=1), freq="D")
    local = days.tz_localize(timezone)
    duration = np.diff(local.as_unit("ns").asi8) / 3.6e12
    return days[:-1][duration != 24]


def audit_load(raw, timezone="America/New_York"):
    stamps = pd.to_datetime(raw.Datetime, errors="coerce")
    values = pd.to_numeric(raw.PJME_MW, errors="coerce")
    valid = pd.DatetimeIndex(stamps.dropna().sort_values().unique())
    missing = pd.date_range(valid.min(), valid.max(), freq="h").difference(valid)
    candidates = {}
    for name, shift in (("hour_starting", 0), ("hour_ending", 1)):
        wall = pd.DatetimeIndex(stamps) - pd.Timedelta(hours=shift)
        localized = wall.tz_localize(timezone, ambiguous="NaT", nonexistent="NaT")
        candidates[name] = {"ambiguous_or_nonexistent_rows": int(localized.isna().sum()), "wall_clock_shift_hours": -shift}
    return {
        "rows": len(raw), "start": str(stamps.min()), "end": str(stamps.max()),
        "sorted_increasing": bool(stamps.is_monotonic_increasing),
        "parse_failures": int(stamps.isna().sum()), "missing_values": int(values.isna().sum()),
        "negative_values": int((values < 0).sum()), "exact_duplicate_rows": int(raw.duplicated().sum()),
        "duplicate_timestamp_rows": int(stamps.duplicated().sum()),
        "duplicate_records": raw[stamps.duplicated(False)].to_dict("records"),
        "missing_naive_hours": len(missing), "missing_naive_timestamps": [str(x) for x in missing],
        "minimum_mw": float(values.min()), "maximum_mw": float(values.max()),
        "rows_per_year": {str(k): int(v) for k, v in stamps.dt.year.value_counts().sort_index().items()},
        "time_semantics_candidates": candidates,
        "warning": "Candidate diagnostics do not establish source time semantics or duplicate ordering.",
    }


def prepare_load(raw, config):
    frame = raw.copy()
    frame["source_row"] = np.arange(len(frame))
    frame["timestamp_original"] = frame.Datetime.astype(str)
    wall = pd.to_datetime(frame.Datetime, errors="coerce")
    value = pd.to_numeric(frame.PJME_MW, errors="coerce")
    frame["load_original"] = value
    frame["invalid_value"] = ~np.isfinite(value) | (value <= 0)
    convention = config.get("timestamp_convention", "unknown")
    confirmed = bool(config.get("time_convention_confirmed", False))
    if confirmed and convention not in ("hour_starting", "hour_ending"):
        raise ValueError("Confirmed time convention must be hour_starting or hour_ending")
    if confirmed and not config.get("time_convention_evidence"):
        raise ValueError("Confirmed time convention requires documented time_convention_evidence")
    if convention not in ("unknown", "hour_starting", "hour_ending"):
        raise ValueError("Unsupported timestamp convention")
    guarded = not confirmed
    if guarded:
        # Preserve native labels: NO speculative timezone conversion or weather merge.
        index = pd.DatetimeIndex(wall)
        days = transition_days(index.min(), index.max(), config["timezone"])
        ambiguous = index.duplicated(False)
        bad_time = ambiguous | index.normalize().isin(days) | index.isna()
        basis = "local_clock_unconfirmed_guarded"
    else:
        adjusted = pd.DatetimeIndex(wall) - pd.Timedelta(hours=int(convention == "hour_ending"))
        # Normalize wall-clock interval starts first, then label the physical
        # interval by its END. y[T] is therefore completed and usable at origin T.
        index = adjusted.tz_localize(config["timezone"], ambiguous="NaT", nonexistent="NaT").tz_convert("UTC") + pd.Timedelta(hours=1)
        bad_time = index.isna() | index.duplicated(False)
        basis = "UTC_confirmed_" + convention + "_interval_end"
    frame["time_invalid"] = bad_time
    frame["time"] = index
    quarantined = frame[bad_time | frame.invalid_value].copy()
    usable = frame[~bad_time].copy().set_index("time").sort_index()
    if not usable.index.is_unique:
        raise ValueError("Unresolved duplicate timestamps")
    grid = pd.date_range(index[~index.isna()].min(), index[~index.isna()].max(), freq="h")
    result = usable.reindex(grid)
    result.index.name = "time"
    result["blocked_time"] = False
    if guarded:
        result["blocked_time"] = result.index.normalize().isin(days)
    else:
        # Quarantine both possible physical instances of an ambiguous hour.
        uncertain_wall = adjusted[bad_time & ~adjusted.isna()]
        for dst in (True, False):
            uncertain = uncertain_wall.tz_localize(config["timezone"], ambiguous=dst, nonexistent="NaT").tz_convert("UTC").dropna() + pd.Timedelta(hours=1)
            result.loc[result.index.isin(uncertain), "blocked_time"] = True
    result["load_observed"] = result.load_original.where(~result.invalid_value.fillna(True).astype(bool))
    result["load_input"] = result.load_observed.ffill(limit=2)
    result.loc[result.blocked_time, "load_input"] = np.nan
    result["imputed_input"] = result.load_observed.isna() & result.load_input.notna()
    # Diagnostic only: never clip or remove large positive loads.
    result["large_jump"] = result.load_observed.diff().abs().gt(10000)
    result.attrs["time_basis"] = basis
    report = {
        "time_basis": basis, "weather_join_allowed": not guarded,
        "grid_hours": len(result), "quarantined_source_rows": len(quarantined),
        "missing_observed_hours": int(result.load_observed.isna().sum()),
        "imputed_input_hours": int(result.imputed_input.sum()),
        "blocked_time_hours": int(result.blocked_time.sum()),
        "large_jump_hours": int(result.large_jump.sum()),
        "time_convention_evidence": config.get("time_convention_evidence"),
        "interval_label": "native_unconfirmed" if guarded else "interval_end",
        "limitations": ["Historical load revisions are not reconstructed.", "Unknown convention: guarded local-clock windows, not a UTC operational replay."] if guarded else ["Historical load revisions and actual publication delays are not reconstructed."],
    }
    return result, quarantined, report


def join_weather(load, weather, time_report):
    if not time_report["weather_join_allowed"]:
        raise ValueError("Weather join blocked: source time convention is unconfirmed")
    if not load.index.is_unique or not weather.index.is_unique:
        raise ValueError("Weather join requires unique timestamps")
    # Both load and preceding-hour radiation use END labels. Temperature and
    # humidity are instantaneous at that same endpoint, in the oracle branch.
    result = load.join(weather, how="left", validate="one_to_one")
    if len(result) != len(load):
        raise AssertionError("Join changed load row count")
    rates = result[weather.columns].isna().groupby(result.index.strftime("%Y-%m")).mean()
    return result, rates.to_dict("index")
