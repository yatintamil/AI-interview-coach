"""
Transfer Transformer for Controlled Invariant-Preserving Task Shifts.
Combines deterministic domain transformation rules with LLM provider abstraction.
"""

import json
import logging
import re
import uuid
from typing import Optional, Dict, Any, List

from backend.domain.ai.interfaces import LLMProvider, LLMRequest
from backend.domain.transfer.taxonomy import TransferLevel
from ai.transfer_engine.schemas import TransferGenerationRequest
from ai.transfer_engine.interfaces import ITransferTransformer
from ai.transfer_engine.normalization import normalize_surface_context

logger = logging.getLogger(__name__)


# Deterministic Domain Variant Knowledge Base for reproducible transformations
TASK_FAMILY_CATALOG: Dict[str, Dict[str, Dict[str, Any]]] = {
    "system_design": {
        "distributed_caching": {
            TransferLevel.L0_RECALL: {
                "surface_context": "Core Cache Invariants & Eviction Theory",
                "surface_distractors": [],
                "prompt_template": "Define the fundamental invariants of distributed caching. How does an LRU eviction policy maintain constant-time bounds, and what causes cache stampedes?",
                "extra_concepts": ["LRU eviction", "Cache stampede prevention", "Cache-aside"],
            },
            TransferLevel.L1_DIRECT_APPLICATION: {
                "surface_context": "High-Throughput Redis Key-Value Store",
                "surface_distractors": ["Write-heavy bursts"],
                "prompt_template": "Design a high-throughput key-value cache layer supporting 100,000 QPS with aggressive TTL eviction and cache stampede prevention.",
                "extra_concepts": ["TTL expiry", "Probabilistic early expiration", "Mutex locks"],
            },
            TransferLevel.L2_NEAR_TRANSFER: {
                "surface_context": "Distributed Media File Chunk Store",
                "surface_distractors": ["Chunk deduplication", "Content addressing"],
                "prompt_template": "Design an edge chunk-caching system for a cloud file-sharing service where large files are partitioned into 4MB chunks. How do you manage eviction and cache-aside lookup across sharded edge nodes?",
                "extra_concepts": ["Chunked LRU", "Content hashing", "Edge node replication"],
            },
            TransferLevel.L3_FAR_TRANSFER: {
                "surface_context": "Multi-Tenant Push Notification Dispatcher",
                "surface_distractors": ["Device token fan-out", "APNs/FCM rate limits"],
                "prompt_template": "Design a real-time notification dispatch engine for 50 million active devices. Apply your caching and eviction principles to ensure high-priority notifications are not delayed by bulk marketing traffic.",
                "extra_concepts": ["Priority queue buffering", "Token bucket throttling", "Backpressure"],
            },
            TransferLevel.L4_AMBIGUOUS_TRANSFER: {
                "surface_context": "Global Telemetry Ingestion Platform",
                "surface_distractors": ["Unspecified payload formats", "Variable ingestion frequency"],
                "prompt_template": "A rapidly growing IoT platform needs you to design their telemetry ingestion buffer. The platform faces intermittent surges and unstable network links. How would you design the buffering and persistence layer without knowing exact peak QPS upfront?",
                "extra_concepts": ["Capacity estimation", "Assumption clarification", "Graceful degradation"],
            },
            TransferLevel.L5_INDEPENDENT_TRANSFER: {
                "surface_context": "Interplanetary Satellite Mesh Network Buffer",
                "surface_distractors": ["Deep space propagation delay", "Orbital occlusion windows"],
                "prompt_template": "Design an autonomous data caching and forwarding architecture for a constellation of low-earth-orbit satellites with intermittent inter-satellite optical links and ground-station passes. Ensure zero data loss when links drop unexpectedly.",
                "extra_concepts": ["Delay-tolerant networking", "Custody transfer", "Store-and-forward"],
            },
        },
        "rate_limiting": {
            TransferLevel.L0_RECALL: {
                "surface_context": "Rate Limiting Algorithmic Foundations",
                "surface_distractors": [],
                "prompt_template": "Explain the mechanics and trade-offs between Token Bucket, Leaky Bucket, and Fixed Window rate limiters.",
                "extra_concepts": ["Token bucket", "Leaky bucket", "Sliding window log"],
            },
            TransferLevel.L1_DIRECT_APPLICATION: {
                "surface_context": "REST API Gateway Throttling",
                "surface_distractors": ["API key tiers"],
                "prompt_template": "Design a centralized rate limiting middleware for an API gateway handling authenticated developer tiers using Redis.",
                "extra_concepts": ["Redis atomic counters", "Sliding window", "429 Too Many Requests"],
            },
            TransferLevel.L2_NEAR_TRANSFER: {
                "surface_context": "High-Demand Flash Sale Ticket Reservation",
                "surface_distractors": ["Shopping cart timer", "Seat reservations"],
                "prompt_template": "Design a admission rate-limiting queue for a stadium ticketing sale where 500,000 users attempt checkout simultaneously upon release.",
                "extra_concepts": ["Virtual waiting room", "Fair queueing", "Atomic lease reservation"],
            },
            TransferLevel.L3_FAR_TRANSFER: {
                "surface_context": "Automated Trading Exchange Order Flow Throttler",
                "surface_distractors": ["Sub-millisecond packet latency", "Financial exchange compliance"],
                "prompt_template": "Design an in-memory microsecond rate regulator on a financial order matching engine to prevent runaway high-frequency trading algorithms from flooding the order book.",
                "extra_concepts": ["Lock-free ring buffer", "Hardware timestamping", "Circuit breaker"],
            },
            TransferLevel.L4_AMBIGUOUS_TRANSFER: {
                "surface_context": "Enterprise SaaS Webhook Delivery Regulator",
                "surface_distractors": ["Untrusted third-party client endpoints", "Sporadic webhook storms"],
                "prompt_template": "Design a webhook emission throttling system for an enterprise platform sending events to diverse customer servers. Traffic patterns are unpredictable and destination endpoints frequently degrade.",
                "extra_concepts": ["Dynamic backoff", "Destination health probing", "Adaptive throttling"],
            },
            TransferLevel.L5_INDEPENDENT_TRANSFER: {
                "surface_context": "Smart Electrical Grid Demand-Response Dispatcher",
                "surface_distractors": ["Transformer thermal limits", "Renewable generation fluctuations"],
                "prompt_template": "Design an autonomous rate regulation network for millions of distributed smart meters and industrial generators to prevent regional power grid frequency instability during sudden renewable drop-offs.",
                "extra_concepts": ["Decentralized consensus", "Frequency droop control", "Dynamic load shedding"],
            },
        },
    }
}


