"""Unit tests for DocumentParser service across PDF, DOCX, and XLSX formats."""

import datetime
import io
import os
from typing import Any, Dict, List
import pytest
import pymupdf
import docx
import openpyxl

from app.core.exceptions import (
    CorruptedDocumentError,
    EmptyFileError,
    EncryptedDocumentError,
    UnsupportedFileTypeError,
)
from app.schemas.document import FileType, SegmentType
from app.services.document_parser import DocumentParser, parse_document


# =====================================================================
# Fixture & Generator Helpers (dynamic in-memory generation)
# =====================================================================

def _get_unicode_font_path() -> str | None:
    """Find a local font supporting Vietnamese Unicode characters."""
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def generate_pdf(pages_text: list[str]) -> bytes:
    """Generate in-memory PDF with specified text per page."""
    doc = pymupdf.open()
    font_path = _get_unicode_font_path()

    for text in pages_text:
        page = doc.new_page()
        if font_path:
            page.insert_font(fontname="custom_font", fontfile=font_path)
            page.insert_text((50, 72), text, fontname="custom_font", fontsize=12)
        else:
            page.insert_text((50, 72), text, fontname="helv", fontsize=12)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_scanned_pdf() -> bytes:
    """Generate in-memory PDF with an image and no extractable text."""
    doc = pymupdf.open()
    page = doc.new_page()
    # Create a small dummy RGB image pixmap
    pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 100, 100), False)
    pix.clear_with(240)
    page.insert_image(page.rect, pixmap=pix)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_encrypted_pdf(password: str = "secret") -> bytes:
    """Generate in-memory encrypted PDF protected with password."""
    doc = pymupdf.open()
    page = doc.new_page()
    font_path = _get_unicode_font_path()
    if font_path:
        page.insert_font(fontname="custom_font", fontfile=font_path)
        page.insert_text((50, 72), "Tài liệu bảo mật", fontname="custom_font", fontsize=12)
    else:
        page.insert_text((50, 72), "Tai lieu bao mat", fontname="helv", fontsize=12)

    pdf_bytes = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="admin",
        user_pw=password,
    )
    doc.close()
    return pdf_bytes


