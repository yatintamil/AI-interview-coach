import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../../services/api';
import {
  OrchestratorStepResultDTO,
  UIPresentationState,
  TransferTaskDTO,
  CoachingEvaluationDTO,
  CoachingInterventionDTO,
  TransferDiagnosisDTO,
  CandidateSkillStateDTO,
  ResearchTelemetryRecordDTO,
  TrainingContextDTO,
  StartCoachingLoopPayload,
} from '../../types/coaching';

export interface CoachingAttemptRecord {
  step: number;
  stageName: string;
  taskPrompt: string;
  answer: string;
  score?: number;
  passed?: boolean;
  coachFeedback?: string;
  interventionContent?: string;
  timestamp: string;
}

export interface UseCoachingSessionReturn {
  // Authoritative backend & derived UI state
  sessionState: OrchestratorStepResultDTO | null;
  uiState: UIPresentationState;
  telemetry: ResearchTelemetryRecordDTO | null;
  isLoading: boolean;
  error: string | null;
  sessionId: string | null;
  candidateId: string | null;

  // Presentation-only tracking
  elapsedSeconds: number;
  hintsCount: number;
  isHintDisabled: boolean;

  // Active step entities
  activeTask: TransferTaskDTO | null;
  activeEvaluation: CoachingEvaluationDTO | null;
  activeIntervention: CoachingInterventionDTO | null;
  activeDiagnosis: TransferDiagnosisDTO | null;
  candidateSkillState: CandidateSkillStateDTO | null;
  trainingContext: TrainingContextDTO | null;
  history: CoachingAttemptRecord[];

  // Actions
  startSession: (candidateId: string, customTopic?: string) => Promise<void>;
  startSessionFromInterview: (
    candidateId: string,
    interviewSessionId: string,
    questionId?: string
  ) => Promise<void>;
  hydrateSession: (sessionId: string) => Promise<void>;
  setHydratedSession: (result: OrchestratorStepResultDTO) => void;
  submitStep: (answer: string) => Promise<void>;
  requestHint: () => void;
  resetSession: () => void;
  fetchTelemetry: () => Promise<void>;
}

