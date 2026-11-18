# Kế hoạch nhóm 5 người · Dự báo phụ tải điện 24 giờ có thời tiết

## 1. Bài toán qua một lần dự báo lúc 12:00

**Phụ tải điện** là mức điện mà một khu vực đang cần tại một thời điểm hoặc trong một khoảng đo. Nhóm dự báo mức phụ tải để biết trước giờ nào nhu cầu có thể tăng cao.

Giả sử bây giờ là **12:00 hôm nay**. Nhóm dùng số đo phụ tải đã có, thời tiết đã có và thông tin biết trước từ lịch, chẳng hạn ngày mai là ngày làm việc hay cuối tuần. Đầu ra là **24 giá trị**, từ 13:00 hôm nay đến 12:00 ngày mai. Mỗi **bước dự báo** là số giờ từ lúc phát hành đến giờ cần dự báo. Trong ví dụ này, 13:00 là bước 1 và 12:00 ngày mai là bước 24.

- **Từ số đo đến đầu vào.** Giả sử nhiệt độ đo lúc 11:00 là 25 °C. Với giả định thời tiết đến chậm một giờ, nhóm có thể dùng 25 °C lúc 12:00. Nhiệt độ đo lúc 13:00 chỉ xuất hiện sau khi dự báo đã phát hành. Đưa giá trị đó vào đầu vào là **rò rỉ dữ liệu**, tức cho mô hình dùng thông tin chưa có tại thời điểm cần đưa ra dự báo.
- **Từ đầu vào đến dự báo.** B biến các thông tin đã có thành **đặc trưng**, tức các giá trị mô hình nhận vào, như nhiệt độ 25 °C hoặc phụ tải một giờ trước. Phụ tải đo thật lúc 13:00 là **nhãn** của bước 1. Khi học từ các ngày trong quá khứ, mô hình dùng nhãn để học mối quan hệ giữa đầu vào và kết quả. Khi phát hành dự báo mới lúc 12:00, mô hình chỉ nhận đặc trưng.
- **Từ dự báo đến kết quả.** Khi có số đo thật lúc 13:00, D tính sai số và so sánh với **đối chứng**, tức cách dự báo đơn giản dùng để làm mốc, chẳng hạn lấy phụ tải cùng giờ hôm trước. D dùng các giai đoạn **validation** (kiểm định để chọn mô hình và tham số), sau đó đánh giá trên giai đoạn **test** (kiểm thử cuối giữ riêng đến khi đã chốt lựa chọn). Mô hình có ích nếu sai số giảm trên cùng các giờ được chấm, với độ phủ được báo kèm. Độ phủ cho biết trong các giờ dự kiến, có bao nhiêu giờ đủ dữ liệu để chấm.

```mermaid
flowchart LR
    A["A · Kiểm tra số đo<br/>Bảng quan sát → B và D"]
    B["B · Tạo đầu vào và nhãn<br/>Bộ mẫu → C và D"]
    C["C · Học cách dự báo<br/>Bộ mô hình → D"]
    D["D · So dự báo với số đo<br/>Bảng kết quả và cấu hình đã chọn → E"]
    E["E · Cho người khác chạy và xem<br/>Bản chạy thử và hướng dẫn → cả nhóm"]
    A --> B --> C --> D --> E
    A --> D
    B --> D
    D -. "Cách chia tập trước khi chạy" .-> C
    E -. "Xác nhận đọc được kết quả" .-> D
```

**Tự kiểm tra trước khi nhận việc.** Lúc 12:00 có thể dùng số đo thời tiết nào? Kết quả bước 24 ứng với giờ nào? Khi có số đo thật, làm sao so sánh mô hình với cách lấy phụ tải hôm trước? Thử trả lời bằng lời của mình, rồi đối chiếu với [ví dụ trong hợp đồng bàn giao](HOP_DONG_BAN_GIAO.md).

## 2. Ai phụ trách bước nào?

