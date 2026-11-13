import React, { useState } from 'react';
import {
  ArrowRight,
  AlertTriangle,
  Award,
  ShieldCheck,
  Send,
  Loader2,
  BookOpen,
  Filter,
  Compass,
  Target,
  X,
} from 'lucide-react';
import { TransferLevel, OrchestratorStepResultDTO } from '../../types/coaching';
import { Candidate } from '../../types';
import { api } from '../../services/api';

export interface ChallengeTask {
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

export const CHALLENGES_CATALOG: ChallengeTask[] = [
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

interface TransferChallengesPaneProps {
  selectedCandidate: Candidate | null;
  onSelectChallengeForCoaching?: (task: ChallengeTask) => void;
}

export const TransferChallengesPane: React.FC<TransferChallengesPaneProps> = ({
  selectedCandidate,
  onSelectChallengeForCoaching,
}) => {
  const [selectedFilter, setSelectedFilter] = useState<string>('ALL');
  const [activeTask, setActiveTask] = useState<ChallengeTask | null>(null);
  const [solutionDraft, setSolutionDraft] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [stepResult, setStepResult] = useState<OrchestratorStepResultDTO | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const filteredChallenges =
    selectedFilter === 'ALL'
      ? CHALLENGES_CATALOG
      : CHALLENGES_CATALOG.filter((c) => c.level === selectedFilter);

  const handleOpenTask = (task: ChallengeTask) => {
    setActiveTask(task);
    setSolutionDraft('');
    setSubmitError(null);
    setStepResult(null);
    setActiveSessionId(null);
  };

  const handleSubmitSolution = async () => {
    if (!activeTask || !solutionDraft.trim()) return;
    if (!selectedCandidate) {
      setSubmitError('Please select or create a candidate profile first.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const sessionId =
        activeSessionId ||
        `transfer_${activeTask.id}_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

      if (!activeSessionId) {
        await api.startTransferCoaching({
          candidate_id: selectedCandidate.id,
          session_id: sessionId,
          training_context: {
            task_id: activeTask.id,
            question_text: `${activeTask.title}\n\nScenario Context: ${activeTask.surfaceContext}`,
            skill_id: activeTask.skillId,
            core_invariants: activeTask.coreInvariants,
            base_surface_context: activeTask.surfaceContext,
            base_expected_concepts: activeTask.expectedConcepts,
            transfer_level: activeTask.level,
            learning_objective: `Demonstrate independent transfer competence on ${activeTask.skillId}`,
          },
          config: {
            max_retries: 2,
            transfer_level: activeTask.level,
            independent_level: 'L5_INDEPENDENT_TRANSFER',
            pass_threshold: 7.0,
            independent_pass_threshold: 8.5,
            min_independent_distance: 0.7,
          },
        });
        setActiveSessionId(sessionId);
      }

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

  return (
    <div className="transfer-challenges-pane">
      {/* Overview Banner */}
      <div className="transfer-taxonomy-hero">
        <div className="hero-badge">
          <Target size={16} />
          <span>Research Transfer Taxonomy</span>
        </div>
        <h2 className="hero-title">Unseen Scenarios & Independent Transfer</h2>
        <p className="hero-desc">
          Test whether you can apply core engineering invariants to novel, unseen situations with surface
          distractors. L5 Independent Transfer strictly requires solving without coaching assistance.
        </p>

        {/* Filter Pills */}
        <div className="transfer-filter-row">
          <span className="filter-label">
            <Filter size={13} />
            <span>Filter Level:</span>
          </span>
          <div className="filter-buttons-list">
            {[
              { id: 'ALL', label: 'All Levels' },
              { id: 'L0_RECALL', label: 'L0 Recall' },
              { id: 'L1_DIRECT_APPLICATION', label: 'L1 Direct' },
              { id: 'L2_NEAR_TRANSFER', label: 'L2 Near' },
              { id: 'L3_FAR_TRANSFER', label: 'L3 Far' },
              { id: 'L4_AMBIGUOUS_TRANSFER', label: 'L4 Ambiguous' },
              { id: 'L5_INDEPENDENT_TRANSFER', label: 'L5 Independent' },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                className={`btn-filter-pill ${selectedFilter === f.id ? 'active' : ''}`}
                onClick={() => setSelectedFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid: Catalog List & Solving Area */}
      <div className="transfer-main-layout">
        {/* Left: Challenge Cards List */}
        <div className="challenges-grid-column">
          {filteredChallenges.map((task) => {
            const isSelected = activeTask?.id === task.id;
            const isL5 = task.level === 'L5_INDEPENDENT_TRANSFER';

            return (
              <div
                key={task.id}
                className={`challenge-card ${isSelected ? 'selected' : ''} ${isL5 ? 'l5-card' : ''}`}
                onClick={() => handleOpenTask(task)}
              >
                <div className="card-top-meta">
                  <span className={`level-badge level-${task.level.toLowerCase()}`}>
                    {task.level.replace('_', ' ')}
                  </span>
                  <span className="difficulty-tag">{task.difficulty}</span>
                </div>

                <h4 className="card-task-title">{task.title}</h4>
                <p className="card-task-context">{task.surfaceContext}</p>

                <div className="card-invariants-preview">
                  <ShieldCheck size={13} className="shield-icon" />
                  <span>{task.coreInvariants.length} Core Invariants Tested</span>
                </div>

                <div className="card-bottom-row">
                  <span className="card-skill-tag">{task.skillId}</span>
                  <button type="button" className="btn-card-select">
                    <span>{isSelected ? 'Active' : 'Attempt Challenge'}</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Active Solver & Evaluation Pane */}
        <div className="challenge-solver-column">
          {activeTask ? (
            <div className="active-solver-card">
              <div className="solver-header-bar">
                <div>
                  <span className="solver-level-tag">{activeTask.level.replace('_', ' ')}</span>
                  <h3 className="solver-title">{activeTask.title}</h3>
                </div>
                <button
                  type="button"
                  className="btn-close-task"
                  onClick={() => setActiveTask(null)}
                  aria-label="Close task solver"
                >
                  <X size={16} />
                </button>
              </div>

              {activeTask.level === 'L5_INDEPENDENT_TRANSFER' && (
                <div className="l5-requirement-callout">
                  <Award size={16} className="callout-icon" />
                  <div>
                    <strong>L5 Independent Transfer Standard:</strong>
                    <p>
                      Independent mastery requires evidence of solving this unseen task without coaching
                      assistance (0 hints requested). Correct answers copied from examples or aided by hints
                      do not qualify.
                    </p>
                  </div>
                </div>
              )}

              <div className="solver-scenario-box">
                <span className="box-title">Scenario Description:</span>
                <p>{activeTask.surfaceContext}</p>
              </div>

              <div className="solver-invariants-box">
                <span className="box-title">Engineering Invariants to Satisfy:</span>
                <ul>
                  {activeTask.coreInvariants.map((inv, idx) => (
                    <li key={idx}>{inv}</li>
                  ))}
                </ul>
              </div>

              {/* Solution Editor */}
              <div className="solver-input-box">
                <label className="box-title">Your Architectural Implementation:</label>
                <textarea
                  className="solution-textarea"
                  rows={6}
                  placeholder="Articulate your technical solution, protocol contracts, data structures, and how you preserve the core invariants..."
                  value={solutionDraft}
                  onChange={(e) => setSolutionDraft(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              {submitError && (
                <div className="coaching-error-banner">
                  <AlertTriangle size={14} />
                  <span>{submitError}</span>
                </div>
              )}

              <div className="solver-actions-row">
                <button
                  type="button"
                  className="btn-submit-transfer"
                  onClick={handleSubmitSolution}
                  disabled={!solutionDraft.trim() || isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={16} className="spin-icon" />
                      <span>Evaluating Transfer Invariants...</span>
                    </>
                  ) : (
                    <>
                      <Send size={15} />
                      <span>Submit Solution for Evaluation</span>
                    </>
                  )}
                </button>
              </div>

              {/* Step Result Evaluation Debrief */}
              {stepResult?.evaluation && (
                <div className="transfer-eval-result-card">
                  <div className="eval-result-header">
                    <div className="score-badge">
                      <Award size={18} />
                      <span>{stepResult.evaluation.overall_score.toFixed(1)} / 10.0</span>
                    </div>

                    <div className="outcome-pill">
                      {stepResult.evaluation.overall_score >= 7.0 ? (
                        <span className="pill-pass">Transfer Succeeded</span>
                      ) : (
                        <span className="pill-retry">Transfer Deficit Detected</span>
                      )}
                    </div>
                  </div>

                  {stepResult.evaluation.strengths && stepResult.evaluation.strengths.length > 0 && (
                    <div className="eval-section-block">
                      <span className="section-title">Demonstrated Strengths:</span>
                      <ul>
                        {stepResult.evaluation.strengths.map((s, idx) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {stepResult.evaluation.weaknesses && stepResult.evaluation.weaknesses.length > 0 && (
                    <div className="eval-section-block">
                      <span className="section-title">Identified Deficits:</span>
                      <ul>
                        {stepResult.evaluation.weaknesses.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {onSelectChallengeForCoaching && (
                    <button
                      type="button"
                      className="btn-bridge-to-coaching"
                      onClick={() => onSelectChallengeForCoaching(activeTask)}
                    >
                      <BookOpen size={14} />
                      <span>Practice Identified Gaps in Coaching Studio</span>
                      <ArrowRight size={13} />
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="solver-placeholder-card">
              <Compass size={28} className="placeholder-icon" />
              <h3>Select a Challenge Task</h3>
              <p>Choose an unseen scenario from the catalog on the left to attempt independent transfer.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
