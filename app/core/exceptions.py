"""Custom exception classes for document processing and validation."""


class DocumentParserException(Exception):
    """Base exception for all document processing errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CorruptedDocumentError(DocumentParserException):
    """Raised when document content is corrupted, truncated, or unreadable."""

    pass


class EncryptedDocumentError(DocumentParserException):
    """Raised when document is password-protected or encrypted."""

    pass


class EmptyFileError(DocumentParserException):
    """Raised when an input document has 0 bytes."""

    pass


class UnsupportedFileTypeError(DocumentParserException):
    """Raised when an input document extension/format is not supported."""

    pass


class FileSizeExceededError(DocumentParserException):
    """Raised when document size exceeds the allowed threshold."""

    pass


class OCREngineError(DocumentParserException):
    """Raised when OCR processing fails."""

    pass


class EmbeddingEngineError(DocumentParserException):
    """Raised when text embedding fails."""

    pass


class VectorStoreError(DocumentParserException):
    """Raised when vector store operations fail."""

    pass


class ChunkingError(DocumentParserException):
    """Raised when text chunking fails."""

    pass


class BM25Error(DocumentParserException):
    """Raised when BM25 indexing or retrieval fails."""

    pass


class RerankerError(DocumentParserException):
    """Raised when Cross-Encoder reranking fails."""

    pass


class HybridSearchError(DocumentParserException):
    """Raised when hybrid search fusion or retrieval fails."""

    pass

