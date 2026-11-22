"""Document Routing service for intelligent per-page processing of PDF documents.

Routes native text pages to PyMuPDF and scanned/image pages to VietnameseOCREngine,
handling mixed PDFs seamlessly and preserving page numbering and layout.
"""

import logging
import time
from typing import List, Optional

import pymupdf

from app.core.config import settings
from app.core.exceptions import CorruptedDocumentError, EncryptedDocumentError
from app.schemas.document import (
    DocumentMetadata,
    DocumentParseResponse,
    DocumentSegment,
    FileType,
    SegmentType,
)
from app.services.layout_processor import LayoutProcessor
from app.services.ocr_engine import get_ocr_engine

logger = logging.getLogger(__name__)


class DocumentRouter:
    """Routes PDF pages intelligently between PyMuPDF (native) and PaddleOCR."""

    @classmethod
    def route_and_parse_pdf(
        cls,
        filename: str,
        content: bytes,
        enable_ocr: Optional[bool] = None,
    ) -> DocumentParseResponse:
        """Parse a PDF document with per-page intelligent routing.

        Args:
            filename: Document filename.
            content: Raw PDF bytes.
            enable_ocr: Override for settings.OCR_ENABLED.

        Returns:
            DocumentParseResponse with combined native and OCR segments.
        """
        t_start = time.perf_counter()
        use_ocr = settings.OCR_ENABLED if enable_ocr is None else enable_ocr

        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise CorruptedDocumentError(
                f"Failed to open PDF document '{filename}': {str(exc)}"
            ) from exc

        try:
            if doc.is_encrypted and doc.needs_pass:
                raise EncryptedDocumentError(
                    f"PDF document '{filename}' is encrypted and requires a password."
                )

            page_count = len(doc)
            if page_count == 0:
                raise CorruptedDocumentError(
                    f"PDF document '{filename}' is corrupted or contains 0 pages."
                )

            all_segments: List[DocumentSegment] = []
            ocr_page_count = 0
            native_page_count = 0
            ocr_confidences: List[float] = []
            has_scanned_pages = False
            current_segment_id = 1

            for page_index in range(page_count):
                page_num = page_index + 1
                try:
                    page = doc[page_index]
                    native_text = page.get_text("text").replace("\xa0", " ").strip()
                    images = page.get_images(full=True)
                except Exception as exc:
                    raise CorruptedDocumentError(
                        f"Failed reading page {page_num} of PDF '{filename}': {str(exc)}"
                    ) from exc

                has_native_text = bool(native_text)
                image_count = len(images)
                # Page requires OCR if text is missing or extremely low despite having images
                is_scanned_page = (not has_native_text) or (image_count > 0 and len(native_text) < 20)

                if is_scanned_page:
                    has_scanned_pages = True

                if is_scanned_page and use_ocr:
                    # Route to OCR Engine
                    logger.info(f"Page {page_num} of '{filename}' routed to VietnameseOCREngine (scan detected).")
                    ocr_page_count += 1

                    # Render page to high-quality image pixmap
                    pix = page.get_pixmap(dpi=settings.OCR_DPI)
                    img_bytes = pix.tobytes("png")

                    ocr_engine = get_ocr_engine()
                    ocr_res = ocr_engine.recognize(img_bytes)

                    if ocr_res.lines:
                        ocr_confidences.append(ocr_res.avg_confidence)

                    # Structure page segments via LayoutProcessor
                    page_segments, current_segment_id = LayoutProcessor.process_ocr_page(
                        ocr_result=ocr_res,
                        page_number=page_num,
                        start_segment_id=current_segment_id,
                        image_count=image_count,
                    )
                    all_segments.extend(page_segments)

                else:
                    # Route to Native PyMuPDF
                    native_page_count += 1
                    segment = DocumentSegment(
                        segment_id=current_segment_id,
                        segment_type=SegmentType.TEXT,
                        page=page_num,
                        text=native_text,
                        table_data=None,
                        source="native",
                        confidence=1.0 if has_native_text else None,
                        bbox=None,
                        layout_type="paragraph" if has_native_text else "unknown",
                        words=[],
                        metadata={
                            "page": page_num,
                            "has_text": has_native_text,
                            "image_count": image_count,
                            "requires_ocr": is_scanned_page,
                            "char_count": len(native_text),
                        },
                    )
                    all_segments.append(segment)
                    current_segment_id += 1

            t_end = time.perf_counter()
            total_duration_ms = round((t_end - t_start) * 1000, 2)
            avg_conf = (
                round(sum(ocr_confidences) / len(ocr_confidences), 4)
                if ocr_confidences
                else None
            )

            metadata = DocumentMetadata(
                file_size_bytes=len(content),
                page_count=page_count,
                ocr_applied=(ocr_page_count > 0),
                ocr_page_count=ocr_page_count,
                native_page_count=native_page_count,
                avg_confidence=avg_conf,
                processing_time_ms=total_duration_ms,
                extra={
                    "format": "PDF",
                    "encrypted": doc.is_encrypted,
                    "mixed_mode": (ocr_page_count > 0 and native_page_count > 0),
                },
            )

            # Indicates whether document contains scanned/image pages requiring OCR
            document_requires_ocr = has_scanned_pages

            return DocumentParseResponse(
                filename=filename,
                file_type=FileType.PDF,
                requires_ocr=document_requires_ocr,
                total_segments=len(all_segments),
                metadata=metadata,
                segments=all_segments,
            )

        finally:
            doc.close()
