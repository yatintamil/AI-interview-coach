"""
Hugging Face Sentence Transformers Embedding Provider.
"""

import logging
from typing import List
from backend.domain.ai.interfaces import EmbeddingProvider
# pyrefly: ignore [missing-import]
from ai.config import ai_settings
# pyrefly: ignore [missing-import]

logger = logging.getLogger(__name__)


class SentenceTransformersProvider:
    """Local Hugging Face sentence transformers embedding provider."""

    def __init__(self, model_name: str = None, dimension: int = None):
        self.model_name = model_name or ai_settings.embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
        self._dimension = dimension or ai_settings.embedding_dimension or 384
        self.provider_name = "sentence_transformers"
        self._model = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_model(self):
        if self._model is None and not hasattr(self, "_failed_load"):
            try:
                # pyrefly: ignore [missing-import]
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading local SentenceTransformer model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}), using deterministic pseudo-embeddings.")
                self._failed_load = True
        return self._model

    def _fallback_pseudo_embedding(self, text: str) -> List[float]:
        import hashlib
        vec = []
        for i in range(self._dimension):
            h = hashlib.sha256(f"{text}_{i}".encode("utf-8")).hexdigest()
            val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
            vec.append(val)
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    def embed_text_sync(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self._dimension
        model = self._get_model()
        if model is not None:
            try:
                vector = model.encode(text, normalize_embeddings=True)
                return vector.tolist()
            except Exception:
                pass
        return self._fallback_pseudo_embedding(text)

    async def embed_text(self, text: str) -> List[float]:
        return self.embed_text_sync(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return [self.embed_text_sync(t) for t in texts]
