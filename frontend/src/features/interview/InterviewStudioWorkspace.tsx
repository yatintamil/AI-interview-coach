import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Video,
  Play,
  Send,
  HelpCircle,
  Clock,
  Compass,
  Code2,
  Terminal,
  Activity,
  StopCircle,
} from 'lucide-react';
import { Candidate, InterviewSession } from '../../types';
import { api } from '../../services/api';
import { WebcamFeed } from '../../components/studio/WebcamFeed';

interface InterviewStudioWorkspaceProps {
  selectedCandidate: Candidate | null;
  initialRole?: string;
  onNavigateToAnalytics?: () => void;
  onNavigateToCoaching?: (ctx?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
  }) => void;
}

export const InterviewStudioWorkspace: React.FC<InterviewStudioWorkspaceProps> = ({
  selectedCandidate,
  initialRole,
}) => {
  const { sessionId: routeSessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();

  const effectiveRole = selectedCandidate?.target_role || initialRole || 'Backend Systems Engineer';

  // Configuration State (for new session)
  const [targetRole, setTargetRole] = useState(effectiveRole);
  const [availableRoles, setAvailableRoles] = useState<Array<{ key: string; display_name: string }>>([]);
  const [interviewType, setInterviewType] = useState('TECHNICAL');
  const [difficultyLevel, setDifficultyLevel] = useState('HARD');
  const [questionCount, setQuestionCount] = useState(3);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [showAdvancedControls, setShowAdvancedControls] = useState<boolean>(false);

  useEffect(() => {
    const role = selectedCandidate?.target_role || initialRole;
    if (role) {
      setTargetRole(role);
      setAvailableRoles((prev) => {
        if (prev.length > 0 && !prev.some((p) => p.display_name.toLowerCase() === role.toLowerCase())) {
          return [{ key: '__custom__', display_name: role }, ...prev];
        }
        return prev;
      });
    }
  }, [selectedCandidate?.target_role, initialRole]);

  useEffect(() => {
    if (typeof api.listTargetRoles === 'function') {
      api
        .listTargetRoles()
        .then((data) => {
          if (data && data.length > 0) {
            const mapped = data.map((d) => ({ key: d.key, display_name: d.display_name }));
            if (initialRole && !mapped.some((m) => m.display_name.toLowerCase() === initialRole.toLowerCase())) {
              mapped.unshift({ key: '__custom__', display_name: initialRole });
            }
            setAvailableRoles(mapped);
          }
        })
        .catch(() => {});
    }
  }, [initialRole]);

  // Active Session State
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [latestEvaluation, setLatestEvaluation] = useState<any | null>(null);
  const [isRequestingHint, setIsRequestingHint] = useState(false);
  const [activeHint, setActiveHint] = useState<string | null>(null);
  const [hintTier, setHintTier] = useState<number>(0);

  // Turn Timer
  const [turnElapsedSeconds, setTurnElapsedSeconds] = useState(0);
  const timerRef = useRef<number | null>(null);

  // Load existing session if route param provided
  useEffect(() => {
    if (routeSessionId) {
      api
        .getInterview(routeSessionId)
        .then((sess) => {
          setSession(sess);
          if (sess.history && sess.history.length > 0) {
            const lastTurn = sess.history[sess.history.length - 1];
            if (lastTurn && lastTurn.evaluation) {
              setLatestEvaluation(lastTurn.evaluation);
            }
          }
          if (sess.status === 'COMPLETED') {
            navigate(`/debrief/${sess.id}`);
          }
        })
        .catch((err) => {
          console.warn('Failed to load session:', err);
        });
    }
  }, [routeSessionId, navigate]);

  // Turn timer
  useEffect(() => {
    if (session && session.status === 'IN_PROGRESS') {
      setTurnElapsedSeconds(0);
      timerRef.current = window.setInterval(() => {
        setTurnElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [session?.current_question_index, session?.status]);

  const handleCreateAndStartSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;
    setIsCreatingSession(true);

    try {
      const created = await api.createInterview({
        candidate_id: selectedCandidate.id,
        target_role: targetRole,
        interview_type: interviewType,
        difficulty_level: difficultyLevel,
        target_question_count: questionCount,
        coaching_mode: 'COACHING',
      });

      const started = await api.startInterview(created.id);
      setSession(started);
      navigate(`/interview/${started.id}`);
    } catch (err: any) {
      alert(`Failed to initialize adaptive interview: ${err.message}`);
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!session || !answerText.trim()) return;
    setIsSubmittingAnswer(true);
    setSubmissionError(null);

    try {
      const res = await api.submitAnswer(session.id, answerText, turnElapsedSeconds);
      if (res && res.evaluation) {
        setLatestEvaluation(res.evaluation);
      }
      setAnswerText('');
      setActiveHint(null);
      setHintTier(0);

      // Re-fetch session to get next question or completed state
      const updated = await api.getInterview(session.id);
      setSession(updated);

      if (updated.status === 'COMPLETED') {
        navigate(`/debrief/${updated.id}`);
      }
    } catch (err: any) {
      setSubmissionError(err.message || 'Evaluation failed. Your response has been preserved. Please retry.');
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleRequestHint = async () => {
    if (!session) return;
    setIsRequestingHint(true);
    try {
      const hint = await api.getInterviewHint(session.id, answerText);
      setActiveHint(hint.hint_text);
      setHintTier((prev) => prev + 1);
    } catch (err: any) {
      alert(`Failed to retrieve hint: ${err.message}`);
    } finally {
      setIsRequestingHint(false);
    }
  };

  const handleCompleteInterviewNow = async () => {
    if (!session) return;
    try {
      const completed = await api.completeInterview(session.id);
      navigate(`/debrief/${completed.id}`);
    } catch (err: any) {
      alert(`Failed to complete session: ${err.message}`);
    }
  };

  if (!selectedCandidate) {
    return (
      <div className="page-container">
        <div className="empty-state-frame">
          <div className="empty-state-icon">
            <Video size={24} />
          </div>
          <h2 className="empty-state-heading">Select a Candidate First</h2>
          <p className="empty-state-copy">
            Adaptive interviews are grounded in candidate resume memory and evaluated against target roles.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/profile')}
          >
            Go to Candidate Profiles
          </button>
        </div>
      </div>
    );
  }

  // 1. Configuration Stage (No active session)
  if (!session || session.status === 'CREATED') {
    return (
      <div className="page-container">
        <div className="assessment-studio-layout">
          <div className="surface-card">
            <div className="surface-header">
              <div className="surface-header-title">
                <h2>Mock Interview: {targetRole}</h2>
                <span className="sr-only">Configure Role-Aware Adaptive Interview Session</span>
              </div>
              <span className="badge badge-brand">Candidate: {selectedCandidate.full_name}</span>
            </div>

            <div className="surface-body">
              <form onSubmit={handleCreateAndStartSession} className="flex flex-col gap-3.5">
                {/* Primary Candidate-Facing Selection: Target Role */}
                <div className="form-field">
                  <label className="form-label text-sm font-semibold" htmlFor="role-select">
                    Target Engineering Role
                  </label>
                  {selectedCandidate?.target_role ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                      <span className="text-white font-medium text-sm">{targetRole}</span>
                      <span className="badge badge-brand text-xs" style={{ padding: '2px 6px' }}>Profile Anchored</span>
                    </div>
                  ) : (
                    <>
                      <p className="text-xs text-secondary mb-1.5">
                        Select your target role to launch your system-planned interview. Questions and follow-ups are synthesized to match this role's architectural depth.
                      </p>
                      <select
                        id="role-select"
                        className="select-control text-sm py-2 px-3"
                        value={targetRole}
                        onChange={(e) => {
                          const newRole = e.target.value;
                          setTargetRole(newRole);
                          if (newRole.toLowerCase().includes('lead') || newRole.toLowerCase().includes('manager')) {
                            setInterviewType('HYBRID');
                          } else {
                            setInterviewType('TECHNICAL');
                          }
                          setDifficultyLevel('HARD');
                          setQuestionCount(5);
                        }}
                      >
                        {availableRoles.length > 0 ? (
                          availableRoles.map((r) => (
                            <option key={r.key} value={r.display_name}>
                              {r.display_name}
                            </option>
                          ))
                        ) : (
                          <>
                            <option value="Backend Systems Engineer">Backend Systems Engineer</option>
                            <option value="Distributed Systems Engineer">Distributed Systems Engineer</option>
                            <option value="Distributed Database Reliability Engineer">Distributed Database Reliability Engineer</option>
                            <option value="Machine Learning Engineer">Machine Learning Engineer</option>
                            <option value="Cloud DevOps / SRE">Cloud DevOps / SRE</option>
                            <option value="Universal Software Engineering">Universal Software Engineering</option>
                          </>
                        )}
                      </select>
                    </>
                  )}
                </div>

                {/* System-Planned Autonomous Assessment Blueprint */}
                <div className="p-3 bg-surface-raised rounded border border-subtle flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Compass size={14} className="text-secondary" />
                      <span className="font-semibold text-xs text-primary">Autonomous Gauntlet Blueprint</span>
                    </div>
                    <span className="badge badge-brand text-[10px]">Autonomous Assessment</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs pt-0.5">
                    <div className="p-2 rounded bg-surface border border-subtle">
                      <span className="text-secondary block mb-0.5 text-[11px]">Planned Gauntlet</span>
                      <strong className="text-primary text-xs">{interviewType === 'TECHNICAL' ? 'Technical Architecture' : interviewType}</strong>
                    </div>
                    <div className="p-2 rounded bg-surface border border-subtle">
                      <span className="text-secondary block mb-0.5 text-[11px]">Calibrated Depth</span>
                      <strong className="text-primary text-xs">{difficultyLevel}: Invariant Strain</strong>
                    </div>
                    <div className="p-2 rounded bg-surface border border-subtle">
                      <span className="text-secondary block mb-0.5 text-[11px]">Assessment Protocol</span>
                      <strong className="text-primary text-xs text-emerald-600 dark:text-emerald-400">Adaptive Evidence-Driven</strong>
                    </div>
                  </div>

                  <div className="text-[11px] text-secondary leading-normal pt-0.5">
                    <strong>Resume-Grounded Probing:</strong> Questions are synthesized from candidate resume facts,
                    probing verifiable claims with increasing cognitive depth. Real-time hints adapt Socratically.
                  </div>
                </div>

                {/* Secondary Diagnostic & Research Controls (Disclosure) */}
                <div className="border-t border-subtle pt-2">
                  <button
                    type="button"
                    className="text-xs text-secondary hover:text-primary flex items-center gap-1.5 transition-colors"
                    onClick={() => setShowAdvancedControls((prev) => !prev)}
                  >
                    <span>{showAdvancedControls ? '▾ Hide' : '▸ Show'} Developer & Diagnostic Overrides</span>
                  </button>

                  {showAdvancedControls && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 mt-1.5 bg-surface-raised p-2.5 rounded border border-subtle">
                      <div className="form-field">
                        <label className="form-label text-xs" htmlFor="type-select">Override Gauntlet Type</label>
                        <select
                          id="type-select"
                          className="select-control text-xs py-1.5"
                          value={interviewType}
                          onChange={(e) => setInterviewType(e.target.value)}
                        >
                          <option value="TECHNICAL">TECHNICAL &mdash; Architecture & Invariants</option>
                          <option value="BEHAVIORAL">BEHAVIORAL &mdash; STAR Leadership</option>
                          <option value="HYBRID">HYBRID &mdash; Technical Depth + System Trade-offs</option>
                        </select>
                      </div>

                      <div className="form-field">
                        <label className="form-label text-xs" htmlFor="difficulty-select">Override Difficulty</label>
                        <select
                          id="difficulty-select"
                          className="select-control text-xs py-1.5"
                          value={difficultyLevel}
                          onChange={(e) => setDifficultyLevel(e.target.value)}
                        >
                          <option value="EASY">EASY &mdash; Foundational Invariants</option>
                          <option value="MEDIUM">MEDIUM &mdash; Complex Edge Cases</option>
                          <option value="HARD">HARD &mdash; Invariant Strain</option>
                        </select>
                      </div>

                      <div className="form-field">
                        <label className="form-label text-xs">Assessment Protocol</label>
                        <div className="px-3 py-1.5 rounded-lg bg-surface-secondary border border-subtle text-xs text-primary font-medium flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                          <span>Adaptive Evidence-Driven (Dynamic Saturation)</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    type="submit"
                    data-testid="btn-start-interview"
                    className="btn btn-primary btn-sm"
                    disabled={isCreatingSession}
                  >
                    <Play size={14} />
                    <span>{isCreatingSession ? 'Initializing Gauntlet...' : 'Start Planned Assessment'}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 2. Active Assessment Stage (Distraction-Free Assessment Workspace)
  const currentQ = session.current_question;
  const evidenceCoverage = Math.min(100, Math.round((session.evidence_coverage_ratio || 0) * 100));

  return (
    <div className="page-container">
      <div className="assessment-studio-layout">
        {/* Top Assessment Meta Bar: True Authoritative Information */}
        <div className="assessment-meta-bar">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-primary">{session.target_role}</span>
            <span className="badge badge-brand text-xs font-semibold">
              {currentQ?.stage_name || 'Core Invariant Reasoning'}
            </span>
            <span className="badge badge-neutral text-xs flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isSubmittingAnswer
                    ? 'bg-amber-400 animate-pulse'
                    : session.status === 'COMPLETED'
                    ? 'bg-emerald-500'
                    : session.status === 'CANCELLED'
                    ? 'bg-rose-500'
                    : 'bg-emerald-500 animate-pulse'
                }`}
              />
              <span>
                {isSubmittingAnswer
                  ? 'Evaluating response'
                  : session.status === 'IN_PROGRESS'
                  ? 'Assessment in progress'
                  : session.status === 'COMPLETED'
                  ? 'Assessment completed'
                  : session.status === 'CANCELLED'
                  ? 'Assessment incomplete'
                  : 'Awaiting evaluation'}
              </span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span data-testid="interview-session-id" className="text-[11px] text-muted font-mono hidden md:inline-block">
              Session: {session.id}
            </span>

            <div className="flex items-center gap-1.5 text-xs text-muted font-mono">
              <Clock size={13} className="text-indigo" />
              <span>Turn Time: {Math.floor(turnElapsedSeconds / 60)}:{('0' + (turnElapsedSeconds % 60)).slice(-2)}</span>
            </div>

            <div className="badge badge-neutral text-xs font-medium">
              {evidenceCoverage}% Evidence Coverage
            </div>

            {session.competencies_assessed_count !== undefined && (
              <div className="badge badge-neutral text-xs">
                {session.competencies_assessed_count}/{session.total_competencies_count || 5} Assessed
              </div>
            )}

            <button
              type="button"
              className="btn btn-outline btn-xs text-muted hover:text-danger flex items-center gap-1"
              onClick={handleCompleteInterviewNow}
              title="Conclude Interview & Compile Evidence Profile"
            >
              <StopCircle size={13} />
              <span>End Interview</span>
            </button>
          </div>
        </div>

        {/* Two-Column Responsive Workspace */}
        <div className="assessment-two-column-workspace">
          {/* Primary Column: Question Prompt & Candidate Formulation */}
          <div className="assessment-primary-column">
            {/* Question Card */}
            <div className="prompt-terminal-card">
              <div className="flex justify-between items-center text-xs text-muted pb-2 mb-2 border-b border-subtle">
                <div className="flex items-center gap-2">
                  <Terminal size={14} className="text-indigo" />
                  <span className="font-semibold text-primary text-xs">
                    Competency: {currentQ?.target_competency || currentQ?.topic || 'Not assessed'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge badge-neutral text-[11px] capitalize">
                    Difficulty: {currentQ?.difficulty || 'Medium'}
                  </span>
                </div>
              </div>

              {currentQ?.assessment_objective && (
                <div className="mb-2 text-[11px] text-muted italic">
                  Objective: {currentQ.assessment_objective}
                </div>
              )}

              <div className="py-1">
                <h3 className="text-base font-semibold text-primary leading-snug font-sans">
                  {currentQ?.question_text || 'Synthesizing next adaptive question based on demonstrated evidence...'}
                </h3>
              </div>

              {currentQ?.expected_concepts && currentQ.expected_concepts.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-subtle flex flex-wrap items-center gap-1.5 text-xs text-muted">
                  <span className="text-[11px] font-medium text-secondary">Target Invariants:</span>
                  <div className="flex flex-wrap gap-1">
                    {currentQ.expected_concepts.map((c, i) => (
                      <span key={i} className="font-mono text-indigo bg-surface-raised px-1.5 py-0.5 rounded text-[10px]">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Evaluation Feedback Banner (if prior turn evaluated) */}
            {latestEvaluation && (
              <div className="p-3 bg-surface-raised rounded border border-subtle text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-primary flex items-center gap-1.5">
                    <Activity size={13} className="text-indigo" />
                    <span>Prior Turn Assessment</span>
                  </span>
                  <span className="badge badge-brand text-[11px] font-mono">
                    Score: {typeof latestEvaluation.overall_score === 'number' ? latestEvaluation.overall_score.toFixed(1) : latestEvaluation.overall_score} / 10
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-1 text-[11px] text-secondary">
                  <div>Correctness: <strong>{typeof latestEvaluation.correctness === 'number' ? latestEvaluation.correctness.toFixed(1) : latestEvaluation.correctness}/10</strong></div>
                  <div>Completeness: <strong>{typeof latestEvaluation.completeness === 'number' ? latestEvaluation.completeness.toFixed(1) : latestEvaluation.completeness}/10</strong></div>
                  <div>Technical Depth: <strong>{typeof latestEvaluation.technical_depth === 'number' ? latestEvaluation.technical_depth.toFixed(1) : (latestEvaluation.reasoning || 0).toFixed?.(1) || 'N/A'}</strong></div>
                </div>
                {latestEvaluation.strengths && latestEvaluation.strengths.length > 0 && (
                  <div className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1">
                    <strong>Demonstrated:</strong> {latestEvaluation.strengths.join(', ')}
                  </div>
                )}
                {latestEvaluation.missing_concepts && latestEvaluation.missing_concepts.length > 0 && (
                  <div className="text-[11px] text-amber-600 dark:text-amber-400 mt-0.5">
                    <strong>Missing Invariants:</strong> {latestEvaluation.missing_concepts.join(', ')}
                  </div>
                )}
                {latestEvaluation.coach_conversational_response && (
                  <div className="mt-1 pt-1 border-t border-subtle text-muted text-[11px] italic">
                    "{latestEvaluation.coach_conversational_response}"
                  </div>
                )}
              </div>
            )}

            {/* Submission Error Banner with Retry */}
            {submissionError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded text-xs flex items-center justify-between">
                <span>Evaluation failed: {submissionError}</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-xs text-xs"
                  onClick={handleSubmitAnswer}
                  disabled={isSubmittingAnswer}
                >
                  Retry Submission
                </button>
              </div>
            )}

            {/* Candidate Response Console */}
            <div className="answer-submission-console">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold text-secondary flex items-center gap-1.5">
                  <Code2 size={13} />
                  <span>Candidate Technical Solution</span>
                </span>
                <span className="text-[11px] text-muted font-mono">{answerText.length} characters</span>
              </div>

              <textarea
                className="textarea-control font-mono text-xs leading-relaxed"
                rows={8}
                placeholder="Formulate your architecture solution, invariant proofs, trade-off analysis, or code logic..."
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                disabled={isSubmittingAnswer}
              />

              <div className="flex justify-between items-center mt-3 pt-2 border-t border-subtle">
                <div className="text-[11px] text-muted">
                  {isSubmittingAnswer
                    ? 'Evaluating response against role invariants...'
                    : 'Adaptive assessment: Response is evaluated to determine your next targeted question.'}
                </div>

                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleSubmitAnswer}
                  disabled={isSubmittingAnswer || !answerText.trim()}
                >
                  <Send size={13} />
                  <span>{isSubmittingAnswer ? 'Evaluating Response...' : 'Submit Answer & Advance'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Secondary Column: Media Preview, Socratic Scaffolding, Evidence Saturation */}
          <div className="assessment-secondary-column">
            {/* Compact Webcam Preview */}
            <div className="surface-card p-2.5">
              <div className="text-xs font-semibold text-secondary mb-1.5 flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <Activity size={12} className="text-indigo" />
                  <span>Media Preview</span>
                </span>
                <span className="badge badge-neutral text-[10px]">
                  {session.status === 'IN_PROGRESS' ? 'LIVE' : 'READY'}
                </span>
              </div>
              <div className="rounded overflow-hidden bg-canvas">
                <WebcamFeed isRecording={session.status === 'IN_PROGRESS'} />
              </div>
            </div>

            {/* Socratic Hint Scaffolding */}
            <div className="surface-card p-3 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-xs font-semibold text-secondary flex items-center gap-1">
                    <HelpCircle size={12} className="text-indigo" />
                    <span>Socratic Scaffolding</span>
                  </span>
                  <span className="badge badge-neutral text-[10px]">Tier {hintTier}</span>
                </div>

                {activeHint ? (
                  <div className="p-2 bg-surface-raised rounded border border-subtle text-xs text-secondary leading-relaxed">
                    <strong className="text-indigo block mb-0.5 text-[11px]">Coach Hint:</strong>
                    {activeHint}
                  </div>
                ) : (
                  <p className="text-[11px] text-muted leading-relaxed">
                    Need guidance on system invariants or edge conditions? Request a Socratic hint laddering step.
                  </p>
                )}
              </div>

              <div className="mt-2.5 flex justify-end">
                <button
                  type="button"
                  className="btn btn-secondary btn-xs"
                  onClick={handleRequestHint}
                  disabled={isRequestingHint || isSubmittingAnswer}
                >
                  <HelpCircle size={12} />
                  <span>{isRequestingHint ? 'Generating Hint...' : 'Request Socratic Hint'}</span>
                </button>
              </div>
            </div>

            {/* Role Evidence Saturation HUD */}
            <div className="surface-card p-2.5">
              <div className="flex justify-between items-center text-[11px] text-muted mb-1.5">
                <span className="font-semibold text-secondary">Evidence Saturation</span>
                <span className="font-mono font-semibold text-primary">{evidenceCoverage}%</span>
              </div>
              <div className="w-full bg-surface-raised h-1.5 rounded-full overflow-hidden mb-1.5">
                <div
                  className="bg-brand h-full transition-all duration-300"
                  style={{ width: `${evidenceCoverage}%` }}
                />
              </div>
              <div className="flex justify-between items-center text-[10px] text-muted">
                <span>
                  {session.competencies_assessed_count || 0} of {session.total_competencies_count || 5} Competencies
                </span>
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">Dynamic Assessment</span>
              </div>
              <p className="text-[10px] text-muted leading-normal mt-1.5 pt-1 border-t border-subtle">
                Questions continue dynamically until sufficient evidence is collected across your target role, or you choose to conclude.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
