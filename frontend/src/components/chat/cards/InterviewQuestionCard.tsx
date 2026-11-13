import React from 'react';
import { HelpCircle, ArrowRight, CheckCircle2 } from 'lucide-react';
import { StructuredUIPayload } from '../../../types';
import { useNavigate } from 'react-router-dom';

interface InterviewQuestionCardProps {
  payload: StructuredUIPayload;
}

export const InterviewQuestionCard: React.FC<InterviewQuestionCardProps> = ({ payload }) => {
  const navigate = useNavigate();
  const role = payload.role || 'Software Engineering';
  const topic = payload.topic || 'System Design & Invariants';
  const invariants = Array.isArray(payload.expected_invariants) ? payload.expected_invariants : [];

  return (
    <div className="structured-card interview-question-card" data-testid="interview-question-card">
      <div className="card-header-badge">
        <span className="badge badge-accent">
          <HelpCircle size={13} className="badge-icon" />
          <span>Interview Problem</span>
        </span>
        <span className="badge badge-subtle">{role}</span>
      </div>

      <div className="card-topic-title">{topic}</div>

      {invariants.length > 0 && (
        <div className="card-invariants-section">
          <div className="invariants-label">Expected Core Invariants:</div>
          <div className="invariants-list">
            {invariants.map((inv, idx) => (
              <div key={idx} className="invariant-pill">
                <CheckCircle2 size={13} className="pill-icon text-success" />
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
          onClick={() => navigate('/interview')}
        >
          <span>Open in Interview Studio</span>
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
};
