import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Mail,
  Calendar,
  Briefcase,
  FileText,
  CheckCircle2,
  ArrowRight,
  Compass,
  Video,
  Target,
} from 'lucide-react';
import { Candidate } from '../../types';
import { useAppSession } from '../../context/AppSessionContext';

interface ProfileDossierWorkspaceProps {
  candidates: Candidate[];
  selectedCandidate: Candidate | null;
  onSelectCandidate: (candidate: Candidate) => void;
  onRefreshCandidates: () => Promise<void>;
  onNavigateToResume: () => void;
}

export const ProfileDossierWorkspace: React.FC<ProfileDossierWorkspaceProps> = ({
  selectedCandidate,
  onNavigateToResume,
}) => {
  const navigate = useNavigate();
  const { activeRoleId } = useAppSession();

  // If no candidate exists, show clean candidate onboarding
  if (!selectedCandidate) {
    return (
      <div className="page-container">
        <div className="surface-card p-6 text-center max-w-lg mx-auto my-8">
          <div className="w-10 h-10 rounded bg-surface-raised border border-subtle text-indigo flex items-center justify-center mx-auto mb-3">
            <User size={20} />
          </div>
          <h2 className="text-base font-bold text-primary mb-1.5">
            Candidate Profile Required
          </h2>
          <p className="text-xs text-secondary leading-relaxed mb-4">
            Please authenticate to view and manage your candidate profile dossier, verified resume claims, and learning roadmaps.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/overview')}
          >
            Authenticate Profile
          </button>
        </div>
      </div>
    );
  }

  const activeResume = selectedCandidate.resumes?.find((r) => r.is_active) || selectedCandidate.resumes?.[0];
  const hasResume = Boolean(activeResume);
  const initials = selectedCandidate.full_name
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <div className="page-container" data-testid="profile-page">
      {/* Page Header */}
      <div className="page-header-row mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="page-main-heading">My Profile & Experience</h1>
            <span className="sr-only">Candidate Registry & Memory Index</span>
          </div>
          <p className="page-subheading">
            Your technical background, parsed resume experience, and interview readiness.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onNavigateToResume}
          >
            <FileText size={14} />
            <span>{hasResume ? 'Manage Resume' : 'Upload Resume'}</span>
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/roles')}
          >
            <Briefcase size={14} />
            <span>Select Target Role</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Hero Profile Banner */}
      <div className="surface-card mb-4">
        <div className="surface-body p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded bg-surface-raised border border-subtle text-primary flex items-center justify-center font-bold text-sm shrink-0">
              {initials || <User size={20} />}
            </div>

            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg font-bold text-primary tracking-tight">{selectedCandidate.full_name}</h2>
                <span className="badge badge-brand text-[10px]">Verified Candidate</span>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-secondary mt-0.5">
                <span className="flex items-center gap-1.5">
                  <Mail size={13} className="text-muted" />
                  <span>{selectedCandidate.email}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <Calendar size={13} className="text-muted" />
                  <span>Member since {new Date(selectedCandidate.created_at).toLocaleDateString()}</span>
                </span>
                {selectedCandidate.total_years_exp > 0 && (
                  <span className="flex items-center gap-1.5">
                    <Briefcase size={13} className="text-muted" />
                    <span>{selectedCandidate.total_years_exp} Years Industry Experience</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto">
            <div className="p-3 bg-surface rounded-lg border border-subtle text-center min-w-[140px]">
              <span className="text-xs text-muted block">Target Transfer Goal</span>
              <strong className="text-sm font-semibold text-indigo flex items-center justify-center gap-1 mt-0.5">
                <Target size={14} />
                <span>L5 Independent</span>
              </strong>
            </div>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigate('/interview')}
            >
              <Video size={16} />
              <span>Start Planned Interview</span>
            </button>
          </div>
        </div>
      </div>

      {/* Two Main Columns: Resume Grounding & Assessment Competency Alignment */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Left: Verified Technical Facts & Resume Grounding */}
        <div className="surface-card flex flex-col">
          <div className="surface-header">
            <div className="surface-header-title">
              <FileText size={18} className="text-indigo" />
              <h2>Resume & Technical Experience</h2>
            </div>
            {hasResume ? (
              <span className="badge badge-success flex items-center gap-1">
                <CheckCircle2 size={12} />
                <span>Resume Active & Parsed</span>
              </span>
            ) : (
              <span className="badge badge-neutral">No Resume Uploaded</span>
            )}
          </div>

          <div className="surface-body flex-1 flex flex-col justify-between p-5 gap-4">
            <div>
              {hasResume ? (
                <div className="mb-4 p-3 bg-surface-raised rounded-md border border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText size={20} className="text-indigo" />
                    <div>
                      <div className="text-sm font-semibold text-primary">{activeResume?.file_name}</div>
                      <div className="text-xs text-muted">
                        Active Resume • {Math.round((activeResume?.file_size_bytes || 0) / 1024)} KB
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm text-xs"
                    onClick={onNavigateToResume}
                  >
                    Inspect Claims
                  </button>
                </div>
              ) : (
                <div className="mb-4 p-4 bg-surface-raised rounded-md border border-dashed border-subtle text-center">
                  <p className="text-xs text-secondary mb-2">
                    Upload your resume to enable verified claim probing and custom competency blueprints.
                  </p>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={onNavigateToResume}
                  >
                    Upload Resume PDF
                  </button>
                </div>
              )}

              <div className="text-xs uppercase font-bold text-muted mb-2 tracking-wider">
                Extracted Competencies & Technical Skills
              </div>

              {selectedCandidate.skills_summary && selectedCandidate.skills_summary.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {selectedCandidate.skills_summary.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-surface-raised border border-subtle text-primary rounded-full text-xs font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-secondary italic">
                  No verified skills extracted yet. Resume upload will parse skills automatically.
                </p>
              )}
            </div>

            <div className="pt-3 border-t border-subtle flex items-center justify-between text-xs text-secondary">
              <span>Grounding status: <strong>{hasResume ? 'Verifiable claims indexed' : 'Awaiting resume upload'}</strong></span>
              <button
                type="button"
                className="text-indigo hover:underline flex items-center gap-1 font-medium"
                onClick={onNavigateToResume}
              >
                <span>View Full Extraction</span>
                <ArrowRight size={12} />
              </button>
            </div>
          </div>
        </div>

        {/* Right: Target Role & Competency Alignment */}
        <div className="surface-card flex flex-col">
          <div className="surface-header">
            <div className="surface-header-title">
              <Briefcase size={18} className="text-indigo" />
              <h2>Target Role & Learning Alignment</h2>
            </div>
            <span className="badge badge-brand">Assessment Blueprint</span>
          </div>

          <div className="surface-body flex-1 flex flex-col justify-between p-5 gap-4">
            <div>
              <p className="text-xs text-secondary leading-relaxed mb-4">
                Your interview gauntlet, cognitive difficulty, and unseen transfer challenges are synthesized to meet Staff Engineer benchmarks for your chosen role.
              </p>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 bg-surface-raised rounded-md border border-subtle">
                  <span className="text-xs text-muted block mb-1">Target Role</span>
                  <strong className="text-sm text-primary block truncate">{activeRoleId || 'Distributed Systems Engineer'}</strong>
                  <button
                    type="button"
                    className="text-xs text-indigo mt-1 hover:underline block font-medium"
                    onClick={() => navigate('/roles')}
                  >
                    Change Role &rarr;
                  </button>
                </div>
                <div className="p-3 bg-surface-raised rounded-md border border-subtle">
                  <span className="text-xs text-muted block mb-1">Learning Stage</span>
                  <strong className="text-sm text-emerald block">Active Tutoring</strong>
                  <button
                    type="button"
                    className="text-xs text-indigo mt-1 hover:underline block font-medium"
                    onClick={() => navigate('/coaching')}
                  >
                    Open Studio &rarr;
                  </button>
                </div>
              </div>

              <div
                className="p-3.5 rounded-sm border leading-relaxed bg-surface-raised border-subtle"
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-primary mb-1">
                  <Compass size={14} className="text-secondary" />
                  <span>Next Recommended Milestone</span>
                </div>
                <p className="text-xs text-secondary leading-relaxed">
                  Complete your planned diagnostic interview or practice the <strong className="text-primary">API Idempotency & Concurrency</strong> transfer challenge to advance your verified transfer level.
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-subtle flex items-center justify-between">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => navigate('/roadmap')}
              >
                <span>View Growth Roadmap</span>
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => navigate('/coaching')}
              >
                <span>Enter AI Studio</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

