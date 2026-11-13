import React, { useState } from 'react';
import {
  OrchestratorStepResultDTO,
  ResearchTelemetryRecordDTO,
} from '../../types/coaching';
import { Terminal, ChevronDown, ChevronUp, Cpu, Database, Eye, RefreshCw } from 'lucide-react';

interface ResearchDebugHUDProps {
  sessionState: OrchestratorStepResultDTO | null;
  telemetry: ResearchTelemetryRecordDTO | null;
  sessionId: string | null;
  onRefreshTelemetry?: () => void;
}

/**
 * Research Debug HUD (Read-Only)
 * STRICT REQUIREMENT:
 * - Hidden/collapsed by default
 * - Read-only (cannot modify coaching policy or state)
 * - Separated from candidate-facing journey
 * - Displays research telemetry and internal state for validation
 */
export const ResearchDebugHUD: React.FC<ResearchDebugHUDProps> = ({
  sessionState,
  telemetry,
  sessionId,
  onRefreshTelemetry,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div
      style={{
        marginTop: '32px',
        borderTop: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.1))',
        paddingTop: '16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          padding: '8px 12px',
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: '8px',
          border: '1px dashed var(--border-subtle, rgba(255, 255, 255, 0.15))',
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={14} style={{ color: 'var(--accent-primary, #6366f1)' }} />
          <span
            style={{
              fontSize: '0.8rem',
              fontWeight: 600,
              letterSpacing: '0.05em',
              color: 'var(--text-muted, #94a3b8)',
              textTransform: 'uppercase',
            }}
          >
            Research Debug HUD (Read-Only Experimental Telemetry)
          </span>
          <span
            className="status-badge"
            style={{
              fontSize: '0.7rem',
              padding: '2px 8px',
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#818cf8',
              borderRadius: '4px',
            }}
          >
            Dev / Research Only
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)' }}>
            {isOpen ? 'Click to collapse' : 'Click to inspect raw telemetry'}
          </span>
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {isOpen && (
        <div
          style={{
            marginTop: '12px',
            padding: '16px',
            background: '#090d16',
            borderRadius: '8px',
            border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.1))',
            fontFamily: 'monospace',
            fontSize: '0.78rem',
            color: '#cbd5e1',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '12px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              paddingBottom: '8px',
            }}
          >
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div>
                <span style={{ color: '#64748b' }}>Session ID: </span>
                <span style={{ color: '#38bdf8' }}>{sessionId || 'N/A'}</span>
              </div>
              <div>
                <span style={{ color: '#64748b' }}>Backend State: </span>
                <span style={{ color: '#a855f7', fontWeight: 'bold' }}>
                  {sessionState?.state || 'NONE'}
                </span>
              </div>
              <div>
                <span style={{ color: '#64748b' }}>Outcome: </span>
                <span style={{ color: '#34d399' }}>{sessionState?.outcome || 'NONE'}</span>
              </div>
              <div>
                <span style={{ color: '#64748b' }}>Retry Count: </span>
                <span>{sessionState?.retry_count ?? 0}</span>
              </div>
            </div>

            {onRefreshTelemetry && (
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '0.72rem' }}
                onClick={(e) => {
                  e.stopPropagation();
                  onRefreshTelemetry();
                }}
                title="Refresh Telemetry Record"
              >
                <RefreshCw size={12} />
                <span>Refresh</span>
              </button>
            )}
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '12px',
              marginBottom: '16px',
            }}
          >
            {/* Task Research Attributes */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
              }}
            >
              <div
                style={{
                  color: '#94a3b8',
                  fontWeight: 600,
                  marginBottom: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <Database size={13} />
                Task Metadata
              </div>
              <div>Task ID: {sessionState?.task?.id || 'N/A'}</div>
              <div>
                Transfer Level:{' '}
                <span style={{ color: '#f59e0b' }}>
                  {sessionState?.task?.transfer_level || 'N/A'}
                </span>
              </div>
              <div>Skill ID: {sessionState?.task?.skill_id || 'N/A'}</div>
              <div>Invariants: {sessionState?.task?.core_invariants?.length ?? 0} listed</div>
            </div>

            {/* Diagnosis & Scaffolding */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
              }}
            >
              <div
                style={{
                  color: '#94a3b8',
                  fontWeight: 600,
                  marginBottom: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <Cpu size={13} />
                Diagnosis & Policy
              </div>
              <div>
                Diagnosis Type:{' '}
                <span style={{ color: '#ec4899' }}>
                  {sessionState?.diagnosis?.failure_type || 'NONE'}
                </span>
              </div>
              <div>
                Confidence:{' '}
                {sessionState?.diagnosis?.confidence
                  ? `${(sessionState.diagnosis.confidence * 100).toFixed(0)}%`
                  : 'N/A'}
              </div>
              <div>
                Intervention:{' '}
                <span style={{ color: '#38bdf8' }}>
                  {sessionState?.intervention?.intervention_type || 'NONE'}
                </span>
              </div>
              <div>
                Scaffold Level:{' '}
                <span style={{ color: '#10b981' }}>
                  {sessionState?.scaffold_state?.current_level ||
                    sessionState?.intervention?.scaffold_level ||
                    'N/A'}
                </span>
              </div>
              <div>
                Scaffold Faded:{' '}
                {sessionState?.scaffold_state?.is_faded ? 'TRUE' : 'FALSE'}
              </div>
            </div>

            {/* Candidate Skill Mastery Estimate */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
              }}
            >
              <div
                style={{
                  color: '#94a3b8',
                  fontWeight: 600,
                  marginBottom: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <Eye size={13} />
                Skill State
              </div>
              <div>
                Mastery Estimate:{' '}
                {sessionState?.candidate_state?.mastery_estimate !== undefined
                  ? sessionState.candidate_state.mastery_estimate.toFixed(2)
                  : 'N/A'}
              </div>
              <div>
                Uncertainty:{' '}
                {sessionState?.candidate_state?.mastery_uncertainty !== undefined
                  ? sessionState.candidate_state.mastery_uncertainty.toFixed(2)
                  : 'N/A'}
              </div>
              <div>
                Dependency Index:{' '}
                {sessionState?.candidate_state?.assistance_dependency_index !== undefined
                  ? sessionState.candidate_state.assistance_dependency_index.toFixed(2)
                  : 'N/A'}
              </div>
              <div>
                Highest Transfer:{' '}
                {sessionState?.candidate_state?.highest_transfer_level || 'N/A'}
              </div>
            </div>
          </div>

          {/* Raw Telemetry JSON Accordion */}
          {telemetry && (
            <div style={{ marginTop: '10px' }}>
              <div style={{ color: '#64748b', marginBottom: '4px' }}>
                Persisted Telemetry Record ({telemetry.attempts_history?.length || 0} attempts):
              </div>
              <pre
                style={{
                  maxHeight: '160px',
                  overflowY: 'auto',
                  background: 'rgba(0, 0, 0, 0.4)',
                  padding: '8px',
                  borderRadius: '4px',
                  fontSize: '0.72rem',
                }}
              >
                {JSON.stringify(telemetry, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
