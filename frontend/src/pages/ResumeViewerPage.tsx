import React, { useState, useEffect } from 'react';
import { Candidate, CandidateProfile, CandidateClaim } from '../types';
import { api } from '../services/api';
import {
  Upload,
  FileText,
  Cpu,
  Briefcase,
  GraduationCap,
  Search,
  Play,
  ShieldCheck,
  Globe,
  RefreshCw,
  BookOpen,
  Code2,
  MapPin,
  Phone,
  Mail,
  Award,
} from 'lucide-react';

interface ResumeViewerPageProps {
  selectedCandidate: Candidate | null;
  onRefreshCandidate: () => Promise<void>;
  onStartInterview: (role?: string) => void;
}

export const ResumeViewerPage: React.FC<ResumeViewerPageProps> = ({
  selectedCandidate,
  onRefreshCandidate,
  onStartInterview,
}) => {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [claims, setClaims] = useState<CandidateClaim[]>([]);
  const [dossier, setDossier] = useState<any>(null);
  const [loadingDossier, setLoadingDossier] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // RAG Search State
  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState<any[]>([]);
  const [ragLoading, setRagLoading] = useState(false);

  useEffect(() => {
    // 1. Immediately wipe previous candidate's resume/claim/dossier data to prevent bleed
    setProfile(null);
    setClaims([]);
    setDossier(null);
    setRagQuery('');
    setRagResults([]);
    setUploadError(null);
    setUploadSuccess(null);

    if (selectedCandidate) {
      loadProfileAndClaims(selectedCandidate.id);
    }
  }, [selectedCandidate?.id]);

  const loadProfileAndClaims = async (candId: string) => {
    setLoadingProfile(true);
    try {
      const data = await api.getCandidateProfile(candId);
      setProfile(data);
      if (data?.personalized_dossier) {
        setDossier(data.personalized_dossier);
      } else {
        try {
          const d = await api.getCandidateDossier(candId);
          setDossier(d);
        } catch {
          // Non-blocking dossier fetch
        }
      }

      const loadedClaims = await api.getCandidateClaims(candId);
      if (loadedClaims && loadedClaims.length > 0) {
        setClaims(loadedClaims);
      } else if (data?.skills) {
        // Synthesize verifiable atomic claims from extracted entities
        const synthesized: CandidateClaim[] = data.skills.map((s, idx) => ({
          id: `claim-${idx + 1}`,
          candidate_id: candId,
          skill_name: s.name,
          claim_text: `Asserts ${s.proficiency || 'demonstrated'} proficiency in ${s.name} on profile.`,
          complexity: idx > 3 ? 'ADVANCED' : 'INTERMEDIATE',
          verification_status: 'UNVERIFIED',
          confidence_score: 0.5,
          verified_quotes: [],
          probe_count: 0,
        }));
        setClaims(synthesized);
      }
    } catch {
      setProfile(null);
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleRefreshDossier = async () => {
    if (!selectedCandidate) return;
    setLoadingDossier(true);
    try {
      const freshDossier = await api.getCandidateDossier(selectedCandidate.id, true);
      setDossier(freshDossier);
    } catch (e: any) {
      console.error('Failed to refresh dossier:', e);
    } finally {
      setLoadingDossier(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !selectedCandidate) return;

    const file = files[0];
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      await api.uploadResume(selectedCandidate.id, file);
      setUploadSuccess(`Resume '${file.name}' parsed, vectorized, and decomposed into atomic claims successfully!`);
      await onRefreshCandidate();
      await loadProfileAndClaims(selectedCandidate.id);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to parse resume.');
    } finally {
      setUploading(false);
    }
  };

  const handleRagSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ragQuery.trim() || !selectedCandidate) return;
    setRagLoading(true);
    try {
      const res = await api.queryResumeRAG(selectedCandidate.id, ragQuery.trim(), 3);
      setRagResults(res.results || []);
    } catch (err: any) {
      alert(`RAG query error: ${err.message}`);
    } finally {
      setRagLoading(false);
    }
  };

  if (!selectedCandidate) {
    return (
      <div className="empty-state-card fade-in">
        <FileText size={44} className="empty-state-icon" />
        <h3>No Candidate Profile Selected</h3>
        <p>Select a candidate from the top navbar or create a new profile.</p>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Studio Header */}
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Resume Intelligence & Claim Decomposition</h2>
            <p className="page-subtitle">
              Structured Entity Extraction & Verifiable Atomic Claims for <strong style={{ color: '#fff' }}>{profile?.full_name || selectedCandidate.full_name}</strong>
            </p>
          </div>

          {profile && (
            <button type="button" className="btn btn-primary" onClick={() => onStartInterview()}>
              <Play size={14} /> Launch Interview Command Center
            </button>
          )}
        </div>
      </div>

      {uploadError && (
        <div className="alert alert-danger" role="alert">
          {uploadError}
        </div>
      )}

      {uploadSuccess && (
        <div className="alert alert-success" role="status">
          {uploadSuccess}
        </div>
      )}

      {/* Upload Zone */}
      <div className="resume-upload-card" onClick={() => document.getElementById('resume-file-input')?.click()} role="button" tabIndex={0}>
        <input
          id="resume-file-input"
          type="file"
          accept=".pdf,.docx,.doc,.txt"
          className="hidden-file-input"
          onChange={handleFileUpload}
          disabled={uploading}
        />
        <Upload size={32} className="resume-upload-icon" />
        <h3 className="section-title" style={{ justifyContent: 'center' }}>
          {uploading ? 'Decomposing Resume & Generating Vector Embeddings...' : 'Upload Candidate Resume (PDF, DOCX, TXT)'}
        </h3>
        <p style={{ fontSize: '0.825rem', marginTop: '4px' }}>
          Extracts skills, work history, projects, and registers atomic claims for adversarial interview verification.
        </p>
      </div>

      {loadingProfile ? (
        <div className="empty-state-card">
          <p style={{ color: 'var(--text-muted)' }}>Loading extracted resume intelligence & atomic claim nodes...</p>
        </div>
      ) : profile ? (
        <div className="grid-2">
          {/* Left Column: Parsed Entities */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Universal Omnirole Launch Card */}
            <div className="studio-panel" style={{ border: '1px solid var(--border-card, #2d3b52)', background: 'var(--surface-card, #162032)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldCheck size={16} color="var(--accent-primary)" />
                  <h3 style={{ fontSize: '0.95rem' }}>Universal Interview Readiness</h3>
                </div>
                <span className="inquisitor-status-pill pill-active" style={{ fontSize: '0.65rem' }}>
                  OMNIROLE ACTIVE
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: '14px', lineHeight: '1.4' }}>
                Test cross-company engineering readiness across system design, algorithmic problem solving, and verified resume claims.
              </p>
              <button
                className="btn btn-primary"
                style={{ width: '100%', fontSize: '0.85rem', padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                onClick={() => onStartInterview()}
              >
                <Play size={14} /> Launch Adaptive Omnirole Interview
              </button>

              {profile.recommended_roles && profile.recommended_roles.length > 0 && (
                <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'block', marginBottom: '6px' }}>
                    Or focus on a specific company track (optional):
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {profile.recommended_roles.map((r, idx) => (
                      <button
                        key={idx}
                        className="btn btn-secondary"
                        style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                        onClick={() => onStartInterview(r)}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Overview */}
            <div className="studio-panel">
              <div className="studio-panel-header">
                <div className="studio-panel-title">
                  <Cpu size={15} color="#818cf8" />
                  <span>Candidate Profile Overview</span>
                </div>
                {profile.seniority_level && (
                  <span style={{ fontSize: '0.72rem', background: 'rgba(99, 102, 241, 0.15)', color: '#a5b4fc', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
                    {profile.seniority_level}
                  </span>
                )}
              </div>

              {/* Candidate Full Name */}
              <div style={{ marginBottom: '10px' }}>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', letterSpacing: '-0.01em' }}>
                  {profile.full_name || selectedCandidate.full_name}
                </h3>
              </div>

              {/* Metadata Badges (Location, Phone, Email) */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '12px', fontSize: '0.78rem', color: '#94a3b8' }}>
                {profile.location && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(255,255,255,0.04)', padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <MapPin size={12} color="#38bdf8" /> {profile.location}
                  </span>
                )}
                {profile.email && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(255,255,255,0.04)', padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <Mail size={12} color="#a5b4fc" /> {profile.email}
                  </span>
                )}
                {profile.phone && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(255,255,255,0.04)', padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <Phone size={12} color="#34d399" /> {profile.phone}
                  </span>
                )}
              </div>

              <p style={{ fontSize: '0.875rem', lineHeight: '1.6', marginBottom: '14px', color: '#e2e8f0' }}>
                {profile.summary || 'Professional candidate summary.'}
              </p>

              {/* Functional Domains & Areas of Interest */}
              {profile.domains && profile.domains.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)', display: 'block', marginBottom: '6px', fontWeight: 600 }}>
                    DOMAINS & AREAS OF INTEREST
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {profile.domains.map((d, i) => (
                      <span key={i} className="concept-tag" style={{ fontSize: '0.72rem' }}>
                        {d}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Soft Skills & Languages & Strengths */}
              {profile.soft_skills && profile.soft_skills.length > 0 && (
                <div>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)', display: 'block', marginBottom: '6px', fontWeight: 600 }}>
                    LANGUAGES & KEY STRENGTHS
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {profile.soft_skills.map((s, i) => (
                      <span key={i} style={{ fontSize: '0.72rem', background: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '2px 8px', borderRadius: '4px' }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Autonomous Web-Researched AI Coach Syllabus */}
            <div className="studio-panel" style={{ border: '1px solid rgba(56, 189, 248, 0.25)', background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.05), var(--bg-card))' }}>
              <div className="studio-panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div className="studio-panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Globe size={16} color="#38bdf8" />
                  <span style={{ color: '#fff', fontWeight: 600 }}>Personalized AI Coach Syllabus (Live Web Researched)</span>
                </div>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '0.72rem', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  onClick={handleRefreshDossier}
                  disabled={loadingDossier}
                >
                  <RefreshCw size={12} className={loadingDossier ? 'spin-anim' : ''} />
                  {loadingDossier ? 'Researching...' : 'Re-Search Web'}
                </button>
              </div>

              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '12px', lineHeight: '1.4' }}>
                The AI Coach dynamically queries live technical web sources (Wikipedia & DuckDuckGo) for this candidate's specific skills, establishing a custom 5-stage interview curriculum.
              </p>

              {dossier?.researched_skills && dossier.researched_skills.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '14px' }}>
                  {dossier.researched_skills.map((s: any, idx: number) => (
                    <div key={idx} style={{ background: 'var(--bg-surface)', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, color: '#38bdf8', fontSize: '0.85rem' }}>
                          {s.skill_name} <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem', fontWeight: 400 }}>({s.formal_title})</span>
                        </span>
                        <span style={{ fontSize: '0.675rem', color: '#a5b4fc', background: 'rgba(99, 102, 241, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                          Live Researched
                        </span>
                      </div>
                      <p style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.4', marginBottom: '6px' }}>
                        {s.web_summary}
                      </p>
                      {s.core_principles && s.core_principles.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {s.core_principles.map((cp: string, cidx: number) => (
                            <span key={cidx} style={{ fontSize: '0.7rem', background: 'rgba(255,255,255,0.05)', color: '#94a3b8', padding: '1px 6px', borderRadius: '3px' }}>
                              • {cp}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                  {loadingDossier ? 'Conducting live web research across candidate skills...' : 'Click "Re-Search Web" to synthesize live skills.'}
                </div>
              )}

              {/* Custom 5-Stage Curriculum Breakdown */}
              {dossier?.custom_curriculum && dossier.custom_curriculum.length > 0 && (
                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#fff', fontWeight: 600, marginBottom: '8px' }}>
                    <BookOpen size={13} color="#a5b4fc" />
                    <span>Candidate's Tailored 5-Stage Interview Syllabus</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {dossier.custom_curriculum.map((stg: any, sIdx: number) => (
                      <div key={sIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.75rem', background: 'rgba(0,0,0,0.2)', padding: '6px 8px', borderRadius: '4px' }}>
                        <span style={{ color: '#38bdf8', fontWeight: 700, minWidth: '55px' }}>
                          Stage {stg.stage_index}:
                        </span>
                        <div>
                          <strong style={{ color: '#e2e8f0' }}>{stg.stage_name}</strong>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                            Focus: <span style={{ color: '#a5b4fc' }}>{stg.focus_skill}</span> &middot; {stg.pedagogical_goal}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Projects & Practical Initiatives */}
            {profile.projects && profile.projects.length > 0 && (
              <div className="studio-panel">
                <div className="studio-panel-header">
                  <div className="studio-panel-title">
                    <Code2 size={15} color="#10b981" />
                    <span>Projects & Practical Initiatives ({profile.projects.length})</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {profile.projects.map((proj, i) => (
                    <div key={i} style={{ padding: '12px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                        <strong style={{ color: '#fff', fontSize: '0.9rem' }}>{proj.title}</strong>
                        {proj.project_url && (
                          <a href={proj.project_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem', color: 'var(--accent-primary)' }}>
                            View Repo
                          </a>
                        )}
                      </div>
                      <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.4', marginBottom: '8px' }}>
                        {proj.description}
                      </p>
                      {proj.technologies_used && proj.technologies_used.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '6px' }}>
                          {proj.technologies_used.map((tech, tidx) => (
                            <span key={tidx} style={{ fontSize: '0.7rem', background: 'rgba(16, 185, 129, 0.1)', color: '#6ee7b7', padding: '1px 6px', borderRadius: '3px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                              {tech}
                            </span>
                          ))}
                        </div>
                      )}
                      {proj.key_achievements && proj.key_achievements.length > 0 && (
                        <ul style={{ paddingLeft: '16px', marginTop: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {proj.key_achievements.map((ach, aidx) => (
                            <li key={aidx}>{ach}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Work History */}
            <div className="studio-panel">
              <div className="studio-panel-header">
                <div className="studio-panel-title">
                  <Briefcase size={15} color="#fbbf24" />
                  <span>Experience Assertions ({profile.experience.length})</span>
                </div>
              </div>
              {profile.experience.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {profile.experience.map((exp, i) => (
                    <div key={i} style={{ padding: '12px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <strong style={{ color: '#fff', fontSize: '0.9rem' }}>{exp.designation}</strong>
                        <span style={{ fontSize: '0.725rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                          {exp.start_date} - {exp.end_date || 'Present'}
                        </span>
                      </div>
                      <div style={{ color: 'var(--accent-primary)', fontSize: '0.8rem', marginTop: '2px' }}>
                        {exp.company_name}
                      </div>
                      {exp.responsibilities?.length > 0 && (
                        <ul style={{ paddingLeft: '16px', marginTop: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {exp.responsibilities.slice(0, 3).map((r, idx) => (
                            <li key={idx} style={{ marginBottom: '3px' }}>{r}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                  Fresher / Academic Track: No corporate employment history listed. Evaluation will focus on projects, fundamental mechanics, and algorithmic problem solving.
                </p>
              )}
            </div>

            {/* Education */}
            <div className="studio-panel">
              <div className="studio-panel-header">
                <div className="studio-panel-title">
                  <GraduationCap size={15} color="#ec4899" />
                  <span>Education Grounding ({profile.education.length})</span>
                </div>
              </div>
              {profile.education.map((edu, i) => (
                <div key={i} style={{ padding: '10px 12px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.875rem' }}>{edu.degree} in {edu.field_of_study}</div>
                    {(edu.start_year || edu.end_year) && (
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                        {edu.start_year ? `${edu.start_year} - ` : ''}{edu.end_year || 'Present'}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{edu.institution}</div>
                </div>
              ))}
            </div>

            {/* Certifications & Achievements */}
            {((profile.certifications && profile.certifications.length > 0) || (profile.achievements && profile.achievements.length > 0)) && (
              <div className="studio-panel">
                <div className="studio-panel-header">
                  <div className="studio-panel-title">
                    <Award size={15} color="#f59e0b" />
                    <span>Certifications & Achievements</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {profile.certifications?.map((c, i) => (
                    <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem' }}>{c.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{c.issuing_organization || 'Certified'} {c.issue_date ? `• ${c.issue_date}` : ''}</div>
                    </div>
                  ))}
                  {profile.achievements?.map((a, i) => (
                    <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem' }}>{a.title}</div>
                      {a.description && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{a.description}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Decomposed Atomic Claims & Vector RAG */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Decomposed Atomic Claims */}
            <div className="studio-panel">
              <div className="studio-panel-header">
                <div className="studio-panel-title">
                  <ShieldCheck size={16} color="var(--status-verified)" />
                  <span>Decomposed Atomic Claims ({claims.length})</span>
                </div>
                <span style={{ fontSize: '0.725rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                  AWAITING INTERVIEW VERIFICATION
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '460px', overflowY: 'auto' }}>
                {claims.map((claim) => (
                  <div key={claim.id} className={`claim-item-card ${claim.verification_status.toLowerCase()}`}>
                    <div className="claim-header">
                      <span className="claim-skill-name">{claim.skill_name}</span>
                      <span className={`claim-status-badge badge-${claim.verification_status.toLowerCase()}`}>
                        {claim.verification_status}
                      </span>
                    </div>
                    <p className="claim-text-snippet">"{claim.claim_text}"</p>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.725rem', color: 'var(--text-dim)' }}>
                      <span>Complexity: {claim.complexity}</span>
                      <span>Confidence: {Math.round(claim.confidence_score * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Test Vector RAG Grounding */}
            <div className="studio-panel">
              <div className="studio-panel-header">
                <div className="studio-panel-title">
                  <Search size={15} color="#818cf8" />
                  <span>Test Vector RAG Grounding</span>
                </div>
              </div>
              <p style={{ fontSize: '0.8rem', marginBottom: '12px' }}>
                Query the underlying pgvector chunks used to ground adversarial questions in the candidate's exact background.
              </p>

              <form onSubmit={handleRagSearch} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Distributed database replication"
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                />
                <button type="submit" className="btn btn-secondary" disabled={ragLoading}>
                  {ragLoading ? 'Querying...' : 'Query'}
                </button>
              </form>

              {ragResults.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {ragResults.map((res, i) => (
                    <div key={i} style={{ padding: '8px 10px', background: 'var(--bg-surface)', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: '0.675rem', color: '#818cf8', fontFamily: 'var(--font-mono)' }}>SECTION: {res.section_name}</span>
                      <p style={{ fontSize: '0.8rem', color: '#e2e8f0', marginTop: '2px' }}>{res.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Guided Stepper Next Step Banner */}
          <div
            className="studio-panel fade-in"
            style={{
              marginTop: '24px',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.08) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
              padding: '20px 24px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span className="inquisitor-status-pill pill-active" style={{ fontSize: '0.7rem' }}>
                  STEP 2 VERIFIED
                </span>
                <h4 style={{ fontSize: '1rem', color: '#fff' }}>Resume Claims Decomposed & Vector Grounded</h4>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Evidence is ready to feed multi-stage adversarial probes in the live interview.
              </p>
            </div>

            <button
              className="btn btn-primary"
              style={{ padding: '10px 22px', fontSize: '0.95rem', fontWeight: 600 }}
              onClick={() => onStartInterview(profile?.recommended_roles?.[0] || undefined)}
            >
              <Play size={16} />
              <span>Launch Step 3: Adaptive Studio</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="studio-panel" style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-dim)' }}>
          <h3>No Resume Intelligence Available</h3>
          <p style={{ marginTop: '6px' }}>Upload a resume file above to extract entities, vector chunks, and atomic claims.</p>
        </div>
      )}
    </div>
  );
};
