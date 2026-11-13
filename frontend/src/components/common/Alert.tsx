import React from 'react';
import { AlertCircle, CheckCircle, Info, AlertTriangle, X } from 'lucide-react';

export type AlertVariant = 'info' | 'success' | 'warning' | 'danger';

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
  title?: string;
  onDismiss?: () => void;
  showIcon?: boolean;
}

export const Alert: React.FC<AlertProps> = ({
  children,
  variant = 'info',
  title,
  onDismiss,
  showIcon = true,
  className = '',
  ...rest
}) => {
  const getIcon = () => {
    switch (variant) {
      case 'success':
        return <CheckCircle size={18} className="alert-icon" />;
      case 'warning':
        return <AlertTriangle size={18} className="alert-icon" />;
      case 'danger':
        return <AlertCircle size={18} className="alert-icon" />;
      case 'info':
      default:
        return <Info size={18} className="alert-icon" />;
    }
  };

  const role = variant === 'danger' ? 'alert' : 'status';
  const combinedClass = `alert alert-${variant} ${className}`.trim();

  return (
    <div className={combinedClass} role={role} {...rest}>
      {showIcon && getIcon()}
      <div className="alert-content">
        {title && <div className="alert-title">{title}</div>}
        <div className="alert-message">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          className="alert-dismiss-btn"
          onClick={onDismiss}
          aria-label="Dismiss notification"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
};
