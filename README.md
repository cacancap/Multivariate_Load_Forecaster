# Dự báo phụ tải điện 24 giờ

## Bắt đầu dành cho nhóm 5 người

1. Đọc kịch bản dự báo lúc 12:00, sơ đồ quy trình và lịch ba tuần. [Kế hoạch nhóm](docs/KE_HOACH_NHOM_5_NGUOI.md)
2. Tìm vai trò của mình, việc đầu tiên và người cần trao đổi khi vướng. [Phiếu giao việc A–E](docs/PHIEU_GIAO_VIEC.md)
3. Dùng bảng bàn giao và ví dụ mô phỏng để thử các phần song song. [Hợp đồng bàn giao](docs/HOP_DONG_BAN_GIAO.md)

Link tải PJME, nguồn thời tiết quan sát NOAA và bộ dự phòng Tetouan, kèm tình trạng dữ liệu đã lưu. [Danh mục nguồn dữ liệu](docs/NGUON_DU_LIEU.md)

## Pipeline tham khảo hiện có

Pipeline nghiên cứu Python/scikit-learn: thu thập có lưu vết → kiểm toán thời gian → đặc trưng nhân quả → mô hình trực tiếp từng horizon → kiểm định theo thời gian → chọn cấu hình → kiểm thử độc lập và báo cáo.

Kết quả đã chạy trên dữ liệu thật: [báo cáo bàn giao](reports/final/REPORT.md). Ensemble 70% SVR + 30% Ridge (cửa sổ 365 ngày) được chọn bằng validation trước khi kiểm thử: MAPE năm 2017 là **4,315%**, đối chứng ngày trước **7,007%**; độ trễ dữ liệu một giờ cho MAPE **4,529%**. Chưa đạt mục tiêu 3,5%. Đây là đánh giá trên các cửa sổ an toàn với độ phủ khoảng 94,8–95,6%, chưa xác nhận đầy đủ quy ước timestamp và chưa huấn luyện nhánh thời tiết.

## Chạy từ thư mục dự án

```powershell
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
python -m pytest -q
python scripts/run_pipeline.py prepare --weather
python scripts/explore_data.py
python scripts/run_pipeline.py run --profile smoke
python scripts/run_pipeline.py run --profile full
```

`smoke` chỉ kiểm thử đường chạy với bốn horizon, hai mô hình và tháng 1/2017; không thay thế thực nghiệm `full`. `full` gồm 24 horizon, năm folds 60 ngày, tìm tham số trên horizon 1/6/12/24, ablation, đối chứng, RF/Ridge cửa sổ 365 ngày, ensemble và độ trễ dữ liệu 0/1 giờ. Giới hạn bốn luồng. Có thể mất nhiều phút hoặc lâu hơn tùy máy; không cam kết trước RAM, thời gian hay MAPE.

Kết quả trong `outputs/<profile>-<branch>-<config-hash>/`: `REPORT.md`, `metrics.csv`, `test_predictions.parquet`, `coverage.json`, `resources.json`, bảng chọn tham số, ablation, sai số đỉnh, mô hình lưu và biểu đồ. Các lần tải được lưu trong `data/raw/` cùng manifest SHA-256. Không sửa dữ liệu gốc.

## Quy ước thời gian và thời tiết

Mặc định **chưa xác nhận** timestamp PJME là giờ bắt đầu hay giờ kết thúc khoảng đo. Pipeline dùng nhãn giờ địa phương, cách ly toàn bộ ngày DST và mọi cửa sổ lịch sử/đầu ra đi qua chúng. Không chuyển UTC bằng suy đoán. Báo cáo độ phủ bắt buộc đọc cùng chỉ số. Đây là thực nghiệm trên các cửa sổ an toàn, chưa phải mô phỏng vận hành UTC đầy đủ.

Thời tiết ERA5 Philadelphia có thể thu thập và kiểm tra độc lập, nhưng **không ghép** khi quy ước thời gian chưa xác nhận. Chỉ khi có bằng chứng về nguồn mới đặt `timestamp_convention: hour_starting` hoặc `hour_ending`, `time_convention_confirmed: true` và thêm `time_convention_evidence` vào cấu hình. Pipeline vẫn cách ly cả hai giờ DST không xác định được thứ tự.

Khi được phép ghép, khoảng đo được chuẩn hóa và gắn nhãn bằng **thời điểm kết thúc trong UTC**: phụ tải `y[T]` đã hoàn thành tại thời điểm phát hành `T`. Bức xạ trung bình giờ trước cũng gắn nhãn cuối giờ nên ghép trực tiếp; nhiệt độ/độ ẩm lấy tức thời tại cuối giờ trong nhánh oracle. Bộ thu thập lấy thêm một ngày đệm cuối. Không được dùng nhãn giờ bắt đầu để coi cả khoảng đo đó đã có sẵn lúc phát hành.