class TransferTransformer(ITransferTransformer):
    """
    Executes controlled invariant-preserving transformations across L0-L5.
    Uses domain rules with fallback to LLM provider for flexible novel generations.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider

    async def transform(self, request: TransferGenerationRequest) -> Dict[str, Any]:
        """
        Transforms the request into a candidate transfer task dictionary.
        Checks deterministic catalog first; falls back to LLM provider if available.
        """
        # 1. Deterministic Domain Catalog Match (fast, 100% reproducible for test suites)
        family_dict = TASK_FAMILY_CATALOG.get(request.task_family, {})
        skill_dict = family_dict.get(request.skill_id, {})
        catalog_variant = skill_dict.get(request.transfer_level)

        if catalog_variant:
            return self._build_from_catalog(request, catalog_variant)

        # 2. LLM Provider Assisted Generation
        if self.provider and getattr(self.provider, "provider_name", "") != "mock":
            try:
                llm_task = await self._generate_with_llm(request)
                if llm_task:
                    return llm_task
            except Exception as e:
                logger.warning(f"LLM transfer generation failed ({e}), falling back to deterministic transformation.")

        # 3. Rule-Based Fallback Synthesis
        return self._synthesize_rule_based(request)

    def _build_from_catalog(
        self, request: TransferGenerationRequest, catalog_entry: Dict[str, Any]
    ) -> Dict[str, Any]:
        task_id = f"transfer_{request.skill_id}_{request.transfer_level.value.lower()}_{uuid.uuid4().hex[:6]}"
        expected_concepts = list(dict.fromkeys(request.base_expected_concepts + catalog_entry["extra_concepts"]))
        return {
            "id": task_id,
            "parent_task_id": request.parent_task_id if request.transfer_level != TransferLevel.L5_INDEPENDENT_TRANSFER else None,
            "skill_id": request.skill_id,
            "transfer_level": request.transfer_level.value,
            "surface_context": catalog_entry["surface_context"],
            "core_invariants": list(request.core_invariants),
            "surface_distractors": list(catalog_entry.get("surface_distractors", [])),
            "expected_concepts": expected_concepts,
            "rubric_id": request.rubric_id or f"rubric_{request.skill_id}_{request.transfer_level.value.lower()}",
            "prompt_template": catalog_entry["prompt_template"],
        }

    def _synthesize_rule_based(self, request: TransferGenerationRequest) -> Dict[str, Any]:
        """
        Generates a structurally shifted task for any arbitrary skill while guaranteeing
        invariant preservation and surface change.
        """
        level = request.transfer_level
        invariants_str = ", ".join(request.core_invariants)

        surface_prefixes = {
            TransferLevel.L0_RECALL: "Foundational Theory of",
            TransferLevel.L1_DIRECT_APPLICATION: f"High-Scale {request.base_surface_context}",
            TransferLevel.L2_NEAR_TRANSFER: f"Distributed Edge Variant of {request.base_surface_context}",
            TransferLevel.L3_FAR_TRANSFER: f"Cross-Domain Operational Engine for {request.skill_id}",
            TransferLevel.L4_AMBIGUOUS_TRANSFER: f"Unconstrained Real-Time Environment for {request.skill_id}",
            TransferLevel.L5_INDEPENDENT_TRANSFER: f"Autonomous Mission-Critical System ({request.skill_id})",
        }

        surface_context = f"{surface_prefixes.get(level, 'Variant of')} ({uuid.uuid4().hex[:4]})"

        if level == TransferLevel.L0_RECALL:
            prompt = f"Explain the core theoretical invariants of {request.skill_id}, specifically focusing on: {invariants_str}."
        elif level == TransferLevel.L1_DIRECT_APPLICATION:
            prompt = f"Design an architecture for {surface_context} that strictly upholds: {invariants_str} under high workload."
        elif level == TransferLevel.L2_NEAR_TRANSFER:
            prompt = f"Consider a new domain: {surface_context}. Adapt your knowledge to preserve {invariants_str} despite the changed operational structure."
        elif level == TransferLevel.L3_FAR_TRANSFER:
            prompt = f"In {surface_context}, requirements differ substantially from traditional {request.base_surface_context}. How do you formulate structural invariants around {invariants_str}?"
        elif level == TransferLevel.L4_AMBIGUOUS_TRANSFER:
            prompt = f"You are tasked with deploying {surface_context}. Requirements, peak throughput, and memory ceilings are unstated. Propose your design and state which invariants among {invariants_str} you would defend first."
        else:  # L5_INDEPENDENT_TRANSFER
            prompt = f"Design a completely autonomous, unassisted architecture for {surface_context}. Ensure robustness for {invariants_str} against catastrophic node failure."

        task_id = f"transfer_{request.skill_id}_{level.value.lower()}_{uuid.uuid4().hex[:6]}"
        return {
            "id": task_id,
            "parent_task_id": request.parent_task_id if level != TransferLevel.L5_INDEPENDENT_TRANSFER else None,
            "skill_id": request.skill_id,
            "transfer_level": level.value,
            "surface_context": surface_context,
            "core_invariants": list(request.core_invariants),
            "surface_distractors": [f"Dynamic constraints in {surface_context}"],
            "expected_concepts": list(request.base_expected_concepts),
            "rubric_id": request.rubric_id,
            "prompt_template": prompt,
        }

    async def _generate_with_llm(self, request: TransferGenerationRequest) -> Optional[Dict[str, Any]]:
        """Invokes active LLMProvider to generate novel surface-shifted challenges."""
        system_prompt = (
            "You are an expert Principal AI Software Architecture Interview Coach.\n"
            "Your objective is to generate an unseen TRANSFER TASK that tests whether a candidate can apply\n"
            "underlying theoretical invariants in a novel situation without relying on surface memorization.\n"
            "Return JSON matching: surface_context (string naming the domain/scenario, e.g. 'Distributed Media Video Chunk Store'), core_invariants, surface_distractors, expected_concepts, prompt_template."
        )

        user_prompt = (
            f"Target Skill: {request.skill_id}\n"
            f"Target Transfer Level: {request.transfer_level.value}\n"
            f"Original Training Context: {request.base_surface_context}\n"
            f"Mandatory Core Invariants (MUST PRESERVE ALL): {json.dumps(request.core_invariants)}\n"
            f"Original Expected Concepts: {json.dumps(request.base_expected_concepts)}\n"
        )

        llm_req = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=800,
            response_json=True,
            metadata={"task_type": "transfer_task_generation"},
        )

        res = await self.provider.generate(llm_req)
        raw: Dict[str, Any] = {}
        if res.raw_json and isinstance(res.raw_json, dict):
            raw = res.raw_json
        elif res.content:
            cleaned = re.sub(r"^```json\s*", "", res.content.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
            raw = json.loads(cleaned)

        if not raw or "prompt_template" not in raw or "surface_context" not in raw:
            return None

        # Boundary normalization: handle string, dict, or structured surface_context
        normalized_surface = normalize_surface_context(raw.get("surface_context"))
        if not normalized_surface:
            logger.warning("LLM generated transfer task with empty surface context; falling back.")
            return None

        # Ensure mandatory invariants remain in the generated output
        cand_invariants = list(dict.fromkeys(request.core_invariants + raw.get("core_invariants", [])))
        cand_concepts = list(dict.fromkeys(request.base_expected_concepts + raw.get("expected_concepts", [])))

        task_id = f"transfer_{request.skill_id}_{request.transfer_level.value.lower()}_{uuid.uuid4().hex[:6]}"
        return {
            "id": task_id,
            "parent_task_id": request.parent_task_id if request.transfer_level != TransferLevel.L5_INDEPENDENT_TRANSFER else None,
            "skill_id": request.skill_id,
            "transfer_level": request.transfer_level.value,
            "surface_context": normalized_surface,
            "core_invariants": cand_invariants,
            "surface_distractors": raw.get("surface_distractors", []),
            "expected_concepts": cand_concepts,
            "rubric_id": request.rubric_id,
            "prompt_template": raw["prompt_template"],
        }
