import React, { useState, useEffect } from 'react';
import { Candidate, AnalyticsOverview, PerformanceTrendPoint, KnowledgeGapItem, CandidateClaim } from '../types';
import { api } from '../services/api';
import {
  BarChart2,
  TrendingUp,
  Target,
  BookOpen,
  Calendar,
  Cpu,
  ShieldCheck,
  Play,
  FlaskConical,
} from 'lucide-react';
import { ResearchDashboard } from '../components/analytics/ResearchDashboard';

interface AnalyticsPageProps {
  selectedCandidate: Candidate | null;
  onStartInterview: () => void;
}

export const AnalyticsPage: React.FC<AnalyticsPageProps> = ({
  selectedCandidate,
  onStartInterview,
}) => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trends, setTrends] = useState<PerformanceTrendPoint[]>([]);
  const [topicScores, setTopicScores] = useState<Record<string, number>>({});
  const [knowledgeGaps, setKnowledgeGaps] = useState<KnowledgeGapItem[]>([]);
  const [claims, setClaims] = useState<CandidateClaim[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'readiness' | 'research'>('readiness');

  useEffect(() => {
    // 1. Wipe previous candidate's analytics state immediately to prevent cross-candidate bleed
    setOverview(null);
    setTrends([]);
    setTopicScores({});
    setKnowledgeGaps([]);
    setClaims([]);

    if (selectedCandidate) {
      loadAnalytics(selectedCandidate.id);
    }
  }, [selectedCandidate?.id]);

  const loadAnalytics = async (candId: string) => {
    setLoading(true);
    try {
      const [ovData, histData, skillsData, claimData] = await Promise.all([
        api.getAnalyticsOverview(candId),
        api.getPerformanceHistory(candId),
        api.getSkillsAnalytics(candId),
        api.getCandidateClaims(candId),
      ]);
      setOverview(ovData);
      setTrends(histData.trends || []);
      setTopicScores(skillsData.topic_scores || {});
      setKnowledgeGaps(skillsData.knowledge_gaps || []);
      setClaims(claimData || []);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!selectedCandidate) {
    return (
      <div className="empty-state-card fade-in">
        <BarChart2 size={44} className="empty-state-icon" />
        <h3>No Candidate Selected</h3>
        <p>Please select a candidate profile from the navbar or profile page to view analytics.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="empty-state-card fade-in">
        <p>Synthesizing candidate evidence graph & readiness metrics...</p>
      </div>
    );
  }

  const verifiedClaims = claims.filter((c) => c.verification_status === 'VERIFIED');
  const verificationRatio = claims.length > 0 ? Math.round((verifiedClaims.length / claims.length) * 100) : 0;
  const hasInterviewData = Boolean(overview && (overview.completed_interviews > 0 || overview.total_interviews > 0));
  const hiringReadiness = hasInterviewData
    ? Math.round(((overview?.overall_average_score ?? 0) * 0.6) + (verificationRatio * 0.4))
    : null;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Candidate Evidence & Hiring Readiness Analytics</h2>
            <p className="page-subtitle">
              Multimodal Telemetry, Claim Verification Matrix & Longitudinal Trends for <strong style={{ color: '#fff' }}>{selectedCandidate.full_name}</strong>
            </p>
          </div>

          <button type="button" className="btn btn-primary" onClick={onStartInterview}>
            <Play size={14} /> Launch Interview Session
          </button>
        </div>
      </div>

      {/* Navigation Tabs between Evidence Readiness and Phase 4 Research Analytics */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
        <button
          type="button"
          className={`btn ${activeTab === 'readiness' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('readiness')}
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <BarChart2 size={15} />
          <span>Evidence & Hiring Readiness</span>
        </button>
        <button
          type="button"
          className={`btn ${activeTab === 'research' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('research')}
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <FlaskConical size={15} />
          <span>Research Analytics & Experiments</span>
        </button>
      </div>

      {activeTab === 'research' ? (
        <ResearchDashboard selectedCandidate={selectedCandidate} />
      ) : (
        <>
          {/* Top Telemetry KPI Cards */}
          <div className="grid-4" style={{ marginBottom: '20px' }}>
            <div className={`stat-card ${hiringReadiness !== null ? 'stat-success' : 'stat-neutral'}`}>
              <div className="stat-label">HIRING READINESS</div>
              <div className="stat-value" style={{ color: hiringReadiness !== null ? 'var(--status-verified)' : 'var(--text-muted)', margin: '4px 0' }}>
                {hiringReadiness !== null ? `${hiringReadiness}%` : 'Unassessed'}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                {hasInterviewData ? 'Bayesian Multimodal Index' : 'Requires Completed Interview'}
              </span>
            </div>

        <div className="stat-card stat-accent">
          <div className="stat-label">CLAIM VERIFICATION RATIO</div>
          <div className="stat-value" style={{ color: '#818cf8', margin: '4px 0' }}>
            {verificationRatio}%
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            {verifiedClaims.length} of {claims.length} Claims Verified
          </span>
        </div>

        <div className="stat-card">
          <div className="stat-label">TECHNICAL DEPTH AVG</div>
          <div className="stat-value" style={{ color: '#06b6d4', margin: '4px 0' }}>
            {overview?.technical_average_score || 0}
            <span style={{ fontSize: '1rem', color: 'var(--text-dim)' }}>/100</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>First-Principles Rigor</span>
        </div>

        <div className="stat-card stat-warning">
          <div className="stat-label">STAR BEHAVIORAL AVG</div>
          <div className="stat-value" style={{ color: 'var(--status-probed)', margin: '4px 0' }}>
            {overview?.behavioral_average_score || 0}
            <span style={{ fontSize: '1rem', color: 'var(--text-dim)' }}>/100</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            {overview?.completed_interviews || 0} Completed Sessions
          </span>
        </div>
      </div>

      {/* Grid: Topic Mastery Breakdown & Claims Verification Matrix */}
      <div className="grid-2" style={{ marginBottom: '20px' }}>
        {/* Topic Mastery */}
        <div className="studio-panel">
          <div className="studio-panel-header">
            <div className="studio-panel-title">
              <Cpu size={16} />
              <span>Demonstrated Domain Mastery</span>
            </div>
          </div>

          {Object.keys(topicScores).length === 0 ? (
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>No domain scores evaluated yet.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Object.entries(topicScores).map(([topic, score]) => (
                <div key={topic} className="candidate-item-row" style={{ display: 'block', cursor: 'default' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem' }}>{topic}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: score >= 75 ? 'var(--status-verified)' : 'var(--status-probed)' }}>
                      {score}%
                    </span>
                  </div>
                  <div className="progress-track" style={{ height: '6px' }}>
                    <div
                      className="progress-fill"
                      style={{
                        width: `${score}%`,
                        background: score >= 75 ? 'var(--status-verified)' : 'var(--status-probed)',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Claim Verification Matrix */}
        <div className="studio-panel">
          <div className="studio-panel-header">
            <div className="studio-panel-title">
              <ShieldCheck size={16} />
              <span>Claim Verification Matrix</span>
            </div>
            <span style={{ fontSize: '0.725rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
              CLAIMED VS VERIFIED
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
            {claims.length === 0 ? (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>No claims extracted from resume yet.</p>
            ) : (
              claims.map((c) => (
                <div
                  key={c.id}
                  className="candidate-item-row"
                  style={{ cursor: 'default' }}
                >
                  <div>
                    <strong style={{ color: '#fff', fontSize: '0.85rem' }}>{c.skill_name}</strong>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }}>
                      Confidence: {Math.round(c.confidence_score * 100)}%
                    </div>
                  </div>

                  <span className={`claim-status-badge badge-${c.verification_status.toLowerCase()}`}>
                    {c.verification_status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Grid: Longitudinal Session Trends + Cumulative Strengths */}
      <div className="grid-2" style={{ marginBottom: '20px' }}>
        {/* Performance Trends */}
        <div className="studio-panel">
          <div className="studio-panel-header">
            <div className="studio-panel-title">
              <TrendingUp size={16} />
              <span>Longitudinal Interview Sessions ({trends.length})</span>
            </div>
          </div>

          {trends.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
              No completed interview sessions logged yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {trends.map((t) => (
                <div
                  key={t.session_id}
                  className="candidate-item-row"
                  style={{ cursor: 'default' }}
                >
                  <div>
                    <strong style={{ color: '#fff', fontSize: '0.875rem' }}>{t.target_role}</strong>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-dim)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Calendar size={12} /> {new Date(t.date).toLocaleDateString()} • {t.interview_type}
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--status-verified)', fontFamily: 'var(--font-mono)' }}>
                      {t.overall_score}
                    </div>
                    <div style={{ fontSize: '0.675rem', color: 'var(--text-dim)' }}>Tech: {t.technical_score}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Strengths & Focus Areas */}
        <div className="studio-panel">
          <div className="studio-panel-header">
            <div className="studio-panel-title">
              <Target size={16} />
              <span>Cumulative Profile Strengths & Gaps</span>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <span style={{ fontSize: '0.725rem', color: 'var(--status-verified)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
              Demonstrated Strengths
            </span>
            <ul style={{ paddingLeft: '18px', fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '6px' }}>
              {(overview?.top_strengths || ['Strong conceptual grasp of software design']).map((s, i) => (
                <li key={i} style={{ marginBottom: '4px' }}>{s}</li>
              ))}
            </ul>
          </div>

          <div>
            <span style={{ fontSize: '0.725rem', color: 'var(--status-probed)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
              Priority Remediation Focus
            </span>
            <ul style={{ paddingLeft: '18px', fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '6px' }}>
              {(overview?.common_weaknesses || ['Deepen architectural edge-case explanations']).map((w, i) => (
                <li key={i} style={{ marginBottom: '4px' }}>{w}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Knowledge Gaps & Remediation Tracker */}
      <div className="studio-panel">
        <div className="studio-panel-header">
          <div className="studio-panel-title">
            <BookOpen size={16} />
            <span>Missing Concepts & Actionable Remediation Roadmap</span>
          </div>
        </div>

        {knowledgeGaps.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            No knowledge gaps detected yet. Complete practice sessions to discover targeted learning items.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {knowledgeGaps.map((kg, i) => (
              <div key={i} className="candidate-item-row" style={{ cursor: 'default' }}>
                <div>
                  <strong style={{ color: '#f87171', fontSize: '0.875rem' }}>{kg.concept}</strong>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)', marginLeft: '10px' }}>Topic: {kg.topic}</span>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>{kg.recommendation}</p>
                </div>
                <span className="claim-status-badge badge-probed">{kg.occurrences}x Missed</span>
              </div>
            ))}
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
};

