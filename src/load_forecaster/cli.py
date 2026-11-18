"""Command-line entry points. No network access is needed after preparation."""
import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import yaml

from .acquisition import sha256, write_json
from .experiment import boundary, predict_saved, prepare, resume_holdout, run_experiment


def main():
    parser = argparse.ArgumentParser(description="Reproducible direct load forecasting")
    parser.add_argument("command", choices=["prepare", "run", "predict"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.yaml"))
    parser.add_argument("--weather", action="store_true", help="Fetch ERA5; merge only with documented, confirmed time semantics")
    parser.add_argument("--profile", choices=["full", "smoke"], default="full")
    parser.add_argument("--branch", choices=["none", "oracle"], default="none")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--origin")
    parser.add_argument("--model")
    parser.add_argument("--delay", type=int, choices=[0, 1], default=0)
    parser.add_argument("--resume-holdout", action="store_true", help="Recover interrupted evaluation from frozen pre-test choices; no selection is repeated")
    args = parser.parse_args()
    pipeline_start = time.perf_counter()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not 1 <= config["threads"] <= 4:
        raise ValueError("threads must be between 1 and 4")
    os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(config["threads"]))
    if args.profile == "smoke":
        config.update(horizons=[1, 6, 12, 24], representative_horizons=[1, 6, 12, 24], models=["ridge", "hist_gradient_boosting"], n_splits=2, validation_hours=168, max_candidates=1, test_end="2017-02-01")
    if args.command == "predict":
        if not args.run_dir or not args.origin:
            parser.error("predict requires --run-dir and --origin")
        quality = json.loads((args.run_dir / "data_quality.json").read_text())
        load_path = root / ("data/processed/load_weather.parquet" if args.branch == "oracle" else "data/processed/load.parquet")
        load = pd.read_parquet(load_path)
        load.attrs["time_basis"] = quality["time_basis"]
        origin = boundary(args.origin, load.index)
        predictions = predict_saved(args.run_dir, load, origin, args.model, args.delay)
        target = args.run_dir / "inference" / f"{origin.strftime('%Y%m%dT%H%M')}-delay{args.delay}.csv"
        target.parent.mkdir(exist_ok=True)
        predictions.to_csv(target, index=False)
        print(predictions.to_string(index=False))
        print(f"Saved: {target}")
        return
    load, quality = prepare(root, config, with_weather=args.weather)
    if args.command == "prepare":
        print(json.dumps(quality, indent=2, ensure_ascii=False))
        return
    if args.branch == "oracle" and "temperature_2m" not in load:
        cached = root / "data/processed/load_weather.parquet"
        if cached.exists() and quality["weather_join_allowed"]:
            load = pd.read_parquet(cached)
        else:
            raise ValueError("Oracle branch unavailable: run prepare --weather with documented time semantics first")
    token = sha256(json.dumps(config, sort_keys=True).encode())[:10]
    was_cached = (root / "outputs" / f"{args.profile}-{args.branch}-{token}" / "COMPLETE.json").exists()
    run = (resume_holdout if args.resume_holdout else run_experiment)(root, config, load, quality, args.profile, args.branch)
    if not (run / "pipeline_wall_clock.json").exists():
        write_json(run / "pipeline_wall_clock.json", {"seconds": time.perf_counter() - pipeline_start, "includes_preparation": True, "profile": args.profile, "cache_replay": was_cached, "resumed_holdout_only": args.resume_holdout})
    write_json(root / "outputs/latest_run.json", {"run_dir": str(run)})
    print(f"Report: {run / 'REPORT.md'}", flush=True)


if __name__ == "__main__":
    main()
