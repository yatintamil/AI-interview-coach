"""
Hugging Face / Open-Source LLM Provider Implementation.
Leverages Hugging Face's serverless inference endpoint with OpenAI compatibility.
"""

import json
import logging
import re
from typing import Optional, Dict, Any
from backend.domain.ai.interfaces import LLMProvider, LLMRequest, LLMResponse
# pyrefly: ignore [missing-import]
from ai.config import ai_settings

logger = logging.getLogger(__name__)


class HuggingFaceLLMProvider:
    """
    LLM Provider backed by Hugging Face's Serverless Router.
    Supports chat completion models like meta-llama/Llama-3.2-3B-Instruct,
    Qwen/Qwen2.5-7B-Instruct, or mistralai/Mistral-7B-Instruct-v0.3.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        base_url: str = "https://router.huggingface.co/hf-inference/v1",
    ):
        self.api_key = api_key or ai_settings.huggingface_api_key or ai_settings.hf_token
        self.default_model = default_model or ai_settings.huggingface_model or "meta-llama/Llama-3.2-3B-Instruct"
        self.base_url = base_url
        self.provider_name = "huggingface"
        self._client = None

    def _get_client(self):
        if self._client is None:
            # pyrefly: ignore [missing-import]
            from openai import AsyncOpenAI
            key = self.api_key or "hf_placeholder_token"
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=key,
                timeout=30.0,
            )
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        model_name = request.model or self.default_model

        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": min(request.max_tokens or 1024, 2048),
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
                    logger.warning(f"Failed to parse HuggingFace JSON output: {ex}")

            usage = getattr(response, "usage", None)
            p_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            c_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            t_tokens = getattr(usage, "total_tokens", 0) if usage else 0

            return LLMResponse(
                content=raw_text,
                raw_json=raw_json,
                provider="huggingface",
                model=model_name,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
            )
        except Exception as e:
            logger.warning(f"HuggingFace inference error: {e}")
            raise
