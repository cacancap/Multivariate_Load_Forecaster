# Phiếu giao việc A–E

Đọc phần mở đầu của [kế hoạch nhóm](KE_HOACH_NHOM_5_NGUOI.md), rồi tìm vai trò của mình bên dưới. Mỗi phiếu có việc có thể bắt đầu ngay, ví dụ đầu ra và người cần liên hệ. Các ví dụ dùng chung số liệu mô phỏng trong [hợp đồng bàn giao](HOP_DONG_BAN_GIAO.md). Điền tên người phụ trách trong buổi khởi động.

## A — Dữ liệu phụ tải và thời tiết

**Thành viên:** … · **Ngân sách:** 28–30 giờ · **Kiểm tra chéo:** B; D xác nhận quy tắc thời gian.

### Mục tiêu

Cung cấp dữ liệu đáng tin và giải thích được ý nghĩa mỗi dòng. Phần của A quyết định việc ghép thời tiết có hợp lệ và dữ liệu nào thực sự có thể dùng để dự báo.

### Việc đầu tiên

Đọc tệp PJME và Tetouan, ghi lại tần suất, đơn vị và cách gắn giờ. Lấy vài dòng để B thử đọc.

### Nhận từ ai

- Tệp phụ tải PJME, nguồn thời tiết quan sát cần khảo sát và bộ Tetouan dự phòng. [Danh mục nguồn dữ liệu và link tải](NGUON_DU_LIEU.md)
- Quy ước bảng quan sát và metadata từ D ở ngày 1–2.
- Yêu cầu đặc trưng tối thiểu của B: phụ tải, ít nhất nhiệt độ, timestamp, thời điểm có sẵn và cờ chất lượng.

### Công việc theo tuần

| Tuần | Việc thực hiện | Bằng chứng bàn giao |
|---|---|---|
| 1 | Thử tải hai hướng; kiểm tra nguồn, đơn vị, khoảng đo và thời gian; quyết định nguồn ngày 3; xử lý thiếu/trùng/DST; lưu nguyên bản và snapshot | Biên bản nguồn, bộ tải, manifest/checksum, bảng quan sát chuẩn, thống kê chất lượng |
| 2 | Kiểm tra độ phủ và độ trễ thời tiết; hỗ trợ B/D xác định giờ hợp lệ; giải thích các vùng lỗi có nguyên nhân từ dữ liệu | Bảng độ phủ theo tháng, danh sách trường hợp cách ly, kết quả kiểm tra độ trễ |
| 3 | Viết phần dữ liệu/khó khăn, kiểm tra dữ liệu bản nộp và tập trình bày | Phần báo cáo, nguồn trích dẫn, sơ đồ dữ liệu, phần slide cá nhân |

### Ví dụ đầu ra lúc 12:00

Dòng nhiệt độ 11:00 có giá trị 25 °C và thời điểm có thể dùng là 12:00. B đọc được dòng này, D kiểm tra được giả định độ trễ.

### Giao cho ai và khi nào

Cuối ngày 3, giao biên bản nguồn cho B và D. Ngày 7, giao bảng quan sát, mô tả nguồn và báo cáo chất lượng cho B và D, cùng bộ tải và hướng dẫn lấy lại bản dữ liệu cho E.

### Trao đổi khi gặp vướng mắc

Khi giờ đo hoặc đơn vị chưa rõ, đưa dòng gốc và bằng chứng nguồn cho D xác nhận. Báo B ngay nếu cách đọc giờ hay tên cột thay đổi.

### Kiểm tra trước khi giao

- [ ] Dữ liệu gốc giữ nguyên; mỗi nguồn có URL, thời điểm lấy, checksum và mô tả đơn vị/tần suất.
- [ ] Có bảng chuẩn theo hợp đồng, giữ dấu vết dòng nguồn và quy tắc xử lý.
- [ ] Tách ô trống, thiếu timestamp, giờ lặp, lỗi giá trị và thời gian mơ hồ; không xóa tải cao chỉ vì lớn.
- [ ] Không nội suy nhãn để chấm điểm; mọi phương pháp điền đầu vào có hướng thời gian và giới hạn rõ.
- [ ] Có ít nhất nhiệt độ quan sát thật, metadata độ trễ và tỷ lệ thiếu; không thay toàn bộ thời tiết bằng số giả/giá trị điền rồi coi là đã tích hợp.
- [ ] PJME chỉ ghép khác nguồn khi đủ bằng chứng thời gian. Nếu không đạt G1, đã bàn giao nguồn Tetouan cho các phần còn lại.
- [ ] Có ví dụ giờ bình thường, giờ thiếu/trùng và trường hợp thời tiết chưa sẵn có tại T.

**Phần báo cáo/bảo vệ:** giới thiệu, nguồn/đặc điểm dữ liệu, khó khăn thời gian và cách xử lý; khoảng 2,5 phút.

## B — Đặc trưng và tạo mẫu dự báo

**Thành viên:** … · **Ngân sách:** 24–28 giờ · **Kiểm tra chéo:** A về ý nghĩa dữ liệu; D về tính nhân quả.

### Mục tiêu

Tạo đầu vào và nhãn cho từng bước dự báo (horizon). Mỗi hàng đầu vào chỉ chứa thông tin có sẵn lúc phát hành. Dùng cùng một cách tạo đầu vào khi huấn luyện và khi dự báo.

### Việc đầu tiên

Lấy bảng quan sát mẫu và tạo một hàng cho lần phát hành 12:00, trước hết ở bước 1.

### Nhận từ ai

- Dữ liệu mẫu và hợp đồng từ D; sau ngày 3 nhận snapshot/metadata của A.
- Danh sách horizon 1–24 giờ và độ trễ quan sát đã thống nhất.
- Giao diện mô hình từ C: nhận X số và y; phần chuẩn hóa học từ dữ liệu do C đặt trong pipeline.

### Công việc theo tuần

| Tuần | Việc thực hiện | Bằng chứng bàn giao |
|---|---|---|
| 1 | Viết bộ tạo mẫu bằng dữ liệu giả lập; lag/rolling/lịch/Fourier/thời tiết quá khứ; tạo nhãn và đầu vào suy luận; nối snapshot thật | X/y và sample index cho 24 horizon, từ điển đặc trưng, kiểm tra nhân quả |
| 2 | So sánh nhóm đặc trưng trên validation bằng mô hình của C; giữ cùng tập mẫu khi bỏ/thêm thời tiết | Bảng ablation, cấu hình, số mẫu và giải thích tác động |
| 3 | Phân tích lỗi theo horizon, viết phần đặc trưng/kiến trúc/khó khăn và tập trình bày | Ví dụ một mẫu tại T, công thức, biểu đồ và phần slide |

### Ví dụ đầu ra lúc 12:00

Hàng dự báo 13:00 nhận 25 °C đo lúc 11:00. Phụ tải thật 220 ở 13:00 nằm trong nhãn để học hoặc chấm, tách khỏi các cột mô hình nhận lúc dự báo.

### Giao cho ai và khi nào

Ngày 7, giao bộ mẫu và danh sách cột cho C và D, giao công cụ tạo đầu vào dự báo cho E. Đến ngày 12, giao kết quả so sánh có và không có thời tiết cho D.

### Trao đổi khi gặp vướng mắc

Nếu chưa rõ số đo có sẵn khi nào, hỏi A bằng một dòng cụ thể. Nếu hai lần chạy có tập giờ khác nhau, kiểm tra danh sách mẫu với D.

### Kiểm tra trước khi giao

- [ ] Có thao tác tạo mẫu huấn luyện và tạo đầu vào dự báo tại một origin, dùng chung logic đặc trưng.
- [ ] Mỗi hàng có origin, target, horizon và danh sách đặc trưng; loại rõ trường hợp không đủ lịch sử.
- [ ] Thay đổi phụ tải và thời tiết sau T không làm thay đổi X tại T.
- [ ] Nhãn đúng giờ đích; không đưa phụ tải đích, thời tiết tương lai hay cột phụ tải vùng khác tại giờ đích vào X.
- [ ] Lag/rolling chỉ lấy từ những quan sát đã sẵn có; xử lý đúng tần suất nguồn 10/60 phút.
- [ ] X chưa được chuẩn hóa bằng thống kê toàn bộ dữ liệu; các bước có học tham số phải fit bên trong train.
- [ ] Có từ điển đặc trưng ghi công thức, đơn vị, dữ liệu nguồn và thời điểm sẵn có muộn nhất.
- [ ] So sánh có/không thời tiết dùng cùng origin/target; có bảng độ phủ và ablation trên validation.