// Canonical competency catalogs anchored on backend Transfer Engine and domain skill mapping
export const CANONICAL_TRAINING_CONTEXTS: Record<string, TrainingContextDTO> = {
  distributed_caching: {
    task_id: 'sysdesign_distributed_cache_v1',
    question_text:
      'Design a scalable distributed in-memory cache layer for an e-commerce platform that experiences 50x read-to-write traffic. Address data partitioning, cache eviction strategy, read/write concurrency consistency, and how you prevent hot-key overload and stampeding herd problems.',
    skill_id: 'distributed_caching',
    core_invariants: [
      'Cache-aside or write-through consistency boundary',
      'Consistent hashing with virtual nodes for partitioning',
      'Eviction policy trade-offs (LRU/LFU/TTL)',
      'Stampeding herd mitigation (probabilistic early expiration or mutex locks)',
    ],
    base_surface_context: 'e-commerce flash sales catalog caching',
    base_expected_concepts: [
      'consistent_hashing',
      'lru_eviction',
      'stampede_mitigation',
      'cache_invalidation',
      'partitioning',
    ],
    topic: 'Distributed Caching & Partitioning',
    learning_objective: 'Master distributed cache partitioning, invalidation consistency, and stampede mitigation.',
  },
  system_decomposition: {
    task_id: 'sysdesign_system_decomposition_v1',
    question_text:
      'Design an event-driven order processing and inventory allocation workflow for a high-volume retail platform. Decompose service boundaries, maintain transactional consistency without two-phase locking, and guarantee at-least-once message processing with idempotency.',
    skill_id: 'system_decomposition',
    core_invariants: [
      'Loose coupling across bounded contexts',
      'Asynchronous message passing with at-least-once or exactly-once semantics',
      'Saga orchestration or choreography without distributed 2PC locks',
      'Transactional outbox pattern for atomic state publication',
    ],
    base_surface_context: 'e-commerce retail order processing and warehouse dispatch',
    base_expected_concepts: [
      'saga_pattern',
      'transactional_outbox',
      'eventual_consistency',
      'idempotency',
      'bounded_context',
    ],
    topic: 'Microservices & Event-Driven Decoupling',
    learning_objective: 'Master microservice boundary decomposition, distributed sagas, and outbox event publishing.',
  },
  concurrency_control: {
    task_id: 'sysdesign_concurrency_control_v1',
    question_text:
      'Design a high-contention ticket reservation system where thousands of users compete for limited seat inventory simultaneously. Detail how you prevent double-booking, configure transaction isolation levels, resolve write skew and deadlocks, and apply optimistic vs pessimistic locking.',
    skill_id: 'concurrency_control',
    core_invariants: [
      'ACID transactional boundaries and rollback invariants',
      'Isolation anomaly prevention (dirty reads, phantom reads, write skew)',
      'Deterministic lock ordering or optimistic concurrency verification',
      'Deadlock detection and exponential backoff retry mechanics',
    ],
    base_surface_context: 'high-concurrency concert ticket reservation',
    base_expected_concepts: [
      'optimistic_locking',
      'pessimistic_locking',
      'isolation_levels',
      'write_skew',
      'deadlock_prevention',
    ],
    topic: 'Database Concurrency & Isolation Levels',
    learning_objective: 'Master transaction isolation guarantees, anomaly prevention, and lock-free concurrency.',
  },
  resilience_patterns: {
    task_id: 'sysdesign_resilience_patterns_v1',
    question_text:
      'Design a resilient API gateway tier communicating with volatile upstream third-party payment providers. Explain how you implement circuit breakers with state transitions (Closed, Open, Half-Open), bounded client backpressure queues, bulkhead resource isolation, and adaptive jittered retries.',
    skill_id: 'resilience_patterns',
    core_invariants: [
      'Fault isolation via bulkhead partitioning',
      'Circuit breaker state transitions (Closed -> Open -> Half-Open)',
      'Exponential backoff with randomized jitter',
      'Load shedding and graceful degradation under backpressure',
    ],
    base_surface_context: 'high-throughput third-party payment processing gateway',
    base_expected_concepts: [
      'circuit_breaker',
      'bulkhead_isolation',
      'exponential_backoff',
      'rate_limiting',
      'backpressure',
    ],
    topic: 'Circuit Breaking & Backpressure Resilience',
    learning_objective: 'Master cascading failure prevention, circuit breaker state machines, and backpressure isolation.',
  },
  rate_limiting: {
    task_id: 'sysdesign_rate_limiting_v1',
    question_text:
      'Design a globally distributed rate limiting tier that enforces tier-based rate budgets (e.g. 10,000 req/sec) across 10 geographical regions. Detail your algorithm (Token Bucket, Leaky Bucket, or Sliding Window Log), how you synchronize atomic counters across regions with sub-millisecond latency, and how you return standard 429 Retry-After semantics.',
    skill_id: 'rate_limiting',
    core_invariants: [
      'Deterministic rate budget enforcement across distributed nodes',
      'Atomic counter increments or sliding window timestamps',
      'Graceful shedding with explicit Retry-After headers',
    ],
    base_surface_context: 'multi-region public API rate enforcement tier',
    base_expected_concepts: [
      'token_bucket',
      'sliding_window',
      'redis_cluster',
      'retry_after',
      'distributed_counter',
    ],
    topic: 'Distributed Rate Limiting & Throttling',
    learning_objective: 'Master distributed rate budgeting, sliding window algorithms, and load shedding.',
  },
  algorithmic_optimization: {
    task_id: 'alg_amortized_complexity_v1',
    question_text:
      'Design an efficient data structure for maintaining sliding-window quantiles and rolling percentiles over high-throughput financial time-series events. Analyze the amortized time complexity, space overhead, and invariance under skewed streaming distributions.',
    skill_id: 'algorithmic_optimization',
    core_invariants: [
      'Optimal substructure and state-space decomposition',
      'Strict asymptotic time and space upper bounds',
      'Invariant-preserving state transition functions',
      'Boundary edge-case resilience under extreme skew',
    ],
    base_surface_context: 'high-frequency financial trade window percentiles',
    base_expected_concepts: [
      'sliding_window',
      'amortized_analysis',
      'balanced_trees',
      'heaps',
      'big_o',
    ],
    topic: 'Data Structure Selection & Amortized Complexity',
    learning_objective: 'Master asymptotic time/space bounds, invariant-preserving state transitions, and optimal data structure trade-offs.',
  },
  memory_management: {
    task_id: 'mem_resource_lifecycle_v1',
    question_text:
      'Diagnose and remediate a high-throughput microservice exhibiting monotonic memory growth and latency degradation under prolonged production load. Detail your heap dump profiling strategy, garbage collection tuning, circular reference resolution, and how you enforce deterministic resource bounds.',
    skill_id: 'memory_management',
    core_invariants: [
      'Deterministic object allocation and reclamation boundaries',
      'Cyclic reference resolution and root reachability',
      'Bounded memory ceilings under high-throughput allocation',
    ],
    base_surface_context: 'long-running streaming telemetry ingestion pipeline',
    base_expected_concepts: [
      'garbage_collection',
      'heap_profiling',
      'reference_cycles',
      'memory_leak',
      'bounded_buffers',
    ],
    topic: 'Memory Architecture & Resource Lifecycle',
    learning_objective: 'Master memory allocation ceilings, garbage collector tuning, and deterministic resource release boundaries.',
  },
  api_security: {
    task_id: 'sec_multitenant_authz_v1',
    question_text:
      'Design a zero-trust multi-tenant authorization and token validation architecture for a distributed SaaS platform. Explain how you enforce tenant boundary isolation, prevent Insecure Direct Object References (IDOR), implement least-privilege role-based access control, and guarantee cryptographic verification without creating database bottlenecks.',
    skill_id: 'api_security',
    core_invariants: [
      'Tenant context propagation and row-level authorization boundaries',
      'Least-privilege permission validation before execution',
      'Cryptographic integrity and tamper detection',
    ],
    base_surface_context: 'multi-tenant enterprise SaaS resource management',
    base_expected_concepts: [
      'rbac',
      'jwt_validation',
      'tenant_isolation',
      'idor_prevention',
      'cryptographic_verification',
    ],
    topic: 'API Security & Multi-Tenant Authorization',
    learning_objective: 'Master multi-tenant isolation, cryptographic token verification, and least-privilege authorization boundaries.',
  },
};

