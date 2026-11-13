"""
Domain Interfaces and Data Transfer Objects for AI Providers.
Decouples application services from specific LLM & Embedding vendors.
"""

from typing import Protocol, Optional, List, Dict, Any, runtime_checkable
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    """Encapsulates a standard LLM generation request."""
    system_prompt: str
    user_prompt: str
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    response_json: bool = Field(default=True)
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""
    content: str
    raw_json: Optional[Any] = None
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    ttft_sec: Optional[float] = None
    total_latency_sec: Optional[float] = None
    stage_timings: Optional[Dict[str, float]] = None


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers (Gemini, OpenAI, Mock, etc.) must implement."""
    
    @property
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'openai', 'mock')."""
        ...

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Asynchronously generates text/JSON using the underlying LLM."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol that all vector embedding providers must implement."""
    
    @property
    def provider_name(self) -> str:
        """Name of the embedding provider."""
        ...

    @property
    def dimension(self) -> int:
        """Vector embedding dimensionality."""
        ...

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single string of text."""
        ...

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        ...
