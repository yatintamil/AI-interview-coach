"""
Single Primary Question Sanitizer & Contract Normalizer.

Enforces candidate-facing interviewer invariants:
1. Strips leaked internal metadata, artificial labels, and rubrics.
2. Isolates exactly ONE primary question per turn while preserving legitimate scenario context.
3. Protects code blocks, inline snippets, and quoted inquiries from accidental splitting.
4. Normalizes compound multi-part inquiries without leaving grammatical fragments.
5. Provides rigorous semantic validation of single-question invariants.
"""

import re
from typing import List, Optional, Tuple


# Internal labels and prefixes that should never leak to candidate-facing dialogue
LEAKED_PREFIX_PATTERNS = [
    r"^(?:Question|Q|Inquiry)\s*\d*[:.-]\s*",
    r"^(?:Scenario|Context)[:.-]\s*",
    r"^(?:Interviewer|Alex|Dr\.\s*Alex\s*Vance)[:.-]\s*",
    r"^(?:Target Competency|Competency)[:.-]\s*.*?(?:\n|$)",
    r"^(?:Assessment Objective|Objective)[:.-]\s*.*?(?:\n|$)",
    r"^(?:Expected Concepts|Key Concepts)[:.-]\s*.*?(?:\n|$)",
    r"^(?:Rubric|Evaluation Criteria)[:.-]\s*.*?(?:\n|$)",
    r"^(?:Please\s+answer\s+the\s+following|Consider\s+the\s+following\s+questions?)[:.-]?\s*",
]

# Patterns for leaked rubrics or scoring criteria appended to question
LEAKED_SUFFIX_PATTERNS = [
    r"\n*\*{0,3}(?:Rubric|Evaluation Criteria|Scoring Guide|Expected Response|Expected Answer|Scoring Rubric)[:.-].*$",
    r"\n*\*{0,3}(?:Note|Tip|Guidance for candidate)[:.-].*$",
    r"\n*\*{0,3}(?:Look for evidence of|Candidate should explain)[:.-].*$",
]

# Conjunction phrases that split two distinct inquiries into a compound question
COMPOUND_CONJUNCTION_PATTERNS = [
    r",\s+and\s+(?:how|why|what|when|where|which|describe|explain|can you|could you)\b",
    r",\s+as\s+well\s+as\s+(?:how|why|what|when|where|which|describe|explain)\b",
    r",\s+also\s+(?:how|why|what|when|where|which|describe|explain)\b",
    r"\band\s+furthermore\s+(?:how|why|what|when)\b",
]

# Patterns representing genuine inquiry verbs and question structures
INQUIRY_DIRECTIVES = [
    # Question words at start of sentence or after clause punctuation
    r"(?:^|[.?!;]|\bscenario:|\bcontext:)\s*(?:what|which|how|why|where|who|whom|whose)\b",
    # Question auxiliary verbs inverted
    r"\b(?:can|could|would|will|should|do|does|did|is|are|have|has)\s+(?:you|we|a candidate|the system|the backend|nodes|replicas|threads|processes|services|it|they)\b",
    # Directive imperative verbs
    r"\b(?:explain|describe|walk me through|outline|discuss|evaluate|compare|illustrate|detail|clarify)\b",
    # Specific inquiry nouns with what/which anywhere
    r"\b(?:what|which)\s+(?:\w+\s+)*(?:trade-off|trade-offs|approach|approaches|mechanism|mechanisms|pattern|patterns|strategy|strategies|technique|techniques|step|steps|invariant|invariants|primitive|primitives)\b",
]


def has_true_inquiry_predicate(text: str) -> bool:
    """
    Returns True only if the text contains an actual inquiry predicate,
    distinguishing between a real question and a subordinate clause like 'When designing...'.
    """
    t_lower = text.lower()
    return any(re.search(pat, t_lower) for pat in INQUIRY_DIRECTIVES)


def mask_protected_spans(text: str) -> Tuple[str, List[str]]:
    """
    Masks code blocks, inline code, and quoted strings so that internal punctuation
    (such as '?' inside comments or quotes) is not misinterpreted as sentence boundaries.
    """
    placeholders: List[str] = []

    def repl(m):
        idx = len(placeholders)
        placeholders.append(m.group(0))
        return f"__MASKED_SPAN_{idx}__"

    # 1. Multi-line code blocks ```...```
    masked = re.sub(r"```[\s\S]*?```", repl, text)
    # 2. Inline code `...`
    masked = re.sub(r"`[^`\n]+`", repl, masked)
    # 3. Double-quoted strings "..."
    masked = re.sub(r'"[^"\n]+"', repl, masked)
    # 4. Single-quoted strings '...'
    masked = re.sub(r"'[^'\n]+'", repl, masked)

    return masked, placeholders


