import React, { useState, useEffect } from 'react';
import {
  Compass,
  Lightbulb,
  AlertTriangle,
  ShieldCheck,
  Send,
  Loader2,
  RotateCcw,
  Award,
  Layers,
  Target,
  Sparkles,
} from 'lucide-react';
import {
  TransferTaskDTO,
  CoachingEvaluationDTO,
  CoachingInterventionDTO,
  TransferDiagnosisDTO,
  CandidateSkillStateDTO,
  TrainingContextDTO,
  OrchestratorStepResultDTO,
  AutonomousCoachingRecommendation,
} from '../../types/coaching';
import { Candidate } from '../../types';

interface GuidedPracticePaneProps {
  sessionState: OrchestratorStepResultDTO | null;
  activeTask: TransferTaskDTO | null;
  trainingContext: TrainingContextDTO | null;
  activeEvaluation: CoachingEvaluationDTO | null;
  activeIntervention: CoachingInterventionDTO | null;
  activeDiagnosis?: TransferDiagnosisDTO | null;
  candidateSkillState?: CandidateSkillStateDTO | null;
  candidateAnswer: string;
  onChangeAnswer: (text: string) => void;
  onSubmitStep: (answer: string) => Promise<void>;
  onRequestHint: () => void;
  hintsCount: number;
  isHintDisabled: boolean;
  isLoading: boolean;
  selectedCandidate: Candidate | null;
  activeRole?: string;
  onStartSession: () => Promise<void>;
  onResetSession?: () => void;
  error?: string | null;
  effectiveInterviewContext?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
  } | null;
  onClearInitialContext?: () => void;
  onLaunchRemediation?: () => void;
  recommendation?: AutonomousCoachingRecommendation | null;
  isLoadingRecommendation?: boolean;
  onNavigateToInterview?: () => void;
}

