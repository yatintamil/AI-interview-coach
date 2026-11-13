import asyncio
import json
import logging
import re
from typing import Optional, Dict, Any
# pyrefly: ignore [missing-import]
from backend.domain.ai.interfaces import LLMProvider, LLMRequest, LLMResponse
# pyrefly: ignore [missing-import]
from ai.config import ai_settings

logger = logging.getLogger(__name__)

_cached_pipeline = None


class LocalTransformersLLMProvider:
    """
    On-device LLM Provider powered by Hugging Face `transformers`.
    Executes inference locally on CPU/GPU without external API calls.
    Free, private, zero-rate-limited.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.model_name = (
            model_name
            or getattr(ai_settings, "local_transformers_model", None)
            or "Qwen/Qwen2.5-0.5B-Instruct"
        )
        self.device = device or "cpu"
        self.provider_name = "local_transformers"
        self._failed_load = False

    def _get_pipeline(self):
        global _cached_pipeline
        if _cached_pipeline is not None:
            return _cached_pipeline

        if not self._failed_load:
            try:
                # pyrefly: ignore [missing-import]
                import torch
                # pyrefly: ignore [missing-import]
                from transformers import pipeline, AutoTokenizer

                logger.info(f"Loading on-device local transformers pipeline: {self.model_name} on {self.device}")
                tokenizer = AutoTokenizer.from_pretrained(self.model_name, clean_up_tokenization_spaces=False)
                _cached_pipeline = pipeline(
                    "text-generation",
                    model=self.model_name,
                    tokenizer=tokenizer,
                    device=self.device,
                    torch_dtype=torch.float32,
                    max_new_tokens=512,
                )
            except Exception as e:
                logger.warning(
                    f"Could not load local transformers model '{self.model_name}': {e}. "
                    f"Falling back to local heuristic generation."
                )
                self._failed_load = True
        return _cached_pipeline

    def _generate_sync(self, prompt: str, max_tokens: int, temperature: float) -> str:
        pipe = self._get_pipeline()
        if pipe is None:
            raise RuntimeError(f"Local transformers pipeline not initialized for {self.model_name}")

        outputs = pipe(
            prompt,
            max_new_tokens=min(max_tokens or 256, 256),
            temperature=max(0.1, temperature),
            do_sample=temperature > 0.0,
            pad_token_id=pipe.tokenizer.eos_token_id,
        )
        generated_text = outputs[0]["generated_text"]
        if generated_text.startswith(prompt):
            return generated_text[len(prompt):].strip()
        return generated_text.strip()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        prompt = f"<|im_start|>system\n{request.system_prompt}<|im_end|>\n<|im_start|>user\n{request.user_prompt}<|im_end|>\n<|im_start|>assistant\n"
        if request.response_json:
            prompt = f"<|im_start|>system\n{request.system_prompt}\nYou MUST output valid JSON only.<|im_end|>\n<|im_start|>user\n{request.user_prompt}<|im_end|>\n<|im_start|>assistant\n"

        try:
            loop = asyncio.get_running_loop()
            raw_text = await loop.run_in_executor(
                None,
                self._generate_sync,
                prompt,
                request.max_tokens or 512,
                request.temperature,
            )

            raw_json = None
            if request.response_json and raw_text:
                cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                cleaned = cleaned.rstrip("`").strip()
                try:
                    raw_json = json.loads(cleaned)
                except Exception:
                    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                    if match:
                        try:
                            raw_json = json.loads(match.group(0))
                        except Exception:
                            pass

            return LLMResponse(
                content=raw_text,
                raw_json=raw_json,
                provider="local_transformers",
                model=self.model_name,
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(raw_text.split()),
                total_tokens=len(prompt.split()) + len(raw_text.split()),
            )
        except Exception as e:
            logger.error(f"Local transformers inference error: {e}")
            raise
