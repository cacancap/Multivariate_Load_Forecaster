# Nguồn dữ liệu cho bài tập dự báo phụ tải điện 24 giờ

Đối chiếu ngày **18/11/2026**. Theo kế hoạch nhóm, phương án đầu tiên là **phụ tải PJME + thời tiết quan sát**. Cuối ngày 3, nếu chưa xác minh được cách hiểu giờ đo PJME và cách ghép thời tiết, nhóm chuyển sang **Tetouan**, dùng phụ tải Zone 1 và thời tiết trong cùng bộ dữ liệu. [Kế hoạch chọn nguồn](KE_HOACH_NHOM_5_NGUOI.md)

| Nguồn | Dùng để làm gì | Link lấy dữ liệu | Tình trạng trong dự án |
|---|---|---|---|
| **PJME hourly** | Phụ tải theo giờ cho phương án PJME và thực nghiệm tham khảo | [Tải trực tiếp PJME_hourly.csv](https://raw.githubusercontent.com/archd3sai/Hourly-Energy-Consumption-Prediction/master/PJME_hourly.csv) · [Trang tệp trên GitHub](https://github.com/archd3sai/Hourly-Energy-Consumption-Prediction/blob/master/PJME_hourly.csv) | Có CSV và bản ghi lần tải trong `data/raw/`. Quy ước giờ đo của CSV còn cần xác minh |
| **NOAA/NCEI Global Hourly (ISD)** | Ứng viên lấy thời tiết **quan sát tại trạm** để ghép với PJME | [Tìm và tải theo trạm, ngày và biến](https://www.ncei.noaa.gov/access/search/data-search/global-hourly/) · [Mô tả bộ dữ liệu](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) | Chưa có bản tải từ trạm trong thư mục dữ liệu. Chưa xác nhận độ phủ và khả năng ghép |
| **Power Consumption of Tetouan City (UCI, ID 849)** | Phương án dự phòng có phụ tải ba vùng và thời tiết trong cùng CSV | [Trang bộ dữ liệu](https://archive.ics.uci.edu/dataset/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity) · [ZIP từ nút Download của UCI](https://archive.ics.uci.edu/static/public/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity.zip) | Đã đối chiếu thông tin và link ZIP trên trang UCI. Chưa có bản ZIP/CSV cục bộ để kiểm tra |
| **Open-Meteo Historical Weather (ERA5)** | Thời tiết **tái phân tích** dùng trong pipeline tham khảo | [Cấu hình và xuất truy vấn](https://open-meteo.com/en/docs/historical-weather-api) | Có phản hồi JSON đã lưu trong `data/raw/weather/`. Kết quả tham khảo hiện tại chưa ghép thời tiết vào PJME |

## PJME và thời tiết quan sát

- **PJME.** Tệp trong dự án có **145.366 dòng dữ liệu** và hai cột `Datetime`, `PJME_MW`. Timestamp nhỏ nhất là **01/01/2002 01:00**, lớn nhất là **03/08/2018 00:00** theo nhãn giờ trong CSV. SHA-256 của tệp cục bộ khớp bản ghi lần tải, `4eb2b16d42bf07ec41ab55cb842191594cb69452725a6d3c0991658a628fde84`. Link CSV là bản sao cộng đồng mà dự án đã lưu. Dùng cổng của PJM để tra cứu dữ liệu đo chính thức và quy ước trường thời gian. Việc đối chiếu cổng chính thức với đúng phiên bản CSV vẫn cần thực hiện trước khi ghép. [Kiểm toán PJME](../reports/final/DATA_AUDIT.md) · [PJM Data Miner 2 – Hourly Load: Metered](https://dataminer2.pjm.com/feed/hrl_load_metered)
- **NOAA/NCEI.** Trên trang tìm kiếm Global Hourly, bắt đầu bằng trạm ứng viên **Philadelphia International Airport (KPHL, USAF 724080, WBAN 13739)**. Tìm theo tên trạm, chọn thời gian trùng với PJME trong giai đoạn **2014–2018** và lấy trường nhiệt độ `TMP` để kiểm tra trước. Đối chiếu giờ quan sát, cờ chất lượng và độ phủ theo tháng trước khi chốt trạm. Một trạm chỉ đại diện cho vị trí đo. Độ trễ một giờ trong bài tập là giả định mô phỏng thời điểm có thể dùng quan sát. [Tài liệu nhận dạng trạm của NCEI](https://www.ncei.noaa.gov/pub/data/noaa/isd-problems.pdf) · [Tìm và tải Global Hourly](https://www.ncei.noaa.gov/access/search/data-search/global-hourly/)

## Tetouan

UCI công bố **52.417 quan sát**, cách nhau **10 phút** theo mô tả cột thời gian. Tệp gốc có tên `Tetuan City power consumption.csv`, gồm số đo phụ tải ba vùng và các biến như nhiệt độ, độ ẩm và tốc độ gió. Chọn **phụ tải Zone 1** làm nhãn. Khi trích dẫn, dùng DOI **10.24432/C5B034**. UCI công bố giấy phép **CC BY 4.0** và để trống đơn vị cho các cột phụ tải trong bảng mô tả, vì vậy giữ đơn vị gốc cho đến khi xác minh được cách diễn giải. [UCI – thông tin biến và giấy phép](https://archive.ics.uci.edu/dataset/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity) · [DOI của bộ dữ liệu](https://doi.org/10.24432/C5B034)

## ERA5 trong thực nghiệm tham khảo

Pipeline lấy nhiệt độ, độ ẩm tương đối và bức xạ trực tiếp tại tọa độ Philadelphia qua Open-Meteo, với `models=era5`. Đây là dữ liệu khí tượng tái phân tích. Khi chạy nhánh giả định biết trước thời tiết, ghi rõ giả định đó. Với thực nghiệm chính của nhóm, dùng thời tiết quan sát được giả định đã có tại giờ phát hành theo kế hoạch. [Open-Meteo – mô hình và biến thời tiết](https://open-meteo.com/en/docs/historical-weather-api) · [Cấu hình thực nghiệm tham khảo](../configs/experiment.yaml)