export const DEFAULT_TRAINING_CONTEXT = CANONICAL_TRAINING_CONTEXTS.distributed_caching;

export function resolveTrainingContext(topicOrSkill?: string): TrainingContextDTO {
  if (!topicOrSkill) return CANONICAL_TRAINING_CONTEXTS.distributed_caching;

  const norm = topicOrSkill.trim().toLowerCase();

  if (CANONICAL_TRAINING_CONTEXTS[norm]) {
    return CANONICAL_TRAINING_CONTEXTS[norm];
  }

  if (norm.includes('microservice') || norm.includes('decoupling') || norm.includes('event-driven') || norm.includes('decomposition')) {
    return CANONICAL_TRAINING_CONTEXTS.system_decomposition;
  }
  if (norm.includes('concurrency') || norm.includes('isolation') || norm.includes('transaction') || norm.includes('lock')) {
    return CANONICAL_TRAINING_CONTEXTS.concurrency_control;
  }
  if (norm.includes('resilience') || norm.includes('circuit') || norm.includes('backpressure') || norm.includes('bulkhead')) {
    return CANONICAL_TRAINING_CONTEXTS.resilience_patterns;
  }
  if (norm.includes('rate limit') || norm.includes('throttl') || norm.includes('token bucket')) {
    return CANONICAL_TRAINING_CONTEXTS.rate_limiting;
  }
  if (norm.includes('cache') || norm.includes('caching') || norm.includes('redis') || norm.includes('partition')) {
    return CANONICAL_TRAINING_CONTEXTS.distributed_caching;
  }
  if (norm.includes('algorithm') || norm.includes('data structure') || norm.includes('complexity') || norm.includes('big o') || norm.includes('amortized')) {
    return CANONICAL_TRAINING_CONTEXTS.algorithmic_optimization;
  }
  if (norm.includes('memory') || norm.includes('heap') || norm.includes('garbage collection') || norm.includes('leak')) {
    return CANONICAL_TRAINING_CONTEXTS.memory_management;
  }
  if (norm.includes('security') || norm.includes('auth') || norm.includes('tenant') || norm.includes('idor')) {
    return CANONICAL_TRAINING_CONTEXTS.api_security;
  }

  const cleanId = norm.replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return {
    task_id: `dyn_${cleanId || 'topic'}_v1`,
    skill_id: cleanId || 'system_architecture',
    question_text: `Analyze and design a production solution for ${topicOrSkill}. Formulate your architectural approach, detail how you prevent common failure modes, and guarantee reliable operational bounds under scale.`,
    core_invariants: [
      `Preserve foundational invariants for ${topicOrSkill}`,
      `Prevent edge-case boundary failures and state corruption`,
      `Maintain deterministic execution and observable performance bounds`,
    ],
    base_surface_context: `high-throughput production ${topicOrSkill} scenario`,
    base_expected_concepts: [
      'foundational_mechanics',
      'failure_prevention',
      'invariant_preservation',
      'scale_considerations',
    ],
    topic: topicOrSkill,
    learning_objective: `Master core invariants, operational trade-offs, and unassisted execution for ${topicOrSkill}.`,
  };
}

