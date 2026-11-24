"""Unit tests for EmbeddingService using BAAI/bge-m3 (Milestone 03)."""

import math
import pytest
from app.core.config import settings
from app.core.exceptions import EmbeddingEngineError
from app.services.embedding_service import EmbeddingService


@pytest.fixture(scope="module")
def embedder() -> EmbeddingService:
    """Fixture providing initialized EmbeddingService."""
    return EmbeddingService.get_instance()


def test_embedding_dimension_and_device(embedder: EmbeddingService):
    """Test that embedding model outputs 1024-dim vectors and resolves device."""
    assert embedder.dimension == settings.EMBEDDING_DIM
    assert embedder.dimension == 1024
    assert embedder.device in ("cuda", "cpu")


def test_embed_single_text(embedder: EmbeddingService):
    """Test embedding a single Vietnamese sentence."""
    text = "Hệ thống xử lý tài liệu thông minh tiếng Việt"
    vectors = embedder.embed_texts([text])

    assert len(vectors) == 1
    vec = vectors[0]
    assert len(vec) == 1024

    # Verify L2 normalization: sum(x^2) should be approximately 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, 0.01) == 1.0


def test_embed_batch_inference_with_length_sorting(embedder: EmbeddingService):
    """Test batch inference with varied text lengths and length-based batching."""
    texts = [
        "Ngắn gọn.",
        "Thông số kỹ thuật phần cứng máy chủ AI và card đồ họa GPU NVIDIA RTX 3050 6GB GDDR6.",
        "Báo cáo tài chính thường niên.",
        "Quy trình xử lý ảnh scan văn bản bằng OCR và nhận diện bố cục văn bản đa cột phức tạp.",
    ]
    vectors = embedder.embed_texts(texts, batch_size=2, use_length_batching=True)

    assert len(vectors) == 4
    for vec in vectors:
        assert len(vec) == 1024
        assert all(isinstance(v, float) for v in vec)
        norm = math.sqrt(sum(x * x for x in vec))
        assert pytest.approx(norm, 0.01) == 1.0


def test_embed_query(embedder: EmbeddingService):
    """Test query embedding helper."""
    query = "Quy định thời hạn bảo hành bao lâu?"
    vec = embedder.embed_query(query)

    assert len(vec) == 1024
    assert isinstance(vec, list)


def test_embed_empty_query_raises_error(embedder: EmbeddingService):
    """Test that empty or blank queries raise EmbeddingEngineError."""
    with pytest.raises(EmbeddingEngineError):
        embedder.embed_query("")

    with pytest.raises(EmbeddingEngineError):
        embedder.embed_query("   ")


def test_numerical_consistency_fp16_vs_fp32(embedder: EmbeddingService):
    """Test numerical consistency between FP16 and FP32."""
    texts = [
        "Hợp đồng kinh tế và điều khoản thanh toán.",
        "Báo cáo tài chính quý 3 năm 2026.",
    ]
    consistency = embedder.compare_fp16_vs_fp32(texts)
    if consistency.get("status") != "skipped_no_cuda":
        assert consistency["avg_cosine_similarity"] >= 0.999
        assert consistency["max_absolute_difference"] < 0.01


def test_cpu_fallback_embed(embedder: EmbeddingService):
    """Test forced CPU fallback embedding produces valid vectors."""
    texts = ["Thử nghiệm suy luận chế độ dự phòng CPU."]
    vectors = embedder._cpu_fallback_embed(texts)

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024
    norm = math.sqrt(sum(x * x for x in vectors[0]))
    assert pytest.approx(norm, 0.01) == 1.0


def test_validate_vectors_rejects_invalid_values(embedder: EmbeddingService):
    """Test validation catches NaNs, Infs, and incorrect dimensions."""
    # Invalid dimension
    with pytest.raises(EmbeddingEngineError):
        embedder._validate_vectors([[0.1] * 512])

    # NaN value
    nan_vec = [0.0] * 1024
    nan_vec[0] = float("nan")
    with pytest.raises(EmbeddingEngineError):
        embedder._validate_vectors([nan_vec])

    # Inf value
    inf_vec = [0.0] * 1024
    inf_vec[1] = float("inf")
    with pytest.raises(EmbeddingEngineError):
        embedder._validate_vectors([inf_vec])
