"""Data models and schemas for text chunking, embedding and vector search."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    """Represents an atomic text chunk derived from document parsing."""

    chunk_id: str = Field(..., description="Unique UUID for this chunk")
    document_id: str = Field(..., description="Unique identifier of the parent document")
    filename: str = Field(..., description="Source document filename")
    page: Optional[int] = Field(default=None, description="1-based page number if applicable", ge=1)
    chunk_index: int = Field(..., description="0-based sequential index of the chunk within the document", ge=0)
    content_type: str = Field(
        ...,
        description="Type of chunk: heading, paragraph, table, sheet, or page",
    )
    text: str = Field(..., description="Chunk content in plain text format")
    token_count: Optional[int] = Field(default=None, description="Estimated or actual token count")
    table_header: Optional[List[str]] = Field(
        default=None,
        description="Header columns preserved for table rows",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional chunk metadata (e.g. source, confidence, bounding box)",
    )


class ChunkingConfig(BaseModel):
    """Configuration parameters for text chunking."""

    chunk_size: int = Field(default=512, description="Target chunk size in characters", ge=50)
    chunk_overlap: int = Field(default=64, description="Overlap between consecutive chunks in characters", ge=0)
    min_chunk_size: int = Field(default=30, description="Minimum acceptable chunk size in characters", ge=10)
    max_tokens: int = Field(default=512, description="Maximum token limit per chunk", ge=32, le=8192)



class IndexResponse(BaseModel):
    """Response model for document indexing."""

    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    total_segments: int = Field(..., description="Number of parsed segments")
    total_chunks: int = Field(..., description="Number of generated text chunks")
    vector_dimension: int = Field(..., description="Embedding vector dimension")
    processing_time_ms: float = Field(..., description="Total pipeline processing latency in milliseconds")
    collection_name: str = Field(..., description="Qdrant collection name")
    status: str = Field(default="indexed", description="Indexing status")


class SearchRequest(BaseModel):
    """Request model for semantic vector search."""

    query: str = Field(..., description="Natural language search query", min_length=1)
    limit: int = Field(default=5, description="Maximum number of search results to return", ge=1, le=100)
    document_id: Optional[str] = Field(default=None, description="Filter results by specific document_id")
    score_threshold: Optional[float] = Field(
        default=None,
        description="Minimum similarity score threshold (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )


class SearchResultItem(BaseModel):
    """Represents a single matching chunk returned from vector search."""

    chunk_id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="Parent document ID")
    filename: str = Field(..., description="Source filename")
    page: Optional[int] = Field(default=None, description="Page number")
    chunk_index: int = Field(..., description="Chunk index")
    content_type: str = Field(..., description="Content type")
    text: str = Field(..., description="Matched chunk text")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class SearchResponse(BaseModel):
    """Response model for semantic vector search."""

    query: str = Field(..., description="The query executed")
    total_results: int = Field(..., description="Number of results found")
    results: List[SearchResultItem] = Field(default_factory=list, description="Ranked list of results")
    search_time_ms: float = Field(..., description="Search latency in milliseconds")


class DeleteDocumentResponse(BaseModel):
    """Response model for document deletion from vector database."""

    document_id: str = Field(..., description="ID of deleted document")
    status: str = Field(..., description="Deletion result status")
    deleted_points: int = Field(..., description="Number of vectors/points deleted")