| Người | Câu hỏi cần giải quyết | Sản phẩm và người nhận chính | Công sức |
|---|---|---|---:|
| A | Các số đo có đáng tin và đã có lúc dự báo chưa? | Bảng quan sát, mô tả nguồn và báo cáo chất lượng → B, D | 28–30 giờ |
| B | Từ bảng quan sát, làm sao tạo đúng đầu vào và nhãn cho 24 bước? | Bộ mẫu, danh sách cột và công cụ tạo đầu vào → C, D và E theo từng sản phẩm | 24–28 giờ |
| C | Mô hình học và dự báo từ bộ mẫu như thế nào? | Bộ mô hình và cấu hình thử → D. Mô hình lưu và hướng dẫn nạp → E | 26–30 giờ |
| D | Làm sao biết mô hình nào dự báo tốt hơn một cách công bằng? | Cách chia tập → C. Bảng kết quả và cấu hình đã chọn → E | 28–30 giờ |
| E | Người khác chạy dự báo và xem kết quả bằng cách nào? | Bản chạy thử, hướng dẫn và bộ nộp → cả nhóm | 24–28 giờ |

Mỗi người viết mã, kiểm tra phần mình, viết phần báo cáo và trực tiếp trình bày. Khi nhận vai trò, đọc [phiếu giao việc A–E](PHIEU_GIAO_VIEC.md). Khi giao hoặc nhận sản phẩm, dùng [bảng bàn giao](HOP_DONG_BAN_GIAO.md).

Trong buổi khởi động, ghi ngày bắt đầu, hạn nộp thực tế và tên A–E vào bảng công việc chung của nhóm. Lịch dự kiến là **3 tuần, khoảng 8–10 giờ/người/tuần**. Ưu tiên người vững đánh giá mô hình ở D và người vững xử lý dữ liệu theo thời gian ở A.

## 3. Tiến độ 3 tuần và cách làm song song

| Mốc | A | B | C | D | E | Cổng đi tiếp |
|---|---|---|---|---|---|---|
| Ngày 1–2 | Khảo sát PJME/thời tiết và tải nguồn dự phòng | Chốt đặc trưng và tạo mẫu giả lập | Ba mô hình nhận X/y giả lập | Schema, dữ liệu mẫu, fold và công thức chỉ số | Lệnh chạy và dashboard từ bảng dự báo mẫu | **G0:** các phần thử được bằng mẫu, thống nhất đầu vào và đầu ra |
| Ngày 3 | Biên bản nguồn và metadata | Kiểm tra nhận dữ liệu hai hướng | Giữ API mô hình độc lập nguồn | Xác nhận nguồn chính, kế hoạch chia tập | Xác nhận giao diện không phụ thuộc tên cột thô | **G1:** quyết định PJME hoặc Tetouan; có hướng thời tiết bắt buộc |
| Ngày 4–7 | Dữ liệu thật, cache, báo cáo chất lượng | Đặc trưng/nhãn 24 bước và kiểm thử | Nối mô hình với dữ liệu thật | Nối fold, đối chứng và đánh giá | Nối lệnh chạy, dự báo và giao diện | **G2:** một lượt chạy thật đủ 24 bước, có thời tiết quá khứ |
| Ngày 8–12 | Độ phủ và độ trễ thời tiết | Ablation nhóm đặc trưng | Tối ưu SVR; bàn giao cấu hình Ridge/RF | Đối chứng, validation, phân tích và chọn mô hình | Cài đặt mới, lưu/nạp và đo suy luận | **G3:** hoàn tất validation; khóa đặc trưng, tham số và trọng số |
| Ngày 13–15 | Phân tích lỗi theo dữ liệu | Phân tích theo horizon/đặc trưng | Kiểm tra mô hình đã lưu | Chạy kiểm thử cuối theo lựa chọn đã khóa | Xuất bảng/đồ thị và demo từ kết quả thật | **G4:** kết quả cuối, độ phủ, lỗi đỉnh và tài nguyên |
| Ngày 16–18 | Hoàn thiện phần dữ liệu | Hoàn thiện phần đặc trưng | Hoàn thiện lý thuyết/tham số | Hoàn thiện kết quả/kết luận | Hợp nhất PDF, readme, ZIP; kiểm tra môi trường mới | **G5:** bộ nộp đầy đủ và nhất quán |
| Ngày 19–21 | Cả nhóm tập trình bày, hỏi chéo, sửa lỗi và duyệt bản nộp | Cùng thực hiện | Cùng thực hiện | Cùng thực hiện | Cùng thực hiện | **G6:** cả 5 người trình bày được; demo có phương án dự phòng |

