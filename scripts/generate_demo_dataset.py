"""Generator script to produce 10 realistic Vietnamese demo documents.

Generates:
- 2 PDF text (multi-page)
- 2 PDF scanned (pure raster image, no text layer) + ground truth
- 2 DOCX (headings, paragraphs, tables)
- 2 XLSX (multi-sheet, dates, empty cells)
- 2 Complex PDF (complex tables / 2-column layout)
"""

import datetime
import json
import os
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import pymupdf

BASE_DIR = Path("D:/rag/vietnamese-document-intelligence")
RAW_PDF_DIR = BASE_DIR / "data/raw/pdf"
RAW_DOCX_DIR = BASE_DIR / "data/raw/docx"
RAW_XLSX_DIR = BASE_DIR / "data/raw/xlsx"
GROUND_TRUTH_DIR = BASE_DIR / "data/ground_truth"
METADATA_DIR = BASE_DIR / "data/metadata"

FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_ITALIC = "C:/Windows/Fonts/ariali.ttf"


def setup_directories():
    for d in [RAW_PDF_DIR, RAW_DOCX_DIR, RAW_XLSX_DIR, GROUND_TRUTH_DIR, METADATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# =====================================================================
# 1. PDF Text 01: Hợp đồng dịch vụ CNTT (3 pages)
# =====================================================================
def create_pdf_text_01():
    filepath = RAW_PDF_DIR / "pdf_text_01_hop_dong_dich_vu_cntt.pdf"
    doc = pymupdf.open()

    # --- Page 1 ---
    page1 = doc.new_page(width=595, height=842)
    page1.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page1.insert_font(fontname="arbd", fontfile=FONT_BOLD)
    page1.insert_font(fontname="arit", fontfile=FONT_ITALIC)

    # National Header
    page1.insert_textbox(pymupdf.Rect(50, 40, 545, 80),
                         "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n----------o0o----------",
                         fontname="arbd", fontsize=11, align=pymupdf.TEXT_ALIGN_CENTER)

    # Disclaimer
    page1.insert_textbox(pymupdf.Rect(50, 85, 545, 105),
                         "[TÀI LIỆU DEMO GIẢ LẬP DÙNG CHO KIỂM THỬ HỆ THỐNG AI - KHÔNG CÓ GIÁ TRỊ PHÁP LÝ]",
                         fontname="arit", fontsize=8, align=pymupdf.TEXT_ALIGN_CENTER)

    # Title
    page1.insert_textbox(pymupdf.Rect(50, 115, 545, 160),
                         "HỢP ĐỒNG DỊCH VỤ CÔNG NGHỆ THÔNG TIN VÀ XỬ LÝ DỮ LIỆU\nSố: 102/2026/HĐDV-AI",
                         fontname="arbd", fontsize=13, align=pymupdf.TEXT_ALIGN_CENTER)

    # Content Page 1
    content_p1 = (
        "Hôm nay, ngày 16 tháng 11 năm 2026, tại văn phòng Hà Nội, chúng tôi gồm các bên:\n\n"
        "BÊN A (BÊN SỬ DỤNG DỊCH VỤ):\n"
        "CÔNG TY CỔ PHẦN CÔNG NGHỆ ALPHA VIỆT NAM\n"
        "- Đại diện: Ông Nguyễn Văn Nam - Chức vụ: Tổng Giám đốc\n"
        "- Địa chỉ: Tầng 12, Tòa nhà Sông Đà, Đường Phạm Hùng, Quận Nam Từ Liêm, Hà Nội\n"
        "- Mã số thuế: 0108998877 | Điện thoại: 024.3789.9999\n\n"
        "BÊN B (BÊN CUNG CẤP DỊCH VỤ):\n"
        "CÔNG TY TNHH GIẢI PHÁP DỮ LIỆU THÔNG MINH VIỆT\n"
        "- Đại diện: Bà Lê Thị Mai - Chức vụ: Giám đốc Điều hành\n"
        "- Địa chỉ: Tầng 8, Tòa nhà Innovation, Khu Công nghệ cao Láng - Hòa Lạc, Hà Nội\n"
        "- Mã số thuế: 0109112233 | Điện thoại: 024.3999.8888\n\n"
        "Hai bên cùng thống nhất ký kết Hợp đồng dịch vụ với các điều khoản cụ thể sau đây:\n\n"
        "ĐIỀU 1: PHẠM VI DỊCH VỤ VÀ MỤC TIÊU CÔNG VIỆC\n"
        "1.1 Bên B chịu trách nhiệm nghiên cứu, thiết kế và triển khai nền tảng Document Intelligence & RAG tiếng Việt "
        "nhằm tự động hóa việc đọc, phân loại, bóc tách dữ liệu từ các định dạng PDF, DOCX, XLSX của Bên A.\n"
        "1.2 Hệ thống phải đảm bảo khả năng mở rộng xử lý tối thiểu 50.000 tài liệu mỗi ngày, hỗ trợ bóc tách bảng biểu "
        "và phát hiện tự động tài liệu scan cần chuyển luồng xử lý OCR chuyên sâu."
    )
    page1.insert_textbox(pymupdf.Rect(50, 165, 545, 800), content_p1, fontname="ar", fontsize=10.5, lineheight=1.35)

    # --- Page 2 ---
    page2 = doc.new_page(width=595, height=842)
    page2.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page2.insert_font(fontname="arbd", fontfile=FONT_BOLD)

    content_p2 = (
        "ĐIỀU 2: TIÊU CHUẨN KỸ THUẬT VÀ QUY TRÌNH BÀN GIAO\n"
        "2.1 Tiêu chuẩn dịch vụ REST API:\n"
        "- Thời gian phản hồi trung bình cho endpoint trích xuất tài liệu: dưới 200ms với tài liệu tiêu chuẩn dưới 5 trang.\n"
        "- Giới hạn dung lượng upload tối đa cho mỗi file: 20 MB.\n"
        "- Mã trạng thái phản hồi HTTP tuân thủ nghiêm ngặt chuẩn RESTful (200, 400, 413, 415).\n"
        "2.2 Tiêu chuẩn trích xuất dữ liệu:\n"
        "- Tài liệu PDF: Đọc đầy đủ từng trang, giữ nguyên số trang và phát hiện trang scan qua cờ requires_ocr.\n"
        "- Tài liệu DOCX: Bảo toàn thứ tự tuần tự giữa các đoạn văn bản (paragraphs) và cấu trúc bảng (tables).\n"
        "- Tài liệu XLSX: Đọc toàn bộ các sheet, chuẩn hóa kiểu ngày tháng sang ISO 8601, bảo toàn giá trị ô trống (null).\n\n"
        "ĐIỀU 3: GIÁ TRỊ HỢP ĐỒNG VÀ PHƯƠNG THỨC THANH TOÁN\n"
        "3.1 Tổng giá trị hợp đồng: 850.000.000 VNĐ (Tám trăm năm mươi triệu đồng chẵn). Giá đã bao gồm thuế GTGT 10%.\n"
        "3.2 Lộ trình thanh toán được chia làm 03 đợt:\n"
        "- Đợt 1: Tạm ứng 30% giá trị hợp đồng tương đương 255.000.000 VNĐ trong vòng 05 ngày sau khi ký kết.\n"
        "- Đợt 2: Thanh toán 40% giá trị tương đương 340.000.000 VNĐ sau khi Bên B bàn giao Milestone 01 (Pipeline & API).\n"
        "- Đợt 3: Quyết toán 30% còn lại tương đương 255.000.000 VNĐ sau khi nghiệm thu toàn diện hệ thống.\n\n"
        "ĐIỀU 4: QUYỀN VÀ NGHĨA VỤ CỦA BÊN A\n"
        "4.1 Cung cấp đầy đủ tập dữ liệu demo đại diện (gồm PDF, DOCX, XLSX và tài liệu scan) để phục vụ kiểm thử.\n"
        "4.2 Bố trí nhân sự kỹ thuật phối hợp kiểm thử tích hợp API và nghiệm thu từng giai đoạn đúng tiến độ cam kết."
    )
    page2.insert_textbox(pymupdf.Rect(50, 50, 545, 800), content_p2, fontname="ar", fontsize=10.5, lineheight=1.35)

    # --- Page 3 ---
    page3 = doc.new_page(width=595, height=842)
    page3.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page3.insert_font(fontname="arbd", fontfile=FONT_BOLD)
    page3.insert_font(fontname="arit", fontfile=FONT_ITALIC)

    content_p3 = (
        "ĐIỀU 5: QUYỀN VÀ NGHĨA VỤ CỦA BÊN B\n"
        "5.1 Đảm bảo hệ thống vận hành liên tục, bảo mật tuyệt đối dữ liệu văn bản nội bộ của Bên A.\n"
        "5.2 Cung cấp đầy đủ tài liệu API, hướng dẫn triển khai trên nền tảng Docker và hỗ trợ kỹ thuật 24/7.\n"
        "5.3 Chịu trách nhiệm bảo hành, vá lỗi miễn phí trong thời gian 12 tháng kể từ ngày ký biên bản nghiệm thu.\n\n"
        "ĐIỀU 6: BẢO MẬT THÔNG TIN (NDA)\n"
        "6.1 Cả hai bên cam kết bảo mật toàn bộ dữ liệu tài liệu, mã nguồn và thông tin kinh doanh liên quan đến dự án.\n"
        "6.2 Không bên nào được phép cung cấp dữ liệu huấn luyện hoặc kết quả trích xuất cho bất kỳ bên thứ ba nào.\n\n"
        "ĐIỀU 7: HIỆU LỰC THI HÀNH VÀ KÝ KẾT\n"
        "7.1 Hợp đồng có hiệu lực kể từ ngày ký đến khi hai bên hoàn tất nghĩa vụ thanh lý hợp đồng.\n"
        "7.2 Hợp đồng được lập thành 04 bản có giá trị pháp lý như nhau, mỗi bên giữ 02 bản để thực hiện."
    )
    page3.insert_textbox(pymupdf.Rect(50, 50, 545, 450), content_p3, fontname="ar", fontsize=10.5, lineheight=1.35)

    # Signature Block
    page3.insert_textbox(pymupdf.Rect(50, 520, 280, 560), "ĐẠI DIỆN BÊN A\nTổng Giám đốc", fontname="arbd", fontsize=11, align=pymupdf.TEXT_ALIGN_CENTER)
    page3.insert_textbox(pymupdf.Rect(50, 565, 280, 600), "(Ký, ghi rõ họ tên và đóng dấu)", fontname="arit", fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
    page3.insert_textbox(pymupdf.Rect(50, 650, 280, 680), "Nguyễn Văn Nam", fontname="arbd", fontsize=11, align=pymupdf.TEXT_ALIGN_CENTER)

    page3.insert_textbox(pymupdf.Rect(315, 520, 545, 560), "ĐẠI DIỆN BÊN B\nGiám đốc Điều hành", fontname="arbd", fontsize=11, align=pymupdf.TEXT_ALIGN_CENTER)
    page3.insert_textbox(pymupdf.Rect(315, 565, 545, 600), "(Ký, ghi rõ họ tên và đóng dấu)", fontname="arit", fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
    page3.insert_textbox(pymupdf.Rect(315, 650, 545, 680), "Lê Thị Mai", fontname="arbd", fontsize=11, align=pymupdf.TEXT_ALIGN_CENTER)

    doc.save(filepath)
    doc.close()
    print(f"Generated: {filepath}")


# =====================================================================
# 2. PDF Text 02: Báo cáo tài chính quý (3 pages)
# =====================================================================
def create_pdf_text_02():
    filepath = RAW_PDF_DIR / "pdf_text_02_bao_cao_tai_chinh_quy.pdf"
    doc = pymupdf.open()

    # --- Page 1 ---
    page1 = doc.new_page(width=595, height=842)
    page1.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page1.insert_font(fontname="arbd", fontfile=FONT_BOLD)
    page1.insert_font(fontname="arit", fontfile=FONT_ITALIC)

    page1.insert_textbox(pymupdf.Rect(50, 50, 545, 90),
                         "CÔNG TY CỔ PHẦN CÔNG NGHỆ THÔNG MINH VIỆT\nSố 15 Đại lộ Thăng Long, Cầu Giấy, Hà Nội",
                         fontname="arbd", fontsize=10, align=pymupdf.TEXT_ALIGN_LEFT)

    page1.insert_textbox(pymupdf.Rect(50, 110, 545, 170),
                         "BÁO CÁO HOẠT ĐỘNG KINH DOANH VÀ TÀI CHÍNH QUÝ 3 NĂM 2026\n"
                         "Phân tích chuyên sâu hiệu quả đầu tư công nghệ AI và Dịch vụ Dữ liệu",
                         fontname="arbd", fontsize=14, align=pymupdf.TEXT_ALIGN_CENTER)

    page1.insert_textbox(pymupdf.Rect(50, 175, 545, 195),
                         "[TÀI LIỆU BÁO CÁO NỘI BỘ GIẢ LẬP DÙNG CHO MỤC ĐÍCH R&D VÀ KIỂM THỬ PIPELINE]",
                         fontname="arit", fontsize=8.5, align=pymupdf.TEXT_ALIGN_CENTER)

    content_p1 = (
        "I. THƯ NGỎ CỦA BAN TỔNG GIÁM ĐỐC\n\n"
        "Kính gửi Quý Cổ đông, Đối tác và toàn thể Cán bộ Nhân viên,\n\n"
        "Quý 3 năm 2026 ghi nhận bước chuyển mình chiến lược của công ty khi chính thức thương mại hóa các giải pháp "
        "Document Intelligence và Retrieval-Augmented Generation (RAG) phục vụ thị trường tài chính, ngân hàng và bảo hiểm. "
        "Trong bối cảnh làn sóng chuyển đổi số toàn diện tại Việt Nam, nhu cầu bóc tách tài liệu tiếng Việt tự động đã tăng trưởng "
        "vượt bậc với mức tăng 145% so với cùng kỳ năm trước.\n\n"
        "Các sản phẩm chủ lực bao gồm: Hệ thống bóc tách hóa đơn VAT điện tử, nền tảng phân tích hợp đồng kinh tế và "
        "trợ lý ảo pháp lý phục vụ cán bộ thẩm định tín dụng. Nhờ đầu tư bài bản vào hạ tầng xử lý văn bản tiếng Việt "
        "kết hợp mô hình trích xuất đa định dạng, biên lợi nhuận gộp của khối dịch vụ phần mềm đã đạt mức kỷ lục 48.5%.\n\n"
        "Chúng tôi xin gửi lời cảm ơn chân thành đến toàn thể đội ngũ kỹ sư AI, các chuyên gia dữ liệu và quý khách hàng "
        "đã luôn tin tưởng, đồng hành cùng sự phát triển bền vững của doanh nghiệp."
    )
    page1.insert_textbox(pymupdf.Rect(50, 210, 545, 800), content_p1, fontname="ar", fontsize=10.5, lineheight=1.4)

    # --- Page 2 ---
    page2 = doc.new_page(width=595, height=842)
    page2.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page2.insert_font(fontname="arbd", fontfile=FONT_BOLD)

    content_p2_header = (
        "II. KẾT QUẢ TÀI CHÍNH TỔNG HỢP QUÝ 3 NĂM 2026\n\n"
        "Đơn vị tính: Triệu Việt Nam Đồng (VND)\n"
        "Bảng 1 dưới đây tổng hợp các chỉ số kinh doanh chính trong kỳ báo cáo so sánh với Quý 2/2026 và mục tiêu đề ra:"
    )
    page2.insert_textbox(pymupdf.Rect(50, 50, 545, 120), content_p2_header, fontname="ar", fontsize=10.5)

    # Draw table
    table_x = 50
    table_y = 130
    row_height = 24
    col_widths = [195, 100, 100, 100]

    headers = ["Chỉ tiêu tài chính", "Quý 2/2026", "Quý 3/2026", "Tăng trưởng"]
    rows = [
        ["1. Doanh thu thuần bán hàng", "42.500", "58.200", "+ 36.9%"],
        ["- Mảng Giải pháp AI & RAG", "18.200", "28.900", "+ 58.8%"],
        ["- Mảng Cloud & Hạ tầng dữ liệu", "15.100", "18.500", "+ 22.5%"],
        ["- Mảng Dịch vụ bảo trì, đào tạo", "9.200", "10.800", "+ 17.4%"],
        ["2. Giá vốn hàng bán (COGS)", "23.800", "29.970", "+ 25.9%"],
        ["3. Lợi nhuận gộp", "18.700", "28.230", "+ 51.0%"],
        ["4. Chi phí nghiên cứu & phát triển (R&D)", "5.400", "7.800", "+ 44.4%"],
        ["5. Chi phí bán hàng & Quản lý doanh nghiệp", "6.200", "7.100", "+ 14.5%"],
        ["6. Lợi nhuận trước thuế (EBT)", "7.100", "13.330", "+ 87.7%"],
        ["7. Lợi nhuận sau thuế (NPAT)", "5.680", "10.664", "+ 87.7%"],
    ]

    # Draw Header
    cur_x = table_x
    for i, h in enumerate(headers):
        rect = pymupdf.Rect(cur_x, table_y, cur_x + col_widths[i], table_y + row_height)
        page2.draw_rect(rect, color=(0.4, 0.4, 0.4), fill=(0.9, 0.93, 0.98), width=0.5)
        page2.insert_textbox(rect, h, fontname="arbd", fontsize=9.5, align=pymupdf.TEXT_ALIGN_CENTER)
        cur_x += col_widths[i]

    # Draw Rows
    cur_y = table_y + row_height
    for row_idx, r in enumerate(rows):
        cur_x = table_x
        bg = (0.97, 0.97, 0.97) if row_idx % 2 == 1 else (1, 1, 1)
        for col_idx, cell in enumerate(r):
            rect = pymupdf.Rect(cur_x, cur_y, cur_x + col_widths[col_idx], cur_y + row_height)
            page2.draw_rect(rect, color=(0.6, 0.6, 0.6), fill=bg, width=0.5)
            font_to_use = "arbd" if "1." in cell or "3." in cell or "6." in cell or "7." in cell else "ar"
            align_to_use = pymupdf.TEXT_ALIGN_LEFT if col_idx == 0 else pymupdf.TEXT_ALIGN_RIGHT
            page2.insert_textbox(pymupdf.Rect(cur_x + 5, cur_y + 3, cur_x + col_widths[col_idx] - 5, cur_y + row_height),
                                 cell, fontname=font_to_use, fontsize=9, align=align_to_use)
            cur_x += col_widths[col_idx]
        cur_y += row_height

    # Commentary after table
    content_p2_footer = (
        "\nNhận xét kết quả kinh doanh:\n"
        "Mảng Giải pháp AI & RAG tiếp tục là động lực tăng trưởng chính, đóng góp 49.6% vào tổng doanh thu toàn công ty. "
        "Chi phí R&D tăng tương ứng phản ánh chiến lược mở rộng năng lực xử lý tài liệu đa định dạng và chuẩn bị "
        "cho việc tích hợp các mô hình OCR và Vector Database tiên tiến trong các quý tiếp theo."
    )
    page2.insert_textbox(pymupdf.Rect(50, cur_y + 10, 545, 800), content_p2_footer, fontname="ar", fontsize=10, lineheight=1.35)

    # --- Page 3 ---
    page3 = doc.new_page(width=595, height=842)
    page3.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page3.insert_font(fontname="arbd", fontfile=FONT_BOLD)

    content_p3 = (
        "III. ĐÁNH GIÁ RỦI RO VÀ BIỆN PHÁP QUẢN TRỊ\n\n"
        "1. Rủi ro hạ tầng điện toán đám mây và GPU:\n"
        "- Tình trạng khan hiếm chip tính toán hiệu năng cao có thể ảnh hưởng đến chi phí vận hành mô hình lớn.\n"
        "- Biện pháp: Tối ưu hóa pipeline tiền xử lý bằng cách phân tách rõ ràng tài liệu có text layer và tài liệu scan, "
        "chỉ kích hoạt worker GPU cho tác vụ OCR thực sự cần thiết.\n\n"
        "2. Rủi ro bảo mật thông tin và tuân thủ dữ liệu cá nhân:\n"
        "- Các quy định của Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân đặt ra yêu cầu nghiêm ngặt đối với "
        "việc trích xuất và lưu trữ tài liệu hợp đồng, hóa đơn.\n"
        "- Biện pháp: Xây dựng cơ chế xử lý dữ liệu in-memory, không lưu trữ file tạm trên ổ đĩa nếu không được cấp phép.\n\n"
        "IV. KẾ HOẠCH VÀ MỤC TIÊU CHIẾN LƯỢC QUÝ 4 NĂM 2026\n\n"
        "- Mục tiêu doanh thu Quý 4: Đạt 75.000 triệu VND (tăng trưởng 28.8% so với Quý 3).\n"
        "- Hoàn thành triển khai Milestone 02: Tích hợp mô hình PaddleOCR tiếng Việt để xử lý 100% tài liệu scan.\n"
        "- Ra mắt phiên bản thử nghiệm cổng API RAG cho phép tìm kiếm ngữ nghĩa trên kho 1.000.000 tài liệu PDF.\n\n"
        "Hà Nội, ngày 16 tháng 11 năm 2026\n"
        "TM. BAN TỔNG GIÁM ĐỐC\n"
        "Giám đốc Tài chính (CFO)\n\n\n\n"
        "Trần Minh Hoàng"
    )
    page3.insert_textbox(pymupdf.Rect(50, 50, 545, 800), content_p3, fontname="ar", fontsize=10.5, lineheight=1.4)

    doc.save(filepath)
    doc.close()
    print(f"Generated: {filepath}")


# =====================================================================
# 3. PDF Scan 01: Hóa đơn VAT (Raster Scan, No Text Layer)
# =====================================================================
def create_pdf_scan_01():
    filepath = RAW_PDF_DIR / "pdf_scan_01_hoa_don_vat.pdf"
    gt_txt_path = GROUND_TRUTH_DIR / "pdf_scan_01_hoa_don_vat.txt"
    gt_json_path = GROUND_TRUTH_DIR / "pdf_scan_01_hoa_don_vat.json"

    # Step 1: Render rich temporary document
    temp_doc = pymupdf.open()
    page = temp_doc.new_page(width=595, height=842)
    page.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page.insert_font(fontname="arbd", fontfile=FONT_BOLD)
    page.insert_font(fontname="arit", fontfile=FONT_ITALIC)

    # Header
    page.insert_textbox(pymupdf.Rect(40, 35, 380, 80),
                         "CÔNG TY CỔ PHẦN THƯƠNG MẠI & DỊCH VỤ SỐ VIỆT\n"
                         "Mã số thuế: 0108998877\n"
                         "Địa chỉ: Số 88 Phố Huế, Phường Hàng Bài, Quận Hoàn Kiếm, Hà Nội\n"
                         "Điện thoại: 024.3988.6666 | Số tài khoản: 1100223344 tại Vietcombank",
                         fontname="ar", fontsize=9.5)

    page.insert_textbox(pymupdf.Rect(390, 35, 555, 80),
                         "Mẫu số: 01GTKT0/001\n"
                         "Ký hiệu: AA/26E\n"
                         "Số: 0004589\n"
                         "Ngày: 16/11/2026",
                         fontname="arbd", fontsize=10, align=pymupdf.TEXT_ALIGN_RIGHT)

    # Title
    page.insert_textbox(pymupdf.Rect(40, 95, 555, 135),
                         "HÓA ĐƠN GIÁ TRỊ GIA TĂNG (VAT INVOICE)\n(BẢN THỂ HIỆN HÓA ĐƠN ĐIỆN TỬ DẠNG QUÉT SCAN)",
                         fontname="arbd", fontsize=13, align=pymupdf.TEXT_ALIGN_CENTER)

    # Customer info
    cust_info = (
        "Đơn vị mua hàng: CÔNG TY TNHH PHÁT TRIỂN CÔNG NGHỆ THĂNG LONG\n"
        "Mã số thuế: 0107776655\n"
        "Địa chỉ: Tầng 5, Tòa nhà Technosoft, Phố Duy Tân, Phường Dịch Vọng Hậu, Quận Cầu Giấy, Hà Nội\n"
        "Hình thức thanh toán: Chuyển khoản (TM/CK) | Đồng tiền thanh toán: VND"
    )
    page.insert_textbox(pymupdf.Rect(40, 140, 555, 195), cust_info, fontname="ar", fontsize=9.5, lineheight=1.3)

    # Table of goods
    table_x = 40
    table_y = 205
    col_w = [30, 235, 45, 45, 80, 80]
    headers = ["STT", "Tên hàng hóa, dịch vụ", "ĐVT", "SL", "Đơn giá", "Thành tiền"]

    items = [
        ["1", "Máy chủ chuyên dụng AI Server H100 GPU", "Bộ", "1", "750.000.000", "750.000.000"],
        ["2", "Thiết bị cân bằng tải mạng 10Gbps Enterprise", "Chiếc", "2", "45.000.000", "90.000.000"],
        ["3", "Bản quyền phần mềm hệ điều hành máy chủ RedHat", "License", "5", "12.000.000", "60.000.000"],
        ["4", "Gói dịch vụ hỗ trợ kỹ thuật và bảo trì hệ thống 12 tháng", "Gói", "1", "50.000.000", "50.000.000"],
    ]

    # Draw header
    cur_x = table_x
    for i, h in enumerate(headers):
        rect = pymupdf.Rect(cur_x, table_y, cur_x + col_w[i], table_y + 22)
        page.draw_rect(rect, color=(0.2, 0.2, 0.2), fill=(0.92, 0.92, 0.92), width=0.8)
        page.insert_textbox(rect, h, fontname="arbd", fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
        cur_x += col_w[i]

    # Draw items
    cur_y = table_y + 22
    for item in items:
        cur_x = table_x
        for i, val in enumerate(item):
            rect = pymupdf.Rect(cur_x, cur_y, cur_x + col_w[i], cur_y + 22)
            page.draw_rect(rect, color=(0.4, 0.4, 0.4), fill=(1, 1, 1), width=0.5)
            align = pymupdf.TEXT_ALIGN_CENTER if i in (0, 2, 3) else (pymupdf.TEXT_ALIGN_RIGHT if i in (4, 5) else pymupdf.TEXT_ALIGN_LEFT)
            padding_x = 4 if align == pymupdf.TEXT_ALIGN_LEFT else (0 if align == pymupdf.TEXT_ALIGN_CENTER else -4)
            page.insert_textbox(pymupdf.Rect(cur_x + 3, cur_y + 3, cur_x + col_w[i] - 3, cur_y + 22),
                                 val, fontname="ar", fontsize=8.5, align=align)
            cur_x += col_w[i]
        cur_y += 22

    # Empty rows simulation
    for _ in range(2):
        cur_x = table_x
        for i in range(len(col_w)):
            rect = pymupdf.Rect(cur_x, cur_y, cur_x + col_w[i], cur_y + 20)
            page.draw_rect(rect, color=(0.4, 0.4, 0.4), fill=(1, 1, 1), width=0.5)
            cur_x += col_w[i]
        cur_y += 20

    # Summary rows
    sum_rect_label = pymupdf.Rect(table_x, cur_y, table_x + 435, cur_y + 22)
    sum_rect_val = pymupdf.Rect(table_x + 435, cur_y, table_x + 515, cur_y + 22)
    page.draw_rect(sum_rect_label, color=(0.4, 0.4, 0.4), fill=(0.96, 0.96, 0.96), width=0.5)
    page.draw_rect(sum_rect_val, color=(0.4, 0.4, 0.4), fill=(1, 1, 1), width=0.5)
    page.insert_textbox(pymupdf.Rect(table_x + 5, cur_y + 3, table_x + 430, cur_y + 22), "Cộng tiền hàng (Total amount):", fontname="arbd", fontsize=9)
    page.insert_textbox(sum_rect_val, "950.000.000", fontname="arbd", fontsize=9, align=pymupdf.TEXT_ALIGN_RIGHT)
    cur_y += 22

    tax_rect_label = pymupdf.Rect(table_x, cur_y, table_x + 435, cur_y + 22)
    tax_rect_val = pymupdf.Rect(table_x + 435, cur_y, table_x + 515, cur_y + 22)
    page.draw_rect(tax_rect_label, color=(0.4, 0.4, 0.4), fill=(0.96, 0.96, 0.96), width=0.5)
    page.draw_rect(tax_rect_val, color=(0.4, 0.4, 0.4), fill=(1, 1, 1), width=0.5)
    page.insert_textbox(pymupdf.Rect(table_x + 5, cur_y + 3, table_x + 430, cur_y + 22), "Thuế suất GTGT (VAT rate): 10%  -  Tiền thuế GTGT:", fontname="arbd", fontsize=9)
    page.insert_textbox(tax_rect_val, "95.000.000", fontname="arbd", fontsize=9, align=pymupdf.TEXT_ALIGN_RIGHT)
    cur_y += 22

    total_rect_label = pymupdf.Rect(table_x, cur_y, table_x + 435, cur_y + 24)
    total_rect_val = pymupdf.Rect(table_x + 435, cur_y, table_x + 515, cur_y + 24)
    page.draw_rect(total_rect_label, color=(0.2, 0.2, 0.2), fill=(0.9, 0.93, 0.98), width=0.8)
    page.draw_rect(total_rect_val, color=(0.2, 0.2, 0.2), fill=(0.9, 0.93, 0.98), width=0.8)
    page.insert_textbox(pymupdf.Rect(table_x + 5, cur_y + 4, table_x + 430, cur_y + 24), "TỔNG CỘNG TIỀN THANH TOÁN (TOTAL PAYMENT):", fontname="arbd", fontsize=9.5)
    page.insert_textbox(total_rect_val, "1.045.000.000", fontname="arbd", fontsize=9.5, align=pymupdf.TEXT_ALIGN_RIGHT)
    cur_y += 24

    # Amount in words
    words_info = "Số tiền viết bằng chữ: Một tỷ không trăm bốn mươi lăm triệu đồng chẵn."
    page.insert_textbox(pymupdf.Rect(40, cur_y + 8, 555, cur_y + 28), words_info, fontname="arit", fontsize=9.5)

    # Signatures
    cur_y += 35
    page.insert_textbox(pymupdf.Rect(60, cur_y, 250, cur_y + 40), "NGƯỜI MUA HÀNG\n(Ký, ghi rõ họ tên)", fontname="arbd", fontsize=9.5, align=pymupdf.TEXT_ALIGN_CENTER)
    page.insert_textbox(pymupdf.Rect(340, cur_y, 530, cur_y + 40), "NGƯỜI BÁN HÀNG\n(Ký, đóng dấu, ghi rõ họ tên)", fontname="arbd", fontsize=9.5, align=pymupdf.TEXT_ALIGN_CENTER)

    page.insert_textbox(pymupdf.Rect(60, cur_y + 85, 250, cur_y + 110), "Trần Quốc Cường", fontname="ar", fontsize=10, align=pymupdf.TEXT_ALIGN_CENTER)
    page.insert_textbox(pymupdf.Rect(340, cur_y + 85, 530, cur_y + 110), "Vũ Hải Đăng\n(Đã ký điện tử hợp lệ)", fontname="arbd", fontsize=9.5, align=pymupdf.TEXT_ALIGN_CENTER)

    # Stamp simulation
    page.draw_circle(pymupdf.Point(435, cur_y + 70), 32, color=(0.85, 0.15, 0.15), width=1.5)
    page.insert_textbox(pymupdf.Rect(405, cur_y + 55, 465, cur_y + 85), "ĐÃ KÝ\n2026-11-16", fontname="arbd", fontsize=8, align=pymupdf.TEXT_ALIGN_CENTER)

    # Step 2: Extract Ground Truth Text from temp_doc BEFORE rasterizing
    ground_truth_text = page.get_text("text").strip()

    # Step 3: Render page to raster image pixmap (150 DPI)
    pix = page.get_pixmap(dpi=150)
    temp_doc.close()

    # Step 4: Create final pure scanned PDF (IMAGE ONLY, NO TEXT LAYER)
    scan_doc = pymupdf.open()
    scan_page = scan_doc.new_page(width=595, height=842)
    scan_page.insert_image(scan_page.rect, pixmap=pix)
    scan_doc.save(filepath)
    scan_doc.close()

    # Step 5: Save Ground Truth
    with open(gt_txt_path, "w", encoding="utf-8") as f:
        f.write(ground_truth_text)

    gt_data = {
        "filename": "pdf_scan_01_hoa_don_vat.pdf",
        "document_type": "invoice",
        "invoice_number": "0004589",
        "template_code": "01GTKT0/001",
        "symbol": "AA/26E",
        "date": "2026-11-16",
        "seller": {
            "name": "CÔNG TY CỔ PHẦN THƯƠNG MẠI & DỊCH VỤ SỐ VIỆT",
            "tax_code": "0108998877",
            "address": "Số 88 Phố Huế, Phường Hàng Bài, Quận Hoàn Kiếm, Hà Nội"
        },
        "buyer": {
            "name": "CÔNG TY TNHH PHÁT TRIỂN CÔNG NGHỆ THĂNG LONG",
            "tax_code": "0107776655",
            "address": "Tầng 5, Tòa nhà Technosoft, Phố Duy Tân, Phường Dịch Vọng Hậu, Quận Cầu Giấy, Hà Nội"
        },
        "items": [
            {"stt": "1", "name": "Máy chủ chuyên dụng AI Server H100 GPU", "unit": "Bộ", "qty": 1, "unit_price": 750000000, "total": 750000000},
            {"stt": "2", "name": "Thiết bị cân bằng tải mạng 10Gbps Enterprise", "unit": "Chiếc", "qty": 2, "unit_price": 45000000, "total": 90000000},
            {"stt": "3", "name": "Bản quyền phần mềm hệ điều hành máy chủ RedHat", "unit": "License", "qty": 5, "unit_price": 12000000, "total": 60000000},
            {"stt": "4", "name": "Gói dịch vụ hỗ trợ kỹ thuật và bảo trì hệ thống 12 tháng", "unit": "Gói", "qty": 1, "unit_price": 50000000, "total": 50000000}
        ],
        "subtotal": 950000000,
        "vat_rate": "10%",
        "vat_amount": 95000000,
        "total_amount": 1045000000,
        "total_words": "Một tỷ không trăm bốn mươi lăm triệu đồng chẵn.",
        "raw_ground_truth_text": ground_truth_text
    }
    with open(gt_json_path, "w", encoding="utf-8") as f:
        json.dump(gt_data, f, ensure_ascii=False, indent=2)

    print(f"Generated Scanned PDF: {filepath}")
    print(f"Saved Ground Truth: {gt_txt_path}")


# =====================================================================
# 4. PDF Scan 02: Biên bản nghiệm thu (Raster Scan, No Text Layer)
# =====================================================================
def create_pdf_scan_02():
    filepath = RAW_PDF_DIR / "pdf_scan_02_bien_ban_nghiem_thu.pdf"
    gt_txt_path = GROUND_TRUTH_DIR / "pdf_scan_02_bien_ban_nghiem_thu.txt"
    gt_json_path = GROUND_TRUTH_DIR / "pdf_scan_02_bien_ban_nghiem_thu.json"

    # Step 1: Render temporary document
    temp_doc = pymupdf.open()
    page = temp_doc.new_page(width=595, height=842)
    page.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page.insert_font(fontname="arbd", fontfile=FONT_BOLD)
    page.insert_font(fontname="arit", fontfile=FONT_ITALIC)

    page.insert_textbox(pymupdf.Rect(50, 40, 545, 80),
                         "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n----------***----------",
                         fontname="arbd", fontsize=11, align=pymupdf.TEXT_ALIGN_CENTER)

    page.insert_textbox(pymupdf.Rect(50, 95, 545, 140),
                         "BIÊN BẢN NGHIỆM THU VÀ BÀN GIAO SẢN PHẨM\n"
                         "Dự án: Nền tảng Document Intelligence & Pipeline Trích xuất Dữ liệu",
                         fontname="arbd", fontsize=13, align=pymupdf.TEXT_ALIGN_CENTER)

    content_top = (
        "- Căn cứ Hợp đồng dịch vụ công nghệ số 102/2026/HĐDV-AI ký ngày 16/11/2026;\n"
        "- Căn cứ kết quả kiểm thử hệ thống tự động và biên bản kiểm thử kỹ thuật nội bộ.\n\n"
        "Hôm nay, ngày 16 tháng 11 năm 2026, tại trụ sở Bên A, chúng tôi tiến hành nghiệm thu gồm:\n\n"
        "BÊN GIAO (BÊN B): CÔNG TY TNHH GIẢI PHÁP DỮ LIỆU THÔNG MINH VIỆT\n"
        "- Đại diện: Bà Lê Thị Mai - Chức vụ: Giám đốc Điều hành\n"
        "- Cán bộ kỹ thuật: Ông Phạm Hoàng Long - Trưởng nhóm Kiến trúc sư AI\n\n"
        "BÊN NHẬN (BÊN A): CÔNG TY CỔ PHẦN CÔNG NGHỆ ALPHA VIỆT NAM\n"
        "- Đại diện: Ông Nguyễn Văn Nam - Chức vụ: Tổng Giám đốc\n"
        "- Cán bộ phụ trách: Ông Đỗ Minh Tuấn - Trưởng phòng Công nghệ thông tin\n\n"
        "Sau khi rà soát và kiểm tra thực tế, hai bên thống nhất các nội dung nghiệm thu sau:"
    )
    page.insert_textbox(pymupdf.Rect(50, 145, 545, 335), content_top, fontname="ar", fontsize=9.5, lineheight=1.35)

    # Table of Acceptance
    table_x = 50
    table_y = 345
    col_w = [35, 235, 125, 100]
    headers = ["STT", "Hạng mục bàn giao", "Tiêu chuẩn kỹ thuật", "Kết quả nghiệm thu"]
    rows = [
        ["1", "Module trích xuất PDF (PyMuPDF)", "Trích xuất từng trang, cờ OCR", "ĐẠT (100%)"],
        ["2", "Module trích xuất DOCX (python-docx)", "Bảo toàn thứ tự văn bản & bảng", "ĐẠT (100%)"],
        ["3", "Module trích xuất XLSX (openpyxl)", "Đọc đa sheet, chuẩn hóa ISO date", "ĐẠT (100%)"],
        ["4", "Hệ thống REST API (FastAPI)", "GET /health, POST /parse (20MB)", "ĐẠT (100%)"],
        ["5", "Bộ kiểm thử tự động (pytest)", "25/25 test cases passed", "ĐẠT (100%)"],
        ["6", "Tài liệu kỹ thuật & Hướng dẫn (README)", "Cấu trúc, cài đặt và ví dụ cURL", "ĐẠT (100%)"],
    ]

    # Draw header
    cur_x = table_x
    for i, h in enumerate(headers):
        rect = pymupdf.Rect(cur_x, table_y, cur_x + col_w[i], table_y + 22)
        page.draw_rect(rect, color=(0.3, 0.3, 0.3), fill=(0.92, 0.94, 0.98), width=0.6)
        page.insert_textbox(rect, h, fontname="arbd", fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
        cur_x += col_w[i]

    cur_y = table_y + 22
    for r in rows:
        cur_x = table_x
        for i, val in enumerate(r):
            rect = pymupdf.Rect(cur_x, cur_y, cur_x + col_w[i], cur_y + 22)
            page.draw_rect(rect, color=(0.5, 0.5, 0.5), fill=(1, 1, 1), width=0.5)
            align = pymupdf.TEXT_ALIGN_CENTER if i in (0, 3) else pymupdf.TEXT_ALIGN_LEFT
            page.insert_textbox(pymupdf.Rect(cur_x + 4, cur_y + 3, cur_x + col_w[i] - 4, cur_y + 22),
                                 val, fontname="ar", fontsize=8.5, align=align)
            cur_x += col_w[i]
        cur_y += 22

    content_bottom = (
        "KẾT LUẬN CỦA HỘI ĐỒNG NGHIỆM THU:\n"
        "1. Toàn bộ các hạng mục công việc Milestone 01 đã được Bên B triển khai đầy đủ, đúng tiến độ và "
        "đạt tất cả các yêu cầu kỹ thuật quy định trong Hợp đồng số 102/2026/HĐDV-AI.\n"
        "2. Bên A chính thức tiếp nhận hệ thống mã nguồn, bộ tài liệu và đồng ý thanh toán đợt 2 cho Bên B.\n"
        "Biên bản được lập thành 04 bản gốc có giá trị như nhau, mỗi bên giữ 02 bản để lưu trữ."
    )
    page.insert_textbox(pymupdf.Rect(50, cur_y + 15, 545, 620), content_bottom, fontname="ar", fontsize=9.5, lineheight=1.35)

    # Signatures
    cur_y = 635
    page.insert_textbox(pymupdf.Rect(60, cur_y, 250, cur_y + 40), "ĐẠI DIỆN BÊN GIAO (BÊN B)\n(Ký và đóng dấu)", fontname="arbd", fontsize=9.5, align=pymupdf.TEXT_ALIGN_CENTER)
    page.insert_textbox(pymupdf.Rect(340, cur_y, 530, cur_y + 40), "ĐẠI DIỆN BÊN NHẬN (BÊN A)\n(Ký và đóng dấu)", fontname="arbd", fontsize=9.5, align=pymupdf.TEXT_ALIGN_CENTER)

    page.insert_textbox(pymupdf.Rect(60, cur_y + 75, 250, cur_y + 105), "Lê Thị Mai", fontname="arbd", fontsize=10, align=pymupdf.TEXT_ALIGN_CENTER)
    page.insert_textbox(pymupdf.Rect(340, cur_y + 75, 530, cur_y + 105), "Nguyễn Văn Nam", fontname="arbd", fontsize=10, align=pymupdf.TEXT_ALIGN_CENTER)

    # Stamp
    page.draw_circle(pymupdf.Point(435, cur_y + 70), 30, color=(0.8, 0.1, 0.1), width=1.5)
    page.insert_textbox(pymupdf.Rect(405, cur_y + 55, 465, cur_y + 85), "ALPHA CORP\nĐÃ DUYỆT", fontname="arbd", fontsize=7.5, align=pymupdf.TEXT_ALIGN_CENTER)

    # Ground truth extract
    ground_truth_text = page.get_text("text").strip()
    pix = page.get_pixmap(dpi=150)
    temp_doc.close()

    # Create scan PDF
    scan_doc = pymupdf.open()
    scan_page = scan_doc.new_page(width=595, height=842)
    scan_page.insert_image(scan_page.rect, pixmap=pix)
    scan_doc.save(filepath)
    scan_doc.close()

    with open(gt_txt_path, "w", encoding="utf-8") as f:
        f.write(ground_truth_text)

    gt_data = {
        "filename": "pdf_scan_02_bien_ban_nghiem_thu.pdf",
        "document_type": "handover_acceptance_record",
        "contract_reference": "102/2026/HĐDV-AI",
        "date": "2026-11-16",
        "party_a": "CÔNG TY CỔ PHẦN CÔNG NGHỆ ALPHA VIỆT NAM",
        "party_b": "CÔNG TY TNHH GIẢI PHÁP DỮ LIỆU THÔNG MINH VIỆT",
        "milestone": "Milestone 01: Document Processing Pipeline & REST API",
        "evaluation_criteria": [
            {"item": "Module trích xuất PDF (PyMuPDF)", "result": "ĐẠT (100%)"},
            {"item": "Module trích xuất DOCX (python-docx)", "result": "ĐẠT (100%)"},
            {"item": "Module trích xuất XLSX (openpyxl)", "result": "ĐẠT (100%)"},
            {"item": "Hệ thống REST API (FastAPI)", "result": "ĐẠT (100%)"},
            {"item": "Bộ kiểm thử tự động (pytest)", "result": "ĐẠT (100%)"},
            {"item": "Tài liệu kỹ thuật & Hướng dẫn (README)", "result": "ĐẠT (100%)"}
        ],
        "conclusion": "Toàn bộ các hạng mục công việc Milestone 01 đã được nghiệm thu đạt 100%.",
        "raw_ground_truth_text": ground_truth_text
    }
    with open(gt_json_path, "w", encoding="utf-8") as f:
        json.dump(gt_data, f, ensure_ascii=False, indent=2)

    print(f"Generated Scanned PDF: {filepath}")
    print(f"Saved Ground Truth: {gt_txt_path}")


# =====================================================================
# 5. DOCX 01: Quy chế nội bộ doanh nghiệp
# =====================================================================
def create_docx_01():
    filepath = RAW_DOCX_DIR / "docx_01_quy_che_noi_bo_doanh_nghiep.docx"
    doc = docx.Document()

    # Title
    p_title = doc.add_heading(level=0)
    run_title = p_title.add_run("QUY CHẾ QUẢN LÝ NỘI BỘ VÀ CHÍNH SÁCH ĐÃI NGỘ NHÂN TÀI AI")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Disclaimer
    p_disc = doc.add_paragraph()
    r_disc = p_disc.add_run("[TÀI LIỆU QUY CHẾ NỘI BỘ GIẢ LẬP PHỤC VỤ THỬ NGHIỆM HỆ THỐNG TRÍCH XUẤT VĂN BẢN]")
    r_disc.font.size = Pt(9)
    r_disc.font.italic = True
    p_disc.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Chapter 1
    doc.add_heading("CHƯƠNG I: QUY ĐỊNH CHUNG VỀ CHẾ ĐỘ LÀM VIỆC VÀ NỀ NẾP", level=1)
    doc.add_paragraph(
        "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng:\n"
        "Quy chế này quy định về thời giờ làm việc, thời giờ nghỉ ngơi, văn hóa công sở, khung bậc lương, "
        "tiêu chuẩn chức danh nghề nghiệp và chính sách khen thưởng kỷ luật áp dụng đối với toàn thể cán bộ "
        "nhân viên, kỹ sư phần mềm, nhà nghiên cứu AI đang công tác tại công ty."
    )
    doc.add_paragraph(
        "Điều 2. Chế độ làm việc linh hoạt (Hybrid Working):\n"
        "1. Khối kỹ thuật và R&D được áp dụng mô hình làm việc linh hoạt: tối thiểu 03 ngày làm việc tại văn phòng "
        "và tối đa 02 ngày làm việc từ xa (Remote) mỗi tuần.\n"
        "2. Nhân viên phải đảm bảo tham gia đầy đủ các buổi họp giao ban kỹ thuật (Daily Standup) và duy trì kết nối "
        "trên hệ thống trao đổi công việc nội bộ trong khung giờ hành chính từ 08:30 đến 17:30."
    )

    # Chapter 2
    doc.add_heading("CHƯƠNG II: KHUNG BẬC NĂNG LỰC VÀ CHÍNH SÁCH ĐÃI NGỘ KỸ SƯ AI", level=1)
    doc.add_paragraph(
        "Điều 3. Khung phân cấp chức danh kỹ thuật:\n"
        "Bảng 1 dưới đây quy định chi tiết 5 cấp bậc chuyên môn kỹ thuật, mức lương cơ bản và phụ cấp chuyên môn hàng tháng:"
    )

    # Table 1
    table1 = doc.add_table(rows=6, cols=5)
    table1.style = "Table Grid"
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers1 = ["Cấp bậc", "Chức danh chuyên môn", "Lương cơ bản (VND)", "Phụ cấp chứng chỉ", "Yêu cầu kinh nghiệm"]
    data1 = [
        ["Level 1", "Junior AI / Data Engineer", "18.000.000 - 25.000.000", "2.000.000", "Dưới 2 năm kinh nghiệm Python/ML"],
        ["Level 2", "Software & RAG Engineer", "26.000.000 - 38.000.000", "3.500.000", "2 - 4 năm kinh nghiệm FastAPI, VectorDB"],
        ["Level 3", "Senior AI Engineer", "40.000.000 - 60.000.000", "5.000.000", "4 - 7 năm kinh nghiệm, làm chủ LLM/OCR"],
        ["Level 4", "Lead AI Architect", "65.000.000 - 90.000.000", "8.000.000", "Trên 7 năm kinh nghiệm thiết kế hệ thống"],
        ["Level 5", "Principal Research Scientist", "95.000.000 - 140.000.000", "12.000.000", "Tiến sĩ / Chuyên gia đầu ngành"],
    ]

    for col_idx, h in enumerate(headers1):
        cell = table1.cell(0, col_idx)
        cell.text = h
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for row_idx, row_data in enumerate(data1):
        for col_idx, val in enumerate(row_data):
            cell = table1.cell(row_idx + 1, col_idx)
            cell.text = val

    # Chapter 3
    doc.add_heading("CHƯƠNG III: CHÍNH SÁCH KHEN THƯỞNG DỰ ÁN VÀ SÁNG KIẾN KỸ THUẬT", level=1)
    doc.add_paragraph(
        "Điều 4. Cơ chế thưởng hoàn thành cột mốc dự án (Milestone Bonus):\n"
        "Nhằm khuyến khích tinh thần đổi mới sáng tạo và đảm bảo tiến độ bàn giao sản phẩm cho khách hàng, "
        "công ty áp dụng chính sách thưởng nóng theo bảng tiêu chuẩn đánh giá dưới đây:"
    )

    # Table 2
    table2 = doc.add_table(rows=4, cols=4)
    table2.style = "Table Grid"
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers2 = ["Hạng mục thành tích", "Tiêu chí đánh giá", "Mức thưởng dự kiến", "Đối tượng thụ hưởng"]
    data2 = [
        ["Hoàn thành Milestone trước hạn", "Bàn giao trước tối thiểu 05 ngày, 100% test pass", "15.000.000 - 30.000.000 VND", "Toàn bộ nhóm dự án"],
        ["Tối ưu hiệu năng pipeline", "Giảm 30% latency phản hồi API", "20.000.000 VND", "Kỹ sư tối ưu backend"],
        ["Đóng góp công nghệ xuất sắc", "Giải pháp xử lý bảng biểu phức tạp không lỗi", "25.000.000 VND", "Cá nhân có sáng kiến"],
    ]

    for col_idx, h in enumerate(headers2):
        cell = table2.cell(0, col_idx)
        cell.text = h
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for row_idx, row_data in enumerate(data2):
        for col_idx, val in enumerate(row_data):
            cell = table2.cell(row_idx + 1, col_idx)
            cell.text = val

    doc.add_paragraph(
        "\nĐiều 5. Hiệu lực thi hành:\n"
        "Quy chế này được Hội đồng Quản trị phê duyệt và có hiệu lực thi hành kể từ ngày 01 tháng 01 năm 2026. "
        "Mọi quy định trước đây trái với quy chế này đều bãi bỏ."
    )

    doc.save(filepath)
    print(f"Generated DOCX: {filepath}")


# =====================================================================
# 6. DOCX 02: Đề xuất dự án RAG tiếng Việt
# =====================================================================
def create_docx_02():
    filepath = RAW_DOCX_DIR / "docx_02_de_xuat_du_an_rag.docx"
    doc = docx.Document()

    # Title
    p_title = doc.add_heading(level=0)
    run_title = p_title.add_run("BẢN ĐỀ XUẤT DỰ ÁN: NỀN TẢNG DOCUMENT INTELLIGENCE & RAG TIẾNG VIỆT")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Subtitle
    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("Hệ thống Trích xuất Tri thức, Tìm kiếm Ngữ nghĩa và Trợ lý AI Chuyên sâu cho Doanh nghiệp Việt")
    r_sub.font.bold = True
    r_sub.font.size = Pt(11)
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Heading 1
    doc.add_heading("1. BỐI CẢNH VÀ MỤC TIÊU DỰ ÁN", level=1)
    doc.add_paragraph(
        "Hiện nay, tại các tổ chức tài chính, ngân hàng và tập đoàn kinh tế Việt Nam, hơn 80% tri thức và dữ liệu nghiệp vụ "
        "đang nằm rải rác dưới dạng tài liệu phi cấu trúc như hợp đồng pháp lý (.pdf), công văn quy định (.docx), "
        "và bảng tính báo cáo tài chính (.xlsx). Việc tìm kiếm thông tin thủ công tiêu tốn hàng nghìn giờ làm việc mỗi tháng "
        "và tiềm ẩn rủi ro sai sót thông tin nghiêm trọng."
    )
    doc.add_paragraph(
        "Mục tiêu cốt lõi của dự án là xây dựng một nền tảng trí tuệ nhân tạo toàn diện có khả năng:\n"
        "- Tự động bóc tách chính xác cấu trúc văn bản và bảng biểu từ tài liệu tiếng Việt đa định dạng.\n"
        "- Nhận diện tự động tài liệu scan và áp dụng OCR chất lượng cao.\n"
        "- Lập chỉ mục ngữ nghĩa kết hợp mô hình BGE-M3 và Qdrant Vector Database.\n"
        "- Trả lời câu hỏi tra cứu nghiệp vụ chính xác, có dẫn chứng nguồn trang cụ thể (Citation)."
    )

    # Heading 2
    doc.add_heading("2. KẾ HOẠCH TRIỂN KHAI VÀ CÁC CỘT MỐC (ROADMAP)", level=1)
    doc.add_paragraph(
        "Dự án được phân kỳ triển khai thành 05 cột mốc chiến lược (Milestones) theo mô hình Agile, "
        "đảm bảo từng giai đoạn đều có sản phẩm chạy được thực tế:"
    )

    # Table 1: Milestones
    table1 = doc.add_table(rows=6, cols=5)
    table1.style = "Table Grid"
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers1 = ["Cột mốc", "Tên giai đoạn", "Phạm vi công việc trọng tâm", "Thời hạn", "Trạng thái"]
    data1 = [
        ["Milestone 01", "Pipeline & REST API", "Parser đa định dạng PDF/DOCX/XLSX, REST API FastAPI, 25 tests", "Tháng 11/2026", "HOÀN THÀNH"],
        ["Milestone 02", "OCR & Vision Layout", "Tích hợp PaddleOCR/VietOCR, nhận diện bảng biểu trong ảnh", "Tháng 12/2026", "Chuẩn bị"],
        ["Milestone 03", "Hybrid Vector Search", "Nhúng vector BGE-M3, Qdrant Database, kết hợp BM25 tiếng Việt", "Tháng 01/2027", "Kế hoạch"],
        ["Milestone 04", "LangGraph RAG Engine", "Agent điều phối tra cứu, tự sửa truy vấn, trích dẫn nguồn văn bản", "Tháng 02/2027", "Kế hoạch"],
        ["Milestone 05", "Frontend & Production", "Giao diện React, giám sát Prometheus/Grafana, triển khai Docker", "Tháng 03/2027", "Kế hoạch"],
    ]

    for col_idx, h in enumerate(headers1):
        cell = table1.cell(0, col_idx)
        cell.text = h
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for row_idx, row_data in enumerate(data1):
        for col_idx, val in enumerate(row_data):
            cell = table1.cell(row_idx + 1, col_idx)
            cell.text = val

    # Heading 3
    doc.add_heading("3. DỰ TOÁN NGÂN SÁCH VÀ HẠ TẦNG KỸ THUẬT", level=1)
    doc.add_paragraph(
        "Bảng 2 ước tính chi phí đầu tư hạ tầng phần cứng và dịch vụ điện toán đám mây cho giai đoạn thử nghiệm (PoC) "
        "và vận hành chính thức (Production) trong năm đầu tiên:"
    )

    # Table 2: Budget
    table2 = doc.add_table(rows=5, cols=4)
    table2.style = "Table Grid"
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers2 = ["Hạng mục tài nguyên", "Quy cách kỹ thuật", "Chi phí ước tính / Tháng", "Ghi chú mục đích"]
    data2 = [
        ["GPU Inference Server", "2 x NVIDIA L40S 48GB VRAM", "35.000.000 VND", "Chạy mô hình Embedding & OCR"],
        ["CPU Application Node", "16 vCPU, 64GB RAM Cloud VM", "8.500.000 VND", "Chạy FastAPI & Document Pipeline"],
        ["Vector Database Node", "Qdrant Cluster 32GB RAM", "6.200.000 VND", "Lưu trữ 2.000.000 vectors"],
        ["Cloud Storage (S3)", "5 TB S3 Compatible Storage", "2.800.000 VND", "Lưu trữ tài liệu gốc và cache"],
    ]

    for col_idx, h in enumerate(headers2):
        cell = table2.cell(0, col_idx)
        cell.text = h
        for p in cell.paragraphs:
            p.runs[0].font.bold = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for row_idx, row_data in enumerate(data2):
        for col_idx, val in enumerate(row_data):
            cell = table2.cell(row_idx + 1, col_idx)
            cell.text = val

    doc.add_paragraph(
        "\n4. KẾT LUẬN VÀ KIẾN NGHỊ:\n"
        "Dự án mang tính chiến lược cao, giúp tiết kiệm 70% thời gian xử lý hồ sơ thủ tục, nâng cao năng suất "
        "lao động và bảo vệ toàn vẹn tài sản tri thức của doanh nghiệp. Kính trình Ban Giám đốc phê duyệt triển khai."
    )

    doc.save(filepath)
    print(f"Generated DOCX: {filepath}")


# =====================================================================
# 7. XLSX 01: Kế hoạch ngân sách 2026 (Multi-sheet, Dates, Nulls)
# =====================================================================
def create_xlsx_01():
    filepath = RAW_XLSX_DIR / "xlsx_01_ke_hoach_ngan_sach_2026.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    border_thin = Border(left=Side(style='thin', color='BFBFBF'),
                         right=Side(style='thin', color='BFBFBF'),
                         top=Side(style='thin', color='BFBFBF'),
                         bottom=Side(style='thin', color='BFBFBF'))

    # Sheet 1: TongQuanNganSach
    ws1 = wb.create_sheet(title="TongQuanNganSach")
    ws1.append(["Mã dự án", "Tên dự án AI", "Khối phụ trách", "Ngày phê duyệt", "Ngân sách duyệt (VND)", "Đã giải ngân (VND)", "Tỷ lệ", "Ghi chú điều chỉnh"])
    
    data_ws1 = [
        ["DA-01", "Hệ thống Document Intelligence", "R&D AI", datetime.date(2026, 1, 15), 850000000, 340000000, "40.0%", "Đã hoàn thành Milestone 01"],
        ["DA-02", "Trợ lý ảo Pháp chế Doanh nghiệp", "Giải pháp Doanh nghiệp", datetime.date(2026, 2, 20), 620000000, 186000000, "30.0%", None], # Empty cell
        ["DA-03", "Hạ tầng Vector Database & Search", "Kỹ thuật Hạ tầng", datetime.date(2026, 3, 10), 450000000, 225000000, "50.0%", "Đang chờ bàn giao server GPU"],
        ["DA-04", "Số hóa kho tài liệu Scan lịch sử", "Vận hành Dữ liệu", datetime.date(2026, 4, 5), 320000000, 0, "0.0%", None], # Empty cell
        ["DA-05", "Nghiên cứu mô hình Small LLM tiếng Việt", "Viện Công nghệ", datetime.date(2026, 5, 12), 1200000000, 480000000, "40.0%", "Hợp tác phòng lab đại học"],
    ]
    for row in data_ws1:
        ws1.append(row)

    # Style sheet 1
    for cell in ws1[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Sheet 2: ChiTietChiPhiQuy1
    ws2 = wb.create_sheet(title="ChiTietChiPhiQuy1")
    ws2.append(["Mã chứng từ", "Ngày hạch toán", "Khoản mục chi phí", "Đơn vị nhận", "Số tiền (VND)", "Mã dự án", "Người duyệt", "Trạng thái"])
    data_ws2 = [
        ["CT-001", datetime.datetime(2026, 1, 20, 9, 30), "Mua sắm máy chủ Dell R750", "Công ty CP Hạ tầng Số", 185000000, "DA-01", "Nguyễn Văn Nam", "Đã thanh toán"],
        ["CT-002", datetime.datetime(2026, 1, 25, 14, 15), "Thuê GPU Cloud NVIDIA A100", "Cloud Provider Global", 35000000, "DA-01", "Lê Thị Mai", "Đã thanh toán"],
        ["CT-003", datetime.datetime(2026, 2, 10, 11, 0), "Bản quyền phần mềm VectorDB", "Qdrant Cloud Inc", 18500000, "DA-03", None, "Chờ duyệt chi"], # Empty cell
        ["CT-004", datetime.datetime(2026, 2, 28, 16, 45), "Thu thù lao chuyên gia gán nhãn", "Nhóm Cộng tác viên", 25000000, "DA-04", "Phạm Hoàng Long", "Đã thanh toán"],
        ["CT-005", datetime.datetime(2026, 3, 15, 10, 20), "Gói dịch vụ Internet cáp quang 1Gbps", "Tập đoàn Viễn thông VN", 12000000, "DA-01", None, None], # Empty cells
    ]
    for row in data_ws2:
        ws2.append(row)

    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Sheet 3: DuPhongRuiRo
    ws3 = wb.create_sheet(title="DuPhongRuiRo")
    ws3.append(["Mã rủi ro", "Tên rủi ro tiềm ẩn", "Mức độ", "Dự phòng (VND)", "Ngày rà soát", "Phương án xử lý"])
    data_ws3 = [
        ["RR-01", "Tăng giá thuê GPU quốc tế", "Cao", 80000000, datetime.date(2026, 3, 1), "Ký hợp đồng giữ giá 12 tháng"],
        ["RR-02", "Biến động nhân sự AI cao cấp", "Trung bình", 50000000, datetime.date(2026, 3, 15), "Ký cam kết gắn kết và ESOP"],
        ["RR-03", "Trễ hạn bàn giao tài liệu từ đối tác", "Thấp", 20000000, datetime.date(2026, 3, 20), None], # Empty cell
    ]
    for row in data_ws3:
        ws3.append(row)

    for cell in ws3[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    wb.save(filepath)
    wb.close()
    print(f"Generated XLSX: {filepath}")


# =====================================================================
# 8. XLSX 02: Quản lý nhân sự và phân công dự án (Multi-sheet, Dates, Nulls)
# =====================================================================
def create_xlsx_02():
    filepath = RAW_XLSX_DIR / "xlsx_02_quan_ly_nhan_su_va_du_an.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")

    # Sheet 1: DanhSachNhanSu
    ws1 = wb.create_sheet(title="DanhSachNhanSu")
    ws1.append(["Mã NV", "Họ và tên", "Phòng ban", "Chức danh", "Ngày vào làm", "Email", "Điện thoại liên hệ", "Điểm KPI Quý 3"])
    data_ws1 = [
        ["NV0101", "Nguyễn Văn Nam", "Ban Điều Hành", "Tổng Giám đốc", datetime.date(2020, 1, 15), "nam.nv@alpha.vn", "0903123456", 95.5],
        ["NV0205", "Lê Thị Mai", "Khối R&D AI", "Giám đốc Nghiên cứu", datetime.date(2021, 5, 10), "mai.lt@alpha.vn", "0912345678", 98.0],
        ["NV0312", "Phạm Hoàng Long", "Khối R&D AI", "Lead AI Architect", datetime.date(2022, 8, 1), "long.ph@alpha.vn", None, 92.5], # Empty phone
        ["NV0315", "Đỗ Minh Tuấn", "Phòng Công nghệ", "Senior Backend Engineer", datetime.date(2023, 3, 15), "tuan.dm@alpha.vn", "0988776655", 91.0],
        ["NV0420", "Trần Thu Trang", "Phòng Dữ liệu", "Data Processing Specialist", datetime.date(2024, 6, 1), "trang.tt@alpha.vn", None, None], # Empty cells
        ["NV0425", "Vũ Hải Đăng", "Khối Nghiệp vụ", "Chuyên viên Thẩm định", datetime.date(2025, 2, 20), "dang.vh@alpha.vn", "0933221100", 88.5],
    ]
    for r in data_ws1:
        ws1.append(r)

    for cell in ws1[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Sheet 2: PhanCongDuAn
    ws2 = wb.create_sheet(title="PhanCongDuAn")
    ws2.append(["Mã PC", "Tên dự án", "Nhân sự phụ trách", "Vai trò", "Ngày bắt đầu", "Ngày kết thúc dự kiến", "Tiến độ", "Ghi chú"])
    data_ws2 = [
        ["PC-01", "Pipeline Document Intelligence", "Phạm Hoàng Long", "Trưởng nhóm Kỹ thuật", datetime.date(2026, 1, 1), datetime.date(2026, 11, 30), "100%", "Bàn giao Milestone 01"],
        ["PC-02", "OCR & Vision Layout Engine", "Phạm Hoàng Long", "Nghiên cứu chính", datetime.date(2026, 12, 1), datetime.date(2026, 12, 31), "10%", "Chuẩn bị tập dữ liệu train"],
        ["PC-03", "FastAPI Service & Test Suite", "Đỗ Minh Tuấn", "Kỹ sư Backend", datetime.date(2026, 10, 15), datetime.date(2026, 11, 20), "100%", None], # Empty cell
        ["PC-04", "Chuẩn hóa dữ liệu Ground Truth", "Trần Thu Trang", "Gán nhãn Dữ liệu", datetime.date(2026, 11, 1), datetime.date(2026, 11, 16), "100%", "Đã kiểm định 10 file"],
    ]
    for r in data_ws2:
        ws2.append(r)

    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Sheet 3: TheoDoiNghiPhep
    ws3 = wb.create_sheet(title="TheoDoiNghiPhep")
    ws3.append(["Mã đơn", "Họ tên nhân viên", "Ngày bắt đầu nghỉ", "Số ngày nghỉ", "Loại nghỉ phép", "Người duyệt", "Tình trạng"])
    data_ws3 = [
        ["NP-101", "Phạm Hoàng Long", datetime.date(2026, 4, 28), 3, "Nghỉ phép năm", "Lê Thị Mai", "Đã duyệt"],
        ["NP-102", "Đỗ Minh Tuấn", datetime.date(2026, 7, 10), 1, "Nghỉ việc riêng", "Lê Thị Mai", "Đã duyệt"],
        ["NP-103", "Trần Thu Trang", datetime.date(2026, 11, 2), 2, "Nghỉ ốm hưởng BHXH", None, "Chờ duyệt"], # Empty approver
    ]
    for r in data_ws3:
        ws3.append(r)

    for cell in ws3[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    wb.save(filepath)
    wb.close()
    print(f"Generated XLSX: {filepath}")


# =====================================================================
# 9. PDF Complex 01: Bảng giá dịch vụ Cloud & AI (Complex Tables, 2 pages)
# =====================================================================
def create_pdf_complex_01():
    filepath = RAW_PDF_DIR / "pdf_complex_01_bang_gia_dich_vu_cloud.pdf"
    doc = pymupdf.open()

    # --- Page 1 ---
    page1 = doc.new_page(width=595, height=842)
    page1.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page1.insert_font(fontname="arbd", fontfile=FONT_BOLD)
    page1.insert_font(fontname="arit", fontfile=FONT_ITALIC)

    page1.insert_textbox(pymupdf.Rect(50, 40, 545, 90),
                         "CÔNG TY CỔ PHẦN ĐIỆN TOÁN ĐÁM MÂY & AI VIỆT NAM\n"
                         "BẢNG BÁO GIÁ DỊCH VỤ HẠ TẦNG VÀ NỀN TẢNG RAG NĂM 2026",
                         fontname="arbd", fontsize=13, align=pymupdf.TEXT_ALIGN_CENTER)

    page1.insert_textbox(pymupdf.Rect(50, 95, 545, 115),
                         "[BẢNG GIÁ DỊCH VỤ KỸ THUẬT TIÊU CHUẨN DÀNH CHO KHÁCH HÀNG DOANH NGHIỆP]",
                         fontname="arit", fontsize=8.5, align=pymupdf.TEXT_ALIGN_CENTER)

    intro = (
        "Chúng tôi xin trân trọng gửi tới Quý Khách hàng biểu phí dịch vụ điện toán đám mây chuyên dụng cho các tác vụ "
        "trí tuệ nhân tạo, xử lý ngôn ngữ tự nhiên và trích xuất tài liệu thông minh. Biểu phí được thiết kế linh hoạt "
        "theo mô hình thuê bao hàng tháng (Monthly Subscription) với cam kết chất lượng dịch vụ (SLA) lên tới 99.95%."
    )
    page1.insert_textbox(pymupdf.Rect(50, 125, 545, 175), intro, fontname="ar", fontsize=10, lineheight=1.35)

    # Complex Table: 3 Tiers Comparison
    table_x = 50
    table_y = 185
    col_w = [145, 115, 115, 120]

    headers = ["Thông số kỹ thuật / Gói", "Gói Khởi động\n(Starter Tier)", "Gói Chuyên nghiệp\n(Pro Tier)", "Gói Doanh nghiệp\n(Enterprise Tier)"]
    rows = [
        ["Năng lực tính toán (vCPU)", "4 vCPU High-freq", "16 vCPU Dedicated", "64 vCPU AMD EPYC"],
        ["Bộ nhớ hệ thống (RAM)", "16 GB DDR5 ECC", "64 GB DDR5 ECC", "256 GB DDR5 ECC"],
        ["Tăng tốc đồ họa (GPU)", "Không có GPU", "1 x NVIDIA L4 (24GB)", "2 x NVIDIA H100 (80GB)"],
        ["Dung lượng lưu trữ NVMe", "100 GB NVMe Gen4", "500 GB NVMe Gen4", "2.000 GB NVMe Enterprise"],
        ["Băng thông mạng Internet", "100 Mbps Shared", "500 Mbps Dedicated", "2 Gbps Dedicated Dual-WAN"],
        ["Hạn mức trích xuất API", "10.000 trang/tháng", "100.000 trang/tháng", "Không giới hạn"],
        ["Hỗ trợ OCR tài liệu scan", "Tối đa 500 trang/tháng", "10.000 trang/tháng", "Không giới hạn worker"],
        ["Hỗ trợ Vector Database", "Shared Cluster", "Dedicated Qdrant Node", "HA Qdrant 3-Nodes Cluster"],
        ["Thời gian cam kết SLA", "99.0% Uptime", "99.9% Uptime", "99.95% Uptime"],
        ["Giá thuê dịch vụ / Tháng", "4.500.000 VND", "24.000.000 VND", "85.000.000 VND"],
    ]

    # Draw Header
    cur_x = table_x
    for i, h in enumerate(headers):
        rect = pymupdf.Rect(cur_x, table_y, cur_x + col_w[i], table_y + 30)
        page1.draw_rect(rect, color=(0.2, 0.2, 0.2), fill=(0.85, 0.9, 0.96), width=0.8)
        page1.insert_textbox(rect, h, fontname="arbd", fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
        cur_x += col_w[i]

    cur_y = table_y + 30
    for r_idx, r in enumerate(rows):
        cur_x = table_x
        bg = (0.97, 0.97, 0.97) if r_idx % 2 == 1 else (1, 1, 1)
        if r_idx == len(rows) - 1:
            bg = (0.9, 0.95, 0.9)  # Highlight price row
        for c_idx, val in enumerate(r):
            rect = pymupdf.Rect(cur_x, cur_y, cur_x + col_w[c_idx], cur_y + 24)
            page1.draw_rect(rect, color=(0.4, 0.4, 0.4), fill=bg, width=0.5)
            font_to_use = "arbd" if c_idx == 0 or r_idx == len(rows) - 1 else "ar"
            align = pymupdf.TEXT_ALIGN_LEFT if c_idx == 0 else pymupdf.TEXT_ALIGN_CENTER
            page1.insert_textbox(pymupdf.Rect(cur_x + 4, cur_y + 4, cur_x + col_w[c_idx] - 4, cur_y + 24),
                                 val, fontname=font_to_use, fontsize=8.5, align=align)
            cur_x += col_w[c_idx]
        cur_y += 24

    # Note below table
    note = (
        "\n* Ghi chú đơn giá: Báo giá trên chưa bao gồm thuế giá trị gia tăng (VAT 10%). "
        "Chi phí được thanh toán định kỳ vào ngày 01 hàng tháng qua hình thức chuyển khoản ngân hàng."
    )
    page1.insert_textbox(pymupdf.Rect(50, cur_y + 10, 545, 800), note, fontname="arit", fontsize=9)

    # --- Page 2 ---
    page2 = doc.new_page(width=595, height=842)
    page2.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page2.insert_font(fontname="arbd", fontfile=FONT_BOLD)

    content_p2 = (
        "CHÍNH SÁCH CHIẾT KHẤU VÀ ĐIỀU KHOẢN HỖ TRỢ KỸ THUẬT\n\n"
        "1. Chính sách ưu đãi cam kết dài hạn:\n"
        "- Khách hàng ký hợp đồng 06 tháng: Giảm ngay 10% tổng giá trị thanh toán.\n"
        "- Khách hàng ký hợp đồng 12 tháng: Giảm ngay 20% và miễn phí 01 tháng sử dụng dịch vụ hạ tầng.\n"
        "- Khách hàng ký hợp đồng 24 tháng: Giảm ngay 30%, tặng kèm gói tích hợp API và đào tạo kỹ thuật nội bộ.\n\n"
        "2. Bảng giá dịch vụ cộng thêm (Add-on Services):\n"
    )
    page2.insert_textbox(pymupdf.Rect(50, 50, 545, 180), content_p2, fontname="ar", fontsize=10, lineheight=1.35)

    # Add-on Table
    addon_x = 50
    addon_y = 190
    addon_col_w = [180, 155, 160]
    addon_headers = ["Dịch vụ bổ sung", "Quy cách đóng gói", "Đơn giá (VND)"]
    addon_rows = [
        ["Thêm GPU NVIDIA L4", "01 GPU 24GB VRAM / Tháng", "14.000.000"],
        ["Thêm GPU NVIDIA H100", "01 GPU 80GB SXM5 / Tháng", "42.000.000"],
        ["Mở rộng lưu trữ NVMe", "Mỗi 500 GB bổ sung / Tháng", "1.200.000"],
        ["Hỗ trợ kỹ thuật 24/7 Dedicated", "Kỹ sư túc trực riêng theo SLA", "15.000.000"],
        ["Đào tạo và Fine-tuning Model", "Gói 40 giờ chuyên gia kỹ thuật", "35.000.000"],
    ]

    cur_x = addon_x
    for i, h in enumerate(addon_headers):
        rect = pymupdf.Rect(cur_x, addon_y, cur_x + addon_col_w[i], addon_y + 24)
        page2.draw_rect(rect, color=(0.3, 0.3, 0.3), fill=(0.92, 0.94, 0.98), width=0.6)
        page2.insert_textbox(rect, h, fontname="arbd", fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
        cur_x += addon_col_w[i]

    cur_y = addon_y + 24
    for r in addon_rows:
        cur_x = addon_x
        for i, val in enumerate(r):
            rect = pymupdf.Rect(cur_x, cur_y, cur_x + addon_col_w[i], cur_y + 22)
            page2.draw_rect(rect, color=(0.5, 0.5, 0.5), fill=(1, 1, 1), width=0.5)
            align = pymupdf.TEXT_ALIGN_LEFT if i == 0 else (pymupdf.TEXT_ALIGN_CENTER if i == 1 else pymupdf.TEXT_ALIGN_RIGHT)
            page2.insert_textbox(pymupdf.Rect(cur_x + 4, cur_y + 3, cur_x + addon_col_w[i] - 4, cur_y + 22),
                                 val, fontname="ar", fontsize=8.5, align=align)
            cur_x += addon_col_w[i]
        cur_y += 22

    terms = (
        "\n3. Điều khoản kỹ thuật và bảo mật:\n"
        "- Tất cả dữ liệu tài liệu truyền tải qua API được mã hóa đầu cuối bằng chuẩn TLS 1.3.\n"
        "- Toàn bộ hạ tầng máy chủ được đặt tại trung tâm dữ liệu đạt chuẩn Tier 3 tại Hà Nội và TP. Hồ Chí Minh.\n"
        "- Báo giá có hiệu lực trong vòng 30 ngày kể từ ngày ban hành."
    )
    page2.insert_textbox(pymupdf.Rect(50, cur_y + 15, 545, 800), terms, fontname="ar", fontsize=9.5, lineheight=1.35)

    doc.save(filepath)
    doc.close()
    print(f"Generated Complex PDF: {filepath}")


# =====================================================================
# 10. PDF Complex 02: Bản tin công nghệ 2 cột (Multi-column Layout, 2 pages)
# =====================================================================
def create_pdf_complex_02():
    filepath = RAW_PDF_DIR / "pdf_complex_02_ban_tin_cong_nghe_hai_cot.pdf"
    doc = pymupdf.open()

    # --- Page 1 ---
    page1 = doc.new_page(width=595, height=842)
    page1.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page1.insert_font(fontname="arbd", fontfile=FONT_BOLD)
    page1.insert_font(fontname="arit", fontfile=FONT_ITALIC)

    # Full width Banner
    page1.draw_rect(pymupdf.Rect(40, 35, 555, 95), color=(0.1, 0.3, 0.6), fill=(0.1, 0.3, 0.6))
    page1.insert_textbox(pymupdf.Rect(50, 42, 545, 70),
                         "BẢN TIN ĐỔI MỚI CÔNG NGHỆ VÀ TRÍ TUỆ NHÂN TẠO VIỆT NAM",
                         fontname="arbd", fontsize=13, align=pymupdf.TEXT_ALIGN_CENTER)
    page1.insert_textbox(pymupdf.Rect(50, 72, 545, 90),
                         "Chuyên san Nghiên cứu Ứng dụng Document Intelligence & RAG trong Chuyển đổi số Quốc gia",
                         fontname="arit", fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)

    # Two columns definition
    col1_rect = pymupdf.Rect(40, 115, 290, 780)
    col2_rect = pymupdf.Rect(305, 115, 555, 780)

    # Vertical separator line
    page1.draw_line(pymupdf.Point(297, 115), pymupdf.Point(297, 780), color=(0.8, 0.8, 0.8), width=0.8)

    col1_text = (
        "XU HƯỚNG BÓC TÁCH TRI THỨC VĂN BẢN\n"
        "Từ OCR truyền thống đến Multimodal RAG\n\n"
        "Trong kỷ nguyên bùng nổ dữ liệu số, các cơ quan ban ngành và doanh nghiệp lớn tại Việt Nam đang phải đối mặt "
        "với khối lượng khổng lồ các văn bản hành chính, hồ sơ đấu thầu và báo cáo tài chính. Trước đây, phương pháp tiếp cận "
        "truyền thống chủ yếu dựa vào công nghệ nhận dạng ký tự quang học (OCR) cổ điển kết hợp biểu thức chính quy (Regex). "
        "Tuy nhiên, cách tiếp cận này bộc lộ nhiều điểm nghẽn nghiêm trọng khi cấu trúc bảng biểu bị thay đổi hoặc chất lượng bản chụp bị mờ.\n\n"
        "Sự xuất hiện của các kiến trúc Document Intelligence thế hệ mới – kết hợp giữa bộ phân tích tài liệu đa định dạng "
        "(Document Parser), mô hình thị giác máy tính nhận diện bố cục (Layout Analysis) và mô hình ngôn ngữ lớn (LLM) – "
        "đã mở ra một kỷ nguyên mới. Hệ thống không chỉ dừng lại ở việc đọc từng ký tự riêng lẻ, mà có khả năng hiểu sâu "
        "ngữ cảnh ngữ nghĩa của từng phân đoạn văn bản, liên kết chính xác hàng và cột trong các bảng số liệu phức tạp.\n\n"
        "Tại các ngân hàng thương mại, việc áp dụng pipeline trích xuất tự động đã giúp rút ngắn thời gian thẩm định hợp đồng "
        "vay vốn từ 48 giờ xuống chỉ còn dưới 15 phút, đồng thời giảm thiểu 95% sai sót trong nhập liệu kế toán."
    )
    page1.insert_textbox(col1_rect, col1_text, fontname="ar", fontsize=9.2, lineheight=1.35)

    col2_text = (
        "THÁCH THỨC VỚI TIẾNG VIỆT ĐẶC THÙ\n"
        "Dấu thanh âm điệu và định dạng phi cấu trúc\n\n"
        "Mặc dù các mô hình ngôn ngữ quốc tế đã đạt được nhiều bước tiến lớn, việc xử lý tiếng Việt vẫn đặt ra những thách thức "
        "vô cùng đặc thù mà các kỹ sư AI trong nước cần giải quyết triệt để:\n\n"
        "1. Hệ thống dấu thanh phức tạp:\n"
        "Tiếng Việt sở hữu 6 thanh điệu kết hợp cùng các ký tự có dấu mũ, móc (ă, â, ê, ô, ơ, ư, đ). Khi xử lý tài liệu quét hoặc "
        "văn bản từ các nguồn font cũ (như TCVN3, VNI), hiện tượng vỡ font, mất dấu thanh hoặc nhầm lẫn giữa khoảng trắng chuẩn "
        "và ký tự non-breaking space (\\xa0) thường xuyên gây sai lệch trong việc lập chỉ mục tìm kiếm.\n\n"
        "2. Bảng biểu không đường viền (Borderless Tables):\n"
        "Rất nhiều biểu mẫu báo cáo tài chính sử dụng bảng biểu phân tách bằng khoảng trắng thay vì kẻ khung viền rõ ràng. "
        "Nếu bộ parser chỉ đọc dòng tuần tự mà không có cơ chế phân tích cấu trúc cột, toàn bộ ý nghĩa dữ liệu số sẽ bị xáo trộn.\n\n"
        "3. Yêu cầu bảo mật dữ liệu nội bộ:\n"
        "Nghị định 13/2023/NĐ-CP đặt ra rào cản pháp lý nghiêm ngặt: dữ liệu tài liệu doanh nghiệp không được gửi ra các API "
        "đám mây nước ngoài không rõ kiểm soát. Do đó, việc xây dựng pipeline xử lý On-Premise hoặc Cloud nội địa là bắt buộc."
    )
    page2_col2 = page1.insert_textbox(col2_rect, col2_text, fontname="ar", fontsize=9.2, lineheight=1.35)

    # --- Page 2 ---
    page2 = doc.new_page(width=595, height=842)
    page2.insert_font(fontname="ar", fontfile=FONT_REGULAR)
    page2.insert_font(fontname="arbd", fontfile=FONT_BOLD)

    # Header Page 2
    page2.insert_textbox(pymupdf.Rect(40, 40, 555, 70),
                         "BẢN TIN ĐỔI MỚI CÔNG NGHỆ VÀ TRÍ TUỆ NHÂN TẠO VIỆT NAM (TIẾP THEO)",
                         fontname="arbd", fontsize=11, align=pymupdf.TEXT_ALIGN_CENTER)

    # Two columns definition Page 2
    col1_p2 = pymupdf.Rect(40, 85, 290, 480)
    col2_p2 = pymupdf.Rect(305, 85, 555, 480)
    page2.draw_line(pymupdf.Point(297, 85), pymupdf.Point(297, 480), color=(0.8, 0.8, 0.8), width=0.8)

    text_c1_p2 = (
        "KIẾN TRÚC HỆ THỐNG HYBRID SEARCH\n\n"
        "Để đáp ứng yêu cầu tra cứu tài liệu với độ chính xác tuyệt đối, việc chỉ sử dụng tìm kiếm ngữ nghĩa (Semantic Vector Search) "
        "là chưa đủ. Trong tài liệu kỹ thuật và pháp lý, người dùng thường xuyên tìm kiếm theo từ khóa chính xác như số hiệu văn bản, "
        "mã điều khoản, hoặc số tiền cụ thể.\n\n"
        "Vì vậy, kiến trúc kết hợp (Hybrid Search) giữa thuật toán đối sánh từ khóa BM25 và mô hình nhúng đa ngôn ngữ BGE-M3 "
        "kết hợp cơ chế chấm điểm lại (Reranking) đang trở thành tiêu chuẩn vàng trong các hệ thống RAG hiện đại.\n\n"
        "Thực nghiệm cho thấy mô hình Hybrid Search giúp nâng cao độ bao phủ (Recall@5) lên 94.2%, vượt trội so với mức 78.5% "
        "khi chỉ sử dụng vector search đơn thuần."
    )
    page2.insert_textbox(col1_p2, text_c1_p2, fontname="ar", fontsize=9.2, lineheight=1.35)

    text_c2_p2 = (
        "LỘ TRÌNH PHÁT TRIỂN TIẾP THEO\n\n"
        "Nhóm kỹ sư dự án đã hoàn thành Milestone 01 với nền tảng trích xuất dữ liệu đa định dạng và hệ thống API hiệu năng cao. "
        "Trong giai đoạn tiếp theo, các mục tiêu then chốt bao gồm:\n\n"
        "- Tích hợp mô hình OCR chuyên sâu cho tài liệu quét, hóa đơn và văn bản viết tay.\n"
        "- Xây dựng bộ đánh giá tự động dựa trên độ đo CER (Character Error Rate) và WER (Word Error Rate).\n"
        "- Tối ưu hóa bộ nhớ đệm (Caching) và khả năng xử lý đồng thời hàng nghìn luồng trích xuất tài liệu.\n\n"
        "Dự án cam kết mang lại giải pháp công nghệ làm chủ hoàn toàn, đóng góp tích cực vào hệ sinh thái AI quốc gia."
    )
    page2.insert_textbox(col2_p2, text_c2_p2, fontname="ar", fontsize=9.2, lineheight=1.35)

    # Full width table at bottom of page 2
    table_y = 505
    page2.insert_textbox(pymupdf.Rect(40, table_y, 555, table_y + 25),
                         "BẢNG SO SÁNH HIỆU QUẢ CÁC PHƯƠNG PHÁP XỬ LÝ VĂN BẢN TIẾNG VIỆT",
                         fontname="arbd", fontsize=10, align=pymupdf.TEXT_ALIGN_CENTER)

    tbl_x = 40
    cur_y = table_y + 25
    col_w = [145, 115, 125, 130]
    headers = ["Phương pháp xử lý", "Độ chính xác text", "Khả năng đọc bảng", "Tốc độ xử lý / trang"]
    rows = [
        ["OCR truyền thống (Tesseract)", "75% - 82%", "Kém (mất cấu trúc)", "1.500 ms - 3.000 ms"],
        ["Pipeline Parser (PyMuPDF/docx)", "98% - 100%", "Tốt (bảo toàn ma trận)", "50 ms - 150 ms"],
        ["Vision LLM / Layout Model", "92% - 96%", "Rất tốt (hiểu ngữ nghĩa)", "2.000 ms - 5.000 ms"],
        ["Hybrid Pipeline (Đang triển khai)", "96% - 99%", "Xuất sắc (kết hợp tối ưu)", "120 ms - 450 ms"],
    ]

    cur_x = tbl_x
    for i, h in enumerate(headers):
        rect = pymupdf.Rect(cur_x, cur_y, cur_x + col_w[i], cur_y + 22)
        page2.draw_rect(rect, color=(0.3, 0.3, 0.3), fill=(0.9, 0.93, 0.98), width=0.6)
        page2.insert_textbox(rect, h, fontname="arbd", fontsize=8.5, align=pymupdf.TEXT_ALIGN_CENTER)
        cur_x += col_w[i]

    cur_y += 22
    for r_idx, r in enumerate(rows):
        cur_x = tbl_x
        bg = (0.97, 0.97, 0.97) if r_idx % 2 == 1 else (1, 1, 1)
        for c_idx, val in enumerate(r):
            rect = pymupdf.Rect(cur_x, cur_y, cur_x + col_w[c_idx], cur_y + 22)
            page2.draw_rect(rect, color=(0.5, 0.5, 0.5), fill=bg, width=0.5)
            font_to_use = "arbd" if c_idx == 0 else "ar"
            align = pymupdf.TEXT_ALIGN_LEFT if c_idx == 0 else pymupdf.TEXT_ALIGN_CENTER
            page2.insert_textbox(pymupdf.Rect(cur_x + 3, cur_y + 3, cur_x + col_w[c_idx] - 3, cur_y + 22),
                                 val, fontname=font_to_use, fontsize=8, align=align)
            cur_x += col_w[c_idx]
        cur_y += 22

    doc.save(filepath)
    doc.close()
    print(f"Generated Complex PDF: {filepath}")


def main():
    setup_directories()
    print("=== STARTING GENERATION OF 10 DEMO DOCUMENTS ===")
    create_pdf_text_01()
    create_pdf_text_02()
    create_pdf_scan_01()
    create_pdf_scan_02()
    create_docx_01()
    create_docx_02()
    create_xlsx_01()
    create_xlsx_02()
    create_pdf_complex_01()
    create_pdf_complex_02()
    print("=== ALL 10 DEMO DOCUMENTS GENERATED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
