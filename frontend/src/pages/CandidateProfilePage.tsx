import React, { useState } from 'react';
import { Candidate } from '../types';
import { api } from '../services/api';
import { User, Mail, Plus, Trash2, CheckCircle, FileText, Upload } from 'lucide-react';

interface CandidateProfilePageProps {
  candidates: Candidate[];
  selectedCandidate: Candidate | null;
  onSelectCandidate: (candidate: Candidate) => void;
  onRefreshCandidates: () => Promise<void>;
  onNavigateToResume: () => void;
}

export const CandidateProfilePage: React.FC<CandidateProfilePageProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onRefreshCandidates,
  onNavigateToResume,
}) => {
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleCreateCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail || !newName) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const created = await api.createCandidate(newEmail, newName);
      await onRefreshCandidates();
      onSelectCandidate(created);
      setNewEmail('');
      setNewName('');
      setSuccessMsg(`Candidate profile for '${created.full_name}' created successfully.`);
    } catch (err: any) {
      setError(err.message || 'Failed to create candidate profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCandidate = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete candidate profile "${name}"?`)) return;
    setError(null);
    try {
      await api.deleteCandidate(id);
      await onRefreshCandidates();
      setSuccessMsg(`Deleted candidate profile "${name}".`);
    } catch (err: any) {
      setError(`Delete failed: ${err.message}`);
    }
  };

  const handleActivateResume = async (candId: string, resId: string) => {
    setError(null);
    try {
      await api.activateResume(candId, resId);
      await onRefreshCandidates();
      setSuccessMsg('Resume activated successfully.');
    } catch (err: any) {
      setError(`Activation failed: ${err.message}`);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2 className="page-title">Candidate Registry & Memory Index</h2>
        <p className="page-subtitle">
          Manage candidate identities, multi-resume attachments, and persistent cognitive profiles.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="alert alert-success" role="status">
          {successMsg}
        </div>
      )}

      <div className="grid-2">
        {/* Left Column: Create Profile & Directory */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="studio-panel">
            <div className="studio-panel-header">
              <div className="studio-panel-title">
                <Plus size={16} />
                <span>Register Candidate Profile</span>
              </div>
            </div>

            <form onSubmit={handleCreateCandidate}>
              <div className="form-group">
                <label className="form-label" htmlFor="new-candidate-name">Full Name</label>
                <input
                  id="new-candidate-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Elena Rostova"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="new-candidate-email">Corporate / Personal Email</label>
                <input
                  id="new-candidate-email"
                  type="email"
                  className="form-input"
                  placeholder="e.g. elena.rostova@domain.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                {loading ? 'Registering Identity...' : 'Create Candidate Profile'}
              </button>
            </form>
          </div>

          <div className="studio-panel">
            <div className="studio-panel-header">
              <div className="studio-panel-title">
                <User size={16} />
                <span>Candidate Directory ({candidates.length})</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {candidates.length === 0 ? (
                <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>No candidate profiles found.</p>
              ) : (
                candidates.map((c) => {
                  const isSelected = selectedCandidate?.id === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => onSelectCandidate(c)}
                      className={`candidate-item-row ${isSelected ? 'selected' : ''}`}
                    >
                      <div>
                        <div className="candidate-name">{c.full_name}</div>
                        <div className="candidate-email">
                          <Mail size={11} /> {c.email}
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className={`claim-status-badge ${c.has_profile ? 'badge-verified' : 'badge-unverified'}`}>
                          {c.has_profile ? 'Profile Ready' : 'No Resume'}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteCandidate(c.id, c.full_name);
                          }}
                          className="btn btn-ghost"
                          style={{ padding: '4px 6px' }}
                          title="Delete Candidate"
                          aria-label={`Delete ${c.full_name}`}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Selected Candidate Telemetry & Resumes */}
        <div>
          {selectedCandidate ? (
            <div className="studio-panel">
              <div className="card-header">
                <div>
                  <h3 className="section-title">{selectedCandidate.full_name}</h3>
                  <p style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginTop: '2px' }}>
                    UUID: {selectedCandidate.id}
                  </p>
                </div>
                <button type="button" className="btn btn-secondary btn-sm" onClick={onNavigateToResume}>
                  <Upload size={13} /> Upload Resume
                </button>
              </div>

              <div className="grid-2" style={{ marginBottom: '18px' }}>
                <div className="stat-card">
                  <div className="stat-label">TOTAL EXPERIENCE</div>
                  <div className="stat-value" style={{ fontSize: selectedCandidate.resumes.length === 0 || !selectedCandidate.total_years_exp ? '1rem' : undefined }}>
                    {selectedCandidate.resumes.length === 0
                      ? 'Resume not uploaded'
                      : !selectedCandidate.total_years_exp
                      ? 'Not provided'
                      : `${selectedCandidate.total_years_exp} Years`}
                  </div>
                </div>
                <div className="stat-card stat-accent">
                  <div className="stat-label">EXTRACTED SKILLS</div>
                  <div className="stat-value" style={{ color: '#818cf8', fontSize: selectedCandidate.skills_summary.length === 0 ? '1rem' : undefined }}>
                    {selectedCandidate.skills_summary.length === 0
                      ? 'None extracted'
                      : `${selectedCandidate.skills_summary.length} Verified`}
                  </div>
                </div>
              </div>

              <div className="studio-panel-header">
                <div className="studio-panel-title">
                  <FileText size={15} />
                  <span>Resume Archives ({selectedCandidate.resumes.length})</span>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {selectedCandidate.resumes.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
                    No resumes attached to this profile yet.
                  </div>
                ) : (
                  selectedCandidate.resumes.map((r) => (
                    <div
                      key={r.id}
                      className={`resume-item-row ${r.is_active ? 'active' : ''}`}
                    >
                      <div>
                        <div className="resume-file-name">
                          <FileText size={14} style={{ color: r.is_active ? 'var(--status-verified)' : 'var(--text-muted)' }} />
                          {r.file_name}
                        </div>
                        <div className="resume-file-meta">
                          {r.file_type.toUpperCase()} • {(r.file_size_bytes / 1024).toFixed(1)} KB • {new Date(r.created_at).toLocaleDateString()}
                        </div>
                      </div>

                      <div>
                        {r.is_active ? (
                          <span className="claim-status-badge badge-verified">
                            <CheckCircle size={10} /> Active
                          </span>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleActivateResume(selectedCandidate.id, r.id)}
                          >
                            Set Active
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state-card">
              <User size={36} className="empty-state-icon" />
              <h3>Select a Candidate Profile</h3>
              <p>Choose a profile from the left column to view resume attachments and history.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
