"""Application configuration module using Pydantic Settings."""

from typing import Set
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
