"""
Skill Mapping, Acronym Normalization, and Invariant Extraction Service.
Provides deterministic, explainable normalization from interview questions and evaluation contexts
to canonical skill identifiers, core architectural invariants, prerequisite dependency graphs,
and clean human-readable competency titles.
"""

import re
from typing import List, Optional, Tuple, Dict, Any, Set
from collections import defaultdict, deque

# Canonical competency catalog recognized across Transfer and Coaching subsystems
CANONICAL_SKILLS: Dict[str, Dict[str, Any]] = {
    "distributed_consensus": {
        "display_name": "Distributed Consensus & Quorum Mechanics",
        "tier": 4,
        "keywords": ["consensus", "quorum", "raft", "paxos", "split-brain", "linearizability", "leader election", "term number", "distributed consensus"],
        "default_invariants": [
            "Quorum intersection property (W + R > N or (N/2)+1)",
            "Strict single-leader invariant per term or epoch",
            "Linearizable write ordering and state machine replication",
        ],
    },
    "distributed_caching": {
        "display_name": "Distributed Caching & Partitioning",
        "tier": 3,
        "keywords": ["cache", "caching", "redis", "memcached", "eviction", "stampede", "thundering herd", "lru", "ttl"],
        "default_invariants": [
            "Cache-aside or write-through consistency boundary",
            "Consistent hashing with virtual nodes for partitioning",
            "Eviction policy bounds (LRU/LFU/TTL)",
            "Stampeding herd mitigation (mutex locks / early expiration)",
        ],
    },
    "system_decomposition": {
        "display_name": "Microservices & Event-Driven Decoupling",
        "tier": 3,
        "keywords": ["microservice", "microservices", "decoupling", "event-driven", "kafka", "rabbitmq", "saga", "outbox", "eventual consistency"],
        "default_invariants": [
            "Loose coupling across bounded contexts",
            "Asynchronous message passing with at-least-once or exactly-once semantics",
            "Saga orchestration or choreography without distributed 2PC locks",
        ],
    },
    "concurrency_control": {
        "display_name": "Database Concurrency & Isolation Levels",
        "tier": 2,
        "keywords": ["concurrency", "isolation", "acid", "deadlock", "serializable", "mvcc", "locking", "transaction", "phantom read", "write skew"],
        "default_invariants": [
            "ACID transactional boundaries and rollback invariants",
            "Isolation anomaly prevention (dirty reads, phantom reads, write skew)",
            "Deterministic lock ordering or optimistic concurrency verification",
        ],
    },
    "database_fundamentals": {
        "display_name": "Relational Data Modeling & Indexing Internals",
        "tier": 1,
        "keywords": ["database", "sql", "indexing", "b-tree", "foreign key", "normalization", "query planner", "table scan"],
        "default_invariants": [
            "Relational schema normalization and foreign key integrity constraints",
            "B-Tree index leaf-page traversal and range scan efficiency",
            "Deterministic query execution plans avoiding unindexed table scans",
        ],
    },
    "storage_engine_and_wal_internals": {
        "display_name": "Storage Engine & Write-Ahead Log Internals",
        "tier": 1,
        "keywords": ["storage engine", "wal", "write-ahead log", "lsm", "sstable", "fsync", "durability", "checkpointing", "page cache"],
        "default_invariants": [
            "Write-Ahead Log sequential append before in-memory page mutation",
            "Fsync durability boundaries across crash recovery checkpoints",
            "LSM compaction or B-Tree split deterministic structural invariants",
        ],
    },
    "resilience_patterns": {
        "display_name": "Circuit Breaking & Backpressure Resilience",
        "tier": 4,
        "keywords": ["circuit breaker", "backpressure", "cascading failure", "rate limit", "rate limiting", "bulkhead", "timeout", "retry with jitter"],
        "default_invariants": [
            "Fault isolation via bulkhead partitioning",
            "Circuit breaker state transitions (Closed -> Open -> Half-Open)",
            "Exponential backoff with randomized jitter",
        ],
    },
    "rate_limiting": {
        "display_name": "Distributed Rate Limiting & Throttling",
        "tier": 2,
        "keywords": ["rate limit", "rate limiting", "token bucket", "leaky bucket", "sliding window", "throttling", "429"],
        "default_invariants": [
            "Deterministic rate budget enforcement across distributed nodes",
            "Atomic counter increments or sliding window timestamps",
            "Graceful shedding with explicit Retry-After headers",
        ],
    },
    "api_idempotency": {
        "display_name": "API Idempotency & Safe Deduplication",
        "tier": 2,
        "keywords": ["idempotency", "idempotent", "deduplication", "idempotency key", "retry", "exactly once"],
        "default_invariants": [
            "Unique idempotency key persistence before side-effect execution",
            "Atomic result caching and cached payload replay on duplicate tokens",
            "Deterministic distributed locking during in-flight request processing",
        ],
    },
    "api_security": {
        "display_name": "API Security & Multi-Tenant Authorization",
        "tier": 2,
        "keywords": ["security", "tenant", "authorization", "idor", "multi-tenant", "authentication", "tampering", "rbac", "jwt"],
        "default_invariants": [
            "Tenant context propagation and row-level authorization boundaries",
            "Least-privilege permission validation before execution",
            "Cryptographic integrity and tamper detection",
        ],
    },
    "algorithmic_optimization": {
        "display_name": "Data Structure Selection & Amortized Complexity",
        "tier": 1,
        "keywords": ["algorithm", "algorithms", "data structure", "complexity", "dynamic programming", "memoization", "amortized", "big o"],
        "default_invariants": [
            "Optimal substructure and state-space decomposition",
            "Strict asymptotic time and space upper bounds",
            "Invariant-preserving state transition functions",
        ],
    },
    "memory_management": {
        "display_name": "Memory Architecture & Resource Lifecycle",
        "tier": 1,
        "keywords": ["memory leak", "garbage collection", "heap dump", "profiling", "allocation", "gil", "reference count", "valgrind", "buffer overflow"],
        "default_invariants": [
            "Deterministic object allocation and reclamation boundaries",
            "Cyclic reference resolution and root reachability",
            "Bounded memory ceilings under high-throughput allocation",
        ],
    },
    "operating_systems_and_threading": {
        "display_name": "OS Fundamentals & Multi-Threading Concurrency",
        "tier": 1,
        "keywords": ["operating system", "thread", "process", "mutex", "semaphore", "context switch", "inter-process", "ipc", "posix"],
        "default_invariants": [
            "Thread synchronization safety avoiding race conditions and deadlocks",
            "Deterministic thread scheduling and priority inversion prevention",
            "Bounded context switch overhead under heavy concurrency",
        ],
    },
    "network_protocols_and_grpc": {
        "display_name": "Network Protocols, HTTP/2 & gRPC Streaming",
        "tier": 2,
        "keywords": ["grpc", "protobuf", "http/2", "tcp", "streaming", "multiplexing", "network protocol", "head-of-line"],
        "default_invariants": [
            "Binary framing and multiplexed stream lifecycle management",
            "Strict transport-level error handling and cancellation propagation",
            "Bounded buffer flow control and TCP backpressure propagation",
        ],
    },
    "high_availability_and_failover": {
        "display_name": "High Availability & Automated Failover",
        "tier": 4,
        "keywords": ["high availability", "failover", "disaster recovery", "active-active", "active-passive", "split brain", "replication lag"],
        "default_invariants": [
            "Deterministic leader election and heartbeating without split-brain",
            "Bounded replication lag limits before promote failover",
            "Fencing mechanisms ensuring dead nodes cannot issue stale writes",
        ],
    },
    "production_tradeoffs_and_cost_governance": {
        "display_name": "Production Trade-Offs & Cost Governance",
        "tier": 5,
        "keywords": ["production tradeoff", "cost governance", "capacity planning", "sla", "slo", "finops", "cloud cost"],
        "default_invariants": [
            "P99 latency SLA versus infrastructure cost Pareto trade-offs",
            "Autoscaling ceilings preventing unbounded runaway billing",
            "Predictable graceful degradation under extreme load saturation",
        ],
    },
    "embedding_fundamentals": {
        "display_name": "Vector Embeddings & Semantic Representation",
        "tier": 1,
        "keywords": ["embedding", "embeddings", "vector", "cosine similarity", "dot product", "dense retrieval", "tokenization", "dimensionality"],
        "default_invariants": [
            "Deterministic normalization and geometric distance metric preservation",
            "Consistent tokenization and vocabulary bounds",
            "Bounded dimension scaling without semantic collapse",
        ],
    },
    "embedding_pipeline_architecture": {
        "display_name": "Embedding Pipeline & Ingestion Architecture",
        "tier": 2,
        "keywords": ["embedding pipeline", "chunking", "rag ingestion", "document parsing", "vector store ingestion", "hybrid search"],
        "default_invariants": [
            "Deterministic chunking with semantic overlap preservation",
            "Idempotent vector upserts and document revision tracking",
            "Batch embedding throughput with rate-limit backpressure handling",
        ],
    },
    "vector_indexing_and_ann": {
        "display_name": "Vector Indexing & Approximate Nearest Neighbors",
        "tier": 3,
        "keywords": ["hnsw", "ann", "vector index", "faiss", "pgvector", "ivf-pq", "recall@k", "nearest neighbor"],
        "default_invariants": [
            "HNSW graph connectivity and small-world property maintenance",
            "Quantization error bounding under vector compression (IVF-PQ)",
            "Recall-versus-latency Pareto frontier tuning",
        ],
    },
    "vector_system_reliability_and_drift": {
        "display_name": "Vector System Reliability & Embedding Drift",
        "tier": 4,
        "keywords": ["embedding drift", "vector reliability", "data drift", "rag evaluation", "grounding", "hallucination"],
        "default_invariants": [
            "Continuous distributional drift detection across semantic spaces",
            "Deterministic re-indexing without query availability downtime",
            "Groundedness verification against source attribution references",
        ],
    },
    "retrieval_tradeoffs_and_ownership": {
        "display_name": "Retrieval Architectures & Production Governance",
        "tier": 5,
        "keywords": ["retrieval tradeoff", "production rag", "reranking", "cross-encoder", "retrieval governance", "context window"],
        "default_invariants": [
            "Multi-stage retrieval latency budget enforcement (bi-encoder -> reranker)",
            "Context window compression without needle-in-haystack omission",
            "Ownership and privacy governance in multi-tenant semantic retrieval",
        ],
    },
    "llm_inference_optimization": {
        "display_name": "LLM Inference Optimization & Serving",
        "tier": 3,
        "keywords": ["llm inference", "vllm", "paged attention", "kv cache", "quantization", "continuous batching", "speculative decoding"],
        "default_invariants": [
            "KV cache memory management and non-contiguous virtual paging",
            "Continuous batching latency guarantees without starvation",
            "Precision quantization safety (INT8/FP8) without catastrophic perplexity drop",
        ],
    },
    "embedded_memory_mapped_io": {
        "display_name": "Embedded Memory-Mapped I/O & Peripheral Control",
        "tier": 1,
        "keywords": ["memory mapped", "mmio", "i/o", "dma", "isr", "interrupt", "peripheral", "register", "volatile", "embedded c"],
        "default_invariants": [
            "Volatile register access guarantees preventing compiler optimization elision",
            "Atomic interrupt service routine (ISR) execution and critical section masking",
            "DMA buffer alignment and cache coherency synchronization",
        ],
    },
    "ci_cd_and_deployment_orchestration": {
        "display_name": "CI/CD & Zero-Downtime Deployment Orchestration",
        "tier": 5,
        "keywords": ["ci/cd", "continuous integration", "canary", "blue-green", "rolling update", "kubernetes", "k8s", "helm", "gitops"],
        "default_invariants": [
            "Zero-downtime rolling update with graceful connection draining",
            "Automated canary analysis and instant blast-radius rollback gates",
            "Immutable artifact provenance and cryptographically signed builds",
        ],
    },
    # Frontend Engineering Canonical Skills
    "frontend_architecture_and_component_state": {
        "display_name": "Component Architecture, State Boundaries & Lifecycle Invariants",
        "tier": 1,
        "keywords": ["virtual dom", "reconciliation", "unidirectional data flow", "react state", "prop drilling", "context api", "frontend architecture", "state management", "component lifecycle", "zustand", "redux"],
        "default_invariants": [
            "State mutations must be pure and unidirectional to prevent cascading re-render loops",
            "Component side-effects must be decoupled from rendering and bound to explicit dependencies",
            "Normalized client state eliminates multi-source synchronization anomalies",
        ],
    },
    "web_performance_and_core_vitals": {
        "display_name": "Web Performance, Rendering Pipeline & Core Web Vitals",
        "tier": 2,
        "keywords": ["core web vitals", "inp", "lcp", "cls", "interaction to next paint", "largest contentful paint", "cumulative layout shift", "code splitting", "tree shaking", "critical rendering path", "bundle optimization", "lighthouse"],
        "default_invariants": [
            "Main thread tasks exceeding 50ms must be chunked or offloaded to keep INP under 200ms",
            "Layout-triggering mutations must be batched to avoid forced synchronous layout reflows",
            "Dynamic imports and code splitting must guard against waterfall bundle download stalls",
        ],
    },
    "asynchronous_data_and_client_caching": {
        "display_name": "Client Data Fetching, Stale-While-Revalidate & Optimistic UI",
        "tier": 3,
        "keywords": ["tanstack query", "react query", "swr", "stale while revalidate", "optimistic ui", "abortcontroller", "client caching", "request deduplication", "optimistic update"],
        "default_invariants": [
            "Concurrent network requests must carry AbortController signals to cancel stale flight requests",
            "Optimistic UI updates must snapshot previous cache state to enable deterministic rollback on error",
            "Cache invalidation keys must follow hierarchical tagging to avoid over-fetching and stale reads",
        ],
    },
    "dom_accessibility_and_security": {
        "display_name": "Accessible DOM Architecture (WCAG 2.2 AA) & Frontend Security",
        "tier": 4,
        "keywords": ["wcag", "aria", "accessibility", "screen reader", "focus trap", "dom xss", "content security policy", "csp", "sanitize html", "keyboard navigation", "axe core"],
        "default_invariants": [
            "Modal dialogues and overlay views must trap keyboard focus and restore prior focus on dismissal",
            "Dynamic DOM injections must be sanitized against DOM XSS vectors under a strict Content Security Policy",
            "All interactive elements must expose accessible names and semantic ARIA roles matching WCAG 2.2 AA",
        ],
    },
    "browser_networking_and_offline_storage": {
        "display_name": "Browser Storage, Service Workers & Offline Synchronization",
        "tier": 4,
        "keywords": ["service worker", "indexeddb", "offline sync", "cachestorage", "pwa", "progressive web app", "background sync", "browser storage quota", "workbox"],
        "default_invariants": [
            "Service worker cache activation must atomically purge legacy cache versions to prevent asset skew",
            "IndexedDB transactions must handle quota exhaustion gracefully with user-notified persistence boundaries",
            "Offline mutation queues must enforce idempotent server-side reconciliation upon reconnect",
        ],
    },
    "frontend_testing_and_star_leadership": {
        "display_name": "Component Testing, Visual Regression & Cross-Functional Delivery",
        "tier": 5,
        "keywords": ["react testing library", "vitest", "playwright", "cypress", "visual regression", "design system tokens", "frontend testing", "component test", "rtl"],
        "default_invariants": [
            "Automated component tests must assert user-facing accessibility semantics rather than internal state",
            "Visual regression tests must lock font and viewport dimensions to prevent false-positive diff failures",
            "Design system component contracts must enforce token-driven semantic theming without hardcoded styles",
        ],
    },
}