**Phần báo cáo/bảo vệ:** kỹ nghệ đặc trưng, tạo nhãn nhiều bước, chống rò rỉ và phần kiến trúc của mình; khoảng 2,5 phút.

## C — Thuật toán và tối ưu mô hình

**Thành viên:** … · **Ngân sách:** 26–30 giờ · **Kiểm tra chéo:** D.

### Mục tiêu

Xây dựng ba mô hình để D có thể gọi huấn luyện và dự báo theo cùng một cách. SVR là phương pháp trọng tâm. Ridge cho một mô hình tuyến tính dễ đối chiếu, còn Random Forest (RF) học bằng cách kết hợp nhiều cây quyết định.

### Việc đầu tiên

Dùng ma trận số mẫu để thử huấn luyện, dự báo và nạp lại một mô hình cho bước 1.

### Nhận từ ai

- Bảng đặc trưng X và nhãn y từ bộ mẫu của D, sau đó từ dữ liệu thật do B chuẩn bị.
- Cách chia tập, chỉ số và danh sách thí nghiệm do D thống nhất. Mỗi fold là một lượt học trên một đoạn lịch sử rồi chấm trên đoạn thời gian tiếp theo.
- Metadata đơn vị và cột của từng bộ dữ liệu.

### Công việc theo tuần

| Tuần | Việc thực hiện | Bằng chứng bàn giao |
|---|---|---|
| 1 | Viết lớp/giao diện cho Ridge, SVR, RF; chuẩn hóa X/y phù hợp; lưu/nạp; chạy trên ma trận mẫu rồi nối thật | Ba mô hình hoạt động, schema cột, kiểm tra lưu/nạp |
| 2 | Tập trung SVR: C/epsilon/gamma; bàn giao cấu hình Ridge/RF để D chạy song song; giải thích kết quả tham số | Config trước chạy, nhật ký validation, bảng tham số và thời gian |
| 3 | Hỗ trợ mô hình chốt cho kiểm thử, phân tích khác biệt thuật toán; viết lý thuyết và tập bảo vệ | Mô hình được chọn, phần phương pháp, bảng kết quả và slide |

### Ví dụ đầu ra lúc 12:00

Mô hình SVR nhận các cột của B ở lần phát hành 12:00 và trả dự báo 200 cho 13:00, theo đơn vị tải gốc của mẫu.

### Giao cho ai và khi nào

Ngày 7, giao bộ mô hình cho D và hướng dẫn nạp cho E. Trước khi chạy thử ở tuần 2, giao danh sách cấu hình cho D. Khi đã chốt cấu hình ngày 12, phối hợp giao mô hình đã lưu cho E sau lượt huấn luyện và kiểm thử ngày 15.

### Trao đổi khi gặp vướng mắc

Nếu sai thứ tự cột, đối chiếu danh sách với B. Nếu chưa có cách chia tập hoặc chưa rõ cách so sánh tham số, thống nhất với D trước khi chạy.

### Kiểm tra trước khi giao

- [ ] Ridge/SVR/RF cùng giao diện fit/predict/lưu/nạp; dự báo trả đúng số hàng và thứ tự.
- [ ] X scaler chỉ fit trên train; SVR có xử lý thang đo y và chuyển dự báo về đơn vị gốc.
- [ ] Mỗi horizon có mô hình riêng; không đưa giá trị thật trong khoảng dự báo vào mô hình để dự báo bước sau.
- [ ] Tắt các bước tự chia validation ngẫu nhiên khi chúng trái với thiết kế thời gian.
- [ ] Danh sách tham số được lưu trước chạy; mọi kết quả có config, seed, dữ liệu và fold tương ứng.
- [ ] Mô hình nạp lại tái tạo dự báo trong sai số số học đã ghi rõ; lưu cùng thứ tự/tên cột và đơn vị.
- [ ] Giải thích được Ridge/L2, RF, epsilon-insensitive loss, kernel RBF và tác động C/epsilon/gamma.
- [ ] Nếu giới hạn cửa sổ huấn luyện SVR vì tài nguyên, ghi rõ và có so sánh Ridge/RF trên cửa sổ tương ứng.

