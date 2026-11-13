"""
AI Infrastructure package exposing concrete provider implementations and factory.
"""

from backend.infrastructure.ai.nvidia_nim_provider import NvidiaNIMLLMProvider
from backend.infrastructure.ai.gemini_provider import GeminiLLMProvider
from backend.infrastructure.ai.openai_provider import OpenAILLMProvider
from backend.infrastructure.ai.mock_provider import MockLLMProvider, MockEmbeddingProvider
from backend.infrastructure.ai.sentence_transformer_provider import SentenceTransformersProvider
from backend.infrastructure.ai.telemetry import ai_telemetry, AITelemetryTracker
from backend.infrastructure.ai.factory import (
    get_llm_provider,
    set_llm_provider,
    reset_providers,
    get_embedding_provider,
    set_embedding_provider,
)

__all__ = [
    "NvidiaNIMLLMProvider",
    "GeminiLLMProvider",
    "OpenAILLMProvider",
    "MockLLMProvider",
    "MockEmbeddingProvider",
    "SentenceTransformersProvider",
    "ai_telemetry",
    "AITelemetryTracker",
    "get_llm_provider",
    "set_llm_provider",
    "reset_providers",
    "get_embedding_provider",
    "set_embedding_provider",
]
