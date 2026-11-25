# Phiếu phân công nhóm IT3190 · Dự báo phụ tải 24 giờ tại Tetouan

**Dùng trong buổi giao việc.** Điền tên và ngày bắt đầu. Mốc “ngày 7” tính từ ngày đầu của nhóm. Đây là kế hoạch ba tuần để các thành viên triển khai, kiểm tra và giải thích được phần việc của mình. Nhánh `complete-experiment` chứa bản chạy tham khảo. Nhóm bắt đầu từ `main` có thể dùng riêng phiếu này. Các lệnh ở cuối tài liệu thuộc bản tham khảo.

Ngày bắt đầu ______ · Hạn nộp ______ · A ______ · B ______ · C ______ · D ______ · E ______

## 1. Cả nhóm đang giải quyết bài toán gì?

Lúc **12:00 hôm nay**, hãy ước lượng phụ tải tại **13:00, 14:00, …, 12:00 ngày mai**. Kết quả là 24 số. Mỗi số được đối chiếu với số đo thật tại đúng giờ tương ứng. Dữ liệu Tetouan gốc cách nhau 10 phút, nên 13:00 cách 12:00 sáu khoảng đo. Nhóm dự báo giá trị ghi tại giờ đích theo đơn vị gốc. Giả định tải lúc phát hành đã có, thời tiết quan sát đến chậm một giờ.

**Zone 1** là thực nghiệm chính. Sau khi nối được toàn bộ quy trình, lặp lại với **Zone 2 và Zone 3**, huấn luyện riêng và giữ cùng cách chia thời gian. Hai câu hỏi để bảo vệ là mô hình có vượt được cách lấy tải cùng giờ hôm trước hoặc tuần trước trên cả 24 giờ hay không, và mô hình dự báo thiếu bao nhiêu tại những giờ nhu cầu tăng mạnh. Khảo sát dữ liệu thành phố Việt Nam là một đầu ra độc lập của A.

## 2. Ai làm gì và giao cho ai?

| Người | Đầu ra mình chịu trách nhiệm | Người dùng tiếp | Mốc đầu tiên |
|---|---|---|---|
| A · Dữ liệu và khai phá | Bảng quan sát sạch, từ điển cột, ba biểu đồ có nhận xét, bảng khảo sát nguồn Việt Nam | B tạo đặc trưng, D đối chiếu số đo và thời gian | Mẫu thật ngày 2, bảng sạch ngày 5 |
| B · Tạo mẫu | Một bảng mẫu với hai danh sách đặc trưng có/không thời tiết, hàm tạo đầu vào tại một giờ phát hành | C huấn luyện, D kiểm tra nhãn, E dùng khi demo | Ví dụ 12:00 ngày 2, đủ 24 bước ngày 6 |
| C · Huấn luyện | Chương trình chạy mô hình, dự báo từng hàng, bộ mô hình đã lưu | D chấm, E nạp lại để demo | Ridge trên dữ liệu mẫu ngày 3, dữ liệu thật ngày 7 |
| D · Kiểm định | Khoảng chia tập, đối chứng, chương trình chấm và bảng sai số | C dùng khoảng chia trước khi học, B/E đọc bảng điểm sau khi chạy | Quy tắc chia ngày 2, bảng điểm đầu tiên ngày 7 |
| E · Tích hợp và trưởng nhóm | Luồng chạy chung, biểu đồ 24 giờ, demo, hướng dẫn và gói nộp | Cả nhóm chạy lại và bảo vệ | Biểu đồ từ mẫu ngày 3, chạy tích hợp ngày 7 |

### A · Chuẩn bị dữ liệu và tìm hiểu quy luật phụ tải

