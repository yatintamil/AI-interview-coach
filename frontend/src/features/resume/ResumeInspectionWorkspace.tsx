import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Upload,
  CheckCircle,
  AlertCircle,
  Video,
  GraduationCap,
  Briefcase,
  Code2,
  RefreshCw,
  Layers,
  ArrowRight,
  ShieldCheck,
  Quote,
  Info,
} from 'lucide-react';
import { useAppSession } from '../../context/AppSessionContext';
import { api } from '../../services/api';
import { CandidateProfile, CandidateClaim } from '../../types';

interface ResumeInspectionWorkspaceProps {
  onStartInterview?: (role?: string) => void;
}

export const ResumeInspectionWorkspace: React.FC<ResumeInspectionWorkspaceProps> = ({
  onStartInterview,
}) => {
  const navigate = useNavigate();
  const { selectedCandidate, refreshCandidates, activeRoleId, setActiveRoleId } = useAppSession();

  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [claims, setClaims] = useState<CandidateClaim[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadResumeData = async (candId: string) => {
    setIsLoading(true);
    try {
      const [profData, claimsData] = await Promise.all([
        api.getCandidateProfile(candId).catch(() => null),
        api.getCandidateClaims(candId).catch(() => []),
      ]);
      setProfile(profData);
      setClaims(claimsData || []);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedCandidate) {
      loadResumeData(selectedCandidate.id);
    } else {
      setProfile(null);
      setClaims([]);
    }
  }, [selectedCandidate?.id]);

  const handleFileUpload = async (file: File) => {
    console.log('handleFileUpload called, file:', file.name, 'selectedCandidate:', selectedCandidate?.id);
    if (!selectedCandidate) {
      console.warn('handleFileUpload aborted: selectedCandidate is null/undefined!');
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      console.log('Calling api.uploadResume for candidate:', selectedCandidate.id);
      await api.uploadResume(selectedCandidate.id, file);
      console.log('api.uploadResume succeeded!');
      setUploadSuccess(`Resume "${file.name}" uploaded and parsed successfully.`);
      await refreshCandidates();
      await loadResumeData(selectedCandidate.id);
    } catch (err: any) {
      console.error('api.uploadResume failed:', err);
      setUploadError(err.message || 'Failed to upload and parse resume file');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  if (!selectedCandidate) {
    return (
      <div className="page-container">
        <div className="empty-state-frame">
          <div className="empty-state-icon">
            <FileText size={24} />
          </div>
          <h2 className="empty-state-heading">No Candidate Profile Active</h2>
          <p className="empty-state-copy">
            Please sign in to view and manage your resume and experience profile.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/profile')}
          >
            Go to My Profile
          </button>
        </div>
      </div>
    );
  }

  const hasResume = Boolean(selectedCandidate.resumes && selectedCandidate.resumes.length > 0);
  const latestResume = hasResume ? selectedCandidate.resumes[selectedCandidate.resumes.length - 1] : null;

  return (
    <div className="page-container" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Workspace Header */}
      <div className="page-header-row mb-3.5">
        <div>
          <h1 className="page-main-heading">
            Resume & Experience Profile
          </h1>
          <p className="page-subheading">
            Ground your adaptive interview questions, system design gauntlets, and coaching in your real engineering background.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn btn-secondary btn-xs"
            onClick={() => loadResumeData(selectedCandidate.id)}
            disabled={isLoading}
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-xs"
            onClick={() => navigate('/roles')}
          >
            <Briefcase size={13} />
            <span>Select Target Role</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-xs"
            onClick={() => {
              if (onStartInterview) {
                onStartInterview(activeRoleId || 'Distributed Systems Engineer');
              } else {
                if (activeRoleId) setActiveRoleId(activeRoleId);
                navigate('/interview');
              }
            }}
          >
            <Video size={13} />
            <span>Start Technical Interview</span>
          </button>
        </div>
      </div>

      {/* Honest Boundary Notice */}
      <div className="flex items-start gap-2.5 p-2.5 rounded border border-subtle bg-surface-raised mb-3.5">
        <Info size={15} className="text-indigo shrink-0 mt-0.5" />
        <div className="text-xs text-secondary leading-relaxed">
          <strong className="text-primary font-semibold">Evidence Grounding Protocol:</strong> Skills and experience shown below are extracted directly from your uploaded document as <em className="text-primary">self-reported candidate claims</em>. Technical interviews will probe these claims to verify hands-on competency against real architectural invariants.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
        {/* Left Column: Upload & Profile Summary */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Upload Card */}
          <div className="surface-card p-5 flex flex-col">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-subtle">
              <div className="flex items-center gap-2">
                <Upload size={18} className="text-indigo" />
                <h2 className="text-sm font-bold text-primary m-0">
                  Upload Candidate Resume
                </h2>
              </div>
              <span className="text-2xs text-muted">PDF, TXT, DOCX</span>
            </div>

            {hasResume && latestResume && (
              <div className="p-3 bg-surface-raised rounded-lg border border-subtle mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <FileText size={16} className="text-emerald shrink-0" />
                  <div>
                    <div className="text-xs font-semibold text-primary truncate max-w-[200px]">
                      {latestResume.file_name}
                    </div>
                    <div className="text-2xs text-muted">
                      Uploaded {new Date(latestResume.uploaded_at || latestResume.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <span className="badge badge-success text-2xs">
                  Active Document
                </span>
              </div>
            )}

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-subtle rounded-xl p-6 text-center cursor-pointer transition-all hover:border-indigo/50 hover:bg-surface-raised/40"
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                cursor: isUploading ? 'not-allowed' : 'pointer',
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                data-testid="resume-file-input"
                accept=".pdf,.txt,.docx"
                style={{ display: 'none' }}
                onChange={(e) => {
                  console.log('FileInput onChange triggered, files:', e.target.files?.length);
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
                disabled={isUploading}
              />
              <Upload size={28} className="text-muted mx-auto mb-2" />
              <div className="text-xs font-semibold text-primary mb-1">
                {isUploading ? 'Parsing document & extracting facts...' : 'Click to browse or drag & drop resume'}
              </div>
              <div className="text-2xs text-muted">
                Supports standard engineering resumes (PDF, TXT)
              </div>
            </div>

            {uploadError && (
              <div className="mt-3 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            {uploadSuccess && (
              <div className="mt-3 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
                <CheckCircle size={14} className="shrink-0" />
                <span>{uploadSuccess}</span>
              </div>
            )}
          </div>

          {/* Profile Summary Card */}
          {profile && (
            <div className="surface-card p-5">
              <h2 className="text-sm font-bold text-primary mb-3 pb-2 border-b border-subtle">
                Extracted Profile Overview
              </h2>

              {profile.summary && (
                <p className="text-xs text-secondary leading-relaxed mb-4">
                  {profile.summary}
                </p>
              )}

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 bg-surface-raised rounded-lg border border-subtle">
                  <div className="text-2xs text-muted uppercase font-semibold">
                    Experience
                  </div>
                  <div className="text-sm font-bold text-primary mt-1">
                    {profile.total_years_exp ? `${profile.total_years_exp} Years` : 'Document Grounded'}
                  </div>
                </div>

                <div className="p-3 bg-surface-raised rounded-lg border border-subtle">
                  <div className="text-2xs text-muted uppercase font-semibold">
                    Verified Claims
                  </div>
                  <div className="text-sm font-bold text-indigo mt-1">
                    {claims.length} Extracted
                  </div>
                </div>
              </div>

              {/* Education */}
              {profile.education && profile.education.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 text-2xs font-bold text-muted uppercase mb-2">
                    <GraduationCap size={13} />
                    <span>Education</span>
                  </div>
                  <div className="flex flex-col gap-2">
                    {profile.education.map((edu, i) => (
                      <div key={i} className="text-xs text-secondary">
                        <span className="font-semibold text-primary">{edu.degree}</span> &mdash; {edu.institution} {edu.end_year ? `(${edu.end_year})` : ''}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Skills & Verifiable Claims with Supporting Quotes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Extracted Skills Card */}
          {profile && profile.skills && profile.skills.length > 0 && (
            <div className="surface-card p-5">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-subtle">
                <div className="flex items-center gap-2">
                  <Code2 size={18} className="text-indigo" />
                  <h2 className="text-sm font-bold text-primary m-0">
                    Extracted Technical Skills
                  </h2>
                </div>
                <span className="text-2xs text-muted">
                  {profile.skills.length} Skills Found
                </span>
              </div>

              <div className="flex flex-wrap gap-2">
                {profile.skills.map((skill, i) => (
                  <span
                    key={i}
                    className="text-xs font-medium px-2.5 py-1 rounded-md bg-surface-raised text-primary border border-subtle"
                  >
                    {skill.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Experience Claims & Evidence */}
          <div className="surface-card p-5">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-subtle">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-indigo" />
                <h2 className="text-sm font-bold text-primary m-0">
                  Document Claims & Supporting Evidence
                </h2>
              </div>
              <span className="badge badge-brand text-2xs">
                {claims.length} Claims
              </span>
            </div>

            {claims.length === 0 ? (
              <div className="text-center py-6 text-muted text-xs">
                <Layers size={24} className="mx-auto mb-2 opacity-50" />
                <p className="m-0">
                  Upload a resume to automatically extract verifiable engineering claims and project excerpts.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {claims.map((claim, idx) => {
                  const isVerified = claim.verification_status === 'VERIFIED';
                  const isProbed = claim.verification_status === 'PROBED';

                  return (
                    <div
                      key={idx}
                      className="p-3 bg-surface-raised rounded-lg border border-subtle"
                      data-testid={`claim-card-${idx}`}
                    >
                      <div className="flex justify-between items-start gap-2 mb-1.5">
                        <div className="text-xs font-semibold text-primary leading-snug">
                          {claim.claim_text}
                        </div>
                        <span
                          className={`text-2xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${
                            isVerified
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : isProbed
                              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                              : 'bg-surface text-muted border border-subtle'
                          }`}
                        >
                          {isVerified
                            ? 'Demonstrated in Interview'
                            : isProbed
                            ? 'Probed in Interview'
                            : 'Self-Reported on Resume'}
                        </span>
                      </div>

                      {claim.supporting_quote && (
                        <div className="flex items-start gap-2 mt-2 p-2 bg-surface rounded-md border border-subtle text-2xs text-secondary italic leading-relaxed">
                          <Quote size={12} className="text-muted shrink-0 mt-0.5" />
                          <span>&ldquo;{claim.supporting_quote}&rdquo;</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Next Actions Banner */}
      <div
        className="surface-card mt-7 p-6 flex flex-wrap items-center justify-between gap-4 border border-subtle"
        style={{
          background: 'linear-gradient(135deg, rgba(22, 30, 49, 0.7) 0%, rgba(17, 23, 38, 0.9) 100%)',
        }}
      >
        <div>
          <h3 className="text-sm font-bold text-primary mb-1">
            Ready for Technical Calibration?
          </h3>
          <p className="text-xs text-secondary m-0">
            Select your target engineering role or launch an autonomous interview planned against your experience.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => navigate('/roles')}
          >
            <span>Target Roles</span>
            <ArrowRight size={14} />
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/interview')}
          >
            <span>Start Technical Gauntlet</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
