import React, { useState } from 'react';
import { CandidateClaim, ClaimVerificationStatus } from '../../types';
import { ShieldCheck, AlertCircle, HelpCircle, CheckCircle2, ChevronDown, ChevronUp, Layers } from 'lucide-react';

interface EvidenceGraphHUDProps {
  claims: CandidateClaim[];
  currentSkillUnderProbe?: string;
  onSelectClaim?: (claim: CandidateClaim) => void;
}

export const EvidenceGraphHUD: React.FC<EvidenceGraphHUDProps> = ({
  claims,
  currentSkillUnderProbe,
  onSelectClaim,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const verifiedCount = claims.filter((c) => c.verification_status === 'VERIFIED').length;
  const probedCount = claims.filter((c) => c.verification_status === 'PROBED').length;
  const totalCount = claims.length;
  const verificationRatio = totalCount > 0 ? Math.round((verifiedCount / totalCount) * 100) : 0;

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const getStatusIcon = (status: ClaimVerificationStatus) => {
    switch (status) {
      case 'VERIFIED':
        return <CheckCircle2 size={13} style={{ color: 'var(--status-verified)' }} />;
      case 'PROBED':
        return <AlertCircle size={13} style={{ color: 'var(--status-probed)' }} />;
      case 'CONTESTED':
        return <AlertCircle size={13} style={{ color: 'var(--status-contested)' }} />;
      default:
        return <HelpCircle size={13} style={{ color: 'var(--status-unverified)' }} />;
    }
  };

  const getStatusBadgeClass = (status: ClaimVerificationStatus) => {
    switch (status) {
      case 'VERIFIED':
        return 'badge-verified';
      case 'PROBED':
        return 'badge-probed';
      case 'CONTESTED':
        return 'badge-contested';
      default:
        return 'badge-unverified';
    }
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'var(--status-verified)';
    if (conf >= 0.5) return 'var(--status-probed)';
    return 'var(--status-contested)';
  };

  return (
    <div className="deck-evidence-graph">
      {/* Evidence Graph Summary Card */}
      <div className="studio-panel" style={{ padding: '16px' }}>
        <div className="studio-panel-header" style={{ marginBottom: '12px' }}>
          <div className="studio-panel-title">
            <Layers size={16} color="#818cf8" />
            <span>Candidate Evidence Graph</span>
          </div>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
            CEG v1.2
          </span>
        </div>

        {/* Verification Ratio Metric */}
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Verified Epistemic Ratio</span>
          <span style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--status-verified)' }}>
            {verificationRatio}%
          </span>
        </div>

        <div className="progress-bar-container" style={{ marginBottom: '14px' }}>
          <div
            className="progress-bar-fill"
            style={{
              width: `${verificationRatio}%`,
              background: 'linear-gradient(90deg, #6366f1, #10b981)',
            }}
          />
        </div>

        {/* Mini stats counters */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', textAlign: 'center' }}>
          <div style={{ background: 'var(--bg-surface)', padding: '6px', borderRadius: '4px' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>VERIFIED</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--status-verified)' }}>{verifiedCount}</div>
          </div>
          <div style={{ background: 'var(--bg-surface)', padding: '6px', borderRadius: '4px' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>PROBING</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--status-probed)' }}>{probedCount}</div>
          </div>
          <div style={{ background: 'var(--bg-surface)', padding: '6px', borderRadius: '4px' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>CLAIMS</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>{totalCount}</div>
          </div>
        </div>
      </div>

      {/* Claim Decomposition Node List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '520px', overflowY: 'auto' }}>
        {claims.length === 0 ? (
          <div className="studio-panel" style={{ textAlign: 'center', padding: '24px 16px', color: 'var(--text-dim)' }}>
            <ShieldCheck size={28} style={{ margin: '0 auto 8px auto', opacity: 0.4 }} />
            <p style={{ fontSize: '0.85rem' }}>No claims extracted yet. Upload a resume to populate the evidence graph.</p>
          </div>
        ) : (
          claims.map((claim) => {
            const isUnderProbe = currentSkillUnderProbe?.toLowerCase() === claim.skill_name.toLowerCase();
            const isExpanded = expandedId === claim.id;

            return (
              <div
                key={claim.id}
                className={`claim-item-card ${claim.verification_status.toLowerCase()} ${isUnderProbe ? 'interactive' : ''}`}
                style={{
                  boxShadow: isUnderProbe ? '0 0 12px rgba(99, 102, 241, 0.35)' : undefined,
                  borderRight: isUnderProbe ? '2px solid var(--accent-primary)' : undefined,
                }}
                onClick={() => {
                  toggleExpand(claim.id);
                  if (onSelectClaim) onSelectClaim(claim);
                }}
              >
                <div className="claim-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {getStatusIcon(claim.verification_status)}
                    <span className="claim-skill-name">{claim.skill_name}</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className={`claim-status-badge ${getStatusBadgeClass(claim.verification_status)}`}>
                      {claim.verification_status}
                    </span>
                    <button
                      type="button"
                      style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 0 }}
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                  </div>
                </div>

                <div className="claim-text-snippet">
                  "{claim.claim_text.length > 90 ? `${claim.claim_text.slice(0, 90)}...` : claim.claim_text}"
                </div>

                {/* Confidence Bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                  <div className="claim-confidence-bar" style={{ flex: 1 }}>
                    <div
                      className="claim-confidence-fill"
                      style={{
                        width: `${Math.round(claim.confidence_score * 100)}%`,
                        background: getConfidenceColor(claim.confidence_score),
                      }}
                    />
                  </div>
                  <span style={{ fontSize: '0.675rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                    {Math.round(claim.confidence_score * 100)}%
                  </span>
                </div>

                {/* Expanded Citation Trace */}
                {isExpanded && (
                  <div
                    className="fade-in"
                    style={{
                      marginTop: '10px',
                      paddingTop: '10px',
                      borderTop: '1px solid var(--border-subtle)',
                      fontSize: '0.775rem',
                    }}
                  >
                    <div style={{ color: 'var(--text-dim)', textTransform: 'uppercase', fontSize: '0.65rem', marginBottom: '4px', letterSpacing: '0.04em' }}>
                      Demonstrated Evidence Quotes
                    </div>
                    {claim.verified_quotes && claim.verified_quotes.length > 0 ? (
                      <ul style={{ paddingLeft: '14px', color: 'var(--text-main)', margin: 0 }}>
                        {claim.verified_quotes.map((q, idx) => (
                          <li key={idx} style={{ marginBottom: '4px', fontStyle: 'italic' }}>
                            "{q}"
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>
                        No direct interview evidence registered yet for this claim.
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
