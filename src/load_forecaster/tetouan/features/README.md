# Vai trò B — Tạo bảng mẫu 20 đặc trưng & Chống rò rỉ dữ liệu

- **Phụ trách**: Thành viên B *(Điền họ tên & MSSV)*
- **Thư mục**: `src/load_forecaster/tetouan/features/`

## Đầu vào
- `data/tetouan/observations.parquet` từ Vai trò A.

## Đầu ra
1. `data/tetouan/samples_zone1.parquet`, `samples_zone2.parquet`, `samples_zone3.parquet`: Bảng phẳng gồm khóa `(zone, origin_time, target_time, horizon)`, 20 cột đặc trưng và nhãn `y_true`.
2. `data/tetouan/features.json`: Thứ tự chuẩn và ý nghĩa của **15 đặc trưng cơ sở (`base`)** + **5 đặc trưng thời tiết trễ 1 giờ (`weather`)**.
3. Hàm dùng chung `forecast_features(obs, origin, zone)` cho lúc huấn luyện (C) và lúc chạy Demo (E).

## Quy tắc chống rò rỉ
- Tại giờ phát hành `T`, chỉ dùng phụ tải $\le T$ và thời tiết $\le T - 1\text{ giờ}$.
- Thay đổi số liệu tải sau `T` hoặc thời tiết từ `T` trở đi **không được làm thay đổi** bất kỳ giá trị nào trong 20 cột đặc trưng.

## Lệnh chạy độc lập
```powershell
python scripts/tetouan.py samples --zone all
```
