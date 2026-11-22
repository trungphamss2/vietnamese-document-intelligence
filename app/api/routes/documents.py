"""API route handlers for document processing."""

from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

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
from app.schemas.document import DocumentParseResponse
from app.services.document_parser import DocumentParser

router = APIRouter(tags=["Documents"])


@router.post(
    "/documents/parse",
    response_model=DocumentParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse document content",
    description=(
        "Upload and parse a document (PDF, DOCX, or XLSX), returning structured "
        "text, tables, and metadata."
    ),
    responses={
        200: {
            "description": "Document parsed successfully",
            "model": DocumentParseResponse,
        },
        400: {"description": "Corrupted, unreadable, or empty document"},
        413: {"description": "File size exceeds maximum allowed limit (20 MB)"},
        415: {"description": "Unsupported document format"},
        500: {"description": "Internal OCR processing error"},
    },
)
async def parse_document_endpoint(
    file: UploadFile = File(
        ...,
        description="Document file to parse (.pdf, .docx, or .xlsx)",
    ),
    enable_ocr: bool = Query(
        default=True,
        description="Enable OCR for scanned/image pages in PDF documents",
    ),
) -> DocumentParseResponse:
    """Handle document upload, perform validation, and return parsed structure."""
    filename = file.filename or ""

    # 1. Validate file extension
    ext = Path(filename).suffix.lower()
    if not ext or ext not in settings.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file format '{ext}'. "
                f"Supported formats are: {', '.join(sorted(settings.SUPPORTED_EXTENSIONS))}"
            ),
        )

    # 2. Read in chunks to enforce 20 MB size limit without excessive memory usage
    chunk_size = 1024 * 1024  # 1 MB chunk
    total_size = 0
    chunks = []

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > settings.MAX_FILE_SIZE_BYTES:
            max_mb = settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File size exceeds maximum allowed limit of {max_mb} MB.",
            )
        chunks.append(chunk)

    # 3. Validate non-empty file
    if total_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    content = b"".join(chunks)

    # 4. Process document via DocumentParser service
    try:
        result = DocumentParser.parse(
            filename=filename,
            content=content,
            enable_ocr=enable_ocr,
        )
        return result
    except (CorruptedDocumentError, EmptyFileError, EncryptedDocumentError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=exc.message,
        )
    except OCREngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        )
    except Exception:
        # Prevent leaking stack traces or internal environment details
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse document. The file may be corrupt or invalid.",
        )