# Directed Prerequisite Dependency DAG: key -> list of skills that must be learned BEFORE key
PREREQUISITE_DEPENDENCIES: Dict[str, List[str]] = {
    # Tier 1: Foundations
    "algorithmic_optimization": [],
    "memory_management": [],
    "database_fundamentals": [],
    "storage_engine_and_wal_internals": ["database_fundamentals"],
    "operating_systems_and_threading": ["memory_management"],
    "embedding_fundamentals": ["algorithmic_optimization"],
    "embedded_memory_mapped_io": ["memory_management"],

    # Tier 2: Core Data, API & Protocol Architecture
    "concurrency_control": ["storage_engine_and_wal_internals", "database_fundamentals"],
    "api_idempotency": ["database_fundamentals", "concurrency_control"],
    "rate_limiting": ["algorithmic_optimization"],
    "api_security": ["operating_systems_and_threading"],
    "network_protocols_and_grpc": ["operating_systems_and_threading"],
    "embedding_pipeline_architecture": ["embedding_fundamentals"],

    # Tier 3: Distributed Systems & Scale
    "distributed_caching": ["concurrency_control", "rate_limiting"],
    "system_decomposition": ["api_idempotency", "network_protocols_and_grpc"],
    "vector_indexing_and_ann": ["embedding_fundamentals", "algorithmic_optimization"],
    "llm_inference_optimization": ["memory_management", "embedding_pipeline_architecture"],

    # Tier 4: Fault Tolerance & Reliability
    "resilience_patterns": ["distributed_caching", "system_decomposition"],
    "distributed_consensus": ["concurrency_control", "distributed_caching"],
    "high_availability_and_failover": ["distributed_consensus", "resilience_patterns"],
    "vector_system_reliability_and_drift": ["vector_indexing_and_ann", "resilience_patterns"],

    # Tier 5: Governance & Production Scale
    "retrieval_tradeoffs_and_ownership": ["vector_system_reliability_and_drift"],
    "production_tradeoffs_and_cost_governance": ["high_availability_and_failover", "resilience_patterns"],
    "ci_cd_and_deployment_orchestration": ["resilience_patterns"],

    # Curated Role Blueprint Competency DAGs
    # Backend Systems Engineer
    "relational_integrity_and_indexing": [],
    "backend_api_and_concurrency": ["relational_integrity_and_indexing"],
    "distributed_caching_and_messaging": ["backend_api_and_concurrency"],
    "system_resilience_and_debugging": ["distributed_caching_and_messaging"],
    "observability_and_star_ownership": ["system_resilience_and_debugging"],

    # Machine Learning Engineer
    "feature_pipelines_and_leakage": [],
    "model_evaluation_and_loss_invariants": ["feature_pipelines_and_leakage"],
    "model_serving_and_latency_optimization": ["model_evaluation_and_loss_invariants"],
    "ml_drift_debugging_and_fallback": ["model_serving_and_latency_optimization"],
    "cross_functional_ml_governance": ["ml_drift_debugging_and_fallback"],
    "ml_pipeline_and_feature_engineering": [],
    "deep_learning_training_and_optimization": ["ml_pipeline_and_feature_engineering"],
    "model_serving_latency_and_quantization": ["deep_learning_training_and_optimization"],
    "model_drift_monitoring_and_governance": ["model_serving_latency_and_quantization"],
    "vector_search_and_rag_systems": ["ml_pipeline_and_feature_engineering"],
    "ml_safety_ethics_and_tradeoffs": ["model_drift_monitoring_and_governance"],

    # Embedded Systems Engineer
    "embedded_firmware_and_concurrency": [],
    "hardware_interfacing_and_timing": ["embedded_firmware_and_concurrency"],
    "memory_constrained_systems": ["embedded_firmware_and_concurrency"],
    "hardware_fault_containment": ["hardware_interfacing_and_timing"],
    "cross_functional_embedded_lifecycle": ["hardware_fault_containment"],
    "embedded_c_and_memory_mapped_io": [],
    "interrupts_and_concurrency_boundaries": ["embedded_c_and_memory_mapped_io"],
    "peripheral_bus_protocols_and_dma": ["interrupts_and_concurrency_boundaries"],
    "fault_diagnostics_watchdogs_and_power": ["peripheral_bus_protocols_and_dma"],
    "embedded_project_ownership_and_star": ["fault_diagnostics_watchdogs_and_power"],

    # Frontend Developer
    "frontend_architecture_and_component_state": [],
    "web_performance_and_core_vitals": ["frontend_architecture_and_component_state"],
    "asynchronous_data_and_client_caching": ["frontend_architecture_and_component_state"],
    "dom_accessibility_and_security": ["frontend_architecture_and_component_state", "web_performance_and_core_vitals"],
    "browser_networking_and_offline_storage": ["asynchronous_data_and_client_caching"],
    "frontend_testing_and_star_leadership": ["dom_accessibility_and_security"],
}

