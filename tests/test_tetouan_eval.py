import numpy as np
import pandas as pd
import pytest

from load_forecaster.tetouan_eval import make_splits, score


def example():
    # Deterministic hourly load. Labels and both baselines come from timestamps.
    origin = pd.date_range("2017-01-01", periods=24 * 150, freq="h")
    load = pd.Series(100.0 + np.arange(len(origin)) % 19, index=origin)
    frames = []
    for h in range(1, 25):
        target = origin + pd.Timedelta(hours=h)
        frames.append(pd.DataFrame({
            "origin_time": origin, "horizon": h, "target_time": target,
            "y_true": load.reindex(target).to_numpy(),
            "day_lag": load.reindex(target - pd.Timedelta(days=1)).to_numpy(),
            "week_lag": load.reindex(target - pd.Timedelta(days=7)).to_numpy(),
        }))
    return pd.concat(frames, ignore_index=True)


def test_hour_grid_and_embargo():
    samples = example()
    splits = make_splits(samples)
    grid = samples.origin_time.drop_duplicates().sort_values()
    assert pd.Timestamp(splits["test"]["eval_start"]) == grid.iloc[len(grid) * 4 // 5]
    for b in [*splits["folds"], splits["test"]]:
        train = samples[samples.origin_time.between(b["train_start"], b["train_end"])]
        assert train.target_time.max() < pd.Timestamp(b["eval_start"])
    for b in splits["folds"]:
        assert pd.Timestamp(b["eval_end"]) - pd.Timestamp(b["eval_start"]) == pd.Timedelta(hours=671)
        assert pd.Timestamp(b["eval_end"]) < pd.Timestamp(splits["test"]["eval_start"])
    with pytest.raises(ValueError):
        make_splits(samples[samples.origin_time != grid.iloc[500]])


def test_score_checks_labels_and_coverage(tmp_path):
    samples = example()
    splits = make_splits(samples)
    b = splits["folds"][-1]
    keep = samples.horizon.eq(1) & samples.origin_time.between(b["eval_start"], b["eval_end"]) & samples.target_time.le(b["eval_end"])
    # Missing ground truth inside fold and an omitted prediction must reduce coverage.
    keep_idx = samples.index[keep]
    samples.loc[keep_idx[0], "y_true"] = np.nan
    p = samples.loc[keep_idx[2:], ["origin_time","target_time","horizon","y_true"]].copy()
    p = p.assign(model="ridge", split="validation", fold=3, y_pred=p.y_true+2)
    p.to_parquet(tmp_path/"predictions.parquet")
    result = score(samples, splits, tmp_path, smoke=True)
    g = result.query("slice == 'overall'").set_index("model")
    assert set(g.index) == {"ridge", "day_prior"}
    assert g.loc["ridge","n"] == g.loc["day_prior","n"] == 669
    assert g.loc["ridge","coverage"] == pytest.approx(669/672)
    assert g.loc["ridge","rmse"] == g.loc["ridge","mae"] == 2
    p.iloc[0, p.columns.get_loc("y_true")] += 1
    p.to_parquet(tmp_path/"predictions.parquet")
    with pytest.raises(ValueError, match="label"):
        score(samples, splits, tmp_path, smoke=True)

def test_full_pairing_weather_and_peak_outputs(tmp_path):
    samples = example()
    splits = make_splits(samples)
    groups = [("validation",i+1,b) for i,b in enumerate(splits["folds"])]
    groups.append(("test",0,splits["test"]))
    outputs=[]
    for split,fold,b in groups:
        keep = (samples.origin_time.between(b["eval_start"],b["eval_end"])
                & samples.target_time.le(b["eval_end"]) & samples.y_true.notna())
        base=samples.loc[keep,["origin_time","target_time","horizon","y_true"]]
        for name,error in [("ridge",1),("ridge_no_weather",3),("random_forest",4),("svr",5)]:
            outputs.append(base.assign(split=split,fold=fold,model=name,y_pred=base.y_true+error))
    pd.concat(outputs).to_parquet(tmp_path/"predictions.parquet",index=False)
    result=score(samples,splits,tmp_path)
    overall=result.query("split == 'test' and slice == 'overall'").set_index("model")
    assert len(overall)==6 and overall.n.nunique()==1
    assert overall.loc["svr","rmse"]==5
    assert len(result.query("split=='test' and model=='svr' and slice=='horizon'")) == 24
    diff=pd.read_csv(tmp_path/"weather_ablation.csv").query("split=='test' and slice=='overall'").iloc[0]
    assert diff.n==overall.loc["ridge","n"] and diff.delta_mae == -2
    matrix=pd.read_csv(tmp_path/"confusion.csv").query("split=='test' and model=='ridge'").iloc[0]
    assert matrix.tp+matrix.fp+matrix.tn+matrix.fn == diff.n
    peaks=pd.read_csv(tmp_path/"peak_windows.csv").query("split=='test' and model=='ridge'")
    assert len(peaks)==len(samples.origin_time.unique())//5-24
    assert peaks.peak_timing_abs_hours.eq(0).all() and peaks.peak_magnitude_abs_error.eq(1).all()
    thresholds=pd.read_csv(tmp_path/"thresholds.csv")
    assert thresholds.threshold_q90.between(115,118).all()
