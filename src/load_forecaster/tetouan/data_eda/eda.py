"""Role A: Exploratory data analysis strictly restricted to the development period."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from load_forecaster.acquisition import write_json
from load_forecaster.tetouan import ZONES, ZONE_LABELS

COLORS = {"zone1": "#176a59", "zone2": "#275ba4", "zone3": "#b45309"}


def _setup_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def _dev_slice(obs: pd.DataFrame, splits: dict | None) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    hourly_idx = obs.index[obs.index == obs.index.floor("h")]
    if splits is not None:
        start = pd.Timestamp(splits["folds"][0]["train_start"])
        end = pd.Timestamp(splits["test"]["train_end"])
    else:
        cut = len(hourly_idx) * 4 // 5
        start = hourly_idx[0]
        end = hourly_idx[max(0, cut - 25)]
    dev_obs = obs.loc[(obs.index >= start) & (obs.index <= end)].copy()
    return dev_obs, start, end


def run_eda(root: Path, splits: dict | None = None) -> dict:
    """Generate the 4 dev-only EDA figures and summary JSON in reports/tetouan/eda/."""
    _setup_matplotlib()
    root = Path(root)
    obs = pd.read_parquet(root / "data/tetouan/observations.parquet")
    dev_obs, dev_start, dev_end = _dev_slice(obs, splits)
    hourly = dev_obs.loc[dev_obs.index == dev_obs.index.floor("h")].copy()
    hourly["hour"] = hourly.index.hour
    hourly["is_weekend"] = hourly.index.dayofweek >= 5

    out_dir = root / "reports/tetouan/eda"
    out_dir.mkdir(parents=True, exist_ok=True)
    scope_txt = f"Phạm vi phát triển (không chạm tập test): {dev_start:%d/%m/%Y %H:%M} – {dev_end:%d/%m/%Y %H:%M}"

    # 1. Typical hourly profile across 3 zones (mean + IQR)
    fig, ax = plt.subplots(figsize=(8.6, 4.2), layout="constrained")
    for z in ZONES:
        grp = hourly.groupby("hour")[z]
        mean = grp.mean()
        q25 = grp.quantile(0.25)
        q75 = grp.quantile(0.75)
        ax.plot(mean.index, mean.values, label=ZONE_LABELS[z], color=COLORS[z], lw=2.2)
        ax.fill_between(mean.index, q25.values, q75.values, color=COLORS[z], alpha=0.14)
    ax.set_xticks(range(0, 24, 2))
    ax.set(
        xlabel="Giờ trong ngày",
        ylabel="Phụ tải (đơn vị nguồn)",
        title="Hình EDA 1: Đường phụ tải điển hình theo giờ của 3 vùng (trung bình và IQR)",
    )
    fig.suptitle(scope_txt, fontsize=9, color="#4b5563")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3)
    fig.savefig(out_dir / "eda_hourly_zones.png", dpi=180)
    plt.close(fig)

    # 2. Weekday vs weekend across 3 zones
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.8), layout="constrained", sharex=True)
    weekday_stats = {}
    for ax, z in zip(axes, ZONES):
        wd = hourly.loc[~hourly.is_weekend].groupby("hour")[z].mean()
        we = hourly.loc[hourly.is_weekend].groupby("hour")[z].mean()
        ax.plot(wd.index, wd.values, label="Ngày thường (T2–T6)", color=COLORS[z], lw=2.2)
        ax.plot(we.index, we.values, label="Cuối tuần (T7–CN)", color="#374151", ls="--", lw=1.8)
        ax.set_title(ZONE_LABELS[z])
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xlabel("Giờ")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(frameon=False, fontsize=8)
        weekday_stats[z] = {
            "weekday_mean": float(hourly.loc[~hourly.is_weekend, z].mean()),
            "weekend_mean": float(hourly.loc[hourly.is_weekend, z].mean()),
            "diff_pct": float(100 * (hourly.loc[hourly.is_weekend, z].mean() - hourly.loc[~hourly.is_weekend, z].mean()) / hourly.loc[~hourly.is_weekend, z].mean()),
        }
    axes[0].set_ylabel("Phụ tải trung bình (đơn vị nguồn)")
    fig.suptitle(f"Hình EDA 2: Phụ tải ngày thường và cuối tuần theo từng vùng\n{scope_txt}", fontsize=10)
    fig.savefig(out_dir / "eda_weekday_weekend.png", dpi=180)
    plt.close(fig)

    # 3. Load vs temperature at fixed hours (14:00 & 20:00)
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), layout="constrained", sharey=True)
    temp_corr = {}
    for ax, hr in zip(axes, (14, 20)):
        sub = hourly.loc[hourly.hour == hr].dropna(subset=["temperature", "zone1"])
        ax.scatter(sub["temperature"], sub["zone1"], s=14, alpha=0.38, color="#275ba4", label="Quan sát thực tế")
        bins = pd.qcut(sub["temperature"], q=8, duplicates="drop")
        trend = sub.groupby(bins, observed=False).agg(t=("temperature", "mean"), y=("zone1", "mean"))
        ax.plot(trend["t"], trend["y"], color="#b45309", lw=2.4, marker="o", ms=4, label="Xu hướng theo phân vị")
        corr = float(sub["temperature"].corr(sub["zone1"]))
        temp_corr[f"hour_{hr}"] = corr
        ax.set_title(f"Khung {hr:02d}:00 (r = {corr:.3f})")
        ax.set(xlabel="Nhiệt độ (°C)")
        ax.grid(alpha=0.22)
        ax.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel("Phụ tải Zone 1 (đơn vị nguồn)")
    fig.suptitle(f"Hình EDA 3: Quan hệ phụ tải Zone 1 theo nhiệt độ ở cùng khung giờ\n{scope_txt}", fontsize=10)
    fig.savefig(out_dir / "eda_temp_load.png", dpi=180)
    plt.close(fig)

    # 4. Steepest positive hourly ramp 24h window in dev set (Zone 1)
    diffs = hourly["zone1"].diff()
    ramp_time = diffs.idxmax()
    ramp_val = float(diffs.loc[ramp_time])
    win_start = max(hourly.index.min(), ramp_time - pd.Timedelta(hours=10))
    win_end = win_start + pd.Timedelta(hours=23)
    if win_end > hourly.index.max():
        win_end = hourly.index.max()
        win_start = win_end - pd.Timedelta(hours=23)
    win = hourly.loc[win_start:win_end]

    fig, ax = plt.subplots(figsize=(8.6, 3.9), layout="constrained")
    ax.plot(win.index, win["zone1"], color="#176a59", lw=2.3, marker="o", ms=4, label="Phụ tải Zone 1")
    ax.axvline(ramp_time, color="#b45309", ls="--", lw=1.6, label=f"Giờ tăng mạnh nhất: {ramp_time:%d/%m %H:%M} (+{ramp_val:,.0f})")
    ax.scatter([ramp_time], [win.loc[ramp_time, "zone1"]], color="#b45309", s=70, zorder=5)
    ax.set(
        xlabel="Thời điểm",
        ylabel="Phụ tải Zone 1 (đơn vị nguồn)",
        title=f"Hình EDA 4: Cửa sổ 24 giờ minh họa mức tăng tải nhanh nhất ({win_start:%d/%m/%Y %H:%M} – {win_end:%d/%m/%Y %H:%M})",
    )
    fig.suptitle(scope_txt, fontsize=9, color="#4b5563")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8.5)
    fig.savefig(out_dir / "eda_ramp_window.png", dpi=180)
    plt.close(fig)

    peak_hours = {z: int(hourly.groupby("hour")[z].mean().idxmax()) for z in ZONES}
    trough_hours = {z: int(hourly.groupby("hour")[z].mean().idxmin()) for z in ZONES}

    summary = {
        "dev_start": str(dev_start),
        "dev_end": str(dev_end),
        "hourly_rows_dev": int(len(hourly)),
        "peak_hour_mean": peak_hours,
        "trough_hour_mean": trough_hours,
        "weekday_vs_weekend": weekday_stats,
        "temperature_correlation_zone1": temp_corr,
        "steepest_ramp_zone1": {
            "timestamp": str(ramp_time),
            "delta_load": ramp_val,
            "window_start": str(win_start),
            "window_end": str(win_end),
        },
        "observations_and_hypotheses": [
            {
                "figure": "eda_hourly_zones.png",
                "finding": f"Cả 3 vùng có chu kỳ ngày rõ rệt: đáy vào rạng sáng ({trough_hours}) và đỉnh buổi tối ({peak_hours}).",
                "hypothesis": "Đặc trưng trễ 24h (day_lag), 168h (week_lag) và mã hóa sin/cos giờ đích sẽ giải thích phần lớn biến thiên cơ sở.",
            },
            {
                "figure": "eda_weekday_weekend.png",
                "finding": f"Cuối tuần giảm tải trung bình {weekday_stats['zone1']['diff_pct']:.2f}% ở Zone 1 so với ngày thường.",
                "hypothesis": "Biến chu kỳ thứ trong tuần (weekday_sin/cos) và week_lag cần thiết để tránh dự báo cao quá mức vào cuối tuần.",
            },
            {
                "figure": "eda_temp_load.png",
                "finding": f"Ở cùng khung 14:00 và 20:00, phụ tải tương quan dương rõ với nhiệt độ (r={temp_corr['hour_14']:.3f} và r={temp_corr['hour_20']:.3f}).",
                "hypothesis": "Thêm biến thời tiết trễ 1h giúp giảm sai số, đặc biệt khi nhiệt độ thay đổi mạnh theo ngày/mùa.",
            },
            {
                "figure": "eda_ramp_window.png",
                "finding": f"Tại {ramp_time:%d/%m/%Y %H:%M}, tải Zone 1 tăng {ramp_val:,.1f} đơn vị chỉ trong 1 giờ.",
                "hypothesis": "Các mô hình tuyến tính/làm mịn có thể dự báo thiếu tại giờ tăng mạnh nếu thiếu đặc trưng xu hướng ngắn hạn (load_now - load_lag1h).",
            },
        ],
    }
    write_json(out_dir / "eda_summary.json", summary)
    return summary