Nếu một cổng chưa đạt, ghi lỗi cụ thể, người sửa và thời hạn xử lý trong lần cập nhật kế tiếp. G1 phải áp dụng quyết định nguồn dự phòng thay vì kéo dài vô hạn việc ghép PJME. G3 chỉ mở kiểm thử cuối khi các kiểm tra dữ liệu/thời gian đã đạt; G4 không đặt điều kiện phải đạt một MAPE mong muốn.

D chuẩn bị mẫu chung từ ngày 1. B thử tạo đầu vào, C thử mô hình, D thử chấm điểm và E thử hiển thị trong khi A khảo sát nguồn thật. Dùng các mốc trong bảng để cập nhật trạng thái trong bảng công việc chung. Chủ phần làm việc trên nhánh riêng và báo người nhận trước khi đổi giao diện.

## 4. Điểm nghẽn và việc cần thống nhất

Dùng các buổi họp 20 phút hai lần mỗi tuần. Nếu một quyết định đến hạn trước buổi họp tiếp theo, người phụ trách đưa bằng chứng vào nhật ký chung để các bên liên quan chốt trong ngày. Nhật ký đặt tại bảng công việc của nhóm, gồm câu hỏi, người chuẩn bị, liên kết bằng chứng, quyết định, người thực hiện và hạn.

| Mốc và dấu hiệu | Ai trao đổi, ai chuẩn bị | Quyết định và nơi lưu |
|---|---|---|
| **Ngày 1–2.** Các phần hiểu khác nhau về đầu vào và đầu ra | Cả nhóm. D chuẩn bị mẫu chung. B thử đọc quan sát, C thử nhận đầu vào và nhãn, D thử chấm, E thử đọc kết quả | D ghi phiên bản mẫu đã duyệt, các cột cần sửa và người sửa vào nhật ký |
| **Cuối ngày 3.** Chưa xác minh được giờ đo hoặc cách ghép thời tiết PJME | A trình bày mẫu và bằng chứng về nguồn, D xác nhận, B cập nhật cách tạo mẫu | A lưu biên bản chọn nguồn, định nghĩa nhãn và thời điểm dữ liệu có sẵn trong nhật ký. Chuyển Tetouan nếu PJME chưa đạt điều kiện |
| **Ngày 7.** Từng phần chạy riêng nhưng chưa nối được | Người giao và người nhận ở bước lỗi kiểm tra một lượt chạy thật đủ 24 bước. D điều phối | Chủ phần lỗi ghi sản phẩm thiếu, cách tái hiện, người sửa và hạn. Các phần khác tiếp tục bằng mẫu đã duyệt |
| **Ngày 12.** Hai mô hình chấm trên các giờ khác nhau hoặc chưa rõ độ phủ | B chuẩn bị danh sách mẫu, C cung cấp dự báo và cấu hình, D đối chiếu số liệu. E thử đọc bảng kết quả | D ghi mẫu so sánh, độ phủ, cấu hình và trọng số đã khóa trước test. E xác nhận đọc được bảng trong nhật ký |

Khi gặp lỗi bàn giao, dùng ngay ba câu hỏi trong cập nhật hằng ngày. Mẫu nào cho thấy lỗi? Ai có thể kiểm tra cùng mình? Công việc nào vẫn tiếp tục được với dữ liệu mô phỏng? Mỗi người cập nhật bốn dòng gồm việc đã làm, liên kết đầu ra, vướng mắc và việc kế tiếp. A/B kiểm tra chéo dữ liệu, C/D kiểm tra chéo mô hình và cách đánh giá, E thử cài đặt như người dùng mới. Chủ phần phụ trách sửa và cung cấp lại bằng chứng.

## 5. Tra cứu quy tắc về nguồn và thí nghiệm

### Chốt nguồn vào cuối ngày 3

A chuẩn bị hai hướng ngay từ đầu. B–E phát triển bằng dữ liệu mẫu và giao diện chung trong thời gian này. Link tải và tình trạng từng nguồn nằm trong [danh mục nguồn dữ liệu](NGUON_DU_LIEU.md).