/**
 * Derives UI presentation state strictly from authoritative backend orchestrator state.
 * Prevents the frontend from making independent pedagogical policy decisions.
 */
function derivePresentationState(
  backendResult: OrchestratorStepResultDTO | null,
  isLoading: boolean,
  error: string | null
): UIPresentationState {
  if (error) return 'ERROR';
  if (!backendResult) return 'IDLE';
  if (isLoading) return 'EVALUATING';

  switch (backendResult.state) {
    case 'TRAINING':
      return 'TRAINING';
    case 'UNDERSTANDING_CHECK':
      return 'UNDERSTANDING_CHECK';
    case 'TRAINING_EVALUATION':
    case 'TRANSFER_ATTEMPT':
      return 'TRANSFER';
    case 'TRANSFER_DIAGNOSIS':
    case 'COACHING_DECISION':
    case 'INTERVENTION':
      return 'COACHING';
    case 'RETRY':
    case 'RETRY_EVALUATION':
      return 'RETRY';
    case 'INDEPENDENT_TRANSFER':
      return 'INDEPENDENT_TRANSFER';
    case 'COMPLETED':
      return 'COMPLETED';
    case 'FAILED':
      return 'ERROR';
    case 'IDLE':
    default:
      return 'IDLE';
  }
}

export function useCoachingSession(): UseCoachingSessionReturn {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<OrchestratorStepResultDTO | null>(null);
  const [telemetry, setTelemetry] = useState<ResearchTelemetryRecordDTO | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [hintsCount, setHintsCount] = useState<number>(0);
  const [history, setHistory] = useState<CoachingAttemptRecord[]>([]);

  // Synchronous refs to prevent stale closure during rapid state transitions
  const sessionIdRef = useRef<string | null>(null);
  const sessionStateRef = useRef<OrchestratorStepResultDTO | null>(null);

  // Presentation-only timer
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    sessionStateRef.current = sessionState;
  }, [sessionState]);

  useEffect(() => {
    if (sessionState && sessionState.state !== 'COMPLETED' && sessionState.state !== 'FAILED' && !isLoading) {
      timerRef.current = window.setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [sessionState, isLoading]);

  // Derive presentation state
  const uiState = useMemo(() => {
    return derivePresentationState(sessionState, isLoading, error);
  }, [sessionState, isLoading, error]);

  // Hint button disabling rule:
  // Presentationally disabled during INDEPENDENT_TRANSFER, COMPLETED, or when loading
  // Backend remains authoritative and enforces coaching policies
  const isHintDisabled = useMemo(() => {
    if (isLoading) return true;
    if (!sessionState) return true;
    return (
      sessionState.state === 'INDEPENDENT_TRANSFER' ||
      sessionState.state === 'COMPLETED' ||
      sessionState.state === 'FAILED'
    );
  }, [sessionState, isLoading]);

  // Active entities extracted from current step result
  const activeTask = sessionState?.task ?? null;
  const activeEvaluation = sessionState?.evaluation ?? null;
  const activeIntervention = sessionState?.intervention ?? null;
  const activeDiagnosis = sessionState?.diagnosis ?? null;
  const candidateSkillState = sessionState?.candidate_state ?? null;
  const trainingContext = sessionState?.training_context ?? null;

  // Hydrate an existing coaching session from authoritative backend state
  const hydrateSession = useCallback(async (targetSessionId: string) => {
    if (!targetSessionId || targetSessionId === 'undefined') return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.getCoachingSession(targetSessionId);
      sessionIdRef.current = targetSessionId;
      sessionStateRef.current = result;
      setSessionId(targetSessionId);
      if (result.candidate_state?.candidate_id) {
        setCandidateId(result.candidate_state.candidate_id);
      }
      setSessionState(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Coaching session could not be restored.';
      setError(message);
      setSessionState(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setHydratedSession = useCallback((result: OrchestratorStepResultDTO) => {
    sessionStateRef.current = result;
    setSessionState(result);
    if (result.session_id) {
      sessionIdRef.current = result.session_id;
      setSessionId(result.session_id);
    }
    if (result.candidate_state?.candidate_id) {
      setCandidateId(result.candidate_state.candidate_id);
    }
  }, []);

  // Start Coaching Loop
  const startSession = useCallback(async (cId: string, customTopic?: string) => {
    setIsLoading(true);
    setError(null);
    setElapsedSeconds(0);
    setHintsCount(0);
    setHistory([]);
    setTelemetry(null);

    const newSessionId = `coach_sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    sessionIdRef.current = newSessionId;
    setSessionId(newSessionId);
    setCandidateId(cId);

    const trainingContext: TrainingContextDTO = resolveTrainingContext(customTopic);

    const payload: StartCoachingLoopPayload = {
      candidate_id: cId,
      session_id: newSessionId,
      training_context: trainingContext,
      config: {
        max_retries: 2,
        pass_threshold: 7.0,
      },
    };

    try {
      const result = await api.startTransferCoaching(payload);
      sessionStateRef.current = result;
      setSessionState(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start coaching session';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Start Coaching Loop Bridged from Real Interview
  const startSessionFromInterview = useCallback(
    async (cId: string, interviewSessionId: string, questionId?: string) => {
      setIsLoading(true);
      setError(null);
      setElapsedSeconds(0);
      setHintsCount(0);
      setHistory([]);
      setTelemetry(null);

      const newSessionId = `coach_sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      sessionIdRef.current = newSessionId;
      setSessionId(newSessionId);
      setCandidateId(cId);

      try {
        const result = await api.startCoachingFromInterview({
          candidate_id: cId,
          interview_session_id: interviewSessionId,
          session_id: newSessionId,
          question_id: questionId,
          config: {
            max_retries: 2,
            pass_threshold: 7.0,
          },
        });
        sessionStateRef.current = result;
        setSessionState(result);
      } catch (err: unknown) {
        const message =
          err instanceof Error
            ? err.message
            : 'Failed to bridge coaching session from interview';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // Submit Answer Step
  const submitStep = useCallback(
    async (answer: string) => {
      const activeSessionId = sessionIdRef.current || sessionId;
      const activeState = sessionStateRef.current || sessionState;

      if (!activeSessionId || !activeState) {
        setError('No active coaching session found');
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const result = await api.submitCoachingStep({
          session_id: activeSessionId,
          step_input: {
            candidate_answer: answer,
            response_time_seconds: elapsedSeconds,
            hints_requested_count: hintsCount,
          },
        });

        // Record history snapshot
        const newRecord: CoachingAttemptRecord = {
          step: history.length + 1,
          stageName: activeState.state,
          taskPrompt: activeState.task?.surface_context || 'Task prompt',
          answer,
          score: result.evaluation?.overall_score,
          passed: (result.evaluation?.overall_score ?? 0) >= 7.0,
          coachFeedback: result.evaluation?.coach_note || result.evaluation?.exemplar_answer,
          interventionContent: result.intervention?.content,
          timestamp: new Date().toLocaleTimeString(),
        };
        setHistory((prev) => [...prev, newRecord]);

        // Update backend state
        sessionStateRef.current = result;
        setSessionState(result);

        // If completed, fetch research telemetry asynchronously
        if (result.state === 'COMPLETED') {
          try {
            const tel = await api.getCoachingTelemetry(activeSessionId);
            setTelemetry(tel);
          } catch {
            // Telemetry fetch non-blocking for candidate UX
          }
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to submit coaching step';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, sessionState, elapsedSeconds, hintsCount, history]
  );

  // Presentation-only hint request counter
  const requestHint = useCallback(() => {
    if (isHintDisabled) return;
    setHintsCount((prev) => prev + 1);
  }, [isHintDisabled]);

  // Fetch telemetry manually (e.g. for Research Debug HUD)
  const fetchTelemetry = useCallback(async () => {
    if (!sessionId) return;
    try {
      const tel = await api.getCoachingTelemetry(sessionId);
      setTelemetry(tel);
    } catch (err: unknown) {
      console.warn('Telemetry fetch error:', err);
    }
  }, [sessionId]);

  const resetSession = useCallback(() => {
    setSessionId(null);
    setCandidateId(null);
    setSessionState(null);
    setTelemetry(null);
    setIsLoading(false);
    setError(null);
    setElapsedSeconds(0);
    setHintsCount(0);
    setHistory([]);
  }, []);

  return {
    sessionState,
    uiState,
    telemetry,
    isLoading,
    error,
    sessionId,
    candidateId,
    elapsedSeconds,
    hintsCount,
    isHintDisabled,
    activeTask,
    activeEvaluation,
    activeIntervention,
    activeDiagnosis,
    candidateSkillState,
    trainingContext,
    history,
    startSession,
    startSessionFromInterview,
    hydrateSession,
    setHydratedSession,
    submitStep,
    requestHint,
    resetSession,
    fetchTelemetry,
  };
}
