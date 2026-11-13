"""
OpenAI LLM Provider Implementation.
"""

import json
import logging
import re
from typing import Optional, Dict, Any
from backend.domain.ai.interfaces import LLMProvider, LLMRequest, LLMResponse
# pyrefly: ignore [missing-import]
from ai.config import ai_settings

logger = logging.getLogger(__name__)


class OpenAILLMProvider:
    """LLM Provider backed by the official openai AsyncOpenAI SDK."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or ai_settings.openai_api_key
        self.default_model = default_model or ai_settings.secondary_model or "gpt-4o-mini"
        self.provider_name = "openai"
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is not set.")
            # pyrefly: ignore [missing-import]
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        model_name = request.model or self.default_model

        kwargs: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_json:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            raw_text = choice.message.content or ""

            raw_json = None
            if request.response_json and raw_text:
                cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                try:
                    raw_json = json.loads(cleaned)
                except Exception as ex:
                    logger.warning(f"Failed to parse OpenAI JSON output: {ex}")

            usage = response.usage
            p_tokens = usage.prompt_tokens if usage else 0
            c_tokens = usage.completion_tokens if usage else 0
            t_tokens = usage.total_tokens if usage else 0

            return LLMResponse(
                content=raw_text,
                raw_json=raw_json,
                provider="openai",
                model=model_name,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
            )
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
