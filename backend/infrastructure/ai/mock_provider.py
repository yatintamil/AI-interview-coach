"""
Mock LLM & Embedding Providers for unit testing and offline development.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from backend.domain.ai.interfaces import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    EmbeddingProvider,
)

logger = logging.getLogger(__name__)


class MockLLMProvider:
    """Configurable Mock LLM Provider that returns pre-seeded or sensible mock JSON responses."""

    def __init__(self, default_response: Optional[Dict[str, Any]] = None):
        self.provider_name = "mock"
        self.default_response = default_response or {
            "full_name": "Candidate Profile",
            "email": "candidate@example.com",
            "skills": [{"name": "Software Engineering", "category": "Technical", "years_of_experience": 2.0}],
            "experience": [],
            "education": [],
            "projects": [],
            "technologies": ["Software Engineering"],
            "domains": ["Engineering Systems"],
            "question": "Can you walk through an engineering project you built, explaining the core architectural trade-offs you evaluated?",
            "category": "technical",
            "topic": "System Architecture & Trade-offs",
            "difficulty": "medium",
            "resume_evidence": "Grounding in candidate verified engineering background.",
            "expected_concepts": ["system architecture", "trade-offs", "operational constraints"],
            "overall_score": 7.5,
            "correctness": 7.5,
            "completeness": 7.5,
            "relevance": 8.0,
            "technical_depth": 7.0,
            "reasoning": 7.5,
            "strengths": ["Structured explanation of system constraints."],
            "weaknesses": ["Could expand more on edge-case failure modes."],
            "missing_concepts": ["failure modes"],
            "evidence": [
                {
                    "claim": "Candidate understands core architectural trade-offs",
                    "basis": "Candidate provided structured breakdown of system components"
                }
            ],
            "recommendations": ["Elaborate on edge case resilience in high-scale scenarios."]
        }
        self.custom_responses: List[Dict[str, Any]] = []

    def set_next_response(self, response_data: Dict[str, Any]):
        """Queue a specific response for the next call."""
        self.custom_responses.append(response_data)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if self.custom_responses:
            data = self.custom_responses.pop(0)
            if isinstance(data, str):
                content_str = data
                raw_json = None
            else:
                content_str = json.dumps(data)
                raw_json = data
        elif not request.response_json:
            # Context-aware conversational response for chat/coaching when structured JSON is not requested
            user_text = (request.user_prompt or "").strip()
            text_lower = user_text.lower()

            if any(k in text_lower for k in ["initiate", "start session", "opening lesson"]):
                content_str = (
                    "### 💡 Welcome to the AI Coaching Studio\n\n"
                    "Today we are mastering **API Idempotency & Concurrency Control**.\n\n"
                    "🎯 **Our Learning Objective**: Master idempotency keys, duplicate request mitigation, and concurrent write safety.\n\n"
                    "Here is our roadmap:\n"
                    "1. **Core Fundamentals & Terminology** — Establishing solid conceptual grounding.\n"
                    "2. **Real-World Architectural Worked Example** — Reasoning through trade-offs.\n"
                    "3. **Understanding Check** — Testing your grasp with a focused scenario.\n"
                    "4. **Guided Practice & Unseen Transfer Challenge** — Proving independent mastery.\n\n"
                    "In distributed systems, operations are **Idempotent** if making the same request multiple times produces the identical side-effects as making it once: `f(f(x)) = f(x)`.\n\n"
                    "How would you like to proceed? Feel free to ask: *'Explain this in simple terms'* or *'Show me how to implement it'*."
                )
            elif any(k in text_lower for k in ["from beginning", "from first", "from the beginning", "start from", "start over", "from first in detail"]):
                content_str = (
                    "### 📘 Teaching from Prerequisites: Why Idempotency Exists\n\n"
                    "Let's start from the very foundation before looking at any complex architecture.\n\n"
                    "**1. The Fundamental Network Problem**\n"
                    "When a client talks to a server across a network, every request can experience three outcomes:\n"
                    "- **Success**: The request arrived, executed, and the response returned.\n"
                    "- **Explicit Failure**: The server actively rejected the request (e.g. 400 Bad Request).\n"
                    "- **Network Timeout / Uncertainty**: The client sent the request, but the connection dropped before a response was received.\n\n"
                    "In this third case, the client cannot tell whether the server crashed *before* processing, or completed the work right before the network dropped.\n\n"
                    "**2. What Idempotency Guarantees**\n"
                    "An operation is **idempotent** if running it multiple times produces the exact same outcome as running it once (`f(f(x)) = f(x)`). "
                    "This invariant allows the client to safely retry failed or timed-out requests without causing duplicate charges or corrupting data.\n\n"
                    "Does this core problem make sense to you so far?"
                )
            elif any(k in text_lower for k in ["simple terms", "simple", "beginner", "eli5", "plain english"]):
                content_str = (
                    "### 💡 Idempotency in Simple Terms\n\n"
                    "Think of pushing an elevator button. If you push the 'Floor 5' button once, the elevator heads to Floor 5. "
                    "If you impatiently mash the button 10 more times, the elevator still goes to Floor 5—it doesn't go 10 times higher or charge you 10 elevator rides.\n\n"
                    "In APIs, that is idempotency: no matter how many times a duplicate request arrives, the end state is identical.\n\n"
                    "An **Idempotency Key** is simply a unique tracking token (like a receipt number) sent with the request so the server recognizes duplicate attempts."
                )
            elif any(k in text_lower for k in ["payment example", "payment", "detailed payment", "worked example"]):
                content_str = (
                    "### 💳 Detailed Payment Processing Example\n\n"
                    "Let's walk through an e-commerce checkout charging a customer $100:\n\n"
                    "1. **Client Action**: The checkout app generates a unique UUID `Idempotency-Key: pay_abc123` and sends `POST /api/v1/payments`.\n"
                    "2. **Atomic Lock**: The payment gateway attempts `SET idemp:pay_abc123 'IN_PROGRESS' NX EX 120`. "
                    "Because it is the first time, the lock succeeds.\n"
                    "3. **Execute Charge**: The server invokes Stripe/processor and debits $100.\n"
                    "4. **Persist Result**: The server stores `{status: 'succeeded', charge_id: 'ch_999'}` into the idempotency store with a 24-hour TTL.\n"
                    "5. **Network Retry**: If the customer's phone lost signal and retries with the same `pay_abc123`, the server sees the key is already resolved, skips the payment processor, and instantly returns the cached `ch_999` receipt without double-charging."
                )
            elif any(k in text_lower for k in ["simultaneously", "race condition", "two requests", "concurrent", "at the same time"]):
                content_str = (
                    "### ⚡ What Happens When Two Requests Arrive Simultaneously?\n\n"
                    "This is the critical race condition candidates must address in system design interviews.\n\n"
                    "Imagine Request A and Request B carry the exact same `Idempotency-Key: pay_abc123` and hit two different load-balanced servers at the exact same millisecond:\n\n"
                    "- **Naive Check-Then-Insert (BROKEN)**:\n"
                    "  Both servers run `SELECT * FROM payments WHERE key = 'pay_abc123'`. "
                    "  Neither finds a record yet. Both proceed to charge the card twice!\n\n"
                    "- **The Atomic Lock Solution (CORRECT)**:\n"
                    "  Both servers execute an atomic compare-and-swap (e.g. Redis `SET NX` or SQL `INSERT ... ON CONFLICT DO NOTHING`).\n"
                    "  - Exactly **one** server wins the lock (returns True).\n"
                    "  - The second server fails to acquire the lock (returns False) and immediately responds with **HTTP 409 Conflict** (`Request currently processing`).\n\n"
                    "The atomic lock guarantees mutual exclusion across distributed nodes."
                )
            elif any(k in text_lower for k in ["implement", "code", "implementation", "show me how"]):
                content_str = (
                    "### 🛠️ Production Python / Redis Implementation\n\n"
                    "```python\n"
                    "import json\n"
                    "from fastapi import HTTPException, status\n\n"
                    "async def process_idempotent_payment(idempotency_key: str, amount_cents: int, db, redis):\n"
                    "    redis_key = f'idemp:{idempotency_key}'\n"
                    "    \n"
                    "    # 1. Attempt atomic lock claim with 2-minute timeout\n"
                    "    acquired = await redis.set(redis_key, 'IN_PROGRESS', nx=True, ex=120)\n"
                    "    if not acquired:\n"
                    "        cached_val = await redis.get(redis_key)\n"
                    "        if cached_val == 'IN_PROGRESS':\n"
                    "            raise HTTPException(\n"
                    "                status_code=status.HTTP_409_CONFLICT,\n"
                    "                detail='A request with this idempotency key is already in progress.'\n"
                    "            )\n"
                    "        # Return cached completed response\n"
                    "        return json.loads(cached_val)\n"
                    "    \n"
                    "    try:\n"
                    "        # 2. Execute critical financial mutation\n"
                    "        charge_result = await db.execute_charge(amount_cents=amount_cents)\n"
                    "        \n"
                    "        # 3. Store completed payload with 24-hour TTL\n"
                    "        await redis.set(redis_key, json.dumps(charge_result), ex=86400)\n"
                    "        return charge_result\n"
                    "    except Exception as exc:\n"
                    "        # On infrastructure error, release lock to allow client retry\n"
                    "        await redis.delete(redis_key)\n"
                    "        raise exc\n"
                    "```"
                )
            elif any(k in text_lower for k in ["check", "understood", "quiz", "understanding", "test me"]):
                content_str = (
                    "### ❓ Conceptual Understanding Check\n\n"
                    "Let's check your understanding based on what we've covered regarding simultaneous requests and atomic locks:\n\n"
                    "> **Scenario**: Server A acquired the atomic lock `idemp:pay_123` and sent a $100 charge to Stripe. "
                    "Stripe successfully processed the charge, but right before Server A could store the completed payload in Redis, "
                    "Server A suffered a hardware kernel panic and rebooted.\n\n"
                    "**Question**: When the client retries 10 seconds later, what happens with the lock TTL, and how should your architecture "
                    "reconcile with Stripe to avoid double-charging the customer? What invariant protects the customer?"
                )
            else:
                content_str = (
                    f"### 🎯 Deepening Your Architectural Understanding\n\n"
                    f"Regarding your inquiry: *\"{user_text[:100]}\"*\n\n"
                    "In distributed systems engineering, building robust APIs requires evaluating both the **happy path** and the **failure boundaries**:\n\n"
                    "1. **Client Isolation**: How the client generates unique request identity (UUIDv4) and handles exponential retry backoff with jitter.\n"
                    "2. **State Storage Trade-offs**: Whether you store idempotency records in Redis (fast in-memory with TTL) vs the primary database (strict ACID transaction alongside business data).\n\n"
                    "Which aspect would you like to explore next? We can walk through code implementation, dive into concurrent race conditions, or check your understanding!"
                )
            raw_json = None
        else:
            data = self.default_response
            content_str = json.dumps(data)
            raw_json = data

        return LLMResponse(
            content=content_str,
            raw_json=raw_json,
            provider="mock",
            model=request.model or "mock-model",
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
        )


class MockEmbeddingProvider:
    """Mock Vector Embedding Provider returning fixed-dimension normalized zero/one vectors."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension
        self.provider_name = "mock"

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text_sync(self, text: str) -> List[float]:
        import hashlib
        h = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        vec = [(float((h >> (i % 32)) & 1) * 0.1) for i in range(self._dimension)]
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [round(x / norm, 6) for x in vec]

    async def embed_text(self, text: str) -> List[float]:
        return self.embed_text_sync(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text_sync(t) for t in texts]
