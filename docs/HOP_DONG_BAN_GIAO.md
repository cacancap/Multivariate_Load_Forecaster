# Hợp đồng bàn giao giữa A–E

**Phiên bản đề xuất 0.1, duyệt vào ngày 2.** Bảng đầu trang dùng để giao việc. Các mục sau mô tả định dạng dự kiến để nhóm tự triển khai. Khi đổi định dạng, ghi phiên bản, lý do và cách chuyển đổi cho người nhận. Đọc kịch bản dự báo trong [kế hoạch nhóm](KE_HOACH_NHOM_5_NGUOI.md) và tìm việc đầu tiên trong [phiếu giao việc](PHIEU_GIAO_VIEC.md).

## 1. Ai giao gì, cho ai và khi nào?

| Người giao | Sản phẩm | Người nhận | Mốc | Cách kiểm tra |
|---|---|---|---|---|
| D | Một bộ dữ liệu mô phỏng dùng thử chung và quy ước bảng | A, B, C, E | Ngày 1–2 | B đọc quan sát, C nhận đặc trưng và nhãn, D chấm, E đọc bảng kết quả |
| A | Biên bản chọn nguồn | B, D | Cuối ngày 3 | D đối chiếu bằng chứng giờ đo, đơn vị và thời điểm có thể sử dụng. B xác nhận cách tạo nhãn |
| A | Bảng quan sát, mô tả nguồn và báo cáo chất lượng | B, D | Ngày 7 | B đọc bảng và kiểm tra cột. D kiểm tra giờ và độ phủ |
| A | Bộ tải và hướng dẫn lấy lại bản dữ liệu | E | Ngày 7 | E lấy được đúng phiên bản dữ liệu |
| B | Bộ mẫu và danh sách cột | C, D | Ngày 7 | C nhận đúng cột và thứ tự. D kiểm tra nhãn và thông tin sẵn có |
| B | Công cụ tạo đầu vào dự báo | E | Ngày 7 | E tạo được đầu vào tại một thời điểm phát hành cho đủ 24 bước |
| B | Kết quả so sánh có và không có thời tiết | D | Ngày 12 | D kiểm tra hai nhánh dùng cùng các mẫu |
| C | Bộ mô hình, hướng dẫn nạp và danh sách cấu hình thử | D, E | Ngày 7 giao bộ mô hình cho D và hướng dẫn cho E. Trước khi thử tuần 2 giao danh sách cấu hình cho D | D thử huấn luyện và dự báo. E thử nạp lại |
| D | Cách chia tập và các khoảng thời gian tương ứng | C | Ngày 7, trước đợt thử cấu hình | C xác nhận cách gán dữ liệu học và kiểm định. D kiểm tra nhãn học đã có trước lúc kiểm định |
| D | Bảng kết quả từ lượt chạy thử | E | Ngày 7 | E đọc được thời điểm phát hành, giờ đích, dự báo và độ phủ |
| D | Bảng validation và cấu hình đã khóa | E | Ngày 12 | E đọc được bảng và đối chiếu được cấu hình với lần chạy. D lưu quyết định trước test |
| D và C | Bảng kiểm thử cuối và định nghĩa chỉ số từ D, mô hình đã lưu từ C | E | Ngày 15 | E đối chiếu số liệu với bảng và thử nạp mô hình cho đủ 24 bước |
| E | Bản chạy thử, rồi hướng dẫn, bản cài mới và gói nộp | Cả nhóm | Ngày 7 cho bản chạy thử, ngày 18 cho bộ nộp | Nhóm thử chạy, đối chiếu kết quả và duyệt phần mình viết |

### Một ví dụ mô phỏng đi qua các bước

Mọi thời điểm dưới đây dùng cùng ngày và cùng cơ sở thời gian mô phỏng, trừ khi ghi ngày mai. Phụ tải dùng đơn vị giả lập `synthetic_unit`. Bảng trích bước 1 của lần phát hành **12:00**. Bộ dùng thử đầy đủ gồm bước 1–24, đến **12:00 ngày mai**.

