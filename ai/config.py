"""
AI Module Configuration
"""

from typing import Optional
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict

class AISettings(BaseSettings):
    # LLM Settings (Primary LLM set to NVIDIA NIM with Gemini / local fallback)
    primary_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    primary_llm_provider: str = "nvidia_nim"  # "nvidia_nim" (primary) -> "gemini" (secondary) -> local -> mock
    secondary_model: str = "gemini-3.8-flash"
    fallback_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    extraction_temperature: float = 0.0
    max_tokens: int = 4096

    # Embedding & RAG Settings (Option A: Local Hugging Face Embeddings)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    chunk_max_tokens: int = 300
    chunk_overlap_tokens: int = 50

    # NVIDIA NIM Cloud API Configuration (Primary Fast Inference Provider)
    nvidia_nim_api_key: Optional[str] = None
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_nim_fallback_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_nim_timeout: float = 40.0
    nvidia_nim_max_retries: int = 2

    # Local Transformers Model (On-device execution via Hugging Face pipeline - Free, zero-quota)
    local_transformers_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    use_local_transformers: bool = False

    # Hugging Face / Free Open-Source Models (Optional Cloud API)
    huggingface_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    huggingface_api_key: Optional[str] = None
    hf_token: Optional[str] = None

    # API Keys / Configs (loaded from env)
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

ai_settings = AISettings()

