import React, { useState, useEffect } from 'react';
import { Candidate } from '../../types';
import {
  CandidateResearchResult,
  ConditionComparison,
} from '../../types/research';
import { api } from '../../services/api';
import {
  FlaskConical,
  Award,
  Layers,
  TrendingUp,
  AlertCircle,
  Clock,
  Zap,
} from 'lucide-react';

interface ResearchDashboardProps {
  selectedCandidate: Candidate | null;
}

export const ResearchDashboard: React.FC<ResearchDashboardProps> = ({ selectedCandidate }) => {
  const [candidateResults, setCandidateResults] = useState<CandidateResearchResult[]>([]);
  const [comparison, setComparison] = useState<ConditionComparison | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadResearchData();
  }, [selectedCandidate?.id]);

  const loadResearchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [compData, candData] = await Promise.all([
        api.getResearchComparison().catch((err) => {
          console.warn('Failed to load cross-condition comparison:', err);
          return null;
        }),
        selectedCandidate
          ? api.getCandidateResearchMetrics(selectedCandidate.id).catch((err) => {
              console.warn('Failed to load candidate research metrics:', err);
              return [];
            })
          : Promise.resolve([]),
      ]);
      setComparison(compData);
      setCandidateResults(candData || []);
    } catch (err: any) {
      setError(err?.message || 'Error loading research analytics');
    } finally {
      setLoading(false);
    }
  };

  const activeResult = candidateResults.length > 0 ? candidateResults[0] : null;

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Research Objective Banner */}
      <div
        className="studio-panel"
        style={{
          border: '1px solid var(--border-card, #2d3b52)',
          background: 'var(--surface-card, #162032)',
          padding: '18px 24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '4px',
                background: 'rgba(37, 99, 235, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--brand-primary, #2563eb)',
              }}
            >
              <FlaskConical size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#fff' }}>
                Controlled Experiment & Transfer Research Framework
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                Empirical investigation of Targeted, Transfer-Aware AI Coaching vs. Baselines on Independent Interview Skill Development
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <span className="badge badge-info" style={{ fontSize: '0.7rem', padding: '4px 10px' }}>
              OBSERVED TELEMETRY
            </span>
            <span className="badge badge-verified" style={{ fontSize: '0.7rem', padding: '4px 10px' }}>
              DERIVED FORMULAS
            </span>
            <span className="badge badge-unsupported" style={{ fontSize: '0.7rem', padding: '4px 10px' }}>
              INSUFFICIENT DATA (LONGITUDINAL)
            </span>
            <span className="badge badge-probed" style={{ fontSize: '0.7rem', padding: '4px 10px' }}>
              NOT MEASURABLE (DIAGNOSIS ACCURACY)
            </span>
          </div>
        </div>
      </div>

      {loading && (
        <div className="empty-state-card">
          <p>Compiling research telemetry and calculating empirical metrics...</p>
        </div>
      )}

      {error && (
        <div className="empty-state-card" style={{ border: '1px solid #ef4444' }}>
          <AlertCircle size={32} color="#ef4444" />
          <p style={{ color: '#ef4444', marginTop: '8px' }}>{error}</p>
        </div>
      )}

      {!loading && (
        <>
          {/* Section 1: Candidate Specific Research Result (if candidate has experiment sessions) */}
          {activeResult ? (
            <div className="studio-panel">
              <div className="studio-panel-header" style={{ marginBottom: '16px' }}>
                <div className="studio-panel-title">
                  <Award size={18} color="#818cf8" />
                  <span>Participant Empirical Trajectory ({activeResult.skill})</span>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: 'rgba(99, 102, 241, 0.15)',
                      color: '#a5b4fc',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                    }}
                  >
                    Condition: {activeResult.condition}
                  </span>
                  <span
                    className={`claim-status-badge ${
                      activeResult.is_completed ? 'badge-verified' : 'badge-probed'
                    }`}
                  >
                    {activeResult.is_completed ? 'COMPLETED' : 'IN_PROGRESS'}
                  </span>
                </div>
              </div>

              {/* 10 Core Metrics Summary Grid */}
              <div className="grid-4" style={{ marginBottom: '20px' }}>
                {/* 1. Learning Gain */}
                <div className="stat-card stat-accent">
                  <div className="stat-label">1. NORMALIZED GAIN</div>
                  <div className="stat-value" style={{ margin: '4px 0', color: '#818cf8' }}>
                    {activeResult.learning_gain.normalized_gain !== null
                      ? `${(activeResult.learning_gain.normalized_gain * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }}>
                    Absolute Gain: {activeResult.learning_gain.absolute_gain !== null ? activeResult.learning_gain.absolute_gain.toFixed(2) : 'N/A'}
                  </span>
                </div>

                {/* 2. Transfer Performance */}
                <div className="stat-card stat-success">
                  <div className="stat-label">2. TRANSFER SCORE (L1–L5)</div>
                  <div className="stat-value" style={{ margin: '4px 0', color: 'var(--status-verified)' }}>
                    {activeResult.performance.transfer_mean !== null
                      ? `${(activeResult.performance.transfer_mean * 100).toFixed(0)}%`
                      : 'N/A'}
                  </div>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }}>
                    Delta vs Posttest: {activeResult.transfer.transfer_delta !== null ? activeResult.transfer.transfer_delta.toFixed(2) : 'N/A'}
                  </span>
                </div>

                {/* 3. Transfer Failure Rate */}
                <div className="stat-card stat-warning">
                  <div className="stat-label">3. TRANSFER FAILURE RATE</div>
                  <div className="stat-value" style={{ margin: '4px 0', color: 'var(--status-probed)' }}>
                    {activeResult.transfer.transfer_failure_rate !== null
                      ? `${(activeResult.transfer.transfer_failure_rate * 100).toFixed(1)}%`
                      : '0.0%'}
                  </div>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }}>
                    Failures / Transfer Attempts
                  </span>
                </div>

                {/* 9. L5 Independent Transfer Achievement */}
                <div className="stat-card">
                  <div className="stat-label">9. L5 INDEPENDENT TRANSFER</div>
                  <div
                    className="stat-value"
                    style={{
                      margin: '4px 0',
                      color: activeResult.transfer.l5_independent_transfer_achieved
                        ? 'var(--status-verified)'
                        : 'var(--status-unsupported)',
                      fontSize: '1.25rem',
                      fontWeight: 800,
                    }}
                  >
                    {activeResult.transfer.l5_independent_transfer_achieved ? 'ACHIEVED' : 'NOT ACHIEVED'}
                  </div>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }}>
                    Score &ge; 70%, 0 Hints, Indep Scaffold
                  </span>
                </div>
              </div>

              {/* Transfer Taxonomy (L0 to L5) Progression */}
              <div style={{ marginBottom: '24px' }}>
                <h4 style={{ fontSize: '0.85rem', color: '#fff', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Layers size={16} /> Canonical Transfer Taxonomy Performance Breakdown
                </h4>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '10px',
                  }}
                >
                  {[
                    { label: 'L0 Recall', score: activeResult.performance.pretest_mean, tag: 'Baseline' },
                    { label: 'L1 Direct Application', score: activeResult.performance.training_mean, tag: 'Direct' },
                    { label: 'L2 Near Transfer', score: activeResult.performance.near_transfer_mean, tag: 'Near' },
                    { label: 'L3 Far Transfer', score: activeResult.performance.far_transfer_mean, tag: 'Far' },
                    { label: 'L4 Ambiguous Transfer', score: activeResult.performance.ambiguous_transfer_mean, tag: 'Ambiguous' },
                    { label: 'L5 Independent Transfer', score: activeResult.performance.independent_transfer_mean, tag: 'Target' },
                  ].map((tier, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(15, 23, 42, 0.7)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '8px',
                        padding: '12px',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '4px' }}>
                        {tier.label}
                      </div>
                      <div
                        style={{
                          fontSize: '1.25rem',
                          fontWeight: 800,
                          fontFamily: 'var(--font-mono)',
                          color: tier.score !== null ? (tier.score >= 0.7 ? 'var(--status-verified)' : 'var(--status-probed)') : 'var(--text-dim)',
                        }}
                      >
                        {tier.score !== null ? `${Math.round(tier.score * 100)}%` : '—'}
                      </div>
                      <span
                        style={{
                          fontSize: '0.65rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: 'rgba(255, 255, 255, 0.05)',
                          color: 'var(--text-dim)',
                          marginTop: '6px',
                          display: 'inline-block',
                        }}
                      >
                        {tier.score !== null ? 'Observed' : 'Not Tested'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bottom Row: Scaffolding, Recovery & Retention */}
              <div className="grid-3">
                {/* Scaffold Reduction & Assistance */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h5 style={{ margin: '0 0 10px', fontSize: '0.8rem', color: '#818cf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <TrendingUp size={14} /> 7 & 8. Assistance & Scaffolding
                  </h5>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Mean Scaffold Level:</span>
                      <strong style={{ color: '#fff' }}>
                        {activeResult.assistance.mean_scaffold_level !== null ? activeResult.assistance.mean_scaffold_level.toFixed(1) : 'N/A'} / 3.0
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Scaffold Reduction:</span>
                      <strong style={{ color: 'var(--status-verified)' }}>
                        {activeResult.assistance.scaffold_reduction !== null ? `+${activeResult.assistance.scaffold_reduction}` : 'N/A'}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Total Hints Requested:</span>
                      <strong style={{ color: '#fff' }}>{activeResult.assistance.total_hints}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Independent Events:</span>
                      <strong style={{ color: 'var(--status-verified)' }}>{activeResult.assistance.independent_events}</strong>
                    </div>
                  </div>
                </div>

                {/* Failure Diagnosis & Recovery */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h5 style={{ margin: '0 0 10px', fontSize: '0.8rem', color: 'var(--status-verified)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Zap size={14} /> 4, 5 & 6. Recovery & Intervention
                  </h5>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Recovery Rate:</span>
                      <strong style={{ color: 'var(--status-verified)' }}>
                        {activeResult.recovery.retry_recovery_rate !== null
                          ? `${Math.round(activeResult.recovery.retry_recovery_rate * 100)}%`
                          : 'N/A (0 Retries)'}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Diagnosis-Associated Recovery:</span>
                      <strong style={{ color: '#818cf8' }}>
                        {activeResult.recovery.diagnosis_associated_recovery_rate !== undefined && activeResult.recovery.diagnosis_associated_recovery_rate !== null
                          ? `${Math.round(activeResult.recovery.diagnosis_associated_recovery_rate * 100)}%`
                          : activeResult.recovery.retry_recovery_rate !== null && activeResult.recovery.diagnosis_count > 0
                          ? `${Math.round(activeResult.recovery.retry_recovery_rate * 100)}%`
                          : activeResult.condition === 'CONDITION_C' ? 'No Diagnosed Retries' : 'N/A (Baseline)'}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Diagnosis Correctness:</span>
                      <span className="badge badge-probed" style={{ fontSize: '0.65rem' }}>
                        NOT MEASURABLE
                      </span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.3 }}>
                      * Telemetry lacks gold-standard expert labels. Successful retry reflects recovery/intervention efficacy, not proof of diagnostic correctness.
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Improvement After Intervention:</span>
                      <strong style={{ color: '#fff' }}>
                        {activeResult.recovery.mean_score_improvement_after_intervention !== null
                          ? `+${(activeResult.recovery.mean_score_improvement_after_intervention * 100).toFixed(0)}%`
                          : 'N/A'}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Targeted Interventions:</span>
                      <strong style={{ color: '#fff' }}>{activeResult.recovery.targeted_intervention_count}</strong>
                    </div>
                  </div>
                </div>

                {/* 10. Longitudinal Retention & Efficiency */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h5 style={{ margin: '0 0 10px', fontSize: '0.8rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Clock size={14} /> 10. Longitudinal Retention
                  </h5>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Retention Ratio:</span>
                      {activeResult.transfer.retention_ratio !== null ? (
                        <strong style={{ color: 'var(--status-verified)' }}>
                          {(activeResult.transfer.retention_ratio * 100).toFixed(1)}%
                        </strong>
                      ) : (
                        <span className="badge badge-unsupported" style={{ fontSize: '0.65rem' }}>
                          INSUFFICIENT DATA
                        </span>
                      )}
                    </div>
                    <p style={{ margin: 0, fontSize: '0.725rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                      Longitudinal retention requires delayed follow-up sessions across distinct time windows (&ge; 24h). Within-session preservation ratio is{' '}
                      <strong style={{ color: '#fff' }}>
                        {activeResult.transfer.transfer_preservation_ratio !== null
                          ? `${(activeResult.transfer.transfer_preservation_ratio * 100).toFixed(0)}%`
                          : 'N/A'}
                      </strong>
                      .
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state-card">
              <FlaskConical size={36} color="#818cf8" style={{ marginBottom: '10px' }} />
              <h4>No Active Experiment Session for Selected Candidate</h4>
              <p style={{ maxWidth: '520px', margin: '6px auto 0', fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                This candidate has not completed an experimental trial session yet. Launching a controlled experiment trial under Condition A, B, or C will populate raw observation telemetry and derived research metrics.
              </p>
            </div>
          )}

          {/* Section 2: Cross-Condition Comparative Analysis (Condition A vs Condition B vs Condition C) */}
          <div className="studio-panel">
            <div className="studio-panel-header" style={{ marginBottom: '16px' }}>
              <div className="studio-panel-title">
                <FlaskConical size={18} color="#818cf8" />
                <span>Controlled Experiment Cohort Comparison (Condition A vs B vs C)</span>
              </div>
              <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                DESCRIPTIVE COHORT BENCHMARK
              </span>
            </div>

            {comparison && comparison.metrics && comparison.metrics.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table className="research-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'left' }}>
                      <th style={{ padding: '10px 14px', color: 'var(--text-dim)', fontWeight: 600 }}>RESEARCH METRIC</th>
                      <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600 }}>
                        CONDITION A<br />
                        <span style={{ fontSize: '0.7rem', fontWeight: 400 }}>Generic Feedback (n={comparison.condition_summaries?.CONDITION_A?.session_count ?? 0})</span>
                      </th>
                      <th style={{ padding: '10px 14px', color: '#38bdf8', fontWeight: 600 }}>
                        CONDITION B<br />
                        <span style={{ fontSize: '0.7rem', fontWeight: 400 }}>Adaptive Difficulty (n={comparison.condition_summaries?.CONDITION_B?.session_count ?? 0})</span>
                      </th>
                      <th style={{ padding: '10px 14px', color: '#818cf8', fontWeight: 600 }}>
                        CONDITION C<br />
                        <span style={{ fontSize: '0.7rem', fontWeight: 400 }}>Transfer-Aware Coaching (n={comparison.condition_summaries?.CONDITION_C?.session_count ?? 0})</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.metrics.map((row, idx) => {
                      const formatStat = (stat?: { mean: number | null; sample_count: number }) => {
                        if (!stat || stat.sample_count === 0 || stat.mean === null) {
                          return <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>— (n=0)</span>;
                        }
                        return (
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                            {stat.mean.toFixed(2)}{' '}
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 400 }}>
                              (n={stat.sample_count})
                            </span>
                          </span>
                        );
                      };

                      return (
                        <tr
                          key={idx}
                          style={{
                            borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                            background: idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent',
                          }}
                        >
                          <td style={{ padding: '12px 14px', color: '#fff', fontWeight: 500, textTransform: 'capitalize' }}>
                            {row.metric_name.replace(/_/g, ' ')}
                            {['posttest_performance', 'transfer_performance', 'independent_transfer_performance'].includes(row.metric_name) && (
                              <span style={{ fontSize: '0.65rem', marginLeft: '6px', color: '#38bdf8' }}>[Observed]</span>
                            )}
                            {['absolute_gain', 'normalized_gain', 'retry_recovery_rate', 'hint_rate', 'scaffold_reduction'].includes(row.metric_name) && (
                              <span style={{ fontSize: '0.65rem', marginLeft: '6px', color: '#34d399' }}>[Derived]</span>
                            )}
                          </td>
                          <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                            {formatStat(row.condition_a)}
                          </td>
                          <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                            {formatStat(row.condition_b)}
                          </td>
                          <td style={{ padding: '12px 14px', color: '#a5b4fc', background: 'rgba(99, 102, 241, 0.03)' }}>
                            {formatStat(row.condition_c)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
                No cross-condition cohort data recorded yet.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