| Bước | Nội dung mẫu | Người tiếp theo làm gì? |
|---|---|---|
| A · Quan sát | Nhiệt độ 25 °C đo 11:00, có thể dùng từ 12:00. Phụ tải thật 13:00 là 220 | B dùng nhiệt độ cho đầu vào lúc 12:00. Giá trị 220 được nối riêng làm nhãn khi học hoặc chấm |
| B · Bộ mẫu | `origin_time=12:00`, `target_time=13:00`, `horizon_hours=1`, một đặc trưng nhiệt độ là 25, nhãn `y=220` | C nhận đặc trưng và nhãn khi huấn luyện. Khi dự báo lúc 12:00, C nhận các đặc trưng đã có |
| C · Dự báo | SVR trả 200 cho khóa 12:00 → 13:00, bước 1 | D ghép đúng khóa với số đo thật |
| D · Chấm | `y_true=220`, `y_pred=200`, sai số tuyệt đối 20. Đối chứng ngày trước trả 190, sai số tuyệt đối 30 | E hiển thị dự báo, số đo và độ phủ do D tính trên lưới dự kiến |
| E · Chạy thử | Hiển thị dòng 13:00 với dự báo 200 và số đo thật 220, gắn nhãn dữ liệu mô phỏng | Cả nhóm đối chiếu màn hình với bảng gốc |

Nếu nhóm thay giá trị thời tiết đo lúc 13:00, đầu vào của lần phát hành 12:00 phải giữ nguyên. Dùng bộ dữ liệu mô phỏng ở mục 6 để thử trên nhiều giờ và tính các chỉ số tổng hợp.

### Quy tắc chung

- Dữ liệu thật và fixture luôn có `dataset_id` khác nhau; UI phải ghi rõ dữ liệu mô phỏng.
- Mỗi lần chạy có `run_id`, seed, phiên bản mã/thư viện, hash cấu hình và hash dữ liệu.
- Mọi bảng chứa thời gian phải khai báo `time_basis`: UTC có xác nhận hoặc giờ địa phương của nguồn. Không trộn hai loại trong một phép nối.
- Không đổi đơn vị ngầm. Dùng `load_value` và `load_unit`; chỉ đặt tên MW sau khi xác nhận đơn vị.
- Giới hạn tối đa bốn luồng và chạy tuần tự giữa các mô hình. Đo thời gian, RAM đỉnh; ghi rõ công cụ và phạm vi đo.

## 2. A bàn giao dữ liệu

### 2.1. Metadata bắt buộc

`dataset_id`, URL nguồn, thời điểm tải, SHA-256 tệp gốc, schema_version, khoảng thời gian, số dòng gốc, tần suất gốc, múi giờ nếu biết, ý nghĩa timestamp/khoảng đo và bằng chứng, đơn vị tải/thời tiết, quy tắc xử lý thiếu/trùng, giả định độ trễ công bố, các giới hạn chưa xác nhận.

PJME theo giờ; Tetouan có tần suất gốc 10 phút. **Horizon luôn tính bằng giờ thực, không phải số dòng.** Khi đủ bằng chứng tải là công suất, có thể lấy trung bình trong giờ đã kết thúc; nếu là năng lượng khoảng đo thì tổng hợp theo ý nghĩa đó. Không cộng sáu giá trị công suất để gọi là công suất giờ. Nếu chưa đủ bằng chứng, giữ tần suất/đơn vị gốc và dự báo quan sát tại các mốc cách T đúng 1…24 giờ; báo rõ đây chưa phải tải trung bình giờ. D chốt định nghĩa nhãn trước thực nghiệm.

### 2.2. Quan sát và thời điểm có thể sử dụng

| Trường | Ý nghĩa |
|---|---|
| `source_row_id`, `timestamp_raw` | Truy ngược dòng và timestamp gốc |
| `observation_time` | Nhãn thời gian đã chuẩn hóa theo metadata |
| `load_observed` | Giá trị thật; giữ thiếu nếu không có, không điền nhãn |
| `load_input` | Giá trị dùng làm đầu vào, có thể điền tiến tối đa hai giờ |
| `load_available_at` | Thời điểm giả định tải có sẵn; mặc định sau khi khoảng đo kết thúc |
| `quality_flags` | Thiếu, điền, giá trị bất thường, trùng, DST mơ hồ hoặc bị cách ly |

