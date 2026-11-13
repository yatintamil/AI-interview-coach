import React from 'react';
import { BookOpen, Compass, Target, Layers } from 'lucide-react';
import { StructuredUIPayload } from '../../../types';

interface CoachingLessonCardProps {
  payload: StructuredUIPayload;
}

export const CoachingLessonCard: React.FC<CoachingLessonCardProps> = ({ payload }) => {
  const rawPhase = String(payload.phase || 'PHASE_B_FUNDAMENTALS');
  const phaseLabel = rawPhase
    .replace('PHASE_', 'Stage ')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const scaffold = String(payload.scaffold_level || 'HIGH').toUpperCase();
  const skill = payload.focus_skill || payload.skill || 'System Architecture';
  const objective = payload.learning_objective || 'Master core structural invariants and unassisted transfer.';

  const scaffoldDescriptions: Record<string, string> = {
    HIGH: 'Full conceptual scaffolding, structured breakdown, and concrete worked examples.',
    MEDIUM: 'Socratic guided questioning with hints on failure.',
    LOW: 'Minimal prompting; candidate plans and justifies design decisions.',
    INDEPENDENT: 'Unassisted independent challenge; evaluates L5 transfer.',
  };

  return (
    <div className="structured-card coaching-lesson-card" data-testid="coaching-lesson-card" style={{
      border: '1px solid var(--border-card, #2d3b52)',
      background: 'var(--surface-card, #162032)',
      padding: '16px',
      borderRadius: '4px',
      marginTop: '10px'
    }}>
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="badge badge-primary flex items-center gap-1.5" style={{
            background: 'var(--brand-subtle, #e0e7ff)',
            color: 'var(--brand-primary, #4f46e5)',
            fontWeight: 600,
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '0.75rem'
          }}>
            <BookOpen size={13} />
            <span>Interactive Tutoring Module</span>
          </span>
          <span className="badge badge-secondary" style={{
            fontSize: '0.75rem',
            padding: '4px 8px',
            borderRadius: '4px',
            background: 'var(--surface-secondary, #f1f5f9)',
            color: 'var(--text-secondary, #475569)'
          }}>
            {phaseLabel}
          </span>
          {payload.is_fallback && (
            <span className="badge badge-warning" data-testid="card-fallback-badge" style={{
              fontSize: '0.72rem',
              padding: '4px 7px',
              borderRadius: '4px',
              background: '#fef3c7',
              color: '#b45309',
              fontWeight: 600,
            }}>
              Offline Adaptive Fallback
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 text-xs font-semibold" style={{
          color: scaffold === 'HIGH' ? '#d97706' : scaffold === 'MEDIUM' ? '#2563eb' : '#059669'
        }}>
          <Compass size={13} />
          <span>Scaffold: {scaffold}</span>
        </div>
      </div>

      <div className="mb-2">
        <div className="text-xs uppercase tracking-wider font-bold text-muted mb-0.5">Target Competency</div>
        <div className="font-semibold text-primary" style={{ fontSize: '0.95rem' }}>{skill}</div>
      </div>

      <div className="p-3 rounded mb-3" style={{ background: 'var(--surface-secondary, #f8fafc)', border: '1px solid var(--border-default, #e2e8f0)' }}>
        <div className="flex items-start gap-2">
          <Target size={15} style={{ color: 'var(--brand-primary, #4f46e5)', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div className="text-xs font-semibold text-primary mb-0.5">Learning Objective</div>
            <div className="text-xs text-secondary leading-relaxed">{objective}</div>
          </div>
        </div>
      </div>

      <div className="text-xs text-muted flex items-center gap-1.5 pt-1 border-t border-slate-100">
        <Layers size={12} />
        <span>{scaffoldDescriptions[scaffold] || scaffoldDescriptions.HIGH}</span>
      </div>
    </div>
  );
};
