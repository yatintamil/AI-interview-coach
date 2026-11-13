import React from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { useAppSession } from './context/AppSessionContext';
import { CandidateAuthGate } from './components/auth/CandidateAuthGate';
import { AppWorkspaceLayout } from './layouts/AppWorkspaceLayout';
import { OverviewWorkspace } from './features/overview/OverviewWorkspace';
import { ProfileDossierWorkspace } from './features/profile/ProfileDossierWorkspace';
import { ResumeInspectionWorkspace } from './features/resume/ResumeInspectionWorkspace';
import { InterviewStudioWorkspace } from './features/interview/InterviewStudioWorkspace';
import { InterviewHistoryWorkspace } from './features/interview/InterviewHistoryWorkspace';
import { EvaluationDebriefWorkspace } from './features/evaluation/EvaluationDebriefWorkspace';
import { TargetRoleSelectionWorkspace } from './features/roles/TargetRoleSelectionWorkspace';
import { SkillGapComparisonWorkspace } from './features/skills/SkillGapComparisonWorkspace';
import { RoadmapPage } from './pages/RoadmapPage';
import { CoachingStudioPage } from './pages/CoachingStudioPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ExperimentStudyPage } from './pages/ExperimentStudyPage';
import { NotFoundPage } from './pages/NotFoundPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <CandidateAuthGate>{children}</CandidateAuthGate>;
};

export const App: React.FC = () => {
  const navigate = useNavigate();
  const {
    candidates,
    selectedCandidate,
    setSelectedCandidateId,
    refreshCandidates,
    activeRoleId,
    setActiveRoleId,
    coachingInterviewContext,
    setCoachingInterviewContext,
  } = useAppSession();

  const handleNavigateToCoaching = (ctx?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
    coachingSessionId?: string;
  }) => {
    if (ctx?.coachingSessionId) {
      navigate(`/coaching/${ctx.coachingSessionId}`);
    } else if (ctx?.interviewSessionId) {
      setCoachingInterviewContext(ctx);
      const params = new URLSearchParams();
      params.set('interviewId', ctx.interviewSessionId);
      if (ctx.questionId) params.set('questionId', ctx.questionId);
      if (ctx.skillId) params.set('skillId', ctx.skillId);
      params.set('mode', 'practice');
      navigate(`/coaching?${params.toString()}`);
    } else {
      navigate('/coaching');
    }
  };

  return (
    <AppWorkspaceLayout>
      <Routes>
        {/* Workspace Routes */}
        <Route
          path="/"
          element={<OverviewWorkspace onOpenNewCandidateModal={() => navigate('/profile')} />}
        />
        <Route
          path="/overview"
          element={<OverviewWorkspace onOpenNewCandidateModal={() => navigate('/profile')} />}
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <ProfileDossierWorkspace
                candidates={candidates}
                selectedCandidate={selectedCandidate}
                onSelectCandidate={(c) => setSelectedCandidateId(c.id)}
                onRefreshCandidates={refreshCandidates}
                onNavigateToResume={() => navigate('/resume')}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/resume"
          element={
            <ProtectedRoute>
              <ResumeInspectionWorkspace
                onStartInterview={(role) => {
                  if (role) setActiveRoleId(role);
                  navigate('/interview');
                }}
              />
            </ProtectedRoute>
          }
        />

        <Route
          path="/roles"
          element={
            <ProtectedRoute>
              <TargetRoleSelectionWorkspace />
            </ProtectedRoute>
          }
        />

        {/* Interview Assessment Routes */}
        <Route
          path="/interview"
          element={
            <ProtectedRoute>
              <InterviewStudioWorkspace
                selectedCandidate={selectedCandidate}
                initialRole={activeRoleId}
                onNavigateToAnalytics={() => navigate('/analytics')}
                onNavigateToCoaching={handleNavigateToCoaching}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interview/:sessionId"
          element={
            <ProtectedRoute>
              <InterviewStudioWorkspace
                selectedCandidate={selectedCandidate}
                initialRole={activeRoleId}
                onNavigateToAnalytics={() => navigate('/analytics')}
                onNavigateToCoaching={handleNavigateToCoaching}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interviews"
          element={
            <ProtectedRoute>
              <InterviewHistoryWorkspace />
            </ProtectedRoute>
          }
        />
        <Route
          path="/debrief"
          element={
            <ProtectedRoute>
              <EvaluationDebriefWorkspace onNavigateToCoaching={handleNavigateToCoaching} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/debrief/:sessionId"
          element={
            <ProtectedRoute>
              <EvaluationDebriefWorkspace onNavigateToCoaching={handleNavigateToCoaching} />
            </ProtectedRoute>
          }
        />

        {/* Learning & Independent Transfer Routes */}
        <Route
          path="/skills"
          element={
            <ProtectedRoute>
              <SkillGapComparisonWorkspace />
            </ProtectedRoute>
          }
        />
        <Route
          path="/roadmap"
          element={
            <ProtectedRoute>
              <RoadmapPage
                selectedCandidate={selectedCandidate}
                onNavigateToCoaching={handleNavigateToCoaching}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/coaching"
          element={
            <ProtectedRoute>
              <CoachingStudioPage
                selectedCandidate={selectedCandidate}
                initialMode="conversation"
                onNavigateToAnalytics={() => navigate('/analytics')}
                initialInterviewContext={coachingInterviewContext}
                onClearInitialContext={() => setCoachingInterviewContext(null)}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/coaching/:coachingSessionId"
          element={
            <ProtectedRoute>
              <CoachingStudioPage
                selectedCandidate={selectedCandidate}
                onNavigateToAnalytics={() => navigate('/analytics')}
                initialInterviewContext={coachingInterviewContext}
                onClearInitialContext={() => setCoachingInterviewContext(null)}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/coaching/chat/:conversationId"
          element={
            <ProtectedRoute>
              <CoachingStudioPage
                selectedCandidate={selectedCandidate}
                initialMode="conversation"
                onNavigateToAnalytics={() => navigate('/analytics')}
                initialInterviewContext={coachingInterviewContext}
                onClearInitialContext={() => setCoachingInterviewContext(null)}
              />
            </ProtectedRoute>
          }
        />
        {/* Legacy deep links and routes compatibly aliased to unified coaching workspace */}
        <Route
          path="/transfer"
          element={
            <ProtectedRoute>
              <CoachingStudioPage
                selectedCandidate={selectedCandidate}
                initialMode="transfer"
                onNavigateToAnalytics={() => navigate('/analytics')}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <CoachingStudioPage
                selectedCandidate={selectedCandidate}
                initialMode="conversation"
                onNavigateToAnalytics={() => navigate('/analytics')}
                initialInterviewContext={coachingInterviewContext}
                onClearInitialContext={() => setCoachingInterviewContext(null)}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chat/:conversationId"
          element={
            <ProtectedRoute>
              <CoachingStudioPage
                selectedCandidate={selectedCandidate}
                initialMode="conversation"
                onNavigateToAnalytics={() => navigate('/analytics')}
                initialInterviewContext={coachingInterviewContext}
                onClearInitialContext={() => setCoachingInterviewContext(null)}
              />
            </ProtectedRoute>
          }
        />

        {/* Insights & Research Routes */}
        <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <AnalyticsPage
                selectedCandidate={selectedCandidate}
                onStartInterview={() => navigate('/interview')}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/study"
          element={
            <ProtectedRoute>
              <ExperimentStudyPage selectedCandidate={selectedCandidate} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/experiment"
          element={
            <ProtectedRoute>
              <ExperimentStudyPage selectedCandidate={selectedCandidate} />
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppWorkspaceLayout>
  );
};
