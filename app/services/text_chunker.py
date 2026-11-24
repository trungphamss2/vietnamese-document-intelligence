"""Intelligent text chunking service for structured documents."""

import hashlib
import re
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import ChunkingError
from app.schemas.chunk import ChunkingConfig, TextChunk
from app.schemas.document import DocumentParseResponse, DocumentSegment, SegmentType


class IntelligentTextChunker:
    """Document-aware intelligent text chunker.
    
    Splits document segments into structured chunks respecting:
    - Headings as atomic context anchors.
    - Paragraphs split by sentence boundaries with configurable overlap.
    - Tables chunked by rows while always preserving table headers.
    - Page mapping, segment metadata, and max token constraints.
    - Document isolation (never mixes content across documents).
    """

    def __init__(self, config: Optional[ChunkingConfig] = None) -> None:
        if config is None:
            self.config = ChunkingConfig(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
                min_chunk_size=settings.MIN_CHUNK_SIZE,
                max_tokens=settings.CHUNK_MAX_TOKENS,
            )
        else:
            self.config = config

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for Vietnamese text (~1.2 - 1.3 tokens per whitespace-separated word)."""
        words = text.split()
        if not words:
            return 0
        return max(1, int(len(words) * 1.25) + 1)

    @staticmethod
    def generate_document_id(filename: str, content_hash_seed: Optional[str] = None) -> str:
        """Generate a deterministic or unique document identifier."""
        if content_hash_seed:
            digest = hashlib.sha256(f"{filename}_{content_hash_seed}".encode("utf-8")).hexdigest()[:16]
            return f"doc_{digest}"
        return f"doc_{uuid.uuid4().hex[:16]}"

    def chunk_document(
        self,
        document: DocumentParseResponse,
        document_id: Optional[str] = None,
    ) -> List[TextChunk]:
        """Split a full DocumentParseResponse into structured TextChunks."""
        try:
            doc_id = document_id or self.generate_document_id(document.filename)
            chunks: List[TextChunk] = []
            chunk_counter = 0

            for segment in document.segments:
                seg_chunks = self.chunk_segment(
                    segment=segment,
                    document_id=doc_id,
                    filename=document.filename,
                    start_index=chunk_counter,
                )
                chunks.extend(seg_chunks)
                chunk_counter += len(seg_chunks)

            return chunks
        except Exception as e:
            raise ChunkingError(f"Failed to chunk document '{document.filename}': {str(e)}") from e

    def chunk_segment(
        self,
        segment: DocumentSegment,
        document_id: str,
        filename: str,
        start_index: int = 0,
    ) -> List[TextChunk]:
        """Chunk an individual DocumentSegment according to its type and structure."""
        base_meta = {
            "source": segment.source,
            "confidence": segment.confidence,
            "bbox": segment.bbox,
            "layout_type": segment.layout_type,
            "sheet_name": segment.sheet_name,
            **segment.metadata,
        }

        # 1. Table or Sheet handling: Row-based splitting with preserved headers
        if segment.segment_type in (SegmentType.TABLE, SegmentType.SHEET) or segment.layout_type == "table":
            if segment.table_data and len(segment.table_data) > 0:
                return self._chunk_table_data(
                    table_data=segment.table_data,
                    document_id=document_id,
                    filename=filename,
                    page=segment.page,
                    sheet_name=segment.sheet_name,
                    base_meta=base_meta,
                    start_index=start_index,
                )
            elif segment.text.strip():
                return self._chunk_plain_text(
                    text=segment.text,
                    content_type="table",
                    document_id=document_id,
                    filename=filename,
                    page=segment.page,
                    base_meta=base_meta,
                    start_index=start_index,
                )

        # 2. Heading handling: Keep as atomic standalone chunk when possible
        if segment.layout_type == "heading":
            clean_text = segment.text.strip()
            if clean_text:
                tokens = self.estimate_tokens(clean_text)
                if len(clean_text) <= self.config.chunk_size and tokens <= self.config.max_tokens:
                    chunk = TextChunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        filename=filename,
                        page=segment.page,
                        chunk_index=start_index,
                        content_type="heading",
                        text=clean_text,
                        token_count=tokens,
                        table_header=None,
                        metadata=base_meta,
                    )
                    return [chunk]
                else:
                    return self._chunk_plain_text(
                        text=clean_text,
                        content_type="heading",
                        document_id=document_id,
                        filename=filename,
                        page=segment.page,
                        base_meta=base_meta,
                        start_index=start_index,
                    )

        # 3. Regular Paragraph / Plain Text handling
        clean_text = segment.text.strip()
        if not clean_text:
            return []

        content_type = segment.layout_type or "paragraph"
        return self._chunk_plain_text(
            text=clean_text,
            content_type=content_type,
            document_id=document_id,
            filename=filename,
            page=segment.page,
            base_meta=base_meta,
            start_index=start_index,
        )

    def _chunk_table_data(
        self,
        table_data: List[List[Any]],
        document_id: str,
        filename: str,
        page: Optional[int],
        sheet_name: Optional[str],
        base_meta: Dict[str, Any],
        start_index: int,
    ) -> List[TextChunk]:
        """Split a 2D table into chunks of rows while retaining the header on every chunk."""
        if not table_data:
            return []

        raw_header = table_data[0]
        header_cols = [str(col).strip() if col is not None else "" for col in raw_header]
        headers = [h if h else f"Cột_{i+1}" for i, h in enumerate(header_cols)]

        rows = table_data[1:] if len(table_data) > 1 else []
        if not rows:
            header_str = " | ".join(headers)
            chunk_text = f"Bảng ({sheet_name or 'Dữ liệu'}):\n| {header_str} |"
            chunk = TextChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                filename=filename,
                page=page,
                chunk_index=start_index,
                content_type="table",
                text=chunk_text,
                token_count=self.estimate_tokens(chunk_text),
                table_header=headers,
                metadata={**base_meta, "row_count": 0},
            )
            return [chunk]

        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        prefix = f"Bảng ({sheet_name or 'Dữ liệu'}):\n{header_line}\n{separator_line}"

        chunks: List[TextChunk] = []
        current_rows: List[str] = []
        current_char_len = len(prefix)
        current_index = start_index

        for row in rows:
            cells = [str(cell).strip() if cell is not None else "" for cell in row]
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            row_line = "| " + " | ".join(cells[:len(headers)]) + " |"
            row_len = len(row_line) + 1

            # Check both character size limit and estimated token limit
            tentative_text = prefix + "\n" + "\n".join(current_rows + [row_line])
            tentative_tokens = self.estimate_tokens(tentative_text)

            if current_rows and (
                current_char_len + row_len > self.config.chunk_size
                or tentative_tokens > self.config.max_tokens
            ):
                chunk_body = prefix + "\n" + "\n".join(current_rows)
                chunks.append(
                    TextChunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        filename=filename,
                        page=page,
                        chunk_index=current_index,
                        content_type="table",
                        text=chunk_body,
                        token_count=self.estimate_tokens(chunk_body),
                        table_header=headers,
                        metadata={**base_meta, "row_count": len(current_rows)},
                    )
                )
                current_index += 1
                current_rows = [row_line]
                current_char_len = len(prefix) + row_len
            else:
                current_rows.append(row_line)
                current_char_len += row_len

        if current_rows:
            chunk_body = prefix + "\n" + "\n".join(current_rows)
            chunks.append(
                TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    filename=filename,
                    page=page,
                    chunk_index=current_index,
                    content_type="table",
                    text=chunk_body,
                    token_count=self.estimate_tokens(chunk_body),
                    table_header=headers,
                    metadata={**base_meta, "row_count": len(current_rows)},
                )
            )

        return chunks

    def _chunk_plain_text(
        self,
        text: str,
        content_type: str,
        document_id: str,
        filename: str,
        page: Optional[int],
        base_meta: Dict[str, Any],
        start_index: int,
    ) -> List[TextChunk]:
        """Split plain text using sentence boundaries, token limits, and overlap."""
        clean_text = text.strip()
        if not clean_text:
            return []

        tokens = self.estimate_tokens(clean_text)
        if len(clean_text) <= self.config.chunk_size and tokens <= self.config.max_tokens:
            return [
                TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    filename=filename,
                    page=page,
                    chunk_index=start_index,
                    content_type=content_type,
                    text=clean_text,
                    token_count=tokens,
                    table_header=None,
                    metadata=base_meta,
                )
            ]

        # Sentence-aware splitting for Vietnamese
        sentence_pattern = r"(?<=[.?!…\n])\s+"
        sentences = [s.strip() for s in re.split(sentence_pattern, clean_text) if s.strip()]

        if not sentences:
            sentences = [clean_text]

        chunks: List[TextChunk] = []
        current_chunk_sentences: List[str] = []
        current_length = 0
        current_index = start_index

        for sentence in sentences:
            # If a single sentence exceeds limits, hard split by words
            s_tokens = self.estimate_tokens(sentence)
            if len(sentence) > self.config.chunk_size or s_tokens > self.config.max_tokens:
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences).strip()
                    if len(chunk_text) >= self.config.min_chunk_size:
                        chunks.append(
                            TextChunk(
                                chunk_id=str(uuid.uuid4()),
                                document_id=document_id,
                                filename=filename,
                                page=page,
                                chunk_index=current_index,
                                content_type=content_type,
                                text=chunk_text,
                                token_count=self.estimate_tokens(chunk_text),
                                table_header=None,
                                metadata=base_meta,
                            )
                        )
                        current_index += 1
                    current_chunk_sentences = []
                    current_length = 0

                sub_chunks = self._hard_split_text(sentence)
                for sub in sub_chunks:
                    chunks.append(
                        TextChunk(
                            chunk_id=str(uuid.uuid4()),
                            document_id=document_id,
                            filename=filename,
                            page=page,
                            chunk_index=current_index,
                            content_type=content_type,
                            text=sub,
                            token_count=self.estimate_tokens(sub),
                            table_header=None,
                            metadata=base_meta,
                        )
                    )
                    current_index += 1
                continue

            sentence_len = len(sentence) + (1 if current_chunk_sentences else 0)
            tentative_text = " ".join(current_chunk_sentences + [sentence]).strip()
            tentative_tokens = self.estimate_tokens(tentative_text)

            if (current_length + sentence_len > self.config.chunk_size or tentative_tokens > self.config.max_tokens) and current_chunk_sentences:
                chunk_text = " ".join(current_chunk_sentences).strip()
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunks.append(
                        TextChunk(
                            chunk_id=str(uuid.uuid4()),
                            document_id=document_id,
                            filename=filename,
                            page=page,
                            chunk_index=current_index,
                            content_type=content_type,
                            text=chunk_text,
                            token_count=self.estimate_tokens(chunk_text),
                            table_header=None,
                            metadata=base_meta,
                        )
                    )
                    current_index += 1

                # Calculate overlap: take tail sentences from previous chunk
                overlap_sentences = []
                overlap_len = 0
                for s in reversed(current_chunk_sentences):
                    if overlap_len + len(s) + 1 <= self.config.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s) + 1
                    else:
                        break

                current_chunk_sentences = overlap_sentences + [sentence]
                current_length = sum(len(s) + 1 for s in current_chunk_sentences) - 1
            else:
                current_chunk_sentences.append(sentence)
                current_length += sentence_len

        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences).strip()
            if len(chunk_text) >= self.config.min_chunk_size or not chunks:
                chunks.append(
                    TextChunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        filename=filename,
                        page=page,
                        chunk_index=current_index,
                        content_type=content_type,
                        text=chunk_text,
                        token_count=self.estimate_tokens(chunk_text),
                        table_header=None,
                        metadata=base_meta,
                    )
                )

        return chunks

    def _hard_split_text(self, text: str) -> List[str]:
        """Split a long text by word boundaries when sentences exceed chunk_size or max_tokens."""
        words = text.split()
        if not words:
            return []

        sub_chunks: List[str] = []
        current_words: List[str] = []
        current_len = 0

        for w in words:
            w_len = len(w) + (1 if current_words else 0)
            tentative_tokens = int(len(current_words + [w]) * 1.25) + 1

            if (current_len + w_len > self.config.chunk_size or tentative_tokens > self.config.max_tokens) and current_words:
                sub_chunks.append(" ".join(current_words))
                current_words = [w]
                current_len = len(w)
            else:
                current_words.append(w)
                current_len += w_len

        if current_words:
            sub_chunks.append(" ".join(current_words))

        return sub_chunks
