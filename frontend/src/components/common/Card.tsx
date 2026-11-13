import React from 'react';

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  variant?: 'default' | 'elevated' | 'bordered' | 'glass';
  header?: React.ReactNode;
  footer?: React.ReactNode;
  actions?: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  header,
  footer,
  actions,
  title,
  subtitle,
  className = '',
  ...rest
}) => {
  const baseClass = 'studio-panel';
  const variantClass = variant !== 'default' ? `studio-panel-${variant}` : '';

  const combinedClass = [baseClass, variantClass, className].filter(Boolean).join(' ');

  return (
    <div className={combinedClass} {...rest}>
      {(header || title || actions) && (
        <div className="studio-panel-header">
          {header ? (
            header
          ) : (
            <>
              <div className="studio-panel-title-group">
                {title && <h3 className="studio-panel-title">{title}</h3>}
                {subtitle && <p className="studio-panel-subtitle">{subtitle}</p>}
              </div>
              {actions && <div className="studio-panel-actions">{actions}</div>}
            </>
          )}
        </div>
      )}
      <div className="studio-panel-body">{children}</div>
      {footer && <div className="studio-panel-footer">{footer}</div>}
    </div>
  );
};
