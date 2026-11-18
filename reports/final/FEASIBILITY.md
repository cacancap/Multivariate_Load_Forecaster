# Đánh giá tính khả thi và mức giải quyết vấn đề cốt lõi

**Kết luận: đề tài khả thi và có giá trị cho bài tập lớn ML. Dự báo phụ tải đã có bằng chứng cải thiện; dự báo chính xác giờ cao điểm và các đợt cực đoan trước 24 giờ mới được giải quyết một phần.**

## Bằng chứng hiện tại

- Pipeline đã chạy từ dữ liệu thật đến mô hình lưu, dự báo và dashboard; mô hình được chọn trước khi xem kiểm thử năm 2017.
- MAPE gộp các khoảng cách 1–24 giờ: 4,315%; đối chứng ngày trước 7,007%. Đây không phải MAPE riêng ở bước 24 giờ.
- Đối chiếu bổ sung với các phương án đơn giản dùng thông tin hiện có: tốt nhất đạt 6.405% MAPE; ensemble vẫn giảm khoảng 32.6% sai số tương đối. Đây là chẩn đoán bổ sung sau thực nghiệm, không dùng để chọn lại mô hình.

| Khoảng cách dự báo | MAPE (%) | MAPE tại giờ tải cao (%) | Recall giờ tải cao (%) |
|---:|---:|---:|---:|
| 1 giờ | 0.94 | 0.91 | 96.8 |
| 6 giờ | 3.38 | 3.90 | 85.2 |
| 12 giờ | 4.69 | 5.74 | 74.0 |
| 24 giờ | 5.84 | 6.88 | 69.1 |

Giờ tải cao được xác định bằng ngưỡng Q90 của train: 40,503.2 MW. Ngưỡng này không phải giới hạn chịu tải của lưới điện.
Ở bước 24 giờ có 622 giờ tải cao trong tập đánh giá: nhận diện 430 giờ, bỏ sót 192 giờ, và 163 cảnh báo nhầm. Tỷ lệ nhận diện khoảng 69,1%, precision 72,5%. Phụ tải tại những giờ tải cao bị dự báo thấp trung bình khoảng 1.824 MW.
Sai lệch thời điểm đỉnh lớn nhất trong cửa sổ dự báo 24 giờ trung bình 3,01 giờ (đối chứng ngày trước: 4,91 giờ). Sai số độ lớn đỉnh trung bình 1.630 MW (đối chứng: 2.381 MW). Đây là cải thiện, nhưng chưa chứng minh cảnh báo đỉnh chính xác theo giờ.

## Các mức kết luận

| Tiêu chí | Kết luận |
|---|---|
| Xây dựng được hệ thống ML chạy trên dữ liệu thật | Đã chứng minh trong môi trường hiện tại |
| Dự báo phụ tải có giá trị hơn các đối chứng đã thử | Đã chứng minh trên các cửa sổ hợp lệ của năm 2017 |
| Dự báo 24 giờ với MAPE dưới 3,5% | Chưa đạt; riêng bước 24 giờ là 5,84% |
| Nhận diện chính xác đỉnh trong các đợt nắng nóng/rét đậm | Chưa chứng minh đầy đủ; chưa có phân tích sự kiện thời tiết cực đoan |
| Sẵn sàng hỗ trợ quyết định điều độ thực tế | Chưa chứng minh |

## Giới hạn chi phối đánh giá

- Độ phủ khoảng 94,8–95,6%; các cửa sổ liên quan DST không rõ nghĩa đã được loại. Kết quả có điều kiện trên tập còn lại.
- Quy ước timestamp và thời điểm công bố phụ tải chưa được xác nhận đầy đủ. Chưa tái dựng các bản sửa dữ liệu theo thời điểm.
- Thời tiết đã thu thập nhưng chưa được ghép/huấn luyện vì điều kiện thời gian chưa được xác nhận; chưa có bằng chứng thực nghiệm rằng thời tiết sẽ giúp đạt 3,5%.
- Kiểm thử một năm, một vùng; chưa xác nhận khả năng tổng quát sang năm khác hoặc vùng khác.
- Toàn bộ khảo sát ghi nhận khoảng 60 phút hoạt động, RAM đỉnh khoảng 1,51 GiB; suy luận đủ 24 giờ khoảng 1,68 giây khi dữ liệu đã trong bộ nhớ. Chưa đạt các giới hạn ban đầu 500 MB và hai phút cho toàn bộ nghiên cứu.

## Khuyến nghị cho nhóm

Giữ nguyên bài toán dự báo 24 giờ và đánh giá phụ tải cao. Có đủ cơ sở để tiếp tục đề tài dưới dạng nghiên cứu thực nghiệm về kỹ nghệ đặc trưng, thuật toán và giới hạn dự báo. Chưa nên cam kết đã giải quyết cảnh báo đỉnh cực đoan hoặc an toàn lưới điện.
Ưu tiên tiếp theo: xác nhận ý nghĩa timestamp; có dữ liệu dự báo thời tiết thực sự sẵn có tại từng lần phát hành; kiểm thử trên thêm một giai đoạn độc lập và trên các sự kiện nóng/lạnh đã định nghĩa trước. Tiêu chí đỉnh cần gồm tỷ lệ bỏ sót, cảnh báo nhầm, thiên lệch dự báo thấp và độ lệch giờ đỉnh.
Giữ năm 2017 như kết quả kiểm thử đã công bố; các cải tiến tiếp theo cần tập kiểm thử độc lập mới để tránh tối ưu theo chính kết quả vừa xem.

Chi tiết: [báo cáo chính](REPORT.md), [chẩn đoán tính khả thi](feasibility_diagnostics.json), [đối chứng bổ sung](feasibility_extra_baselines.csv).
