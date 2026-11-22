"""Data models and schemas for document parsing and API responses."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"


class SegmentType(str, Enum):
    """Types of extracted document segments."""

    TEXT = "text"
    TABLE = "table"
    SHEET = "sheet"


class DocumentSegment(BaseModel):
    """Represents an atomic extracted segment from a document.

    Attributes:
        segment_id: 1-based sequential index of the segment within the document.
        segment_type: Type of segment (text, table, or sheet).
        page: 1-based page number (applicable to PDF documents).
        sheet_name: Worksheet name (applicable to XLSX documents).
        text: Extracted plain text or textual representation of tabular data.
        table_data: 2D array of rows and cells for table or sheet segments.
        metadata: Segment-level metadata (e.g. char count, OCR requirement, dimensions).
    """

    segment_id: int = Field(
        ...,
        description="1-based sequential index of the segment",
        ge=1,
    )
    segment_type: SegmentType = Field(
        ...,
        description="Segment classification: text, table, or sheet",
    )
    page: Optional[int] = Field(
        default=None,
        description="1-based page number for paginated documents (e.g. PDF)",
        ge=1,
    )
    sheet_name: Optional[str] = Field(
        default=None,
        description="Worksheet title (e.g. XLSX)",
    )
    text: str = Field(
        default="",
        description="Extracted plain text or text representation of structured data",
    )
    table_data: Optional[List[List[Any]]] = Field(
        default=None,
        description="Structured 2D row/cell representation for tables or sheets",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Segment-specific metadata",
    )
    # Milestone 02 Extensions
    source: Optional[str] = Field(
        default="native",
        description="Extraction source: 'native', 'ocr', or 'mixed'",
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score for OCR-extracted content (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    bbox: Optional[List[float]] = Field(
        default=None,
        description="Bounding box coordinates [x1, y1, x2, y2] if available",
    )
    layout_type: Optional[str] = Field(
        default=None,
        description="Layout classification: heading, paragraph, table, image, header_footer, unknown",
    )
    words: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Detailed list of detected text lines/words with confidence and bboxes",
    )


class DocumentMetadata(BaseModel):
    """Document-level metadata."""

    file_size_bytes: int = Field(
        ...,
        description="Original document size in bytes",
        ge=0,
    )
    page_count: Optional[int] = Field(
        default=None,
        description="Total page count (for PDF)",
        ge=0,
    )
    sheet_count: Optional[int] = Field(
        default=None,
        description="Total sheet count (for XLSX)",
        ge=0,
    )
    paragraph_count: Optional[int] = Field(
        default=None,
        description="Total non-empty paragraph count (for DOCX)",
        ge=0,
    )
    table_count: Optional[int] = Field(
        default=None,
        description="Total table/sheet count (for DOCX/XLSX)",
        ge=0,
    )
    # Milestone 02 Extensions
    ocr_applied: bool = Field(
        default=False,
        description="Whether OCR was performed on any part of the document",
    )
    ocr_page_count: int = Field(
        default=0,
        description="Number of pages processed via OCR",
        ge=0,
    )
    native_page_count: int = Field(
        default=0,
        description="Number of pages processed via native extraction",
        ge=0,
    )
    avg_confidence: Optional[float] = Field(
        default=None,
        description="Average OCR confidence score across OCR-processed content",
        ge=0.0,
        le=1.0,
    )
    processing_time_ms: Optional[float] = Field(
        default=None,
        description="Total pipeline processing latency in milliseconds",
        ge=0.0,
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional format-specific metadata",
    )


class DocumentParseResponse(BaseModel):
    """Unified response model for document parsing."""

    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Detected file type")
    requires_ocr: bool = Field(
        default=False,
        description="Indicates whether the document or any of its pages require OCR",
    )
    total_segments: int = Field(
        ...,
        description="Total number of segments extracted",
        ge=0,
    )
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    segments: List[DocumentSegment] = Field(
        ...,
        description="Sequential list of document segments",
    )


class HealthResponse(BaseModel):
    """Response model for the service health check endpoint."""

    status: str = Field(default="healthy", description="Service health status")
    version: str = Field(..., description="Current application version")
    environment: str = Field(..., description="Deployment environment")