# Prerequisite Tier Numbers (1 to 5)
PREREQUISITE_TIERS: Dict[str, int] = {
    k: v.get("tier", 3) for k, v in CANONICAL_SKILLS.items()
}
PREREQUISITE_TIERS.update({
    # Backend Systems Engineer
    "relational_integrity_and_indexing": 1,
    "backend_api_and_concurrency": 2,
    "distributed_caching_and_messaging": 3,
    "system_resilience_and_debugging": 4,
    "observability_and_star_ownership": 5,

    # Machine Learning Engineer
    "feature_pipelines_and_leakage": 1,
    "model_evaluation_and_loss_invariants": 2,
    "model_serving_and_latency_optimization": 3,
    "ml_drift_debugging_and_fallback": 4,
    "cross_functional_ml_governance": 5,
    "ml_pipeline_and_feature_engineering": 1,
    "deep_learning_training_and_optimization": 2,
    "model_serving_latency_and_quantization": 3,
    "model_drift_monitoring_and_governance": 4,
    "vector_search_and_rag_systems": 3,
    "ml_safety_ethics_and_tradeoffs": 5,

    # Embedded Systems Engineer
    "embedded_firmware_and_concurrency": 1,
    "hardware_interfacing_and_timing": 2,
    "memory_constrained_systems": 3,
    "hardware_fault_containment": 4,
    "cross_functional_embedded_lifecycle": 5,
    "embedded_c_and_memory_mapped_io": 1,
    "interrupts_and_concurrency_boundaries": 2,
    "peripheral_bus_protocols_and_dma": 3,
    "fault_diagnostics_watchdogs_and_power": 4,
    "embedded_project_ownership_and_star": 5,

    # Frontend Developer
    "frontend_architecture_and_component_state": 1,
    "web_performance_and_core_vitals": 2,
    "asynchronous_data_and_client_caching": 3,
    "dom_accessibility_and_security": 4,
    "browser_networking_and_offline_storage": 4,
    "frontend_testing_and_star_leadership": 5,
})

