"""Read-only viewer for completed, validated experiment artifacts."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Dự báo phụ tải điện", layout="wide")
st.title("Dự báo phụ tải điện 24 giờ")
completed = sorted((ROOT / "outputs").glob("*/COMPLETE.json"))
if not completed:
    st.info("Chưa có thực nghiệm hoàn tất. Chạy pipeline trước để xem kết quả đã xác minh.")
    st.stop()
names = [p.parent.name for p in completed]
default = next((i for i, name in enumerate(names) if name.startswith("full-")), 0)
selected = st.selectbox("Thực nghiệm", names, index=default)
run = ROOT / "outputs" / selected
config = json.loads((run / "config.json").read_text(encoding="utf-8"))
quality = json.loads((run / "data_quality.json").read_text(encoding="utf-8"))
if selected.startswith("smoke-"):
    st.warning("Đây là lần chạy thử nhỏ, không phải kết quả đánh giá toàn năm.")
if "oracle" in selected:
    st.warning("Nhánh này giả định biết trước thời tiết tương lai; không thể coi là độ chính xác vận hành.")
if not quality["weather_join_allowed"]:
    st.info("Chưa xác nhận quy ước timestamp PJME. Đã cách ly các cửa sổ đi qua ngày DST và chưa ghép thời tiết.")
score = pd.read_csv(run / "metrics.csv")
delay = st.radio("Độ chậm dữ liệu phụ tải (giờ)", [0, 1], horizontal=True)
st.caption(f"Khoảng kiểm thử: {config['development_end']} đến trước {config['test_end']}. Mọi mô hình dùng cùng tập thời điểm đánh giá.")
overall = score[(score["slice"] == "overall") & (score.delay_hours == delay)].sort_values("mape_percent")
st.dataframe(overall[["model", "mape_percent", "mae_mw", "rmse_mw", "peak_mape_percent", "n"]], hide_index=True, width="stretch")
curves = score[(score.delay_hours == delay) & score["slice"].str.startswith("horizon_")].copy()
curves["horizon"] = curves["slice"].str.removeprefix("horizon_").astype(int)
st.subheader("Sai số theo khoảng cách dự báo")
st.line_chart(curves.pivot(index="horizon", columns="model", values="mape_percent"), x_label="Giờ", y_label="MAPE (%)")
coverage = pd.DataFrame(json.loads((run / "coverage.json").read_text())["per_horizon"])
st.subheader("Độ phủ sau kiểm tra chất lượng")
st.dataframe(coverage[coverage.delay_hours == delay], hide_index=True, width="stretch")


@st.cache_data
def read_predictions(path, model, delay):
    return pd.read_parquet(path, filters=[("model", "=", model), ("delay_hours", "=", delay)])


choices = json.loads((run / "selected_models.json").read_text())
best = min(choices, key=lambda row: row["all_horizon_cv_mape_percent"])
ensemble = json.loads((run / "ensemble_selection.json").read_text())
recommended = best["model"]
if ensemble and ensemble["mape_percent"] < best["all_horizon_cv_mape_percent"] - 0.1:
    recommended = "weighted_ensemble"
options = sorted(overall.model.unique())
model = st.selectbox("Mô hình để xem dự báo", options, index=options.index(recommended))
model_data = read_predictions(str(run / "test_predictions.parquet"), model, delay)
counts = model_data.groupby("origin_time").horizon.nunique()
available = sorted(counts[counts == len(config["horizons"])].index)
if not available:
    st.info("Không có cửa sổ đủ toàn bộ giờ dự báo trong bộ kết quả này.")
    st.stop()
origin = st.select_slider("Thời điểm phát hành", available, value=available[len(available) // 2], format_func=str)
window = model_data[model_data.origin_time == origin].sort_values("horizon")
st.line_chart(window.set_index("target_time")[["load_mw", "prediction_mw"]], x_label="Giờ đích", y_label="MW")
peaks = pd.read_csv(run / f"peak_summary_delay{delay}.csv")
st.subheader("Sai số đỉnh trong cửa sổ dự báo")
st.dataframe(peaks, hide_index=True, width="stretch")
st.download_button("Tải bảng chỉ số", (run / "metrics.csv").read_bytes(), file_name="metrics.csv", mime="text/csv")
with st.expander("Giới hạn và báo cáo đầy đủ"):
    st.markdown((run / "REPORT.md").read_text(encoding="utf-8"))
