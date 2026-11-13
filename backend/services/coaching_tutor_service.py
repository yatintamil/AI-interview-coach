"""
Conversational AI Coaching Tutor Service.
Coordinates proactive pedagogical AI tutoring across Phases A through F:
- Phase A: Identify What to Learn & Why It Matters
- Phase B: Explain Fundamentals (Plain Language, Terminology, Code Example, Common Mistakes)
- Phase C: Demonstrate Worked Example (Engineering Reasoning, Trade-offs)
- Phase D: Check Understanding (Focused Question, Addressing Misconceptions)
- Phase E: Guided Practice (Progressive Exercises, Hints without Spoilers)
- Phase F: Unseen Transfer Challenge & Independent Practice (Targeting L5 Independent Transfer)
"""

import re
import uuid
import time
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository
from backend.repositories.interview_repository import (
    InterviewSessionRepository,
    QuestionRepository,
)
from backend.repositories.transfer_diagnosis_repository import TransferDiagnosisRepository
from backend.repositories.transfer_task_repository import TransferAttemptRepository
from backend.repositories.roadmap_repository import RoadmapRepository
from backend.schemas.chat import (
    ConversationDetailDTO,
    ConversationMessageDTO,
    SendMessageResponse,
    ChatRole,
    ChatIntent,
    InitiateCoachingRequest,
    InitiateCoachingResponse,
)
from backend.infrastructure.ai.factory import get_llm_provider
from backend.domain.ai.interfaces import LLMRequest
from ai.config import ai_settings
from ai.transfer_engine.task_generator import TransferTaskGenerator
from ai.transfer_engine.schemas import TransferGenerationRequest
from backend.domain.transfer.taxonomy import TransferLevel

logger = logging.getLogger(__name__)

# Standard Competency Knowledge Catalog for Curated Pedagogical Fallbacks
COMPETENCY_CATALOG: Dict[str, Dict[str, Any]] = {
    "api_idempotency": {
        "title": "API Idempotency & Concurrency Control",
        "objective": "Master idempotency keys, duplicate request mitigation, and concurrent write safety",
        "why_it_matters": "In high-throughput distributed architectures, network retries and concurrent client requests can cause duplicate payments, inventory corruption, or race conditions unless protected by strict idempotency invariants.",
        "fundamentals": """### 💡 Core Concept: What is Idempotency?
In HTTP and distributed APIs, an operation is **idempotent** if making the same request multiple times produces the exact same side-effects as making it once:
`f(f(x)) = f(x)`

While `GET`, `PUT`, and `DELETE` are semantically idempotent by HTTP specification, `POST` requests (like creating a payment or placing an order) are not. When a client encounters a network timeout, it cannot tell if the request failed before reaching the server, or succeeded right before the response was lost. Retrying without safeguards causes duplicate charges.

### 🔑 Essential Terminology
1. **Idempotency Key**: A unique client-generated UUID (e.g., `Idempotency-Key: 9b1deb4d...`) accompanying the request header.
2. **At-Least-Once Delivery**: Message queues and network retries guarantee delivery, but may deliver duplicates.
3. **Atomic Compare-and-Swap (CAS)**: Ensuring only one execution thread claims a key before state changes.
4. **Result Storage**: Persisting the original HTTP status code and response body alongside the key so duplicate requests return the identical response without re-executing business logic.

### 🛠️ Production Architecture Pattern
```text
Client Request (with Idempotency-Key: X)
      │
      ▼
API Gateway / App Server
      │
      ├── 1. Atomic Claim (SET NX key:X EX 120s in Redis or INSERT into idempotency_keys)
      │      ├── Already exists & completed? ──► Return cached HTTP response immediately (200/201)
      │      └── In-flight lock held? ──────────► Return 409 Conflict ("Request in progress")
      │
      ├── 2. Execute Core Business Logic (e.g., Charge credit card, update DB ledger)
      │
      └── 3. Update Key Record with final response payload & TTL
             └── Return response to client
```

### ⚠️ Common Interview Mistakes
- **Relying solely on database unique constraints**: A unique constraint protects the DB write, but leaves the client with an unhandled 500/503 error instead of a clean, cached response.
- **Ignoring in-flight concurrency**: If two identical requests hit the server within 2ms of each other, naive check-then-insert code without atomic locking suffers a race condition.
- **Permanent storage without TTL**: Idempotency records should have a realistic expiration window (e.g., 24–72 hours).""",
    },
    "distributed_caching": {
        "title": "Distributed Caching & Partitioning",
        "objective": "Master cache stampede mitigation, eviction policies, and consistent hash rings",
        "why_it_matters": "When scaling read-heavy services to millions of queries per second, caching is critical. But naive caching causes cascading database outages during cache expirations or node rebalances.",
        "fundamentals": """### 💡 Core Concept: Caching Invariants
A cache is not merely a key-value store; it is a latency and throughput buffer governed by strict consistency and eviction guarantees.

### 🔑 Essential Terminology
1. **Consistent Hashing**: A distributed hash ring with virtual nodes ensuring that adding or removing a cache node only remaps `K/N` keys rather than invalidating the entire cache.
2. **Cache Stampede (Thundering Herd)**: When a popular key expires, hundreds of concurrent requests simultaneously miss the cache and overwhelm the primary database.
3. **Mutex / Distributed Lock Stampede Defense**: Only the first worker to observe a cache miss acquires an in-memory or distributed lock to query the DB and repopulate the cache; other workers wait or receive stale data.
4. **Probabilistic Early Expiration (XFetch)**: Pre-emptively refreshing a key before its TTL expires based on request probability: `time() - delta * beta * ln(rand()) > expiry`.

### ⚠️ Common Interview Mistakes
- **Forgetting Virtual Nodes**: Basic consistent hashing creates non-uniform hotspots unless each physical server maps to 100+ virtual tokens across the ring.
- **Cache-Aside race conditions**: Updating the database without invalidating the cache, or invalidating before the database transaction commits.""",
    },
    "database_concurrency": {
        "title": "Database Concurrency & Isolation Levels",
        "objective": "Master ACID isolation levels, phantom reads, and optimistic vs pessimistic locking",
        "why_it_matters": "In multi-tenant systems, concurrent transactions competing for shared rows will corrupt data without rigorous locking or MVCC isolation controls.",
        "fundamentals": """### 💡 Core Concept: Isolation vs Throughput
ANSI SQL defines four isolation levels: Read Uncommitted, Read Committed, Repeatable Read, and Serializable. Each trades performance for consistency guarantees.

### 🔑 Essential Terminology
1. **Dirty Read**: Reading uncommitted changes made by another transaction.
2. **Non-Repeatable Read**: Re-reading a row within the same transaction and seeing modified values because another transaction committed.
3. **Phantom Read**: Re-running a range query and discovering new rows inserted by another committed transaction.
4. **Optimistic Concurrency Control (OCC)**: Using a `version` column: `UPDATE items SET qty = qty - 1, version = version + 1 WHERE id = 1 AND version = 5;`. If rows affected == 0, abort and retry.
5. **Pessimistic Locking**: `SELECT ... FOR UPDATE` locks rows until transaction completion.

### ⚠️ Common Interview Mistakes
- **Assuming Repeatable Read prevents Phantom Reads**: In standard Postgres/MySQL InnoDB, Repeatable Read uses MVCC snapshots for plain SELECTs, but locking queries (`SELECT FOR UPDATE`) can still encounter phantoms unless Serializable or Next-Key locking is active.
- **Using Pessimistic Locks in high-contention read workflows**: Causes severe lock queuing, latency spikes, and deadlocks.""",
    },
    "resilience_patterns": {
        "title": "Circuit Breaking & Backpressure Resilience",
        "objective": "Master fail-fast thresholds, exponential backoff with jitter, and bulkhead isolation",
        "why_it_matters": "Downstream service latency is infectious. A single slow dependency will exhaust server thread pools across the entire fleet within seconds unless isolated.",
        "fundamentals": """### 💡 Core Concept: Fail-Fast & Bounded Latency
The primary goal of resilience engineering is preventing localized faults from causing cascading systemic collapse.

### 🔑 Essential Terminology
1. **Circuit Breaker (Closed, Open, Half-Open)**: Monitors error/timeout rates. Trips to Open (fails fast immediately) when threshold is exceeded, preventing thread exhaustion.
2. **Bulkhead Pattern**: Partitioning thread pools or connection pools so that a failure in one service (e.g., recommendations) cannot consume resources reserved for critical paths (e.g., checkout).
3. **Exponential Backoff with Full Jitter**: Retrying after `min(max_backoff, base * 2^attempt) * random()`. Adding random jitter prevents synchronized retry storms.
4. **Load Shedding & Backpressure**: Returning HTTP 429/503 when queue depth exceeds safety margins before worker threads block.""",
    },
    "rate_limiting": {
        "title": "Distributed Rate Limiting & Throttling",
        "objective": "Master token bucket algorithms, sliding window logs, and atomic Redis Lua evaluation",
        "why_it_matters": "APIs face malicious scraping, noisy-neighbor tenant abuse, and cascading traffic surges unless protected by high-precision, low-overhead distributed rate limiters.",
        "fundamentals": """### 💡 Core Concept: Rate Limiting Algorithms
Rate limiters protect downstream service capacity by enforcing request budgets over defined temporal windows.

### 🔑 Essential Terminology
1. **Token Bucket**: Tokens accumulate at a fixed refill rate up to bucket capacity; each request consumes 1 token. Supports controlled bursts.
2. **Leaky Bucket**: Requests queue into a FIFO buffer and drain at a constant continuous rate. Smooths bursty traffic into steady egress.
3. **Sliding Window Counter**: Interpolates counts from the previous window with current window elapsed fraction to prevent boundary 2x bursts.
4. **Atomic Redis Lua**: Executing key lookup, expiration checks, and token decrement in a single atomic Lua script to prevent concurrency race conditions.""",
    },
    "system_decomposition": {
        "title": "Microservices & Event-Driven Decoupling",
        "objective": "Master bounded contexts, Transactional Outbox, and Saga choreography vs orchestration",
        "why_it_matters": "Distributed architectures face split-brain consistency bugs and distributed 2PC blocking when decomposing monoliths without transactional messaging invariants.",
        "fundamentals": """### 💡 Core Concept: Eventual Consistency & Decoupling
Services must encapsulate private state while communicating through immutable asynchronous domain events without distributed database locks.

### 🔑 Essential Terminology
1. **Transactional Outbox**: Persisting domain changes and event records in the same ACID database transaction, then tailing via CDC (Debezium) to prevent dual-write loss.
2. **Saga Pattern**: Coordinating long-running transactions across distributed services using compensating rollback transactions.
3. **Idempotent Consumer**: Consumers deduplicate message delivery using persistent message UUID ledgers.""",
    },
    "algorithmic_optimization": {
        "title": "Data Structure Selection & Amortized Complexity",
        "objective": "Master cache locality, amortized complexity proofs, and optimal data structure trade-offs",
        "why_it_matters": "High-throughput systems bottleneck on CPU memory bus and cache misses unless memory layout and algorithmic complexity are rigorously optimized.",
        "fundamentals": """### 💡 Core Concept: Asymptotic vs Hardware Reality
Big-O measures asymptotic scaling, but memory hierarchy (L1/L2/L3 cache lines) and contiguous memory access often dominate real-world latency.

### 🔑 Essential Terminology
1. **Amortized Analysis**: Evaluating average operation cost over a sequence of operations (e.g., dynamic array doubling).
2. **Cache Locality**: Structuring data contiguously in memory to maximize CPU pre-fetching and minimize cache line invalidations.
3. **Skip Lists & Balanced Trees**: Probabilistic vs deterministic logarithmic search and insertion trade-offs.""",
    },
    "memory_management": {
        "title": "Memory Architecture & Resource Lifecycle",
        "objective": "Master off-heap allocation, GC pause mitigation, and resource lifecycle safety",
        "why_it_matters": "Garbage collection stop-the-world pauses and memory fragmentation cause catastrophic p99 latency spikes in high-scale services.",
        "fundamentals": """### 💡 Core Concept: Memory Lifecycles
Managing memory boundaries between managed heaps and native buffers to maintain predictable execution latency.

### 🔑 Essential Terminology
1. **Generational GC**: Exploiting the weak generational hypothesis (most objects die young).
2. **Off-Heap Memory**: Allocating direct memory buffers outside the garbage collector's domain to prevent GC pause overhead.
3. **Object Pooling**: Reusing allocated instances to eliminate allocation churn in hot loops.""",
    },
    "api_security": {
        "title": "API Security & Multi-Tenant Authorization",
        "objective": "Master JWT verification, RBAC/ABAC authorization models, and timing attack prevention",
        "why_it_matters": "Data exposure and broken object-level authorization (BOLA) represent the #1 vulnerability in modern distributed API architectures.",
        "fundamentals": """### 💡 Core Concept: Zero Trust & Principle of Least Privilege
Never trust incoming requests implicitly; verify identity cryptographically and enforce granular row-level authorization on every data path.

### 🔑 Essential Terminology
1. **Stateless JWT vs Revocable Sessions**: Cryptographic token signature verification vs distributed Redis token revocation lists.
2. **BOLA / IDOR Defense**: Enforcing that the authenticated tenant context matches the requested entity's tenant_id at the DB query level.
3. **Constant-Time Comparison**: Preventing cryptographic timing side-channel attacks during secret or HMAC validation.""",
    },
}


class PedagogicalIntent:
    TEACH_FROM_BEGINNING = "TEACH_FROM_BEGINNING"
    EXPLAIN_THOROUGHLY = "EXPLAIN_THOROUGHLY"
    SIMPLIFY_BEGINNER = "SIMPLIFY_BEGINNER"
    CONCURRENCY_RACE_CONDITIONS = "CONCURRENCY_RACE_CONDITIONS"
    SHOW_IMPLEMENTATION = "SHOW_IMPLEMENTATION"
    WORKED_EXAMPLE = "WORKED_EXAMPLE"
    EXPLAIN_SPECIFIC_TERM = "EXPLAIN_SPECIFIC_TERM"
    CHECK_UNDERSTANDING = "CHECK_UNDERSTANDING"
    CLARIFY_ANSWER = "CLARIFY_ANSWER"
    GUIDED_PRACTICE = "GUIDED_PRACTICE"
    TRANSFER_CHALLENGE = "TRANSFER_CHALLENGE"
    HINT_REQUEST = "HINT_REQUEST"
    GENERAL_COACHING = "GENERAL_COACHING"
    FOUNDATIONAL_EXPLANATION = "FOUNDATIONAL_EXPLANATION"
    CONCEPT_CLARIFICATION = "CONCEPT_CLARIFICATION"
    MISCONCEPTION_CORRECTION = "MISCONCEPTION_CORRECTION"
    TARGETED_REMEDIATION = "TARGETED_REMEDIATION"
    INDEPENDENT_TRANSFER = "INDEPENDENT_TRANSFER"
    NEXT_COMPETENCY = "NEXT_COMPETENCY"
    WHY_QUESTION = "WHY_QUESTION"
    HOW_QUESTION = "HOW_QUESTION"
    COMPARISON = "COMPARISON"
    WHY_WRONG = "WHY_WRONG"
    MORE_DETAIL = "MORE_DETAIL"


class TeachingStage:
    STAGE_1_PREREQUISITES = "STAGE_1_PREREQUISITES"
    STAGE_2_CORE_MECHANICS = "STAGE_2_CORE_MECHANICS"
    STAGE_2_SIMPLIFIED_INTUITION = "STAGE_2_SIMPLIFIED_INTUITION"
    STAGE_3_WORKED_EXAMPLE = "STAGE_3_WORKED_EXAMPLE"
    STAGE_4_CONCURRENCY_DEEP_DIVE = "STAGE_4_CONCURRENCY_DEEP_DIVE"
    STAGE_5_IMPLEMENTATION = "STAGE_5_IMPLEMENTATION"
    STAGE_6_UNDERSTANDING_CHECK = "STAGE_6_UNDERSTANDING_CHECK"
    STAGE_7_GUIDED_PRACTICE = "STAGE_7_GUIDED_PRACTICE"
    STAGE_8_TRANSFER_CHALLENGE = "STAGE_8_TRANSFER_CHALLENGE"


class CognitiveUnderstandingType:
    MEMORIZED_DEFINITION = "MEMORIZED_DEFINITION"
    GENUINE_UNDERSTANDING = "GENUINE_UNDERSTANDING"
    CORRECT_REASONING = "CORRECT_REASONING"
    INCORRECT_REASONING = "INCORRECT_REASONING"
    MISCONCEPTION = "MISCONCEPTION"
    CONCEPT_APPLICATION = "CONCEPT_APPLICATION"
    TRADE_OFF_ANALYSIS = "TRADE_OFF_ANALYSIS"


class AdaptiveTeachingAction:
    DEEPEN_APPLICATION = "DEEPEN_APPLICATION"
    APPLICATION_CHECK = "APPLICATION_CHECK"
    TARGETED_MISCONCEPTION_CORRECTION = "TARGETED_MISCONCEPTION_CORRECTION"
    FOUNDATIONAL_REMEDIATION = "FOUNDATIONAL_REMEDIATION"
    FADE_SCAFFOLD_TO_PRACTICE = "FADE_SCAFFOLD_TO_PRACTICE"
    ADVANCE_TO_INDEPENDENT_TRANSFER = "ADVANCE_TO_INDEPENDENT_TRANSFER"


def analyze_cognitive_understanding(
    user_message: str,
    focus_skill: str,
    last_question: Optional[str] = None,
    failure_count: int = 0,
) -> Dict[str, Any]:
    """
    Evaluates candidate conversational answers along 7 cognitive understanding dimensions:
    - Memorized definitions
    - Genuine conceptual understanding
    - Correct reasoning
    - Incorrect reasoning
    - Misconceptions
    - Ability to apply a concept
    - Ability to explain trade-offs

    Determines the appropriate adaptive teaching decision:
    - Memorized answers -> application checks
    - Misconceptions -> targeted correction
    - Repeated failures (>=2) -> foundational remediation
    - Correct understanding -> deeper application
    - Practical application & trade-offs -> fade scaffold / advance to transfer
    """
    text = user_message.lower().strip()
    detected_misconceptions: List[str] = []
    demonstrated_invariants: List[str] = []

    # 1. Misconception Detection Patterns (Specific, high-severity interview traps)
    misconception_traps = {
        "unique_constraint_without_app_lock": [
            r"\b(only|just|solely)\s+(a\s+)?(db|database)?\s*unique\s+constraint\b",
            r"\bunique constraint (handles|solves|prevents) (it|concurrency|everything) without (any\s+)?locks?\b",
            r"\b(we don't need locks|no locks needed).*unique constraint\b",
            r"\bunique constraint alone\b",
        ],
        "lock_without_ttl_or_expiration": [
            r"\block without (ttl|expiration|timeout|expiring)\b",
            r"\bpermanent lock\b",
            r"\block indefinitely\b",
            r"\block without expiration\b",
            r"\bignore cache stampedes?\b",
        ],
        "cache_invalidation_before_db_commit": [
            r"\b(invalidate|delete|clear) (the )?cache before (updating|writing to|committing) (the )?(db|database)\b",
            r"\bcache invalidation before db\b",
        ],
        "repeatable_read_prevents_phantoms": [
            r"\brepeatable read (prevents|stops|eliminates) (all )?phantom reads?\b",
            r"\brepeatable read prevents phantoms in all engines\b",
        ],
        "blind_infinite_retries": [
            r"\b(infinite|endless) retries\b",
            r"\bretry immediately without (backoff|jitter|delay)\b",
            r"\bwhile true.*retry\b",
        ],
        "distributed_transaction_over_external_http": [
            r"\bwrap (the )?external (http|api|stripe|payment) (call|request) in (a |the )?(local |db )?transaction\b",
            r"\bdb transaction wraps external\b",
        ],
        "single_threaded_redis_no_lock_needed": [
            r"\bsingle-?threaded.*no (distributed )?locks? needed\b",
            r"\bredis is single-?threaded so we don't need\b",
        ],
    }

    for trap_name, patterns in misconception_traps.items():
        if any(re.search(p, text) for p in patterns):
            detected_misconceptions.append(trap_name)

    # 2. Trade-off Analysis Patterns
    trade_off_indicators = [
        r"\b(trade-?offs?|trading off|on the other hand|in exchange for|trades latency for|at the cost of)\b",
        r"\b(cache-aside vs write-through|write-through vs cache-aside)\b",
        r"\b(optimistic vs pessimistic|pessimistic vs optimistic)\b",
        r"\b(higher latency.*consistency|consistency.*latency)\b",
        r"\b(throughput vs latency|latency vs throughput)\b",
        r"\b(availability vs consistency|consistency vs availability)\b",
    ]
    is_trade_off = any(re.search(p, text) for p in trade_off_indicators)

    # 3. Practical Concept Application Patterns
    application_indicators = [
        r"\b(redis\.set|set nx|setnx|ex=|px=)\b",
        r"\b(http 409|409 conflict|status 409)\b",
        r"\b(select.*for update|version = version \+ 1)\b",
        r"\b(virtual nodes?|token ring|hash ring with virtual)\b",
        r"\b(idempotency-key header|x-idempotency-key)\b",
        r"\b(half-open|closed, open, half-open)\b",
        r"\b(exponential backoff with (full )?jitter)\b",
        r"\b(write-ahead log|wal|two-phase commit|2pc|saga pattern)\b",
    ]
    is_application = any(re.search(p, text) for p in application_indicators)

    # 4. Memorized Definition Patterns (Reciting dictionary definitions without causal mechanics)
    memorized_indicators = [
        r"\bidempotency (is|means|defined as)\b",
        r"\bf\(f\(x\)\)\s*=\s*f\(x\)\b",
        r"\bproducing the same result (regardless|no matter)\b",
        r"\bconsistent hashing is a (distributed )?hashing (algorithm|technique|scheme)\b",
        r"\ba? ?circuit breaker is a (design )?pattern that (stops|prevents) (cascading )?failures\b",
        r"\bacid stands for atomicity,? consistency,? isolation,? (and )?durability\b",
    ]
    has_memorized_phrasing = any(re.search(p, text) for p in memorized_indicators)

    # Causal reasoning indicators: "because", "since", "due to", "in order to", "as a result", "leads to", "prevents"
    causal_indicators = [
        r"\b(because|since|due to|in order to|as a result|so that|the reason is)\b",
        r"\b(timeout.*uncertainty|uncertain if.*committed|at-least-once)\b",
        r"\b(concurrent.*serialize|race condition.*atomic|prevent.*double)\b",
    ]
    has_causality = any(re.search(p, text) for p in causal_indicators)

    # 5. Flawed / Incorrect Reasoning Indicators (non-standard flaws)
    incorrect_reasoning_indicators = [
        r"\b(increase (the )?timeout to 10 minutes|timeout.*10 minutes)\b",
        r"\b(store.*only in (the )?(browser|cookie|localstorage))\b",
        r"\b(just retry in the background without checking)\b",
        r"\b(ignore the error and proceed)\b",
    ]
    is_flawed_reasoning = any(re.search(p, text) for p in incorrect_reasoning_indicators)

    # Determine Classification
    if detected_misconceptions:
        understanding_type = CognitiveUnderstandingType.MISCONCEPTION
        confidence = 0.95
        rationale = f"Detected architectural misconception trap: {', '.join(detected_misconceptions)}."
    elif is_flawed_reasoning:
        understanding_type = CognitiveUnderstandingType.INCORRECT_REASONING
        confidence = 0.88
        rationale = "Candidate presented flawed technical reasoning that fails under production failure conditions."
    elif has_memorized_phrasing and not has_causality and not is_application:
        understanding_type = CognitiveUnderstandingType.MEMORIZED_DEFINITION
        confidence = 0.92
        rationale = "Candidate stated a formal textbook definition without demonstrating causal mechanics or operational execution."
    elif is_trade_off:
        understanding_type = CognitiveUnderstandingType.TRADE_OFF_ANALYSIS
        confidence = 0.90
        rationale = "Candidate articulated architectural trade-offs between competing operational dimensions."
    elif is_application:
        understanding_type = CognitiveUnderstandingType.CONCEPT_APPLICATION
        confidence = 0.92
        rationale = "Candidate demonstrated concrete operational implementation and system interaction patterns."
    elif has_causality and ("prevent" in text or "serialize" in text or "retry" in text or "atomic" in text or "lock" in text or "miss" in text):
        understanding_type = CognitiveUnderstandingType.GENUINE_UNDERSTANDING
        confidence = 0.89
        rationale = "Candidate explained the underlying causal invariant and system failure boundaries in their own words."
    elif len(text) > 30:
        understanding_type = CognitiveUnderstandingType.CORRECT_REASONING
        confidence = 0.82
        rationale = "Candidate provided sound conceptual commentary aligned with system requirements."
    else:
        understanding_type = CognitiveUnderstandingType.CORRECT_REASONING
        confidence = 0.70
        rationale = "Concise response aligned with topic discussion."

    # Determine Adaptive Teaching Action
    if failure_count >= 2:
        recommended_action = AdaptiveTeachingAction.FOUNDATIONAL_REMEDIATION
    elif understanding_type in (CognitiveUnderstandingType.MISCONCEPTION, CognitiveUnderstandingType.INCORRECT_REASONING):
        recommended_action = AdaptiveTeachingAction.TARGETED_MISCONCEPTION_CORRECTION
    elif understanding_type == CognitiveUnderstandingType.MEMORIZED_DEFINITION:
        recommended_action = AdaptiveTeachingAction.APPLICATION_CHECK
    elif understanding_type == CognitiveUnderstandingType.TRADE_OFF_ANALYSIS:
        recommended_action = AdaptiveTeachingAction.ADVANCE_TO_INDEPENDENT_TRANSFER
    elif understanding_type == CognitiveUnderstandingType.CONCEPT_APPLICATION:
        recommended_action = AdaptiveTeachingAction.FADE_SCAFFOLD_TO_PRACTICE
    elif understanding_type in (CognitiveUnderstandingType.GENUINE_UNDERSTANDING, CognitiveUnderstandingType.CORRECT_REASONING):
        recommended_action = AdaptiveTeachingAction.DEEPEN_APPLICATION
    else:
        recommended_action = AdaptiveTeachingAction.DEEPEN_APPLICATION

    return {
        "understanding_type": understanding_type,
        "recommended_action": recommended_action,
        "detected_misconceptions": detected_misconceptions,
        "demonstrated_invariants": demonstrated_invariants,
        "confidence": confidence,
        "rationale": rationale,
    }