# Acronym mapping for technical titles
ACRONYMS: Dict[str, str] = {
    "dom": "DOM",
    "inp": "INP",
    "lcp": "LCP",
    "cls": "CLS",
    "wcag": "WCAG",
    "aria": "ARIA",
    "xss": "XSS",
    "csp": "CSP",
    "pwa": "PWA",
    "rtl": "RTL",
    "html": "HTML",
    "ui": "UI",
    "io": "I/O",
    "i_o": "I/O",
    "isrs": "ISRs",
    "isr": "ISR",
    "dma": "DMA",
    "grpc": "gRPC",
    "rag": "RAG",
    "ann": "ANN",
    "acid": "ACID",
    "mvcc": "MVCC",
    "cicd": "CI/CD",
    "ci_cd": "CI/CD",
    "ci": "CI",
    "cd": "CD",
    "k8s": "Kubernetes (K8s)",
    "kubernetes": "Kubernetes",
    "adamw": "AdamW",
    "llm": "LLM",
    "wal": "WAL",
    "ttl": "TTL",
    "lru": "LRU",
    "lfu": "LFU",
    "cpu": "CPU",
    "gpu": "GPU",
    "api": "API",
    "sql": "SQL",
    "nosql": "NoSQL",
    "rest": "REST",
    "http": "HTTP",
    "tcp": "TCP",
    "ip": "IP",
    "os": "OS",
    "ram": "RAM",
    "rom": "ROM",
    "fp8": "FP8",
    "int8": "INT8",
    "kv": "KV",
    "bfs": "BFS",
    "dfs": "DFS",
    "dag": "DAG",
    "sla": "SLA",
    "slo": "SLO",
    "sli": "SLI",
    "dns": "DNS",
    "cdn": "CDN",
    "tls": "TLS",
    "ssl": "SSL",
    "jwt": "JWT",
    "oauth": "OAuth",
    "rbac": "RBAC",
    "abac": "ABAC",
    "crud": "CRUD",
    "fifo": "FIFO",
    "lifo": "LIFO",
    "mmio": "MMIO",
}


