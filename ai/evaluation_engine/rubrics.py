"""
Configurable Evaluation Rubrics and Structured Question-Specific Rubrics.
Provides question-specific rubrics distinguishing essential concepts, optional advanced details,
common misconceptions, unverified personal claim handling, and deterministic scoring weights.
"""

import re
from typing import Dict, List, Optional, Any
# pyrefly: ignore [import-not-found, missing-import]
from pydantic import BaseModel, Field, ConfigDict


class RubricWeights(BaseModel):
    model_config = ConfigDict(extra="ignore")

    correctness: float = Field(default=0.30, ge=0.0, le=1.0)
    completeness: float = Field(default=0.25, ge=0.0, le=1.0)
    technical_depth: float = Field(default=0.20, ge=0.0, le=1.0)
    relevance: float = Field(default=0.15, ge=0.0, le=1.0)
    reasoning: float = Field(default=0.10, ge=0.0, le=1.0)


class QuestionRubric(BaseModel):
    """
    Structured rubric tailored to an individual question.
    Enforces evaluation of technical correctness rather than verbatim keyword matching,
    separates essential concepts from optional advanced depth, and detects misconceptions.
    """
    model_config = ConfigDict(extra="ignore")

    topic: str
    question_id: Optional[str] = None
    interview_type: str = "TECHNICAL"
    weights: RubricWeights = Field(default_factory=RubricWeights)
    essential_concepts: List[str] = Field(default_factory=list)
    optional_advanced_concepts: List[str] = Field(default_factory=list)
    common_misconceptions: List[str] = Field(default_factory=list)
    unverified_claim_indicators: List[str] = Field(default_factory=list)
    performance_level_descriptions: Dict[str, str] = Field(default_factory=dict)
    evaluation_guidance: str = ""


# Configurable default rubrics per interview type
RUBRIC_CONFIGS: Dict[str, RubricWeights] = {
    "TECHNICAL": RubricWeights(
        correctness=0.30,
        completeness=0.25,
        technical_depth=0.20,
        relevance=0.15,
        reasoning=0.10,
    ),
    "BEHAVIORAL": RubricWeights(
        correctness=0.10,  # authenticity/context
        completeness=0.30,  # STAR method coverage
        technical_depth=0.10,
        relevance=0.25,  # direct answer to prompt
        reasoning=0.25,  # structured ownership & impact
    ),
    "MIXED": RubricWeights(
        correctness=0.25,
        completeness=0.25,
        technical_depth=0.20,
        relevance=0.15,
        reasoning=0.15,
    ),
}


