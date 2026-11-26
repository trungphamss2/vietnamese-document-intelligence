"""Unit and integration tests for RRF fusion and HybridSearchService (Milestone 04)."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chunk import HybridSearchRequest, SearchResultItem, TextChunk
from app.services.bm25_service import BM25Service
from app.services.hybrid_search_service import HybridSearchService, compute_rrf_score

client = TestClient(app)


def test_compute_rrf_score_math():
    """Verify Reciprocal Rank Fusion mathematical calculation."""
    # Rank 1 in both dense and sparse with k=60, weights=1.0 -> 2 / 61
    both_r1 = compute_rrf_score(dense_rank=1, sparse_rank=1, k=60)
    assert pytest.approx(both_r1, 1e-6) == 2.0 / 61.0

    # Rank 1 in dense only
    dense_only = compute_rrf_score(dense_rank=1, sparse_rank=None, k=60)
    assert pytest.approx(dense_only, 1e-6) == 1.0 / 61.0

    # Rank 2 in both -> 2/62 > Rank 1 in one (1/61)
    both_r2 = compute_rrf_score(dense_rank=2, sparse_rank=2, k=60)
    assert both_r2 > dense_only


def test_hybrid_fusion_dedup_and_reranking(tmp_path: Path):
    """Verify RRF deduplication, metadata preservation, and reranker toggle."""
    bm25 = BM25Service(storage_path=str(tmp_path / "bm25_hybrid.json"))
    chunks = [
        TextChunk(
            chunk_id="c_overlap",
            document_id="doc_1",
            filename="invoice.pdf",
            page=1,
            chunk_index=0,
            content_type="paragraph",
            text="Hóa đơn VAT số 0004589 tổng thanh toán 55.000.000 VNĐ.",
            metadata={"source": "ocr"},
        ),
        TextChunk(
            chunk_id="c_sparse_only",
            document_id="doc_1",
            filename="invoice.pdf",
            page=1,
            chunk_index=1,
            content_type="table",
            text="Mã số thuế 0312345678 Công ty Cổ phần Công nghệ AI.",
            metadata={"source": "ocr"},
        ),
    ]
    bm25.index_chunks(chunks, document_id="doc_1")

    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 1024

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        SearchResultItem(
            chunk_id="c_overlap",
            document_id="doc_1",
            filename="invoice.pdf",
            page=1,
            chunk_index=0,
            content_type="paragraph",
            text="Hóa đơn VAT số 0004589 tổng thanh toán 55.000.000 VNĐ.",
            score=0.82,
            metadata={"source": "ocr"},
        ),
        SearchResultItem(
            chunk_id="c_dense_only",
            document_id="doc_2",
            filename="report.pdf",
            page=2,
            chunk_index=0,
            content_type="paragraph",
            text="Báo cáo doanh thu bán hàng và cung cấp dịch vụ.",
            score=0.75,
            metadata={"source": "native"},
        ),
    ]

    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda query, candidates, top_k, score_threshold: [
        {**c, "rerank_score": 0.95 if c["chunk_id"] == "c_overlap" else 0.12, "score": 0.95 if c["chunk_id"] == "c_overlap" else 0.12}
        for c in candidates
    ][:top_k]

    service = HybridSearchService(
        embedder=mock_embedder,
        vector_store=mock_vector_store,
        bm25_service=bm25,
        reranker_service=mock_reranker,
    )

    # 1. With reranking disabled -> pure RRF order, c_overlap deduplicated & boosted
    res_rrf = service.search_hybrid(
        HybridSearchRequest(query="0004589 VAT 0312345678", top_k=5, candidate_limit=10, enable_reranking=False)
    )
    assert res_rrf.rerank_applied is False
    assert res_rrf.fused_candidates_count == 3  # c_overlap, c_sparse_only, c_dense_only (deduplicated)
    chunk_ids = [r.chunk_id for r in res_rrf.results]
    assert len(chunk_ids) == len(set(chunk_ids))  # Strictly unique
    assert res_rrf.results[0].chunk_id == "c_overlap"
    assert res_rrf.results[0].dense_rank == 1
    assert res_rrf.results[0].sparse_rank == 1

    # 2. With reranking enabled
    res_rerank = service.search_hybrid(
        HybridSearchRequest(query="0004589 VAT", top_k=2, candidate_limit=10, enable_reranking=True)
    )
    assert res_rerank.rerank_applied is True
    assert len(res_rerank.results) == 2
    assert res_rerank.results[0].rerank_score == 0.95


def test_hybrid_search_api_empty_query():
    """Verify POST /search/hybrid rejects blank queries with HTTP 400."""
    response = client.post("/search/hybrid", json={"query": "   "})
    assert response.status_code == 400


def test_sync_delete_qdrant_and_bm25(tmp_path: Path):
    """Verify DELETE /documents/{document_id} removes chunks from both Qdrant and BM25."""
    from qdrant_client import QdrantClient
    from app.api.routes.indexing import get_bm25_service, get_vector_store
    from app.services.vector_store import QdrantVectorStore

    bm25 = BM25Service(storage_path=str(tmp_path / "bm25_del.json"))
    chunks = [
        TextChunk(
            chunk_id="del_c0",
            document_id="doc_to_delete",
            filename="del.pdf",
            page=1,
            chunk_index=0,
            content_type="paragraph",
            text="Tài liệu thử nghiệm đồng bộ xóa giữa Qdrant và BM25.",
        )
    ]
    bm25.index_chunks(chunks, document_id="doc_to_delete")

    # Use real QdrantClient in memory to verify full delete synchronization
    mem_vs = QdrantVectorStore.__new__(QdrantVectorStore)
    mem_vs.host = "memory"
    mem_vs.port = 0
    mem_vs.collection_name = "test_sync_del"
    mem_vs.client = QdrantClient(":memory:")
    mem_vs.ensure_collection()
    mem_vs.upsert_chunks(chunks, vectors=[[0.05] * 1024], document_id="doc_to_delete")

    app.dependency_overrides[get_vector_store] = lambda: mem_vs
    app.dependency_overrides[get_bm25_service] = lambda: bm25
    try:
        res = client.delete("/documents/doc_to_delete")
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"
        assert bm25.total_chunks == 0
        assert mem_vs.search([0.05] * 1024, limit=5) == []
    finally:
        app.dependency_overrides.clear()