def clean_competency_display_name(
    raw_name: str,
    fallback_topic: Optional[str] = None,
) -> Tuple[str, bool, str]:
    """
    Cleans raw or unmapped competency names, strips 'unmapped_' prefixes,
    deduplicates stuttered tokens, maps recognized acronyms, and matches canonical catalog.

    Returns:
        (clean_display_title, is_flagged_for_review, canonical_or_clean_id)
    """
    if not raw_name:
        raw_name = fallback_topic or "General Technical Competency"

    # Step 1: Strip leading 'unmapped_' prefix
    working = raw_name.strip()
    is_unmapped_prefix = False
    while working.lower().startswith("unmapped_") or working.lower().startswith("unmapped "):
        is_unmapped_prefix = True
        working = working[9:].strip()

    # Step 2: Check if normalized match exists in canonical catalog
    canonical_id, is_canonical = normalize_skill(topic=working, category=fallback_topic)
    if is_canonical and canonical_id in CANONICAL_SKILLS:
        return CANONICAL_SKILLS[canonical_id]["display_name"], False, canonical_id

    # Step 3: Clean tokenization & deduplication
    tokens = re.split(r"[_\s\-\/]+", working)
    clean_tokens: List[str] = []
    prev_token = None

    for t in tokens:
        tl = t.lower().strip()
        if not tl:
            continue
        # Deduplicate immediate repetitions like 'c_c' -> 'c'
        if tl == prev_token:
            continue
        prev_token = tl

        if tl in ACRONYMS:
            clean_tokens.append(ACRONYMS[tl])
        elif tl == "c" and clean_tokens and clean_tokens[-1].lower() == "embedded":
            clean_tokens.append("C/C++")
        else:
            clean_tokens.append(t.capitalize())

    clean_title = " ".join(clean_tokens)
    if not clean_title:
        clean_title = "Technical Architecture Competency"

    clean_slug = re.sub(r"[^a-z0-9]+", "_", clean_title.lower()).strip("_")
    # Flag for review if it wasn't matched in the canonical catalog
    is_flagged = is_unmapped_prefix or (clean_slug not in CANONICAL_SKILLS)
    return clean_title, is_flagged, clean_slug


