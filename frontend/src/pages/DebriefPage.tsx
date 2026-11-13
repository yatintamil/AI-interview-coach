import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { InterviewSession, Candidate } from '../types';
import { SessionDebriefCard } from '../components/studio/SessionDebriefCard';
import { Card, Button, Badge, EmptyState, LoadingState } from '../components/common';
import { Video, Award, Calendar, ArrowRight } from 'lucide-react';
import { useAppSession, useSafeNavigate } from '../context/AppSessionContext';

interface DebriefPageProps {
  onNavigateToCoaching?: (context: {
    interviewSessionId: string;
    questionId?: string;
    skillId?: string;
    coachingSessionId?: string;
  }) => void;
}

export const DebriefPage: React.FC<DebriefPageProps> = ({ onNavigateToCoaching }) => {
  const { sessionId: paramSessionId } = useParams<{ sessionId?: string }>();
  const navigate = useSafeNavigate();
  const {
    interviewSessionId,
    setInterviewSessionId,
    selectedCandidate,
    setSelectedCandidateId,
  } = useAppSession();

  const querySessionId = typeof window !== 'undefined' && window.location?.search
    ? new URLSearchParams(window.location.search).get('interviewId') || new URLSearchParams(window.location.search).get('sessionId')
    : null;

  const activeSessionId = paramSessionId || querySessionId || interviewSessionId;

  const [session, setSession] = useState<InterviewSession | null>(null);
  const [candidateSessions, setCandidateSessions] = useState<InterviewSession[]>([]);
  const [sessionCandidate, setSessionCandidate] = useState<Candidate | null>(selectedCandidate);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync route param into context
  useEffect(() => {
    if (paramSessionId && paramSessionId !== 'undefined' && paramSessionId !== interviewSessionId) {
      setInterviewSessionId(paramSessionId);
    }
  }, [paramSessionId, interviewSessionId, setInterviewSessionId]);

  // Load candidate's previous sessions if active session is not loaded yet
  useEffect(() => {
    if (selectedCandidate && typeof api.listCandidateInterviews === 'function') {
      api
        .listCandidateInterviews(selectedCandidate.id)
        .then((list) => {
          setCandidateSessions(list || []);
        })
        .catch(() => {
          setCandidateSessions([]);
        });
    } else {
      setCandidateSessions([]);
    }
  }, [selectedCandidate?.id]);

  useEffect(() => {
    if (!activeSessionId || activeSessionId === 'undefined') {
      setSession(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    api
      .getInterview(activeSessionId)
      .then(async (loadedSession) => {
        if (!isMounted) return;
        setSession(loadedSession);

        if (!selectedCandidate || selectedCandidate.id !== loadedSession.candidate_id) {
          try {
            const cand = await api.getCandidate(loadedSession.candidate_id);
            if (isMounted) {
              setSessionCandidate(cand);
              setSelectedCandidateId(cand.id);
            }
          } catch {
            // fallback
          }
        } else {
          setSessionCandidate(selectedCandidate);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to retrieve interview session.');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeSessionId, selectedCandidate, setSelectedCandidateId]);

  if (loading) {
    return (
      <div style={{ maxWidth: '720px', margin: '40px auto' }}>
        <LoadingState
          message="Retrieving Interview Debrief..."
          subtext={`Loading rubric evaluations, evidence, and scores for session ${activeSessionId}`}
          minHeight="260px"
        />
      </div>
    );
  }

  if (error || !session) {
    const completedSessions = candidateSessions.filter((s) => s.status === 'COMPLETED');

    return (
      <div className="fade-in debrief-selection-container" style={{ maxWidth: '840px', margin: '30px auto' }}>
        {completedSessions.length > 0 ? (
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Award size={18} color="var(--accent-primary)" />
                <span>Completed Interview Sessions ({completedSessions.length})</span>
              </div>
            }
            subtitle={`Select an interview session for ${selectedCandidate?.full_name || 'candidate'} to inspect its rubric assessment & debrief.`}
            actions={
              <Button
                variant="primary"
                size="sm"
                icon={<Video size={14} />}
                onClick={() => navigate('/interview')}
              >
                Start New Interview
              </Button>
            }
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {completedSessions.map((s) => (
                <div
                  key={s.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 18px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    flexWrap: 'wrap',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <strong style={{ color: '#fff', fontSize: '0.95rem' }}>{s.target_role}</strong>
                      <Badge variant="verified" size="sm">COMPLETED</Badge>
                      {s.report?.final_score !== undefined && (
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--status-verified)' }}>
                          Score: {Math.round(s.report.final_score <= 10 ? s.report.final_score * 10 : s.report.final_score)}/100
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Calendar size={13} />
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : 'Recent'}
                      </span>
                      <span>Questions: {s.target_question_count}</span>
                    </div>
                  </div>

                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<ArrowRight size={14} />}
                    iconPosition="right"
                    onClick={() => {
                      setInterviewSessionId(s.id);
                      navigate(`/debrief/${s.id}`);
                    }}
                  >
                    View Debrief
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        ) : (
          <EmptyState
            icon={<Award size={40} />}
            title={error ? 'Debrief Unavailable' : 'No Completed Interview Selected'}
            description={
              error ||
              'Complete an adaptive technical interview to generate an executive debrief, rubric breakdown, and AI coaching recommendations.'
            }
            action={
              <Button
                variant="primary"
                icon={<Video size={16} />}
                onClick={() => navigate('/interview')}
              >
                Go to Interview Studio
              </Button>
            }
          />
        )}
      </div>
    );
  }

  const effectiveCandidate: Candidate = sessionCandidate || {
    id: session.candidate_id,
    email: '',
    full_name: 'Candidate',
    created_at: new Date().toISOString(),
    resumes: [],
    has_profile: true,
    skills_summary: [],
    total_years_exp: 0,
  };

  return (
    <div className="fade-in debrief-page-container" style={{ padding: '8px 0 32px 0' }}>
      <SessionDebriefCard
        session={session}
        candidate={effectiveCandidate}
        onNavigateToAnalytics={() => navigate('/analytics')}
        onRetake={() => navigate('/interview')}
        onNavigateToCoaching={(ctx) => {
          if (onNavigateToCoaching) {
            onNavigateToCoaching(ctx);
          } else {
            const params = new URLSearchParams();
            if (ctx.interviewSessionId) params.set('interviewId', ctx.interviewSessionId);
            if (ctx.questionId) params.set('questionId', ctx.questionId);
            if (ctx.skillId) params.set('skillId', ctx.skillId);
            navigate(`/coaching?${params.toString()}`);
          }
        }}
      />
    </div>
  );
};
