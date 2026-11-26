"""Role E: Interactive 3-tab Streamlit Demo for Tetouan 24-hour Load Forecasting."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from load_forecaster.tetouan import ZONES, ZONE_LABELS
from load_forecaster.tetouan.features import forecast_features
from load_forecaster.tetouan.models import predict_saved

MODEL_LABELS = {
    "ridge": "Ridge",
    "random_forest": "Random Forest",
    "svr": "SVR (RBF)",
    "ridge_no_weather": "Ridge (bỏ thời tiết)",
}


def _latest_run(zone: str) -> Path | None:
    base = ROOT / "outputs/tetouan" / zone / "full"
    latest = base / "latest.txt"
    if not latest.is_file():
        return None
    d = base / latest.read_text(encoding="utf-8").strip()
    return d if d.is_dir() else None


@st.cache_data
def _load_observations() -> pd.DataFrame:
    return pd.read_parquet(ROOT / "data/tetouan/observations.parquet")


def main() -> None:
    st.set_page_config(
        page_title="IT3190 · Dự báo phụ tải Tetouan 24 giờ",
        layout="wide",
    )
    st.title("Dự báo phụ tải điện 24 giờ — Thành phố Tetouan (Zone 1, 2, 3)")
    st.caption("Mô hình học máy trực tiếp 24 bước (Ridge, Random Forest, SVR) · Thời tiết trễ 1 giờ · Tập kiểm thử độc lập")

    obs_path = ROOT / "data/tetouan/observations.parquet"
    if not obs_path.is_file():
        st.error("Chưa tìm thấy dữ liệu. Hãy chạy: `python scripts/tetouan.py prepare` trước.")
        return

    obs = _load_observations()
    avail_zones = [z for z in ZONES if _latest_run(z) is not None]
    if not avail_zones:
        st.warning("Chưa có kết quả huấn luyện `full`. Hãy chạy `python scripts/tetouan.py full --zone all`.")
        return

    with st.sidebar:
        st.header("Cấu hình Live Demo")
        zone = st.selectbox("Chọn vùng dự báo", avail_zones, format_func=lambda z: ZONE_LABELS[z])
        run_dir = _latest_run(zone)
        selection = json.loads((run_dir / "selection.json").read_text(encoding="utf-8"))
        splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
        best_model = selection["best_model"]
        models_avail = ["ridge", "random_forest", "svr", "ridge_no_weather"]
        model = st.selectbox(
            "Chọn mô hình",
            models_avail,
            index=models_avail.index(best_model) if best_model in models_avail else 0,
            format_func=lambda m: f"{MODEL_LABELS.get(m, m)} {'(Khóa theo CV)' if m == best_model else ''}",
        )

        test_start = pd.Timestamp(splits["test"]["eval_start"])
        test_end = pd.Timestamp(splits["test"]["eval_end"]) - pd.Timedelta(hours=24)
        valid_dates = pd.date_range(test_start.normalize(), test_end.normalize(), freq="D").date
        default_date = pd.Timestamp("2017-12-01").date()
        date_idx = list(valid_dates).index(default_date) if default_date in valid_dates else len(valid_dates) // 2
        chosen_date = st.date_input("Ngày phát hành (tập Test)", value=valid_dates[date_idx], min_value=valid_dates[0], max_value=valid_dates[-1])
        chosen_hour = st.slider("Giờ phát hành (T)", min_value=0, max_value=23, value=12)
        origin = pd.Timestamp(chosen_date) + pd.Timedelta(hours=int(chosen_hour))
        origin = min(max(origin, test_start), test_end)
        st.info(f"Giờ phát hành hợp lệ: **{origin:%d/%m/%Y %H:%M}**\n\nThời tiết mới nhất được phép dùng: **{(origin - pd.Timedelta(hours=1)):%H:%M}**")

    tab1, tab2, tab3 = st.tabs([
        "1. Live Demo 24 giờ",
        "2. Kết quả 3 vùng & Giờ quan trọng",
        "3. Khám phá dữ liệu (EDA) & Nguồn Việt Nam",
    ])

    with tab1:
        feat = forecast_features(obs, origin, zone=zone).sort_values("horizon")
        y_pred = predict_saved(run_dir, feat, model=model, zone=zone)
        targets = pd.DatetimeIndex(feat["target_time"])
        y_true = obs[zone].reindex(targets).to_numpy()
        day_prior = obs[zone].reindex(targets - pd.Timedelta(hours=24)).to_numpy()
        week_prior = obs[zone].reindex(targets - pd.Timedelta(hours=168)).to_numpy()

        df_view = pd.DataFrame({
            "Bước (h)": feat["horizon"],
            "Giờ đích": targets.strftime("%d/%m %H:%M"),
            "Dự báo": np.round(y_pred, 2),
            "Thực đo": np.round(y_true, 2),
            "Hôm trước": np.round(day_prior, 2),
            "Tuần trước": np.round(week_prior, 2),
            "Sai số tuyệt đối": np.round(np.abs(y_pred - y_true), 2),
        })

        valid_mask = np.isfinite(y_true)
        if valid_mask.any():
            mae = float(np.mean(np.abs(y_pred[valid_mask] - y_true[valid_mask])))
            mape = float(np.mean(np.abs((y_pred[valid_mask] - y_true[valid_mask]) / y_true[valid_mask])) * 100)
            peak_idx = int(np.argmax(y_true))
            peak_err = float(y_pred[peak_idx] - y_true[peak_idx])
            day_mape = float(np.mean(np.abs((day_prior[valid_mask] - y_true[valid_mask]) / y_true[valid_mask])) * 100)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("MAE cửa sổ 24h", f"{mae:,.1f}")
            c2.metric("MAPE cửa sổ 24h", f"{mape:.2f}%", delta=f"{mape - day_mape:+.2f}% vs hôm trước", delta_color="inverse")
            c3.metric("Sai lệch tại giờ đỉnh thực", f"{peak_err:+,.1f}", help=f"Đỉnh thực tại h={int(feat['horizon'].iloc[peak_idx])}")
            c4.metric("Mô hình đang chạy", MODEL_LABELS.get(model, model))

        chart_df = pd.DataFrame({
            "Dự báo": y_pred,
            "Thực đo": y_true,
            "Đối chứng hôm trước": day_prior,
        }, index=feat["horizon"])
        st.line_chart(chart_df)
        st.dataframe(df_view, use_container_width=True, hide_index=True)

    with tab2:
        rep = ROOT / "reports/tetouan"
        if (rep / "summary_all_zones.csv").is_file():
            st.subheader("Bảng tổng hợp tập kiểm thử (3 vùng)")
            st.dataframe(pd.read_csv(rep / "summary_all_zones.csv"), use_container_width=True, hide_index=True)

        col_a, col_b = st.columns(2)
        if (rep / "zones_comparison.png").is_file():
            col_a.image(str(rep / "zones_comparison.png"), caption="So sánh MAPE tập kiểm thử 3 vùng")
        if (rep / "horizons.png").is_file():
            col_b.image(str(rep / "horizons.png"), caption="MAPE theo từng bước dự báo 1..24 (Zone 1)")

        col_c, col_d = st.columns(2)
        if (rep / "weather.png").is_file():
            col_c.image(str(rep / "weather.png"), caption="Thí nghiệm thêm vs bỏ thời tiết")
        if (rep / "critical_hours.png").is_file():
            col_d.image(str(rep / "critical_hours.png"), caption="Sai lệch tại giờ đỉnh & giờ tăng mạnh Q95")

        crit_path = run_dir / "critical_hours.csv"
        if crit_path.is_file():
            st.subheader(f"Chi tiết giờ đỉnh & giờ tăng mạnh >= Q95 ({ZONE_LABELS[zone]} - Tập Test)")
            crit_df = pd.read_csv(crit_path)
            st.dataframe(crit_df[crit_df["split"] == "test"], use_container_width=True, hide_index=True)

    with tab3:
        eda_dir = ROOT / "reports/tetouan/eda"
        if eda_dir.is_dir():
            st.subheader("4 biểu đồ khai phá dữ liệu (chỉ dùng phần phát triển 80% đầu)")
            e1, e2 = st.columns(2)
            for col, fname, cap in [
                (e1, "eda_hourly_zones.png", "Đường tải theo giờ của 3 vùng"),
                (e2, "eda_weekday_weekend.png", "Ngày thường vs Cuối tuần"),
            ]:
                if (eda_dir / fname).is_file():
                    col.image(str(eda_dir / fname), caption=cap)
            e3, e4 = st.columns(2)
            for col, fname, cap in [
                (e3, "eda_temp_load.png", "Phụ tải theo nhiệt độ"),
                (e4, "eda_ramp_window.png", "Cửa sổ 24h tăng tải mạnh nhất"),
            ]:
                if (eda_dir / fname).is_file():
                    col.image(str(eda_dir / fname), caption=cap)

        vn_doc = ROOT / "docs/KHAO_SAT_NGUON_VIET_NAM.md"
        if vn_doc.is_file():
            st.markdown(vn_doc.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
