# Kịch bản thuyết trình bảo vệ 15 phút (Nhóm 5 thành viên A–E)

> **Dự án**: Dự báo phụ tải điện đa bước 24 giờ tại Tetouan (Zone 1, Zone 2, Zone 3) — UCI ID 849  
> **Tổng thời lượng**: 15 phút (mỗi thành viên trình bày trực tiếp 2,5 – 3,5 phút)

---

## Phân bổ thời lượng & Nội dung chi tiết từng thành viên

### 1. Thành viên A — Dữ liệu 3 vùng, EDA & Khảo sát nguồn Việt Nam (`00:00 – 02:30` · 2,5 phút)
- **Điền tên & MSSV**: *(Điền họ tên & MSSV Thành viên A)*
- **Nội dung trình bày**:
  1. **Bài toán**: Tại mỗi giờ phát hành `T` (ví dụ `12:00`), dự báo 24 giá trị phụ tải cho 24 giờ tiếp theo (`13:00` → `12:00` hôm sau). Zone 1 là thực nghiệm chính; Zone 2 và Zone 3 để đối chiếu mở rộng.
  2. **Kiểm toán dữ liệu (`audit.json`)**: Bộ UCI Tetouan có **52.416 dòng** (mỗi 10 phút từ `01/01/2017` đến `30/12/2017`, khớp SHA-256 chính thức), **0 mốc thiếu**, **0 dòng trùng**, **8.736 mốc tròn giờ**. Giữ nguyên đơn vị và giờ gốc vì metadata UCI chưa xác nhận đơn vị vật lý/DST.
  3. **3 biểu đồ EDA (chỉ vẽ trên phần phát triển `01/01 – 18/10/2017`)**:
     - Cả 3 vùng đạt đỉnh buổi tối (khoảng `20:00`) và đáy rạng sáng (`06:00–07:00`).
     - Cuối tuần Zone 1 giảm tải trung bình **3,29%**, Zone 2 giảm **8,38%**.
     - Nhiệt độ tương quan dương rõ với tải Zone 1 tại cùng khung giờ (`r = 0,577` lúc 14:00; `r = 0,686` lúc 20:00).
     - Cửa sổ tăng mạnh nhất phần phát triển: `26/03/2017 19:00` tăng `+12.279,8` trong 1 giờ.
  4. **Khảo sát nguồn Việt Nam (`docs/KHAO_SAT_NGUON_VIET_NAM.md`)**: Open-Meteo (ERA5, UTC+7) cung cấp đủ 5 biến thời tiết theo giờ cho Hà Nội & TP.HCM, nhưng EVN/EVNHANOI/EVNHCMC/NSMO hiện chưa công khai chuỗi phụ tải theo giờ cấp thành phố.

---

### 2. Thành viên B — Tạo mẫu 20 đặc trưng & Chống rò rỉ (`02:30 – 05:00` · 2,5 phút)
- **Điền tên & MSSV**: *(Điền họ tên & MSSV Thành viên B)*
- **Nội dung trình bày**:
  1. **Cách chuyển chuỗi 10 phút thành bảng học máy**: Mỗi giờ phát hành `T` tạo ra 24 hàng (`h = 1..24`), mỗi hàng có **20 đặc trưng** (`15` cơ sở + `5` thời tiết):
     - Tải gần nhất (`load_now`, `lag1h`, `lag2h`, `lag24h`, `lag168h`, `mean24h`, `max24h`).
     - Tải cùng giờ đích hôm trước (`day_lag`) và tuần trước (`week_lag`).
     - Mã hóa chu kỳ giờ/thứ/ngày trong năm (`sin/cos` của `target_time`).
     - 5 biến thời tiết lấy tại **`T - 1 giờ`** (giả định độ trễ quan sát 1 giờ).
  2. **Kiểm soát chống rò rỉ**: Dùng chung đúng một hàm `forecast_features()` cho cả lúc huấn luyện (C) và lúc demo (E). Kiểm thử tự động xác nhận thay đổi số liệu tương lai không làm thay đổi bất kỳ đặc trưng nào.
  3. **Nhận xét tác động thời tiết (`weather_ablation.csv`)**: Trên cùng tập hàng hợp lệ, việc thêm 5 biến thời tiết trễ 1h giúp giảm sai số trên tập validation ở Zone 2 (`5,516%` vs `5,547%`) và một số fold (Zone 1 fold 2 `-0,012` đpt; Zone 3 fold 3 `-0,075` đpt), nhưng trên tập kiểm thử cuối không cải thiện thêm (`+0,012` đpt ở Zone 1; `+0,108` đpt ở Zone 2) vì thông tin nhiệt nền đã được phản ánh phần lớn qua `load_now` và `day_lag`.