def generate_docx_paragraphs(paragraphs: list[str]) -> bytes:
    """Generate in-memory DOCX with paragraphs only."""
    doc = docx.Document()
    for p_text in paragraphs:
        doc.add_paragraph(p_text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def generate_docx_table(rows: list[list[str]]) -> bytes:
    """Generate in-memory DOCX with a single table."""
    doc = docx.Document()
    if rows:
        table = doc.add_table(rows=len(rows), cols=len(rows[0]))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                table.cell(r_idx, c_idx).text = str(val)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def generate_docx_mixed(elements: list[tuple[str, Any]]) -> bytes:
    """Generate in-memory DOCX with interleaved paragraphs ('p') and tables ('tbl')."""
    doc = docx.Document()
    for el_type, val in elements:
        if el_type == "p":
            doc.add_paragraph(str(val))
        elif el_type == "tbl":
            table = doc.add_table(rows=len(val), cols=len(val[0]))
            for r_idx, row in enumerate(val):
                for c_idx, cell_text in enumerate(row):
                    table.cell(r_idx, c_idx).text = str(cell_text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def generate_xlsx(sheets_data: dict[str, list[list[Any]]]) -> bytes:
    """Generate in-memory XLSX workbook with arbitrary sheet definitions."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default active sheet

    for sheet_title, rows in sheets_data.items():
        ws = wb.create_sheet(title=sheet_title)
        for row in rows:
            ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


# =====================================================================
# PDF Parsing Tests
# =====================================================================

def test_pdf_single_page_with_text():
    """Test extracting text from single-page PDF."""
    font_path = _get_unicode_font_path()
    sample_text = "Hợp đồng kinh tế số 102/2026" if font_path else "Hop dong kinh te so 102/2026"
    pdf_bytes = generate_pdf([sample_text])
    res = DocumentParser.parse("contract.pdf", pdf_bytes)

    assert res.file_type == FileType.PDF
    assert res.metadata.page_count == 1
    assert res.total_segments == 1
    assert res.requires_ocr is False
    assert ("Hợp đồng kinh tế" in res.segments[0].text) or ("Hop dong kinh te" in res.segments[0].text)
    assert res.segments[0].page == 1
    assert res.segments[0].segment_type == SegmentType.TEXT


def test_pdf_multi_page():
    """Test extracting text across multiple pages in PDF."""
    font_path = _get_unicode_font_path()
    if font_path:
        pages = [
            "Trang 1: Giới thiệu giải pháp AI",
            "Trang 2: Kiến trúc hệ thống RAG",
            "Trang 3: Kế hoạch triển khai",
        ]
    else:
        pages = [
            "Trang 1: Gioi thieu giai phap AI",
            "Trang 2: Kien truc he thong RAG",
            "Trang 3: Ke hoach trien khai",
        ]

    pdf_bytes = generate_pdf(pages)
    res = DocumentParser.parse("technical_spec.pdf", pdf_bytes)

    assert res.metadata.page_count == 3
    assert res.total_segments == 3
    for idx, expected in enumerate(pages):
        assert res.segments[idx].page == idx + 1
        assert ("Trang" in res.segments[idx].text)
        assert res.segments[idx].segment_type == SegmentType.TEXT


def test_pdf_scanned_requires_ocr():
    """Test detecting scanned / image-only PDF requiring OCR."""
    pdf_bytes = generate_scanned_pdf()
    res = DocumentParser.parse("scanned_doc.pdf", pdf_bytes)

    assert res.metadata.page_count == 1
    assert res.requires_ocr is True
    assert res.segments[0].metadata["requires_ocr"] is True
    assert res.segments[0].metadata["has_text"] is False
    assert res.segments[0].metadata["image_count"] > 0


def test_pdf_corrupted():
    """Test handling corrupted PDF content."""
    corrupt_bytes = b"%PDF-1.4\ncorrupted incomplete byte stream invalid"
    with pytest.raises(CorruptedDocumentError):
        DocumentParser.parse("corrupt.pdf", corrupt_bytes)


def test_pdf_encrypted():
    """Test handling password-encrypted PDF."""
    enc_bytes = generate_encrypted_pdf(password="secret123")
    with pytest.raises(EncryptedDocumentError):
        DocumentParser.parse("protected.pdf", enc_bytes)


# =====================================================================
# DOCX Parsing Tests
# =====================================================================

def test_docx_paragraphs_only():
    """Test extracting DOCX containing only paragraphs."""
    paragraphs = [
        "Điều 1: Mục đích và phạm vi ứng dụng.",
        "Điều 2: Quyền và nghĩa vụ các bên.",
        "Điều 3: Điều khoản thi hành.",
    ]
    docx_bytes = generate_docx_paragraphs(paragraphs)
    res = DocumentParser.parse("agreement.docx", docx_bytes)

    assert res.file_type == FileType.DOCX
    assert res.metadata.paragraph_count == 3
    assert res.metadata.table_count == 0
    assert res.total_segments == 3
    for idx, p_text in enumerate(paragraphs):
        assert res.segments[idx].segment_type == SegmentType.TEXT
        assert res.segments[idx].text == p_text


def test_docx_table_only():
    """Test extracting DOCX containing only a table."""
    table_rows = [
        ["Mã hàng", "Tên sản phẩm", "Đơn giá"],
        ["SP01", "GPU H100", "30000"],
        ["SP02", "Server Dell R750", "12000"],
    ]
    docx_bytes = generate_docx_table(table_rows)
    res = DocumentParser.parse("price_list.docx", docx_bytes)

    assert res.file_type == FileType.DOCX
    assert res.metadata.table_count == 1
    assert res.total_segments == 1
    table_segment = res.segments[0]
    assert table_segment.segment_type == SegmentType.TABLE
    assert table_segment.table_data == table_rows
    assert "GPU H100" in table_segment.text


def test_docx_mixed_paragraphs_and_tables():
    """Test preserving order of interleaved paragraphs and tables in DOCX."""
    elements = [
        ("p", "Báo cáo tiến độ quý 4:"),
        ("tbl", [["Hạng mục", "Trạng thái"], ["Backend API", "Hoàn thành"]]),
        ("p", "Nhận xét tổng kết tiến độ khả quan."),
    ]
    docx_bytes = generate_docx_mixed(elements)
    res = DocumentParser.parse("status_report.docx", docx_bytes)

    assert res.total_segments == 3
    assert res.metadata.paragraph_count == 2
    assert res.metadata.table_count == 1

    # Verify sequential preservation
    assert res.segments[0].segment_type == SegmentType.TEXT
    assert res.segments[0].text == "Báo cáo tiến độ quý 4:"

    assert res.segments[1].segment_type == SegmentType.TABLE
    assert res.segments[1].table_data == [["Hạng mục", "Trạng thái"], ["Backend API", "Hoàn thành"]]

    assert res.segments[2].segment_type == SegmentType.TEXT
    assert res.segments[2].text == "Nhận xét tổng kết tiến độ khả quan."


def test_docx_corrupted():
    """Test handling corrupted DOCX file."""
    corrupted_bytes = b"PK\x03\x04corrupted fake docx archive content"
    with pytest.raises(CorruptedDocumentError):
        DocumentParser.parse("invalid.docx", corrupted_bytes)


# =====================================================================
# XLSX Parsing Tests
# =====================================================================

def test_xlsx_multiple_worksheets():
    """Test extracting multiple worksheets from XLSX."""
    sheets = {
        "DoanhSo": [
            ["Khu vực", "Doanh số"],
            ["Miền Bắc", 120000000],
            ["Miền Nam", 180000000],
        ],
        "ChiPhi": [
            ["Khoản mục", "Số tiền"],
            ["Nhân sự", 50000000],
        ],
    }
    xlsx_bytes = generate_xlsx(sheets)
    res = DocumentParser.parse("financials.xlsx", xlsx_bytes)

    assert res.file_type == FileType.XLSX
    assert res.metadata.sheet_count == 2
    assert res.total_segments == 2

    assert res.segments[0].sheet_name == "DoanhSo"
    assert res.segments[0].segment_type == SegmentType.SHEET
    assert res.segments[0].table_data[0] == ["Khu vực", "Doanh số"]

    assert res.segments[1].sheet_name == "ChiPhi"
    assert res.segments[1].table_data[0] == ["Khoản mục", "Số tiền"]


def test_xlsx_empty_cells():
    """Test handling empty cells (None) in XLSX."""
    sheets = {
        "KhoHang": [
            ["Mã SP", "Tên SP", "Số lượng", "Ghi chú"],
            ["SP10", "Router Cisco", None, "Chưa kiểm kê"],
            ["SP11", None, 15, None],
        ]
    }
    xlsx_bytes = generate_xlsx(sheets)
    res = DocumentParser.parse("inventory.xlsx", xlsx_bytes)

    table = res.segments[0].table_data
    assert table[1][2] is None
    assert table[2][1] is None
    assert table[2][3] is None


def test_xlsx_dates_and_datetimes():
    """Test proper ISO serialization conversion for date and datetime cells."""
    d = datetime.date(2026, 11, 16)
    dt = datetime.datetime(2026, 11, 16, 10, 30, 0)
    sheets = {
        "NhatKy": [
            ["Hoạt động", "Ngày", "Thời điểm"],
            ["Khởi động", d, dt],
        ]
    }
    xlsx_bytes = generate_xlsx(sheets)
    res = DocumentParser.parse("audit_log.xlsx", xlsx_bytes)

    row = res.segments[0].table_data[1]
    # Date/datetime should be converted to ISO format strings
    assert "2026-11-16" in row[1]
    assert "2026-11-16T10:30:00" in row[2]


def test_xlsx_corrupted():
    """Test handling corrupted XLSX content."""
    corrupt_bytes = b"PK\x03\x04corrupted fake xlsx archive"
    with pytest.raises(CorruptedDocumentError):
        DocumentParser.parse("broken.xlsx", corrupt_bytes)


# =====================================================================
# Validation and Edge Case Tests
# =====================================================================

def test_empty_file_raises_empty_file_error():
    """Test that zero-byte input raises EmptyFileError."""
    with pytest.raises(EmptyFileError):
        DocumentParser.parse("empty.pdf", b"")


def test_unsupported_extension_raises_unsupported_error():
    """Test that non-supported file extension raises UnsupportedFileTypeError."""
    with pytest.raises(UnsupportedFileTypeError):
        DocumentParser.parse("program.exe", b"fake binary content")


def test_parse_document_convenience_function():
    """Test the module-level parse_document functional shortcut."""
    font_path = _get_unicode_font_path()
    sample_text = "Nội dung tài liệu kiểm thử" if font_path else "Noi dung tai lieu kiem thu"
    pdf_bytes = generate_pdf([sample_text])
    res = parse_document("sample.pdf", pdf_bytes)
    assert res.file_type == FileType.PDF
    assert res.total_segments == 1
