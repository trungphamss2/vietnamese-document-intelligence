"""Vector database service managing Qdrant storage, indexing and retrieval."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import VectorStoreError
from app.schemas.chunk import SearchResultItem, TextChunk

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Service managing Qdrant collection, upserting, deduplication, and vector search."""

    _instance: Optional["QdrantVectorStore"] = None

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = None
        self._initialize_client()

    @classmethod
    def get_instance(cls) -> "QdrantVectorStore":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_client(self) -> None:
        """Connect to Qdrant service and guarantee collection exists."""
        try:
            from qdrant_client import QdrantClient

            self.client = QdrantClient(host=self.host, port=self.port, timeout=10.0)
            self.ensure_collection()
            logger.info("Successfully connected to Qdrant at %s:%d, collection='%s'", self.host, self.port, self.collection_name)
        except Exception as e:
            logger.error("Failed to connect to Qdrant at %s:%d: %s", self.host, self.port, e)
            raise VectorStoreError(f"Could not connect to Qdrant ({self.host}:{self.port}): {str(e)}") from e

    def ensure_collection(self, collection_name: Optional[str] = None) -> None:
        """Ensure collection exists with appropriate 1024-dimension Cosine distance config."""
        col = collection_name or self.collection_name
        try:
            from qdrant_client.http import models

            collections = self.client.get_collections().collections
            exists = any(c.name == col for c in collections)

            if not exists:
                logger.info("Creating Qdrant collection '%s' with dimension %d (Cosine)...", col, settings.EMBEDDING_DIM)
                self.client.create_collection(
                    collection_name=col,
                    vectors_config=models.VectorParams(
                        size=settings.EMBEDDING_DIM,
                        distance=models.Distance.COSINE,
                    ),
                )
                # Create payload index for document_id to accelerate filtering and deduplication
                self.client.create_payload_index(
                    collection_name=col,
                    field_name="document_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                logger.info("Collection '%s' created successfully.", col)
        except Exception as e:
            raise VectorStoreError(f"Failed to ensure collection '{col}': {str(e)}") from e

    def upsert_chunks(
        self,
        chunks: List[TextChunk],
        vectors: List[List[float]],
        document_id: str,
    ) -> int:
        """Upsert text chunks with vectors into Qdrant.
        
        To prevent stale/duplicate chunks when re-indexing the same document_id,
        existing points for this document_id are purged prior to batch upsert.
        
        Args:
            chunks: List of TextChunk objects.
            vectors: Corresponding list of 1024-dim embedding vectors.
            document_id: Parent document identifier.
            
        Returns:
            Number of points successfully upserted.
        """
        if not chunks or not vectors:
            return 0

        if len(chunks) != len(vectors):
            raise VectorStoreError(f"Mismatch: received {len(chunks)} chunks and {len(vectors)} vectors.")

        try:
            from qdrant_client.http import models

            # 1. Deduplication / Re-indexing handling: delete existing chunks for this doc
            self.delete_by_document_id(document_id)

            # 2. Prepare PointStruct list
            points = []
            for chunk, vec in zip(chunks, vectors):
                # Ensure valid UUID for Qdrant point_id
                try:
                    point_id = str(uuid.UUID(chunk.chunk_id))
                except (ValueError, TypeError):
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{chunk.chunk_index}"))

                payload = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "page": chunk.page,
                    "chunk_index": chunk.chunk_index,
                    "content_type": chunk.content_type,
                    "text": chunk.text,
                    "table_header": chunk.table_header,
                    "metadata": chunk.metadata,
                }

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vec,
                        payload=payload,
                    )
                )

            # 3. Batch upsert
            batch_size = 64
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )

            logger.info("Upserted %d chunks for document_id='%s' into '%s'", len(points), document_id, self.collection_name)
            return len(points)

        except Exception as e:
            raise VectorStoreError(f"Failed to upsert chunks for document '{document_id}': {str(e)}") from e

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        document_id: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResultItem]:
        """Perform semantic cosine similarity search against Qdrant.
        
        Args:
            query_vector: 1024-dim embedding vector of the query.
            limit: Maximum number of results.
            document_id: Optional filter for a specific document.
            score_threshold: Optional minimum cosine similarity.
            
        Returns:
            List of SearchResultItem sorted by similarity score descending.
        """
        try:
            from qdrant_client.http import models

            query_filter = None
            if document_id:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )

            # Use query_points (official in qdrant-client >= 1.10.0/1.20.0) with fallback
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    query_filter=query_filter,
                    score_threshold=score_threshold,
                    with_payload=True,
                )
                search_hits = response.points
            else:
                search_hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=query_filter,
                    score_threshold=score_threshold,
                    with_payload=True,
                )

            results: List[SearchResultItem] = []
            for hit in search_hits:
                payload = hit.payload or {}
                results.append(
                    SearchResultItem(
                        chunk_id=str(payload.get("chunk_id", hit.id)),
                        document_id=str(payload.get("document_id", "")),
                        filename=str(payload.get("filename", "")),
                        page=payload.get("page"),
                        chunk_index=int(payload.get("chunk_index", 0)),
                        content_type=str(payload.get("content_type", "paragraph")),
                        text=str(payload.get("text", "")),
                        score=float(hit.score),
                        metadata=payload.get("metadata", {}),
                    )
                )

            return results


        except Exception as e:
            raise VectorStoreError(f"Vector search failed: {str(e)}") from e

    def delete_by_document_id(self, document_id: str) -> int:
        """Delete all vectors belonging to document_id from collection."""
        try:
            from qdrant_client.http import models

            # Count points matching filter first
            filter_selector = models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            )

            response = self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_selector,
            )
            logger.info("Deleted points for document_id='%s' (status=%s)", document_id, getattr(response, "status", "ok"))
            return 1
        except Exception as e:
            logger.warning("Could not delete existing points for document_id='%s': %s", document_id, e)
            return 0


def get_vector_store() -> QdrantVectorStore:
    """Dependency injection helper for QdrantVectorStore."""
    return QdrantVectorStore.get_instance()
