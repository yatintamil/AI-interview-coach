import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'default',
      size = 'md',
      icon,
      iconPosition = 'left',
      loading = false,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const classNames = [
      'ui-button',
      `ui-button-${variant}`,
      `ui-button-${size}`,
      loading ? 'ui-button-loading' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <button
        ref={ref}
        className={classNames}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <span className="ui-button-spinner" aria-hidden="true">
            <svg
              className="ui-spinner-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
              <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
            </svg>
          </span>
        )}
        {!loading && icon && iconPosition === 'left' && (
          <span className="ui-button-icon-left">{icon}</span>
        )}
        {children && <span className="ui-button-text">{children}</span>}
        {!loading && icon && iconPosition === 'right' && (
          <span className="ui-button-icon-right">{icon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
