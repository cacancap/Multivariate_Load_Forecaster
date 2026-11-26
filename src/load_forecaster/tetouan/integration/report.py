"""Role E: Demo plotting and multi-zone summary chart/table exporter."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from load_forecaster.tetouan import ZONES, ZONE_LABELS

COLORS = {
    "ridge": "#b45309",
    "svr": "#176a59",
    "random_forest": "#275ba4",
    "day_prior": "#777982",
    "week_prior": "#974e85",
    "ridge_no_weather": "#d97706",
}
NAMES = {
    "ridge": "Ridge",
    "svr": "SVR RBF",
    "random_forest": "Random Forest",
    "day_prior": "Ngày trước",
    "week_prior": "Tuần trước",
    "ridge_no_weather": "Ridge bỏ thời tiết",
}


def _setup_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def _latest_run(root: Path, zone: str, profile: str = "full") -> Path | None:
    ref = Path(root) / "outputs/tetouan" / zone / profile
    latest = ref / "latest.txt"
    if not latest.is_file():
        return None
    run_dir = ref / latest.read_text(encoding="utf-8").strip()
    return run_dir if run_dir.is_dir() else None


def plot_demo(
    out: Path,
    table: pd.DataFrame,
    obs: pd.DataFrame,
    zone: str = "zone1",
    simulated: bool = False,
) -> Path:
    """Plot 24-hour forecast vs observed load and day-prior reference."""
    _setup_matplotlib()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    t = pd.DatetimeIndex(table["target_time"])
    actual = obs[zone].reindex(t)
    day_prior = obs[zone].reindex(t - pd.Timedelta(hours=24))
    model_key = str(table["model"].iloc[0])
    origin_ts = pd.Timestamp(table["origin_time"].iloc[0])

    fig, ax = plt.subplots(figsize=(8.6, 3.9), layout="constrained")
    ax.plot(
        table["horizon"],
        table["y_pred"],
        label=f"Dự báo ({NAMES.get(model_key, model_key)})",
        color="#126553",
        lw=2.4,
        marker="o",
        ms=3.5,
    )
    if actual.notna().any():
        ax.plot(table["horizon"], actual.to_numpy(), label="Thực đo sau phát hành", color="#1f2937", ls="--", lw=2.0)
    if day_prior.notna().any():
        ax.plot(table["horizon"], day_prior.to_numpy(), label="Đối chứng hôm trước", color="#9ca3af", ls=":", lw=1.6)

    tag = " [MÔ PHỎNG]" if simulated else ""
    ax.set_xticks([1, 4, 8, 12, 16, 20, 24])
    ax.set(
        xlabel="Bước dự báo (giờ sau khi phát hành)",
        ylabel=f"Phụ tải {ZONE_LABELS[zone]} (đơn vị nguồn)",
        title=f"Dự báo 24 giờ — {ZONE_LABELS[zone]} phát hành lúc {origin_ts:%H:%M ngày %d/%m/%Y}{tag}",
    )
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3, fontsize=8.5)
    dest = out / "demo.png"
    fig.savefig(dest, dpi=180)
    plt.close(fig)
    return dest


def export_reports(root: Path) -> Path:
    """Collect latest verified outputs from all available zones into reports/tetouan/ and plot charts."""
    _setup_matplotlib()
    root = Path(root)
    report_dir = root / "reports/tetouan"
    report_dir.mkdir(parents=True, exist_ok=True)

    zone_runs: dict[str, Path] = {}
    for z in ZONES:
        run_dir = _latest_run(root, z, "full")
        if run_dir is not None:
            zone_runs[z] = run_dir

    if not zone_runs:
        raise FileNotFoundError("No completed full runs found under outputs/tetouan/<zone>/full/")

    files_to_copy = [
        "scores.csv",
        "coverage.csv",
        "thresholds.csv",
        "weather_ablation.csv",
        "critical_hours.csv",
        "case_studies.csv",
        "training_resources.csv",
        "selection.json",
        "splits.json",
        "run_resources.json",
        "verification.json",
        "predictions.parquet",
        "all_predictions.parquet",
        "tuning.csv",
        "demo.png",
        "forecast.csv",
        "inference_resources.json",
    ]

    summary_parts = []
    ablation_parts = []
    critical_parts = []

    for z, run_dir in zone_runs.items():
        z_rep = report_dir / z
        z_rep.mkdir(parents=True, exist_ok=True)
        for fname in files_to_copy:
            src = run_dir / fname
            if src.is_file():
                shutil.copy2(src, z_rep / fname)
                if z == "zone1":
                    shutil.copy2(src, report_dir / fname)

        scores = pd.read_csv(z_rep / "scores.csv")
        overall_test = scores[(scores["split"] == "test") & (scores["slice"] == "overall")].copy()
        summary_parts.append(overall_test)

        if (z_rep / "weather_ablation.csv").is_file():
            ablation_parts.append(pd.read_csv(z_rep / "weather_ablation.csv"))
        if (z_rep / "critical_hours.csv").is_file():
            crit = pd.read_csv(z_rep / "critical_hours.csv")
            critical_parts.append(crit[crit["split"] == "test"].copy())

    for fname in ["features.json", "audit.json", "column_dictionary.json", "prepare_resources.json", "splits.json"]:
        src = root / "data/tetouan" / fname
        if src.is_file():
            shutil.copy2(src, report_dir / fname)

    if summary_parts:
        summary_df = pd.concat(summary_parts, ignore_index=True)
        summary_df.to_csv(report_dir / "summary_all_zones.csv", index=False)

    # 1. Zone 1 Test MAPE by horizon 1..24
    z1_scores_path = report_dir / "zone1/scores.csv"
    if z1_scores_path.is_file():
        s_h = pd.read_csv(z1_scores_path).query("split == 'test' and slice == 'horizon'")
        fig, ax = plt.subplots(figsize=(8.6, 3.8), layout="constrained")
        for model in ["ridge", "random_forest", "svr", "day_prior", "week_prior"]:
            part = s_h[s_h["model"] == model].sort_values("horizon")
            if part.empty:
                continue
            ax.plot(
                part["horizon"],
                part["mape_percent"],
                label=NAMES.get(model, model),
                color=COLORS.get(model, "#333333"),
                ls="--" if model.endswith("prior") else "-",
                lw=1.9,
            )
        ax.set_xticks([1, 4, 8, 12, 16, 20, 24])
        ax.set(
            xlabel="Bước dự báo (giờ)",
            ylabel="MAPE (%)",
            title="Zone 1: Sai số MAPE trên tập kiểm thử theo từng bước dự báo (h = 1..24)",
        )
        ax.grid(axis="y", alpha=0.25)
        ax.legend(ncols=3, fontsize=8.5, frameon=False)
        fig.savefig(report_dir / "horizons.png", dpi=180)
        plt.close(fig)

    # 2. Weather ablation chart across available zones
    if ablation_parts:
        ab_df = pd.concat(ablation_parts, ignore_index=True)
        fig, ax = plt.subplots(figsize=(8.8, max(3.0, 0.55 * len(ab_df))), layout="constrained")
        labels = [
            f"{ZONE_LABELS.get(r.zone, r.zone)} · {'Kiểm định ' + str(r.fold) if r.split == 'validation' else 'Kiểm thử cuối'}"
            for r in ab_df.itertuples()
        ]
        vals = ab_df["delta_mape_pp"].to_numpy()
        ax.barh(labels, vals, color=["#176a59" if v < 0 else "#b45309" for v in vals])
        ax.axvline(0.0, color="#374151", lw=1.0)
        ax.set(
            xlabel="Chênh lệch MAPE (Có thời tiết − Bỏ thời tiết), điểm phần trăm (< 0 là thời tiết giúp giảm lỗi)",
            title="Thí nghiệm thời tiết trên mô hình Ridge (cùng hàng hợp lệ)",
        )
        ax.grid(axis="x", alpha=0.2)
        fig.savefig(report_dir / "weather.png", dpi=180)
        plt.close(fig)

    # 3. Zones comparison (Test MAPE across Zone 1, Zone 2, Zone 3)
    if summary_parts:
        model_order = ["ridge", "random_forest", "svr", "day_prior", "week_prior"]
        zones_avail = [z for z in ZONES if z in zone_runs]
        fig, ax = plt.subplots(figsize=(9.0, 4.0), layout="constrained")
        x = np.arange(len(zones_avail))
        width = 0.15
        for idx, m in enumerate(model_order):
            vals = []
            for z in zones_avail:
                sub = summary_df[(summary_df["zone"] == z) & (summary_df["model"] == m)]
                vals.append(float(sub["mape_percent"].iloc[0]) if not sub.empty else np.nan)
            offset = (idx - (len(model_order) - 1) / 2) * width
            bars = ax.bar(x + offset, vals, width=width, label=NAMES.get(m, m), color=COLORS.get(m, "#555"))
            for bar, v in zip(bars, vals):
                if np.isfinite(v):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        v + 0.12,
                        f"{v:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=7.2,
                    )
        ax.set_xticks(x)
        ax.set_xticklabels([ZONE_LABELS[z] for z in zones_avail])
        ax.set(
            ylabel="MAPE tập kiểm thử (%)",
            title="So sánh sai số MAPE trên tập kiểm thử giữa các vùng và đối chứng",
        )
        ax.grid(axis="y", alpha=0.25)
        ax.legend(frameon=False, ncol=5, fontsize=8)
        fig.savefig(report_dir / "zones_comparison.png", dpi=180)
        plt.close(fig)

    # 4. Critical hours chart (Peak hour & 95% Ramp hour under-prediction / signed error)
    if critical_parts:
        crit_df = pd.concat(critical_parts, ignore_index=True)
        z1_crit = crit_df[crit_df["zone"] == "zone1"]
        if not z1_crit.empty:
            fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.8), layout="constrained")
            for ax, ev, title in [
                (axes[0], "peak_hour", "Giờ đỉnh trong cửa sổ 24h (Zone 1 Test)"),
                (axes[1], "ramp_hour", "Giờ tăng tải mạnh ≥ Q95 (Zone 1 Test)"),
            ]:
                sub = z1_crit[z1_crit["event_type"] == ev].copy()
                order = [m for m in ["ridge", "random_forest", "svr", "day_prior", "week_prior"] if m in sub["model"].values]
                sub = sub.set_index("model").loc[order].reset_index()
                y_pos = np.arange(len(sub))
                bars = ax.barh(
                    y_pos,
                    sub["mean_signed_error"],
                    color=["#b45309" if v < 0 else "#176a59" for v in sub["mean_signed_error"]],
                )
                ax.axvline(0.0, color="#374151", lw=1.0)
                ax.set_yticks(y_pos)
                ax.set_yticklabels([NAMES.get(m, m) for m in sub["model"]])
                ax.set_xlabel("Sai lệch TB có dấu (y_pred − y_true)")
                ax.set_title(title)
                vals = sub["mean_signed_error"].to_numpy(dtype=float)
                span = max(1.0, float(np.nanmax(vals) - min(0.0, np.nanmin(vals))))
                x_min = min(0.0, float(np.nanmin(vals))) - (0.58 * span if np.nanmin(vals) < 0 else 0.05 * span)
                x_max = max(0.0, float(np.nanmax(vals))) + 0.52 * span
                ax.set_xlim(x_min, x_max)
                ax.grid(axis="x", alpha=0.22)
                for bar, row in zip(bars, sub.itertuples()):
                    w = bar.get_width()
                    offset = 0.015 * span if w >= 0 else -0.015 * span
                    ax.text(
                        w + offset,
                        bar.get_y() + bar.get_height() / 2,
                        f"{row.mean_signed_error:+.0f} (thiếu {row.under_prediction_rate*100:.0f}%)",
                        va="center",
                        ha="left" if w >= 0 else "right",
                        fontsize=7.5,
                    )
            fig.savefig(report_dir / "critical_hours.png", dpi=180)
            plt.close(fig)

    return report_dir
