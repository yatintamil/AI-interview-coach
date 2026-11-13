import React from 'react';
import { Candidate, CandidateProfile } from '../../types';
import { Compass, Cpu, Play, CheckCircle } from 'lucide-react';

interface InterviewSetupCardProps {
  selectedCandidate: Candidate;
  profile: CandidateProfile | null;
  targetRole: string;
  setTargetRole: (r: string) => void;
  targetRoles: string[];
  setTargetRoles: (roles: string[]) => void;
  customRoleDescription: string;
  setCustomRoleDescription: (d: string) => void;
  isCustomRole: boolean;
  setIsCustomRole: (v: boolean) => void;
  interviewType: string;
  setInterviewType: (t: string) => void;
  difficulty: string;
  setDifficulty: (d: string) => void;
  questionCount?: number;
  setQuestionCount?: (c: number) => void;
  coachingMode: string;
  setCoachingMode: (m: string) => void;
  creating: boolean;
  onLaunch: (e: React.FormEvent) => void;
}

const OMNIROLE_DEFAULT = 'Adaptive Omnirole (Universal Competencies)';
const POPULAR_ROLES = [
  'Embedding Systems Engineer',
  'Distributed Database Reliability Engineer',
  'Machine Learning Engineer',
  'Backend Systems Engineer',
  'Cloud DevOps / SRE',
];

