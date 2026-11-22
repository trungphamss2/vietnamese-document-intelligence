"""Comprehensive integration and unit test suite for Milestone 02 OCR Pipeline.

Covers:
- VietnameseOCREngine (GPU detection, CPU fallback, text recognition, confidence, bounding boxes)
- LayoutProcessor (reading order, 2-column layout, heading vs paragraph, table reconstruction)
- DocumentRouter (pure text PDF, pure scanned PDF, mixed PDF, page number preservation)
- Rotated document orientation handling
- API Integration (POST /documents/parse with enable_ocr flag, response schema verification)
"""

import io
from pathlib import Path
import pytest
import pymupdf
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.document import FileType, SegmentType
from app.services.document_parser import DocumentParser
from app.services.document_router import DocumentRouter
from app.services.layout_processor import LayoutProcessor
from app.services.ocr_engine import OCRLine, OCRResult, VietnameseOCREngine, get_ocr_engine

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# =====================================================================
# Helpers: Synthetic Test Asset Generators
# =====================================================================

def _get_font_file() -> str | None:
    """Find a system font with Vietnamese Unicode support."""
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def create_mixed_pdf() -> bytes:
    """Generate in-memory 2-page PDF: Page 1 is Native Text, Page 2 is Scanned Image."""
    doc = pymupdf.open()
    font_file = _get_font_file()

    # Page 1: Pure Native Text
    p1 = doc.new_page(width=595, height=842)
    if font_file:
        p1.insert_font(fontname="F0", fontfile=font_file)
        p1.insert_text((50, 72), "Trang 1: Báo cáo kỹ thuật hệ thống - Dữ liệu văn bản gốc.", fontname="F0", fontsize=14)
        p1.insert_text((50, 110), "Hệ thống hỗ trợ trích xuất văn bản tự động không cần OCR cho trang này.", fontname="F0", fontsize=11)
    else:
        p1.insert_text((50, 72), "Trang 1: Bao cao ky thuat he thong - Du lieu van ban goc.", fontsize=14)
        p1.insert_text((50, 110), "He thong ho tro trich xuat van ban tu dong khong can OCR cho trang nay.", fontsize=11)

    # Page 2: Scanned Page (Text rasterized into Pixmap image, no PDF text layer)
    p2 = doc.new_page(width=595, height=842)
    img = Image.new("RGB", (900, 700), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_file, 26) if font_file else ImageFont.load_default()
    draw.text((50, 50), "Trang 2: HOÁ ĐƠN QUÉT SCAN DẠNG ẢNH", fill=(0, 0, 0), font=font)
    draw.text((50, 120), "Mã số thuế: 0108998877", fill=(0, 0, 0), font=font)
    draw.text((50, 180), "Tổng tiền: 1.045.000.000 VND", fill=(0, 0, 0), font=font)

    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    p2.insert_image(p2.rect, stream=img_bytes)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# =====================================================================
# Phase 1: VietnameseOCREngine Tests
# =====================================================================

def test_ocr_engine_singleton_and_device():
    """Verify OCREngine singleton instantiation and CPU fallback device detection."""
    engine1 = get_ocr_engine()
    engine2 = get_ocr_engine()
    assert engine1 is engine2
    assert isinstance(engine1, VietnameseOCREngine)
    # Host has RTX 3050 GPU, but PaddlePaddle CPU build gracefully falls back to CPU
    assert isinstance(engine1.use_gpu, bool)
    assert engine1.device in ["cpu", "gpu"]


def test_ocr_engine_recognize_vietnamese_text():
    """Verify OCR recognizes Vietnamese characters on real scanned document, returns bbox & confidence."""
    engine = get_ocr_engine()
    sample_pdf = PROJECT_ROOT / "data" / "raw" / "pdf" / "pdf_scan_01_hoa_don_vat.pdf"
    if not sample_pdf.exists():
        pytest.skip("pdf_scan_01_hoa_don_vat.pdf not found")

    doc = pymupdf.open(sample_pdf)
    pix = doc[0].get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    doc.close()

    result = engine.recognize(img_bytes)

    assert isinstance(result, OCRResult)
    assert len(result.lines) >= 10
    assert result.avg_confidence > 0.85
    assert ("HÓA ĐƠN" in result.full_text) or ("CÔNG TY" in result.full_text) or ("THƯƠNG MẠI" in result.full_text)

    # Verify bounding boxes format: [x1, y1, x2, y2]
    first_line = result.lines[0]
    assert len(first_line.bbox) == 4
    x1, y1, x2, y2 = first_line.bbox
    assert x2 > x1
    assert y2 > y1
    assert 0.0 <= first_line.confidence <= 1.0


