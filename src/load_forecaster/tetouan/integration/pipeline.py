"""Role E: Unified CLI orchestrator connecting Roles A -> B -> D -> C -> E."""
from __future__ import annotations

import argparse
import datetime
import json
import tempfile
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from load_forecaster.acquisition import write_json
from load_forecaster.resources import ResourceRecorder
from load_forecaster.tetouan import ZONES
from load_forecaster.tetouan.data_eda import prepare_observations, run_eda
from load_forecaster.tetouan.evaluation import make_splits, score_run
from load_forecaster.tetouan.features import forecast_features, prepare_samples
from load_forecaster.tetouan.models import predict_saved, train_zone

from .package import create_submission_zip
from .pdf_builder import build_pdf_report
from .report import export_reports, plot_demo


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _current_run(root: Path, zone: str, profile: str = "full") -> Path:
    base = Path(root) / "outputs/tetouan" / zone / profile
    latest = base / "latest.txt"
    if not latest.is_file():
        raise FileNotFoundError(f"No {profile} run found for {zone} at {latest}")
    run_dir = base / latest.read_text(encoding="utf-8").strip()
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Missing run directory {run_dir}")
    return run_dir


def verify_run(root: Path, out: Path, samples: pd.DataFrame, obs: pd.DataFrame, zone: str, smoke: bool) -> dict:
    """Verify future-mutation invariance and exact saved-model reload."""
    data_dir = Path(root) / "data/tetouan"
    predictions = pd.read_parquet(out / "predictions.parquet")
    splits = _read_json(out / "splits.json")
    eval_split = "validation" if smoke else "test"
    sub = predictions[predictions["split"] == eval_split]
    if sub.empty:
        raise ValueError(f"No predictions found for verification in {eval_split}")

    # Pick an eligible origin in the evaluation window
    origin = pd.Timestamp(sub["origin_time"].sort_values().iloc[len(sub) // 2])
    before = forecast_features(obs, origin, zone=zone).sort_values("horizon")

    # Mutate all load values strictly after origin_time and all weather at/after origin_time
    mutated = obs.copy()
    mutated.loc[mutated.index > origin, zone] = -99999.0
    for wcol in ("temperature", "humidity", "wind_speed", "general_diffuse", "diffuse"):
        mutated.loc[mutated.index >= origin, wcol] = -99999.0
    after = forecast_features(mutated, origin, zone=zone).sort_values("horizon")

    feat_info = _read_json(data_dir / "features.json")
    cols = feat_info["base"] + feat_info["weather"]
    pd.testing.assert_frame_equal(before[cols], after[cols])

    replay_err = {}
    expected_h = [1] if smoke else list(range(1, 25))
    for model_name in sorted(predictions["model"].unique()):
        exp = predictions[(predictions["model"] == model_name) & (predictions["origin_time"] == origin)].sort_values("horizon")
        if exp.empty:
            continue
        assert exp["horizon"].tolist() == expected_h
        y_reloaded = predict_saved(out, before[before["horizon"].isin(expected_h)], model=model_name, zone=zone)
        np.testing.assert_allclose(y_reloaded, exp["y_pred"].to_numpy(), rtol=1e-9, atol=1e-6)
        y_mut = predict_saved(out, after[after["horizon"].isin(expected_h)], model=model_name, zone=zone)
        np.testing.assert_allclose(y_mut, y_reloaded, rtol=0.0, atol=1e-8)
        replay_err[model_name] = float(np.max(np.abs(y_reloaded - exp["y_pred"].to_numpy())))

    result = {
        "zone": zone,
        "verified_split": eval_split,
        "verified_origin": str(origin),
        "future_mutation_invariant": True,
        "future_mutation_checked_horizons": len(expected_h),
        "max_abs_reload_error": replay_err,
        "splits_train_end": splits["test"]["train_end"],
    }
    write_json(out / "verification.json", result)
    return result


def _ensure_data(root: Path, zones_needed: tuple[str, ...]) -> None:
    data_dir = root / "data/tetouan"
    if not (data_dir / "observations.parquet").is_file():
        prepare_observations(root)
    missing = [z for z in zones_needed if not (data_dir / f"samples_{z}.parquet").is_file()]
    if missing or not (data_dir / "features.json").is_file():
        prepare_samples(root, zones=ZONES)


def _zones_from_arg(zone_arg: str) -> tuple[str, ...]:
    return ZONES if zone_arg == "all" else (zone_arg,)


def main(argv: list[str] | None = None, root: Path | None = None) -> None:
    parser = argparse.ArgumentParser(description="Tetouan 24-hour multi-zone forecasting pipeline")
    parser.add_argument(
        "action",
        choices=[
            "observations",
            "samples",
            "prepare",
            "eda",
            "split",
            "smoke",
            "train",
            "score",
            "full",
            "predict",
            "demo",
            "report",
            "pdf",
            "package",
        ],
    )
    parser.add_argument("--zone", choices=[*ZONES, "all"], default="zone1")
    parser.add_argument("--origin", default="2017-12-01 12:00", help="Exact source-clock hour, e.g. 2017-12-01 12:00")
    parser.add_argument("--model", choices=["ridge", "svr", "random_forest", "ridge_no_weather"])
    parser.add_argument("--selection", type=Path, help="Replay a frozen selection.json")
    args = parser.parse_args(argv)

    root = Path(root) if root is not None else Path.cwd()
    data_dir = root / "data/tetouan"
    runs_root = root / "outputs/tetouan"
    rec = ResourceRecorder()

    if args.action == "observations":
        with rec.stage("observations"):
            prepare_observations(root)
        write_json(data_dir / "observations_resources.json", rec.rows)
        return

    if args.action == "samples":
        if not (data_dir / "observations.parquet").is_file():
            prepare_observations(root)
        with rec.stage("samples"):
            prepare_samples(root, zones=_zones_from_arg(args.zone))
        write_json(data_dir / "samples_resources.json", rec.rows)
        return

    if args.action == "prepare":
        with rec.stage("prepare"):
            prepare_observations(root)
            prepare_samples(root, zones=ZONES)
        write_json(data_dir / "prepare_resources.json", rec.rows)
        return

    if args.action == "eda":
        _ensure_data(root, ("zone1",))
        splits_path = data_dir / "splits.json"
        splits = _read_json(splits_path) if splits_path.is_file() else None
        summary = run_eda(root, splits=splits)
        print(json.dumps({"eda_output": str(root / "reports/tetouan/eda"), "dev_end": summary["dev_end"]}, ensure_ascii=False))
        return

    if args.action == "report":
        out_rep = export_reports(root)
        print(out_rep)
        return

    if args.action == "pdf":
        pdf_path = build_pdf_report(root)
        print(pdf_path)
        return

    if args.action == "package":
        zip_path = create_submission_zip(root)
        print(zip_path, zip_path.stat().st_size)
        return

    target_zones = _zones_from_arg(args.zone)
    _ensure_data(root, target_zones)

    if args.action in {"predict", "demo"}:
        obs = pd.read_parquet(data_dir / "observations.parquet")
        origin = pd.Timestamp(args.origin)
        for z in target_zones:
            out = _current_run(root, z, "full")
            model = args.model or _read_json(out / "selection.json")["best_model"]
            rec_inf = ResourceRecorder()
            with rec_inf.stage("load_features_and_predict_24"):
                feat_rows = forecast_features(obs, origin, zone=z).sort_values("horizon")
                y = predict_saved(out, feat_rows, model=model, zone=z)
            table = feat_rows[["zone", "origin_time", "target_time", "horizon"]].copy()
            table["model"] = model
            table["y_pred"] = y
            print(f"=== {z} ({model}) ===")
            print(table.to_string(index=False))
            table.to_csv(out / "forecast.csv", index=False)
            write_json(out / "inference_resources.json", rec_inf.rows)
            if args.action == "demo":
                demo_png = plot_demo(out, table, obs, zone=z)
                print("Saved demo chart:", demo_png)
        return

    if args.action == "split":
        rows_z1 = pd.read_parquet(data_dir / "samples_zone1.parquet")
        splits = make_splits(rows_z1)
        write_json(data_dir / "splits.json", splits)
        print(data_dir / "splits.json")
        return

    if args.action == "score":
        for z in target_zones:
            rows = pd.read_parquet(data_dir / f"samples_{z}.parquet")
            obs = pd.read_parquet(data_dir / "observations.parquet")
            out = _current_run(root, z, "full")
            splits = _read_json(out / "splits.json")
            res = score_run(rows, splits, out, zone=z, smoke=False)
            ver = verify_run(root, out, rows, obs, zone=z, smoke=False)
            print(json.dumps({"scored": res, "verified": ver["future_mutation_invariant"]}))
        return

    # smoke, train, full
    smoke = args.action == "smoke"
    obs = pd.read_parquet(data_dir / "observations.parquet")
    features = _read_json(data_dir / "features.json")
    for z in target_zones:
        rec_z = ResourceRecorder()
        with rec_z.stage("read_samples_and_split"):
            rows = pd.read_parquet(data_dir / f"samples_{z}.parquet")
            splits = make_splits(rows)
        if (data_dir / "splits.json").is_file() and _read_json(data_dir / "splits.json") != splits:
            raise ValueError("Stored split differs from the current hourly grid. Re-run split.")

        profile_dir = runs_root / z / ("smoke" if smoke else "full")
        profile_dir.mkdir(parents=True, exist_ok=True)
        out = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=profile_dir))
        write_json(out / "splits.json", splits)
        if args.selection:
            if smoke:
                parser.error("--selection is only supported for train/full")
            write_json(out / "selection.json", _read_json(args.selection))

        with rec_z.stage("train_and_predict"):
            train_zone(rows, features, splits, out, zone=z, smoke=smoke)
        if args.action != "train":
            with rec_z.stage("score"):
                score_run(rows, splits, out, zone=z, smoke=smoke)
            with rec_z.stage("verify"):
                verify_run(root, out, rows, obs, zone=z, smoke=smoke)
            if not smoke:
                # Generate default demo artifact on test origin for immediate packaging
                origin = pd.Timestamp(args.origin)
                best_m = _read_json(out / "selection.json")["best_model"]
                feat_rows = forecast_features(obs, origin, zone=z).sort_values("horizon")
                y = predict_saved(out, feat_rows, model=best_m, zone=z)
                table = feat_rows[["zone", "origin_time", "target_time", "horizon"]].copy()
                table["model"] = best_m
                table["y_pred"] = y
                table.to_csv(out / "forecast.csv", index=False)
                plot_demo(out, table, obs, zone=z)

        write_json(out / "run_resources.json", rec_z.rows)
        tmp = profile_dir / f"{uuid.uuid4().hex}.tmp"
        tmp.write_text(out.name, encoding="utf-8")
        tmp.replace(profile_dir / "latest.txt")
        print(f"[{z}] Completed {args.action}: {out}")
