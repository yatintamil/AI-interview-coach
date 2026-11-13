import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Home } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div
      className="studio-panel fade-in"
      style={{
        maxWidth: '560px',
        margin: '60px auto',
        padding: '48px 32px',
        textAlign: 'center',
        background: 'var(--bg-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-card)',
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          padding: '16px',
          borderRadius: '50%',
          background: 'rgba(239, 68, 68, 0.12)',
          color: '#f87171',
          marginBottom: '20px',
        }}
      >
        <AlertTriangle size={40} />
      </div>

      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '8px' }}>
        404 — Page Not Found
      </h1>

      <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '28px' }}>
        The requested URL path does not exist in the Multimodal Studio workflow.
      </p>

      <button
        type="button"
        className="btn btn-primary"
        onClick={() => navigate('/profile')}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', margin: '0 auto' }}
      >
        <Home size={16} />
        <span>Return to Candidate Profiles</span>
      </button>
    </div>
  );
};