def classify_pedagogical_intent(user_message: str, convo_meta: Optional[Dict[str, Any]] = None) -> str:
    """
    Robust pedagogical intent classifier recognizing conversational goals:
    - Concurrency & Simultaneous arrivals
    - Teach from beginning / First principles
    - Show implementation / Code
    - Check understanding / Quiz
    - Simplify / Beginner analogies
    - Worked examples
    - Explain thoroughly / Deep dive
    - Unseen transfer challenge
    - Hints & Guided practice
    - Clarifying answers to prior questions
    """
    meta = convo_meta or {}
    text = user_message.lower().strip()

    # Priority 0: Explicit Action Type from quick action buttons
    action_type = meta.get("action_type")
    if action_type:
        action_upper = str(action_type).upper()
        if action_upper in ("FOUNDATIONAL_EXPLANATION", "SIMPLIFY_BEGINNER"):
            return PedagogicalIntent.SIMPLIFY_BEGINNER
        elif action_upper in ("CONCEPT_CLARIFICATION", "EXPLAIN_THOROUGHLY"):
            return PedagogicalIntent.EXPLAIN_THOROUGHLY
        elif action_upper == "MISCONCEPTION_CORRECTION":
            return PedagogicalIntent.MISCONCEPTION_CORRECTION
        elif action_upper == "WORKED_EXAMPLE":
            return PedagogicalIntent.WORKED_EXAMPLE
        elif action_upper == "UNDERSTANDING_CHECK":
            return PedagogicalIntent.CHECK_UNDERSTANDING
        elif action_upper == "GUIDED_PRACTICE":
            return PedagogicalIntent.GUIDED_PRACTICE
        elif action_upper == "TARGETED_REMEDIATION":
            return PedagogicalIntent.TARGETED_REMEDIATION
        elif action_upper == "TRANSFER_ASSESSMENT":
            return PedagogicalIntent.TRANSFER_CHALLENGE
        elif action_upper == "INDEPENDENT_TRANSFER":
            return PedagogicalIntent.INDEPENDENT_TRANSFER
        elif action_upper == "NEXT_COMPETENCY":
            return PedagogicalIntent.NEXT_COMPETENCY

    # Priority 0.2: Common Interview Mistakes & Misconceptions
    misconception_patterns = [
        r"\b(common (interview )?mistakes|common pitfalls|where candidates fail|common errors)\b",
        r"\b(misconception|misconceptions|typical bugs)\b",
    ]
    if any(re.search(p, text) for p in misconception_patterns):
        return PedagogicalIntent.MISCONCEPTION_CORRECTION

    # Priority 0.4: Next Competency / Roadmap Advancement
    next_comp_patterns = [
        r"\b(next competency|next topic|next skill|what's next|move on to next)\b",
    ]
    if any(re.search(p, text) for p in next_comp_patterns):
        return PedagogicalIntent.NEXT_COMPETENCY

    # Priority 0.6: L5 Independent Transfer Challenge
    indep_patterns = [
        r"\b(l5 independent transfer|attempt l5|independent transfer|without assistance|without hints)\b",
    ]
    if any(re.search(p, text) for p in indep_patterns):
        return PedagogicalIntent.INDEPENDENT_TRANSFER

    # Priority 1: Concurrency / Simultaneous Arrivals / Race Conditions
    concurrency_patterns = [
        r"\b(simultaneous|simultaneously)\b",
        r"\b(two|multiple|concurrent)\s+requests\b",
        r"\bat the same time\b",
        r"\brace condition\b",
        r"\b(race|concurrency|collision|in-flight)\b",
        r"\bboth requests\b",
        r"\bsame millisecond\b",
        r"\bwhat happens when two\b",
    ]
    if any(re.search(p, text) for p in concurrency_patterns):
        return PedagogicalIntent.CONCURRENCY_RACE_CONDITIONS

    # Priority 2: Teach from the Beginning / From Scratch / First Principles / Ready to Start
    beginning_patterns = [
        r"\b(teach me from first|teach from first|from first)\b",
        r"\b(from the beginning|from beginning|from the start|from start)\b",
        r"\b(start from scratch|from scratch)\b",
        r"\b(from zero|from ground up|first principles)\b",
        r"\b(start over|start fresh|start again)\b",
        r"\b(prerequisites|basics first)\b",
        r"\b(ready|i'm ready|i am ready|im ready)\b",
        r"\b(let's start|lets start|let's begin|lets begin|let us start|let us begin)\b",
        r"\b(start|begin|proceed|go ahead|let's do it|lets do it)\b",
        r"\b(yes|yeah|yep|sure|ok|okay)\b",
        r"\b(teach me|explain fundamentals|explain the fundamentals|explain the topics|explain topic|dive in)\b",
    ]
    if any(re.search(p, text) for p in beginning_patterns):
        return PedagogicalIntent.TEACH_FROM_BEGINNING

    # Priority 3: Show Implementation / Code
    impl_patterns = [
        r"\b(how to implement|implement it|implementation)\b",
        r"\b(show me the code|show code|write code|in code|code snippet)\b",
        r"\b(python code|code example|sample code|code implementation)\b",
        r"\b(how do i implement|how would you code)\b",
    ]
    if any(re.search(p, text) for p in impl_patterns):
        return PedagogicalIntent.SHOW_IMPLEMENTATION

    # Priority 4: Check Understanding / Quiz
    check_patterns = [
        r"\b(check (whether|if) i understood|check my understanding|check understanding)\b",
        r"\b(quiz me|test my understanding|test me on this|ask me a question)\b",
        r"\b(did i get this right|am i right|is this correct)\b",
    ]
    if any(re.search(p, text) for p in check_patterns):
        return PedagogicalIntent.CHECK_UNDERSTANDING

    # Priority 5: Unseen Transfer Challenge
    transfer_patterns = [
        r"\b(transfer challenge|unseen transfer|unseen scenario|l5 transfer)\b",
        r"\b(different problem|independent challenge|test me independently)\b",
        r"\b(unseen|transfer)\b",
    ]
    if any(re.search(p, text) for p in transfer_patterns):
        return PedagogicalIntent.TRANSFER_CHALLENGE

    # Priority 6: Hint Request
    hint_patterns = [
        r"\b(give me a hint|hint|clue|i am stuck|i'm stuck)\b",
    ]
    if any(re.search(p, text) for p in hint_patterns):
        return PedagogicalIntent.HINT_REQUEST

    # Priority 7: Guided Practice
    practice_patterns = [
        r"\b(guided practice|practice exercise|exercise|practice problem|practice)\b",
    ]
    if any(re.search(p, text) for p in practice_patterns):
        return PedagogicalIntent.GUIDED_PRACTICE

    # Priority 8: Simplify / Beginner
    simplify_patterns = [
        r"\b(simple terms|simpler terms|simple language)\b",
        r"\b(like i am a beginner|as a beginner|for beginners|beginner)\b",
        r"\b(eli5|layman|layman's terms|plain english)\b",
        r"\b(explain simply|make it simpler|simpler)\b",
        r"\b(i don't understand|i do not understand|confused|what does that mean)\b",
    ]
    if any(re.search(p, text) for p in simplify_patterns):
        return PedagogicalIntent.SIMPLIFY_BEGINNER

    # Priority 9: Worked Example / Real-World Example
    example_patterns = [
        r"\b(payment example|detailed payment example)\b",
        r"\b(worked example|walk through|walk me through)\b",
        r"\b(real-world scenario|case study|concrete example|detailed example)\b",
        r"\b(give me an example|show me an example|another example|give an example)\b",
    ]
    if any(re.search(p, text) for p in example_patterns):
        return PedagogicalIntent.WORKED_EXAMPLE

    # Priority 9.2: Why Wrong / Error Diagnosis
    if re.search(r"\b(why is my answer wrong|why was that wrong|where is my error|where is my mistake|what did i do wrong|why did i fail)\b", text):
        return PedagogicalIntent.WHY_WRONG

    # Priority 9.4: Comparison / Differences
    if re.search(r"\b(difference between|compare|differences between|vs\b|versus)\b", text):
        return PedagogicalIntent.COMPARISON

    # Priority 9.6: Why Questions (e.g. "Why is Redis used?")
    if re.search(r"\b(why is|why are|why do we|why does)\b", text):
        return PedagogicalIntent.WHY_QUESTION

    # Priority 9.8: How Questions (e.g. "How does this work in a real system?")
    if re.search(r"\b(how does this work|how does it work|how do we|how does)\b", text):
        return PedagogicalIntent.HOW_QUESTION

    # Priority 10: Explain Thoroughly / In Detail / More Detail
    thorough_patterns = [
        r"\b(explain indetail|in detail|indetail|give it in detail)\b",
        r"\b(deep dive|elaborate|thoroughly|more thoroughly)\b",
        r"\b(explain more|give more detail|in-depth|go deeper)\b",
        r"\b(more technical detail|more detail|deeper technical)\b",
        r"\b(break it down|comprehensive)\b",
    ]
    if any(re.search(p, text) for p in thorough_patterns):
        return PedagogicalIntent.EXPLAIN_THOROUGHLY

    # Priority 10.5: Specific Term Explanation ("What is database indexing?", "What is...", "Define...")
    if re.search(r"\b(what is|what does|define|meaning of|what's)\b", text):
        return PedagogicalIntent.EXPLAIN_SPECIFIC_TERM

    # Priority 11: Clarify Answer (responding to coach's check/question)
    # Only if NOT asking an explicit question and not starting with a question word
    last_q = meta.get("last_question_asked")
    is_direct_question = text.endswith("?") or any(text.startswith(p) for p in ["what", "why", "how", "can", "could", "explain", "compare", "tell", "show", "give"])
    if last_q and len(text) > 15 and not is_direct_question:
        return PedagogicalIntent.CLARIFY_ANSWER

    return PedagogicalIntent.GENERAL_COACHING


