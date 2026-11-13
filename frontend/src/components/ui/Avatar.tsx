import React from 'react';

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg';
}

export const Avatar: React.FC<AvatarProps> = ({
  size = 'md',
  className = '',
  children,
  ...props
}) => {
  return (
    <div className={`ui-avatar ui-avatar-${size} ${className}`} {...props}>
      {children}
    </div>
  );
};

export interface AvatarFallbackProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
}

export const AvatarFallback: React.FC<AvatarFallbackProps> = ({
  className = '',
  children,
  ...props
}) => {
  return (
    <span className={`ui-avatar-fallback ${className}`} {...props}>
      {children}
    </span>
  );
};
