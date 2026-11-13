import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Candidate, CandidateReadinessResponse } from '../types';
import { api } from '../services/api';

export interface AppSessionState {
  selectedCandidateId?: string;
  interviewSessionId?: string;
  coachingSessionId?: string;
  currentQuestionId?: string;
  roadmapId?: string;
  activeRoleId?: string;
  isLoggedOut?: boolean;
  coachingInterviewContext?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
  } | null;
}

export interface AppSessionContextValue {
  session: AppSessionState;
  selectedCandidateId?: string;
  interviewSessionId?: string;
  coachingSessionId?: string;
  currentQuestionId?: string;
  roadmapId?: string;
  activeRoleId?: string;
  isLoggedOut: boolean;
  isAuthenticated: boolean;
  isAuthResolving: boolean;
  readiness: CandidateReadinessResponse | null;
  refreshReadiness: () => Promise<void>;
  coachingInterviewContext?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
  } | null;
  candidates: Candidate[];
  selectedCandidate: Candidate | null;
  isLoadingCandidates: boolean;
  setSelectedCandidateId: (id: string | undefined) => void;
  setInterviewSessionId: (id: string | undefined) => void;
  setCoachingSessionId: (id: string | undefined) => void;
  setCurrentQuestionId: (id: string | undefined) => void;
  setRoadmapId: (id: string | undefined) => void;
  setActiveRoleId: (role: string | undefined) => void;
  setCoachingInterviewContext: (ctx: AppSessionState['coachingInterviewContext']) => void;
  clearSession: () => void;
  logout: (promptConfirmation?: boolean) => Promise<boolean> | boolean;
  login: (email: string, password?: string) => Promise<{ success: boolean; candidate?: Candidate; error?: string }>;
  register: (email: string, fullName: string, password?: string) => Promise<{ success: boolean; candidate?: Candidate; error?: string }>;
  refreshCandidates: () => Promise<void>;
}

const SESSION_STORAGE_KEY = 'ai_interview_coach_session_state';

function loadInitialSessionState(): AppSessionState {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (err) {
    console.warn('Failed to parse session state from sessionStorage:', err);
  }
  return {};
}

function saveSessionState(state: AppSessionState): void {
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(state));
  } catch (err) {
    console.warn('Failed to save session state to sessionStorage:', err);
  }
}

function getAuthTokenSafe(): string | null {
  if (typeof api?.getAuthToken === 'function') {
    try {
      return api.getAuthToken();
    } catch {}
  }
  try {
    return sessionStorage.getItem('candidate_auth_token') || localStorage.getItem('candidate_auth_token');
  } catch {
    return null;
  }
}

function safeClearAuthToken(): void {
  if (typeof api?.clearAuthToken === 'function') {
    try {
      api.clearAuthToken();
    } catch {}
  }
  try {
    sessionStorage.removeItem('candidate_auth_token');
    localStorage.removeItem('candidate_auth_token');
  } catch {}
}

const AppSessionContext = createContext<AppSessionContextValue | undefined>(undefined);