class CoachingTutorService:
    """
    Pedagogical AI Coaching Tutor coordinating Socratic dialogue, proactive teaching,
    worked examples, understanding checks, guided practice, and unseen transfer challenges.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.convo_repo = ConversationRepository(session)
        self.candidate_repo = CandidateRepository(session)
        self.skill_state_repo = CandidateSkillStateRepository(session)
        self.interview_repo = InterviewSessionRepository(session)
        self.diagnosis_repo = TransferDiagnosisRepository(session)
        self.roadmap_repo = RoadmapRepository(session)
        self.transfer_task_gen = TransferTaskGenerator()

    async def get_candidate_learning_memory(self, candidate_id: str) -> Dict[str, Any]:
        """
        Retrieves compact, longitudinal learning evidence for an existing candidate:
        - Concepts already taught from conversation history
        - Recurring misconceptions from diagnostic records and skill state
        - Evaluated attempt metrics (count, success rate, average hints requested)
        - Latent mastery levels and validated transfer achievements
        - Unresolved learning objectives
        Avoids raw conversation text injection; summarizes empirical learning state.
        """
        if not candidate_id:
            return {
                "concepts_already_taught": [],
                "unresolved_objectives": [],
                "recurring_misconceptions": [],
                "attempts_count": 0,
                "successful_attempts": 0,
                "avg_hints_requested": 0.0,
                "skill_profiles": {},
            }

        # 1. Past conversation metadata
        concepts_taught: List[str] = []
        unresolved_objectives: List[str] = []
        try:
            convos = await self.convo_repo.list_by_candidate(candidate_id, limit=25)
            for c in convos:
                meta = c.metadata_ or {}
                taught_skill = meta.get("focus_skill") or meta.get("focus_key")
                if taught_skill and taught_skill not in concepts_taught:
                    concepts_taught.append(taught_skill)
                obj = meta.get("learning_objective")
                if obj and meta.get("active_phase") != "PHASE_F_TRANSFER" and obj not in unresolved_objectives:
                    unresolved_objectives.append(obj)
        except Exception as e:
            logger.debug(f"Learning memory convos query: {e}")

        # 2. Diagnosed Misconceptions & Failure Types
        recurring_misconceptions: List[str] = []
        try:
            diags = await self.diagnosis_repo.list_by_candidate(candidate_id, limit=10)
            for d in diags:
                diag_summary = d.failure_type or ""
                if d.misconception_details:
                    diag_summary += f": {d.misconception_details}"
                if diag_summary and diag_summary not in recurring_misconceptions:
                    recurring_misconceptions.append(diag_summary)
        except Exception as e:
            logger.debug(f"Learning memory diagnosis query: {e}")

        # 3. Evaluated Transfer Attempts & Assistance Telemetry
        attempts_count = 0
        successful_attempts = 0
        total_hints = 0
        try:
            attempt_repo = TransferAttemptRepository(self.session)
            attempts = await attempt_repo.list_by_candidate(candidate_id, limit=20)
            attempts_count = len(attempts)
            successful_attempts = sum(1 for a in attempts if a.transfer_success)
            total_hints = sum(a.hints_requested_count for a in attempts)
        except Exception as e:
            logger.debug(f"Learning memory attempts query: {e}")

        avg_hints = (total_hints / attempts_count) if attempts_count > 0 else 0.0

        # 4. Longitudinal Skill States
        skill_profiles: Dict[str, Dict[str, Any]] = {}
        try:
            states = await self.skill_state_repo.list_by_candidate(candidate_id)
            for s in states:
                skill_profiles[s.skill_name] = {
                    "mastery_estimate": round(s.mastery_estimate, 2),
                    "highest_transfer_level": s.highest_transfer_level,
                    "assistance_dependency_index": round(s.assistance_dependency_index, 2),
                    "recurring_failures": list(s.recurring_failure_types or []),
                }
                for rf in s.recurring_failure_types or []:
                    if rf and rf not in recurring_misconceptions:
                        recurring_misconceptions.append(rf)
        except Exception as e:
            logger.debug(f"Learning memory skill states query: {e}")

        return {
            "concepts_already_taught": concepts_taught,
            "unresolved_objectives": unresolved_objectives[:4],
            "recurring_misconceptions": recurring_misconceptions[:4],
            "attempts_count": attempts_count,
            "successful_attempts": successful_attempts,
            "avg_hints_requested": round(avg_hints, 2),
            "skill_profiles": skill_profiles,
        }

    async def get_autonomous_coaching_recommendation(
        self, candidate_id: str, target_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inspects candidate evidence (profile, interview evaluation deficits, roadmap gaps, ADI, recurring failure modes)
        and proactively synthesizes an autonomous coaching recommendation without requiring manual user selection.
        Handles cold-start gracefully when no prior assessment evidence exists.
        """
        effective_role = target_role or "Software Engineer"
        cand_name = "Candidate"
        has_evidence = False
        evidence_source = "COLD_START"

        # 1. Inspect Candidate Profile
        if candidate_id:
            try:
                candidate_obj = await self.candidate_repo.get_with_details(candidate_id)
                if candidate_obj:
                    if candidate_obj.full_name and "unknown" not in candidate_obj.full_name.lower():
                        cand_name = candidate_obj.full_name
                    if not target_role and getattr(candidate_obj, "target_role", None):
                        effective_role = candidate_obj.target_role
            except Exception as e:
                logger.debug(f"Candidate profile lookup: {e}")

        # 2. Inspect Latest Interview Evaluation Deficits
        interview_weakness: Optional[Dict[str, Any]] = None
        if candidate_id:
            try:
                sessions = await self.interview_repo.list_by_candidate(candidate_id, limit=5)
                for s in sessions:
                    sess_with_hist = await self.interview_repo.get_with_full_history(s.id)
                    if sess_with_hist and sess_with_hist.questions:
                        scored_q = []
                        for q in sess_with_hist.questions:
                            if q.answer and q.answer.evaluation:
                                scored_q.append((float(q.answer.evaluation.overall_score), q))
                        if scored_q:
                            scored_q.sort(key=lambda x: x[0])
                            lowest_score, lowest_q = scored_q[0]
                            ev = lowest_q.answer.evaluation
                            interview_weakness = {
                                "topic": getattr(lowest_q, "topic", "") or getattr(lowest_q, "target_competency", "System Design"),
                                "score": lowest_score,
                                "question_text": lowest_q.question_text,
                                "weaknesses": ev.weaknesses or [],
                                "missing_concepts": ev.missing_concepts or [],
                                "session_id": sess_with_hist.id,
                                "question_id": lowest_q.id,
                            }
                            break
            except Exception as e:
                logger.debug(f"Interview evaluation inspection: {e}")

        # 3. Inspect Active Roadmap Priorities
        roadmap_gap: Optional[Dict[str, Any]] = None
        if candidate_id:
            try:
                active_roadmap = await self.roadmap_repo.get_by_candidate(candidate_id)
                if active_roadmap and active_roadmap.items:
                    uncompleted = [item for item in active_roadmap.items if item.status != "COMPLETED"]
                    if uncompleted:
                        uncompleted.sort(key=lambda it: it.sequence_order)
                        top_item = uncompleted[0]
                        roadmap_gap = {
                            "skill_id": top_item.skill_id,
                            "skill_title": top_item.skill_title,
                            "priority": top_item.priority,
                            "learning_objective": top_item.learning_objective,
                            "rationale": top_item.rationale,
                            "current_transfer": top_item.current_transfer_level,
                            "assistance_dependency": top_item.assistance_dependency,
                        }
            except Exception as e:
                logger.debug(f"Roadmap inspection: {e}")

        # 4. Inspect Longitudinal Skill States & Failure Diagnoses
        skill_deficit: Optional[Dict[str, Any]] = None
        if candidate_id:
            try:
                states = await self.skill_state_repo.list_by_candidate(candidate_id)
                if states:
                    assessed = [s for s in states if s.total_attempts > 0 or s.mastery_estimate > 0.0]
                    if assessed:
                        assessed.sort(key=lambda s: (s.mastery_estimate, -s.assistance_dependency_index))
                        lowest_state = assessed[0]
                        skill_deficit = {
                            "skill_name": lowest_state.skill_name,
                            "mastery_estimate": lowest_state.mastery_estimate,
                            "highest_transfer": lowest_state.highest_transfer_level,
                            "adi": lowest_state.assistance_dependency_index,
                            "recurring_failures": lowest_state.recurring_failure_types or [],
                        }
            except Exception as e:
                logger.debug(f"Skill state inspection: {e}")

        # 5. Determine Autonomous Recommendation based on empirical evidence hierarchy
        if interview_weakness and interview_weakness["score"] < 7.5:
            has_evidence = True
            evidence_source = "INTERVIEW_EVALUATION"
            raw_skill = interview_weakness["topic"]
            canonical_skill = raw_skill.lower().replace(" ", "_")
            matched_key = None
            for cat_key in COMPETENCY_CATALOG:
                if cat_key in canonical_skill or canonical_skill in cat_key:
                    matched_key = cat_key
                    break
            final_skill_id = matched_key or canonical_skill
            skill_info = COMPETENCY_CATALOG.get(final_skill_id, {})
            skill_title = skill_info.get("title") or raw_skill.replace("_", " ").title()
            score_val = interview_weakness["score"]
            weak_str = ", ".join(interview_weakness["weaknesses"][:2]) if interview_weakness["weaknesses"] else "conceptual invariants"
            missing_str = ", ".join(interview_weakness["missing_concepts"][:2]) if interview_weakness["missing_concepts"] else "core mechanisms"

            justification = (
                f"In your recent interview for {effective_role}, your response on '{raw_skill}' "
                f"scored {score_val:.1f}/10 with detected weaknesses in {weak_str}. "
                f"Missing concepts: {missing_str}. Resolving this foundational gap will unlock independent transfer."
            )
            learning_objective = skill_info.get("objective") or f"Master core operational invariants of {skill_title} and eliminate conceptual gaps."
            scaffold_level = "HIGH" if score_val < 5.0 else "MEDIUM"
            action_type = "START_LEARNING"

        elif roadmap_gap:
            has_evidence = True
            evidence_source = "ROADMAP_GAP"
            final_skill_id = roadmap_gap["skill_id"]
            skill_info = COMPETENCY_CATALOG.get(final_skill_id, {})
            skill_title = roadmap_gap["skill_title"]
            justification = (
                f"Top priority from your learning roadmap for {effective_role}: "
                f"{roadmap_gap['rationale']} Current transfer distance is limited to {roadmap_gap['current_transfer']} "
                f"(Assistance Dependency: {roadmap_gap['assistance_dependency']:.2f})."
            )
            learning_objective = roadmap_gap["learning_objective"]
            scaffold_level = "HIGH" if roadmap_gap["assistance_dependency"] > 0.30 else "MEDIUM"
            action_type = "RESUME_COACHING"

        elif skill_deficit and skill_deficit["mastery_estimate"] < 0.75:
            has_evidence = True
            evidence_source = "SKILL_STATE"
            final_skill_id = skill_deficit["skill_name"]
            skill_info = COMPETENCY_CATALOG.get(final_skill_id, {})
            skill_title = skill_info.get("title") or final_skill_id.replace("_", " ").title()
            failures_str = f" Diagnosed failure modes: {', '.join(skill_deficit['recurring_failures'])}." if skill_deficit['recurring_failures'] else ""
            justification = (
                f"Longitudinal skill tracking shows low demonstrated mastery ({skill_deficit['mastery_estimate'] * 100:.0f}%) "
                f"in {skill_title}. Current transfer level: {skill_deficit['highest_transfer']}.{failures_str}"
            )
            learning_objective = skill_info.get("objective") or f"Advance from {skill_deficit['highest_transfer']} to validated L5 Independent Transfer."
            scaffold_level = "HIGH"
            action_type = "START_LEARNING"

        else:
            # Cold-Start Archetype
            has_evidence = False
            evidence_source = "COLD_START"
            role_lower = effective_role.lower()
            if any(k in role_lower for k in ["backend", "system", "distributed", "database", "sre", "reliability"]):
                final_skill_id = "distributed_caching"
            elif any(k in role_lower for k in ["ml", "machine learning", "data science", "algorithm"]):
                final_skill_id = "algorithmic_optimization"
            else:
                final_skill_id = "api_idempotency"

            skill_info = COMPETENCY_CATALOG.get(final_skill_id, {})
            skill_title = skill_info.get("title") or "Distributed Caching & Partitioning"
            justification = (
                f"Welcome, {cand_name}! We don't have prior interview records or assessment evidence for your profile yet. "
                f"We recommend completing a short diagnostic interview to benchmark your baseline skills, "
                f"or you can dive straight into the foundational core competency for {effective_role}."
            )
            learning_objective = skill_info.get("objective") or f"Explore core {effective_role} principles and establish an empirical skill baseline."
            scaffold_level = "HIGH"
            action_type = "DIAGNOSTIC_OR_FOUNDATIONAL"

        return {
            "candidate_id": candidate_id,
            "candidate_name": cand_name,
            "target_role": effective_role,
            "has_evidence": has_evidence,
            "evidence_source": evidence_source,
            "recommended_skill_id": final_skill_id,
            "recommended_skill_title": skill_title,
            "justification": justification,
            "learning_objective": learning_objective,
            "scaffold_level": scaffold_level,
            "target_transfer_level": "L5_INDEPENDENT_TRANSFER",
            "action_type": action_type,
            "interview_context": interview_weakness,
        }

    async def initiate_coaching_session(
        self, payload: InitiateCoachingRequest
    ) -> InitiateCoachingResponse:
        """
        Initiates a personalized conversational coaching session:
        1. Gathers candidate profile, resume, target role, interview deficits, and skill state.
        2. Retrieves longitudinal learning memory (concepts taught, recurring misconceptions, assistance dependency).
        3. Selects the most relevant learning objective and explains why it matters.
        4. Proactively generates the opening teaching lesson (Phases A & B) adapting to prior evidence.
        5. Persists the conversation and message thread.
        """
        candidate_id = payload.candidate_id
        target_role = payload.target_role or "Software Engineer"
        cand_name = "Candidate"
        profile_summary = ""
        weak_topics = []

        # 1. Inspect Candidate Profile and Resume
        if candidate_id:
            try:
                candidate_obj = await self.candidate_repo.get_with_details(candidate_id)
                if candidate_obj:
                    if candidate_obj.full_name and "unknown" not in candidate_obj.full_name.lower():
                        cand_name = candidate_obj.full_name
                    if not payload.target_role and getattr(candidate_obj, "target_role", None):
                        target_role = candidate_obj.target_role

                profile_model = await self.candidate_repo.get_profile(candidate_id)
                if profile_model and profile_model.profile_data:
                    pd = dict(profile_model.profile_data)
                    skills_list = [s.get("name", "") for s in pd.get("skills", []) if s.get("name")]
                    exp_val = pd.get("total_years_experience", 0)
                    profile_summary = f"Experience: {exp_val} years. Skills: {', '.join(skills_list[:6])}."
            except Exception as e:
                logger.debug(f"Candidate profile lookup: {e}")

        # 2. Retrieve Longitudinal Learning Memory
        learning_memory = await self.get_candidate_learning_memory(candidate_id)

        # 3. Inspect Interview Deficits and Evaluation Weaknesses
        interview_deficit_note = ""
        if payload.interview_session_id:
            try:
                interview = await self.interview_repo.get_with_full_history(payload.interview_session_id)
                if interview and interview.questions:
                    scored_questions = []
                    for q in interview.questions:
                        if q.answer and q.answer.evaluation:
                            score = getattr(q.answer.evaluation, "overall_score", 10.0)
                            scored_questions.append((score, q))
                    if scored_questions:
                        scored_questions.sort(key=lambda x: x[0])
                        lowest_score, lowest_q = scored_questions[0]
                        q_topic = getattr(lowest_q, "topic", "")
                        weaknesses = getattr(lowest_q.answer.evaluation, "weaknesses", []) or []
                        missing_concepts = getattr(lowest_q.answer.evaluation, "missing_concepts", []) or []
                        weak_topics.append(q_topic)
                        interview_deficit_note = (
                            f"Evaluated Interview Turn: '{lowest_q.question_text[:120]}...'. "
                            f"Score: {lowest_score:.1f}/10. Weaknesses: {', '.join(weaknesses[:2])}. "
                            f"Missing Concepts: {', '.join(missing_concepts[:3])}."
                        )
            except Exception as e:
                logger.debug(f"Interview evaluation inspection: {e}")

        # 4. Inspect Candidate Skill State
        if candidate_id and not weak_topics:
            try:
                states = await self.skill_state_repo.list_by_candidate(candidate_id)
                if states:
                    low_states = sorted(states, key=lambda s: s.mastery_estimate)
                    for s in low_states:
                        if s.mastery_estimate < 0.75:
                            weak_topics.append(s.skill_name)
            except Exception as e:
                logger.debug(f"Skill state inspection: {e}")

        # 5. Check Recent Failure Diagnosis if Available
        if candidate_id and not weak_topics:
            try:
                recent_diags = await self.diagnosis_repo.list_by_candidate(candidate_id, limit=3)
                if recent_diags:
                    weak_topics.append(recent_diags[0].affected_skill)
            except Exception as e:
                logger.debug(f"Diagnosis inspection: {e}")

        # 6. Determine Focus Competency & Learning Objective (Autonomous Decision)
        rec = await self.get_autonomous_coaching_recommendation(candidate_id, target_role)
        is_cold_start = not rec["has_evidence"]

        if payload.focus_skill:
            skill_input = payload.focus_skill.lower().replace(" ", "_")
            matched_key = None
            for k in COMPETENCY_CATALOG:
                if k in skill_input or skill_input in k:
                    matched_key = k
                    break
            selected_key = matched_key or "distributed_caching"
            competency_info = COMPETENCY_CATALOG.get(selected_key, COMPETENCY_CATALOG["distributed_caching"])
            focus_skill = competency_info["title"]
            learning_objective = competency_info["objective"]
            why_it_matters = competency_info["why_it_matters"]
        else:
            selected_key = rec["recommended_skill_id"]
            competency_info = COMPETENCY_CATALOG.get(selected_key, COMPETENCY_CATALOG.get("distributed_caching", {}))
            focus_skill = rec["recommended_skill_title"]
            learning_objective = rec["learning_objective"]
            why_it_matters = rec["justification"]
            if not interview_deficit_note and rec["has_evidence"]:
                interview_deficit_note = rec["justification"]

        # 7. Check if Reopening an Existing Conversation
        if payload.conversation_id:
            existing_convo = await self.convo_repo.get_with_messages(payload.conversation_id)
            if existing_convo and existing_convo.messages:
                return InitiateCoachingResponse(
                    conversation=ConversationDetailDTO.model_validate(existing_convo),
                    focus_skill=focus_skill,
                    learning_objective=learning_objective,
                    why_it_matters=why_it_matters,
                    target_role=target_role,
                    scaffold_level=(existing_convo.metadata_ or {}).get("scaffold_level", "HIGH"),
                    active_phase=(existing_convo.metadata_ or {}).get("active_phase", "PHASE_B_FUNDAMENTALS"),
                    is_resumed=True,
                )

        # 8. Synthesize Proactive Opening Lesson (Phase A & Phase B) with Memory Adaptation
        if is_cold_start and not payload.focus_skill:
            opening_lesson = (
                f"### 👋 Welcome to AI Coaching Studio, {cand_name}!\n\n"
                f"I'm your **Autonomous AI Technical Coach**. I see you're preparing for the **{target_role}** track.\n\n"
                f"> ℹ️ **No Prior Assessment Records Found**: Because you haven't completed an interview evaluation or uploaded diagnostic evidence yet, "
                f"we recommend taking a brief **Diagnostic Technical Interview** to benchmark your baseline skills.\n\n"
                f"Alternatively, we can jump straight into the foundational core competency for your role: **{focus_skill}**.\n\n"
                f"### 🎯 Learning Objective\n{learning_objective}\n\n"
                f"How would you like to start? Feel free to ask: *'Can you explain this in simple terms?'* or *'Give me a diagnostic question to test my baseline.'*"
            )
        else:
            opening_lesson = await self._generate_proactive_opening_lesson(
                cand_name=cand_name,
                target_role=target_role,
                focus_skill=focus_skill,
                learning_objective=learning_objective,
                why_it_matters=why_it_matters,
                profile_summary=profile_summary,
                interview_deficit_note=interview_deficit_note,
                fallback_fundamentals=competency_info.get("fundamentals", ""),
                learning_memory=learning_memory,
            )

        # 9. Create and Persist Conversation Thread with Persistent Coaching Memory Metadata
        conversation_title = f"{focus_skill} — AI Coaching"
        metadata = {
            "session_type": "coaching_studio",
            "target_role": target_role,
            "focus_skill": focus_skill,
            "focus_key": selected_key,
            "learning_objective": learning_objective,
            "why_it_matters": why_it_matters,
            "scaffold_level": "HIGH" if (learning_memory.get("avg_hints_requested", 0.0) > 1.0) else "MEDIUM",
            "active_phase": "PHASE_B_FUNDAMENTALS",
            "teaching_stage": TeachingStage.STAGE_1_PREREQUISITES,
            "concepts_already_explained": ["fundamentals_overview", "lesson_roadmap"],
            "expressed_difficulties": [],
            "intent_history": ["INITIATE_COACHING"],
            "last_question_asked": "How would you like to proceed? Feel free to ask: 'Explain this in simple terms' or 'Can you give an example?'",
            "provider_used": "opening_lesson",
            "interview_session_id": payload.interview_session_id,
            "candidate_id": candidate_id,
            "learning_memory_summary": {
                "concepts_already_taught": learning_memory.get("concepts_already_taught", []),
                "recurring_misconceptions": learning_memory.get("recurring_misconceptions", []),
                "attempts_count": learning_memory.get("attempts_count", 0),
            },
            "turn_count": 1,
        }

        convo = await self.convo_repo.create_conversation(
            candidate_id=candidate_id,
            title=conversation_title,
            metadata=metadata,
        )

        # Add the coach's opening teaching turn as the very first message
        coach_message = await self.convo_repo.add_message(
            conversation_id=convo.id,
            role=ChatRole.ASSISTANT.value,
            content=opening_lesson,
            message_type="text",
            ui_payload={
                "type": "COACHING_LESSON",
                "phase": "PHASE_B_FUNDAMENTALS",
                "focus_skill": focus_skill,
                "learning_objective": learning_objective,
                "scaffold_level": "HIGH",
            },
            intent=ChatIntent.COACHING.value,
        )

        await self.session.commit()

        # Eagerly reload with full messages
        full_convo = await self.convo_repo.get_with_messages(convo.id)
        return InitiateCoachingResponse(
            conversation=ConversationDetailDTO.model_validate(full_convo or convo),
            focus_skill=focus_skill,
            learning_objective=learning_objective,
            why_it_matters=why_it_matters,
            target_role=target_role,
            scaffold_level="HIGH",
            active_phase="PHASE_B_FUNDAMENTALS",
            is_resumed=False,
        )

    async def _generate_proactive_opening_lesson(
        self,
        cand_name: str,
        target_role: str,
        focus_skill: str,
        learning_objective: str,
        why_it_matters: str,
        profile_summary: str,
        interview_deficit_note: str,
        fallback_fundamentals: str,
        learning_memory: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Uses configured LLM Provider to craft the personalized opening coaching turn.
        Falls back reliably to curated architectural curriculum.
        """
        provider = get_llm_provider(task="routine")
        system_prompt = (
            "You are the World's Best AI Interview Coach for software engineers. "
            "Your pedagogical philosophy is warm, psychologically safe, and deeply technical (Staff Engineer standard).\n\n"
            "You are initiating a personalized learning session in the AI Coaching Studio. "
            "You must lead the learning process proactively: explain what the candidate should learn, "
            "why it matters for their selected target role, outline the session roadmap, and immediately "
            "teach the foundational mechanics in clear, accessible language before asking them to formulate solutions.\n\n"
            f"Candidate: {cand_name}\n"
            f"Target Role: {target_role}\n"
            f"Focus Competency: {focus_skill}\n"
            f"Learning Objective: {learning_objective}\n"
            f"Why It Matters: {why_it_matters}\n"
        )
        if interview_deficit_note:
            system_prompt += f"Recent Interview Diagnostic Evidence: {interview_deficit_note}\n"
        if profile_summary:
            system_prompt += f"Candidate Background: {profile_summary}\n"

        if learning_memory:
            concepts = learning_memory.get("concepts_already_taught", [])
            misconceptions = learning_memory.get("recurring_misconceptions", [])
            attempts = learning_memory.get("attempts_count", 0)
            avg_hints = learning_memory.get("avg_hints_requested", 0.0)
            if concepts or misconceptions or attempts > 0:
                system_prompt += (
                    f"\nCandidate Longitudinal Learning Memory:\n"
                    f"- Prior Concepts Explored: {', '.join(concepts) if concepts else 'None'}\n"
                    f"- Known Diagnosed Misconceptions: {', '.join(misconceptions) if misconceptions else 'None'}\n"
                    f"- Prior Attempts Count: {attempts} (Avg hints required: {avg_hints:.1f})\n"
                    "Use this memory to tailor the depth of your explanation and proactively clarify known recurring misconceptions.\n"
                )

        system_prompt += (
            "\nSTRUCTURE YOUR OPENING MESSAGE STRICTLY AS FOLLOWS:\n"
            "1. Warm Personal Greeting & Objective Introduction (Phase A):\n"
            f"- Greet {cand_name} and warmly welcome them to the AI Coaching Studio.\n"
            f"- State clearly that today's session is focused on mastering **{focus_skill}**.\n"
            f"- Explain in 1-2 motivating sentences why this topic is essential for {target_role} interviews ({why_it_matters}).\n"
            f"- State our target learning objective: {learning_objective}.\n"
            "2. Session Roadmap (What We Will Learn):\n"
            "Present a clear, motivating 4-step roadmap:\n"
            "  1. 📘 **Core Fundamentals & Terminology** — Unpack the core idea in plain language and define key terminology.\n"
            "  2. 🏗️ **Real-World Architectural Worked Example** — Walk through real production trade-offs, state machines, and code flow.\n"
            "  3. 🧠 **Understanding Check** — Quick conceptual questions to verify your mental model.\n"
            "  4. 🚀 **Guided Practice & Unseen Transfer Challenge** — Hands-on problem solving to build independent mastery.\n"
            "3. Invitation to Begin:\n"
            "- IMPORTANT: Do NOT dump the full topic fundamentals or code yet! Keep this opening focused on the introduction and roadmap.\n"
            "- Ask the candidate if they are ready to dive into Step 1 (the core fundamentals) or if they have an initial question.\n"
            "- Conclude by asking them to reply: *\"I'm ready\"* or *\"Let's start\"* whenever they're set!\n"
            "Format cleanly with markdown headings, bullet points, and an encouraging tone."
        )

        try:
            req = LLMRequest(
                system_prompt=system_prompt,
                user_prompt="Initiate the coaching session now.",
                temperature=0.2,
                max_tokens=600,
                response_json=False,
                metadata={"task_type": "conversational_coaching"},
            )
            init_timeout = float(getattr(ai_settings, "nvidia_nim_timeout", 40.0))
            resp = await asyncio.wait_for(provider.generate(req), timeout=init_timeout)
            if (
                resp
                and resp.content
                and len(resp.content.strip()) > 100
                and (
                    focus_skill.split()[0].lower() in resp.content.lower()
                    or "objective" in resp.content.lower()
                    or "roadmap" in resp.content.lower()
                )
            ):
                return resp.content.strip()
        except Exception as e:
            logger.warning(f"Opening lesson primary LLM generation error ({type(provider).__name__}): {e}. Attempting failover...")
            try:
                from backend.infrastructure.ai.gemini_provider import GeminiLLMProvider
                from backend.infrastructure.ai.nvidia_nim_provider import NvidiaNIMLLMProvider
                failover = None
                if isinstance(provider, GeminiLLMProvider) and ai_settings.nvidia_nim_api_key:
                    failover = NvidiaNIMLLMProvider()
                elif isinstance(provider, NvidiaNIMLLMProvider) and ai_settings.gemini_api_key:
                    failover = GeminiLLMProvider()
                if failover is not None:
                    f_resp = await asyncio.wait_for(failover.generate(req), timeout=15.0)
                    if f_resp and f_resp.content and len(f_resp.content.strip()) > 100:
                        return f_resp.content.strip()
            except Exception as f_err:
                logger.warning(f"Opening lesson failover LLM error: {f_err}")

        # Deterministic Curated Fallback
        memory_banner = ""
        if learning_memory and learning_memory.get("recurring_misconceptions"):
            recurr = learning_memory["recurring_misconceptions"][0]
            memory_banner = f"> 🧠 **Learning Memory Note**: We've flagged *{recurr}* from your prior diagnostic evidence. We will actively reinforce this boundary today.\n\n"
        elif learning_memory and learning_memory.get("concepts_already_taught"):
            past = ", ".join(learning_memory["concepts_already_taught"][:2])
            memory_banner = f"> 🧠 **Building On Previous Mastery**: Connecting our work on *{past}* directly to this session's architectural trade-offs.\n\n"

        return (
            f"Hello {cand_name}! Welcome to the **AI Coaching Studio**.\n\n"
            f"{memory_banner}"
            f"Today, we will focus on mastering **{focus_skill}**.\n\n"
            f"💡 **Why It Matters for {target_role}**:\n{why_it_matters}\n\n"
            f"🎯 **Our Learning Objective**: {learning_objective}\n\n"
            "📋 **Here is our 4-step roadmap for this session**:\n"
            "1. 📘 **Core Fundamentals & Essential Terminology** — Understanding the core primitives and why naive approaches fail.\n"
            "2. 🏗️ **Real-World Architectural Worked Example** — Seeing how staff engineers design state machines and handle failure boundaries.\n"
            "3. 🧠 **Understanding Check** — Testing your grasp with interactive conceptual checks.\n"
            "4. 🚀 **Guided Practice & Unseen Transfer Challenge** — Proving you can apply these invariants independently.\n\n"
            "---\n\n"
            "💬 **Are you ready to dive into Step 1 (the core fundamentals), or is there a specific aspect you'd like to touch on first?**\n\n"
            "*Reply with \"I'm ready\" or \"Let's start\" whenever you're set!*"
        )

    async def process_coaching_turn(
        self,
        conversation_id: str,
        user_message: str,
        candidate_id: Optional[str] = None,
        target_role: Optional[str] = None,
        focus_skill: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendMessageResponse:
        """
        Processes a candidate turn within an ongoing coaching session:
        - Classifies pedagogical intent with robust conversational understanding.
        - Tracks stateful teaching stages, explained concepts, expressed difficulties, and history.
        - Connects to AI provider with honest, context-aware pedagogical fallbacks.
        - Progresses through pedagogical stages without repeating generic responses.
        - Persists state in conversation metadata and repository.
        """
        t_turn_start = time.perf_counter()

        # Step 1: History Retrieval
        convo = await self.convo_repo.get_with_messages(conversation_id)
        if not convo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Coaching conversation '{conversation_id}' not found.",
            )
        t_history_retrieval_sec = time.perf_counter() - t_turn_start

        convo_meta = dict(convo.metadata_ or {})
        effective_cand_id = candidate_id or convo.candidate_id
        effective_role = target_role or convo_meta.get("target_role") or "Software Engineer"
        effective_skill = focus_skill or convo_meta.get("focus_skill") or "System Architecture"
        effective_objective = convo_meta.get("learning_objective") or f"Master core invariants of {effective_skill}"
        current_phase = convo_meta.get("active_phase", "PHASE_B_FUNDAMENTALS")
        scaffold_level = convo_meta.get("scaffold_level", "HIGH")

        # Strictly synchronize competency key with effective skill to prevent curriculum mismatch
        skill_input = effective_skill.lower().replace(" ", "_")
        if "idemp" in skill_input:
            selected_key = "api_idempotency"
        elif any(k in skill_input for k in ["cache", "partition", "stampede"]):
            selected_key = "distributed_caching"
        elif any(k in skill_input for k in ["concurr", "isolation", "lock", "acid", "db"]):
            selected_key = "database_concurrency"
        elif any(k in skill_input for k in ["resilien", "circuit", "backoff", "bulkhead"]):
            selected_key = "resilience_patterns"
        else:
            selected_key = convo_meta.get("focus_key") or "api_idempotency"

        convo_meta["focus_key"] = selected_key
        convo_meta["focus_skill"] = effective_skill

        # Stateful Learning Progression Memory
        stage = convo_meta.get("teaching_stage", TeachingStage.STAGE_1_PREREQUISITES)
        concepts_explained = list(convo_meta.get("concepts_already_explained", []))
        expressed_difficulties = list(convo_meta.get("expressed_difficulties", []))
        intent_history = list(convo_meta.get("intent_history", []))

        # Step 2: Persist Candidate User Message
        t_user_persist_start = time.perf_counter()
        user_msg = await self.convo_repo.add_message(
            conversation_id=conversation_id,
            role=ChatRole.USER.value,
            content=user_message,
            message_type="text",
            intent=ChatIntent.COACHING.value,
        )
        t_user_persist_sec = time.perf_counter() - t_user_persist_start

        # Step 3: Extract Prior Message Dialogue (Bounded context window preserving complete technical depth and code blocks)
        t_prompt_start = time.perf_counter()
        prior_history_lines = []
        if convo.messages:
            prior_msgs = [m for m in convo.messages if str(m.id) != str(user_msg.id)]
            total_history_budget = 8000
            current_len = 0
            collected = []
            for m in reversed(prior_msgs[-10:]):
                speaker = "Candidate" if m.role == ChatRole.USER.value else "Coach"
                # Preserve complete candidate technical reasoning and code without arbitrary 500-char truncation
                max_len = 2500
                m_content = m.content[:max_len].strip()
                line = f"{speaker}: {m_content}"
                if current_len + len(line) > total_history_budget:
                    break
                collected.append(line)
                current_len += len(line)
            prior_history_lines = list(reversed(collected))
        history_str = "\n".join(prior_history_lines) if prior_history_lines else "None"

        # 3. Detect Robust Pedagogical Intent
        detected_intent = classify_pedagogical_intent(user_message, convo_meta)
        intent_history.append(detected_intent)
        logger.info(
            f"Coaching turn on convo '{conversation_id}': classified intent '{detected_intent}' "
            f"for message: '{user_message[:60]}...'"
        )

        # Track candidate expressed difficulties from conversational cues
        msg_lower = user_message.lower()
        if any(k in msg_lower for k in ["simultaneous", "at the same time", "race condition", "two requests", "both arrive"]):
            diff = "concurrency race conditions during simultaneous requests"
            if diff not in expressed_difficulties:
                expressed_difficulties.append(diff)
        elif any(k in msg_lower for k in ["don't understand", "do not understand", "confused", "lost", "what does that mean"]):
            diff = f"conceptual confusion at {stage}"
            if diff not in expressed_difficulties:
                expressed_difficulties.append(diff)

        # Step 3.5: Cognitive Understanding Analysis & Adaptive Teaching Decision
        past_misconceptions = list(convo_meta.get("diagnosed_misconceptions", []))
        cognitive_eval = analyze_cognitive_understanding(
            user_message=user_message,
            focus_skill=effective_skill,
            last_question=convo_meta.get("last_question_asked"),
            failure_count=len(past_misconceptions),
        )
        for disc in cognitive_eval.get("detected_misconceptions", []):
            if disc not in past_misconceptions:
                past_misconceptions.append(disc)
        convo_meta["diagnosed_misconceptions"] = past_misconceptions
        convo_meta["last_cognitive_eval"] = cognitive_eval

        # 4. Determine Phase & Stage Progression
        new_phase = current_phase
        new_stage = stage
        ui_card = None

        # Determine whether the candidate is submitting an answer to the coach's prior question
        # OR whether the candidate is asking a new question / requesting a topic / using quick actions.
        # CRITICAL FIX (Phase 8): Do NOT treat candidate questions as answers to the coach's prior check.
        user_text_clean = user_message.strip().lower()
        is_direct_user_query = (
            detected_intent in (
                PedagogicalIntent.WHY_QUESTION,
                PedagogicalIntent.HOW_QUESTION,
                PedagogicalIntent.COMPARISON,
                PedagogicalIntent.WHY_WRONG,
                PedagogicalIntent.EXPLAIN_SPECIFIC_TERM,
                PedagogicalIntent.MORE_DETAIL,
                PedagogicalIntent.SIMPLIFY_BEGINNER,
                PedagogicalIntent.TEACH_FROM_BEGINNING,
                PedagogicalIntent.WORKED_EXAMPLE,
                PedagogicalIntent.CONCURRENCY_RACE_CONDITIONS,
                PedagogicalIntent.SHOW_IMPLEMENTATION,
                PedagogicalIntent.CHECK_UNDERSTANDING,
                PedagogicalIntent.GUIDED_PRACTICE,
                PedagogicalIntent.TRANSFER_CHALLENGE,
                PedagogicalIntent.INDEPENDENT_TRANSFER,
                PedagogicalIntent.HINT_REQUEST,
                PedagogicalIntent.NEXT_COMPETENCY,
                PedagogicalIntent.MISCONCEPTION_CORRECTION,
                PedagogicalIntent.TARGETED_REMEDIATION,
            )
            or user_text_clean.endswith("?")
            or any(user_text_clean.startswith(p) for p in [
                "what", "why", "how", "can you", "could you", "explain", "compare", "tell me",
                "show me", "give me", "is there", "are there", "diff", "difference", "i don't understand",
                "i do not understand", "confused", "eli5"
            ])
            or bool(meta.get("action_type"))
        )

        is_candidate_answering = (
            not is_direct_user_query
            and (
                detected_intent == PedagogicalIntent.CLARIFY_ANSWER
                or (
                    bool(convo_meta.get("last_question_asked"))
                    and cognitive_eval["understanding_type"] in (
                        CognitiveUnderstandingType.MEMORIZED_DEFINITION,
                        CognitiveUnderstandingType.MISCONCEPTION,
                        CognitiveUnderstandingType.INCORRECT_REASONING,
                        CognitiveUnderstandingType.TRADE_OFF_ANALYSIS,
                        CognitiveUnderstandingType.CONCEPT_APPLICATION,
                        CognitiveUnderstandingType.GENUINE_UNDERSTANDING,
                    )
                )
            )
        )

        if is_candidate_answering:
            rec_action = cognitive_eval["recommended_action"]
            if rec_action == AdaptiveTeachingAction.APPLICATION_CHECK:
                new_phase = "PHASE_D_CHECK_UNDERSTANDING"
                new_stage = TeachingStage.STAGE_6_UNDERSTANDING_CHECK
            elif rec_action == AdaptiveTeachingAction.TARGETED_MISCONCEPTION_CORRECTION:
                new_phase = "PHASE_B_FUNDAMENTALS"
                new_stage = TeachingStage.STAGE_2_CORE_MECHANICS
                scaffold_level = "HIGH"
                disc_diff = f"misconception: {', '.join(cognitive_eval.get('detected_misconceptions', []))}"
                if disc_diff not in expressed_difficulties:
                    expressed_difficulties.append(disc_diff)
            elif rec_action == AdaptiveTeachingAction.FOUNDATIONAL_REMEDIATION:
                new_phase = "PHASE_B_FUNDAMENTALS"
                new_stage = TeachingStage.STAGE_2_SIMPLIFIED_INTUITION
                scaffold_level = "HIGH"
            elif rec_action == AdaptiveTeachingAction.DEEPEN_APPLICATION:
                new_phase = "PHASE_C_WORKED_EXAMPLE"
                new_stage = TeachingStage.STAGE_4_CONCURRENCY_DEEP_DIVE
                scaffold_level = "MEDIUM"
            elif rec_action in (AdaptiveTeachingAction.ADVANCE_TO_INDEPENDENT_TRANSFER, AdaptiveTeachingAction.FADE_SCAFFOLD_TO_PRACTICE):
                new_phase = "PHASE_F_TRANSFER"
                new_stage = TeachingStage.STAGE_8_TRANSFER_CHALLENGE
                scaffold_level = "INDEPENDENT"
        elif detected_intent == PedagogicalIntent.TEACH_FROM_BEGINNING:
            new_stage = TeachingStage.STAGE_1_PREREQUISITES
            new_phase = "PHASE_B_FUNDAMENTALS"
            if "network_timeouts" not in concepts_explained:
                concepts_explained.append("network_timeouts")
            if "at_least_once_delivery" not in concepts_explained:
                concepts_explained.append("at_least_once_delivery")
            if "idempotency_key_contract" not in concepts_explained:
                concepts_explained.append("idempotency_key_contract")
        elif detected_intent in (PedagogicalIntent.SIMPLIFY_BEGINNER, PedagogicalIntent.FOUNDATIONAL_EXPLANATION):
            new_stage = TeachingStage.STAGE_2_SIMPLIFIED_INTUITION
            new_phase = "PHASE_B_FUNDAMENTALS"
            if "intuitive_mental_model" not in concepts_explained:
                concepts_explained.append("intuitive_mental_model")
        elif detected_intent == PedagogicalIntent.MISCONCEPTION_CORRECTION:
            new_stage = TeachingStage.STAGE_2_CORE_MECHANICS
            new_phase = "PHASE_B_FUNDAMENTALS"
            if "common_misconceptions" not in concepts_explained:
                concepts_explained.append("common_misconceptions")
        elif detected_intent == PedagogicalIntent.TARGETED_REMEDIATION:
            new_stage = TeachingStage.STAGE_2_CORE_MECHANICS
            new_phase = "PHASE_B_FUNDAMENTALS"
            scaffold_level = "HIGH"
        elif detected_intent == PedagogicalIntent.EXPLAIN_THOROUGHLY:
            new_stage = TeachingStage.STAGE_2_CORE_MECHANICS
            new_phase = "PHASE_B_FUNDAMENTALS"
            if "3_phase_lifecycle" not in concepts_explained:
                concepts_explained.append("3_phase_lifecycle")
        elif detected_intent == PedagogicalIntent.WORKED_EXAMPLE:
            new_stage = TeachingStage.STAGE_3_WORKED_EXAMPLE
            new_phase = "PHASE_C_WORKED_EXAMPLE"
            if "payment_checkout_flow" not in concepts_explained:
                concepts_explained.append("payment_checkout_flow")
        elif detected_intent == PedagogicalIntent.CONCURRENCY_RACE_CONDITIONS:
            new_stage = TeachingStage.STAGE_4_CONCURRENCY_DEEP_DIVE
            new_phase = "PHASE_C_WORKED_EXAMPLE"
            if "toctou_race_condition" not in concepts_explained:
                concepts_explained.append("toctou_race_condition")
            if "atomic_mutual_exclusion" not in concepts_explained:
                concepts_explained.append("atomic_mutual_exclusion")
        elif detected_intent == PedagogicalIntent.SHOW_IMPLEMENTATION:
            new_stage = TeachingStage.STAGE_5_IMPLEMENTATION
            new_phase = "PHASE_C_WORKED_EXAMPLE"
            if "redis_fastapi_code" not in concepts_explained:
                concepts_explained.append("redis_fastapi_code")
        elif detected_intent == PedagogicalIntent.CHECK_UNDERSTANDING:
            new_stage = TeachingStage.STAGE_6_UNDERSTANDING_CHECK
            new_phase = "PHASE_D_CHECK_UNDERSTANDING"
        elif detected_intent == PedagogicalIntent.GUIDED_PRACTICE:
            new_stage = TeachingStage.STAGE_7_GUIDED_PRACTICE
            new_phase = "PHASE_E_PRACTICE"
            scaffold_level = "MEDIUM"
        elif detected_intent == PedagogicalIntent.INDEPENDENT_TRANSFER:
            new_stage = TeachingStage.STAGE_8_TRANSFER_CHALLENGE
            new_phase = "PHASE_F_TRANSFER"
            scaffold_level = "INDEPENDENT"
        elif detected_intent == PedagogicalIntent.NEXT_COMPETENCY:
            new_stage = TeachingStage.STAGE_1_PREREQUISITES
            new_phase = "PHASE_A_ORIENTATION"
        elif detected_intent in (
            PedagogicalIntent.EXPLAIN_SPECIFIC_TERM,
            PedagogicalIntent.WHY_QUESTION,
            PedagogicalIntent.HOW_QUESTION,
            PedagogicalIntent.COMPARISON,
            PedagogicalIntent.WHY_WRONG,
            PedagogicalIntent.MORE_DETAIL,
        ):
            new_stage = TeachingStage.STAGE_2_SIMPLIFIED_INTUITION
            new_phase = "PHASE_B_FUNDAMENTALS"
        elif detected_intent == PedagogicalIntent.TRANSFER_CHALLENGE:
            new_stage = TeachingStage.STAGE_8_TRANSFER_CHALLENGE
            new_phase = "PHASE_F_TRANSFER"
            scaffold_level = "LOW"
            try:
                t_req = TransferGenerationRequest(
                    skill_id=effective_skill.lower().replace(" ", "_"),
                    transfer_level=TransferLevel.L3_FAR_TRANSFER,
                    core_invariants=["Deterministic state reconciliation", "Failure boundary isolation"],
                    base_surface_context=f"Real-world high-throughput {effective_skill}",
                    base_expected_concepts=["idempotency", "consistency", "failure_recovery"],
                    parent_task_id=f"coaching_task_{uuid.uuid4().hex[:6]}",
                )
                t_task = await self.transfer_task_gen.generate_transfer_task(t_req)
                ui_card = {
                    "type": "TRANSFER_TASK",
                    "transfer_level": t_task.transfer_level.value,
                    "surface_context": t_task.surface_context,
                    "core_invariants": t_task.core_invariants,
                    "task_id": t_task.id,
                }
            except Exception as e:
                logger.debug(f"Transfer task generation fallback: {e}")
        elif detected_intent == PedagogicalIntent.HINT_REQUEST:
            ui_card = {
                "type": "SOCRATIC_HINT",
                "scaffold_level": scaffold_level,
                "topic": effective_skill,
                "guiding_question": "What invariant must hold before you commit the state modification?",
            }

        # 5. Build Intent-Specific Pedagogical Directive for AI Provider
        if is_candidate_answering:
            rec_act = cognitive_eval.get("recommended_action")
            und_type = cognitive_eval.get("understanding_type")
            misc = cognitive_eval.get("detected_misconceptions", [])
            if rec_act == AdaptiveTeachingAction.APPLICATION_CHECK:
                specific_directive = (
                    "The candidate stated a memorized or formal textbook definition without operational mechanics. "
                    "Do NOT simply accept the definition as complete mastery. "
                    "Acknowledge their definition briefly, then challenge them with a concrete, practical application check: "
                    "ask how this invariant is enforced in code or architecture during concurrent execution."
                )
            elif rec_act == AdaptiveTeachingAction.TARGETED_MISCONCEPTION_CORRECTION:
                specific_directive = (
                    f"The candidate exhibited an architectural misconception ({', '.join(misc) if misc else 'concurrency failure'}). "
                    "CRITICAL: Do NOT agree with the candidate. Directly and politely correct the misconception. "
                    "Explain why their assumption fails in production (e.g. race conditions, external API side-effects, or deadlock), "
                    "provide the correct invariant, and check their understanding before advancing."
                )
            elif rec_act == AdaptiveTeachingAction.FOUNDATIONAL_REMEDIATION:
                specific_directive = (
                    "The candidate has repeatedly struggled or exhibited flawed reasoning on this competency. "
                    "Step back to foundational first principles: provide an intuitive, simplified mental model with a clear analogy, "
                    "strip away edge-case complexity, and check their grasp on the single most fundamental invariant."
                )
            elif rec_act == AdaptiveTeachingAction.ADVANCE_TO_INDEPENDENT_TRANSFER:
                specific_directive = (
                    "The candidate demonstrated high-level conceptual understanding and sound trade-off analysis. "
                    "Validate their reasoning enthusiastically, and challenge them with an unassisted L5 Independent Transfer "
                    "problem in a new, unfamiliar domain context without hints."
                )
            else:
                specific_directive = (
                    "The candidate demonstrated solid conceptual understanding and correct reasoning. "
                    "Validate what they got right, and deepen the application by asking about a real-world edge case, "
                    "such as crash recovery, network partitions, or high-concurrency race condition mitigation."
                )
        else:
            intent_directives = {
                PedagogicalIntent.TEACH_FROM_BEGINNING: (
                    "The candidate asked to be taught from the beginning in detail. "
                    "DO NOT repeat the lesson introduction or generic greetings. "
                    "Start with foundational prerequisites: the network problem (timeouts vs failures), "
                    "why retries are necessary (at-least-once delivery), what idempotency guarantees mathematically, "
                    "and how an Idempotency-Key acts as a contract. Explain one concept at a time with accessible language. "
                    "End by asking a focused question checking their intuition before proceeding."
                ),
                PedagogicalIntent.SIMPLIFY_BEGINNER: (
                    "The candidate asked for a simpler, beginner-friendly explanation. "
                    "You MUST follow this EXACT 6-step digestible lesson structure:\n"
                    "1. Short intuitive explanation (2-3 sentences maximum).\n"
                    "2. One useful analogy.\n"
                    "3. Connection between the analogy and the technical concept.\n"
                    "4. One practical code or architectural example showing correct usage.\n"
                    "5. One common mistake candidates make.\n"
                    "6. One focused question checking candidate understanding.\n"
                    "7. STOP and wait for candidate response.\n"
                    "CRITICAL RULES: Do NOT generate massive tables, five different headings, or repetitive summaries. "
                    "Keep the tone encouraging, technical and concise. Teach one chunk at a time, then verify understanding."
                ),
                PedagogicalIntent.MISCONCEPTION_CORRECTION: (
                    "The candidate asked about common interview mistakes and misconceptions for this competency. "
                    "Explain the top 2-3 most frequent mistakes candidates make in interviews, the root misconception "
                    "behind each, and the exact architectural invariant to preserve. "
                    "Keep it concise, encouraging, and end with a quick question asking if they have seen or made this mistake before."
                ),
                PedagogicalIntent.TARGETED_REMEDIATION: (
                    "The candidate requested targeted remediation on diagnosed weaknesses. "
                    "Directly address the missing invariant with a 2-3 sentence explanation and a minimal code/design snippet. "
                    "Verify understanding with a short Socratic question before advancing."
                ),
                PedagogicalIntent.INDEPENDENT_TRANSFER: (
                    "The candidate wants to attempt an unassisted L5 Independent Transfer challenge. "
                    "Present an unseen real-world challenge in a new surface context with NO spoilers and NO hints. "
                    "State the core requirements clearly and invite them to formulate their independent solution."
                ),
                PedagogicalIntent.NEXT_COMPETENCY: (
                    "The candidate asked to advance to the next competency on their learning roadmap. "
                    "Acknowledge the invariants they explored, provide a brief positive encouragement, "
                    "and recommend the next logical competency for their role."
                ),
                PedagogicalIntent.WORKED_EXAMPLE: (
                    "The candidate asked for a worked example. "
                    "Walk through a concrete payment transaction scenario ($100 checkout) step by step. "
                    "Detail what happens on initial request, network drop, client retry, and cache lookup. "
                    "Highlight why naive check-then-insert fails and how distributed locking solves it."
                ),
                PedagogicalIntent.CONCURRENCY_RACE_CONDITIONS: (
                    "The candidate asked specifically what happens when two requests arrive simultaneously. "
                    "Explain the exact Time-of-Check to Time-of-Use (TOCTOU) race condition in detail: "
                    "why two simultaneous SELECTs both see nothing and double-charge, and how Atomic Mutual Exclusion "
                    "(e.g. Redis SET NX or DB Unique Constraint) serializes execution so Request 1 gets the lock "
                    "and Request 2 gets HTTP 409 Conflict."
                ),
                PedagogicalIntent.SHOW_IMPLEMENTATION: (
                    "The candidate asked for code or implementation. "
                    "Provide clean, production-grade Python code (FastAPI + Redis) demonstrating atomic locking, "
                    "in-progress conflict handling (HTTP 409), cached response return, and transaction TTL. "
                    "Annotate each step clearly."
                ),
                PedagogicalIntent.CHECK_UNDERSTANDING: (
                    "The candidate asked for an understanding check. "
                    "Pose a focused conceptual scenario testing failure recovery or concurrency (e.g. server crash "
                    "after debiting account but before updating cache). Ask what the recovery mechanism should do on retry."
                ),
                PedagogicalIntent.CLARIFY_ANSWER: (
                    "The candidate is answering your previous question or clarifying their thought process. "
                    "Evaluate their response constructively: validate what they got right, explain any missing invariants, "
                    "and guide them to the next step."
                ),
                PedagogicalIntent.EXPLAIN_THOROUGHLY: (
                    "The candidate asked for a thorough explanation in detail. "
                    "Break down the 3-phase execution lifecycle in detail: (1) Key reservation and atomic lock, "
                    "(2) Mutation and ledger recording, and (3) Result caching with TTL. "
                    "Explain the failure boundaries and recovery guarantees at each phase."
                ),
                PedagogicalIntent.EXPLAIN_SPECIFIC_TERM: (
                    "The candidate asked to explain a specific technical term (e.g. database indexing). "
                    "ANSWER THEIR ACTUAL QUESTION DIRECTLY FIRST in simple, direct English by default. "
                    "Structure: (1) Plain English definition (1-2 short sentences, 15-20 words max per sentence). "
                    "(2) Relatable analogy (e.g. index at the back of a textbook). "
                    "(3) How it works technically (avoiding full table scans with B-Trees). "
                    "(4) One key trade-off (faster reads vs slower writes + extra disk storage). "
                    "(5) One short, friendly check question to verify intuition."
                ),
                PedagogicalIntent.WHY_QUESTION: (
                    "The candidate asked why a specific technology or design is used (e.g. 'Why is Redis used?'). "
                    "ANSWER THEIR ACTUAL QUESTION DIRECTLY FIRST in simple, direct English. "
                    "Structure: (1) Direct answer: In-memory RAM speed (< 1ms) and atomic operations. "
                    "(2) Practical use cases: Caching hot data, distributed session management, atomic rate limiting. "
                    "(3) Main trade-off: RAM cost and data volatility on restarts without persistence. "
                    "(4) A short check question."
                ),
                PedagogicalIntent.COMPARISON: (
                    "The candidate asked to compare concepts (e.g. SQL vs NoSQL). "
                    "ANSWER DIRECTLY FIRST in clear, simple language without huge dense tables. "
                    "Structure: (1) Core distinction in 2 short sentences. "
                    "(2) SQL/Relational: Structured schemas, tables, strict ACID transactions (PostgreSQL). "
                    "(3) NoSQL: Flexible documents/key-values, horizontal scaling (MongoDB, Redis). "
                    "(4) When to pick which (integrity vs scale). (5) A short check question."
                ),
                PedagogicalIntent.WHY_WRONG: (
                    "The candidate asked why their previous answer was wrong or incomplete. "
                    "ANSWER DIRECTLY AND EMPATHETICALLY FIRST. "
                    "Structure: (1) The exact flaw or race window in 1-2 short sentences. "
                    "(2) The production failure consequence (double-charge, data corruption). "
                    "(3) The correct invariant or fix. (4) A quick question checking their intuition."
                ),
                PedagogicalIntent.HOW_QUESTION: (
                    "The candidate asked how a concept works in a real system. "
                    "ANSWER DIRECTLY FIRST with a realistic step-by-step production flow in plain English. "
                    "Structure: (1) 3-4 numbered steps from client request to database commit. "
                    "(2) Where the failure boundary is. (3) How recovery works. (4) A short check question."
                ),
                PedagogicalIntent.MORE_DETAIL: (
                    "The candidate asked for more technical depth. "
                    "Provide deeper architectural mechanics and failure edge cases while keeping sentences short (15-20 words max)."
                ),
            }
            specific_directive = intent_directives.get(
                detected_intent,
                "Ground your answer in the core learning objective and answer the candidate's question directly."
            )

        system_prompt = (
            "You are the World's Best Conversational AI Interview Coach. "
            "You are actively conducting a private coaching lesson tailored to the candidate's weaknesses.\n\n"
            f"Target Role: {effective_role}\n"
            f"Focus Competency: {effective_skill}\n"
            f"Learning Objective: {effective_objective}\n"
            f"Current Teaching Stage: {new_stage}\n"
            f"Current Pedagogical Phase: {new_phase}\n"
            f"Active Scaffold Level: {scaffold_level}\n"
            f"Concepts Already Explained: {', '.join(concepts_explained) if concepts_explained else 'None'}\n"
            f"Candidate Expressed Difficulties: {', '.join(expressed_difficulties) if expressed_difficulties else 'None'}\n"
            f"Detected Pedagogical Intent: {detected_intent}\n\n"
            f"SPECIFIC DIRECTIVE FOR THIS TURN:\n{specific_directive}\n\n"
            "COMMUNICATION & TEACHING STANDARDS (PHASE 8):\n"
            "- ALWAYS ANSWER THE CANDIDATE'S ACTUAL QUESTION FIRST before introducing new material or asking follow-up questions.\n"
            "- SIMPLE AND DIRECT ENGLISH BY DEFAULT: Use short sentences (15-20 words max per sentence).\n"
            "- Prefer accessible, everyday vocabulary before introducing specialized jargon.\n"
            "- Use one concrete, relatable real-world analogy.\n"
            "- Emphasize the key technical distinction and operational trade-off.\n"
            "- Keep responses readable, punchy, and conversational: NO academic walls of text, NO multi-page essays, NO giant dense tables.\n"
            "- End with one focused, friendly check question to verify intuition.\n\n"
            "TEACHING RULES:\n"
            "- Directly address the candidate's specific question rather than repeating generic introductory text.\n"
            "- For beginner/intuitive explanations, produce a concise 6-step lesson without textbook chapters, massive tables, or multiple headings.\n"
            "- Build progressively on prior turns without resetting the conversation.\n"
            "- Use clean Markdown formatting with headers, bullet lists, and code blocks.\n\n"
            "DISTRIBUTED SYSTEMS AND TRANSACTIONAL BOUNDARY INVARIANTS:\n"
            "- Internal Database Atomicity: When the business modification (e.g. balance ledger) and the idempotency record live in the SAME relational database, wrap them in a single ACID transaction (BEGIN ... COMMIT). Both commit or roll back atomically; no partial-commit failure window exists.\n"
            "- External Distributed Boundary: When calling an external third-party API (e.g. Stripe, Adyen, downstream microservice), an internal DB transaction CANNOT wrap an external network call. If the server crashes after the external service executes the charge but before the local record/cache is persisted:\n"
            "  1. The client's retry must NOT execute a blind re-charge.\n"
            "  2. Pass the client's Idempotency-Key downstream to the payment gateway so the gateway deduplicates.\n"
            "  3. Write a PENDING/INTENT record locally before making the external call.\n"
            "  4. On retry/recovery, query the external gateway by idempotency key or reconcile via webhooks before making any state changes.\n"
            "- Challenges & Edge Cases: When a candidate challenges an earlier claim, asks edge-case questions (e.g. Redis network partitions, Two Generals problem, timeout retries), address their specific point directly with technical depth without resetting the conversation."
        )
        system_prompt += f"\n\nRecent Dialogue History:\n{history_str}\n"
        t_prompt_construction_sec = time.perf_counter() - t_prompt_start

        # Step 4: Provider Selection and Connection Setup
        t_provider_select_start = time.perf_counter()
        provider = get_llm_provider(task="routine")
        t_provider_setup_sec = time.perf_counter() - t_provider_select_start

        assistant_content = ""
        provider_name = ""
        t_llm_total_sec = 0.0
        t_ttft_sec = None
        t_fallback_sec = 0.0
        is_fallback = False

        # Step 5: Execute Model Inference with Bounded Configurable Timeout
        t_llm_start = time.perf_counter()
        try:
            task_type_label = "guided_practice" if (detected_intent and "practice" in str(detected_intent).lower()) else "coaching_turn"
            req = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_message,
                temperature=0.25,
                max_tokens=800,
                response_json=False,
                metadata={"task_type": task_type_label},
            )
            llm_timeout = float(getattr(ai_settings, "nvidia_nim_timeout", 40.0))
            resp = await asyncio.wait_for(provider.generate(req), timeout=llm_timeout)
            t_llm_total_sec = time.perf_counter() - t_llm_start
            t_ttft_sec = getattr(resp, "ttft_sec", None) or t_llm_total_sec

            if resp and resp.content and len(resp.content.strip()) > 35:
                content_cand = resp.content.strip()
                if not content_cand.lower().startswith("error:"):
                    assistant_content = content_cand
                    base_prov = getattr(provider, "provider_name", type(provider).__name__)
                    model_id = getattr(provider, "default_model", getattr(provider, "model", None))
                    provider_name = f"{base_prov}:{model_id}" if model_id else base_prov
        except Exception as e:
            t_llm_total_sec = time.perf_counter() - t_llm_start
            logger.warning(
                f"Coaching turn LLM failure ({type(provider).__name__}) after {t_llm_total_sec:.3f}s: {e}. "
                "Attempting failover provider fallback...",
                exc_info=True,
            )
            # Bi-directional Failover:
            # If primary was NVIDIA NIM -> failover to Gemini
            # If primary was Gemini -> failover to NVIDIA NIM
            try:
                from backend.infrastructure.ai.gemini_provider import GeminiLLMProvider
                from backend.infrastructure.ai.nvidia_nim_provider import NvidiaNIMLLMProvider
                from backend.infrastructure.ai.telemetry import ai_telemetry

                failover_provider = None
                if isinstance(provider, NvidiaNIMLLMProvider) and ai_settings.gemini_api_key:
                    failover_provider = GeminiLLMProvider()
                elif isinstance(provider, GeminiLLMProvider) and ai_settings.nvidia_nim_api_key:
                    failover_provider = NvidiaNIMLLMProvider()

                if failover_provider is not None:
                    ai_telemetry.record_fallback(
                        primary_provider=getattr(provider, "provider_name", "nvidia_nim"),
                        fallback_provider=getattr(failover_provider, "provider_name", "gemini"),
                        task_type="coaching_turn",
                        reason=str(e)[:150],
                    )
                    f_resp = await asyncio.wait_for(failover_provider.generate(req), timeout=15.0)
                    if f_resp and f_resp.content and len(f_resp.content.strip()) > 35:
                        content_cand = f_resp.content.strip()
                        if not content_cand.lower().startswith("error:"):
                            assistant_content = content_cand
                            base_prov = getattr(failover_provider, "provider_name", type(failover_provider).__name__)
                            model_id = getattr(failover_provider, "default_model", getattr(failover_provider, "model", None))
                            provider_name = f"{base_prov}:{model_id}" if model_id else base_prov
                            logger.info(f"Failover provider '{provider_name}' successfully handled coaching turn.")
            except Exception as sec_e:
                logger.warning(f"Failover provider fallback also failed: {sec_e}")

        # Step 6: Fallback Activation if Live Inference Failed or Timed Out
        if not assistant_content:
            is_fallback = True
            t_fallback_start = time.perf_counter()
            from backend.infrastructure.ai.telemetry import ai_telemetry
            ai_telemetry.record_fallback(
                primary_provider=getattr(provider, "provider_name", "nvidia_nim"),
                fallback_provider="deterministic_adaptive_curriculum",
                task_type="coaching_turn",
                reason="all_live_inference_providers_unavailable",
            )
            assistant_content = self._synthesize_adaptive_teaching_response(
                intent=detected_intent,
                focus_key=selected_key,
                focus_skill=effective_skill,
                target_role=effective_role,
                user_message=user_message,
                convo_meta=convo_meta,
            )
            t_fallback_sec = time.perf_counter() - t_fallback_start
            provider_name = "adaptive_curriculum_fallback"
            if not assistant_content.startswith("> ⚠️"):
                assistant_content = (
                    "> ⚠️ **Live AI Provider Unavailable** (Deterministic Fallback Activated)\n\n"
                    f"*Your query*: \"{user_message[:120]}\"\n\n"
                    f"*Active Competency*: **{effective_skill}**\n\n"
                    + assistant_content
                    + "\n\n---\n*Note: Live model generation was unreachable. You can retry your question.*"
                )

        # Step 7: Persist Assistant Message & Update Conversation Metadata
        t_db_persist_start = time.perf_counter()
        if ui_card is None:
            ui_card = {}
        ui_card["provider_used"] = provider_name
        ui_card["is_fallback"] = is_fallback
        ui_card["teaching_stage"] = new_stage

        # Compute Granular Stage Timings
        stage_timings = {
            "history_retrieval_ms": round(t_history_retrieval_sec * 1000, 2),
            "user_persistence_ms": round(t_user_persist_sec * 1000, 2),
            "prompt_construction_ms": round(t_prompt_construction_sec * 1000, 2),
            "provider_setup_ms": round(t_provider_setup_sec * 1000, 2),
            "ttft_ms": round(t_ttft_sec * 1000, 2) if t_ttft_sec is not None else None,
            "llm_generation_ms": round(t_llm_total_sec * 1000, 2) if not is_fallback else None,
            "fallback_activation_ms": round(t_fallback_sec * 1000, 2) if is_fallback else None,
            "db_persistence_ms": 0.0,
            "total_backend_ms": round((time.perf_counter() - t_turn_start) * 1000, 2),
        }
        ui_card["stage_timings"] = stage_timings

        asst_msg = await self.convo_repo.add_message(
            conversation_id=conversation_id,
            role=ChatRole.ASSISTANT.value,
            content=assistant_content,
            message_type="card" if ui_card and ui_card.get("type") else "text",
            ui_payload=ui_card,
            intent=ChatIntent.COACHING.value,
        )

        # Update metadata state
        convo_meta["active_phase"] = new_phase
        convo_meta["teaching_stage"] = new_stage
        convo_meta["scaffold_level"] = scaffold_level
        convo_meta["turn_count"] = convo_meta.get("turn_count", 0) + 1
        convo_meta["concepts_already_explained"] = concepts_explained
        convo_meta["expressed_difficulties"] = expressed_difficulties
        convo_meta["intent_history"] = intent_history
        convo_meta["provider_used"] = provider_name
        convo_meta["last_stage_timings"] = stage_timings

        # Extract last asked question if assistant ended with a question
        if "?" in assistant_content:
            question_lines = [line.strip() for line in assistant_content.split("\n") if "?" in line]
            if question_lines:
                convo_meta["last_question_asked"] = question_lines[-1]

        convo.metadata_ = convo_meta
        flag_modified(convo, "metadata_")

        # Step 8: Persist Evidence-Backed Skill State Progression
        if effective_cand_id:
            try:
                existing_state = await self.skill_state_repo.get_by_candidate_and_skill(
                    effective_cand_id, effective_skill
                )
                curr_mastery = existing_state.mastery_estimate if existing_state else 0.50
                curr_uncertainty = existing_state.mastery_uncertainty if existing_state else 0.40
                curr_transfer_level = existing_state.highest_transfer_level if existing_state else "L0_RECALL"
                curr_adi = existing_state.assistance_dependency_index if existing_state else 0.5
                curr_failures = list(existing_state.recurring_failure_types or []) if existing_state else []

                # Core Invariant: Coach explaining something never increases mastery.
                # Only candidate-demonstrated understanding, reasoning, or transfer performance updates mastery.
                if is_candidate_answering:
                    cog_und = cognitive_eval.get("understanding_type")
                    det_misc = cognitive_eval.get("detected_misconceptions", [])

                    # 1. Misconceptions & Flawed Reasoning: No mastery gain, increase ADI, record failure modes
                    if cog_und in (CognitiveUnderstandingType.MISCONCEPTION, CognitiveUnderstandingType.INCORRECT_REASONING):
                        for m in det_misc:
                            if m not in curr_failures:
                                curr_failures.append(m)
                        new_adi = min(1.0, curr_adi + 0.10)
                        new_uncertainty = min(0.60, max(curr_uncertainty, 0.40))
                        await self.skill_state_repo.upsert_skill_state(
                            candidate_id=effective_cand_id,
                            skill_name=effective_skill,
                            mastery_estimate=curr_mastery,
                            mastery_uncertainty=new_uncertainty,
                            highest_transfer_level=curr_transfer_level,
                            assistance_dependency_index=new_adi,
                            recurring_failure_types=curr_failures,
                            assessed_at=datetime.utcnow(),
                        )

                    # 2. Memorized Definitions: Verify application before awarding mastery bump
                    elif cog_und == CognitiveUnderstandingType.MEMORIZED_DEFINITION:
                        new_uncertainty = max(0.20, curr_uncertainty * 0.95)
                        await self.skill_state_repo.upsert_skill_state(
                            candidate_id=effective_cand_id,
                            skill_name=effective_skill,
                            mastery_estimate=curr_mastery,
                            mastery_uncertainty=new_uncertainty,
                            highest_transfer_level=curr_transfer_level,
                            assistance_dependency_index=curr_adi,
                            recurring_failure_types=curr_failures,
                            assessed_at=datetime.utcnow(),
                        )

                    # 3. Genuine Understanding, Reasoning, Application & Trade-offs
                    else:
                        if current_phase == "PHASE_D_CHECK_UNDERSTANDING":
                            new_mastery = min(1.0, max(curr_mastery, 0.65))
                            new_uncertainty = max(0.15, curr_uncertainty * 0.85)
                            new_level = "L1_NEAR_TRANSFER" if curr_transfer_level == "L0_RECALL" else curr_transfer_level
                            new_adi = max(0.0, curr_adi - 0.05)
                            await self.skill_state_repo.upsert_skill_state(
                                candidate_id=effective_cand_id,
                                skill_name=effective_skill,
                                mastery_estimate=new_mastery,
                                mastery_uncertainty=new_uncertainty,
                                highest_transfer_level=new_level,
                                assistance_dependency_index=new_adi,
                                recurring_failure_types=curr_failures,
                                assessed_at=datetime.utcnow(),
                            )
                        elif current_phase == "PHASE_E_PRACTICE":
                            # Guided practice cannot establish L5 Independent Transfer
                            new_mastery = min(1.0, max(curr_mastery, 0.75))
                            new_uncertainty = max(0.12, curr_uncertainty * 0.80)
                            new_level = "L2_NEAR_TRANSFER" if curr_transfer_level in ("L0_RECALL", "L1_NEAR_TRANSFER") else curr_transfer_level
                            new_adi = max(0.0, curr_adi - 0.10)
                            await self.skill_state_repo.upsert_skill_state(
                                candidate_id=effective_cand_id,
                                skill_name=effective_skill,
                                mastery_estimate=new_mastery,
                                mastery_uncertainty=new_uncertainty,
                                highest_transfer_level=new_level,
                                assistance_dependency_index=new_adi,
                                recurring_failure_types=curr_failures,
                                assessed_at=datetime.utcnow(),
                            )
                        elif current_phase == "PHASE_F_TRANSFER":
                            # Distinguish unassisted independent performance from guided practice
                            if scaffold_level == "INDEPENDENT" and detected_intent != PedagogicalIntent.HINT_REQUEST:
                                new_mastery = min(1.0, max(curr_mastery, 0.88))
                                new_uncertainty = max(0.08, curr_uncertainty * 0.70)
                                new_level = "L5_INDEPENDENT_TRANSFER"
                                new_adi = max(0.0, curr_adi - 0.20)
                            else:
                                new_mastery = min(1.0, max(curr_mastery, 0.80))
                                new_uncertainty = max(0.10, curr_uncertainty * 0.75)
                                new_level = "L3_FAR_TRANSFER"
                                new_adi = max(0.0, curr_adi - 0.10)

                            await self.skill_state_repo.upsert_skill_state(
                                candidate_id=effective_cand_id,
                                skill_name=effective_skill,
                                mastery_estimate=new_mastery,
                                mastery_uncertainty=new_uncertainty,
                                highest_transfer_level=new_level,
                                assistance_dependency_index=new_adi,
                                recurring_failure_types=curr_failures,
                                assessed_at=datetime.utcnow(),
                            )
            except Exception as e:
                logger.warning(f"Failed to persist skill state evaluation in coaching turn: {e}")

        await self.session.commit()
        t_db_persist_sec = time.perf_counter() - t_db_persist_start
        stage_timings["db_persistence_ms"] = round(t_db_persist_sec * 1000, 2)
        stage_timings["total_backend_ms"] = round((time.perf_counter() - t_turn_start) * 1000, 2)

        return SendMessageResponse(
            conversation_id=conversation_id,
            user_message=ConversationMessageDTO.model_validate(user_msg),
            assistant_message=ConversationMessageDTO.model_validate(asst_msg),
            detected_intent=ChatIntent.COACHING,
            is_fallback=is_fallback,
            provider_used=provider_name,
            stage_timings=stage_timings,
        )

    def _synthesize_adaptive_teaching_response(
        self,
        intent: str,
        focus_key: str,
        focus_skill: str,
        target_role: str,
        user_message: str,
        convo_meta: Dict[str, Any],
    ) -> str:
        """
        Honest, stateful, deterministic adaptive curriculum fallback.
        Ensures substantive pedagogical progression without repeating generic templates.
        """
        footer = "\n\n> 📚 *Curriculum Track: Adaptive Learning Studio Fallback (Offline Mode)*"
        msg_lower = (user_message or "").strip().lower()

        # -------------------------------------------------------------
        # Universal Direct Query Handlers (Direct answers to candidate inquiries)
        # -------------------------------------------------------------
        # 1. Database Indexing
        if "index" in msg_lower and any(kw in msg_lower for kw in ["what", "explain", "how", "why", "meaning", "work", "simply", "eli5"]):
            return (
                "### 📖 What is Database Indexing?\n\n"
                "Imagine a 1,000-page textbook. If you want to find 'photosynthesis', you don't read every page. You check the index at the back. It points you to the exact page immediately.\n\n"
                "A database index works the same way:\n"
                "- **Without an index**: The database must read every row on disk. This is called a Full Table Scan. On 10 million rows, this takes seconds or minutes.\n"
                "- **With an index**: The database maintains a balanced search tree (usually a **B-Tree**). It finds any specific row in just 3 or 4 disk reads (O(log N) time).\n\n"
                "#### ⚖️ The Key Trade-Off:\n"
                "- **Faster Reads**: `SELECT` queries finish in single-digit milliseconds.\n"
                "- **Slower Writes**: Every `INSERT`, `UPDATE`, or `DELETE` must also update the index tree.\n"
                "- **Disk Cost**: Indexes take additional RAM and SSD storage space.\n\n"
                "**Quick Intuition Check**:\n"
                "If an analytics table has 10 million rows and receives 99% read queries and only 1% writes, would adding an index on `customer_id` be a good architectural choice?"
                + footer
            )

        # 2. Redis & In-Memory Stores
        if "redis" in msg_lower and any(kw in msg_lower for kw in ["why", "what", "used", "use", "purpose", "how"]):
            return (
                "### ⚡ Why is Redis Used?\n\n"
                "Redis is an in-memory key-value data store. Unlike traditional databases that write to disk, Redis stores data in RAM.\n\n"
                "Engineers choose Redis for three primary reasons:\n"
                "1. **Microsecond Speed**: Reading from RAM takes less than 1 millisecond. Querying a disk-based database often takes 20 to 100 milliseconds.\n"
                "2. **High Throughput**: A single Redis node can handle over 100,000 operations per second.\n"
                "3. **Atomic Operations**: Redis executes commands single-threaded. Commands like `INCR`, `SET NX` (set if not exists), and `LPUSH` run atomically without concurrency race conditions.\n\n"
                "#### ⚖️ The Key Trade-Off:\n"
                "- **Cost**: RAM is significantly more expensive than hard drives or SSDs.\n"
                "- **Volatility**: If a server loses power, data in RAM disappears unless you enable disk persistence (AOF or RDB).\n\n"
                "**Quick Intuition Check**:\n"
                "In a payment system, would you use Redis as the primary database for financial records, or as a cache and lock manager in front of PostgreSQL?"
                + footer
            )

        # 3. SQL vs NoSQL Comparison
        if ("sql" in msg_lower and "nosql" in msg_lower) or (intent == PedagogicalIntent.COMPARISON and any(k in msg_lower for k in ["sql", "database", "relational"])):
            return (
                "### 🔄 SQL vs NoSQL: The Core Differences\n\n"
                "The choice between SQL and NoSQL comes down to data structure, consistency guarantees, and how your application scales.\n\n"
                "#### 1. SQL (Relational Databases)\n"
                "- **Examples**: PostgreSQL, MySQL, SQLite.\n"
                "- **Data Model**: Rigid tables with strict columns, data types, and foreign keys.\n"
                "- **Transactions**: Strong ACID guarantees. Transactions either succeed completely or roll back.\n"
                "- **Best For**: Financial ledgers, complex multi-table joins, and data where integrity is paramount.\n\n"
                "#### 2. NoSQL (Non-Relational Stores)\n"
                "- **Examples**: MongoDB (Documents), DynamoDB / Cassandra (Wide-Column), Redis (Key-Value).\n"
                "- **Data Model**: Flexible, schema-less JSON documents or key-value pairs.\n"
                "- **Scaling**: Designed for horizontal scaling across distributed server clusters.\n"
                "- **Best For**: Real-time event streams, user activity feeds, and rapid prototyping with evolving schemas.\n\n"
                "#### ⚖️ Rule of Thumb:\n"
                "- Pick **SQL** when you need strict consistency and relational integrity.\n"
                "- Pick **NoSQL** when you need massive horizontal write volume and schema flexibility.\n\n"
                "**Quick Intuition Check**:\n"
                "If you are designing the bank account balance service for an online store, which type would you choose and why?"
                + footer
            )

        # 4. Why Answer Is Wrong / Flawed
        if intent == PedagogicalIntent.WHY_WRONG or any(kw in msg_lower for kw in ["why is my answer wrong", "why was that wrong", "where is my error", "what did i do wrong"]):
            return (
                "### 💡 Why Your Answer Was Incomplete or Flawed\n\n"
                "In system design and technical interviews, solutions that work on a local computer often fail under concurrent production traffic.\n\n"
                "Here is the exact reason your proposed answer had a failure window:\n"
                "- **Non-Atomic Operations**: Checking a condition first (`if not exists`) and then saving a record creates a Time-of-Check to Time-of-Use (TOCTOU) gap. Two concurrent requests can both pass the check before either saves.\n"
                "- **External Network Boundaries**: Local database transactions cannot roll back third-party API calls (like Stripe or SMS gateways). If the gateway charges the card before your database commits, an error results in a double charge.\n\n"
                "#### The Fix:\n"
                "Always reserve an **atomic lock** or pass a unique **Idempotency-Key** to the payment gateway before making the call.\n\n"
                "Does this distinction between single-threaded code and distributed concurrency make sense?"
                + footer
            )

        # 5. How It Works in a Real System
        if intent == PedagogicalIntent.HOW_QUESTION or "real system" in msg_lower or "production system" in msg_lower:
            return (
                "### ⚙️ How This Works in a Real Production System\n\n"
                "In production microservices, high-reliability APIs follow a strict 5-step execution pipeline:\n\n"
                "1. **Client Request**: The mobile app generates a unique UUID `Idempotency-Key` and attaches it as an HTTP header.\n"
                "2. **Atomic Lock**: The API Gateway attempts to claim the key in Redis: `SET idemp:uuid 'IN_PROGRESS' NX EX 120`. If the key already exists, it immediately returns `HTTP 409 Conflict` or the cached result.\n"
                "3. **Business Execution**: The service charges the payment gateway (passing the same idempotency key) and records the balance in PostgreSQL.\n"
                "4. **Response Caching**: The completed JSON response is saved in Redis with a 24-hour expiration.\n"
                "5. **Client Retry**: If a cellular network drop causes the phone to retry, Redis serves the cached 200 OK instantly without touching the payment processor.\n\n"
                "If the worker crashes mid-transaction, the 120-second TTL expires automatically so the client can safely retry without deadlock.\n\n"
                "Does this end-to-end production pipeline make the architecture clear?"
                + footer
            )

        # 6. Socratic Quiz / Understanding Check
        if intent == PedagogicalIntent.CHECK_UNDERSTANDING or any(kw in msg_lower for kw in ["quiz me", "ask me a question", "test me", "test my understanding"]):
            return (
                "### ❓ Conceptual Quiz on API Reliability\n\n"
                "Let's test your intuition with a classic Staff Engineer interview scenario:\n\n"
                "> **The Production Scenario**:\n"
                "> A customer clicks 'Confirm Payment' for a $200 airline ticket on their phone.\n"
                "> 1. Your API server receives the request and successfully charges their credit card through Stripe.\n"
                "> 2. Just as the server starts writing the confirmation to your database, the server loses power and reboots.\n"
                "> 3. Five seconds later, the user's phone times out and retries the exact same checkout request.\n\n"
                "**Question for You**:\n"
                "How does an Idempotency-Key protect the customer from being charged a second $200 during this retry?"
                + footer
            )

        # -------------------------------------------------------------
        # Competency: API Idempotency & Concurrency Control
        # -------------------------------------------------------------
        if focus_key == "api_idempotency":
            if intent == PedagogicalIntent.TEACH_FROM_BEGINNING:
                return (
                    "### 📚 Teaching from First Principles: Why Idempotency Is Necessary\n\n"
                    "Let's step back and build this up from the very foundation—starting with the physics of distributed systems before writing any code.\n\n"
                    "#### 1. The Core Dilemma: The Fallacy of the Network\n"
                    "In a single computer program, a function call either succeeds or fails. But across a network, there are **three** possible outcomes when a client sends a request:\n"
                    "1. **Success**: The server received the request, processed it, and returned a response.\n"
                    "2. **Explicit Failure**: The server actively rejected the request (e.g., 400 Bad Request, invalid payload).\n"
                    "3. **Unknown (Network Timeout)**: The client sent the request, but 5 seconds later has received nothing back.\n\n"
                    "Did the request get lost on the way to the server? Or did the server successfully process it, but the network connection died right before sending the response? **The client cannot know.**\n\n"
                    "#### 2. The Inevitability of Retries (At-Least-Once Delivery)\n"
                    "Because the client cannot tell whether the server did the work, standard distributed client libraries automatically retry the request.\n"
                    "- This guarantees **At-Least-Once Delivery**: The operation is guaranteed to reach the server, but network jitter means it might execute 2, 3, or 5 times!\n"
                    "- If the operation is charging a credit card $100, retrying without protection charges the customer multiple times.\n\n"
                    "#### 3. What Idempotency Guarantees\n"
                    "An operation is **idempotent** if applying it multiple times produces the exact same outcome as applying it once:\n"
                    "`f(f(x)) = f(x)`\n\n"
                    "In backend APIs, the client attaches a unique identifier to every request: the **Idempotency Key** (a UUID). The server uses this key as a contract: *'No matter how many times I receive this key, I will only execute the state modification once, and return the identical result every time.'*\n\n"
                    "---\n"
                    "🎯 **A Quick Check Before We Continue**:\n"
                    "Does the fundamental difference between network delivery (at-least-once) and idempotency (execute-once) make intuitive sense, or would you like to explore an everyday analogy first?"
                    + footer
                )

            elif intent in (PedagogicalIntent.SIMPLIFY_BEGINNER, PedagogicalIntent.FOUNDATIONAL_EXPLANATION):
                return (
                    "### 💡 Intuitive Mental Model: API Idempotency\n\n"
                    "**1. Core Concept**:\n"
                    "In backend APIs, idempotency means that making the exact same request multiple times produces the exact same outcome as making it once. If a network timeout causes a client to retry, the server must never re-execute the mutation or double-charge the user; instead, it returns the original result.\n\n"
                    "**2. Analogy**:\n"
                    "Think of an elevator call button: pressing the button once illuminates it and summons the elevator. Pressing it five more times rapidly does not summon five separate elevators or make it arrive five times faster.\n\n"
                    "**3. Technical Connection**:\n"
                    "In distributed systems, the client sends a unique identifier called an `Idempotency-Key` (like pressing the button). The server checks if it has already seen this key; if it has, it returns the already-computed response rather than performing a duplicate action.\n\n"
                    "**4. Practical Example**:\n"
                    "```python\n"
                    "# Atomically claim the key in Redis (NX = only set if Not Exists)\n"
                    "acquired = redis.set(f\"idemp:{key}\", \"IN_PROGRESS\", nx=True, ex=120)\n"
                    "if not acquired:\n"
                    "    # Already exists: return in-progress conflict or cached response\n"
                    "    return get_cached_response_or_409(key)\n\n"
                    "result = execute_payment(amount)\n"
                    "redis.set(f\"idemp:{key}\", result, ex=86400)\n"
                    "return result\n"
                    "```\n\n"
                    "**5. Common Candidate Mistake**:\n"
                    "Candidates often check if the key exists and then insert it in two separate steps without an atomic lock. In high-concurrency environments, two identical requests arriving at the exact same millisecond will both pass the check and double-charge the customer.\n\n"
                    "**6. Check Your Understanding**:\n"
                    "What should the server do if a second request with the same idempotency key arrives while the first request is still executing?\n\n"
                    "Take a moment to reply with your thoughts!"
                    + footer
                )

            elif intent == PedagogicalIntent.MISCONCEPTION_CORRECTION:
                return (
                    "### ⚠️ Common Interview Mistakes: API Idempotency & Concurrency\n\n"
                    "Here are the top three pitfalls candidates fall into during system design interviews:\n\n"
                    "1. **Non-Atomic Check-Then-Insert (TOCTOU)**: Writing `if not exists: insert()` creates a race window where two concurrent requests both pass the check and double-execute. Always use an atomic operation like Redis `SET NX` or SQL unique constraints.\n"
                    "2. **Wrapping External APIs in DB Transactions**: Attempting to wrap an external payment call (e.g. Stripe) inside a local database transaction. Network calls cannot be rolled back by SQL; pass the idempotency key downstream instead.\n"
                    "3. **Permanent Keys Without TTL**: Forgetting to set a bounded Time-To-Live (TTL) on idempotency records, causing unbounded storage growth.\n\n"
                    "Which of these three failure modes have you encountered or designed around previously?"
                    + footer
                )

            elif intent == PedagogicalIntent.NEXT_COMPETENCY:
                return (
                    f"### 🚀 Next Competency Recommendation\n\n"
                    f"Excellent progress! You have explored the core invariants of **API Idempotency & Concurrency Control** (atomic keys, TOCTOU prevention, and external boundary isolation).\n\n"
                    f"Based on your target role as **{target_role}**, the next logical milestone on your learning roadmap is **Distributed Caching & Partitioning**.\n\n"
                    f"Would you like to transition to Distributed Caching now, or attempt an unseen transfer challenge first?"
                    + footer
                )

            elif intent == PedagogicalIntent.INDEPENDENT_TRANSFER:
                return (
                    "### 🏆 L5 Independent Transfer Challenge: Unassisted Execution\n\n"
                    "You are now attempting an **unassisted L5 Independent Transfer challenge**. No hints will be provided.\n\n"
                    "**Domain: High-Throughput Stock Trading Execution Gateway**\n"
                    "> Traders submit market buy orders over volatile network connections. Your execution engine must guarantee that:\n"
                    "> 1. A buy order with a specific client order ID executes at most once on the exchange matching engine.\n"
                    "> 2. If the matching engine takes up to 3 seconds to confirm, concurrent duplicate submissions return an immediate in-progress acknowledgment without blocking.\n"
                    "> 3. Network disconnects between your gateway and the exchange are reconciled cleanly upon reconnection.\n\n"
                    "Formulate your architectural solution, specifying the data stores, atomic invariant checks, and failure recovery flow."
                    + footer
                )

            elif intent == PedagogicalIntent.WORKED_EXAMPLE:
                return (
                    "### 🏗️ Worked Example: Staff Engineer Reasoning on Payment Checkout\n\n"
                    "Let's trace how an experienced distributed systems engineer designs a production **Payments Checkout API** where network retries must never double-charge a customer.\n\n"
                    "#### 1. The Scenario & Failure Mode\n"
                    "- User clicks 'Pay $100' in a mobile checkout app.\n"
                    "- Mobile client generates `Idempotency-Key: pay_uuid_987` and sends `POST /api/v1/payments`.\n"
                    "- The API server talks to Stripe, charges $100, and inserts the record into the database ledger.\n"
                    "- **The Failure**: Right as the server is sending the HTTP 200 response back, the user's mobile cellular connection drops.\n"
                    "- The mobile app's HTTP client catches a network timeout and automatically retries the identical POST with `Idempotency-Key: pay_uuid_987`.\n\n"
                    "#### 2. The Architectural Flow\n"
                    "```text\n"
                    "Client (Retry POST pay_uuid_987)\n"
                    "   │\n"
                    "   ▼\n"
                    "API Gateway / App Server\n"
                    "   │\n"
                    "   ├── 1. Atomic Redis Lock Check:\n"
                    "   │      redis.set(\"idemp:pay_uuid_987\", \"IN_PROGRESS\", nx=True, ex=120)\n"
                    "   │\n"
                    "   │      ──► Lock FAILED (Key already exists!)\n"
                    "   │\n"
                    "   ├── 2. Inspect Existing State:\n"
                    "   │      status = redis.get(\"idemp:pay_uuid_987\")\n"
                    "   │\n"
                    "   │      Case A: status == \"IN_PROGRESS\"\n"
                    "   │              ──► Another thread is executing! Return HTTP 409 Conflict (\"In Progress\")\n"
                    "   │\n"
                    "   │      Case B: status contains completed JSON response {\"charge_id\": \"ch_123\", \"amount\": 100}\n"
                    "   │              ──► Return cached HTTP 200 response IMMEDIATELY without touching Stripe!\n"
                    "   │\n"
                    "   └── 3. No Duplicate Charge Occurred!\n"
                    "```\n\n"
                    "#### 3. Key Invariants Preserved\n"
                    "1. **Never re-execute external side-effects**: Stripe is called exactly once.\n"
                    "2. **Transparent client recovery**: The client gets a valid 200 OK and order confirmation as if the network never dropped."
                    + footer
                )

            elif intent == PedagogicalIntent.CONCURRENCY_RACE_CONDITIONS:
                return (
                    "### ⚡ Deep Dive: What Happens When Two Requests Arrive Simultaneously?\n\n"
                    "This is the critical race condition candidates must address in system design interviews. Let's analyze the exact microsecond race condition when two identical requests hit the server at the **exact same millisecond**.\n\n"
                    "#### 1. The Naive Approach and Why It Breaks (TOCTOU Race Condition)\n"
                    "A naive implementation might write:\n"
                    "```python\n"
                    "# BROKEN NAIVE CODE:\n"
                    "existing = db.query(\"SELECT * FROM payments WHERE key = :key\", key=req_key)\n"
                    "if existing is None:\n"
                    "    # 💥 RACE WINDOW!\n"
                    "    charge_customer()\n"
                    "    db.insert(\"INSERT INTO payments (key, status) VALUES (:key, 'DONE')\", key=req_key)\n"
                    "```\n"
                    "**What happens when Request A and Request B arrive at t=0ms?**\n"
                    "- `t=0.0ms`: Request A runs `SELECT` -> finds nothing.\n"
                    "- `t=0.1ms`: Request B runs `SELECT` -> finds nothing (Request A hasn't inserted yet!).\n"
                    "- `t=0.5ms`: Request A calls `charge_customer()` -> $100 charged!\n"
                    "- `t=0.6ms`: Request B calls `charge_customer()` -> **ANOTHER $100 charged!**\n"
                    "This is a **Time-of-Check to Time-of-Use (TOCTOU)** race condition.\n\n"
                    "#### 2. The Engineered Solution: Atomic Mutual Exclusion\n"
                    "To prevent this, the check and the reservation MUST happen in a single, atomic CPU instruction that cannot be split:\n"
                    "```text\n"
                    "Request A (t=0ms) ──┐\n"
                    "                    ├─► ATOMIC MUTEX BARRIER (Redis SET key \"IN_PROGRESS\" NX EX 120)\n"
                    "Request B (t=0ms) ──┘\n"
                    "                          │\n"
                    "       ┌──────────────────┴──────────────────┐\n"
                    "       ▼                                     ▼\n"
                    "Request A: Returns True (Acquired!)    Request B: Returns False (Key exists!)\n"
                    "       │                                     │\n"
                    "Executes payment logic               Inspects key:\n"
                    "Records DB ledger                    State is \"IN_PROGRESS\"\n"
                    "Stores completed JSON response       Returns HTTP 409 Conflict\n"
                    "                                     (or polls briefly for completion)\n"
                    "```\n\n"
                    "#### 3. Database Alternative: Unique Constraints\n"
                    "If not using Redis, this invariant is enforced in relational databases via an **atomic INSERT with a UNIQUE constraint**:\n"
                    "- Request A: `INSERT INTO idempotency_keys (key, status) VALUES ('123', 'IN_PROGRESS')` -> Succeeds.\n"
                    "- Request B: `INSERT INTO idempotency_keys (key, status) VALUES ('123', 'IN_PROGRESS')` -> Raises `UniqueViolation` / duplicate key error.\n"
                    "- Request B's exception handler catches the unique violation, recognizes an in-flight duplicate, and returns `HTTP 409 Conflict`.\n\n"
                    "Does seeing the timeline of how atomic operations serialize concurrent arrivals make the race condition resolution clear?"
                    + footer
                )

            elif intent == PedagogicalIntent.SHOW_IMPLEMENTATION:
                return (
                    "### 💻 Production Implementation: API Idempotency with Redis & FastAPI\n\n"
                    "Here is a production-grade, Staff Engineer implementation in Python using FastAPI and Redis.\n\n"
                    "```python\n"
                    "import json\n"
                    "import uuid\n"
                    "from fastapi import FastAPI, Header, HTTPException, status\n"
                    "from pydantic import BaseModel\n"
                    "import redis\n\n"
                    "app = FastAPI()\n"
                    "r = redis.Redis(host=\"localhost\", port=6379, db=0, decode_responses=True)\n\n"
                    "class PaymentRequest(BaseModel):\n"
                    "    amount_cents: int\n"
                    "    currency: str\n"
                    "    recipient_account: str\n\n"
                    "@app.post(\"/api/v1/payments\")\n"
                    "def process_payment(\n"
                    "    payload: PaymentRequest,\n"
                    "    idempotency_key: str = Header(..., alias=\"Idempotency-Key\")\n"
                    "):\n"
                    "    redis_key = f\"idempotency:{idempotency_key}\"\n"
                    "    \n"
                    "    # -------------------------------------------------------------\n"
                    "    # Step 1: Atomic Claim with SET NX (Not Exists) + TTL\n"
                    "    # -------------------------------------------------------------\n"
                    "    # nx=True: Only sets if the key does NOT exist\n"
                    "    # ex=120: Expires lock after 2 minutes in case worker crashes\n"
                    "    acquired = r.set(redis_key, \"IN_PROGRESS\", nx=True, ex=120)\n"
                    "    \n"
                    "    if not acquired:\n"
                    "        # Key already exists! Check status:\n"
                    "        cached_value = r.get(redis_key)\n"
                    "        \n"
                    "        if cached_value == \"IN_PROGRESS\":\n"
                    "            # Another concurrent request is actively executing this transaction!\n"
                    "            raise HTTPException(\n"
                    "                status_code=status.HTTP_409_CONFLICT,\n"
                    "                detail=\"A request with this Idempotency-Key is currently being processed. Please retry shortly.\"\n"
                    "            )\n"
                    "        \n"
                    "        # Request previously completed! Return the cached response directly:\n"
                    "        cached_response = json.loads(cached_value)\n"
                    "        return {\n"
                    "            \"status\": \"cached\",\n"
                    "            \"message\": \"Returned from idempotent cache\",\n"
                    "            \"data\": cached_response\n"
                    "        }\n\n"
                    "    # -------------------------------------------------------------\n"
                    "    # Step 2: Execute Core Business Logic Safely\n"
                    "    # -------------------------------------------------------------\n"
                    "    try:\n"
                    "        transaction_id = f\"txn_{uuid.uuid4().hex[:10]}\"\n"
                    "        payment_result = {\n"
                    "            \"transaction_id\": transaction_id,\n"
                    "            \"amount_cents\": payload.amount_cents,\n"
                    "            \"currency\": payload.currency,\n"
                    "            \"recipient\": payload.recipient_account,\n"
                    "            \"processed_at\": \"2026-10-15T08:00:00Z\"\n"
                    "        }\n"
                    "        \n"
                    "        # ---------------------------------------------------------\n"
                    "        # Step 3: Cache the Completed Result with 24h TTL\n"
                    "        # ---------------------------------------------------------\n"
                    "        r.set(redis_key, json.dumps(payment_result), ex=86400) # 24 hour retention\n"
                    "        \n"
                    "        return {\n"
                    "            \"status\": \"created\",\n"
                    "            \"message\": \"Payment processed successfully\",\n"
                    "            \"data\": payment_result\n"
                    "        }\n"
                    "        \n"
                    "    except Exception as exc:\n"
                    "        # If business logic failed before charging, release lock so client can retry\n"
                    "        r.delete(redis_key)\n"
                    "        raise HTTPException(\n"
                    "            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n"
                    "            detail=f\"Payment processing failed: {str(exc)}\"\n"
                    "        )\n"
                    "```\n\n"
                    "#### Production Engineering Highlights:\n"
                    "1. **Atomic Acquisition (`nx=True`)**: Serializes concurrent requests with zero race conditions.\n"
                    "2. **Conflict Barrier (`409 Conflict`)**: Protects against concurrent in-flight retries.\n"
                    "3. **Fault-Tolerant TTL (`ex=120`)**: If the process crashes while charging, the lock auto-cleans so the client isn't permanently locked out.\n"
                    "4. **Permanent Response Retention (`ex=86400`)**: Caches successful responses for 24 hours."
                    + footer
                )

            elif intent == PedagogicalIntent.CHECK_UNDERSTANDING:
                return (
                    "### ❓ Conceptual Understanding Check on Idempotency\n\n"
                    "Let's test your understanding with a realistic production failure scenario:\n\n"
                    "> **The Crash Scenario**:\n"
                    "> A client submits a payment with `Idempotency-Key: pay_abc123`.\n"
                    "> 1. The server acquires the atomic lock in Redis (`IN_PROGRESS`).\n"
                    "> 2. The server calls Stripe and **successfully charges the user's card $100**.\n"
                    "> 3. The server writes the transaction to the database ledger.\n"
                    "> 4. **Crash!** Right before the server can write the completed JSON payload to Redis and send HTTP 200, the server process crashes abruptly.\n"
                    "> \n"
                    "> Five seconds later, the client times out and retries the identical request with `Idempotency-Key: pay_abc123`.\n\n"
                    "**Question for You**:\n"
                    "When the client retries, what should the recovery mechanism do to prevent charging the card a second time while still ensuring the client gets a successful response?\n\n"
                    "Take a moment to formulate your thoughts and reply here!"
                    + footer
                )

            elif intent == PedagogicalIntent.CLARIFY_ANSWER or convo_meta.get("last_cognitive_eval"):
                cog = convo_meta.get("last_cognitive_eval") or {}
                rec_act = cog.get("recommended_action")
                und_type = cog.get("understanding_type")
                det_misc = cog.get("detected_misconceptions", [])

                if rec_act == AdaptiveTeachingAction.FOUNDATIONAL_REMEDIATION:
                    return (
                        "### 🔄 Foundational Remediation: Resetting to Core Primitives\n\n"
                        "Let's pause and reset to first principles. When concurrency edge cases become confusing, the best engineering discipline is breaking the system down into its simplest observable primitives.\n\n"
                        "#### The 3 Non-Negotiable Invariants:\n"
                        "1. **Atomic In-Flight Claim**: Exactly one request can hold execution status for a given key at any moment.\n"
                        "2. **Atomic Settlement**: The balance modification and the completion marker must commit atomically.\n"
                        "3. **Durable Result Caching**: Subsequent retries return the cached response without touching business logic.\n\n"
                        "Let's test this single foundational step:\n"
                        "If a duplicate request arrives and finds that the key is currently marked `IN_PROGRESS` by another worker, what exact HTTP response status should the server return?"
                        + footer
                    )
                elif rec_act == AdaptiveTeachingAction.APPLICATION_CHECK or und_type == CognitiveUnderstandingType.MEMORIZED_DEFINITION:
                    return (
                        "### 🔍 Understanding Check: Moving Beyond Textbook Definitions\n\n"
                        "You accurately cited the mathematical definition of idempotency: `f(f(x)) = f(x)`. "
                        "However, in high-throughput distributed systems, reciting the definition isn't enough to prevent duplicate execution.\n\n"
                        "**Let's test practical application:**\n"
                        "A client sends `POST /v1/payments/charge` with `Idempotency-Key: pay_abc123`.\n"
                        "Two identical requests arrive at your API gateway at the exact same millisecond.\n\n"
                        "```python\n"
                        "# Naive Implementation\n"
                        "existing = db.query(IdempotencyRecord).filter_by(key=key).first()\n"
                        "if not existing:\n"
                        "    charge_result = stripe.charge(...)\n"
                        "    db.insert(IdempotencyRecord(key=key))\n"
                        "```\n\n"
                        "1. Why does this naive implementation fail under concurrent load?\n"
                        "2. What atomic primitive or concurrency control mechanism must replace `if not existing` to guarantee execute-once semantics?"
                        + footer
                    )
                elif rec_act == AdaptiveTeachingAction.TARGETED_MISCONCEPTION_CORRECTION or und_type in (CognitiveUnderstandingType.MISCONCEPTION, CognitiveUnderstandingType.INCORRECT_REASONING):
                    misc_str = f" ({', '.join(det_misc)})" if det_misc else ""
                    return (
                        f"### ⚠️ Architectural Misconception Correction{misc_str}\n\n"
                        "Your proposed approach is a very common interview pitfall, but in production distributed architectures it introduces critical failure modes.\n\n"
                        "#### Why This Assumption Fails Under Concurrency:\n"
                        "1. **Non-Atomic TOCTOU Window**: If two concurrent threads query before writing, both see an empty state and both execute the side-effect before any unique constraint or lock can stop them.\n"
                        "2. **External Gateway Side-Effects**: Local database transactions **cannot** roll back third-party HTTP calls (e.g., Stripe, SMS gateways). If the external call succeeds before the database aborts, the customer is double-charged.\n"
                        "3. **Deadlocks and Connection Starvation**: Attempting to resolve concurrency solely via database row-level locking under high write volume leads to database thread exhaustion and transaction deadlocks.\n\n"
                        "#### The Production Invariant:\n"
                        "You must establish an **Atomic Mutual Exclusion lock** (such as Redis `SET NX` or a distributed pre-flight reservation) *before* invoking external network side-effects. "
                        "The second concurrent request immediately receives `HTTP 409 Conflict`.\n\n"
                        "Does this distinction between external side-effects and database rollback boundaries make sense?"
                        + footer
                    )
                elif rec_act == AdaptiveTeachingAction.FOUNDATIONAL_REMEDIATION:
                    return (
                        "### 🔄 Foundational Remediation: Resetting to Core Primitives\n\n"
                        "Let's pause and reset to first principles. When concurrency edge cases become confusing, the best engineering discipline is breaking the system down into its simplest observable primitives.\n\n"
                        "#### The 3 Non-Negotiable Invariants:\n"
                        "1. **Atomic In-Flight Claim**: Exactly one request can hold execution status for a given key at any moment.\n"
                        "2. **Atomic Settlement**: The balance modification and the completion marker must commit atomically.\n"
                        "3. **Durable Result Caching**: Subsequent retries return the cached response without touching business logic.\n\n"
                        "Let's test this single foundational step:\n"
                        "If a duplicate request arrives and finds that the key is currently marked `IN_PROGRESS` by another worker, what exact HTTP response status should the server return?"
                        + footer
                    )
                elif rec_act == AdaptiveTeachingAction.ADVANCE_TO_INDEPENDENT_TRANSFER or und_type == CognitiveUnderstandingType.TRADE_OFF_ANALYSIS:
                    return (
                        "### 🎯 Advanced Architectural Reasoning & Trade-Off Analysis\n\n"
                        "Outstanding analysis! You demonstrated genuine conceptual understanding by articulating the architectural trade-offs between local ACID serialization and distributed external failure boundaries.\n\n"
                        "Because you have demonstrated solid conceptual mastery and trade-off discernment, let's advance directly to an **L5 Unseen Independent Transfer Challenge** to verify your ability to apply these invariants unassisted:\n\n"
                        "**Domain: Global Event Ticketing & Seat Reservation**\n"
                        "> During a flash sale, 50,000 concurrent fans attempt to reserve 5,000 seats. Multiple requests attempt to reserve the same seat simultaneously over flaky mobile connections.\n"
                        "> 1. A seat must be held for 10 minutes exclusively for the first user.\n"
                        "> 2. Duplicate clicks or retries must never double-book or charge twice.\n"
                        "> 3. Expired holds must release automatically without a background cron scan.\n\n"
                        "Formulate your architectural solution detailing data stores, atomic invariant checks, TTL expiry, and recovery flow."
                        + footer
                    )
                else:
                    return (
                        "### 🎯 Deep Dive: Validated Reasoning & Concurrency Invariant Probe\n\n"
                        "Spot on! Your reasoning correctly identifies how atomic mutual exclusion and idempotent replay work together to guarantee execute-once semantics.\n\n"
                        "#### The In-Depth Failure Recovery Probe:\n"
                        "Suppose your server successfully claims the lock, charges the customer through Stripe, and writes the ledger to the database. "
                        "Right before it can cache the final result in Redis, the server process crashes due to an Out-Of-Memory (OOM) panic.\n\n"
                        "When the client times out and retries with the same `Idempotency-Key` 10 seconds later:\n"
                        "1. How does your recovery architecture ensure the customer is NOT charged a second time?\n"
                        "2. How does the server retrieve and return the completed payment payload to the client?\n\n"
                        "Take a moment to formulate your thoughts and reply here!"
                        + footer
                    )

            elif intent == PedagogicalIntent.EXPLAIN_THOROUGHLY:
                return (
                    "### 🔍 Comprehensive Deep Dive: The 3-Phase Idempotency Execution Lifecycle\n\n"
                    "Let's break down the end-to-end architecture into its three strict lifecycle phases, along with the invariant boundaries of each.\n\n"
                    "#### Phase 1: Atomic Key Reservation (The Invariant Barrier)\n"
                    "Before touching any business logic, databases, or payment gateways, the incoming request must cross an atomic reservation gate.\n"
                    "- **The Invariant**: Exactly one thread across the entire distributed cluster can hold execution rights for `Idempotency-Key: K` at any instant.\n"
                    "- **Mechanism**: Distributed lock (`SET NX EX`) or relational database row with a unique constraint.\n"
                    "- **Outcomes**:\n"
                    "  - `Acquired`: Thread proceeds to Phase 2.\n"
                    "  - `Failed - In Progress`: Return `HTTP 409 Conflict`.\n"
                    "  - `Failed - Completed`: Parse cached response payload and return `HTTP 200 OK` immediately.\n\n"
                    "#### Phase 2: Transaction Execution & State Modification\n"
                    "Once the key is reserved, the core domain logic executes.\n"
                    "- **Two-Phase Idempotency with DB Ledger**: If your database is Postgres, the safest pattern is storing the idempotency record inside the *same atomic database transaction* as the financial ledger write.\n"
                    "  ```sql\n"
                    "  BEGIN;\n"
                    "  INSERT INTO payments (id, amount, account) VALUES (...);\n"
                    "  INSERT INTO idempotency_records (key, response_payload, status) VALUES (...);\n"
                    "  COMMIT;\n"
                    "  ```\n"
                    "  This guarantees that the ledger entry and the idempotency record either both commit, or both roll back together.\n"
                    "- **External Gateway Boundary**: For external side-effects (e.g. Stripe), pass the idempotency key downstream to prevent double charges across network boundaries.\n\n"
                    "#### Phase 3: Result Caching & Bounded TTL Eviction\n"
                    "- After committing the state change, the final HTTP status code and response body are cached under key `K`.\n"
                    "- **TTL Strategy**: Idempotency records should NOT live forever. Standard practice is a 24- to 72-hour TTL. After 72 hours, retries are considered stale and require a fresh request."
                    + footer
                )

            elif intent == PedagogicalIntent.TRANSFER_CHALLENGE:
                return (
                    "### 🧪 Unseen Transfer Challenge (Targeting L5 Independent Transfer)\n\n"
                    "Now that we've covered the core invariants of idempotency and atomic locking, let's test whether you can apply "
                    "these same structural principles to a completely different domain context.\n\n"
                    "**Domain: Global Event Ticketing & Seat Reservation**\n"
                    "> During a stadium concert release, 50,000 users are competing for 5,000 seats. "
                    "When a user selects Seat A12 and clicks 'Reserve', your backend service must guarantee that:\n"
                    "> 1. A12 is reserved for exactly that user for a 10-minute checkout hold.\n"
                    "> 2. Network timeouts or duplicate clicks never create double-bookings.\n"
                    "> 3. If the user does not complete checkout within 10 minutes, the seat automatically becomes available to other users without a long-running batch job.\n\n"
                    "**Your Task**: Outline your architectural solution detailing the data store, atomic state invariants, "
                    "and how you handle concurrency. Formulate your solution below!"
                    + footer
                )

            elif intent == PedagogicalIntent.HINT_REQUEST:
                return (
                    "### 💡 Socratic Hint on Idempotency & Locking\n\n"
                    "Consider the relationship between **time-to-live (TTL)** and **atomic conditional updates**:\n"
                    "- What happens if you store an `expires_at` timestamp directly inside the lock record?\n"
                    "- How can you use database transactions with `WHERE expires_at < NOW()` or Redis key expiration "
                    "to ensure expired state cleans itself up automatically?"
                    + footer
                )

            elif intent == PedagogicalIntent.GUIDED_PRACTICE:
                return (
                    "### 🛠️ Guided Practice: Designing an Idempotent Webhook Consumer\n\n"
                    "Let's practice by designing an inbound webhook handler for Stripe payment events:\n\n"
                    "- Stripe sends `payment_intent.succeeded` webhooks to your service.\n"
                    "- Stripe guarantees at-least-once delivery, meaning you may receive the same webhook event ID multiple times.\n"
                    "- Your handler must fulfill the customer's order, provision user access, and send a confirmation email.\n\n"
                    "**Your Challenge**: Write down the 3-step sequence your webhook consumer must execute upon receiving event `evt_123` to guarantee the customer's account is only provisioned once."
                    + footer
                )

        # -------------------------------------------------------------
        # Competency: Distributed Caching & Partitioning
        # -------------------------------------------------------------
        elif focus_key == "distributed_caching":
            if intent == PedagogicalIntent.TEACH_FROM_BEGINNING:
                return (
                    "### 📚 Teaching from First Principles: Why Distributed Caching Is Necessary\n\n"
                    "Let's trace distributed caching from hardware physics to large-scale system topology.\n\n"
                    "#### 1. The Latency Hierarchy\n"
                    "- **CPU L1/L2 Cache**: ~1-4 nanoseconds\n"
                    "- **Main Memory (RAM / Redis)**: ~100 nanoseconds (~0.0001 ms)\n"
                    "- **NVMe SSD / Local Disk**: ~100 microseconds (0.1 ms)\n"
                    "- **Relational Database over Network**: ~5-50 milliseconds (50,000 to 500,000x slower than RAM!)\n\n"
                    "When your backend scales to 50,000 QPS, querying a relational database on every read causes connection exhaustion, disk I/O bottlenecks, and cascading latency spikes.\n\n"
                    "#### 2. Core Caching Patterns\n"
                    "1. **Cache-Aside (Lazy Loading)**: The application checks the cache. On miss, it reads from the DB, populates the cache, and returns. Simple and resilient to cache failures.\n"
                    "2. **Write-Through**: The application writes to the cache, which synchronously updates the database. Ensures freshness at the cost of write latency.\n"
                    "3. **Write-Back (Write-Behind)**: The application writes to the cache and acknowledges immediately; the cache asynchronously flushes to the DB in batches. Extreme write throughput, but risks data loss on crash.\n\n"
                    "#### 3. The Central Architectural Dilemma: Cache Invalidation\n"
                    "*\"There are only two hard things in Computer Science: cache invalidation and naming things.\"*\n"
                    "When data changes in the database, how do edge caches know their copies are stale without race conditions?\n\n"
                    "Does this latency hierarchy and cache-aside lifecycle make intuitive sense?"
                    + footer
                )
            elif intent in (PedagogicalIntent.SIMPLIFY_BEGINNER, PedagogicalIntent.FOUNDATIONAL_EXPLANATION):
                return (
                    "### 💡 Intuitive Mental Model: Distributed Caching\n\n"
                    "**1. Core Concept**:\n"
                    "A distributed cache is an in-memory storage layer situated in front of your primary database. It temporarily stores frequently read data in RAM so queries can return in sub-milliseconds without touching disk or overwhelming the database.\n\n"
                    "**2. Analogy**:\n"
                    "Think of a cache like a notepad on your desk with the day's phone numbers. Instead of walking over to the filing cabinet across the room for every call, you glance at the notepad in front of you.\n\n"
                    "**3. Technical Connection**:\n"
                    "In high-traffic systems, the application checks the cache (the notepad) first. Only on a cache miss does it query the database (the filing cabinet), and it writes the retrieved record back to the cache for future requests.\n\n"
                    "**4. Practical Example**:\n"
                    "```python\n"
                    "# Cache-Aside with Mutex Lock to prevent thundering herds\n"
                    "cached_user = cache.get(user_id)\n"
                    "if cached_user is None:\n"
                    "    with distributed_lock(f\"lock:{user_id}\", ttl=5):\n"
                    "        cached_user = db.query_user(user_id)\n"
                    "        cache.set(user_id, cached_user, ttl=300)\n"
                    "return cached_user\n"
                    "```\n\n"
                    "**5. Common Candidate Mistake**:\n"
                    "Forgetting cache stampede (the thundering herd): when a popular key expires, hundreds of concurrent threads simultaneously miss the cache and overwhelm the database. Using a mutex lock or probabilistic early expiration prevents this.\n\n"
                    "**6. Check Your Understanding**:\n"
                    "When updating a user's record in the database, should you update the cached entry or invalidate (delete) it, and why?\n\n"
                    "Take a moment to reply with your thoughts!"
                    + footer
                )
            elif intent == PedagogicalIntent.MISCONCEPTION_CORRECTION:
                return (
                    "### ⚠️ Common Interview Mistakes: Distributed Caching\n\n"
                    "Here are the top three pitfalls candidates make in caching architecture interviews:\n\n"
                    "1. **Invalidating Before Database Commit**: Deleting the cache key before the DB transaction commits creates a race where a concurrent reader fetches old uncommitted data and repopulates the cache forever.\n"
                    "2. **Unbounded Keys Without TTL**: Treating cache like a permanent database without eviction policies (LRU/LFU) or TTL, inevitably leading to Redis OOM crashes.\n"
                    "3. **Missing Virtual Nodes in Consistent Hashing**: Using basic hashing without virtual nodes, causing extreme hotspotting on individual cache partitions.\n\n"
                    "Have you encountered any of these cache synchronization pitfalls?"
                    + footer
                )
            elif intent == PedagogicalIntent.NEXT_COMPETENCY:
                return (
                    f"### 🚀 Next Competency Recommendation\n\n"
                    f"Outstanding progress! You have explored the core invariants of **Distributed Caching & Partitioning** (cache-aside, stampede mitigation, and consistent hashing).\n\n"
                    f"For your target track as **{target_role}**, the next high-value architectural competency is **Database Concurrency & Isolation Levels**.\n\n"
                    f"Would you like to start Database Concurrency, or test your unassisted skills on an unseen transfer challenge?"
                    + footer
                )
            elif intent == PedagogicalIntent.INDEPENDENT_TRANSFER:
                return (
                    "### 🏆 L5 Independent Transfer Challenge: Unassisted Execution\n\n"
                    "You are now attempting an **unassisted L5 Independent Transfer challenge**. No hints will be provided.\n\n"
                    "**Domain: Global Live Sports Leaderboard & Telemetry Ingestion**\n"
                    "> 5 million concurrent viewers follow a real-time World Cup final with 200,000 score queries per second. Your caching tier must guarantee that:\n"
                    "> 1. Score queries achieve sub-5ms p99 latency globally across 3 continents.\n"
                    "> 2. When a goal is scored, score updates propagate to viewers within 2 seconds without crushing the backend.\n"
                    "> 3. An unexpected cache node failure does not cascade to the primary relational database.\n\n"
                    "Outline your partitioning topology, cache eviction strategy, invalidation mechanism, and failure boundaries below."
                    + footer
                )
            elif intent == PedagogicalIntent.CONCURRENCY_RACE_CONDITIONS:
                return (
                    "### ⚡ Cache Stampede Mitigation under Concurrent Load\n\n"
                    "When a popular cached key expires, hundreds of concurrent requests will simultaneously encounter a cache miss.\n"
                    "- **Naive approach**: All 100 requests query the primary database to recompute the value. The DB CPU spikes to 100% and crashes.\n"
                    "- **Engineered Solution 1 (Distributed Mutex)**: Only the *first* request to detect the miss acquires a lock (`SET lock:key NX EX 5`). "
                    "That single worker queries the DB and updates the cache. The remaining 99 requests wait or receive stale data.\n"
                    "- **Engineered Solution 2 (Probabilistic Early Expiration / XFetch)**: Workers pre-emptively recompute the cache before it expires based on request frequency: `time() - delta * beta * ln(rand()) > expiry`.\n\n"
                    "Does the difference between locking on miss and probabilistic background refresh make sense?"
                    + footer
                )
            elif intent == PedagogicalIntent.WORKED_EXAMPLE:
                return (
                    "### 🏗️ Worked Example: Multi-Tier Distributed Caching with Edge Invalidation\n\n"
                    "Let's trace how a Staff Engineer designs a global **Product Catalog Cache** serving 100,000 QPS with sub-5ms p99 latency.\n\n"
                    "#### 1. Topology\n"
                    "```text\n"
                    "Client ──► Edge CDN (Cloudflare / CloudFront, TTL=30s)\n"
                    "             │ (Cache Miss)\n"
                    "             ▼\n"
                    "         API Gateway ──► Local Redis Cluster (Cluster mode, 6 shards, TTL=300s)\n"
                    "                           │ (Cache Miss)\n"
                    "                           ├──► Acquire Distributed Mutex (Redis SET lock:prod_123 NX EX 3)\n"
                    "                           │    └──► Primary Postgres Read Replica\n"
                    "                           └──► Repopulate Redis & Release Lock\n"
                    "```\n\n"
                    "#### 2. Invalidation Event Pipeline\n"
                    "When an admin updates a product price:\n"
                    "1. Update relational DB: `UPDATE products SET price = 99.00 WHERE id = 123`\n"
                    "2. Commit DB transaction FIRST.\n"
                    "3. Emit CDC event via Debezium / Kafka: `{\"event\": \"PRODUCT_UPDATED\", \"id\": 123}`\n"
                    "4. Cache invalidator consumers delete key `cache:product:123` across all Redis clusters.\n"
                    "5. Purge CDN edge tag `purge_tag('product-123')`.\n\n"
                    "Why must we invalidate AFTER the database commit, never before?"
                    + footer
                )
            elif intent == PedagogicalIntent.SHOW_IMPLEMENTATION:
                return (
                    "### 💻 Production Implementation: Cache-Aside with Mutex Stampede Lock in Python\n\n"
                    "```python\n"
                    "import asyncio\n"
                    "import json\n"
                    "from typing import Optional, Dict, Any\n"
                    "import redis.asyncio as aioredis\n\n"
                    "r = aioredis.from_url(\"redis://localhost:6379\", decode_responses=True)\n\n"
                    "async def get_product_details(product_id: str) -> Dict[str, Any]:\n"
                    "    cache_key = f\"product:{product_id}\"\n"
                    "    lock_key = f\"lock:{cache_key}\"\n\n"
                    "    # 1. Fast Path: Check Cache\n"
                    "    cached = await r.get(cache_key)\n"
                    "    if cached:\n"
                    "        return json.loads(cached)\n\n"
                    "    # 2. Cache Miss: Acquire Distributed Mutex to Prevent Stampede\n"
                    "    acquired = await r.set(lock_key, \"1\", nx=True, ex=5)\n"
                    "    if acquired:\n"
                    "        try:\n"
                    "            # Double-check cache in case another worker filled it\n"
                    "            recheck = await r.get(cache_key)\n"
                    "            if recheck:\n"
                    "                return json.loads(recheck)\n\n"
                    "            # 3. Fetch from Primary Database\n"
                    "            product_data = await fetch_from_primary_db(product_id)\n\n"
                    "            # 4. Populate Cache with TTL + Jitter\n"
                    "            ttl = 300 + int(hash(product_id) % 30)\n"
                    "            await r.set(cache_key, json.dumps(product_data), ex=ttl)\n"
                    "            return product_data\n"
                    "        finally:\n"
                    "            await r.delete(lock_key)\n"
                    "    else:\n"
                    "        # Lock held by peer worker: wait briefly and read cached result\n"
                    "        await asyncio.sleep(0.05)\n"
                    "        return await get_product_details(product_id)\n"
                    "```\n\n"
                    "Notice the TTL jitter (`300 + hash % 30`) to prevent simultaneous key expiration!"
                    + footer
                )
            elif intent == PedagogicalIntent.CHECK_UNDERSTANDING:
                return (
                    "### 🎯 Formative Check: Cache Invalidation Race Conditions\n\n"
                    "Consider this sequence of events in a high-concurrency system:\n"
                    "1. Worker A wants to update a user's address. Worker A deletes `user:101` from the cache.\n"
                    "2. Right before Worker A commits the update to Postgres, Worker B receives a read request for `user:101`.\n"
                    "3. Worker B gets a cache miss, reads the OLD address from Postgres, and puts the old address back into the cache.\n"
                    "4. Worker A finally commits the new address to Postgres.\n\n"
                    "**Question**: What is the bug here, and how does the Cache-Aside pattern prevent stale data from remaining in the cache indefinitely?"
                    + footer
                )
            elif intent == PedagogicalIntent.TRANSFER_CHALLENGE:
                return (
                    "### 🚀 Unseen Transfer Challenge: Multi-Region Distributed Cache Invalidation\n\n"
                    "You are the Lead Architect for a global SaaS application running in 3 regions: US-East, EU-Central, and AP-South.\n"
                    "- Each region has its own local Redis cache cluster.\n"
                    "- All writes go to the primary database in US-East.\n"
                    "- Network partitions between regions can last up to 30 seconds.\n\n"
                    "**Your Challenge**: Design an invalidation and read mechanism ensuring EU users never observe price changes revert to old values during cross-Atlantic network jitter."
                    + footer
                )
            elif intent == PedagogicalIntent.HINT_REQUEST:
                return (
                    "### 💡 Socratic Hint: Distributed Caching & Invalidation\n\n"
                    "Consider two architectural invariants:\n"
                    "1. **TTL as the Ultimate Safety Net**: Even if an invalidation message is lost in Kafka, bounded TTL ensures stale data self-heals.\n"
                    "2. **Version Vectors / Monotonic Timestamps**: Storing a `version` or `updated_at` timestamp inside the cache value allows readers to reject values older than their known session state."
                    + footer
                )

        # -------------------------------------------------------------
        # Competency: Database Concurrency & Isolation Levels
        # -------------------------------------------------------------
        elif focus_key == "database_concurrency":
            if intent in (PedagogicalIntent.SIMPLIFY_BEGINNER, PedagogicalIntent.FOUNDATIONAL_EXPLANATION):
                return (
                    "### 💡 Intuitive Mental Model: Database Concurrency\n\n"
                    "**1. Core Concept**:\n"
                    "Database concurrency control ensures that multiple transactions executing at the same time do not corrupt shared data or read partial, uncommitted state. It balances strict consistency against transaction throughput.\n\n"
                    "**2. Analogy**:\n"
                    "Imagine a shared spreadsheet where two people edit the same cell simultaneously. Without locking or conflict detection, the last person to hit save quietly overwrites the other person's changes without knowing it.\n\n"
                    "**3. Technical Connection**:\n"
                    "In relational databases, isolation levels define how visible one transaction's changes are to others. Optimistic Concurrency Control uses a version number to detect when another transaction modified the row while you were preparing your update.\n\n"
                    "**4. Practical Example**:\n"
                    "```sql\n"
                    "-- Optimistic Concurrency Control (OCC) with version check\n"
                    "UPDATE inventory\n"
                    "SET stock = stock - 1, version = version + 1\n"
                    "WHERE item_id = 42 AND version = 3;\n"
                    "-- If rows affected == 0, another transaction committed first; rollback and retry.\n"
                    "```\n\n"
                    "**5. Common Candidate Mistake**:\n"
                    "Assuming the default isolation level (Read Committed in Postgres) prevents update race conditions. Read Committed prevents dirty reads, but two concurrent transactions reading `stock=5` can both decrement it and produce an incorrect total without row locking or version checks.\n\n"
                    "**6. Check Your Understanding**:\n"
                    "What is the main trade-off between using Optimistic Concurrency Control (OCC) versus Pessimistic Locking (`SELECT FOR UPDATE`) under high write contention?\n\n"
                    "Take a moment to reply with your thoughts!"
                    + footer
                )
            elif intent == PedagogicalIntent.MISCONCEPTION_CORRECTION:
                return (
                    "### ⚠️ Common Interview Mistakes: Database Concurrency\n\n"
                    "Here are the top three concurrency mistakes in database design:\n\n"
                    "1. **Assuming Read Committed Prevents Lost Updates**: Read Committed allows two concurrent transactions to read the same balance ($100), deduct $10, and commit $90 instead of $80.\n"
                    "2. **Over-using Serializable Isolation**: Jumping straight to Serializable without understanding that it causes serialization failure errors (`40001`) under high throughput, requiring aggressive retry logic.\n"
                    "3. **Long-Running Transactions With Pessimistic Locks**: Holding `SELECT FOR UPDATE` while calling external network services, creating thread pool starvation and database deadlocks.\n\n"
                    "Which locking pattern do you typically reach for first in high-traffic APIs?"
                    + footer
                )
            elif intent == PedagogicalIntent.NEXT_COMPETENCY:
                return (
                    f"### 🚀 Next Competency Recommendation\n\n"
                    f"Great progress! You have explored the core invariants of **Database Concurrency & Isolation Levels** (OCC, MVCC, and deadlocks).\n\n"
                    f"Next on your learning roadmap for **{target_role}** is **Circuit Breaking & Backpressure Resilience**.\n\n"
                    f"Ready to explore Resilience Patterns, or would you like to solve a transfer challenge first?"
                    + footer
                )
            elif intent == PedagogicalIntent.INDEPENDENT_TRANSFER:
                return (
                    "### 🏆 L5 Independent Transfer Challenge: Unassisted Execution\n\n"
                    "You are now attempting an **unassisted L5 Independent Transfer challenge**. No hints will be provided.\n\n"
                    "**Domain: Flash Sale Ticket Reservation Ledger**\n"
                    "> 100,000 customers compete for 5,000 concert tickets simultaneously. Your database layer must guarantee that:\n"
                    "> 1. Exact zero inventory overselling occurs under maximum concurrency.\n"
                    "> 2. Database transactions complete under 15ms without cascading deadlocks.\n"
                    "> 3. Failed transactions during high lock contention retry gracefully without customer session drops.\n\n"
                    "Detail your database schema, isolation level, locking strategy, and retry backoff mechanics."
                    + footer
                )
            elif intent == PedagogicalIntent.TEACH_FROM_BEGINNING:
                return (
                    "### 📚 Teaching from First Principles: Database Isolation & ACID Guarantees\n\n"
                    "ANSI SQL defines four transaction isolation levels to balance consistency against throughput:\n\n"
                    "| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read |\n"
                    "| :--- | :--- | :--- | :--- |\n"
                    "| **Read Uncommitted** | Possible | Possible | Possible |\n"
                    "| **Read Committed** (Postgres default) | Prevented | Possible | Possible |\n"
                    "| **Repeatable Read** | Prevented | Prevented | Prevented in MVCC / Possible in locking queries |\n"
                    "| **Serializable** | Prevented | Prevented | Prevented |\n\n"
                    "Higher isolation guarantees prevent data corruption, but introduce lock contention, queuing, and serialization failures (`40001` error)."
                    + footer
                )
            elif intent == PedagogicalIntent.CONCURRENCY_RACE_CONDITIONS:
                return (
                    "### ⚡ Lost Updates & TOCTOU in Relational Databases\n\n"
                    "A classic interview trap is the **Lost Update** anomaly:\n"
                    "```sql\n"
                    "-- Transaction 1 and Transaction 2 both execute:\n"
                    "SELECT balance FROM accounts WHERE id = 10; -- returns $100 for both\n"
                    "-- Tx1 adds $50, Tx2 deducts $20\n"
                    "UPDATE accounts SET balance = 150 WHERE id = 10; -- Tx1 commits\n"
                    "UPDATE accounts SET balance = 80 WHERE id = 10;  -- Tx2 commits and OVERWRITES Tx1!\n"
                    "```\n"
                    "#### The Solution:\n"
                    "1. **Pessimistic**: `SELECT balance FROM accounts WHERE id = 10 FOR UPDATE;` (Locks the row).\n"
                    "2. **Optimistic**: `UPDATE accounts SET balance = balance + 50, version = version + 1 WHERE id = 10 AND version = 1;` (Atomic test-and-set)."
                    + footer
                )
            elif intent == PedagogicalIntent.WORKED_EXAMPLE or intent == PedagogicalIntent.SHOW_IMPLEMENTATION:
                return (
                    "### 💻 Implementation: Optimistic Concurrency Control (OCC) with Retries\n\n"
                    "```python\n"
                    "async def deduct_inventory_occ(item_id: int, quantity: int, max_retries: int = 3):\n"
                    "    for attempt in range(max_retries):\n"
                    "        async with db.transaction() as tx:\n"
                    "            # 1. Read current state and version\n"
                    "            item = await tx.fetch_one(\"SELECT stock, version FROM items WHERE id = :id\", id=item_id)\n"
                    "            if item.stock < quantity:\n"
                    "                raise ValueError(\"Insufficient stock\")\n\n"
                    "            # 2. Atomic Compare-and-Swap Update\n"
                    "            rows_updated = await tx.execute(\n"
                    "                \"\"\"\n"
                    "                UPDATE items\n"
                    "                SET stock = stock - :qty, version = version + 1\n"
                    "                WHERE id = :id AND version = :version\n"
                    "                \"\"\",\n"
                    "                id=item_id, qty=quantity, version=item.version\n"
                    "            )\n"
                    "            if rows_updated == 1:\n"
                    "                return True  # Success!\n"
                    "        # Conflict detected: another transaction committed first. Retry with backoff\n"
                    "        await asyncio.sleep(0.02 * (2 ** attempt))\n"
                    "    raise RuntimeError(\"OCC conflict limit exceeded\")\n"
                    "```"
                    + footer
                )

        # -------------------------------------------------------------
        # Competency: Circuit Breaking & Backpressure Resilience
        # -------------------------------------------------------------
        elif focus_key == "resilience_patterns":
            if intent in (PedagogicalIntent.SIMPLIFY_BEGINNER, PedagogicalIntent.FOUNDATIONAL_EXPLANATION):
                return (
                    "### 💡 Intuitive Mental Model: Resilience Patterns\n\n"
                    "**1. Core Concept**:\n"
                    "Resilience patterns protect distributed microservices from cascading failures when downstream dependencies degrade. Rather than letting a slow service exhaust system resources, resilience patterns isolate faults and fail fast.\n\n"
                    "**2. Analogy**:\n"
                    "Think of an electrical circuit breaker in your home. When a faulty appliance draws dangerous current, the breaker trips open instantly, cutting power to that single outlet so the entire house doesn't catch fire.\n\n"
                    "**3. Technical Connection**:\n"
                    "In software systems, a circuit breaker monitors calls to a downstream service. If error rates spike, the breaker trips to 'Open', instantly returning a fallback or HTTP 503 instead of tying up server worker threads for 30 seconds.\n\n"
                    "**4. Practical Example**:\n"
                    "```python\n"
                    "# Circuit Breaker state check before calling downstream service\n"
                    "if circuit_breaker.is_open(\"payment_service\"):\n"
                    "    return fallback_response(\"Payments temporarily degraded; queued for retry\", 503)\n"
                    "try:\n"
                    "    response = call_payment_service(payload, timeout=2.0)\n"
                    "    circuit_breaker.record_success(\"payment_service\")\n"
                    "except (TimeoutError, ServiceUnavailable):\n"
                    "    circuit_breaker.record_failure(\"payment_service\")\n"
                    "    raise\n"
                    "```\n\n"
                    "**5. Common Candidate Mistake**:\n"
                    "Implementing retries without exponential backoff and jitter. If an overwhelmed service is recovering, thousands of synchronized client retries hitting it at the exact same millisecond will immediately crash it again.\n\n"
                    "**6. Check Your Understanding**:\n"
                    "When a circuit breaker is in the 'Half-Open' state, what criteria determine whether it resets to 'Closed' or trips back to 'Open'?\n\n"
                    "Take a moment to reply with your thoughts!"
                    + footer
                )
            elif intent == PedagogicalIntent.MISCONCEPTION_CORRECTION:
                return (
                    "### ⚠️ Common Interview Mistakes: Resilience Patterns\n\n"
                    "Here are the top three mistakes candidates make when designing resilient distributed systems:\n\n"
                    "1. **Synchronized Retries Without Jitter**: Retrying exactly every 1000ms creates a 'retry storm' (thundering herd) that keeps the recovering downstream service perpetually offline. Always add full jitter: `backoff * random()`.\n"
                    "2. **Infinite Timeout Bounds**: Setting no HTTP timeout or arbitrary 60-second timeouts. Slow dependencies exhaust connection pools and crash upstream callers.\n"
                    "3. **Missing Bulkhead Isolation**: Using a single thread pool for all outbound RPC calls so that one hung recommendation engine blocks high-priority checkout traffic.\n\n"
                    "Have you observed these failure cascades in production services?"
                    + footer
                )
            elif intent == PedagogicalIntent.NEXT_COMPETENCY:
                return (
                    f"### 🚀 Next Competency Recommendation\n\n"
                    f"Bravo! You have developed a deep understanding of **Resilience Patterns** (circuit breaking, bulkhead isolation, and backpressure).\n\n"
                    f"For your target track as **{target_role}**, the next recommended milestone on your learning roadmap is **Distributed Rate Limiting & Throttling**.\n\n"
                    f"Would you like to explore Distributed Rate Limiting next, or tackle an independent transfer challenge?"
                    + footer
                )
            elif intent == PedagogicalIntent.INDEPENDENT_TRANSFER:
                return (
                    "### 🏆 L5 Independent Transfer Challenge: Unassisted Execution\n\n"
                    "You are now attempting an **unassisted L5 Independent Transfer challenge**. No hints will be provided.\n\n"
                    "**Domain: Critical Healthcare Telemetry Dispatch Gateway**\n"
                    "> Hospital monitors stream ICU vitals into your ingestion gateway. The downstream clinical alert notification service is experiencing a 70% packet drop and 10-second latency spikes. Your gateway must guarantee that:\n"
                    "> 1. Slowdowns in clinical alerts do NOT drop real-time patient telemetry ingestion.\n"
                    "> 2. Critical telemetry is buffered with backpressure without memory exhaustion.\n"
                    "> 3. Automated fail-fast circuit breaking isolates the degraded alert service until it recovers.\n\n"
                    "Detail your architectural topology, thread pool allocation, circuit breaker states, and backpressure strategy."
                    + footer
                )
            elif intent == PedagogicalIntent.TEACH_FROM_BEGINNING:
                return (
                    "### 📚 Teaching from First Principles: Preventing Cascading Failures\n\n"
                    "The primary goal of resilience engineering is preventing localized faults from triggering systemic fleet-wide outages.\n\n"
                    "#### 1. The Bulkhead Pattern\n"
                    "Named after watertight compartments in ships: if one compartment floods, the others remain buoyant.\n"
                    "In microservices, dedicate separate thread pools and HTTP connection pools to separate services so that a slow recommendation engine cannot starve checkout processing.\n\n"
                    "#### 2. Exponential Backoff with Full Jitter\n"
                    "`backoff = min(max_backoff, base * (2 ** attempt)) * random()`\n"
                    "Adding random jitter breaks synchronization so 10,000 clients do not hit the recovering server at the exact same millisecond."
                    + footer
                )

        # -------------------------------------------------------------
        # Context-Aware Fallback for Inquiries & Architectural Edge Cases
        # -------------------------------------------------------------
        msg_low = user_message.lower()
        if any(w in msg_low for w in ["partition", "split-brain", "blast radius", "redis down", "redis fail"]):
            return (
                "### ⚡ Architectural Deep Dive: Redis Partitioning & Blast Radius Mitigation\n\n"
                f"You asked: *\"{user_message[:120]}\"*\n\n"
                "When your caching or distributed lock layer (e.g. Redis) undergoes a network partition or outage, you face a classic **CAP theorem trade-off**:\n\n"
                "#### 1. The Blast Radius: Fail-Open vs. Fail-Closed\n"
                "- **Fail-Closed (Consistency Over Availability)**: If Redis is unreachable, the API returns `HTTP 503 Service Unavailable` or `HTTP 409 Conflict`. No requests proceed without a verified idempotency lock. This guarantees **zero double-charges**, but completely halts payment processing.\n"
                "- **Fail-Open (Availability Over Consistency)**: If Redis is unreachable, the service bypasses the cache and executes the payment anyway. Availability remains 100%, but concurrent retries will cause duplicate financial mutations.\n\n"
                "#### 2. The Production Hybrid Solution: Relational DB Fallback\n"
                "Staff Engineers design a tiered fallback:\n"
                "1. **Tier 1 (Fast Path)**: Redis `SET NX` handles 99.99% of high-throughput locking at sub-millisecond latency.\n"
                "2. **Tier 2 (Partition Resilience)**: If Redis health-checks fail (circuit breaker trips to Open), the API Gateway falls back to PostgreSQL `INSERT INTO idempotency_records ... ON CONFLICT DO NOTHING` within the primary database.\n"
                "Latency increases from 1ms to 25ms, but payments stay operational and consistency is preserved 100% without duplicates."
                + footer
            )
        elif any(w in msg_low for w in ["two generals", "generals problem", "ack", "timeout retry", "retry strategy"]):
            return (
                "### 🛡️ Connecting Back: The Two Generals Problem & Timeout Retry Strategies\n\n"
                f"You asked: *\"{user_message[:120]}\"*\n\n"
                "Let's trace how the foundational **Two Generals Problem** directly governs why our timeout and retry strategy requires receiver-side idempotency:\n\n"
                "#### 1. The Mathematical Invariant: Unreliable Networks Cannot Guarantee Common Knowledge\n"
                "In distributed computing, when General A sends a message across an untrusted channel, General A cannot distinguish between:\n"
                "1. The message was lost before reaching General B.\n"
                "2. General B received the message and executed the order, but the acknowledgment (ACK) was dropped on the return path.\n"
                "3. General B received the message, but is executing it very slowly (high latency/timeout).\n\n"
                "#### 2. Why Retries Alone Are Dangerous\n"
                "Because the sender cannot know whether the server executed the command before a timeout occurred, the sender **must retry** to achieve at-least-once delivery. "
                "However, if the server actually executed the command (Case 2 or 3), a blind retry causes duplicate execution (e.g. charging $100 twice).\n\n"
                "#### 3. The Unbreakable Pair: Exponential Backoff + Jitter + Idempotency Keys\n"
                "- **Client Side**: Uses exponential backoff with full jitter to prevent retry storms (thundering herds) when the network is degraded.\n"
                "- **Server Side**: Idempotency keys make retries safe. Because the operation is mathematically idempotent (`f(f(x)) = f(x)`), the client can retry as many times as needed across the unreliable channel without ever corrupting state."
                + footer
            )

        if intent in (PedagogicalIntent.SIMPLIFY_BEGINNER, PedagogicalIntent.FOUNDATIONAL_EXPLANATION):
            return (
                f"### 💡 Intuitive Mental Model: {focus_skill}\n\n"
                f"**1. Core Concept**:\n"
                f"In backend engineering, {focus_skill} is designed to enforce deterministic state transitions and ensure high availability under heavy load without data corruption.\n\n"
                f"**2. Analogy**:\n"
                f"Think of an airport baggage checkpoint: each bag receives an unambiguous barcode tag, ensuring that even with hundreds of flights arriving simultaneously, luggage is routed deterministically to the correct carousel.\n\n"
                f"**3. Technical Connection**:\n"
                f"In distributed software systems, {focus_skill} establishes clear boundaries and invariants so that operations can execute reliably, recover from network jitter, and scale gracefully.\n\n"
                f"**4. Practical Example**:\n"
                f"```python\n"
                f"# Enforce invariant boundary for {focus_skill}\n"
                f"with transactional_boundary():\n"
                f"    validate_preconditions(request)\n"
                f"    result = execute_operation(request)\n"
                f"    persist_checkpoint(result)\n"
                f"return result\n"
                f"```\n\n"
                f"**5. Common Candidate Mistake**:\n"
                f"Designing purely for the happy path while overlooking network timeouts, race conditions, or partial write failures during concurrent operations.\n\n"
                f"**6. Check Your Understanding**:\n"
                f"What is the single most critical invariant you must preserve when designing a scalable architecture for {focus_skill}?\n\n"
                f"Take a moment to reply with your thoughts!"
                + footer
            )
        elif intent == PedagogicalIntent.MISCONCEPTION_CORRECTION:
            return (
                f"### ⚠️ Common Interview Mistakes: {focus_skill}\n\n"
                f"When discussing **{focus_skill}** in system design interviews, candidates typically make three errors:\n"
                "1. **Ignoring Failure Boundaries**: Assuming network calls and database writes succeed synchronously without error handling.\n"
                "2. **Over-engineering Prematurely**: Introducing distributed consensus (e.g. Raft) when simpler atomic locking or OCC suffices.\n"
                "3. **Missing Observable Telemetry**: Failing to specify how latency, error rates, and invariant breaches are monitored in production.\n\n"
                "Which of these architectural concerns is most relevant to your current project experience?"
                + footer
            )
        elif intent == PedagogicalIntent.NEXT_COMPETENCY:
            return (
                f"### 🚀 Next Competency Recommendation\n\n"
                f"Great work exploring **{focus_skill}**! You have covered the key structural invariants and failure boundaries.\n\n"
                f"Based on your learning progression for **{target_role}**, we recommend exploring related architectural invariants or attempting an unassisted transfer challenge.\n\n"
                f"Would you like to continue to the next topic, or practice an unassisted challenge?"
                + footer
            )
        elif intent == PedagogicalIntent.INDEPENDENT_TRANSFER:
            return (
                f"### 🏆 L5 Independent Transfer Challenge: {focus_skill}\n\n"
                f"You are attempting an **unassisted L5 Independent Transfer challenge** on **{focus_skill}**. No hints will be provided.\n\n"
                f"**Domain: Large-Scale Distributed Media Ingestion & Processing Platform**\n"
                f"> Formulate an end-to-end architecture applying the invariants of {focus_skill}.\n"
                f"> Ensure your design preserves data consistency, bounds resource consumption, and handles network timeouts without cascading failures.\n\n"
                f"Detail your architectural decisions, data stores, invariant checks, and failure recovery flow."
                + footer
            )

        return (
            f"### 🎯 Pedagogical Coaching on {focus_skill}\n\n"
            f"Regarding your inquiry: *\"{user_message[:120]}\"*\n\n"
            f"For **{target_role}** interviews, mastering this topic requires grounding your design in two invariants:\n"
            "1. **Deterministic State Transitions**: Ensuring that concurrent executions converge on identical, unambiguous state across distributed nodes.\n"
            "2. **Bounded Failure Recovery**: Guaranteeing that network timeouts, process crashes, or retries leave the system in a known, safe state through atomic invariants and reconciliation.\n\n"
            "Would you like to explore a **worked example**, inspect the **code implementation**, or attempt an **unseen transfer challenge**?"
            + footer
        )

    def _synthesize_fallback_turn(
        self,
        user_message: str,
        focus_skill: str,
        target_role: str,
        is_simplify: bool,
        is_worked_example: bool,
        is_check_understanding: bool,
        is_transfer: bool,
        is_hint: bool,
    ) -> str:
        """Backwards compatibility wrapper delegating to adaptive curriculum synthesis."""
        intent = PedagogicalIntent.GENERAL_COACHING
        if is_simplify:
            intent = PedagogicalIntent.SIMPLIFY_BEGINNER
        elif is_worked_example:
            intent = PedagogicalIntent.WORKED_EXAMPLE
        elif is_check_understanding:
            intent = PedagogicalIntent.CHECK_UNDERSTANDING
        elif is_transfer:
            intent = PedagogicalIntent.TRANSFER_CHALLENGE
        elif is_hint:
            intent = PedagogicalIntent.HINT_REQUEST

        focus_key = "api_idempotency"
        skill_input = focus_skill.lower().replace(" ", "_")
        if "idemp" in skill_input:
            focus_key = "api_idempotency"
        elif any(k in skill_input for k in ["cache", "partition", "stampede"]):
            focus_key = "distributed_caching"
        elif any(k in skill_input for k in ["concurr", "isolation", "lock", "acid", "db"]):
            focus_key = "database_concurrency"
        elif any(k in skill_input for k in ["resilien", "circuit", "backoff", "bulkhead"]):
            focus_key = "resilience_patterns"

        return self._synthesize_adaptive_teaching_response(
            intent=intent,
            focus_key=focus_key,
            focus_skill=focus_skill,
            target_role=target_role,
            user_message=user_message,
            convo_meta={},
        )