**Phần báo cáo/bảo vệ:** lý thuyết các mô hình, thử tham số và phần kiến trúc của mình; khoảng 2,5 phút.

## D — Thiết kế kiểm định và phân tích thực nghiệm

**Thành viên:** … · **Ngân sách:** 28–30 giờ · **Kiểm tra chéo:** C về phép tính/mô hình; A/B về thời gian.

### Mục tiêu

**“Các kết quả có được đo đúng và đủ để kết luận mô hình hữu ích không?”** D xây chương trình đánh giá, thiết kế phép so sánh và lập luận từ kết quả. Đây là phần lập trình và nghiên cứu độc lập.

| Phần | Người sở hữu | D phối hợp như thế nào? |
|---|---|---|
| Nguồn, timestamp, đơn vị và làm sạch | A | Kiểm tra quyết định có phù hợp kịch bản dự báo và ranh giới train/test |
| Đặc trưng và nhãn | B | Đưa ca kiểm tra để xác minh thông tin sẵn có tại T và vị trí nhãn |
| Mô hình và scaler trong pipeline | C | Cung cấp fold, gọi fit/predict và kiểm tra dùng cùng mẫu |
| Chia tập, chỉ số, lựa chọn và phân tích | **D** | Trực tiếp viết và chịu trách nhiệm |
| Lệnh chạy/giao diện/bản phát hành | E | Bàn giao schema, kết quả thật và ý nghĩa chỉ số để hiển thị |

### Việc đầu tiên

Lấy bảng dự báo mẫu để tính tay sai số. Sau đó viết hàm chấm và thử chia các đoạn thời gian để mô hình học bằng dữ liệu cũ rồi được chấm trên dữ liệu mới hơn.

### Nhận từ ai

- Yêu cầu bài toán và dữ liệu nguồn; ý kiến A/B về khả năng sẵn có của dữ liệu.
- Bộ mẫu từ B và bộ mô hình từ C. D dùng hai đầu ra này để chạy cùng một phép đánh giá cho nhiều mô hình.
- Nguồn tham khảo hiện có để xác định rủi ro; kết quả cũ không được thay cho kết quả bản nhóm.

### Công việc theo tuần

| Tuần | Việc trực tiếp thực hiện | Đầu ra |
|---|---|---|
| 1 | Chốt hợp đồng và bộ mẫu; quy định origin/target; chia train/validation/test; viết chỉ số và đối chứng; kiểm tra G1/G2 | Schema, fixtures, fold manifest, hàm đánh giá, ca kiểm tra chống rò rỉ |
| 2 | Lập danh sách thử nghiệm; chạy đối chứng/Ridge/RF; nhận SVR/ablation; so sánh trên cùng mẫu; chọn cấu hình và ensemble bằng validation | Trial manifest, bảng CV, biểu đồ, bản khóa lựa chọn trước test |
| 3 | Chạy kiểm thử cuối, phân tích lỗi theo horizon/mùa/tải cao; diễn giải lợi ích và giới hạn | Bảng kiểm thử, confusion matrix tải cao, sai lệch đỉnh, kết luận và phần slide |

### Ví dụ một đầu việc trọn vẹn của D

Giả sử C đưa SVR có MAPE 3% và RF có MAPE 4%. D thực hiện:

1. Xác định hai con số là validation hay test; cùng horizon và cùng đơn vị phần trăm hay không.
2. So khớp danh sách `(origin_time, target_time, horizon)` và nhãn; đưa cả hai về cùng tập mẫu hợp lệ.
3. Kiểm tra các lần fit đã dùng đúng train; scaler không học từ validation/test; weather không lấy từ tương lai.
4. Tính lại MAPE/RMSE từ dự báo từng hàng; tách h=1, h=6, h=12, h=24 và chỉ số gộp.
5. Đánh giá tải cao: mô hình nào bỏ sót nhiều, báo nhầm nhiều, dự báo thấp đỉnh hoặc lệch giờ đỉnh.
6. Dùng kết quả validation để lưu lựa chọn. Sau đó mới chấm tập kiểm thử cuối và trình bày cả kết quả tốt lẫn chưa đạt.

### Phần chương trình D cần viết

- Bộ chia thời gian, sinh fold trên lưới origin đầy đủ trước khi lọc mẫu.
- Hàm MAE, RMSE, MAPE; chỉ số nhận diện tải cao và sai số đỉnh.
- Các dự báo đối chứng dùng dữ liệu quá khứ.
- Vòng lặp nhận mô hình C và mẫu B, fit trên train, dự báo validation/test, lưu dự báo từng hàng.
- Bộ tổng hợp bảng/biểu đồ và metadata của lần chạy; thao tác khóa/lưu lựa chọn trước kiểm thử.

### Ví dụ đầu ra lúc 12:00

SVR dự báo 200 cho số đo thật 220 ở 13:00, sai tuyệt đối 20. So với đối chứng ngày trước dự báo 190, sai tuyệt đối 30, SVR tốt hơn ở hàng này. D dùng nhiều ngày để kiểm tra kết quả có lặp lại hay không.

### Giao cho ai và khi nào

Ngày 7, giao cách chia tập cho C trước đợt thử cấu hình và bảng từ lượt chạy thử cho E. Ngày 12, giao bảng validation và cấu hình đã khóa cho E. Ngày 15, giao bảng kiểm thử cuối và định nghĩa chỉ số cho E.

### Trao đổi khi gặp vướng mắc

Nếu các mô hình thiếu những giờ khác nhau, yêu cầu B kiểm tra danh sách mẫu và C kiểm tra dự báo. E xác nhận với D rằng có thể đọc bảng và đối chiếu số liệu hiển thị.

### Kiểm tra trước khi giao

- [ ] Có sơ đồ chia dữ liệu và fold manifest với mốc thời gian cụ thể.
- [ ] Nhãn huấn luyện đã được quan sát trước origin validation; gap bao phủ horizon lớn nhất.
- [ ] Chấm đúng trên một bộ số nhỏ có kết quả tính tay; thống nhất MAPE theo đơn vị %.
- [ ] So sánh trên cùng mẫu, phát hiện được nhãn lệch, khóa trùng hoặc thiếu dự báo.
- [ ] Lưu riêng điểm gộp và điểm từng horizon; không dùng điểm h=1 làm đại diện cho dự báo 24 giờ.
- [ ] Ngưỡng tải cao lấy từ train; confusion matrix có định nghĩa positive/negative, Precision/Recall/F1 và số mẫu.
- [ ] Có đối chứng và thí nghiệm có/không thời tiết; có độ phủ, sai số tại giờ tải cao và sai lệch giờ đỉnh.
- [ ] Cấu hình/đặc trưng/trọng số được lưu trước test; không chọn lại vì nhìn thấy kết quả test.
- [ ] Có bảng kết quả chung, phân tích nguyên nhân và kết luận đúng phạm vi bằng chứng.

**Phần báo cáo/bảo vệ:** chương kết quả thực nghiệm, phần kết luận, giới hạn và quy trình lựa chọn; khoảng 2,5 phút.

## E — Hệ thống thử nghiệm và bản nộp

**Thành viên:** … · **Ngân sách:** 24–28 giờ · **Kiểm tra chéo:** B/C về suy luận; D về hiển thị kết quả.

### Mục tiêu

Biến các mô-đun thành chương trình người khác chạy được, giúp người dùng hiểu dự báo và bảo đảm sản phẩm nộp phản ánh đúng thực nghiệm.

### Việc đầu tiên

Lấy bảng dự báo mẫu của D để dựng màn hình và thử đọc kết quả trước khi có mô hình cuối.