```powershell
python scripts/run_pipeline.py run --weather --branch oracle
```

Lệnh trên chỉ chạy sau khi xác nhận quy ước. `oracle` dùng thời tiết tái phân tích ở giờ đích, **giả định biết trước thời tiết**, không phải kết quả triển khai thực tế. Không gộp bảng xếp hạng hai nhánh. Thời tiết tái phân tích lịch sử cũng không được coi là có sẵn tức thời trong nhánh chính. NYISO vẫn là hướng mở rộng, chưa chuyển nguồn tự động khi nguồn đó không truy cập được.

## Dự báo lại bằng mô hình đã lưu

```powershell
python scripts/run_pipeline.py predict --run-dir outputs/full-none-9cb1d10a47 --origin "2017-07-15 12:00" --delay 0
```

Mặc định sử dụng mô hình đơn có CV tốt nhất; dùng ensemble nếu nó cải thiện thêm trên 0,1 điểm phần trăm MAPE ở validation. Có thể chọn rõ bằng `--model weighted_ensemble`. Lưu mô hình của hai ứng viên CV dẫn đầu, với từng horizon và độ trễ. Không cho phép dùng mô hình đã huấn luyện qua thời điểm phát hành để dự báo hồi tố. Đầu vào lúc huấn luyện và suy luận đi qua cùng `SampleBuilder`. Nhánh causal không cần biết phụ tải tương lai. Nhánh oracle cần thời tiết tương lai theo giả định của nó.

## Thiết kế kiểm định

- Phát triển 2014–2016, giữ năm 2017 làm holdout. Tạo năm fold trên lưới giờ đầy đủ **trước** khi lọc dữ liệu.
- Giữ gap ít nhất 24 giờ, kiểm tra nhãn huấn luyện có trước đầu validation. Không fit scaler bằng dữ liệu validation/test. SVR chuẩn hóa cả X và y trong từng lần fit.
- Lựa chọn mô hình/cấu hình/ensemble bằng validation, lưu quyết định trước khi đánh giá holdout. Không tự tối ưu lại dựa trên test. MAPE của 24 horizon có trọng số bằng nhau khi chọn mô hình.
- Các mô hình chấm trên cùng cặp thời điểm; kịch bản chậm một giờ cũng dùng tập chung để so sánh. Nhãn thiếu không được nội suy. Điền tiến đầu vào tối đa hai giờ; các khoảng dài hơn giữ thiếu.
- Đỉnh dùng ngưỡng Q90 của phụ tải quan sát trước holdout, không lấy ngưỡng từ test. Sai số giờ đỉnh chỉ tính cho cửa sổ đủ toàn bộ horizon cấu hình; đồng hạng lấy giờ sớm nhất.
- Dữ liệu đã sửa hồi tố và thời điểm công bố từng quan sát chưa được tái dựng. Mặc định giả định phụ tải giờ vừa kết thúc có sẵn; kiểm tra độ nhạy bằng độ trễ một giờ.
- Lần chạy hoàn tất được tái sử dụng. Nếu bị ngắt sau khi bắt đầu holdout, dùng `python scripts/run_pipeline.py run --profile full --resume-holdout`. Chế độ này kiểm tra dữ liệu và các lựa chọn đã khóa, chỉ khôi phục kiểm thử, không chạy lại tìm tham số. Mỗi horizon/độ trễ hoàn tất được lưu thành checkpoint; các lần khôi phục tiếp theo tái sử dụng chúng. Không đổi cấu hình khi khôi phục.

## Cấu trúc

`src/load_forecaster/` chứa thu thập, thời gian, đặc trưng, mô hình, đánh giá và điều phối. `configs/experiment.yaml` là cấu hình tái lập. `tests/` kiểm tra rò rỉ, DST, năm nhuận, khoảng thiếu, cache, retry, chuẩn hóa và tính công bằng khi chấm điểm.

Dashboard chỉ đọc kết quả đã xác minh:

```powershell
streamlit run app/dashboard.py
```

Kiểm tra mô hình đã lưu và xuất lại báo cáo gọn sau một lần chạy hoàn tất:

```powershell
python scripts/verify_saved_models.py --run-dir outputs/full-none-9cb1d10a47
python scripts/export_report.py --run-dir outputs/full-none-9cb1d10a47
```

Nguồn: [PJME mirror](https://github.com/archd3sai/Hourly-Energy-Consumption-Prediction), [Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api), [scikit-learn](https://scikit-learn.org/stable/).