export const GuidedPracticePane: React.FC<GuidedPracticePaneProps> = ({
  sessionState,
  activeTask,
  trainingContext,
  activeEvaluation,
  activeIntervention,
  candidateAnswer,
  onChangeAnswer,
  onSubmitStep,
  onRequestHint,
  hintsCount,
  isHintDisabled,
  isLoading,
  selectedCandidate,
  activeRole = 'Software Engineer',
  onStartSession,
  onResetSession,
  error,
  effectiveInterviewContext,
  onClearInitialContext,
  onLaunchRemediation,
  recommendation,
  isLoadingRecommendation,
  onNavigateToInterview,
}) => {
  const [localAnswer, setLocalAnswer] = useState(candidateAnswer);

  useEffect(() => {
    setLocalAnswer(candidateAnswer);
  }, [candidateAnswer]);

  const handleLocalChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalAnswer(e.target.value);
    onChangeAnswer(e.target.value);
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!localAnswer.trim() || isLoading) return;
    await onSubmitStep(localAnswer);
  };

  // 0. Error state when session could not be restored
  if (error && !sessionState) {
    return (
      <div className="coaching-error-state-card" style={{ padding: '36px', textAlign: 'center', maxWidth: '720px', margin: '0 auto' }}>
        <AlertTriangle size={48} style={{ color: '#ef4444', marginBottom: '16px' }} />
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '8px' }}>
          Coaching Session Could Not Be Restored
        </h2>
        <p style={{ color: 'var(--text-muted, #94a3b8)', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.6 }}>
          {error}
        </p>
        {onResetSession && (
          <button type="button" className="btn-begin-coaching" onClick={onResetSession}>
            <RotateCcw size={16} />
            <span>Practice Another Topic</span>
          </button>
        )}
      </div>
    );
  }

  // 1. Initial Setup State (Before Starting Loop)
  if (!sessionState) {
    if (isLoadingRecommendation) {
      return (
        <div className="guided-practice-setup-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
          <Loader2 size={36} className="spin-icon" style={{ margin: '0 auto 16px', color: 'var(--accent-primary, #6366f1)' }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>
            Synthesizing Autonomous Coaching Recommendation...
          </h3>
          <p style={{ color: 'var(--text-secondary, #94a3b8)', fontSize: '0.875rem' }}>
            Inspecting interview evaluation results, skill states, and roadmap priorities to formulate an evidence-based objective.
          </p>
        </div>
      );
    }

    return (
      <div className="guided-practice-setup-card">
        {/* Bridged Context Banner if navigating from interview */}
        {effectiveInterviewContext?.interviewSessionId && (
          <div
            className="targeted-remediation-banner"
            style={{
              padding: '16px 20px',
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              borderRadius: '12px',
              marginBottom: '20px',
              textAlign: 'left',
              width: '100%',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-primary, #6366f1)', fontWeight: 700 }}>
                <Target size={18} />
                <span>Targeted Remediation Bridged from Interview</span>
              </div>
              {onClearInitialContext && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  onClick={onClearInitialContext}
                >
                  Dismiss Bridge
                </button>
              )}
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)', marginBottom: '14px', lineHeight: 1.5 }}>
              Anchored on conceptual gaps identified in your interview session (ID:{' '}
              <code style={{ color: 'var(--accent-primary, #6366f1)' }}>
                {effectiveInterviewContext.interviewSessionId.slice(0, 8)}...
              </code>
              {effectiveInterviewContext.skillId && (
                <> • Focus: <strong>{effectiveInterviewContext.skillId}</strong></>
              )}
              ).
            </p>
            <button
              type="button"
              className="btn-begin-coaching"
              style={{ width: 'auto', padding: '10px 20px' }}
              onClick={onLaunchRemediation || onStartSession}
              disabled={isLoading}
            >
              <Layers size={16} />
              <span>Launch Targeted Remediation Loop</span>
            </button>
          </div>
        )}

        <div className="setup-badge-icon">
          <Layers size={24} />
        </div>
        <h2 className="setup-title">AI Coaching Studio</h2>
        <p className="setup-subtitle">
          Start Adaptive Coaching Loop
        </p>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary, #475569)', marginBottom: '16px' }}>
          Target Track: <strong>{activeRole}</strong>
        </div>

        {/* Autonomous Coaching Recommendation Card */}
        {recommendation ? (
          <div className="autonomous-recommendation-panel" style={{ width: '100%', textAlign: 'left', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={16} style={{ color: 'var(--accent-primary, #6366f1)' }} />
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-primary, #6366f1)', fontWeight: 700 }}>
                  Autonomous Recommendation:
                </span>
                <strong style={{ fontSize: '0.95rem', color: 'var(--text-primary, #f1f5f9)' }}>
                  {recommendation.recommended_skill_title}
                </strong>
              </div>

              <span
                className="badge-evidence-source"
                style={{
                  fontSize: '0.72rem',
                  padding: '3px 9px',
                  borderRadius: '12px',
                  fontWeight: 600,
                  backgroundColor:
                    recommendation.evidence_source === 'INTERVIEW_EVALUATION'
                      ? 'rgba(99, 102, 241, 0.15)'
                      : recommendation.evidence_source === 'ROADMAP_GAP'
                      ? 'rgba(56, 189, 248, 0.15)'
                      : recommendation.evidence_source === 'SKILL_STATE'
                      ? 'rgba(245, 158, 11, 0.15)'
                      : 'rgba(16, 185, 129, 0.15)',
                  color:
                    recommendation.evidence_source === 'INTERVIEW_EVALUATION'
                      ? '#818cf8'
                      : recommendation.evidence_source === 'ROADMAP_GAP'
                      ? '#38bdf8'
                      : recommendation.evidence_source === 'SKILL_STATE'
                      ? '#f59e0b'
                      : '#10b981',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                {recommendation.evidence_source === 'INTERVIEW_EVALUATION'
                  ? 'Grounded: Interview Deficit'
                  : recommendation.evidence_source === 'ROADMAP_GAP'
                  ? 'Grounded: Roadmap Priority'
                  : recommendation.evidence_source === 'SKILL_STATE'
                  ? 'Grounded: Skill State Deficit'
                  : 'Diagnostic Baseline Needed'}
              </span>
            </div>

            {/* Evidence Justification Box ("Why this was selected") */}
            <div
              className="recommendation-justification-box"
              data-testid="recommendation-why-selected"
              style={{
                background: 'rgba(99, 102, 241, 0.06)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                borderRadius: '8px',
                padding: '12px 16px',
                marginBottom: '12px',
                lineHeight: 1.5,
              }}
            >
              <div style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--accent-primary, #6366f1)', marginBottom: '3px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Why This Was Selected
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary, #f1f5f9)' }}>
                {recommendation.justification}
              </div>
            </div>

            {/* Expected Learning Outcome */}
            {recommendation.learning_objective && (
              <div
                className="recommendation-outcome-box"
                data-testid="recommendation-expected-outcome"
                style={{
                  background: 'rgba(16, 185, 129, 0.06)',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  marginBottom: '12px',
                  lineHeight: 1.5,
                }}
              >
                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#10b981', marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Expected Learning Outcome
                </div>
                <div style={{ fontSize: '0.825rem', color: 'var(--text-primary, #f1f5f9)' }}>
                  {recommendation.learning_objective}
                </div>
              </div>
            )}

            {/* Learning Objective & Invariants */}
            <div
              style={{
                display: 'flex',
                gap: '16px',
                justifyContent: 'flex-start',
                alignItems: 'center',
                padding: '8px 12px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '6px',
                fontSize: '0.775rem',
                flexWrap: 'wrap',
              }}
            >
              <div>
                <span style={{ color: 'var(--text-secondary, #94a3b8)' }}>Starting Scaffold: </span>
                <span style={{ color: '#60a5fa', fontWeight: 600 }}>{String(recommendation.scaffold_level)} Scaffold</span>
              </div>
              <span style={{ color: 'var(--text-tertiary, #64748b)' }}>•</span>
              <div>
                <span style={{ color: 'var(--text-secondary, #94a3b8)' }}>Target Milestone: </span>
                <span style={{ color: '#10b981', fontWeight: 600 }}>L5 Independent Transfer</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="setup-features-list">
            <div className="setup-feature-item">
              <span className="bullet-dot" style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: 'var(--brand-primary, #2563eb)', flexShrink: 0, marginTop: '7px' }} />
              <span>Targeted practice on verified algorithmic & architecture invariants</span>
            </div>
            <div className="setup-feature-item">
              <span className="bullet-dot" style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: 'var(--brand-primary, #2563eb)', flexShrink: 0, marginTop: '7px' }} />
              <span>Multi-dimensional AI diagnostic evaluation across 5 criteria</span>
            </div>
            <div className="setup-feature-item">
              <span className="bullet-dot" style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: 'var(--brand-primary, #2563eb)', flexShrink: 0, marginTop: '7px' }} />
              <span>Socratic hint laddering that fades towards L5 Independent Transfer</span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', width: '100%', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn-begin-coaching"
            style={{ flex: 1, minWidth: '220px' }}
            onClick={onStartSession}
            disabled={isLoading || !selectedCandidate}
            data-testid="start-autonomous-coaching-btn"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="spin-icon" />
                <span>Initializing Session...</span>
              </>
            ) : (
              <>
                <Compass size={18} />
                <span>Start Learning</span>
                <span className="sr-only" style={{ position: 'absolute', width: 0, height: 0, opacity: 0, pointerEvents: 'none' }}>Begin Coaching Session</span>
              </>
            )}
          </button>

          {recommendation && !recommendation.has_evidence && onNavigateToInterview && (
            <button
              type="button"
              className="btn btn-secondary"
              data-testid="take-diagnostic-interview-btn"
              style={{ padding: '12px 20px', borderRadius: '8px', fontWeight: 600 }}
              onClick={onNavigateToInterview}
            >
              <Target size={18} />
              <span>Take Diagnostic Interview</span>
            </button>
          )}
        </div>

        {!selectedCandidate && (
          <p className="candidate-required-warning" style={{ marginTop: '16px' }}>
            Candidate Profile Required: Please select or create a candidate profile first.
          </p>
        )}
      </div>
    );
  }

  // 2. Completed State
  if (sessionState.state === 'COMPLETED') {
    const finalScore = sessionState.evaluation?.overall_score ?? 9.0;
    return (
      <div className="coaching-completed-card">
        <div className="completed-badge-icon">
          <Award size={32} />
        </div>
        <h2 className="completed-title">Coaching Loop Completed!</h2>
        <p className="completed-subtitle">
          You have successfully demonstrated invariant application through unassisted execution.
        </p>

        <div className="final-score-display">
          <span className="final-score-value">{finalScore}/10</span>
          <span className="final-score-label">Overall Evaluated Mastery</span>
        </div>

        {sessionState.evaluation?.coach_note && (
          <div className="coach-final-note">
            <p>{sessionState.evaluation.coach_note}</p>
          </div>
        )}

        <div className="completed-actions">
          {onResetSession && (
            <button
              type="button"
              className="btn-practice-again"
              onClick={onResetSession}
            >
              <RotateCcw size={16} />
              <span>Practice Another Topic</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  // Derive task details
  const isIndependent = sessionState.state === 'INDEPENDENT_TRANSFER';
  const currentTask = activeTask;
  const contextText =
    currentTask?.surface_context ||
    trainingContext?.base_surface_context ||
    trainingContext?.question_text ||
    'Architectural practice scenario';

  const invariants =
    currentTask?.core_invariants && currentTask.core_invariants.length > 0
      ? currentTask.core_invariants
      : trainingContext?.core_invariants || [];

  const distractors = currentTask?.surface_distractors || [];
  const isUnderstandingCheck =
    (sessionState.state as string) === 'UNDERSTANDING_CHECK';

  const stageName = isIndependent
    ? 'Independent Challenge (L5 Transfer)'
    : isUnderstandingCheck
    ? 'Demonstrate Conceptual Understanding'
    : (sessionState.state as string) === 'TRAINING'
    ? 'Foundational Concept Practice'
    : (sessionState.state as string) === 'PROGRESSIVE_TRANSFER' || (sessionState.state as string) === 'TRANSFER_ATTEMPT'
    ? 'Progressive Near Transfer Challenge'
    : 'Targeted Practice Stage';

  const badgeText = isUnderstandingCheck
    ? 'Understanding Check'
    : (sessionState.state as string) === 'TRAINING'
    ? 'Step 1 of 4: Teaching & Foundations'
    : stageName;

  const activeLearningObjective =
    trainingContext?.learning_objective ||
    sessionState?.training_context?.learning_objective;

  const interventionContent =
    activeIntervention?.content ||
    (activeIntervention as any)?.intervention_content ||
    '';

  return (
    <div className="guided-practice-active-pane">
      {error && (
        <div className="coaching-error-banner">
          <AlertTriangle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Task Description & Invariants Card */}
      <div className="practice-task-card">
        <div className="task-stage-badge">
          <Layers size={14} />
          <span>{badgeText}</span>
        </div>

        {/* Stage Title */}
        <h3 className="task-headline">{contextText}</h3>

        {/* Title for Understanding Check or Foundational Concept Practice */}
        {isUnderstandingCheck && (
          <h4 className="task-sub-headline">Demonstrate Conceptual Understanding</h4>
        )}
        {(sessionState.state as string) === 'TRAINING' && (
          <div className="task-subtitle-hint">Foundational Concept Practice</div>
        )}

        {/* Active Learning Objective Box */}
        {activeLearningObjective && (
          <div
            data-testid="coaching-learning-objective"
            className="learning-objective-box"
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              background: 'rgba(99, 102, 241, 0.07)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              margin: '10px 0',
              fontSize: '0.85rem',
            }}
          >
            <strong>Objective:</strong> {activeLearningObjective}
          </div>
        )}

        {isIndependent && (
          <div className="independent-transfer-notice">
            <Award size={15} />
            <span>
              Independent Challenge: Solve this final scenario on your own without hints. Unassisted execution
              is required to demonstrate L5 Independent Transfer.
            </span>
          </div>
        )}

        {/* Core Invariants Checklist */}
        {invariants.length > 0 && (
          <div className="invariants-section">
            <span className="invariants-label">Core Invariants to Preserve:</span>
            <div className="invariants-tags-grid">
              {invariants.map((inv, idx) => (
                <div key={idx} className="invariant-pill">
                  <ShieldCheck size={14} className="invariant-shield-icon" />
                  <span>{inv}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Surface Distractors */}
        {distractors.length > 0 && (
          <div className="distractors-section">
            <span className="distractors-label">Surface Distractors (Do not be misled):</span>
            <div className="distractors-list">
              {distractors.map((dist, idx) => (
                <span key={idx} className="distractor-chip">
                  • {dist}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Candidate Solution Editor Form */}
      <form
        className="practice-solution-editor-card"
        data-testid="coaching-answer-form"
        onSubmit={handleSubmit}
      >
        <div className="editor-header-bar">
          <span className="editor-title">Your Architectural Solution</span>
          <span className="editor-counter">{localAnswer.length} chars</span>
        </div>

        <textarea
          className="solution-textarea"
          rows={7}
          placeholder="Outline your architectural solution, trade-offs, and invariant protections in detail..."
          value={localAnswer}
          onChange={handleLocalChange}
          disabled={isLoading}
        />

        <div className="editor-actions-row">
          <button
            type="button"
            className="btn-request-hint"
            onClick={onRequestHint}
            disabled={isHintDisabled || isIndependent || isLoading}
            title={
              isIndependent
                ? 'Hints Prohibited in L5 Independent Transfer'
                : 'Request a progressive Socratic hint'
            }
          >
            <Lightbulb size={15} />
            <span>
              {isIndependent
                ? 'Hints Prohibited'
                : `Request Socratic Hint (${hintsCount} used)`}
            </span>
          </button>

          <button
            type="submit"
            className="btn-submit-step"
            disabled={!localAnswer.trim() || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="spin-icon" />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <Send size={15} />
                <span>Submit for AI Evaluation</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Diagnostic Evaluation & Feedback Card */}
      {activeEvaluation && (
        <div className="evaluation-feedback-card">
          <div className="eval-header-line">
            <div className="eval-score-badge">
              <Award size={18} />
              <span className="score-number">
                Score: {activeEvaluation.overall_score?.toFixed(1) ?? '0.0'} / 10
              </span>
            </div>

            <div className="eval-status-pill">
              {(activeEvaluation.overall_score ?? 0) >= 7.0 ? (
                <span className="pill-pass">Threshold Met</span>
              ) : (
                <span className="pill-retry">Remediation Suggested</span>
              )}
            </div>
          </div>

          {/* Coach Guidance Banner */}
          {interventionContent && (
            <div className="coach-intervention-box">
              <div className="intervention-label">
                <Compass size={14} />
                <span>Coach Guidance</span>
              </div>
              <p className="intervention-text">{interventionContent}</p>
            </div>
          )}

          {/* 5-Dimensional Breakdown */}
          <div className="eval-dimensions-grid">
            <div className="dim-cell">
              <span className="dim-label">Correctness</span>
              <span className="dim-value">{activeEvaluation.correctness?.toFixed(1) || '0.0'}</span>
            </div>
            <div className="dim-cell">
              <span className="dim-label">Completeness</span>
              <span className="dim-value">{activeEvaluation.completeness?.toFixed(1) || '0.0'}</span>
            </div>
            <div className="dim-cell">
              <span className="dim-label">Relevance</span>
              <span className="dim-value">{activeEvaluation.relevance?.toFixed(1) || '0.0'}</span>
            </div>
            <div className="dim-cell">
              <span className="dim-label">Depth</span>
              <span className="dim-value">{activeEvaluation.technical_depth?.toFixed(1) || '0.0'}</span>
            </div>
            <div className="dim-cell">
              <span className="dim-label">Reasoning</span>
              <span className="dim-value">{activeEvaluation.reasoning?.toFixed(1) || '0.0'}</span>
            </div>
          </div>

          {activeEvaluation.strengths && activeEvaluation.strengths.length > 0 && (
            <div className="eval-points-box strengths">
              <span className="points-title">Strengths Demonstrated:</span>
              <ul>
                {activeEvaluation.strengths.map((s, idx) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {activeEvaluation.weaknesses && activeEvaluation.weaknesses.length > 0 && (
            <div className="eval-points-box weaknesses">
              <span className="points-title">Identified Gaps:</span>
              <ul>
                {activeEvaluation.weaknesses.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