# Curated question-specific rubrics for core engineering problems
CURATED_QUESTION_RUBRICS: Dict[str, QuestionRubric] = {
    "iot_telemetry_protocols": QuestionRubric(
        topic="IoT Telemetry Protocols & Resource-Constrained Ingestion",
        question_id="emb_stage3_01",
        interview_type="TECHNICAL",
        weights=RubricWeights(
            correctness=0.35,
            completeness=0.25,
            technical_depth=0.20,
            relevance=0.10,
            reasoning=0.10,
        ),
        essential_concepts=[
            "MQTT QoS levels (QoS 0 fire-and-forget, QoS 1 PUBACK, QoS 2 4-step handshake)",
            "TCP vs UDP transport trade-offs (connection overhead, persistent state vs lightweight packet)",
            "CoAP Confirmable (CON) / Non-confirmable (NON) messaging over UDP",
            "Battery drain and bandwidth consumption on constrained nodes",
            "SRAM buffering or ring buffer for intermittent disconnects",
        ],
        optional_advanced_concepts=[
            "External SPI flash memory staging with wear-leveling block cycling",
            "Adaptive backpressure / sensor sampling throttling / load shedding",
            "eSleep / deep sleep duty cycling",
        ],
        common_misconceptions=[
            "MQTT QoS 2 delivery guarantee automatically provides exactly-once application processing without backend deduplication/idempotency",
            "UDP transport cannot achieve reliability (ignoring CoAP application-layer ACKs and retries)",
        ],
        unverified_claim_indicators=[
            "Claims of personal company battery life statistics or deployment scale without architectural rationale",
        ],
        performance_level_descriptions={
            "EXEMPLARY": "Accurately contrasts TCP persistent connection cost vs UDP CoAP headers; explains all 3 MQTT QoS handshakes; notes QoS 2 does not guarantee application idempotency; details SRAM ring buffering and backpressure.",
            "PROFICIENT": "Explains MQTT QoS levels, recognizes CoAP runs on UDP with lightweight overhead, describes buffering during network dropouts.",
            "DEVELOPING": "Mentions QoS levels but confuses TCP vs UDP mechanics, or overlooks memory exhaustion risks during network partitions.",
            "INSUFFICIENT": "Declines to answer, or claims MQTT has no overhead and CoAP is identical to HTTP.",
        },
        evaluation_guidance=(
            "Recognize correct QoS explanations, TCP/UDP trade-offs, CoAP Confirmable messages, battery and bandwidth considerations. "
            "Verify technical nuance: MQTT QoS 2 delivery guarantees at transport layer do not automatically guarantee exactly-once application processing. "
            "Credit equivalent architectural terms (e.g. queue instead of ring buffer; rate-limiting instead of backpressure)."
        ),
    ),

    "hnsw_vs_ivfpq": QuestionRubric(
        topic="HNSW vs IVF-PQ Vector Indexing Mechanics",
        question_id="emb_stage2_01",
        interview_type="TECHNICAL",
        weights=RubricWeights(
            correctness=0.30,
            completeness=0.25,
            technical_depth=0.25,
            relevance=0.10,
            reasoning=0.10,
        ),
        essential_concepts=[
            "HNSW hierarchical graph traversal (multi-layer proximity graph with skip connections)",
            "efSearch parameter and graph connectivity (M) governing routing beam width",
            "IVF coarse clustering (Voronoi cells, nlist centroids, nprobe scanning)",
            "Product Quantization (PQ) decomposing vectors into sub-vectors and quantizing to codebooks",
            "RAM footprint comparison (HNSW requires raw vectors + graph links; IVF-PQ compresses vectors by 80-95%)",
            "Latency vs recall trade-offs across 50M scale",
        ],
        optional_advanced_concepts=[
            "Asymmetric Distance Computation (ADC) vs Symmetric Distance Computation (SDC)",
            "Hardware considerations (CPU cache locality, SIMD AVX-512 vectorization, memory bus saturation)",
            "Disk-backed hybrid architectures (DiskANN)",
        ],
        common_misconceptions=[
            "HNSW uses less RAM than IVF-PQ (in reality HNSW requires significantly more memory)",
            "General performance claims treated as universal guarantees regardless of dimensionality, hardware, or index parameters",
        ],
        unverified_claim_indicators=[
            "Claims of measured latency or recall outcomes at a specific employer without technical justification",
        ],
        performance_level_descriptions={
            "EXEMPLARY": "Rigorous breakdown of hierarchical graph traversal (efSearch/M) vs Voronoi cell partitioning (nlist/nprobe); details PQ sub-vector quantization; quantifies RAM differences (hundreds of GBs vs compressed codebooks); explains hardware and parameter dependencies.",
            "PROFICIENT": "Correctly contrasts graph-based HNSW with clustered/quantized IVF-PQ; acknowledges HNSW offers lower latency and higher recall at the expense of high RAM footprint.",
            "DEVELOPING": "Knows HNSW is graph-based and PQ compresses vectors, but confuses memory trade-offs or claims HNSW is low memory.",
            "INSUFFICIENT": "Confuses basic ANN concepts or asserts that exact brute-force search is scalable to 50M vectors in real-time.",
        },
        evaluation_guidance=(
            "Recognize hierarchical graph traversal, graph connectivity, efSearch, IVF coarse clustering, nprobe, Product Quantization, "
            "memory and recall trade-offs. Do not treat general performance claims as universal guarantees: assess whether candidate understands "
            "results depend on hardware, dimensions, index parameters, and dataset characteristics. Missing optional advanced details (ADC, DiskANN) "
            "must not penalize an otherwise correct answer."
        ),
    ),

    "vector_cost_governance": QuestionRubric(
        topic="In-Memory Vector Cost Governance vs SLA Defense",
        question_id="emb_stage5_01",
        interview_type="BEHAVIORAL",
        weights=RubricWeights(
            correctness=0.20,
            completeness=0.25,
            technical_depth=0.20,
            relevance=0.20,
            reasoning=0.15,
        ),
        essential_concepts=[
            "Vector quantization (Scalar Quantization SQ8 or Product Quantization PQ) to reduce RAM",
            "Tiered storage / hot in-memory vs warm disk-backed indexing (e.g. SSD / DiskANN)",
            "Latency distribution monitoring (p50, p95, strict p99 retrieval SLA)",
            "Recall@K evaluation against ground-truth KNN",
            "Stakeholder communication and trade-off negotiation",
        ],
        optional_advanced_concepts=[
            "HNSW graph tuning (reducing M and efConstruction)",
            "Asynchronous NVMe SSD reads (IO_uring / memory-mapped vector storage)",
            "Dedicated VIP routing vs long-tail query pools",
        ],
        common_misconceptions=[
            "Quantization can be rolled out blindly without measuring Recall@K impact on domain queries",
            "Disk-backed storage has identical p99 latency to pure RAM without caching",
        ],
        unverified_claim_indicators=[
            "Unverified previous-company cost reduction claims (e.g. 'I cut our AWS bill by $2M') without verifiable technical evidence",
        ],
        performance_level_descriptions={
            "EXEMPLARY": "Articulates structured hot/cold tiering (RAM for hot queries, SSD/DiskANN for long tail); evaluates SQ8/PQ memory vs Recall@10 impact; explains p99 SLA defense with empirical data; handles stakeholder alignment diplomatically.",
            "PROFICIENT": "Proposes valid memory reduction techniques (quantization, disk offloading) and discusses maintaining p99 SLAs while communicating trade-offs to stakeholders.",
            "DEVELOPING": "Mentions cost cutting or caching, but lacks concrete vector indexing techniques or ignores p99 SLA risks.",
            "INSUFFICIENT": "Suggests deleting vectors randomly or claims RAM costs cannot be optimized in vector search.",
        },
        evaluation_guidance=(
            "Recognize valid architecture concepts: hot/cold storage, SSD-backed indexing, Product Quantization, HNSW tuning, "
            "p50/p95/p99 monitoring, Recall@K. Distinguish hypothetical architectural reasoning from genuine personal experience: "
            "if the candidate claims previous-company experience or measured outcomes without evidence, flag that claim as unverified under "
            "unsupported_claims. Do NOT discard all technically correct architectural reasoning because of it."
        ),
    ),

    "dense_vs_bm25_rag": QuestionRubric(
        topic="Vector Retrieval & Retrieval-Augmented Generation (RAG)",
        question_id="rag_hybrid_01",
        interview_type="TECHNICAL",
        weights=RubricWeights(
            correctness=0.30,
            completeness=0.25,
            technical_depth=0.25,
            relevance=0.10,
            reasoning=0.10,
        ),
        essential_concepts=[
            "Dense vector retrieval strengths (semantic similarity, paraphrasing) and limitations (rare IDs, out-of-vocabulary)",
            "BM25 sparse lexical search strengths (exact matching, alphanumeric IDs, rare terms) and limitations (synonyms, vocabulary mismatch)",
            "Hybrid retrieval combining dense vector search with sparse BM25 inverted index",
            "Result fusion (merging candidate pools) and re-ranking (cross-encoder)",
        ],
        optional_advanced_concepts=[
            "Reciprocal Rank Fusion (RRF) formula: Score(d) = sum(1 / (k + rank(d)))",
            "Chunking boundary invariants and semantic chunk overlap",
            "Cross-encoder full-attention re-ranking vs bi-encoder dot product",
        ],
        common_misconceptions=[
            "Dense embeddings alone are universally superior to BM25 for technical documentation, code, and exact entity lookups",
            "Raw cosine similarity scores and unbounded BM25 scores can be directly added together without rank fusion or score normalization",
        ],
        unverified_claim_indicators=[
            "Unverified claims of 100% precision or universal superiority on internal company datasets without evidence",
        ],
        performance_level_descriptions={
            "EXEMPLARY": "Clearly explains semantic embedding strengths vs lexical BM25 exact match; describes parallel retrieval architecture; explains rank fusion (RRF or score normalization) to reconcile disparate distributions; details cross-encoder re-ranking for top-K.",
            "PROFICIENT": "Explains why dense retrieval struggles with rare identifiers where BM25 shines; proposes combining both in a hybrid pipeline with re-ranking.",
            "DEVELOPING": "Mentions both vectors and keywords, but fails to explain how to combine them or why dense search fails on rare identifiers.",
            "INSUFFICIENT": "Claims vector search has no limitations and BM25 is obsolete.",
        },
        evaluation_guidance=(
            "Recognize semantic similarity, exact lexical matching, rare identifiers, hybrid retrieval, result fusion, reranking. "
            "Recognize Reciprocal Rank Fusion as a possible improvement, but do not make it mandatory unless the question or rubric explicitly "
            "requires that depth. Credit equivalent formulations (e.g. cross-encoder, rank fusion, sparse-dense ensemble)."
        ),
    ),

    "caching_stampede_protection": QuestionRubric(
        topic="Caching Topologies & Stampede Protection",
        question_id="sys_stage3_01",
        interview_type="TECHNICAL",
        weights=RubricWeights(
            correctness=0.35,
            completeness=0.25,
            technical_depth=0.20,
            relevance=0.10,
            reasoning=0.10,
        ),
        essential_concepts=[
            "Cache stampede / thundering herd problem description (many concurrent requests on key expiration)",
            "Mutex locks / distributed lock / single-flight request coalescing (only one worker populates cache)",
            "Probabilistic early expiration (XFetch algorithm) / stale-while-revalidate / background cache refresh",
            "TTL jitter / randomized TTL to prevent simultaneous cache key expiration spikes",
            "Cache warming / pre-populating anticipated hot keys",
        ],
        optional_advanced_concepts=[
            "XFetch optimal refresh formula: -beta * delta * ln(random())",
            "Bloom filters or null object caching for cache penetration prevention",
            "Two-tier caching (local in-memory L1 + distributed Redis/Memcached L2)",
            "Database circuit breaking or connection pool throttling during cache failure",
        ],
        common_misconceptions=[
            "Increasing TTL or adding more cache memory alone prevents thundering herd on expiration",
            "Write-through caching completely eliminates stampedes without locking or coalescing",
            "Stale-while-revalidate is unsafe for all read-heavy workloads",
        ],
        unverified_claim_indicators=[
            "Unverified previous company scale claims (e.g. 'I saved 100M queries at my last job') without architectural explanation",
        ],
        performance_level_descriptions={
            "EXEMPLARY": "Clearly explains thundering herd mechanics; details mutex locking / single-flight coalescing; contrasts stale-while-revalidate with probabilistic early expiration (XFetch); explains TTL jitter and pre-warming.",
            "PROFICIENT": "Explains cache stampedes and details at least two primary defenses: mutex/locks on miss, TTL randomization, and background refresh.",
            "DEVELOPING": "Recognizes the problem of expired cache keys but relies solely on naive solutions like increasing cache size.",
            "INSUFFICIENT": "Declines to answer, or claims in-memory caching never experiences expiration spikes.",
        },
        evaluation_guidance=(
            "Recognize valid solutions: mutex lock, single-flight coalescing, probabilistic early expiration (XFetch), "
            "stale-while-revalidate, TTL jitter, pre-warming, two-tier caching. "
            "Do NOT penalize missing optional advanced details (XFetch formula, Bloom filters) if core mechanisms are sound."
        ),
    ),

    "model_serving_latency_quantization": QuestionRubric(
        topic="High-Throughput Model Inference & KV Cache Optimization",
        question_id="ai_stage3_01",
        interview_type="TECHNICAL",
        weights=RubricWeights(
            correctness=0.35,
            completeness=0.25,
            technical_depth=0.20,
            relevance=0.10,
            reasoning=0.10,
        ),
        essential_concepts=[
            "Continuous batching / iteration-level scheduling (vs static request batching) eliminating head-of-line blocking",
            "PagedAttention / non-contiguous virtual memory allocation for KV cache eliminating memory fragmentation",
            "KV cache memory limits and GPU memory bandwidth bottlenecks during autoregressive token generation",
            "Model quantization (INT8, FP8, FP16) reducing memory footprint and memory bus pressure",
            "Trade-offs between throughput (batch size) and p99 latency (time-to-first-token TTFT vs inter-token latency ITL)",
        ],
        optional_advanced_concepts=[
            "Speculative decoding / draft model verification to accelerate decode phase",
            "Tensor parallelism (Megatron-LM style) and AllReduce communication overhead",
            "Chunked prefill vs decode phase separation",
            "Weight-only vs weight-and-activation quantization (e.g., AWQ, GPTQ vs SmoothQuant)",
        ],
        common_misconceptions=[
            "KV cache size is static and does not scale with sequence length or batch size",
            "Quantization only speeds up compute without affecting GPU memory bandwidth requirements",
            "Static request batching has equal efficiency to continuous iteration-level scheduling",
        ],
        unverified_claim_indicators=[
            "Claims of custom kernel optimization or measured latency at a previous company without technical architecture",
        ],
        performance_level_descriptions={
            "EXEMPLARY": "Rigorous breakdown of continuous iteration-level batching vs static batching; details PagedAttention block tables and zero-fragmentation KV cache; explains GPU memory bandwidth bounds during decode; contrasts TTFT vs ITL latency metrics.",
            "PROFICIENT": "Explains continuous batching, PagedAttention memory management, KV cache scaling, and model quantization benefits for GPU bandwidth and p99 latency.",
            "DEVELOPING": "Mentions batching and quantization, but confuses static batching with continuous batching or lacks understanding of KV cache memory footprint.",
            "INSUFFICIENT": "Declines to answer, or confuses model training with LLM autoregressive serving.",
        },
        evaluation_guidance=(
            "Recognize continuous batching, PagedAttention, KV cache memory footprint, quantization (INT8/FP16), "
            "GPU memory bandwidth constraints, and p99 token generation latency. "
            "Credit equivalent frameworks (vLLM, TensorRT-LLM, Triton). Do not penalize missing speculative decoding."
        ),
    ),
}


