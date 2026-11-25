# Nguồn thực nghiệm chính • Tetouan Zone 1

Dùng duy nhất **Power Consumption of Tetouan City**, UCI ID 849. Tệp chứa số đo phụ tải ba vùng và thời tiết, ghi mỗi 10 phút. Nhãn là giá trị Zone 1 tại đúng giờ đích. [Trang UCI](https://archive.ics.uci.edu/dataset/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity) · [ZIP chính thức](https://archive.ics.uci.edu/static/public/849/power%2Bconsumption%2Bof%2Btetouan%2Bcity.zip) · [DOI](https://doi.org/10.24432/C5B034)

CSV có 52.416 dòng, từ 01/01/2017 00:00 đến 30/12/2017 23:50, trong đó có 8.736 mốc đúng giờ. Kiểm tra thực tế không thấy giờ trùng hoặc thiếu mốc 10 phút. Giữ đơn vị và giờ ghi của nguồn vì metadata chưa xác nhận đơn vị vật lý và múi giờ. SHA-256 của ZIP là `3c4bf684161180937043a9fb65701a83d44b740b0d42f0492b6e7aec57ddbbfe`.

Chạy `python scripts/tetouan.py prepare` để đọc hoặc tải bản gốc và tái tạo kiểm toán. Bộ dữ liệu của Salam & El Hibaoui (2018), giấy phép CC BY 4.0. Bản PJME dùng trong nghiên cứu trước được lưu riêng cùng [báo cáo tham khảo](../reports/final/REPORT.md).