export const InterviewSetupCard: React.FC<InterviewSetupCardProps> = ({
  selectedCandidate,
  profile,
  targetRole,
  setTargetRole,
  targetRoles,
  setTargetRoles,
  customRoleDescription,
  setCustomRoleDescription,
  isCustomRole,
  setIsCustomRole,
  interviewType,
  setInterviewType,
  difficulty,
  setDifficulty,
  coachingMode,
  setCoachingMode,
  creating,
  onLaunch,
}) => {
  const toggleRole = (r: string) => {
    if (targetRoles.includes(r)) {
      if (targetRoles.length > 1) {
        const next = targetRoles.filter((item) => item !== r);
        setTargetRoles(next);
        setTargetRole(next[0]);
      }
    } else {
      const next = [...targetRoles, r];
      setTargetRoles(next);
      setTargetRole(next[0]);
    }
  };

  return (
    <div className="studio-panel" style={{ maxWidth: '820px', margin: '0 auto' }}>
      <div className="studio-panel-header">
        <div className="studio-panel-title">
          <Compass size={18} color="var(--accent-primary)" />
          <span>Configure Role-Aware Adaptive Interview Session</span>
        </div>
      </div>

      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '20px' }}>
        Configuring interview round for <strong style={{ color: '#fff' }}>{selectedCandidate.full_name}</strong>.
        Structured role intelligence maps competencies, objectives, and invariants. Resume context personalizes scenario framing.
      </p>

      <form onSubmit={onLaunch}>
        {/* Track Selection Hero */}
        <div className="form-group" style={{ marginBottom: '22px' }}>
          <label className="form-label" style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '8px' }}>
            Target Role Intelligence & Blueprint Selection
          </label>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div
              className={`setup-track-card ${!isCustomRole ? 'selected' : ''}`}
              onClick={() => {
                setIsCustomRole(false);
                setTargetRole(OMNIROLE_DEFAULT);
                setTargetRoles([OMNIROLE_DEFAULT]);
              }}
              role="button"
              tabIndex={0}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Compass size={18} color="var(--accent-primary)" />
                  <strong style={{ fontSize: '0.95rem' }}>Adaptive Omnirole (Universal)</strong>
                </div>
                {!isCustomRole && <CheckCircle size={16} color="var(--accent-primary)" />}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.4 }}>
                Tests cross-company engineering excellence: algorithms, scalable systems, debugging, and leadership invariants.
              </p>
            </div>

            <div
              className={`setup-track-card ${isCustomRole ? 'selected' : ''}`}
              onClick={() => {
                setIsCustomRole(true);
                if (targetRole === OMNIROLE_DEFAULT) {
                  const defaultRole = profile?.recommended_roles?.[0] || 'Embedding Systems Engineer';
                  setTargetRole(defaultRole);
                  setTargetRoles([defaultRole]);
                }
              }}
              role="button"
              tabIndex={0}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Cpu size={18} color="#60a5fa" />
                  <strong style={{ fontSize: '0.95rem' }}>Specialized / Multi-Role Gauntlet</strong>
                </div>
                {isCustomRole && <CheckCircle size={16} color="#60a5fa" />}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.4 }}>
                Synthesizes role competency blueprints for single or combined roles (e.g. Embedding Systems + Distributed Database).
              </p>
            </div>
          </div>

          {isCustomRole && (
            <div className="fade-in" style={{ marginTop: '14px', padding: '14px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ marginBottom: '10px' }}>
                <label className="form-label" style={{ fontSize: '0.825rem', marginBottom: '6px' }}>Curated Role Profiles (Click to toggle multi-role synthesis):</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {POPULAR_ROLES.map((r) => {
                    const isSelected = targetRoles.includes(r);
                    return (
                      <button
                        type="button"
                        key={r}
                        className={`badge ${isSelected ? 'badge-verified' : ''}`}
                        style={{
                          cursor: 'pointer',
                          padding: '4px 10px',
                          border: isSelected ? '1px solid var(--accent-primary)' : '1px solid rgba(255,255,255,0.1)',
                          background: isSelected ? 'rgba(37, 99, 235, 0.15)' : 'rgba(255,255,255,0.03)',
                          color: isSelected ? '#fff' : 'var(--text-muted)',
                        }}
                        onClick={() => toggleRole(r)}
                      >
                        {isSelected ? 'Selected: ' : '+ '}{r}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ marginTop: '12px' }}>
                <label className="form-label" style={{ fontSize: '0.825rem' }}>Primary Target Role Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Embedding Systems Engineer, Distributed Database Reliability Engineer"
                  value={targetRole}
                  onChange={(e) => {
                    setTargetRole(e.target.value);
                    if (!targetRoles.includes(e.target.value) && e.target.value.trim()) {
                      setTargetRoles([e.target.value.trim()]);
                    }
                  }}
                  required
                />
              </div>

              <div style={{ marginTop: '12px' }}>
                <label className="form-label" style={{ fontSize: '0.825rem' }}>
                  Custom Role Description & Expectations (Optional — used to construct structured profile if unknown)
                </label>
                <textarea
                  className="form-input"
                  rows={2}
                  placeholder="e.g. Focus on vector index memory footprints, HNSW graph construction, and high-throughput real-time embedding pipelines..."
                  value={customRoleDescription}
                  onChange={(e) => setCustomRoleDescription(e.target.value)}
                  style={{ resize: 'vertical' }}
                />
              </div>
            </div>
          )}
        </div>

        {/* 3-Column Configuration Grid */}
        <div className="grid-3" style={{ marginBottom: '20px' }}>
          <div className="form-group">
            <label className="form-label">Interview Type</label>
            <select
              className="form-select"
              value={interviewType}
              onChange={(e) => setInterviewType(e.target.value)}
            >
              <option value="TECHNICAL">Technical Deep-Dive</option>
              <option value="BEHAVIORAL">Behavioral & Leadership (STAR)</option>
              <option value="MIXED">Full-Loop (Mixed Technical & Behavioral)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Initial Difficulty</label>
            <select
              className="form-select"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            >
              <option value="EASY">Foundational / Entry-Level</option>
              <option value="MEDIUM">Calibrated Mid-Level</option>
              <option value="HARD">Senior / Staff Gauntlet</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Assessment Protocol</label>
            <div style={{ padding: '8px 12px', background: 'rgba(99, 102, 241, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(99, 102, 241, 0.25)', fontSize: '0.85rem', color: '#c7d2fe' }}>
              <strong>Adaptive Evidence-Driven</strong>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Questions dynamically adapt until role competencies have sufficient empirical evidence or until you choose to conclude.
              </div>
            </div>
          </div>
        </div>

        {/* Coaching Mode Selector */}
        <div className="form-group" style={{ marginBottom: '25px' }}>
          <label className="form-label">Coaching Mode</label>
          <div style={{ display: 'flex', gap: '16px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.85rem' }}>
              <input
                type="radio"
                name="coachingMode"
                value="COACHING"
                checked={coachingMode === 'COACHING'}
                onChange={() => setCoachingMode('COACHING')}
              />
              <span><strong>Interactive Coaching Mode</strong> (Socratic hints, pedagogical nudges & exemplars available)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.85rem' }}>
              <input
                type="radio"
                name="coachingMode"
                value="SIMULATION"
                checked={coachingMode === 'SIMULATION'}
                onChange={() => setCoachingMode('SIMULATION')}
              />
              <span><strong>Strict Exam Simulation</strong> (No hints, continuous timer)</span>
            </label>
          </div>
        </div>

        {/* Stage Preview Box */}
        <div style={{ padding: '14px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', marginBottom: '22px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            5-Stage Lifecycle Assessment Structure:
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', fontSize: '0.78rem' }}>
            <span className="badge badge-verified">1. Orientation & Baseline</span>
            <span className="badge badge-verified">2. Core Mechanics & Code</span>
            <span className="badge badge-verified">3. Scalable Systems</span>
            <span className="badge badge-verified">4. Incident Debugging</span>
            <span className="badge badge-verified">5. Behavioral STAR</span>
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: '100%', padding: '12px', fontSize: '1rem', fontWeight: 600 }}
          disabled={creating}
        >
          <Play size={18} />
          {creating ? 'Initializing Adaptive Session...' : 'Launch Live Interview Gauntlet'}
        </button>
      </form>
    </div>
  );
};
