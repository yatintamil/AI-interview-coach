import React from 'react';
import { Lightbulb, HelpCircle } from 'lucide-react';
import { StructuredUIPayload } from '../../../types';

interface SocraticHintCardProps {
  payload: StructuredUIPayload;
}

export const SocraticHintCard: React.FC<SocraticHintCardProps> = ({ payload }) => {
  const scaffoldLevel = payload.scaffold_level || 'MEDIUM';
  const guidingQuestion = payload.guiding_question || payload.hint || 'How does this invariant preserve consistency across boundary cases?';

  return (
    <div className="structured-card socratic-hint-card" data-testid="socratic-hint-card">
      <div className="card-header-badge">
        <span className="badge badge-hint">
          <Lightbulb size={13} className="badge-icon" />
          <span>Socratic Guidance</span>
        </span>
        <span className="badge badge-subtle">Scaffold: {scaffoldLevel}</span>
      </div>

      <div className="socratic-question-box">
        <HelpCircle size={16} className="question-box-icon" />
        <p className="guiding-question-text">{guidingQuestion}</p>
      </div>

      <div className="socratic-footer-tip">
        Reflect on this question and attempt to explain the boundary behavior in your next turn.
      </div>
    </div>
  );
};
