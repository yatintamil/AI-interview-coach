import React from 'react';
import {
  Layers,
  MessageSquare,
  Compass,
  Award,
  History,
  RotateCcw,
  Zap,
} from 'lucide-react';
import { Candidate } from '../../types';
import { ScaffoldLevel } from '../../types/coaching';

export type CoachingWorkspaceMode = 'conversation' | 'practice' | 'transfer';

export interface CompetencyOption {
  id: string;
  label: string;
}

interface CoachingHeaderProps {
  selectedCandidate: Candidate | null;
  activeRole: string;
  selectedSkill: string;
  competencies?: CompetencyOption[];
  onSelectSkill?: (skillId: string) => void;
  activeMode: CoachingWorkspaceMode;
  onChangeMode: (mode: CoachingWorkspaceMode) => void;
  scaffoldLevel: ScaffoldLevel | string;
  currentPhaseTitle?: string;
  sessionId?: string | null;
  onToggleHistoryDrawer: () => void;
  isHistoryDrawerOpen: boolean;
  onResetSession?: () => void;
  masteryScore?: number | null;
  hasMasteryEvidence?: boolean;
  activeSkillTitle?: string | null;
  activeLearningObjective?: string | null;
}

export const CoachingHeader: React.FC<CoachingHeaderProps> = ({
  selectedCandidate,
  activeRole,
  selectedSkill,
  activeMode,
  onChangeMode,
  scaffoldLevel,
  currentPhaseTitle = 'Phase B: Fundamentals & Mechanics',
  sessionId,
  onToggleHistoryDrawer,
  isHistoryDrawerOpen,
  onResetSession,
  masteryScore,
  hasMasteryEvidence,
  activeSkillTitle,
  activeLearningObjective,
}) => {
  const getScaffoldColor = (scaffold: string) => {
    switch (scaffold) {
      case 'HIGH':
      case 'HIGH_ASSISTANCE':
        return '#94a3b8'; // Slate
      case 'MEDIUM':
      case 'MEDIUM_ASSISTANCE':
        return '#60a5fa'; // Light cobalt
      case 'LOW':
      case 'LOW_ASSISTANCE':
        return '#2563eb'; // Primary cobalt
      case 'INDEPENDENT':
        return '#059669'; // Forest emerald
      default:
        return '#94a3b8';
    }
  };

  const scaffoldFormatted =
    scaffoldLevel === 'HIGH_ASSISTANCE' || scaffoldLevel === 'HIGH'
      ? 'High Scaffold'
      : scaffoldLevel === 'MEDIUM_ASSISTANCE' || scaffoldLevel === 'MEDIUM'
      ? 'Medium Scaffold'
      : scaffoldLevel === 'LOW_ASSISTANCE' || scaffoldLevel === 'LOW'
      ? 'Low Scaffold'
      : scaffoldLevel === 'INDEPENDENT'
      ? 'Independent (Unassisted)'
      : String(scaffoldLevel);

  const displayCompetency = activeSkillTitle || selectedSkill;

  return (
    <header className="coaching-unified-header">
      {/* Top Meta & Mode Navigation Bar */}
      <div className="coaching-header-top-row">
        <div className="coaching-brand-group">
          <button
            type="button"
            className={`btn-history-toggle ${isHistoryDrawerOpen ? 'active' : ''}`}
            onClick={onToggleHistoryDrawer}
            title={isHistoryDrawerOpen ? 'Hide History Drawer' : 'Show Sessions & History'}
            aria-label="Toggle coaching session history drawer"
            data-testid="sessions-toggle-btn"
          >
            <History size={16} />
            <span className="history-btn-label">Sessions</span>
          </button>

          <div className="coaching-title-cluster">
            <div className="coaching-icon-badge">
              <Compass size={16} />
            </div>
            <div>
              <div className="coaching-main-title">
                AI Coach
              </div>
              {displayCompetency && (
                <div style={{ fontSize: '0.725rem', color: 'var(--text-tertiary, #64748b)', fontWeight: 500 }}>
                  {displayCompetency}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Center Mode Switcher: Learn, Practice, Transfer */}
        <nav className="coaching-mode-segmented-bar" aria-label="Coaching workspace view modes">
          <button
            type="button"
            className={`mode-segment-btn ${activeMode === 'conversation' ? 'active' : ''}`}
            onClick={() => onChangeMode('conversation')}
            data-testid="mode-tab-conversation"
          >
            <MessageSquare size={15} />
            <span>Learn</span>
          </button>

          <button
            type="button"
            className={`mode-segment-btn ${activeMode === 'practice' ? 'active' : ''}`}
            onClick={() => onChangeMode('practice')}
            data-testid="mode-tab-practice"
          >
            <Layers size={15} />
            <span>Practice</span>
          </button>

          <button
            type="button"
            className={`mode-segment-btn ${activeMode === 'transfer' ? 'active' : ''}`}
            onClick={() => onChangeMode('transfer')}
            data-testid="mode-tab-transfer"
          >
            <Award size={15} />
            <span>Transfer</span>
          </button>
        </nav>

        {/* Candidate & Session Info */}
        <div className="coaching-meta-indicators">
          {sessionId && (
            <div
              className="meta-indicator-chip session-chip"
              data-testid="coaching-session-id"
              title={`Active Session: ${sessionId}`}
            >
              <Compass size={13} />
              <span className="mono-text">{sessionId.length > 18 ? `${sessionId.slice(0, 16)}...` : sessionId}</span>
            </div>
          )}

          {selectedCandidate && (
            <div className="meta-indicator-chip candidate-chip" title={`${selectedCandidate.full_name} (${activeRole})`}>
              <span className="candidate-avatar-dot"></span>
              <span className="candidate-name-label" data-testid="coaching-candidate-name">{selectedCandidate.full_name}</span>
              <span className="role-badge-small">{activeRole}</span>
            </div>
          )}

          {onResetSession && (
            <button
              type="button"
              className="btn-header-action"
              onClick={onResetSession}
              title="Reset coaching session to start fresh"
              data-testid="coaching-reset-btn"
            >
              <RotateCcw size={13} />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* Authoritative Competency & Scaffold Ribbon */}
      <div className="coaching-control-ribbon">
        <div className="competency-badge-cluster">
          <div className="active-competency-pill" data-testid="active-competency-badge">
            <span className="ribbon-label">Active Focus:</span>
            <span className="active-competency-name">{displayCompetency}</span>
          </div>

          {activeLearningObjective && (
            <div
              data-testid="coaching-header-objective"
              className="objective-tag-pill"
              title={activeLearningObjective}
            >
              <strong>Objective:</strong> {activeLearningObjective}
            </div>
          )}
        </div>

        {/* Active Stage & Scaffold Level Pill */}
        <div className="stage-scaffold-cluster">
          {currentPhaseTitle && (
            <div
              className="meta-indicator-chip phase-pill"
              title={`Phase: ${currentPhaseTitle}`}
              style={{
                background: 'var(--surface-raised, #1e293b)',
                border: '1px solid var(--border-subtle, #243042)',
                fontSize: '0.75rem',
                fontWeight: 600,
              }}
            >
              <span className="candidate-avatar-dot" style={{ background: 'var(--brand-primary, #2563eb)' }}></span>
              <span>{currentPhaseTitle}</span>
            </div>
          )}

          {hasMasteryEvidence && masteryScore !== null && masteryScore !== undefined ? (
            <div
              className="meta-indicator-chip"
              data-testid="mastery-evidence-badge"
              style={{
                background: 'rgba(37, 99, 235, 0.10)',
                color: 'var(--brand-primary, #2563eb)',
                border: '1px solid #1d4ed8',
                fontWeight: 600,
              }}
            >
              <Award size={13} />
              <span>{Math.round(masteryScore * 100)}% Mastery</span>
            </div>
          ) : (
            <div
              className="meta-indicator-chip mastery-insufficient-chip"
              data-testid="mastery-evidence-badge"
              style={{
                background: 'rgba(148, 163, 184, 0.08)',
                color: 'var(--text-secondary, #94a3b8)',
                border: '1px solid rgba(148, 163, 184, 0.2)',
                fontSize: '0.75rem',
                fontWeight: 500,
              }}
              title="No evaluated assessment evidence for this competency yet"
            >
              <span>Not enough evidence</span>
            </div>
          )}

          <div
            className="scaffold-pill"
            style={{
              borderColor: `${getScaffoldColor(scaffoldLevel)}40`,
              backgroundColor: `${getScaffoldColor(scaffoldLevel)}15`,
              color: getScaffoldColor(scaffoldLevel),
            }}
            title="Scaffold level automatically fades as you demonstrate invariant understanding"
          >
            <Zap size={13} />
            <span className="scaffold-text">{scaffoldFormatted}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
