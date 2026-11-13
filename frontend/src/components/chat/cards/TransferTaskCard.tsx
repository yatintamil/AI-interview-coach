import React from 'react';
import { GitBranch, ArrowRight, ShieldCheck } from 'lucide-react';
import { StructuredUIPayload, formatTransferLevel } from '../../../types';
import { useNavigate } from 'react-router-dom';

interface TransferTaskCardProps {
  payload: StructuredUIPayload;
}

export const TransferTaskCard: React.FC<TransferTaskCardProps> = ({ payload }) => {
  const navigate = useNavigate();
  const displayLevel = formatTransferLevel(payload.transfer_level || 'L3_FAR_TRANSFER');
  const invariants = Array.isArray(payload.core_invariants)
    ? payload.core_invariants
    : Array.isArray(payload.invariants)
    ? payload.invariants
    : [];

  return (
    <div className="structured-card transfer-task-card" data-testid="transfer-task-card">
      <div className="card-header-badge">
        <span className="badge badge-transfer">
          <GitBranch size={13} className="badge-icon" />
          <span>Transfer Challenge</span>
        </span>
        <span className="badge badge-level">{displayLevel}</span>
      </div>

      <div className="transfer-card-meta">
        Targeting schema induction and cross-domain structural invariant mapping.
      </div>

      {invariants.length > 0 && (
        <div className="card-invariants-section">
          <div className="invariants-label">Target Invariants:</div>
          <div className="invariants-list">
            {invariants.map((inv, idx) => (
              <div key={idx} className="invariant-pill">
                <ShieldCheck size={13} className="pill-icon text-cyan" />
                <span>{inv}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card-action-footer">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => navigate('/coaching')}
        >
          <span>Practice in Coaching Studio</span>
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
};