1. Tải [bộ UCI Tetouan](https://doi.org/10.24432/C5B034), giữ tệp gốc, ghi nguồn và mã kiểm tra. Xác minh tên cột cho ba vùng, tần suất, khoảng ngày, số mốc thiếu/trùng, giá trị bất thường, đơn vị nào đã biết và giả định nào còn mở.
2. Giao B bảng số đo có thời gian, ba cột tải và các cột thời tiết. Giao D danh sách giờ hợp lệ, quy tắc xử lý dòng lỗi và một ví dụ tra ngược về dòng gốc. Giữ riêng nhãn thiếu để D loại khỏi phép chấm.
3. Trên **phần phát triển do D xác định**, vẽ ba hình: đường tải điển hình theo giờ của ba vùng; đường tải ngày thường và cuối tuần; mức tải theo nhiệt độ ở cùng khung giờ. Ghi trên mỗi hình phạm vi dữ liệu, một nhận xét và một giả thuyết B/D có thể kiểm tra. Đưa thêm một cửa sổ 24 giờ có tải tăng nhanh để minh họa.
4. Khảo sát Hà Nội trước, sau đó thêm một địa phương khác, chẳng hạn TP.HCM, nếu còn thời gian. Mỗi nguồn ghi đường dẫn hoặc đầu mối, phạm vi đo (hộ/trạm/toàn thành phố), phụ tải hay thời tiết, đơn vị, tần suất, khoảng ngày, điều kiện truy cập và trạng thái đã đọc được tệp hay mới thấy mô tả. Nếu có cả hai tệp, ghép thử một tuần và báo số giờ trùng. Ghi rõ phần thiếu nếu mới có thời tiết hoặc sản lượng theo ngày.

**Hoàn thành khi** B đọc được bảng và tra đúng một hàng, D tái kiểm tra được giờ đích, nhóm có thể dùng ba hình để giải thích lựa chọn đặc trưng. Giao khai phá cuối tuần 1, bảng nguồn Việt Nam cuối tuần 2. Giới hạn khảo sát nguồn trong khoảng một buổi làm việc đầu tiên rồi báo kết quả, để tuần 1 vẫn kịp bàn giao Tetouan.

### B · Chuyển số đo thành bài toán học máy

1. Ngày 1–2 dùng bảng nhỏ để tạo mẫu. Khóa của một dự báo gồm vùng, giờ phát hành, giờ đích và bước dự báo. Với mỗi vùng, nhãn là tải thực của chính vùng đó ở giờ đích.
2. Tạo các cột đầu vào từ phụ tải hiện tại, lịch sử giờ/ngày/tuần, trung bình và cực đại của 24 giờ đã qua, lịch và thời tiết quá khứ. Bàn giao tên, thứ tự, ý nghĩa từng cột cùng hai danh sách cột dùng cho thí nghiệm thời tiết. Cả hai cấu hình phải dùng cùng các hàng đủ điều kiện.
3. Dùng cùng quy tắc tạo đặc trưng khi học và khi E gọi dự báo. Thử thay số đo tải, thời tiết sau 12:00 và quan sát thời tiết chưa có tại 12:00. Đầu vào của lần phát hành 12:00 phải giữ nguyên.

**Hoàn thành khi** C nhận được một lần phát hành đủ 24 bước, D kiểm tra được nhãn bằng dữ liệu của A. Sau khi D trả bảng điểm, B viết nhận xét việc thêm thời tiết giúp hay làm tăng sai số ở vùng nào. **C là người chạy hai cấu hình**.

### C · Xây mô hình và tạo dự báo

1. Bắt đầu từ các hàng mẫu của B và ranh giới thời gian của D. Cho Ridge học trên phần train, trả 24 giá trị cho một lần phát hành. Sau đó bổ sung Random Forest và SVR, mỗi thuật toán có một mô hình riêng cho từng bước. Fit các bước chuẩn hóa bằng dữ liệu train.
2. Chạy trên các lượt kiểm định do D giao, ghi tham số, thời gian và RAM. Chạy hai lần Ridge với cùng tham số, thời gian, nhãn và hàng hợp lệ, chỉ đổi danh sách cột B cung cấp. C trao D **dự báo từng hàng** kèm vùng, mô hình, bộ đặc trưng, lượt kiểm định và khóa thời gian.
3. Khi D chốt lựa chọn bằng kết quả kiểm định, C dùng cấu hình đó để huấn luyện lại và xuất dự báo kiểm thử cuối. Giao E mô hình đã lưu, thứ tự đặc trưng và ví dụ nạp lại để dự báo. Khi mở rộng vùng, đổi nhãn và toàn bộ đặc trưng tải trễ sang đúng vùng, huấn luyện riêng và ghi rõ cấu hình dùng chung để so sánh.

**Hoàn thành khi** D ghép được từng dự báo với đúng một nhãn, E nạp mô hình và tái tạo đủ 24 giá trị. C chịu trách nhiệm sửa lỗi huấn luyện, dự báo và lưu/nạp.

### D · Thiết kế phép thử và đo sai số

1. Giao C cách chia 80% đầu để phát triển, 20% cuối để kiểm thử, ba lượt kiểm định mở rộng, mỗi lượt 28 ngày. Chia theo lưới giờ trước khi lọc mẫu, chừa ít nhất 24 giờ và kiểm tra ngày của nhãn train cuối cùng nằm trước giờ phát hành đầu tiên của phần chấm.
2. Viết hai đối chứng lấy tải cùng giờ đích hôm trước và tuần trước. Viết hàm chấm độc lập từ bảng dự báo. Thử bằng một hàng tính tay, chẳng hạn thực đo 100 và dự báo 90 cho sai số tuyệt đối 10, sai số phần trăm 10%.
3. So mô hình trên cùng các cửa sổ đủ 24 giờ. Báo MAE, RMSE, MAPE, số cửa sổ và độ phủ. Tách kết quả từng bước để thấy giờ thứ 1 và giờ thứ 24 khác nhau thế nào. Dùng validation để chốt cấu hình với C rồi mới mở test.
4. Chấm **hồi quy tại giờ quan trọng**. Trong mỗi cửa sổ, tìm giờ có tải thực cao nhất (nếu hòa, lấy giờ sớm nhất) rồi so dự báo với số đo **ở chính giờ đó**. Với giờ tăng mạnh, chọn trước ngưỡng phân vị 95% của mức tăng dương theo giờ trên train cho từng vùng. Báo MAE theo đơn vị gốc, tỷ lệ dự báo thiếu và sai lệch trung bình có dấu (dự báo trừ thực đo). Báo cả số giờ đích phân biệt vì nhiều cửa sổ có thể cùng chứa một sự kiện.

**Hoàn thành khi** nhóm biết mô hình có vượt đối chứng trên toàn đường 24 giờ và có thường dự báo thiếu tại đỉnh hay không. D giao bảng điểm cho E, bảng so sánh thời tiết cho B và hai ví dụ có mốc giờ cụ thể cho người trình bày. D sửa phần chia tập và chấm điểm; lỗi mô hình trả về C.

### E · Tích hợp, demo và điều phối nhóm

1. Ngày 1 cùng B/C/D chốt **một ví dụ giao nhận**. E dựng trước biểu đồ bằng dữ liệu minh họa và ghi rõ trạng thái mô phỏng. Giao diện phải thể hiện vùng, giờ phát hành, đủ 24 giờ đích, đường dự báo và đường thực đo khi xem lại.
2. Cuối tuần 1, E chủ trì buổi chạy tích hợp. B tạo mẫu thật, C phát hành 24 dự báo Ridge, D chấm cùng đối chứng và E vẽ từ đúng bảng đó. Khi lỗi, E ghi một dòng gồm lỗi, chủ phần sửa và hạn sửa. E chịu trách nhiệm lỗi điều phối lệnh, hiển thị và đóng gói.
3. Tuần 2, E theo dõi hai phụ thuộc quan trọng: C đã có danh sách mẫu cùng khoảng chia từ B/D, và D đã có dự báo từng hàng từ C. Chốt quyết định ảnh hưởng toàn nhóm vào một bảng chung. Cuối tuần 3, nhờ một thành viên khác chạy lại theo hướng dẫn và đối chiếu số trên demo với bảng điểm D giao.
4. Mỗi người viết phần phương pháp, kiểm tra, kết quả và hạn chế của mình. E biên tập thành PDF đủ bảy nội dung học phần, kiểm tra trích dẫn, tạo `readme.txt`, ZIP mã nguồn và phân thời lượng để cả năm người trình bày. Ghi đóng góp thực tế khi công việc hoàn tất.

**Hoàn thành khi** một bạn khác chạy được demo từ hướng dẫn, truy được một số liệu từ PDF về bảng điểm và tái hiện được ví dụ 24 giờ. Với trưởng nhóm nhận E, đây là sản phẩm kỹ thuật cá nhân bên cạnh việc điều phối.

## 3. Lịch ba tuần và cách tránh chờ nhau

| Khi nào | Kết quả cả nhóm cần nhìn thấy | Nếu bị chặn |
|---|---|---|
| Ngày 1–2 | A đưa vài dòng thật; B/C/D/E thống nhất ví dụ 12:00 → 13:00 đến 12:00 hôm sau và định dạng bảng | C thử với ma trận số, D chấm bảng tính tay, E vẽ từ dự báo mẫu ngay khi định dạng đã rõ |
| Ngày 7 | Một lần phát hành thật đủ 24 bước ở Zone 1, có Ridge và đối chứng, đồ thị và điểm số | E xác định bước lỗi, chủ phần sửa. Ưu tiên nối xong luồng Zone 1 trước lượt huấn luyện lớn |
| Ngày 8–14 | C chạy các mô hình và cặp cấu hình thời tiết; D chấm validation; A/B giải thích theo dữ liệu; chốt cấu hình trước test | Nếu hai mô hình có số hàng khác nhau, B/C đối chiếu khóa, D công bố tập so sánh và độ phủ |
| Ngày 15–21 | Chấm test, so sánh ba vùng và các giờ quan trọng, hoàn thiện demo, PDF, ZIP và tập bảo vệ | D ghi rõ nhóm/sự kiện ít mẫu. E chỉ hiển thị kết quả truy được về lần chạy thực tế |

**Ví dụ luồng C–D:** C dự báo 200 cho 13:00. D lấy nhãn 220 từ bảng B, kiểm tra cùng thời điểm rồi tính sai số tuyệt đối 20. Nếu 13:00 là đỉnh thực của cửa sổ, D cũng ghi mức dự báo thiếu 20 ở đỉnh. E dùng chính hàng đó để giải thích trên biểu đồ.

## 4. Tra cứu khi thực hành trên nhánh complete-experiment

Các lệnh dưới đây chạy từ thư mục gốc của bản tham khảo Zone 1. Chế độ `smoke` thử một bước. Để kiểm tra đầu ra 24 bước, dùng mô hình từ lượt `full` và xem 24 hàng của cùng một lần phát hành. Xem [nguồn dữ liệu](NGUON_DU_LIEU.md) và [ví dụ về các bảng](HOP_DONG_BAN_GIAO.md).

| Người |Lệnh thực tế | Đầu vào → đầu ra | Ai dùng tiếp |
|---|---|---|---|
| A · dữ liệu | `python scripts/tetouan.py observations` | ZIP UCI → bảng quan sát và kiểm toán tại `data/tetouan/observations.parquet`, `audit.json` | B đọc số đo, D kiểm tra các khoảng thời gian |
| B · đặc trưng | `python scripts/tetouan.py samples` | Bảng quan sát → `data/tetouan/samples.parquet` và `features.json` gồm danh sách cơ sở và cột thời tiết bổ sung | C nhận một bảng mẫu. Sau khi D chấm, B giải thích tác động của thời tiết |
| C · mô hình | `python scripts/tetouan.py train` | Mẫu của B, khoảng chia của D → `predictions.parquet`, `selection.json`, `models/`. C chạy cả hai cấu hình Ridge | D chấm từng hàng. E dùng mô hình đã lưu |
| D · đánh giá | Trước khi C học, `python scripts/tetouan.py split`. Sau khi C chạy, `python scripts/tetouan.py score` | Lưới giờ → `data/tetouan/splits.json`. Bảng dự báo → `scores.csv`, `weather_ablation.csv`, `all_predictions.parquet` gồm hai đối chứng | C dùng quy tắc chia đã chốt. B, D diễn giải kết quả. E đọc bảng điểm |
| E · tích hợp | `python scripts/tetouan.py smoke` để nối thử. `python scripts/tetouan.py demo` để trình diễn | Mô hình đã lưu → bảng và biểu đồ dự báo 24 giờ. Tích hợp hướng dẫn, PDF và ZIP | Cả nhóm dùng khi bảo vệ |

Đầu ra huấn luyện, chấm và demo nằm trong lần chạy được ghi tại `outputs/tetouan/full/latest.txt`. Muốn chạy liền các bước C và D dùng `python scripts/tetouan.py full`. Chạy duy nhất một lệnh huấn luyện tại một thời điểm.

Bản nộp gồm ZIP mã nguồn, readme.txt và PDF đủ bảy nội dung học phần. Cả năm người trực tiếp trình bày trong khoảng 15 phút. Chỉ đưa kết quả Zone 2–3 và các giờ tăng mạnh vào bản nộp khi đã có đầu ra tái lập được.
