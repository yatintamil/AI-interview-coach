import {
  Candidate,
  CandidateProfile,
  ResumeSummary,
  InterviewSession,
  TurnAnswerResult,
  AnalyticsOverview,
  PerformanceTrendPoint,
  KnowledgeGapItem,
  CandidateClaim,
  CandidateEvidenceGraph,
  CoachHint,
  StartCoachingLoopPayload,
  SubmitCoachingStepPayload,
  OrchestratorStepResultDTO,
  ResearchTelemetryRecordDTO,
  StartCoachingFromInterviewPayload,
  InterviewWeaknessesResponse,
  AutonomousCoachingRecommendation,
  CandidateSkillStateDTO,
  ConversationDTO,
  ConversationDetailDTO,
  CreateConversationRequest,
  SendMessageRequest,
  SendMessageResponse,
  InitiateCoachingRequest,
  InitiateCoachingResponse,
} from '../types';

const API_BASE = '/api/v1';

let currentAuthToken: string | null = null;
try {
  currentAuthToken = sessionStorage.getItem('candidate_auth_token');
} catch {}

export function setAuthToken(token: string | null): void {
  currentAuthToken = token;
  try {
    if (token) {
      sessionStorage.setItem('candidate_auth_token', token);
      localStorage.setItem('candidate_auth_token', token);
    } else {
      sessionStorage.removeItem('candidate_auth_token');
      localStorage.removeItem('candidate_auth_token');
    }
  } catch {}
}

export function getAuthToken(): string | null {
  if (!currentAuthToken) {
    try {
      currentAuthToken = sessionStorage.getItem('candidate_auth_token') || localStorage.getItem('candidate_auth_token');
    } catch {}
  }
  return currentAuthToken;
}

export function clearAuthToken(): void {
  currentAuthToken = null;
  try {
    sessionStorage.removeItem('candidate_auth_token');
    localStorage.removeItem('candidate_auth_token');
  } catch {}
}

