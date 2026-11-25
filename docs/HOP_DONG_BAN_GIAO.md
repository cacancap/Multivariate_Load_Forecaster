# Một hàng trong thực nghiệm Tetouan

Lúc 12:00 ngày 01/03/2017, nhiệt độ mới nhất được dùng là 16,86 đo lúc 11:00. Giá trị thực ở 13:00 là 34.517,10638. Đối chứng ngày trước lấy giá trị 35.188,47458 đo lúc 13:00 ngày 28/02. Sai số tuyệt đối ở hàng này là 671,36820.

| Bảng | Mỗi hàng mang ý nghĩa gì |
|---|---|
| Quan sát | Một mốc 10 phút với tải và thời tiết |
| Mẫu | `origin_time` là giờ phát hành, `target_time` là giờ đích, `horizon` là khoảng cách theo giờ. `y_true` là tải thật tại giờ đích. Các cột đầu vào chỉ dùng tải đã có và thời tiết trễ một giờ |
| Dự báo | Giữ các khóa thời gian và nhãn, thêm tập dữ liệu `split`, lượt kiểm định `fold`, tên mô hình `model` và dự báo `y_pred` |
| Điểm | Đánh giá trên cùng cặp giờ. MAE và RMSE theo đơn vị nguồn, MAPE theo phần trăm, độ phủ bằng số cặp được chấm chia số cặp dự kiến |

Người nhận và lệnh chạy cho từng bảng có trong [kế hoạch và phân công](KE_HOACH_NHOM_5_NGUOI.md).