---

### 3. Thành viên C — Huấn luyện 24 bước & Lưu/Nạp đa vùng (`05:00 – 08:00` · 3,0 phút)
- **Điền tên & MSSV**: *(Điền họ tên & MSSV Thành viên C)*
- **Nội dung trình bày**:
  1. **Chiến lược Direct Multi-Step**: Huấn luyện **24 mô hình độc lập** cho `h = 1..24` ở mỗi thuật toán (**Ridge**, **Random Forest**, **SVR RBF**) + biến thể **Ridge bỏ thời tiết**. `StandardScaler` chỉ `fit` trên tập train từng lượt.
  2. **Chọn cấu hình bằng Validation trước khi mở Test (`selection.json`)**:
     - Zone 1 CV: Random Forest `3,524%`, Ridge `3,540%`, SVR `4,229%`. Vì Ridge chỉ chênh `0,016` đpt (< ngưỡng `0,1` đpt) và nhanh hơn ~28 lần (`0,42s` vs `11,90s`), quy tắc chọn khóa **Ridge (`alpha = 100.0`)** cho Zone 1.
     - Mở rộng sang Zone 2 (`alpha = 100.0`, CV `5,516%`) và Zone 3 (`alpha = 0,1`, CV `5,519%`): Ridge đều thắng CV và được khóa trước khi chấm tập kiểm thử.
  3. **Kiểm chứng lưu/nạp (`verification.json`)**: 24 file `.joblib` lưu kèm `latest_train_target` để chặn dự báo hồi tố; sai số khi nạp lại bằng `predict_saved` gần như bằng 0 (`< 1e-10`).

---

### 4. Thành viên D — Chia tập, Đối chứng & Đánh giá Giờ quan trọng (`08:00 – 11:30` · 3,5 phút)
- **Điền tên & MSSV**: *(Điền họ tên & MSSV Thành viên D)*
- **Nội dung trình bày**:
  1. **Thiết kế phép thử chống rò rỉ**: Chia **80% đầu phát triển** (3 lượt expanding CV 28 ngày) / **20% cuối kiểm thử** (`19/10 – 30/12/2017`), chừa khoảng đệm `>= 24 giờ` trước mỗi tập đánh giá. Mọi mô hình và 2 đối chứng (`day_prior`, `week_prior`) chấm trên cùng **1.724 cửa sổ đủ 24 giờ** (`41.376` cặp, độ phủ `98,6%`).
  2. **Kết quả trên tập kiểm thử (Test)**:
     - **Zone 1**: Ridge đạt **MAPE `3,273%`** (MAE `919,85`), vượt cả `day_prior` (**`3,461%`**) và `week_prior` (**`3,851%`**). Riêng theo từng bước `h=1..24`, Ridge vượt mạnh ở `h=1..10` (`1,84%` ở `h=1`) và `h=21..24`, còn ở `h=12..20` dao động quanh `3,5–3,7%` (xấp xỉ `day_prior`).
     - **Zone 2**: Ridge đạt **MAPE `4,012%`** (RF `3,938%`), vượt xa `day_prior` (`5,378%`) và `week_prior` (`4,809%`).
     - **Zone 3**: Ridge đạt **MAPE `5,416%`**, vượt `day_prior` (`5,697%`) và `week_prior` (`9,997%`).
  3. **Hồi quy tại giờ đỉnh & giờ tăng mạnh (`ramp_q95 = 8.772,3` tính trên train Zone 1)**:
     - **Giờ đỉnh (Zone 1 Test, 123 giờ đỉnh phân biệt)**: Ridge có MAE `827,82`, sai lệch trung bình có dấu **`+164,04`** và tỷ lệ dự báo thiếu **`43,7%`** (ít thiếu hơn `day_prior` với `-188,60` và thiếu `55,5%`).
     - **Giờ tăng mạnh >= Q95 (Zone 1 Test, 19 giờ đích phân biệt)**: Ridge có MAE `1.312,52`, sai lệch có dấu **`+460,83`**, tỷ lệ dự báo thiếu **`35,7%`**.
  4. **2 ví dụ giờ cụ thể trên tập Test Zone 1 (`case_studies.csv`)**:
     - *Ví dụ giờ đỉnh (`h=24`)*: Phát hành `22/10/2017 19:00` → đích `23/10/2017 19:00`: thực đo `46.451,82`, Ridge dự báo `45.137,56` (**thiếu `-1.314,26`**).
     - *Ví dụ giờ tăng mạnh (`h=24`)*: Phát hành `23/10/2017 18:00` → đích `24/10/2017 18:00` (tải tăng `+11.740,57` trong 1h): thực đo `45.903,54`, Ridge dự báo `44.729,78` (**thiếu `-1.173,76`**).

