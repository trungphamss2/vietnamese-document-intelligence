"""API integration tests for Vietnamese Document Intelligence Platform."""

import datetime
import io
import os
import pytest
from fastapi.testclient import TestClient
import pymupdf
import docx
import openpyxl

from app.main import app

client = TestClient(app)


# =====================================================================
# In-Memory Document Generators for API Testing
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


def make_valid_pdf() -> bytes:
    """Generate minimal valid PDF bytes."""
    doc = pymupdf.open()
    page = doc.new_page()
    font_path = _get_unicode_font_path()
    if font_path:
        page.insert_font(fontname="custom_font", fontfile=font_path)
        page.insert_text((50, 72), "Văn bản thử nghiệm API", fontname="custom_font", fontsize=12)
    else:
        page.insert_text((50, 72), "Van ban thu nghiem API", fontname="helv", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_valid_docx() -> bytes:
    """Generate minimal valid DOCX bytes."""
    doc = docx.Document()
    doc.add_paragraph("Tài liệu DOCX thử nghiệm qua API.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_valid_xlsx() -> bytes:
    """Generate minimal valid XLSX bytes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BangDuLieu"
    ws.append(["Mã", "Tên", "Thời gian"])
    ws.append(["A01", "Dự án RAG", datetime.date(2026, 11, 16)])
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


# =====================================================================
# Integration Tests
# =====================================================================

def test_health_endpoint():
    """Verify GET /health returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


def test_upload_pdf_success():
    """Verify POST /documents/parse successfully extracts PDF."""
    pdf_bytes = make_valid_pdf()
    response = client.post(
        "/documents/parse",
        files={"file": ("test_doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_doc.pdf"
    assert data["file_type"] == "pdf"
    assert data["requires_ocr"] is False
    assert data["metadata"]["page_count"] == 1
    assert len(data["segments"]) == 1
    assert ("Văn bản thử nghiệm" in data["segments"][0]["text"]) or ("Van ban thu nghiem" in data["segments"][0]["text"])


def test_upload_docx_success():
    """Verify POST /documents/parse successfully extracts DOCX."""
    docx_bytes = make_valid_docx()
    response = client.post(
        "/documents/parse",
        files={
            "file": (
                "test_doc.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_doc.docx"
    assert data["file_type"] == "docx"
    assert data["metadata"]["paragraph_count"] == 1
    assert len(data["segments"]) == 1
    assert "Tài liệu DOCX thử nghiệm" in data["segments"][0]["text"]


def test_upload_xlsx_success():
    """Verify POST /documents/parse successfully extracts XLSX."""
    xlsx_bytes = make_valid_xlsx()
    response = client.post(
        "/documents/parse",
        files={
            "file": (
                "test_sheet.xlsx",
                xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_sheet.xlsx"
    assert data["file_type"] == "xlsx"
    assert data["metadata"]["sheet_count"] == 1
    assert len(data["segments"]) == 1
    assert data["segments"][0]["sheet_name"] == "BangDuLieu"
    assert data["segments"][0]["table_data"][0] == ["Mã", "Tên", "Thời gian"]


def test_upload_empty_file():
    """Verify POST /documents/parse returns 400 for empty files."""
    response = client.post(
        "/documents/parse",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_unsupported_extension():
    """Verify POST /documents/parse returns 415 for unsupported file types."""
    response = client.post(
        "/documents/parse",
        files={"file": ("unsupported.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 415
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_oversized_file():
    """Verify POST /documents/parse returns 413 when file exceeds 20 MB."""
    # 20 MB + 1 KB
    large_payload = b"0" * (20 * 1024 * 1024 + 1024)
    response = client.post(
        "/documents/parse",
        files={"file": ("large.pdf", large_payload, "application/pdf")},
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed limit" in response.json()["detail"]


def test_upload_fake_extension_corrupt_content():
    """Verify POST /documents/parse returns 400 when file content is invalid/corrupt."""
    fake_content = b"This is clearly not a valid PDF or DOCX binary stream."

    # Test fake PDF
    res_pdf = client.post(
        "/documents/parse",
        files={"file": ("fake.pdf", fake_content, "application/pdf")},
    )
    assert res_pdf.status_code == 400
    assert "detail" in res_pdf.json()
    assert "Traceback" not in res_pdf.text

    # Test fake DOCX
    res_docx = client.post(
        "/documents/parse",
        files={"file": ("fake.docx", fake_content, "application/octet-stream")},
    )
    assert res_docx.status_code == 400
    assert "detail" in res_docx.json()
    assert "Traceback" not in res_docx.text

    # Test fake XLSX
    res_xlsx = client.post(
        "/documents/parse",
        files={"file": ("fake.xlsx", fake_content, "application/octet-stream")},
    )
    assert res_xlsx.status_code == 400
    assert "detail" in res_xlsx.json()
    assert "Traceback" not in res_xlsx.text


def test_upload_encrypted_pdf():
    """Verify POST /documents/parse returns 400 for password-protected PDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Encrypted content")
    enc_bytes = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="admin",
        user_pw="secret123",
    )
    doc.close()

    response = client.post(
        "/documents/parse",
        files={"file": ("protected.pdf", enc_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    assert "encrypted" in response.json()["detail"].lower()
    assert "Traceback" not in response.text
