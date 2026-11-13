"""
Google Gemini LLM Provider Implementation.
"""

import json
import logging
import re
from typing import Optional, Dict, Any
from backend.domain.ai.interfaces import LLMProvider, LLMRequest, LLMResponse
# pyrefly: ignore [missing-import]
from ai.config import ai_settings

logger = logging.getLogger(__name__)


class GeminiLLMProvider:
    """LLM Provider backed by the official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or ai_settings.gemini_api_key
        self.default_model = default_model or ai_settings.primary_model or "gemini-3.8-flash"
        self.provider_name = "gemini"
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not set.")
            # pyrefly: ignore [missing-import]
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        # pyrefly: ignore [missing-import]
        from google.genai import types

        model_name = request.model or self.default_model
        # Normalize model name if necessary
        if not model_name.startswith("gemini"):
            model_name = "gemini-3.8-flash"
        elif any(v in model_name for v in ["3.6", "2.5", "2.0", "1.5", "1.0", "pro"]):
            model_name = "gemini-3.8-flash"

        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            response_mime_type="application/json" if request.response_json else "text/plain",
        )

        try:
            import asyncio
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=model_name,
                    contents=request.user_prompt,
                    config=config,
                ),
            )

            raw_text = response.text or ""
            raw_json = None
            if request.response_json and raw_text:
                cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                try:
                    raw_json = json.loads(cleaned)
                except Exception as ex:
                    logger.warning(f"Failed to parse Gemini JSON output: {ex}")

            usage = getattr(response, "usage_metadata", None)
            p_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            c_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

            return LLMResponse(
                content=raw_text,
                raw_json=raw_json,
                provider="gemini",
                model=model_name,
                prompt_tokens=p_tokens or 0,
                completion_tokens=c_tokens or 0,
                total_tokens=(p_tokens or 0) + (c_tokens or 0),
            )
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise
