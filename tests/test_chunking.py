"""Unit tests for IntelligentTextChunker (Milestone 03)."""

import pytest
from app.schemas.chunk import ChunkingConfig, TextChunk
from app.schemas.document import (
    DocumentMetadata,
    DocumentParseResponse,
    DocumentSegment,
    FileType,
    SegmentType,
)
from app.services.text_chunker import IntelligentTextChunker


@pytest.fixture
def chunker() -> IntelligentTextChunker:
    """Fixture providing a chunker with custom small sizes for testing."""
    config = ChunkingConfig(
        chunk_size=120,
        chunk_overlap=30,
        min_chunk_size=20,
    )
    return IntelligentTextChunker(config=config)


def test_chunk_heading_atomic(chunker: IntelligentTextChunker):
    """Test that headings remain atomic standalone chunks."""
    segment = DocumentSegment(
        segment_id=1,
        segment_type=SegmentType.TEXT,
        page=1,
        text="ĐIỀU 1. ĐỊNH NGHĨA VÀ GIẢI THÍCH TỪ NGỮ",
        layout_type="heading",
        metadata={"font_size": 14},
    )

    chunks = chunker.chunk_segment(
        segment=segment,
        document_id="doc_test_1",
        filename="contract.pdf",
    )

    assert len(chunks) == 1
    assert chunks[0].content_type == "heading"
    assert chunks[0].text == "ĐIỀU 1. ĐỊNH NGHĨA VÀ GIẢI THÍCH TỪ NGỮ"
    assert chunks[0].page == 1
    assert chunks[0].document_id == "doc_test_1"
    assert chunks[0].chunk_index == 0


def test_chunk_paragraph_with_overlap(chunker: IntelligentTextChunker):
    """Test paragraph splitting with sentence boundary and overlap."""
    text = (
        "Hợp đồng kinh tế số 102 được ký kết tại Hà Nội. "
        "Bên A đồng ý cung cấp giải pháp trí tuệ nhân tạo OCR tiếng Việt cho Bên B. "
        "Thời gian triển khai dự kiến là sáu mươi ngày làm việc kể từ ngày thanh toán đợt một. "
        "Mọi tranh chấp phát sinh sẽ được giải quyết thông qua thương lượng và hòa giải."
    )
    segment = DocumentSegment(
        segment_id=1,
        segment_type=SegmentType.TEXT,
        page=2,
        text=text,
        layout_type="paragraph",
    )

    chunks = chunker.chunk_segment(
        segment=segment,
        document_id="doc_test_2",
        filename="contract.docx",
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.page == 2
        assert chunk.content_type == "paragraph"
        assert len(chunk.text) >= 20
        assert chunk.document_id == "doc_test_2"

    # Verify sequential indexing
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_table_preserves_headers(chunker: IntelligentTextChunker):
    """Test table chunking preserves the header row in each chunk."""
    table_data = [
        ["STT", "Tên Hàng Hóa", "Đơn Giá (VNĐ)", "Ghi Chú"],
        ["1", "Máy chủ Dell PowerEdge R750 32GB RAM", "125.000.000", "Bảo hành 36 tháng"],
        ["2", "Card đồ họa NVIDIA RTX 3050 6GB GDDR6", "7.500.000", "Hàng mới 100%"],
        ["3", "Ổ cứng SSD NVMe Samsung 990 Pro 2TB", "4.800.000", "Chính hãng"],
        ["4", "Bộ nhớ RAM DDR5 Corsair 64GB 5600MHz", "5.200.000", "Kit 2 thanh 32GB"],
    ]

    segment = DocumentSegment(
        segment_id=1,
        segment_type=SegmentType.TABLE,
        page=3,
        text="Bảng danh mục thiết bị",
        table_data=table_data,
        layout_type="table",
    )

    chunks = chunker.chunk_segment(
        segment=segment,
        document_id="doc_table_1",
        filename="quote.xlsx",
    )

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.content_type == "table"
        assert chunk.table_header == ["STT", "Tên Hàng Hóa", "Đơn Giá (VNĐ)", "Ghi Chú"]
        # Header must be present in chunk text
        assert "Tên Hàng Hóa" in chunk.text
        assert "Đơn Giá (VNĐ)" in chunk.text


def test_chunk_document_multi_page(chunker: IntelligentTextChunker):
    """Test chunking a full DocumentParseResponse across multiple pages."""
    doc_response = DocumentParseResponse(
        filename="multi_page_doc.pdf",
        file_type=FileType.PDF,
        requires_ocr=False,
        total_segments=3,
        metadata=DocumentMetadata(
            file_size_bytes=5000,
            page_count=2,
            native_page_count=2,
        ),
        segments=[
            DocumentSegment(
                segment_id=1,
                segment_type=SegmentType.TEXT,
                page=1,
                text="Tiêu đề trang nhất: Báo cáo tài chính quý 3 năm 2026",
                layout_type="heading",
            ),
            DocumentSegment(
                segment_id=2,
                segment_type=SegmentType.TEXT,
                page=1,
                text="Tình hình kinh doanh khả quan nhờ ứng dụng công nghệ nhận diện tài liệu tự động.",
                layout_type="paragraph",
            ),
            DocumentSegment(
                segment_id=3,
                segment_type=SegmentType.TEXT,
                page=2,
                text="Trang 2: Chi tiết các khoản chi phí và lợi nhuận ròng sau thuế đạt kỳ vọng.",
                layout_type="paragraph",
            ),
        ],
    )

    chunks = chunker.chunk_document(doc_response, document_id="doc_full_1")

    assert len(chunks) == 3
    assert chunks[0].page == 1
    assert chunks[0].content_type == "heading"
    assert chunks[1].page == 1
    assert chunks[1].content_type == "paragraph"
    assert chunks[2].page == 2
    assert chunks[2].content_type == "paragraph"
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert all(c.document_id == "doc_full_1" for c in chunks)


def test_chunk_document_isolation():
    """Test that chunking different documents maintains strict isolation."""
    chunker = IntelligentTextChunker()
    doc_a = DocumentParseResponse(
        filename="doc_a.pdf",
        file_type=FileType.PDF,
        total_segments=1,
        metadata=DocumentMetadata(file_size_bytes=100),
        segments=[
            DocumentSegment(segment_id=1, segment_type=SegmentType.TEXT, page=1, text="Nội dung tài liệu A")
        ],
    )
    doc_b = DocumentParseResponse(
        filename="doc_b.pdf",
        file_type=FileType.PDF,
        total_segments=1,
        metadata=DocumentMetadata(file_size_bytes=200),
        segments=[
            DocumentSegment(segment_id=1, segment_type=SegmentType.TEXT, page=1, text="Nội dung tài liệu B")
        ],
    )

    chunks_a = chunker.chunk_document(doc_a, document_id="id_doc_a")
    chunks_b = chunker.chunk_document(doc_b, document_id="id_doc_b")

    assert chunks_a[0].document_id == "id_doc_a"
    assert chunks_b[0].document_id == "id_doc_b"
    assert chunks_a[0].filename == "doc_a.pdf"
    assert chunks_b[0].filename == "doc_b.pdf"
    assert chunks_a[0].text != chunks_b[0].text
