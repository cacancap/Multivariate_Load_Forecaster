# Vai trò A — Dữ liệu 3 vùng, Kiểm toán & Khai phá (EDA)

- **Phụ trách**: Thành viên A *(Điền họ tên & MSSV)*
- **Thư mục**: `src/load_forecaster/tetouan/data_eda/`

## Đầu vào
- Bộ dữ liệu gốc **Power Consumption of Tetouan City** (UCI ID 849, DOI `10.24432/C5B034`, giấy phép CC BY 4.0) tải về `data/tetouan/raw/uci849.zip`.

## Đầu ra
1. `data/tetouan/observations.parquet`: Bảng quan sát sạch theo mốc 10 phút gồm 3 cột tải (`zone1`, `zone2`, `zone3`) và 5 cột thời tiết.
2. `data/tetouan/valid_hours.parquet`: Danh sách mốc tròn giờ hợp lệ bàn giao cho D.
3. `data/tetouan/audit.json` & `data/tetouan/column_dictionary.json`: Kiểm toán SHA-256, thống kê thiếu/trùng/bất thường, ví dụ tra ngược dòng CSV gốc, từ điển cột.
4. `reports/tetouan/eda/`: 4 biểu đồ EDA trên **phần phát triển (80% đầu)** và `eda_summary.json`.
5. `docs/KHAO_SAT_NGUON_VIET_NAM.md`: Bảng khảo sát nguồn phụ tải & thời tiết Hà Nội, TP.HCM.

## Lệnh chạy độc lập
```powershell
python scripts/tetouan.py observations
python scripts/tetouan.py eda
```
