# Dự báo phụ tải Zone 1 trong 24 giờ

Lúc 12:00, người vận hành muốn biết nhu cầu điện từng giờ từ 13:00 hôm nay tới 12:00 ngày mai. Mô hình nhận phụ tải đến lúc phát hành, đặc trưng lịch và thời tiết đã đo ít nhất một giờ trước đó. Mỗi mô hình học cách dự báo một khoảng cách nhất định. Nhãn là số đo gốc tại đúng giờ đích. [Một hàng minh họa](HOP_DONG_BAN_GIAO.md)

Tuần 1, A chuẩn bị số đo, B tạo đầu vào, C thử mô hình trên ma trận nhỏ, D viết bộ chia thời gian và chấm bằng số tính tay, E dựng demo từ bảng mẫu. Nối thử Ridge và đối chứng trên dữ liệu thật. [Nguồn dữ liệu](NGUON_DU_LIEU.md)

Tuần 2, C chạy huấn luyện trên các khoảng D đã chia và xuất cả hai cấu hình Ridge với cùng mẫu. D so mô hình với tải cùng giờ hôm trước và tuần trước. B và D giải thích thời tiết có giúp giảm sai số hay không. Tuần 3, E tích hợp sản phẩm, cả nhóm đối chiếu số liệu và tập trình bày trong khoảng 15 phút. [Phân công và lệnh chạy](PHIEU_GIAO_VIEC.md)

Bản nộp có mã nguồn ZIP, readme.txt và báo cáo PDF bảy nội dung. Mỗi người trình bày phần mình, dẫn nguồn dữ liệu, thư viện và nêu rõ phần mã kế thừa.