def unmask_protected_spans(text: str, placeholders: List[str]) -> str:
    """Restores masked code blocks, inline code, and quoted strings."""
    for idx, orig in enumerate(placeholders):
        text = text.replace(f"__MASKED_SPAN_{idx}__", orig)
    return text


def strip_leaked_metadata(text: str) -> str:
    """Removes leaked internal metadata prefixes, markdown headers, rubrics, and scoring directives."""
    cleaned = text.strip()

    # Remove leaked suffix rubrics first
    for pat in LEAKED_SUFFIX_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

    # Remove leaked prefix labels iteratively
    changed = True
    while changed:
        prev = cleaned
        for pat in LEAKED_PREFIX_PATTERNS:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        cleaned = re.sub(r"^\*{1,3}(?:Question|Interviewer|Scenario|Context):\*{1,3}\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        cleaned = re.sub(r"^#{1,4}\s*(?:Question|Scenario|Context|Overview|Problem|Target Competency|Competency|Rubric|Evaluation Criteria).*?(?:\n|$)", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        changed = (cleaned != prev)

    return cleaned


def extract_first_from_numbered_list(text: str) -> Optional[str]:
    """If the question was generated as a numbered or bulleted list of questions, extracts the first one."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    list_items: List[str] = []
    scenario_preamble: List[str] = []

    for line in lines:
        m = re.match(r"^(?:\d+[\.\)]|[-*•])\s*(.*)", line)
        if m:
            list_items.append(m.group(1).strip())
        elif not list_items:
            scenario_preamble.append(line)

    if list_items:
        first_q = list_items[0]
        preamble = " ".join(scenario_preamble).strip()
        if preamble:
            return f"{preamble} {first_q}".strip()
        return first_q

    return None


def sanitize_and_enforce_single_question(question_text: str) -> str:
    """
    Ensures question contains exactly ONE primary inquiry.
    Preserves scenario context while eliminating compound multi-barrel inquiries.
    Protects quoted phrases and code blocks from accidental punctuation truncation.
    """
    if not question_text or not question_text.strip():
        return "Could you walk me through your engineering approach to this problem?"

    cleaned = strip_leaked_metadata(question_text)

    # 1. Handle bulleted or numbered question lists
    extracted_from_list = extract_first_from_numbered_list(cleaned)
    if extracted_from_list:
        cleaned = extracted_from_list

    # Mask protected spans (quotes, code blocks)
    masked, placeholders = mask_protected_spans(cleaned)

    # 2. Check for multiple unmasked question marks
    if masked.count("?") > 1:
        segments = masked.split("?")
        first_segment_unmasked = unmask_protected_spans(segments[0].strip(), placeholders)
        # Verify first segment contains a true inquiry predicate
        if has_true_inquiry_predicate(first_segment_unmasked) and len(first_segment_unmasked) >= 20:
            cleaned = f"{first_segment_unmasked}?"
            masked, placeholders = mask_protected_spans(cleaned)

    # 2b. Check for multiple sentences containing independent inquiry predicates
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", masked) if s.strip()]
    inquiry_sentences_indices = [idx for idx, s in enumerate(raw_sentences) if has_true_inquiry_predicate(s)]
    if len(inquiry_sentences_indices) > 1:
        # Isolate the first inquiry sentence while preserving any scenario preamble before it
        first_inquiry_idx = inquiry_sentences_indices[0]
        selected_sentences = raw_sentences[: first_inquiry_idx + 1]
        cleaned_masked = " ".join(selected_sentences).strip()
        cleaned = unmask_protected_spans(cleaned_masked, placeholders).strip()
        masked, placeholders = mask_protected_spans(cleaned)

    # 3. Check for compound conjunction inquiries within a single question mark
    # Only cut if the clause BEFORE the conjunction possesses a true inquiry predicate!
    for pat in COMPOUND_CONJUNCTION_PATTERNS:
        match = re.search(pat, masked, flags=re.IGNORECASE)
        if match:
            left_part_masked = masked[: match.start()].strip()
            left_part_unmasked = unmask_protected_spans(left_part_masked, placeholders)
            if has_true_inquiry_predicate(left_part_unmasked) and len(left_part_unmasked) >= 20:
                if not left_part_unmasked.endswith("?"):
                    left_part_unmasked += "?"
                cleaned = left_part_unmasked
                masked, placeholders = mask_protected_spans(cleaned)
                break

    # Unmask protected content
    cleaned = unmask_protected_spans(cleaned, placeholders).strip()

    # 4. Final normalization
    cleaned = re.sub(r"\?\*+$", "?", cleaned).strip()
    if not cleaned.endswith("?"):
        cleaned = cleaned.rstrip(".! *#") + "?"

    # Remove duplicate internal whitespace and collapse single newlines into continuous prose
    cleaned = re.sub(r"(?<!\n)\n(?!\n)", " ", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned


def validate_question_semantics(text: str) -> Tuple[bool, str]:
    """
    Validates that candidate-facing question text conforms to single primary inquiry standards:
    1. Between 20 and 600 characters in length.
    2. Ends with a single question mark.
    3. Contains an interrogative predicate or directive.
    4. Free of leaked rubrics, internal system metadata, or markdown role headers.
    5. Free of dangling grammatical fragments (e.g., ending in 'and?', 'with?').
    6. Contains exactly one unmasked question mark.
    """
    if not text or not text.strip():
        return False, "Empty question text"

    t = text.strip()
    if len(t) < 20:
        return False, f"Question too short ({len(t)} chars)"
    if len(t) > 600:
        return False, f"Question exceeds maximum length ({len(t)} chars)"
    if not t.endswith("?"):
        return False, "Question must end with '?'"

    masked, _ = mask_protected_spans(t)
    if masked.count("?") > 1:
        return False, f"Question contains multiple unmasked inquiries ({masked.count('?')} '?')"

    # Check for leaked rubrics or metadata
    leak_match = re.search(
        r"\b(?:rubric|evaluation criteria|scoring guide|target competency|expected concepts?|candidate should)\b",
        t,
        flags=re.I,
    )
    if leak_match:
        return False, f"Leaked rubric or internal metadata detected: '{leak_match.group(0)}'"

    # Check for dangling fragments (coordinating conjunctions and prepositions)
    dangling_match = re.search(
        r"\b(?:and|or|with|because|to|the|if|as|but|so|from|at|by|for)\s*\?$",
        t,
        flags=re.I,
    )
    if dangling_match:
        return False, f"Dangling grammatical fragment ending in '{dangling_match.group(0)}'"

    # Check for true inquiry predicate
    if not has_true_inquiry_predicate(t):
        return False, "Question lacks an inquiry predicate or directive"

    return True, "Valid single primary question"


# Patterns detecting compound secondary constraints and auxiliary evaluation bundles
COMPOUND_CONSTRAINT_PATTERNS = [
    # Cascading secondary constraints: while maintaining X and preventing Y
    r"\bwhile\s+(?:also\s+)?(?:maintaining|ensuring|preserving|preventing|minimizing|optimizing|handling)\b.*?\band\s+(?:maintaining|ensuring|preserving|preventing|minimizing|optimizing|handling)\b",
    r"\bwhile\s+(?:maintaining|ensuring|preserving)\b.*?\band\s+(?:preventing|minimizing|securing)\b",
    # Compound auxiliary evaluation scope: considering the potential impact on X and Y
    r"\bconsidering\s+(?:the\s+)?(?:potential\s+)?(?:impact|trade-offs?|effects?)\s+on\b.*?\band\b",
    # Secondary compound requirement: while also balancing/optimizing/handling
    r"\bwhile\s+also\s+(?:balancing|handling|optimizing|ensuring|minimizing|preventing|managing)\b",
]

COMPOUND_INQUIRY_PATTERNS = [
    r",\s*(?:and|as well as|along with)\s+(?:how|what|why|which|where|when|explain|describe)\b",
    r"\band\s+how\s+(?:would|do|can|does|is|are)\b",
]


def validate_substantive_question_focus(text: str) -> Tuple[bool, str]:
    """
    Validates that candidate-facing question text maintains a single substantive evaluation focus.
    Rejects questions that bundle multiple independent design decisions,
    multiple evaluation targets joined with compound conjunctions, or
    auxiliary constraint cascades (e.g. 'while maintaining X and preventing Y',
    'considering the potential impact on X and Y').

    Accepts single scenario sentences followed by exactly ONE primary inquiry.
    """
    if not text or not text.strip():
        return False, "Empty question text"

    # 1. First run basic semantic checks (length, single ?, no leaked rubrics)
    is_valid, sem_reason = validate_question_semantics(text)
    if not is_valid:
        return False, sem_reason

    masked, _ = mask_protected_spans(text)

    # 2. Check for compound secondary constraint cascades
    for pat in COMPOUND_CONSTRAINT_PATTERNS:
        m = re.search(pat, masked, flags=re.IGNORECASE)
        if m:
            return False, f"Bundles multiple substantive constraints/targets: '{m.group(0).strip()}'"

    # 3. Check for multiple coordinated inquiries where preceding clause also contains an inquiry
    for pat in COMPOUND_INQUIRY_PATTERNS:
        m = re.search(pat, masked, flags=re.IGNORECASE)
        if m:
            pre_clause = masked[: m.start()].strip()
            if has_true_inquiry_predicate(pre_clause):
                return False, f"Combines multiple independent inquiries in one sentence: '{m.group(0).strip()}'"

    # 4. Check for numbered or bulleted sub-questions
    if re.search(r"(?:^|\s)(?:1[\.\)]\s+.*?\s+2[\.\)]|[-*•]\s+.*?\n\s*[-*•])", masked, flags=re.DOTALL):
        return False, "Contains numbered or bulleted multi-part inquiries"

    # 5. Check for multiple sentences containing independent inquiry predicates
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", masked) if s.strip()]
    inquiry_sentences = [s for s in raw_sentences if has_true_inquiry_predicate(s)]
    if len(inquiry_sentences) > 1:
        return (
            False,
            f"Combines multiple independent inquiry sentences: '{inquiry_sentences[0][:60]}...' and '{inquiry_sentences[1][:60]}...'",
        )

    return True, "Focused single substantive inquiry"


class CompetencyAlignmentError(ValueError):
    """Raised when a question cannot be aligned with the canonical assessment target competency."""
    pass


GENERIC_DOMAIN_VOCABULARY = {
    "distributed", "database", "databases", "system", "systems", "architecture",
    "architectures", "infrastructure", "software", "engineering", "application",
    "applications", "design", "principles", "principle", "foundations", "foundation",
    "fundamentals", "overview", "internals", "internal", "mechanics", "management",
    "patterns", "pattern", "performance", "scalability", "scalable", "service",
    "services", "data", "storage", "cloud", "backend", "frontend", "web",
    "implementation", "deep", "dive", "code", "mode", "modes", "file", "files",
    "state", "handling", "processing", "solution", "solutions", "approach",
    "approaches", "technique", "techniques", "concept", "concepts", "computing",
    "computer", "network", "networks", "networking", "core", "theory", "theoretical",
    "practical", "advanced", "baseline", "cache", "memory", "limits", "throughput",
    "latency", "layer", "layers", "buffer", "buffers", "queue", "queues", "pipeline",
    "pipelines", "cluster", "clusters", "node", "nodes", "query", "queries", "read",
    "reads", "write", "writes", "table", "tables", "client", "clients", "server",
    "servers", "scale", "overhead", "tradeoff", "trade-off", "tradeoffs", "trade-offs",
    "optimization", "optimizations", "strategy", "strategies", "mechanism", "mechanisms",
    "protection", "prevention", "mitigation", "best", "practices"
}

# Domain synonym dictionaries for high-precision deterministic competency verification
DOMAIN_COMPETENCY_SYNONYMS = {
    "concurrency": [
        "mvcc", "transaction", "transactions", "isolation", "concurrency", "acid", "write skew",
        "phantom read", "dirty read", "dirty write", "deadlock", "deadlocks", "optimistic concurrency",
        "pessimistic lock", "pessimistic locking", "row-level lock", "row lock", "select for update", "two-phase locking",
        "serializable", "serializability", "repeatable read", "read committed", "snapshot isolation",
        "lock contention", "lost update", "lost updates", "database concurrency", "async", "asyncio",
        "event loop", "thread", "threads", "threadpool", "goroutine", "mutex", "mutexes", "race condition",
        "critical section", "lock-free", "compare-and-swap", "cas", "read skew", "serializability violation",
        "optimistic locking"
    ],
    "micro-frontend": [
        "micro-frontend", "micro-frontends", "microfrontend", "microfrontends", "micro frontend",
        "micro frontends", "module federation", "webpack module federation", "iframe", "iframes", "sandboxing", "sandbox",
        "shadow dom", "web components", "css scoping", "scoped css", "style leakage", "sub-app", "sub-application",
        "sub-applications", "single-spa", "single spa", "import maps", "namespace pollution", "host container", "shell container",
        "remote container", "remote entry", "independent deployment", "runtime isolation", "shell application", "micro-frontend isolation"
    ],
    "model_serving": [
        "continuous batching", "iteration-level", "pagedattention", "kv cache", "model serving",
        "throughput", "vllm", "tensor parallelism", "dynamic batching", "head-of-line blocking",
        "head of line", "preemption", "gpu batching", "latency-throughput", "inference serving",
        "model serving throughput", "serving throughput", "inference", "speculative decoding",
        "quantization", "tensorrt-llm", "triton inference server"
    ],
    "feature_store": [
        "feature store", "point-in-time", "data leakage", "training-serving skew", "feast",
        "offline store", "online store", "feature drift", "timestamp join", "entity key",
        "feature store consistency", "point-in-time correctness", "hopsworks", "tecton"
    ],
    "caching": [
        "cache", "caching", "redis", "memcached", "cache-aside", "write-through", "write-behind",
        "cache invalidation", "cache stampede", "thundering herd", "eviction", "ttl", "stale data",
        "distributed caching", "lru", "lfu", "consistent hashing", "hash ring", "virtual nodes",
        "cache penetration", "cache avalanche"
    ],
    "dom_reconciliation": [
        "reconciliation", "virtual dom", "fiber", "work loop", "time slicing", "diffing",
        "dom tree", "synthetic event", "react.memo", "rerender", "re-render", "component lifecycle"
    ],
    "consensus": [
        "consensus", "quorum", "raft", "paxos", "split-brain", "linearizability", "linearizable",
        "leader election", "term number", "state machine replication", "log compaction",
        "distributed consensus", "viewstamped replication", "zab", "multi-paxos", "etcd",
        "leaderless", "dynamo", "vector clock", "vector clocks", "gossip protocol", "two-phase commit",
        "2pc", "atomic broadcast", "safety invariant", "liveness invariant", "election timeout",
        "heartbeat quorum", "split vote", "split-vote", "majority vote", "majority quorum",
        "quorum arithmetic", "quorum intersection", "leader safety", "log matching", "byzantine fault tolerance",
        "bft", "f+1", "2f+1"
    ],
    "resilience": [
        "circuit breaker", "backpressure", "bulkhead", "half-open", "cascading failure",
        "exponential backoff", "jitter", "rate limiting", "throttling", "token bucket",
        "leaky bucket", "sliding window counter", "retry storm", "fail-fast", "load shedding"
    ],
    "iac": [
        "terraform", "infrastructure as code", "drift detection", "configuration drift", "state locking",
        "remote state", "state lock", "immutable infrastructure", "cloudformation", "ansible", "pulumi",
        "cloud security", "iac", "dynamodb lock", "s3 backend", "backend s3", "iam", "least privilege",
        "least-privilege", "plan vs apply", "declarative infrastructure"
    ],
    "api_architecture": [
        "api", "apis", "endpoint", "endpoints", "rest", "fastapi", "graphql", "http",
        "idempotency", "idempotent", "idempotency keys", "retry semantics", "safe retry",
        "deduplication", "event loop blocking"
    ],
    "algorithms": [
        "algorithmic", "algorithm", "algorithms", "complexity", "big-o", "asymptotic",
        "time complexity", "space complexity", "sliding window", "two pointers", "two pointer",
        "amortized", "amortized analysis", "invariants", "boundary edge cases", "data structure",
        "data structures", "tree", "graph", "sorting", "recursion", "dynamic programming", "memoization",
        "recurrence relation", "prefix sum", "in-place", "tail call", "space-time tradeoff",
        "binary search", "monotonic stack"
    ],
    "modular_architecture": [
        "solid", "dependency inversion", "clean architecture", "hexagonal", "domain-driven",
        "loose coupling", "separation of concerns", "modularity", "interface", "decomposition",
        "dependency injection", "system decomposition", "bounded context", "ports and adapters",
        "interface segregation"
    ],
    "containers": [
        "kubernetes", "k8s", "cni", "pod lifecycle", "sigterm", "readiness probe", "liveness probe",
        "kube-proxy", "prestop", "namespaces", "cgroups", "docker", "container", "containers",
        "container orchestration", "node affinity", "ingress", "ipam", "ip allocation",
        "container network interface", "pod churn"
    ],
    "vector_search": [
        "hnsw", "ivf", "ivf-pq", "ann", "product quantization", "vector search", "embedding",
        "nearest neighbor", "efsearch", "nprobe", "voronoi", "similarity", "cosine", "dot product",
        "diskann", "reranking", "reranker", "cross-encoder", "vector index", "scalar quantization",
        "quantization", "recall", "ram overhead", "hosting costs", "p99"
    ],
    "rag": [
        "rag", "bm25", "hybrid retrieval", "sparse", "dense", "reciprocal rank fusion", "rrf",
        "lexical", "chunking", "re-ranker", "rerank", "fusion", "cross-encoder", "semantic similarity"
    ],
    "iot_telemetry": [
        "mqtt", "coap", "qos", "telemetry", "sensor", "udp", "battery", "sram", "backpressure",
        "ring buffer", "flash", "wear leveling", "cellular", "power consumption", "packet buffering"
    ],
    "machine_learning": [
        "model", "training", "inference", "drift", "feature store", "pipeline", "latency",
        "throughput", "overfitting", "validation", "batching", "gpu", "precision", "loss", "recall"
    ],
}

KNOWN_ACRONYMS = {
    "api", "dom", "sql", "wal", "ann", "llm", "kv", "gpu", "cpu", "gil", "acid", "mvcc",
    "raft", "ttl", "lru", "lfu", "iac", "sre", "cni", "slo", "sla", "sli", "ami", "iam", "bft", "2pc"
}



DOMAIN_NEGATIVE_SIGNATURES = {
    "model_serving": {
        "negative_keywords": [
            "cache stampede", "thundering herd", "primary database", "redis cluster",
            "cache-aside", "write-through", "cache invalidation", "stale-while-revalidate",
            "acid", "mvcc", "mqtt", "coap", "sensor"
        ],
        "positive_anchors": [
            "continuous batching", "pagedattention", "paged attention", "kv cache",
            "tensor parallelism", "tensorrt", "vllm", "quantization", "gpu", "inference",
            "token generation", "speculative decoding", "llm"
        ],
        "domain_name": "Model Serving & Inference Latency",
        "conflicting_domain": "Backend Database Caching / IoT",
    },
    "caching": {
        "negative_keywords": [
            "continuous batching", "pagedattention", "paged attention", "kv cache",
            "tensor parallelism", "tensorrt", "vllm", "int8 quantization", "speculative decoding",
            "mqtt", "coap"
        ],
        "positive_anchors": [
            "cache", "caching", "cache stampede", "thundering herd", "cache invalidation",
            "cache-aside", "write-through", "redis", "memcached", "lru", "ttl", "stale data"
        ],
        "domain_name": "Distributed Caching & Invalidation",
        "conflicting_domain": "LLM Inference Serving / IoT",
    },
    "vector_search": {
        "negative_keywords": [
            "mqtt", "coap", "sensor", "battery drain", "sram buffer",
            "cache stampede", "thundering herd", "primary database"
        ],
        "positive_anchors": [
            "hnsw", "ivf", "ivf-pq", "vector", "embedding", "nearest neighbor",
            "product quantization", "ann", "diskann", "similarity"
        ],
        "domain_name": "Vector Indexing & ANN Search",
        "conflicting_domain": "IoT Telemetry / Database Caching",
    },
    "rag": {
        "negative_keywords": [
            "mqtt", "coap", "sensor", "battery drain", "sram buffer", "microcontroller",
            "cache stampede", "thundering herd"
        ],
        "positive_anchors": [
            "rag", "bm25", "hybrid retrieval", "dense vector", "lexical",
            "reciprocal rank fusion", "cross-encoder", "reranking", "chunking"
        ],
        "domain_name": "RAG & Hybrid Retrieval",
        "conflicting_domain": "IoT Telemetry / Database Caching",
    },
    "iot_telemetry": {
        "negative_keywords": [
            "hnsw", "ivf-pq", "vector search", "bm25", "dense retrieval", "reciprocal rank fusion",
            "continuous batching", "paged attention", "pagedattention", "kv cache"
        ],
        "positive_anchors": [
            "mqtt", "coap", "telemetry", "sensor", "qos", "microcontroller",
            "sram", "battery", "udp", "embedded"
        ],
        "domain_name": "IoT Telemetry & Constrained Protocols",
        "conflicting_domain": "Vector Search / LLM Serving",
    },
    "consensus": {
        "negative_keywords": [
            "continuous batching", "pagedattention", "kv cache", "hnsw", "mqtt", "coap"
        ],
        "positive_anchors": [
            "raft", "paxos", "consensus", "quorum", "split-brain", "linearizability",
            "leader election", "log compaction"
        ],
        "domain_name": "Distributed Consensus & Replication",
        "conflicting_domain": "LLM Serving / Vector Search",
    },
}


def _extract_domain_keywords_for_competency(
    competency_name: str,
    expected_concepts: Optional[List[str]] = None,
    core_invariants: Optional[List[str]] = None,
) -> List[str]:
    """
    Extracts relevant domain keywords, stem tokens, and concept phrases for a given competency.
    Filters out common stopwords and generic domain vocabulary.
    """
    keywords: List[str] = []
    comp_lower = competency_name.lower()

    stopwords = {
        "and", "or", "in", "of", "for", "the", "a", "an", "to", "with", "vs", "versus",
        "levels", "level", "control", "mechanics", "patterns", "pattern", "architecture", "systems", "system",
        "engineering", "fundamentals", "implementation", "deep", "dive", "management",
        "reads", "read", "writes", "write", "data", "file", "files", "mode", "modes", "code"
    }

    # 1. Add direct expected concepts
    if expected_concepts:
        for c in expected_concepts:
            c_clean = c.strip().lower()
            if c_clean and c_clean not in keywords and c_clean not in stopwords and c_clean not in GENERIC_DOMAIN_VOCABULARY:
                keywords.append(c_clean)
                for part in re.split(r"[\s/_-]+", c_clean):
                    if len(part) >= 4 and part not in keywords and part not in stopwords and part not in GENERIC_DOMAIN_VOCABULARY:
                        keywords.append(part)

    # 2. Add core invariants terms
    if core_invariants:
        for inv in core_invariants:
            inv_clean = inv.strip().lower()
            if inv_clean and inv_clean not in keywords and inv_clean not in stopwords and inv_clean not in GENERIC_DOMAIN_VOCABULARY:
                keywords.append(inv_clean)
                for part in re.split(r"[\s/_-]+", inv_clean):
                    if len(part) >= 4 and part not in keywords and part not in stopwords and part not in GENERIC_DOMAIN_VOCABULARY:
                        keywords.append(part)

    # 3. Add competency tokens (filtering out common stopwords and generic vocabulary)
    for word in re.split(r"[\s/&_-]+", comp_lower):
        clean_word = word.strip()
        if (
            len(clean_word) >= 4
            and clean_word not in stopwords
            and clean_word not in GENERIC_DOMAIN_VOCABULARY
            and clean_word not in keywords
        ):
            keywords.append(clean_word)

    # 4. Add domain synonym catalog terms
    if any(k in comp_lower for k in ["concurrency", "isolation", "transaction", "acid"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["concurrency"] if s not in keywords])
    if any(k in comp_lower for k in ["micro-frontend", "microfrontend", "micro frontend"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["micro-frontend"] if s not in keywords])
    if any(k in comp_lower for k in ["model serving", "serving throughput", "serving", "quantization"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["model_serving"] if s not in keywords])
    if any(k in comp_lower for k in ["feature store", "feature consistency"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["feature_store"] if s not in keywords])
    if any(k in comp_lower for k in ["cache", "caching", "partitioning"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["caching"] if s not in keywords])
    if any(k in comp_lower for k in ["dom", "reconciliation", "fiber"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["dom_reconciliation"] if s not in keywords])
    if any(k in comp_lower for k in ["consensus", "quorum", "raft", "paxos"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["consensus"] if s not in keywords])
    if any(k in comp_lower for k in ["circuit", "resilience", "backpressure", "breaker"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["resilience"] if s not in keywords])
    if any(k in comp_lower for k in ["iac", "terraform", "infrastructure as code", "cloud security"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["iac"] if s not in keywords])
    if any(k in comp_lower for k in ["api", "idempotency", "endpoint", "rest"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["api_architecture"] if s not in keywords])
    if any(k in comp_lower for k in ["algorithm", "algorithmic", "complexity", "big-o", "invariants"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["algorithms"] if s not in keywords])
    if any(k in comp_lower for k in ["modular", "clean architecture", "decomposition", "solid"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["modular_architecture"] if s not in keywords])
    if any(k in comp_lower for k in ["container", "kubernetes", "cni", "pod", "orchestration"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["containers"] if s not in keywords])
    if any(k in comp_lower for k in ["vector", "embedding", "hnsw", "ivf", "indexing", "ann"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["vector_search"] if s not in keywords])
    if any(k in comp_lower for k in ["rag", "bm25", "hybrid retrieval", "sparse", "dense"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["rag"] if s not in keywords])
    if any(k in comp_lower for k in ["iot", "telemetry", "sensor", "mqtt", "coap", "constrained"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["iot_telemetry"] if s not in keywords])
    if any(k in comp_lower for k in ["machine learning", "ml", "model", "inference"]):
        keywords.extend([s for s in DOMAIN_COMPETENCY_SYNONYMS["machine_learning"] if s not in keywords])

    return keywords


def validate_question_competency_alignment(
    question_text: str,
    target_competency: str,
    expected_concepts: Optional[List[str]] = None,
    core_invariants: Optional[List[str]] = None,
    preceding_competency: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Deterministically verifies that candidate-facing question text actually assesses
    the selected canonical target competency rather than drifting to preceding competencies
    or asking off-topic questions.

    Checks:
    1. Matches at least one SUBSTANTIVE domain keyword, concept, or technical invariant from target competency.
    2. Rejects questions matching solely generic shared vocabulary (e.g. 'distributed', 'database', 'architecture').
    3. Rejects questions where preceding competency keywords dominate and target competency concepts are absent.
    4. Handles in-competency follow-up vs cross-competency transitions safely.
    """
    if not question_text or not question_text.strip():
        return False, "Question text is empty"

    if not target_competency or not target_competency.strip():
        return False, "Target competency is missing or empty"

    q_lower = question_text.lower()
    target_comp_clean = target_competency.strip()

    # Generic role baseline bypass (e.g. when question_plan is absent and role is used as placeholder)
    generic_role_indicators = [
        "omnirole", "universal software engineering", "universal", "software engineer",
        "backend systems engineer", "backend_systems_engineer", "systems engineer",
        "general", "technical"
    ]
    if (
        target_comp_clean.lower() in generic_role_indicators
        or "universal software engineering" in target_comp_clean.lower()
        or target_comp_clean.lower().endswith(("engineer", "architect", "sre", "developer"))
    ):
        return True, f"Generic role competency baseline: '{target_competency}'"

    # Domain Isolation & Cross-Domain Boundary Verification
    comp_norm = target_comp_clean.lower().replace("-", "_").replace(" ", "_")
    matched_domain_key = None
    for dom_key in DOMAIN_NEGATIVE_SIGNATURES:
        if dom_key in comp_norm or any(part in comp_norm for part in dom_key.split("_") if len(part) >= 4):
            matched_domain_key = dom_key
            break

    if matched_domain_key:
        dom_spec = DOMAIN_NEGATIVE_SIGNATURES[matched_domain_key]
        neg_hits = [
            kw for kw in dom_spec["negative_keywords"]
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower)
        ]
        pos_hits = [
            kw for kw in dom_spec["positive_anchors"]
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower)
        ]
        if neg_hits and not pos_hits:
            return (
                False,
                f"Question assesses {dom_spec['conflicting_domain']} (detected: {', '.join(neg_hits[:2])}) "
                f"instead of canonical target competency '{target_competency}' ({dom_spec['domain_name']}).",
            )

    target_keywords = _extract_domain_keywords_for_competency(
        competency_name=target_comp_clean,
        expected_concepts=expected_concepts,
        core_invariants=core_invariants,
    )

    # Detect matching target concepts
    target_hits: List[str] = []
    for kw in target_keywords:
        pattern = r"\b" + re.escape(kw) + r"\b" if " " not in kw else re.escape(kw)
        if re.search(pattern, q_lower):
            if kw not in target_hits:
                target_hits.append(kw)

    # Preceding competency contamination check
    is_transition = False
    preceding_hits: List[str] = []
    if preceding_competency and preceding_competency.strip():
        p_clean = preceding_competency.strip()
        if p_clean.lower() != target_comp_clean.lower():
            is_transition = True
            preceding_keywords = _extract_domain_keywords_for_competency(p_clean)
            for pkw in preceding_keywords:
                # Only check keywords that are unique to the preceding competency
                if pkw not in target_keywords:
                    pattern = r"\b" + re.escape(pkw) + r"\b" if " " not in pkw else re.escape(pkw)
                    if re.search(pattern, q_lower):
                        if pkw not in preceding_hits:
                            preceding_hits.append(pkw)

    # Substantive target evidence check:
    # A question cannot pass solely through generic shared vocabulary (e.g. 'distributed', 'database', 'system', 'architecture')
    substantive_target_hits = [h for h in target_hits if h.lower() not in GENERIC_DOMAIN_VOCABULARY]

    # Evaluation Rules:
    if not target_hits or not substantive_target_hits:
        if is_transition and preceding_hits:
            return (
                False,
                f"Question assesses preceding competency '{preceding_competency}' "
                f"(detected: {', '.join(preceding_hits[:3])}) instead of canonical target competency '{target_competency}'.",
            )
        matched_sample = f" (matched generic: {', '.join(target_hits[:3])})" if target_hits else ""
        return (
            False,
            f"Question lacks substantive conceptual evidence for canonical target competency '{target_competency}'"
            f"{matched_sample} (expected concepts: {', '.join((expected_concepts or [])[:3]) or target_competency}).",
        )

    # If preceding keywords heavily dominate target keywords during a transition
    if is_transition and len(preceding_hits) >= 2 and len(substantive_target_hits) <= 1:
        return (
            False,
            f"Question is primarily focused on preceding competency '{preceding_competency}' "
            f"(detected: {', '.join(preceding_hits[:3])}) rather than canonical target competency '{target_competency}'.",
        )

    return True, f"Aligned with canonical target competency '{target_competency}' (matched: {', '.join(substantive_target_hits[:3])})"


