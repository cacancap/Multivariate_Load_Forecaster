# Vai trò E — Tích hợp, Demo CLI & Web, Báo cáo PDF & Đóng gói

- **Phụ trách**: Thành viên E *(Điền họ tên & MSSV)*
- **Thư mục**: `src/load_forecaster/tetouan/integration/`

## Đầu vào
- Dữ liệu & EDA từ A (`observations.parquet`, `eda/`).
- Hàm tạo đặc trưng từ B (`forecast_features()`).
- Mô hình đã lưu từ C (`models/*.joblib`, `selection.json`).
- Quy tắc chia & bảng điểm từ D (`splits.json`, `scores.csv`, `weather_ablation.csv`, `critical_hours.csv`).

## Đầu ra
1. `scripts/tetouan.py`: CLI hợp nhất chạy toàn bộ luồng A → B → D → C → E.
2. `app/tetouan_demo.py`: Giao diện Web Streamlit 3 tab cho buổi bảo vệ 15 phút.
3. `reports/tetouan/`: Toàn bộ bảng điểm 3 vùng, 5 biểu đồ tổng hợp và báo cáo `IT3190_Tetouan.pdf` đủ 7 mục.
4. `submission/IT3190_Tetouan.zip`: Gói nộp bài tái lập được kèm `readme.txt` và kịch bản bảo vệ.

## Lệnh chạy độc lập
```powershell
python scripts/tetouan.py smoke --zone zone1
python scripts/tetouan.py full --zone all
python scripts/tetouan.py report
python scripts/tetouan.py pdf
python scripts/tetouan.py package
streamlit run app/tetouan_demo.py
```
