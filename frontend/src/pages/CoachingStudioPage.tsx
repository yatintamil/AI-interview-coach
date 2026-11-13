import React from 'react';
import { Candidate } from '../types';
import {
  UnifiedCoachingWorkspace,
  AVAILABLE_COMPETENCIES,
  SUGGESTED_PROMPTS,
} from '../features/coaching/UnifiedCoachingWorkspace';

export interface CoachingStudioPageProps {
  selectedCandidate: Candidate | null;
  onNavigateToAnalytics?: () => void;
  initialMode?: 'conversation' | 'practice' | 'transfer';
  initialInterviewContext?: {
    interviewSessionId?: string;
    questionId?: string;
    skillId?: string;
  } | null;
  onClearInitialContext?: () => void;
}

export { AVAILABLE_COMPETENCIES, SUGGESTED_PROMPTS };

export const CoachingStudioPage: React.FC<CoachingStudioPageProps> = ({
  selectedCandidate,
  onNavigateToAnalytics,
  initialMode = 'practice',
  initialInterviewContext,
  onClearInitialContext,
}) => {
  return (
    <UnifiedCoachingWorkspace
      selectedCandidate={selectedCandidate}
      initialMode={initialMode}
      initialInterviewContext={initialInterviewContext}
      onClearInitialContext={onClearInitialContext}
      onNavigateToAnalytics={onNavigateToAnalytics}
    />
  );
};
