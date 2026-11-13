import React, { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

export interface ThemeToggleProps {
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('app-ui-theme') as 'dark' | 'light' | null;
      if (saved) return saved;
    }
    return 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('app-ui-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <button
      type="button"
      className={`ui-theme-toggle-btn ${className}`}
      onClick={toggleTheme}
      title={theme === 'dark' ? 'Switch to Light Workspace' : 'Switch to Dark Workspace'}
      aria-label="Toggle visual theme"
    >
      {theme === 'dark' ? (
        <>
          <Sun size={15} />
          <span className="theme-toggle-text">Light</span>
        </>
      ) : (
        <>
          <Moon size={15} />
          <span className="theme-toggle-text">Dark</span>
        </>
      )}
    </button>
  );
};
