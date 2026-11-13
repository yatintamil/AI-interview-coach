import React, { useEffect, useState } from 'react';
import { InterviewSession, Candidate } from '../../types';
import { Award, ArrowRight, RotateCcw, BarChart2, CheckCircle2, AlertTriangle, Target, Compass } from 'lucide-react';
import { api } from '../../services/api';
import { InterviewWeaknessItem } from '../../types/coaching';

interface SessionDebriefCardProps {
  session: InterviewSession;
  candidate: Candidate;
  onNavigateToAnalytics: () => void;
  onRetake: () => void;
  onNavigateToCoaching?: (context: { interviewSessionId: string; questionId?: string; skillId?: string }) => void;
}

export const SessionDebriefCard: React.FC<SessionDebriefCardProps> = ({
  session,
  candidate,
  onNavigateToAnalytics,
  onRetake,
  onNavigateToCoaching,
}) => {
  const report = session.report;
  const [weaknesses, setWeaknesses] = useState<InterviewWeaknessItem[]>([]);

  useEffect(() => {
    let isMounted = true;
    const loadWeaknesses = async () => {
      try {
        const res = await api.getInterviewWeaknesses(session.id);
        if (isMounted && res && res.weaknesses) {
          setWeaknesses(res.weaknesses);
        }
      } catch (err) {
        console.warn('Failed to load session weaknesses for coaching recommendations:', err);
      }
    };
    loadWeaknesses();
    return () => {
      isMounted = false;
    };
  }, [session.id]);

  const to100 = (v: number | undefined, fallback: number) => {
    if (v === undefined || v === null) return fallback;
    return v <= 10 ? Math.round(v * 10) : Math.round(v);
  };
  const finalScore = to100(report?.final_score, 75);
  const techScore = to100(report?.technical_score, 70);
  const behScore = to100(report?.behavioral_score, 75);
  const commScore = to100(report?.communication_score, 80);

  return (
    <div className="studio-panel fade-in" style={{ maxWidth: '880px', margin: '0 auto', padding: '30px' }}>
      {/* Header Banner */}
      <div style={{ textAlign: 'center', marginBottom: '28px' }}>
        <div style={{ display: 'inline-flex', padding: '12px', borderRadius: '50%', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-primary)', marginBottom: '12px' }}>
          <Award size={36} />
        </div>
        <h2 style={{ fontSize: '1.6rem', marginBottom: '6px' }}>Adaptive Interview Completed</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
          Executive debrief & rubric assessment for <strong style={{ color: '#fff' }}>{candidate.full_name}</strong> in{' '}
          <span style={{ color: 'var(--accent-primary)' }}>{session.target_role}</span>
        </p>
      </div>

      {/* Main Scorecard Metrics */}
      <div className="grid-4" style={{ marginBottom: '28px' }}>
        <div className="studio-panel" style={{ textAlign: 'center', padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '6px' }}>FINAL SCORE</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: finalScore >= 70 ? 'var(--status-verified)' : 'var(--status-contested)' }}>
            {finalScore}<span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/100</span>
          </div>
        </div>

        <div className="studio-panel" style={{ textAlign: 'center', padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '6px' }}>TECHNICAL DEPTH</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#60a5fa' }}>
            {techScore}%
          </div>
        </div>

        <div className="studio-panel" style={{ textAlign: 'center', padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '6px' }}>BEHAVIORAL / STAR</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#a78bfa' }}>
            {behScore}%
          </div>
        </div>

        <div className="studio-panel" style={{ textAlign: 'center', padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '6px' }}>COMMUNICATION</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#34d399' }}>
            {commScore}%
          </div>
        </div>
      </div>

      {/* Strengths & Weaknesses Breakdown */}
      {report && (
        <div className="grid-2" style={{ marginBottom: '28px' }}>
          <div className="studio-panel" style={{ padding: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-verified)', fontWeight: 600, marginBottom: '12px' }}>
              <CheckCircle2 size={16} />
              <span>Demonstrated Strengths</span>
            </div>
            <ul style={{ paddingLeft: '18px', fontSize: '0.85rem', color: 'var(--text-main)', lineHeight: 1.6 }}>
              {(report.summary_strengths || []).map((s, idx) => (
                <li key={idx}>{s}</li>
              ))}
            </ul>
          </div>

          <div className="studio-panel" style={{ padding: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b', fontWeight: 600, marginBottom: '12px' }}>
              <AlertTriangle size={16} />
              <span>Target Focus Areas & Gaps</span>
            </div>
            <ul style={{ paddingLeft: '18px', fontSize: '0.85rem', color: 'var(--text-main)', lineHeight: 1.6 }}>
              {(report.summary_weaknesses || []).map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Role Competency Blueprint Profile Breakdown */}
      {report?.role_competency_profile && (
        <div className="studio-panel" style={{ padding: '20px', marginBottom: '28px', border: '1px solid rgba(99, 102, 241, 0.25)', background: 'rgba(99, 102, 241, 0.03)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-primary)', fontWeight: 700 }}>
              <Award size={18} />
              <span>Role Competency Profile ({report.role_competency_profile.provenance || report.role_competency_profile.role_name || 'Role Assessment'})</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', fontSize: '0.75rem' }}>
              <span className="badge badge-verified">
                {report.role_competency_profile.sufficient_evidence_count || 0} / {report.role_competency_profile.total_competencies || Object.keys(report.role_competency_profile.competency_records || {}).length} Sufficient Evidence
              </span>
              <span style={{ padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                Coverage: {Math.round(((report.role_competency_profile.overall_coverage_ratio ?? report.role_competency_profile.competency_coverage_ratio) || 0) * 100)}%
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {Object.values(report.role_competency_profile.competency_records || {}).map((rec: any, idx) => {
              const isSufficient = rec.coverage_status === 'SUFFICIENT_EVIDENCE';
              const isPartial = rec.coverage_status === 'PARTIALLY_ASSESSED';
              const name = rec.competency_name || rec.name || `Competency ${idx + 1}`;

              // Calculate average score safely from scores array or average_score property
              let avgScore: number | null = null;
              if (Array.isArray(rec.scores) && rec.scores.length > 0) {
                avgScore = rec.scores.reduce((a: number, b: number) => a + b, 0) / rec.scores.length;
              } else if (typeof rec.average_score === 'number') {
                avgScore = rec.average_score;
              }

              const statusText = rec.coverage_status ? String(rec.coverage_status).replace(/_/g, ' ') : 'UNASSESSED';
              const demonstrated = rec.demonstrated_concepts || rec.concepts_demonstrated || [];
              const missing = rec.missing_concepts || [];

              return (
                <div
                  key={rec.competency_id || idx}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '6px',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <strong style={{ fontSize: '0.875rem', color: '#fff' }}>{name}</strong>
                      {rec.importance && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                          [{rec.importance}]
                        </span>
                      )}
                    </div>
                    <span
                      style={{
                        fontSize: '0.725rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: 600,
                        background: isSufficient ? 'rgba(34, 197, 94, 0.15)' : isPartial ? 'rgba(245, 158, 11, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                        color: isSufficient ? '#4ade80' : isPartial ? '#fbbf24' : 'var(--text-muted)',
                      }}
                    >
                      {statusText} {avgScore !== null ? `• Avg: ${avgScore.toFixed(1)}/10` : ''}
                    </span>
                  </div>

                  {rec.description && (
                    <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)', margin: 0 }}>
                      {rec.description}
                    </p>
                  )}

                  {demonstrated.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: '#4ade80' }}>
                      Demonstrated: {demonstrated.join(', ')}
                    </div>
                  )}

                  {missing.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: '#f87171' }}>
                      Conceptual Gaps: {missing.join(', ')}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Actionable Transfer-Aware Coaching Opportunities */}
      {weaknesses.length > 0 && (
        <div className="studio-panel" style={{ padding: '20px', marginBottom: '28px', border: '1px solid var(--border-card, #2d3b52)', background: 'var(--surface-card, #162032)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-primary)', fontWeight: 700 }}>
              <Target size={18} />
              <span>Targeted AI Transfer Coaching Opportunities</span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {weaknesses.length} target {weaknesses.length === 1 ? 'skill' : 'skills'} identified from interview evaluation
            </span>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
            Our Transfer Engine detected specific conceptual gaps during your interview answers. You can bridge directly into the AI Coaching Studio to practice deliberate invariant reasoning, diagnostic feedback, and progressive transfer challenges.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {weaknesses.map((item) => (
              <div
                key={item.question_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  flexWrap: 'wrap',
                  gap: '12px',
                }}
              >
                <div style={{ flex: 1, minWidth: '240px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.9rem' }}>{item.topic}</span>
                    <span style={{ fontSize: '0.725rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>
                      Score: {typeof item.overall_score === 'number' ? item.overall_score.toFixed(1) : 'N/A'}/10
                    </span>
                  </div>
                  <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                    {(item.weaknesses || []).slice(0, 2).join(' • ') || 'Key conceptual invariant reinforcement recommended'}
                  </div>
                </div>

                {onNavigateToCoaching && (
                  <button
                    className="btn btn-primary"
                    style={{ padding: '8px 16px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                    onClick={() => onNavigateToCoaching({ interviewSessionId: session.id, questionId: item.question_id, skillId: item.skill_id })}
                  >
                    <Compass size={14} />
                    <span>Practice in AI Coaching</span>
                    <ArrowRight size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Next Steps Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', borderTop: '1px solid var(--border-color)', paddingTop: '22px' }}>
        <button className="btn btn-secondary" onClick={onRetake}>
          <RotateCcw size={16} />
          <span>Retake / Calibrate New Session</span>
        </button>

        <button
          className="btn btn-primary"
          style={{ padding: '10px 20px', fontSize: '0.95rem', fontWeight: 600 }}
          onClick={onNavigateToAnalytics}
        >
          <BarChart2 size={16} />
          <span>View Evidence & Research Analytics</span>
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
};
