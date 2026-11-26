"""Cross-Encoder Reranker Service using BAAI/bge-reranker-v2-m3 (Milestone 04)."""

import gc
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.core.exceptions import RerankerError
from app.services.embedding_service import _GPU_INFERENCE_LOCK

logger = logging.getLogger(__name__)

_RERANKER_INSTANCE_LOCK = threading.Lock()
_RERANKER_INFERENCE_LOCK = _GPU_INFERENCE_LOCK


class BGERerankerService:
    """Singleton service for Cross-Encoder reranking using BAAI/bge-reranker-v2-m3.

    Optimized for NVIDIA GeForce RTX 3050 6GB Laptop GPU with FP16 half-precision,
    batch inference, CUDA OOM recovery, and CPU fallback.
    """

    _instance: Optional["BGERerankerService"] = None

    def __init__(self) -> None:
        self.model_name = settings.RERANKER_MODEL
        self.device = self._resolve_device(settings.RERANKER_DEVICE)
        self.batch_size = settings.RERANKER_BATCH_SIZE
        self.max_length = settings.RERANKER_MAX_LENGTH
        self.use_fp16 = settings.RERANKER_USE_FP16
        self.model = None

        self._initialize_model()

    @classmethod
    def get_instance(cls) -> "BGERerankerService":
        """Get or initialize singleton instance."""
        if cls._instance is None:
            with _RERANKER_INSTANCE_LOCK:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        with _RERANKER_INSTANCE_LOCK:
            cls._instance = None

    def _resolve_device(self, configured_device: str) -> str:
        """Determine target hardware device (CUDA vs CPU)."""
        import torch

        if configured_device == "cuda":
            if torch.cuda.is_available():
                return "cuda"
            logger.warning("CUDA requested for Reranker but not available. Falling back to CPU.")
            return "cpu"
        elif configured_device == "cpu":
            return "cpu"
        else:  # "auto"
            return "cuda" if torch.cuda.is_available() else "cpu"

    def _resolve_model_path(self) -> str:
        """Resolve local model snapshot if present, else fallback to Hugging Face ID."""
        if settings.RERANKER_SNAPSHOT_PATH and os.path.exists(settings.RERANKER_SNAPSHOT_PATH):
            logger.info("Using configured local Reranker snapshot: %s", settings.RERANKER_SNAPSHOT_PATH)
            return settings.RERANKER_SNAPSHOT_PATH

        snapshots_dir = (
            Path.home()
            / ".cache"
            / "huggingface"
            / "hub"
            / "models--BAAI--bge-reranker-v2-m3"
            / "snapshots"
        )
        if snapshots_dir.exists():
            for child in snapshots_dir.iterdir():
                if child.is_dir() and (child / "config.json").exists():
                    logger.info("Auto-detected local Reranker snapshot: %s", child)
                    return str(child)

        return self.model_name

    def _initialize_model(self) -> None:
        """Load CrossEncoder model weights and configure precision."""
        try:
            from sentence_transformers import CrossEncoder

            resolved_path = self._resolve_model_path()
            logger.info(
                "Loading Cross-Encoder '%s' on device='%s' (max_length=%d)...",
                resolved_path,
                self.device,
                self.max_length,
            )
            model = CrossEncoder(
                resolved_path,
                max_length=self.max_length,
                device=self.device,
                trust_remote_code=True,
            )

            if self.device == "cuda" and self.use_fp16:
                try:
                    model.model.half()
                    logger.info("Enabled FP16 half-precision for Cross-Encoder GPU inference.")
                except Exception as fp_err:
                    logger.warning("Could not set FP16 for Reranker, using default: %s", fp_err)

            self.model = model
            logger.info("Cross-Encoder '%s' successfully loaded.", self.model_name)
        except Exception as e:
            logger.error("Failed to initialize Cross-Encoder '%s': %s", self.model_name, e)
            raise RerankerError(f"Failed to initialize Cross-Encoder: {str(e)}") from e

    def predict_pairs(
        self,
        pairs: List[Tuple[str, str]],
        batch_size: Optional[int] = None,
    ) -> List[float]:
        """Compute relevance scores for (query, text) pairs.

        Supports dynamic batch halving and automatic CPU fallback on CUDA OOM.
        """
        if not pairs:
            return []

        initial_bs = batch_size or self.batch_size
        current_bs = initial_bs
        import torch

        while current_bs >= 1:
            try:
                with _RERANKER_INFERENCE_LOCK:
                    scores = self.model.predict(
                        pairs,
                        batch_size=current_bs,
                        show_progress_bar=False,
                    )
                    # Convert to standard Python float list
                    if isinstance(scores, np.ndarray):
                        scores_list = [float(s) for s in scores.flatten()]
                    elif isinstance(scores, (list, tuple)):
                        scores_list = [float(s) for s in scores]
                    else:
                        scores_list = [float(scores)]

                    if self.device == "cuda":
                        torch.cuda.empty_cache()

                    return scores_list

            except torch.cuda.OutOfMemoryError as oom_err:
                logger.warning(
                    "CUDA OOM in Reranker with batch_size=%d: %s. Halving batch size.",
                    current_bs,
                    oom_err,
                )
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
                current_bs //= 2

            except Exception as exc:
                logger.error("Error during Cross-Encoder prediction: %s", exc)
                raise RerankerError(f"Reranking prediction failed: {str(exc)}") from exc

        # If all CUDA batch sizes failed with OOM, fallback to CPU
        logger.error("All CUDA batch sizes OOMed in Reranker. Attempting CPU fallback.")
        return self._cpu_fallback_predict(pairs)

    def _cpu_fallback_predict(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """Execute prediction strictly on CPU when GPU memory is exhausted."""
        import torch

        logger.warning("Executing Cross-Encoder CPU fallback for %d pairs.", len(pairs))
        with _RERANKER_INFERENCE_LOCK:
            try:
                self.model.model.to("cpu")
                self.model.model.float()
                self.device = "cpu"

                scores = self.model.predict(pairs, batch_size=2, show_progress_bar=False)
                if isinstance(scores, np.ndarray):
                    res = [float(s) for s in scores.flatten()]
                else:
                    res = [float(s) for s in scores]

                # Restore to CUDA if GPU is available
                if torch.cuda.is_available() and settings.RERANKER_DEVICE != "cpu":
                    self.model.model.to("cuda")
                    if self.use_fp16:
                        self.model.model.half()
                    self.device = "cuda"

                return res
            except Exception as e:
                logger.error("Reranker CPU fallback failed: %s", e)
                raise RerankerError(f"Reranker CPU fallback failed: {str(e)}") from e

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Rerank candidate chunks using Cross-Encoder joint attention.

        Args:
            query: The search query string.
            candidates: List of candidate chunk dictionaries (must contain 'text').
            top_k: Optional limit on the number of returned results.
            score_threshold: Optional minimum reranker score threshold.

        Returns:
            Ranked list of candidates with attached 'rerank_score' and updated 'score'.
        """
        if not candidates:
            return []

        if not query or not query.strip():
            raise RerankerError("Search query cannot be empty for reranking.")

        # Construct (query, passage) pairs
        pairs = [(query, c.get("text", "")) for c in candidates]
        scores = self.predict_pairs(pairs)

        reranked = []
        for cand, score in zip(candidates, scores):
            if score_threshold is not None and score < score_threshold:
                continue

            item = dict(cand)
            item["rerank_score"] = float(score)
            item["score"] = float(score)  # Rerank score becomes primary score
            reranked.append(item)

        # Sort descending by Cross-Encoder relevance score
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        if top_k is not None and top_k > 0:
            reranked = reranked[:top_k]

        return reranked


def get_reranker_service() -> BGERerankerService:
    """Dependency provider for BGERerankerService."""
    return BGERerankerService.get_instance()
