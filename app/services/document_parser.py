"""Document parsing service supporting PDF, DOCX, and XLSX formats.

This module is designed to be independent of FastAPI and web frameworks,
taking raw bytes and filename as input, and returning unified schema outputs.
"""

import datetime
import io
from pathlib import Path
from typing import Any, List, Optional
import zipfile

import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
import openpyxl
import openpyxl.utils.exceptions
import pymupdf

from app.core.exceptions import (
    CorruptedDocumentError,
    DocumentParserException,
    EmptyFileError,
    EncryptedDocumentError,
    UnsupportedFileTypeError,
)
from app.schemas.document import (
    DocumentMetadata,
    DocumentParseResponse,
    DocumentSegment,
    FileType,
    SegmentType,
)


class DocumentParser:
    """Unified document parser for PDF, DOCX, and XLSX files."""

    @classmethod
    def parse(
        cls,
        filename: str,
        content: bytes,
        enable_ocr: Optional[bool] = None,
    ) -> DocumentParseResponse:
        """Parse document content based on file extension.

        Args:
            filename: Name of the input document including extension.
            content: Raw byte payload of the document.
            enable_ocr: Optional flag to enable/disable OCR for PDF documents.

        Returns:
            DocumentParseResponse containing extracted segments and metadata.

        Raises:
            EmptyFileError: If content is empty.
            UnsupportedFileTypeError: If file extension is unsupported.
            CorruptedDocumentError: If file is malformed or unreadable.
            EncryptedDocumentError: If file is password-protected.
        """
        if not content or len(content) == 0:
            raise EmptyFileError(f"Document '{filename}' is empty (0 bytes).")

        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return cls.parse_pdf(filename=filename, content=content, enable_ocr=enable_ocr)
        elif ext == ".docx":
            return cls.parse_docx(filename=filename, content=content)
        elif ext == ".xlsx":
            return cls.parse_xlsx(filename=filename, content=content)
        else:
            raise UnsupportedFileTypeError(
                f"Unsupported file format '{ext}' for file '{filename}'. "
                "Supported formats are: .pdf, .docx, .xlsx"
            )

    @classmethod
    def parse_pdf(
        cls,
        filename: str,
        content: bytes,
        enable_ocr: Optional[bool] = None,
    ) -> DocumentParseResponse:
        """Extract text and metadata from a PDF file using DocumentRouter.

        Handles per-page intelligent routing between native PyMuPDF and OCR,
        preserves page numbering and layout information.

        Args:
            filename: Original PDF filename.
            content: PDF binary content.
            enable_ocr: Optional flag to enable/disable OCR processing.

        Returns:
            DocumentParseResponse with structured segments.

        Raises:
            CorruptedDocumentError: If PDF structure is invalid.
            EncryptedDocumentError: If PDF is encrypted/password-protected.
        """
        from app.services.document_router import DocumentRouter

        return DocumentRouter.route_and_parse_pdf(
            filename=filename,
            content=content,
            enable_ocr=enable_ocr,
        )

    @classmethod
    def parse_docx(cls, filename: str, content: bytes) -> DocumentParseResponse:
        """Extract paragraphs and tables from a DOCX document in sequential order.

        Args:
            filename: Original DOCX filename.
            content: DOCX binary content.

        Returns:
            DocumentParseResponse with ordered paragraph and table segments.

        Raises:
            CorruptedDocumentError: If DOCX package is invalid or corrupted.
        """
        try:
            doc = docx.Document(io.BytesIO(content))
        except (
            docx.opc.exceptions.PackageNotFoundError,
            zipfile.BadZipFile,
            KeyError,
            Exception,
        ) as exc:
            raise CorruptedDocumentError(
                f"Failed to read DOCX document '{filename}': {str(exc)}"
            ) from exc

        segments: List[DocumentSegment] = []
        paragraph_count = 0
        table_count = 0

        try:
            # Iterate through body elements in document order to preserve sequencing
            for child in doc.element.body.iterchildren():
                if isinstance(child, CT_P):
                    paragraph = Paragraph(child, doc)
                    text = paragraph.text.replace("\xa0", " ").strip()
                    if text:
                        paragraph_count += 1
                        segment = DocumentSegment(
                            segment_id=len(segments) + 1,
                            segment_type=SegmentType.TEXT,
                            page=None,
                            text=text,
                            table_data=None,
                            metadata={"char_count": len(text)},
                        )
                        segments.append(segment)

                elif isinstance(child, CT_Tbl):
                    table = Table(child, doc)
                    table_rows: List[List[str]] = []
                    for row in table.rows:
                        row_cells = [cell.text.replace("\xa0", " ").strip() for cell in row.cells]
                        table_rows.append(row_cells)

                    table_count += 1
                    # Generate formatted text representation for indexing/RAG
                    table_text = "\n".join(" | ".join(row) for row in table_rows)
                    segment = DocumentSegment(
                        segment_id=len(segments) + 1,
                        segment_type=SegmentType.TABLE,
                        page=None,
                        text=table_text,
                        table_data=table_rows,
                        metadata={
                            "row_count": len(table_rows),
                            "col_count": len(table_rows[0]) if table_rows else 0,
                        },
                    )
                    segments.append(segment)

        except Exception as exc:
            raise CorruptedDocumentError(
                f"Error processing elements in DOCX '{filename}': {str(exc)}"
            ) from exc

        metadata = DocumentMetadata(
            file_size_bytes=len(content),
            paragraph_count=paragraph_count,
            table_count=table_count,
            extra={"format": "DOCX"},
        )

        return DocumentParseResponse(
            filename=filename,
            file_type=FileType.DOCX,
            requires_ocr=False,
            total_segments=len(segments),
            metadata=metadata,
            segments=segments,
        )

    @classmethod
    def parse_xlsx(cls, filename: str, content: bytes) -> DocumentParseResponse:
        """Extract all worksheets, rows, and cells from an XLSX workbook.

        Handles empty cells, formats date/datetime fields into ISO strings for
        JSON serialization, and guarantees proper workbook closing.

        Args:
            filename: Original XLSX filename.
            content: XLSX binary content.

        Returns:
            DocumentParseResponse with worksheet segments.

        Raises:
            CorruptedDocumentError: If workbook is corrupted or unreadable.
        """
        try:
            wb = openpyxl.load_workbook(
                filename=io.BytesIO(content),
                data_only=True,
                read_only=False,
            )
        except (
            openpyxl.utils.exceptions.InvalidFileException,
            zipfile.BadZipFile,
            KeyError,
            Exception,
        ) as exc:
            raise CorruptedDocumentError(
                f"Failed to read XLSX document '{filename}': {str(exc)}"
            ) from exc

        try:
            segments: List[DocumentSegment] = []
            sheet_count = len(wb.worksheets)

            for sheet in wb.worksheets:
                sheet_rows: List[List[Any]] = []
                for row in sheet.iter_rows(values_only=True):
                    row_vals: List[Any] = []
                    for cell in row:
                        if cell is None:
                            row_vals.append(None)
                        elif isinstance(
                            cell, (datetime.datetime, datetime.date, datetime.time)
                        ):
                            row_vals.append(cell.isoformat())
                        elif isinstance(cell, (int, float, bool, str)):
                            row_vals.append(cell)
                        else:
                            row_vals.append(str(cell))

                    # Include row only if it has at least one non-null value
                    if any(val is not None for val in row_vals):
                        sheet_rows.append(row_vals)

                # Format text representation for RAG consumption
                text_lines = [
                    " | ".join("" if c is None else str(c) for c in r)
                    for r in sheet_rows
                ]
                sheet_text = "\n".join(text_lines)

                col_count = max((len(r) for r in sheet_rows), default=0)
                segment = DocumentSegment(
                    segment_id=len(segments) + 1,
                    segment_type=SegmentType.SHEET,
                    sheet_name=sheet.title,
                    text=sheet_text,
                    table_data=sheet_rows,
                    metadata={
                        "sheet_name": sheet.title,
                        "row_count": len(sheet_rows),
                        "col_count": col_count,
                    },
                )
                segments.append(segment)

            metadata = DocumentMetadata(
                file_size_bytes=len(content),
                sheet_count=sheet_count,
                table_count=sheet_count,
                extra={"format": "XLSX"},
            )

            return DocumentParseResponse(
                filename=filename,
                file_type=FileType.XLSX,
                requires_ocr=False,
                total_segments=len(segments),
                metadata=metadata,
                segments=segments,
            )
        finally:
            wb.close()


def parse_document(
    filename: str,
    content: bytes,
    enable_ocr: Optional[bool] = None,
) -> DocumentParseResponse:
    """Convenience functional wrapper for DocumentParser.parse."""
    return DocumentParser.parse(filename=filename, content=content, enable_ocr=enable_ocr)
