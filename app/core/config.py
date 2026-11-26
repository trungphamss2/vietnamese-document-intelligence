"""Application configuration module using Pydantic Settings."""

from typing import Optional, Set

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the application."""

    PROJECT_NAME: str = "Vietnamese Document Intelligence & RAG Platform"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = (
        "Document processing pipeline and REST API for Vietnamese documents "
        "(PDF, DOCX, XLSX)."
    )
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Document upload & processing limits (20 MB default)
    MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024

    # Supported file extensions
    SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".xlsx"}

    # OCR & Vision Layout Configuration (Milestone 02)
    OCR_ENABLED: bool = True
    OCR_LANG: str = "vi"
    OCR_USE_GPU: bool = True
    OCR_DPI: int = 150
    OCR_USE_ORIENTATION_CLASSIFY: bool = True
    OCR_USE_UNWARPING: bool = False
    OCR_CONFIDENCE_THRESHOLD: float = 0.5
    PADDLE_CACHE_DIR: str = "D:/rag/vietnamese-document-intelligence/.cache/paddlex"
    PADDLE_HOME_DIR: str = "D:/rag/vietnamese-document-intelligence/.cache/paddle"

    # Text Chunking Configuration (Milestone 03)
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MIN_CHUNK_SIZE: int = 30
    CHUNK_MAX_TOKENS: int = 512

    # Embedding Configuration (Milestone 03)
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "auto"  # "cuda", "cpu", or "auto"
    EMBEDDING_BATCH_SIZE: int = 4  # Optimized for RTX 3050 6GB
    EMBEDDING_MAX_SEQ_LENGTH: int = 512
    EMBEDDING_DIM: int = 1024
    EMBEDDING_USE_FP16: bool = True
    HF_CACHE_DIR: str = "D:/rag/vietnamese-document-intelligence/.cache/hf"
    LOCAL_SNAPSHOT_PATH: Optional[str] = (
        "C:/Users/trung/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"
    )


    # Qdrant Vector Database Configuration (Milestone 03)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_COLLECTION: str = "vietnamese_documents"
    QDRANT_STORAGE_DIR: str = "D:/rag/qdrant_storage"

    # BM25 Sparse Retrieval Configuration (Milestone 04)
    BM25_STORAGE_PATH: str = "data/bm25_index.json"
    BM25_K1: float = 1.5
    BM25_B: float = 0.75

    # Hybrid Search & Reciprocal Rank Fusion (RRF) Configuration (Milestone 04)
    RRF_K: int = 60
    RRF_WEIGHT_DENSE: float = 1.0
    RRF_WEIGHT_SPARSE: float = 1.0
    HYBRID_CANDIDATE_LIMIT: int = 20

    # Cross-Encoder Reranker Configuration (Milestone 04)
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_DEVICE: str = "auto"  # "cuda", "cpu", or "auto"
    RERANKER_BATCH_SIZE: int = 8  # Optimized for 6GB VRAM
    RERANKER_MAX_LENGTH: int = 512
    RERANKER_USE_FP16: bool = True
    RERANKER_SNAPSHOT_PATH: Optional[str] = None


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
