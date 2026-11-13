import React from 'react';
import { Loader2 } from 'lucide-react';

export interface LoadingStateProps {
  message?: string;
  subtext?: string;
  minHeight?: string;
  size?: number;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading...',
  subtext,
  minHeight = '200px',
  size = 32,
}) => {
  return (
    <div
      className="loading-state-container fade-in"
      style={{ minHeight }}
      role="status"
      aria-live="polite"
    >
      <Loader2 size={size} className="spin loading-spinner" />
      <div className="loading-message">{message}</div>
      {subtext && <div className="loading-subtext">{subtext}</div>}
    </div>
  );
};
