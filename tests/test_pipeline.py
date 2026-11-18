import io
import json

import numpy as np
import pandas as pd
import pytest
import requests

from load_forecaster.acquisition import CachedDownloader, retry_delay, validate_load, validate_weather
from load_forecaster.evaluation import common_predictions, metrics, temporal_folds
from load_forecaster.experiment import select_candidate
from load_forecaster.features import SampleBuilder
from load_forecaster.models import build_model
from load_forecaster.temporal import join_weather, prepare_load


def config(**kwargs):
    return {"timezone": "America/New_York", "timestamp_convention": "unknown", "time_convention_confirmed": False, **kwargs}


def raw_data(start="2016-01-01", periods=600):
    idx = pd.date_range(start, periods=periods, freq="h")
    return pd.DataFrame({"Datetime": idx, "PJME_MW": 30000 + np.arange(periods) + 1000 * np.sin(np.arange(periods) / 24)})


def test_future_mutation_does_not_change_causal_features_or_predictions():
    raw = raw_data()
    load, _, _ = prepare_load(raw, config())
    origin = load.index[400]
    before = SampleBuilder(load)
    changed = raw.copy()
    changed.loc[changed.Datetime > origin, "PJME_MW"] = 900000
    after_load, _, _ = prepare_load(changed, config())
    after = SampleBuilder(after_load)
    for h in (1, 6, 12, 24):
        a, b = before.features([origin], h), after.features([origin], h)
        pd.testing.assert_frame_equal(a, b)
        X, y = before.samples(load.index[200:350], h, load.index[399])
        model = build_model("ridge").fit(X, y)
        np.testing.assert_allclose(model.predict(a), model.predict(b))


def test_dst_unknown_quarantines_whole_days_and_duplicates():
    raw = raw_data("2016-03-01", 24 * 30)
    raw = pd.concat([raw, raw.iloc[[100]]], ignore_index=True).sample(frac=1, random_state=1)
    load, quarantine, report = prepare_load(raw, config())
    assert report["weather_join_allowed"] is False
    assert load.loc["2016-03-13"].blocked_time.all()
    assert len(quarantine) >= 26
    X, _ = SampleBuilder(load).samples(load.index, 24)
    assert not ((X.index >= "2016-03-13") & (X.index < "2016-03-21")).any()
    with pytest.raises(ValueError, match="unconfirmed"):
        join_weather(load, pd.DataFrame(index=load.index), report)


def test_confirmed_dst_preserves_elapsed_hours_and_quarantines_both_folds():
    raw = pd.DataFrame({"Datetime": ["2016-11-06 00:00", "2016-11-06 01:00", "2016-11-06 01:00", "2016-11-06 02:00", "2016-11-06 03:00"], "PJME_MW": [100, 90, 80, 70, 60]})
    load, quarantine, report = prepare_load(raw, config(timestamp_convention="hour_starting", time_convention_confirmed=True, time_convention_evidence="Synthetic test defines interval starts"))
    assert len(load) == 5
    assert len(quarantine) == 2
    assert load.blocked_time.sum() == 2
    assert load.index.tz is not None
    assert report["weather_join_allowed"]


def test_missing_inputs_only_forward_filled_two_hours_never_labels():
    raw = raw_data()
    raw = raw.drop(index=[300, 301, 302, 303])
    load, _, _ = prepare_load(raw, config())
    assert load.load_input.iloc[300:302].notna().all()
    assert load.load_input.iloc[302:304].isna().all()
    assert load.load_observed.iloc[300:304].isna().all()
    X, y = SampleBuilder(load).samples(load.index[250:350], 1)
    assert load.index[299] not in X.index
    assert y.notna().all()


def test_large_positive_loads_not_clipped_and_negative_quarantined():
    raw = raw_data()
    raw.loc[300, "PJME_MW"] = 100000
    raw.loc[301, "PJME_MW"] = -1
    load, q, _ = prepare_load(raw, config())
    assert load.load_observed.iloc[300] == 100000
    assert pd.isna(load.load_observed.iloc[301])
    assert len(q) == 1


