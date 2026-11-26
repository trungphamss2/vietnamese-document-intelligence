"""Unit tests for BGERerankerService using BAAI/bge-reranker-v2-m3 (Milestone 04)."""

import pytest
from app.core.exceptions import RerankerError
from app.services.reranker_service import BGERerankerService


@pytest.fixture(scope="module")
def reranker() -> BGERerankerService:
    """Provide initialized BGERerankerService instance."""
    return BGERerankerService.get_instance()


def test_reranker_initialization(reranker: BGERerankerService):
    """Verify Cross-Encoder model loads successfully on CUDA or CPU."""
    assert reranker.model is not None
    assert reranker.device in ("cuda", "cpu")


def test_reranker_scores_relevant_higher(reranker: BGERerankerService):
    """Verify relevant Vietnamese document passage receives strictly higher score than irrelevant one."""
    query = "Điều khoản hiệu lực hợp đồng và bảo mật thông tin"
    candidates = [
        {
            "chunk_id": "irrelevant_1",
            "document_id": "doc_2",
            "filename": "thuc_don.pdf",
            "page": 1,
            "content_type": "paragraph",
            "text": "Hôm nay thực đơn bữa trưa gồm có cơm tấm sườn bì chả và canh chua.",
            "metadata": {"tag": "food"},
        },
        {
            "chunk_id": "relevant_1",
            "document_id": "doc_1",
            "filename": "hop_dong.pdf",
            "page": 3,
            "content_type": "paragraph",
            "text": "Điều 6: Bảo mật thông tin. Hai bên cam kết bảo mật tuyệt đối dữ liệu trong suốt hiệu lực hợp đồng.",
            "metadata": {"tag": "legal"},
        },
    ]

    ranked = reranker.rerank(query=query, candidates=candidates, top_k=2)
    assert len(ranked) == 2
    assert ranked[0]["chunk_id"] == "relevant_1"
    assert ranked[0]["rerank_score"] > ranked[1]["rerank_score"]
    # Verify metadata preservation
    assert ranked[0]["document_id"] == "doc_1"
    assert ranked[0]["filename"] == "hop_dong.pdf"
    assert ranked[0]["page"] == 3
    assert ranked[0]["metadata"]["tag"] == "legal"


def test_reranker_top_k_and_threshold(reranker: BGERerankerService):
    """Test top_k truncation and score_threshold filtering."""
    query = "Báo cáo doanh thu thuần quý 3"
    candidates = [
        {"chunk_id": "c1", "text": "Doanh thu thuần quý 3 năm 2026 đạt 150 tỷ đồng."},
        {"chunk_id": "c2", "text": "Lợi nhuận sau thuế tăng trưởng 12% so với cùng kỳ."},
        {"chunk_id": "c3", "text": "Hướng dẫn cài đặt Docker trên hệ điều hành Windows 11."},
    ]

    top_1 = reranker.rerank(query=query, candidates=candidates, top_k=1)
    assert len(top_1) == 1
    assert top_1[0]["chunk_id"] == "c1"

    # High threshold should filter out irrelevant c3
    filtered = reranker.rerank(query=query, candidates=candidates, score_threshold=0.05)
    assert all(item["rerank_score"] >= 0.05 for item in filtered)


def test_reranker_cpu_fallback_and_empty_inputs(reranker: BGERerankerService):
    """Test CPU fallback execution and empty/invalid input handling."""
    assert reranker.rerank(query="test", candidates=[]) == []

    with pytest.raises(RerankerError):
        reranker.rerank(query="   ", candidates=[{"chunk_id": "c1", "text": "abc"}])

    scores = reranker._cpu_fallback_predict([
        ("hợp đồng kinh tế", "Hợp đồng kinh tế dịch vụ công nghệ thông tin.")
    ])
    assert len(scores) == 1
    assert isinstance(scores[0], float)


def test_reranker_oom_recovery_triggers_fallback(monkeypatch, reranker: BGERerankerService):
    """Test CUDA OOM triggers batch size halving and falls back to CPU predict."""
    import torch

    call_batch_sizes = []

    def fake_predict(pairs, batch_size=8, show_progress_bar=False):
        call_batch_sizes.append(batch_size)
        raise torch.cuda.OutOfMemoryError("Simulated CUDA OOM")

    monkeypatch.setattr(reranker.model, "predict", fake_predict)
    monkeypatch.setattr(reranker, "_cpu_fallback_predict", lambda pairs: [0.42 for _ in pairs])

    scores = reranker.predict_pairs([("q", "doc")], batch_size=4)
    assert scores == [0.42]
    assert call_batch_sizes == [4, 2, 1]
