"""
Zero-Repetition Question Bank & Skill-Indexed Interview Matrix.
Provides a comprehensive set of curated, high-yield technical and behavioral
questions mapped across candidate skill domains and the 5 progressive interview stages.
"""

from typing import List, Dict, Any, Optional, Tuple

QUESTION_BANK: List[Dict[str, Any]] = [
    # =========================================================================
    # STAGE 1: FOUNDATIONAL ORIENTATION (Domain Fundamentals & Resume Grounding)
    # =========================================================================
    {
        "id": "cache_stage1_01",
        "skills": ["caching", "cache", "backend", "distributed caching", "cache invalidation", "redis"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Caching Fundamentals & Purpose",
        "difficulty": "easy",
        "depth_level": "FOUNDATION",
        "question": (
            "In backend architecture, why do we introduce an in-memory cache in front of a primary database?"
        ),
        "expected_concepts": [
            "latency reduction", "read-heavy workloads", "database offloading",
            "staleness tolerance", "ttl", "cache hit ratio"
        ],
        "resume_evidence": "Candidate caching and backend optimization fundamentals.",
    },
    {
        "id": "cache_stage2_01",
        "skills": ["caching", "cache", "backend", "distributed caching", "cache invalidation", "redis"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Cache Invalidation & Consistency Boundaries",
        "difficulty": "medium",
        "depth_level": "PRACTICAL",
        "question": (
            "In a practical web application with a cache in front of a database, "
            "what specific invalidation strategy do you use when a record is updated in the database?"
        ),
        "expected_concepts": [
            "cache invalidation", "cache-aside pattern", "stale data prevention",
            "delete on update vs overwrite", "write-through", "ttl fallback"
        ],
        "resume_evidence": "Candidate practical caching and data consistency experience.",
    },
    {
        "id": "cache_stage2_02",
        "skills": ["caching", "cache", "backend", "distributed caching", "cache invalidation", "redis"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Cache Invalidation Failure & Inconsistency",
        "difficulty": "medium",
        "depth_level": "FOLLOW_UP",
        "question": (
            "If the primary database update succeeds but the cache invalidation call fails, "
            "how do you handle that temporary inconsistency?"
        ),
        "expected_concepts": [
            "cache invalidation", "eventual consistency", "ttl",
            "retry with backoff", "transactional outbox", "stale data"
        ],
        "resume_evidence": "Candidate edge-case cache consistency and failure recovery.",
    },
    {
        "id": "py_stage1_01",
        "skills": ["python", "backend", "fastapi", "django"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Python Memory Management & Concurrency",
        "difficulty": "medium",
        "question": (
            "In Python, how does the Global Interpreter Lock (GIL) impact CPU-bound versus I/O-bound multi-threaded workloads?"
        ),
        "expected_concepts": [
            "GIL", "multithreading vs multiprocessing", "CPU-bound vs I/O-bound",
            "concurrency", "process isolation"
        ],
        "resume_evidence": "Candidate Python / backend experience.",
    },
    {
        "id": "py_stage1_02",
        "skills": ["python", "fastapi", "asyncio", "rest"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Asynchronous Event Loops in FastAPI",
        "difficulty": "medium",
        "question": (
            "When designing an asynchronous API with FastAPI, what is the operational impact of running a blocking synchronous "
            "database query inside an `async def` endpoint?"
        ),
        "expected_concepts": [
            "event loop blocking", "run_in_executor", "starlette threadpool",
            "async def vs def", "thread starvation", "concurrency"
        ],
        "resume_evidence": "Candidate FastAPI / asynchronous programming experience.",
    },
    {
        "id": "fe_stage1_01",
        "skills": ["react", "javascript", "typescript", "frontend"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "React Rendering Lifecycle & Virtual DOM",
        "difficulty": "medium",
        "question": (
            "When state updates in a React component, how does the reconciliation algorithm determine which DOM nodes need modifying?"
        ),
        "expected_concepts": [
            "reconciliation", "fiber tree", "virtual dom diffing",
            "stable keys", "useMemo", "useCallback", "React.memo"
        ],
        "resume_evidence": "Candidate React / frontend development experience.",
    },
    {
        "id": "db_stage1_01",
        "skills": ["sql", "postgresql", "mysql", "database", "backend"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Relational Indexing & Query Plans",
        "difficulty": "medium",
        "question": (
            "When an SQL query on a table with millions of rows experiences high latency, how does a B-tree index accelerate lookups?"
        ),
        "expected_concepts": [
            "b-tree index", "selectivity", "explain analyze",
            "sequential scan vs index scan", "composite index order", "index bloat"
        ],
        "resume_evidence": "Candidate SQL database and schema modeling background.",
    },
    {
        "id": "ml_stage1_01",
        "skills": ["machine learning", "deep learning", "ai", "pytorch", "tensorflow", "python"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Bias-Variance Tradeoff & Model Generalization",
        "difficulty": "medium",
        "question": (
            "How do you identify overfitting versus underfitting in a machine learning pipeline using training and validation curves, "
            "and what specific regularization techniques do you apply to mitigate them?"
        ),
        "expected_concepts": [
            "bias-variance tradeoff", "overfitting", "validation curve",
            "l1/l2 regularization", "dropout", "cross-validation", "early stopping"
        ],
        "resume_evidence": "Candidate Machine Learning / Data Science experience.",
    },
    {
        "id": "general_stage1_01",
        "skills": ["software engineering", "general", "developer"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Software Design Principles & Modularity",
        "difficulty": "medium",
        "question": (
            "Looking across your development experience, how do you apply the SOLID principles—specifically Dependency Inversion "
            "and Single Responsibility—to keep code maintainable as team size and complexity grow?"
        ),
        "expected_concepts": [
            "single responsibility", "dependency inversion", "interfaces/abstractions",
            "loose coupling", "high cohesion", "unit testability"
        ],
        "resume_evidence": "Candidate software engineering fundamentals.",
    },

    # =========================================================================
    # STAGE 2: CORE IMPLEMENTATION & MECHANICS (Algorithmic & Code Trade-offs)
    # =========================================================================
    {
        "id": "py_stage2_01",
        "skills": ["python", "backend", "data structures", "algorithms"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "coding_theory",
        "topic": "Data Structure Selection & Amortized Complexity",
        "difficulty": "medium",
        "question": (
            "Compare the internal implementation, time complexity, and memory overhead of a Python `list` versus a `collections.deque` "
            "when implementing a high-throughput FIFO queue. Why is `pop(0)` on a list problematic?"
        ),
        "expected_concepts": [
            "dynamic array vs doubly linked list", "o(1) vs o(n) pop",
            "memory over-allocation", "amortized time complexity", "cache locality"
        ],
        "resume_evidence": "Candidate backend data structures background.",
    },
    {
        "id": "fe_stage2_01",
        "skills": ["react", "typescript", "frontend", "state management"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "coding_theory",
        "topic": "Complex Frontend State Management & Immutability",
        "difficulty": "medium",
        "question": (
            "When dealing with nested client state or real-time streaming data, how do you enforce state immutability, "
            "and what are the architectural trade-offs between local component state, Context API, and external stores like Zustand or Redux?"
        ),
        "expected_concepts": [
            "immutability", "context re-render overhead", "selector-based subscriptions",
            "predictable state mutations", "structural sharing"
        ],
        "resume_evidence": "Candidate frontend state management implementation.",
    },
    {
        "id": "db_stage2_01",
        "skills": ["sql", "postgresql", "database", "backend", "concurrency", "isolation", "database concurrency & isolation", "transactions", "acid", "mvcc"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "coding_theory",
        "topic": "ACID Invariants & Transaction Isolation Levels",
        "difficulty": "hard",
        "question": (
            "In relational transaction processing, what are the differences between Read Committed, Repeatable Read, and Serializable? "
            "Describe a concrete scenario where a Phantom Read or Write Skew occurs if isolation is insufficient."
        ),
        "expected_concepts": [
            "acid properties", "read committed vs repeatable read", "serializable",
            "dirty reads", "phantom reads", "write skew", "mvcc", "locks"
        ],
        "resume_evidence": "Candidate database transaction management background.",
    },
    {
        "id": "db_stage2_concurrency_02",
        "skills": ["database", "backend", "concurrency", "isolation", "database concurrency & isolation", "transactions", "mvcc", "locks"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Database Concurrency & Isolation",
        "difficulty": "medium",
        "depth_level": "PRACTICAL",
        "question": (
            "When concurrent transactions update the same balance records, how do you prevent lost updates using optimistic concurrency control versus pessimistic locking?"
        ),
        "expected_concepts": [
            "lost updates", "optimistic concurrency control", "pessimistic locking", "select for update", "version column", "isolation levels", "write skew"
        ],
        "resume_evidence": "Candidate database concurrency and transaction isolation experience.",
    },
    {
        "id": "db_stage2_concurrency_03",
        "skills": ["database", "backend", "concurrency", "isolation", "database concurrency & isolation", "transactions", "mvcc"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Write Skew & Snapshot Isolation",
        "difficulty": "hard",
        "depth_level": "FOLLOW_UP",
        "question": (
            "How does Multi-Version Concurrency Control (MVCC) snapshot isolation permit write skew anomalies even when dirty reads and non-repeatable reads are prevented?"
        ),
        "expected_concepts": [
            "mvcc", "snapshot isolation", "write skew", "serializable snapshot isolation", "transaction isolation levels"
        ],
        "resume_evidence": "Candidate advanced transaction isolation and anomaly prevention.",
    },
    {
        "id": "mfe_stage2_01",
        "skills": ["frontend", "micro-frontend", "microfrontend", "micro-frontend isolation", "module federation", "architecture", "isolation"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Micro-Frontend Isolation & Runtime Sandboxing",
        "difficulty": "medium",
        "depth_level": "PRACTICAL",
        "question": (
            "When composing multiple independently deployed micro-frontends on a single page, how do you enforce runtime isolation to prevent global CSS collisions and JavaScript scope leakage?"
        ),
        "expected_concepts": [
            "micro-frontend isolation", "module federation", "shadow dom", "css scoping", "iframe sandboxing", "runtime boundaries", "sub-applications"
        ],
        "resume_evidence": "Candidate micro-frontend modularity and isolation architecture.",
    },
    {
        "id": "mfe_stage2_02",
        "skills": ["frontend", "micro-frontend", "microfrontend", "micro-frontend isolation", "module federation", "architecture", "isolation"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Micro-Frontend Cross-App Communication",
        "difficulty": "medium",
        "depth_level": "FOLLOW_UP",
        "question": (
            "How do you design a decoupled event communication bus between micro-frontend sub-applications without creating tight runtime coupling or leaking state?"
        ),
        "expected_concepts": [
            "event bus", "micro-frontend isolation", "custom events", "loosely coupled communication", "shared state boundaries"
        ],
        "resume_evidence": "Candidate micro-frontend inter-application messaging.",
    },
    {
        "id": "ml_serving_stage2_01",
        "skills": ["machine learning", "model serving", "model serving throughput", "continuous batching", "pagedattention", "inference"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Model Serving Throughput & Continuous Batching",
        "difficulty": "medium",
        "depth_level": "PRACTICAL",
        "question": (
            "In high-throughput LLM model serving, how does continuous iteration-level batching with PagedAttention resolve memory fragmentation and head-of-line blocking in the KV cache?"
        ),
        "expected_concepts": [
            "continuous batching", "pagedattention", "kv cache", "head-of-line blocking", "model serving throughput", "memory fragmentation"
        ],
        "resume_evidence": "Candidate LLM model serving and throughput optimization.",
    },
    {
        "id": "ml_feature_stage2_01",
        "skills": ["machine learning", "feature store", "feature store consistency", "point-in-time", "data leakage", "mlops"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Feature Store Consistency & Point-in-Time Correctness",
        "difficulty": "medium",
        "depth_level": "PRACTICAL",
        "question": (
            "When serving machine learning features across real-time APIs and offline model training, how does a feature store maintain point-in-time correctness to prevent data leakage?"
        ),
        "expected_concepts": [
            "feature store consistency", "point-in-time correctness", "data leakage", "training-serving skew", "entity timestamp"
        ],
        "resume_evidence": "Candidate feature store architecture and data consistency.",
    },
    {
        "id": "iac_stage1_01",
        "skills": ["terraform", "iac", "infrastructure as code", "cloud security", "drift detection", "cloud", "devops"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Infrastructure as Code & Cloud Security Foundations",
        "difficulty": "medium",
        "depth_level": "FOUNDATION",
        "question": (
            "In Terraform-managed cloud infrastructure, how do state locking and remote backends prevent race conditions and state corruption during concurrent team deployments?"
        ),
        "expected_concepts": [
            "Terraform state management", "drift detection", "immutable infrastructure", "IAM least privilege", "state locking", "remote backend"
        ],
        "resume_evidence": "Candidate Terraform and infrastructure as code foundation.",
    },
    {
        "id": "iac_stage1_02",
        "skills": ["terraform", "iac", "infrastructure as code", "cloud security", "drift detection", "cloud", "devops"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Drift Detection & Terraform Reconciliation",
        "difficulty": "hard",
        "depth_level": "FOLLOW_UP",
        "question": (
            "When Terraform detects drift between actual cloud resources and the remote state file, how do you safely reconcile state without triggering accidental resource destruction?"
        ),
        "expected_concepts": [
            "drift detection", "Terraform state management", "immutable infrastructure", "state refresh", "terraform import"
        ],
        "resume_evidence": "Candidate Terraform drift remediation and state reconciliation.",
    },
    {
        "id": "container_stage2_01",
        "skills": ["kubernetes", "cni", "container orchestration", "pod lifecycle", "devops", "cloud"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Container Orchestration, CNI & Pod Lifecycle Invariants",
        "difficulty": "hard",
        "depth_level": "PRACTICAL",
        "question": (
            "During a Kubernetes rolling update, how do readiness probes coordinate with CNI routing and preStop hooks to prevent traffic drop before a pod receives SIGTERM?"
        ),
        "expected_concepts": [
            "Kubernetes pod lifecycle", "SIGTERM handling", "liveness vs readiness probes", "CNI routing", "preStop hook", "zero-downtime deployment"
        ],
        "resume_evidence": "Candidate Kubernetes container lifecycle and CNI networking knowledge.",
    },
    {
        "id": "container_stage2_02",
        "skills": ["kubernetes", "cni", "container orchestration", "pod lifecycle", "devops", "cloud"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Kubernetes CNI IPAM & Network Partition Resiliency",
        "difficulty": "hard",
        "depth_level": "FOLLOW_UP",
        "question": (
            "Under heavy pod churn, how does the Kubernetes CNI plugin coordinate IPAM allocation with kube-proxy to prevent routing to dead endpoints?"
        ),
        "expected_concepts": [
            "CNI routing", "Kubernetes pod lifecycle", "IPAM allocation", "kube-proxy", "endpoint routing"
        ],
        "resume_evidence": "Candidate Kubernetes CNI and container networking mechanics.",
    },
    {
        "id": "algo_stage1_01",
        "skills": ["algorithms", "data structures", "complexity", "invariants", "big-o", "general"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Algorithmic Mechanics, Complexity & Invariants",
        "difficulty": "medium",
        "depth_level": "FOUNDATION",
        "question": (
            "When designing a sliding window algorithm over an unindexed data stream, what invariant must be preserved across window contractions to guarantee O(N) amortized time complexity?"
        ),
        "expected_concepts": [
            "Big-O asymptotic complexity", "boundary edge cases", "invariant maintenance", "data structure selection", "amortized complexity"
        ],
        "resume_evidence": "Candidate algorithmic reasoning and complexity invariants.",
    },
    {
        "id": "arch_stage2_01",
        "skills": ["clean architecture", "solid", "modularity", "system decomposition", "design patterns", "general"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "technical",
        "topic": "Modular Clean Architecture & System Decomposition",
        "difficulty": "medium",
        "depth_level": "PRACTICAL",
        "question": (
            "In Clean Architecture or Hexagonal Architecture, how do you apply the Dependency Inversion Principle to prevent database and external delivery models from leaking into domain entities?"
        ),
        "expected_concepts": [
            "SOLID principles", "dependency injection", "loose coupling", "domain-driven boundaries", "dependency inversion"
        ],
        "resume_evidence": "Candidate clean architecture and modular decomposition mastery.",
    },
    {
        "id": "api_stage1_idempotency_01",
        "skills": ["api architecture", "idempotency", "rest", "concurrency", "backend"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "API Architecture, Idempotency & Concurrency Mechanics",
        "difficulty": "medium",
        "depth_level": "FOUNDATION",
        "question": (
            "When designing a mission-critical payment or order submission API, how do idempotency keys and database unique constraints prevent duplicate processing during client retries?"
        ),
        "expected_concepts": [
            "idempotency keys", "retry semantics", "atomic commit", "duplicate request handling", "event loop blocking"
        ],
        "resume_evidence": "Candidate API design and idempotency mechanics.",
    },
    {
        "id": "algo_stage2_01",
        "skills": ["algorithms", "data structures", "backend", "general"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "coding_theory",
        "topic": "Dynamic Programming & Memoization Patterns",
        "difficulty": "medium",
        "question": (
            "How do you determine whether an algorithmic problem is solvable via Dynamic Programming versus a Greedy strategy? "
            "Explain optimal substructure and overlapping subproblems with a concrete example."
        ),
        "expected_concepts": [
            "optimal substructure", "overlapping subproblems", "memoization (top-down)",
            "tabulation (bottom-up)", "greedy choice property", "state space"
        ],
        "resume_evidence": "Candidate algorithmic problem solving background.",
    },

    # =========================================================================
    # STAGE 3: SCALABLE SYSTEMS & ARCHITECTURE (Distributed Systems & Scale)
    # =========================================================================
    {
        "id": "sys_stage3_01",
        "skills": ["system design", "backend", "distributed systems", "cloud", "scalability"],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architecture",
        "category": "system_design",
        "topic": "Caching Topologies & Stampede Protection",
        "difficulty": "hard",
        "question": (
            "When operating a high-throughput cache layer in front of a primary database, "
            "what mechanisms protect the database from a cache stampede or thundering herd when a popular key expires?"
        ),
        "expected_concepts": [
            "cache-aside vs write-through", "thundering herd / cache stampede",
            "mutex locks / probabilistic early expiration", "bloom filters", "ttl jitter", "stale cache"
        ],
        "resume_evidence": "Candidate system design and caching knowledge.",
    },
    {
        "id": "sys_stage3_02",
        "skills": ["docker", "kubernetes", "cloud", "devops", "microservices"],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architecture",
        "category": "system_design",
        "topic": "Microservices Communication & Decoupling",
        "difficulty": "hard",
        "question": (
            "In an event-driven microservices architecture, how do you guarantee eventual consistency and "
            "reliable message delivery across service boundaries without relying on distributed two-phase commit locks?"
        ),
        "expected_concepts": [
            "sync vs async messaging", "backpressure", "eventual consistency",
            "saga pattern (orchestration vs choreography)", "outbox pattern", "idempotency keys"
        ],
        "resume_evidence": "Candidate cloud, microservices, and distributed architecture background.",
    },
    {
        "id": "db_stage3_01",
        "skills": ["database", "sql", "postgresql", "backend", "scalability"],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architecture",
        "category": "system_design",
        "topic": "Database Sharding & Read Replicas",
        "difficulty": "hard",
        "question": (
            "As data volume grows beyond a single primary database, how do read replicas with replication lag impact data consistency, "
            "and what criteria do you use to choose a shard key when implementing horizontal database sharding?"
        ),
        "expected_concepts": [
            "read replicas", "replication lag", "read-after-write consistency",
            "horizontal sharding", "shard key distribution", "cross-shard queries", "hotspots"
        ],
        "resume_evidence": "Candidate database scaling and high-availability architecture.",
    },

    # =========================================================================
    # STAGE 4: DEBUGGING, EDGE CASES & INCIDENT RESPONSE
    # =========================================================================
    {
        "id": "dbg_stage4_01",
        "skills": ["backend", "python", "docker", "devops", "cloud"],
        "stage_index": 4,
        "stage_name": "Debugging & Edge Cases",
        "category": "debugging",
        "topic": "Production Memory Leak & High Latency Incident",
        "difficulty": "hard",
        "question": (
            "A production backend service starts returning 504 Gateway Timeouts under peak traffic, with memory usage steadily creeping to 100%. "
            "Walk me through your step-by-step triage protocol: what telemetry do you inspect first, and how do you pinpoint whether it's a memory leak, connection pool exhaustion, or an unindexed query?"
        ),
        "expected_concepts": [
            "apdex / p99 latency metrics", "connection pool starvation", "thread/memory dump",
            "heap profiling", "slow query logs", "mitigation before diagnosis", "rollback / scale"
        ],
        "resume_evidence": "Candidate production troubleshooting and incident response.",
    },
    {
        "id": "dbg_stage4_02",
        "skills": ["frontend", "react", "javascript", "typescript"],
        "stage_index": 4,
        "stage_name": "Debugging & Edge Cases",
        "category": "debugging",
        "topic": "Frontend Race Conditions & Stale Closures",
        "difficulty": "medium",
        "question": (
            "Users report intermittent UI bugs where rapid search filtering displays results from a previous request instead of the latest one. "
            "How do you debug this race condition, and what clean patterns (such as AbortController, debouncing, or cancellation tokens) do you implement?"
        ),
        "expected_concepts": [
            "race conditions", "network latency jitter", "abortcontroller",
            "cleanup functions in useEffect", "debouncing vs throttling", "stale closures"
        ],
        "resume_evidence": "Candidate frontend debugging and state resilience.",
    },
    {
        "id": "dbg_stage4_03",
        "skills": ["general", "software engineering", "backend"],
        "stage_index": 4,
        "stage_name": "Debugging & Edge Cases",
        "category": "debugging",
        "topic": "Deadlock Detection & Concurrency Edge Cases",
        "difficulty": "hard",
        "question": (
            "Suppose two background workers process records in parallel and frequently lock up in a database deadlock. "
            "How do you inspect the database lock graph to diagnose the mutual hold-and-wait condition, and how do you redesign the transaction order to eliminate deadlocks?"
        ),
        "expected_concepts": [
            "coffman conditions", "mutual hold-and-wait", "lock order consistency",
            "pg_locks / sys.innodb_lock_waits", "optimistic locking", "exponential backoff retry"
        ],
        "resume_evidence": "Candidate concurrency and database deadlock analysis.",
    },

    # =========================================================================
    # STAGE 5: BEHAVIORAL LEADERSHIP & STAR FRAMEWORK
    # =========================================================================
    {
        "id": "beh_stage5_01",
        "skills": ["behavioral", "general", "leadership", "teamwork"],
        "stage_index": 5,
        "stage_name": "Behavioral Leadership & STAR",
        "category": "behavioral",
        "topic": "Technical Disagreement & Cross-Functional Alignment",
        "difficulty": "medium",
        "question": (
            "Tell me about a time in a software project where you strongly disagreed with an architectural or product decision proposed "
            "by a teammate or manager. Structure your answer using Situation, Task, Action, and Result: how did you objectively present your data and align on the final outcome?"
        ),
        "expected_concepts": [
            "situation context", "task ownership", "objective data / benchmarking",
            "active listening / disagree and commit", "measurable business or technical result"
        ],
        "resume_evidence": "Candidate engineering collaboration and technical communication.",
    },
    {
        "id": "beh_stage5_02",
        "skills": ["behavioral", "general", "leadership", "project management"],
        "stage_index": 5,
        "stage_name": "Behavioral Leadership & STAR",
        "category": "behavioral",
        "topic": "Critical Production Failure & Root Cause Postmortem",
        "difficulty": "medium",
        "question": (
            "Describe a situation where a code change or system you built caused an unexpected regression or service failure. "
            "What was your immediate action to stabilize the user experience, how did you conduct the blameless post-mortem, and what systemic safeguards did you put in place to prevent recurrence?"
        ),
        "expected_concepts": [
            "blameless postmortem", "rapid containment", "5 whys root cause",
            "automated regression test", "observability guardrails", "personal accountability"
        ],
        "resume_evidence": "Candidate engineering ownership and reliability mindset.",
    },
    {
        "id": "sys_stage3_03",
        "skills": ["api", "backend", "scalability", "cloud", "system design"],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architecture",
        "category": "system_design",
        "topic": "Distributed Rate Limiting & API Resilience",
        "difficulty": "hard",
        "question": (
            "When architecting an API Gateway that services tens of thousands of requests per second, how do you implement "
            "distributed rate limiting (e.g. Token Bucket vs Sliding Window Counter with Redis) without causing high network latency or race conditions?"
        ),
        "expected_concepts": [
            "token bucket", "sliding window log vs counter", "redis lua scripts",
            "race conditions", "http 429 retry-after", "distributed synchronization"
        ],
        "resume_evidence": "Candidate API architecture and rate limiting design.",
    },
    {
        "id": "dbg_stage4_04",
        "skills": ["security", "backend", "general", "devops"],
        "stage_index": 4,
        "stage_name": "Debugging & Edge Cases",
        "category": "debugging",
        "topic": "Security Vulnerability Mitigation & Invariant Enforcement",
        "difficulty": "hard",
        "question": (
            "Suppose an audit reveals that an API endpoint is susceptible to parameter tampering and unauthorized resource access across tenants. "
            "How do you enforce multi-tenant authorization invariants at the database and application levels to guarantee complete data isolation?"
        ),
        "expected_concepts": [
            "row-level security (rls)", "tenant id context propagation", "authorization middleware",
            "idor prevention", "defense in depth", "least privilege"
        ],
        "resume_evidence": "Candidate API security and multi-tenant authorization.",
    },

    # =========================================================================
    # EMBEDDED SYSTEMS, C/C++, HARDWARE & IOT TRACK
    # =========================================================================
    {
        "id": "emb_stage1_01",
        "skills": ["embedded c", "embedded systems", "c", "c++", "hardware", "iot", "vlsi", "microcontroller", "arduino", "robotics"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Microcontroller Memory Architecture & Volatile Registers",
        "difficulty": "medium",
        "question": (
            "In embedded C and microcontroller programming, what are the architectural differences between memory allocated on the stack versus the heap, "
            "how does the `volatile` keyword prevent unsafe compiler optimizations on memory-mapped I/O registers, and why is dynamic memory allocation often avoided in safety-critical firmware?"
        ),
        "expected_concepts": [
            "stack vs heap", "sram vs flash", "volatile keyword",
            "memory-mapped io", "heap fragmentation", "deterministic execution"
        ],
        "resume_evidence": "Candidate Embedded Systems and microcontroller background.",
    },
    {
        "id": "emb_stage2_01",
        "skills": ["embedded c", "embedded systems", "c", "c++", "hardware", "iot", "rtos"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "coding_theory",
        "topic": "RTOS Task Scheduling & Interrupt Service Routines",
        "difficulty": "hard",
        "question": (
            "When designing real-time firmware on an RTOS, how do you handle Interrupt Service Routines (ISRs) without violating timing constraints, "
            "and what mechanisms (such as priority inheritance or priority ceiling) prevent the Priority Inversion anomaly when sharing resources between high and low priority tasks?"
        ),
        "expected_concepts": [
            "isr deferral / bottom half", "priority inversion", "priority inheritance",
            "mutex vs binary semaphore", "context switching latency", "critical sections"
        ],
        "resume_evidence": "Candidate RTOS and real-time concurrency experience.",
    },
    {
        "id": "emb_stage3_01",
        "skills": ["embedded systems", "iot", "hardware", "c", "c++", "networking"],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architecture",
        "category": "system_design",
        "topic": "IoT Telemetry Protocols & Resource-Constrained Ingestion",
        "difficulty": "hard",
        "question": (
            "When designing an IoT sensor telemetry architecture with thousands of distributed battery-powered nodes, what are the trade-offs between MQTT (QoS 0 vs 1 vs 2) and CoAP/UDP, "
            "and how do you implement packet buffering and backpressure to prevent SRAM overflow during intermittent cellular or wireless dropouts?"
        ),
        "expected_concepts": [
            "mqtt qos levels", "coap vs mqtt", "ring buffer / circular buffer",
            "flash wear leveling", "battery power consumption", "backpressure"
        ],
        "resume_evidence": "Candidate IoT telemetry and communication protocols.",
    },
    {
        "id": "emb_stage4_01",
        "skills": ["embedded systems", "hardware", "iot", "c", "c++", "debugging"],
        "stage_index": 4,
        "stage_name": "Debugging & Edge Cases",
        "category": "debugging",
        "topic": "Watchdog Timer Resets & Bus Contention Diagnostics",
        "difficulty": "hard",
        "question": (
            "A deployed microcontroller device intermittently locks up or enters an infinite reset loop in the field. "
            "How do you systematically triage whether the root cause is a hardware brownout reset (BOR), a stack-pointer collision, a watchdog timer expiration, or a bus hang on an I2C/SPI transaction?"
        ),
        "expected_concepts": [
            "watchdog timer (wdt)", "brownout reset (bor)", "stack overflow / collision",
            "i2c clock stretching lockup", "hardfault handler", "jtag/swd debugging"
        ],
        "resume_evidence": "Candidate hardware debugging and embedded fault tolerance.",
    },
    {
        "id": "emb_stage5_01",
        "skills": ["embedded systems", "hardware", "iot", "behavioral", "leadership"],
        "stage_index": 5,
        "stage_name": "Behavioral Leadership & STAR",
        "category": "behavioral",
        "topic": "Hardware-Software Integration Under Critical Deadline",
        "difficulty": "medium",
        "question": (
            "Describe a challenging project where an unexpected hardware timing drift or component erratum threatened your delivery schedule. "
            "How did you isolate whether the root issue was in firmware or circuit design, and how did you collaborate with teammates to deliver a reliable engineering fix?"
        ),
        "expected_concepts": [
            "hardware-software co-design", "oscilloscope / logic analyzer verification",
            "firmware workaround for silicon erratum", "cross-functional ownership", "measurable outcome"
        ],
        "resume_evidence": "Candidate hardware engineering collaboration and problem resolution.",
    },

    # =========================================================================
    # CLOUD, DEVOPS & INFRASTRUCTURE TRACK
    # =========================================================================
    {
        "id": "devops_stage1_01",
        "skills": ["docker", "kubernetes", "cloud", "devops", "linux"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation",
        "category": "technical",
        "topic": "Linux Container Isolation & Multi-Stage Builds",
        "difficulty": "medium",
        "question": (
            "How do Linux kernel namespaces (PID, NET, MNT) and cgroups provide process isolation and resource governance in container runtimes like Docker, "
            "and how do multi-stage container builds optimize production image security and attack surfaces?"
        ),
        "expected_concepts": [
            "namespaces", "cgroups", "multi-stage builds",
            "minimal base images (distroless/alpine)", "container security", "layer caching"
        ],
        "resume_evidence": "Candidate Docker and Linux containerization knowledge.",
    },
    {
        "id": "devops_stage2_01",
        "skills": ["kubernetes", "docker", "devops", "cloud", "microservices"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "coding_theory",
        "topic": "Kubernetes Pod Scheduling & Health Probes",
        "difficulty": "hard",
        "question": (
            "In Kubernetes cluster orchestration, how does the kube-scheduler evaluate node affinity and resource requests, "
            "and what are the critical operational differences and failure semantics between Liveness, Readiness, and Startup probes?"
        ),
        "expected_concepts": [
            "kube-scheduler", "node affinity / taints and tolerations",
            "liveness vs readiness vs startup probes", "cascade restart loops", "graceful shutdown"
        ],
        "resume_evidence": "Candidate Kubernetes cluster management experience.",
    },

    # =========================================================================
    # AI, MACHINE LEARNING & DATA SCIENCE TRACK
    # =========================================================================
    {
        "id": "ai_stage2_01",
        "skills": ["ai", "machine learning", "deep learning", "vector", "rag", "python"],
        "stage_index": 2,
        "stage_name": "Core Implementation & Mechanics",
        "category": "coding_theory",
        "topic": "Vector Indexing Algorithms & Retrieval Precision",
        "difficulty": "hard",
        "question": (
            "When implementing vector search for semantic retrieval or RAG, what are the mathematical and computational trade-offs between "
            "exact flat index scans versus approximate nearest neighbor graphs like HNSW, and how do cosine similarity versus dot product metrics impact retrieval latency?"
        ),
        "expected_concepts": [
            "hnsw graph", "approximate nearest neighbors (ann)", "cosine similarity vs dot product",
            "vector dimensionality", "recall vs latency trade-off", "quantization (pq/sq)"
        ],
        "resume_evidence": "Candidate vector search and RAG architecture knowledge.",
    },
    {
        "id": "ai_stage3_01",
        "skills": [
            "ai", "machine learning", "deep learning", "python", "scalability",
            "model serving", "model serving throughput", "continuous batching",
            "pagedattention", "kv cache", "quantization", "gpu memory",
            "model_serving_latency_and_quantization"
        ],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architecture",
        "category": "system_design",
        "topic": "High-Throughput Model Inference & KV Cache Optimization",
        "difficulty": "hard",
        "question": (
            "When serving large deep learning or LLM models under high concurrent traffic, how do dynamic continuous batching, "
            "PagedAttention / KV cache management, and model quantization (INT8/FP16) optimize GPU memory bandwidth and p99 token generation latency?"
        ),
        "expected_concepts": [
            "continuous batching", "pagedattention", "kv cache memory footprint",
            "quantization (int8/fp16)", "gpu memory bandwidth bound", "p99 latency"
        ],
        "resume_evidence": "Candidate AI model serving and production scaling knowledge.",
    },

    # =========================================================================
    # ROLE SPECIFIC: EMBEDDING SYSTEMS ENGINEER (Stages 1 to 5)
    # =========================================================================
    {
        "id": "emb_stage1_01",
        "skills": ["embedding", "vector", "vector search", "dense embeddings", "machine learning"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation & Resume Grounding",
        "category": "technical",
        "topic": "Dense Representations & Metric Space Normalization",
        "difficulty": "medium",
        "question": (
            "In large-scale embedding systems, how does unit-normalizing dense vectors affect the mathematical equivalence "
            "between Cosine Similarity and Dot Product, and why do high-dimensional spaces experience the curse of dimensionality during distance calculations?"
        ),
        "expected_concepts": [
            "cosine similarity", "dot product", "l2 unit normalization", "curse of dimensionality", "distance concentration"
        ],
        "resume_evidence": "Candidate embedding systems and vector representation knowledge.",
    },
    {
        "id": "emb_stage2_01",
        "skills": ["embedding", "vector indexing", "ann", "hnsw", "ivf"],
        "stage_index": 2,
        "stage_name": "Core Engineering & Algorithmic Mechanics",
        "category": "technical",
        "topic": "HNSW vs IVF-PQ Vector Indexing Mechanics",
        "difficulty": "hard",
        "question": (
            "When scaling Approximate Nearest Neighbor (ANN) search over 50 million vectors, what are the internal algorithmic differences "
            "between HNSW (Hierarchical Navigable Small World) graphs and IVF-PQ (Inverted File with Product Quantization) in terms of query latency, RAM overhead, and recall curves?"
        ),
        "expected_concepts": [
            "HNSW", "IVF", "Product Quantization (PQ)", "efSearch vs M", "recall vs latency trade-off", "RAM footprint"
        ],
        "resume_evidence": "Candidate vector indexing and ANN algorithms experience.",
    },
    {
        "id": "emb_stage3_01",
        "skills": ["embedding", "pipeline", "serving", "concurrency", "vector store"],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architectural Trade-offs",
        "category": "system_design",
        "topic": "High-Throughput Embedding Generation Pipeline",
        "difficulty": "hard",
        "question": (
            "You are architecting an embedding pipeline that must process 10,000 document updates per second with sub-second downstream vector store sync. "
            "How would you design dynamic inference batching, worker pool concurrency, backpressure handling, and vector database write ingestion?"
        ),
        "expected_concepts": [
            "dynamic batching", "GPU inference saturation", "backpressure", "streaming ingestion", "vector database synchronization"
        ],
        "resume_evidence": "Candidate scalable vector pipeline and ingestion architecture knowledge.",
    },
    {
        "id": "emb_stage4_01",
        "skills": ["embedding", "debugging", "drift", "vector search", "reliability"],
        "stage_index": 4,
        "stage_name": "Incident Invariants, Failure Modes & Debugging",
        "category": "technical",
        "topic": "Vector Drift, Dimension Mismatch & Silent Degradation",
        "difficulty": "hard",
        "question": (
            "Imagine an embedding model upgrade is deployed, but top-k retrieval recall drops by 40% without throwing runtime exceptions. "
            "How do you systematically detect semantic drift, diagnose dimension or normalization mismatch, and execute a zero-downtime dual-index migration?"
        ),
        "expected_concepts": [
            "embedding drift", "silent recall degradation", "dual-index migration", "dimension mismatch", "fallback lexical retrieval"
        ],
        "resume_evidence": "Candidate vector incident triage and drift debugging experience.",
    },
    {
        "id": "emb_stage5_01",
        "skills": ["embedding", "tradeoffs", "ownership", "cost", "sla"],
        "stage_index": 5,
        "stage_name": "Cross-Functional Ownership & STAR Leadership",
        "category": "behavioral",
        "topic": "In-Memory Vector Cost Governance vs SLA Defense",
        "difficulty": "medium",
        "question": (
            "Describe a situation where in-memory vector index hosting costs were escalating rapidly while product stakeholders demanded strict p99 retrieval SLAs. "
            "How did you evaluate hybrid search, disk-backed indexing trade-offs, and guide engineering leadership to an optimal consensus?"
        ),
        "expected_concepts": [
            "RAM cost governance", "p99 latency SLA", "hybrid search", "stakeholder negotiation", "trade-off communication"
        ],
        "resume_evidence": "Candidate cross-functional leadership in vector infrastructure.",
    },

    # =========================================================================
    # ROLE SPECIFIC: DISTRIBUTED DATABASE RELIABILITY ENGINEER (Stages 1 to 5)
    # =========================================================================
    {
        "id": "ddb_stage1_01",
        "skills": ["database", "distributed systems", "consensus", "raft", "paxos"],
        "stage_index": 1,
        "stage_name": "Foundational Orientation & Resume Grounding",
        "category": "technical",
        "topic": "Distributed Consensus & Quorum Arithmetic",
        "difficulty": "medium",
        "question": (
            "In a distributed cluster running a consensus protocol like Raft, suppose two nodes become disconnected. "
            "What would you expect the remaining nodes to do?"
        ),
        "expected_concepts": [
            "Raft consensus", "quorum intersection (N/2 + 1)", "randomized election timeouts", "term numbers", "leader safety"
        ],
        "resume_evidence": "Candidate distributed consensus and replication foundations.",
    },
    {
        "id": "ddb_stage2_01",
        "skills": ["database", "storage engine", "wal", "lsm", "b-tree"],
        "stage_index": 2,
        "stage_name": "Core Engineering & Algorithmic Mechanics",
        "category": "technical",
        "topic": "Write-Ahead Log (WAL) Durability & LSM Compaction Storms",
        "difficulty": "hard",
        "question": (
            "In a database storage engine, how does the Write-Ahead Log (WAL) and fsync barrier guarantee durability during a sudden power loss?"
        ),
        "expected_concepts": [
            "Write-Ahead Log (WAL)", "fsync semantics", "LSM-tree compaction storms", "write amplification", "rate-limiting compaction"
        ],
        "resume_evidence": "Candidate storage engine internals and durability knowledge.",
    },
    {
        "id": "ddb_stage3_01",
        "skills": ["database", "replication", "partition", "split-brain", "high availability"],
        "stage_index": 3,
        "stage_name": "Scalable Systems & Architectural Trade-offs",
        "category": "system_design",
        "topic": "Multi-Region Replication & Split-Brain Fencing",
        "difficulty": "hard",
        "question": (
            "In a multi-datacenter database setup experiencing an asymmetric network partition, "
            "what mechanism prevents a severed minority node from accepting stale writes?"
        ),
        "expected_concepts": [
            "split-brain protection", "fencing tokens", "synchronous vs asynchronous replication", "partition isolation", "CAP trade-offs"
        ],
        "resume_evidence": "Candidate multi-region database replication and failover design.",
    },
    {
        "id": "ddb_stage4_01",
        "skills": ["database", "debugging", "split-brain", "incident", "data recovery"],
        "stage_index": 4,
        "stage_name": "Incident Invariants, Failure Modes & Debugging",
        "category": "technical",
        "topic": "Split-Brain Divergence Reconciliation & Recovery",
        "difficulty": "hard",
        "question": (
            "During a catastrophic cross-datacenter partition, two nodes operated as primary for 90 seconds and accepted diverging writes. "
            "How do you detect divergence, protect data consistency, and lead the technical recovery to reconcile conflicting transactional records?"
        ),
        "expected_concepts": [
            "split-brain divergence", "vector clocks / LSN", "conflict resolution", "transaction log reconciliation", "data consistency invariants"
        ],
        "resume_evidence": "Candidate incident crisis management and database recovery experience.",
    },
    {
        "id": "ddb_stage5_01",
        "skills": ["database", "migration", "ownership", "slo", "zero downtime"],
        "stage_index": 5,
        "stage_name": "Cross-Functional Ownership & STAR Leadership",
        "category": "behavioral",
        "topic": "Zero-Downtime Schema Migrations & Reliability Governance",
        "difficulty": "medium",
        "question": (
            "Tell me about a high-stakes scenario where you had to perform an online schema migration on a multi-terabyte production database without downtime. "
            "How did you structure the expand-and-contract phases, communicate risk to stakeholders, and defend uptime SLOs?"
        ),
        "expected_concepts": [
            "expand and contract pattern", "online schema migration", "backward compatibility", "uptime SLO defense", "stakeholder communication"
        ],
        "resume_evidence": "Candidate operational ownership and production database governance.",
    },
]


class QuestionBankService:
    """
    Selects curated questions tailored to candidate skills and target stage,
    enforcing strictly zero-repetition across an interview session and
    synthesizing conversational bridges based on the candidate's last answer and score.
    """

    @classmethod
    def _synthesize_conversational_bridge(
        cls,
        base_question: str,
        best_candidate: Dict[str, Any],
        last_question: Optional[str] = None,
        last_answer: Optional[str] = None,
        last_score: Optional[float] = None,
        last_missing_concepts: Optional[List[str]] = None,
        candidate_claims: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        """
        Synthesizes an organic conversational transition acknowledging the candidate's
        previous answer, bridging into the new question, or adapting to performance.
        Returns:
            (clean_question, bridge_lead_in)
        """
        from ai.interview_engine.question_sanitizer import sanitize_and_enforce_single_question
        clean_q = sanitize_and_enforce_single_question(base_question)

        if not last_answer and last_score is None:
            # Turn 1: Anchor directly in a claim matching the question's domain if available
            if candidate_claims:
                candidate_skills = [s.lower() for s in best_candidate.get("skills", [])]
                matching_claim = None
                for c in candidate_claims:
                    c_text = str(c).lower()
                    if any(s in c_text for s in candidate_skills):
                        matching_claim = str(c).strip().rstrip(".")
                        break
                if matching_claim:
                    return clean_q, f"Referencing your background with {matching_claim}:"
            return clean_q, f"Let's explore your experience with {best_candidate.get('topic', 'this area')}:"

        # Performance-based adaptive steering & conversational continuity
        if last_score is not None and last_score < 4.5:
            # Candidate struggled or omitted critical concepts -> Scaffold and step back
            if last_missing_concepts and len(last_missing_concepts) > 0:
                missing = last_missing_concepts[0]
                bridge_prefix = (
                    f"In your previous explanation, you glossed over the role of {missing}. "
                    f"Let's step back and anchor on the foundational principles:"
                )
            else:
                bridge_prefix = (
                    "Taking a step back from our previous discussion to examine the core architectural foundations from first principles:"
                )
        elif last_score is not None and last_score >= 8.0:
            # Candidate demonstrated mastery -> Escalate rigor, scale, and failure modes
            bridge_prefix = (
                "You articulated the trade-offs effectively in your previous response. "
                "Now let's push the boundary to system-scale constraints, race conditions, and failure modes:"
            )
        else:
            # Solid/balanced answer -> Smooth conversational bridge
            bridge_prefix = (
                "Building directly on your insights from that scenario, let's explore the next layer of the stack:"
            )

        return clean_q, bridge_prefix

    @classmethod
    def find_question(
        cls,
        stage_index: int,
        target_role: str,
        resume_summary: Optional[str] = None,
        asked_questions: Optional[List[str]] = None,
        difficulty: str = "medium",
        last_question: Optional[str] = None,
        last_answer: Optional[str] = None,
        last_score: Optional[float] = None,
        last_missing_concepts: Optional[List[str]] = None,
        candidate_claims: Optional[List[str]] = None,
        candidate_dossier: Optional[Dict[str, Any]] = None,
        target_competency: Optional[str] = None,
        expected_concepts: Optional[List[str]] = None,
        is_followup: bool = False,
        followup_concept: Optional[str] = None,
        depth_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        asked_list = asked_questions or []
        resume_text = (f"{target_role} {resume_summary or ''}").lower()

        # Dynamic difficulty steering based on last turn score
        calibrated_difficulty = difficulty.lower()
        if last_score is not None:
            if last_score < 4.5 and calibrated_difficulty == "hard":
                calibrated_difficulty = "medium"
            elif last_score >= 8.0 and calibrated_difficulty == "medium":
                calibrated_difficulty = "hard"

        # PRIORITY 1: Autonomous Web-Researched Candidate Curriculum
        if candidate_dossier and candidate_dossier.get("custom_curriculum"):
            curriculum = candidate_dossier["custom_curriculum"]
            matching_stage = next((s for s in curriculum if s.get("stage_index") == stage_index), None)
            if not matching_stage and curriculum:
                matching_stage = curriculum[min(max(0, stage_index - 1), len(curriculum) - 1)]

            if matching_stage:
                base_q = matching_stage["domain_inquiry"]
                # Check if this exact inquiry was already asked; if so, pick from researched_skills interview inquiries
                if any(base_q[:35].lower() in a.lower() for a in asked_list):
                    for sk in candidate_dossier.get("researched_skills", []):
                        for alt in sk.get("sample_interview_inquiries", []):
                            if not any(alt[:35].lower() in a.lower() for a in asked_list):
                                base_q = alt
                                break

                # Validate alignment with canonical target competency if target_competency is specified
                is_dossier_aligned = True
                if target_competency:
                    from ai.interview_engine.question_sanitizer import validate_question_competency_alignment
                    is_dossier_aligned, _ = validate_question_competency_alignment(
                        question_text=base_q,
                        target_competency=target_competency,
                        expected_concepts=expected_concepts,
                    )

                if is_dossier_aligned:
                    focus_skill = matching_stage.get("focus_skill", target_role)
                    expected = matching_stage.get("expected_concepts", [focus_skill])
                    clean_q, lead_in = cls._synthesize_conversational_bridge(
                        base_question=base_q,
                        best_candidate={"question": base_q, "topic": focus_skill},
                        last_question=last_question,
                        last_answer=last_answer,
                        last_score=last_score,
                        last_missing_concepts=last_missing_concepts,
                        candidate_claims=candidate_claims,
                    )
                    return {
                        "question": clean_q,
                        "coach_lead_in": lead_in,
                        "category": "technical" if stage_index <= 4 else "behavioral",
                        "topic": focus_skill,
                        "difficulty": calibrated_difficulty,
                        "stage_name": matching_stage.get("stage_name", f"Stage {stage_index}"),
                        "stage_index": stage_index,
                        "total_stages": 5,
                        "resume_evidence": f"Autonomous live web research grounding: {focus_skill}",
                        "expected_concepts": expected,
                        "target_competency": target_competency or focus_skill,
                        "assessment_objective": f"Assess candidate mastery of {focus_skill}",
                    }

        # PRIORITY 2: Filter bank by stage_index
        stage_candidates = [
            q for q in QUESTION_BANK
            if q["stage_index"] == stage_index
        ]
        if not stage_candidates:
            stage_candidates = QUESTION_BANK

        # 2. Filter out already asked questions using robust prefix & substring matching
        def is_already_asked(q: Dict[str, Any]) -> bool:
            core_text = q["question"].strip().lower()
            core_sub = core_text[:40]
            for a in asked_list:
                a_lower = a.strip().lower()
                if core_text in a_lower or core_sub in a_lower:
                    return True
            return False

        unasked = [q for q in stage_candidates if not is_already_asked(q)]

        if not unasked:
            # Fallback to any unasked question from the entire bank
            unasked = [q for q in QUESTION_BANK if not is_already_asked(q)]

        if not unasked:
            # If exhausted entire bank, cycle safely
            unasked = stage_candidates

        # 3. Enforce CANONICAL TARGET COMPETENCY filter if specific target_competency is specified
        is_role_placeholder = (
            target_competency.strip().lower() == target_role.strip().lower()
            or target_competency.strip().lower().endswith(("engineer", "architect", "sre", "developer"))
            or "universal software engineering" in target_competency.strip().lower()
            or "omnirole" in target_competency.strip().lower()
        )
        if target_competency and not is_role_placeholder:
            from ai.interview_engine.question_sanitizer import (
                sanitize_and_enforce_single_question,
                validate_question_competency_alignment,
                CompetencyAlignmentError,
            )
            # Find all candidates in unasked that align with canonical target competency
            aligned_candidates = [
                q for q in unasked
                if validate_question_competency_alignment(
                    question_text=sanitize_and_enforce_single_question(q["question"]),
                    target_competency=target_competency,
                    expected_concepts=expected_concepts,
                )[0]
            ]
            # If not in unasked stage candidates, search all unasked in entire question bank
            if not aligned_candidates:
                all_unasked = [q for q in QUESTION_BANK if not is_already_asked(q)]
                aligned_candidates = [
                    q for q in all_unasked
                    if validate_question_competency_alignment(
                        question_text=sanitize_and_enforce_single_question(q["question"]),
                        target_competency=target_competency,
                        expected_concepts=expected_concepts,
                    )[0]
                ]

            if not aligned_candidates:
                raise CompetencyAlignmentError(
                    f"No verified fallback question available in question bank for canonical target competency '{target_competency}'."
                )
            unasked = aligned_candidates

        # 4. Score candidates with COMPETENCY-FIRST PRIORITY
        target_role_lower = target_role.lower()
        target_comp_lower = (target_competency or "").lower()
        exp_concepts_lower = [c.lower() for c in (expected_concepts or [])]
        followup_lower = (followup_concept or "").lower()

        best_candidate = unasked[0]
        best_match_score = -1
        matched_skills_found: List[str] = []

        import re
        role_keywords = [w for w in re.split(r"[\s/_-]+", target_role_lower) if len(w) > 3]
        comp_keywords = [w for w in re.split(r"[\s/_-]+", target_comp_lower) if len(w) > 3] if target_comp_lower else []

        for candidate in unasked:
            score = 0
            current_matched: List[str] = []
            cand_skills_lower = [s.lower() for s in candidate.get("skills", [])]
            cand_topic_lower = candidate.get("topic", "").lower()
            cand_q_lower = candidate.get("question", "").lower()

            # A. Match Target Competency (+40 pts)
            for kw in comp_keywords:
                if any(kw in sk for sk in cand_skills_lower) or kw in cand_topic_lower or kw in cand_q_lower:
                    score += 40

            # B. Match Expected Concepts (+15 pts each)
            for exp in exp_concepts_lower:
                if any(exp in c_exp.lower() for c_exp in candidate.get("expected_concepts", [])) or exp in cand_q_lower:
                    score += 15

            # C. Targeted Follow-up boost (+25 pts)
            if is_followup and followup_lower:
                if followup_lower in cand_q_lower or any(followup_lower in c_exp.lower() for c_exp in candidate.get("expected_concepts", [])):
                    score += 25

            # D. Match Target Role (+10 pts)
            for kw in role_keywords:
                if any(kw in sk for sk in cand_skills_lower) or kw in cand_topic_lower:
                    score += 10

            # E. Resume claim personalization (+1 pt max per match, cannot outvote competency)
            for skill in candidate.get("skills", []):
                s_lower = skill.lower()
                if resume_text and s_lower in resume_text:
                    score += 1
                    current_matched.append(skill)
                elif candidate_claims and any(s_lower in str(c).lower() for c in candidate_claims):
                    score += 1
                    current_matched.append(skill)

            # F. Match difficulty
            if candidate["difficulty"].lower() == calibrated_difficulty:
                score += 2

            # G. Match depth level (FOUNDATION, PRACTICAL, FOLLOW_UP, ADVANCED)
            if depth_level and candidate.get("depth_level") == depth_level:
                score += 15

            if score > best_match_score:
                best_match_score = score
                best_candidate = candidate
                matched_skills_found = current_matched

        # 5. Dynamically ground resume evidence
        if matched_skills_found:
            dynamic_evidence = f"Grounding in candidate verified background: {', '.join(matched_skills_found[:3])}."
        else:
            dynamic_evidence = f"Grounding in candidate competencies for {target_competency or target_role}."

        # 6. Synthesize conversational bridge
        clean_question, bridge_lead_in = cls._synthesize_conversational_bridge(
            base_question=best_candidate["question"],
            best_candidate=best_candidate,
            last_question=last_question,
            last_answer=last_answer,
            last_score=last_score,
            last_missing_concepts=last_missing_concepts,
            candidate_claims=candidate_claims,
        )

        # Question-Rubric Integrity: The bank question's expected concepts must reflect the actual question asked
        candidate_bank_concepts = list(best_candidate.get("expected_concepts", []))
        if expected_concepts:
            from ai.interview_engine.question_sanitizer import GENERIC_DOMAIN_VOCABULARY
            cand_q_text = best_candidate.get("question", "").lower()
            cand_top_text = best_candidate.get("topic", "").lower()
            matched_external = [
                ec for ec in expected_concepts
                if any(
                    tok in cand_q_text or tok in cand_top_text
                    for tok in ec.lower().split()
                    if len(tok) >= 4 and tok not in GENERIC_DOMAIN_VOCABULARY
                )
            ]
            out_concepts = candidate_bank_concepts
            for ec in matched_external:
                if ec not in out_concepts:
                    out_concepts.append(ec)
        else:
            out_concepts = candidate_bank_concepts

        # If best_candidate is from a specific competency, respect it
        effective_competency = target_competency or best_candidate["topic"]
        if target_competency and target_competency.lower() not in best_candidate["topic"].lower():
            # Check if best_candidate actually assesses target_competency
            cand_q_lower = best_candidate.get("question", "").lower()
            if not any(k in cand_q_lower for k in target_competency.lower().split() if len(k) > 4):
                effective_competency = best_candidate["topic"]

        return {
            "question": clean_question,
            "coach_lead_in": bridge_lead_in,
            "category": best_candidate["category"],
            "topic": best_candidate["topic"],
            "difficulty": best_candidate.get("difficulty", calibrated_difficulty),
            "stage_name": best_candidate["stage_name"],
            "stage_index": best_candidate["stage_index"],
            "total_stages": 5,
            "resume_evidence": dynamic_evidence,
            "expected_concepts": out_concepts,
            "target_competency": effective_competency,
            "assessment_objective": f"Assess candidate mastery of {effective_competency}",
        }



