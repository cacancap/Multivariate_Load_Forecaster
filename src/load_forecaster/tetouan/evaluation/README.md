# Vai trò D — Chia tập, Đối chứng & Đánh giá Giờ quan trọng

- **Phụ trách**: Thành viên D *(Điền họ tên & MSSV)*
- **Thư mục**: `src/load_forecaster/tetouan/evaluation/`

## Đầu vào
- Lưới giờ phát hành từ `samples_{zone}.parquet` (để chia tập).
- Bảng dự báo từng hàng `predictions.parquet` từ Vai trò C.

## Đầu ra
1. `data/tetouan/splits.json`: Chia **80% đầu phát triển** (3 lượt expanding CV mỗi lượt 28 ngày) / **20% cuối kiểm thử**, giữ khoảng đệm $\ge$ 24 giờ.
2. `scores.csv`: Chấm MAE, RMSE, MAPE, độ phủ, sai lệch có dấu, tỷ lệ dự báo thiếu trên **cùng tập cửa sổ đủ 24 giờ** cho các mô hình và 2 đối chứng (`day_prior`, `week_prior`).
3. `weather_ablation.csv`: So sánh trực tiếp `ridge` có thời tiết vs. `ridge_no_weather`.
4. `critical_hours.csv` & `thresholds.csv`: Đánh giá hồi quy tại **giờ đỉnh** (hòa lấy giờ sớm nhất) và **giờ tăng mạnh** (phân vị 95% mức tăng dương tính trên tập train của từng vùng), kèm số giờ đích phân biệt.
5. `case_studies.csv`: 2 ví dụ giờ cụ thể trên tập test phục vụ trình bày bảo vệ.

## Lệnh chạy độc lập
```powershell
python scripts/tetouan.py split
python scripts/tetouan.py score --zone zone1
```
