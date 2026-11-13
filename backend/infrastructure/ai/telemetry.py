"""
AI Provider Telemetry and Observability Module.
Tracks provider selection, model usage, request latency, token consumption,
retry counts, error categories, and fallback activations without logging PII.
"""

import time
import logging
from collections import deque
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class AIOperationRecord:
    timestamp: float
    provider: str
    model: str
    task_type: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    success: bool = True
    retry_count: int = 0
    error_type: Optional[str] = None
    fallback_activated: bool = False
    fallback_reason: Optional[str] = None
    ttft_ms: Optional[float] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


class AITelemetryTracker:
    """
    In-memory, thread-safe, research-compliant telemetry tracker.
    Stores aggregated statistics and a bounded ring buffer of recent events.
    Strictly excludes candidate personally identifiable information (PII).
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._history: deque = deque(maxlen=max_history)
        self._total_requests: int = 0
        self._successful_requests: int = 0
        self._failed_requests: int = 0
        self._retries_total: int = 0
        self._fallbacks_total: int = 0
        self._tokens_prompt_total: int = 0
        self._tokens_completion_total: int = 0
        self._provider_counts: Dict[str, int] = {}
        self._model_counts: Dict[str, int] = {}
        self._task_counts: Dict[str, int] = {}
        self._latency_sum_ms: float = 0.0

    def record_inference(
        self,
        provider: str,
        model: str,
        task_type: str,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        success: bool = True,
        retry_count: int = 0,
        error_type: Optional[str] = None,
        fallback_activated: bool = False,
        fallback_reason: Optional[str] = None,
        ttft_ms: Optional[float] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> AIOperationRecord:
        record = AIOperationRecord(
            timestamp=time.time(),
            provider=provider,
            model=model,
            task_type=task_type,
            latency_ms=round(latency_ms, 2),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens or (prompt_tokens + completion_tokens),
            success=success,
            retry_count=retry_count,
            error_type=error_type,
            fallback_activated=fallback_activated,
            fallback_reason=fallback_reason,
            ttft_ms=round(ttft_ms, 2) if ttft_ms is not None else None,
            extra_metadata=extra_metadata or {},
        )

        self._history.append(record)
        self._total_requests += 1
        if success:
            self._successful_requests += 1
        else:
            self._failed_requests += 1

        self._retries_total += retry_count
        if fallback_activated:
            self._fallbacks_total += 1

        self._tokens_prompt_total += prompt_tokens
        self._tokens_completion_total += completion_tokens
        self._latency_sum_ms += latency_ms

        self._provider_counts[provider] = self._provider_counts.get(provider, 0) + 1
        self._model_counts[model] = self._model_counts.get(model, 0) + 1
        self._task_counts[task_type] = self._task_counts.get(task_type, 0) + 1

        logger.debug(
            f"AI Telemetry: [{provider}:{model}] task={task_type} latency={latency_ms:.1f}ms "
            f"tokens={total_tokens} success={success} fallback={fallback_activated}"
        )
        return record

    def record_fallback(
        self,
        primary_provider: str,
        fallback_provider: str,
        task_type: str,
        reason: str,
        latency_ms: float = 0.0,
    ):
        """Records an explicit fallback activation from primary to secondary/deterministic."""
        return self.record_inference(
            provider=fallback_provider,
            model=f"fallback_from_{primary_provider}",
            task_type=task_type,
            latency_ms=latency_ms,
            success=True,
            fallback_activated=True,
            fallback_reason=reason,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Returns consolidated metrics across all recorded operations."""
        avg_latency = (
            round(self._latency_sum_ms / self._total_requests, 2)
            if self._total_requests > 0
            else 0.0
        )
        success_rate = (
            round((self._successful_requests / self._total_requests) * 100, 2)
            if self._total_requests > 0
            else 100.0
        )
        fallback_rate = (
            round((self._fallbacks_total / self._total_requests) * 100, 2)
            if self._total_requests > 0
            else 0.0
        )

        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "success_rate_percent": success_rate,
            "total_retries": self._retries_total,
            "total_fallbacks": self._fallbacks_total,
            "fallback_rate_percent": fallback_rate,
            "average_latency_ms": avg_latency,
            "total_prompt_tokens": self._tokens_prompt_total,
            "total_completion_tokens": self._tokens_completion_total,
            "total_tokens": self._tokens_prompt_total + self._tokens_completion_total,
            "provider_distribution": dict(self._provider_counts),
            "model_distribution": dict(self._model_counts),
            "task_distribution": dict(self._task_counts),
            "tracked_events_in_memory": len(self._history),
        }

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent telemetry records formatted as dicts, newest first."""
        events = list(self._history)
        events.reverse()
        return [asdict(ev) for ev in events[:limit]]

    def reset(self):
        """Resets all metrics (primarily for unit test isolation)."""
        self._history.clear()
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._retries_total = 0
        self._fallbacks_total = 0
        self._tokens_prompt_total = 0
        self._tokens_completion_total = 0
        self._provider_counts.clear()
        self._model_counts.clear()
        self._task_counts.clear()
        self._latency_sum_ms = 0.0


# Global singleton instance
ai_telemetry = AITelemetryTracker()

