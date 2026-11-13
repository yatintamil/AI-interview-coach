"""
Role Intelligence and Resolution Service.

Provides deterministic role normalization, curated competency registries,
multi-role resolution, custom role interpretation, and safe offline research fallbacks.
Enforces the principle: ROLE DEFINES WHAT IS ASSESSED.
"""

import re
import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple

from backend.domain.role.models import (
    RoleProvenance,
    CompetencyImportance,
    RequirementClassification,
    RoleResearchStatus,
    RoleResearchSpecification,
    RoleSpecification,
    RoleProfile,
    RoleCompetency,
    RoleCompetencyBlueprint,
)
from ai.interview_engine.role_research_engine import RoleResearchEngine, RoleCandidateMatcher, _ROLE_CACHE

logger = logging.getLogger(__name__)


# ============================================================================
# CURATED ROLE COMPETENCIES REGISTRY
# ============================================================================

CURATED_ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "embedding_systems_engineer": {
        "display_name": "Embedding Systems Engineer",
        "aliases": [
            "embedding engineer", "embedding systems engineer", "embedding system engineer",
            "vector search engineer", "vector retrieval engineer", "retrieval systems engineer"
        ],
        "description": (
            "Specialized engineering role focused on large-scale representation learning, "
            "vector indexing, approximate nearest neighbor (ANN) retrieval, embedding inference pipelines, "
            "and production vector search infrastructure."
        ),
        "responsibilities": [
            "Design and operate high-throughput embedding generation and model inference pipelines",
            "Build and tune Approximate Nearest Neighbor (ANN) vector indices (HNSW, IVF-PQ)",
            "Optimize latency, memory footprint, and recall trade-offs for production vector search",
            "Handle embedding drift, versioning, and cold-start indexing",
            "Integrate vector search into hybrid retrieval and re-ranking pipelines",
        ],
        "knowledge_areas": [
            "Vector Representations & Metric Spaces",
            "Approximate Nearest Neighbor (ANN) Indexing",
            "High-Throughput Model Serving & Pipeline Concurrency",
            "Vector Search Systems & Hybrid Retrieval",
            "Retrieval Reliability & Operational Scale",
        ],
        "competencies": [
            {
                "identifier": "embedding_fundamentals",
                "name": "Embedding Fundamentals & Metric Spaces",
                "description": "Understanding dense representations, dimensional geometry, and distance metric invariants.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "dense embeddings", "cosine similarity", "dot product", "euclidean distance",
                    "vector normalization", "curse of dimensionality", "semantic representation"
                ],
                "core_invariants": [
                    "Cosine similarity requires unit-normalized vectors for dot product equivalence",
                    "High-dimensional metric spaces suffer from distance concentration"
                ],
                "assessment_objectives": [
                    "Determine candidate's grasp of geometric metric spaces, normalization invariants, and dimensionality trade-offs."
                ],
                "evidence_requirements": [
                    "Explains normalization requirements for distance metrics",
                    "Reasons about dimensionality selection vs representation fidelity"
                ],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "vector_indexing_and_ann",
                "name": "Vector Indexing & Approximate Nearest Neighbor Search",
                "description": "Mastery of ANN algorithms, graph-based indices, quantization, and recall-latency curves.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "HNSW", "IVF", "Product Quantization (PQ)", "efSearch vs M parameters",
                    "recall vs latency trade-off", "index build time", "memory overhead"
                ],
                "core_invariants": [
                    "HNSW achieves logarithmic search complexity via hierarchical small-world skip-graphs at the cost of high RAM consumption",
                    "Quantization compresses memory footprint at the expense of vector precision and recall"
                ],
                "assessment_objectives": [
                    "Assess whether candidate can evaluate, configure, and debug graph vs clustering ANN index trade-offs under latency budgets."
                ],
                "evidence_requirements": [
                    "Details HNSW graph traversal and pruning invariants",
                    "Compares memory and query performance of HNSW vs IVF-PQ"
                ],
                "difficulty_expectations": "hard",
                "stage_suitability": 2,
            },
            {
                "identifier": "embedding_pipeline_architecture",
                "name": "Embedding Generation Pipeline & Serving Architecture",
                "description": "Designing high-throughput asynchronous batching, model inference, and vector ingestion pipelines.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "dynamic batching", "GPU/CPU inference offloading", "streaming ingestion",
                    "backpressure", "asynchronous event loops", "vector store synchronization"
                ],
                "core_invariants": [
                    "Inference latency is bounded by batch size and device memory bandwidth",
                    "Backpressure mechanisms must prevent queue bloat during embedding generation spikes"
                ],
                "assessment_objectives": [
                    "Determine candidate's ability to architect resilient, concurrent vector processing pipelines at scale."
                ],
                "evidence_requirements": [
                    "Articulates batching, queue management, and worker pool scaling",
                    "Designs vector persistence and synchronization strategy"
                ],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "vector_system_reliability_and_drift",
                "name": "Vector System Invariants, Failures & Drift Debugging",
                "description": "Diagnosing silent degradation, embedding distribution shift, dimension mismatch, and index corruption.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "embedding drift", "dimension mismatch", "zero-downtime index re-building",
                    "fallback lexical search", "degraded recall monitoring", "circuit breaking"
                ],
                "core_invariants": [
                    "Model updates require complete re-indexing or dual-embedding compatibility layers",
                    "Silent semantic degradation cannot be caught by binary health checks alone"
                ],
                "assessment_objectives": [
                    "Test candidate's response to catastrophic vector retrieval failures and data distribution shifts."
                ],
                "evidence_requirements": [
                    "Explains migration strategy during embedding model upgrades",
                    "Proposes automated detection of semantic drift and recall drop"
                ],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "retrieval_tradeoffs_and_ownership",
                "name": "Production Trade-offs, Cost Governance & Ownership",
                "description": "Executive decision-making regarding in-memory cost, latency SLAs, and cross-functional retrieval quality.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": [
                    "RAM cost governance", "p99 latency SLAs", "hybrid search weighting",
                    "re-ranking trade-offs", "cross-functional stakeholder alignment"
                ],
                "core_invariants": [
                    "In-memory vector indexing must be weighed against commodity disk-backed storage and SLA targets"
                ],
                "assessment_objectives": [
                    "Evaluate engineering maturity, architectural trade-off justification, and cross-functional leadership."
                ],
                "evidence_requirements": [
                    "Defends hardware and index configuration based on cost and SLA targets",
                    "Communicates cross-functional trade-offs between relevance, cost, and latency"
                ],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "distributed_database_reliability_engineer": {
        "display_name": "Distributed Database Reliability Engineer",
        "aliases": [
            "distributed database engineer", "database reliability engineer", "database sre",
            "distributed systems engineer", "distributed systems architect", "distributed systems",
            "storage systems engineer"
        ],
        "description": (
            "Specialized engineering role focusing on distributed storage engines, consensus protocols, "
            "replication topologies, durability invariants, high-availability failover, and zero-downtime operations."
        ),
        "responsibilities": [
            "Maintain consistency, replication, and durability invariants across distributed database clusters",
            "Implement and verify distributed consensus algorithms (Raft, Paxos)",
            "Diagnose and recover from split-brain scenarios and network partitions",
            "Optimize storage engines (LSM-trees, B-trees) and write-ahead logs (WAL)",
            "Design disaster recovery, point-in-time recovery, and zero-downtime migration procedures",
        ],
        "knowledge_areas": [
            "Distributed Consensus & Quorum Protocols",
            "Storage Engine Internals & Write-Ahead Logging",
            "High-Availability, Failover & Partition Recovery",
            "Data Invariant Verification & Incident Debugging",
            "Scalability, SLOs & Disaster Recovery",
        ],
        "competencies": [
            {
                "identifier": "distributed_consensus_and_quorum",
                "name": "Distributed Consensus & Quorum Mechanics",
                "description": "Mastery of consensus algorithms (Raft/Paxos), leader election, quorum reads/writes, and linearizability.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "Raft consensus", "Paxos", "leader election", "quorum arithmetic",
                    "split-vote resolution", "linearizable reads", "term numbers"
                ],
                "core_invariants": [
                    "A quorum requires (N/2)+1 nodes to guarantee overlapping consensus sets",
                    "Only one leader can be elected per term"
                ],
                "assessment_objectives": [
                    "Verify candidate's formal reasoning regarding distributed consensus, election safety, and linearizability."
                ],
                "evidence_requirements": [
                    "Proves quorum intersection property",
                    "Explains leader election invariants and log matching property"
                ],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "storage_engine_and_wal_internals",
                "name": "Storage Engine Internals & Durability Invariants",
                "description": "Deep understanding of write-ahead logging (WAL), fsync semantics, LSM-trees, memtables, and SSTable compaction.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "Write-Ahead Log (WAL)", "fsync vs fdatasync", "LSM-tree", "B-tree vs LSM",
                    "SSTable compaction", "memtable flushing", "write amplification"
                ],
                "core_invariants": [
                    "A transaction cannot be acknowledged as committed until its WAL record is durably flushed to non-volatile storage",
                    "Compaction prevents read amplification at the cost of background I/O write amplification"
                ],
                "assessment_objectives": [
                    "Determine candidate's ability to reason about hardware durability, crash recovery, and storage engine I/O trade-offs."
                ],
                "evidence_requirements": [
                    "Details crash recovery procedure from WAL checkpoints",
                    "Compares LSM compaction strategies (leveled vs size-tiered)"
                ],
                "difficulty_expectations": "hard",
                "stage_suitability": 2,
            },
            {
                "identifier": "replication_and_partition_resilience",
                "name": "Replication Topologies & Network Partition Resilience",
                "description": "Designing synchronous vs asynchronous replication, split-brain protection, and partition tolerance.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "split-brain protection", "fencing tokens", "synchronous vs asynchronous replication",
                    "replication lag", "CAP theorem trade-offs", "network partitions"
                ],
                "core_invariants": [
                    "Network partitions must isolate the minority partition from accepting non-fenced writes",
                    "Asynchronous replication admits bounded data loss on ungraceful failover"
                ],
                "assessment_objectives": [
                    "Assess whether candidate can design partition-resilient multi-region database replication."
                ],
                "evidence_requirements": [
                    "Explains fencing token mechanisms to stop stale leader split-brain",
                    "Defines replication lag remediation under peak write loads"
                ],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "incident_debugging_and_split_brain_recovery",
                "name": "Incident Triage, Split-Brain Invariants & Recovery",
                "description": "Root-cause diagnosis during catastrophic storage failures, data corruption, and post-partition reconciliation.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": [
                    "split-brain data divergence", "vector clocks", "conflict resolution",
                    "point-in-time recovery (PITR)", "silent corruption detection", "checksums"
                ],
                "core_invariants": [
                    "Conflicting divergent writes post-split-brain require deterministic reconciliation rules or manual remediation"
                ],
                "assessment_objectives": [
                    "Test candidate's hands-on crisis management, invariant verification, and disaster recovery execution."
                ],
                "evidence_requirements": [
                    "Formulates step-by-step triage for split-brain data reconciliation",
                    "Validates data integrity using block-level and cryptographic checksums"
                ],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "database_governance_and_slo_defense",
                "name": "Database Reliability Governance & Zero-Downtime Migration",
                "description": "Cross-functional SLA/SLO defense, capacity modeling, and schema migration without downtime.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": [
                    "online schema migrations", "RPO and RTO definitions", "error budgets",
                    "capacity modeling", "blameless postmortem leadership"
                ],
                "core_invariants": [
                    "Schema modifications on multi-terabyte tables must be backward-compatible and non-blocking"
                ],
                "assessment_objectives": [
                    "Evaluate operational leadership, risk management, and communication during planned maintenance."
                ],
                "evidence_requirements": [
                    "Outlines zero-downtime expand-and-contract schema migration methodology",
                    "Defines quantifiable RPO/RTO objectives for mission-critical clusters"
                ],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "machine_learning_engineer": {
        "display_name": "Machine Learning Engineer",
        "aliases": ["ml engineer", "machine learning engineer", "ml systems engineer", "ai engineer"],
        "description": "Engineering role bridging statistical modeling, feature pipelines, model training loops, and low-latency production model serving.",
        "responsibilities": [
            "Build robust feature engineering and training data pipelines",
            "Evaluate model performance, prevent data leakage, and establish offline-online metric parity",
            "Optimize model inference latency, throughput, and memory consumption",
            "Implement MLOps continuous training, model registries, and drift detection",
        ],
        "knowledge_areas": ["Feature Pipelines", "Evaluation & Metric Parity", "Serving & Optimization", "MLOps & Drift", "ML Governance"],
        "competencies": [
            {
                "identifier": "feature_pipelines_and_leakage",
                "name": "Feature Engineering & Data Leakage Prevention",
                "description": "Building point-in-time correct feature pipelines and eliminating train-serve skew.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["point-in-time correctness", "train-serve skew", "feature store", "data leakage"],
                "core_invariants": ["Features used at inference time must strictly reflect information available at prediction timestamp"],
                "assessment_objectives": ["Assess candidate's ability to design leak-free feature pipelines."],
                "evidence_requirements": ["Explains point-in-time join logic and prevention of lookahead bias"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "model_evaluation_and_loss_invariants",
                "name": "Model Evaluation, Calibration & Metrics",
                "description": "Rigorous evaluation across imbalanced distributions, loss formulations, and probability calibration.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["precision-recall AUC", "Brier score", "log loss", "probability calibration", "class imbalance"],
                "core_invariants": ["ROC-AUC is insensitive to class balance changes; PR-AUC must be used under extreme class skew"],
                "assessment_objectives": ["Determine candidate's evaluation rigor on non-trivial data distributions."],
                "evidence_requirements": ["Selects appropriate metrics for imbalanced datasets and explains calibration"],
                "difficulty_expectations": "hard",
                "stage_suitability": 2,
            },
            {
                "identifier": "model_serving_and_latency_optimization",
                "name": "Model Serving & High-Throughput Inference Optimization",
                "description": "Low-latency model serving, dynamic batching, quantization (FP16/INT8), and GPU memory management.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["dynamic batching", "quantization", "ONNX/TensorRT", "GPU memory saturation", "p99 latency"],
                "core_invariants": ["Batch size increases throughput at the cost of linear latency escalation"],
                "assessment_objectives": ["Assess ability to meet sub-50ms inference SLAs under high traffic."],
                "evidence_requirements": ["Designs serving tier with batching, worker isolation, and caching"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "ml_drift_debugging_and_fallback",
                "name": "Concept Drift, Outlier Triage & Fallback Systems",
                "description": "Detecting covariate shift, concept drift, corrupted inputs, and executing safe fallback policies.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["covariate shift", "concept drift", "KS-test / PSI", "shadow deployment", "fallback rules"],
                "core_invariants": ["Model performance degrades silently when input distributions shift from training priors"],
                "assessment_objectives": ["Test candidate's production monitoring and graceful degradation strategies."],
                "evidence_requirements": ["Proposes automated statistical drift detection and safe fallback routing"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "cross_functional_ml_governance",
                "name": "Business Impact Alignment, Cost & Ethical Governance",
                "description": "Balancing business ROI, cloud GPU compute costs, model explainability, and cross-functional leadership.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["GPU cost optimization", "business KPI translation", "fairness guardrails", "model governance"],
                "core_invariants": ["A 1% model accuracy lift is invalid if inference cost exceeds business return"],
                "assessment_objectives": ["Evaluate cross-functional leadership and economic trade-off reasoning."],
                "evidence_requirements": ["Communicates trade-offs between model complexity, operating cost, and business value"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "backend_systems_engineer": {
        "display_name": "Backend Systems Engineer",
        "aliases": ["backend engineer", "backend systems engineer", "backend developer", "api engineer"],
        "description": "Core software engineering role focusing on robust web APIs, transactional databases, caching, concurrency, and scalable distributed services.",
        "responsibilities": [
            "Develop high-performance REST and gRPC API endpoints",
            "Design normalized and denormalized relational schemas and query plans",
            "Implement distributed caching, queueing, and asynchronous workflows",
            "Maintain system resilience, circuit breaking, and telemetry",
        ],
        "knowledge_areas": ["API & Concurrency Mechanics", "Relational Integrity & Indexes", "Distributed Caching & Queues", "Resilience & Circuit Breaking", "Observability & Ownership"],
        "competencies": [
            {
                "identifier": "backend_api_and_concurrency",
                "name": "API Architecture, Idempotency & Concurrency Mechanics",
                "description": "Designing robust, stateless APIs, idempotency keys, race condition avoidance, and event loops.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["idempotency keys", "event loop blocking", "thread pool exhaustion", "HTTP semantics", "race conditions"],
                "core_invariants": ["Non-idempotent POST requests must be protected by unique client tokens across retries"],
                "assessment_objectives": ["Assess candidate's ability to design concurrent, safe API endpoints."],
                "evidence_requirements": ["Explains idempotency storage and race-condition prevention mechanisms"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "relational_integrity_and_indexing",
                "name": "Relational Data Integrity, Transactions & Query Planning",
                "description": "ACID guarantees, transaction isolation levels, index selection (B-tree), and query plan analysis.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["ACID isolation levels", "read committed vs serializable", "B-tree indexing", "explain analyze", "deadlocks"],
                "core_invariants": ["Composite index lookups require left-to-right prefix matching"],
                "assessment_objectives": ["Determine mastery of database query optimization and locking mechanics."],
                "evidence_requirements": ["Diagnoses query latency using EXPLAIN ANALYZE and structures safe composite indexes"],
                "difficulty_expectations": "hard",
                "stage_suitability": 2,
            },
            {
                "identifier": "distributed_caching_and_messaging",
                "name": "Distributed Caching, Invalidation & Asynchronous Messaging",
                "description": "Cache-aside, write-through, thundering herd mitigation, and message queue consumer delivery semantics.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["cache invalidation", "cache-aside pattern", "thundering herd", "Kafka / RabbitMQ", "at-least-once delivery"],
                "core_invariants": ["At-least-once consumer delivery necessitates consumer-side idempotency"],
                "assessment_objectives": ["Assess architectural trade-offs in caching strategies and decoupled event architectures."],
                "evidence_requirements": ["Architects cache-aside with TTL jitter and idempotent message consumption"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "system_resilience_and_debugging",
                "name": "Cascade Failure Mitigation, Circuit Breaking & Incident Triage",
                "description": "Preventing cascade outages, designing circuit breakers, rate limiters, and diagnosing live service crashes.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["cascade failure", "circuit breaker pattern", "token bucket rate limiting", "exponential backoff with jitter"],
                "core_invariants": ["Downstream dependency slowdowns exhaust caller connection pools unless protected by timeouts and circuit breakers"],
                "assessment_objectives": ["Test candidate's ability to protect distributed systems under severe degradation."],
                "evidence_requirements": ["Structures circuit breaker state transitions and backoff retry policies"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "observability_and_star_ownership",
                "name": "Production Observability, SLA Management & Cross-Team Ownership",
                "description": "Distributed tracing (OpenTelemetry), p99 latency SLOs, and leading cross-functional incident retrospectives.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["OpenTelemetry tracing", "p99 vs average latency", "SLO error budgets", "blameless postmortems"],
                "core_invariants": ["Average latency masks catastrophic tail degradation; p99/p99.9 metrics are mandatory"],
                "assessment_objectives": ["Evaluate operational maturity, telemetry design, and engineering communication."],
                "evidence_requirements": ["Defends latency metrics and illustrates blameless incident leadership"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "cloud_devops_sre": {
        "display_name": "Cloud DevOps / SRE",
        "aliases": ["cloud engineer", "devops engineer", "site reliability engineer", "sre", "platform engineer", "infrastructure engineer"],
        "description": "Systems engineering role dedicated to infrastructure as code, container orchestration, automated delivery pipelines, telemetry, and site reliability.",
        "responsibilities": [
            "Automate multi-cloud infrastructure with Terraform and Kubernetes",
            "Design zero-downtime CI/CD deployment pipelines",
            "Establish site reliability objectives (SLOs) and error budget policies",
            "Lead incident triage, chaos engineering, and disaster recovery drills",
        ],
        "knowledge_areas": ["Infrastructure as Code", "Container Orchestration", "CI/CD & Progressive Delivery", "Chaos & Incident Mitigation", "SLO Governance"],
        "competencies": [
            {
                "identifier": "iac_and_cloud_foundations",
                "name": "Infrastructure as Code & Cloud Security Foundations",
                "description": "Declarative cloud state, state lock management, drift detection, and least-privilege IAM.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["Terraform state management", "drift detection", "immutable infrastructure", "IAM least privilege"],
                "core_invariants": ["Production infrastructure mutations must be driven declaratively through version-controlled state"],
                "assessment_objectives": ["Assess candidate's ability to maintain repeatable, drift-free cloud infrastructure."],
                "evidence_requirements": ["Explains state locking, remote backends, and zero-trust IAM roles"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "container_orchestration_and_networking",
                "name": "Container Orchestration, CNI & Pod Lifecycle Invariants",
                "description": "Kubernetes architecture, kube-scheduler, ingress controllers, CNI networking, and graceful pod termination.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["Kubernetes pod lifecycle", "SIGTERM handling", "liveness vs readiness probes", "CNI routing"],
                "core_invariants": ["Readiness probe failure must immediately excise pod from service endpoints before SIGTERM is issued"],
                "assessment_objectives": ["Test deep knowledge of Kubernetes networking and container runtime invariants."],
                "evidence_requirements": ["Distinguishes readiness from liveness probes and designs graceful shutdown handlers"],
                "difficulty_expectations": "hard",
                "stage_suitability": 2,
            },
            {
                "identifier": "ci_cd_and_progressive_delivery",
                "name": "Progressive Delivery, Canary Rollouts & Automated Rollbacks",
                "description": "Blue-green deployments, canary traffic routing, automated metric analysis, and instant rollback gates.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["canary deployment", "blue-green deployment", "automated rollback metrics", "artifact immutability"],
                "core_invariants": ["Deployment pipelines must verify canary error rates against baseline before promoting traffic"],
                "assessment_objectives": ["Assess whether candidate can design zero-downtime automated release systems."],
                "evidence_requirements": ["Structures automated canary analysis and rollback triggers"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "incident_mitigation_and_chaos_engineering",
                "name": "Chaos Engineering, Outage Triage & Runbook Automation",
                "description": "Simulating failure domains (region failure, packet loss), automated remediation, and post-outage recovery.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["chaos engineering", "MTTR reduction", "automated failover", "split-DNS routing", "postmortem RCA"],
                "core_invariants": ["Untested disaster recovery failover mechanisms fail under real production crises"],
                "assessment_objectives": ["Evaluate real-world crisis response and automated system stabilization."],
                "evidence_requirements": ["Formulates chaos experiment to validate multi-zone resilience"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "slo_governance_and_capacity_planning",
                "name": "Site Reliability Governance, Error Budgets & Executive Toil Reduction",
                "description": "Negotiating SLOs with product teams, enforcing error budget gates, and eliminating operational toil.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["SLO / SLI / SLA", "error budget freeze policy", "toil budget (50% rule)", "capacity forecasting"],
                "core_invariants": ["Exhausted error budgets must halt feature launches to prioritize reliability engineering"],
                "assessment_objectives": ["Assess candidate's ability to govern platform reliability across business stakeholders."],
                "evidence_requirements": ["Defines enforceable error budget policies and communicates reliability trade-offs"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "universal_software_engineering": {
        "display_name": "Universal Software Engineering",
        "aliases": ["omnirole", "adaptive omnirole", "software engineer", "general software engineer", "full stack engineer"],
        "description": "Adaptive universal engineering assessment evaluating foundational algorithms, clean architecture, distributed systems trade-offs, and collaborative leadership.",
        "responsibilities": [
            "Write maintainable, robust code with clear invariant preservation",
            "Design scalable architectures and select optimal data structures",
            "Debug complex race conditions and system bottlenecks",
            "Collaborate effectively across cross-functional product and engineering teams",
        ],
        "knowledge_areas": ["Foundations & Invariants", "Clean Architecture", "Distributed Systems", "Incident Debugging", "Collaborative Leadership"],
        "competencies": [
            {
                "identifier": "algorithmic_mechanics_and_invariants",
                "name": "Algorithmic Mechanics, Complexity & Invariants",
                "description": "Time/space complexity proofs, boundary conditions, and invariant preservation in core data structures.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["Big-O asymptotic complexity", "boundary edge cases", "invariant maintenance", "data structure selection"],
                "core_invariants": ["Invariants established at initialization must be preserved across every state transition"],
                "assessment_objectives": ["Test candidate's foundational algorithmic rigor and edge-case resilience."],
                "evidence_requirements": ["Analyzes worst-case time/space bounds and proves boundary invariants"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "modular_architecture_and_design",
                "name": "Modular Clean Architecture & System Decomposition",
                "description": "Separation of concerns, dependency inversion, clean interface boundaries, and high testability.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["SOLID principles", "dependency injection", "loose coupling", "domain-driven boundaries"],
                "core_invariants": ["Domain business logic must remain independent of external delivery and persistence frameworks"],
                "assessment_objectives": ["Assess code organization, interface clarity, and maintainability."],
                "evidence_requirements": ["Decomposes monolithic procedures into clean, testable interfaces"],
                "difficulty_expectations": "medium",
                "stage_suitability": 2,
            },
            {
                "identifier": "scalable_systems_and_tradeoffs",
                "name": "Scalable Systems Architecture & Trade-off Reasoning",
                "description": "Horizontal scaling, caching patterns, database bottlenecks, and latency vs throughput trade-offs.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["horizontal vs vertical scaling", "read-replicas", "caching trade-offs", "load balancing"],
                "core_invariants": ["Scaling stateless compute requires addressing underlying database connection and transaction bottlenecks"],
                "assessment_objectives": ["Determine architectural reasoning under 10x traffic escalation."],
                "evidence_requirements": ["Identifies bottlenecks and articulates architectural trade-offs"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "debugging_and_failure_investigation",
                "name": "Failure Modes, Race Condition Triage & Debugging",
                "description": "Systematic reproduction of edge failures, memory leak investigation, and distributed deadlock triage.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["race conditions", "reproduction methodology", "thread contention", "memory profiling"],
                "core_invariants": ["Intermittent race conditions cannot be resolved by arbitrary sleeps; synchronization primitives are required"],
                "assessment_objectives": ["Assess diagnostic methodology during unexplained production regressions."],
                "evidence_requirements": ["Structures hypothesis-driven root cause debugging methodology"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "collaborative_ownership_and_star",
                "name": "Cross-Functional Ownership, Conflict Resolution & STAR Leadership",
                "description": "Situation-Task-Action-Result leadership, technical debt negotiation, and cross-team alignment.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["STAR framework", "technical debt communication", "conflict resolution", "mentorship"],
                "core_invariants": ["Effective technical leadership requires framing engineering priorities in terms of business impact and risk"],
                "assessment_objectives": ["Evaluate communication, executive presence, and constructive team ownership."],
                "evidence_requirements": ["Provides structured STAR narrative demonstrating accountability and impact"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "ai_data_science_engineer": {
        "display_name": "AI & Data Science Engineer",
        "aliases": [
            "ai data science engineer", "ai data science student", "ai engineer", "data scientist",
            "junior data scientist", "ai research specialist", "ai data scientist", "machine learning and data science"
        ],
        "description": "Engineering and analytical role focused on statistical modeling, data hygiene, supervised/unsupervised machine learning, and scalable inference.",
        "responsibilities": [
            "Analyze and prepare tabular, text, and numerical datasets avoiding leakage and bias",
            "Train, cross-validate, and calibrate predictive machine learning and deep learning models",
            "Engineer meaningful domain features and perform dimensional reduction",
            "Design reproducible evaluation pipelines comparing precision, recall, ROC-AUC, and F1-score",
            "Deploy lightweight model inference APIs and monitor performance against baseline metrics",
        ],
        "knowledge_areas": [
            "Data Preprocessing & Exploratory Data Analysis",
            "Supervised & Unsupervised Machine Learning",
            "Model Evaluation, Validation Splits & Metric Calibration",
            "Feature Engineering & Dimensionality Reduction",
            "Model Deployment & Production Data Pipelines",
        ],
        "competencies": [
            {
                "identifier": "ml_foundations_and_data_hygiene",
                "name": "Machine Learning Foundations & Data Hygiene",
                "description": "Understanding core ML algorithms, train/val/test split invariants, and data leakage prevention.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["train-test split", "data leakage", "overfitting vs underfitting", "bias-variance tradeoff", "imbalanced classes", "normalization"],
                "core_invariants": ["Data transformations must be fit exclusively on training splits to prevent leakage into validation data"],
                "assessment_objectives": ["Assess whether candidate structures resilient data pipelines without data leakage."],
                "evidence_requirements": ["Explains prevention of data leakage during scaling/imputation", "Reasons about model generalization"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "feature_engineering_and_evaluation",
                "name": "Feature Engineering, Evaluation & Calibration",
                "description": "Selecting domain features, handling missingness, and choosing metrics aligned with task objectives.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["precision vs recall", "ROC-AUC", "F1-score", "cross-validation", "feature scaling", "confusion matrix"],
                "core_invariants": ["Accuracy is an invalid evaluation metric under severe class imbalance"],
                "assessment_objectives": ["Assess metric selection and evaluation rigor under asymmetric error costs."],
                "evidence_requirements": ["Justifies metric trade-offs for high-cost false negatives", "Explains k-fold cross-validation methodology"],
                "difficulty_expectations": "medium",
                "stage_suitability": 2,
            },
            {
                "identifier": "ml_pipelines_and_model_deployment",
                "name": "Production ML Pipelines & Model Serving",
                "description": "Building reproducible training pipelines, serialization, batch vs streaming inference, and API serving.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["model serialization", "ONNX", "batch vs real-time inference", "inference latency", "concept drift", "FastAPI serving"],
                "core_invariants": ["Serving pipelines must apply identical preprocessing transformations as training pipelines"],
                "assessment_objectives": ["Assess candidate's ability to transition models from notebooks to robust production inference APIs."],
                "evidence_requirements": ["Details model serving architecture and latency budgets", "Explains monitoring for distribution drift"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "data_modeling_and_analytical_rigor",
                "name": "Data Modeling, SQL Analytics & Failure Diagnostics",
                "description": "Querying relational data, diagnosing model degradation, and identifying edge cases in predictions.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["SQL joins & aggregations", "window functions", "root cause model degradation", "outlier detection", "error analysis"],
                "core_invariants": ["Systematic residual error analysis is required to identify systematic sub-population failures"],
                "assessment_objectives": ["Assess SQL fluency and systematic error analysis when a deployed model underperforms."],
                "evidence_requirements": ["Explains query strategies and systematic error slicing"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "ai_communication_and_star_ownership",
                "name": "AI Product Communication & STAR Project Ownership",
                "description": "Communicating model trade-offs to non-technical stakeholders and demonstrating ownership of end-to-end deliverables.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["STAR framework", "stakeholder communication", "ethical AI considerations", "trade-off framing"],
                "core_invariants": ["Model predictions and confidence limitations must be transparently communicated to end-users"],
                "assessment_objectives": ["Evaluate clarity when explaining model choices and project results."],
                "evidence_requirements": ["Delivers structured STAR answer explaining technical decisions and quantifiable outcomes"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "embedded_systems_engineer": {
        "display_name": "Embedded Systems Engineer",
        "aliases": [
            "embedded systems engineer", "embedded engineer", "firmware engineer", "embedded software engineer",
            "microcontroller engineer", "iot engineer", "robotics systems engineer"
        ],
        "description": "Hardware-software co-design role developing deterministic, resource-constrained firmware, device drivers, and real-time control loops.",
        "responsibilities": [
            "Develop bare-metal and RTOS firmware in C and C++ for microcontrollers and embedded processors",
            "Implement interrupt service routines, direct memory access (DMA), and peripheral drivers",
            "Configure hardware communication buses including I2C, SPI, UART, and CAN",
            "Diagnose memory leaks, stack overflows, timing violations, and hardware faults with logic analyzers",
            "Optimize memory usage, power consumption (deep sleep modes), and execution latency",
        ],
        "knowledge_areas": [
            "Microcontroller Architecture & Memory-Mapped I/O",
            "Interrupts, ISRs & Concurrency Invariants",
            "Embedded C/C++ Semantics & Volatile Memory",
            "Hardware Peripheral Interfacing (SPI, I2C, UART, DMA)",
            "Real-Time Operating Systems (RTOS) & Fault Recovery",
        ],
        "competencies": [
            {
                "identifier": "embedded_c_and_memory_mapped_io",
                "name": "Embedded C/C++ & Memory-Mapped I/O",
                "description": "Register-level programming, pointer arithmetic, bitwise manipulation, and memory layout.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["volatile qualifier", "memory-mapped registers", "bitwise operations", "const pointers", "structure padding", "endianness"],
                "core_invariants": ["Hardware registers modified asynchronously by hardware must be declared volatile to prevent compiler register caching"],
                "assessment_objectives": ["Verify candidate's grasp of low-level memory invariants and hardware register manipulation."],
                "evidence_requirements": ["Explains why volatile is essential for hardware status registers and shared variables"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "interrupts_and_concurrency_boundaries",
                "name": "Interrupt Service Routines (ISRs) & Real-Time Constraints",
                "description": "Handling hardware interrupts, race condition mitigation, atomic operations, and circular buffers.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["ISR execution time", "critical sections", "interrupt nesting & priority", "circular ring buffers", "atomic operations"],
                "core_invariants": ["ISRs must be non-blocking and minimal; lengthy processing must be deferred to the main loop or worker tasks"],
                "assessment_objectives": ["Assess interrupt safety, shared resource protection, and latency determinism."],
                "evidence_requirements": ["Designs lock-free ring buffer for inter-context data passing"],
                "difficulty_expectations": "medium",
                "stage_suitability": 2,
            },
            {
                "identifier": "peripheral_bus_protocols_and_dma",
                "name": "Hardware Bus Protocols & DMA Transfers",
                "description": "Interfacing sensors and displays via I2C, SPI, UART, and offloading CPU cycles via DMA.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["I2C pull-up resistors & clock stretching", "SPI clock polarity & phase (CPOL/CPHA)", "UART framing errors", "DMA circular mode"],
                "core_invariants": ["DMA memory buffers must not be modified by CPU while transfer is in flight without cache coherency synchronization"],
                "assessment_objectives": ["Evaluate protocol selection and DMA throughput optimization."],
                "evidence_requirements": ["Compares throughput and bus contention of SPI vs I2C under sensor streaming"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "fault_diagnostics_watchdogs_and_power",
                "name": "Embedded Fault Recovery, Watchdogs & Low-Power Management",
                "description": "Diagnosing hard faults, stack overflow protection, independent watchdog timers, and low-power sleep modes.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["independent watchdog timer (IWDG)", "hard fault handler", "stack canary", "deep sleep power states", "brownout reset"],
                "core_invariants": ["Watchdog timer refresh must be coupled to actual system progress, never naively refreshed inside a periodic timer interrupt"],
                "assessment_objectives": ["Assess embedded resilience and fail-safe system design under transient electrical or software faults."],
                "evidence_requirements": ["Explains proper watchdog design and stack fault diagnosis"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "embedded_project_ownership_and_star",
                "name": "Hardware-Software Integration & STAR Leadership",
                "description": "Debugging multi-disciplinary hardware/software boundaries, collaborating with electrical engineers, and taking ownership.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["STAR framework", "hardware-software debugging", "bill of materials (BOM) trade-offs", "cross-functional ownership"],
                "core_invariants": ["Hardware-software boundary defects require systematic isolation of physical vs firmware layers"],
                "assessment_objectives": ["Evaluate communication and practical engineering ownership during physical prototype integration."],
                "evidence_requirements": ["Structures clear STAR explanation of diagnosing hardware-software integration challenges"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "full_stack_software_engineer": {
        "display_name": "Full-Stack Software Engineer",
        "aliases": [
            "full stack software engineer", "full stack engineer", "full-stack developer", "web developer",
            "frontend and backend engineer", "software engineer full stack"
        ],
        "description": "End-to-end engineering role designing reactive user interfaces, performant APIs, relational data models, and scalable deployment pipelines.",
        "responsibilities": [
            "Build responsive, accessible, component-driven user interfaces using modern frameworks (React, Next.js)",
            "Design clean RESTful and GraphQL APIs with robust validation and error handling",
            "Model relational and document database schemas with composite indexes and migration strategies",
            "Implement secure authentication, session management, and state synchronization across client and server",
            "Deploy, containerize, and monitor end-to-end applications in production environments",
        ],
        "knowledge_areas": [
            "Client Architecture, React State & Rendering Performance",
            "API Design, HTTP Protocol & Data Contracts",
            "Relational Database Modeling & Query Optimization",
            "Full-Stack Security, Authentication & Session Invariants",
            "End-to-End System Integration & Observability",
        ],
        "competencies": [
            {
                "identifier": "fullstack_api_and_data_contracts",
                "name": "Full-Stack API Architecture & Data Contracts",
                "description": "Designing clean, typed client-server communication, pagination, and error representations.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["RESTful resource modeling", "idempotent methods", "pagination (cursor vs offset)", "JSON schemas & validation", "HTTP status codes"],
                "core_invariants": ["Client-side input validation is for user experience only; server-side validation is non-negotiable for security and integrity"],
                "assessment_objectives": ["Evaluate candidate's ability to design clean, consistent, and secure API boundaries."],
                "evidence_requirements": ["Explains pagination trade-offs under high insertion rates", "Defines structured error envelopes"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "frontend_state_and_rendering_performance",
                "name": "Frontend State Management & Rendering Optimization",
                "description": "Component lifecycle, state synchronization, re-render minimization, and client caching.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["React virtual DOM & reconciliation", "memoization (useMemo, useCallback)", "optimistic UI updates", "server state caching (React Query)", "bundle splitting"],
                "core_invariants": ["State mutations must be immutable to ensure predictable component re-rendering and prevent subtle lifecycle bugs"],
                "assessment_objectives": ["Assess candidate's ability to debug unnecessary renders and optimize web performance."],
                "evidence_requirements": ["Explains causes and remedies for cascading re-renders", "Demonstrates optimistic UI patterns"],
                "difficulty_expectations": "medium",
                "stage_suitability": 2,
            },
            {
                "identifier": "database_modeling_and_fullstack_persistence",
                "name": "Database Schema Modeling & Full-Stack Persistence",
                "description": "Relational integrity, N+1 query prevention, indexing, and migration lifecycles.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["N+1 query problem", "eager vs lazy loading", "composite indexes & B-Trees", "database migrations & zero downtime", "transactions & ACID"],
                "core_invariants": ["Foreign key constraints and database transactions protect data integrity regardless of application-level bugs"],
                "assessment_objectives": ["Assess data modeling and backend query optimization under production read/write loads."],
                "evidence_requirements": ["Identifies and resolves N+1 query bottlenecks in ORM code", "Designs indexes aligned with query predicates"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "fullstack_security_and_incident_resolution",
                "name": "Full-Stack Security, Authentication & Production Incidents",
                "description": "Mitigating XSS, CSRF, SQL injection, JWT vs session auth, and debugging production regressions.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["JWT vs HttpOnly session cookies", "CORS policy configuration", "CSRF protection", "XSS sanitization", "rate limiting"],
                "core_invariants": ["Sensitive access tokens must never be stored in browser localStorage due to direct exposure to XSS"],
                "assessment_objectives": ["Assess defensive security engineering and structured root-cause analysis during live outages."],
                "evidence_requirements": ["Justifies HttpOnly cookie storage for session tokens", "Explains debugging methodology for CORS errors"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "fullstack_star_ownership_and_delivery",
                "name": "Full-Stack Product Ownership & STAR Leadership",
                "description": "Balancing technical debt against product deadlines, cross-functional collaboration, and feature ownership.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["STAR framework", "technical debt communication", "scrum/agile delivery", "cross-functional collaboration"],
                "core_invariants": ["Delivering complex full-stack features requires clear incremental milestones and automated regression tests"],
                "assessment_objectives": ["Evaluate communication, accountability, and engineering maturity."],
                "evidence_requirements": ["Structures compelling STAR response showcasing end-to-end feature delivery and impact"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
    "frontend_developer": {
        "display_name": "Frontend Developer",
        "aliases": [
            "frontend developer", "frontend engineer", "front end developer", "front end engineer",
            "ui engineer", "ui developer", "client engineer", "react developer", "web frontend developer",
            "web developer frontend", "frontend software engineer", "client side engineer"
        ],
        "description": "Specialized client-side engineering role designing performant web applications, accessible user experiences (WCAG 2.2 AA), predictable state architectures, and resilient Core Web Vitals.",
        "responsibilities": [
            "Build responsive, accessible, component-driven user interfaces using modern client frameworks (React, TypeScript)",
            "Optimize browser rendering performance, bundle size, and Core Web Vitals (INP, LCP, CLS)",
            "Design unidirectional client state management and resilient asynchronous data synchronization with optimistic UI",
            "Enforce web accessibility standards (WCAG 2.2 AA), keyboard navigation, and DOM security (DOM XSS prevention, CSP)",
            "Implement automated unit, component, and visual regression tests across varying devices and viewports",
        ],
        "knowledge_areas": [
            "Component Architecture, Virtual DOM & State Invariants",
            "Web Performance, Rendering Pipeline & Core Web Vitals",
            "Client Data Fetching, Cache Invalidation & Optimistic UI",
            "Accessible DOM Architecture (WCAG 2.2 AA) & Frontend Security",
            "Browser Storage, Service Workers & Offline Synchronization",
            "Component Testing, Visual Regression & Cross-Functional Delivery",
        ],
        "competencies": [
            {
                "identifier": "frontend_architecture_and_component_state",
                "name": "Component Architecture, State Boundaries & Lifecycle Invariants",
                "description": "Component lifecycle, state synchronization, re-render minimization, immutability, and predictable state machines.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["React virtual DOM & reconciliation", "immutability", "unidirectional data flow", "prop drilling vs context API", "state machine modeling", "custom hooks"],
                "core_invariants": ["State mutations must be immutable and unidirectional to prevent unpredictable re-render cascades"],
                "assessment_objectives": ["Assess candidate's ability to architect scalable component hierarchies and eliminate redundant re-renders."],
                "evidence_requirements": ["Explains virtual DOM reconciliation algorithm and reasons about immutable state updates"],
                "difficulty_expectations": "medium",
                "stage_suitability": 1,
            },
            {
                "identifier": "web_performance_and_core_vitals",
                "name": "Web Performance, Rendering Pipeline & Core Web Vitals",
                "description": "Main-thread task scheduling, critical rendering path, code splitting, tree shaking, and Core Web Vitals optimization.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["INP (Interaction to Next Paint)", "LCP (Largest Contentful Paint)", "CLS (Cumulative Layout Shift)", "code splitting & tree-shaking", "critical rendering path", "long tasks & yield to main"],
                "core_invariants": ["Main thread long-tasks (>50ms) must be chunked or yielded to keep INP within target budgets (<200ms)"],
                "assessment_objectives": ["Evaluate mastery of browser layout engines, performance profiling, and Web Vitals remediation."],
                "evidence_requirements": ["Diagnoses layout shifts (CLS) and structures async chunking with scheduler.yield() or requestIdleCallback"],
                "difficulty_expectations": "hard",
                "stage_suitability": 2,
            },
            {
                "identifier": "asynchronous_data_and_client_caching",
                "name": "Client Data Fetching, Stale-While-Revalidate & Optimistic UI",
                "description": "Server-state caching, cache invalidation keys, race condition cancellation, and optimistic UI rollback patterns.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["TanStack Query / SWR", "cache invalidation keys", "optimistic rollback", "race condition mitigation (AbortController)", "network offline retry", "request deduplication"],
                "core_invariants": ["Concurrent network requests must support AbortController cancellation to eliminate out-of-order response overwrites"],
                "assessment_objectives": ["Determine candidate's ability to synchronize remote state with optimistic client caches cleanly."],
                "evidence_requirements": ["Implements optimistic updates with snapshot rollback and cancels stale fetch promises via AbortSignal"],
                "difficulty_expectations": "hard",
                "stage_suitability": 3,
            },
            {
                "identifier": "dom_accessibility_and_security",
                "name": "Accessible DOM Architecture (WCAG 2.2 AA) & Frontend Security",
                "description": "WCAG 2.2 AA accessibility, semantic HTML, ARIA patterns, focus management, DOM XSS sanitization, and CSP.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["WCAG 2.2 AA compliance", "ARIA live regions & roles", "keyboard focus traps", "DOM XSS prevention", "Content Security Policy (CSP)", "DOMPurify sanitization"],
                "core_invariants": ["Interactive custom widgets must maintain keyboard focus trap and semantic ARIA announcements for screen readers"],
                "assessment_objectives": ["Assess accessibility engineering rigor and defensive DOM security practices."],
                "evidence_requirements": ["Structures accessible modal focus loop and demonstrates secure HTML sanitization against XSS"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "browser_networking_and_offline_storage",
                "name": "Browser Storage, Service Workers & Offline Synchronization",
                "description": "IndexedDB transactions, Service Worker lifecycle, CacheStorage API, background sync, and storage quota management.",
                "importance": CompetencyImportance.CORE,
                "role_relationship": "primary",
                "expected_concepts": ["IndexedDB transactions", "CacheStorage API", "Service Worker lifecycle", "offline background sync", "storage quotas", "atomic cache migration"],
                "core_invariants": ["Service worker cache updates must be atomic to prevent asset version skew across chunked bundle files"],
                "assessment_objectives": ["Assess progressive web application (PWA) resilience, offline persistence, and service worker mechanics."],
                "evidence_requirements": ["Architects offline-first mutation queue in IndexedDB with replay on network restoration"],
                "difficulty_expectations": "hard",
                "stage_suitability": 4,
            },
            {
                "identifier": "frontend_testing_and_star_leadership",
                "name": "Component Testing, Visual Regression & Cross-Functional Delivery",
                "description": "Component behavior testing, visual snapshot regression, design system token governance, and cross-functional leadership.",
                "importance": CompetencyImportance.CROSS_FUNCTIONAL,
                "role_relationship": "cross_functional",
                "expected_concepts": ["React Testing Library (RTL)", "Vitest / Jest", "Playwright visual regression", "design system tokens", "user-centric accessibility queries", "STAR leadership"],
                "core_invariants": ["Automated component tests must assert user-facing accessibility semantics rather than internal component state"],
                "assessment_objectives": ["Evaluate frontend testing strategy, design-system governance, and cross-functional engineering communication."],
                "evidence_requirements": ["Writes robust RTL assertions using accessible role queries and articulates design-engineering trade-offs"],
                "difficulty_expectations": "medium",
                "stage_suitability": 5,
            },
        ],
    },
}


class RoleIntelligenceService:
    """
    Core service for deterministic role resolution, multi-role synthesis,
    custom role interpretation, and role competency blueprint construction.
    """

    @classmethod
    def normalize_role_text(cls, role_text: str) -> str:
        """
        Normalizes role strings cleanly into canonical registry keys.
        Handles variations, casing, punctuation, and common synonyms.
        """
        if not role_text:
            return "universal_software_engineering"

        cleaned = role_text.strip().lower()
        cleaned = re.sub(r"[^a-z0-9\s/_-]", "", cleaned)
        cleaned = re.sub(r"[\s/_-]+", " ", cleaned).strip()

        # Check known aliases
        for reg_key, profile_data in CURATED_ROLE_PROFILES.items():
            if cleaned == reg_key or cleaned == profile_data["display_name"].lower():
                return reg_key
            for alias in profile_data["aliases"]:
                if cleaned == alias.lower():
                    return reg_key

        # Substring / keyword fuzzy matching
        if "embedding" in cleaned or "vector" in cleaned:
            return "embedding_systems_engineer"
        if ("database" in cleaned and ("reliability" in cleaned or "sre" in cleaned or "distributed" in cleaned)) or ("distributed" in cleaned and ("system" in cleaned or "architect" in cleaned or "engineer" in cleaned or "storage" in cleaned)):
            return "distributed_database_reliability_engineer"
        if "data science" in cleaned or "data scientist" in cleaned or "ai data science" in cleaned or "artificial intelligence and data science" in cleaned or "ai & ds" in cleaned or "ai&ds" in cleaned or cleaned in ("ai engineer", "artificial intelligence engineer"):
            return "ai_data_science_engineer"
        if "machine learning" in cleaned or cleaned.startswith("ml ") or cleaned.endswith(" ml") or cleaned == "ml":
            return "machine_learning_engineer"
        if "embedded" in cleaned or "firmware" in cleaned or "microcontroller" in cleaned or "robotics" in cleaned:
            return "embedded_systems_engineer"
        if "frontend" in cleaned or "front end" in cleaned or "front-end" in cleaned or "ui engineer" in cleaned or "ui developer" in cleaned or "client engineer" in cleaned or "react developer" in cleaned:
            return "frontend_developer"
        if "full stack" in cleaned or "fullstack" in cleaned or "full-stack" in cleaned or "web developer" in cleaned:
            return "full_stack_software_engineer"
        if "devops" in cleaned or "sre" in cleaned or "reliability engineer" in cleaned or "cloud" in cleaned:
            return "cloud_devops_sre"
        if "backend" in cleaned:
            return "backend_systems_engineer"
        if "omnirole" in cleaned or "universal" in cleaned or "software engineer" in cleaned:
            return "universal_software_engineering"

        # Slugify unknown text safely
        slug = re.sub(r"\s+", "_", cleaned)
        return slug or "universal_software_engineering"

    @classmethod
    async def research_role(
        cls,
        spec: RoleResearchSpecification,
        force_refresh: bool = False,
    ) -> RoleProfile:
        """
        Executes dynamic web research on a selected target role using provider-independent search.
        Discovers real responsibilities, industry expectations, dynamic competencies,
        failure scenarios, and interview rubrics with full source provenance.
        """
        if force_refresh:
            spec.force_refresh = True
        engine = RoleResearchEngine()
        return await engine.research_role(spec)

    @classmethod
    def resolve_role_profile(
        cls,
        spec: RoleSpecification,
    ) -> RoleProfile:
        """
        Resolves a RoleSpecification into a structured RoleProfile.
        Priority:
        1. Validated Web Research Cache (Dynamic Role Intelligence)
        2. Known Curated Registry
        3. Custom Role with User Description
        4. Deterministic Safe Fallback
        """
        # Step 1: Check if dynamic web research exists in cache for this role
        research_spec = RoleResearchSpecification(
            role_name=spec.role_name,
            experience_level=spec.seniority,
        )
        cache_key = _ROLE_CACHE.compute_cache_key(research_spec)
        cached_profile, _ = _ROLE_CACHE.get(cache_key, allow_stale=True)
        if cached_profile:
            return cached_profile

        norm_key = cls.normalize_role_text(spec.role_name)

        if norm_key in CURATED_ROLE_PROFILES:
            raw = CURATED_ROLE_PROFILES[norm_key]
            return RoleProfile(
                role_name=raw["display_name"],
                normalized_role_name=norm_key,
                aliases=raw.get("aliases", []),
                role_description=raw.get("description", ""),
                responsibilities=raw.get("responsibilities", []),
                common_tasks=raw.get("responsibilities", []),
                knowledge_areas=raw.get("knowledge_areas", []),
                technical_skills=[c["name"] for c in raw.get("competencies", [])],
                tools_and_technologies=[],
                competencies=[c["identifier"] for c in raw.get("competencies", [])],
                seniority_expectations={"baseline": spec.seniority or "Mid-Senior"},
                evidence_sources=["Curated Internal Role Registry"],
                provenance=RoleProvenance.CURATED,
            )

        # Custom role with user-provided description
        if spec.custom_role_description and spec.custom_role_description.strip():
            desc = spec.custom_role_description.strip()
            sentences = [s.strip() for s in desc.split(".") if len(s.strip()) > 10]
            knowledge_areas = sentences[:4] if sentences else ["Core Domain Engineering"]
            return RoleProfile(
                role_name=spec.role_name.strip(),
                normalized_role_name=norm_key,
                aliases=[spec.role_name.strip()],
                role_description=desc,
                responsibilities=sentences,
                common_tasks=sentences,
                knowledge_areas=knowledge_areas,
                technical_skills=[f"{spec.role_name} Fundamentals"],
                tools_and_technologies=[],
                competencies=[f"{norm_key}_core_mechanics"],
                seniority_expectations={"baseline": spec.seniority or "Mid"},
                evidence_sources=["User-Provided Role Specification"],
                provenance=RoleProvenance.USER_PROVIDED,
            )

        # Fallback safe profile
        universal = CURATED_ROLE_PROFILES["universal_software_engineering"]
        return RoleProfile(
            role_name=spec.role_name.strip() or universal["display_name"],
            normalized_role_name=norm_key,
            aliases=[spec.role_name.strip()],
            role_description=f"Specialized software engineering role: {spec.role_name}. Evaluated through core engineering competencies.",
            responsibilities=universal.get("responsibilities", []),
            common_tasks=universal.get("responsibilities", []),
            knowledge_areas=universal.get("knowledge_areas", []),
            technical_skills=[c["name"] for c in universal.get("competencies", [])],
            tools_and_technologies=[],
            competencies=[c["identifier"] for c in universal.get("competencies", [])],
            seniority_expectations={"baseline": spec.seniority or "Mid"},
            evidence_sources=["Safe Engineering Fallback"],
            provenance=RoleProvenance.FALLBACK,
        )

    @classmethod
    def build_competency_blueprint(
        cls,
        spec: RoleSpecification,
    ) -> RoleCompetencyBlueprint:
        """
        Builds the complete RoleCompetencyBlueprint translating the role specification
        into testable competencies mapped across the 5 interview stages.
        Supports dynamic web-researched competencies (>5), single role and multi-role synthesis.
        """
        all_roles = spec.get_all_roles()

        if len(all_roles) <= 1:
            return cls._build_single_role_blueprint(spec)

        return cls._build_multi_role_blueprint(spec, all_roles)

    @classmethod
    def _build_single_role_blueprint(cls, spec: RoleSpecification) -> RoleCompetencyBlueprint:
        profile = cls.resolve_role_profile(spec)
        norm_key = profile.normalized_role_name

        competencies: List[RoleCompetency] = []
        stage_suitability: Dict[int, List[str]] = {1: [], 2: [], 3: [], 4: [], 5: []}

        # Case 1: Dynamic Web-Researched Profile
        if profile.provenance == RoleProvenance.RESEARCHED:
            from ai.interview_engine.role_research_engine import CuratedRoleKnowledgeSearchProvider
            corpus = CuratedRoleKnowledgeSearchProvider.AUTHORITATIVE_ROLE_CORPUS
            matched_key = next((k for k in corpus if k in norm_key), None)
            if not matched_key:
                if "frontend" in norm_key or "ui" in norm_key:
                    matched_key = "frontend"
                elif "embedded" in norm_key or "firmware" in norm_key:
                    matched_key = "embedded"
                elif "machine_learning" in norm_key or "ml" in norm_key or "ai" in norm_key:
                    matched_key = "machine_learning"
                elif "security" in norm_key:
                    matched_key = "security"
                elif "distributed" in norm_key:
                    matched_key = "distributed"
                else:
                    matched_key = "backend"
            raw_comps = corpus.get(matched_key, corpus.get("backend", {}))["competencies"]

            for rc in raw_comps:
                comp = RoleCompetency(
                    identifier=rc["identifier"],
                    name=rc["name"],
                    description=f"Mastery of {rc['name']} within the context of {profile.role_name}.",
                    category=rc.get("category", "software_engineering"),
                    importance=rc.get("importance", CompetencyImportance.CORE),
                    requirement_classification=rc.get("classification", RequirementClassification.REQUIRED),
                    expected_proficiency=rc.get("expected_proficiency", "Senior"),
                    role_relationship=rc.get("role_relationship", "primary"),
                    expected_concepts=rc.get("expected_concepts", []),
                    core_invariants=rc.get("core_invariants", []),
                    assessment_objectives=[f"Assess candidate's ability to reason about {rc['name']}."],
                    evidence_requirements=[f"Candidate demonstrates operational understanding of {rc['expected_concepts'][0]}"],
                    difficulty_expectations=rc.get("difficulty", "medium"),
                    stage_suitability=rc.get("stage", 1),
                    provenance=RoleProvenance.RESEARCHED,
                )
                competencies.append(comp)
                stg = rc.get("stage", 1)
                stage_suitability[stg].append(comp.identifier)

        # Case 2: Curated Baseline Role Registry
        elif norm_key in CURATED_ROLE_PROFILES:
            raw_comps = CURATED_ROLE_PROFILES[norm_key]["competencies"]
            for rc in raw_comps:
                comp = RoleCompetency(
                    identifier=rc["identifier"],
                    name=rc["name"],
                    description=rc["description"],
                    importance=rc.get("importance", CompetencyImportance.CORE),
                    role_relationship=rc.get("role_relationship", "primary"),
                    expected_concepts=rc.get("expected_concepts", []),
                    core_invariants=rc.get("core_invariants", []),
                    assessment_objectives=rc.get("assessment_objectives", []),
                    evidence_requirements=rc.get("evidence_requirements", []),
                    difficulty_expectations=rc.get("difficulty_expectations", "medium"),
                    provenance=profile.provenance,
                )
                competencies.append(comp)
                stg = rc.get("stage_suitability", 1)
                stage_suitability[stg].append(comp.identifier)

        # Case 3: Custom Role with User Description
        elif profile.provenance == RoleProvenance.USER_PROVIDED:
            competencies, stage_suitability = cls._synthesize_custom_competencies(profile, spec)

        # Case 4: Safe Universal Engineering Fallback
        else:
            raw_comps = CURATED_ROLE_PROFILES["universal_software_engineering"]["competencies"]
            for rc in raw_comps:
                comp = RoleCompetency(
                    identifier=rc["identifier"],
                    name=rc["name"],
                    description=rc["description"],
                    importance=rc.get("importance", CompetencyImportance.CORE),
                    role_relationship=rc.get("role_relationship", "primary"),
                    expected_concepts=rc.get("expected_concepts", []),
                    core_invariants=rc.get("core_invariants", []),
                    assessment_objectives=rc.get("assessment_objectives", []),
                    evidence_requirements=rc.get("evidence_requirements", []),
                    difficulty_expectations=rc.get("difficulty_expectations", "medium"),
                    provenance=RoleProvenance.FALLBACK,
                )
                competencies.append(comp)
                stg = rc.get("stage_suitability", 1)
                stage_suitability[stg].append(comp.identifier)

        return RoleCompetencyBlueprint(
            role_name=profile.role_name,
            normalized_role_name=profile.normalized_role_name,
            competencies=competencies,
            stage_suitability=stage_suitability,
            common_competencies=[c.identifier for c in competencies if c.importance == CompetencyImportance.CROSS_FUNCTIONAL],
            role_specific_competencies={profile.role_name: [c.identifier for c in competencies if c.importance != CompetencyImportance.CROSS_FUNCTIONAL]},
            provenance=profile.provenance,
        )

    @classmethod
    def _build_multi_role_blueprint(
        cls,
        spec: RoleSpecification,
        all_roles: List[str],
    ) -> RoleCompetencyBlueprint:
        """
        Synthesizes multiple target roles into a unified blueprint separating
        common foundational/architectural competencies from role-specific competencies.
        """
        individual_blueprints = [
            cls._build_single_role_blueprint(RoleSpecification(role_name=r, seniority=spec.seniority))
            for r in all_roles
        ]

        combined_competencies: Dict[str, RoleCompetency] = {}
        common_comp_ids: List[str] = []
        role_specific_map: Dict[str, List[str]] = {}
        stage_suitability: Dict[int, List[str]] = {1: [], 2: [], 3: [], 4: [], 5: []}

        # Track competency presence across roles
        comp_appearance_count: Dict[str, int] = {}
        for bp in individual_blueprints:
            role_specific_map[bp.role_name] = []
            for comp in bp.competencies:
                comp_appearance_count[comp.identifier] = comp_appearance_count.get(comp.identifier, 0) + 1
                combined_competencies[comp.identifier] = comp

        total_roles = len(individual_blueprints)

        # Classify as common vs role-specific
        for bp in individual_blueprints:
            for comp in bp.competencies:
                c_id = comp.identifier
                if comp_appearance_count[c_id] > 1 or comp.importance == CompetencyImportance.CROSS_FUNCTIONAL:
                    if c_id not in common_comp_ids:
                        common_comp_ids.append(c_id)
                else:
                    if c_id not in role_specific_map[bp.role_name]:
                        role_specific_map[bp.role_name].append(c_id)

        # Merge stage suitability: ensure each stage has representative competencies from common and specific sets
        for stage_idx in range(1, 6):
            for bp in individual_blueprints:
                for c_id in bp.stage_suitability.get(stage_idx, []):
                    if c_id not in stage_suitability[stage_idx]:
                        stage_suitability[stage_idx].append(c_id)

        joined_name = " + ".join([bp.role_name for bp in individual_blueprints])
        norm_name = "_and_".join([bp.normalized_role_name for bp in individual_blueprints])

        return RoleCompetencyBlueprint(
            role_name=joined_name,
            normalized_role_name=norm_name,
            competencies=list(combined_competencies.values()),
            stage_suitability=stage_suitability,
            common_competencies=common_comp_ids,
            role_specific_competencies=role_specific_map,
            provenance=RoleProvenance.CURATED if all(bp.provenance == RoleProvenance.CURATED for bp in individual_blueprints) else RoleProvenance.RESEARCHED,
        )

    @classmethod
    def _synthesize_custom_competencies(
        cls,
        profile: RoleProfile,
        spec: RoleSpecification,
    ) -> Tuple[List[RoleCompetency], Dict[int, List[str]]]:
        """
        Synthesizes structured 5-stage competencies when candidate provides a custom role description.
        """
        role_title = profile.role_name
        norm = profile.normalized_role_name
        desc = profile.role_description or ""

        # Extract domain invariants or keywords
        words = [w for w in re.split(r"[\s,;]+", desc) if len(w) > 4][:10]
        keywords = words or [norm, "architecture", "scalability", "resilience"]

        c1 = RoleCompetency(
            identifier=f"{norm}_stage1_foundations",
            name=f"{role_title} Orientation & Domain Foundations",
            description=f"Foundational concepts and principles in {role_title}.",
            importance=CompetencyImportance.CORE,
            expected_concepts=[keywords[0] if len(keywords) > 0 else "domain fundamentals", "core definitions"],
            core_invariants=[f"Core operational invariants in {role_title}"],
            assessment_objectives=[f"Verify baseline fluency in {role_title} fundamentals."],
            evidence_requirements=["Accurately defines domain concepts and scope"],
            stage_suitability=1,
            provenance=RoleProvenance.USER_PROVIDED,
        )

        c2 = RoleCompetency(
            identifier=f"{norm}_stage2_mechanics",
            name=f"{role_title} Engineering & Algorithmic Mechanics",
            description=f"Core algorithms, data flow, and internal mechanics for {role_title}.",
            importance=CompetencyImportance.CORE,
            expected_concepts=[keywords[1] if len(keywords) > 1 else "algorithmic mechanics", "data structures"],
            core_invariants=["Efficiency and algorithmic invariant preservation"],
            assessment_objectives=[f"Examine candidate's technical depth in {role_title} mechanics."],
            evidence_requirements=["Articulates step-by-step processing mechanics"],
            stage_suitability=2,
            provenance=RoleProvenance.USER_PROVIDED,
        )

        c3 = RoleCompetency(
            identifier=f"{norm}_stage3_systems",
            name=f"{role_title} Scalable Systems & Trade-offs",
            description=f"System architecture, scaling, latency, and throughput in {role_title}.",
            importance=CompetencyImportance.CORE,
            expected_concepts=[keywords[2] if len(keywords) > 2 else "distributed systems", "concurrency", "trade-offs"],
            core_invariants=["Scalability constraints and resource boundaries"],
            assessment_objectives=[f"Assess architectural trade-off reasoning in {role_title}."],
            evidence_requirements=["Defends architectural choices under load"],
            stage_suitability=3,
            provenance=RoleProvenance.USER_PROVIDED,
        )

        c4 = RoleCompetency(
            identifier=f"{norm}_stage4_debugging",
            name=f"{role_title} Failure Invariants & Debugging",
            description=f"Debugging failure modes, data corruption, and edge-case incidents in {role_title}.",
            importance=CompetencyImportance.CORE,
            expected_concepts=[keywords[3] if len(keywords) > 3 else "failure modes", "resilience", "debugging"],
            core_invariants=["Fault isolation and invariant recovery"],
            assessment_objectives=[f"Test troubleshooting and incident remediation in {role_title}."],
            evidence_requirements=["Diagnoses edge-case failure and provides remediation"],
            stage_suitability=4,
            provenance=RoleProvenance.USER_PROVIDED,
        )

        c5 = RoleCompetency(
            identifier=f"{norm}_stage5_ownership",
            name=f"{role_title} Cross-Functional Ownership & Trade-offs",
            description=f"Operational leadership, stakeholder communication, and cost/quality trade-offs.",
            importance=CompetencyImportance.CROSS_FUNCTIONAL,
            expected_concepts=["STAR framework", "trade-off communication", "stakeholder alignment"],
            core_invariants=["Aligning technical execution with business outcomes"],
            assessment_objectives=[f"Evaluate executive presence and communication in {role_title}."],
            evidence_requirements=["Demonstrates ownership and structured communication"],
            stage_suitability=5,
            provenance=RoleProvenance.USER_PROVIDED,
        )

        comps = [c1, c2, c3, c4, c5]
        suitability = {1: [c1.identifier], 2: [c2.identifier], 3: [c3.identifier], 4: [c4.identifier], 5: [c5.identifier]}
        return comps, suitability
