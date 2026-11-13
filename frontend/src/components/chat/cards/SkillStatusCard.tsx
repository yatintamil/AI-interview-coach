import React from 'react';
import { Award, ShieldCheck, Info } from 'lucide-react';
import { StructuredUIPayload, formatTransferLevel } from '../../../types';

interface SkillStatusCardProps {
  payload: StructuredUIPayload;
}

export const SkillStatusCard: React.FC<SkillStatusCardProps> = ({ payload }) => {
  const skills = Array.isArray(payload.skills) ? payload.skills : [];

  return (
    <div className="structured-card skill-status-card" data-testid="skill-status-card">
      <div className="card-header-badge">
        <span className="badge badge-accent">
          <Award size={13} className="badge-icon" />
          <span>Verified Skill Status</span>
        </span>
        <span className="badge badge-subtle">{skills.length} Competencies</span>
      </div>

      {skills.length > 0 ? (
        <div className="skill-status-table">
          {skills.map((s, idx) => {
            const skillName = s.skill ? String(s.skill).replace(/_/g, ' ') : 'Competency';
            const transferLevelText = formatTransferLevel(s.transfer_level);
            const masteryVal = typeof s.mastery === 'number' ? s.mastery : 0;

            return (
              <div key={idx} className="skill-status-row">
                <div className="skill-name-col">
                  <span className="skill-name-text">{skillName}</span>
                  <span className="skill-transfer-level">
                    <ShieldCheck size={11} className="text-cyan" />
                    {transferLevelText}
                  </span>
                </div>
                <div className="skill-mastery-col">
                  <span className="mastery-val">{Math.round(masteryVal * 100)}%</span>
                  <div className="progress-bar-container mini">
                    <div
                      className="progress-bar-fill progress-bar-verified"
                      style={{ width: `${Math.min(100, Math.max(5, masteryVal * 100))}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="empty-subtle">No verified skill states found. Complete interview sessions to generate verified data.</p>
      )}

      <div className="card-guarantee-note">
        <Info size={13} />
        <span>Conversational inquiry only. Verified skill estimates are strictly preserved.</span>
      </div>
    </div>
  );
};