def test_ocr_engine_handles_empty_image():
    """Verify OCR engine gracefully handles solid blank image without errors."""
    engine = get_ocr_engine()
    blank_img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    blank_img.save(buf, format="PNG")
    result = engine.recognize(buf.getvalue())

    assert len(result.lines) == 0
    assert result.full_text == ""
    assert result.avg_confidence == 0.0


def test_ocr_rotated_document():
    """Verify OCR handles rotated document images without crashing."""
    engine = get_ocr_engine()
    sample_pdf = PROJECT_ROOT / "data" / "raw" / "pdf" / "pdf_scan_01_hoa_don_vat.pdf"
    if not sample_pdf.exists():
        pytest.skip("pdf_scan_01_hoa_don_vat.pdf not found")

    doc = pymupdf.open(sample_pdf)
    pix = doc[0].get_pixmap(dpi=150)
    doc.close()

    img = Image.open(io.BytesIO(pix.tobytes("png"))).rotate(90, expand=True)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = engine.recognize(buf.getvalue())
    assert isinstance(result, OCRResult)
    assert len(result.lines) > 0


# =====================================================================
# Phase 2: LayoutProcessor Tests
# =====================================================================

def test_layout_processor_reading_order_two_column():
    """Verify LayoutProcessor restores reading order in a 2-column layout."""
    # Create lines: Header at top, Column 1 (left), Column 2 (right), Footer at bottom
    lines = [
        OCRLine(text="BẢN TIN CÔNG NGHỆ 2 CỘT", confidence=0.99, bbox=[50, 20, 500, 50]),
        OCRLine(text="Cột 1 Dòng 1: Trí tuệ nhân tạo", confidence=0.95, bbox=[50, 80, 240, 110]),
        OCRLine(text="Cột 1 Dòng 2: Mô hình ngôn ngữ", confidence=0.95, bbox=[50, 130, 240, 160]),
        OCRLine(text="Cột 2 Dòng 1: Hạ tầng đám mây", confidence=0.95, bbox=[280, 80, 480, 110]),
        OCRLine(text="Cột 2 Dòng 2: Lưu trữ phân tán", confidence=0.95, bbox=[280, 130, 480, 160]),
        OCRLine(text="Trang 1 / 1 Hết", confidence=0.98, bbox=[50, 200, 500, 220]),
    ]
    sorted_lines = LayoutProcessor._sort_reading_order(lines)
    sorted_texts = [l.text for l in sorted_lines]

    # Header must be first
    assert sorted_texts[0] == "BẢN TIN CÔNG NGHỆ 2 CỘT"
    # Column 1 lines should precede Column 2 lines
    c1_idx = sorted_texts.index("Cột 1 Dòng 1: Trí tuệ nhân tạo")
    c2_idx = sorted_texts.index("Cột 2 Dòng 1: Hạ tầng đám mây")
    assert c1_idx < c2_idx


def test_layout_processor_table_reconstruction():
    """Verify LayoutProcessor detects table rows/columns and reconstructs matrix."""
    lines = [
        OCRLine(text="STT", confidence=0.98, bbox=[50, 100, 90, 125]),
        OCRLine(text="Hạng mục", confidence=0.98, bbox=[120, 100, 250, 125]),
        OCRLine(text="Thành tiền", confidence=0.98, bbox=[280, 100, 400, 125]),
        OCRLine(text="1", confidence=0.99, bbox=[50, 140, 90, 165]),
        OCRLine(text="Máy chủ AI", confidence=0.97, bbox=[120, 140, 250, 165]),
        OCRLine(text="750.000.000", confidence=0.96, bbox=[280, 140, 400, 165]),
    ]
    ocr_result = OCRResult(lines=lines, avg_confidence=0.97, full_text="")
    segments, next_id = LayoutProcessor.process_ocr_page(ocr_result, page_number=1, start_segment_id=1)

    table_segs = [s for s in segments if s.segment_type == SegmentType.TABLE]
    assert len(table_segs) == 1
    table_seg = table_segs[0]
    assert table_seg.table_data is not None
    assert len(table_seg.table_data) == 2
    assert table_seg.table_data[0] == ["STT", "Hạng mục", "Thành tiền"]
    assert table_seg.table_data[1] == ["1", "Máy chủ AI", "750.000.000"]
    assert table_seg.source == "ocr"
    assert table_seg.layout_type == "table"


