"""Export portable Tetouan research tables, figures and a PDF from a completed run."""
import argparse
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/tetouan"
COLORS = {"ridge":"#b45309","svr":"#176a59","random_forest":"#275ba4","day_prior":"#777982","week_prior":"#974e85"}
NAMES = {"ridge":"Ridge","svr":"SVR RBF","random_forest":"Random Forest","day_prior":"Ngày trước","week_prior":"Tuần trước","ridge_no_weather":"Ridge bỏ thời tiết"}


def plot_demo(out,table,obs):
    fig, ax = plt.subplots(figsize=(8,3.6),layout="constrained")
    t = pd.DatetimeIndex(table.target_time)
    ax.plot(table.horizon, table.y_pred, label=NAMES[table.model.iloc[0]], color="#126553",lw=2.4)
    ax.plot(table.horizon, obs.load.reindex(t), label="Thực đo sau phát hành",color="#303b50",ls="--")
    ax.set(xlabel="Số giờ sau khi phát hành",ylabel="Phụ tải Zone 1 (đơn vị gốc)",
           title=f"Dự báo phát hành lúc {table.origin_time.iloc[0]:%H:%M ngày %d/%m/%Y}")
    ax.grid(axis="y",alpha=.2)
    ax.legend(frameon=False)
    fig.savefig(out/"demo.png",dpi=160)
    plt.close(fig)
    print(out/"demo.png")


def export():
    ref = ROOT/"outputs/tetouan/full"
    run = ref/(ref/"latest.txt").read_text().strip()
    REPORT.mkdir(parents=True,exist_ok=True)
    for file in ["scores.csv","coverage.csv","confusion.csv","thresholds.csv","weather_ablation.csv",
                 "training_resources.csv","selection.json","splits.json","run_resources.json",
                 "verification.json","predictions.parquet","all_predictions.parquet","peak_windows.csv",
                 "inference_resources.json","demo.png","forecast.csv"]:
        shutil.copy2(run/file, REPORT/file)
    if (run/"tuning.csv").is_file():
        shutil.copy2(run/"tuning.csv",REPORT/"tuning.csv")
    for file in ["features.json","audit.json","prepare_resources.json"]:
        shutil.copy2(ROOT/"data/tetouan"/file,REPORT/file)
    scores=pd.read_csv(REPORT/"scores.csv").query("split == 'test' and slice == 'horizon'")
    fig,ax=plt.subplots(figsize=(8.6,3.65),layout="constrained")
    for model,color in COLORS.items():
        s=scores[scores.model==model].sort_values("horizon")
        ax.plot(s.horizon,s.mape_percent,label=NAMES[model],color=color,
                ls="--" if model.endswith("prior") else "-",lw=1.8)
    ax.set(xlabel="Bước dự báo (giờ)",ylabel="MAPE (%)",title="Sai số trên tập kiểm thử theo khoảng cách dự báo")
    ax.set_xticks([1,4,8,12,16,20,24])
    ax.grid(axis="y",alpha=.25)
    ax.legend(ncols=3,fontsize=8,frameon=False)
    fig.savefig(REPORT/"horizons.png",dpi=180)
    plt.close(fig)
    val=pd.read_csv(REPORT/"weather_ablation.csv").query("slice == 'overall'")
    fig,ax=plt.subplots(figsize=(8.6,2.75),layout="constrained")
    tags=[f"Kiểm định {v.fold}" if v.split=="validation" else "Kiểm thử cuối" for v in val.itertuples()]
    ax.barh(tags,val.delta_mape_pp,color=["#176a59" if d<0 else "#b45309" for d in val.delta_mape_pp])
    ax.axvline(0,color="#444",lw=1)
    ax.set_xlabel("Chênh MAPE (có − bỏ thời tiết), điểm phần trăm")
    fig.savefig(REPORT/"weather.png",dpi=160)
    plt.close(fig)
    print(REPORT)


if __name__=="__main__":
    export()