def get_rubric_for_type(interview_type: str) -> RubricWeights:
    """Returns default rubric weights for a given interview type."""
    key = (interview_type or "TECHNICAL").upper()
    return RUBRIC_CONFIGS.get(key, RUBRIC_CONFIGS["TECHNICAL"])


def get_rubric_for_question(
    topic: str,
    question_text: str = "",
    expected_concepts: Optional[List[str]] = None,
    interview_type: str = "TECHNICAL",
) -> QuestionRubric:
    """
    Resolves the exact, structured QuestionRubric for any interview question.
    Matches curated rubrics by topic / key phrases first, or dynamically synthesizes
    a structured rubric distinguishing essential concepts, optional advanced depth, and misconceptions.
    """
    topic_lower = (topic or "").lower()
    q_lower = (question_text or "").lower()
    combined_text = f"{topic_lower} {q_lower}"
    exp = list(expected_concepts or [])

    # 1. Match curated rubrics with strict regex word boundaries to prevent substring bleed
    if re.search(r"\b(cache stampedes?|thundering herds?|caching topologies|caching topology|cache invalidations?|stampede protection)\b", combined_text):
        return CURATED_QUESTION_RUBRICS["caching_stampede_protection"]

    if re.search(r"\b(continuous batching|iteration-level batching|dynamic batching|pagedattentions?|paged attentions?|kv caches?|model serving throughput|gpu memory bandwidth)\b", combined_text):
        return CURATED_QUESTION_RUBRICS["model_serving_latency_quantization"]

    if re.search(r"\b(coap|mqtt|iot telemetry|qos 0|qos 1|qos 2)\b", combined_text):
        return CURATED_QUESTION_RUBRICS["iot_telemetry_protocols"]

    if re.search(r"\b(hnsw vs ivf|ivf-pq|approximate nearest neighbor)\b", combined_text) or (
        re.search(r"\bhnsw\b", combined_text) and re.search(r"\bivf\b", combined_text)
    ):
        return CURATED_QUESTION_RUBRICS["hnsw_vs_ivfpq"]

    if re.search(r"\b(hosting costs?|vector costs?|p99 retrieval|vector index hosting)\b", combined_text):
        return CURATED_QUESTION_RUBRICS["vector_cost_governance"]

    # RAG: check with word boundaries and ensure it is not an unrelated word like 'leverage' or 'storage'
    if re.search(r"\b(bm25|dense vector retrieval|hybrid retrieval|dense \+ bm25|reciprocal rank fusion|cross-encoder|reranking)\b", combined_text) or (
        re.search(r"\brag\b", combined_text) and re.search(r"\b(retrieval|search|documents|chunks|dense|sparse)\b", combined_text)
    ):
        return CURATED_QUESTION_RUBRICS["dense_vs_bm25_rag"]

    # 2. Dynamic rubric synthesis for other questions
    weights = get_rubric_for_type(interview_type)
    
    # Partition expected concepts into essential vs optional
    essential: List[str] = []
    optional: List[str] = []
    for c in exp:
        c_low = c.lower()
        if any(adv in c_low for adv in ["edge case", "advanced", "tuning", "hardware", "asymmetric", "formula"]):
            optional.append(c)
        else:
            essential.append(c)

    if not essential and exp:
        essential = exp[:max(1, len(exp) // 2)]
        optional = exp[len(essential):]

    return QuestionRubric(
        topic=topic or "Technical Question",
        question_id=None,
        interview_type=interview_type,
        weights=weights,
        essential_concepts=essential or [topic],
        optional_advanced_concepts=optional,
        common_misconceptions=[
            f"Over-simplifying trade-offs in {topic or 'the domain'}",
            "Treating empirical performance as a universal guarantee without considering constraints",
        ],
        unverified_claim_indicators=[
            "Claims of production scale or measured performance at previous employers without supporting architectural evidence",
        ],
        performance_level_descriptions={
            "EXEMPLARY": f"Demonstrates comprehensive mastery of {topic}, explaining core mechanics, quantitative trade-offs, and edge-case handling.",
            "PROFICIENT": f"Explains the primary mechanism and practical application of {topic} clearly with valid reasoning.",
            "DEVELOPING": f"Displays basic awareness of {topic} but omits critical trade-offs or exhibits minor misconceptions.",
            "INSUFFICIENT": f"Fails to address {topic} or presents fundamental conceptual errors.",
        },
        evaluation_guidance=(
            f"Evaluate technical correctness and reasoning on {topic}. "
            "Credit equivalent phrasing and alternative valid architectures. "
            "Do not penalize missing optional advanced concepts if essential concepts are correctly explained."
        ),
    )
