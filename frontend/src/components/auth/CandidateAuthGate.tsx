import React, { useState } from 'react';
import {
  ShieldCheck,
  UserPlus,
  LogIn,
  AlertCircle,
  ArrowRight,
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  Cpu,
  Target,
  Layers,
} from 'lucide-react';
import { useAppSession } from '../../context/AppSessionContext';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Badge,
  Tabs,
  TabsList,
  TabsTrigger,
} from '../ui';

interface CandidateAuthGateProps {
  children: React.ReactNode;
}

export const CandidateAuthGate: React.FC<CandidateAuthGateProps> = ({ children }) => {
  const { isAuthenticated, isAuthResolving, login, register } = useAppSession();

  const [activeTab, setActiveTab] = useState<'signin' | 'register'>('signin');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (isAuthResolving) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          padding: '60px 20px',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-sans)',
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            border: '2px solid var(--border-card)',
            borderTopColor: 'var(--brand-primary)',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            marginBottom: '16px',
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <p style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Verifying candidate session credentials...
        </p>
      </div>
    );
  }

  if (isAuthenticated) {
    return <>{children}</>;
  }

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setErrorMessage(null);

    const result = await login(email.trim(), password || 'CandidateP@ss123!');
    setLoading(false);
    if (!result.success) {
      setErrorMessage(
        result.error?.includes('404') || result.error?.includes('not found')
          ? `No candidate profile found for "${email.trim()}". Please switch to "Create Account".`
          : result.error?.includes('401') || result.error?.includes('Incorrect password')
          ? 'Incorrect password. Please verify your credentials and try again.'
          : result.error || 'Authentication failed. Please verify your credentials.'
      );
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !fullName.trim()) return;

    if (password && password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }
    if (password && confirmPassword && password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please re-enter.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    const result = await register(
      email.trim(),
      fullName.trim(),
      password || 'CandidateP@ss123!'
    );
    setLoading(false);
    if (!result.success) {
      setErrorMessage(
        result.error?.includes('409') || result.error?.includes('already exists')
          ? `An account with "${email.trim()}" already exists. Please sign in instead.`
          : result.error || 'Registration failed. Please try again.'
      );
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - 120px)',
        padding: '40px 20px',
        width: '100%',
        boxSizing: 'border-box',
      }}
      data-testid="candidate-auth-gate"
    >
      {/* Centered Executive Auth Card */}
      <Card
        variant="default"
        style={{
          width: '100%',
          maxWidth: '460px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <CardHeader style={{ paddingBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '4px',
                backgroundColor: 'var(--surface-raised)',
                border: '1px solid var(--border-card)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-primary)',
              }}
            >
              <Lock size={16} />
            </div>
            <div>
              <span
                style={{
                  display: 'block',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                Session Authentication
              </span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Interview Workspace Access
              </span>
            </div>
          </div>

          <CardTitle style={{ fontSize: '1.35rem', fontWeight: 700 }}>
            {activeTab === 'signin' ? 'Sign in to Candidate Portal' : 'Create Candidate Account'}
          </CardTitle>
          <CardDescription style={{ fontSize: '0.84rem', marginTop: '4px' }}>
            {activeTab === 'signin'
              ? 'Enter your verified candidate credentials to access your interview workspace.'
              : 'Set up your candidate identity to begin your adaptive interview coaching.'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {/* Mode Switcher Tabs */}
          <Tabs
            value={activeTab}
            onValueChange={(val) => {
              setActiveTab(val as 'signin' | 'register');
              setErrorMessage(null);
            }}
            style={{ marginBottom: '20px' }}
          >
            <TabsList style={{ width: '100%', display: 'flex' }}>
              <TabsTrigger
                value="signin"
                data-testid="tab-signin"
                icon={<LogIn size={14} />}
                style={{ flex: 1 }}
              >
                Sign In
              </TabsTrigger>
              <TabsTrigger
                value="register"
                data-testid="tab-register"
                icon={<UserPlus size={14} />}
                style={{ flex: 1 }}
              >
                Create Account
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Error Banner */}
          {errorMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '10px 12px',
                borderRadius: '4px',
                backgroundColor: 'var(--color-danger-bg)',
                border: '1px solid var(--color-danger-border)',
                color: 'var(--color-danger)',
                fontSize: '0.82rem',
                lineHeight: 1.45,
                marginBottom: '18px',
              }}
              data-testid="auth-error-banner"
            >
              <AlertCircle size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{errorMessage}</div>
            </div>
          )}

          {/* Form Content */}
          {activeTab === 'signin' ? (
            <form onSubmit={handleSignIn}>
              {/* Email Input */}
              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="candidate-auth-email"
                  style={{
                    display: 'block',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                  }}
                >
                  Candidate Email Address
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail
                    size={15}
                    style={{
                      position: 'absolute',
                      left: '12px',
                      top: '11px',
                      pointerEvents: 'none',
                      color: 'var(--text-tertiary)',
                    }}
                  />
                  <input
                    id="candidate-auth-email"
                    type="email"
                    required
                    placeholder="candidate@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    data-testid="input-signin-email"
                    className="input-control"
                    style={{ paddingLeft: '36px' }}
                  />
                </div>
              </div>

              {/* Password Input */}
              <div style={{ marginBottom: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <label
                    htmlFor="candidate-auth-password"
                    style={{
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      color: 'var(--text-secondary)',
                    }}
                  >
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setPassword('CandidateP@ss123!')}
                    style={{
                      fontSize: '0.72rem',
                      color: 'var(--text-tertiary)',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                    }}
                  >
                    Default: CandidateP@ss123!
                  </button>
                </div>
                <div style={{ position: 'relative' }}>
                  <Lock
                    size={15}
                    style={{
                      position: 'absolute',
                      left: '12px',
                      top: '11px',
                      pointerEvents: 'none',
                      color: 'var(--text-tertiary)',
                    }}
                  />
                  <input
                    id="candidate-auth-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    data-testid="input-signin-password"
                    className="input-control"
                    style={{ paddingLeft: '36px', paddingRight: '36px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '9px',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-tertiary)',
                      cursor: 'pointer',
                      padding: '2px',
                    }}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              {/* Remember Me */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
                <input
                  type="checkbox"
                  id="remember-me-checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  style={{ cursor: 'pointer', accentColor: 'var(--brand-primary)' }}
                />
                <label
                  htmlFor="remember-me-checkbox"
                  style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', cursor: 'pointer' }}
                >
                  Remember session on this device
                </label>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="default"
                size="lg"
                loading={loading}
                data-testid="btn-submit-signin"
                style={{ width: '100%' }}
                icon={<ArrowRight size={15} />}
                iconPosition="right"
              >
                Sign In to Account
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              {/* Full Name */}
              <div style={{ marginBottom: '14px' }}>
                <label
                  htmlFor="candidate-auth-fullname"
                  style={{
                    display: 'block',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                  }}
                >
                  Full Name
                </label>
                <div style={{ position: 'relative' }}>
                  <User
                    size={15}
                    style={{
                      position: 'absolute',
                      left: '12px',
                      top: '11px',
                      pointerEvents: 'none',
                      color: 'var(--text-tertiary)',
                    }}
                  />
                  <input
                    id="candidate-auth-fullname"
                    type="text"
                    required
                    placeholder="Jordan Lee"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    data-testid="input-register-fullname"
                    className="input-control"
                    style={{ paddingLeft: '36px' }}
                  />
                </div>
              </div>

              {/* Email */}
              <div style={{ marginBottom: '14px' }}>
                <label
                  htmlFor="candidate-register-email"
                  style={{
                    display: 'block',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                  }}
                >
                  Candidate Email Address
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail
                    size={15}
                    style={{
                      position: 'absolute',
                      left: '12px',
                      top: '11px',
                      pointerEvents: 'none',
                      color: 'var(--text-tertiary)',
                    }}
                  />
                  <input
                    id="candidate-register-email"
                    type="email"
                    required
                    placeholder="jordan.lee@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    data-testid="input-register-email"
                    className="input-control"
                    style={{ paddingLeft: '36px' }}
                  />
                </div>
              </div>

              {/* Password */}
              <div style={{ marginBottom: '14px' }}>
                <label
                  htmlFor="candidate-register-password"
                  style={{
                    display: 'block',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                  }}
                >
                  Account Password (min 6 characters)
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock
                    size={15}
                    style={{
                      position: 'absolute',
                      left: '12px',
                      top: '11px',
                      pointerEvents: 'none',
                      color: 'var(--text-tertiary)',
                    }}
                  />
                  <input
                    id="candidate-register-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    data-testid="input-register-password"
                    className="input-control"
                    style={{ paddingLeft: '36px', paddingRight: '36px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '9px',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-tertiary)',
                      cursor: 'pointer',
                      padding: '2px',
                    }}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div style={{ marginBottom: '20px' }}>
                <label
                  htmlFor="candidate-register-confirm"
                  style={{
                    display: 'block',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                  }}
                >
                  Confirm Password
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock
                    size={15}
                    style={{
                      position: 'absolute',
                      left: '12px',
                      top: '11px',
                      pointerEvents: 'none',
                      color: 'var(--text-tertiary)',
                    }}
                  />
                  <input
                    id="candidate-register-confirm"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    data-testid="input-register-confirm"
                    className="input-control"
                    style={{ paddingLeft: '36px' }}
                  />
                </div>
              </div>

              {/* Submit */}
              <Button
                type="submit"
                variant="default"
                size="lg"
                loading={loading}
                data-testid="btn-submit-register"
                style={{ width: '100%' }}
                icon={<ArrowRight size={15} />}
                iconPosition="right"
              >
                Create Candidate Profile
              </Button>
            </form>
          )}
        </CardContent>

        <CardFooter style={{ flexDirection: 'column', gap: '8px', textAlign: 'center' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              fontSize: '0.76rem',
              color: 'var(--text-secondary)',
            }}
          >
            <ShieldCheck size={14} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
            <span>Strict cryptographic session token authentication active</span>
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', margin: 0, lineHeight: 1.45 }}>
            Candidate evidence, telemetry metrics, and evaluation debriefs are strictly isolated.
          </p>
        </CardFooter>
      </Card>

      {/* Architectural Pillars Footer Pills */}
      <div
        style={{
          marginTop: '28px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
        }}
      >
        <Badge variant="outline" icon={<Cpu size={12} />}>
          Document-Grounded Probes
        </Badge>
        <Badge variant="outline" icon={<Layers size={12} />}>
          Socratic Scaffolding & Hint Ladders
        </Badge>
        <Badge variant="outline" icon={<Target size={12} />}>
          Target: L5 Independent Transfer
        </Badge>
      </div>
    </div>
  );
};
