"""BM25 Sparse Retrieval Service for Vietnamese Document Chunks (Milestone 04)."""

import json
import logging
import math
import os
import re
import threading
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.exceptions import BM25Error
from app.schemas.chunk import TextChunk

logger = logging.getLogger(__name__)

_BM25_LOCK = threading.Lock()


class PositiveBM25Okapi(BM25Okapi):
    """BM25Okapi using Lucene smooth IDF so small corpora never yield zero/negative IDFs."""

    def _calc_idf(self, nd: Dict[str, int]) -> None:
        for word, freq in nd.items():
            self.idf[word] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))


def tokenize_vietnamese_bm25(text: str) -> List[str]:
    """Tokenize Vietnamese text for BM25 keyword matching.

    Normalizes Unicode to NFC, converts to lowercase, and extracts alphanumeric
    words, technical identifiers, invoice codes, and punctuation-separated tokens.
    """
    if not text or not isinstance(text, str):
        return []

    normalized = unicodedata.normalize("NFC", text.lower())
    # Match alphanumeric words including Vietnamese diacritics and composite tokens with hyphens/slashes
    raw_tokens = re.findall(
        r"[a-z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ\-_/]+",
        normalized,
    )
    tokens: List[str] = []
    for tok in raw_tokens:
        clean = tok.strip("-_/")
        if clean:
            tokens.append(clean)
            # If token contains slash or hyphen (e.g., 01gtkt0/001, hđdv-ai), also index sub-parts
            if "/" in clean or "-" in clean:
                sub_parts = re.split(r"[\/\-_]+", clean)
                for part in sub_parts:
                    if part and len(part) >= 2:
                        tokens.append(part)
    return tokens


