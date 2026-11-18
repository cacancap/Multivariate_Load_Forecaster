"""The same availability-aware feature rules for fit and inference."""
from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar


class SampleBuilder:
    def __init__(self, load, timezone="America/New_York", weather_mode="none", delay_hours=0, fourier_order=1):
        if weather_mode not in ("none", "oracle"):
            raise ValueError("Weather mode must be none or oracle")
        if delay_hours < 0 or int(delay_hours) != delay_hours:
            raise ValueError("Publication delay must be a nonnegative integer")
        self.load, self.timezone, self.weather_mode = load, timezone, weather_mode
        self.delay = int(delay_hours)
        self.fourier_order = fourier_order
        self._future_clear = {}
        self.series = load.load_input
        self.history = pd.DataFrame(index=load.index)
        for lag in (0, 1, 2, 23, 24, 47, 48, 167, 168):
            self.history[f"origin_lag_{lag}"] = self.series.shift(lag + self.delay)
        delayed = self.series.shift(self.delay)
        for window in (24, 168):
            rolling = delayed.rolling(window, min_periods=window)
            for name in ("mean", "std", "max"):
                self.history[f"rolling_{name}_{window}"] = getattr(rolling, name)()
        self.history["imputed_history_count"] = load.imputed_input.astype(float).shift(self.delay).rolling(169, min_periods=169).sum()
        self.history_ok = load.blocked_time.astype(int).shift(self.delay).rolling(169, min_periods=169).max().eq(0)
        dates = self._local(load.index)
        self.holidays = USFederalHolidayCalendar().holidays(dates.min().normalize(), dates.max().normalize() + pd.Timedelta(days=40))

    def _local(self, times):
        times = pd.DatetimeIndex(times)
        return times.tz_convert(self.timezone).tz_localize(None) if times.tz is not None else times

    def features(self, origins, horizon):
        if horizon < 1:
            raise ValueError("Horizon must be positive")
        origins = pd.DatetimeIndex(origins)
        target = origins + pd.Timedelta(hours=horizon)
        X = self.history.reindex(origins).copy()
        for lag in (24, 168):
            if horizon + self.delay <= lag:
                X[f"target_lag_{lag}"] = self.series.reindex(target - pd.Timedelta(hours=lag)).to_numpy()
        # Same local clock yesterday is separate from 24 elapsed hours.
        local_target = self._local(target)
        local_prev = local_target - pd.Timedelta(days=1)
        if origins.tz is not None:
            prev = local_prev.tz_localize(self.timezone, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
        else:
            prev = local_prev
        available = (~prev.isna()) & (prev <= origins - pd.Timedelta(hours=self.delay))
        # For h=24 at DST boundaries / delayed publication this can be unavailable.
        # Omit the optional feature for these horizons; no future imputation.
        if horizon + self.delay <= 23:
            X["same_local_hour_yesterday"] = self.series.reindex(prev).to_numpy()
            X.loc[~available, "same_local_hour_yesterday"] = np.nan
        X["target_hour"] = local_target.hour
        X["target_weekday"] = local_target.dayofweek
        X["target_weekend"] = (local_target.dayofweek >= 5).astype(int)
        X["target_holiday"] = local_target.normalize().isin(self.holidays).astype(int)
        phases = {
            "day": np.asarray(local_target.hour) / 24,
            "week": (np.asarray(local_target.dayofweek) * 24 + np.asarray(local_target.hour)) / 168,
            "year": (np.asarray(local_target.dayofyear) - 1 + np.asarray(local_target.hour) / 24) / np.where(local_target.is_leap_year, 366, 365),
        }
        for name, phase in phases.items():
            for order in range(1, self.fourier_order + 1):
                X[f"sin_{name}_{order}"] = np.sin(2 * np.pi * order * phase)
                X[f"cos_{name}_{order}"] = np.cos(2 * np.pi * order * phase)
        if self.weather_mode == "oracle":
            weather = self.load.reindex(target)
            for name in ("temperature_2m", "relative_humidity_2m", "direct_normal_irradiance"):
                X[f"oracle_{name}"] = weather[name].to_numpy()
            temp = X.oracle_temperature_2m
            X["cooling_demand"] = np.maximum(0, temp - 22)
            X["heating_demand"] = np.maximum(0, 18 - temp)
            X["temperature_squared"] = temp ** 2
        X.loc[~self.history_ok.reindex(origins).fillna(False), :] = np.nan
        return X.astype("float32")

    def samples(self, origins, horizon, label_cutoff=None):
        X = self.features(origins, horizon)
        target = X.index + pd.Timedelta(hours=horizon)
        y = pd.Series(self.load.load_observed.reindex(target).to_numpy(), index=X.index, name="load_mw")
        # A guarded local-clock prediction cannot cross a DST transition.
        if horizon not in self._future_clear:
            # Reuse one calendar-derived mask per horizon instead of building
            # an N-by-horizon matrix for every estimator/fold/candidate.
            self._future_clear[horizon] = self.load.blocked_time.astype(int).rolling(horizon, min_periods=horizon).max().shift(-horizon).eq(0)
        future_clear = self._future_clear[horizon]
        good = X.notna().all(axis=1) & y.notna() & future_clear.reindex(X.index).fillna(False)
        if label_cutoff is not None:
            good &= target < label_cutoff
        return X.loc[good], y.loc[good]

    def at_origin(self, origin, horizons=range(1, 25)):
        return {h: self.features(pd.DatetimeIndex([origin]), h) for h in horizons}

    def baseline(self, origins, horizon, period):
        # On delayed data, h=24 may need day-before-yesterday, never y[T].
        repetitions = int(np.ceil((horizon + self.delay) / period))
        source = pd.DatetimeIndex(origins) + pd.Timedelta(hours=horizon - repetitions * period)
        return self.series.reindex(source).to_numpy()
