IT3190 • Dự báo phụ tải điện Zone 1, Tetouan
==========================================

Giải nén ZIP, mở terminal tại thư mục chứa readme.txt. Phiên bản đã chạy dùng Python 3.13 trên Windows. Cài phụ thuộc đúng phiên bản trong requirements.txt. Các lệnh dùng đường dẫn tương đối từ thư mục gốc.

  python -m venv .venv
  .venv\Scripts\activate
  python -m pip install -r requirements.txt

1. Kiểm tra nhanh một bước Ridge và đối chứng trên dữ liệu thật
  python scripts/tetouan.py smoke

Lệnh tự chuẩn bị dữ liệu nếu thiếu. ZIP bàn giao có bản gốc UCI và manifest. Khi bản gốc chưa có, bộ tải cần kết nối tới archive.ics.uci.edu. SHA-256 và kiểm toán xem reports/tetouan/audit.json. Lần chạy thử chỉ dùng khối kiểm định cuối ở phần phát triển.

2. Từ tệp gốc tới kết quả chính
  python scripts/tetouan.py prepare
  python scripts/tetouan.py full

Mỗi lượt tạo thư mục riêng dưới outputs/tetouan/smoke hoặc full. latest.txt của mỗi loại ghi tên lần chạy đã hoàn tất. Mở scores.csv, weather_ablation.csv và verification.json trong đó. Các bảng, PDF và hình của lần bàn giao ở reports/tetouan. Dự báo gốc được lưu dưới dạng Parquet, có thể đọc bằng pandas.read_parquet.

3. Lặp lại lựa chọn đúng như bản nộp
  python scripts/tetouan.py full --selection reports/tetouan/selection.json

Chế độ này dùng lại tham số đã khóa và kiểm tra dấu vân tay dữ liệu/cấu hình. Khi tự tìm lại, thời gian máy ảnh hưởng quy tắc ưu tiên tốc độ cho các cấu hình chênh dưới 0,1 điểm phần trăm MAPE. Seed 42. Chỉ chạy một lệnh huấn luyện trên máy tại một thời điểm, tối đa bốn luồng.

4. Khi các thành viên làm riêng
  python scripts/tetouan.py observations
  python scripts/tetouan.py samples
  python scripts/tetouan.py split
  python scripts/tetouan.py train
  python scripts/tetouan.py score

A tạo bảng quan sát. B tạo mẫu và danh sách cột. D chia tập rồi C huấn luyện cả hai biến thể Ridge và các mô hình so sánh. D chấm điểm và tạo đối chứng. Các lệnh split và train dùng cùng bộ chia. Sau train, score tạo bảng chấm. full tự thực hiện cả huấn luyện, chấm và kiểm chứng dự báo lại. Xem docs/PHIEU_GIAO_VIEC.md.

5. Dự báo từ mô hình đã lưu, demo và lập lại báo cáo
  python scripts/tetouan.py predict --origin "2017-12-01 12:00"
  python scripts/tetouan.py demo --origin "2017-12-01 12:00"
  python scripts/tetouan_report.py
  python -m pip install reportlab==4.4.9
  python scripts/tetouan_pdf.py

Demo dùng mô hình đã chọn theo kiểm định. Mở demo.png trong thư mục lần chạy để xem 24 dự báo cùng tải thực đo sau thời điểm phát hành. Ghi bảng vào forecast.csv. Có thể chọn --model ridge, svr, random_forest hoặc ridge_no_weather. Dùng giờ tròn trên đoạn kiểm thử có đủ lịch sử, sau thời điểm học. Để xuất lại toàn bộ báo cáo, chạy prepare, full rồi demo với giờ ví dụ trước khi chạy hai lệnh xuất báo cáo. Font PDF lấy từ Windows Arial hoặc đặt biến môi trường TETOUAN_FONT_DIR trỏ tới thư mục chứa DejaVuSans.ttf và DejaVuSans-Bold.ttf.

6. Kiểm tra
  python -m pytest -q tests/test_tetouan_data.py tests/test_tetouan_models.py tests/test_tetouan_eval.py

Dữ liệu của Salam & El Hibaoui, UCI ID 849, DOI 10.24432/C5B034, giấy phép CC BY 4.0. Mã dùng pandas, NumPy, scikit-learn và các thư viện ghi trong requirements.txt. Phần kế thừa và công cụ hỗ trợ được nêu trong PDF. Thông tin thành viên và đóng góp cá nhân do nhóm điền.