class BM25Service:
    """Thread-safe singleton service for BM25 sparse indexing, retrieval, and persistence."""

    _instance: Optional["BM25Service"] = None

    def __init__(
        self,
        storage_path: Optional[str] = None,
        k1: Optional[float] = None,
        b: Optional[float] = None,
    ) -> None:
        self.storage_path = Path(storage_path or settings.BM25_STORAGE_PATH)
        self.k1 = k1 if k1 is not None else settings.BM25_K1
        self.b = b if b is not None else settings.BM25_B
        self.chunks: Dict[str, Dict[str, Any]] = {}  # chunk_id -> chunk dict
        self.chunk_ids: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[PositiveBM25Okapi] = None

        self._load_index()

    @classmethod
    def get_instance(cls) -> "BM25Service":
        """Get or initialize singleton instance."""
        if cls._instance is None:
            with _BM25_LOCK:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        with _BM25_LOCK:
            cls._instance = None

    def _rebuild_bm25(self) -> None:
        """Rebuild the in-memory BM25Okapi model from current chunks."""
        self.chunk_ids = list(self.chunks.keys())
        self.tokenized_corpus = [
            tokenize_vietnamese_bm25(self.chunks[cid]["text"])
            for cid in self.chunk_ids
        ]
        if self.tokenized_corpus and any(len(c) > 0 for c in self.tokenized_corpus):
            self.bm25 = PositiveBM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b)
        else:
            self.bm25 = None
        logger.info("BM25 index rebuilt with %d chunks.", len(self.chunk_ids))

    def _load_index(self) -> None:
        """Load index from persistent JSON storage if available."""
        if not self.storage_path.exists():
            logger.info("BM25 index file %s does not exist; starting with empty index.", self.storage_path)
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.chunks = {c["chunk_id"]: c for c in data if "chunk_id" in c}
                self._rebuild_bm25()
                logger.info("Loaded %d BM25 chunks from %s.", len(self.chunks), self.storage_path)
        except Exception as e:
            logger.warning("Failed to load BM25 index from %s: %s", self.storage_path, e)

    def _save_index(self) -> None:
        """Persist index to disk atomically."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.storage_path.with_suffix(".tmp")
            chunk_list = list(self.chunks.values())
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(chunk_list, f, ensure_ascii=False, indent=2)
            if tmp_path.exists():
                tmp_path.replace(self.storage_path)
            logger.info("Saved %d BM25 chunks to %s.", len(chunk_list), self.storage_path)
        except Exception as e:
            logger.error("Failed to save BM25 index to %s: %s", self.storage_path, e)
            raise BM25Error(f"Failed to persist BM25 index: {str(e)}") from e

    def index_chunks(self, chunks: List[TextChunk], document_id: Optional[str] = None) -> int:
        """Index text chunks into BM25.

        If document_id is provided, any existing chunks for that document_id are
        purged first to ensure synchronized deduplication with Qdrant.
        """
        if not chunks:
            return 0

        with _BM25_LOCK:
            target_doc_id = document_id or chunks[0].document_id
            # 1. Purge prior chunks for this document_id if any
            self.chunks = {
                cid: c for cid, c in self.chunks.items() if c.get("document_id") != target_doc_id
            }

            # 2. Add new chunks
            for ch in chunks:
                self.chunks[ch.chunk_id] = {
                    "chunk_id": ch.chunk_id,
                    "document_id": ch.document_id,
                    "filename": ch.filename,
                    "page": ch.page,
                    "chunk_index": ch.chunk_index,
                    "content_type": ch.content_type,
                    "text": ch.text,
                    "token_count": ch.token_count,
                    "table_header": ch.table_header,
                    "metadata": ch.metadata,
                }

            # 3. Rebuild BM25 model & persist
            self._rebuild_bm25()
            self._save_index()
            return len(chunks)

    def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks associated with document_id and rebuild index."""
        if not document_id:
            return 0

        with _BM25_LOCK:
            prior_count = len(self.chunks)
            self.chunks = {
                cid: c for cid, c in self.chunks.items() if c.get("document_id") != document_id
            }
            deleted_count = prior_count - len(self.chunks)

            if deleted_count > 0:
                self._rebuild_bm25()
                self._save_index()
                logger.info("Deleted %d BM25 chunks for document_id='%s'.", deleted_count, document_id)
            return deleted_count

    def search(
        self,
        query: str,
        limit: int = 10,
        document_id: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Perform BM25 sparse keyword search.

        Returns ranked list of candidate chunks with raw BM25 scores.
        """
        if not query or not query.strip() or self.bm25 is None or not self.chunk_ids:
            return []

        tokens = tokenize_vietnamese_bm25(query)
        if not tokens:
            return []

        with _BM25_LOCK:
            scores = self.bm25.get_scores(tokens)

            scored_items = []
            for idx, score in enumerate(scores):
                if score <= 0.0:
                    continue
                if score_threshold is not None and score < score_threshold:
                    continue

                cid = self.chunk_ids[idx]
                chunk_data = self.chunks[cid]

                if document_id and chunk_data.get("document_id") != document_id:
                    continue

                scored_items.append((score, chunk_data))

            # Sort descending by BM25 score
            scored_items.sort(key=lambda x: x[0], reverse=True)
            top_items = scored_items[:limit]

            results = []
            for rank, (score, c) in enumerate(top_items, start=1):
                results.append({
                    "chunk_id": c["chunk_id"],
                    "document_id": c["document_id"],
                    "filename": c["filename"],
                    "page": c.get("page"),
                    "chunk_index": c.get("chunk_index", 0),
                    "content_type": c.get("content_type", "paragraph"),
                    "text": c["text"],
                    "score": float(score),
                    "rank": rank,
                    "metadata": c.get("metadata", {}),
                })
            return results

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve raw chunk metadata by chunk_id."""
        return self.chunks.get(chunk_id)

    @property
    def total_chunks(self) -> int:
        """Total number of indexed chunks."""
        return len(self.chunks)


def get_bm25_service() -> BM25Service:
    """Dependency provider for BM25Service."""
    return BM25Service.get_instance()
