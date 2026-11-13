import React from 'react';

export interface StatCardProps {
  label: string;
  value: React.ReactNode;
  subtext?: string;
  icon?: React.ReactNode;
  accent?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    text: string;
  };
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  icon,
  accent = 'neutral',
  trend,
  onClick,
}) => {
  const accentClass = `stat-card-${accent}`;

  return (
    <div
      className={`stat-card ${accentClass} ${onClick ? 'stat-card-clickable' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="stat-card-header">
        <span className="stat-label">{label}</span>
        {icon && <span className="stat-icon-wrapper">{icon}</span>}
      </div>
      <div className="stat-value">{value}</div>
      {(subtext || trend) && (
        <div className="stat-footer">
          {trend && (
            <span className={`stat-trend stat-trend-${trend.direction}`}>
              {trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'}{' '}
              {trend.text}
            </span>
          )}
          {subtext && <span className="stat-subtext">{subtext}</span>}
        </div>
      )}
    </div>
  );
};