export async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = getAuthToken();
  if (!token) {
    return init !== undefined ? window.fetch(url, init) : window.fetch(url);
  }
  const existingHeaders = init?.headers;
  const headers: Record<string, string> = {};
  if (existingHeaders instanceof Headers) {
    existingHeaders.forEach((v, k) => { headers[k] = v; });
  } else if (Array.isArray(existingHeaders)) {
    existingHeaders.forEach(([k, v]) => { headers[k] = v; });
  } else if (existingHeaders) {
    Object.assign(headers, existingHeaders);
  }
  if (!headers['Authorization'] && !headers['authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return window.fetch(url, { ...init, headers });
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  clearAuthToken,
  setAuthToken,
  getAuthToken,

  // Authentication API
  async register(email: string, full_name: string, password?: string): Promise<{
    access_token: string;
    token_type: string;
    candidate_id: string;
    candidate: Candidate;
    auth_tier: string;
  }> {
    const payload: Record<string, string> = { email, full_name };
    if (password) payload.password = password;
    const res = await window.fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await handleResponse<{
      access_token: string;
      token_type: string;
      candidate_id: string;
      candidate: Candidate;
      auth_tier: string;
    }>(res);
    setAuthToken(data.access_token);
    return data;
  },

  async login(email: string, password?: string): Promise<{
    access_token: string;
    token_type: string;
    candidate_id: string;
    candidate: Candidate;
    auth_tier: string;
  }> {
    const payload: Record<string, string> = { email };
    if (password) payload.password = password;
    const res = await window.fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await handleResponse<{
      access_token: string;
      token_type: string;
      candidate_id: string;
      candidate: Candidate;
      auth_tier: string;
    }>(res);
    setAuthToken(data.access_token);
    return data;
  },

  async getMe(): Promise<{
    authenticated_candidate_id: string;
    candidate: Candidate;
  }> {
    const res = await authFetch(`${API_BASE}/auth/me`);
    return handleResponse(res);
  },

  async logout(): Promise<{ status: string; message: string }> {
    try {
      const res = await authFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
      const data = await handleResponse<{ status: string; message: string }>(res);
      clearAuthToken();
      return data;
    } catch {
      clearAuthToken();
      return { status: 'success', message: 'Logged out locally' };
    }
  },

  async requestCandidateToken(candidateId: string, email: string): Promise<{
    access_token: string;
    candidate_id: string;
    auth_tier: string;
  }> {
    const res = await window.fetch(`${API_BASE}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_id: candidateId, email }),
    });
    const data = await handleResponse<{
      access_token: string;
      candidate_id: string;
      auth_tier: string;
    }>(res);
    setAuthToken(data.access_token);
    return data;
  },

  // Candidate APIs
  async listCandidates(): Promise<{ candidates: Candidate[]; total: number }> {
    const res = await authFetch(`${API_BASE}/candidates`);
    return handleResponse(res);
  },

  async getCandidate(id: string): Promise<Candidate> {
    const res = await authFetch(`${API_BASE}/candidates/${id}`);
    return handleResponse(res);
  },

  async getCandidateReadiness(candidateId: string, targetRole?: string): Promise<import('../types').CandidateReadinessResponse> {
    const url = targetRole
      ? `${API_BASE}/candidates/${candidateId}/readiness?target_role=${encodeURIComponent(targetRole)}`
      : `${API_BASE}/candidates/${candidateId}/readiness`;
    const res = await authFetch(url);
    return handleResponse(res);
  },

  async createCandidate(email: string, full_name: string): Promise<Candidate> {
    const res = await authFetch(`${API_BASE}/candidates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, full_name }),
    });
    return handleResponse(res);
  },

  async updateCandidate(
    candidateId: string,
    payload: Partial<{ email: string; full_name: string; target_role: string | null }>
  ): Promise<Candidate> {
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async deleteCandidate(id: string): Promise<{ status: string; id: string }> {
    const res = await authFetch(`${API_BASE}/candidates/${id}`, { method: 'DELETE' });
    return handleResponse(res);
  },

  // Resume APIs
  async uploadResume(candidateId: string, file: File): Promise<{
    candidate_id: string;
    resume_id: string;
    status: string;
    profile: CandidateProfile;
    indexed_rag_chunks: number;
    created_at: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}/resumes`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  async getCandidateProfile(candidateId: string): Promise<CandidateProfile | null> {
    const res = await authFetch(`${API_BASE}/resumes/candidates/${candidateId}/profile`);
    if (res.status === 404) return null;
    return handleResponse(res);
  },

  async getCandidateDossier(candidateId: string, forceRefresh = false): Promise<any> {
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}/dossier?force_refresh=${forceRefresh}`);
    return handleResponse(res);
  },

  async queryResumeRAG(candidateId: string, query: string, top_k = 3): Promise<{
    candidate_id: string;
    query: string;
    results: Array<{ chunk_id: string; section_name: string; content: string; score: number }>;
  }> {
    const res = await authFetch(`${API_BASE}/resumes/candidates/${candidateId}/rag/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k }),
    });
    return handleResponse(res);
  },

  async listCandidateResumes(candidateId: string): Promise<ResumeSummary[]> {
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}/resumes`);
    return handleResponse(res);
  },

  async activateResume(candidateId: string, resumeId: string): Promise<ResumeSummary> {
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}/resumes/${resumeId}/activate`, {
      method: 'PUT',
    });
    return handleResponse(res);
  },

  // Interview APIs
  async createInterview(payload: {
    candidate_id: string;
    resume_id?: string;
    target_role: string;
    target_roles?: string[];
    custom_role_description?: string;
    interview_type: string;
    difficulty_level: string;
    target_question_count: number;
    coaching_mode?: string;
  }): Promise<InterviewSession> {
    const res = await authFetch(`${API_BASE}/interviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getInterview(interviewId: string): Promise<InterviewSession> {
    const res = await authFetch(`${API_BASE}/interviews/${interviewId}`);
    return handleResponse(res);
  },

  async startInterview(interviewId: string): Promise<InterviewSession> {
    const res = await authFetch(`${API_BASE}/interviews/${interviewId}/start`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async getInterviewHint(interviewId: string, partial_answer?: string): Promise<CoachHint> {
    const res = await authFetch(`${API_BASE}/interviews/${interviewId}/hint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ partial_answer }),
    });
    return handleResponse(res);
  },

  async submitAnswer(
    interviewId: string,
    answer_text: string,
    response_time_seconds = 0
  ): Promise<TurnAnswerResult> {
    const res = await authFetch(`${API_BASE}/interviews/${interviewId}/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer_text, response_time_seconds }),
    });
    return handleResponse(res);
  },

  async completeInterview(interviewId: string, reason: string = 'CANDIDATE_REQUESTED'): Promise<InterviewSession> {
    const res = await authFetch(`${API_BASE}/interviews/${interviewId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    return handleResponse(res);
  },

  async listCandidateInterviews(candidateId: string): Promise<InterviewSession[]> {
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}/interviews`);
    return handleResponse(res);
  },

  // Analytics APIs
  async getAnalyticsOverview(candidateId: string): Promise<AnalyticsOverview> {
    const res = await authFetch(`${API_BASE}/analytics/overview?candidate_id=${candidateId}`);
    return handleResponse(res);
  },

  async getPerformanceHistory(candidateId: string): Promise<{
    candidate_id: string;
    trends: PerformanceTrendPoint[];
    total_completed_interviews: number;
  }> {
    const res = await authFetch(`${API_BASE}/analytics/history?candidate_id=${candidateId}`);
    return handleResponse(res);
  },

  async getSkillsAnalytics(candidateId: string): Promise<{
    candidate_id: string;
    topic_scores: Record<string, number>;
    knowledge_gaps: KnowledgeGapItem[];
  }> {
    const res = await authFetch(`${API_BASE}/analytics/skills?candidate_id=${candidateId}`);
    return handleResponse(res);
  },

  // Candidate Evidence Graph & Claims APIs
  async getCandidateClaims(candidateId: string): Promise<CandidateClaim[]> {
    try {
      const res = await authFetch(`${API_BASE}/candidates/${candidateId}/claims`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback handled gracefully
    }
    return [];
  },

  async getCandidateEvidenceGraph(candidateId: string): Promise<CandidateEvidenceGraph> {
    try {
      const res = await authFetch(`${API_BASE}/candidates/${candidateId}/evidence-graph`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return {
      candidate_id: candidateId,
      total_claims: 0,
      verified_count: 0,
      probed_count: 0,
      overall_verification_ratio: 0,
      claims: [],
    };
  },

  // Transfer-Aware Coaching APIs (Phase 4)
  async startTransferCoaching(payload: StartCoachingLoopPayload): Promise<OrchestratorStepResultDTO> {
    const res = await authFetch(`${API_BASE}/coaching/start-loop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async submitCoachingStep(payload: SubmitCoachingStepPayload): Promise<OrchestratorStepResultDTO> {
    const res = await authFetch(`${API_BASE}/coaching/submit-step`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getCoachingSession(sessionId: string): Promise<OrchestratorStepResultDTO> {
    const res = await authFetch(`${API_BASE}/coaching/session/${sessionId}`);
    return handleResponse(res);
  },

  async getCoachingTelemetry(sessionId: string): Promise<ResearchTelemetryRecordDTO> {
    const res = await authFetch(`${API_BASE}/coaching/session/${sessionId}/telemetry`);
    return handleResponse(res);
  },

  async startCoachingFromInterview(payload: StartCoachingFromInterviewPayload): Promise<OrchestratorStepResultDTO> {
    const res = await authFetch(`${API_BASE}/coaching/start-from-interview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getInterviewWeaknesses(sessionId: string, threshold = 7.0): Promise<InterviewWeaknessesResponse> {
    const res = await authFetch(`${API_BASE}/interviews/${sessionId}/weaknesses?eligibility_threshold=${threshold}`);
    return handleResponse(res);
  },

  async getCoachingRecommendation(candidateId: string, targetRole?: string): Promise<AutonomousCoachingRecommendation> {
    const roleParam = targetRole ? `&target_role=${encodeURIComponent(targetRole)}` : '';
    const res = await authFetch(`${API_BASE}/coaching/recommendation?candidate_id=${encodeURIComponent(candidateId)}${roleParam}`);
    return handleResponse(res);
  },

  async getCandidateSkillStates(candidateId: string): Promise<CandidateSkillStateDTO[]> {
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}/skill-states`);
    return handleResponse(res);
  },

  // Roadmap & Skill Gap APIs
  async listTargetRoles(): Promise<Array<{
    key: string;
    display_name: string;
    aliases: string[];
    description: string;
    responsibilities: string[];
    knowledge_areas: string[];
    competencies: Array<{
      identifier: string;
      name: string;
      description: string;
      importance: string;
      core_invariants: string[];
      expected_concepts: string[];
    }>;
  }>> {
    const res = await authFetch(`${API_BASE}/roadmap/roles`);
    return handleResponse(res);
  },

  async researchRole(spec: {
    role_name: string;
    role_category?: string;
    industry?: string;
    experience_level?: string;
    target_company?: string;
    target_location?: string;
    force_refresh?: boolean;
  }): Promise<any> {
    const res = await authFetch(`${API_BASE}/roles/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
    });
    return handleResponse(res);
  },

  async getRoleResearch(roleName: string, experienceLevel = 'Mid', forceRefresh = false): Promise<any> {
    const params = new URLSearchParams({
      experience_level: experienceLevel,
      force_refresh: String(forceRefresh),
    });
    const res = await authFetch(`${API_BASE}/roles/research/${encodeURIComponent(roleName)}?${params.toString()}`);
    return handleResponse(res);
  },

  async matchRole(candidateId: string, roleName: string, experienceLevel = 'Mid', forceRefresh = false): Promise<any> {
    const res = await authFetch(`${API_BASE}/roles/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: candidateId,
        role_name: roleName,
        experience_level: experienceLevel,
        force_refresh: forceRefresh,
      }),
    });
    return handleResponse(res);
  },

  async getRoleRecommendations(candidateId: string): Promise<import('../types').RoleRecommendationsResponse> {
    const res = await authFetch(`${API_BASE}/roadmap/roles/recommendations?candidate_id=${candidateId}`);
    return handleResponse(res);
  },

  async getSkillGaps(candidateId: string, targetRole: string, seniority = 'Mid'): Promise<import('../types/roadmap').SkillGapAnalysisResult> {
    const params = new URLSearchParams({
      candidate_id: candidateId,
      target_role: targetRole,
      seniority,
    });
    const res = await authFetch(`${API_BASE}/roadmap/gaps?${params.toString()}`);
    return handleResponse(res);
  },

  async generateRoadmap(candidateId: string, targetRole: string, seniority = 'Mid'): Promise<import('../types/roadmap').PersonalizedRoadmapDTO> {
    const res = await authFetch(`${API_BASE}/roadmap/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: candidateId,
        target_role: targetRole,
        seniority,
      }),
    });
    return handleResponse(res);
  },

  async getCandidateRoadmap(candidateId: string): Promise<import('../types/roadmap').PersonalizedRoadmapDTO> {
    const res = await authFetch(`${API_BASE}/roadmap/candidate/${candidateId}`);
    return handleResponse(res);
  },

  async startCoachingFromRoadmapItem(itemId: string, candidateId?: string): Promise<import('../types/roadmap').StartCoachingFromRoadmapResponse> {
    const res = await authFetch(`${API_BASE}/roadmap/items/${itemId}/start-coaching`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(candidateId ? { candidate_id: candidateId } : {}),
    });
    return handleResponse(res);
  },

  async syncRoadmapProgress(candidateId: string): Promise<import('../types/roadmap').PersonalizedRoadmapDTO> {
    const res = await authFetch(`${API_BASE}/roadmap/candidate/${candidateId}/sync-progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  // Conversational AI Coaching Studio APIs
  async initiateCoachingSession(payload: InitiateCoachingRequest): Promise<InitiateCoachingResponse> {
    const res = await authFetch(`${API_BASE}/chat/coaching/initiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Chat & Conversational Coach APIs (Phase 3)
  async createConversation(payload: CreateConversationRequest): Promise<ConversationDTO> {
    const res = await authFetch(`${API_BASE}/chat/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async listConversations(candidateId?: string): Promise<ConversationDTO[]> {
    const url = candidateId
      ? `${API_BASE}/chat/conversations?candidate_id=${encodeURIComponent(candidateId)}`
      : `${API_BASE}/chat/conversations`;
    const res = await authFetch(url);
    return handleResponse(res);
  },

  async getConversation(conversationId: string, candidateId?: string): Promise<ConversationDetailDTO> {
    const url = candidateId
      ? `${API_BASE}/chat/conversations/${conversationId}?candidate_id=${encodeURIComponent(candidateId)}`
      : `${API_BASE}/chat/conversations/${conversationId}`;
    const res = await authFetch(url);
    return handleResponse(res);
  },

  async renameConversation(
    conversationId: string,
    title: string,
    candidateId?: string
  ): Promise<ConversationDTO> {
    const url = candidateId
      ? `${API_BASE}/chat/conversations/${conversationId}?candidate_id=${encodeURIComponent(candidateId)}`
      : `${API_BASE}/chat/conversations/${conversationId}`;
    const res = await authFetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    return handleResponse(res);
  },

  async deleteConversation(
    conversationId: string,
    candidateId?: string
  ): Promise<{ status: string; deleted_id: string }> {
    const url = candidateId
      ? `${API_BASE}/chat/conversations/${conversationId}?candidate_id=${encodeURIComponent(candidateId)}`
      : `${API_BASE}/chat/conversations/${conversationId}`;
    const res = await authFetch(url, { method: 'DELETE' });
    return handleResponse(res);
  },

  async sendChatMessage(
    conversationId: string,
    payload: SendMessageRequest
  ): Promise<SendMessageResponse> {
    const res = await authFetch(`${API_BASE}/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Research Analytics & Experiments (Phase 4)
  async getResearchSessionMetrics(sessionId: string): Promise<import('../types/research').CandidateResearchResult> {
    const res = await authFetch(`${API_BASE}/research/session/${encodeURIComponent(sessionId)}`);
    return handleResponse(res);
  },

  async getCandidateResearchMetrics(candidateId: string): Promise<import('../types/research').CandidateResearchResult[]> {
    const res = await authFetch(`${API_BASE}/research/candidate/${encodeURIComponent(candidateId)}`);
    return handleResponse(res);
  },

  async getResearchConditionSummary(condition: string): Promise<import('../types/research').ResearchConditionSummary> {
    const res = await authFetch(`${API_BASE}/research/condition/${encodeURIComponent(condition)}`);
    return handleResponse(res);
  },

  async getResearchComparison(): Promise<import('../types/research').ConditionComparison> {
    const res = await authFetch(`${API_BASE}/research/compare`);
    return handleResponse(res);
  },

  // Participant Study Journey & Consent (Phase 9.3)
  async getStudyInfo(): Promise<import('../types/research').StudyInformation> {
    const res = await authFetch(`${API_BASE}/experiments/study-info`);
    return handleResponse(res);
  },

  async getParticipantConsent(candidateId: string): Promise<import('../types/research').ConsentRecord> {
    const res = await authFetch(`${API_BASE}/experiments/consent/${encodeURIComponent(candidateId)}`);
    return handleResponse(res);
  },

  async submitParticipantConsent(
    candidateId: string,
    consentVersion: string = 'v1.0-feasibility-study',
    agreed: boolean = true
  ): Promise<import('../types/research').ConsentRecord> {
    const res = await authFetch(`${API_BASE}/experiments/consent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: candidateId,
        consent_version: consentVersion,
        agreed,
      }),
    });
    return handleResponse(res);
  },

  async withdrawParticipant(
    candidateId: string,
    reason?: string
  ): Promise<import('../types/research').ParticipantWithdrawalResult> {
    const res = await authFetch(`${API_BASE}/experiments/withdraw`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: candidateId,
        reason: reason || 'Voluntary participant withdrawal',
        data_policy: 'EXCLUDE_FROM_ANALYSIS',
      }),
    });
    return handleResponse(res);
  },

  async getActiveExperimentSession(
    candidateId: string
  ): Promise<import('../types/research').ActiveSessionResponse> {
    const res = await authFetch(`${API_BASE}/experiments/candidate/${encodeURIComponent(candidateId)}/active`);
    return handleResponse(res);
  },

  async startExperiment(
    candidateId: string,
    config: any,
    experimentName: string = 'Feasibility_Pilot_Trial_v1'
  ): Promise<import('../types/research').ExperimentStepResult> {
    const res = await authFetch(`${API_BASE}/experiments/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: candidateId,
        config,
        experiment_name: experimentName,
      }),
    });
    return handleResponse(res);
  },

  async submitExperimentStep(
    sessionId: string,
    candidateAnswer: string,
    hintsRequested: number = 0,
    responseTimeSeconds: number = 0
  ): Promise<import('../types/research').ExperimentStepResult> {
    const res = await authFetch(`${API_BASE}/experiments/${encodeURIComponent(sessionId)}/step`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_answer: candidateAnswer,
        hints_requested: hintsRequested,
        response_time_seconds: responseTimeSeconds,
      }),
    });
    return handleResponse(res);
  },

  async getDueRetentions(): Promise<import('../types/research').RetentionSchedule[]> {
    const res = await authFetch(`${API_BASE}/experiments/retention/due`);
    return handleResponse(res);
  },

  async devResetDatabase(confirmation: string = 'CONFIRM_DEVELOPMENT_RESET'): Promise<{
    status: string;
    message: string;
    database_target: string;
    total_records_cleared: number;
    cleared_records: Record<string, number>;
    preserved_system_tables: Record<string, number>;
  }> {
    const res = await window.fetch(`${API_BASE}/auth/dev-reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmation }),
    });
    return handleResponse(res);
  },
};