Thời tiết nên bàn giao bảng riêng với `weather_observation_time`, `weather_available_at`, các biến và cờ chất lượng. Mặc định thời tiết quan sát có độ trễ **một giờ**, ghi là giả định chứ không phải lịch sử công bố đã xác minh. Nguồn tái phân tích không tự đạt điều kiện này. Tại T chỉ nhận quan sát quá khứ có cả thời điểm quan sát và `available_at` không vượt T.

Giữ giờ DST mơ hồ/không tồn tại trong báo cáo cách ly; không tự dịch giờ hoặc lấy trung bình giờ trùng. Không suy đoán UTC để ghép PJME với thời tiết. Nếu nguồn chung chưa xác nhận múi giờ, báo rõ cơ sở giờ địa phương và không ghép ngoài nguồn bằng giả định UTC. Áp dụng quyết định chuyển nguồn cuối ngày 3 trong kế hoạch.

**Nghiệm thu:** tệp gốc bất biến; khóa thời gian của bảng được dùng không trùng; có bảng số dòng trước/sau, lý do loại/điền và độ phủ theo tháng. Khoảng thiếu dài giữ thiếu. Bước nhảy/tải cao chỉ được gắn cờ để kiểm tra, không tự cắt bỏ cực đại.

## 3. B bàn giao mẫu dự báo

Giao diện tối thiểu dự kiến:

```text
build_samples(origins, horizons, label_cutoff) -> X, y, sample_index, validity
forecast_features(origin, horizons) -> X, sample_index, validity
```

Hai thao tác dùng chung quy tắc đặc trưng. `label_cutoff` chỉ giới hạn nhãn được phép học; mọi đặc trưng vẫn phải tính theo thời điểm origin của từng dòng. Nhãn kiểm định có thể được nối riêng để chấm điểm, không truyền vào bộ tạo đầu vào suy luận.

Khóa mẫu duy nhất: `(origin_time, target_time, horizon_hours)`; `target_time = origin_time + horizon_hours`, horizon nguyên từ 1 đến 24. Bàn giao `X` với tên/thứ tự cột cố định, `y` đúng đơn vị, và chỉ mục khớp từng dòng. Không truyền `load_observed` ở giờ đích thành một cột của X. `validity` lưu cả mẫu không hợp lệ và lý do để D tính độ phủ trên lưới origin ban đầu.

- Lag/rolling dựa trên thời gian: lag 24 giờ ở nguồn 10 phút không phải 24 dòng. Ngưỡng điền hai giờ cũng phải tính bằng thời gian.
- Tại origin T, chỉ dùng tải có `load_available_at <= T`. Kiểm tra độ nhạy chậm tải một giờ bằng cùng cơ chế.
- Tải tại `target_time − 24h`/`−168h` chỉ là đặc trưng nếu đã có sẵn tại T. Khi chưa có thì giữ thiếu/loại theo chính sách đã chốt, không dùng nhãn tương lai.
- Thời tiết đầu vào là lịch sử đã biết tại T, không phải thời tiết thật ở target. Lưu tuổi của quan sát được dùng và cờ thiếu.
- Đặc trưng lịch được tính theo cơ sở thời gian đã công bố. Ngày lễ liên bang Mỹ phù hợp PJME; không áp dụng máy móc cho Tetouan.
- Không fit scaler hoặc bộ điền theo thống kê trên toàn bộ dữ liệu. Thành phần cần học tham số phải được fit trong train của mỗi fold.
- Có từ điển đặc trưng: tên, công thức, đơn vị, dữ liệu cần có, độ trễ và phiên bản. Cột không dùng trong nhánh không thời tiết phải được ghi rõ.

Ví dụ với giờ đã xác nhận là cuối khoảng đo: tại T=12:00, tải khoảng vừa kết thúc có thể dùng theo giả định cơ sở; thời tiết quan sát 11:00 có sẵn lúc 12:00 khi độ trễ một giờ. Dự báo 13:00…12:00 ngày sau. Ở kịch bản tải chậm một giờ, tải kết thúc 12:00 chưa dùng được. Ví dụ này không thay thế việc A xác minh nguồn.

## 4. C bàn giao mô hình

```text
make_model(model_name, parameters, seed) -> estimator
estimator.fit(X_train, y_train)
estimator.predict(X_future) -> predictions_in_original_unit
save/load(model_artifact)
```

