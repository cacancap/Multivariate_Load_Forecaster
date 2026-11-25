# Phân công và bàn giao • Tetouan Zone 1

Chạy các lệnh tại thư mục dự án. Mỗi giờ phát hành có 24 hàng mẫu. Ví dụ, lúc 12:00 chương trình dùng tải đã có đến 12:00 và thời tiết đo muộn nhất lúc 11:00. Nhãn bước 1 là số đo Zone 1 lúc 13:00.

| Người | Lệnh thực tế | Đầu vào → đầu ra | Ai dùng tiếp |
|---|---|---|---|
| A · dữ liệu | `python scripts/tetouan.py observations` | ZIP UCI → bảng quan sát và kiểm toán tại `data/tetouan/observations.parquet`, `audit.json` | B đọc số đo, D kiểm tra các khoảng thời gian |
| B · đặc trưng | `python scripts/tetouan.py samples` | Bảng quan sát → `data/tetouan/samples.parquet` và `features.json` gồm danh sách cơ sở và cột thời tiết bổ sung | C nhận một bảng mẫu. Sau khi D chấm, B giải thích tác động của thời tiết |
| C · mô hình | `python scripts/tetouan.py train` | Mẫu của B, khoảng chia của D → `predictions.parquet`, `selection.json`, `models/`. C chạy cả hai cấu hình Ridge | D chấm từng hàng. E dùng mô hình đã lưu |
| D · đánh giá | Trước khi C học, `python scripts/tetouan.py split`. Sau khi C chạy, `python scripts/tetouan.py score` | Lưới giờ → `data/tetouan/splits.json`. Bảng dự báo → `scores.csv`, `weather_ablation.csv`, `all_predictions.parquet` gồm hai đối chứng | C dùng quy tắc chia đã chốt. B, D diễn giải kết quả. E đọc bảng điểm |
| E · tích hợp | `python scripts/tetouan.py smoke` để nối thử. `python scripts/tetouan.py demo` để trình diễn | Mô hình đã lưu → bảng và biểu đồ dự báo 24 giờ. Tích hợp hướng dẫn, PDF và ZIP | Cả nhóm dùng khi bảo vệ |

Đầu ra huấn luyện, chấm và demo nằm trong lần chạy được ghi tại `outputs/tetouan/full/latest.txt`. Muốn chạy liền các bước C và D dùng `python scripts/tetouan.py full`. Chạy duy nhất một lệnh huấn luyện tại một thời điểm.

Thành viên A ______ · B ______ · C ______ · D ______ · E ______. Đóng góp cá nhân thực tế ______.
