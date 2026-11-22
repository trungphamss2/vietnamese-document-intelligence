"""Vietnamese OCR Engine service leveraging PaddleOCR with GPU/CPU support."""

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, List, Optional, Union
import unicodedata

from app.core.config import settings
from app.core.exceptions import OCREngineError

logger = logging.getLogger(__name__)


def _setup_paddle_env() -> None:
    """Configure environment variables and blocklists for PaddleX / PaddleOCR."""
    os.environ["PADDLE_PDX_CACHE_HOME"] = settings.PADDLE_CACHE_DIR
    os.environ["PADDLE_HOME"] = settings.PADDLE_HOME_DIR
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

    # Bypass oneDNN PIR instruction bug on CPU for PP-OCRv6 models
    try:
        import paddlex.inference.models.runners.paddle_static.config.blocklists as bl
        if "PP-OCRv6_medium_det" not in bl.MKLDNN_BLOCKLIST:
            bl.MKLDNN_BLOCKLIST.append("PP-OCRv6_medium_det")
        if "PP-OCRv6_medium_rec" not in bl.MKLDNN_BLOCKLIST:
            bl.MKLDNN_BLOCKLIST.append("PP-OCRv6_medium_rec")
    except Exception as exc:
        logger.debug(f"Could not modify MKLDNN blocklist: {exc}")


@dataclass
class OCRLine:
    """Represents a single recognized text line with coordinates and confidence."""

    text: str
    confidence: float
    bbox: List[float]  # [x_min, y_min, x_max, y_max]
    polygon: Optional[List[List[float]]] = None  # 4 corner coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "bbox": [round(c, 2) for c in self.bbox],
            "polygon": [[round(pt[0], 2), round(pt[1], 2)] for pt in self.polygon] if self.polygon else None,
        }


@dataclass
class OCRResult:
    """Encapsulates the complete OCR extraction for an image or page."""

    lines: List[OCRLine] = field(default_factory=list)
    full_text: str = ""
    avg_confidence: float = 0.0
    orientation_angle: Optional[float] = None
    processing_time_ms: float = 0.0
    device: str = "cpu"


class VietnameseOCREngine:
    """Production-grade Vietnamese OCR Engine wrapper around PaddleOCR."""

    _instance: Optional["VietnameseOCREngine"] = None

    def __init__(self) -> None:
        _setup_paddle_env()
        self.device = self._detect_device()
        self._ocr = self._init_paddleocr()

    def _detect_device(self) -> str:
        """Detect GPU availability (RTX 3050 6GB) with graceful CPU fallback."""
        try:
            import paddle
            if settings.OCR_USE_GPU and paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
                logger.info(f"Paddle is compiled with CUDA. Using GPU: {paddle.device.cuda.get_device_name(0)}")
                return "gpu"
        except Exception as exc:
            logger.warning(f"GPU detection encountered issue ({exc}); falling back to CPU.")
        logger.info("Using CPU for Vietnamese OCR inference.")
        return "cpu"

    @property
    def use_gpu(self) -> bool:
        """Indicate whether OCR engine is running with GPU acceleration."""
        return self.device == "gpu"

    def _init_paddleocr(self) -> Any:
        """Initialize PaddleOCR instance configured for Vietnamese language."""
        from paddleocr import PaddleOCR

        logger.info(f"Initializing PaddleOCR (lang={settings.OCR_LANG}, device={self.device})...")
        try:
            # We configure orientation classification to handle rotated scans
            ocr = PaddleOCR(
                lang=settings.OCR_LANG,
                use_doc_orientation_classify=settings.OCR_USE_ORIENTATION_CLASSIFY,
                use_doc_unwarping=settings.OCR_USE_UNWARPING,
                use_textline_orientation=True,
            )
            return ocr
        except Exception as exc:
            raise OCREngineError(f"Failed to initialize PaddleOCR engine: {str(exc)}") from exc

    def recognize(self, image_input: Union[str, Path, bytes]) -> OCRResult:
        """Perform text detection and recognition on an image.

        Args:
            image_input: Image filepath (str/Path) or raw image bytes (PNG/JPEG).

        Returns:
            OCRResult containing extracted lines, bounding boxes, and confidence.
        """
        temp_file: Optional[Path] = None
        t_start = time.perf_counter()

        if isinstance(image_input, bytes):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(image_input)
                temp_file = Path(f.name)
            target_path = str(temp_file)
        else:
            target_path = str(image_input)

        try:
            predictions = self._ocr.predict(target_path)
            lines: List[OCRLine] = []
            orientation_angle: Optional[float] = None

            for page_pred in predictions:
                rec_texts = page_pred.get("rec_texts", [])
                rec_scores = page_pred.get("rec_scores", [])
                rec_polys = page_pred.get("dt_polys", [])
                if len(rec_polys) == 0:
                    rec_polys = page_pred.get("rec_polys", [])

                angles = page_pred.get("textline_orientation_angles", [])
                if angles:
                    orientation_angle = float(angles[0]) if isinstance(angles[0], (int, float)) else None

                for idx, text in enumerate(rec_texts):
                    score = float(rec_scores[idx]) if idx < len(rec_scores) else 0.0
                    poly = rec_polys[idx] if idx < len(rec_polys) else []

                    # Convert polygon to list of points
                    if hasattr(poly, "tolist"):
                        poly_list = poly.tolist()
                    else:
                        poly_list = [list(pt) for pt in poly] if poly else []

                    # Compute bounding box [x_min, y_min, x_max, y_max]
                    if poly_list:
                        xs = [pt[0] for pt in poly_list]
                        ys = [pt[1] for pt in poly_list]
                        bbox = [min(xs), min(ys), max(xs), max(ys)]
                    else:
                        bbox = [0.0, 0.0, 0.0, 0.0]

                    # Normalize Unicode text (NFC)
                    norm_text = unicodedata.normalize("NFC", text).strip()
                    if norm_text:
                        lines.append(
                            OCRLine(
                                text=norm_text,
                                confidence=score,
                                bbox=bbox,
                                polygon=poly_list,
                            )
                        )

            avg_conf = (
                sum(line.confidence for line in lines) / len(lines)
                if lines
                else 0.0
            )
            full_text = "\n".join(line.text for line in lines)
            t_end = time.perf_counter()

            return OCRResult(
                lines=lines,
                full_text=full_text,
                avg_confidence=round(avg_conf, 4),
                orientation_angle=orientation_angle,
                processing_time_ms=round((t_end - t_start) * 1000, 2),
                device=self.device,
            )

        except Exception as exc:
            raise OCREngineError(f"Error during OCR recognition: {str(exc)}") from exc
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    @classmethod
    def get_instance(cls) -> "VietnameseOCREngine":
        """Get or initialize singleton OCR engine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_ocr_engine() -> VietnameseOCREngine:
    """Convenience function returning the singleton OCR engine."""
    return VietnameseOCREngine.get_instance()
