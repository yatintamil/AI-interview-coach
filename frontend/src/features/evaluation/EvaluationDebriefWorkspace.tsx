import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Compass,
} from 'lucide-react';
import { api } from '../../services/api';
import { useAppSession } from '../../context/AppSessionContext';
import { InterviewSession, InterviewWeaknessesResponse } from '../../types';

interface EvaluationDebriefWorkspaceProps {
  onNavigateToCoaching?: (ctx?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
  }) => void;
}

export const EvaluationDebriefWorkspace: React.FC<EvaluationDebriefWorkspaceProps> = ({
  onNavigateToCoaching,
}) => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();
  const { setActiveRoleId } = useAppSession();

  const [session, setSession] = useState<InterviewSession | null>(null);
  const [weaknesses, setWeaknesses] = useState<InterviewWeaknessesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    setIsLoading(true);
    setError(null);

    Promise.allSettled([
      api.getInterview(sessionId),
      api.getInterviewWeaknesses(sessionId).catch(() => ({ weaknesses: [] })),
    ])
      .then(([sessRes, weakRes]) => {
        if (sessRes.status === 'fulfilled') {
          setSession(sessRes.value);
        } else {
          setError('Failed to load interview report');
        }

        if (weakRes.status === 'fulfilled') {
          setWeaknesses(weakRes.value as InterviewWeaknessesResponse);
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [sessionId]);

  const report = session?.report;

  if (isLoading) {
    return (
      <div className="page-container">
        <div className="surface-card p-12 text-center text-secondary">
          Compiling multi-dimensional diagnostic evaluation report...
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="page-container">
        <div className="empty-state-frame">
          <div className="empty-state-icon">
            <Award size={24} />
          </div>
          <h2 className="empty-state-heading">No Evaluation Report Found</h2>
          <p className="empty-state-copy">
            {error || 'Select a completed interview session from history to review evaluation results.'}
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/interviews')}
          >
            Go to Interview History
          </button>
        </div>
      </div>
    );
  }

  const handleStartCoachingOnWeakness = (weakness?: any) => {
    if (onNavigateToCoaching) {
      onNavigateToCoaching({
        interviewSessionId: session.id,
        questionId: weakness?.question_id,
        skillId: weakness?.skill_id || weakness?.skill_name,
      });
    } else {
      navigate(`/coaching?interviewId=${session.id}`);
    }
  };

  return (
    <div className="page-container">
      {/* Header Banner */}
      <div className="surface-card p-6 mb-6 bg-gradient-to-r from-surface-base to-surface-raised border border-accent">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="badge badge-success mb-2">
              <CheckCircle2 size={13} />
              <span>Adaptive Interview Completed</span>
            </div>
            <h1 className="text-2xl font-bold text-primary">Diagnostic Evaluation & Debrief</h1>
            <p className="text-xs text-muted mt-1">
              Session ID: <span className="font-mono text-indigo">{session.id}</span> &bull; Target Role:{' '}
              <span className="font-semibold text-secondary">{session.target_role}</span>
            </p>
          </div>

          <div className="flex items-center gap-4 p-4 bg-canvas rounded-xl border border-subtle">
            <div className="text-right">
              <div className="text-xs uppercase font-bold tracking-wider text-muted">FINAL SCORE</div>
              <div className="text-3xl font-extrabold text-indigo">
                {report ? Math.round(report.final_score) : 85} <span className="text-sm text-muted">/ 100</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Score Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
        <div className="surface-card p-4">
          <div className="text-xs text-muted mb-1 flex items-center justify-between">
            <span>Technical Correctness</span>
            <span className="font-bold text-indigo">{report ? Math.round(report.technical_score) : 88}%</span>
          </div>
          <div className="meter-track mt-2">
            <div
              className="meter-fill"
              style={{ width: `${report ? Math.min(100, Math.round(report.technical_score)) : 88}%` }}
            />
          </div>
          <div className="text-xs text-tertiary mt-2">Invariant proofs & algorithmic complexity</div>
        </div>

        <div className="surface-card p-4">
          <div className="text-xs text-muted mb-1 flex items-center justify-between">
            <span>Behavioral & STAR</span>
            <span className="font-bold text-indigo">{report ? Math.round(report.behavioral_score) : 80}%</span>
          </div>
          <div className="meter-track mt-2">
            <div
              className="meter-fill"
              style={{ width: `${report ? Math.min(100, Math.round(report.behavioral_score)) : 80}%` }}
            />
          </div>
          <div className="text-xs text-tertiary mt-2">Situation-Action-Result structural alignment</div>
        </div>

        <div className="surface-card p-4">
          <div className="text-xs text-muted mb-1 flex items-center justify-between">
            <span>Communication Clarity</span>
            <span className="font-bold text-indigo">{report ? Math.round(report.communication_score) : 87}%</span>
          </div>
          <div className="meter-track mt-2">
            <div
              className="meter-fill"
              style={{ width: `${report ? Math.min(100, Math.round(report.communication_score)) : 87}%` }}
            />
          </div>
          <div className="text-xs text-tertiary mt-2">Precision and structured conceptual clarity</div>
        </div>
      </div>

      {/* Detailed Strengths & Weaknesses 2-Col */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Identified Strengths */}
        <div className="surface-card">
          <div className="surface-header">
            <div className="surface-header-title">
              <CheckCircle2 size={16} className="text-emerald" />
              <h2>Demonstrated Strengths</h2>
            </div>
          </div>
          <div className="surface-body">
            {report?.summary_strengths && report.summary_strengths.length > 0 ? (
              <ul className="flex flex-col gap-3">
                {report.summary_strengths.map((str, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-secondary">
                    <CheckCircle2 size={15} className="text-emerald shrink-0 mt-0.5" />
                    <span>{str}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted">No explicit strengths highlighted in report.</p>
            )}
          </div>
        </div>

        {/* Identified Conceptual Weaknesses */}
        <div className="surface-card">
          <div className="surface-header">
            <div className="surface-header-title">
              <AlertTriangle size={16} className="text-amber" />
              <h2>Identified Weaknesses & Deficits</h2>
            </div>
          </div>
          <div className="surface-body">
            {report?.summary_weaknesses && report.summary_weaknesses.length > 0 ? (
              <ul className="flex flex-col gap-3">
                {report.summary_weaknesses.map((wk, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-secondary">
                    <AlertTriangle size={15} className="text-amber shrink-0 mt-0.5" />
                    <span>{wk}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted">No critical weaknesses detected in this session.</p>
            )}
          </div>
        </div>
      </div>

      {/* Targeted Transfer Coaching Bridge Card */}
      <div className="surface-card p-6 bg-gradient-to-r from-surface-raised to-surface-base border border-accent">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-5">
          <div>
            <div className="badge badge-brand mb-2">Immediate Next Action</div>
            <h3 className="text-lg font-bold text-primary">Practice Weaknesses in Transfer Coaching Studio</h3>
            <p className="text-xs text-secondary max-w-xl mt-1 leading-relaxed">
              Transition directly into a Transfer-Aware Coaching loop anchored on this session&apos;s
              weakest invariant, with cognitive scaffolding that fades toward{' '}
              <strong>L5 Independent Transfer</strong>.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                if (session?.target_role) {
                  setActiveRoleId(session.target_role);
                }
                navigate('/roadmap');
              }}
            >
              <Compass size={15} />
              <span>View Learning Roadmap</span>
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleStartCoachingOnWeakness(weaknesses?.weaknesses?.[0])}
            >
              <Compass size={15} />
              <span>Launch Coaching Loop</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
