import React, { useEffect, useState, useRef } from 'react';
import { api } from '../services/api';
import { Candidate } from '../types';
import {
  StudyInformation,
  ConsentRecord,
  ExperimentStepResult,
  ActiveSessionResponse,
} from '../types/research';
import {
  Card,
  Button,
  Badge,
  Alert,
  LoadingState,
  ProgressBar,
} from '../components/common';
import {
  FlaskConical,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Send,
  HelpCircle,
  LogOut,
  Award,
  BookOpen,
  Compass,
} from 'lucide-react';
import { useAppSession, useSafeNavigate } from '../context/AppSessionContext';

interface ExperimentStudyPageProps {
  selectedCandidate?: Candidate | null;
}

export const ExperimentStudyPage: React.FC<ExperimentStudyPageProps> = () => {
  const navigate = useSafeNavigate();
  const { selectedCandidate, candidates, setSelectedCandidateId } = useAppSession();

  // Study Protocol & Consent States
  const [studyInfo, setStudyInfo] = useState<StudyInformation | null>(null);
  const [consent, setConsent] = useState<ConsentRecord | null>(null);
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [loadingStudy, setLoadingStudy] = useState(true);
  const [submittingConsent, setSubmittingConsent] = useState(false);

  // Active Session & Progression States
  const [activeSession, setActiveSession] = useState<ActiveSessionResponse['session'] | null>(null);
  const [currentPrompt, setCurrentPrompt] = useState<string>('');
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [lastStepResult, setLastStepResult] = useState<ExperimentStepResult | null>(null);
  const [startingSession, setStartingSession] = useState(false);

  // Candidate Answer Form States
  const [candidateAnswer, setCandidateAnswer] = useState('');
  const [hintsRequested, setHintsRequested] = useState(0);
  const [submittingStep, setSubmittingStep] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Withdrawal States
  const [isWithdrawModalOpen, setIsWithdrawModalOpen] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState('');
  const [withdrawing, setWithdrawing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Timer for active task turn
  const timerRef = useRef<any>(null);

  useEffect(() => {
    if (activeSession && activeSession.status === 'IN_PROGRESS') {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [activeSession]);

  // If no candidate is selected yet, but candidates list exists, automatically select the first
  useEffect(() => {
    if (!selectedCandidate && candidates && candidates.length > 0) {
      setSelectedCandidateId(candidates[0].id);
    }
  }, [selectedCandidate, candidates, setSelectedCandidateId]);

  // Load study metadata unconditionally on mount
  useEffect(() => {
    let isMounted = true;
    api
      .getStudyInfo()
      .then((info) => {
        if (isMounted) {
          setStudyInfo(info);
          setLoadingStudy(false);
        }
      })
      .catch((err) => {
        console.warn('Failed to load study info:', err);
        if (isMounted) setLoadingStudy(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Load candidate-specific consent status and active session
  useEffect(() => {
    let isMounted = true;
    async function loadCandidateStudyState() {
      if (!selectedCandidate) {
        return;
      }
      setErrorMsg(null);
      try {
        try {
          const consentRec = await api.getParticipantConsent(selectedCandidate.id);
          if (isMounted) setConsent(consentRec);
        } catch {
          if (isMounted) setConsent(null);
        }

        const activeRes = await api.getActiveExperimentSession(selectedCandidate.id);
        if (isMounted && activeRes.has_active_session && activeRes.session) {
          setActiveSession(activeRes.session);
          setCurrentPhase(activeRes.session.current_phase);
          if (activeRes.current_task_prompt) {
            setCurrentPrompt(activeRes.current_task_prompt);
          }
        } else if (isMounted) {
          setActiveSession(null);
        }
      } catch (err: any) {
        if (isMounted) setErrorMsg(err.message || 'Failed to load candidate study data.');
      }
    }
    loadCandidateStudyState();
    return () => {
      isMounted = false;
    };
  }, [selectedCandidate]);

  // Handle explicit informed consent submission
  const handleConsentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate || !consentAgreed) return;
    setSubmittingConsent(true);
    setErrorMsg(null);
    try {
      const rec = await api.submitParticipantConsent(
        selectedCandidate.id,
        studyInfo?.consent_version || 'v1.0-feasibility-study',
        true
      );
      setConsent(rec);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to record consent.');
    } finally {
      setSubmittingConsent(false);
    }
  };

  // Start / Enroll in experimental session
  const handleStartSession = async () => {
    if (!selectedCandidate) return;
    setStartingSession(true);
    setErrorMsg(null);
    try {
      const res = await api.startExperiment(
        selectedCandidate.id,
        {
          condition: 'CONDITION_C', // Automatically balanced or assigned by server
          skill: 'distributed_caching',
          require_consent: true,
          informed_consent_signed: true,
          execution_provenance: 'HUMAN_PILOT',
        },
        'Feasibility_Study_Cohort_v1'
      );
      setLastStepResult(res);
      setCurrentPrompt(res.task_prompt);
      setCurrentPhase(res.phase);
      setElapsedSeconds(0);
      setCandidateAnswer('');

      // Refresh active session DTO
      const activeRes = await api.getActiveExperimentSession(selectedCandidate.id);
      if (activeRes.has_active_session && activeRes.session) {
        setActiveSession(activeRes.session);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to enroll in experiment session.');
    } finally {
      setStartingSession(false);
    }
  };

  // Submit candidate answer turn
  const handleSubmitTurn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSession || !candidateAnswer.trim()) return;
    setSubmittingStep(true);
    setErrorMsg(null);
    try {
      const res = await api.submitExperimentStep(
        activeSession.session_id,
        candidateAnswer.trim(),
        hintsRequested,
        elapsedSeconds
      );
      setLastStepResult(res);
      setCurrentPhase(res.phase);
      if (res.task_prompt) {
        setCurrentPrompt(res.task_prompt);
      }
      setCandidateAnswer('');
      setHintsRequested(0);
      setElapsedSeconds(0);

      // Refresh active session state
      const activeRes = await api.getActiveExperimentSession(selectedCandidate!.id);
      if (activeRes.has_active_session && activeRes.session) {
        setActiveSession(activeRes.session);
      } else {
        // Session completed
        setActiveSession(null);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit step.');
    } finally {
      setSubmittingStep(false);
    }
  };

  // Execute voluntary participant withdrawal
  const handleWithdrawConfirm = async () => {
    if (!selectedCandidate) return;
    setWithdrawing(true);
    setErrorMsg(null);
    try {
      const res = await api.withdrawParticipant(selectedCandidate.id, withdrawReason.trim() || undefined);
      setConsent({
        id: 'withdrawn',
        candidate_id: selectedCandidate.id,
        consent_status: 'WITHDRAWN',
        consent_version: studyInfo?.consent_version || 'v1.0-feasibility-study',
        consented_at: new Date().toISOString(),
        withdrawn_at: res.withdrawn_at,
        withdrawal_reason: withdrawReason,
        study_title: studyInfo?.title || 'Study',
      });
      setActiveSession(null);
      setIsWithdrawModalOpen(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to process withdrawal.');
    } finally {
      setWithdrawing(false);
    }
  };

  if (loadingStudy) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center' }}>
        <LoadingState message="Loading study protocol and participant enrollment..." />
      </div>
    );
  }

  // Calculate phase progression index
  const phases = ['PRETEST', 'TRAINING', 'POSTTEST', 'TRANSFER_TEST', 'INDEPENDENT_TRANSFER', 'COMPLETED'];
  const currentPhaseIndex = Math.max(0, phases.indexOf(currentPhase || 'PRETEST'));
  const progressPercent = Math.round(((currentPhaseIndex) / (phases.length - 1)) * 100);

  return (
    <div className="study-container" style={{ padding: '2rem', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Top Protocol Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
              }}
            >
              <FlaskConical size={20} />
            </div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>
              {studyInfo?.title || 'Transfer-Aware AI Interview Coaching Feasibility Study'}
            </h1>
          </div>
          <p style={{ margin: 0, color: 'var(--color-text-secondary, #6b7280)', fontSize: '0.9rem' }}>
            Participant: <strong>{selectedCandidate ? `${selectedCandidate.full_name} (${selectedCandidate.email})` : 'Select Candidate Below'}</strong> &bull; Investigator:{' '}
            {studyInfo?.principal_investigator}
          </p>
        </div>

        {consent?.consent_status === 'CONSENTED' && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsWithdrawModalOpen(true)}
            style={{ color: '#ef4444', borderColor: '#fca5a5' }}
          >
            <LogOut size={14} style={{ marginRight: '0.25rem' }} />
            Withdraw from Study
          </Button>
        )}
      </div>

      {errorMsg && (
        <Alert
          variant="danger"
          title="Experiment Error"
          onDismiss={() => setErrorMsg(null)}
          className="mb-4"
        >
          {errorMsg}
        </Alert>
      )}

      {/* VIEW 1: WITHDRAWN PARTICIPANT */}
      {consent?.consent_status === 'WITHDRAWN' ? (
        <Card>
          <div style={{ padding: '2.5rem', textAlign: 'center' }}>
            <AlertTriangle size={48} style={{ color: '#ef4444', marginBottom: '1rem' }} />
            <h2 style={{ color: '#b91c1c' }}>Participant Voluntary Withdrawal Recorded</h2>
            <p style={{ maxWidth: '600px', margin: '0 auto 1.5rem auto', color: 'var(--color-text-secondary, #6b7280)' }}>
              In accordance with study data policy, your voluntary withdrawal was recorded on{' '}
              {new Date(consent.withdrawn_at || consent.consented_at).toLocaleString()}. All ongoing experimental sessions
              have been marked as abandoned, and further trial tasks are permanently blocked. Your data has been excluded
              from primary research analysis exports.
            </p>
            <Badge variant="warning">Status: WITHDRAWN</Badge>
          </div>
        </Card>
      ) : consent?.consent_status !== 'CONSENTED' ? (
        /* VIEW 2: INFORMED CONSENT & ONBOARDING */
        <Card>
          <div style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <ShieldCheck size={24} style={{ color: '#10b981' }} />
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Participant Onboarding & Informed Consent</h2>
            </div>

            {!selectedCandidate && (
              <div style={{ marginBottom: '1.25rem', padding: '1rem', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px' }}>
                <strong style={{ display: 'block', marginBottom: '0.5rem', color: '#1e40af' }}>Select Participant Identity:</strong>
                <select
                  onChange={(e) => setSelectedCandidateId(e.target.value)}
                  style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid #93c5fd', width: '100%', maxWidth: '400px' }}
                  defaultValue=""
                >
                  <option value="" disabled>-- Select Candidate Profile --</option>
                  {candidates.map((c) => (
                    <option key={c.id} value={c.id}>{c.full_name} ({c.email})</option>
                  ))}
                </select>
              </div>
            )}

            <div
              style={{
                background: 'var(--color-bg-secondary, #f9fafb)',
                borderRadius: '8px',
                padding: '1.25rem',
                border: '1px solid var(--color-border, #e5e7eb)',
                marginBottom: '1.5rem',
                fontSize: '0.92rem',
                lineHeight: 1.6,
              }}
            >
              <h4 style={{ marginTop: 0, marginBottom: '0.5rem', color: '#374151' }}>1. Study Purpose</h4>
              <p style={{ marginBottom: '1rem' }}>{studyInfo?.purpose}</p>

              <h4 style={{ marginBottom: '0.5rem', color: '#374151' }}>2. Procedures</h4>
              <p style={{ marginBottom: '1rem' }}>{studyInfo?.procedures}</p>

              <h4 style={{ marginBottom: '0.5rem', color: '#374151' }}>3. Risks and Foreseeable Benefits</h4>
              <p style={{ marginBottom: '1rem' }}>{studyInfo?.risks_and_benefits}</p>

              <h4 style={{ marginBottom: '0.5rem', color: '#374151' }}>4. Voluntary Participation & Withdrawal</h4>
              <p style={{ marginBottom: '1rem' }}>{studyInfo?.voluntary_participation}</p>

              <h4 style={{ marginBottom: '0.5rem', color: '#374151' }}>5. Confidentiality & Data Handling</h4>
              <p style={{ marginBottom: '1rem' }}>{studyInfo?.data_handling}</p>

              <div
                style={{
                  background: '#fef3c7',
                  border: '1px solid #fde68a',
                  borderRadius: '6px',
                  padding: '0.75rem',
                  fontSize: '0.85rem',
                  color: '#92400e',
                }}
              >
                <strong>Institutional Protocol Notice:</strong> {studyInfo?.ethics_statement}
              </div>
            </div>

            <form onSubmit={handleConsentSubmit}>
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={consentAgreed}
                    onChange={(e) => setConsentAgreed(e.target.checked)}
                    style={{ marginTop: '0.25rem', width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                  <span style={{ fontSize: '0.95rem', color: '#374151', lineHeight: 1.5 }}>
                    I have read the study procedures, understand that my participation is voluntary, and give my explicit
                    informed consent to participate in this controlled research trial (Protocol Version:{' '}
                    <code>{studyInfo?.consent_version || 'v1.0-feasibility-study'}</code>).
                  </span>
                </label>
              </div>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                <Button variant="secondary" onClick={() => navigate('/profile')}>
                  Decline & Return to Dashboard
                </Button>
                <Button variant="primary" type="submit" disabled={!consentAgreed || submittingConsent || !selectedCandidate}>
                  {submittingConsent ? 'Recording Consent...' : !selectedCandidate ? 'Select Candidate to Consent' : 'Consent & Enroll in Study'}
                </Button>
              </div>
            </form>
          </div>
        </Card>
      ) : !activeSession && !lastStepResult?.is_complete ? (
        /* VIEW 3: READY TO ENROLL */
        <Card>
          <div style={{ padding: '2.5rem', textAlign: 'center' }}>
            <CheckCircle2 size={48} style={{ color: '#10b981', marginBottom: '1rem' }} />
            <h2>Informed Consent Verified</h2>
            <p style={{ color: 'var(--color-text-secondary, #6b7280)', maxWidth: '600px', margin: '0 auto 1.5rem auto' }}>
              Your informed consent is on file (Recorded on {new Date(consent.consented_at).toLocaleDateString()}). You are
              ready to begin the sequential 5-phase evaluation journey. You will be automatically assigned to an experimental
              treatment group to examine problem-solving transfer.
            </p>
            <Button variant="primary" size="lg" onClick={handleStartSession} disabled={startingSession}>
              {startingSession ? 'Enrolling in Study...' : 'Begin Experimental Assessment'}
            </Button>
          </div>
        </Card>
      ) : lastStepResult?.is_complete ? (
        /* VIEW 4: STUDY COMPLETED */
        <Card>
          <div style={{ padding: '2.5rem', textAlign: 'center' }}>
            <Award size={56} style={{ color: '#8b5cf6', marginBottom: '1rem' }} />
            <h2 style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>Experimental Assessment Completed!</h2>
            <p style={{ color: 'var(--color-text-secondary, #6b7280)', maxWidth: '650px', margin: '0 auto 1.5rem auto' }}>
              Thank you for participating! You have completed all 5 phases of the controlled experiment. Your responses have
              been persisted to the research database with verified transfer distance metrics.
            </p>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                maxWidth: '700px',
                margin: '0 auto 2rem auto',
                textAlign: 'left',
              }}
            >
              <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Final Trial Score</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#111827' }}>
                  {lastStepResult.score ? `${Math.round(lastStepResult.score * 100)}%` : 'N/A'}
                </div>
              </div>
              <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Evaluated Condition</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#6366f1' }}>
                  {lastStepResult.condition}
                </div>
              </div>
              <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>7-Day Retention Status</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#10b981' }}>
                  Scheduled
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <Button variant="primary" onClick={() => navigate('/analytics')}>
                View Comparative Analytics
              </Button>
            </div>
          </div>
        </Card>
      ) : (
        /* VIEW 5: ACTIVE EXPERIMENT TRIAL STEP */
        <div>
          {/* Phase Stepper Bar */}
          <Card className="mb-4" style={{ marginBottom: '1.5rem' }}>
            <div style={{ padding: '0.75rem 1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Compass size={18} style={{ color: '#6366f1' }} />
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Current Phase: {currentPhase}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Badge variant="primary">{activeSession?.condition}</Badge>
                  <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Elapsed: {elapsedSeconds}s</span>
                </div>
              </div>
              <ProgressBar value={progressPercent} max={100} />
            </div>
          </Card>

          {/* Feedback from previous step if present */}
          {lastStepResult?.feedback && (
            <Card className="mb-4" style={{ marginBottom: '1.5rem', border: '1px solid var(--border-card, #2d3b52)' }}>
              <div style={{ padding: '1rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--brand-primary, #2563eb)', fontSize: '0.95rem' }}>
                  Evaluator Feedback from Previous Step
                </h4>
                <p style={{ margin: '0 0 0.5rem 0', color: 'var(--text-secondary, #cbd5e1)', fontSize: '0.9rem' }}>
                  {lastStepResult.feedback}
                </p>
                {lastStepResult.score !== null && lastStepResult.score !== undefined && (
                  <Badge variant={lastStepResult.score >= 0.7 ? 'success' : 'warning'}>
                    Score: {Math.round(lastStepResult.score * 100)}%
                  </Badge>
                )}
              </div>
            </Card>
          )}

          {/* Active Question Prompt */}
          <Card className="mb-4" style={{ marginBottom: '1.5rem' }}>
            <div style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <BookOpen size={18} style={{ color: '#6366f1' }} />
                <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Task Instructions</h3>
              </div>
              <div
                style={{
                  background: 'var(--color-bg-secondary, #f9fafb)',
                  borderRadius: '6px',
                  padding: '1rem',
                  fontSize: '0.95rem',
                  lineHeight: 1.6,
                  color: '#1f2937',
                  border: '1px solid #e5e7eb',
                }}
              >
                {currentPrompt || 'Loading next architectural task...'}
              </div>
            </div>
          </Card>

          {/* Response Form */}
          <Card>
            <form onSubmit={handleSubmitTurn} style={{ padding: '1.25rem' }}>
              <label htmlFor="participant-answer" style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.95rem' }}>
                Formulate Your Architectural Solution:
              </label>
              <textarea
                id="participant-answer"
                rows={8}
                value={candidateAnswer}
                onChange={(e) => setCandidateAnswer(e.target.value)}
                placeholder="Describe your design invariants, trade-offs, eviction policies, and failure mitigation strategies..."
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  fontFamily: 'inherit',
                  fontSize: '0.92rem',
                  lineHeight: 1.5,
                  marginBottom: '1rem',
                  boxSizing: 'border-box',
                }}
                disabled={submittingStep}
              />

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {activeSession?.condition === 'CONDITION_C' ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setHintsRequested((prev) => prev + 1)}
                    disabled={submittingStep}
                  >
                    <HelpCircle size={14} style={{ marginRight: '0.25rem' }} />
                    Request Hint ({hintsRequested} requested)
                  </Button>
                ) : (
                  <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>Autonomous mode active</div>
                )}

                <Button variant="primary" type="submit" disabled={!candidateAnswer.trim() || submittingStep}>
                  <Send size={15} style={{ marginRight: '0.5rem' }} />
                  {submittingStep ? 'Evaluating Solution...' : 'Submit Architectural Solution'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Voluntary Withdrawal Modal */}
      {isWithdrawModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: '12px',
              padding: '1.5rem',
              maxWidth: '500px',
              width: '90%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
          >
            <h3 style={{ margin: '0 0 0.75rem 0', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={20} />
              Confirm Voluntary Withdrawal
            </h3>
            <p style={{ fontSize: '0.9rem', color: '#4b5563', lineHeight: 1.5, marginBottom: '1rem' }}>
              Are you sure you want to withdraw? Withdrawing will immediately abandon your active experiment session,
              cancel any pending follow-up assessments, and permanently block future trial tasks for this study. Your data
              will be excluded from primary research evaluation datasets.
            </p>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                Optional Reason for Withdrawal:
              </label>
              <input
                type="text"
                value={withdrawReason}
                onChange={(e) => setWithdrawReason(e.target.value)}
                placeholder="e.g. Time constraint, preferred standard practice"
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #d1d5db', boxSizing: 'border-box' }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <Button variant="secondary" onClick={() => setIsWithdrawModalOpen(false)} disabled={withdrawing}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleWithdrawConfirm}
                disabled={withdrawing}
                style={{ background: '#dc2626', borderColor: '#dc2626' }}
              >
                {withdrawing ? 'Processing Withdrawal...' : 'Confirm Withdrawal'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
