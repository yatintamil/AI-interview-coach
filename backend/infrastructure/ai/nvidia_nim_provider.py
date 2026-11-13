"""
NVIDIA NIM Cloud LLM Provider Implementation.
Provides ultra-fast GPU-accelerated inference via OpenAI-compatible NIM endpoints.
Adheres strictly to backend.domain.ai.interfaces.LLMProvider protocol.
Implements bounded retries with exponential backoff & jitter, error categorization,
model fallback, and granular telemetry tracking.
"""

import asyncio
import json
import logging
import random
import re
import time
from typing import Optional, Dict, Any

from backend.domain.ai.interfaces import LLMProvider, LLMRequest, LLMResponse
from backend.infrastructure.ai.telemetry import ai_telemetry
from ai.config import ai_settings

logger = logging.getLogger(__name__)


class NvidiaNIMLLMProvider:
    """
    LLM Provider backed by the official openai AsyncOpenAI client
    targeting the NVIDIA NIM API (default: https://integrate.api.nvidia.com/v1).
    Reuses persistent client connections, enforces fast bounded timeouts,
    implements jittered backoff retries, and records operational telemetry.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key or ai_settings.nvidia_nim_api_key
        self.base_url = (
            base_url
            or getattr(ai_settings, "nvidia_nim_base_url", None)
            or "https://integrate.api.nvidia.com/v1"
        )
        self.default_model = (
            default_model
            or getattr(ai_settings, "nvidia_nim_model", None)
            or "nvidia/nemotron-3-ultra-550b-a55b"
        )
        self.fallback_model = (
            getattr(ai_settings, "nvidia_nim_fallback_model", None)
            or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
        )
        self.timeout = (
            timeout
            if timeout is not None
            else getattr(ai_settings, "nvidia_nim_timeout", 20.0)
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else getattr(ai_settings, "nvidia_nim_max_retries", 2)
        )
        self.provider_name = "nvidia_nim"
        self._client = None
        self._bound_loop = None
        self._last_metrics: Dict[str, Any] = {}

    def get_last_metrics(self) -> Dict[str, Any]:
        """Returns the token usage and latency metrics from the most recent generation."""
        return getattr(self, "_last_metrics", {})

    def _get_client(self):
        """Initializes and reuses the asynchronous OpenAI client, rebinding if event loop changes."""
        from openai import AsyncOpenAI

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        is_real_openai = isinstance(self._client, AsyncOpenAI)
        needs_reinit = False

        if self._client is None:
            needs_reinit = True
        elif is_real_openai and (
            (getattr(self, "_bound_loop", None) is not None and self._bound_loop != current_loop)
            or (getattr(self, "_bound_loop", None) is not None and self._bound_loop.is_closed())
        ):
            needs_reinit = True

        if needs_reinit:
            if not self.api_key:
                raise ValueError("NVIDIA_NIM_API_KEY is not set.")
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=0,  # Provider handles explicit exponential backoff with jitter
            )
            self._bound_loop = current_loop
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Asynchronously generates text/JSON using the NVIDIA NIM endpoint.
        - Reuses persistent HTTP connection pool.
        - Categorizes errors (Auth vs Rate Limit vs Timeout vs Network).
        - Applies bounded exponential backoff with jitter.
        - Recovers via self.fallback_model if primary model fails.
        - Emits detailed telemetry.
        """
        client = self._get_client()
        model_name = request.model or self.default_model

        # Allow full timeout for primary model execution
        primary_timeout = self.timeout
        t_overall_start = time.perf_counter()
        retries_conducted = 0
        last_error = None
        req_meta = getattr(request, "metadata", None) or {}

        try:
            resp, retries_conducted = await self._execute_with_retry(
                client=client,
                model_name=model_name,
                request=request,
                timeout=primary_timeout,
            )
            ai_telemetry.record_inference(
                provider="nvidia_nim",
                model=model_name,
                task_type=req_meta.get("task_type", "routine"),
                latency_ms=(time.perf_counter() - t_overall_start) * 1000,
                prompt_tokens=resp.prompt_tokens,
                completion_tokens=resp.completion_tokens,
                total_tokens=resp.total_tokens,
                success=True,
                retry_count=retries_conducted,
                ttft_ms=(resp.ttft_sec * 1000) if resp.ttft_sec else None,
            )
            return resp
        except Exception as primary_err:
            last_error = primary_err
            logger.warning(
                f"NVIDIA NIM primary model '{model_name}' failed after {retries_conducted} retries: {primary_err}"
            )

            # Try fallback model if configured and distinct
            if self.fallback_model and model_name != self.fallback_model:
                logger.info(
                    f"Attempting NVIDIA NIM fallback model '{self.fallback_model}'..."
                )
                try:
                    fallback_timeout = self.timeout
                    resp, fallback_retries = await self._execute_with_retry(
                        client=client,
                        model_name=self.fallback_model,
                        request=request,
                        timeout=fallback_timeout,
                    )
                    ai_telemetry.record_inference(
                        provider="nvidia_nim",
                        model=self.fallback_model,
                        task_type=req_meta.get("task_type", "routine"),
                        latency_ms=(time.perf_counter() - t_overall_start) * 1000,
                        prompt_tokens=resp.prompt_tokens,
                        completion_tokens=resp.completion_tokens,
                        total_tokens=resp.total_tokens,
                        success=True,
                        retry_count=retries_conducted + fallback_retries,
                        fallback_activated=True,
                        fallback_reason=f"primary_model_failed: {str(primary_err)[:100]}",
                        ttft_ms=(resp.ttft_sec * 1000) if resp.ttft_sec else None,
                    )
                    return resp
                except Exception as fb_err:
                    last_error = fb_err
                    logger.error(f"NVIDIA NIM fallback model '{self.fallback_model}' also failed: {fb_err}")

            # Record failure telemetry
            ai_telemetry.record_inference(
                provider="nvidia_nim",
                model=model_name,
                task_type=req_meta.get("task_type", "routine"),
                latency_ms=(time.perf_counter() - t_overall_start) * 1000,
                success=False,
                retry_count=retries_conducted,
                error_type=type(last_error).__name__,
                fallback_activated=False,
            )
            raise last_error

    async def _execute_with_retry(
        self,
        client,
        model_name: str,
        request: LLMRequest,
        timeout: float,
    ) -> tuple[LLMResponse, int]:
        """
        Executes inference call with bounded exponential backoff & jitter.
        Categorizes exceptions to determine if retry is appropriate.
        """
        from openai import AuthenticationError, RateLimitError, APIConnectionError, InternalServerError, BadRequestError

        attempts = 0
        t0 = time.perf_counter()

        while attempts <= self.max_retries:
            time_left = timeout - (time.perf_counter() - t0)
            if time_left <= 1.0 and attempts > 0:
                raise TimeoutError(f"NVIDIA NIM deadline exceeded during retries ({timeout:.1f}s)")

            per_attempt_timeout = max(3.0, time_left)

            try:
                resp = await self._execute_call(client, model_name, request, timeout=per_attempt_timeout)
                return resp, attempts
            except AuthenticationError as auth_err:
                # Fatal credential error: do not retry
                logger.error(f"NVIDIA NIM Authentication Error: {auth_err}. Verify NVIDIA_NIM_API_KEY in .env.")
                raise
            except BadRequestError as bad_req_err:
                # Client parameter error: do not retry
                logger.error(f"NVIDIA NIM Bad Request on model '{model_name}': {bad_req_err}")
                raise
            except (RateLimitError, APIConnectionError, InternalServerError, TimeoutError, asyncio.TimeoutError) as retryable_err:
                attempts += 1
                if attempts > self.max_retries:
                    raise retryable_err

                # Exponential backoff with jitter: base 0.5s * 2^(attempt-1) + jitter [0.1, 0.4]s
                backoff = min(2.5, 0.5 * (2 ** (attempts - 1))) + random.uniform(0.1, 0.4)
                logger.warning(
                    f"NVIDIA NIM {type(retryable_err).__name__} on '{model_name}' (attempt {attempts}/{self.max_retries}): "
                    f"retrying in {backoff:.2f}s..."
                )
                await asyncio.sleep(backoff)
            except Exception as general_err:
                # Unclassified error: check error string for 429 / 503
                err_str = str(general_err).lower()
                if "429" in err_str or "503" in err_str or "timeout" in err_str or "connection" in err_str:
                    attempts += 1
                    if attempts > self.max_retries:
                        raise general_err
                    backoff = min(2.5, 0.5 * (2 ** (attempts - 1))) + random.uniform(0.1, 0.4)
                    await asyncio.sleep(backoff)
                else:
                    raise general_err

        raise TimeoutError("NVIDIA NIM retries exhausted.")

    async def _execute_call(
        self,
        client,
        model_name: str,
        request: LLMRequest,
        timeout: Optional[float] = None,
    ) -> LLMResponse:
        """Executes a single chat completion attempt against the specified NIM model."""
        call_timeout = timeout or self.timeout
        kwargs: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        # Request JSON mode if specified and supported
        if request.response_json:
            if "diffusiongemma" not in model_name:
                kwargs["response_format"] = {"type": "json_object"}
            else:
                kwargs["messages"][0]["content"] += "\nReturn strictly valid JSON only."

        t0 = time.perf_counter()
        ttft_sec = None

        try:
            # For non-JSON text tutoring, stream to measure exact TTFT and avoid buffered hang
            if not request.response_json:
                kwargs["stream"] = True

                async def _consume_stream() -> str:
                    nonlocal ttft_sec
                    stream_or_resp = await client.chat.completions.create(**kwargs)
                    # Support non-streaming mock/direct completion responses
                    if hasattr(stream_or_resp, "choices") and stream_or_resp.choices and hasattr(stream_or_resp.choices[0], "message"):
                        msg = stream_or_resp.choices[0].message
                        return msg.content or getattr(msg, "reasoning_content", None) or ""
                    chunks = []
                    reasoning_chunks = []
                    async for chunk in stream_or_resp:
                        if chunk.choices and chunk.choices[0].delta:
                            delta = chunk.choices[0].delta
                            if delta.content:
                                if ttft_sec is None:
                                    ttft_sec = time.perf_counter() - t0
                                chunks.append(delta.content)
                            elif getattr(delta, "reasoning_content", None):
                                reasoning_chunks.append(delta.reasoning_content)
                    if not chunks and reasoning_chunks:
                        chunks = reasoning_chunks
                    return "".join(chunks)

                raw_text = await asyncio.wait_for(_consume_stream(), timeout=call_timeout)
                latency_sec = time.perf_counter() - t0
                if ttft_sec is None:
                    ttft_sec = latency_sec

                # Strip thinking/channel tags emitted by certain reasoning models
                raw_text = re.sub(r"^<\|.*?channel\|>.*?(?:<channel\|>|$)", "", raw_text, flags=re.DOTALL).strip()
                raw_text = re.sub(r"^<channel\|>", "", raw_text).strip()
                raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
                raw_json = None

                # Token count estimations for streaming completions
                est_p_tokens = len((request.system_prompt + " " + request.user_prompt).split()) * 1.3
                est_c_tokens = len(raw_text.split()) * 1.3
                p_tokens = int(est_p_tokens)
                c_tokens = int(est_c_tokens)
                t_tokens = p_tokens + c_tokens
            else:
                response = await asyncio.wait_for(
                    client.chat.completions.create(**kwargs),
                    timeout=call_timeout,
                )
                latency_sec = time.perf_counter() - t0
                ttft_sec = latency_sec

                choice = response.choices[0]
                raw_text = choice.message.content or getattr(choice.message, "reasoning_content", None) or ""

                # Strip thinking tags if present
                raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

                raw_json = None
                if raw_text:
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

                usage = response.usage
                p_tokens = usage.prompt_tokens if usage else 0
                c_tokens = usage.completion_tokens if usage else 0
                t_tokens = usage.total_tokens if usage else 0

            self._last_metrics = {
                "prompt_tokens": p_tokens,
                "input_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "output_tokens": c_tokens,
                "total_tokens": t_tokens,
                "ttft_sec": ttft_sec,
                "latency_sec": latency_sec,
                "model": model_name,
            }

            logger.info(
                f"NVIDIA NIM [{model_name}] completed in {latency_sec:.3f}s (TTFT: {ttft_sec:.3f}s, "
                f"prompt_tokens={p_tokens}, completion_tokens={c_tokens})"
            )

            return LLMResponse(
                content=raw_text,
                raw_json=raw_json,
                provider="nvidia_nim",
                model=model_name,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
                ttft_sec=ttft_sec,
                total_latency_sec=latency_sec,
            )
        except Exception as e:
            latency_sec = time.perf_counter() - t0
            logger.warning(
                f"NVIDIA NIM generation error on model '{model_name}' "
                f"after {latency_sec:.3f}s: {type(e).__name__} - {e}"
            )
            raise

    async def check_health(self) -> Dict[str, Any]:
        """Quick connectivity probe verifying credentials and endpoint latency."""
        t0 = time.perf_counter()
        if not self.api_key:
            return {
                "status": "UNCONFIGURED",
                "error": "NVIDIA_NIM_API_KEY is not set",
                "provider": "nvidia_nim",
            }
        try:
            req = LLMRequest(
                system_prompt="You are a health check agent.",
                user_prompt="Reply with: NIM_OK",
                max_tokens=10,
                response_json=False,
            )
            resp = await self.generate(req)
            elapsed = time.perf_counter() - t0
            return {
                "status": "HEALTHY",
                "provider": "nvidia_nim",
                "model": resp.model,
                "latency_sec": round(elapsed, 3),
                "ttft_sec": round(resp.ttft_sec, 3) if resp.ttft_sec else None,
                "response_sample": resp.content[:30] if resp.content else "",
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            return {
                "status": "UNHEALTHY",
                "provider": "nvidia_nim",
                "error": f"{type(e).__name__}: {str(e)}",
                "latency_sec": round(elapsed, 3),
            }
