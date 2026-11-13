"""
AI Provider Factory and Registry.
Provides dependency injection, connection reuse, and runtime provider resolution.
Enforces the priority order:
1. NVIDIA NIM (Primary ultra-fast inference provider)
2. Google Gemini (Secondary cloud fallback)
3. Local on-device Transformers (Optional on-device execution)
4. Mock / Deterministic NLP (Safe deterministic fallback)
"""

import os
import sys
import logging
from typing import Optional

from backend.domain.ai.interfaces import LLMProvider, EmbeddingProvider
from backend.infrastructure.ai.gemini_provider import GeminiLLMProvider
from backend.infrastructure.ai.openai_provider import OpenAILLMProvider
from backend.infrastructure.ai.mock_provider import MockLLMProvider, MockEmbeddingProvider
from backend.infrastructure.ai.sentence_transformer_provider import SentenceTransformersProvider
from backend.infrastructure.ai.nvidia_nim_provider import NvidiaNIMLLMProvider
from backend.infrastructure.ai.local_transformers_provider import LocalTransformersLLMProvider
from backend.infrastructure.ai.huggingface_provider import HuggingFaceLLMProvider
from ai.config import ai_settings

logger = logging.getLogger(__name__)

_global_gemini_provider: Optional[LLMProvider] = None
_global_nim_provider: Optional[LLMProvider] = None
_global_major_provider: Optional[LLMProvider] = None
_global_routine_provider: Optional[LLMProvider] = None
_global_embedding_provider: Optional[EmbeddingProvider] = None


def get_llm_provider(task: str = "routine", force_mock: bool = False) -> LLMProvider:
    """
    Factory function returning the active LLM Provider based on project-wide priority:
    - Priority 1: NVIDIA NIM (Primary high-performance inference engine).
    - Priority 2: Google Gemini (Secondary cloud fallback when NIM unconfigured or during failover).
    - Priority 3: Local on-device Hugging Face Transformers (Only if explicitly enabled).
    - Priority 4: Mock/Deterministic NLP rule engines (Safe offline fallback).
    """
    global _global_gemini_provider, _global_nim_provider, _global_major_provider, _global_routine_provider

    # 1. Environment / Parameter Mock Overrides (for testing & offline validation)
    if force_mock or os.environ.get("LLM_PROVIDER", "").lower() == "mock" or "pytest" in sys.modules:
        if task == "major" and _global_major_provider is not None:
            return _global_major_provider
        if task != "major" and _global_routine_provider is not None:
            return _global_routine_provider
        return MockLLMProvider()

    # 2. Test/Manual Provider Injections
    if task == "major" and _global_major_provider is not None:
        return _global_major_provider
    if task != "major" and _global_routine_provider is not None:
        return _global_routine_provider

    primary_choice = getattr(ai_settings, "primary_llm_provider", "nvidia_nim").lower()

    # 3. Priority 1: NVIDIA NIM (Default Primary)
    if primary_choice == "nvidia_nim" and ai_settings.nvidia_nim_api_key:
        if _global_nim_provider is None:
            try:
                _global_nim_provider = NvidiaNIMLLMProvider()
                logger.info(
                    f"Initialized primary NVIDIA NIM provider with model '{_global_nim_provider.default_model}'."
                )
            except Exception as e:
                logger.warning(f"Failed to initialize primary NVIDIA NIM provider: {e}")
        if _global_nim_provider is not None:
            return _global_nim_provider

    # 4. Priority 2: Google Gemini (Primary if explicitly requested, or secondary cloud fallback)
    if (primary_choice == "gemini" or primary_choice == "nvidia_nim") and ai_settings.gemini_api_key:
        if _global_gemini_provider is None:
            try:
                _global_gemini_provider = GeminiLLMProvider()
                logger.info("Initialized Google Gemini LLM provider as secondary cloud failover.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")
        if _global_gemini_provider is not None:
            return _global_gemini_provider

    # 5. Fallback to NVIDIA NIM if Gemini was chosen as primary but unavailable
    if ai_settings.nvidia_nim_api_key:
        if _global_nim_provider is None:
            try:
                _global_nim_provider = NvidiaNIMLLMProvider()
                logger.info("Initialized NVIDIA NIM LLM provider.")
            except Exception as e:
                logger.warning(f"Failed to initialize NVIDIA NIM provider: {e}")
        if _global_nim_provider is not None:
            return _global_nim_provider

    # 6. Priority 3: Local on-device Transformers (Only if explicitly enabled)
    if getattr(ai_settings, "use_local_transformers", False):
        try:
            return LocalTransformersLLMProvider()
        except Exception as e:
            logger.warning(f"Failed to initialize LocalTransformers provider: {e}")

    # 7. Priority 4: OpenAI / Anthropic for Major tasks if configured
    if task == "major" and getattr(ai_settings, "openai_api_key", None):
        try:
            return OpenAILLMProvider()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI provider: {e}")

    # 8. Final Deterministic Fallback
    logger.info(f"Using local Mock/Deterministic NLP provider for {task} task.")
    return MockLLMProvider()


def set_llm_provider(provider: LLMProvider, task: Optional[str] = None):
    """Override the active LLM provider (useful for testing and dependency injection)."""
    global _global_gemini_provider, _global_nim_provider, _global_major_provider, _global_routine_provider
    if task == "major":
        _global_major_provider = provider
    elif task == "routine":
        _global_routine_provider = provider
    else:
        _global_major_provider = provider
        _global_routine_provider = provider
        _global_gemini_provider = provider
        _global_nim_provider = provider


def reset_providers():
    """Resets cached provider singletons (useful between test runs)."""
    global _global_gemini_provider, _global_nim_provider, _global_major_provider, _global_routine_provider, _global_embedding_provider
    _global_gemini_provider = None
    _global_nim_provider = None
    _global_major_provider = None
    _global_routine_provider = None
    _global_embedding_provider = None


def get_embedding_provider(force_mock: bool = False) -> EmbeddingProvider:
    """Factory function returning the active Vector Embedding Provider."""
    global _global_embedding_provider
    if force_mock or os.environ.get("LLM_PROVIDER", "").lower() == "mock":
        return MockEmbeddingProvider(dimension=ai_settings.embedding_dimension)

    if _global_embedding_provider is not None:
        return _global_embedding_provider

    try:
        _global_embedding_provider = SentenceTransformersProvider()
        return _global_embedding_provider
    except Exception as e:
        logger.warning(
            f"Failed to initialize SentenceTransformersProvider ({e}), falling back to MockEmbeddingProvider."
        )
        _global_embedding_provider = MockEmbeddingProvider(dimension=ai_settings.embedding_dimension)
        return _global_embedding_provider


def set_embedding_provider(provider: EmbeddingProvider):
    """Override the active embedding provider (useful for testing)."""
    global _global_embedding_provider
    _global_embedding_provider = provider