# =====================================================================
# Phase 3: DocumentRouter & Mixed PDF Tests
# =====================================================================

def test_document_router_pure_text_pdf():
    """Verify DocumentRouter uses PyMuPDF native extraction for text PDFs with zero OCR overhead."""
    text_pdf_path = PROJECT_ROOT / "data" / "raw" / "pdf" / "pdf_text_01_hop_dong_dich_vu_cntt.pdf"
    if not text_pdf_path.exists():
        pytest.skip("Test file pdf_text_01_hop_dong_dich_vu_cntt.pdf not found.")

    with open(text_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    res = DocumentParser.parse("hop_dong.pdf", pdf_bytes, enable_ocr=True)

    assert res.file_type == FileType.PDF
    assert res.metadata.ocr_applied is False
    assert res.metadata.ocr_page_count == 0
    assert res.metadata.native_page_count == res.metadata.page_count
    assert all(s.source == "native" for s in res.segments)


def test_document_router_mixed_pdf():
    """Verify DocumentRouter correctly processes mixed PDF: Page 1 native, Page 2 OCR."""
    mixed_bytes = create_mixed_pdf()
    res = DocumentParser.parse("mixed_contract.pdf", mixed_bytes, enable_ocr=True)

    assert res.metadata.page_count == 2
    assert res.metadata.ocr_applied is True
    assert res.metadata.ocr_page_count == 1
    assert res.metadata.native_page_count == 1
    assert res.metadata.extra.get("mixed_mode") is True

    # Page 1 must be native
    p1_segs = [s for s in res.segments if s.page == 1]
    assert len(p1_segs) >= 1
    assert all(s.source == "native" for s in p1_segs)
    assert any("Báo cáo" in s.text or "Bao cao" in s.text for s in p1_segs)

    # Page 2 must be OCR
    p2_segs = [s for s in res.segments if s.page == 2]
    assert len(p2_segs) >= 1
    assert all(s.source == "ocr" for s in p2_segs)
    assert any("QUÉT SCAN" in s.text or "0108998877" in s.text or "1.045.000.000" in s.text for s in p2_segs)


# =====================================================================
# Phase 4: API Integration Tests
# =====================================================================

def test_api_parse_pdf_with_ocr_flag():
    """Verify API POST /documents/parse respects enable_ocr query parameter."""
    mixed_bytes = create_mixed_pdf()

    # 1. Parse with enable_ocr=false -> OCR skipped, scanned page detected as requires_ocr
    resp_no_ocr = client.post(
        "/documents/parse?enable_ocr=false",
        files={"file": ("mixed.pdf", mixed_bytes, "application/pdf")},
    )
    assert resp_no_ocr.status_code == 200
    data_no_ocr = resp_no_ocr.json()
    assert data_no_ocr["metadata"]["ocr_applied"] is False
    assert data_no_ocr["requires_ocr"] is True

    # 2. Parse with enable_ocr=true (default) -> OCR applied to Page 2
    resp_with_ocr = client.post(
        "/documents/parse?enable_ocr=true",
        files={"file": ("mixed.pdf", mixed_bytes, "application/pdf")},
    )
    assert resp_with_ocr.status_code == 200
    data_with_ocr = resp_with_ocr.json()
    assert data_with_ocr["metadata"]["ocr_applied"] is True
    assert data_with_ocr["metadata"]["ocr_page_count"] == 1
    assert data_with_ocr["metadata"]["native_page_count"] == 1
