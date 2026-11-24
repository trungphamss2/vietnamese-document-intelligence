"""API endpoints for document indexing, vector retrieval, and deletion (Milestone 03)."""

import time
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.config import settings
from app.core.exceptions import (
    CorruptedDocumentError,
    DocumentParserException,
    EmptyFileError,
    EncryptedDocumentError,
    FileSizeExceededError,
    OCREngineError,
    UnsupportedFileTypeError,
)
from app.schemas.chunk import (
    ChunkingConfig,
    DeleteDocumentResponse,
    IndexResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.document_parser import DocumentParser
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.text_chunker import IntelligentTextChunker
from app.services.vector_store import QdrantVectorStore, get_vector_store

router = APIRouter(tags=["Indexing & Search"])


def get_document_parser() -> DocumentParser:
    """Dependency provider for DocumentParser."""
    return DocumentParser()



@router.post(
    "/documents/index",
    response_model=IndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Parse, chunk, embed, and index a document into Qdrant",
    description=(
        "Uploads a PDF, DOCX, or XLSX document, extracts structured segments, "
        "chunks content intelligently, computes dense vectors using BAAI/bge-m3, "
        "and stores vectors and payloads into Qdrant collection."
    ),
)
async def index_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, XLSX)"),
    document_id: Optional[str] = Form(
        default=None,
        description="Optional custom document_id. If omitted, a deterministic ID is generated.",
    ),
    enable_ocr: bool = Form(
        default=True,
        description="Enable OCR for scanned pages or images without text",
    ),
    chunk_size: Optional[int] = Form(
        default=None,
        description="Target chunk size in characters (default from config)",
    ),
    chunk_overlap: Optional[int] = Form(
        default=None,
        description="Overlap size between chunks (default from config)",
    ),
    parser: DocumentParser = Depends(get_document_parser),
    embedder: EmbeddingService = Depends(get_embedding_service),
    vector_store: QdrantVectorStore = Depends(get_vector_store),
) -> IndexResponse:
    """Parse, chunk, embed and index an uploaded document."""
    start_time = time.perf_counter()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    # 1. Read document content
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{file.filename}' is empty (0 bytes).",
        )

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        max_mb = settings.MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {max_mb:.0f} MB.",
        )

    # 2. Parse document via DocumentParser (Milestone 01-02 pipeline)
    try:
        parsed_doc = parser.parse(
            filename=file.filename,
            content=content,
            enable_ocr=enable_ocr,
        )

    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=exc.message)
    except EmptyFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except FileSizeExceededError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=exc.message)
    except EncryptedDocumentError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    except CorruptedDocumentError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    except OCREngineError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message)
    except DocumentParserException as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)

    # 3. Intelligent chunking
    config = ChunkingConfig(
        chunk_size=chunk_size or settings.CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
        min_chunk_size=settings.MIN_CHUNK_SIZE,
    )
    chunker = IntelligentTextChunker(config=config)
    doc_id = document_id or IntelligentTextChunker.generate_document_id(
        filename=file.filename,
        content_hash_seed=str(len(content)),
    )
    chunks = chunker.chunk_document(document=parsed_doc, document_id=doc_id)

    if not chunks:
        # Edge case: empty document text
        duration_ms = (time.perf_counter() - start_time) * 1000
        return IndexResponse(
            document_id=doc_id,
            filename=file.filename,
            total_segments=parsed_doc.total_segments,
            total_chunks=0,
            vector_dimension=settings.EMBEDDING_DIM,
            processing_time_ms=round(duration_ms, 2),
            collection_name=vector_store.collection_name,
            status="indexed_empty",
        )

    # 4. Dense embedding generation via BAAI/bge-m3
    texts = [c.text for c in chunks]
    vectors = embedder.embed_texts(texts=texts)

    # 5. Qdrant upsert (with automatic deduplication/purging of prior document_id points)
    vector_store.upsert_chunks(chunks=chunks, vectors=vectors, document_id=doc_id)

    duration_ms = (time.perf_counter() - start_time) * 1000
    return IndexResponse(
        document_id=doc_id,
        filename=file.filename,
        total_segments=parsed_doc.total_segments,
        total_chunks=len(chunks),
        vector_dimension=len(vectors[0]) if vectors else settings.EMBEDDING_DIM,
        processing_time_ms=round(duration_ms, 2),
        collection_name=vector_store.collection_name,
        status="indexed",
    )


@router.post(
    "/search/vector",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Perform semantic vector search against indexed document chunks",
    description="Embeds natural language query using BGE-M3 and searches Qdrant for top matching chunks.",
)
async def search_vector(
    request: SearchRequest,
    embedder: EmbeddingService = Depends(get_embedding_service),
    vector_store: QdrantVectorStore = Depends(get_vector_store),
) -> SearchResponse:
    """Execute semantic cosine search on Qdrant."""
    start_time = time.perf_counter()

    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty or blank.",
        )

    query_vec = embedder.embed_query(request.query)
    results = vector_store.search(
        query_vector=query_vec,
        limit=request.limit,
        document_id=request.document_id,
        score_threshold=request.score_threshold,
    )

    duration_ms = (time.perf_counter() - start_time) * 1000
    return SearchResponse(
        query=request.query,
        total_results=len(results),
        results=results,
        search_time_ms=round(duration_ms, 2),
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete all indexed vectors and metadata for a document",
    description="Removes all points associated with the specified document_id from Qdrant.",
)
async def delete_document(
    document_id: str,
    vector_store: QdrantVectorStore = Depends(get_vector_store),
) -> DeleteDocumentResponse:
    """Delete document points from Qdrant."""
    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id cannot be empty.",
        )

    count = vector_store.delete_by_document_id(document_id.strip())
    return DeleteDocumentResponse(
        document_id=document_id.strip(),
        status="deleted",
        deleted_points=count,
    )
