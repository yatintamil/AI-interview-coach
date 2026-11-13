import React from 'react';
import { Compass, ArrowRight, AlertTriangle } from 'lucide-react';
import { StructuredUIPayload } from '../../../types';
import { useNavigate } from 'react-router-dom';

interface RoadmapSummaryCardProps {
  payload: StructuredUIPayload;
}

export const RoadmapSummaryCard: React.FC<RoadmapSummaryCardProps> = ({ payload }) => {
  const navigate = useNavigate();
  const role = payload.role || 'Software Engineer';
  const gaps = Array.isArray(payload.top_gaps) ? payload.top_gaps : [];

  return (
    <div className="structured-card roadmap-summary-card" data-testid="roadmap-summary-card">
      <div className="card-header-badge">
        <span className="badge badge-roadmap">
          <Compass size={13} className="badge-icon" />
          <span>Curriculum Roadmap</span>
        </span>
        <span className="badge badge-subtle">{role}</span>
      </div>

      <div className="card-topic-title">Target Competency Gaps</div>

      {gaps.length > 0 ? (
        <div className="roadmap-gaps-list">
          {gaps.map((item, idx) => {
            const skillTitle = item.skill_name || item.skill_id || 'Competency';
            const gapValue = typeof item.gap === 'number' ? item.gap : 0;
            const gapPercent = Math.min(100, Math.max(0, Math.round(gapValue * 100)));

            return (
              <div key={idx} className="roadmap-gap-item">
                <div className="gap-item-info">
                  <span className="gap-skill-name">{skillTitle}</span>
                  <span className="gap-score-tag">
                    <AlertTriangle size={12} className="text-warning" />
                    Gap: {gapPercent}%
                  </span>
                </div>
                <div className="progress-bar-container">
                  <div
                    className="progress-bar-fill progress-bar-warning"
                    style={{ width: `${Math.max(10, gapPercent)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="empty-subtle">No high-priority gaps detected for this role track.</p>
      )}

      <div className="card-action-footer">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => navigate('/roadmap')}
        >
          <span>View Full Learning Roadmap</span>
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
};
