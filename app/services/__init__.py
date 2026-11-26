"""Business logic and document processing services."""

from app.services.bm25_service import BM25Service, get_bm25_service, tokenize_vietnamese_bm25
from app.services.document_parser import DocumentParser, parse_document
from app.services.document_router import DocumentRouter
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.hybrid_search_service import HybridSearchService, compute_rrf_score, get_hybrid_search_service
from app.services.layout_processor import LayoutProcessor
from app.services.ocr_engine import VietnameseOCREngine, get_ocr_engine
from app.services.reranker_service import BGERerankerService, get_reranker_service
from app.services.text_chunker import IntelligentTextChunker
from app.services.vector_store import QdrantVectorStore, get_vector_store

__all__ = [
    "DocumentParser",
    "parse_document",
    "DocumentRouter",
    "LayoutProcessor",
    "VietnameseOCREngine",
    "get_ocr_engine",
    "IntelligentTextChunker",
    "EmbeddingService",
    "get_embedding_service",
    "QdrantVectorStore",
    "get_vector_store",
    "BM25Service",
    "get_bm25_service",
    "tokenize_vietnamese_bm25",
    "BGERerankerService",
    "get_reranker_service",
    "HybridSearchService",
    "get_hybrid_search_service",
    "compute_rrf_score",
]

