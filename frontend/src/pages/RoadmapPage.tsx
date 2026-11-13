import React, { useState, useEffect } from 'react';
import { Candidate } from '../types';
import {
  SkillGapAnalysisResult,
  PersonalizedRoadmapDTO,
  RoadmapItemDTO,
  SkillGapPriority,
} from '../types/roadmap';
import { api } from '../services/api';
import { useAppSession, useSafeNavigate } from '../context/AppSessionContext';
import {
  Map,
  Target,
  ShieldCheck,
  ArrowRight,
  Play,
  RefreshCw,
  CheckCircle,
  Layers,
  ChevronRight,
  Code,
  Clock,
  Flag,
} from 'lucide-react';

interface RoadmapPageProps {
  selectedCandidate: Candidate | null;
  onNavigateToCoaching?: (context?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
    coachingSessionId?: string;
  }) => void;
}

const SENIORITY_TIERS = ['Junior', 'Mid', 'Senior', 'Staff', 'Lead', 'Principal'];

export const RoadmapPage: React.FC<RoadmapPageProps> = ({
  selectedCandidate,
  onNavigateToCoaching,
}) => {
  const navigate = useSafeNavigate();
  const { activeRoleId, setRoadmapId, setCoachingSessionId } = useAppSession();

  const designatedRole = selectedCandidate?.target_role || activeRoleId || 'Backend Systems Engineer';
  const [targetRole, setTargetRole] = useState(designatedRole);
  const [roleOptions, setRoleOptions] = useState<string[]>([
    'Frontend Developer',
    'Backend Systems Engineer',
    'Machine Learning Engineer',
    'Embedded Systems Engineer',
    'Cloud DevOps / SRE',
    'AI & Data Science Engineer',
    'Full-Stack Software Engineer',
    'Distributed Systems Engineer',
    'Software Engineer',
  ]);
  const [seniority, setSeniority] = useState('Senior');
  const [gapAnalysis, setGapAnalysis] = useState<SkillGapAnalysisResult | null>(null);
  const [roadmap, setRoadmap] = useState<PersonalizedRoadmapDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'roadmap' | 'gaps'>('roadmap');
  const [error, setError] = useState<string | null>(null);

  // Sync with candidate target_role or activeRoleId
  useEffect(() => {
    const role = selectedCandidate?.target_role || activeRoleId;
    if (role && role !== targetRole) {
      setTargetRole(role);
      setRoleOptions((prev) => (prev.includes(role) ? prev : [role, ...prev]));
    }
  }, [selectedCandidate?.target_role, activeRoleId]);

  useEffect(() => {
    if (typeof api.listTargetRoles === 'function') {
      api
        .listTargetRoles()
        .then((data) => {
          if (data && data.length > 0) {
            const names = data.map((d) => d.display_name);
            setRoleOptions((prev) => {
              const combined = Array.from(new Set([...names, ...prev]));
              if (activeRoleId && !combined.includes(activeRoleId)) {
                combined.unshift(activeRoleId);
              }
              return combined;
            });
          }
        })
        .catch(() => {});
    }
  }, [activeRoleId]);

  const hasResume = Boolean(
    selectedCandidate && selectedCandidate.resumes && selectedCandidate.resumes.length > 0
  );
  const isResumeProcessed = Boolean(
    hasResume && selectedCandidate?.resumes?.some((r) => r.processing_status === 'COMPLETED')
  );

  // Fetch or calculate gaps and roadmap
  const loadData = async () => {
    if (!selectedCandidate) return;
    if (!hasResume || !isResumeProcessed) {
      setRoadmap(null);
      setGapAnalysis(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch active roadmap if exists
      const currentRole = selectedCandidate.target_role || activeRoleId || targetRole;
      let activeRoadmap: PersonalizedRoadmapDTO | null = null;
      try {
        const candidateRoadmap = await api.getCandidateRoadmap(selectedCandidate.id);
        if (candidateRoadmap && candidateRoadmap.items && candidateRoadmap.items.length > 0) {
          // Only reuse existing roadmap if it corresponds to candidate's active target role
          if (!currentRole || candidateRoadmap.target_role.toLowerCase() === currentRole.toLowerCase()) {
            activeRoadmap = candidateRoadmap;
            setRoadmap(activeRoadmap);
            setRoadmapId(activeRoadmap.id);
            setTargetRole(activeRoadmap.target_role);
            setSeniority(activeRoadmap.seniority || 'Mid');
          }
        }
      } catch {
        // No active roadmap yet
      }

      const roleForGaps = activeRoadmap ? activeRoadmap.target_role : currentRole;
      setTargetRole(roleForGaps);

      // 2. Fetch skill gap analysis
      const gaps = await api.getSkillGaps(
        selectedCandidate.id,
        roleForGaps,
        activeRoadmap ? activeRoadmap.seniority : seniority
      );
      setGapAnalysis(gaps);

      // If roadmap didn't exist yet or had 0 items for this role, generate one
      if (!activeRoadmap || !activeRoadmap.items || activeRoadmap.items.length === 0) {
        const generated = await api.generateRoadmap(selectedCandidate.id, roleForGaps, seniority);
        setRoadmap(generated);
        setRoadmapId(generated.id);
      }
    } catch (err: any) {
      if (err.message?.includes('PREREQUISITE_MISSING') || err.message?.includes('Candidate evidence required')) {
        setRoadmap(null);
        setGapAnalysis(null);
      } else {
        setError(err.message || 'Failed to load skill gap and roadmap intelligence.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedCandidate?.id, hasResume, isResumeProcessed]);

  const handleGenerateNewRole = async () => {
    if (!selectedCandidate) return;
    setLoading(true);
    setError(null);
    try {
      if (typeof api.updateCandidate === 'function') {
        await api.updateCandidate(selectedCandidate.id, { target_role: targetRole }).catch(() => {});
      }
      const gaps = await api.getSkillGaps(selectedCandidate.id, targetRole, seniority);
      setGapAnalysis(gaps);
      const generated = await api.generateRoadmap(selectedCandidate.id, targetRole, seniority);
      setRoadmap(generated);
      setRoadmapId(generated.id);
    } catch (err: any) {
      setError(err.message || 'Failed to re-generate roadmap.');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncProgress = async () => {
    if (!selectedCandidate) return;
    setActionLoading('sync');
    setError(null);
    try {
      const synced = await api.syncRoadmapProgress(selectedCandidate.id);
      setRoadmap(synced);
      setRoadmapId(synced.id);
      const gaps = await api.getSkillGaps(selectedCandidate.id, targetRole, seniority);
      setGapAnalysis(gaps);
    } catch (err: any) {
      setError(err.message || 'Failed to sync roadmap progress.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleLaunchCoaching = async (item: RoadmapItemDTO) => {
    if (!selectedCandidate) return;
    setActionLoading(item.id);
    try {
      const res = await api.startCoachingFromRoadmapItem(item.id, selectedCandidate.id);
      setCoachingSessionId(res.coaching_session_id);
      if (onNavigateToCoaching) {
        onNavigateToCoaching({
          coachingSessionId: res.coaching_session_id,
          skillId: res.skill_id,
        });
      } else {
        navigate(`/coaching/${res.coaching_session_id}`);
      }
    } catch (err: any) {
      alert(`Could not launch coaching session: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const getPriorityBadgeClass = (priority: SkillGapPriority) => {
    switch (priority) {
      case 'CRITICAL':
        return 'badge-critical';
      case 'HIGH':
        return 'badge-high';
      case 'MEDIUM':
        return 'badge-medium';
      case 'LOW':
        return 'badge-low';
      case 'SATISFIED':
        return 'badge-satisfied';
      default:
        return 'badge-neutral';
    }
  };

  const getProficiencyBadge = (state?: string) => {
    switch (state) {
      case 'DEMONSTRATED_WEAKNESS':
        return {
          label: 'Demonstrated Weakness',
          bg: 'rgba(239, 68, 68, 0.15)',
          color: '#f87171',
          border: 'rgba(239, 68, 68, 0.35)',
        };
      case 'PARTIALLY_DEMONSTRATED':
        return {
          label: 'Partially Demonstrated',
          bg: 'rgba(245, 158, 11, 0.15)',
          color: '#fbbf24',
          border: 'rgba(245, 158, 11, 0.35)',
        };
      case 'DEMONSTRATED_COMPETENCY':
        return {
          label: 'Demonstrated Competency',
          bg: 'rgba(16, 185, 129, 0.15)',
          color: '#34d399',
          border: 'rgba(16, 185, 129, 0.35)',
        };
      case 'NO_EVIDENCE':
        return {
          label: 'No Evidence',
          bg: 'rgba(148, 163, 184, 0.12)',
          color: '#94a3b8',
          border: 'rgba(148, 163, 184, 0.25)',
        };
      case 'NOT_ASSESSED':
      default:
        return {
          label: 'Pending Assessment',
          bg: 'rgba(56, 189, 248, 0.15)',
          color: '#38bdf8',
          border: 'rgba(56, 189, 248, 0.35)',
        };
    }
  };

  const getEvidenceTier = (item: RoadmapItemDTO) => {
    if (item.status === 'COMPLETED' || item.current_transfer_level === 'L5_INDEPENDENT_TRANSFER') {
      return {
        tier: 5,
        title: 'Tier 5: L5 Independent Transfer',
        scaffold: 'INDEPENDENT',
        color: '#34d399',
        bg: 'rgba(16, 185, 129, 0.15)',
        border: 'rgba(16, 185, 129, 0.3)',
        summary: 'Demonstrated unassisted on novel context',
      };
    }
    if (
      item.current_transfer_level === 'L3_DEEP_ANALOGY' ||
      item.current_transfer_level === 'L4_CROSS_DOMAIN' ||
      (item.assistance_dependency < 0.4 && item.status !== 'NOT_STARTED')
    ) {
      return {
        tier: 4,
        title: 'Tier 4: Reduced Assistance',
        scaffold: 'LOW',
        color: '#38bdf8',
        bg: 'rgba(56, 189, 248, 0.15)',
        border: 'rgba(56, 189, 248, 0.3)',
        summary: 'Solved with minimal Socratic scaffolding',
      };
    }
    if (
      item.current_transfer_level === 'L2_NEAR_DOMAIN' ||
      (item.assistance_dependency < 0.7 && item.status !== 'NOT_STARTED')
    ) {
      return {
        tier: 3,
        title: 'Tier 3: Demonstrated with Assistance',
        scaffold: 'MEDIUM',
        color: '#fbbf24',
        bg: 'rgba(245, 158, 11, 0.15)',
        border: 'rgba(245, 158, 11, 0.3)',
        summary: 'Solved with guided prompts & hints',
      };
    }
    if (item.status === 'IN_PROGRESS' || item.status === 'PRACTICING') {
      return {
        tier: 2,
        title: 'Tier 2: Currently Developing',
        scaffold: 'HIGH',
        color: '#a5b4fc',
        bg: 'rgba(99, 102, 241, 0.15)',
        border: 'rgba(99, 102, 241, 0.3)',
        summary: 'Active coaching in progress; schema induction',
      };
    }
    return {
      tier: 1,
      title: 'Tier 1: Assessed, Needs Practice',
      scaffold: 'HIGH',
      color: '#f87171',
      bg: 'rgba(239, 68, 68, 0.15)',
      border: 'rgba(239, 68, 68, 0.3)',
      summary: 'Assessed in interview, unpractised in studio',
    };
  };

  if (!selectedCandidate) {
    return (
      <div className="empty-state-card">
        <Target size={48} className="empty-state-icon" />
        <h3>No Candidate Selected</h3>
        <p>Select a candidate from the top bar to inspect role-aware skill gaps and personalized roadmap.</p>
      </div>
    );
  }

  if (!hasResume) {
    return (
      <div className="roadmap-container" data-testid="roadmap-no-resume-state">
        <div className="surface-card p-8 text-center max-w-2xl mx-auto my-8 border-subtle">
          <div className="icon-badge mx-auto mb-4" style={{ width: '48px', height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <Map size={24} className="text-indigo" />
          </div>
          <h2 className="text-xl font-bold text-primary mb-2">Resume Evidence Required for Personalized Roadmap</h2>
          <p className="text-sm text-secondary mb-6 leading-relaxed">
            Personalized learning paths, milestone recommendations, and role gap analyses require verified candidate evidence.
            Upload your resume so the AI Coach can extract your technical claims, or browse standard industry role blueprints in the role catalog.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigate('/resume')}
            >
              Upload Resume to Enable Roadmap
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/roles')}
            >
              Explore Role Catalog (Generic)
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!isResumeProcessed) {
    return (
      <div className="roadmap-container" data-testid="roadmap-processing-state">
        <div className="surface-card p-8 text-center max-w-2xl mx-auto my-8 border-subtle">
          <RefreshCw size={32} className="animate-spin text-indigo mx-auto mb-4" />
          <h2 className="text-xl font-bold text-primary mb-2">Resume Parsing in Progress</h2>
          <p className="text-sm text-secondary mb-6 leading-relaxed">
            Your resume has been uploaded and is being analyzed. Extracted skills, background evidence, and personalized learning milestones will appear once parsing completes.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate('/resume')}
          >
            View Parsing Status
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="roadmap-container">
      {/* Role Targeting Bar */}
      <div className="card role-selector-card">
        <div className="role-selector-header">
          <div className="role-title-group">
            <div className="icon-badge">
              <Map size={20} />
            </div>
            <div>
              <h2 className="section-title">My Skill Growth & Roadmap</h2>
              <p className="section-subtitle">
                Track your evaluated competence and progress toward unassisted L5 Independent Transfer.
              </p>
            </div>
          </div>

          <div className="role-controls-row">
            <div className="control-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>Target Role</span>
                {selectedCandidate?.target_role === targetRole && (
                  <span className="badge badge-brand" style={{ fontSize: '0.65rem', padding: '1px 5px' }}>Profile Anchored</span>
                )}
              </label>
              <select
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                className="select-input"
              >
                {roleOptions.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div className="control-group">
              <label>Seniority Tier</label>
              <select
                value={seniority}
                onChange={(e) => setSeniority(e.target.value)}
                className="select-input"
              >
                {SENIORITY_TIERS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleGenerateNewRole}
              disabled={loading}
              className="btn btn-primary"
            >
              <RefreshCw size={15} className={loading ? 'spin' : ''} />
              <span>Target & Generate</span>
            </button>
          </div>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}

        {/* High-level Empirical Stats */}
        {gapAnalysis && (
          <>
            <div className="stats-metric-grid">
              <div className="stat-card">
                <div className="stat-value">{gapAnalysis.total_role_competencies || gapAnalysis.total_competencies_evaluated}</div>
                <div className="stat-label">Total Role Competencies</div>
              </div>
              <div className="stat-card stat-accent">
                <div className="stat-value">{gapAnalysis.assessed_competencies_count ?? gapAnalysis.gaps.filter(g => g.is_measured_proficiency).length}</div>
                <div className="stat-label">Assessed With Evidence</div>
              </div>
              <div className="stat-card stat-warning">
                <div className="stat-value">{gapAnalysis.gaps_detected}</div>
                <div className="stat-label">Identified Skill Gaps</div>
              </div>
              <div className="stat-card stat-success">
                <div className="stat-value">{roadmap?.items?.length || 0}</div>
                <div className="stat-label">Roadmap Milestones</div>
              </div>
            </div>

            {/* Excluded & Satisfied Competencies Explanation Panel */}
            {((gapAnalysis.excluded_competencies && gapAnalysis.excluded_competencies.length > 0) || (roadmap?.excluded_competencies && roadmap.excluded_competencies.length > 0)) && (
              <div style={{ marginTop: '12px', padding: '10px 14px', background: 'rgba(15, 23, 42, 0.45)', border: '1px solid rgba(148, 163, 184, 0.2)', borderRadius: '8px', fontSize: '0.8rem' }}>
                <span style={{ fontWeight: 600, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <ShieldCheck size={14} style={{ color: '#4ade80' }} />
                  Satisfied or Excluded Role Competencies (Not generated as active gaps):
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {(gapAnalysis.excluded_competencies || roadmap?.excluded_competencies || []).map((exc, eIdx) => (
                    <div key={eIdx} style={{ color: '#cbd5e1', fontSize: '0.76rem' }}>
                      &bull; <strong style={{ color: '#e2e8f0' }}>{exc.skill_name}:</strong> {exc.reason}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* View Switcher Tabs */}
        <div className="tab-pill-bar">
          <button
            className={`tab-pill ${activeTab === 'roadmap' ? 'active' : ''}`}
            onClick={() => setActiveTab('roadmap')}
          >
            <Layers size={15} />
            <span>Personalized Roadmap ({roadmap?.items.length || 0} Milestones)</span>
          </button>
          <button
            className={`tab-pill ${activeTab === 'gaps' ? 'active' : ''}`}
            onClick={() => setActiveTab('gaps')}
          >
            <ShieldCheck size={15} />
            <span>Role Gap Diagnosis ({gapAnalysis?.gaps.length || 0})</span>
          </button>
          <div className="tab-pill-actions">
            <button
              onClick={handleSyncProgress}
              disabled={actionLoading === 'sync'}
              className="btn btn-secondary btn-sm"
              title="Sync milestone completion against recent coaching and transfer results"
            >
              <RefreshCw size={13} className={actionLoading === 'sync' ? 'spin' : ''} />
              <span>Sync Progress</span>
            </button>
          </div>
        </div>
      </div>

      {/* TAB 1: ROADMAP MILESTONES */}
      {activeTab === 'roadmap' && roadmap && (
        <div className="roadmap-milestones-section">
          {/* Progress Overview Bar with Authoritative Role Metadata Banner */}
          <div className="card progress-overview-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span className="badge badge-brand" style={{ fontSize: '0.8rem', padding: '3px 10px', fontWeight: 600 }}>
                  Target Role: {roadmap.target_role}
                </span>
                <span className="badge badge-neutral" style={{ fontSize: '0.8rem', padding: '3px 10px' }}>
                  Seniority: {roadmap.seniority}
                </span>
                <span className="badge badge-success" style={{ fontSize: '0.8rem', padding: '3px 10px' }}>
                  Status: {roadmap.status}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                Roadmap Updated: {roadmap.updated_at ? new Date(roadmap.updated_at).toLocaleDateString() : 'Active'}
              </div>
            </div>

            <div className="progress-header">
              <span className="progress-title">
                Roadmap Completion: {roadmap.completed_items} of {roadmap.total_items} milestones achieved
              </span>
              <span className="progress-percent">{roadmap.overall_progress.toFixed(1)}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${Math.max(5, roadmap.overall_progress)}%` }}
              />
            </div>
          </div>

          {/* Evidence-Based Competency Progression Tiers */}
          <div
            className="surface-card mb-6 p-5"
          >
            <div className="flex items-center justify-between gap-3 mb-2">
              <span className="font-bold text-sm text-primary">Evidence-Based Competency Progression Tiers</span>
              <span className="text-2xs text-muted">Evaluated on real assessment & transfer challenge performance</span>
            </div>
            <p className="text-xs text-secondary mb-4 leading-relaxed">
              Competence is evaluated strictly on unassisted transfer performance. Reading explanations, completing lessons, or receiving AI responses does not count as independent mastery.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { tier: 1, label: '1. Assessed (Needs Practice)', scaffold: 'HIGH', isL5: false },
                { tier: 2, label: '2. Currently Developing', scaffold: 'HIGH', isL5: false },
                { tier: 3, label: '3. Assisted Performance', scaffold: 'MED', isL5: false },
                { tier: 4, label: '4. Reduced Assistance', scaffold: 'LOW', isL5: false },
                { tier: 5, label: '5. L5 Independent Transfer', scaffold: 'NONE', isL5: true },
              ].map((t) => {
                const count = roadmap.items.filter((it) => getEvidenceTier(it).tier === t.tier).length;
                return (
                  <div
                    key={t.tier}
                    className="p-3 rounded-md border text-center"
                    style={{
                      background: t.isL5 ? 'rgba(5, 150, 105, 0.12)' : 'var(--surface-raised, #1e293b)',
                      borderColor: t.isL5 ? 'rgba(5, 150, 105, 0.3)' : 'var(--border-card, #2d3b52)',
                    }}
                  >
                    <div
                      className="text-xl font-bold"
                      style={{ color: t.isL5 ? '#6ee7b7' : 'var(--text-primary, #f8fafc)' }}
                    >
                      {count}
                    </div>
                    <div className="text-xs font-semibold text-primary truncate mt-0.5" title={t.label}>{t.label}</div>
                    <div className="text-2xs text-muted mt-1">Scaffold: {t.scaffold}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Milestone Items List */}
          <div className="milestones-flow">
            {roadmap.items.map((item) => {
              const isCompleted = item.status === 'COMPLETED';
              const isInProgress = item.status === 'IN_PROGRESS' || item.status === 'PRACTICING';
              const tierInfo = getEvidenceTier(item);
              const profBadge = getProficiencyBadge(item.proficiency_state);

              return (
                <div
                  key={item.id}
                  className={`card milestone-card ${isCompleted ? 'milestone-completed' : ''} ${
                    isInProgress ? 'milestone-in-progress' : ''
                  }`}
                >
                  <div className="milestone-header">
                    <div className="milestone-number-badge">
                      {isCompleted ? <CheckCircle size={16} /> : `#${item.sequence_order}`}
                    </div>

                    <div className="milestone-title-area">
                      <div className="milestone-tag-row">
                        <span
                          style={{
                            background: profBadge.bg,
                            color: profBadge.color,
                            border: `1px solid ${profBadge.border}`,
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: '4px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: profBadge.color }} />
                          {profBadge.label}
                        </span>
                        <span className={`priority-badge ${getPriorityBadgeClass(item.priority)}`}>
                          {item.priority}
                        </span>
                        <span className="importance-badge">{item.role_importance}</span>
                        <span className={`status-badge status-${item.status.toLowerCase()}`}>
                          {item.status.replace('_', ' ')}
                        </span>
                        {item.difficulty_level && (
                          <span
                            style={{
                              background: 'rgba(148, 163, 184, 0.1)',
                              color: '#94a3b8',
                              border: '1px solid rgba(148, 163, 184, 0.25)',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              padding: '2px 8px',
                              borderRadius: '4px',
                            }}
                          >
                            {item.difficulty_level}
                          </span>
                        )}
                        {item.estimated_duration && (
                          <span
                            style={{
                              background: 'rgba(148, 163, 184, 0.1)',
                              color: '#94a3b8',
                              border: '1px solid rgba(148, 163, 184, 0.25)',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Clock size={11} /> {item.estimated_duration}
                          </span>
                        )}
                        {item.is_flagged_for_review && (
                          <span
                            style={{
                              background: 'rgba(234, 179, 8, 0.15)',
                              color: '#facc15',
                              border: '1px solid rgba(234, 179, 8, 0.3)',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Flag size={11} /> Review Flagged
                          </span>
                        )}
                        <span
                          style={{
                            background: tierInfo.bg,
                            color: tierInfo.color,
                            border: `1px solid ${tierInfo.border}`,
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: '4px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: tierInfo.color }} />
                          {item.progression_tier || tierInfo.title} &bull; Scaffold: {tierInfo.scaffold}
                        </span>
                      </div>
                      <h3 className="milestone-skill-title">{item.skill_title}</h3>
                      {item.prerequisite_milestone_ids && item.prerequisite_milestone_ids.length > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600 }}>Prerequisites:</span>
                          {item.prerequisite_milestone_ids.map((pId, pIdx) => (
                            <span
                              key={pIdx}
                              style={{
                                fontSize: '0.7rem',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                background: 'rgba(99, 102, 241, 0.12)',
                                color: '#a5b4fc',
                                border: '1px solid rgba(99, 102, 241, 0.25)',
                              }}
                            >
                              {pId.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="milestone-action-area">
                      {isCompleted ? (
                        <div className="completion-badge">
                          <CheckCircle size={15} />
                          <span>L5 Transfer Verified</span>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleLaunchCoaching(item)}
                          disabled={actionLoading === item.id}
                          className="btn btn-coaching-launch"
                        >
                          <Play size={14} />
                          <span>{isInProgress ? 'Resume Coaching' : 'Practice in AI Coaching'}</span>
                          <ArrowRight size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Objective & Pedagogical Invariants */}
                  <div className="milestone-body">
                    <div className="milestone-objective-block">
                      <span className="label-bold">Target Objective:</span>
                      <p className="objective-text">{item.learning_objective}</p>
                    </div>

                    {item.core_invariants && item.core_invariants.length > 0 && (
                      <div className="invariants-row">
                        <span className="label-dim">Core Invariants:</span>
                        <div className="invariants-pills">
                          {item.core_invariants.map((inv, i) => (
                            <span key={i} className="invariant-pill">
                              {inv}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Metrics Comparison */}
                    <div className="metric-comparison-row">
                      <div className="metric-chip">
                        <span className="metric-chip-label">
                          {item.is_measured_proficiency ? 'Measured Mastery:' : 'Estimated Prior:'}
                        </span>
                        <span className="metric-chip-val">
                          {item.is_measured_proficiency
                            ? `${(item.current_mastery * 100).toFixed(0)}% / Target ${(item.target_mastery * 100).toFixed(0)}%`
                            : `~${(item.current_mastery * 100).toFixed(0)}% (Unassessed) • Target ${(item.target_mastery * 100).toFixed(0)}%`}
                        </span>
                      </div>
                      <div className="metric-chip">
                        <span className="metric-chip-label">Transfer Distance:</span>
                        <span className="metric-chip-val">{item.current_transfer_level.replace(/_/g, ' ')} &rarr; L5 Independent</span>
                      </div>
                      <div className="metric-chip">
                        <span className="metric-chip-label">Assistance Dependency:</span>
                        <span className="metric-chip-val">{(item.assistance_dependency * 100).toFixed(0)}%</span>
                      </div>
                    </div>

                    {/* Rationale & Action Steps */}
                    <div className="rationale-box">
                      <p className="rationale-text">{item.rationale}</p>
                    </div>

                    {item.actionable_steps && item.actionable_steps.length > 0 && (
                      <ul className="action-steps-list">
                        {item.actionable_steps.map((step, sIdx) => (
                          <li key={sIdx} className="action-step-item">
                            <ChevronRight size={13} className="bullet-icon" />
                            <span>{step}</span>
                          </li>
                        ))}
                      </ul>
                    )}

                    {/* Actionable Implementation Task */}
                    {item.implementation_task && item.implementation_task.title && (
                      <div style={{ marginTop: '14px', padding: '12px 14px', background: 'rgba(15, 23, 42, 0.65)', border: '1px solid rgba(148, 163, 184, 0.18)', borderRadius: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                          <Code size={14} style={{ color: '#38bdf8' }} />
                          <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f1f5f9' }}>
                            {item.implementation_task.title}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0 0 8px 0', lineHeight: 1.45 }}>
                          {item.implementation_task.description}
                        </p>
                        {item.implementation_task.technology_stack && item.implementation_task.technology_stack.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                            {item.implementation_task.technology_stack.map((t, idx) => (
                              <span key={idx} style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                        {item.implementation_task.acceptance_criteria && item.implementation_task.acceptance_criteria.length > 0 && (
                          <div style={{ marginTop: '6px' }}>
                            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#cbd5e1' }}>Acceptance Criteria:</span>
                            <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', fontSize: '0.75rem', color: '#94a3b8' }}>
                              {item.implementation_task.acceptance_criteria.map((crit, cIdx) => (
                                <li key={cIdx}>{crit}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Expected Deliverables & Required Advancement Evidence */}
                    {item.expected_deliverables && item.expected_deliverables.length > 0 && (
                      <div style={{ marginTop: '10px', fontSize: '0.78rem', color: '#94a3b8' }}>
                        <span style={{ fontWeight: 600, color: '#e2e8f0' }}>Expected Deliverables: </span>
                        {item.expected_deliverables.join(' • ')}
                      </div>
                    )}

                    {item.evidence_required && (
                      <div style={{ marginTop: '10px', padding: '8px 12px', background: 'rgba(56, 189, 248, 0.08)', borderLeft: '3px solid #38bdf8', borderRadius: '0 6px 6px 0', fontSize: '0.75rem', color: '#cbd5e1' }}>
                        <span style={{ fontWeight: 600, color: '#38bdf8' }}>Advancement Evidence Required: </span>
                        {item.evidence_required}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'roadmap' && !roadmap && !loading && (
        <div className="surface-card p-8 text-center text-secondary border-subtle">
          <Layers size={32} className="mx-auto mb-3 text-muted" />
          <h3 className="text-base font-bold text-primary mb-1">No Personalized Roadmap Generated Yet</h3>
          <p className="text-xs text-muted mb-4 max-w-md mx-auto">
            Click &ldquo;Target &amp; Generate&rdquo; above to synthesize an evidence-grounded milestone plan for {targetRole}.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleGenerateNewRole}
          >
            Generate Personalized Roadmap
          </button>
        </div>
      )}

      {/* TAB 2: DETAILED SKILL GAP DIAGNOSIS */}
      {activeTab === 'gaps' && gapAnalysis && (
        <div className="gaps-list-section">
          <div className="card-grid">
            {gapAnalysis.gaps.map((gap) => (
              <div key={gap.skill_id} className="card gap-detail-card">
                <div className="gap-card-header">
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span
                        style={{
                          background: getProficiencyBadge(gap.proficiency_state).bg,
                          color: getProficiencyBadge(gap.proficiency_state).color,
                          border: `1px solid ${getProficiencyBadge(gap.proficiency_state).border}`,
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: getProficiencyBadge(gap.proficiency_state).color }} />
                        {getProficiencyBadge(gap.proficiency_state).label}
                      </span>
                      <span className={`priority-badge ${getPriorityBadgeClass(gap.priority)}`}>
                        {gap.priority} PRIORITY
                      </span>
                    </div>
                    <h4 className="gap-skill-name">{gap.skill_name}</h4>
                  </div>
                  <div className="priority-score-badge">
                    <span className="score-val">{gap.priority_score.toFixed(2)}</span>
                    <span className="score-lbl">Priority Score</span>
                  </div>
                </div>

                <div className="gap-metrics-bar">
                  <div className="gap-metric">
                    <span className="lbl">{gap.is_measured_proficiency ? 'Measured Mastery' : 'Estimated Prior'}</span>
                    <span className="val">
                      {(gap.candidate_mastery * 100).toFixed(0)}%
                      {!gap.is_measured_proficiency && <span style={{ fontSize: '0.72rem', color: '#94a3b8', marginLeft: '4px', fontWeight: 400 }}>(Unassessed)</span>}
                    </span>
                  </div>
                  <div className="gap-metric">
                    <span className="lbl">Role Requirement</span>
                    <span className="val">{(gap.required_mastery * 100).toFixed(0)}%</span>
                  </div>
                  <div className="gap-metric">
                    <span className="lbl">Transfer Deficit</span>
                    <span className="val">{gap.transfer_deficit.toFixed(2)}</span>
                  </div>
                  <div className="gap-metric">
                    <span className="lbl">Effective Gap</span>
                    <span className="val font-highlight">{gap.effective_gap.toFixed(2)}</span>
                  </div>
                </div>

                <div className="gap-diagnostic-reasoning">
                  <p>{gap.reasoning}</p>
                </div>

                {gap.core_invariants && gap.core_invariants.length > 0 && (
                  <div className="gap-invariants-list">
                    <span className="label-bold">Target Invariants:</span>
                    <div className="invariants-pills">
                      {gap.core_invariants.map((inv, idx) => (
                        <span key={idx} className="invariant-pill">
                          {inv}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'gaps' && !gapAnalysis && !loading && (
        <div className="surface-card p-8 text-center text-secondary border-subtle">
          <ShieldCheck size={32} className="mx-auto mb-3 text-muted" />
          <h3 className="text-base font-bold text-primary mb-1">No Role Gap Diagnosis Available</h3>
          <p className="text-xs text-muted max-w-md mx-auto">
            Take a diagnostic technical interview or click &ldquo;Target &amp; Generate&rdquo; to benchmark competencies against {targetRole}.
          </p>
        </div>
      )}
    </div>
  );
};
