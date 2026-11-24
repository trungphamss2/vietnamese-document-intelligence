"""Embedding service utilizing BAAI/bge-m3 with RTX 3050 6GB optimization."""

import gc
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from app.core.config import settings
from app.core.exceptions import EmbeddingEngineError

logger = logging.getLogger(__name__)

# Global concurrency lock across threads to prevent OCR & Embedding VRAM contention on GPU
_GPU_INFERENCE_LOCK = threading.Lock()


class EmbeddingService:
    """Singleton service for generating dense text embeddings with BAAI/bge-m3.
    
    Optimized for RTX 3050 6GB:
    - FP16 half-precision on CUDA.
    - Length-based batching to minimize padding overhead.
    - Adaptive batch sizing and automatic OOM recovery.
    - Thread-safe GPU execution.
    - Seamless CPU fallback.
    """

    _instance: Optional["EmbeddingService"] = None

    def __init__(self) -> None:
        self.model = None
        self.device = "cpu"
        self.dimension = settings.EMBEDDING_DIM
        self._initialize_model()

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolve_model_path(self) -> str:
        """Resolve model path: prioritize verified local snapshot if present, else model id."""
        if settings.LOCAL_SNAPSHOT_PATH and os.path.exists(settings.LOCAL_SNAPSHOT_PATH):
            logger.info("Using local BAAI/bge-m3 snapshot from: %s", settings.LOCAL_SNAPSHOT_PATH)
            return settings.LOCAL_SNAPSHOT_PATH
        
        # Check standard default hub cache
        default_hub = (
            Path.home()
            / ".cache"
            / "huggingface"
            / "hub"
            / "models--BAAI--bge-m3"
            / "snapshots"
            / "5617a9f61b028005a4858fdac845db406aefb181"
        )
        if default_hub.exists():
            logger.info("Auto-detected local Hugging Face snapshot: %s", default_hub)
            return str(default_hub)

        return settings.EMBEDDING_MODEL

    def _initialize_model(self) -> None:
        """Load BAAI/bge-m3 with hardware-aware optimization."""
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            # 1. Device resolution
            if settings.EMBEDDING_DEVICE == "cuda":
                target_device = "cuda" if torch.cuda.is_available() else "cpu"
            elif settings.EMBEDDING_DEVICE == "cpu":
                target_device = "cpu"
            else:  # "auto"
                target_device = "cuda" if torch.cuda.is_available() else "cpu"

            self.device = target_device
            model_target = self._resolve_model_path()
            logger.info("Initializing embedding model '%s' on %s", model_target, self.device)

            with _GPU_INFERENCE_LOCK:
                # 2. Load model
                model = SentenceTransformer(
                    model_name_or_path=model_target,
                    device=self.device,
                    trust_remote_code=True,
                )

                # Set max sequence length
                if hasattr(model, "max_seq_length"):
                    model.max_seq_length = settings.EMBEDDING_MAX_SEQ_LENGTH

                # 3. Precision optimization: FP16 on CUDA for RTX 3050 VRAM efficiency
                if self.device == "cuda" and settings.EMBEDDING_USE_FP16:
                    try:
                        model.half()
                        logger.info("Enabled FP16 half-precision for GPU inference.")
                    except Exception as fp_err:
                        logger.warning("Could not set FP16, proceeding with standard precision: %s", fp_err)

            self.model = model
            if hasattr(self.model, "get_embedding_dimension"):
                self.dimension = self.model.get_embedding_dimension() or settings.EMBEDDING_DIM
            elif hasattr(self.model, "get_sentence_embedding_dimension"):
                self.dimension = self.model.get_sentence_embedding_dimension() or settings.EMBEDDING_DIM
            else:
                self.dimension = settings.EMBEDDING_DIM
            logger.info("Embedding model loaded successfully. Vector dimension: %d", self.dimension)

        except Exception as e:
            logger.error("Failed to initialize embedding model: %s", e)
            raise EmbeddingEngineError(f"Failed to initialize embedding model '{settings.EMBEDDING_MODEL}': {str(e)}") from e

    def embed_texts(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        use_length_batching: bool = True,
    ) -> List[List[float]]:
        """Compute dense embeddings for a list of texts with adaptive batching and OOM recovery.
        
        Args:
            texts: List of text strings to embed.
            batch_size: Optional batch size override (defaults to settings.EMBEDDING_BATCH_SIZE).
            use_length_batching: Whether to sort by text length to minimize token padding.
            
        Returns:
            List of L2-normalized float vectors, each of dimension 1024.
        """
        if not texts:
            return []

        bs = batch_size or settings.EMBEDDING_BATCH_SIZE

        # Length-based batching: sort indices by text length, embed, and revert order
        if use_length_batching and len(texts) > 1:
            sorted_indices = sorted(range(len(texts)), key=lambda i: len(texts[i]))
            sorted_texts = [texts[i] for i in sorted_indices]
            sorted_vectors = self._embed_with_retry(sorted_texts, bs)
            
            # Reconstruct original order
            vectors = [None] * len(texts)
            for orig_idx, vec in zip(sorted_indices, sorted_vectors):
                vectors[orig_idx] = vec
            return vectors

        return self._embed_with_retry(texts, bs)

    def _embed_with_retry(self, texts: List[str], initial_batch_size: int) -> List[List[float]]:
        """Execute embedding inference with automatic batch halving and CPU fallback on OOM."""
        current_bs = initial_batch_size
        import torch

        while current_bs >= 1:
            try:
                with _GPU_INFERENCE_LOCK:
                    embeddings = self.model.encode(
                        texts,
                        batch_size=current_bs,
                        show_progress_bar=False,
                        normalize_embeddings=True,
                        convert_to_numpy=True,
                    )

                if isinstance(embeddings, np.ndarray):
                    if len(embeddings.shape) == 1:
                        embeddings = np.expand_dims(embeddings, axis=0)
                    vec_list = embeddings.tolist()
                else:
                    vec_list = [list(vec) for vec in embeddings]

                self._validate_vectors(vec_list)
                return vec_list

            except Exception as e:
                is_oom = "out of memory" in str(e).lower() or "cuda" in str(e).lower()
                if self.device == "cuda" and is_oom:
                    logger.warning("CUDA OOM detected at batch_size=%d. Freeing cache...", current_bs)
                    torch.cuda.empty_cache()
                    gc.collect()

                    if current_bs > 1:
                        current_bs = max(1, current_bs // 2)
                        logger.info("Retrying embedding with halved batch_size=%d...", current_bs)
                        continue
                    else:
                        logger.warning("OOM persisted at batch_size=1. Falling back to CPU...")
                        return self._cpu_fallback_embed(texts)

                raise EmbeddingEngineError(f"Failed to embed texts: {str(e)}") from e

        return self._cpu_fallback_embed(texts)

    def _cpu_fallback_embed(self, texts: List[str]) -> List[List[float]]:
        """Gracefully switch model to CPU and compute embeddings."""
        logger.info("Executing CPU fallback embedding for %d texts...", len(texts))
        try:
            import torch
            with _GPU_INFERENCE_LOCK:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()

                # Temporarily move to CPU float32
                self.model.to("cpu")
                self.model.float()
                self.device = "cpu"

                embeddings = self.model.encode(
                    texts,
                    batch_size=2,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )

            if isinstance(embeddings, np.ndarray):
                if len(embeddings.shape) == 1:
                    embeddings = np.expand_dims(embeddings, axis=0)
                vec_list = embeddings.tolist()
            else:
                vec_list = [list(vec) for vec in embeddings]

            self._validate_vectors(vec_list)
            return vec_list

        except Exception as cpu_err:
            raise EmbeddingEngineError(f"Embedding failed even on CPU fallback: {str(cpu_err)}") from cpu_err

    def _validate_vectors(self, vectors: List[List[float]]) -> None:
        """Validate output vectors: dimension 1024, no NaNs, no Infs."""
        for idx, vec in enumerate(vectors):
            if len(vec) != self.dimension:
                raise EmbeddingEngineError(f"Vector {idx} dimension mismatch: expected {self.dimension}, got {len(vec)}")
            arr = np.array(vec, dtype=np.float32)
            if np.isnan(arr).any() or np.isinf(arr).any():
                raise EmbeddingEngineError(f"Vector {idx} contains NaN or Infinite values.")

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query string for semantic vector search."""
        if not query or not query.strip():
            raise EmbeddingEngineError("Search query cannot be empty.")

        vectors = self.embed_texts([query.strip()], batch_size=1, use_length_batching=False)
        if not vectors:
            raise EmbeddingEngineError("No vector returned for query.")
        return vectors[0]

    def compare_fp16_vs_fp32(self, texts: List[str]) -> Dict[str, float]:
        """Compare FP16 and FP32 outputs on CPU/GPU to verify numerical consistency."""
        import torch
        if not torch.cuda.is_available():
            return {"status": "skipped_no_cuda"}

        with _GPU_INFERENCE_LOCK:
            # 1. FP16 on CUDA
            self.model.to("cuda")
            self.model.half()
            v_fp16 = self.model.encode(texts, batch_size=2, normalize_embeddings=True)

            # 2. FP32 on CPU
            self.model.to("cpu")
            self.model.float()
            v_fp32 = self.model.encode(texts, batch_size=2, normalize_embeddings=True)

            # Restore to default CUDA FP16
            self.model.to("cuda")
            self.model.half()
            self.device = "cuda"

        # Calculate cosine similarity and max absolute diff with float64 precision
        cos_sims = []
        max_diffs = []
        for v16, v32 in zip(v_fp16, v_fp32):
            v16_64 = np.asarray(v16, dtype=np.float64)
            v32_64 = np.asarray(v32, dtype=np.float64)
            denom = np.linalg.norm(v16_64) * np.linalg.norm(v32_64)
            if denom == 0.0:
                sim = 0.0
            else:
                sim = float(np.clip(np.dot(v16_64, v32_64) / denom, -1.0, 1.0))
            cos_sims.append(sim)
            max_diffs.append(float(np.max(np.abs(v16_64 - v32_64))))

        return {
            "avg_cosine_similarity": float(np.mean(cos_sims)),
            "min_cosine_similarity": float(np.min(cos_sims)),
            "max_absolute_difference": float(np.max(max_diffs)),
            "avg_absolute_difference": float(np.mean(max_diffs)),
        }


def get_embedding_service() -> EmbeddingService:
    """Dependency injection helper for EmbeddingService."""
    return EmbeddingService.get_instance()
