# Kiểm toán dữ liệu PJME

Nguồn: https://raw.githubusercontent.com/archd3sai/Hourly-Energy-Consumption-Prediction/master/PJME_hourly.csv

| Kiểm tra | Kết quả |
|---|---:|
| Dòng gốc | 145,366 |
| Dòng lặp timestamp (sau lần đầu) | 4 |
| Dòng trùng hoàn toàn | 0 |
| Mốc thiếu theo lịch giờ địa phương chưa gắn timezone | 30 |
| Phụ tải nhỏ nhất/lớn nhất (MW) | 14,544 / 62,009 |
| Dòng nguồn cách ly | 767 |
| Giờ đầu vào điền tiến tối đa hai giờ | 1 |

## Cách diễn giải thời gian

Giả thuyết giờ bắt đầu: 33 dòng mơ hồ/không tồn tại khi gắn timezone.
Giả thuyết giờ kết thúc: 8 dòng mơ hồ/không tồn tại sau khi dịch nhãn một giờ.
Khác biệt này là dấu hiệu để điều tra, chưa phải bằng chứng xác nhận quy ước của nguồn.
Cách xử lý hiện tại: local_clock_unconfirmed_guarded. Cho phép ghép thời tiết: False.

Các giờ cao tải vẫn được giữ. Không xóa theo IQR, không nội suy nhãn và không gộp hai timestamp DST khác giá trị.
Báo cáo trên mô tả toàn bộ nguồn thô. Thực nghiệm chính dùng 2014–2017; độ phủ sau tạo mẫu được ghi riêng theo horizon.

## Số dòng theo năm

| Năm | Dòng nguồn |
|---|---:|
| 2002 | 8757 |
| 2003 | 8758 |
| 2004 | 8782 |
| 2005 | 8758 |
| 2006 | 8758 |
| 2007 | 8758 |
| 2008 | 8782 |
| 2009 | 8758 |
| 2010 | 8757 |
| 2011 | 8758 |
| 2012 | 8782 |
| 2013 | 8758 |
| 2014 | 8760 |
| 2015 | 8760 |
| 2016 | 8784 |
| 2017 | 8760 |
| 2018 | 5136 |
