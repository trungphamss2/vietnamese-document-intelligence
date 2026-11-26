"""Unit tests for BM25Service sparse retrieval, tokenization, persistence, and sync (Milestone 04)."""

from pathlib import Path
from app.schemas.chunk import TextChunk
from app.services.bm25_service import BM25Service, tokenize_vietnamese_bm25


def _make_sample_chunks(doc_id: str = "doc_1") -> list[TextChunk]:
    return [
        TextChunk(
            chunk_id=f"{doc_id}_c0",
            document_id=doc_id,
            filename="hoa_don_01.pdf",
            page=1,
            chunk_index=0,
            content_type="paragraph",
            text="Hóa đơn giá trị gia tăng Mẫu số 01GTKT0/001 Số 0004589 ngày 15/10/2026.",
            metadata={"source": "ocr"},
        ),
        TextChunk(
            chunk_id=f"{doc_id}_c1",
            document_id=doc_id,
            filename="hoa_don_01.pdf",
            page=1,
            chunk_index=1,
            content_type="table",
            text="Thiết bị mạng Cisco Catalyst 9200 tổng tiền thanh toán 125.000.000 VNĐ.",
            metadata={"source": "ocr"},
        ),
    ]


def test_vietnamese_bm25_tokenizer():
    """Verify Vietnamese NFC normalization, lowercase, and composite invoice code tokenization."""
    tokens = tokenize_vietnamese_bm25("Hóa đơn Mẫu 01GTKT0/001 số HĐDV-AI năm 2026!")
    assert "hóa" in tokens
    assert "đơn" in tokens
    assert "01gtkt0/001" in tokens
    assert "01gtkt0" in tokens
    assert "001" in tokens
    assert "hđdv-ai" in tokens
    assert "hđdv" in tokens
    assert "2026" in tokens


def test_bm25_index_search_and_filter(tmp_path: Path):
    """Test BM25 indexing, exact identifier search, and document_id filtering."""
    storage = tmp_path / "bm25_test.json"
    bm25 = BM25Service(storage_path=str(storage))

    chunks_1 = _make_sample_chunks("doc_invoice")
    chunks_2 = [
        TextChunk(
            chunk_id="doc_contract_c0",
            document_id="doc_contract",
            filename="hop_dong.pdf",
            page=2,
            chunk_index=0,
            content_type="paragraph",
            text="Hợp đồng dịch vụ CNTT số 102/2026/HĐDV-AI điều khoản bảo mật dữ liệu.",
            metadata={"source": "native"},
        )
    ]

    assert bm25.index_chunks(chunks_1, document_id="doc_invoice") == 2
    assert bm25.index_chunks(chunks_2, document_id="doc_contract") == 1
    assert bm25.total_chunks == 3

    # Exact identifier match should prioritize invoice chunk
    hits = bm25.search("0004589 01GTKT0/001", limit=5)
    assert len(hits) >= 1
    assert hits[0]["chunk_id"] == "doc_invoice_c0"
    assert hits[0]["filename"] == "hoa_don_01.pdf"
    assert hits[0]["page"] == 1
    assert hits[0]["metadata"]["source"] == "ocr"

    # Filter by document_id
    filtered = bm25.search("2026", limit=5, document_id="doc_contract")
    assert len(filtered) == 1
    assert filtered[0]["document_id"] == "doc_contract"


def test_bm25_persistence_and_reload(tmp_path: Path):
    """Test BM25 index persistence to disk and clean reload."""
    storage = tmp_path / "bm25_persist.json"
    bm25_writer = BM25Service(storage_path=str(storage))
    bm25_writer.index_chunks(_make_sample_chunks("doc_persist"))
    assert storage.exists()

    # Load from disk in a new instance
    bm25_reader = BM25Service(storage_path=str(storage))
    assert bm25_reader.total_chunks == 2
    hits = bm25_reader.search("Cisco Catalyst 9200", limit=3)
    assert len(hits) == 1
    assert hits[0]["chunk_id"] == "doc_persist_c1"


def test_bm25_reindex_dedup_and_delete(tmp_path: Path):
    """Test deduplication on re-indexing and document deletion synchronization."""
    storage = tmp_path / "bm25_sync.json"
    bm25 = BM25Service(storage_path=str(storage))

    bm25.index_chunks(_make_sample_chunks("doc_a"), document_id="doc_a")
    bm25.index_chunks(
        [
            TextChunk(
                chunk_id="doc_b_c0",
                document_id="doc_b",
                filename="b.pdf",
                page=1,
                chunk_index=0,
                content_type="paragraph",
                text="Tài liệu kỹ thuật dự án RAG tiếng Việt.",
            )
        ],
        document_id="doc_b",
    )
    assert bm25.total_chunks == 3

    # Re-index doc_a with 1 updated chunk -> old 2 chunks must be purged
    bm25.index_chunks(
        [
            TextChunk(
                chunk_id="doc_a_new_c0",
                document_id="doc_a",
                filename="hoa_don_01_v2.pdf",
                page=1,
                chunk_index=0,
                content_type="paragraph",
                text="Hóa đơn cập nhật mới nhất số 9999999.",
            )
        ],
        document_id="doc_a",
    )
    assert bm25.total_chunks == 2
    assert bm25.search("0004589") == []
    assert bm25.search("9999999")[0]["chunk_id"] == "doc_a_new_c0"

    # Delete doc_a
    deleted = bm25.delete_by_document_id("doc_a")
    assert deleted == 1
    assert bm25.total_chunks == 1
    assert bm25.search("9999999") == []

    # Verify deletion persisted to disk
    bm25_reloaded = BM25Service(storage_path=str(storage))
    assert bm25_reloaded.total_chunks == 1