| Hướng | Điều kiện và cách dùng |
|---|---|
| PJME + quan sát thời tiết | Giữ làm nguồn chính nếu có bằng chứng đủ về timestamp và ý nghĩa khoảng đo, ghép được nguồn thời tiết hợp lệ và báo được độ phủ. Kiểm tra trạm, trường dữ liệu và cờ chất lượng ở [NOAA Global Hourly](https://www.ncei.noaa.gov/access/search/data-search/global-hourly/) |
| Tetouan — nguồn dự phòng | Nếu đến cuối ngày 3 PJME chưa đạt điều kiện, chuyển sang Tetouan. Nguồn có phụ tải ba vùng và thời tiết trong cùng bộ dữ liệu. Dùng Zone 1 làm mục tiêu chính. [Tetouan/UCI](https://archive.ics.uci.edu/dataset/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity) |

**Biên bản quyết định ngày 3 do A lập, D xác nhận**, gồm URL/phiên bản/checksum, khoảng thời gian, số quan sát, đơn vị gốc, tần suất, quy ước timestamp, giả định thời điểm có dữ liệu, quy tắc thiếu/trùng và độ phủ. Mục nào chưa xác nhận phải được ghi rõ. Không bật cờ “đã xác nhận thời gian” chỉ dựa vào việc mô hình chạy được.

Tetouan có tần suất gốc 10 phút. Nếu xác nhận dữ liệu là công suất, có thể lấy trung bình các khoảng đo hoàn tất để tạo phụ tải giờ; năng lượng theo khoảng đo cần quy tắc cộng phù hợp. Khi ý nghĩa/đơn vị chưa đủ cơ sở để tổng hợp, giữ quan sát gốc và dự báo tại các giờ đích cách nhau một giờ, ghi rõ mục tiêu là giá trị quan sát ở giờ đích. Không tự đổi sang MW. Giao diện ở hợp đồng bàn giao hỗ trợ cả tần suất gốc 10 và 60 phút.

Một trạm thời tiết đại diện cho vùng phụ tải rộng là giả định cần nêu. Thời tiết bắt buộc có dữ liệu thật trong thực nghiệm, nhưng không bắt buộc phải làm sai số giảm.

### Thực nghiệm và dữ liệu kiểm thử

- **PJME:** phát triển trên 2014–2017; giữ phần 2018 đến thời điểm cuối hiện có làm kiểm thử cuối. Dùng 5 fold mở rộng với validation 60 ngày nếu đủ lưới hợp lệ.
- **Tetouan:** giữ 20% cuối trục thời gian làm kiểm thử; phần trước dùng phát triển với 3 fold mở rộng, mỗi validation 28 ngày. Làm tròn ranh giới về giờ hoàn tất, trước khi lọc mẫu.
- 2017 của PJME đã được xem trong nghiên cứu tham khảo nên được coi là dữ liệu phát triển/tái lập, không phải kiểm thử mới chưa xem.
- A được kiểm tra định dạng, timestamp và độ phủ ở phần kiểm thử; biểu đồ/phân tích chọn đặc trưng và mọi tối ưu chỉ dùng phần phát triển.
- Ridge: 4 giá trị alpha. RF: 4 cấu hình độ sâu/kích thước lá. SVR: tối đa 12 tổ hợp C/epsilon/gamma. Chốt danh sách trước khi chạy; chọn trên các horizon 1/6/12/24 rồi xác nhận đủ 24 horizon.
- So sánh mô hình trên cùng cặp thời điểm. Thí nghiệm có/không thời tiết dùng cùng mẫu hợp lệ. Báo n và độ phủ, không chỉ báo sai số.
- Nếu dùng ensemble, chọn thành phần và trọng số bằng validation. Không bê nguyên trọng số 70/30 của dự án tham khảo sang bản nhóm.
- Lưu quyết định trước kiểm thử cuối; phục hồi lần chạy bị ngắt từ lựa chọn đã lưu, không chọn lại theo kết quả kiểm thử.
- Chỉ mở rộng nguồn/vùng thứ hai sau G3 nếu còn thời gian. Mỗi nguồn/vùng phải huấn luyện và đánh giá riêng; ghi rõ đây là lặp lại thực nghiệm hay thử chuyển mô hình.

### Các lựa chọn của nhóm

- Nhóm **tự viết lại phần cốt lõi**: thu thập/xử lý dữ liệu, tạo mẫu, mô hình qua scikit-learn, kiểm định và điều phối thực nghiệm. Dự án hiện có là tài liệu tham khảo, không được mặc định coi là đóng góp mới của nhóm.
- Dự báo tại T cho **T+1 đến T+24**; thời điểm phát hành cách nhau một giờ. Đánh giá thêm các giờ tải cao và đỉnh trong cửa sổ dự báo.
- **Thời tiết bắt buộc**. Chỉ dùng các quan sát được giả định đã có sẵn tại T; mặc định mô phỏng độ trễ thời tiết một giờ. Giả định này không chứng minh đã tái dựng lịch sử công bố dữ liệu.
- Thuật toán trọng tâm: **SVR**. Ridge và Random Forest là mô hình so sánh; có đối chứng ngày trước, tuần trước và thời tiết có/không.
- Không dùng thời tiết thực tế ở giờ đích như thể đã biết trước. Dữ liệu tái phân tích có độ trễ không tự động được coi là quan sát sẵn có tại T.
- MAPE dưới 3,5% là mục tiêu nghiên cứu, không phải điều kiện ép nghiệm thu. Phải báo kết quả thật và giới hạn.
- Tài nguyên được đo thực tế; thời gian tìm tham số được phân biệt với một lần suy luận.

## 6. Yêu cầu nộp bài và bảo vệ

### Yêu cầu học phần

Nguồn đối chiếu: [Yêu cầu đồ án IT3190](D:/XStudying_At_Hust/FifthSemester/Courses/IT3190_MachineLearning/BTL/Yeu_cau_Do_an_Mon_hoc_IT3190.md). Liên kết này trỏ đến tệp trên máy hiện tại; khi chia sẻ, nhóm lưu một bản nguồn tham khảo mà mọi thành viên truy cập được.

- Đề xuất phải mô tả bài toán, kịch bản ứng dụng, thuật toán, đầu vào/đầu ra, tiền xử lý và nguồn/đặc điểm/kích thước dữ liệu.
- Có cài đặt và thực nghiệm trên dữ liệu thực tế; đánh giá đúng phương pháp, thử tham số, so sánh và tránh overfitting.
- Giao nộp **mã nguồn trong một tệp ZIP/RAR**, **`readme.txt`** và **báo cáo PDF** đủ 7 nội dung trong bảng dưới.
- Cả 5 thành viên tham gia thực hiện và trực tiếp trình bày; thời lượng khoảng **15 phút/nhóm**.
- Mã nguồn, báo cáo và trình bày phải thống nhất. Phần kế thừa mã/thư viện/công cụ mã nguồn mở phải được trích dẫn trong PDF và nêu trong trình bày.

Các chỉ số trong yêu cầu học phần là ví dụ theo dạng bài toán. Nhóm dùng chỉ số hồi quy cho phụ tải; confusion matrix/Precision/Recall/F1 áp dụng cho bài toán phụ trợ nhận diện giờ tải cao có định nghĩa rõ.

### Phân công báo cáo và bảo vệ

| Nội dung PDF bắt buộc | Người viết/chủ trì | Bằng chứng cần có |
|---|---|---|
| 1. Giới thiệu và mô tả bài toán | A viết, D kiểm tra kịch bản | Input/output, thời điểm phát hành, ý nghĩa tải cao |
| 2. Phương pháp học máy và tập dữ liệu | A dữ liệu; B đặc trưng; C thuật toán | Nguồn/đơn vị/độ phủ; công thức và giải thích phương pháp |
| 3. Kết quả thực nghiệm và đánh giá | D chủ trì, B/C cung cấp thí nghiệm | Split, tham số, đối chứng, ablation, lỗi đỉnh và giới hạn |
| 4. Chức năng hệ thống | E | Lệnh chạy, ảnh giao diện, một ví dụ sử dụng |
| 5. Kiến trúc mã nguồn | E tổng hợp; từng người mô tả mô-đun | Luồng dữ liệu, vai trò lớp/hàm, giao diện bàn giao |
| 6. Khó khăn và giải pháp | Mỗi người viết phần mình; E biên tập | Vấn đề thật, cách kiểm tra, giải pháp và phần còn tồn tại |
| 7. Khám phá mới và kết luận | D tổng hợp; cả nhóm duyệt | Nhận xét bám số liệu, giới hạn và hướng tiếp theo |

Từng người viết nội dung chuyên môn từ tuần 1; E hợp nhất và kiểm tra hình thức. Chưa có số liệu thì để dấu chờ, không điền số của dự án tham khảo như kết quả nhóm.

| Thứ tự bảo vệ | Người | Nội dung | Thời lượng dự kiến |
|---|---|---|---:|
| 1 | A | Bài toán, dữ liệu và xử lý nguồn | 2,5 phút |
| 2 | B | Đặc trưng, tạo mẫu và thông tin có sẵn tại T | 2,5 phút |
| 3 | C | SVR, các mô hình so sánh và tham số | 2,5 phút |
| 4 | D | Thiết kế đánh giá, kết quả và giới hạn | 2,5 phút |
| 5 | E | Kiến trúc, chức năng và demo | 2,5 phút |

Tổng 12,5 phút; dành 2,5 phút dự phòng trong khung khoảng 15 phút. Việc phần hỏi đáp có nằm trong thời lượng này hay không cần theo thông báo thực tế của giảng viên. Mỗi người tự soạn phần slide của mình; E hợp nhất. Cả nhóm phải hiểu luồng chung và dùng cùng một bộ số liệu đã xuất.

### Ghi nhận đóng góp và nguồn kế thừa

| Thành viên | Mã nguồn/kiểm tra đã thực hiện | Thí nghiệm hoặc phân tích | Phần báo cáo/slide | Liên kết bằng chứng |
|---|---|---|---|---|
| A | … | … | … | … |
| B | … | … | … | … |
| C | … | … | … | … |
| D | … | … | … | … |
| E | … | … | … | … |

| Nguồn/mã/thư viện/công cụ kế thừa | URL/phiên bản | Nhóm đã sử dụng phần nào | Đóng góp mới của nhóm | Vị trí trích dẫn PDF/slide |
|---|---|---|---|---|
| Dự án tham khảo hiện tại | … | … | … | … |
| Nguồn phụ tải/thời tiết | … | … | … | … |
| Thư viện/công cụ thực tế khác | … | … | … | … |

## 7. Kiểm tra trước khi nộp

- [ ] Có đề xuất mô tả bài toán, phương pháp, input/output, biểu diễn dữ liệu và nguồn dữ liệu.
- [ ] Có dữ liệu thời tiết thật và thực nghiệm có/không thời tiết trên cùng mẫu.
- [ ] Các kiểm tra thời gian, nhãn và chuẩn hóa đạt; mô hình dự báo đủ 24 bước bằng cùng logic với huấn luyện.
- [ ] Có kết quả validation và kiểm thử cuối tách biệt; lựa chọn đã được lưu trước kiểm thử.
- [ ] Có MAE/RMSE/MAPE theo horizon, n/độ phủ, nhận diện tải cao và sai lệch giờ đỉnh; ngưỡng tải cao lấy từ train.
- [ ] Có đo tài nguyên và nạp lại mô hình; đã chạy theo hướng dẫn trên môi trường mới.
- [ ] Một tệp ZIP/RAR chứa mã nguồn sạch, cấu hình, phụ thuộc và phần tối thiểu chạy demo; dữ liệu đầy đủ có hướng dẫn lấy và kiểm tra phiên bản.
- [ ] Có `readme.txt` với phiên bản thư viện và các bước thiết lập/chạy cụ thể; README Markdown hiện tại không thay thế tệp bắt buộc này.
- [ ] Có PDF đủ 7 nội dung, trích dẫn nguồn/mã kế thừa và đóng góp thành viên.
- [ ] PDF, slide, giao diện và mã nộp dùng cùng bộ số liệu; không nhầm MAPE gộp với MAPE riêng ở bước 24 giờ.
- [ ] Cả 5 người đã tập trình bày; có bản demo và ảnh/video dự phòng từ lần chạy thật.
- [ ] Đã kiểm tra tên tệp, mở được ZIP/PDF và xác nhận hạn/cách nộp thực tế của giảng viên.
