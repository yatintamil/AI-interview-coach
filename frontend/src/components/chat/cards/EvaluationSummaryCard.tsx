import React from 'react';
import { CheckCircle2, TrendingUp, FileText } from 'lucide-react';
import { StructuredUIPayload } from '../../../types';

interface EvaluationSummaryCardProps {
  payload: StructuredUIPayload;
}

export const EvaluationSummaryCard: React.FC<EvaluationSummaryCardProps> = ({ payload }) => {
  const score = typeof payload.score === 'number' ? payload.score : null;
  const feedback = typeof payload.feedback === 'string' ? payload.feedback : '';
  const rubric =
    payload.rubric_breakdown && typeof payload.rubric_breakdown === 'object'
      ? payload.rubric_breakdown
      : {};

  return (
    <div className="structured-card evaluation-summary-card" data-testid="evaluation-summary-card">
      <div className="card-header-badge">
        <span className="badge badge-accent">
          <TrendingUp size={13} className="badge-icon" />
          <span>Evaluation Assessment</span>
        </span>
        {score !== null && (
          <span className="badge badge-score">
            Score: {score} / 10
          </span>
        )}
      </div>

      {feedback && (
        <div className="evaluation-feedback-body">
          <FileText size={14} className="feedback-icon" />
          <p className="feedback-text">{feedback}</p>
        </div>
      )}

      {Object.keys(rubric).length > 0 && (
        <div className="evaluation-rubric-breakdown">
          <div className="rubric-label">Rubric Breakdown:</div>
          <div className="rubric-items">
            {Object.entries(rubric).map(([k, v], idx) => (
              <div key={idx} className="rubric-item-row">
                <CheckCircle2 size={12} className="text-success" />
                <span className="rubric-key">{k.replace(/_/g, ' ')}:</span>
                <span className="rubric-val">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
