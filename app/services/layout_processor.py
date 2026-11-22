"""Layout processing service for structured document layout analysis.

Analyzes bounding boxes, restores reading order, classifies layout elements
(heading, paragraph, table, image), and reconstructs table structures.
"""

from typing import Any, Dict, List, Optional, Tuple
import re

from app.schemas.document import DocumentSegment, SegmentType
from app.services.ocr_engine import OCRLine, OCRResult


class LayoutProcessor:
    """Processes OCR lines or raw text blocks into structured layout segments."""

    @classmethod
    def process_ocr_page(
        cls,
        ocr_result: OCRResult,
        page_number: int,
        start_segment_id: int = 1,
        image_count: int = 0,
    ) -> Tuple[List[DocumentSegment], int]:
        """Convert OCR results of a single page into structured DocumentSegments.

        Args:
            ocr_result: OCRResult containing detected lines and bounding boxes.
            page_number: 1-based page number.
            start_segment_id: Current sequential segment ID.
            image_count: Number of images on the source page.

        Returns:
            Tuple of (list of DocumentSegments, next segment ID).
        """
        if not ocr_result.lines:
            # Empty page or no text detected
            empty_segment = DocumentSegment(
                segment_id=start_segment_id,
                segment_type=SegmentType.TEXT,
                page=page_number,
                text="",
                table_data=None,
                source="ocr",
                confidence=0.0,
                bbox=None,
                layout_type="unknown",
                words=[],
                metadata={
                    "page": page_number,
                    "requires_ocr": True,
                    "has_text": False,
                    "line_count": 0,
                    "image_count": image_count,
                    "char_count": 0,
                },
            )
            return [empty_segment], start_segment_id + 1

        # 1. Sort lines into natural reading order
        sorted_lines = cls._sort_reading_order(ocr_result.lines)

        # 2. Group lines into candidate regions (tables vs paragraphs/headings)
        regions = cls._group_regions(sorted_lines)

        segments: List[DocumentSegment] = []
        current_id = start_segment_id

        for region in regions:
            layout_type = region["type"]
            region_lines: List[OCRLine] = region["lines"]

            if not region_lines:
                continue

            # Compute bounding box enclosing all lines in region
            x_min = min(line.bbox[0] for line in region_lines)
            y_min = min(line.bbox[1] for line in region_lines)
            x_max = max(line.bbox[2] for line in region_lines)
            y_max = max(line.bbox[3] for line in region_lines)
            region_bbox = [round(x_min, 2), round(y_min, 2), round(x_max, 2), round(y_max, 2)]

            avg_conf = sum(line.confidence for line in region_lines) / len(region_lines)
            words_data = [line.to_dict() for line in region_lines]

            if layout_type == "table":
                # Reconstruct table rows and columns
                table_data, table_text = cls._reconstruct_table(region_lines)
                segment = DocumentSegment(
                    segment_id=current_id,
                    segment_type=SegmentType.TABLE,
                    page=page_number,
                    text=table_text,
                    table_data=table_data,
                    source="ocr",
                    confidence=round(avg_conf, 4),
                    bbox=region_bbox,
                    layout_type="table",
                    words=words_data,
                    metadata={
                        "page": page_number,
                        "row_count": len(table_data),
                        "col_count": max((len(r) for r in table_data), default=0),
                        "requires_ocr": False,
                        "has_text": True,
                        "image_count": image_count,
                    },
                )
            else:
                region_text = "\n".join(line.text for line in region_lines)
                segment = DocumentSegment(
                    segment_id=current_id,
                    segment_type=SegmentType.TEXT,
                    page=page_number,
                    text=region_text,
                    table_data=None,
                    source="ocr",
                    confidence=round(avg_conf, 4),
                    bbox=region_bbox,
                    layout_type=layout_type,
                    words=words_data,
                    metadata={
                        "page": page_number,
                        "char_count": len(region_text),
                        "requires_ocr": False,
                        "has_text": True,
                        "image_count": image_count,
                    },
                )

            segments.append(segment)
            current_id += 1

        return segments, current_id

    @classmethod
    def _sort_reading_order(cls, lines: List[OCRLine]) -> List[OCRLine]:
        """Sort lines respecting natural reading order (detecting 2-column if present)."""
        if len(lines) <= 1:
            return lines

        # Check for 2-column layout by inspecting x-coordinates
        x_centers = [(line.bbox[0] + line.bbox[2]) / 2 for line in lines]
        min_x = min(line.bbox[0] for line in lines)
        max_x = max(line.bbox[2] for line in lines)
        mid_x = (min_x + max_x) / 2

        # A 2-column layout typically has clear left and right clusters
        left_lines = [line for line in lines if line.bbox[2] <= mid_x + 30]
        right_lines = [line for line in lines if line.bbox[0] >= mid_x - 30]

        is_two_column = (
            len(left_lines) >= len(lines) * 0.25 and
            len(right_lines) >= len(lines) * 0.25 and
            (len(left_lines) + len(right_lines)) >= len(lines) * 0.6
        )

        if is_two_column:
            # Sort left column top-to-bottom, then right column top-to-bottom
            left_sorted = sorted(left_lines, key=lambda l: (l.bbox[1], l.bbox[0]))
            right_sorted = sorted(right_lines, key=lambda l: (l.bbox[1], l.bbox[0]))
            # Full-width headers (lines crossing mid_x)
            header_lines = [l for l in lines if l not in left_lines and l not in right_lines and l.bbox[1] < min(left_lines[0].bbox[1] if left_lines else 999, right_lines[0].bbox[1] if right_lines else 999)]
            footer_lines = [l for l in lines if l not in left_lines and l not in right_lines and l not in header_lines]

            header_sorted = sorted(header_lines, key=lambda l: l.bbox[1])
            footer_sorted = sorted(footer_lines, key=lambda l: l.bbox[1])
            return header_sorted + left_sorted + right_sorted + footer_sorted

        # Standard single-column: sort primarily by y with tolerance for same line
        # Tolerance: half average line height
        avg_height = sum(l.bbox[3] - l.bbox[1] for l in lines) / len(lines)
        tolerance = max(avg_height * 0.6, 8.0)

        def line_sort_key(line: OCRLine) -> Tuple[int, float]:
            y_bucket = int(line.bbox[1] / tolerance)
            return (y_bucket, line.bbox[0])

        return sorted(lines, key=line_sort_key)

    @classmethod
    def _group_regions(cls, sorted_lines: List[OCRLine]) -> List[Dict[str, Any]]:
        """Classify lines into headings, paragraphs, and tables."""
        if not sorted_lines:
            return []

        regions: List[Dict[str, Any]] = []
        current_region_type: Optional[str] = None
        current_lines: List[OCRLine] = []

        # Detect table clusters: lines that share overlapping y-intervals (multiple cells on same row)
        table_line_indices = cls._detect_table_line_indices(sorted_lines)

        for idx, line in enumerate(sorted_lines):
            line_type = "table" if idx in table_line_indices else cls._classify_single_line(line)

            if current_region_type is None:
                current_region_type = line_type
                current_lines.append(line)
            elif current_region_type == line_type:
                # Same type: group together unless heading
                if line_type == "heading":
                    # Headings are generally standalone segments
                    regions.append({"type": current_region_type, "lines": current_lines})
                    current_lines = [line]
                else:
                    current_lines.append(line)
            else:
                # Transition to new region
                regions.append({"type": current_region_type, "lines": current_lines})
                current_region_type = line_type
                current_lines = [line]

        if current_lines:
            regions.append({"type": current_region_type or "paragraph", "lines": current_lines})

        return regions

    @classmethod
    def _detect_table_line_indices(cls, lines: List[OCRLine]) -> set[int]:
        """Identify line indices that belong to table structures based on horizontal coexistence."""
        table_indices = set()

        for i, line_a in enumerate(lines):
            y_a_mid = (line_a.bbox[1] + line_a.bbox[3]) / 2
            coexisting_count = 0
            for j, line_b in enumerate(lines):
                if i != j:
                    y_b_min = line_b.bbox[1]
                    y_b_max = line_b.bbox[3]
                    # Check if line_b overlaps vertically with line_a's midpoint
                    if y_b_min <= y_a_mid <= y_b_max:
                        # Ensure there is horizontal separation
                        if abs(line_a.bbox[0] - line_b.bbox[0]) > 40:
                            coexisting_count += 1

            if coexisting_count >= 1:
                table_indices.add(i)

        return table_indices

    @classmethod
    def _classify_single_line(cls, line: OCRLine) -> str:
        """Classify a non-table line as heading or paragraph."""
        text = line.text.strip()
        length = len(text)

        # Common Vietnamese heading patterns
        heading_patterns = [
            r"^(ĐIỀU|CHƯƠNG|MỤC|PHẦN)\s+[0-9IVXLCDM]+",
            r"^[0-9]+\.\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]",
            r"^(CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM|ĐỘC LẬP - TỰ DO - HẠNH PHÚC)",
            r"^(HỢP ĐỒNG|BIÊN BẢN|BÁO CÁO|QUY CHẾ|ĐỀ XUẤT|BẢNG BÁO GIÁ|BẢN TIN)",
        ]

        for pattern in heading_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "heading"

        # Uppercase heuristic for short texts
        if length <= 60 and text.isupper() and len(text.split()) <= 8:
            return "heading"

        return "paragraph"

    @classmethod
    def _reconstruct_table(cls, table_lines: List[OCRLine]) -> Tuple[List[List[str]], str]:
        """Reconstruct rows and columns from table OCR lines."""
        if not table_lines:
            return [], ""

        # Cluster lines into rows based on y-midpoint proximity
        rows: List[List[OCRLine]] = []
        sorted_by_y = sorted(table_lines, key=lambda l: (l.bbox[1], l.bbox[0]))

        for line in sorted_by_y:
            y_mid = (line.bbox[1] + line.bbox[3]) / 2
            placed = False
            for row in rows:
                row_y_mid = sum((l.bbox[1] + l.bbox[3]) / 2 for l in row) / len(row)
                row_height = sum(l.bbox[3] - l.bbox[1] for l in row) / len(row)
                if abs(y_mid - row_y_mid) <= max(row_height * 0.6, 12.0):
                    row.append(line)
                    placed = True
                    break
            if not placed:
                rows.append([line])

        # Sort cells in each row by x-coordinate (left to right)
        table_matrix: List[List[str]] = []
        for row in rows:
            sorted_row = sorted(row, key=lambda l: l.bbox[0])
            table_matrix.append([l.text.strip() for l in sorted_row if l.text.strip()])

        # Build markdown-compatible pipe text
        text_lines = [" | ".join(row) for row in table_matrix]
        table_text = "\n".join(text_lines)

        return table_matrix, table_text
