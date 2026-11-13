import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Candidate, CandidateProfile, InterviewSession, Question, TurnEvaluation, CandidateClaim, CoachHint } from '../types';
import { api } from '../services/api';
import { useAppSession, useSafeNavigate } from '../context/AppSessionContext';
import { WebcamFeed } from '../components/studio/WebcamFeed';
import { AudioVisualizer } from '../components/studio/AudioVisualizer';
import { EvidenceGraphHUD } from '../components/studio/EvidenceGraphHUD';
import { InterviewSetupCard } from '../components/studio/InterviewSetupCard';
import { StageProgressionHUD } from '../components/studio/StageProgressionHUD';
import { SessionDebriefCard } from '../components/studio/SessionDebriefCard';
import {
  CheckCircle,
  Award,
  Clock,
  ArrowRight,
  ShieldCheck,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  Send,
  Terminal,
  Bot,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';

interface InterviewStudioPageProps {
  selectedCandidate: Candidate | null;
  initialRole?: string;
  onNavigateToAnalytics: () => void;
  onNavigateToCoaching?: (context: { interviewSessionId: string; questionId?: string; skillId?: string; coachingSessionId?: string }) => void;
}

const OMNIROLE_DEFAULT = 'Adaptive Omnirole (Universal Competencies)';

export const InterviewStudioPage: React.FC<InterviewStudioPageProps> = ({
  selectedCandidate,
  initialRole,
  onNavigateToAnalytics,
  onNavigateToCoaching,
}) => {
  const { sessionId: routeSessionId } = useParams<{ sessionId?: string }>();
  const navigate = useSafeNavigate();
  const { interviewSessionId, setInterviewSessionId, setSelectedCandidateId } = useAppSession();

  // Session Configuration Form & Candidate Profile
  const candidateRole = selectedCandidate?.target_role || initialRole;
  const effectiveRole = candidateRole && candidateRole !== OMNIROLE_DEFAULT ? candidateRole : OMNIROLE_DEFAULT;
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [targetRole, setTargetRole] = useState(effectiveRole);
  const [targetRoles, setTargetRoles] = useState<string[]>([effectiveRole]);
  const [customRoleDescription, setCustomRoleDescription] = useState('');
  const [isCustomRole, setIsCustomRole] = useState(Boolean(initialRole && initialRole !== OMNIROLE_DEFAULT));
  const [interviewType, setInterviewType] = useState('TECHNICAL');
  const [difficulty, setDifficulty] = useState('EASY');
  const [questionCount, setQuestionCount] = useState(5);
  const [coachingMode, setCoachingMode] = useState('COACHING');

  // Active Session State
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null);
  const [loadingSession, setLoadingSession] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [candidateAnswer, setCandidateAnswer] = useState('');
  const [latestEvaluation, setLatestEvaluation] = useState<TurnEvaluation | null>(null);
  const [coachHint, setCoachHint] = useState<CoachHint | null>(null);
  const [loadingHint, setLoadingHint] = useState(false);
  const [showExemplar, setShowExemplar] = useState(false);

  // Candidate Evidence Graph Claims
  const [claims, setClaims] = useState<CandidateClaim[]>([]);

  // Studio Telemetry & Controls
  const [speechEnabled, setSpeechEnabled] = useState(true);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [isVoiceDictating, setIsVoiceDictating] = useState(false);
  const [dictationInterim, setDictationInterim] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Speech Recognition Reference
  const recognitionRef = useRef<any>(null);

  // Route-based session hydration
  useEffect(() => {
    if (routeSessionId && routeSessionId !== 'undefined') {
      setInterviewSessionId(routeSessionId);
      if (!activeSession || activeSession.id !== routeSessionId) {
        setLoadingSession(true);
        api
          .getInterview(routeSessionId)
          .then((loaded) => {
            setActiveSession(loaded);
            setCurrentQuestion(loaded.current_question || null);
            if (loaded.status === 'COMPLETED') {
              navigate(`/debrief/${loaded.id}`, { replace: true });
            } else {
              setIsTimerRunning(true);
            }
            if (loaded.candidate_id && (!selectedCandidate || selectedCandidate.id !== loaded.candidate_id)) {
              setSelectedCandidateId(loaded.candidate_id);
            }
          })
          .catch((err) => {
            console.warn('Failed to load interview session from route:', err);
          })
          .finally(() => {
            setLoadingSession(false);
          });
      }
    }
  }, [routeSessionId, activeSession?.id, selectedCandidate?.id, setInterviewSessionId, setSelectedCandidateId, navigate]);

  // Load Candidate Profile & Claims (With Strict State Isolation)
  useEffect(() => {
    // 1. Immediately reset active interview state on candidate change to prevent data bleed
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (isVoiceDictating && recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      setIsVoiceDictating(false);
    }

    if (!routeSessionId) {
      setActiveSession(null);
      setCurrentQuestion(null);
      setCandidateAnswer('');
      setLatestEvaluation(null);
      setCoachHint(null);
      setIsTimerRunning(false);
      setElapsedSeconds(0);
    }
    setClaims([]);
    setProfile(null);

    if (initialRole && initialRole !== OMNIROLE_DEFAULT) {
      setTargetRole(initialRole);
      setIsCustomRole(true);
    } else {
      setTargetRole(OMNIROLE_DEFAULT);
      setIsCustomRole(false);
    }

    // 2. Fetch selected candidate's isolated profile and claims
    if (selectedCandidate) {
      api.getCandidateProfile(selectedCandidate.id)
        .then((p) => {
          setProfile(p);
          if (p?.seniority_level && p.seniority_level.toLowerCase().includes('fresher')) {
            setDifficulty('EASY');
          }
        })
        .catch(() => {});

      // Fetch or initialize Candidate Claims for this specific candidate
      api.getCandidateClaims(selectedCandidate.id)
        .then((loadedClaims) => {
          if (loadedClaims && loadedClaims.length > 0) {
            setClaims(loadedClaims);
          } else {
            api.getCandidateProfile(selectedCandidate.id).then((p) => {
              if (p?.skills) {
                const initial: CandidateClaim[] = p.skills.slice(0, 7).map((s, idx) => ({
                  id: `claim-${idx + 1}`,
                  candidate_id: selectedCandidate.id,
                  skill_name: s.name,
                  claim_text: `Proficiency in ${s.name} (${s.proficiency || 'Intermediate'}) asserted on profile.`,
                  complexity: idx > 3 ? 'ADVANCED' : 'INTERMEDIATE',
                  verification_status: 'UNVERIFIED',
                  confidence_score: 0.5,
                  verified_quotes: [],
                  probe_count: 0,
                }));
                setClaims(initial);
              }
            }).catch(() => {});
          }
        })
        .catch(() => {});
    }
  }, [selectedCandidate?.id, initialRole]);

  // Session Timer Effect
  useEffect(() => {
    let interval: any = null;
    if (isTimerRunning) {
      interval = setInterval(() => setElapsedSeconds((prev) => prev + 1), 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isTimerRunning]);

  // Setup Web Speech Recognition
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        if (final) {
          setCandidateAnswer((prev) => `${prev} ${final}`.trim());
          setDictationInterim('');
        } else {
          setDictationInterim(interim);
        }
      };

      recognition.onerror = (event: any) => {
        if (event.error === 'not-allowed') {
          alert('Microphone access was denied. Please allow microphone permissions in your browser to use voice dictation.');
        }
        setIsVoiceDictating(false);
      };

      recognition.onend = () => {
        setIsVoiceDictating(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  // Text-to-Speech Vocalizer for AI Inquisitor
  const speakQuestion = (text: string) => {
    if (!speechEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      window.speechSynthesis.resume(); // Prevents silent stall in Chromium engines

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.98;
      utterance.pitch = 1.0;

      const voices = window.speechSynthesis.getVoices();
      const naturalVoice = voices.find((v) => v.name.includes('Natural') || v.name.includes('Google') || v.lang === 'en-US');
      if (naturalVoice) utterance.voice = naturalVoice;

      utterance.onstart = () => setIsAiSpeaking(true);
      utterance.onend = () => setIsAiSpeaking(false);
      utterance.onerror = () => setIsAiSpeaking(false);

      window.speechSynthesis.speak(utterance);
    } catch {
      setIsAiSpeaking(false);
    }
  };

  const toggleVoiceDictation = () => {
    if (!recognitionRef.current) {
      alert('Speech Recognition is not supported in this browser. You can type your answer directly.');
      return;
    }
    if (isVoiceDictating) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Handled
      }
      setIsVoiceDictating(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsVoiceDictating(true);
      } catch (err: any) {
        console.warn('Recognition start error:', err);
        setIsVoiceDictating(false);
      }
    }
  };

  const handleCreateAndStartInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;

    setCreating(true);
    setLatestEvaluation(null);
    setCoachHint(null);
    try {
      const roleToSend = isCustomRole && targetRole.trim() ? targetRole.trim() : OMNIROLE_DEFAULT;
      const rolesToSend = isCustomRole && targetRoles.length > 0 ? targetRoles : [roleToSend];
      const customDescToSend = isCustomRole && customRoleDescription.trim() ? customRoleDescription.trim() : undefined;
      const session = await api.createInterview({
        candidate_id: selectedCandidate.id,
        target_role: roleToSend,
        target_roles: rolesToSend,
        custom_role_description: customDescToSend,
        interview_type: interviewType,
        difficulty_level: difficulty,
        target_question_count: questionCount,
        coaching_mode: coachingMode,
      });

      const started = await api.startInterview(session.id);
      setActiveSession(started);
      setInterviewSessionId(started.id);
      setCurrentQuestion(started.current_question || null);
      setCandidateAnswer('');
      setElapsedSeconds(0);
      setIsTimerRunning(true);
      navigate(`/interview/${started.id}`);

      if (started.current_question) {
        speakQuestion(started.current_question.question_text);
        updateClaimStatusForQuestion(started.current_question.topic);
      }
    } catch (err: any) {
      alert(`Failed to launch interview studio: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  const handleRequestCoachHint = async () => {
    if (!activeSession || loadingHint) return;
    setLoadingHint(true);
    try {
      const hint = await api.getInterviewHint(activeSession.id, candidateAnswer);
      setCoachHint(hint);
    } catch (err: any) {
      alert(`Coach hint unavailable: ${err.message}`);
    } finally {
      setLoadingHint(false);
    }
  };

  const updateClaimStatusForQuestion = (topic: string) => {
    setClaims((prev) =>
      prev.map((c) => {
        if (topic.toLowerCase().includes(c.skill_name.toLowerCase()) || c.skill_name.toLowerCase().includes(topic.toLowerCase())) {
          return {
            ...c,
            verification_status: c.verification_status === 'UNVERIFIED' ? 'PROBED' : c.verification_status,
            probe_count: c.probe_count + 1,
          };
        }
        return c;
      })
    );
  };

  const handleSubmitAnswer = async () => {
    if (!activeSession || !candidateAnswer.trim() || submitting) return;

    if (isVoiceDictating && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsVoiceDictating(false);
    }

    setSubmitting(true);
    setIsTimerRunning(false);

    try {
      const result = await api.submitAnswer(
        activeSession.id,
        candidateAnswer.trim(),
        elapsedSeconds
      );

      setLatestEvaluation(result.evaluation);

      // Bayesian update to Candidate Evidence Graph claims based on score
      if (currentQuestion) {
        const turnScore = result.evaluation.overall_score;
        const answerSample = candidateAnswer.trim().slice(0, 140);

        setClaims((prev) =>
          prev.map((c) => {
            const matches =
              currentQuestion.topic.toLowerCase().includes(c.skill_name.toLowerCase()) ||
              c.skill_name.toLowerCase().includes(currentQuestion.topic.toLowerCase());
            if (matches) {
              const newStatus = turnScore >= 7.0 ? 'VERIFIED' : turnScore >= 4.5 ? 'PROBED' : 'CONTESTED';
              const newConfidence = Math.min(0.98, Math.max(0.2, (c.confidence_score + (turnScore / 10)) / 2));
              const quotes = [...c.verified_quotes];
              if (!quotes.includes(answerSample)) quotes.push(answerSample);

              return {
                ...c,
                verification_status: newStatus,
                confidence_score: Number(newConfidence.toFixed(2)),
                verified_quotes: quotes,
              };
            }
            return c;
          })
        );
      }

      if (result.is_completed) {
        const completed = await api.getInterview(activeSession.id);
        setActiveSession(completed);
        setCurrentQuestion(null);
        setInterviewSessionId(completed.id);
        navigate(`/debrief/${completed.id}`);
      } else {
        setCurrentQuestion(result.next_question || null);
        setActiveSession((prev) => prev ? {
          ...prev,
          current_question_index: result.current_question_index,
          evidence_coverage_ratio: result.evidence_coverage_ratio,
          competencies_assessed_count: result.competencies_assessed_count,
          total_competencies_count: result.total_competencies_count,
        } : prev);
        if (result.next_question) {
          speakQuestion(result.next_question.question_text);
          updateClaimStatusForQuestion(result.next_question.topic);
        }
      }
    } catch (err: any) {
      alert(`Evaluation error: ${err.message}`);
      setIsTimerRunning(true);
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextTurn = () => {
    setLatestEvaluation(null);
    setCandidateAnswer('');
    setDictationInterim('');
    setCoachHint(null);
    setShowExemplar(false);
    setElapsedSeconds(0);
    setIsTimerRunning(true);
    if (currentQuestion) {
      speakQuestion(currentQuestion.question_text);
    }
  };

  const handleResetSession = () => {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (isVoiceDictating && recognitionRef.current) recognitionRef.current.stop();

    setActiveSession(null);
    setCurrentQuestion(null);
    setLatestEvaluation(null);
    setCandidateAnswer('');
    setDictationInterim('');
    setCoachHint(null);
    setShowExemplar(false);
    setElapsedSeconds(0);
    setIsTimerRunning(false);
    setInterviewSessionId(undefined);
    navigate('/interview');
  };

  const effectiveSessionId = activeSession?.id || (routeSessionId && routeSessionId !== 'undefined' ? routeSessionId : interviewSessionId);

  if (loadingSession) {
    return (
      <div className="studio-panel fade-in" style={{ textAlign: 'center', padding: '60px 20px', maxWidth: '700px', margin: '40px auto' }}>
        <Loader2 size={36} className="spin" style={{ color: 'var(--accent-primary)', marginBottom: '16px' }} />
        <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>Loading Interview Session...</h3>
        <p style={{ color: 'var(--text-muted)' }}>Retrieving active interview state for session {effectiveSessionId}</p>
        <div data-testid="interview-session-id" style={{ display: 'none' }}>{effectiveSessionId}</div>
      </div>
    );
  }

  if (!selectedCandidate) {
    return (
      <div className="studio-panel fade-in" style={{ textAlign: 'center', padding: '64px 20px', color: 'var(--text-dim)' }}>
        {effectiveSessionId && (
          <div data-testid="interview-session-id" style={{ display: 'none' }}>{effectiveSessionId}</div>
        )}
        <Bot size={44} style={{ margin: '0 auto 16px auto', opacity: 0.35, color: '#818cf8' }} />
        <h3>No Candidate Profile Selected</h3>
        <p style={{ marginTop: '8px' }}>Select a candidate from the top navbar or create one to launch the Interview Studio.</p>
      </div>
    );
  }

  // ==========================================
  // VIEW 1: STUDIO CONFIGURATION & LAUNCH DECK
  // ==========================================
  if (!activeSession) {
    return (
      <div className="fade-in">
        {effectiveSessionId && (
          <div data-testid="interview-session-id" style={{ display: 'none' }}>{effectiveSessionId}</div>
        )}
        <InterviewSetupCard
          selectedCandidate={selectedCandidate}
          profile={profile}
          targetRole={targetRole}
          setTargetRole={setTargetRole}
          targetRoles={targetRoles}
          setTargetRoles={setTargetRoles}
          customRoleDescription={customRoleDescription}
          setCustomRoleDescription={setCustomRoleDescription}
          isCustomRole={isCustomRole}
          setIsCustomRole={setIsCustomRole}
          interviewType={interviewType}
          setInterviewType={setInterviewType}
          difficulty={difficulty}
          setDifficulty={setDifficulty}
          questionCount={questionCount}
          setQuestionCount={setQuestionCount}
          coachingMode={coachingMode}
          setCoachingMode={setCoachingMode}
          creating={creating}
          onLaunch={handleCreateAndStartInterview}
        />
      </div>
    );
  }

  // ==========================================
  // VIEW 2: COMPLETED INTERVIEW EXECUTIVE REPORT
  // ==========================================
  if (activeSession.status === 'COMPLETED') {
    return (
      <div className="fade-in">
        <SessionDebriefCard
          session={activeSession}
          candidate={selectedCandidate}
          onNavigateToAnalytics={onNavigateToAnalytics}
          onRetake={handleResetSession}
          onNavigateToCoaching={onNavigateToCoaching}
        />
      </div>
    );
  }

  // ==========================================
  // VIEW 3: LIVE MULTIMODAL COMMAND DECK (3 PANES)
  // ==========================================
  const currentStageIndex = currentQuestion?.stage_index || Math.min(Math.max((currentQuestion?.question_index || 0) + 1, 1), 5);
  const stageName = currentQuestion?.stage_name || (
    currentStageIndex === 1 ? 'Orientation & Resume Grounding' :
    currentStageIndex === 2 ? 'Core Mechanics & Invariants' :
    currentStageIndex === 3 ? 'Scalable Systems & Architecture' :
    currentStageIndex === 4 ? 'Incident Debugging & Triage' : 'STAR Leadership & Ownership'
  );
  const currentTurn = (currentQuestion?.question_index || 0) + 1;

  const handleConcludeInterview = async () => {
    if (!activeSession) return;
    const confirmStop = window.confirm(
      "Conclude the interview now? The AI evaluator will compile a comprehensive assessment report from all evidence collected so far."
    );
    if (!confirmStop) return;
    try {
      setSubmitting(true);
      const finished = await api.completeInterview(activeSession.id, 'CANDIDATE_REQUESTED');
      setActiveSession(finished);
      setCurrentQuestion(null);
      setInterviewSessionId(finished.id);
      navigate(`/debrief/${finished.id}`);
    } catch (err: any) {
      alert(`Error concluding interview: ${err?.message || err}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fade-in">
      <StageProgressionHUD
        currentStageIndex={currentStageIndex}
        totalStages={5}
        currentTurn={currentTurn}
        evidenceCoverageRatio={activeSession.evidence_coverage_ratio}
        competenciesAssessedCount={activeSession.competencies_assessed_count}
        totalCompetenciesCount={activeSession.total_competencies_count}
        stageName={stageName}
        targetCompetency={currentQuestion?.target_competency}
        assessmentObjective={currentQuestion?.assessment_objective}
        isFollowup={currentQuestion?.is_followup}
        onConcludeInterview={handleConcludeInterview}
      />
      <div className="studio-grid" style={{ marginTop: '16px' }}>
        {/* ========================================================= */}
        {/* DECK LEFT: AI INQUISITOR PANEL */}
        {/* ========================================================= */}
        <div className="deck-inquisitor">
          <div className="studio-panel">
            <div className="studio-panel-header">
              <div className="studio-panel-title">
                <Bot size={16} color="#818cf8" />
                <span>AI Inquisitor Lead</span>
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ padding: '4px 6px' }}
                onClick={() => setSpeechEnabled(!speechEnabled)}
                title={speechEnabled ? 'Mute AI Voice Synthesis' : 'Enable AI Voice Synthesis'}
              >
                {speechEnabled ? <Volume2 size={15} color="#818cf8" /> : <VolumeX size={15} color="var(--text-dim)" />}
              </button>
            </div>

            <div className="inquisitor-avatar-card">
              <div className="inquisitor-glyph">
                <Terminal size={20} />
              </div>
              <div>
                <div style={{ fontSize: '0.925rem', fontWeight: 600, color: '#fff' }}>
                  Dr. Alex Vance
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Principal Systems Inquisitor
                </div>
                <div style={{ marginTop: '4px' }}>
                  {isAiSpeaking ? (
                    <span className="inquisitor-status-pill pill-speaking">
                      <span className="pulse-dot" /> SPEAKING
                    </span>
                  ) : submitting ? (
                    <span className="inquisitor-status-pill pill-evaluating">
                      <span className="pulse-dot" /> ANALYZING EVIDENCE
                    </span>
                  ) : (
                    <span className="inquisitor-status-pill pill-listening">
                      <span className="pulse-dot" /> LISTENING
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Multi-Tier Engine Telemetry Badge */}
            <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: 'var(--text-dim)', background: 'rgba(99, 102, 241, 0.06)', padding: '5px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <ShieldCheck size={13} color="#818cf8" />
              <span>Grounded Engine Active &middot; Zero Quota Protected</span>
            </div>

            {/* AI Speech Wave Visualizer */}
            <div style={{ marginTop: '14px' }}>
              <AudioVisualizer isActive={isAiSpeaking} color="#818cf8" height={36} mode="wave" />
            </div>

            {/* Turn & Evidence Telemetry */}
            <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Evidence Coverage</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: '#818cf8', fontWeight: 600 }}>
                  {Math.min(100, Math.round((activeSession.evidence_coverage_ratio || 0) * 100))}%
                </span>
              </div>
              <div className="progress-bar-container">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${Math.min(100, Math.round((activeSession.evidence_coverage_ratio || 0) * 100))}%` }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '0.78rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Questions Answered</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: '#fff' }}>
                  {activeSession.current_question_index}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', fontSize: '0.78rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Competencies Assessed</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>
                  {activeSession.competencies_assessed_count || 0} / {activeSession.total_competencies_count || 5}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Elapsed Time</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontFamily: 'var(--font-mono)', color: '#e2e8f0' }}>
                  <Clock size={14} color="#818cf8" />
                  <span>{Math.floor(elapsedSeconds / 60)}:{(elapsedSeconds % 60).toString().padStart(2, '0')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* DECK CENTER: ACTIVE QUESTION & CANDIDATE WORKSPACE */}
        {/* ========================================================= */}
        <div className="deck-canvas">
          {/* Active Question Hero */}
          {currentQuestion && (
            <div className="question-hero-card">
              {/* Stage Lifecycle Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="inquisitor-status-pill pill-active" style={{ fontSize: '0.675rem' }}>
                    STAGE {currentQuestion.stage_index || 1}/{currentQuestion.total_stages || 5}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#fff', fontWeight: 600 }}>
                    {currentQuestion.stage_name || 'Foundational Orientation'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: '#818cf8' }}>
                    TOPIC: {currentQuestion.topic}
                  </span>
                  <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: 'var(--status-probed)' }}>
                    {currentQuestion.difficulty}
                  </span>
                </div>
              </div>

              {/* Warm Conversational Lead-In & Live Web Skill */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
                {currentQuestion.researched_skill && (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', background: 'rgba(37, 99, 235, 0.12)', color: '#93c5fd', border: '1px solid #1d4ed8', padding: '2px 8px', borderRadius: '4px' }}>
                    Live Web Researched: <strong>{currentQuestion.researched_skill}</strong>
                  </span>
                )}
                {currentQuestion.coach_lead_in && (
                  <span style={{ fontSize: '0.8rem', color: '#cbd5e1', fontStyle: 'italic' }}>
                    "{currentQuestion.coach_lead_in}"
                  </span>
                )}
              </div>

              <div className="question-text">
                {currentQuestion.question_text}
              </div>

              {/* Resume Grounding Anchor */}
              {currentQuestion.resume_evidence && (
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', background: 'var(--bg-canvas)', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', marginTop: '4px' }}>
                  <ShieldCheck size={16} style={{ color: '#818cf8', flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <strong style={{ color: '#fff' }}>Grounded in your background:</strong> {currentQuestion.resume_evidence}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Turn Evaluation Feedback (If just evaluated) */}
          {latestEvaluation && (
            <div className="studio-panel fade-in" style={{ border: '1px solid var(--status-verified-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle size={18} color="var(--status-verified)" />
                  <strong style={{ fontSize: '1rem', color: '#fff' }}>Turn Evaluation Completed</strong>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Turn Score:</span>
                  <span className="score-badge" style={{ fontSize: '1rem', padding: '4px 10px' }}>
                    {latestEvaluation.overall_score.toFixed(1)}/10
                  </span>
                </div>
              </div>

              {/* Rubric Breakdown Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '14px', background: 'var(--bg-surface)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                    <span>Correctness</span>
                    <span>{latestEvaluation.correctness}</span>
                  </div>
                  <div className="progress-bar-container" style={{ height: '3px' }}>
                    <div className="progress-bar-fill" style={{ width: `${latestEvaluation.correctness * 10}%` }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                    <span>Completeness</span>
                    <span>{latestEvaluation.completeness}</span>
                  </div>
                  <div className="progress-bar-container" style={{ height: '3px' }}>
                    <div className="progress-bar-fill" style={{ width: `${latestEvaluation.completeness * 10}%` }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                    <span>Tech Depth</span>
                    <span>{latestEvaluation.technical_depth}</span>
                  </div>
                  <div className="progress-bar-container" style={{ height: '3px' }}>
                    <div className="progress-bar-fill" style={{ width: `${latestEvaluation.technical_depth * 10}%` }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                    <span>Reasoning</span>
                    <span>{latestEvaluation.reasoning}</span>
                  </div>
                  <div className="progress-bar-container" style={{ height: '3px' }}>
                    <div className="progress-bar-fill" style={{ width: `${latestEvaluation.reasoning * 10}%` }} />
                  </div>
                </div>
              </div>

              {/* Empathy Intelligence & Real-Time Coach Conversation */}
              <div style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(236, 72, 153, 0.08) 100%)', border: '1px solid rgba(99, 102, 241, 0.3)', padding: '12px 16px', borderRadius: '8px', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#a5b4fc', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                    <Bot size={15} color="#818cf8" />
                    AI Coach Conversation & Empathy
                  </div>
                  {latestEvaluation.detected_feeling && (
                    <span style={{ fontSize: '0.72rem', background: 'rgba(244, 63, 94, 0.15)', color: '#fda4af', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '2px 10px', borderRadius: '12px', fontWeight: 600 }}>
                      Coach Sensed: {latestEvaluation.detected_feeling}
                    </span>
                  )}
                </div>

                <div style={{ fontSize: '0.875rem', color: '#f8fafc', lineHeight: '1.5', fontStyle: 'italic', marginBottom: '8px' }}>
                  "{latestEvaluation.coach_conversational_response || latestEvaluation.coach_note}"
                </div>

                {latestEvaluation.socratic_scaffold && (
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', background: 'rgba(15, 23, 42, 0.6)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.8rem', color: '#e2e8f0' }}>
                    <Lightbulb size={14} style={{ color: '#fbbf24', flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <strong style={{ color: '#fef08a' }}>Socratic Scaffolding: </strong>
                      {latestEvaluation.socratic_scaffold}
                    </div>
                  </div>
                )}
              </div>

              {/* Staff Engineer Exemplar Model Answer */}
              {latestEvaluation.exemplar_answer && (
                <div style={{ marginBottom: '12px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ width: '100%', fontSize: '0.8rem', justifyContent: 'space-between', padding: '8px 12px' }}
                    onClick={() => setShowExemplar(!showExemplar)}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Award size={14} color="#fbbf24" />
                      <strong>Staff Engineer Exemplar Model Answer</strong>
                    </span>
                    {showExemplar ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {showExemplar && (
                    <div className="fade-in" style={{ padding: '14px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '0 0 var(--radius-sm) var(--radius-sm)', fontSize: '0.825rem', color: '#cbd5e1', lineHeight: '1.6', whiteSpace: 'pre-line' }}>
                      {latestEvaluation.exemplar_answer}
                    </div>
                  )}
                </div>
              )}

              {/* Demonstrated Strengths and Conceptual Gaps */}
              {((latestEvaluation.strengths && latestEvaluation.strengths.length > 0) || (latestEvaluation.missing_concepts && latestEvaluation.missing_concepts.length > 0)) && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px', marginBottom: '12px' }}>
                  {latestEvaluation.strengths && latestEvaluation.strengths.length > 0 && (
                    <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '10px 12px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '0.725rem', fontWeight: 700, color: '#34d399', marginBottom: '4px', letterSpacing: '0.04em' }}>
                        DEMONSTRATED STRENGTHS
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.775rem', color: '#e2e8f0', lineHeight: 1.4 }}>
                        {latestEvaluation.strengths.slice(0, 2).map((s, idx) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {latestEvaluation.missing_concepts && latestEvaluation.missing_concepts.length > 0 && (
                    <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', padding: '10px 12px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '0.725rem', fontWeight: 700, color: '#f87171', marginBottom: '4px', letterSpacing: '0.04em' }}>
                        CONCEPTS TO REINFORCE
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                        {latestEvaluation.missing_concepts.map((mc, idx) => (
                          <span key={idx} style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5' }}>
                            {mc}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Verbatim Evidence Citation */}
              {latestEvaluation.evidence && latestEvaluation.evidence.length > 0 && (
                <div style={{ background: 'var(--bg-surface)', padding: '10px 12px', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '10px' }}>
                  <span style={{ color: 'var(--text-dim)', textTransform: 'uppercase', fontSize: '0.675rem' }}>EVIDENCE DETECTED IN ANSWER:</span>
                  <div style={{ color: '#e2e8f0', marginTop: '2px', fontStyle: 'italic' }}>
                    "{latestEvaluation.evidence[0].claim || latestEvaluation.evidence[0].basis}"
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    if (window.speechSynthesis) window.speechSynthesis.cancel();
                    navigate(`/debrief/${activeSession.id}`);
                  }}
                >
                  Complete & View Debrief
                </button>
                <button className="btn btn-primary" onClick={handleNextTurn}>
                  Proceed to Next Turn <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Live WebCam Studio HUD Frame */}
          {!latestEvaluation && (
            <div className="studio-panel" style={{ padding: '16px' }}>
              <WebcamFeed isRecording={isVoiceDictating || submitting} />

              {/* Speech-to-Text Dictation & Scratchpad */}
              <div style={{ marginTop: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label className="form-label" style={{ margin: 0 }}>
                    Candidate Response Workspace
                  </label>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      type="button"
                      className={`btn ${isVoiceDictating ? 'btn-danger' : 'btn-secondary'}`}
                      style={{ padding: '5px 12px', fontSize: '0.8rem' }}
                      onClick={toggleVoiceDictation}
                    >
                      {isVoiceDictating ? (
                        <>
                          <MicOff size={14} />
                          <span>Stop Dictating</span>
                        </>
                      ) : (
                        <>
                          <Mic size={14} />
                          <span>Voice Dictation (Mic)</span>
                        </>
                      )}
                    </button>
                    <kbd>Ctrl+Enter</kbd>
                  </div>
                </div>

                {/* AI Coach Socratic Hint System */}
                {activeSession.coaching_mode !== 'SIMULATION' && (
                  <div style={{ marginBottom: '10px' }}>
                    {!coachHint ? (
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{
                          fontSize: '0.775rem',
                          color: 'var(--accent-primary)',
                          padding: '5px 12px',
                          border: '1px dashed var(--accent-primary)',
                          borderRadius: 'var(--radius-sm)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                        onClick={handleRequestCoachHint}
                        disabled={loadingHint}
                      >
                        <Lightbulb size={13} color="var(--accent-primary)" />
                        <span>{loadingHint ? 'Coach is analyzing cognitive scaffolding...' : 'Stuck or seeking guidance? Request Socratic Coach Hint'}</span>
                      </button>
                    ) : (
                      <div className="studio-panel fade-in" style={{ border: '1px solid var(--border-card, #2d3b52)', background: 'var(--surface-raised, #1e293b)', padding: '10px 14px', marginBottom: '10px', borderRadius: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Lightbulb size={15} color="#fbbf24" />
                            <strong style={{ fontSize: '0.825rem', color: '#fbbf24' }}>Coach's Socratic Nudge</strong>
                          </div>
                          <span className="claim-status-badge badge-probed" style={{ fontSize: '0.625rem' }}>
                            CORE PATTERN: {coachHint.key_concept_to_consider}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: '#e2e8f0', lineHeight: '1.4', marginBottom: '4px' }}>
                          {coachHint.hint_text}
                        </p>
                        <div style={{ fontSize: '0.75rem', color: '#cbd5e1', fontStyle: 'italic' }}>
                          Nudge: {coachHint.pedagogical_nudge}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <textarea
                  className="form-textarea"
                  style={{ minHeight: '130px', fontSize: '0.925rem', lineHeight: '1.6' }}
                  placeholder="Speak via microphone or type your technical answer here... Explain your thought process and architecture trade-offs."
                  value={dictationInterim ? `${candidateAnswer} [${dictationInterim}]` : candidateAnswer}
                  onChange={(e) => setCandidateAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSubmitAnswer();
                    }
                  }}
                  disabled={submitting}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    {candidateAnswer.split(/\s+/).filter(Boolean).length} words spoken
                  </span>

                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ padding: '8px 20px' }}
                    onClick={handleSubmitAnswer}
                    disabled={!candidateAnswer.trim() || submitting}
                  >
                    <Send size={14} />
                    <span>{submitting ? 'Analyzing Epistemic Evidence...' : 'Submit Answer'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ========================================================= */}
        {/* DECK RIGHT: CANDIDATE EVIDENCE GRAPH HUD */}
        {/* ========================================================= */}
        <EvidenceGraphHUD
          claims={claims}
          currentSkillUnderProbe={currentQuestion?.topic}
        />
      </div>
    </div>
  );
};