def normalize_skill(
    topic: str,
    category: Optional[str] = None,
    expected_concepts: Optional[List[str]] = None,
) -> Tuple[str, bool]:
    """
    Deterministically maps interview question metadata to a canonical skill identifier.
    Returns:
        (skill_id, is_canonical)
    """
    clean_text = f"{topic or ''} {category or ''} {' '.join(expected_concepts or [])}".lower()
    search_corpus = clean_text.replace("_", " ").replace("-", " ")
    
    # Check for direct keyword matches against canonical competencies
    best_match: Optional[str] = None
    best_match_score = 0
    
    for skill_id, config in CANONICAL_SKILLS.items():
        score = 0
        for kw in config["keywords"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", search_corpus):
                score += 2 if len(kw.split()) > 1 else 1
        if score > best_match_score:
            best_match_score = score
            best_match = skill_id
            
    if best_match and best_match_score >= 1:
        return best_match, True
        
    # Unmapped fallback
    raw_topic = re.sub(r"^unmapped[_\s]+", "", (topic or "general").strip(), flags=re.IGNORECASE)
    clean_topic = re.sub(r"[^a-z0-9]+", "_", raw_topic.lower()).strip("_")
    unmapped_id = f"unmapped_{clean_topic[:40]}" if clean_topic else "unmapped_general"
    return unmapped_id, False


def is_canonical_skill(skill_id: str) -> bool:
    """Checks whether a given skill_id belongs to the validated canonical catalog."""
    return skill_id in CANONICAL_SKILLS


def get_prerequisites_for_skill(skill_id: str) -> List[str]:
    """Returns direct prerequisite competency IDs for the given skill."""
    return list(PREREQUISITE_DEPENDENCIES.get(skill_id, []))


def get_skill_tier(skill_id: str) -> int:
    """Returns the pedagogical progression tier (1 to 5) for the skill."""
    return PREREQUISITE_TIERS.get(skill_id, 3)


def topological_prerequisite_sort(
    competency_ids: List[str],
    prerequisites_map: Optional[Dict[str, List[str]]] = None,
    priority_key_map: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Topologically sorts competency IDs based on prerequisite dependencies (foundational -> advanced).
    Ensures that for any competency X with prerequisite Y, Y appears before X if both are in competency_ids.
    Breaks ties by:
      1. Tier level (Tier 1 Foundations first, Tier 5 Governance last)
      2. Priority key (e.g. CRITICAL before HIGH)
      3. Original list order
    Safely resolves any cycles.
    """
    if not competency_ids:
        return []

    prereqs = prerequisites_map or PREREQUISITE_DEPENDENCIES
    valid_ids: Set[str] = set(competency_ids)
    original_idx: Dict[str, int] = {cid: idx for idx, cid in enumerate(competency_ids)}

    def tie_breaker(cid: str) -> tuple:
        tier = get_skill_tier(cid)
        p_val = priority_key_map.get(cid, 2) if priority_key_map else 0
        return (tier, p_val, original_idx.get(cid, 0))

    # Build adjacency and in-degree tables restricted to competencies present in valid_ids
    adj: Dict[str, Set[str]] = defaultdict(set)
    in_degree: Dict[str, int] = {cid: 0 for cid in valid_ids}

    for cid in valid_ids:
        for p in prereqs.get(cid, []):
            if p in valid_ids and p != cid:
                adj[p].add(cid)
                in_degree[cid] += 1

    zero_in_degree = [cid for cid, deg in in_degree.items() if deg == 0]
    zero_in_degree.sort(key=tie_breaker)

    result: List[str] = []
    visited: Set[str] = set()
    queue = deque(zero_in_degree)

    while queue:
        curr = queue.popleft()
        if curr in visited:
            continue
        visited.add(curr)
        result.append(curr)

        newly_available: List[str] = []
        for dependent in sorted(adj[curr], key=tie_breaker):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0 and dependent not in visited:
                newly_available.append(dependent)

        newly_available.sort(key=tie_breaker)
        queue.extend(newly_available)

    if len(result) < len(valid_ids):
        remaining = [cid for cid in valid_ids if cid not in visited]
        remaining.sort(key=tie_breaker)
        result.extend(remaining)

    return result


def extract_core_invariants(
    expected_concepts: Optional[List[str]],
    topic: str,
    skill_id: str,
) -> List[str]:
    """
    Extracts structural invariants that must be preserved during transfer.
    Derives primarily from expected_concepts if present, supplemented by canonical
    skill defaults or topic context.
    """
    invariants: List[str] = []
    
    if expected_concepts:
        for c in expected_concepts:
            clean_c = c.strip()
            if clean_c and clean_c not in invariants:
                invariants.append(clean_c)
                if len(invariants) >= 4:
                    break
                    
    # If fewer than 2 concepts, supplement from canonical catalog defaults
    if len(invariants) < 2 and skill_id in CANONICAL_SKILLS:
        defaults = CANONICAL_SKILLS[skill_id]["default_invariants"]
        for d in defaults:
            if d not in invariants:
                invariants.append(d)
            if len(invariants) >= 3:
                break
                
    if not invariants:
        clean_name, _, _ = clean_competency_display_name(raw_name=topic)
        invariants = [
            f"Foundational architectural principles and state invariants for {clean_name}",
            f"Failure boundary containment and error handling for {clean_name}",
        ]
        
    return invariants