export const AppSessionProvider: React.FC<{ children: ReactNode; initialState?: AppSessionState }> = ({
  children,
  initialState,
}) => {
  const [session, setSession] = useState<AppSessionState>(() => ({
    ...loadInitialSessionState(),
    ...(initialState || {}),
  }));

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [isLoadingCandidates, setIsLoadingCandidates] = useState(false);
  const [activeCandidate, setActiveCandidate] = useState<Candidate | null>(null);
  const [isAuthResolving, setIsAuthResolving] = useState<boolean>(() => {
    // If a token exists in storage, we need to verify it with /auth/me
    return Boolean(getAuthTokenSafe());
  });

  // Sync session state to sessionStorage
  useEffect(() => {
    saveSessionState(session);
  }, [session]);

  // Initial session verification: If token exists, verify candidate with /auth/me
  useEffect(() => {
    const token = getAuthTokenSafe();
    if (!token) {
      setIsAuthResolving(false);
      return;
    }

    let isMounted = true;
    api.getMe()
      .then((data) => {
        if (!isMounted) return;
        if (data?.candidate) {
          setActiveCandidate(data.candidate);
          setSession((prev) => ({
            ...prev,
            selectedCandidateId: data.candidate.id,
            isLoggedOut: false,
          }));
          try {
            sessionStorage.removeItem('candidate_logged_out');
          } catch {}
        }
      })
      .catch((err) => {
        console.warn('Existing session validation failed, resetting credentials:', err);
        safeClearAuthToken();
        setActiveCandidate(null);
        setSession((prev) => ({
          ...prev,
          selectedCandidateId: undefined,
          isLoggedOut: true,
        }));
      })
      .finally(() => {
        if (isMounted) setIsAuthResolving(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const refreshCandidates = useCallback(async () => {
    setIsLoadingCandidates(true);
    try {
      const res = await api.listCandidates();
      const cands = res.candidates || [];
      setCandidates(cands);

      // If we have an active candidate ID, sync activeCandidate with refreshed record
      setSession((prev) => {
        if (prev.selectedCandidateId) {
          const match = cands.find((c) => c.id === prev.selectedCandidateId);
          if (match) {
            setActiveCandidate(match);
          }
        }
        return prev;
      });
    } catch (err) {
      console.warn('Failed to fetch candidate list:', err);
    } finally {
      setIsLoadingCandidates(false);
    }
  }, []);

  useEffect(() => {
    refreshCandidates();
  }, [refreshCandidates]);

  const setSelectedCandidateId = useCallback((id: string | undefined) => {
    try {
      if (id) {
        sessionStorage.removeItem('candidate_logged_out');
      }
    } catch {}
    setSession((prev) => {
      const next = { ...prev, selectedCandidateId: id, isLoggedOut: false };
      saveSessionState(next);
      return next;
    });
  }, []);

  const setInterviewSessionId = useCallback((id: string | undefined) => {
    setSession((prev) => ({ ...prev, interviewSessionId: id }));
  }, []);

  const setCoachingSessionId = useCallback((id: string | undefined) => {
    setSession((prev) => ({ ...prev, coachingSessionId: id }));
  }, []);

  const setCurrentQuestionId = useCallback((id: string | undefined) => {
    setSession((prev) => ({ ...prev, currentQuestionId: id }));
  }, []);

  const setRoadmapId = useCallback((id: string | undefined) => {
    setSession((prev) => ({ ...prev, roadmapId: id }));
  }, []);

  const setActiveRoleId = useCallback((role: string | undefined) => {
    setSession((prev) => {
      const next = { ...prev, activeRoleId: role };
      saveSessionState(next);
      return next;
    });
    // Persist to candidate profile preference if candidate exists
    if (session.selectedCandidateId) {
      api
        .updateCandidate(session.selectedCandidateId, { target_role: role || null })
        .then((updated) => {
          setActiveCandidate(updated);
        })
        .catch((err) => {
          console.warn('Failed to persist candidate target role preference:', err);
        });
    }
  }, [session.selectedCandidateId]);

  const setCoachingInterviewContext = useCallback((ctx: AppSessionState['coachingInterviewContext']) => {
    setSession((prev) => ({ ...prev, coachingInterviewContext: ctx }));
  }, []);

  // Compute selectedCandidate:
  // Strictly requires candidate identity - never falls back silently to candidates[0] when unauthenticated!
  const selectedCandidate = React.useMemo(() => {
    const isLoggedOutStorage =
      typeof sessionStorage !== 'undefined' && sessionStorage.getItem('candidate_logged_out') === 'true';
    if (session.isLoggedOut || isLoggedOutStorage) return null;

    if (activeCandidate) {
      // If candidate changed in session
      if (session.selectedCandidateId && activeCandidate.id === session.selectedCandidateId) {
        return activeCandidate;
      }
    }

    if (session.selectedCandidateId) {
      if (candidates.length > 0) {
        const match = candidates.find((c) => c.id === session.selectedCandidateId);
        if (match) return match;
      }
      return {
        id: session.selectedCandidateId,
        full_name: 'Authenticated Candidate',
        email: 'candidate@session.local',
        created_at: new Date().toISOString(),
        resumes: [],
        has_profile: false,
        skills_summary: [],
        total_years_exp: 0,
        readiness_state: 'NO_RESUME',
      } as Candidate;
    }

    return null;
  }, [candidates, session.selectedCandidateId, session.isLoggedOut, activeCandidate]);

  const [readiness, setReadiness] = useState<CandidateReadinessResponse | null>(null);

  const refreshReadiness = useCallback(async () => {
    if (!selectedCandidate) {
      setReadiness(null);
      return;
    }
    try {
      const res = await api.getCandidateReadiness(selectedCandidate.id, session.activeRoleId);
      setReadiness(res);
    } catch {
      const hasResumes = Boolean(selectedCandidate.resumes && selectedCandidate.resumes.length > 0);
      const isCompleted = hasResumes && selectedCandidate.resumes.some((r) => r.processing_status === 'COMPLETED');
      const hasProfile = Boolean(isCompleted && selectedCandidate.has_profile);
      const state = !hasResumes
        ? 'NO_RESUME'
        : (!isCompleted || !hasProfile)
        ? 'RESUME_PROCESSING'
        : session.activeRoleId
        ? 'ROLE_READY'
        : 'PROFILE_READY';

      setReadiness({
        candidate_id: selectedCandidate.id,
        readiness_state: state,
        is_resume_uploaded: hasResumes,
        is_resume_processed: isCompleted,
        is_profile_ready: hasProfile,
        is_role_selected: Boolean(session.activeRoleId),
        target_role: session.activeRoleId || null,
        is_assessment_ready: false,
        completed_interviews_count: 0,
        is_coaching_ready: false,
        is_transfer_ready: false,
        allowed_features: hasProfile
          ? ['platform_overview', 'generic_role_catalog', 'resume_upload', 'personalized_profile']
          : ['platform_overview', 'generic_role_catalog', 'resume_upload'],
        blocked_features: !hasResumes
          ? {
              personalized_roadmap: 'Upload an engineering resume to generate a personalized roadmap.',
              skill_gap_analysis: 'Upload an engineering resume to diagnose skill gaps.',
            }
          : {},
        next_action: !hasResumes
          ? { action: 'UPLOAD_RESUME', route: '/resume', title: 'Upload Resume', rationale: 'Anchor coaching in resume evidence.' }
          : { action: 'SELECT_ROLE', route: '/roles', title: 'Select Target Role', rationale: 'Select target role.' },
      });
    }
  }, [selectedCandidate, session.activeRoleId]);

  useEffect(() => {
    refreshReadiness();
  }, [refreshReadiness]);

  // Synchronize candidate target_role to prevent cross-candidate or stale default leakage
  useEffect(() => {
    if (!selectedCandidate) {
      if (session.activeRoleId) {
        setSession((prev) => {
          const next = { ...prev, activeRoleId: undefined };
          saveSessionState(next);
          return next;
        });
      }
      return;
    }

    if (selectedCandidate.target_role !== undefined) {
      const candidateTargetRole = selectedCandidate.target_role || undefined;
      if (session.activeRoleId !== candidateTargetRole) {
        setSession((prev) => {
          const next = { ...prev, activeRoleId: candidateTargetRole };
          saveSessionState(next);
          return next;
        });
      }
    }
  }, [selectedCandidate?.id, selectedCandidate?.target_role]);


  // Synchronize authenticated bearer token for active candidate
  useEffect(() => {
    if (session.isLoggedOut || !selectedCandidate) {
      return;
    }
    // If we have selectedCandidate but token is missing, request one
    const token = getAuthTokenSafe();
    if (!token && selectedCandidate.id && selectedCandidate.email && typeof api.requestCandidateToken === 'function') {
      api.requestCandidateToken(selectedCandidate.id, selectedCandidate.email).catch((err) => {
        console.warn('Failed to acquire candidate auth token:', err);
      });
    }
  }, [selectedCandidate?.id, selectedCandidate?.email, session.isLoggedOut]);

  const clearSession = useCallback(() => {
    setSession({});
    setActiveCandidate(null);
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
      sessionStorage.removeItem('candidate_auth_token');
      localStorage.removeItem('candidate_auth_token');
    } catch {}
  }, []);

  const login = useCallback(async (email: string, password?: string) => {
    try {
      const res = await api.login(email, password);
      setActiveCandidate(res.candidate);
      setSession((prev) => ({
        ...prev,
        selectedCandidateId: res.candidate_id,
        isLoggedOut: false,
      }));
      try {
        sessionStorage.removeItem('candidate_logged_out');
      } catch {}
      return { success: true, candidate: res.candidate };
    } catch (err: any) {
      return { success: false, error: err.message || 'Login failed' };
    }
  }, []);

  const register = useCallback(
    async (email: string, fullName: string, password?: string) => {
      try {
        const res = await api.register(email, fullName, password);
        setActiveCandidate(res.candidate);
        setSession((prev) => ({
          ...prev,
          selectedCandidateId: res.candidate_id,
          isLoggedOut: false,
        }));
        try {
          sessionStorage.removeItem('candidate_logged_out');
        } catch {}
        await refreshCandidates();
        return { success: true, candidate: res.candidate };
      } catch (err: any) {
        return { success: false, error: err.message || 'Registration failed' };
      }
    },
    [refreshCandidates]
  );

  const logout = useCallback(async (promptConfirmation = true) => {
    if (promptConfirmation && typeof window !== 'undefined' && typeof window.confirm === 'function') {
      const confirmed = window.confirm(
        'Are you sure you want to log out? Any unsaved progress in active sessions will be closed.'
      );
      if (!confirmed) return false;
    }

    try {
      await api.logout();
    } catch {
      safeClearAuthToken();
    }

    // 1. Clear auth tokens in storage
    safeClearAuthToken();
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
      sessionStorage.removeItem('candidate_auth_token');
      localStorage.removeItem('candidate_auth_token');
      sessionStorage.setItem('candidate_logged_out', 'true');
    } catch {}

    // 2. Clear state
    setActiveCandidate(null);
    setSession({
      isLoggedOut: true,
      selectedCandidateId: undefined,
      interviewSessionId: undefined,
      coachingSessionId: undefined,
      currentQuestionId: undefined,
      roadmapId: undefined,
      activeRoleId: undefined,
      coachingInterviewContext: null,
    });

    return true;
  }, []);

  const isAuthenticated = Boolean(selectedCandidate);

  const value: AppSessionContextValue = {
    session,
    selectedCandidateId: session.selectedCandidateId,
    interviewSessionId: session.interviewSessionId,
    coachingSessionId: session.coachingSessionId,
    currentQuestionId: session.currentQuestionId,
    roadmapId: session.roadmapId,
    activeRoleId: session.activeRoleId,
    isLoggedOut: Boolean(session.isLoggedOut),
    isAuthenticated,
    isAuthResolving,
    readiness,
    refreshReadiness,
    coachingInterviewContext: session.coachingInterviewContext,
    candidates,
    selectedCandidate,
    isLoadingCandidates,
    setSelectedCandidateId,
    setInterviewSessionId,
    setCoachingSessionId,
    setCurrentQuestionId,
    setRoadmapId,
    setActiveRoleId,
    setCoachingInterviewContext,
    clearSession,
    logout,
    login,
    register,
    refreshCandidates,
  };

  return <AppSessionContext.Provider value={value}>{children}</AppSessionContext.Provider>;
};

const defaultSessionContext: AppSessionContextValue = {
  session: {},
  candidates: [],
  selectedCandidate: null,
  isLoadingCandidates: false,
  isLoggedOut: false,
  isAuthenticated: false,
  isAuthResolving: false,
  readiness: null,
  refreshReadiness: async () => {},
  setSelectedCandidateId: () => {},
  setInterviewSessionId: () => {},
  setCoachingSessionId: () => {},
  setCurrentQuestionId: () => {},
  setRoadmapId: () => {},
  setActiveRoleId: () => {},
  setCoachingInterviewContext: () => {},
  clearSession: () => {},
  logout: () => true,
  login: async () => ({ success: false }),
  register: async () => ({ success: false }),
  refreshCandidates: async () => {},
};

export function useAppSession(): AppSessionContextValue {
  const context = useContext(AppSessionContext);
  return context || defaultSessionContext;
}

export function useSafeNavigate() {
  try {
    return useNavigate();
  } catch {
    return () => {};
  }
}

export function useSafeLocation() {
  try {
    return useLocation();
  } catch {
    return { pathname: '/profile', search: '', hash: '', state: null, key: 'default' };
  }
}
