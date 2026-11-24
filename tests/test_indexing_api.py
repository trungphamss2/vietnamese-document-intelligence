"""Integration tests for document indexing and semantic search API endpoints (Milestone 03)."""

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_index_docx_document():
    """Test POST /documents/index with a valid DOCX file."""
    # Create simple docx in memory
    from docx import Document
    doc = Document()
    doc.add_heading("HỢP ĐỒNG MUA BÁN HÀNG HÓA", level=1)
    doc.add_paragraph("Bên A đồng ý bán cho Bên B hệ thống máy chủ phục vụ tính toán AI.")
    doc.add_paragraph("Giá trị hợp đồng là 500.000.000 VNĐ, thanh toán làm hai đợt.")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    response = client.post(
        "/documents/index",
        files={"file": ("hop_dong_test.docx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"enable_ocr": "false"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "hop_dong_test.docx"
    assert data["total_chunks"] >= 2
    assert data["vector_dimension"] == 1024
    assert data["status"] == "indexed"
    assert "document_id" in data

    doc_id = data["document_id"]

    # Search for this document's content
    search_res = client.post(
        "/search/vector",
        json={"query": "giá trị hợp đồng thanh toán bao nhiêu tiền", "limit": 3, "document_id": doc_id},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_results"] >= 1
    assert any("500.000.000" in r["text"] for r in search_data["results"])

    # Delete the document
    del_res = client.delete(f"/documents/{doc_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "deleted"
    assert del_data["document_id"] == doc_id


def test_search_vector_empty_query():
    """Test POST /search/vector with blank query triggers 400 Bad Request."""
    response = client.post("/search/vector", json={"query": "   "})
    assert response.status_code == 400


def test_index_empty_file():
    """Test POST /documents/index with 0-byte file triggers 400 Bad Request."""
    response = client.post(
        "/documents/index",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400


def test_index_unsupported_extension():
    """Test POST /documents/index with unsupported file extension triggers 415."""
    response = client.post(
        "/documents/index",
        files={"file": ("test.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 415


def test_delete_empty_document_id():
    """Test DELETE /documents/{document_id} with whitespace-only ID triggers 400."""
    response = client.delete("/documents/%20")
    assert response.status_code == 400
