import React from 'react';
import { StructuredUIPayload } from '../../types';
import { InterviewQuestionCard } from './cards/InterviewQuestionCard';
import { TransferTaskCard } from './cards/TransferTaskCard';
import { SocraticHintCard } from './cards/SocraticHintCard';
import { RoadmapSummaryCard } from './cards/RoadmapSummaryCard';
import { SkillStatusCard } from './cards/SkillStatusCard';
import { EvaluationSummaryCard } from './cards/EvaluationSummaryCard';
import { CoachingLessonCard } from './cards/CoachingLessonCard';
import { StructuredCardFallback } from './cards/StructuredCardFallback';

interface StructuredResponseRendererProps {
  payload?: StructuredUIPayload | null;
}

export const StructuredResponseRenderer: React.FC<StructuredResponseRendererProps> = ({ payload }) => {
  if (!payload || !payload.type) {
    return null;
  }

  const type = payload.type.toUpperCase();

  switch (type) {
    case 'COACHING_LESSON':
    case 'LESSON':
    case 'TUTOR_LESSON':
      return <CoachingLessonCard payload={payload} />;

    case 'INTERVIEW_QUESTION':
      return <InterviewQuestionCard payload={payload} />;

    case 'TRANSFER_TASK':
      return <TransferTaskCard payload={payload} />;

    case 'SOCRATIC_HINT':
    case 'COACHING_INTERVENTION':
    case 'HINT':
      return <SocraticHintCard payload={payload} />;

    case 'ROADMAP_SUMMARY':
    case 'ROADMAP':
      return <RoadmapSummaryCard payload={payload} />;

    case 'SKILL_STATUS':
    case 'SKILL_GAP':
      return <SkillStatusCard payload={payload} />;

    case 'EVALUATION_SUMMARY':
    case 'EVALUATION':
      return <EvaluationSummaryCard payload={payload} />;

    default:
      return <StructuredCardFallback payload={payload} />;
  }
};
