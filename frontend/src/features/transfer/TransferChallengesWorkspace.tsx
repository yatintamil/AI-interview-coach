import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  ArrowRight,
  CheckCircle2,
  Layers,
  Zap,
  AlertTriangle,
  RotateCcw,
  RefreshCw,
  Award,
} from 'lucide-react';
import { useAppSession } from '../../context/AppSessionContext';
import { api } from '../../services/api';
import {
  TransferLevel,
  formatTransferLevel,
  OrchestratorStepResultDTO,
} from '../../types/coaching';

interface ChallengeTask {
  id: string;
  skillId: string;
  title: string;
  level: TransferLevel;
  difficulty: 'Medium' | 'Hard' | 'Extreme';
  surfaceContext: string;
  coreInvariants: string[];
  surfaceDistractors: string[];
  expectedConcepts: string[];
}

const CHALLENGES_CATALOG: ChallengeTask[] = [
  {
    id: 'tc-l5-cache-coherence',
    skillId: 'Distributed Caching',
    title: 'Cross-Datacenter Lease Expiry & Cache Coherence',
    level: 'L5_INDEPENDENT_TRANSFER',
    difficulty: 'Extreme',
    surfaceContext:
      'High-frequency ticker dissemination cluster broadcasting quotes across 3 geo-distributed edge regions with strict sub-millisecond staleness bounds.',
    coreInvariants: [
      'Cache-aside vs Write-through consistency guarantees',
      'Bounded staleness window with master lease expiry',
      'Thundering herd & cache stampede mutex isolation',
    ],
    surfaceDistractors: [
      'Stock ticker NASDAQ protocol format',
      'Opening bell market volatility spikes',
      'Network frame MTU fragmentation',
    ],
    expectedConcepts: ['leases', 'cache_stampede', 'eventual_consistency', 'ttl_jitter'],
  },
  {
    id: 'tc-l4-rate-limiting',
    skillId: 'System Resilience',
    title: 'Hierarchical Token Bucket in Ephemeral Container Pods',
    level: 'L4_AMBIGUOUS_TRANSFER',
    difficulty: 'Hard',
    surfaceContext:
      'Multi-tenant healthcare integration gateway ingesting asymmetric HL7 FHIR records during mass disaster triage.',
    coreInvariants: [
      'Sliding window log vs Token bucket memory complexity',
      'Decentralized Redis synchronization with Lua script atomicity',
      'Tenant isolation across asymmetric priority tiers',
    ],
    surfaceDistractors: [
      'HIPAA compliance log redaction rules',
      'HL7 XML payload byte schemas',
      'REST vs GraphQL request routing',
    ],
    expectedConcepts: ['token_bucket', 'sliding_window', 'lua_atomicity', 'backpressure'],
  },
  {
    id: 'tc-l3-consensus-recovery',
    skillId: 'Distributed Consensus',
    title: 'Split-Brain Partition Resolution in Quorum Replicas',
    level: 'L3_FAR_TRANSFER',
    difficulty: 'Hard',
    surfaceContext:
      'Autonomous planetary exploration rover maintaining consistent navigational state during planetary occlusion radio blackouts.',
    coreInvariants: [
      'Quorum consensus (N/2 + 1) majority voting',
      'Monotonic term epochs and log divergence truncation',
      'Leader fencing tokens to invalidate stale masters',
    ],
    surfaceDistractors: [
      'Rover solar battery power constraints',
      'Martian atmospheric radio interference',
      'Wheel motor drive telemetry formats',
    ],
    expectedConcepts: ['raft', 'fencing_token', 'epoch_rollover', 'quorum_reads'],
  },
  {
    id: 'tc-l2-lockfree-ringbuffer',
    skillId: 'Concurrency & Synchronization',
    title: 'Single-Producer Multi-Consumer Ring Buffer with Zero Locks',
    level: 'L2_NEAR_TRANSFER',
    difficulty: 'Medium',
    surfaceContext:
      'Real-time uncompressed audio mixer dispatching 96kHz PCM streams from physical microphone buffer to 4 spatial convolution threads.',
    coreInvariants: [
      'Memory barriers and cacheline false-sharing padding',
      'Atomic CAS index wrap-around with power-of-two bitmask',
      'ABA sequence preservation with generational counters',
    ],
    surfaceDistractors: [
      'Audio sampling bitrates (44.1kHz vs 96kHz)',
      'Surround sound 7.1 channel panning',
    ],
    expectedConcepts: ['cas_atomic', 'memory_barrier', 'cacheline_padding', 'ring_buffer'],
  },
  {
    id: 'tc-l1-inverted-index',
    skillId: 'Algorithmic Retrieval',
    title: 'Real-Time Inverted Index with Incremental Postings Updates',
    level: 'L1_DIRECT_APPLICATION',
    difficulty: 'Medium',
    surfaceContext:
      'E-commerce product catalog search engine updating millions of inventory listings without blocking read queries.',
    coreInvariants: [
      'Read-copy-update (RCU) posting lists',
      'Skip-list pointer intersection complexity',
      'BM25 frequency score normalization',
    ],
    surfaceDistractors: [
      'Holiday discount coupon codes',
      'Currency conversion multipliers',
    ],
    expectedConcepts: ['posting_lists', 'rcu', 'bm25', 'skip_pointers'],
  },
  {
    id: 'tc-l0-lru-cache-definition',
    skillId: 'Data Structures & Algorithms',
    title: 'LRU Cache Invariants and Hash-Map Doubly-Linked List',
    level: 'L0_RECALL',
    difficulty: 'Medium',
    surfaceContext:
      'Standard key-value cache with fixed capacity requiring O(1) get and O(1) put operations.',
    coreInvariants: [
      'O(1) amortized hash table lookup',
      'Doubly-linked list node splicing for least-recently-used tracking',
      'Capacity boundary eviction policy',
    ],
    surfaceDistractors: [
      'Key format strings',
      'Item payload datatypes',
    ],
    expectedConcepts: ['hashmap', 'doubly_linked_list', 'o1_eviction', 'node_splicing'],
  },
];

