"""
Vector Embedding Generator for Resume RAG indexing using EmbeddingProvider abstraction.
"""

import asyncio
from typing import List, Optional
from ai.config import ai_settings
from backend.domain.ai.interfaces import EmbeddingProvider
from backend.infrastructure.ai.factory import get_embedding_provider


class VectorEmbedder:
    """
    Embedding Service Wrapper utilizing the pluggable EmbeddingProvider protocol.
    """

    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or get_embedding_provider()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a float vector for the input text using the configured EmbeddingProvider.
        """
        if not text or not text.strip():
            return [0.0] * self.provider.dimension

        if hasattr(self.provider, "embed_text_sync"):
            return self.provider.embed_text_sync(text)

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.provider.embed_text(text)).result()
            else:
                return asyncio.run(self.provider.embed_text(text))
        except Exception:
            return [0.0] * self.provider.dimension