- Một mô hình cho mỗi horizon; không đưa giá trị thật/dự báo của các giờ trong khoảng dự báo trở lại đầu vào.
- Ridge/SVR có scaler đầu vào fit riêng trên train. SVR chuẩn hóa y trong train và đổi dự báo về đơn vị gốc. RF không cần scaler.
- C cung cấp khả năng fit/predict; D quyết định fold, thử cấu hình và cách chọn. Tắt early stopping dùng chia ngẫu nhiên; nếu cần thì dùng tập thời gian do D chỉ định.
- Mỗi artifact lưu model, horizon, tên/thứ tự cột, đơn vị, metadata thời gian, phiên bản đặc trưng, tham số, seed và thời điểm nhãn train mới nhất.
- Kiểm tra đầu vào sai schema/đơn vị phải báo lỗi rõ. Không âm thầm sắp sai cột hoặc thay nhãn thiếu bằng 0.
- SVR tối đa 365 ngày train; Ridge/RF có lượt cùng cửa sổ để phân biệt ảnh hưởng dữ liệu. Giới hạn được ghi trong manifest.
- Save/load phải cho dự báo tương đương trong sai số số học đã khai báo; không dùng artifact học qua origin để tuyên bố dự báo lịch sử tại origin đó.

## 5. D bàn giao thực nghiệm và kết quả

### 5.1. Fold, manifest và lựa chọn

D xuất danh sách origin train/validation/test trên lưới đầy đủ **trước khi lọc**. Fold có ranh giới và khoảng cách tối thiểu 24 giờ; kiểm tra trực tiếp mọi nhãn train đã có sẵn trước origin kiểm định đầu tiên. Đối chứng cũng chỉ dùng tải có sẵn.

Áp dụng khoảng phát triển/holdout và số fold tại kế hoạch chung: PJME ưu tiên phần 2018 chưa dùng; 2017 không được gọi là test mới. Tetouan giữ 20% cuối theo thời gian. Nếu không đủ độ dài, D lập điều chỉnh bằng dữ liệu phát triển trước khi mở holdout và lưu lý do. Không chọn cấu hình từ test.

Manifest mỗi trial gồm mô hình/tham số/horizon, fold, khoảng train và độ trễ, phiên bản dữ liệu/đặc trưng, seed, độ phủ, chỉ số, thời gian và RAM. D dùng cùng định nghĩa MAPE trung bình fold/horizon; ghi rõ trọng số. Khi chênh dưới 0,1 điểm phần trăm ưu tiên nhanh hơn. Trọng số ensemble nếu có cũng chỉ chọn bằng validation.

Khóa cấu hình/đặc trưng/quy tắc lọc/ensemble trước test cuối. Có thể tiếp tục lần chạy gián đoạn bằng checkpoint của cùng cấu hình; không thay lựa chọn sau khi nhìn kết quả test.

### 5.2. Bảng dự báo và chỉ số

Mỗi dòng dự báo gồm `run_id`, `dataset_id`, `feature_set`, `model`, `split`, `fold_id`, `origin_time`, `target_time`, `horizon_hours`, `y_true`, `y_pred`, `load_unit`, `time_basis`. Dòng không chấm được có trạng thái/lý do riêng; không tạo nhãn thay thế.

So sánh mô hình trên giao các khóa mẫu hợp lệ và báo thêm độ phủ từng mô hình trên cùng lưới gốc. Ablation thời tiết có/không cũng dùng cùng khóa. Không gọi tăng chất lượng nếu chỉ bỏ thêm mẫu khó. Các nguồn/định nghĩa nhãn khác nhau có bảng riêng.

| Chỉ số | Quy tắc |
|---|---|
| MAE | Trung bình trị tuyệt đối sai số, đơn vị tải gốc |
| RMSE | Căn trung bình bình phương sai số, đơn vị tải gốc |
| MAPE | `100 × mean(abs(y_true − y_pred) / abs(y_true))`; loại mẫu y=0 khỏi riêng phép tính này và báo số lượng |
| Tải cao | Ngưỡng Q90 chỉ tính từ nhãn train; `>= Q90` là dương tính cho cả tải thật và dự báo |
| Precision/Recall/F1 | Kèm TP/FP/TN/FN và số mẫu; mẫu số bằng 0 ghi không xác định, không tự báo hoàn hảo |
| Đỉnh 24 giờ | Chỉ cửa sổ đủ 24 đích quan sát; báo sai số độ lớn đỉnh và độ lệch giờ đỉnh, trường hợp hòa lấy giờ sớm nhất |

