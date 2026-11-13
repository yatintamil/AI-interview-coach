import React from 'react';
import { Compass, CheckCircle2 } from 'lucide-react';

interface StageProgressionHUDProps {
  currentStageIndex: number;
  totalStages: number;
  currentTurn: number;
  totalTurns?: number;
  evidenceCoverageRatio?: number;
  competenciesAssessedCount?: number;
  totalCompetenciesCount?: number;
  stageName: string;
  targetCompetency?: string;
  assessmentObjective?: string;
  isFollowup?: boolean;
  onConcludeInterview?: () => void;
}

const STAGES = [
  { index: 1, name: 'Orientation', desc: 'Domain & Resume Grounding' },
  { index: 2, name: 'Core Mechanics', desc: 'Algorithms & Code Invariants' },
  { index: 3, name: 'Scalable Systems', desc: 'Architecture & Trade-offs' },
  { index: 4, name: 'Incident Debugging', desc: 'Failure Modes & Triage' },
  { index: 5, name: 'STAR Leadership', desc: 'Behavioral Ownership' },
];

export const StageProgressionHUD: React.FC<StageProgressionHUDProps> = ({
  currentStageIndex,
  totalStages,
  currentTurn,
  evidenceCoverageRatio,
  competenciesAssessedCount,
  totalCompetenciesCount,
  stageName,
  targetCompetency,
  assessmentObjective,
  isFollowup,
  onConcludeInterview,
}) => {
  return (
    <div className="stage-hud-wrapper">
      <div className="stage-hud-header">
        <div className="stage-hud-title">
          <Compass size={16} className="compass-icon" />
          <span>Stage {currentStageIndex} of {totalStages}: <strong>{stageName}</strong></span>
          {targetCompetency && (
            <span
              style={{
                marginLeft: '10px',
                fontSize: '0.75rem',
                padding: '2px 8px',
                borderRadius: '4px',
                background: 'rgba(99, 102, 241, 0.2)',
                color: 'var(--accent-primary)',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                fontWeight: 600,
              }}
              title={assessmentObjective || targetCompetency}
            >
              Competency: {targetCompetency}
            </span>
          )}
          {isFollowup && (
            <span
              style={{
                marginLeft: '6px',
                fontSize: '0.725rem',
                padding: '2px 7px',
                borderRadius: '4px',
                background: 'rgba(245, 158, 11, 0.2)',
                color: '#fbbf24',
                border: '1px solid rgba(245, 158, 11, 0.4)',
                fontWeight: 600,
              }}
            >
              Adaptive Probe / Follow-Up
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="stage-hud-turn-badge" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Question #{currentTurn}</span>
            {typeof evidenceCoverageRatio === 'number' && (
              <>
                <span style={{ opacity: 0.5 }}>·</span>
                <span style={{ color: '#818cf8', fontWeight: 700 }}>
                  {Math.min(100, Math.round(evidenceCoverageRatio * 100))}% Evidence Coverage
                </span>
              </>
            )}
            {typeof competenciesAssessedCount === 'number' && competenciesAssessedCount > 0 && (
              <>
                <span style={{ opacity: 0.5 }}>·</span>
                <span style={{ color: '#38bdf8' }}>
                  {competenciesAssessedCount}/{totalCompetenciesCount || 5} Assessed
                </span>
              </>
            )}
          </div>
          {onConcludeInterview && (
            <button
              type="button"
              onClick={onConcludeInterview}
              className="btn btn-ghost"
              style={{
                fontSize: '0.75rem',
                padding: '3px 8px',
                color: '#f87171',
                border: '1px solid rgba(248, 113, 113, 0.3)',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(239, 68, 68, 0.08)',
                cursor: 'pointer',
              }}
              title="Conclude interview and generate comprehensive skill debrief"
            >
              Conclude Interview
            </button>
          )}
        </div>
      </div>

      <div className="stage-hud-steps">
        {STAGES.map((s) => {
          const isCompleted = s.index < currentStageIndex;
          const isActive = s.index === currentStageIndex;

          return (
            <div
              key={s.index}
              className={`stage-hud-pill ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
            >
              <div className="stage-pill-number">
                {isCompleted ? <CheckCircle2 size={13} /> : s.index}
              </div>
              <div className="stage-pill-details">
                <span className="stage-pill-name">{s.name}</span>
                <span className="stage-pill-desc">{s.desc}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