def test_delay_one_omits_unavailable_day_lag_at_h24():
    load, _, _ = prepare_load(raw_data(), config())
    builder = SampleBuilder(load, delay_hours=1)
    X = builder.features([load.index[400]], 24)
    assert "target_lag_24" not in X
    assert X.origin_lag_0.iloc[0] == pytest.approx(load.load_input.iloc[399], rel=1e-6)
    assert builder.baseline([load.index[400]], 24, 24)[0] == load.load_input.iloc[376]


def test_leap_year_and_five_regular_folds_with_label_embargo():
    idx = pd.date_range("2014-01-01", "2017-01-01", freq="h", inclusive="left")
    assert len(idx[idx.year == 2016]) == 8784
    folds = list(temporal_folds(idx))
    assert len(folds) == 5
    assert all(len(v) == 1440 and t[-1] + pd.Timedelta(hours=24) < v[0] for t, v in folds)
    assert all(len(folds[i][0]) < len(folds[i + 1][0]) for i in range(4))
    with pytest.raises(ValueError):
        list(temporal_folds(idx.delete(200)))


def test_scalers_fit_train_only_and_svr_inverse_target_units():
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(100, 3)))
    y = 30000 + 1000 * X[0]
    svr = build_model("svr").fit(X, y)
    np.testing.assert_allclose(svr.transformer_.mean_, [y.mean()])
    np.testing.assert_allclose(svr.regressor_.steps[0][1].mean_, X.mean())
    before = svr.regressor_.steps[0][1].mean_.copy()
    predictions = svr.predict(pd.DataFrame(np.full((5, 3), 500)))
    np.testing.assert_allclose(svr.regressor_.steps[0][1].mean_, before)
    assert predictions.min() > 10000
    assert build_model("hist_gradient_boosting").early_stopping is False


def test_cache_reuses_hash_and_rejects_invalid_http_200(tmp_path):
    payload = b"Datetime,PJME_MW\n2016-01-01 00:00:00,30000\n"
    class Response:
        content = payload
        url = "https://example.test/load"
        def raise_for_status(self):
            pass
    class Session:
        calls = 0
        def get(self, *args, **kwargs):
            self.calls += 1
            return Response()
    session = Session()
    client = CachedDownloader(session=session, sleep=lambda _: None)
    path = tmp_path / "load.csv"
    client.fetch(Response.url, path, validate_load)
    client.fetch(Response.url, path, validate_load)
    assert session.calls == 1
    path.write_bytes(payload + b"2016-01-01 01:00:00,31000\n")
    with pytest.raises(ValueError, match="provenance"):
        client.fetch(Response.url, path, validate_load)
    Response.content = b"<html>upstream error</html>"
    invalid = tmp_path / "invalid.csv"
    with pytest.raises(ValueError):
        client.fetch(Response.url, invalid, validate_load)
    assert not invalid.exists()


def test_retry_after_is_obeyed(tmp_path):
    waits = []
    class Response:
        url = "https://example.test"
        headers = {"Retry-After": "7"}
        content = b"Datetime,PJME_MW\n2016-01-01,30000\n"
        status_code = 429
        def raise_for_status(self):
            if self.status_code == 429:
                raise requests.HTTPError(response=self)
    class Session:
        calls = 0
        def get(self, *args, **kwargs):
            self.calls += 1
            r = Response()
            if self.calls > 1:
                r.status_code = 200
            return r
    client = CachedDownloader(session=Session(), sleep=waits.append)
    client.fetch(Response.url, tmp_path / "a.csv", validate_load)
    assert waits == [7]
    assert retry_delay(None, 2) == 4


def test_weather_validates_coverage_and_units():
    idx = pd.date_range("2016-02-29", periods=24, freq="h", tz="UTC")
    names = ["temperature_2m", "relative_humidity_2m", "direct_normal_irradiance"]
    obj = {"utc_offset_seconds": 0, "hourly": {"time": idx.as_unit("s").asi8.tolist(), **{k: [20] * 24 for k in names}}, "hourly_units": dict(zip(names, ["°C", "%", "W/m²"]))}
    params = {"start_date": "2016-02-29", "end_date": "2016-02-29", "hourly": ",".join(names)}
    validate_weather(json.dumps(obj).encode(), params)
    obj["hourly"]["temperature_2m"][0] = None
    with pytest.raises(ValueError, match="nonfinite"):
        validate_weather(json.dumps(obj).encode(), params)


