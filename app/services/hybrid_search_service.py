"""Hybrid Retrieval Service combining Dense Vector Search, BM25 and Cross-Encoder Reranking (Milestone 04)."""

import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import HybridSearchError
from app.schemas.chunk import HybridSearchRequest, HybridSearchResponse, HybridSearchResultItem
from app.services.bm25_service import BM25Service, get_bm25_service
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.reranker_service import BGERerankerService, get_reranker_service
from app.services.vector_store import QdrantVectorStore, get_vector_store

logger = logging.getLogger(__name__)


def compute_rrf_score(
    dense_rank: Optional[int],
    sparse_rank: Optional[int],
    k: int = 60,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
) -> float:
    """Calculate Reciprocal Rank Fusion (RRF) score for a single candidate.

    Formula:
        RRF = (w_dense / (k + rank_dense)) + (w_sparse / (k + rank_sparse))
    Ranks are 1-based integers (1, 2, ...). If a document was not retrieved
    by a method, its rank contribution is 0.0.
    """
    score = 0.0
    if dense_rank is not None and dense_rank > 0:
        score += dense_weight / (k + dense_rank)
    if sparse_rank is not None and sparse_rank > 0:
        score += sparse_weight / (k + sparse_rank)
    return float(score)


class HybridSearchService:
    """Orchestrates Hybrid Retrieval: Dense + Sparse BM25 + RRF + Cross-Encoder."""

    def __init__(
        self,
        embedder: Optional[EmbeddingService] = None,
        vector_store: Optional[QdrantVectorStore] = None,
        bm25_service: Optional[BM25Service] = None,
        reranker_service: Optional[BGERerankerService] = None,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._bm25_service = bm25_service
        self._reranker_service = reranker_service

    @property
    def embedder(self) -> EmbeddingService:
        if self._embedder is None:
            self._embedder = get_embedding_service()
        return self._embedder

    @property
    def vector_store(self) -> QdrantVectorStore:
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    @property
    def bm25_service(self) -> BM25Service:
        if self._bm25_service is None:
            self._bm25_service = get_bm25_service()
        return self._bm25_service

    @property
    def reranker_service(self) -> BGERerankerService:
        if self._reranker_service is None:
            self._reranker_service = get_reranker_service()
        return self._reranker_service

    def search_hybrid(self, request: HybridSearchRequest) -> HybridSearchResponse:
        """Execute full hybrid retrieval pipeline.

        1. Dense Retrieval (BGE-M3 + Qdrant)
        2. Sparse Retrieval (BM25)
        3. Reciprocal Rank Fusion (RRF) & Deduplication
        4. Cross-Encoder Reranking (BAAI/bge-reranker-v2-m3)
        """
        start_time = time.perf_counter()
        query = request.query.strip()
        if not query:
            raise HybridSearchError("Query cannot be empty.")

        k_rrf = request.rrf_k or settings.RRF_K
        dense_w = request.dense_weight if request.dense_weight is not None else settings.RRF_WEIGHT_DENSE
        sparse_w = request.sparse_weight if request.sparse_weight is not None else settings.RRF_WEIGHT_SPARSE
        candidate_limit = request.candidate_limit or settings.HYBRID_CANDIDATE_LIMIT
        top_k = request.top_k

        # -------------------------------------------------------------
        # 1. Dense Retrieval (Qdrant)
        # -------------------------------------------------------------
        dense_candidates: List[Dict[str, Any]] = []
        try:
            query_vector = self.embedder.embed_query(query)
            dense_search_results = self.vector_store.search(
                query_vector=query_vector,
                limit=candidate_limit,
                document_id=request.document_id,
            )
            for rank, item in enumerate(dense_search_results, start=1):
                dense_candidates.append({
                    "chunk_id": item.chunk_id,
                    "document_id": item.document_id,
                    "filename": item.filename,
                    "page": item.page,
                    "content_type": item.content_type,
                    "text": item.text,
                    "dense_rank": rank,
                    "dense_score": float(item.score),
                    "metadata": item.metadata,
                })
        except Exception as e:
            logger.warning("Dense retrieval encountered an issue (fallback to sparse): %s", e)
            dense_candidates = []

        # -------------------------------------------------------------
        # 2. Sparse Retrieval (BM25)
        # -------------------------------------------------------------
        sparse_candidates: List[Dict[str, Any]] = []
        try:
            bm25_results = self.bm25_service.search(
                query=query,
                limit=candidate_limit,
                document_id=request.document_id,
            )
            for rank, item in enumerate(bm25_results, start=1):
                sparse_candidates.append({
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "filename": item["filename"],
                    "page": item.get("page"),
                    "content_type": item.get("content_type", "paragraph"),
                    "text": item["text"],
                    "sparse_rank": rank,
                    "sparse_score": float(item["score"]),
                    "metadata": item.get("metadata", {}),
                })
        except Exception as e:
            logger.warning("BM25 retrieval encountered an issue: %s", e)
            sparse_candidates = []

        # -------------------------------------------------------------
        # 3. Reciprocal Rank Fusion (RRF) & Deduplication
        # -------------------------------------------------------------
        fused_pool: Dict[str, Dict[str, Any]] = {}

        # Add all dense candidates
        for c in dense_candidates:
            cid = c["chunk_id"]
            fused_pool[cid] = {
                "chunk_id": cid,
                "document_id": c["document_id"],
                "filename": c["filename"],
                "page": c.get("page"),
                "content_type": c.get("content_type", "paragraph"),
                "text": c["text"],
                "dense_rank": c["dense_rank"],
                "dense_score": c["dense_score"],
                "sparse_rank": None,
                "sparse_score": None,
                "metadata": c.get("metadata", {}),
            }

        # Merge in all sparse candidates
        for c in sparse_candidates:
            cid = c["chunk_id"]
            if cid in fused_pool:
                fused_pool[cid]["sparse_rank"] = c["sparse_rank"]
                fused_pool[cid]["sparse_score"] = c["sparse_score"]
            else:
                fused_pool[cid] = {
                    "chunk_id": cid,
                    "document_id": c["document_id"],
                    "filename": c["filename"],
                    "page": c.get("page"),
                    "content_type": c.get("content_type", "paragraph"),
                    "text": c["text"],
                    "dense_rank": None,
                    "dense_score": None,
                    "sparse_rank": c["sparse_rank"],
                    "sparse_score": c["sparse_score"],
                    "metadata": c.get("metadata", {}),
                }

        # Compute RRF score for all unique candidates
        for cid, item in fused_pool.items():
            rrf_val = compute_rrf_score(
                dense_rank=item["dense_rank"],
                sparse_rank=item["sparse_rank"],
                k=k_rrf,
                dense_weight=dense_w,
                sparse_weight=sparse_w,
            )
            item["rrf_score"] = rrf_val
            item["score"] = rrf_val  # Default score before reranking

        # Sort candidate pool descending by RRF score
        ranked_pool = sorted(fused_pool.values(), key=lambda x: x["rrf_score"], reverse=True)
        # Limit candidate pool to candidate_limit before reranking
        candidate_pool = ranked_pool[:candidate_limit]

        # -------------------------------------------------------------
        # 4. Cross-Encoder Reranking (optional)
        # -------------------------------------------------------------
        rerank_applied = False
        if request.enable_reranking and candidate_pool:
            try:
                candidate_pool = self.reranker_service.rerank(
                    query=query,
                    candidates=candidate_pool,
                    top_k=top_k,
                    score_threshold=request.score_threshold,
                )
                rerank_applied = True
            except Exception as e:
                logger.warning("Cross-Encoder reranking failed, falling back to RRF: %s", e)
                # Keep RRF order
                candidate_pool = candidate_pool[:top_k]
        else:
            if request.score_threshold is not None:
                candidate_pool = [
                    c for c in candidate_pool if c["score"] >= request.score_threshold
                ]
            candidate_pool = candidate_pool[:top_k]

        # Convert to Pydantic items
        result_items: List[HybridSearchResultItem] = []
        for c in candidate_pool:
            result_items.append(
                HybridSearchResultItem(
                    chunk_id=c["chunk_id"],
                    document_id=c["document_id"],
                    filename=c["filename"],
                    page=c.get("page"),
                    content_type=c.get("content_type", "paragraph"),
                    text=c["text"],
                    score=float(c["score"]),
                    rrf_score=float(c.get("rrf_score", 0.0)),
                    dense_rank=c.get("dense_rank"),
                    dense_score=c.get("dense_score"),
                    sparse_rank=c.get("sparse_rank"),
                    sparse_score=c.get("sparse_score"),
                    rerank_score=c.get("rerank_score"),
                    metadata=c.get("metadata", {}),
                )
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        return HybridSearchResponse(
            query=query,
            total_results=len(result_items),
            results=result_items,
            dense_candidates_count=len(dense_candidates),
            sparse_candidates_count=len(sparse_candidates),
            fused_candidates_count=len(fused_pool),
            rerank_applied=rerank_applied,
            search_time_ms=round(duration_ms, 2),
        )


def get_hybrid_search_service() -> HybridSearchService:
    """Dependency provider for HybridSearchService."""
    return HybridSearchService()
