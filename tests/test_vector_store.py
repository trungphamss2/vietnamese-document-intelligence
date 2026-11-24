"""Unit and integration tests for QdrantVectorStore (Milestone 03)."""

import uuid
import pytest
from app.core.config import settings
from app.schemas.chunk import TextChunk
from app.services.vector_store import QdrantVectorStore


@pytest.fixture
def test_vector_store() -> QdrantVectorStore:
    """Fixture providing QdrantVectorStore connected to test collection."""
    test_collection = f"test_collection_{uuid.uuid4().hex[:8]}"
    store = QdrantVectorStore(collection_name=test_collection)
    yield store
    # Cleanup test collection after tests
    try:
        store.client.delete_collection(test_collection)
    except Exception:
        pass


def test_ensure_collection(test_vector_store: QdrantVectorStore):
    """Test collection creation and verification."""
    client = test_vector_store.client
    col_info = client.get_collection(test_vector_store.collection_name)
    assert col_info is not None
    assert col_info.config.params.vectors.size == settings.EMBEDDING_DIM


def test_upsert_and_search(test_vector_store: QdrantVectorStore):
    """Test upserting chunks and performing vector search."""
    doc_id = "doc_test_search"
    chunks = [
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=doc_id,
            filename="contract.pdf",
            page=1,
            chunk_index=0,
            content_type="paragraph",
            text="Hợp đồng cung cấp giải pháp trí tuệ nhân tạo OCR tiếng Việt.",
        ),
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=doc_id,
            filename="contract.pdf",
            page=2,
            chunk_index=1,
            content_type="paragraph",
            text="Thời gian bảo hành thiết bị là ba mươi sáu tháng kể từ ngày bàn giao.",
        ),
    ]

    # Dummy normalized 1024-dim vectors
    vec1 = [0.0] * 1024
    vec1[0] = 1.0
    vec2 = [0.0] * 1024
    vec2[1] = 1.0
    vectors = [vec1, vec2]

    # 1. Upsert
    inserted = test_vector_store.upsert_chunks(chunks=chunks, vectors=vectors, document_id=doc_id)
    assert inserted == 2

    # 2. Search exact match on vec1
    query_vec = [0.0] * 1024
    query_vec[0] = 1.0
    results = test_vector_store.search(query_vector=query_vec, limit=2)

    assert len(results) >= 1
    assert results[0].document_id == doc_id
    assert results[0].chunk_index == 0
    assert "OCR tiếng Việt" in results[0].text
    assert pytest.approx(results[0].score, 0.01) == 1.0


def test_filter_by_document_id(test_vector_store: QdrantVectorStore):
    """Test searching with document_id filtering."""
    # Doc A
    chunk_a = TextChunk(
        chunk_id=str(uuid.uuid4()),
        document_id="doc_A",
        filename="doc_a.pdf",
        page=1,
        chunk_index=0,
        content_type="paragraph",
        text="Văn bản của cơ quan A.",
    )
    # Doc B
    chunk_b = TextChunk(
        chunk_id=str(uuid.uuid4()),
        document_id="doc_B",
        filename="doc_b.pdf",
        page=1,
        chunk_index=0,
        content_type="paragraph",
        text="Văn bản của cơ quan B.",
    )

    vec = [0.0] * 1024
    vec[5] = 1.0

    test_vector_store.upsert_chunks([chunk_a], [vec], document_id="doc_A")
    test_vector_store.upsert_chunks([chunk_b], [vec], document_id="doc_B")

    # Search filtered by doc_B only
    results = test_vector_store.search(query_vector=vec, limit=5, document_id="doc_B")
    assert len(results) == 1
    assert results[0].document_id == "doc_B"
    assert "cơ quan B" in results[0].text


def test_reindexing_and_deduplication(test_vector_store: QdrantVectorStore):
    """Test that re-indexing the same document_id purges previous chunks cleanly."""
    doc_id = "doc_to_reindex"

    # Initial indexing: 3 chunks
    chunks_v1 = [
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=doc_id,
            filename="draft.docx",
            page=1,
            chunk_index=i,
            content_type="paragraph",
            text=f"Phiên bản 1 dòng {i}",
        )
        for i in range(3)
    ]
    vecs_v1 = [[0.1 * i] + [0.0] * 1023 for i in range(3)]
    test_vector_store.upsert_chunks(chunks=chunks_v1, vectors=vecs_v1, document_id=doc_id)

    # Re-indexing: updated to only 1 chunk
    chunks_v2 = [
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=doc_id,
            filename="draft.docx",
            page=1,
            chunk_index=0,
            content_type="paragraph",
            text="Phiên bản 2 đã được rút gọn chỉ còn 1 dòng duy nhất.",
        )
    ]
    query_vec = [0.0] * 1024
    query_vec[99] = 1.0
    test_vector_store.upsert_chunks(chunks=chunks_v2, vectors=[query_vec], document_id=doc_id)

    # Search should return only 1 result for doc_id
    results = test_vector_store.search(query_vector=query_vec, limit=10, document_id=doc_id)
    assert len(results) == 1
    assert "Phiên bản 2" in results[0].text


def test_delete_document(test_vector_store: QdrantVectorStore):
    """Test deleting document points by document_id."""
    doc_id = "doc_delete_me"
    chunk = TextChunk(
        chunk_id=str(uuid.uuid4()),
        document_id=doc_id,
        filename="temp.pdf",
        page=1,
        chunk_index=0,
        content_type="paragraph",
        text="Dữ liệu tạm thời cần xoá.",
    )
    vec = [0.5] * 1024
    test_vector_store.upsert_chunks([chunk], [vec], document_id=doc_id)

    # Confirm exists
    res_before = test_vector_store.search(query_vector=vec, limit=5, document_id=doc_id)
    assert len(res_before) == 1

    # Delete
    del_status = test_vector_store.delete_by_document_id(doc_id)
    assert del_status >= 1

    # Confirm purged
    res_after = test_vector_store.search(query_vector=vec, limit=5, document_id=doc_id)
    assert len(res_after) == 0
