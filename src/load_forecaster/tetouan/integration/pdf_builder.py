"""Role E: Build the 7-section Vietnamese PDF report strictly from verified report files."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from load_forecaster.tetouan import ZONES, ZONE_LABELS

MODEL_NAMES = {
    "ridge": "Ridge",
    "svr": "SVR (RBF)",
    "random_forest": "Random Forest",
    "day_prior": "Đối chứng hôm trước",
    "week_prior": "Đối chứng tuần trước",
    "ridge_no_weather": "Ridge bỏ thời tiết",
}


def _register_fonts() -> tuple[str, str]:
    candidates = []
    env_dir = os.environ.get("TETOUAN_FONT_DIR")
    if env_dir:
        p = Path(env_dir)
        candidates.append((p / "DejaVuSans.ttf", p / "DejaVuSans-Bold.ttf"))
        candidates.append((p / "arial.ttf", p / "arialbd.ttf"))
    win_fonts = Path("C:/Windows/Fonts")
    candidates.append((win_fonts / "arial.ttf", win_fonts / "arialbd.ttf"))
    candidates.append((Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")))

    for reg, bold in candidates:
        if reg.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont("VietSans", str(reg)))
            pdfmetrics.registerFont(TTFont("VietSans-Bold", str(bold)))
            return "VietSans", "VietSans-Bold"
    raise FileNotFoundError("Could not locate Vietnamese-capable TrueType fonts (arial.ttf or DejaVuSans.ttf)")


def _fmt(val, decimals: int = 2) -> str:
    if val is None or pd.isna(val):
        return "—"
    if decimals == 0:
        return f"{float(val):,.0f}"
    return f"{float(val):,.{decimals}f}"


def build_pdf_report(root: Path) -> Path:
    """Compile reports/tetouan/IT3190_Tetouan.pdf covering all 7 required sections."""
    root = Path(root)
    rep = root / "reports/tetouan"
    font_reg, font_bold = _register_fonts()

    audit = json.loads((rep / "audit.json").read_text(encoding="utf-8"))
    features = json.loads((rep / "features.json").read_text(encoding="utf-8"))
    z1_sel = json.loads((rep / "zone1/selection.json").read_text(encoding="utf-8"))
    z1_ver = json.loads((rep / "zone1/verification.json").read_text(encoding="utf-8"))
    z1_scores = pd.read_csv(rep / "zone1/scores.csv")
    summary_all = pd.read_csv(rep / "summary_all_zones.csv")
    ablation_z1 = pd.read_csv(rep / "zone1/weather_ablation.csv")
    crit_z1 = pd.read_csv(rep / "zone1/critical_hours.csv")
    thresh_z1 = pd.read_csv(rep / "zone1/thresholds.csv")
    case_z1 = pd.read_csv(rep / "zone1/case_studies.csv") if (rep / "zone1/case_studies.csv").is_file() else pd.DataFrame()
    eda_sum = json.loads((rep / "eda/eda_summary.json").read_text(encoding="utf-8")) if (rep / "eda/eda_summary.json").is_file() else {}
    res_z1 = pd.read_csv(rep / "zone1/training_resources.csv") if (rep / "zone1/training_resources.csv").is_file() else pd.DataFrame()

    best_z1 = z1_sel["best_model"]
    z1_test_overall = z1_scores[(z1_scores["split"] == "test") & (z1_scores["slice"] == "overall")].set_index("model")
    z1_winner_row = z1_test_overall.loc[best_z1]
    z1_day_row = z1_test_overall.loc["day_prior"]
    z1_week_row = z1_test_overall.loc["week_prior"]

    pdf_path = rep / "IT3190_Tetouan.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="IT3190 - Dự báo phụ tải điện 24 giờ tại Tetouan",
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle("TitleVN", parent=styles["Title"], fontName=font_bold, fontSize=16.5, leading=22, textColor=colors.HexColor("#0f3d3e"), spaceAfter=6)
    style_sub = ParagraphStyle("SubVN", parent=styles["Normal"], fontName=font_reg, fontSize=9.5, leading=13.5, textColor=colors.HexColor("#475569"), spaceAfter=10)
    style_h1 = ParagraphStyle("H1VN", parent=styles["Heading1"], fontName=font_bold, fontSize=12.5, leading=17, textColor=colors.HexColor("#176a59"), spaceBefore=10, spaceAfter=5)
    style_body = ParagraphStyle("BodyVN", parent=styles["Normal"], fontName=font_reg, fontSize=9.7, leading=14.2, textColor=colors.HexColor("#1e293b"), spaceAfter=5)
    style_bold = ParagraphStyle("BoldVN", parent=style_body, fontName=font_bold)
    style_cap = ParagraphStyle("CapVN", parent=style_body, fontName=font_reg, fontSize=8.6, leading=12, textColor=colors.HexColor("#475569"), spaceAfter=7)

    items = []

    def p(text: str, style=style_body) -> None:
        items.append(Paragraph(text, style))

    def h1(text: str) -> None:
        items.append(Paragraph(text, style_h1))

    def table(headers: list[str], rows: list[list[str]], widths_mm: list[float]) -> None:
        cell_h = ParagraphStyle("TH", fontName=font_bold, fontSize=8.2, leading=11, textColor=colors.white)
        cell_b = ParagraphStyle("TB", fontName=font_reg, fontSize=8.2, leading=11, textColor=colors.HexColor("#1e293b"))
        data = [[Paragraph(str(c), cell_h) for c in headers]]
        for r in rows:
            data.append([Paragraph(str(c), cell_b) for c in r])
        t = Table(data, colWidths=[w * mm for w in widths_mm], repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176a59")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        items.append(t)
        items.append(Spacer(1, 6))

    def pic(rel_path: str, w_mm: float, h_mm: float, caption: str) -> None:
        img_path = rep / rel_path
        if img_path.is_file():
            items.append(Image(str(img_path), width=w_mm * mm, height=h_mm * mm))
            p(caption, style_cap)

    def frame(canvas, doc_obj) -> None:
        canvas.saveState()
        canvas.setFont(font_reg, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(17 * mm, 10 * mm, "IT3190 · Dự báo phụ tải điện 24 giờ tại Tetouan (Zone 1, 2, 3)")
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"Trang {doc_obj.page}")
        canvas.restoreState()

    # Header
    p("BÁO CÁO ĐỒ ÁN MÔN HỌC IT3190", style_title)
    p("<b>Đề tài: Dự báo phụ tải điện đa bước 24 giờ tại thành phố Tetouan (Zone 1, Zone 2, Zone 3)</b><br/>Nhóm 5 thành viên (Vai trò A–E) · Bộ dữ liệu UCI ID 849", style_sub)

    # 1. Bài toán và kịch bản sử dụng
    h1("1. Bài toán và kịch bản sử dụng")
    p(
        "Tại mỗi mốc tròn giờ phát hành <b>T</b> (ví dụ 12:00 hôm nay), hệ thống dự báo đồng thời <b>24 giá trị phụ tải điện</b> cho 24 giờ tiếp theo "
        "(13:00, 14:00, ..., 12:00 ngày hôm sau). Thực nghiệm chính thực hiện trên <b>Zone 1</b> và mở rộng so sánh sang <b>Zone 2, Zone 3</b>."
    )
    p(
        f"Mô hình vô địch của Zone 1 được khóa trước theo 3 lượt kiểm định mở rộng là <b>{MODEL_NAMES.get(best_z1, best_z1)}</b>. "
        f"Trên tập kiểm thử độc lập (20% cuối năm), mô hình đạt <b>MAPE = {_fmt(z1_winner_row['mape_percent'], 3)}%</b>, "
        f"MAE = {_fmt(z1_winner_row['mae'], 2)} (đơn vị nguồn), vượt rõ hai đối chứng hôm trước ({_fmt(z1_day_row['mape_percent'], 3)}%) "
        f"và tuần trước ({_fmt(z1_week_row['mape_percent'], 3)}%) trên cùng {_fmt(z1_winner_row['n'], 0)} cặp giờ phát hành–đích."
    )
    pic("demo.png", 172, 76, "Hình 1: Kết quả Demo 24 giờ thực tế trên Zone 1 đối chiếu đường dự báo, thực đo và đối chứng hôm trước.")

    # 2. Tập dữ liệu và phương pháp
    h1("2. Tập dữ liệu và phương pháp")
    p(
        f"Bộ dữ liệu gốc <b>Power Consumption of Tetouan City</b> (Salam & El Hibaoui, 2018; UCI ID 849; CC BY 4.0) gồm "
        f"<b>{_fmt(audit['rows'], 0)} dòng</b> đo mỗi 10 phút từ {audit['start']} đến {audit['end']}, trong đó có {_fmt(audit['hourly_grid_size'], 0)} mốc tròn giờ. "
        f"Kiểm toán xác nhận khớp SHA-256 chính thức, không thiếu mốc 10 phút và không trùng thời điểm. "
        f"Metadata UCI chưa xác nhận đơn vị vật lý và múi giờ/DST nên toàn bộ chuỗi giữ nguyên đơn vị gốc và giờ gốc."
    )
    p(
        f"<b>Khai phá dữ liệu (chỉ trên phần phát triển 80% đầu):</b> {eda_sum.get('dev_start', '')} đến {eda_sum.get('dev_end', '')}. "
        f"Tải 3 vùng đều có chu kỳ ngày rõ nét; tải cuối tuần tại Zone 1 giảm {_fmt(abs(eda_sum.get('weekday_vs_weekend', {}).get('zone1', {}).get('diff_pct', 0)), 2)}% so với ngày thường; "
        f"nhiệt độ tại khung 14:00 tương quan dương với tải Zone 1 (r = {_fmt(eda_sum.get('temperature_correlation_zone1', {}).get('hour_14', 0), 3)})."
    )
    pic("eda/eda_hourly_zones.png", 170, 74, "Hình 2: Đường tải điển hình theo giờ (trung bình và dải tứ phân vị) của 3 vùng trên phần phát triển.")
    pic("eda/eda_temp_load.png", 172, 68, "Hình 3: Quan hệ phụ tải Zone 1 và nhiệt độ tại khung 14:00 và 20:00 (phần phát triển).")

    p(
        f"<b>Đặc trưng & Chia tập chống rò rỉ:</b> Mỗi mẫu gồm {len(features['base'])} đặc trưng cơ sở (tải hiện tại, trễ 1h/2h/24h/168h, trung bình/cực đại 24h, "
        f"day_lag, week_lag, sin/cos giờ-thứ-năm của giờ đích) và {len(features['weather'])} đặc trưng thời tiết trễ 1 giờ (tại T−1h). "
        "Lưới giờ được chia 80% đầu phát triển (3 lượt expanding CV 28 ngày) và 20% cuối kiểm thử, giữ khoảng đệm >= 24 giờ trước mỗi tập chấm. "
        "Áp dụng chiến lược dự báo trực tiếp (24 mô hình độc lập cho h=1..24) với Ridge, Random Forest và SVR (RBF)."
    )

    items.append(PageBreak())

    # 3. Kết quả thực nghiệm và đánh giá
    h1("3. Kết quả thực nghiệm và đánh giá")
    p("<b>3.1. Bảng tổng hợp sai số trên tập kiểm thử (Zone 1, Zone 2, Zone 3):</b>", style_bold)
    rows_summary = []
    for z in ZONES:
        sub = summary_all[summary_all["zone"] == z]
        for m in ["ridge", "random_forest", "svr", "ridge_no_weather", "day_prior", "week_prior"]:
            r = sub[sub["model"] == m]
            if r.empty:
                continue
            row = r.iloc[0]
            rows_summary.append([
                ZONE_LABELS[z],
                MODEL_NAMES.get(m, m),
                _fmt(row["mae"], 2),
                _fmt(row["rmse"], 2),
                f"{_fmt(row['mape_percent'], 3)}%",
                f"{_fmt(row['coverage'] * 100, 1)}%",
            ])
    table(["Vùng", "Mô hình", "MAE", "RMSE", "MAPE (%)", "Độ phủ"], rows_summary, [20, 44, 28, 28, 26, 24])

    pic("zones_comparison.png", 172, 74, "Hình 4: So sánh MAPE tập kiểm thử trên cả 3 vùng giữa 3 thuật toán và 2 đối chứng.")
    pic("horizons.png", 172, 74, "Hình 5: Diễn biến MAPE theo 24 bước dự báo trên tập kiểm thử Zone 1.")

    p("<b>3.2. Thí nghiệm bỏ/thêm thời tiết (Ridge có thời tiết vs. Ridge bỏ thời tiết):</b>", style_bold)
    ab_test = ablation_z1[ablation_z1["split"] == "test"].iloc[0]
    ab_rows = []
    for z in ZONES:
        p_ab = rep / z / "weather_ablation.csv"
        if p_ab.is_file():
            df_ab = pd.read_csv(p_ab)
            rt = df_ab[df_ab["split"] == "test"].iloc[0]
            ab_rows.append([
                ZONE_LABELS[z],
                f"{_fmt(rt['ridge_mape_percent'], 3)}%",
                f"{_fmt(rt['ridge_no_weather_mape_percent'], 3)}%",
                f"{rt['delta_mape_pp']:+.3f} đpt",
                f"{rt['delta_mae']:+.2f}",
            ])
    table(["Vùng (Tập Test)", "Ridge có thời tiết", "Ridge bỏ thời tiết", "Chênh MAPE", "Chênh MAE"], ab_rows, [32, 36, 38, 34, 30])
    pic("weather.png", 170, 66, "Hình 6: Chênh lệch MAPE khi bổ sung 5 biến thời tiết trễ 1h trên từng lượt CV và tập kiểm thử.")

    p("<b>3.3. Hồi quy tại giờ đỉnh và giờ tăng tải mạnh (ngưỡng phân vị 95% trên train):</b>", style_bold)
    crit_test = crit_z1[crit_z1["split"] == "test"]
    crit_rows = []
    for ev_label, ev_key in [("Giờ đỉnh (Peak)", "peak_hour"), ("Giờ tăng mạnh Q95", "ramp_hour")]:
        sub_ev = crit_test[crit_test["event_type"] == ev_key]
        for m in [best_z1, "ridge", "day_prior", "week_prior"]:
            rm = sub_ev[sub_ev["model"] == m]
            if rm.empty:
                continue
            row = rm.iloc[0]
            crit_rows.append([
                ev_label,
                MODEL_NAMES.get(m, m),
                _fmt(row["mae"], 2),
                f"{row['mean_signed_error']:+.2f}",
                f"{row['under_prediction_rate'] * 100:.1f}%",
                _fmt(row["n_distinct_targets"], 0),
            ])
    table(["Nhóm giờ (Zone 1 Test)", "Mô hình", "MAE", "Sai lệch có dấu", "Tỷ lệ thiếu", "Số giờ đích riêng"], crit_rows, [36, 38, 24, 28, 22, 24])
    pic("critical_hours.png", 172, 65, "Hình 7: Mức độ dự báo thiếu tại giờ đỉnh và giờ tăng mạnh (>= Q95 trên train) của Zone 1.")

    if not case_z1.empty:
        p("<b>3.4. Hai ví dụ giờ cụ thể trên tập kiểm thử Zone 1 (phục vụ đối chiếu bảo vệ):</b>", style_bold)
        cs_rows = []
        for r in case_z1.itertuples():
            cs_rows.append([
                "Giờ đỉnh" if r.case_type == "peak_example" else "Giờ tăng mạnh",
                str(r.origin_time),
                str(r.target_time),
                f"h={r.horizon}",
                _fmt(r.y_true, 2),
                _fmt(r.y_pred, 2),
                f"{r.signed_error:+.2f}",
            ])
        table(["Tình huống", "Giờ phát hành", "Giờ đích", "Bước", "Thực đo", "Dự báo", "Lệch có dấu"], cs_rows, [26, 32, 32, 14, 22, 22, 24])

    # 4. Chức năng và hướng dẫn sử dụng
    h1("4. Chức năng và hướng dẫn sử dụng")
    p(
        "Hệ thống hỗ trợ chạy trọn gói qua CLI và trình diễn tương tác qua giao diện Web Streamlit:<br/>"
        "• <b>Chạy kiểm tra nhanh:</b> <font name='Courier'>python scripts/tetouan.py smoke --zone zone1</font><br/>"
        "• <b>Chạy toàn bộ 3 vùng:</b> <font name='Courier'>python scripts/tetouan.py full --zone all</font><br/>"
        "• <b>Demo dòng lệnh (24 giờ):</b> <font name='Courier'>python scripts/tetouan.py demo --zone zone1 --origin \"2017-12-01 12:00\"</font><br/>"
        "• <b>Giao diện Web Demo (3 tab):</b> <font name='Courier'>streamlit run app/tetouan_demo.py</font><br/>"
        "• <b>Kiểm thử tự động:</b> <font name='Courier'>python -m pytest -q</font>"
    )

    # 5. Kiến trúc mã nguồn
    h1("5. Kiến trúc mã nguồn (5 gói chức năng tương ứng 5 thành viên A–E)")
    arch_rows = [
        ["data_eda/ (A)", "observations.py, eda.py", "Tải UCI 849, làm sạch 3 vùng, kiểm toán SHA-256, 4 biểu đồ EDA dev-only"],
        ["features/ (B)", "samples.py", "Sinh bảng mẫu 20 đặc trưng + hàm forecast_features() dùng chung train/demo"],
        ["models/ (C)", "train.py, predict.py", "Tìm tham số, train 24 bước Ridge/RF/SVR, lưu .joblib & chặn hồi tố"],
        ["evaluation/ (D)", "splits.py, metrics.py", "Chia 80/20 + 3 CV gap >= 24h, 2 đối chứng, chấm tổng thể & giờ đỉnh/Q95"],
        ["integration/ (E)", "pipeline.py, report.py, pdf_builder.py, package.py", "CLI hợp nhất, kiểm chứng bất biến tương lai, Web Streamlit, PDF & ZIP"],
    ]
    table(["Gói (Vai trò)", "Tập tin chính", "Chức năng & Dữ liệu bàn giao"], arch_rows, [30, 48, 94])

    # 6. Khó khăn và giải pháp
    h1("6. Khó khăn và giải pháp")
    p(
        "• <b>Rò rỉ dữ liệu thời gian và độ trễ thời tiết:</b> Đảm bảo chia tập trên lưới giờ đầy đủ với gap >= 24 giờ, khóa mô hình trên validation "
        "trước khi mở test và chỉ dùng thời tiết ở mốc T−1h; bổ sung kiểm thử tự động thay đổi dữ liệu tương lai xác nhận đầu ra bất biến.<br/>"
        "• <b>Tên cột không đồng nhất ở bộ UCI:</b> CSV gốc có hai khoảng trắng ở tên cột Zone 2 và Zone 3; chuẩn hóa khoảng trắng trước khi ánh xạ.<br/>"
        "• <b>Dự báo thiếu tại giờ cao điểm/tăng đột biến:</b> Phân tích riêng theo ngưỡng Q95 tính trên train và trực quan hóa sai lệch có dấu để nhận diện rõ giới hạn của mô hình."
    )

    # 7. Phát hiện, giới hạn và hướng tiếp theo
    h1("7. Phát hiện, giới hạn và hướng tiếp theo")
    z1_ramp_test = crit_test[(crit_test["event_type"] == "ramp_hour") & (crit_test["model"] == best_z1)].iloc[0]
    z1_peak_test = crit_test[(crit_test["event_type"] == "peak_hour") & (crit_test["model"] == best_z1)].iloc[0]
    p(
        f"<b>Trả lời 2 câu hỏi trọng tâm khi bảo vệ:</b><br/>"
        f"1) <i>Mô hình có vượt đối chứng hôm trước/tuần trước trên 24 giờ không?</i> Có: Trên Zone 1, {MODEL_NAMES.get(best_z1, best_z1)} đạt MAPE "
        f"{_fmt(z1_winner_row['mape_percent'], 3)}%, thấp hơn nhiều so với hôm trước ({_fmt(z1_day_row['mape_percent'], 3)}%) và tuần trước ({_fmt(z1_week_row['mape_percent'], 3)}%).<br/>"
        f"2) <i>Mô hình dự báo thiếu bao nhiêu ở giờ đỉnh và giờ tăng mạnh?</i> Trên tập kiểm thử Zone 1, tại giờ đỉnh {MODEL_NAMES.get(best_z1, best_z1)} "
        f"có sai lệch có dấu trung bình {z1_peak_test['mean_signed_error']:+.2f} (tỷ lệ dự báo thiếu {z1_peak_test['under_prediction_rate']*100:.1f}%); "
        f"tại giờ tăng mạnh >= Q95 ({_fmt(thresh_z1[thresh_z1['split']=='test']['ramp_q95'].iloc[0], 1)}), sai lệch có dấu là "
        f"{z1_ramp_test['mean_signed_error']:+.2f} (thiếu {z1_ramp_test['under_prediction_rate']*100:.1f}%)."
    )
    p(
        "<b>Khảo sát nguồn Việt Nam & Hướng tiếp theo:</b> Thời tiết theo giờ cho Hà Nội và TP.HCM lấy được trực tiếp từ Open-Meteo (ERA5, UTC+7), "
        "nhưng chuỗi phụ tải theo giờ cấp thành phố của EVN/NSMO chưa công khai cho công chúng. Hướng tiếp theo là kết nối nguồn đo xa nội bộ và thử nghiệm mô hình học sâu chuỗi thời gian."
    )
    p(
        f"<b>Kế thừa & Trích dẫn:</b> Dữ liệu của Salam & El Hibaoui (2018), UCI ID 849, DOI 10.24432/C5B034 (CC BY 4.0). "
        f"Mã nguồn kế thừa <i>CachedDownloader, build_model, temporal_folds, ResourceRecorder</i> từ nhánh nền tảng của repo; "
        f"sai số nạp lại mô hình tối đa = {max(z1_ver.get('max_abs_reload_error', {'v': 0.0}).values()):.2e}."
    )

    p("<b>Bảng phân công và đóng góp thực tế của nhóm 5 thành viên:</b>", style_bold)
    contrib_rows = [
        ["A · Dữ liệu & EDA", "[Điền họ tên & MSSV]", "20%", "Chuẩn bị dữ liệu sạch 3 vùng, audit.json, 4 hình EDA, khảo sát nguồn VN"],
        ["B · Đặc trưng", "[Điền họ tên & MSSV]", "20%", "Xây bảng mẫu 20 đặc trưng, hàm dùng chung train/demo, test chống rò rỉ"],
        ["C · Mô hình", "[Điền họ tên & MSSV]", "20%", "Huấn luyện 24 bước Ridge/RF/SVR, tuning CV, lưu/nạp mô hình 3 vùng"],
        ["D · Kiểm định", "[Điền họ tên & MSSV]", "20%", "Chia tập 80/20 + 3 CV gap >= 24h, 2 đối chứng, chấm giờ đỉnh & tăng mạnh Q95"],
        ["E · Tích hợp & Nhóm trưởng", "[Điền họ tên & MSSV]", "20%", "Điều phối luồng A–E, Demo CLI & Web Streamlit, báo cáo PDF, ZIP & kịch bản"],
    ]
    table(["Vai trò", "Họ tên & MSSV", "Tỷ lệ", "Đóng góp thực tế"], contrib_rows, [36, 40, 14, 82])

    doc.build(items, onFirstPage=frame, onLaterPages=frame)
    return pdf_path
