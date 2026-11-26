IT3190 • Dự báo phụ tải điện 24 giờ tại Tetouan (Zone 1, Zone 2, Zone 3)
==========================================================================

Giải nén ZIP, mở terminal tại thư mục gốc chứa readme.txt.
Mọi lệnh sử dụng đường dẫn tương đối từ thư mục gốc.

1. Tạo môi trường ảo và cài đặt phụ thuộc (Python >= 3.11, khuyến nghị 3.13)
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python -m pip install reportlab==4.4.9 "pillow<13,>=11"
   python -m pip install -e . --no-deps

2. Kiểm thử tự động toàn bộ mã nguồn (chống rò rỉ, chia tập, tính tay, nạp lại mô hình)
   python -m pytest -q

3. Chuẩn bị dữ liệu, chia tập, khai phá EDA (tương ứng Vai trò A, B, D)
   python scripts/tetouan.py prepare
   python scripts/tetouan.py split
   python scripts/tetouan.py eda

4. Chạy kiểm thử nhanh toàn luồng (1 bước, 1 lượt validation trên Zone 1)
   python scripts/tetouan.py smoke --zone zone1

5. Chạy thực nghiệm đầy đủ cho cả 3 vùng (Zone 1, Zone 2, Zone 3)
   python scripts/tetouan.py full --zone all
   (Hoặc chạy riêng từng vùng: --zone zone1 / --zone zone2 / --zone zone3)

6. Chạy Demo 24 giờ (CLI & Giao diện Web Streamlit)
   python scripts/tetouan.py demo --zone zone1 --origin "2017-12-01 12:00"
   streamlit run app/tetouan_demo.py

7. Xuất tổng hợp biểu đồ, báo cáo PDF 7 mục và đóng gói ZIP nộp bài
   python scripts/tetouan.py report
   python scripts/tetouan.py pdf
   python scripts/tetouan.py package

8. Chạy riêng theo từng vai trò trong nhóm 5 người
   - Vai trò A (Dữ liệu & EDA):   python scripts/tetouan.py observations ; python scripts/tetouan.py eda
   - Vai trò B (Đặc trưng):       python scripts/tetouan.py samples --zone all
   - Vai trò D (Chia & Chấm):     python scripts/tetouan.py split ; python scripts/tetouan.py score --zone all
   - Vai trò C (Huấn luyện):      python scripts/tetouan.py train --zone all
   - Vai trò E (Demo, PDF, ZIP):  python scripts/tetouan.py demo ; python scripts/tetouan.py report ; python scripts/tetouan.py pdf ; python scripts/tetouan.py package

Ghi chú nguồn dữ liệu:
- UCI Machine Learning Repository ID 849: Power Consumption of Tetouan City
- Salam, A. & El Hibaoui, A. (2018), DOI: 10.24432/C5B034, Giấy phép: CC BY 4.0
