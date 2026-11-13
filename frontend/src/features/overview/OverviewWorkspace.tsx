import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Video,
  ArrowRight,
  Compass,
  Briefcase,
} from 'lucide-react';
import { useAppSession } from '../../context/AppSessionContext';
import { api } from '../../services/api';
import { InterviewSession } from '../../types';
import { CandidateSkillStateDTO, formatTransferLevel } from '../../types/coaching';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { Avatar, AvatarFallback } from '../../components/ui/Avatar';

interface OverviewWorkspaceProps {
  onOpenNewCandidateModal: () => void;
}

export const OverviewWorkspace: React.FC<OverviewWorkspaceProps> = ({ onOpenNewCandidateModal }) => {
  const navigate = useNavigate();
  const {
    selectedCandidate,
    activeRoleId,
  } = useAppSession();

  const [recentInterviews, setRecentInterviews] = useState<InterviewSession[]>([]);
  const [skillStates, setSkillStates] = useState<CandidateSkillStateDTO[]>([]);

  useEffect(() => {
    if (!selectedCandidate) {
      setRecentInterviews([]);
      setSkillStates([]);
      return;
    }

    let isMounted = true;
    Promise.allSettled([
      api.listCandidateInterviews(selectedCandidate.id),
      api.getCandidateSkillStates(selectedCandidate.id),
    ]).then(([interviewsRes, skillsRes]) => {
      if (!isMounted) return;

      if (interviewsRes.status === 'fulfilled') {
        const sorted = [...(interviewsRes.value || [])].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setRecentInterviews(sorted.slice(0, 5));
      } else {
        setRecentInterviews([]);
      }

      if (skillsRes.status === 'fulfilled') {
        setSkillStates(skillsRes.value || []);
      } else {
        setSkillStates([]);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [selectedCandidate?.id]);

  const hasResume = Boolean(
    selectedCandidate && selectedCandidate.resumes && selectedCandidate.resumes.length > 0
  );
  const isResumeProcessed = Boolean(
    hasResume && selectedCandidate?.resumes?.some((r) => r.processing_status === 'COMPLETED')
  );
  const targetRole = activeRoleId || selectedCandidate?.target_role || null;

  // 1. Onboarding Zero-State if no candidate is selected or candidates list is empty
  if (!selectedCandidate) {
    return (
      <div className="page-container" data-testid="onboarding-welcome-view" style={{ maxWidth: '960px', margin: '0 auto', padding: '32px 16px' }}>
        <div
          className="surface-card"
          style={{
            padding: '40px 32px',
            textAlign: 'center',
            marginBottom: '28px',
          }}
        >
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 12px',
              borderRadius: '4px',
              backgroundColor: 'rgba(37, 99, 235, 0.12)',
              border: '1px solid rgba(37, 99, 235, 0.3)',
              color: '#93c5fd',
              fontSize: '0.75rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              marginBottom: '16px',
            }}
          >
            <span>Candidate Learning System</span>
          </div>

          <h1
            style={{
              fontSize: '2rem',
              fontWeight: 800,
              color: '#f8fafc',
              letterSpacing: '-0.025em',
              margin: '0 0 12px 0',
              lineHeight: 1.25,
            }}
          >
            Welcome to AI Interview Coach
          </h1>

          <p
            style={{
              fontSize: '0.95rem',
              color: '#94a3b8',
              lineHeight: 1.6,
              maxWidth: '640px',
              margin: '0 auto 28px',
            }}
          >
            An empirical interview preparation workspace designed to evaluate independent problem-solving
            capabilities across changing system invariants, progressing candidates toward{' '}
            <strong style={{ color: '#f8fafc' }}>L5 Independent Transfer</strong>.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <button
              type="button"
              className="btn btn-primary btn-lg"
              data-testid="welcome-create-profile-btn"
              onClick={onOpenNewCandidateModal}
            >
              <span>Authenticate Candidate Profile</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>

        {/* Structured 4-Stage Workflow Progression List */}
        <div className="surface-card p-5">
          <div className="text-xs font-bold uppercase tracking-wider text-muted mb-3">
            System Architecture & Evaluation Stages
          </div>
          <div className="flex flex-col gap-2">
            {[
              { step: '1', title: 'Ground Evidence', desc: 'Extract verifiable technical claims, project facts, and architectural invariants from your resume.' },
              { step: '2', title: 'Select Target Role', desc: 'Align assessment criteria to target engineering requirements and calibrated competency blueprints.' },
              { step: '3', title: 'Interview Studio', desc: 'Engage with adaptive technical gauntlets featuring real-time Socratic hint laddering.' },
              { step: '4', title: 'Independent Transfer', desc: 'Verify autonomous Staff-level problem-solving on unseen transfer challenges.' },
            ].map((stage) => (
              <div
                key={stage.step}
                className="p-3 bg-surface-raised border border-subtle rounded-md flex items-start gap-3"
              >
                <div
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '4px',
                    background: 'var(--brand-primary, #2563eb)',
                    color: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {stage.step}
                </div>
                <div>
                  <div className="text-sm font-semibold text-primary">{stage.title}</div>
                  <div className="text-xs text-muted mt-0.5">{stage.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Determine Primary Recommendation based on real evidence
  let whereAmI = '';
  let whatToDoNextTitle = '';
  let whatToDoNextDesc = '';
  let whyRecommended = '';
  let primaryActionLabel = '';
  let primaryActionRoute = '';

  if (!hasResume) {
    whereAmI = 'Step 1 of 5: Profile Grounding & Evidence Extraction';
    whatToDoNextTitle = 'Upload Your Engineering Resume';
    whatToDoNextDesc = 'Anchor your adaptive interview questions and socratic coaching in real architectural claims and project evidence.';
    whyRecommended = 'Adaptive probing requires verified candidate background to test verifiable technical invariants. Generic practice is available in the Role Catalog.';
    primaryActionLabel = 'Upload Resume';
    primaryActionRoute = '/resume';
  } else if (!isResumeProcessed) {
    whereAmI = 'Step 1 of 5: Resume Parsing & Evidence Extraction';
    whatToDoNextTitle = 'Processing Resume & Grounding Claims';
    whatToDoNextDesc = 'Your resume is currently being analyzed to extract verifiable skills, experience, and project invariants without fabrication.';
    whyRecommended = 'Candidate profile and evidence graphs unlock immediately once parsing is complete.';
    primaryActionLabel = 'View Parsing Status';
    primaryActionRoute = '/resume';
  } else if (!targetRole) {
    whereAmI = 'Step 2 of 5: Target Role Selection';
    whatToDoNextTitle = 'Select Your Target Engineering Role';
    whatToDoNextDesc = 'Choose your target role from AI-recommended matches or industry blueprints to configure your interview assessment plan.';
    whyRecommended = 'Interview questions, competency invariants, and learning milestones are calibrated specifically for your target role.';
    primaryActionLabel = 'Select Target Role';
    primaryActionRoute = '/roles';
  } else if (recentInterviews.length === 0) {
    whereAmI = 'Step 2 of 5: Baseline Technical Assessment';
    whatToDoNextTitle = `Take Your System-Planned Interview for ${targetRole}`;
    whatToDoNextDesc = 'Complete a multi-stage technical gauntlet to diagnose your conceptual depth, invariant reasoning, and personalized focus areas.';
    whyRecommended = `The autonomous planner has prepared a calibrated gauntlet for ${targetRole} to identify your real skill gaps.`;
    primaryActionLabel = 'Start Planned Assessment';
    primaryActionRoute = '/interview';
  } else {
    // Has completed an interview
    const latestInterview = recentInterviews[0];
    const weakSkill = skillStates.find((s) => s.mastery_estimate < 0.70) || skillStates[0];
    const rawSkillName = weakSkill ? weakSkill.skill_name : 'distributed_caching';
    const skillName = rawSkillName
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());

    whereAmI = `Step 3 of 5: Targeted Learning & Guided Practice (${targetRole})`;
    whatToDoNextTitle = `Master ${skillName} in AI Learning Studio`;
    whatToDoNextDesc = 'Learn core architectural invariants through proactive concept explanations, Staff Engineer worked examples, and socratic checks leading to an unseen transfer challenge.';
    whyRecommended = latestInterview.report?.final_score
      ? `Your recent assessment scored ${latestInterview.report.final_score.toFixed(1)}/10.0 with identified deficits in ${skillName}.`
      : `Your diagnostic assessment flagged ${skillName} for targeted remediation prior to independent transfer.`;
    primaryActionLabel = 'Enter AI Learning Studio';
    primaryActionRoute = '/coaching';
  }

  return (
    <div className="page-container" data-testid="overview-page">
      {/* Top Identity & Status Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8 pb-5 border-b border-subtle">
        <div className="flex items-center gap-4">
          <Avatar size="lg">
            <AvatarFallback>
              {selectedCandidate ? selectedCandidate.full_name.charAt(0).toUpperCase() : 'U'}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl font-bold text-primary tracking-tight">{selectedCandidate?.full_name}</h2>
              <Badge variant="accent">Target: {targetRole}</Badge>
            </div>
            <p className="text-xs text-secondary mt-1 flex items-center gap-2">
              <span>Goal: <strong className="text-primary font-semibold">L5 Independent Transfer</strong></span>
              <span style={{ opacity: 0.4 }}>&bull;</span>
              {!hasResume ? (
                <span className="text-amber font-medium">Resume Evidence Required (Unverified)</span>
              ) : !isResumeProcessed ? (
                <span className="text-indigo font-medium">Parsing Evidence</span>
              ) : (
                <span className="text-emerald font-medium">Verified Identity Grounded</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/profile')}
            icon={<User size={14} />}
          >
            My Profile
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/roles')}
            icon={<Briefcase size={14} />}
          >
            Target Roles
          </Button>
        </div>
      </div>

      {/* Primary 3-Question Recommendation Hero */}
      <Card className="mb-8">
        <CardHeader>
          <div className="flex items-center gap-2.5 mb-1">
            <Badge variant="accent">Current Stage</Badge>
            <span className="text-xs text-secondary font-medium">
              {whereAmI}
            </span>
          </div>
          <CardTitle className="text-2xl md:text-3xl">
            {whatToDoNextTitle}
          </CardTitle>
          <CardDescription className="text-sm md:text-base">
            {whatToDoNextDesc}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 rounded-sm border border-subtle bg-surface-raised flex items-start gap-3 text-xs leading-relaxed max-w-3xl">
            <Compass size={16} className="text-secondary shrink-0 mt-0.5" />
            <div>
              <strong className="text-primary font-semibold">Autonomous Planning Rationale: </strong>
              <span>{whyRecommended}</span>
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex flex-wrap items-center gap-4 justify-start">
          <Button
            variant="default"
            size="md"
            onClick={() => navigate(primaryActionRoute)}
            icon={<ArrowRight size={16} />}
            iconPosition="right"
          >
            {primaryActionLabel}
          </Button>

          {hasResume && recentInterviews.length > 0 && (
            <Button
              variant="outline"
              size="md"
              onClick={() => navigate('/roadmap')}
            >
              View Growth Roadmap
            </Button>
          )}
        </CardFooter>
      </Card>

      {/* Supporting Information: Recent Activity & Evidence-Backed Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Left: Recent Activity */}
        <div className="surface-card flex flex-col">
          <div className="surface-header">
            <div className="surface-header-title">
              <h2>Recent Assessment Activity</h2>
            </div>
            {recentInterviews.length > 0 && (
              <span className="badge badge-neutral">{recentInterviews.length} Sessions</span>
            )}
          </div>

          <div className="surface-body flex-1 p-5">
            {recentInterviews.length === 0 ? (
              <div className="text-center py-8 text-secondary">
                <Video size={28} className="mx-auto mb-2 text-muted" />
                <p className="text-xs mb-3">No completed interview sessions yet.</p>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => navigate('/interview')}
                >
                  Start Your First Interview
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {recentInterviews.map((sess) => (
                  <div
                    key={sess.id}
                    className="p-3 bg-surface-raised rounded-lg border border-subtle flex items-center justify-between hover:border-indigo/40 transition-colors cursor-pointer"
                    onClick={() => navigate(sess.status === 'COMPLETED' ? `/debrief/${sess.id}` : `/interview/${sess.id}`)}
                  >
                    <div>
                      <div className="text-xs font-semibold text-primary">{sess.target_role || 'Technical Interview'}</div>
                      <div className="text-xs text-muted mt-0.5">
                        {sess.difficulty_level} • {sess.interview_type} • {new Date(sess.created_at).toLocaleDateString()}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {sess.report?.final_score !== undefined && (
                        <span className="badge badge-brand text-xs font-bold">
                          {sess.report.final_score.toFixed(1)}/10
                        </span>
                      )}
                      <span className="text-xs text-indigo hover:underline flex items-center gap-1 font-medium">
                        <span>{sess.status === 'COMPLETED' ? 'View Debrief' : 'Resume'}</span>
                        <ArrowRight size={12} />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Evidence-Backed Competency States */}
        <div className="surface-card flex flex-col">
          <div className="surface-header">
            <div className="surface-header-title">
              <h2>Evidence-Backed Competencies</h2>
            </div>
            <Badge variant="outline">Transfer Mastery</Badge>
          </div>

          <div className="surface-body flex-1 p-5">
            {skillStates.length === 0 ? (
              <div className="text-center py-8 text-secondary">
                <p className="text-xs mb-3">
                  {!hasResume
                    ? 'Skill state is grounded strictly in your verified resume and evaluated interview performance. Upload your resume to begin.'
                    : !isResumeProcessed
                    ? 'Resume parsing in progress. Extracted competencies will appear once verified.'
                    : 'Skill state is generated when you answer questions in interviews and AI coaching.'}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(!hasResume || !isResumeProcessed ? '/resume' : '/coaching')}
                >
                  {!hasResume ? 'Upload Resume' : !isResumeProcessed ? 'Check Parsing' : 'Begin Coaching Session'}
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {skillStates.slice(0, 4).map((sk) => (
                  <div
                    key={sk.skill_name}
                    className="p-3 bg-surface-raised rounded-lg border border-subtle flex items-center justify-between"
                  >
                    <div>
                      <div className="text-sm font-semibold text-primary">
                        {sk.skill_name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </div>
                      <div className="text-xs text-muted mt-0.5">
                        Transfer Level: <strong className="text-primary">{formatTransferLevel(sk.highest_transfer_level)}</strong> • Assessed Attempts: {sk.total_attempts}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-2.5 py-1 rounded bg-surface border border-subtle text-secondary">
                        {Math.round(sk.mastery_estimate * 100)}% Evaluated
                      </span>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm text-xs text-indigo"
                        onClick={() => navigate('/coaching')}
                      >
                        Practice &rarr;
                      </button>
                    </div>
                  </div>
                ))}

                <div className="pt-2 text-right">
                  <button
                    type="button"
                    className="text-xs text-indigo font-medium hover:underline inline-flex items-center gap-1"
                    onClick={() => navigate('/roadmap')}
                  >
                    <span>Inspect all {skillStates.length} competencies on Growth Roadmap</span>
                    <ArrowRight size={12} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
