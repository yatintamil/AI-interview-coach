"""
Personalized Roadmap and Skill Gap Application Service.
Coordinates Role Intelligence, Skill Gap Engine, Candidate Skill States,
Roadmap Persistence, and Transfer Coaching Loop bridges.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.orm.attributes import flag_modified

from backend.models.candidate import CandidateModel
from backend.models.roadmap import PersonalizedRoadmapModel, RoadmapItemModel
from backend.models.skill_state import CandidateSkillStateModel

from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository
from backend.repositories.roadmap_repository import RoadmapRepository
from backend.repositories.interview_repository import InterviewSessionRepository

from backend.domain.role.models import RoleSpecification, CompetencyImportance
from ai.interview_engine.role_intelligence import RoleIntelligenceService
from backend.domain.transfer.skill_mapping import (
    normalize_skill,
    extract_core_invariants,
    CANONICAL_SKILLS,
    clean_competency_display_name,
    get_prerequisites_for_skill,
    get_skill_tier,
    topological_prerequisite_sort,
)
from ai.coaching_orchestrator.schemas import TrainingContext, CoachingSessionConfig
from backend.services.transfer_coaching_service import TransferCoachingService

from backend.domain.roadmap.models import (
    SkillGapPriority,
    RoadmapItemStatus,
    RoadmapStatus,
    SkillGapDTO,
    SkillGapAnalysisResult,
    RoadmapItemDTO,
    PersonalizedRoadmapDTO,
    GenerateRoadmapRequest,
    StartCoachingFromRoadmapResponse,
    VALID_SENIORITY_TIERS,
)
from ai.skill_gap_engine.engine import SkillGapEngine
from ai.skill_gap_engine.constants import MAX_SATISFIED_ADI

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE & COMPETENCY DOMAIN-SPECIFIC ACTIONABLE IMPLEMENTATION CHALLENGES
# ============================================================================

COMPETENCY_IMPLEMENTATION_CATALOG: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Backend Systems Engineer
    # -------------------------------------------------------------------------
    "backend_api_and_concurrency": {
        "title": "Distributed Idempotency & Rate Limiting Engine",
        "description": (
            "Design and implement a high-throughput API gateway middleware that enforces strict request idempotency "
            "via Redis atomic locks and a token bucket rate limiter. Eliminate race conditions and event loop starvation under burst load."
        ),
        "technology_stack": ["Python / FastAPI", "Redis (Redlock)", "Docker", "Pytest-Asyncio / Locust"],
        "acceptance_criteria": [
            "Strict idempotency verification across concurrent duplicate POST requests using idempotent client tokens.",
            "Zero duplicate database records or state mutations under a 5,000 req/s concurrent load test.",
            "Sub-15ms p99 latency overhead for idempotency check and lock release on cache hits.",
            "Deterministic recovery and lock release within 200ms following simulated worker crash.",
        ],
        "deliverables": [
            "FastAPI idempotency and rate limiting middleware package with Redis distributed lock engine.",
            "Concurrency test harness with Locust simulating network packet retransmissions and double-submits.",
            "Architecture Decision Record (ADR) analyzing lease durations, TTL expiration, and lock release safety.",
        ],
        "topics": [
            "ASGI concurrency model and asyncio non-blocking event loop execution",
            "Redis distributed locking (SETNX with TTL) and Redlock lease renewal semantics",
            "Token bucket and leaky bucket rate limiting algorithms under distributed state",
            "HTTP idempotency standards (RFC 7395 / IETF Idempotency-Key draft)",
        ],
        "exercises": [
            "Implement an idempotency interceptor handling concurrently fired identical requests with mutex locking.",
            "Simulate a Redis network timeout during lock acquisition and assert graceful fail-safe behavior.",
            "Benchmark endpoint latency under 10k req/s burst load to detect event loop starvation.",
        ],
        "evaluation_criteria": [
            "Invariant adherence: Guarantee that non-idempotent mutations cannot be executed twice.",
            "Resource bounds: Zero connection pool exhaustion or unhandled lock retention.",
            "Transfer independence: Ability to diagnose and resolve lock lease expirations without hints.",
        ],
    },
    "relational_integrity_and_indexing": {
        "title": "ACID Transaction Isolation & Composite Index Optimization",
        "description": (
            "Architect a high-volume transactional ledger service using PostgreSQL. Eliminate sequential table scans "
            "using covering composite B-Tree indexes adhering to the left-prefix rule, configure transaction isolation, and eliminate deadlocks."
        ),
        "technology_stack": ["PostgreSQL 16", "SQLAlchemy 2.0 / asyncpg", "Alembic", "pg_stat_statements"],
        "acceptance_criteria": [
            "100% elimination of sequential scans on high-traffic queries using EXPLAIN (ANALYZE, BUFFERS).",
            "Deterministic resolution of serialization anomalies under concurrent balance transfers.",
            "Zero deadlock crashes during 1,000 concurrent transactional operations through consistent lock ordering.",
            "Idempotent Alembic migration script establishing covering composite indexes with zero downtime.",
        ],
        "deliverables": [
            "PostgreSQL schema migration script with optimized B-Tree and covering composite indexes.",
            "Transaction manager implementation with optimistic retry logic for serialization failures.",
            "Query optimization report demonstrating p99 latency drop with EXPLAIN ANALYZE traces before and after.",
        ],
        "topics": [
            "PostgreSQL MVCC (Multi-Version Concurrency Control) storage engine and vacuum mechanics",
            "Transaction isolation levels: Read Committed vs Repeatable Read vs Serializable anomalies",
            "B-Tree index structure, composite index left-prefix matching, and Index-Only Scans",
            "Deadlock detection graphs and multi-resource lock acquisition hierarchies",
        ],
        "exercises": [
            "Analyze query plans using EXPLAIN (ANALYZE, BUFFERS) and refactor slow queries into Index-Only Scans.",
            "Simulate concurrent financial debit/credit operations to trigger and eliminate deadlock graphs.",
            "Implement optimistic locking with row versioning and backoff retry for hot records.",
        ],
        "evaluation_criteria": [
            "Correctness: Absolute preservation of ACID transaction invariants under concurrent execution.",
            "Query plan efficiency: Verification of minimal buffer hits and elimination of filter operations.",
            "Architectural explanation: Defending index trade-offs regarding write amplification.",
        ],
    },
    "distributed_caching_and_messaging": {
        "title": "Resilient Cache-Aside Layer with Thundering Herd Protection",
        "description": (
            "Architect a distributed caching subsystem with Redis and Kafka/RabbitMQ. Implement request coalescing "
            "(Singleflight pattern), randomized TTL jitter, and stale-while-revalidate background refresh to prevent cache stampedes."
        ),
        "technology_stack": ["Redis Cluster", "Kafka / aiokafka", "FastAPI / Python", "Prometheus"],
        "acceptance_criteria": [
            "Simultaneous expiration of a hot cache key under 2,000 req/s causes exactly ONE database query via Singleflight coalescing.",
            "Randomized TTL jitter distribution prevents correlated bulk cache expirations.",
            "Message consumer guarantees at-least-once delivery with zero duplicate state mutations via consumer idempotency.",
            "Graceful fallback to stale cache or degraded response if Redis becomes temporarily unreachable.",
        ],
        "deliverables": [
            "Singleflight request coalescing cache client library with TTL jitter and stale-while-revalidate.",
            "Idempotent Kafka consumer with transactional outbox or deduplication store.",
            "Benchmark dashboard measuring cache hit ratio and database query suppression under stampede load.",
        ],
        "topics": [
            "Cache-aside vs Write-through vs Write-behind architectural trade-offs",
            "Cache stampede (thundering herd) mechanics and singleflight request deduplication",
            "TTL jitter and probabilistic early expiration (XFetch algorithm) for proactive refreshing",
            "Kafka partition ordering, consumer group offset commits, and consumer-side deduplication",
        ],
        "exercises": [
            "Build a singleflight cache wrapper that collapses concurrent duplicate misses into a single database fetch.",
            "Simulate simultaneous expiration of 10,000 keys and demonstrate stable database connection usage.",
            "Construct an idempotent Kafka event consumer processing duplicate and out-of-order events.",
        ],
        "evaluation_criteria": [
            "Stampede containment: Database query rate remains completely bounded during key invalidation bursts.",
            "Consumer safety: Idempotency keys prevent duplicate business processing on consumer retries.",
            "Operational insight: Explaining latency-consistency trade-offs between cache invalidation strategies.",
        ],
    },
    "system_resilience_and_debugging": {
        "title": "Distributed Circuit Breaker & Cascade Outage Mitigation",
        "description": (
            "Design an adaptive circuit breaker and bulkhead isolation library. Implement sliding-window failure rate tracking, "
            "half-open probe requests, exponential backoff retries with full jitter, and fallback degradation strategies."
        ),
        "technology_stack": ["Python / Asyncio", "FastAPI", "Chaos / Fault Injection", "Prometheus"],
        "acceptance_criteria": [
            "Circuit transitions from Closed to Open within 3 consecutive failure bursts or 50% failure rate in window.",
            "Fast-fail response time < 5ms when circuit state is Open, avoiding upstream thread starvation.",
            "Caller connection pools retain >= 50% capacity during sustained downstream service outage.",
            "Automatic half-open probing and seamless recovery when downstream health is restored.",
        ],
        "deliverables": [
            "Asynchronous circuit breaker decorator with sliding-window error rate tracking and bulkhead limits.",
            "Chaos engineering test suite simulating network partitions, latency spikes, and 500 errors.",
            "Production incident postmortem runbook detailing circuit tripping thresholds and alert policies.",
        ],
        "topics": [
            "Circuit breaker state machine (Closed, Open, Half-Open) and transition triggers",
            "Bulkhead pool isolation to prevent cascading resource starvation across endpoints",
            "Exponential backoff with full jitter algorithms (decorrelated jitter) to avoid retry storms",
            "Graceful degradation patterns: Static fallbacks, cached responses, and partial data returns",
        ],
        "exercises": [
            "Inject 500ms network delays and verify circuit trips without exhausting caller connection pools.",
            "Validate half-open probe rate limiting and automatic circuit closure upon consecutive successes.",
            "Implement bulkhead concurrency quotas separating mission-critical routes from auxiliary endpoints.",
        ],
        "evaluation_criteria": [
            "Fault containment: Downstream latency spikes are completely isolated within 3 failure cycles.",
            "Resource preservation: Caller memory and connection headroom remain stable under dependency crash.",
            "Root-cause diagnostic rigor: Explaining failure cascade mechanisms in distributed systems.",
        ],
    },
    "observability_and_star_ownership": {
        "title": "Distributed Tracing, p99 Latency SLOs & Telemetry Pipeline",
        "description": (
            "Integrate OpenTelemetry instrumentation across asynchronous services. Establish distributed trace context propagation, "
            "emit high-cardinality metric histograms, and configure alerts on p99 and p99.9 tail latency error budgets."
        ),
        "technology_stack": ["OpenTelemetry SDK", "Jaeger", "Prometheus", "Grafana"],
        "acceptance_criteria": [
            "100% trace context propagation (W3C TraceContext) across HTTP and asynchronous message boundaries.",
            "Structured JSON logging enriched with active trace_id and span_id for instant correlation.",
            "Prometheus histogram alerts triggering on p99 latency SLO burn rate degradation.",
            "Comprehensive blameless retrospective document for a simulated critical production incident.",
        ],
        "deliverables": [
            "OpenTelemetry instrumentation package with Jaeger and Prometheus exporters.",
            "Grafana RED (Rate, Errors, Duration) metrics dashboard with p95/p99 latency distribution panels.",
            "Blameless postmortem document analyzing root cause, contributing factors, and systemic remediations.",
        ],
        "topics": [
            "OpenTelemetry span hierarchies, baggage, and W3C TraceContext distributed propagation",
            "Tail latency mathematics: Why averages deceive and why p99/p99.9 govern user experience",
            "SLIs (Service Level Indicators), SLOs, and Error Budget burn rate alert strategies",
            "Blameless engineering postmortem methodology and cross-team incident retrospectives",
        ],
        "exercises": [
            "Instrument end-to-end distributed trace propagation across 3 microservices communicating via HTTP and queues.",
            "Configure Prometheus recording rules calculating p99 latency from exponential histogram buckets.",
            "Author a detailed incident postmortem analyzing a cascading timeout outage with preventive action items.",
        ],
        "evaluation_criteria": [
            "Observability completeness: Traces clearly highlight latency bottlenecks across service hops.",
            "Metric validity: Histogram bucket configurations accurately capture tail latency without distortion.",
            "Executive communication: Ability to articulate complex system failures clearly to stakeholders.",
        ],
    },

    # -------------------------------------------------------------------------
    # Machine Learning Engineer
    # -------------------------------------------------------------------------
    "feature_pipelines_and_leakage": {
        "title": "Point-in-Time Correct Feature Pipeline & Leakage Guard",
        "description": (
            "Build a point-in-time correct feature engineering pipeline using Polars or DuckDB. Guarantee zero train-serve skew "
            "and eliminate future information leakage during historical joins. Implement automated feature validation checks."
        ),
        "technology_stack": ["Python", "Polars / DuckDB", "Feast Feature Store", "Pytest"],
        "acceptance_criteria": [
            "Point-in-time correct as-of joins guarantee that inference features reflect only historical data prior to prediction event.",
            "100% detection and blocking of lookahead leakage in synthetic backtest validation datasets.",
            "Automated parity verification between offline training features and online low-latency feature cache.",
            "Sub-10ms feature retrieval latency from online key-value store for serving inference.",
        ],
        "deliverables": [
            "Point-in-time feature transformation pipeline with temporal as-of join logic.",
            "Automated test suite verifying data leakage prevention across event-driven datasets.",
            "Architecture Decision Record (ADR) on online/offline feature parity and synchronization.",
        ],
        "topics": [
            "Point-in-time correctness and as-of temporal join mechanics in feature engineering",
            "Train-serve skew root causes: Timestamp drifts, data leakage, and divergent transformations",
            "Feature store architecture: Offline analytics store vs online low-latency key-value cache",
            "Automated data quality assertions and statistical validation tests",
        ],
        "exercises": [
            "Implement an as-of join pipeline in Polars joining user events with historical feature state.",
            "Simulate lookahead bias in a backtest and construct assertions that catch timestamp anomalies.",
            "Benchmark online feature lookup latency under concurrent prediction workloads.",
        ],
        "evaluation_criteria": [
            "Temporal rigor: Zero exposure of future information to model training frames.",
            "Transformation parity: Identical feature values generated across batch and real-time paths.",
            "Scalability: Feature pipeline executes with linear memory complexity without OOM failures.",
        ],
    },
    "model_evaluation_and_loss_invariants": {
        "title": "Imbalanced Classification & Metric Calibration Engine",
        "description": (
            "Develop a comprehensive evaluation harness for production ML models under severe class imbalance. "
            "Implement Precision-Recall AUC analysis, Brier score probability calibration, and cost-weighted loss optimization."
        ),
        "technology_stack": ["Python", "Scikit-Learn", "PyTorch / LightGBM", "Matplotlib / SciPy"],
        "acceptance_criteria": [
            "Selection and implementation of PR-AUC and cost-weighted utility metrics over misleading ROC-AUC for imbalanced data.",
            "Probability calibration via Platt scaling or isotonic regression reducing Brier score by >= 25%.",
            "Optimal decision threshold tuning balancing business false-positive costs against false-negative impact.",
            "Automated calibration curve generation and reliability diagram validation.",
        ],
        "deliverables": [
            "Production evaluation pipeline calculating calibrated probabilities, PR curves, and Brier metrics.",
            "Probability calibration module with isotonic regression and temperature scaling.",
            "Evaluation report comparing baseline vs calibrated predictions across stratified minority cohorts.",
        ],
        "topics": [
            "Metric selection under severe class imbalance (PR-AUC vs ROC-AUC mathematical trade-offs)",
            "Probability calibration techniques: Platt scaling, Isotonic regression, and Temperature scaling",
            "Brier score decomposition: Reliability, resolution, and uncertainty",
            "Cost-sensitive learning and asymmetric loss formulation for real-world business impact",
        ],
        "exercises": [
            "Evaluate an imbalanced dataset (99:1 ratio) and demonstrate how ROC-AUC masks high false-positive rates.",
            "Fit a calibration layer on an overconfident neural network and evaluate reliability curves.",
            "Optimize decision threshold given concrete dollar costs for false alarms vs missed detections.",
        ],
        "evaluation_criteria": [
            "Statistical rigor: Defending metric selection based on business cost matrices.",
            "Calibration validity: Calibrated probabilities reflect true empirical event frequencies.",
            "Transfer independence: Ability to explain calibration drift across shifting test cohorts.",
        ],
    },
    "model_serving_and_latency_optimization": {
        "title": "High-Throughput Model Serving with Dynamic Batching & Quantization",
        "description": (
            "Deploy a production model serving microservice using Triton Inference Server or FastAPI with ONNX Runtime. "
            "Implement adaptive dynamic batching, INT8 weight quantization, and enforce a sub-50ms p99 latency SLA."
        ),
        "technology_stack": ["Triton Inference Server / FastAPI", "PyTorch / ONNX Runtime", "TensorRT", "Locust"],
        "acceptance_criteria": [
            "Dynamic batching algorithm coalesces incoming requests up to max batch size within a 10ms timeout window.",
            "INT8/FP16 post-training quantization achieves >= 2.5x throughput improvement with < 1% accuracy degradation.",
            "Strict sub-50ms p99 inference latency under sustained 1,000 req/s concurrent workload.",
            "Zero GPU memory leakage or worker crashes during continuous 1-hour load test.",
        ],
        "deliverables": [
            "Containerized model serving service with dynamic batching and ONNX Runtime execution engine.",
            "Quantization script converting FP32 model weights to INT8 with calibration dataset.",
            "Load test benchmark report detailing throughput (req/s), GPU utilization, and p99 latency distribution.",
        ],
        "topics": [
            "Dynamic batching trade-offs: Latency inflation vs throughput maximization on GPU/CPU",
            "Post-training quantization (PTQ) and quantization-aware training (QAT) mechanics",
            "ONNX Runtime graph optimizations, kernel fusions, and TensorRT acceleration",
            "GPU memory management, pinned host memory, and asynchronous CUDA stream execution",
        ],
        "exercises": [
            "Configure a dynamic batching queue and measure latency vs batch size trade-off curve.",
            "Convert a Transformer / CNN model to ONNX INT8 and benchmark speedup on CPU/GPU.",
            "Simulate concurrent traffic spikes to identify memory allocation bottlenecks.",
        ],
        "evaluation_criteria": [
            "Latency compliance: Strict adherence to sub-50ms p99 SLA under high request volumes.",
            "Resource efficiency: Optimal GPU compute utilization without memory thrashing.",
            "Architectural defense: Explaining quantization trade-offs regarding numerical precision.",
        ],
    },
    "ml_drift_debugging_and_fallback": {
        "title": "Real-Time Feature Drift Detector & Safe Fallback Router",
        "description": (
            "Construct an automated covariate shift and prediction drift detection engine using Kolmogorov-Smirnov "
            "and Population Stability Index (PSI) tests. Configure shadow deployment routing and rule-based fallback."
        ),
        "technology_stack": ["Evidently AI / SciPy", "FastAPI", "Redis", "Prometheus"],
        "acceptance_criteria": [
            "Real-time statistical drift detection triggering alerts when PSI > 0.20 or KS p-value < 0.01.",
            "Automated circuit-breaking and fallback routing to heuristic rules when extreme drift is detected.",
            "Shadow deployment harness comparing online model predictions against candidate models in real time.",
            "Zero downtime switchover during fallback policy activation.",
        ],
        "deliverables": [
            "Drift monitoring service computing KS-test, PSI, and Jensen-Shannon divergence over streaming features.",
            "Fallback router routing traffic to rule heuristics or cached ensemble upon drift detection.",
            "Runbook defining operational triage steps for sudden data pipeline corruption.",
        ],
        "topics": [
            "Covariate shift vs concept drift vs prior probability shift mathematical definitions",
            "Statistical distance metrics: Kolmogorov-Smirnov test, Population Stability Index (PSI), Wasserstein distance",
            "Shadow deployment and canary release strategies for production ML models",
            "Safe fallback architectures: Fallback heuristics, ensemble overrides, and human-in-the-loop triggers",
        ],
        "exercises": [
            "Inject synthetic covariate shift into an input feature stream and assert drift detection within 100 samples.",
            "Implement a router that automatically triggers fallback responses when feature distribution shifts.",
            "Build a Prometheus exporter tracking real-time feature divergence metrics.",
        ],
        "evaluation_criteria": [
            "Statistical sensitivity: Detecting genuine distribution shifts while minimizing false positive alerts.",
            "System safety: Seamless fallback execution without dropping user requests or returning corrupted outputs.",
            "Operational readiness: Comprehensive triage protocol for production drift incidents.",
        ],
    },
    "cross_functional_ml_governance": {
        "title": "Model ROI, Cloud GPU Cost Profiler & Governance Framework",
        "description": (
            "Develop a comprehensive model governance framework analyzing cloud inference compute costs per 1M predictions "
            "against business revenue uplift. Formulate model cards, latency-cost Pareto frontiers, and fairness guardrails."
        ),
        "technology_stack": ["Python", "Prometheus / Cost Metrics", "Markdown / Model Cards", "Fairlearn"],
        "acceptance_criteria": [
            "Quantitative Pareto frontier analysis comparing model accuracy gains against incremental cloud GPU dollar costs.",
            "Comprehensive Model Card documenting intended use, limitations, data lineage, and evaluation metrics.",
            "Subgroup demographic parity and disparate impact ratio analysis ensuring compliance with ethical standards.",
            "Executive presentation pitch justifying ML infrastructure budget based on validated business ROI.",
        ],
        "deliverables": [
            "Cost-benefit calculator model estimating inference infrastructure cost per 1M users.",
            "Standardized production Model Card documentation template for enterprise governance.",
            "Fairness and ethical audit report analyzing demographic subgroups across prediction cohorts.",
        ],
        "topics": [
            "ML system unit economics: Cost per prediction, cloud GPU reservation models, and amortization",
            "Model card standards (Mitchell et al.) for model transparency and regulatory compliance",
            "Fairness metrics: Equalized odds, demographic parity, and disparate impact analysis",
            "Cross-functional stakeholder communication: Bridging data science metrics to business KPIs",
        ],
        "exercises": [
            "Construct a cost-performance trade-off curve across model architecture variants (e.g., 7B vs 1.5B parameters).",
            "Conduct a bias audit on a credit or hiring dataset using disparity metrics.",
            "Draft an executive briefing defending why a slightly less accurate model is preferred due to cost boundaries.",
        ],
        "evaluation_criteria": [
            "Economic rigor: Clear mathematical linkage between ML metrics and business bottom line.",
            "Governance maturity: Thorough risk documentation covering ethics, data privacy, and failure boundaries.",
            "Cross-functional leadership: Explaining technical compromises in terms of organizational risk.",
        ],
    },

    # -------------------------------------------------------------------------
    # Embedded Systems Engineer
    # -------------------------------------------------------------------------
    "embedded_firmware_and_concurrency": {
        "title": "Bare-Metal Interrupt-Safe State Machine & Ring Buffer",
        "description": (
            "Implement a lock-free circular ring buffer and cooperative event scheduler in C/C++ for an ARM Cortex-M MCU. "
            "Guarantee atomic volatile register access, zero ISR priority inversions, and bounded interrupt latency under 100kHz tick rate."
        ),
        "technology_stack": ["C / C++ (C11/C++17)", "ARM Cortex-M (QEMU / STM32)", "GDB / Valgrind", "FreeRTOS"],
        "acceptance_criteria": [
            "Lock-free single-producer single-consumer circular buffer with volatile atomic index updates.",
            "Zero race conditions or data corruption between interrupt service routines (ISRs) and main loop.",
            "Interrupt service routine execution time guaranteed < 5 microseconds at 100kHz input frequency.",
            "Formal state machine transition table with static assertion of all valid states and transitions.",
        ],
        "deliverables": [
            "Interrupt-safe lock-free circular buffer library in MISRA-C compliant C.",
            "Cooperative event-driven scheduler with static priority-based task dispatch.",
            "QEMU simulation test suite validating atomic transfers under high-frequency simulated interrupts.",
        ],
        "topics": [
            "ARM Cortex-M NVIC (Nested Vectored Interrupt Controller) priority grouping and preemption",
            "Volatile keyword semantics, compiler optimization barriers, and memory synchronization instructions (DMB, DSB, ISB)",
            "Lock-free circular buffer algorithms for single-producer single-consumer concurrency",
            "Interrupt latency minimization and deferred interrupt servicing patterns",
        ],
        "exercises": [
            "Implement a lock-free ring buffer transferring bytes between UART ISR and user processing thread.",
            "Simulate nested interrupt preemption to verify absence of priority inversion or stack corruption.",
            "Measure interrupt execution cycle counts using ARM DWT cycle counter registers.",
        ],
        "evaluation_criteria": [
            "Concurrency correctness: Zero shared data mutation without explicit critical section or atomic barrier.",
            "Timing determinism: Strict adherence to bounded execution time in all interrupt handlers.",
            "Code safety: Elimination of undefined behavior, memory leaks, or unhandled hardware flags.",
        ],
    },
    "hardware_interfacing_and_timing": {
        "title": "SPI/I2C Device Driver with Non-Blocking DMA Transfers",
        "description": (
            "Write a bare-metal peripheral device driver for an SPI/I2C sensor with DMA transfer offloading. "
            "Enforce bus clock timing constraints, implement bus arbitration, and handle clock stretching without CPU spinning."
        ),
        "technology_stack": ["C", "ARM Cortex-M HAL / Register-Level", "Logic Analyzer / Sigrok", "GDB"],
        "acceptance_criteria": [
            "Non-blocking peripheral transfers offloaded completely to Direct Memory Access (DMA) controller.",
            "Zero CPU busy-wait spinning during peripheral transfer windows, allowing MCU sleep entry.",
            "Robust timeout and bus recovery protocol handling I2C bus lockup and clock stretching within 10ms.",
            "Strict adherence to SPI setup, hold, and clock phase/polarity (CPOL/CPHA) timing specifications.",
        ],
        "deliverables": [
            "Register-level SPI and I2C driver package with non-blocking DMA transfer callbacks.",
            "I2C bus recovery routine generating manual clock pulses to free stuck slave devices.",
            "Timing analysis report verifying waveform alignment with logic analyzer captures.",
        ],
        "topics": [
            "SPI protocol mechanics: CPOL/CPHA modes, chip select timing, and multi-slave topologies",
            "I2C protocol internals: START/STOP conditions, ACK/NACK bit sequences, arbitration, and clock stretching",
            "DMA (Direct Memory Access) channel configuration, circular buffer modes, and transfer complete interrupts",
            "Hardware timing budgets, rise/fall times, and pull-up resistor calculation",
        ],
        "exercises": [
            "Write an SPI DMA transfer routine reading sensor FIFO registers without blocking main execution.",
            "Implement a bus clear algorithm that toggles SCL 9 times to recover from a stuck SDA low line.",
            "Inspect and decode I2C protocol packets using logic analyzer traces to diagnose timing violations.",
        ],
        "evaluation_criteria": [
            "Non-blocking architecture: Main CPU thread remains free during peripheral transfer durations.",
            "Fault resilience: Automatic bus reset when peripheral disconnects or fails to acknowledge.",
            "Hardware protocol fidelity: Exact compliance with protocol electrical and timing specifications.",
        ],
    },
    "memory_constrained_systems": {
        "title": "Zero-Heap Static Memory Allocator & Stack Watermark Profiler",
        "description": (
            "Design a deterministic fixed-block memory allocator with zero dynamic heap allocation for an MCU with 32KB RAM. "
            "Implement stack paint watermarking to detect stack overflow and guarantee zero dynamic heap fragmentation."
        ),
        "technology_stack": ["C", "GCC ARM Embedded Toolchain", "Linker Scripts (.ld)", "GDB"],
        "acceptance_criteria": [
            "100% elimination of dynamic malloc/free calls in firmware codebase (zero heap fragmentation).",
            "Fixed-block memory pool allocator with deterministic O(1) allocation and deallocation time.",
            "Stack watermarking pattern (0xA5A5A5A5) detecting stack headroom and catching overflows before corruption.",
            "Custom linker script defining explicit memory sections (.bss, .data, .stack, .firmware_pool).",
        ],
        "deliverables": [
            "Fixed-size block memory pool library with compile-time bounded static storage.",
            "Stack watermarking profiler logging runtime minimum stack headroom across all tasks.",
            "Custom GNU ld linker script with static memory boundary assertions.",
        ],
        "topics": [
            "Dynamic memory allocation pitfalls in mission-critical embedded systems (heap fragmentation, nondeterminism)",
            "Fixed-block memory pool (slab) allocation algorithms and free-list management",
            "Stack memory layout, activation records, and stack overflow corruption vectors",
            "Linker script syntax: Memory regions, section placements, and symbol export",
        ],
        "exercises": [
            "Implement a fixed-block slab allocator managing a pre-allocated static byte array.",
            "Paint the stack with a known pattern during system boot and read high-water mark during stress execution.",
            "Configure a linker script assertion that triggers a compile-time error if static RAM exceeds 80% capacity.",
        ],
        "evaluation_criteria": [
            "Determinism: Guaranteed constant-time memory allocation with zero fragmentation risk.",
            "Stack safety: Real-time visibility into stack margins and prevention of buffer overruns.",
            "Resource discipline: Exact utilization accounting of every byte of available RAM.",
        ],
    },
    "hardware_fault_containment": {
        "title": "Hardware Watchdog & Brownout Recovery Subsystem",
        "description": (
            "Configure a multi-stage hardware watchdog timer (WDT) and Brown-Out Detection (BOD) peripheral handler. "
            "Implement crash dump logging into non-volatile FRAM/Flash and verify deterministic reboot recovery within 50ms."
        ),
        "technology_stack": ["C", "Hardware Watchdog Peripheral", "Internal Flash / FRAM Driver", "JTAG / OpenOCD"],
        "acceptance_criteria": [
            "Independent Hardware Watchdog (IWDG) windowed refresh requires proof of main thread and task loop liveness.",
            "Brownout Detection (BOD) interrupt handler triggers emergency state save into non-volatile memory before power drops.",
            "Post-reboot diagnostic analyzer identifies reboot cause register flags (PIN, POR, IWDG, WWDG, BOR).",
            "System restores safe operational state within 50ms of power recovery.",
        ],
        "deliverables": [
            "Multi-task watchdog supervision module checking task heartbeats before kicking hardware watchdog.",
            "Emergency power-loss interrupt handler writing critical state registers to non-volatile flash.",
            "Bootloader reset reason triage logger outputting human-readable reset telemetry.",
        ],
        "topics": [
            "Independent Watchdog (IWDG) vs Windowed Watchdog (WWDG) operating principles",
            "Brownout Detection (BOD) and Power-On Reset (POR) voltage monitoring peripherals",
            "Non-volatile memory endurance, page write timing, and atomic state snapshotting",
            "Failsafe state machines and graceful reboot recovery in safety-critical hardware",
        ],
        "exercises": [
            "Simulate a task freeze and verify that watchdog timer forces a clean microcontroller reset.",
            "Trigger a simulated brownout voltage drop and capture the emergency state preservation write in GDB.",
            "Inspect MCU reset cause registers during startup and branch to appropriate recovery workflows.",
        ],
        "evaluation_criteria": [
            "Failsafe reliability: System recovers automatically from any software hang without external power cycling.",
            "Data integrity: Zero corruption of persistent flash state during sudden power loss.",
            "Diagnostic transparency: Boot telemetry accurately logs exact cause of every reboot event.",
        ],
    },
    "cross_functional_embedded_lifecycle": {
        "title": "HW/SW Co-Design, Thermal Budgeting & Production Test Harness",
        "description": (
            "Formulate a hardware/software co-design specification addressing power consumption states (Active, Sleep, Standby), "
            "thermal dissipation limits, and an automated Hardware-in-the-Loop (HIL) test script for manufacturing line validation."
        ),
        "technology_stack": ["Python (PySerial / PyVISA)", "Power Profiling Hardware / DMM", "Automated HIL Rig", "Markdown"],
        "acceptance_criteria": [
            "Power state machine transitions reducing idle current consumption to < 10 microamps in deep sleep.",
            "Automated Python test harness executing 50 functional hardware tests via serial commands in < 2 minutes.",
            "Thermal dissipation model verifying MCU temperature remains < 65°C under maximum sustained processing load.",
            "Hardware/software interface contract detailing GPIO pinmux assignments, voltage levels, and BOM constraints.",
        ],
        "deliverables": [
            "Automated Hardware-in-the-Loop (HIL) test harness executing automated manufacturing validation.",
            "Power budget spreadsheet and measurement analysis across active, sleep, and standby operational modes.",
            "Hardware-software interface control document (ICD) with pinout definitions and electrical boundaries.",
        ],
        "topics": [
            "Ultra-low-power sleep modes: Stop, Standby, Shutdown, and wake-up timer configurations",
            "Automated test equipment (ATE) and Hardware-in-the-Loop (HIL) manufacturing verification",
            "Thermal design power (TDP), junction temperature limits, and thermal throttling in embedded systems",
            "Cross-functional collaboration with electrical engineering, board layout, and firmware teams",
        ],
        "exercises": [
            "Measure current consumption across sleep states using a digital multimeter or power profiler.",
            "Write an automated Python test script verifying board peripheral bringup and reporting PASS/FAIL status.",
            "Draft an Interface Control Document (ICD) defining electrical specifications and communication protocols.",
        ],
        "evaluation_criteria": [
            "Energy efficiency: Validated current consumption adheres strictly to battery life requirements.",
            "Test automation: Manufacturing test script reliably catches hardware assembly defects.",
            "Cross-disciplinary clarity: Specifications bridge electrical engineering constraints with software architecture.",
        ],
    },

    # -------------------------------------------------------------------------
    # Frontend Developer
    # -------------------------------------------------------------------------
    "frontend_architecture_and_component_state": {
        "title": "Normalized Client State Engine with Unidirectional Mutation Isolation",
        "description": (
            "Architect a robust client-side state engine using React 19, TypeScript, and Zustand. "
            "Eliminate cascading re-render loops through normalized state slices, immutable update patterns, "
            "and predictable state machine boundaries."
        ),
        "technology_stack": ["React 19", "TypeScript", "Zustand", "Vite", "React Profiler"],
        "acceptance_criteria": [
            "Zero redundant re-renders of un-subscribed sibling components validated via React DevTools Profiler.",
            "Strict unidirectional data flow with 100% typed actions and runtime invariant assertions.",
            "Normalized relational client state avoiding multi-source synchronization anomalies.",
            "Sub-16ms frame budget preservation during rapid consecutive UI interactions.",
        ],
        "deliverables": [
            "Modular typed state slice package with custom selector hooks.",
            "Automated unit test suite verifying state transition determinism under race conditions.",
            "React Profiler flamegraph report proving elimination of unnecessary component renders.",
        ],
        "topics": [
            "Virtual DOM diffing algorithms, reconciliation keys, and fiber architecture",
            "Normalized client state modeling vs deeply nested object anti-patterns",
            "Predictable state machine patterns (XState / Zustand) for complex async UI flows",
            "React Compiler and automatic memoization mechanics",
        ],
        "exercises": [
            "Refactor a heavily prop-drilled dashboard into isolated Zustand atomic state slices.",
            "Construct an automated test asserting that mutating slice A never triggers renders in component B.",
            "Profile a table containing 1,000 items and eliminate synchronous rendering bottlenecks.",
        ],
        "evaluation_criteria": [
            "Architectural purity: Absolute adherence to unidirectional, immutable data mutation.",
            "Rendering efficiency: Proven isolation of component render boundaries under stress.",
            "Type safety: Zero use of 'any' types in state definitions and action contracts.",
        ],
    },
    "web_performance_and_core_vitals": {
        "title": "Main-Thread Task Scheduling & Core Web Vitals (INP/LCP/CLS) Optimization",
        "description": (
            "Profile and remediate Web Vitals bottlenecks on a complex web app. Chunk main-thread execution "
            "tasks (>50ms) using modern browser scheduling APIs (scheduler.yield), eliminate layout shifts (CLS), "
            "and achieve sub-150ms Interaction to Next Paint (INP)."
        ),
        "technology_stack": ["TypeScript", "Web Vitals API", "Lighthouse CI", "Chrome DevTools Performance", "Vite Code Splitting"],
        "acceptance_criteria": [
            "Interaction to Next Paint (INP) maintained under 150ms during heavy continuous typing and filtering.",
            "Cumulative Layout Shift (CLS) reduced to < 0.05 across dynamic image and ad load sequences.",
            "Main-thread tasks exceeding 50ms chunked using scheduler.yield() or requestIdleCallback fallbacks.",
            "Bundle footprint reduced by >= 35% through route-level dynamic code splitting and tree-shaking.",
        ],
        "deliverables": [
            "Yield-to-main asynchronous scheduling utility breaking up CPU-bound operations.",
            "Lighthouse CI configuration with automated performance budget gates in build pipeline.",
            "Chrome Performance trace report detailing main thread flamechart before vs after optimization.",
        ],
        "topics": [
            "Core Web Vitals metrics: INP, LCP, CLS measurement mechanics and diagnostic thresholds",
            "Browser rendering pipeline: Recalculate Styles, Layout (Reflow), Paint, and Composite",
            "Long Tasks API and cooperative multitasking via scheduler.yield() and requestPostAnimationFrame",
            "Bundle analysis: Rollup chunking strategies, dead-code elimination, and dynamic import waterfalls",
        ],
        "exercises": [
            "Instrument the Web Vitals JavaScript library to emit real-time telemetry beacons.",
            "Chunk an expensive client-side search indexing loop into 16ms yieldable time slices.",
            "Audit bundle chunks using rollup-plugin-visualizer to eliminate duplicate vendor libraries.",
        ],
        "evaluation_criteria": [
            "Empirical performance: Verified reduction in main-thread blocking time in performance traces.",
            "Layout stability: Strict reservation of visual dimensions preventing content jumps.",
            "Engineering rigor: Deep understanding of browser layout engines and execution threads.",
        ],
    },
    "asynchronous_data_and_client_caching": {
        "title": "Resilient Stale-While-Revalidate Query Layer with Optimistic Rollback",
        "description": (
            "Build an asynchronous client data layer with TanStack Query. Implement hierarchical cache query keys, "
            "AbortController request cancellation, and instantaneous optimistic UI mutations with deterministic snapshot rollback upon server error."
        ),
        "technology_stack": ["TanStack Query v5", "TypeScript", "Mock Service Worker (MSW)", "Axios / Fetch API"],
        "acceptance_criteria": [
            "Instantaneous UI updates via onMutate snapshotting with automatic rollback upon HTTP 500 error.",
            "100% cancellation of in-flight HTTP requests via AbortSignal when user navigates away or types new query.",
            "Hierarchical cache invalidation targeting exact resource subtrees without over-fetching.",
            "Exponential backoff retry with jitter on network failure, preventing server stampede on reconnect.",
        ],
        "deliverables": [
            "Production-ready custom query and mutation hook package with typed cache key factories.",
            "MSW network failure simulation test harness verifying optimistic mutation rollback.",
            "Technical design doc explaining cache invalidation trade-offs and client memory bounds.",
        ],
        "topics": [
            "Stale-While-Revalidate caching mechanics and garbage collection (gcTime vs staleTime)",
            "Optimistic mutation patterns, cache snapshotting, and transaction rollback mechanics",
            "HTTP request cancellation using AbortController and Signal propagation",
            "Offline mutation queuing and persistent client storage synchronization",
        ],
        "exercises": [
            "Implement a live 'like/unlike' feed toggle with immediate optimistic UI update and error rollback.",
            "Build an autocomplete search component canceling prior network calls on every keystroke.",
            "Configure a query cache garbage collection strategy bounding client heap consumption.",
        ],
        "evaluation_criteria": [
            "Consistency: Client cache never desynchronizes from true server state upon error.",
            "Resource hygiene: Zero orphaned network requests or memory leaks upon component unmount.",
            "User experience: Seamless perception of zero-latency interaction with graceful error states.",
        ],
    },
    "dom_accessibility_and_security": {
        "title": "WCAG 2.2 AA Accessible Modal Dialog & DOM XSS Sanitization Filter",
        "description": (
            "Design a headless accessible modal dialogue and rich content viewer. Enforce keyboard focus trapping, "
            "Esc key dismissal with focus restoration, ARIA live region announcements, and DOMPurify sanitization preventing DOM-based XSS."
        ),
        "technology_stack": ["React", "TypeScript", "Axe-Core", "DOMPurify", "Playwright A11y", "ARIA 1.2"],
        "acceptance_criteria": [
            "Zero Axe-Core accessibility violations (100% WCAG 2.2 AA compliance).",
            "Keyboard focus trapped strictly within active modal and restored to triggering element on exit.",
            "All dynamic HTML content rendered through DOMPurify sanitization with strict allowed tags and attributes.",
            "Screen readers announce state changes via semantic aria-live, aria-expanded, and aria-modal attributes.",
        ],
        "deliverables": [
            "Accessible, headless dialog component package with keyboard navigation tests.",
            "DOMPurify sanitization utility with strict Content Security Policy (CSP) integration.",
            "Automated Playwright accessibility test suite asserting focus states and color contrast.",
        ],
        "topics": [
            "WCAG 2.2 AA standards: Color contrast, keyboard focus order, touch targets, and ARIA roles",
            "Focus management: Keyboard traps, activeElement tracking, and initial focus heuristics",
            "DOM-based Cross-Site Scripting (XSS) attack vectors and HTML sanitization mechanics",
            "Content Security Policy (CSP) directives: Nonces, hashes, and unsafe-inline elimination",
        ],
        "exercises": [
            "Build a custom modal dialog from scratch supporting Tab, Shift+Tab, and Escape key focus loops.",
            "Craft a suite of malicious XSS injection payloads and verify complete neutralization by DOMPurify.",
            "Write automated Playwright tests verifying screen-reader ARIA attribute state transitions.",
        ],
        "evaluation_criteria": [
            "Accessibility fidelity: Flawless navigation using keyboard and screen reader simulators.",
            "Security robustness: Impregnable defense against script execution in dynamic user content.",
            "Spec adherence: Exact alignment with W3C ARIA Authoring Practices Guide (APG).",
        ],
    },
    "browser_networking_and_offline_storage": {
        "title": "Offline-First Service Worker Cache & IndexedDB Event Queue",
        "description": (
            "Implement an offline-first client architecture using Service Workers and IndexedDB. "
            "Cache static application shells, queue offline data mutations in IndexedDB, and synchronize updates with the backend upon network restoration."
        ),
        "technology_stack": ["Workbox", "Service Worker API", "IndexedDB (idb)", "TypeScript", "Chrome DevTools"],
        "acceptance_criteria": [
            "Complete application shell loads and renders offline within 200ms from CacheStorage.",
            "Offline user actions persistently queued in IndexedDB transactions with guaranteed durability.",
            "Service worker updates execute atomically without asset version skew across deployed bundles.",
            "Automatic background synchronization replay of queued mutations with idempotency tokens.",
        ],
        "deliverables": [
            "Custom Service Worker package with Workbox caching strategies and skipWaiting lifecycle.",
            "IndexedDB persistent mutation queue with automatic online sync replay handler.",
            "Browser storage quota management module with LRU eviction for cached media.",
        ],
        "topics": [
            "Service Worker lifecycle: Install, activate, fetch, and client claim mechanics",
            "Caching strategies: Cache-First, Network-First, and Stale-While-Revalidate trade-offs",
            "IndexedDB transactions, object stores, and cursor-based batch processing",
            "Background Sync API, storage quota limits, and eviction policy governance",
        ],
        "exercises": [
            "Simulate full offline mode in Chrome DevTools and verify that application remains functional.",
            "Queue 10 offline edits in IndexedDB and verify they are dispatched in order upon re-connecting.",
            "Handle an atomic service worker update prompting the user to reload without broken chunk errors.",
        ],
        "evaluation_criteria": [
            "Offline resilience: Zero data loss when operations are performed without active internet connection.",
            "Cache hygiene: Clean removal of outdated cache keys during service worker activation.",
            "Architectural safety: Transactional integrity in client database operations.",
        ],
    },
    "frontend_testing_and_star_leadership": {
        "title": "Behavior-Driven Component Test Suite & Visual Regression Harness",
        "description": (
            "Build a comprehensive frontend testing harness using Vitest, React Testing Library, and Playwright. "
            "Enforce user-behavior queries (byRole, byLabelText), visual regression snapshot assertions, and author an Architecture Decision Record (ADR)."
        ),
        "technology_stack": ["Vitest", "React Testing Library (RTL)", "Playwright", "Storybook Test Runner", "TypeScript"],
        "acceptance_criteria": [
            "100% component test assertions bound to user-visible accessibility roles rather than implementation details.",
            "Visual regression test suite catching subtle layout regressions across mobile and desktop viewports.",
            "Component test suite achieving >= 90% branch coverage on complex interactive user journeys.",
            "Well-structured Architecture Decision Record (ADR) framing frontend trade-offs and tech debt.",
        ],
        "deliverables": [
            "Comprehensive RTL and Vitest component test package with custom render utilities.",
            "Playwright visual regression test suite with pixel-diff threshold assertions.",
            "Architecture Decision Record (ADR) documenting design system tokenization and component API.",
        ],
        "topics": [
            "Guiding principles of React Testing Library: Testing user behavior vs component internals",
            "Visual regression testing: Pixel-diffing, anti-aliasing tolerances, and viewport matrixes",
            "Mocking strategies: MSW network-level mocking vs fragile module mocking",
            "STAR leadership: Communicating architectural decisions, managing tech debt, and cross-team alignment",
        ],
        "exercises": [
            "Write test cases for an asynchronous form using findByRole and waitFor assertions.",
            "Configure a Playwright visual regression test and capture an intentional 2px layout shift.",
            "Draft a STAR leadership response describing the successful migration of a legacy frontend codebase.",
        ],
        "evaluation_criteria": [
            "Testing fidelity: Tests survive internal refactoring without breaking if behavior is preserved.",
            "Coverage meaningfulness: High branch coverage on critical edge cases rather than trivial snapshots.",
            "Leadership communication: Persuasive, structured reasoning on engineering trade-offs.",
        ],
    },
}

# Alias role-specific blueprint identifiers to canonical catalog challenges
COMPETENCY_IMPLEMENTATION_CATALOG.update({
    "ml_pipeline_and_feature_engineering": COMPETENCY_IMPLEMENTATION_CATALOG["feature_pipelines_and_leakage"],
    "deep_learning_training_and_optimization": COMPETENCY_IMPLEMENTATION_CATALOG["model_evaluation_and_loss_invariants"],
    "model_serving_latency_and_quantization": COMPETENCY_IMPLEMENTATION_CATALOG["model_serving_and_latency_optimization"],
    "model_drift_monitoring_and_governance": COMPETENCY_IMPLEMENTATION_CATALOG["ml_drift_debugging_and_fallback"],
    "vector_search_and_rag_systems": COMPETENCY_IMPLEMENTATION_CATALOG["feature_pipelines_and_leakage"],
    "ml_safety_ethics_and_tradeoffs": COMPETENCY_IMPLEMENTATION_CATALOG["cross_functional_ml_governance"],
    "embedded_c_and_memory_mapped_io": COMPETENCY_IMPLEMENTATION_CATALOG["embedded_firmware_and_concurrency"],
    "interrupts_and_concurrency_boundaries": COMPETENCY_IMPLEMENTATION_CATALOG["embedded_firmware_and_concurrency"],
    "peripheral_bus_protocols_and_dma": COMPETENCY_IMPLEMENTATION_CATALOG["hardware_interfacing_and_timing"],
    "fault_diagnostics_watchdogs_and_power": COMPETENCY_IMPLEMENTATION_CATALOG["hardware_fault_containment"],
    "embedded_project_ownership_and_star": COMPETENCY_IMPLEMENTATION_CATALOG["cross_functional_embedded_lifecycle"],
})


class RoadmapService:
    """
    Application Service managing the lifecycle of Skill Gap Analysis
    and Personalized Roadmaps for interview candidates.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.candidate_repo = CandidateRepository(session)
        self.skill_state_repo = CandidateSkillStateRepository(session)
        self.roadmap_repo = RoadmapRepository(session)
        self.interview_repo = InterviewSessionRepository(session)

    @classmethod
    def determine_progression_tier(
        cls,
        status: str,
        current_transfer_level: str,
        current_mastery: float,
        target_mastery: float,
        assistance_dependency: float,
    ) -> str:
        """Determines the candidate's verified evidence-based progression tier."""
        has_l5 = current_transfer_level == "L5_INDEPENDENT_TRANSFER"
        has_mastery = current_mastery >= target_mastery
        low_assistance = assistance_dependency <= MAX_SATISFIED_ADI

        if status == RoadmapItemStatus.COMPLETED.value or (has_l5 and has_mastery and low_assistance):
            return "Tier 5: L5 Independent Transfer"
        elif assistance_dependency <= 0.40 and current_transfer_level in ["L3_FAR_DOMAIN", "L4_CROSS_DOMAIN", "L5_INDEPENDENT_TRANSFER"]:
            return "Tier 4: Reduced Assistance"
        elif status != RoadmapItemStatus.NOT_STARTED.value and assistance_dependency < 0.70:
            return "Tier 3: Assisted Performance"
        elif status in [RoadmapItemStatus.IN_PROGRESS.value, RoadmapItemStatus.PRACTICING.value]:
            return "Tier 2: Currently Developing"
        else:
            return "Tier 1: Assessed, Needs Practice"

    @classmethod
    def synthesize_actionable_milestone_details(
        cls,
        skill_id: str,
        clean_title: str,
        is_flagged: bool,
        seniority: str,
        invariants: List[str],
        target_role: str,
        status: str,
        current_transfer_level: str,
        current_mastery: float,
        target_mastery: float,
        assistance_dependency: float,
    ) -> Dict[str, Any]:
        """Synthesizes rich, role-specific actionable tasks, exercises, deliverables, and criteria."""
        tier = get_skill_tier(skill_id)
        primary_inv = invariants[0] if invariants else "Structural correctness and state boundary consistency"
        secondary_inv = invariants[1] if len(invariants) > 1 else primary_inv

        diff_map = {
            1: "FOUNDATIONAL",
            2: "INTERMEDIATE",
            3: "INTERMEDIATE",
            4: "ADVANCED",
            5: "EXPERT",
        }
        difficulty = diff_map.get(tier, "INTERMEDIATE")
        duration = "1-2 weeks" if tier <= 2 else ("2 weeks" if tier == 3 else "2-3 weeks")

        # Check domain-specific competency implementation catalog
        cat_entry = COMPETENCY_IMPLEMENTATION_CATALOG.get(skill_id)
        if not cat_entry:
            for cat_k, cat_v in COMPETENCY_IMPLEMENTATION_CATALOG.items():
                if cat_k in skill_id or skill_id in cat_k:
                    cat_entry = cat_v
                    break

        if cat_entry:
            implementation_task = {
                "title": cat_entry["title"],
                "description": cat_entry["description"],
                "technology_stack": cat_entry["technology_stack"],
                "acceptance_criteria": cat_entry["acceptance_criteria"],
            }
            deliverables = list(cat_entry["deliverables"])
            topics = list(cat_entry["topics"])
            exercises = list(cat_entry["exercises"])
            eval_criteria = list(cat_entry["evaluation_criteria"])
        else:
            role_lower = (target_role or "").lower()
            if "frontend" in role_lower or "ui" in role_lower or "react" in role_lower or "client" in role_lower:
                tech_stack = ["TypeScript", "React", "Vite", "Web Vitals API", "Vitest / RTL"]
                implementation_task = {
                    "title": f"Frontend Engineering Challenge: {clean_title} Architecture & Verification",
                    "description": (
                        f"As a {seniority} {target_role}, design and implement a responsive client module for {clean_title}. "
                        f"Your implementation must enforce the primary invariant: '{primary_inv}', "
                        f"eliminate redundant re-render cascades, and maintain Core Web Vitals (INP < 150ms)."
                    ),
                    "technology_stack": tech_stack,
                    "acceptance_criteria": [
                        f"Strict runtime enforcement of invariant: '{primary_inv}'.",
                        "Zero unhandled UI runtime exceptions or unexpected layout shifts (CLS < 0.05).",
                        "Interaction to Next Paint (INP) maintained under 150ms during continuous user interaction.",
                        "Automated component test suite achieving >= 85% branch coverage with accessible role queries.",
                    ],
                }
                deliverables = [
                    f"Modular client component package for {clean_title} with strict TypeScript types.",
                    "Automated test suite using React Testing Library validating accessible user behaviors.",
                    f"Technical design doc (ADR) detailing rendering trade-offs and Web Vitals for {target_role}.",
                ]
                topics = [
                    f"Core foundations of {clean_title}: Component architecture and state boundaries",
                    f"Enforcing '{primary_inv}' during client state transitions and re-renders",
                    "Rendering pipeline optimization, code splitting, and Core Web Vitals",
                ]
                exercises = [
                    f"Design and execute component tests verifying '{primary_inv}'.",
                    f"Profile user interactions in {clean_title} to eliminate main-thread bottlenecks.",
                    "Benchmark render cycle durations and bundle chunk sizes across desktop and mobile viewports.",
                ]
                eval_criteria = [
                    f"Invariant adherence: Explicit verification of '{primary_inv}'.",
                    "User experience fidelity: Accessible, responsive interface with sub-100ms response time.",
                    "Client architectural hygiene: Predictable state updates and zero memory leaks upon unmount.",
                ]
            elif "embedded" in role_lower or "firmware" in role_lower or "microcontroller" in role_lower:
                tech_stack = ["C / C++", "ARM Cortex-M Toolchain", "GDB", "Valgrind", "Logic Analyzer"]
                implementation_task = {
                    "title": f"Embedded Systems Challenge: {clean_title} Firmware & Timing Verification",
                    "description": (
                        f"As a {seniority} {target_role}, develop a deterministic, resource-bounded firmware module for {clean_title}. "
                        f"Enforce the primary invariant: '{primary_inv}', eliminate dynamic heap allocations, and guarantee bounded interrupt timing."
                    ),
                    "technology_stack": tech_stack,
                    "acceptance_criteria": [
                        f"Strict runtime enforcement of invariant: '{primary_inv}'.",
                        "100% elimination of dynamic malloc/free calls in firmware routines.",
                        "Deterministic interrupt and peripheral timing adhering to hardware specifications.",
                        "Automated unit test harnesses achieving >= 85% coverage in simulated QEMU/GDB environments.",
                    ],
                }
                deliverables = [
                    f"Register-level firmware module for {clean_title} with static memory boundaries.",
                    "Hardware timing verification test script with logic analyzer waveform assertions.",
                    f"Technical documentation detailing clock budgets, power states, and memory maps for {target_role}.",
                ]
                topics = [
                    f"Core foundations of {clean_title}: Hardware registers, timing, and memory constraints",
                    f"Enforcing '{primary_inv}' under real-time interrupts and peripheral bus activity",
                    "Deterministic state machines, fault containment, and watchdog timer governance",
                ]
                exercises = [
                    f"Implement test assertions in C verifying '{primary_inv}'.",
                    f"Measure interrupt latency and execution cycles for {clean_title} using cycle counter registers.",
                    "Simulate hardware fault conditions to verify graceful containment and safe recovery.",
                ]
                eval_criteria = [
                    f"Invariant adherence: Explicit verification of '{primary_inv}'.",
                    "Determinism: Guaranteed execution bounds and elimination of race conditions.",
                    "Hardware safety: Zero risk of stack overflow, memory corruption, or bus lockup.",
                ]
            elif "machine_learning" in role_lower or "ml" in role_lower or "ai" in role_lower:
                tech_stack = ["Python", "PyTorch / Scikit-Learn", "FastAPI / Triton", "Pytest"]
                implementation_task = {
                    "title": f"Machine Learning Challenge: {clean_title} Pipeline & Invariant Guard",
                    "description": (
                        f"As a {seniority} {target_role}, design and implement a production-grade ML pipeline module for {clean_title}. "
                        f"Your implementation must enforce the primary invariant: '{primary_inv}', "
                        f"prevent data leakage, and ensure calibrated model performance under production distribution shifts."
                    ),
                    "technology_stack": tech_stack,
                    "acceptance_criteria": [
                        f"Strict runtime enforcement of invariant: '{primary_inv}'.",
                        "Zero temporal lookahead leakage during feature generation or historical joins.",
                        "Automated probability calibration and metric validation under class imbalance.",
                        "Sub-20ms inference latency at p95 under concurrent prediction workloads.",
                    ],
                }
                deliverables = [
                    f"Production ML pipeline package for {clean_title} with automated validation checks.",
                    "Evaluation harness calculating calibrated probabilities, PR curves, and drift metrics.",
                    f"Architecture Decision Record (ADR) detailing model trade-offs and latency budgets for {target_role}.",
                ]
                topics = [
                    f"Core foundations of {clean_title}: Feature hygiene, loss dynamics, and model serving",
                    f"Enforcing '{primary_inv}' during offline training and online inference",
                    "Statistical drift detection, model calibration, and fallback governance",
                ]
                exercises = [
                    f"Construct test assertions verifying '{primary_inv}'.",
                    f"Inject synthetic distribution drift to verify automated alert triggers in {clean_title}.",
                    "Benchmark model serving throughput across varying batch sizes and device targets.",
                ]
                eval_criteria = [
                    f"Invariant adherence: Explicit verification of '{primary_inv}'.",
                    "Statistical rigor: Proven prevention of data leakage and sound evaluation metrics.",
                    "Production readiness: Clean modular code with low latency and automated regression tests.",
                ]
            else:
                tech_stack = ["Python / Go", "PostgreSQL / Redis", "Docker", "Pytest / k6"]
                if "caching" in skill_id or "consensus" in skill_id:
                    tech_stack = ["Redis / Memcached", "Go / Python", "Distributed Locks", "Prometheus"]
                elif "database" in skill_id or "concurrency" in skill_id or "sql" in skill_id:
                    tech_stack = ["PostgreSQL", "SQLAlchemy / asyncpg", "Alembic", "JMeter"]
                elif "vector" in skill_id or "embedding" in skill_id:
                    tech_stack = ["Qdrant / Milvus / pgvector", "PyTorch / Transformers", "FastAPI", "Locust"]

                implementation_task = {
                    "title": f"Backend Engineering Challenge: {clean_title} Architecture & Verification",
                    "description": (
                        f"As a {seniority} {target_role}, design and implement an end-to-end production module for {clean_title}. "
                        f"Your implementation must enforce the primary invariant: '{primary_inv}', "
                        f"contain error cascades under concurrent load, and demonstrate deterministic recovery."
                    ),
                    "technology_stack": tech_stack,
                    "acceptance_criteria": [
                        f"Strict runtime enforcement of invariant: '{primary_inv}'.",
                        "Zero unhandled exception cascades or state corruption under concurrent peak traffic.",
                        "Deterministic failure containment and self-healing recovery within 500ms of fault injection.",
                        "Automated test suite achieving >= 85% branch coverage with edge-case regression harnesses.",
                    ],
                }
                deliverables = [
                    f"Modular, production-ready implementation package for {clean_title}.",
                    "Automated test suite with fault-injection harnesses validating core invariants.",
                    f"Technical design doc (ADR) detailing latency vs consistency trade-offs for {target_role}.",
                ]
                topics = [
                    f"Core foundations of {clean_title}: Invariant boundaries and trade-offs",
                    f"Enforcing '{primary_inv}' under concurrent and distributed workloads",
                    f"Failure containment: Mitigating cascading degradation and latency spikes",
                ]
                exercises = [
                    f"Design and execute test assertions verifying '{primary_inv}'.",
                    f"Simulate a partial network partition or burst concurrency to expose race conditions in {clean_title}.",
                    "Benchmark latency and memory consumption across varying load distributions.",
                ]
                eval_criteria = [
                    f"Invariant adherence: Explicit verification of '{primary_inv}' and '{secondary_inv}'.",
                    "Transfer independence: Ability to explain and remediate unseen production failures without hints.",
                    "Architectural rigor: Clean separation of concerns, robust error handling, and bounded resource use.",
                ]

        evidence_req = (
            f"Demonstrated unassisted resolution of a transfer problem on {clean_title} during AI Coaching, "
            f"achieving an evaluation score >= 80% with Assistance Dependency Index (ADI) <= 0.25."
        )

        prog_tier = cls.determine_progression_tier(
            status=status,
            current_transfer_level=current_transfer_level,
            current_mastery=current_mastery,
            target_mastery=target_mastery,
            assistance_dependency=assistance_dependency,
        )

        return {
            "topics_to_study": topics,
            "practical_exercises": exercises,
            "implementation_task": implementation_task,
            "expected_deliverables": deliverables,
            "estimated_duration": duration,
            "difficulty_level": difficulty,
            "evaluation_criteria": eval_criteria,
            "evidence_required": evidence_req,
            "prerequisite_milestone_ids": get_prerequisites_for_skill(skill_id),
            "mapping_status": "REVIEW_FLAGGED" if is_flagged else "MAPPED",
            "is_flagged_for_review": is_flagged,
            "progression_tier": prog_tier,
        }

    async def calculate_gaps(
        self,
        candidate_id: str,
        target_role: str,
        seniority: str = "Mid",
    ) -> SkillGapAnalysisResult:
        """
        Computes role-aware, transfer-adjusted skill gaps for a candidate.
        """
        # 1. Validate candidate existence (never fabricate fake candidate records)
        cand = await self.candidate_repo.get(candidate_id)
        if not cand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found.",
            )

        # 2. Enforce evidence prerequisite: candidate must have a processed resume/profile OR assessment/skill states
        from backend.services.readiness_service import CandidateReadinessService
        readiness_svc = CandidateReadinessService(self.session)
        await readiness_svc.assert_has_candidate_evidence(candidate_id, "Skill gap analysis")

        # 3. Build target role competency blueprint
        spec = RoleSpecification(
            role_name=target_role,
            seniority=seniority,
        )
        blueprint = RoleIntelligenceService.build_competency_blueprint(spec)

        # 3. Retrieve all candidate longitudinal skill states
        # First register raw and lowercased keys, then overwrite with normalized canonical key
        # so canonical records deterministically take precedence.
        tracked_states = await self.skill_state_repo.list_by_candidate(candidate_id)
        states_by_skill: Dict[str, CandidateSkillStateModel] = {}
        for s in tracked_states:
            raw_key = s.skill_name
            states_by_skill[raw_key] = s
            states_by_skill[raw_key.lower().strip()] = s
            states_by_skill[raw_key.lower().strip().replace(" ", "_")] = s

        for s in tracked_states:
            norm_key, is_canonical = normalize_skill(topic=s.skill_name, category=s.skill_name)
            if is_canonical or norm_key not in states_by_skill:
                states_by_skill[norm_key] = s

        # 4. Dispatch to deterministic SkillGapEngine
        return SkillGapEngine.analyze_gaps(
            candidate_id=candidate_id,
            candidate_states=states_by_skill,
            blueprint=blueprint,
            seniority=seniority,
        )

    async def generate_or_update_roadmap(
        self,
        candidate_id: Any,
        target_role: Optional[str] = None,
        seniority: str = "Mid",
    ) -> PersonalizedRoadmapDTO:
        """
        Generates or refreshes the candidate's personalized roadmap derived from skill gaps.
        Preserves previously completed milestones and active coaching links.
        """
        if isinstance(candidate_id, GenerateRoadmapRequest):
            req = candidate_id
            candidate_id = req.candidate_id
            target_role = req.target_role or req.role_name
            seniority = req.seniority or "Mid"
        else:
            candidate_id = str(candidate_id)
            target_role = target_role
            seniority = seniority or "Mid"

        if not target_role or not str(target_role).strip():
            raise ValueError("Target role is mandatory before generating a personalized roadmap")
        target_role = str(target_role).strip()

        sen_key = (seniority or "Mid").lower().strip()
        if sen_key not in VALID_SENIORITY_TIERS:
            raise ValueError(f"Invalid seniority tier '{seniority}'. Must be one of: Junior, Mid, Senior, Staff, Lead, Principal.")
        seniority = VALID_SENIORITY_TIERS[sen_key]

        # 1. Synchronize candidate target_role record
        cand = await self.candidate_repo.get(candidate_id)
        if cand and getattr(cand, "target_role", None) != target_role:
            cand.target_role = target_role
            self.session.add(cand)
            await self.session.flush()

        # 1b. Compute empirical skill gaps
        gap_result = await self.calculate_gaps(candidate_id, target_role, seniority)

        # 1b. Resolve researched role intelligence profile for evidence-grounded rationale & transfer challenge
        role_spec = RoleSpecification(role_name=target_role, seniority=seniority)
        role_prof = RoleIntelligenceService.resolve_role_profile(role_spec)
        comps_by_id = {
            (c.identifier if hasattr(c, "identifier") else str(c)): c
            for c in getattr(role_prof, "competencies", [])
        }
        source_ev = [s.model_dump() if hasattr(s, "model_dump") else s for s in (getattr(role_prof, "source_evidence", None) or [])]
        arch_patterns = getattr(role_prof, "architecture_patterns", []) or []
        fail_scenarios = getattr(role_prof, "failure_scenarios", []) or []
        learn_resources = getattr(role_prof, "learning_resources", []) or []

        raw_comps = getattr(role_prof, "competencies", []) or []
        target_invariants = [
            c.name if hasattr(c, "name") else str(c).replace("_", " ").title()
            for c in raw_comps[:3]
        ] if raw_comps else ["Fault Isolation", "State Consistency"]

        unseen_challenge = {
            "title": f"Unseen Transfer Challenge: {target_role} Resilience & Failure Remediation",
            "scenario": (
                f"Under an architecture utilizing {arch_patterns[0] if arch_patterns else 'distributed event pipelines'}, "
                f"diagnose and remediate an unexpected production failure: {fail_scenarios[0] if fail_scenarios else 'cascading downstream timeout degradation'}."
            ),
            "target_invariants": target_invariants,
            "provenance": "DERIVED_FROM_WEB_RESEARCH" if getattr(role_prof, "provenance", None) and str(getattr(role_prof.provenance, "value", "")) == "RESEARCHED" else "DERIVED_FROM_CURATED_SPEC",
        }

        # 2. Check for existing active roadmap
        existing_roadmap = await self.roadmap_repo.get_by_candidate(candidate_id)

        if existing_roadmap and existing_roadmap.target_role.lower() == target_role.lower():
            roadmap = existing_roadmap
            roadmap.seniority = seniority

            # Index existing items by ID, title, and normalized slug for deterministic matching
            existing_items_by_skill: Dict[str, RoadmapItemModel] = {}
            for item in roadmap.items:
                existing_items_by_skill[item.skill_id] = item
                clean_t, _, clean_s = clean_competency_display_name(item.skill_id)
                existing_items_by_skill[clean_s] = item
                clean_t2, _, clean_s2 = clean_competency_display_name(item.skill_title)
                existing_items_by_skill[clean_s2] = item
                existing_items_by_skill[clean_t2.lower().strip()] = item

            # Update existing items and add newly identified gaps
            for gap in gap_result.gaps:
                clean_title, is_flagged, clean_slug = clean_competency_display_name(gap.skill_name)
                item = (
                    existing_items_by_skill.get(gap.skill_id)
                    or existing_items_by_skill.get(clean_slug)
                    or existing_items_by_skill.get(clean_title.lower().strip())
                )
                matched_comp = comps_by_id.get(gap.skill_id)
                rationale = gap.reasoning
                actionable_steps = list(gap.actionable_steps or [])
                if matched_comp:
                    if getattr(matched_comp, "practical_applications", None):
                        rationale += f" [Industry Expectation: Practical applications include {', '.join(matched_comp.practical_applications[:2])}.]"
                    if getattr(matched_comp, "supporting_references", None):
                        refs = '; '.join(f'{r.publisher}' for r in matched_comp.supporting_references[:2])
                        rationale += f" [Supporting Research: {refs}.]"
                if learn_resources and not any("Recommended Resource:" in s for s in actionable_steps):
                    first_res = learn_resources[0]
                    res_title = first_res.get("title") if isinstance(first_res, dict) else getattr(first_res, "title", str(first_res))
                    res_url = first_res.get("url", "Online") if isinstance(first_res, dict) else getattr(first_res, "url", "Online")
                    actionable_steps.append(f"Recommended Resource: {res_title} ({res_url})")

                details = self.synthesize_actionable_milestone_details(
                    skill_id=gap.skill_id,
                    clean_title=clean_title,
                    is_flagged=is_flagged,
                    seniority=seniority,
                    invariants=gap.core_invariants,
                    target_role=target_role,
                    status=item.status if item else (RoadmapItemStatus.COMPLETED.value if gap.priority == SkillGapPriority.SATISFIED else RoadmapItemStatus.NOT_STARTED.value),
                    current_transfer_level=gap.highest_transfer_level.value,
                    current_mastery=gap.candidate_mastery,
                    target_mastery=gap.required_mastery,
                    assistance_dependency=gap.assistance_dependency,
                )

                prof_state = gap.proficiency_state.value if hasattr(gap.proficiency_state, "value") else str(gap.proficiency_state)
                if item:
                    # Update metrics while preserving completed / in_progress states
                    item.skill_id = gap.skill_id
                    item.skill_title = clean_title
                    item.role_importance = gap.role_importance.value
                    item.priority = gap.priority.value
                    item.sequence_order = gap.priority_rank
                    item.proficiency_state = prof_state
                    item.current_mastery = gap.candidate_mastery
                    item.target_mastery = gap.required_mastery
                    item.current_transfer_level = gap.highest_transfer_level.value
                    item.assistance_dependency = gap.assistance_dependency
                    item.learning_objective = gap.learning_objective
                    item.rationale = rationale
                    item.core_invariants = gap.core_invariants
                    item.recurring_failures = gap.recurring_failure_types
                    item.actionable_steps = actionable_steps

                    # Update rich actionable milestone content
                    item.topics_to_study = details["topics_to_study"]
                    item.practical_exercises = details["practical_exercises"]
                    item.implementation_task = details["implementation_task"]
                    item.expected_deliverables = details["expected_deliverables"]
                    item.estimated_duration = details["estimated_duration"]
                    item.difficulty_level = details["difficulty_level"]
                    item.evaluation_criteria = details["evaluation_criteria"]
                    item.evidence_required = details["evidence_required"]
                    item.prerequisite_milestone_ids = details["prerequisite_milestone_ids"]
                    item.mapping_status = details["mapping_status"]
                    item.is_flagged_for_review = details["is_flagged_for_review"]
                    item.progression_tier = details["progression_tier"]

                    # If demonstrated L5 satisfaction, update to COMPLETED
                    if gap.priority == SkillGapPriority.SATISFIED and item.status != RoadmapItemStatus.COMPLETED.value:
                        item.status = RoadmapItemStatus.COMPLETED.value
                        item.completed_at = datetime.now(timezone.utc)
                else:
                    # New gap item to insert dynamically without truncation (accounts for all gaps)
                    if gap.priority != SkillGapPriority.SATISFIED:
                        new_item = RoadmapItemModel(
                            id=str(uuid.uuid4()),
                            roadmap_id=roadmap.id,
                            skill_id=gap.skill_id,
                            skill_title=clean_title,
                            role_importance=gap.role_importance.value,
                            priority=gap.priority.value,
                            sequence_order=len(roadmap.items) + 1,
                            proficiency_state=prof_state,
                            learning_objective=gap.learning_objective,
                            rationale=rationale,
                            current_mastery=gap.candidate_mastery,
                            target_mastery=gap.required_mastery,
                            current_transfer_level=gap.highest_transfer_level.value,
                            target_transfer_level="L5_INDEPENDENT_TRANSFER",
                            assistance_dependency=gap.assistance_dependency,
                            status=RoadmapItemStatus.NOT_STARTED.value,
                            core_invariants=gap.core_invariants,
                            recurring_failures=gap.recurring_failure_types,
                            actionable_steps=actionable_steps,
                            topics_to_study=details["topics_to_study"],
                            practical_exercises=details["practical_exercises"],
                            implementation_task=details["implementation_task"],
                            expected_deliverables=details["expected_deliverables"],
                            estimated_duration=details["estimated_duration"],
                            difficulty_level=details["difficulty_level"],
                            evaluation_criteria=details["evaluation_criteria"],
                            evidence_required=details["evidence_required"],
                            prerequisite_milestone_ids=details["prerequisite_milestone_ids"],
                            mapping_status=details["mapping_status"],
                            is_flagged_for_review=details["is_flagged_for_review"],
                            progression_tier=details["progression_tier"],
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        roadmap.items.append(new_item)
                        existing_items_by_skill[gap.skill_id] = new_item
                        existing_items_by_skill[clean_slug] = new_item

            # Purge any legacy items from roadmap.items that do not belong to the target role blueprint
            target_valid_ids = {g.skill_id.lower().strip() for g in gap_result.gaps}
            target_valid_slugs = {clean_competency_display_name(g.skill_name)[2].lower().strip() for g in gap_result.gaps}
            target_valid_titles = {clean_competency_display_name(g.skill_name)[0].lower().strip() for g in gap_result.gaps}

            # Clean and backfill any legacy items that were previously unmapped or lacked actionable details, and deduplicate
            from sqlalchemy.orm import object_session
            seen_slugs = set()
            cleaned_items = []
            for item in list(roadmap.items):
                clean_t, is_flagged, clean_slug = clean_competency_display_name(item.skill_title)
                dedup_key = clean_slug or clean_t.lower().strip()
                item_id = item.skill_id.lower().strip()

                # If item does not belong to the target role's blueprint competencies, delete it
                is_valid_role_comp = (
                    item_id in target_valid_ids
                    or dedup_key in target_valid_slugs
                    or clean_t.lower().strip() in target_valid_titles
                )
                if not is_valid_role_comp:
                    if object_session(item) is not None:
                        await self.session.delete(item)
                    continue

                if dedup_key in seen_slugs:
                    if object_session(item) is not None:
                        await self.session.delete(item)
                    continue
                seen_slugs.add(dedup_key)

                canon_slug = item.skill_id if not item.skill_id.startswith("unmapped_") else clean_slug

                if not item.implementation_task or not item.implementation_task.get("title") or "unmapped" in item.skill_title.lower() or item.skill_id.startswith("unmapped_"):
                    item.skill_title = clean_t
                    item.skill_id = canon_slug
                    item_details = self.synthesize_actionable_milestone_details(
                        skill_id=canon_slug,
                        clean_title=clean_t,
                        is_flagged=is_flagged,
                        seniority=seniority,
                        invariants=item.core_invariants or [f"Foundational architectural principles for {clean_t}"],
                        target_role=target_role,
                        status=item.status,
                        current_transfer_level=item.current_transfer_level,
                        current_mastery=item.current_mastery,
                        target_mastery=item.target_mastery,
                        assistance_dependency=item.assistance_dependency,
                    )
                    item.topics_to_study = item_details["topics_to_study"]
                    item.practical_exercises = item_details["practical_exercises"]
                    item.implementation_task = item_details["implementation_task"]
                    item.expected_deliverables = item_details["expected_deliverables"]
                    item.estimated_duration = item_details["estimated_duration"]
                    item.difficulty_level = item_details["difficulty_level"]
                    item.evaluation_criteria = item_details["evaluation_criteria"]
                    item.evidence_required = item_details["evidence_required"]
                    item.prerequisite_milestone_ids = item_details["prerequisite_milestone_ids"]
                    item.mapping_status = item_details["mapping_status"]
                    item.is_flagged_for_review = item_details["is_flagged_for_review"]
                    item.progression_tier = item_details["progression_tier"]
                cleaned_items.append(item)

            roadmap.items = cleaned_items

            # Topologically sort and reassign sequential sequence order
            item_ids = [i.skill_id for i in roadmap.items]
            sorted_order = topological_prerequisite_sort(item_ids)
            order_map = {sid: idx for idx, sid in enumerate(sorted_order)}
            roadmap.items.sort(key=lambda i: order_map.get(i.skill_id, i.sequence_order))
            for idx, item in enumerate(roadmap.items, 1):
                item.sequence_order = idx

            roadmap.meta_info = {
                "total_gaps": gap_result.gaps_detected,
                "satisfied_competencies": gap_result.satisfied_competencies,
                "total_role_competencies": gap_result.total_role_competencies,
                "assessed_competencies_count": gap_result.assessed_competencies_count,
                "unassessed_competencies_count": gap_result.unassessed_competencies_count,
                "identified_gaps_count": gap_result.gaps_detected,
                "milestones_generated_count": len(roadmap.items),
                "excluded_competencies": gap_result.excluded_competencies,
                "research_status": getattr(role_prof, "research_status", "NOT_STARTED").value if hasattr(getattr(role_prof, "research_status", None), "value") else str(getattr(role_prof, "research_status", "NOT_STARTED")),
                "research_provenance": getattr(role_prof, "provenance", "CURATED").value if hasattr(getattr(role_prof, "provenance", None), "value") else str(getattr(role_prof, "provenance", "CURATED")),
                "research_freshness_timestamp": getattr(role_prof, "research_freshness_timestamp", None),
                "source_count": len(source_ev),
                "source_evidence": source_ev,
                "unseen_transfer_challenge": unseen_challenge,
            }
            flag_modified(roadmap, "meta_info")
        else:
            # Archive ANY previous active roadmaps for this candidate to eliminate stale roadmap persistence
            from sqlalchemy import update
            await self.session.execute(
                update(PersonalizedRoadmapModel)
                .where(
                    PersonalizedRoadmapModel.candidate_id == candidate_id,
                    PersonalizedRoadmapModel.status == RoadmapStatus.ACTIVE.value,
                )
                .values(status=RoadmapStatus.ARCHIVED.value, updated_at=datetime.now(timezone.utc))
            )

            now = datetime.now(timezone.utc)
            # Create brand new roadmap
            roadmap = PersonalizedRoadmapModel(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                target_role=target_role,
                seniority=seniority,
                status=RoadmapStatus.ACTIVE.value,
                summary=f"Personalized transfer learning roadmap for {target_role} ({seniority} tier).",
                meta_info={
                    "total_gaps": gap_result.gaps_detected,
                    "satisfied_competencies": gap_result.satisfied_competencies,
                    "total_role_competencies": gap_result.total_role_competencies,
                    "assessed_competencies_count": gap_result.assessed_competencies_count,
                    "unassessed_competencies_count": gap_result.unassessed_competencies_count,
                    "identified_gaps_count": gap_result.gaps_detected,
                    "milestones_generated_count": 0,
                    "excluded_competencies": gap_result.excluded_competencies,
                    "research_status": getattr(role_prof, "research_status", "NOT_STARTED").value if hasattr(getattr(role_prof, "research_status", None), "value") else str(getattr(role_prof, "research_status", "NOT_STARTED")),
                    "research_provenance": getattr(role_prof, "provenance", "CURATED").value if hasattr(getattr(role_prof, "provenance", None), "value") else str(getattr(role_prof, "provenance", "CURATED")),
                    "research_freshness_timestamp": getattr(role_prof, "research_freshness_timestamp", None),
                    "source_count": len(source_ev),
                    "source_evidence": source_ev,
                    "unseen_transfer_challenge": unseen_challenge,
                },
                created_at=now,
                updated_at=now,
            )
            roadmap.items = []

            # Dynamic length: filter out competencies where the candidate already demonstrated mastery or independent transfer.
            active_gaps = [g for g in gap_result.gaps if g.priority != SkillGapPriority.SATISFIED]
            if not active_gaps and gap_result.gaps:
                # If all competencies are satisfied, keep top competency for mastery maintenance
                active_gaps = [gap_result.gaps[0]]

            # Account for all identified gaps (no arbitrary truncation)
            selected_gaps = active_gaps

            # Build items
            for idx, gap in enumerate(selected_gaps, start=1):
                matched_comp = comps_by_id.get(gap.skill_id)
                rationale = gap.reasoning
                actionable_steps = list(gap.actionable_steps or [])
                if matched_comp:
                    if getattr(matched_comp, "practical_applications", None):
                        rationale += f" [Industry Expectation: Practical applications include {', '.join(matched_comp.practical_applications[:2])}.]"
                    if getattr(matched_comp, "supporting_references", None):
                        refs = '; '.join(f'{r.publisher}' for r in matched_comp.supporting_references[:2])
                        rationale += f" [Supporting Research: {refs}.]"
                if learn_resources and not any("Recommended Resource:" in s for s in actionable_steps):
                    first_res = learn_resources[0]
                    res_title = first_res.get("title") if isinstance(first_res, dict) else getattr(first_res, "title", str(first_res))
                    res_url = first_res.get("url", "Online") if isinstance(first_res, dict) else getattr(first_res, "url", "Online")
                    actionable_steps.append(f"Recommended Resource: {res_title} ({res_url})")

                clean_title, is_flagged, _ = clean_competency_display_name(gap.skill_name)
                details = self.synthesize_actionable_milestone_details(
                    skill_id=gap.skill_id,
                    clean_title=clean_title,
                    is_flagged=is_flagged,
                    seniority=seniority,
                    invariants=gap.core_invariants,
                    target_role=target_role,
                    status=(
                        RoadmapItemStatus.COMPLETED.value
                        if gap.priority == SkillGapPriority.SATISFIED
                        else RoadmapItemStatus.NOT_STARTED.value
                    ),
                    current_transfer_level=gap.highest_transfer_level.value,
                    current_mastery=gap.candidate_mastery,
                    target_mastery=gap.required_mastery,
                    assistance_dependency=gap.assistance_dependency,
                )

                item_model = RoadmapItemModel(
                    id=str(uuid.uuid4()),
                    roadmap_id=roadmap.id,
                    skill_id=gap.skill_id,
                    skill_title=clean_title,
                    role_importance=gap.role_importance.value,
                    priority=gap.priority.value,
                    sequence_order=idx,
                    proficiency_state=gap.proficiency_state.value if hasattr(gap.proficiency_state, "value") else str(gap.proficiency_state),
                    learning_objective=gap.learning_objective,
                    rationale=rationale,
                    current_mastery=gap.candidate_mastery,
                    target_mastery=gap.required_mastery,
                    current_transfer_level=gap.highest_transfer_level.value,
                    target_transfer_level="L5_INDEPENDENT_TRANSFER",
                    assistance_dependency=gap.assistance_dependency,
                    status=(
                        RoadmapItemStatus.COMPLETED.value
                        if gap.priority == SkillGapPriority.SATISFIED
                        else RoadmapItemStatus.NOT_STARTED.value
                    ),
                    completed_at=datetime.now(timezone.utc) if gap.priority == SkillGapPriority.SATISFIED else None,
                    core_invariants=gap.core_invariants,
                    recurring_failures=gap.recurring_failure_types,
                    actionable_steps=actionable_steps,
                    topics_to_study=details["topics_to_study"],
                    practical_exercises=details["practical_exercises"],
                    implementation_task=details["implementation_task"],
                    expected_deliverables=details["expected_deliverables"],
                    estimated_duration=details["estimated_duration"],
                    difficulty_level=details["difficulty_level"],
                    evaluation_criteria=details["evaluation_criteria"],
                    evidence_required=details["evidence_required"],
                    prerequisite_milestone_ids=details["prerequisite_milestone_ids"],
                    mapping_status=details["mapping_status"],
                    is_flagged_for_review=details["is_flagged_for_review"],
                    progression_tier=details["progression_tier"],
                    created_at=now,
                    updated_at=now,
                )
                roadmap.items.append(item_model)

            # Topologically sort and reassign sequential sequence order
            item_ids = [i.skill_id for i in roadmap.items]
            sorted_order = topological_prerequisite_sort(item_ids)
            order_map = {sid: s_idx for s_idx, sid in enumerate(sorted_order)}
            roadmap.items.sort(key=lambda i: order_map.get(i.skill_id, i.sequence_order))
            for s_idx, item in enumerate(roadmap.items, 1):
                item.sequence_order = s_idx

            self.session.add(roadmap)
            await self.session.flush()

        # 3. Recompute progress stats
        total_items = len(roadmap.items)
        completed_items = sum(
            1 for item in roadmap.items if item.status == RoadmapItemStatus.COMPLETED.value
        )
        roadmap.total_items = total_items
        roadmap.completed_items = completed_items
        roadmap.overall_progress = round((completed_items / total_items) * 100.0, 1) if total_items > 0 else 0.0

        if roadmap.meta_info:
            roadmap.meta_info["milestones_generated_count"] = total_items
            flag_modified(roadmap, "meta_info")

        if completed_items == total_items and total_items > 0:
            roadmap.status = RoadmapStatus.COMPLETED.value

        await self.session.commit()
        return self._to_dto(roadmap)

    async def get_roadmap_for_candidate(self, candidate_id: str) -> Optional[PersonalizedRoadmapDTO]:
        """Retrieves the active personalized roadmap for a candidate."""
        from backend.services.readiness_service import CandidateReadinessService
        readiness_svc = CandidateReadinessService(self.session)
        readiness = await readiness_svc.get_candidate_readiness(candidate_id)
        if not (readiness.is_profile_ready or readiness.is_assessment_ready or readiness.is_coaching_ready):
            return None
        roadmap = await self.roadmap_repo.get_by_candidate(candidate_id)
        if not roadmap or len(roadmap.items) == 0:
            cand = await self.candidate_repo.get(candidate_id)
            target_role = getattr(cand, "target_role", None) or "Backend Systems Engineer"
            return await self.generate_or_update_roadmap(candidate_id, target_role, getattr(roadmap, "seniority", "Senior"))
        return self._to_dto(roadmap)

    async def start_coaching_for_item(
        self,
        item_id: str,
        candidate_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bridges a roadmap milestone item directly into the Transfer-Aware Coaching Studio.
        Instantiates or resumes CoachingOrchestrator anchored on the item's core invariants.
        """
        item = await self.roadmap_repo.get_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roadmap milestone item '{item_id}' not found.",
            )

        if candidate_id and str(item.roadmap.candidate_id) != str(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Roadmap item does not belong to the specified candidate.",
            )
        candidate_id = item.roadmap.candidate_id

        # Build anchor training context from roadmap item
        invariants = list(item.core_invariants or [])
        if not invariants and item.skill_id in CANONICAL_SKILLS:
            invariants = CANONICAL_SKILLS[item.skill_id]["default_invariants"]

        weakness_desc = ""
        if item.recurring_failures:
            clean_fails = [f.replace("CONCEPT_GAP:", "").replace("_", " ").title() for f in item.recurring_failures]
            weakness_desc = f"diagnosed shortcomings in {', '.join(clean_fails)}"
        elif item.rationale and "weakness" in item.rationale.lower():
            weakness_desc = item.rationale
        else:
            weakness_desc = f"the gap identified in your interview regarding {item.skill_title}"

        # Pedagogical 3-phase initial teaching lesson: 1. Explain, 2. Worked Example, 3. Check Understanding
        primary_inv = invariants[0] if invariants else "Structural consistency and failure isolation"
        secondary_inv = invariants[1] if len(invariants) > 1 else (invariants[0] if invariants else "Deterministic state synchronization")
        inv_summary = "; ".join(invariants[:2]) if invariants else primary_inv

        explain_part = (
            f"### 1. Concept Explanation: {item.skill_title}\n"
            f"**Learning Objective:** {item.learning_objective}\n\n"
            f"The key gap identified in your assessment was {weakness_desc}. Let's master the foundational invariant before exploring complex variations.\n\n"
            f"**Core Invariants:** {inv_summary}.\n"
            f"When designing systems around {item.skill_title}, your solution must actively maintain these invariant boundaries to avoid data corruption, latency spikes, or cascading degradation."
        )

        example_part = (
            f"### 2. Concrete Worked Example\n"
            f"Consider a production workload requiring {item.skill_title}:\n"
            f"- **Naive Approach (Anti-Pattern):** An implementation that overlooks '{primary_inv}' risks severe runtime failures under burst traffic or partial network partitions.\n"
            f"- **Invariant-Preserving Pattern:** By explicitly enforcing '{secondary_inv}', the architecture guarantees predictable behavior, deterministic recovery, and strong isolation."
        )

        check_part = (
            f"### 3. Check Understanding\n"
            f"Before we test this in an unseen scenario, explain how adhering to '{primary_inv}' directly prevents {weakness_desc}, and what trade-off or failure mode you must account for."
        )

        teaching_lesson = f"{explain_part}\n\n{example_part}\n\n{check_part}"

        canonical_text = (
            f"Demonstrate architectural design for {item.skill_title}. "
            f"Specifically address invariants: {'; '.join(invariants[:3]) if invariants else 'Foundational constraints'}."
        )

        training_context = TrainingContext(
            task_id=f"roadmap_task_{item.skill_id[:20]}_{uuid.uuid4().hex[:6]}",
            question_text=canonical_text,
            skill_id=item.skill_id,
            core_invariants=invariants,
            base_surface_context=item.skill_title,
            base_expected_concepts=invariants if invariants else [item.skill_title],
            topic=item.skill_title,
            target_role=item.roadmap.target_role,
            weakness=weakness_desc,
            current_mastery=item.current_mastery,
            transfer_level=item.current_transfer_level,
            role_importance=item.role_importance,
            learning_objective=item.learning_objective,
            teaching_lesson=teaching_lesson,
        )

        # Generate persistent coaching session ID preserving roadmap item provenance
        coaching_session_id = f"coach_rdmp_{item.id[:8]}_{uuid.uuid4().hex[:6]}"

        # Initialize Coaching Loop via TransferCoachingService
        coaching_service = TransferCoachingService(session=self.session)
        init_result = await coaching_service.start_coaching_loop(
            candidate_id=candidate_id,
            session_id=coaching_session_id,
            training_context=training_context,
            config=CoachingSessionConfig(max_retries=2, pass_threshold=7.0),
            target_role=item.roadmap.target_role,
        )
        try:
            from backend.api.v1.endpoints.transfer_coaching import _active_services
            _active_services[coaching_session_id] = coaching_service
        except Exception:
            pass

        # Update roadmap item link and status
        item.status = RoadmapItemStatus.IN_PROGRESS.value
        item.coaching_session_id = coaching_session_id
        await self.session.commit()

        return StartCoachingFromRoadmapResponse(
            item_id=item.id,
            roadmap_id=item.roadmap_id,
            skill_id=item.skill_id,
            coaching_session_id=coaching_session_id,
            orchestrator_state=init_result.model_dump(mode="json"),
            training_context=training_context.model_dump(mode="json"),
        )

    async def sync_roadmap_progress(self, candidate_id: str) -> Optional[PersonalizedRoadmapDTO]:
        """
        Synchronizes all milestone items against latest candidate skill state evidence.
        Updates item mastery, transfer level, and marks items COMPLETED if L5 criteria are met.
        """
        roadmap = await self.roadmap_repo.get_by_candidate(candidate_id)
        if not roadmap:
            return None

        tracked_states = await self.skill_state_repo.list_by_candidate(candidate_id)
        states_by_skill: Dict[str, CandidateSkillStateModel] = {}
        for s in tracked_states:
            states_by_skill[s.skill_name] = s
            states_by_skill[s.skill_name.lower().strip()] = s
            states_by_skill[s.skill_name.lower().strip().replace(" ", "_")] = s
            norm_key, _ = normalize_skill(topic=s.skill_name, category=s.skill_name)
            states_by_skill[norm_key] = s

        for item in roadmap.items:
            candidate_keys = [
                item.skill_id,
                item.skill_id.lower().strip(),
                item.skill_id.lower().strip().replace("_", " "),
                item.skill_title,
                item.skill_title.lower().strip(),
                item.skill_title.lower().strip().replace(" ", "_"),
            ]
            state = None
            for k in candidate_keys:
                if k in states_by_skill:
                    state = states_by_skill[k]
                    break
            if not state:
                norm_id, _ = normalize_skill(topic=item.skill_title, category=item.skill_id)
                state = states_by_skill.get(norm_id)

            if state:
                item.current_mastery = float(state.mastery_estimate)
                item.current_transfer_level = state.highest_transfer_level
                item.assistance_dependency = float(state.assistance_dependency_index)
                item.recurring_failures = list(state.recurring_failure_types or [])

                # Verify rigorous completion criteria:
                # 1. Mastery estimate meets or exceeds target
                # 2. Demonstrated highest transfer level is L5 Independent Transfer
                # 3. Assistance Dependency Index is low (<= 0.25)
                has_l5_transfer = state.highest_transfer_level == "L5_INDEPENDENT_TRANSFER"
                has_sufficient_mastery = state.mastery_estimate >= item.target_mastery
                has_low_assistance = state.assistance_dependency_index <= MAX_SATISFIED_ADI

                if has_l5_transfer and has_sufficient_mastery and has_low_assistance:
                    item.status = RoadmapItemStatus.COMPLETED.value
                    if not item.completed_at:
                        item.completed_at = datetime.now(timezone.utc)
                elif item.status == RoadmapItemStatus.NOT_STARTED.value and state.total_attempts > 0:
                    item.status = RoadmapItemStatus.IN_PROGRESS.value

                item.progression_tier = self.determine_progression_tier(
                    status=item.status,
                    current_transfer_level=item.current_transfer_level,
                    current_mastery=item.current_mastery,
                    target_mastery=item.target_mastery,
                    assistance_dependency=item.assistance_dependency,
                )

        # Recompute overall progress
        total_items = len(roadmap.items)
        completed_items = sum(
            1 for item in roadmap.items if item.status == RoadmapItemStatus.COMPLETED.value
        )
        roadmap.total_items = total_items
        roadmap.completed_items = completed_items
        roadmap.overall_progress = round((completed_items / total_items) * 100.0, 1) if total_items > 0 else 0.0

        if completed_items == total_items and total_items > 0:
            roadmap.status = RoadmapStatus.COMPLETED.value

        await self.session.commit()
        return self._to_dto(roadmap)

    def _to_dto(self, model: PersonalizedRoadmapModel) -> PersonalizedRoadmapDTO:
        """Converts ORM model to clean DTO."""
        items_dto = [
            RoadmapItemDTO(
                id=item.id,
                roadmap_id=item.roadmap_id,
                skill_id=item.skill_id,
                skill_title=item.skill_title,
                role_importance=item.role_importance,
                priority=SkillGapPriority(item.priority),
                sequence_order=item.sequence_order,
                learning_objective=item.learning_objective,
                rationale=item.rationale,
                current_mastery=item.current_mastery,
                target_mastery=item.target_mastery,
                current_transfer_level=item.current_transfer_level,
                target_transfer_level=item.target_transfer_level,
                assistance_dependency=item.assistance_dependency,
                status=RoadmapItemStatus(item.status),
                coaching_session_id=item.coaching_session_id,
                core_invariants=list(item.core_invariants or []),
                recurring_failures=list(item.recurring_failures or []),
                actionable_steps=list(item.actionable_steps or []),
                topics_to_study=list(item.topics_to_study or []),
                practical_exercises=list(item.practical_exercises or []),
                implementation_task=dict(item.implementation_task or {}),
                expected_deliverables=list(item.expected_deliverables or []),
                estimated_duration=item.estimated_duration or "1-2 weeks",
                difficulty_level=item.difficulty_level or "INTERMEDIATE",
                evaluation_criteria=list(item.evaluation_criteria or []),
                evidence_required=item.evidence_required,
                prerequisite_milestone_ids=list(item.prerequisite_milestone_ids or []),
                mapping_status=item.mapping_status or "MAPPED",
                is_flagged_for_review=bool(item.is_flagged_for_review),
                progression_tier=item.progression_tier or "Tier 1: Assessed, Needs Practice",
                proficiency_state=getattr(item, "proficiency_state", "NOT_ASSESSED") or "NOT_ASSESSED",
                is_measured_proficiency=(getattr(item, "proficiency_state", "NOT_ASSESSED") in ["DEMONSTRATED_COMPETENCY", "PARTIALLY_DEMONSTRATED", "DEMONSTRATED_WEAKNESS"]),
                notes=item.notes,
                completed_at=item.completed_at,
                created_at=item.created_at or datetime.now(timezone.utc),
                updated_at=item.updated_at or datetime.now(timezone.utc),
            )
            for item in sorted(model.items, key=lambda i: i.sequence_order)
        ]

        meta = model.meta_info or {}
        return PersonalizedRoadmapDTO(
            id=model.id,
            candidate_id=model.candidate_id,
            target_role=model.target_role,
            seniority=model.seniority,
            status=RoadmapStatus(model.status),
            overall_progress=model.overall_progress,
            total_items=model.total_items,
            completed_items=model.completed_items,
            total_role_competencies=meta.get("total_role_competencies", len(items_dto)),
            assessed_competencies_count=meta.get("assessed_competencies_count", 0),
            unassessed_competencies_count=meta.get("unassessed_competencies_count", 0),
            identified_gaps_count=meta.get("identified_gaps_count", len(items_dto)),
            milestones_generated_count=len(items_dto),
            excluded_competencies=meta.get("excluded_competencies", []),
            summary=model.summary,
            items=items_dto,
            meta_info=meta,
            created_at=model.created_at or datetime.now(timezone.utc),
            updated_at=model.updated_at or datetime.now(timezone.utc),
        )
