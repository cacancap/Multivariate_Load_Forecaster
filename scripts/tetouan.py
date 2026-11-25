"""Run the Tetouan assignment from a source checkout. All paths are project-relative."""
import argparse
import datetime
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

# Only the forest parallelizes. Each numerical worker uses one native thread.
for name in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[name] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
import pandas as pd
from load_forecaster.resources import ResourceRecorder

DATA = ROOT / "data/tetouan"
RUNS = ROOT / "outputs/tetouan"


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def current(profile):
    directory = RUNS / profile
    ref = directory / "latest.txt"
    if not ref.exists():
        raise SystemExit(f"No completed {profile} run. Run smoke or full first.")
    return directory / ref.read_text().strip()


def observations():
    return pd.read_parquet(DATA / "observations.parquet")


def verify(out, rows, smoke):
    from load_forecaster.tetouan_data import forecast_features
    from load_forecaster.tetouan_models import predict_saved

    predictions = pd.read_parquet(out / "predictions.parquet")
    obs = observations()
    model = "ridge"
    pool = predictions[(predictions.model == model) & (predictions.horizon == 1)]
    pool = pool[pool.split == ("validation" if smoke else "test")]
    sample = pool[pool.origin_time.dt.hour == 12].iloc[0]
    origin = sample.origin_time
    label = origin + pd.Timedelta(hours=1)
    row = rows[(rows.origin_time == origin) & (rows.horizon == 1)].iloc[0]
    assert row.target_time == label
    assert row.y_true == sample.y_true == obs.loc[label, "load"]
    assert row.load_now == obs.loc[origin, "load"]
    assert row.temperature_lag1h == obs.loc[origin - pd.Timedelta(hours=1), "temperature"]
    baseline = obs.loc[label - pd.Timedelta(days=1), "load"]
    assert baseline == row.day_lag
    result = dict(origin_time=origin, target_time=label, load_at_origin=row.load_now,
                  weather_time=origin - pd.Timedelta(hours=1), temperature=row.temperature_lag1h,
                  y_true=row.y_true, ridge_pred=sample.y_pred, day_prior=baseline,
                  ridge_absolute_error=abs(sample.y_pred-row.y_true), baseline_absolute_error=abs(baseline-row.y_true))
    joined = pd.read_parquet(out / "all_predictions.parquet")
    scored = joined[(joined.origin_time == origin) & (joined.horizon == 1) & (joined.model == "day_prior")]
    assert len(scored) == 1 and scored.iloc[0].y_pred == baseline
    if not smoke:
        future = obs.copy()
        future.loc[future.index > origin] += 777
        before = forecast_features(obs, origin).sort_values("horizon")
        after = forecast_features(future, origin).sort_values("horizon")
        names = read_json(DATA / "features.json")
        cols = names["base"] + names["weather"]
        pd.testing.assert_frame_equal(before[cols], after[cols])
        replay = {}
        for name in predictions.model.unique():
            expected = predictions[(predictions.model == name) & (predictions.origin_time == origin)].sort_values("horizon")
            assert expected.horizon.tolist() == list(range(1,25))
            y = predict_saved(out, before, name)
            np.testing.assert_allclose(y, expected.y_pred, rtol=1e-9, atol=1e-6)
            np.testing.assert_allclose(predict_saved(out, after, name), y, rtol=0, atol=1e-8)
            replay[name] = float(np.max(np.abs(y - expected.y_pred.to_numpy())))
        result["max_abs_reload_error"] = replay
        result["future_mutation_checked_horizons"] = 24
    write_json(out / "verification.json",result)
    print(json.dumps(result,default=str))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["observations","samples","prepare","split","smoke","full","train","score","predict","demo"])
    parser.add_argument("--origin", help="Source-clock time, e.g. 2017-12-01 12:00")
    parser.add_argument("--model", choices=["ridge","svr","random_forest","ridge_no_weather"])
    parser.add_argument("--selection", type=Path, help="Replay a previously frozen full selection.json")
    args = parser.parse_args()
    from load_forecaster.tetouan_data import prepare_data, prepare_observations, prepare_samples, forecast_features
    from load_forecaster.tetouan_eval import make_splits, score
    from load_forecaster.tetouan_models import train, predict_saved

    rec = ResourceRecorder()
    if args.action in {"observations","samples"}:
        with rec.stage(args.action):
            {"observations":prepare_observations,"samples":prepare_samples}[args.action](ROOT)
        write_json(DATA / f"{args.action}_resources.json",rec.rows)
        return
    if args.action == "prepare" or (args.action in {"full","smoke","train"} and not (DATA / "samples.parquet").exists()):
        with rec.stage("prepare"):
            prepare_data(ROOT)
        write_json(DATA / "prepare_resources.json",rec.rows)
        if args.action == "prepare":
            return
    if args.action in {"predict","demo"}:
        out = current("full")
        origin = pd.Timestamp(args.origin or "2017-12-01 12:00")
        model = args.model or read_json(out/"selection.json")["best_model"]
        with rec.stage("load_features_and_predict_24"):
            obs = observations()
            features = forecast_features(obs,origin).sort_values("horizon")
            y = predict_saved(out,features,model)
        table = features[["origin_time","target_time","horizon"]].copy()
        table["model"] = model
        table["y_pred"] = y
        print(table.to_string(index=False))
        table.to_csv(out/"forecast.csv",index=False)
        write_json(out/"inference_resources.json",rec.rows)
        if args.action == "demo":
            from tetouan_report import plot_demo
            plot_demo(out,table,obs)
        return
    with rec.stage("read_samples_and_split"):
        rows = pd.read_parquet(DATA/"samples.parquet")
        features = read_json(DATA/"features.json")
        splits = make_splits(rows)
    if args.action == "split":
        write_json(DATA/"splits.json",splits)
        print(DATA/"splits.json")
        return
    if (DATA/"splits.json").exists():
        if read_json(DATA/"splits.json") != splits:
            raise ValueError("Stored split differs from the current hourly grid. Re-run split and review.")
    if args.action == "score":
        out = current("full")
        with rec.stage("score"):
            score(rows,read_json(out/"splits.json"),out)
        with rec.stage("verify"):
            verify(out,rows,False)
        write_json(out/"rescore_resources.json",rec.rows)
        print(out/"scores.csv")
        return
    smoke = args.action == "smoke"
    profile = RUNS / ("smoke" if smoke else "full")
    profile.mkdir(parents=True,exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime("%Y%m%d-%H%M%S-"),dir=profile))
    write_json(out/"splits.json",splits)
    if args.selection:
        if smoke:
            parser.error("--selection is for train/full")
        write_json(out/"selection.json",read_json(args.selection))
    with rec.stage("train_and_predict"):
        train(rows,features,splits,out,smoke=smoke)
    if args.action != "train":
        with rec.stage("score"):
            score(rows,splits,out,smoke=smoke)
        with rec.stage("verify"):
            verify(out,rows,smoke)
    write_json(out/"run_resources.json",rec.rows)
    tmp = profile / (uuid.uuid4().hex+".tmp")
    tmp.write_text(out.name)
    tmp.replace(profile/"latest.txt")
    print(out)


if __name__ == "__main__":
    main()