def test_comparison_requires_common_pairs_and_same_labels():
    frame = pd.DataFrame({"branch": ["none"] * 3, "delay_hours": [0] * 3, "origin_time": [1, 1, 2], "target_time": [2, 2, 3], "horizon": [1] * 3, "model": ["a", "b", "a"], "load_mw": [10, 10, 20], "prediction_mw": [9, 11, 19]})
    shared, coverage = common_predictions(frame)
    assert len(shared) == 2
    assert coverage["common_pairs"] == 1
    frame.loc[1, "load_mw"] = 12
    with pytest.raises(ValueError, match="disagree"):
        common_predictions(frame)


def test_selection_prefers_speed_within_point_one_percentage_point():
    assert select_candidate([{"mape_percent": 3.0, "fit_predict_seconds": 10}, {"mape_percent": 3.09, "fit_predict_seconds": 1}])["mape_percent"] == 3.09
    assert metrics([100, 200], [90, 180], 150)["peak_mape_percent"] == pytest.approx(10)


def test_end_to_end_artifacts_reload_and_checksum_guard(tmp_path, monkeypatch):
    from load_forecaster.experiment import predict_saved, resume_holdout, run_experiment
    raw = raw_data("2014-01-01", 24 * 55)
    cfg = config(seed=42, threads=1, train_start="2014-01-01", development_end="2014-02-15", test_end="2014-02-20", horizons=[1, 24], representative_horizons=[1, 24], n_splits=2, validation_hours=48, gap_hours=24, max_candidates=1, models=["ridge"])
    load, _, quality = prepare_load(raw, cfg)
    path = tmp_path / "data/raw/PJME_hourly.csv"
    path.parent.mkdir(parents=True)
    raw.to_csv(path, index=False)
    run = run_experiment(tmp_path, cfg, load, quality, profile="integration")
    assert (run / "COMPLETE.json").exists()
    predictions = pd.read_parquet(run / "test_predictions.parquet")
    assert predictions.target_time.max() < pd.Timestamp(cfg["test_end"])
    assert predictions.groupby(["origin_time", "target_time", "delay_hours"]).model.nunique().eq(3).all()
    origin = pd.Timestamp("2014-02-16 12:00")
    first = predict_saved(run, load, origin)
    second = predict_saved(run, load, origin)
    pd.testing.assert_frame_equal(first, second)
    saved = predictions[(predictions.model == "ridge") & (predictions.delay_hours == 0) & (predictions.origin_time == origin)].sort_values("horizon")
    np.testing.assert_allclose(first.prediction_mw, saved.prediction_mw)
    with pytest.raises(ValueError, match="future training"):
        predict_saved(run, load, pd.Timestamp("2014-02-01"))
    assert run_experiment(tmp_path, cfg, load, quality, profile="integration") == run
    changed = load.copy()
    changed.loc[origin, "load_input"] += 1
    with pytest.raises(ValueError, match="checksum"):
        run_experiment(tmp_path, cfg, changed, quality, profile="integration")
    # Simulate termination after checkpoints: recover predictions with zero
    # refits and no renewed hyperparameter selection, preserving pre-test files.
    (run / "COMPLETE.json").unlink()
    def forbidden(*args, **kwargs):
        raise AssertionError("Recovery must reuse complete head checkpoints")
    monkeypatch.setattr("load_forecaster.experiment._fit", forbidden)
    monkeypatch.setattr("load_forecaster.experiment.evaluate_cv", forbidden)
    assert resume_holdout(tmp_path, cfg, load, quality, profile="integration") == run
    pd.testing.assert_frame_equal(predictions, pd.read_parquet(run / "test_predictions.parquet"))
    assert json.loads((run / "recovery.json").read_text())["contract_unchanged"]
    (run / "COMPLETE.json").unlink()
    frozen = json.loads((run / "selected_models.json").read_text())
    frozen[0]["params"]["alpha"] = 999
    (run / "selected_models.json").write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="checksum"):
        resume_holdout(tmp_path, cfg, load, quality, profile="integration")


