import React from 'react';

export interface ProgressBarProps {
  value: number; // 0 to 100 or 0 to 10 (auto-scaled)
  max?: number;
  label?: string;
  showValueLabel?: boolean;
  valueSuffix?: string;
  size?: 'sm' | 'md' | 'lg';
  colorMode?: 'auto' | 'primary' | 'success' | 'warning' | 'danger';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  label,
  showValueLabel = true,
  valueSuffix = '%',
  size = 'md',
  colorMode = 'auto',
}) => {
  // Normalize value to percentage
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const getColorClass = () => {
    if (colorMode !== 'auto') return `progress-fill-${colorMode}`;
    if (percentage >= 70) return 'progress-fill-success';
    if (percentage >= 50) return 'progress-fill-warning';
    return 'progress-fill-danger';
  };

  const height = size === 'sm' ? '4px' : size === 'lg' ? '10px' : '6px';

  return (
    <div className="progress-meter-group">
      {(label || showValueLabel) && (
        <div className="progress-label-row">
          {label && <span className="progress-label-text">{label}</span>}
          {showValueLabel && (
            <span className="progress-value-text">
              {Math.round(value)}
              {valueSuffix}
            </span>
          )}
        </div>
      )}
      <div className="progress-bar-container" style={{ height }}>
        <div
          className={`progress-bar-fill ${getColorClass()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
