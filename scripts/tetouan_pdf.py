"""Build the Vietnamese hand-in PDF from exported evidence (ReportLab + stdlib)."""
import csv
import json
import os
from pathlib import Path
from statistics import mean
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer, PageBreak

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"reports/tetouan"
NAMES={"ridge":"Ridge","ridge_no_weather":"Ridge bỏ thời tiết","svr":"SVR RBF","random_forest":"Random Forest","week_prior":"Tuần trước","day_prior":"Ngày trước"}

def read(name):
    with (DIR/(name+".csv")).open(encoding="utf-8",newline="") as file:
        return list(csv.DictReader(file))

def js(name):
    return json.loads((DIR/(name+".json")).read_text(encoding="utf-8"))

def number(v,d=2):
    return f"{float(v):,.{d}f}".replace(","," ").replace(".",",")

def main():
    for folder,regular,bold in [
        (Path(os.environ.get("TETOUAN_FONT_DIR","/usr/share/fonts/truetype/dejavu")),"DejaVuSans.ttf","DejaVuSans-Bold.ttf"),
        (Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts","arial.ttf","arialbd.ttf")]:
        if (folder/regular).exists() and (folder/bold).exists():
            pdfmetrics.registerFont(TTFont("Text",str(folder/regular)))
            pdfmetrics.registerFont(TTFont("Head",str(folder/bold)))
            break
    else:
        raise SystemExit("Set TETOUAN_FONT_DIR to a directory containing DejaVu Sans regular and bold.")
    pdf=SimpleDocTemplate(str(DIR/"IT3190_Tetouan.pdf"),pagesize=A4,leftMargin=19*mm,rightMargin=19*mm,
         topMargin=21*mm,bottomMargin=19*mm,title="IT3190 • Dự báo phụ tải Tetouan Zone 1")
    items=[]
    def para(t, size=10.2, bold=False, ink="#253945", gap=6):
        items.append(Paragraph(escape(t),ParagraphStyle("p",fontName="Head" if bold else "Text",fontSize=size,
            leading=size*1.43,spaceAfter=gap,textColor=colors.HexColor(ink))))
    def head(t):
        para(t,17,True,"#124f4c",10)
    def grid(header,rows,widths):
        def cell(s,heading):
            return Paragraph(escape(str(s)),ParagraphStyle("c",fontName="Head" if heading else "Text",
               fontSize=8.3,leading=11.5,textColor=colors.white if heading else colors.HexColor("#243943")))
        t=Table([[cell(s,i==0) for s in row] for i,row in enumerate([header]+list(rows))],
               colWidths=[w*mm for w in widths],repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#155a57")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#eff5f4"),colors.white]),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        items.extend([t,Spacer(1,6)])
    def pic(name,w,h):
        items.append(Image(str(DIR/name),width=w*mm,height=h*mm))
    def page(): items.append(PageBreak())
    def frame(c,doc):
        c.saveState()
        c.setFillColor(colors.HexColor("#155a57")); c.setFont("Head",9)
        c.drawString(19*mm,283*mm,"IT3190     /     HỌC MÁY VÀ KHAI PHÁ DỮ LIỆU")
        c.setStrokeColor(colors.HexColor("#bad1cc"));c.line(19*mm,280*mm,191*mm,280*mm)
        c.setFont("Text",8);c.drawString(19*mm,12*mm,"Tetouan  •  Zone 1  |  Bộ dữ liệu UCI 849")
        c.drawRightString(191*mm,12*mm,f"{doc.page}");c.restoreState()
    scores=read("scores")
    def points(slice_name,h=None):
        return {r["model"]:r for r in scores if r["split"]=="test" and r["slice"]==slice_name and (h is None or int(r["horizon"])==h)}
    total=points("overall")
    frozen=js("selection")
    name=frozen["best_model"]; title=NAMES[name]
    winner=total[name]; audit=js("audit")
    q=[r for r in read("thresholds") if r["split"]=="test"][0]
    weather=[r for r in read("weather_ablation") if r["slice"]=="overall"]
    dw=next(r for r in weather if r["split"]=="test")
    head("Dự báo phụ tải Zone 1 trong 24 giờ")
    para("Bài tập lớn • Nhập môn học máy và khai phá dữ liệu",12,True)
    para("Thành viên và mã sinh viên: ______________________________________________")
    para("Đóng góp cá nhân: _______________________________________________________")
    head("1. Bài toán và kịch bản sử dụng")
    para("Mỗi giờ đúng, nhóm phát hành một dãy 24 dự báo cho một vùng phân phối điện của Tetouan, Maroc. Người dùng có thể xem khi nào nhu cầu sẽ tăng trong ngày kế tiếp và mô hình thường sai bao nhiêu ở các giờ tải cao.")
    para("Ví dụ lúc 12:00, đầu vào dùng phụ tải đến 12:00, đặc điểm lịch của giờ đích và thời tiết đo muộn nhất lúc 11:00. Với bước 1, đáp án là số đo Zone 1 lúc 13:00. Với bước 24, đáp án là số đo lúc 12:00 ngày sau. Mỗi giờ phát hành tạo một dãy dự báo mới.")
    pic("demo.png",166,74)
    para("Hình 1. Đường thực đo được ghép sau dự báo để đối chiếu. Mô hình dùng trong demo được chọn bằng ba lượt kiểm định theo thời gian.",9)
    para(f"{title} được chọn trên dữ liệu phát triển. Trên tập kiểm thử, MAPE của mô hình là {number(winner['mape_percent'],3)}%, chấm trên {number(winner['n'],0)} cặp giờ phát hành và giờ đích.",12,True)
    page()
    head("2. Tập dữ liệu và phương pháp")
    para(f"ZIP chính thức của UCI chứa CSV với {number(audit['rows'],0)} dòng, từ 01/01 đến 30/12/2017. Có 8.736 mốc đúng giờ trên lịch nguồn. Kiểm toán cho thấy không thiếu mốc 10 phút, không trùng thời điểm và không thấy ô trống ở các cột gốc. Mức tải Zone 1 dao động từ {number(audit['value_stats']['load']['min'])} đến {number(audit['value_stats']['load']['max'])} theo đơn vị nguồn.")
    para("Hai trường thời gian giúp phân biệt thời điểm mô hình có thông tin và thời điểm cần dự báo. Với mỗi bước h, nhãn được tìm đúng tại T+h giờ. Hàng thiếu nhãn không được đưa vào phép chấm. Các hàng thiếu lịch sử cần thiết được giữ trong lưới dự kiến khi tính độ phủ.")
    grid(["Nhóm biến","Cách xây dựng"],[
        ["Phụ tải","Giá trị tại T, độ trễ 1, 2, 24, 168 giờ, trung bình và cực đại 24 số đo đúng giờ đã biết. Thêm tải tại giờ đích trừ 24 hoặc 168 giờ."],
        ["Lịch","Mã hóa sin/cos của giờ trong ngày, thứ trong tuần và ngày trong năm của giờ đích."],
        ["Thời tiết","Nhiệt độ, độ ẩm, gió và hai biến diffuse của UCI, tra tại đúng T−1 giờ. Hai vùng phụ tải còn lại không tham gia đầu vào."]], [34,134])
    para("Mỗi thuật toán học 24 mô hình độc lập, mỗi mô hình dự báo một bước. Toàn bộ phép chuẩn hóa được fit trong tập học của từng lượt.",10.5,True)
    grid(["Thuật toán","Nguyên lý và tham số"],[
         ["Ridge","Tối thiểu hóa tổng bình phương sai số cộng α nhân tổng bình phương hệ số. Chuẩn hóa đầu vào giúp mức phạt so sánh được giữa các biến."],
         ["Random Forest","Trung bình dự báo của nhiều cây xây trên các mẫu ngẫu nhiên. Giới hạn độ sâu và số điểm tối thiểu mỗi lá để kiểm soát độ phức tạp."],
         ["SVR RBF","Bỏ qua sai số trong dải ε, phạt phần vượt dải theo C. Kernel RBF đo độ gần của mẫu với độ rộng do γ điều khiển. Chuẩn hóa cả X và y, rồi đổi dự báo về đơn vị gốc."],
         ["Đối chứng","Dùng phụ tải đo đúng giờ đích hôm trước hoặc tuần trước. Cả hai giá trị đều có sẵn tại T cho h từ 1 đến 24."]],[34,134])
    para("Nguồn: Salam, A. & El Hibaoui, A. (2018), Power Consumption of Tetouan City, UCI Machine Learning Repository. DOI 10.24432/C5B034. Giấy phép CC BY 4.0. Bảng kiểm toán lưu SHA-256 của ZIP và CSV để nhận diện chính xác bản dữ liệu.")
    page()
    head("3. Kết quả thực nghiệm và đánh giá")
    para("Giữ 20% cuối lưới giờ để kiểm thử một lần. Ba lượt kiểm định trên 80% đầu mở rộng dần phần học, mỗi khối chấm dài 28 ngày. Chừa 24 giờ giữa các tập và chỉ chấm nhãn nằm trong khối tương ứng. Tập kiểm thử bắt đầu lúc "+q["eval_start"].replace("T"," ")+" theo đồng hồ của nguồn.")
    para("Seed 42. Tìm 4 cấu hình Ridge, 4 Random Forest và 3 SVR trên các bước 1, 6, 12 và 24. Chọn theo MAPE trung bình của các lượt và bước. Trong nhóm cách điểm thấp nhất dưới 0,1 điểm phần trăm, ưu tiên cấu hình nhanh hơn. Sau đó kiểm định đủ 24 bước và khóa lựa chọn trước tập cuối.")
    para("MAE là trung bình sai số tuyệt đối. RMSE lấy căn bậc hai của sai số bình phương trung bình, nên nhấn mạnh các lỗi lớn. MAPE là trung bình sai số tuyệt đối chia tải thực, nhân 100. Bảng dưới chấm trên đúng cùng các cặp giờ.")
    para("Trong lần chạy bàn giao, MAPE kiểm định trung bình của Ridge và RF lần lượt là "+number(frozen["validation_mape"]["ridge"],3)+"% và "+number(frozen["validation_mape"]["random_forest"],3)+"%. Lựa chọn theo quy tắc kiểm định là "+title+". Cấu hình Ridge dùng α = "+str(frozen["params"]["ridge"]["alpha"])+".",9)
    grid(["Mô hình","MAE","RMSE","MAPE (%)","MAPE tải cao (%)"],[
        [NAMES[k],number(r["mae"],1),number(r["rmse"],1),number(r["mape_percent"],3),number(points("high_load")[k]["mape_percent"],3)] for k,r in sorted(total.items(),key=lambda x:float(x[1]["mape_percent"]))],[43,27,27,30,41])
    para(f"Độ phủ chung {number(100*float(winner['coverage']))}% ({winner['n']}/{winner['expected_n']} cặp dự kiến). Mẫu số gồm cả các bước ở cuối khối có giờ đích vượt ranh giới. Ngưỡng tải cao là phân vị 90% của nhãn train tại các giờ đích phân biệt, bằng {number(q['threshold_q90'])}.")
    pic("horizons.png",166,70.5)
    para(f"Hình 2. Với {title}, MAPE bước 1 là {number(points('horizon',1)[name]['mape_percent'],3)}%, bước 24 là {number(points('horizon',24)[name]['mape_percent'],3)}%. Chi tiết từng bước và mùa có trong scores.csv.",9)
    page()
    head("3. Đánh giá thời tiết và giờ tải cao")
    para("Hai lượt Ridge dùng cùng α, nhãn, khoảng thời gian và hàng hợp lệ. Chỉ cột thời tiết thay đổi. Dấu âm trong hình biểu thị sai số khi thêm thời tiết thấp hơn.")
    pic("weather.png",166,53)
    grid(["Tập chấm","Số cặp","MAPE bỏ thời tiết","MAPE có thời tiết","Chênh (đpt)"],[
        ["Test" if r["split"]=="test" else "Validation "+r["fold"],r["n"],number(r["mape_no_weather"],3),number(r["mape_weather"],3),number(r["delta_mape_pp"],3)] for r in weather],[34,24,42,42,26])
    para(f"Trên tập kiểm thử, thay đổi MAPE là {number(dw['delta_mape_pp'],3)} điểm phần trăm. MAE thay đổi {number(dw['delta_mae'])} và RMSE thay đổi {number(dw['delta_rmse'])} theo đơn vị nguồn. Kết luận này áp dụng cho Ridge và độ trễ thời tiết một giờ.")
    if all(float(r["delta_mape_pp"])>0 for r in weather if r["split"]=="validation") and float(dw["delta_mape_pp"])<0:
        para("Cả ba khối kiểm định đều tăng MAPE khi thêm thời tiết, trong khi tập cuối giảm rất nhẹ. Lợi ích theo phần trăm chưa nhất quán qua thời gian. Lịch và phụ tải quá khứ có thể đã phản ánh một phần biến động thời tiết, nhưng phép thử này chưa xác định được nguyên nhân.",9)
    c=next(r for r in read("confusion") if r["split"]=="test" and r["model"]==name)
    para("Nhận diện tải cao bằng "+title,12,True)
    grid(["Thực đo / dự báo","Dưới ngưỡng","Tải cao"],[["Dưới ngưỡng",c["tn"],c["fp"]],["Tải cao",c["fn"],c["tp"]]],[63,50,55])
    para("Ngưỡng từ train áp dụng cho cả số đo và dự báo. Precision, recall và F1 lần lượt bằng "+", ".join(number(c[x],3) if c[x] else "không xác định" for x in ["precision","recall","f1"])+".")
    peaks=[r for r in read("peak_windows") if r["split"]=="test" and r["model"]==name]
    para(f"Trong {number(len(peaks),0)} cửa sổ đủ 24 giờ, sai số tuyệt đối trung bình của độ lớn đỉnh là {number(mean(float(r['peak_magnitude_abs_error']) for r in peaks))} và thời điểm đỉnh lệch trung bình {number(mean(float(r['peak_timing_abs_hours']) for r in peaks))} giờ. Khi hai giờ cùng đạt cực đại, lấy giờ sớm nhất.")
    page()
    head("4. Chức năng và sử dụng")
    para("Từ thư mục chứa readme.txt, cài requirements.txt. Lệnh python scripts/tetouan.py smoke chạy thử dữ liệu thật, một Ridge và đối chứng. Lệnh full huấn luyện, chấm và kiểm tra nạp lại. Lệnh demo nạp mô hình đã lưu, xuất forecast.csv và hình 24 giờ. Có thể dùng --origin để chọn giờ khác trong tập kiểm thử.")
    para("Mỗi lần chạy có thư mục riêng trong outputs/tetouan. Tệp latest.txt chỉ đến lần hoàn tất. readme.txt có lệnh chạy riêng cho từng thành viên và cách huấn luyện lại với cấu hình đã khóa.")
    head("5. Kiến trúc mã nguồn")
    grid(["Thành phần","Trách nhiệm"],[
        ["tetouan_data.py","prepare_data lưu nguồn và kiểm toán. Bộ tạo mẫu và forecast_features dùng chung cách tính từng cột ở thời điểm phát hành."],
        ["tetouan_models.py","train chọn cấu hình, fit riêng từng bước và lưu mô hình. predict_saved kiểm tra thời điểm, cột đầu vào, rồi trả dự báo đúng thứ tự."],
        ["tetouan_eval.py","make_splits chia lưới trước khi lọc. score chạy đối chứng, kiểm tra khóa, ghép kết quả và tính chỉ số trên các cặp giờ chung."],
        ["scripts/tetouan.py","Lệnh tích hợp, đo thời gian/RAM, kiểm tra một hàng thật và đối chiếu dự báo sau khi nạp mô hình."],
        ["Báo cáo và demo","tetouan_report.py sinh hình và xuất bảng. tetouan_pdf.py tạo PDF trực tiếp từ các tệp kết quả của lần chạy."]],[50,118])
    head("6. Khó khăn và giải pháp")
    para("Một dòng chỉ cách dòng kế 10 phút, nên dịch một dòng sẽ sai nhãn một giờ. Các phép tra cứu dùng timestamp và đã được thử với dòng bị thiếu. Sửa tải và thời tiết sau giờ phát hành giữ nguyên đầu vào và dự báo trong phép kiểm chứng. Phép kiểm tra ranh giới so trực tiếp nhãn train muộn nhất với origin kiểm định sớm nhất.")
    vr=js("verification")
    para(f"Kiểm tra nạp lại tất cả các bước và bốn cấu hình trên một origin thật với dung sai tuyệt đối 10⁻⁶ và tương đối 10⁻⁹. Chênh lệch lớn nhất quan sát được là {max(vr['max_abs_reload_error'].values()):.3g} đơn vị nguồn. verification.json lưu giá trị tải, nhiệt độ, nhãn và sai số để đối chiếu.")
    page()
    head("7. Phát hiện, giới hạn và hướng tiếp theo")
    for model in ["ridge","random_forest","svr"]:
        r=total[model]
        beat=[NAMES[b].lower() for b in ["day_prior","week_prior"] if float(r["mape_percent"])<float(total[b]["mape_percent"])]
        para(f"{NAMES[model]} đạt MAPE {number(r['mape_percent'],3)}% trên tập cuối. "+("Sai số thấp hơn đối chứng "+ " và ".join(beat)+"." if beat else "Cả hai đối chứng có sai số bằng hoặc thấp hơn."))
    para("Dữ liệu chỉ có một vùng đích và gần một năm lịch. Những mẫu đánh giá cuốn chiếu có giờ đích chồng lặp. Kết quả mô tả đúng đoạn kiểm thử cuối năm, chưa đủ để suy rộng qua các năm. UCI chưa xác nhận đơn vị vật lý, múi giờ và lịch công bố từng số đo. Mô phỏng giả định tải có ngay lúc đo, thời tiết trễ một giờ.")
    para("Nếu có thêm dữ liệu, có thể lặp lại theo năm, kiểm tra độ trễ công bố thực tế và khảo sát riêng các ngày có thay đổi mạnh ở phụ tải. Những hướng này cần được đánh giá trên thời gian chưa dùng để chọn mô hình.")
    para("Tài nguyên đo trên máy chạy",12,True)
    measured=js("prepare_resources")+js("run_resources")+js("inference_resources")
    grid(["Công đoạn","Giây","RAM đỉnh (MiB)"],[[r["stage"],number(r["seconds"],2),number(r["peak_rss_mb"],1)] for r in measured],[90,35,43])
    para("RSS được lấy mẫu định kỳ trong quá trình chạy. Các mô hình chạy tuần tự. Random Forest tối đa bốn luồng, phép toán BLAS giới hạn một luồng. Chi tiết từng nhóm huấn luyện có trong training_resources.csv.")
    para("Nguồn, phần kế thừa và công cụ",12,True)
    para("Dữ liệu và thời tiết: Salam & El Hibaoui, UCI Machine Learning Repository, DOI 10.24432/C5B034, CC BY 4.0. Mã dự án dùng lại CachedDownloader, build_model, temporal_folds và ResourceRecorder từ pipeline PJME. Phần mới xây dựng bộ mẫu Tetouan, huấn luyện, đánh giá và demo. Công cụ Codex hỗ trợ viết, chạy và kiểm tra mã. Thông tin đóng góp của sinh viên do nhóm điền.")
    para("Thư viện: NumPy và pandas để tính toán, PyArrow cho Parquet, scikit-learn huấn luyện, joblib lưu mô hình, psutil và threadpoolctl đo và giới hạn tài nguyên, Matplotlib và ReportLab dựng hình và PDF. Phiên bản được ghi trong requirements.txt và readme.txt. Khi bảo vệ, nêu rõ nguồn dữ liệu, công cụ và phần kế thừa.")
    pdf.build(items,onFirstPage=frame,onLaterPages=frame)
    print(DIR/"IT3190_Tetouan.pdf")

if __name__=="__main__":
    main()
