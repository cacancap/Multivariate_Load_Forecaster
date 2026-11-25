import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from load_forecaster.tetouan_data import BASE, WEATHER, SOURCE_COLUMNS, _samples, forecast_features


def observations():
    index = pd.date_range("2017-01-01", periods=12 * 24 * 6, freq="10min")
    position = np.arange(len(index), dtype=float)
    return pd.DataFrame({col: position / (i + 1) for i, col in enumerate(SOURCE_COLUMNS.values())},
                        index=index)


def test_target_is_clock_hour_and_missing_target_stays_missing():
    obs = observations()
    origin = pd.Timestamp("2017-01-10 12:00")
    target = origin + pd.Timedelta(hours=1)
    # Removing one intermediate measurement makes even a six-row shift incorrect.
    obs = obs.drop(origin + pd.Timedelta(minutes=30))
    rows = _samples(obs, [origin], True)
    assert rows.iloc[0].target_time == target
    assert rows.iloc[0].y_true == obs.at[target, "load"]
    assert rows.iloc[-1].target_time == origin + pd.Timedelta(hours=24)
    assert rows.iloc[-1].day_lag == obs.at[origin, "load"]
    assert rows.iloc[0].temperature_lag1h == obs.at[origin-pd.Timedelta(hours=1), "temperature"]
    missing = _samples(obs.drop(target), [origin], True)
    assert pd.isna(missing.iloc[0].y_true)
    assert missing.iloc[1].y_true == rows.iloc[1].y_true


def test_future_load_and_delayed_weather_cannot_change_features_or_predictions():
    obs = observations()
    origin = pd.Timestamp("2017-01-11 12:00")
    cols = BASE + WEATHER
    history = _samples(obs, pd.date_range("2017-01-09", periods=24, freq="h"), True)
    train = history.loc[history.horizon.eq(1)]
    model = Ridge().fit(train[cols], train.y_true)
    before = forecast_features(obs, origin)
    altered = obs.copy()
    altered.loc[altered.index > origin, "load"] += 100000
    wx = [c for c in altered if c != "load"]
    altered.loc[altered.index > origin - pd.Timedelta(hours=1), wx] -= 500
    after = forecast_features(altered, origin)
    pd.testing.assert_frame_equal(before, after)
    np.testing.assert_array_equal(model.predict(before.iloc[[0]][cols]), model.predict(after.iloc[[0]][cols]))
    np.testing.assert_array_equal(before[cols], _samples(obs, [origin], True)[cols])
    assert before.y_true.isna().all()


def test_issue_time_must_be_on_the_hour():
    with pytest.raises(ValueError, match="exact hour"):
        forecast_features(observations(), pd.Timestamp("2017-01-09 12:10"))