---

### 5. Thành viên E — Tích hợp, Live Demo & Chốt câu hỏi bảo vệ (`11:30 – 15:00` · 3,5 phút)
- **Điền tên & MSSV**: *(Điền họ tên & MSSV Thành viên E)*
- **Nội dung trình bày**:
  1. **Live Demo trực tiếp (`~1,5 phút`)**:
     - Chạy Web Demo `streamlit run app/tetouan_demo.py` (chọn **Zone 1**, ngày `01/12/2017 12:00`, nạp mô hình `ridge` đã khóa theo CV) hoặc chạy lệnh `python scripts/tetouan.py demo --zone zone1 --origin "2017-12-01 12:00"`.
     - Chỉ rõ 3 đường trên biểu đồ: **Dự báo 24h**, **Thực đo sau phát hành**, **Đối chứng hôm trước**; đối chiếu bảng 24 dòng (`forecast.csv`) khớp với lần chạy đã lưu.
  2. **Trả lời thẳng 2 câu hỏi trọng tâm của hội đồng**:
     - *Câu 1 (Có thắng baseline trên cả 24h?)*: Trên tổng thể 24 giờ của **cả 3 vùng**, mô hình Ridge được chọn đều có MAPE thấp hơn cả đối chứng hôm trước và tuần trước (Zone 1: `3,273%` vs `3,461%`/`3,851%`; Zone 2: `4,012%` vs `5,378%`/`4,809%`; Zone 3: `5,416%` vs `5,697%`/`9,997%`). Ở Zone 1, lợi thế rõ rệt nhất ở 10 giờ đầu và 4 giờ cuối.
     - *Câu 2 (Dự báo thiếu bao nhiêu ở giờ đỉnh/tăng mạnh?)*: Tổng thể tập test Zone 1, Ridge có sai lệch có dấu `+164,0` ở giờ đỉnh (thiếu ở `43,7%` cửa sổ) và `+460,8` ở giờ tăng mạnh Q95 (thiếu ở `35,7%` mốc); tuy nhiên ở những đợt tăng đột biến hoặc đỉnh cao nhất đầu kỳ test (`23–24/10/2017`), mô hình vẫn có thể dự báo thiếu `~1.174 – 1.314` đơn vị.
  3. **Hạn chế & Hướng phát triển**: Chưa có xác nhận đơn vị vật lý và múi giờ/DST từ UCI; chưa có chuỗi tải giờ công khai tại Việt Nam; thời tiết hiện trễ 1h (chưa tích hợp dự báo thời tiết tương lai).