def test_confirmed_hour_ending_spring_has_no_fake_missing_hour():
    raw = pd.DataFrame({"Datetime": ["2016-03-13 01:00", "2016-03-13 02:00", "2016-03-13 04:00", "2016-03-13 05:00"], "PJME_MW": [100, 90, 80, 70]})
    load, q, _ = prepare_load(raw, config(timestamp_convention="hour_ending", time_convention_confirmed=True, time_convention_evidence="Synthetic data explicitly defines hour-ending labels"))
    assert len(load) == 4
    assert len(q) == 0
    assert load.load_observed.notna().all()


def test_weather_join_is_one_to_one_and_reports_monthly_missing():
    load, _, report = prepare_load(raw_data(), config(timestamp_convention="hour_starting", time_convention_confirmed=True, time_convention_evidence="Synthetic fixture"))
    weather = pd.DataFrame({"temperature_2m": 20.0}, index=load.index[1:])
    joined, missing = join_weather(load, weather, report)
    assert len(joined) == len(load)
    assert missing["2016-01"]["temperature_2m"] == pytest.approx(1 / len(load))
    with pytest.raises(ValueError, match="unique"):
        join_weather(load, pd.concat([weather, weather.iloc[[0]]]), report)


def test_solar_preceding_hour_mean_aligns_to_load_interval_end():
    load, _, report = prepare_load(raw_data(periods=10), config(timestamp_convention="hour_starting", time_convention_confirmed=True, time_convention_evidence="Synthetic interval-start fixture"))
    times = pd.date_range(load.index.min(), periods=11, freq="h")
    weather = pd.DataFrame({"temperature_2m": np.arange(11), "direct_normal_irradiance": np.arange(11) * 10}, index=times)
    joined, _ = join_weather(load, weather, report)
    assert joined.temperature_2m.iloc[0] == 0
    assert joined.direct_normal_irradiance.iloc[0] == 0
    assert joined.direct_normal_irradiance.iloc[-1] == 90
    assert load.index[0] == pd.Timestamp("2016-01-01 06:00", tz="UTC")
    assert report["interval_label"] == "interval_end"


def test_direct_forecast_cannot_cross_blocked_intermediate_hour():
    load, _, _ = prepare_load(raw_data(), config())
    origin = load.index[250]
    load.loc[origin + pd.Timedelta(hours=3), "blocked_time"] = True
    builder = SampleBuilder(load)
    short, _ = builder.samples([origin], 1)
    long, _ = builder.samples([origin], 6)
    assert len(short) == 1
    assert long.empty


def test_saved_weighted_ensemble_uses_selected_weights_and_same_features(tmp_path):
    import joblib
    from load_forecaster.experiment import predict_saved
    raw = raw_data()
    cfg = config(seed=42, threads=1, development_end="2016-01-16", horizons=[1])
    load, _, quality = prepare_load(raw, cfg)
    builder = SampleBuilder(load, fourier_order=2)
    X, y = builder.samples(load.index[200:350], 1, pd.Timestamp(cfg["development_end"]))
    (tmp_path / "models").mkdir()
    for name, alpha in (("ridge", 1), ("ridge_365", 1000)):
        model = build_model(name, {"alpha": alpha}).fit(X, y)
        joblib.dump({"model": model, "columns": list(X), "horizon": 1, "delay_hours": 0, "weather_mode": "none", "timezone": "America/New_York", "time_basis": quality["time_basis"], "config": cfg}, tmp_path / "models" / f"{name}-delay0-h1.joblib")
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    (tmp_path / "selected_models.json").write_text(json.dumps([{"model": "ridge", "all_horizon_cv_mape_percent": 5}, {"model": "ridge_365", "all_horizon_cv_mape_percent": 6}]))
    (tmp_path / "ensemble_selection.json").write_text(json.dumps({"models": ["ridge", "ridge_365"], "weight": 0.3, "mape_percent": 4}))
    origin = load.index[450]
    with pytest.raises(ValueError, match="completed experiment"):
        predict_saved(tmp_path, load, origin, "ridge")
    (tmp_path / "COMPLETE.json").write_text(json.dumps({"status": "complete"}))
    a = predict_saved(tmp_path, load, origin, "ridge")
    b = predict_saved(tmp_path, load, origin, "ridge_365")
    mixed = predict_saved(tmp_path, load, origin)
    assert mixed.model.eq("weighted_ensemble").all()
    np.testing.assert_allclose(mixed.prediction_mw, 0.3 * a.prediction_mw + 0.7 * b.prediction_mw)
