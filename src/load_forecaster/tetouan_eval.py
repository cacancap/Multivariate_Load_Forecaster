"""Tetouan chronological evaluation on identical origin/target pairs.

Coverage denominator = scheduled origins times requested horizons. Targets beyond
the block end, missing measurements and unavailable predictions reduce coverage.
High-load slice coverage is conditional on an observed in-block high-load label.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .evaluation import temporal_folds

KEY = ["origin_time", "target_time", "horizon"]
HOUR = pd.Timedelta(hours=1)


def _bounds(train, evaluation):
    return {
        "train_start": train[0].isoformat(), "train_end": train[-1].isoformat(),
        "eval_start": evaluation[0].isoformat(), "eval_end": evaluation[-1].isoformat(),
    }


def _check_bounds(b):
    first, last, start, end = (pd.Timestamp(b[k]) for k in (
        "train_start", "train_end", "eval_start", "eval_end"))
    if not first <= last or last + 24 * HOUR >= start or start > end:
        raise ValueError("Train labels must precede evaluation origins with a 24-hour embargo")


def make_splits(samples):
    """Boundaries refer to origins (inclusive), before filtering feature/label NaNs."""
    origins = pd.DatetimeIndex(samples["origin_time"].drop_duplicates().sort_values())
    complete = pd.date_range(origins.min(), origins.max(), freq="h")
    if not origins.equals(complete) or (origins != origins.floor("h")).any():
        raise ValueError("Supply the complete hourly origin grid before filtering samples")
    cut = len(origins) * 4 // 5
    dev = origins[:cut]
    folds = [_bounds(tr, va) for tr, va in temporal_folds(
        dev, n_splits=3, test_size=28*24, gap=24)]
    test = _bounds(origins[:cut-24], origins[cut:])
    for b in [*folds, test]:
        _check_bounds(b)
    return {"folds": folds, "test": test}


def _metrics(truth, pred):
    y = np.asarray(truth, dtype=float)
    error = np.asarray(pred, dtype=float) - y
    nz = y != 0
    return {
        "n": len(y), "n_mape": int(nz.sum()),
        "mae": np.abs(error).mean() if len(y) else np.nan,
        "rmse": np.sqrt(np.square(error).mean()) if len(y) else np.nan,
        "mape_percent": 100*np.abs(error[nz]/y[nz]).mean() if nz.any() else np.nan,
    }


def _threshold(samples, b, horizons, fit_columns):
    tr = samples[samples.origin_time.between(b["train_start"], b["train_end"]) & samples.horizon.isin(horizons)]
    if (tr.target_time >= pd.Timestamp(b["eval_start"])).any():
        raise ValueError("Train label crosses evaluation boundary")
    # Count each observed target once across eligible direct-head training rows.
    eligible = np.isfinite(tr[fit_columns].to_numpy(dtype=float)).all(axis=1)
    measured = tr.loc[eligible, ["target_time","y_true"]].drop_duplicates()
    if measured.empty or measured.target_time.duplicated().any():
        raise ValueError("Missing or conflicting training labels")
    return measured.y_true.quantile(0.90), len(measured)


def _classification(y, p, q):
    actual, predicted = y >= q, p >= q
    tp, tn = int((actual & predicted).sum()), int((~actual & ~predicted).sum())
    fp, fn = int((~actual & predicted).sum()), int((actual & ~predicted).sum())
    def ratio(a, b):
        return a / b if b else np.nan
    return {"threshold": q, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "accuracy": ratio(tp+tn, len(y)), "precision": ratio(tp,tp+fp),
            "recall": ratio(tp,tp+fn), "f1": ratio(2*tp,2*tp+fp+fn)}


def _peak_rows(common, name, split, fold):
    # Columns sorted by horizon, so argmax resolves ties to the earliest hour.
    truth = common.pivot(index="origin_time", columns="horizon", values="y_true").reindex(columns=range(1,25))
    pred = common.pivot(index="origin_time", columns="horizon", values=name).reindex(columns=truth.columns)
    valid = truth.notna().all(axis=1) & pred.notna().all(axis=1)
    truth, pred = truth.loc[valid], pred.loc[valid]
    return pd.DataFrame({"model":name, "split":split, "fold":fold,
        "peak_magnitude_abs_error":(pred.max(axis=1)-truth.max(axis=1)).abs(),
        "peak_timing_signed_hours":pred.idxmax(axis=1)-truth.idxmax(axis=1),
        "peak_timing_abs_hours":(pred.idxmax(axis=1)-truth.idxmax(axis=1)).abs()}).reset_index()


def score(samples, splits, out: Path, smoke=False):
    """Produce joined predictions, common-row scores and paired Ridge ablation."""
    out = Path(out)
    learned = pd.read_parquet(out/"predictions.parquet")
    if learned.empty or learned.duplicated(["split","fold","model",*KEY]).any():
        raise ValueError("Empty or duplicate predictions")
    if samples.duplicated(KEY).any() or not samples.target_time.eq(
            samples.origin_time + pd.to_timedelta(samples.horizon, unit="h")).all():
        raise ValueError("Invalid sample key or target timestamp")
    learned_names = ["ridge"] if smoke else ["ridge","random_forest","svr","ridge_no_weather"]
    horizons = [1] if smoke else list(range(1,25))
    selection = out/"selection.json"
    columns = json.loads(selection.read_text(encoding="utf-8"))["inputs"]["columns"] if selection.exists() else []
    fit_columns = list(dict.fromkeys([*columns,"day_lag","week_lag","y_true"]))
    plans = [("validation", i+1, b) for i,b in enumerate(splits["folds"])]
    plans = plans[-1:] if smoke else [*plans, ("test",0,splits["test"])]
    expected_groups = {(split,fold,name) for split,fold,_ in plans for name in learned_names}
    if set(learned[["split","fold","model"]].itertuples(index=False,name=None)) != expected_groups:
        raise ValueError("Unexpected or missing split, fold or model")
    scores, weather, covers, confusions, peaks, thresholds, predictions = [], [], [], [], [], [], []
    for split, fold, b in plans:
        _check_bounds(b)
        q, training_labels = _threshold(samples, b, horizons, fit_columns)
        tag = {"split":split,"fold":fold}
        thresholds.append({**tag,"threshold_q90":q,"n_unique_train_labels":training_labels,**b})
        scheduled = samples.loc[samples.origin_time.between(b["eval_start"],b["eval_end"])
                                & samples.horizon.isin(horizons), [*KEY,"y_true","day_lag","week_lag"]].copy()
        expected_n = (int((pd.Timestamp(b["eval_end"])-pd.Timestamp(b["eval_start"]))/HOUR)+1)*len(horizons)
        if len(scheduled) != expected_n:
            raise ValueError("Incomplete scheduled origin/horizon grid")
        inside = scheduled.target_time <= pd.Timestamp(b["eval_end"])
        measured_mask = inside & np.isfinite(scheduled.y_true)
        observed = scheduled.loc[measured_mask].copy()
        pred = learned.loc[learned.split.eq(split) & learned.fold.eq(fold)].copy()
        checked = pred.merge(observed[[*KEY,"y_true"]], on=KEY, how="left",
                             validate="many_to_one", suffixes=("","_observed"))
        if checked.y_true_observed.isna().any() or not np.array_equal(checked.y_true,checked.y_true_observed):
            raise ValueError("Prediction label disagrees with observed sample or is outside evaluation dates")
        pred = pred.loc[np.isfinite(pred.y_pred)]
        wide = observed.merge(pred.pivot(index=KEY,columns="model",values="y_pred"),
                              on=KEY, how="left",validate="one_to_one")
        wide = wide.rename(columns={"day_lag":"day_prior","week_lag":"week_prior"})
        names = [*learned_names,"day_prior"] if smoke else [*learned_names,"day_prior","week_prior"]
        common_mask = np.isfinite(wide[names]).all(axis=1)
        common = wide.loc[common_mask]
        if common.empty:
            raise ValueError("No shared valid pairs")
        long = wide[[*KEY,"y_true",*names]].assign(on_common=common_mask).melt(
            id_vars=[*KEY,"y_true","on_common"],var_name="model",value_name="y_pred")
        predictions.append(long.loc[np.isfinite(long.y_pred)].assign(**tag))
        for name in names:
            covers.append({**tag,"model":name,"expected_n":expected_n,
                "outside_block_n":int((~inside).sum()),"missing_label_n":int((inside & ~measured_mask).sum()),
                "observed_n":len(observed),"available_n":int(np.isfinite(wide[name]).sum()),
                "common_n":len(common),"common_coverage":len(common)/expected_n})
            confusions.append({**tag,"model":name,**_classification(common.y_true,common[name],q)})
            if not smoke:
                peaks.append(_peak_rows(common, name, split, fold))

        # Slice masks are functions of an entire grid/observed frame to keep denominators explicit.
        slices = [("overall",0,lambda f: np.ones(len(f),dtype=bool))]
        slices += [("horizon",h,lambda f,h=h: f.horizon.eq(h)) for h in horizons]
        slices += [("high_load",0,lambda f: f.y_true.ge(q) & f.target_time.le(pd.Timestamp(b["eval_end"])))]
        for season, months in {"winter":(12,1,2),"spring":(3,4,5),"summer":(6,7,8),"autumn":(9,10,11)}.items():
            if scheduled.target_time.dt.month.isin(months).any():
                slices.append(("season_"+season,0,lambda f,m=months: f.target_time.dt.month.isin(m)))
        for label,h,mask in slices:
            sub = common.loc[mask(common)]
            denom = int(mask(scheduled).sum())
            for name in names:
                scores.append({**tag,"model":name,"slice":label,"horizon":h,
                    **_metrics(sub.y_true,sub[name]),"expected_n":denom,
                    "coverage":len(sub)/denom if denom else np.nan})
            if not smoke:
                paired = wide.loc[mask(wide)].dropna(subset=["ridge","ridge_no_weather"])
                with_w = _metrics(paired.y_true,paired.ridge)
                no_w = _metrics(paired.y_true,paired.ridge_no_weather)
                row = {**tag,"slice":label,"horizon":h,"n":len(paired),"expected_n":denom}
                for metric,short,delta in [("mae","mae","mae"),("rmse","rmse","rmse"),("mape_percent","mape","mape_pp")]:
                    row[short+"_no_weather"] = no_w[metric]
                    row[short+"_weather"] = with_w[metric]
                    row["delta_"+delta] = with_w[metric]-no_w[metric]
                weather.append(row)
    pd.concat(predictions,ignore_index=True).to_parquet(out/"all_predictions.parquet",index=False)
    result = pd.DataFrame(scores)
    result.to_csv(out/"scores.csv",index=False)
    for rows,name in [(covers,"coverage"),(thresholds,"thresholds"),(confusions,"confusion")]:
        pd.DataFrame(rows).to_csv(out/(name+".csv"),index=False)
    if weather:
        pd.DataFrame(weather).to_csv(out/"weather_ablation.csv",index=False)
        pd.concat(peaks,ignore_index=True).to_csv(out/"peak_windows.csv",index=False)
    return result
