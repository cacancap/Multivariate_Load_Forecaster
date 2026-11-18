"""Development-only EDA; never reads holdout load values for plots/statistics."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from load_forecaster.experiment import boundary


def main():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/experiment.yaml").read_text(encoding="utf-8"))
    load = pd.read_parquet(root / "data/processed/load.parquet")
    start = boundary(config["train_start"], load.index)
    end = boundary(config["development_end"], load.index)
    dev = load.loc[(load.index >= start) & (load.index < end)].copy()
    observed = dev.load_observed
    local = dev.index.tz_convert(config["timezone"]).tz_localize(None) if dev.index.tz is not None else dev.index
    table = pd.DataFrame({"load_mw": observed.to_numpy(), "hour": local.hour, "weekday": local.dayofweek, "month": local.strftime("%Y-%m")}, index=dev.index)
    summary = table.groupby("month").load_mw.agg(["count", "mean", "min", "max"])
    summary["missing_observed_hours"] = observed.isna().groupby(local.strftime("%Y-%m")).sum()
    correlations = {lag: float(observed.corr(observed.shift(lag))) for lag in (1, 2, 24, 48, 168, 336)}
    out = root / "outputs/exploration"
    out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "development_monthly.csv")
    heatmap = table.pivot_table(index="weekday", columns="hour", values="load_mw", aggfunc="mean")
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    observed.resample("D").mean().plot(ax=axes[0], linewidth=0.7)
    axes[0].set(title="Development 2014-2016: mean daily load (original safe observations)", ylabel="MW", xlabel="Native PJME time labels")
    im = axes[1].imshow(heatmap.to_numpy(), aspect="auto", origin="upper", cmap="viridis")
    axes[1].set(yticks=range(7), yticklabels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], xticks=range(0, 24, 2), xlabel="Hour label", title="Mean load by weekday and hour")
    fig.colorbar(im, ax=axes[1], label="MW")
    fig.tight_layout()
    fig.savefig(out / "development_patterns.png", dpi=150)
    plt.close(fig)
    lines = ["# Khảo sát dữ liệu phát triển 2014–2016", "",
             "Chỉ dùng dữ liệu trước holdout 2017 để khảo sát mùa vụ. Không ghép thời tiết khi chưa xác nhận timestamp.", "",
             f"Số giờ lịch: {len(dev):,}; phụ tải quan sát còn lại: {int(observed.notna().sum()):,}; thiếu/cách ly: {int(observed.isna().sum()):,}.",
             f"Phụ tải quan sát: min {observed.min():,.0f}, trung vị {observed.median():,.0f}, max {observed.max():,.0f} MW.", "",
             "## Tương quan với phụ tải quá khứ", "", "| Độ lùi (giờ) | Tương quan Pearson |", "|---:|---:|"]
    lines += [f"| {lag} | {value:.4f} |" for lag, value in correlations.items()]
    lines += ["", "Tương quan được tính trên cặp quan sát hợp lệ ở lưới giờ, không dồn hàng sau khi bỏ giờ thiếu. Đây là mô tả dữ liệu, không phải chỉ số dự báo ngoài mẫu.", "", "![Mùa vụ dữ liệu phát triển](development_patterns.png)", "", "Chi tiết từng tháng: development_monthly.csv. Các khoảng trống quanh DST được giữ nguyên, không dùng đường nối đồ thị để nội suy dữ liệu huấn luyện."]
    (out / "EDA_DEVELOPMENT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Development EDA saved: {out}")


if __name__ == "__main__":
    main()
