import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Candidate, ConversationDTO, ConversationDetailDTO, ConversationMessageDTO, AutonomousCoachingRecommendation } from '../../types';
import { api } from '../../services/api';
import { useAppSession } from '../../context/AppSessionContext';
import { useCoachingSession } from '../../pages/coaching/useCoachingSession';
import { ResearchDebugHUD } from '../../pages/coaching/ResearchDebugHUD';
import { CoachingHeader, CoachingWorkspaceMode, CompetencyOption } from './CoachingHeader';
import { CoachingHistoryDrawer } from './CoachingHistoryDrawer';
import { ConversationalTutorPane, PromptChip } from './ConversationalTutorPane';
import { GuidedPracticePane } from './GuidedPracticePane';
import { TransferChallengesPane, ChallengeTask } from './TransferChallengesPane';

export const AVAILABLE_COMPETENCIES: CompetencyOption[] = [
  { id: 'distributed_caching', label: 'Distributed Caching & Partitioning' },
  { id: 'system_decomposition', label: 'Microservices & Event-Driven Decoupling' },
  { id: 'concurrency_control', label: 'Database Concurrency & Isolation Levels' },
  { id: 'resilience_patterns', label: 'Circuit Breaking & Backpressure Resilience' },
  { id: 'rate_limiting', label: 'Distributed Rate Limiting & Throttling' },
  { id: 'algorithmic_optimization', label: 'Data Structure Selection & Amortized Complexity' },
  { id: 'memory_management', label: 'Memory Architecture & Resource Lifecycle' },
  { id: 'api_security', label: 'API Security & Multi-Tenant Authorization' },
];

export const SUGGESTED_PROMPTS: PromptChip[] = [
  { label: 'Explain in simple terms', prompt: 'Can you explain this in simple terms like I am a beginner?' },
  { label: 'Show worked example', prompt: 'Can you walk through a real-world worked example showing how an engineer reasons through this?' },
  { label: 'Check my understanding', prompt: 'Give me a focused question to check my conceptual understanding of this concept.' },
  { label: 'Common interview mistakes', prompt: 'What are the most common mistakes candidates make on this in interviews?' },
  { label: 'Unseen transfer challenge', prompt: 'Give me an unseen transfer challenge to test if I can apply this independently.' },
  { label: 'Attempt L5 Independent Transfer', prompt: 'I want to attempt the L5 Independent Transfer challenge without assistance.' },
];

interface UnifiedCoachingWorkspaceProps {
  selectedCandidate?: Candidate | null;
  activeRole?: string;
  initialMode?: CoachingWorkspaceMode;
  initialSessionId?: string;
  initialConversationId?: string;
  initialInterviewContext?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
  } | null;
  onClearInitialContext?: () => void;
  onNavigateToAnalytics?: () => void;
}

