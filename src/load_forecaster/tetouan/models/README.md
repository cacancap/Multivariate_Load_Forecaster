# Vai trò C — Huấn luyện mô hình 24 bước & Lưu/Nạp dự báo

- **Phụ trách**: Thành viên C *(Điền họ tên & MSSV)*
- **Thư mục**: `src/load_forecaster/tetouan/models/`

## Đầu vào
- Bảng mẫu `samples_{zone}.parquet` và `features.json` từ Vai trò B.
- Khoảng chia `splits.json` từ Vai trò D.

## Đầu ra
1. `predictions.parquet`: Dự báo từng hàng (validation & test) cho `ridge`, `random_forest`, `svr`, `ridge_no_weather`.
2. `selection.json` & `tuning.csv`: Tham số chọn theo validation và mô hình tốt nhất được khóa trước khi mở tập test.
3. `models/{model}-h1..h24.joblib`: Bộ 24 mô hình riêng cho từng bước dự báo, kèm `latest_train_target` chống dự báo hồi tố.
4. `training_resources.csv`: Thời gian chạy và RAM tiêu thụ của từng thuật toán.

## Lệnh chạy độc lập & Ví dụ nạp lại cho E
```powershell
python scripts/tetouan.py train --zone zone1
python scripts/tetouan.py predict --zone zone1 --origin "2017-12-01 12:00"
```
```python
from load_forecaster.tetouan.models import predict_saved
y_pred = predict_saved(run_dir, feature_rows, model="svr", zone="zone1")
```
