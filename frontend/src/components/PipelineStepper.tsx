import React from 'react';
import { Candidate } from '../types';
import { User, FileText, Video, Award, Compass, Layers, BarChart2, CheckCircle2 } from 'lucide-react';
import { useAppSession, useSafeLocation, useSafeNavigate } from '../context/AppSessionContext';

interface PipelineStepperProps {
  selectedCandidate: Candidate | null;
  hasResume: boolean;
  hasClaims: boolean;
  completedSessionsCount?: number;
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  selectedCandidate,
  hasResume,
  hasClaims,
  completedSessionsCount = 0,
}) => {
  const location = useSafeLocation();
  const navigate = useSafeNavigate();
  const { interviewSessionId, coachingSessionId } = useAppSession();

  const pathname = location.pathname;

  const steps = [
    {
      id: 'profile',
      label: 'Candidate Identity',
      sublabel: selectedCandidate ? selectedCandidate.full_name : 'Select or Create',
      icon: User,
      route: '/profile',
      isCompleted: Boolean(selectedCandidate),
      isActive: pathname === '/profile' || pathname === '/',
      isClickable: true,
    },
    {
      id: 'resume',
      label: 'Resume & Claims',
      sublabel: hasClaims ? 'Claims Decomposed' : hasResume ? 'Resume Parsed' : 'Upload Resume',
      icon: FileText,
      route: '/resume',
      isCompleted: Boolean(selectedCandidate && (hasResume || hasClaims)),
      isActive: pathname.startsWith('/resume'),
      isClickable: Boolean(selectedCandidate),
    },
    {
      id: 'interview',
      label: 'Adaptive Studio',
      sublabel: completedSessionsCount > 0 ? `${completedSessionsCount} Rounds Done` : '5-Stage Live Gauntlet',
      icon: Video,
      route: interviewSessionId && interviewSessionId !== 'undefined' ? `/interview/${interviewSessionId}` : '/interview',
      isCompleted: completedSessionsCount > 0 || Boolean(interviewSessionId),
      isActive: pathname.startsWith('/interview'),
      isClickable: Boolean(selectedCandidate),
    },
    {
      id: 'debrief',
      label: 'Executive Debrief',
      sublabel: interviewSessionId ? 'Rubric Assessment' : 'Requires Round',
      icon: Award,
      route: interviewSessionId && interviewSessionId !== 'undefined' ? `/debrief/${interviewSessionId}` : '/debrief',
      isCompleted: completedSessionsCount > 0,
      isActive: pathname.startsWith('/debrief'),
      isClickable: Boolean(interviewSessionId && interviewSessionId !== 'undefined'),
    },
    {
      id: 'roadmap',
      label: 'Skill Gaps & Roadmap',
      sublabel: 'Role-Aware Milestones',
      icon: Compass,
      route: '/roadmap',
      isCompleted: false,
      isActive: pathname.startsWith('/roadmap'),
      isClickable: Boolean(selectedCandidate),
    },
    {
      id: 'coaching',
      label: 'AI Coaching Studio',
      sublabel: coachingSessionId ? 'Active Session' : 'Transfer & Scaffolding',
      icon: Layers,
      route: coachingSessionId && coachingSessionId !== 'undefined' ? `/coaching/${coachingSessionId}` : '/coaching',
      isCompleted: false,
      isActive: pathname.startsWith('/coaching'),
      isClickable: Boolean(coachingSessionId || selectedCandidate),
    },
    {
      id: 'analytics',
      label: 'Evidence Analytics',
      sublabel: completedSessionsCount > 0 ? 'Readiness Metrics' : 'Gaps & Readiness',
      icon: BarChart2,
      route: '/analytics',
      isCompleted: completedSessionsCount > 0,
      isActive: pathname.startsWith('/analytics'),
      isClickable: Boolean(selectedCandidate),
    },
  ];

  return (
    <div className="pipeline-stepper-container">
      <div className="pipeline-stepper-inner">
        {steps.map((step, idx) => {
          const Icon = step.icon;

          return (
            <React.Fragment key={step.id}>
              <div
                className={`pipeline-step-item ${step.isActive ? 'active' : ''} ${step.isCompleted ? 'completed' : ''} ${
                  !step.isClickable ? 'disabled' : ''
                }`}
                onClick={() => {
                  if (step.isClickable) {
                    navigate(step.route);
                  }
                }}
                role="button"
                tabIndex={step.isClickable ? 0 : -1}
                aria-disabled={!step.isClickable}
              >
                <div className="step-badge">
                  {step.isCompleted ? (
                    <CheckCircle2 size={16} className="completed-icon" />
                  ) : (
                    <span>{idx + 1}</span>
                  )}
                </div>

                <div className="step-info">
                  <div className="step-title-row">
                    <Icon size={14} className="step-type-icon" />
                    <span className="step-label">{step.label}</span>
                  </div>
                  <span className="step-sublabel">{step.sublabel}</span>
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div className={`step-connector ${steps[idx].isCompleted ? 'completed' : ''}`}>
                  <div className="connector-line" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