export const UnifiedCoachingWorkspace: React.FC<UnifiedCoachingWorkspaceProps> = ({
  selectedCandidate: propCandidate,
  activeRole: propActiveRole,
  initialMode,
  initialSessionId,
  initialConversationId,
  initialInterviewContext,
  onClearInitialContext,
  onNavigateToAnalytics: _onNavigateToAnalytics,
}) => {
  // Safe navigation fallback for unit tests rendered without Router context
  let navigate: (path: string) => void = () => {};
  try {
    navigate = useNavigate();
  } catch {
    navigate = () => {};
  }

  // Safe route params
  let routeCoachingSessionId: string | undefined;
  let routeConversationId: string | undefined;
  try {
    const params = useParams<{ coachingSessionId?: string; conversationId?: string }>();
    routeCoachingSessionId = params.coachingSessionId;
    routeConversationId = params.conversationId;
  } catch {
    // Outside router
  }

  // Query params fallback
  const queryParams = useMemo(() => {
    try {
      if (typeof window !== 'undefined' && window.location?.search) {
        const sp = new URLSearchParams(window.location.search);
        return {
          interviewId: sp.get('interviewId') || sp.get('interview_session_id'),
          questionId: sp.get('questionId') || sp.get('question_id'),
          skillId: sp.get('skillId') || sp.get('skill_id'),
          mode: sp.get('mode') as CoachingWorkspaceMode | null,
          debug: sp.get('debug') === 'true' || sp.get('research') === 'true',
        };
      }
    } catch {
      // ignore
    }
    return { interviewId: null, questionId: null, skillId: null, mode: null, debug: false };
  }, []);

  const sessionContext = useAppSession();
  const sessionCandidate = sessionContext.selectedCandidate;
  const [hydratedCandidate, setHydratedCandidate] = useState<Candidate | null>(null);

  const effectiveCandidate =
    hydratedCandidate || (propCandidate !== undefined ? propCandidate : sessionCandidate);
  const effectiveCandidateId = effectiveCandidate?.id || sessionContext.selectedCandidateId;
  const activeRole = propActiveRole || sessionContext.activeRoleId || 'Software Engineer';

  // Active workspace mode: conversation, practice, or transfer
  const [activeMode, setActiveMode] = useState<CoachingWorkspaceMode>(() => {
    if (initialMode) return initialMode;
    if (queryParams.mode === 'conversation' || queryParams.mode === 'practice' || queryParams.mode === 'transfer') {
      return queryParams.mode;
    }
    if (routeConversationId) return 'conversation';
    if (routeCoachingSessionId) return 'practice';
    return 'practice';
  });

  useEffect(() => {
    if (initialMode) {
      setActiveMode(initialMode);
    } else if (queryParams.mode === 'conversation' || queryParams.mode === 'practice' || queryParams.mode === 'transfer') {
      setActiveMode(queryParams.mode);
    } else if (routeConversationId) {
      setActiveMode('conversation');
    } else if (routeCoachingSessionId) {
      setActiveMode('practice');
    }
  }, [initialMode, queryParams.mode, routeConversationId, routeCoachingSessionId]);

  const [selectedSkill, setSelectedSkill] = useState<string>(
    queryParams.skillId || AVAILABLE_COMPETENCIES[0].id
  );
  const [recommendation, setRecommendation] = useState<AutonomousCoachingRecommendation | null>(null);
  const [isLoadingRecommendation, setIsLoadingRecommendation] = useState(false);
  const userOverrodeSkillRef = useRef(false);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false);
  const [candidatePracticeAnswer, setCandidatePracticeAnswer] = useState('');
  const [providerFallbackNotice, setProviderFallbackNotice] = useState<string | null>(null);

  // Fetch autonomous, evidence-driven coaching recommendation
  useEffect(() => {
    if (!effectiveCandidateId) return;
    if (typeof api?.getCoachingRecommendation !== 'function') return;
    let isCancelled = false;
    setIsLoadingRecommendation(true);
    api.getCoachingRecommendation(effectiveCandidateId, activeRole)
      .then((rec) => {
        if (!isCancelled && rec) {
          setRecommendation(rec);
          if (!userOverrodeSkillRef.current && !queryParams.skillId) {
            setSelectedSkill(rec.recommended_skill_id);
          }
        }
      })
      .catch((err) => {
        console.warn('Failed to fetch autonomous coaching recommendation:', err);
      })
      .finally(() => {
        if (!isCancelled) setIsLoadingRecommendation(false);
      });
    return () => {
      isCancelled = true;
    };
  }, [effectiveCandidateId, activeRole, queryParams.skillId]);

  // 1. Structured Coaching Loop Hook (TransferCoachingService)
  const {
    sessionState,
    telemetry,
    isLoading: isCoachingLoading,
    error: coachingError,
    sessionId: activeCoachingSessionId,
    hintsCount,
    isHintDisabled,
    activeTask,
    activeEvaluation,
    activeIntervention,
    activeDiagnosis,
    candidateSkillState,
    trainingContext,
    startSession,
    startSessionFromInterview,
    hydrateSession,
    submitStep,
    requestHint,
    resetSession,
    fetchTelemetry,
  } = useCoachingSession();

  // 2. Conversational Threads State (ConversationService)
  const [conversations, setConversations] = useState<ConversationDTO[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    initialConversationId || routeConversationId || null
  );
  const [activeConversation, setActiveConversation] = useState<ConversationDetailDTO | null>(null);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  // Fetch candidate conversations
  const loadConversations = useCallback(async () => {
    if (!effectiveCandidateId) return;
    setIsLoadingConversations(true);
    try {
      const list = await api.listConversations(effectiveCandidateId);
      setConversations(list);
      return list;
    } catch {
      return [];
    } finally {
      setIsLoadingConversations(false);
    }
  }, [effectiveCandidateId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load active conversation details
  const loadActiveConversation = useCallback(
    async (convoId: string) => {
      try {
        const detail = await api.getConversation(convoId, effectiveCandidateId);
        setActiveConversation(detail);
        setActiveConversationId(convoId);
      } catch (err: any) {
        setChatError(err.message || 'Failed to load conversation history.');
      }
    },
    [effectiveCandidateId]
  );

  useEffect(() => {
    const targetConvoId = routeConversationId || activeConversationId;
    if (targetConvoId) {
      loadActiveConversation(targetConvoId);
    }
  }, [routeConversationId, activeConversationId, loadActiveConversation]);

  // Handle Hydration of Coaching Session
  const targetSessionId =
    initialSessionId ||
    (routeCoachingSessionId && routeCoachingSessionId !== 'undefined' ? routeCoachingSessionId : null) ||
    sessionContext.coachingSessionId;
  const attemptedSessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (
      targetSessionId &&
      targetSessionId !== 'undefined' &&
      targetSessionId !== activeCoachingSessionId &&
      attemptedSessionIdRef.current !== targetSessionId &&
      !isCoachingLoading
    ) {
      attemptedSessionIdRef.current = targetSessionId;
      hydrateSession(targetSessionId);
      setActiveMode('practice');
    }
  }, [targetSessionId, activeCoachingSessionId, isCoachingLoading, hydrateSession]);

  // Handle Bridged Interview Context
  const effectiveInterviewContext =
    initialInterviewContext ||
    sessionContext.coachingInterviewContext ||
    (queryParams.interviewId
      ? {
          interviewSessionId: queryParams.interviewId,
          questionId: queryParams.questionId || undefined,
          skillId: queryParams.skillId || undefined,
        }
      : null);


  // Single Authoritative Active Context & State
  const activeTrainingContext = sessionState?.training_context ?? trainingContext;

  const authoritativeSkillId =
    activeTrainingContext?.skill_id ||
    recommendation?.recommended_skill_id ||
    selectedSkill;

  const authoritativeSkillTitle =
    activeTrainingContext?.topic ||
    recommendation?.recommended_skill_title ||
    AVAILABLE_COMPETENCIES.find((c) => c.id === authoritativeSkillId)?.label ||
    authoritativeSkillId.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const authoritativeLearningObjective =
    activeTrainingContext?.learning_objective ||
    recommendation?.learning_objective ||
    activeConversation?.metadata?.learning_objective ||
    `Master foundational operational invariants and transfer-level execution for ${authoritativeSkillTitle}.`;

  const hasMasteryEvidence = Boolean(
    candidateSkillState &&
    (candidateSkillState.total_attempts ?? 0) > 0 &&
    candidateSkillState.last_assessed_at &&
    (candidateSkillState.mastery_uncertainty ?? 1.0) < 0.75
  );

  const authoritativeMasteryScore = hasMasteryEvidence
    ? candidateSkillState?.mastery_estimate
    : null;

  // Chat Actions
  const handleCreateNewConversation = async (title = 'New Coaching Session') => {
    if (!effectiveCandidateId) return;
    try {
      const created = await api.createConversation({
        candidate_id: effectiveCandidateId,
        title,
        metadata: {
          session_type: 'coaching_studio',
          target_role: activeRole,
          focus_skill: authoritativeSkillId,
          learning_objective: authoritativeLearningObjective,
        },
      });
      await loadConversations();
      setActiveConversationId(created.id);
      navigate(`/coaching/chat/${created.id}`);
      setActiveMode('conversation');
    } catch (err: any) {
      alert(`Could not create coaching thread: ${err.message}`);
    }
  };

  const handleRenameConversation = async (id: string, newTitle: string) => {
    try {
      await api.renameConversation(id, newTitle, effectiveCandidateId);
      await loadConversations();
      if (activeConversation && activeConversation.id === id) {
        setActiveConversation({ ...activeConversation, title: newTitle });
      }
    } catch (err: any) {
      alert(`Rename failed: ${err.message}`);
    }
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await api.deleteConversation(id, effectiveCandidateId);
      const remaining = await loadConversations();
      if (remaining && remaining.length > 0) {
        setActiveConversationId(remaining[0].id);
        navigate(`/coaching/chat/${remaining[0].id}`);
      } else {
        setActiveConversation(null);
        setActiveConversationId(null);
      }
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleSendChatMessage = async (text: string, actionType?: string) => {
    if (!text.trim() || isSendingChat) return;
    setIsSendingChat(true);
    setChatError(null);
    setProviderFallbackNotice(null);

    let targetConvoId = activeConversationId;
    try {
      if (!targetConvoId) {
        const titleSnippet = text.length > 32 ? `${text.slice(0, 30)}...` : text;
        const newConvo = await api.createConversation({
          candidate_id: effectiveCandidateId,
          title: titleSnippet,
          metadata: {
            session_type: 'coaching_studio',
            target_role: activeRole,
            focus_skill: authoritativeSkillId,
            learning_objective: authoritativeLearningObjective,
          },
        });
        targetConvoId = newConvo.id;
        setActiveConversationId(newConvo.id);
        await loadConversations();
      }

      // Optimistic user turn
      const optimisticUserMsg: ConversationMessageDTO = {
        id: `opt-${Date.now()}`,
        conversation_id: targetConvoId,
        role: 'user',
        content: text,
        message_type: 'text',
        sequence: (activeConversation?.messages.length || 0) + 1,
        created_at: new Date().toISOString(),
      };

      if (activeConversation) {
        setActiveConversation({
          ...activeConversation,
          messages: [...activeConversation.messages, optimisticUserMsg],
        });
      }

      const res = await api.sendChatMessage(targetConvoId, {
        content: text,
        candidate_id: effectiveCandidateId,
        target_role: activeRole,
        focus_skill: authoritativeSkillId,
        metadata: {
          session_type: 'coaching_studio',
          focus_skill: authoritativeSkillId,
          learning_objective: authoritativeLearningObjective,
          action_type: actionType,
        },
      });

      if (res.is_fallback) {
        setProviderFallbackNotice(
          'Using grounded pedagogical curriculum fallback due to model latency. Socratic instruction remains fully active.'
        );
      }

      setActiveConversation((prev) => {
        if (!prev) {
          return {
            id: res.conversation_id,
            candidate_id: effectiveCandidateId || '',
            title: text.slice(0, 30),
            status: 'ACTIVE',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            messages: [res.user_message, res.assistant_message],
          };
        }
        const filtered = prev.messages.filter((m) => m.id !== optimisticUserMsg.id);
        return {
          ...prev,
          messages: [...filtered, res.user_message, res.assistant_message],
        };
      });
    } catch (err: any) {
      setChatError(err.message || 'Message delivery failed. Please check your network.');
    } finally {
      setIsSendingChat(false);
    }
  };

  // Structured Practice Handlers
  const handleStartCoachingSession = async () => {
    if (!effectiveCandidateId) return;
    await startSession(effectiveCandidateId, selectedSkill);
    setActiveMode('practice');
  };

  const handleSubmitPracticeStep = async (answer: string) => {
    await submitStep(answer);
  };

  // Transfer Challenge to Coaching Bridge
  const handleSelectChallengeForCoaching = (task: ChallengeTask) => {
    setSelectedSkill(task.skillId);
    setActiveMode('practice');
    if (effectiveCandidateId) {
      startSession(effectiveCandidateId, task.skillId);
    }
  };

  // Candidate Identity Synchronization from Hydrated Session
  const sessionCandId = sessionState?.candidate_state?.candidate_id;
  useEffect(() => {
    if (sessionCandId) {
      if (!hydratedCandidate || hydratedCandidate.id !== sessionCandId) {
        const found = sessionContext.candidates.find((c) => c.id === sessionCandId);
        if (found) {
          setHydratedCandidate(found);
          sessionContext.setSelectedCandidateId(found.id);
        } else {
          api.getCandidate?.(sessionCandId)?.then?.((cand: Candidate) => {
            if (cand) {
              setHydratedCandidate(cand);
              sessionContext.setSelectedCandidateId(cand.id);
            }
          }).catch?.(() => {});
        }
      }
    }
  }, [sessionCandId, hydratedCandidate, sessionContext.candidates, sessionContext.setSelectedCandidateId]);

  // Competency Dropdown Restoration from Hydrated Session
  const resolvedTopicSkill =
    sessionState?.training_context?.skill_id ||
    trainingContext?.skill_id;

  useEffect(() => {
    if (resolvedTopicSkill) {
      const match = AVAILABLE_COMPETENCIES.find(
        (c) => c.id === resolvedTopicSkill || c.id === resolvedTopicSkill.toLowerCase().replace(/ /g, '_')
      );
      if (match) {
        setSelectedSkill(match.id);
      } else {
        setSelectedSkill(resolvedTopicSkill);
      }
    }
  }, [resolvedTopicSkill]);

  const currentScaffold =
    sessionState?.scaffold_state?.current_level ||
    (activeConversation?.metadata?.scaffold_level as any) ||
    'HIGH';

  const phaseTitle =
    (sessionState?.state as string) === 'TRAINING'
      ? 'Phase B: Fundamentals & Mechanics'
      : (sessionState?.state as string) === 'PROGRESSIVE_TRANSFER'
      ? 'Phase E: Guided Progressive Transfer'
      : (sessionState?.state as string) === 'INDEPENDENT_TRANSFER'
      ? 'Phase F: L5 Independent Transfer'
      : 'Socratic Dialogue & Fundamentals';

  const displayedSessionId = activeCoachingSessionId || targetSessionId || activeConversationId;

  // Dynamic state-grounded prompt chips
  const dynamicSuggestedPrompts = useMemo<PromptChip[]>(() => {
    const rawPhase = String(sessionState?.state || activeConversation?.metadata?.active_phase || 'PHASE_B_FUNDAMENTALS');
    const skillName = authoritativeSkillTitle;

    if (rawPhase.includes('TRANSFER') || rawPhase.includes('INDEPENDENT')) {
      return [
        { label: 'Attempt L5 Independent Transfer', prompt: `I want to attempt the L5 Independent Transfer challenge for ${skillName} without assistance.` },
        { label: 'Request Socratic hint', prompt: `Can you give me a subtle Socratic hint for ${skillName} without spoiling the core invariant?` },
        { label: 'Targeted remediation', prompt: `I am having trouble with edge cases in ${skillName}. Can you diagnose what invariant I am missing?` },
        { label: 'Next competency on roadmap', prompt: `What is the next recommended competency on my learning roadmap?` },
      ];
    }

    if (rawPhase.includes('PRACTICE') || rawPhase.includes('PROGRESSIVE')) {
      return [
        { label: 'Check my understanding', prompt: `Give me a focused question to check my conceptual understanding of ${skillName}.` },
        { label: 'Show worked example', prompt: `Can you walk through a concrete engineering worked example for ${skillName}?` },
        { label: 'Common interview mistakes', prompt: `What are the most common mistakes candidates make on ${skillName} in interviews?` },
        { label: 'Attempt L5 Independent Transfer', prompt: `I want to attempt the L5 Independent Transfer challenge for ${skillName} without assistance.` },
      ];
    }

    // Phase B / Fundamentals default
    return [
      { label: 'Explain in simple terms', prompt: `Can you explain ${skillName} in simple terms like I am a beginner?` },
      { label: 'Show worked example', prompt: `Can you walk through a real-world worked example showing how an engineer reasons through ${skillName}?` },
      { label: 'Check my understanding', prompt: `Give me a focused question to check my conceptual understanding of ${skillName}.` },
      { label: 'Common interview mistakes', prompt: `What are the most common mistakes candidates make on ${skillName} in interviews?` },
      { label: 'Start guided practice', prompt: `I am ready to practice hands-on exercises for ${skillName}.` },
      { label: 'Unseen transfer challenge', prompt: `Give me an unseen transfer challenge for ${skillName} to test if I can apply this independently.` },
    ];
  }, [sessionState?.state, activeConversation?.metadata?.active_phase, authoritativeSkillTitle]);

  // Clean Session Reset Handler
  const handleResetSession = useCallback(() => {
    resetSession();
    sessionContext.setCoachingSessionId(undefined);
    sessionContext.setCoachingInterviewContext(undefined);
    setActiveConversation(null);
    setActiveConversationId(null);
    setCandidatePracticeAnswer('');
    userOverrodeSkillRef.current = false;

    if (typeof window !== 'undefined' && window.sessionStorage) {
      try {
        const raw = sessionStorage.getItem('ai_interview_coach_session_state');
        if (raw) {
          const parsed = JSON.parse(raw);
          delete parsed.coachingSessionId;
          delete parsed.coachingInterviewContext;
          sessionStorage.setItem('ai_interview_coach_session_state', JSON.stringify(parsed));
        }
      } catch {}
    }

    if (effectiveCandidateId && typeof api?.getCoachingRecommendation === 'function') {
      setIsLoadingRecommendation(true);
      api.getCoachingRecommendation(effectiveCandidateId, activeRole)
        .then((rec) => {
          if (rec) {
            setRecommendation(rec);
            setSelectedSkill(rec.recommended_skill_id);
          }
        })
        .finally(() => setIsLoadingRecommendation(false));
    }
  }, [resetSession, sessionContext, effectiveCandidateId, activeRole]);

  // Candidate switching state isolation
  const prevCandidateIdRef = useRef<string | null>(effectiveCandidateId || null);
  useEffect(() => {
    if (prevCandidateIdRef.current && prevCandidateIdRef.current !== effectiveCandidateId) {
      prevCandidateIdRef.current = effectiveCandidateId || null;
      resetSession();
      setActiveConversation(null);
      setActiveConversationId(null);
      setCandidatePracticeAnswer('');
      userOverrodeSkillRef.current = false;
      if (effectiveCandidateId && typeof api?.getCoachingRecommendation === 'function') {
        setIsLoadingRecommendation(true);
        api.getCoachingRecommendation(effectiveCandidateId, activeRole)
          .then((rec) => {
            if (rec) {
              setRecommendation(rec);
              setSelectedSkill(rec.recommended_skill_id);
            }
          })
          .finally(() => setIsLoadingRecommendation(false));
      }
    } else {
      prevCandidateIdRef.current = effectiveCandidateId || null;
    }
  }, [effectiveCandidateId, activeRole, resetSession]);

  return (
    <div className="unified-coaching-workspace-container">
      {/* Top Header */}
      <CoachingHeader
        selectedCandidate={effectiveCandidate}
        activeRole={activeRole}
        selectedSkill={authoritativeSkillId}
        competencies={AVAILABLE_COMPETENCIES}
        onSelectSkill={(skill) => {
          userOverrodeSkillRef.current = true;
          setSelectedSkill(skill);
        }}
        activeMode={activeMode}
        onChangeMode={(mode) => setActiveMode(mode)}
        scaffoldLevel={currentScaffold}
        currentPhaseTitle={phaseTitle}
        sessionId={displayedSessionId}
        onToggleHistoryDrawer={() => setIsHistoryDrawerOpen((prev) => !prev)}
        isHistoryDrawerOpen={isHistoryDrawerOpen}
        onResetSession={handleResetSession}
        masteryScore={authoritativeMasteryScore}
        hasMasteryEvidence={hasMasteryEvidence}
        activeSkillTitle={authoritativeSkillTitle}
        activeLearningObjective={authoritativeLearningObjective}
      />

      {/* Main Workspace Body with Drawer */}
      <div className="workspace-main-content-layout">
        <CoachingHistoryDrawer
          isOpen={isHistoryDrawerOpen}
          onClose={() => setIsHistoryDrawerOpen(false)}
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={(id) => {
            setActiveConversationId(id);
            setActiveMode('conversation');
            navigate(`/coaching/chat/${id}`);
          }}
          onCreateNewConversation={() => handleCreateNewConversation()}
          onRenameConversation={handleRenameConversation}
          onDeleteConversation={handleDeleteConversation}
          isLoadingList={isLoadingConversations}
          selectedCandidate={effectiveCandidate}
          onNavigateToRoadmap={() => navigate('/roadmap')}
          onNavigateToInterview={() => navigate('/interview')}
          activeSessionId={activeCoachingSessionId}
        />

        {/* Workspace Central Task Pane */}
        <main className="workspace-center-pane" aria-label="Coaching workspace central pane">
          {activeMode === 'conversation' && (
            <ConversationalTutorPane
              messages={activeConversation?.messages || []}
              isSending={isSendingChat}
              onSendMessage={handleSendChatMessage}
              suggestedPrompts={dynamicSuggestedPrompts}
              providerFallbackNotice={providerFallbackNotice}
              onRetryLastTurn={() => {
                const lastMsg = activeConversation?.messages?.filter((m) => m.role === 'user').slice(-1)[0];
                if (lastMsg) handleSendChatMessage(lastMsg.content);
              }}
              error={chatError}
            />
          )}

          {activeMode === 'practice' && (
            <GuidedPracticePane
              sessionState={sessionState}
              activeTask={activeTask}
              trainingContext={trainingContext}
              activeEvaluation={activeEvaluation}
              activeIntervention={activeIntervention}
              activeDiagnosis={activeDiagnosis}
              candidateSkillState={candidateSkillState}
              candidateAnswer={candidatePracticeAnswer}
              onChangeAnswer={(val) => setCandidatePracticeAnswer(val)}
              onSubmitStep={handleSubmitPracticeStep}
              onRequestHint={requestHint}
              hintsCount={hintsCount}
              isHintDisabled={isHintDisabled}
              isLoading={isCoachingLoading}
              selectedCandidate={effectiveCandidate}
              activeRole={activeRole}
              onStartSession={handleStartCoachingSession}
              onResetSession={handleResetSession}
              error={coachingError}
              effectiveInterviewContext={effectiveInterviewContext}
              onClearInitialContext={onClearInitialContext}
              recommendation={recommendation}
              isLoadingRecommendation={isLoadingRecommendation}
              onNavigateToInterview={() => navigate('/interview')}
              onLaunchRemediation={() => {
                if (effectiveCandidateId && effectiveInterviewContext?.interviewSessionId) {
                  startSessionFromInterview(
                    effectiveCandidateId,
                    effectiveInterviewContext.interviewSessionId,
                    effectiveInterviewContext.questionId
                  );
                }
              }}
            />
          )}

          {activeMode === 'transfer' && (
            <TransferChallengesPane
              selectedCandidate={effectiveCandidate}
              onSelectChallengeForCoaching={handleSelectChallengeForCoaching}
            />
          )}
        </main>
      </div>

      {/* Read-Only Collapsible Research Telemetry HUD (Admin / Researcher View Only) */}
      {queryParams.debug && (
        <ResearchDebugHUD
          sessionState={sessionState}
          telemetry={telemetry}
          sessionId={activeCoachingSessionId}
          onRefreshTelemetry={fetchTelemetry}
        />
      )}
    </div>
  );
};