export const TransferChallengesWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCandidate } = useAppSession();

  const [selectedFilter, setSelectedFilter] = useState<string>('ALL');
  const [activeSolvingTask, setActiveSolvingTask] = useState<ChallengeTask | null>(null);
  const [solutionDraft, setSolutionDraft] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [stepResult, setStepResult] = useState<OrchestratorStepResultDTO | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const filtered =
    selectedFilter === 'ALL'
      ? CHALLENGES_CATALOG
      : CHALLENGES_CATALOG.filter((c) => c.level === selectedFilter);

  const handleOpenTask = (task: ChallengeTask) => {
    setActiveSolvingTask(task);
    setSolutionDraft('');
    setSubmitError(null);
    setStepResult(null);
    setActiveSessionId(null);
  };

  const handleSubmitTransferSolution = async () => {
    if (!activeSolvingTask || !solutionDraft.trim()) return;
    if (!selectedCandidate) {
      setSubmitError('Please select or create a candidate profile first.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // 1. Initialize session anchored on the challenge task if not already started
      const sessionId =
        activeSessionId ||
        `transfer_${activeSolvingTask.id}_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

      if (!activeSessionId) {
        await api.startTransferCoaching({
          candidate_id: selectedCandidate.id,
          session_id: sessionId,
          training_context: {
            task_id: activeSolvingTask.id,
            question_text: `${activeSolvingTask.title}\n\nScenario Context: ${activeSolvingTask.surfaceContext}`,
            skill_id: activeSolvingTask.skillId,
            core_invariants: activeSolvingTask.coreInvariants,
            base_surface_context: activeSolvingTask.surfaceContext,
            base_expected_concepts: activeSolvingTask.expectedConcepts,
            transfer_level: activeSolvingTask.level,
            learning_objective: `Demonstrate independent transfer competence on ${activeSolvingTask.skillId}`,
          },
          config: {
            max_retries: 2,
            transfer_level: activeSolvingTask.level,
            independent_level: 'L5_INDEPENDENT_TRANSFER',
            pass_threshold: 7.0,
            independent_pass_threshold: 8.5,
            min_independent_distance: 0.7,
          },
        });
        setActiveSessionId(sessionId);
      }

      // 2. Submit candidate answer for real backend evaluation & diagnostic analysis
      const res = await api.submitCoachingStep({
        session_id: sessionId,
        step_input: {
          candidate_answer: solutionDraft,
          response_time_seconds: 45.0,
          hints_requested_count: 0,
        },
      });

      setStepResult(res);
    } catch (err: any) {
      setSubmitError(err.message || 'Transfer challenge evaluation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartTargetedCoaching = () => {
    if (stepResult?.session_id) {
      navigate(`/coaching/${stepResult.session_id}`);
    } else {
      navigate('/coaching');
    }
  };

  const evalScore = stepResult?.evaluation?.overall_score ?? 0;
  const isPass =
    evalScore >= 7.0 ||
    stepResult?.outcome === 'TRANSFER_SUCCESS' ||
    stepResult?.outcome === 'INDEPENDENT_SUCCESS';
  const hasDiagnosis =
    stepResult?.diagnosis &&
    stepResult.diagnosis.failure_type !== 'NONE';

  return (
    <div className="page-container">
      {/* Workspace Header */}
      <div className="page-header-row mb-6">
        <div>
          <h1 className="page-main-heading">Independent Transfer Task Arena</h1>
          <p className="page-subheading">
            Solve unfamiliar system tasks across changing surface contexts
            {selectedCandidate ? ` for ${selectedCandidate.full_name}` : ''}, targeting{' '}
            <strong>L5 Independent Transfer</strong>.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => navigate('/coaching')}
        >
          <Compass size={14} />
          <span>Launch Coaching Studio</span>
        </button>
      </div>

      {/* 6-Stage Transfer Taxonomy Visualizer */}
      <div className="surface-card p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="surface-header-title">
            <Layers size={16} className="text-indigo" />
            <h2 className="text-sm font-semibold">The 6-Stage Transfer Pedagogy Continuum</h2>
          </div>
          <span className="badge badge-brand">Faded Assistance Model</span>
        </div>

        <div className="taxonomy-grid">
          <div className="taxonomy-step">
            <div className="taxonomy-level">L0</div>
            <div className="taxonomy-name">Recall</div>
            <div className="taxonomy-desc">Surface reproduction from memory with zero variance.</div>
          </div>
          <div className="taxonomy-step">
            <div className="taxonomy-level">L1</div>
            <div className="taxonomy-name">Direct App</div>
            <div className="taxonomy-desc">Identical domain with standard parameter substitution.</div>
          </div>
          <div className="taxonomy-step">
            <div className="taxonomy-level">L2</div>
            <div className="taxonomy-name">Near Transfer</div>
            <div className="taxonomy-desc">Modified surface features within the same system domain.</div>
          </div>
          <div className="taxonomy-step">
            <div className="taxonomy-level">L3</div>
            <div className="taxonomy-name">Far Transfer</div>
            <div className="taxonomy-desc">Unfamiliar problem domain sharing underlying invariants.</div>
          </div>
          <div className="taxonomy-step">
            <div className="taxonomy-level">L4</div>
            <div className="taxonomy-name">Ambiguous</div>
            <div className="taxonomy-desc">Incomplete requirements with hidden invariant constraints.</div>
          </div>
          <div className="taxonomy-step active">
            <div className="taxonomy-level text-emerald">L5</div>
            <div className="taxonomy-name text-emerald">Independent Transfer</div>
            <div className="taxonomy-desc">
              Autonomous invariant reasoning under novel constraints with zero scaffolding.
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        <button
          type="button"
          className={`btn btn-sm ${selectedFilter === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setSelectedFilter('ALL')}
        >
          All Challenges ({CHALLENGES_CATALOG.length})
        </button>
        <button
          type="button"
          className={`btn btn-sm ${
            selectedFilter === 'L5_INDEPENDENT_TRANSFER' ? 'btn-primary' : 'btn-secondary'
          }`}
          onClick={() => setSelectedFilter('L5_INDEPENDENT_TRANSFER')}
        >
          L5 Independent Transfer
        </button>
        <button
          type="button"
          className={`btn btn-sm ${
            selectedFilter === 'L4_AMBIGUOUS_TRANSFER' ? 'btn-primary' : 'btn-secondary'
          }`}
          onClick={() => setSelectedFilter('L4_AMBIGUOUS_TRANSFER')}
        >
          L4 Ambiguous
        </button>
        <button
          type="button"
          className={`btn btn-sm ${
            selectedFilter === 'L3_FAR_TRANSFER' ? 'btn-primary' : 'btn-secondary'
          }`}
          onClick={() => setSelectedFilter('L3_FAR_TRANSFER')}
        >
          L3 Far Transfer
        </button>
        <button
          type="button"
          className={`btn btn-sm ${
            selectedFilter === 'L2_NEAR_TRANSFER' ? 'btn-primary' : 'btn-secondary'
          }`}
          onClick={() => setSelectedFilter('L2_NEAR_TRANSFER')}
        >
          L2 Near Transfer
        </button>
        <button
          type="button"
          className={`btn btn-sm ${
            selectedFilter === 'L1_DIRECT_APPLICATION' ? 'btn-primary' : 'btn-secondary'
          }`}
          onClick={() => setSelectedFilter('L1_DIRECT_APPLICATION')}
        >
          L1 Direct App
        </button>
        <button
          type="button"
          className={`btn btn-sm ${
            selectedFilter === 'L0_RECALL' ? 'btn-primary' : 'btn-secondary'
          }`}
          onClick={() => setSelectedFilter('L0_RECALL')}
        >
          L0 Recall
        </button>
      </div>

      {/* Task Grid */}
      <div className="transfer-arena-grid">
        {filtered.map((task) => (
          <div key={task.id} className="transfer-task-card">
            <div className="flex justify-between items-center">
              <span className="badge badge-brand">{formatTransferLevel(task.level)}</span>
              <span
                className={`badge ${
                  task.difficulty === 'Extreme'
                    ? 'badge-danger'
                    : task.difficulty === 'Hard'
                    ? 'badge-warning'
                    : 'badge-neutral'
                }`}
              >
                {task.difficulty}
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-primary">{task.title}</h3>
              <div className="text-xs text-muted mt-1">
                Competency: <span className="text-indigo">{task.skillId}</span>
              </div>
            </div>

            <p className="text-xs text-secondary leading-relaxed bg-surface-raised p-3 rounded-md border border-subtle">
              {task.surfaceContext}
            </p>

            <div>
              <div className="text-xs font-semibold text-muted uppercase mb-1">
                Core Invariants to Preserve:
              </div>
              <ul className="flex flex-col gap-1">
                {task.coreInvariants.map((inv, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 text-xs text-secondary">
                    <CheckCircle2 size={13} className="text-emerald shrink-0 mt-0.5" />
                    <span>{inv}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <div className="text-xs font-semibold text-muted uppercase mb-1">
                Surface Distractors to Filter:
              </div>
              <div className="flex flex-wrap gap-1">
                {task.surfaceDistractors.map((dis, idx) => (
                  <span key={idx} className="badge badge-neutral text-2xs">
                    {dis}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-2 mt-auto flex gap-2">
              <button
                type="button"
                className="btn btn-secondary btn-sm flex-1"
                onClick={() => handleOpenTask(task)}
              >
                <span>Attempt Task</span>
              </button>

              <button
                type="button"
                className="btn btn-primary btn-sm flex-1"
                onClick={() => navigate('/coaching')}
              >
                <Zap size={14} />
                <span>Coach Loop</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Interactive Solver & Backend Transfer Evaluation Modal */}
      {activeSolvingTask && (
        <div className="modal-backdrop-layer" role="dialog" aria-modal="true">
          <div className="modal-dialog-panel max-w-2xl">
            <div className="modal-dialog-header">
              <div className="modal-dialog-title">
                <Zap size={18} className="text-indigo" />
                <span>Transfer Challenge Workspace</span>
              </div>
              <button
                type="button"
                className="modal-close-button"
                onClick={() => setActiveSolvingTask(null)}
              >
                &times;
              </button>
            </div>

            <div className="modal-dialog-body flex flex-col gap-4">
              <div>
                <h4 className="text-base font-bold text-primary">{activeSolvingTask.title}</h4>
                <div className="badge badge-brand mt-1">
                  {formatTransferLevel(activeSolvingTask.level)}
                </div>
                <div className="text-xs text-secondary mt-2 bg-canvas p-3 rounded border border-subtle leading-relaxed">
                  <strong>Task Context:</strong> {activeSolvingTask.surfaceContext}
                </div>
              </div>

              <div>
                <label className="form-label" htmlFor="solution-draft">
                  Your Independent Solution
                </label>
                <textarea
                  id="solution-draft"
                  className="textarea-control font-mono text-xs"
                  rows={5}
                  placeholder="Explain how your solution preserves the underlying invariants (e.g. lease timing, partition recovery, consensus quorum) despite the novel domain framing..."
                  value={solutionDraft}
                  onChange={(e) => setSolutionDraft(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              {submitError && (
                <div className="p-3 bg-rose-950/40 border border-rose-500/50 rounded text-xs text-rose-300 flex items-center gap-2">
                  <AlertTriangle size={15} />
                  <span>{submitError}</span>
                </div>
              )}

              {/* Real Backend Evaluation & Failure Diagnostics Display */}
              {stepResult && (
                <div className="flex flex-col gap-3">
                  {/* Evaluation Score Card */}
                  <div
                    className={`p-4 rounded-lg border ${
                      isPass
                        ? 'bg-emerald-950/30 border-emerald-500/40'
                        : 'bg-rose-950/30 border-rose-500/40'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-bold uppercase text-primary">
                        Transfer Evaluation Result: {isPass ? 'PASSED' : 'TRANSFER DEFICIT DETECTED'}
                      </span>
                      <span className="text-sm font-mono font-bold text-indigo">
                        Score: {evalScore.toFixed(1)} / 10.0
                      </span>
                    </div>

                    {stepResult.evaluation?.coach_note && (
                      <p className="text-xs text-secondary leading-relaxed mt-1">
                        {stepResult.evaluation.coach_note}
                      </p>
                    )}

                    {stepResult.outcome === 'INDEPENDENT_SUCCESS' && (
                      <div className="mt-2 text-xs text-emerald flex items-center gap-1 font-semibold">
                        <Award size={14} />
                        <span>Validated Independent Transfer: Mastered with zero assistance!</span>
                      </div>
                    )}
                  </div>

                  {/* Stage 9: Structured Failure Diagnosis */}
                  {hasDiagnosis && stepResult.diagnosis && (
                    <div className="p-4 bg-amber-950/20 border border-amber-500/40 rounded-lg flex flex-col gap-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase text-amber flex items-center gap-1">
                          <AlertTriangle size={14} />
                          <span>Diagnosed Failure Root-Cause</span>
                        </span>
                        <span className="badge badge-warning text-2xs">
                          Confidence: {(stepResult.diagnosis.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <div className="text-xs font-semibold text-primary">
                        Barrier:{' '}
                        <span className="text-amber">{stepResult.diagnosis.failure_type}</span>{' '}
                        &bull; Affected Competency:{' '}
                        <span className="text-indigo">{stepResult.diagnosis.affected_skill}</span>
                      </div>

                      <p className="text-xs text-secondary leading-relaxed">
                        {stepResult.diagnosis.diagnostic_reasoning}
                      </p>

                      {/* Deterministic Signals */}
                      {stepResult.diagnosis.deterministic_signals && (
                        <div className="text-2xs text-muted flex flex-wrap gap-2 pt-1 border-t border-subtle">
                          {Object.entries(stepResult.diagnosis.deterministic_signals).map(
                            ([k, v]) => (
                              <span key={k}>
                                {k}: <strong>{String(v)}</strong>
                              </span>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Stage 10: Administered Targeted Intervention & Scaffold Level */}
                  {stepResult.intervention && (
                    <div className="p-4 bg-surface-raised border border-subtle rounded-lg flex flex-col gap-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase text-secondary flex items-center gap-1">
                          <Compass size={14} />
                          <span>Targeted Coaching Intervention</span>
                        </span>
                        <span className="badge badge-brand text-2xs">
                          Scaffold: {stepResult.intervention.scaffold_level}
                        </span>
                      </div>

                      <p className="text-xs text-secondary leading-relaxed">
                        {stepResult.intervention.content}
                      </p>

                      <div className="text-2xs text-muted italic">
                        Pedagogical Objective: {stepResult.intervention.pedagogical_intent}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="modal-dialog-footer">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setActiveSolvingTask(null)}
              >
                Close
              </button>

              {stepResult && !isPass && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setSolutionDraft('');
                    setStepResult(null);
                  }}
                >
                  <RotateCcw size={13} />
                  <span>Retry Attempt</span>
                </button>
              )}

              {stepResult && !isPass && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleStartTargetedCoaching}
                >
                  <Zap size={14} />
                  <span>Start Targeted Coaching & Recovery</span>
                  <ArrowRight size={13} />
                </button>
              )}

              {!stepResult && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleSubmitTransferSolution}
                  disabled={!solutionDraft.trim() || isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw size={13} className="animate-spin" />
                      <span>Evaluating Invariants...</span>
                    </>
                  ) : (
                    <span>Submit for Transfer Evaluation</span>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