Báo tổng thể, từng horizon, mùa và tải cao; luôn ghi số mẫu. Mùa phải có định nghĩa phù hợp địa điểm nguồn. Độ phủ cửa sổ đủ 24 giờ được báo riêng. Chỉ số theo horizon không thay thế chỉ số cửa sổ đỉnh.

### 5.3. Các đầu ra E được phép dùng

D bàn giao dự kiến `predictions.parquet`, `metrics.csv`, `coverage.json`, `resources.json`, `experiment_manifest.json`, `selected_config.json`, và bản phân tích kết quả. Đây là tên hợp đồng cho nhóm; khi ánh xạ sang tệp hiện có phải có bảng ánh xạ.

Mỗi số trong báo cáo/UI phải truy về run và bảng tương ứng. Không dùng số mẫu trong tài liệu này hoặc kết quả kế thừa để điền vào bảng thực nghiệm mới.

## 6. Dữ liệu mô phỏng để thử từ ngày 1

D thống nhất bộ dữ liệu mô phỏng (fixture) và kết quả mong đợi để A, B, C và E cùng dùng. Không cần tải nguồn thật để thử giao diện.

| Fixture | Nội dung và mục đích |
|---|---|
| Chuỗi sạch | Ít nhất 21 ngày theo giờ, tải dương và thời tiết mô phỏng có quy luật; ghi đơn vị `synthetic_unit`. Hai khối validation 48 giờ và gap 24 giờ chỉ để kiểm tra đường chạy, không thay cấu hình đánh giá thật |
| Nguồn 10 phút | Kiểm tra lag 24 giờ tương ứng thời điểm cách 144 bước, horizon vẫn 1…24 giờ |
| Thời gian | Ngày DST xuân/thu, năm nhuận, thứ tự đảo, hai giờ trùng chưa biết thứ tự, cơ sở thời gian chưa xác nhận |
| Chất lượng | Thiếu 1, 2 và 4 giờ; nhãn thiếu; ngoại lai lớn nhưng hợp lệ; giá trị âm; thời tiết có sẵn chậm |
| Chỉ số tính tay | `y=[100,200]`, `pred=[90,220]`: MAE=15, RMSE=√250≈15,8114, MAPE=10%. Với Q90 train đã biết là 150: TP=1, TN=1, FP=0, FN=0 |

Fixture DST chỉ kiểm tra cách xử lý thời gian, không lấy quy mô vài ngày làm dữ liệu huấn luyện thật. Ghi ngày/múi giờ cụ thể theo nguồn và giữ cả trường hợp phải từ chối xử lý.

## 7. Các kiểm tra trước khi tích hợp

- **A/B:** xáo thứ tự dòng không đổi kết quả chuẩn hóa hợp lệ; timestamp mơ hồ bị cách ly; không có nhãn điền; tổng số dòng được giải trình.
- **B/D:** thay toàn bộ tải và thời tiết sau T không đổi X tại T. Thay quan sát trước T nhưng chưa được công bố ở T cũng không đổi X. Thử riêng cho từng horizon và độ trễ.
- **C/D:** scaler/bộ biến đổi học chỉ thấy train; nhãn train không vượt ranh giới kiểm định; thay nhãn test không làm thay mô hình hoặc lựa chọn cấu hình.
- **D/C:** chỉ số khớp ví dụ tính tay; dự báo và đối chứng có cùng khóa; peak threshold từ train; độ phủ không mất sau phép nối.
- **C/E:** nạp lại đủ 24 mô hình cho kết quả tương đương; báo rõ horizon thiếu; schema sai bị từ chối; không dự báo hồi tố bằng mô hình học tương lai.
- **E/cả nhóm:** môi trường mới chạy được theo `readme.txt`; UI phân biệt fixture/kết quả thật; PDF, slides và bảng số liệu khớp cùng run.

Nghiệm thu theo mẫu cuối [phiếu giao việc](PHIEU_GIAO_VIEC.md). Người nhận có thể yêu cầu sửa khi sai hợp đồng; chủ module chịu trách nhiệm sửa và cung cấp lại bằng chứng. Các thay đổi nhỏ có phiên bản, không bắt cả nhóm chờ một thành viên hoàn thành mọi thứ.