### Nhận từ ai

- Schema kết quả và bảng mẫu của D ngay từ ngày 1–2.
- Bộ tạo đầu vào tại T của B, mô hình/schema cột của C và snapshot của A.
- Nội dung báo cáo/slide do từng thành viên tự viết.

### Công việc theo tuần

| Tuần | Việc thực hiện | Bằng chứng bàn giao |
|---|---|---|
| 1 | Môi trường/phụ thuộc, lệnh chạy, UI từ kết quả mẫu; chuẩn bị đề cương tài liệu và danh sách trích dẫn | CLI nhỏ, màn hình mẫu có nhãn, hướng dẫn khởi tạo |
| 2 | Nối bộ thực nghiệm D; hiển thị model/horizon/độ phủ; chạy môi trường mới, kiểm tra lưu/nạp và thời gian suy luận | Giao diện với dữ liệu thật, nhật ký tái lập và bản hướng dẫn cập nhật |
| 3 | Hợp nhất báo cáo/slide, đóng gói mã, hoàn thành `readme.txt`, kiểm tra demo và tập bảo vệ | ZIP/RAR, PDF, readme, slide và bản dự phòng demo |

### Ví dụ đầu ra lúc 12:00

Màn hình ghi rõ dữ liệu mô phỏng, lần phát hành 12:00, dòng 13:00 có dự báo 200 và số đo thật 220. Bản dùng cho demo có đủ 24 giờ đích.

### Giao cho ai và khi nào

Ngày 7, giao bản chạy thử cho cả nhóm. Ngày 18, giao hướng dẫn, bản chạy trên môi trường mới và gói nộp để cả nhóm duyệt.

### Trao đổi khi gặp vướng mắc

Nếu thiếu tên mô hình, giờ đích hoặc độ phủ, đưa D một ví dụ bảng mà màn hình chưa đọc được. Trao đổi với B về cách tạo đầu vào và C về cách nạp mô hình.

### Kiểm tra trước khi giao

- [ ] Có các bước lấy/chuẩn bị dữ liệu, chạy kiểm tra nhỏ, huấn luyện/đánh giá, nạp mô hình và dự báo.
- [ ] Giao diện đọc kết quả đã xuất, hiển thị rõ nguồn dữ liệu, mô hình, horizon, thời điểm và độ phủ.
- [ ] Mặc định hiển thị lựa chọn đã chốt bằng validation; các số trên UI khớp tệp kết quả.
- [ ] Demo dùng cửa sổ có đủ 24 giờ; thông báo rõ khi thiếu lịch sử hoặc mô hình chưa hoàn tất.
- [ ] Nạp lại mô hình và dự báo tại origin kiểm tra khớp trong sai số số học; không dùng mô hình đã học sau origin để tuyên bố dự báo hồi tố.
- [ ] Đã thử theo hướng dẫn trên môi trường mới; ghi phiên bản thư viện, đường dẫn và dữ liệu/mô hình cần có.
- [ ] Có `readme.txt` bắt buộc, ZIP/RAR sạch, PDF đủ 7 nội dung; không phụ thuộc thông tin đăng nhập riêng để chạy demo.
- [ ] Các tác giả đã duyệt phần mình viết; trích dẫn và bảng đóng góp đầy đủ; demo có phương án dự phòng từ lần chạy thật.

**Phần báo cáo/bảo vệ:** chức năng, kiến trúc tổng thể, triển khai và demo; khoảng 2,5 phút. E biên tập tổng thể, từng người cung cấp nội dung và hình/bảng của mình đúng hạn.

## Mẫu nghiệm thu áp dụng cho mọi phiếu

| Trường | Nội dung điền |
|---|---|
| Phiếu/người thực hiện | … |
| Phiên bản dữ liệu, cấu hình, mã nguồn | … |
| Đầu ra và liên kết bằng chứng | … |
| Kiểm tra đã chạy và kết quả | … |
| Hạn chế/vướng mắc còn lại | … |
| Người kiểm tra chéo | … |
| Kết luận | Chưa đạt / Đạt để tích hợp / Đạt bản nộp |
| Ngày xác nhận | … |
