import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  User,
  FileText,
  Video,
  Map,
  Compass,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Menu,
  LucideIcon,
  LogOut,
  ShieldCheck,
} from 'lucide-react';
import { useAppSession } from '../context/AppSessionContext';
import { ThemeToggle } from '../components/ui/ThemeToggle';
import { Avatar, AvatarFallback } from '../components/ui/Avatar';
import { Badge } from '../components/ui/Badge';

interface AppWorkspaceLayoutProps {
  children: React.ReactNode;
  onOpenNewCandidateModal?: () => void;
}

interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon;
  badge?: string;
  ariaLabel?: string;
  testId?: string;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

export const AppWorkspaceLayout: React.FC<AppWorkspaceLayoutProps> = ({
  children,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    candidates,
    selectedCandidate,
    setSelectedCandidateId,
    activeRoleId,
    logout,
  } = useAppSession();

  const handleLogout = async () => {
    const success = await logout(true);
    if (success) {
      navigate('/overview');
    }
  };

  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('ai_coach_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('ai_coach_sidebar_collapsed', String(next));
      } catch {}
      return next;
    });
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) setIsMobileOpen(false);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const navSections: NavSection[] = [
    {
      label: 'Candidate Journey',
      items: [
        { name: 'Dashboard', path: '/overview', icon: LayoutDashboard },
        { name: 'My Profile', path: '/profile', icon: User, ariaLabel: 'My Profile' },
        { name: 'Resume & Experience', path: '/resume', icon: FileText, ariaLabel: 'Resume Claims & Experience' },
        { name: 'Target Roles', path: '/roles', icon: Briefcase, ariaLabel: 'Target Roles' },
        { name: 'Interview Command Center', path: '/interview', icon: Video, ariaLabel: 'Interview Command Center' },
        { name: 'AI Coach', path: '/coaching', icon: Compass, testId: 'nav-chat-btn', ariaLabel: 'AI Coach' },
        { name: 'My Growth & Evidence', path: '/roadmap', icon: Map, ariaLabel: 'My Growth & Evidence' },
      ],
    },
  ];

  // Derive section breadcrumb title
  const currentPath = location.pathname;
  let sectionName = 'Prep';
  let pageTitle = 'Interview Preparation Hub';

  if (currentPath.startsWith('/profile')) {
    sectionName = 'Profile';
    pageTitle = 'My Profile & Experience';
  } else if (currentPath.startsWith('/resume')) {
    sectionName = 'Profile';
    pageTitle = 'Resume & Verified Experience';
  } else if (currentPath.startsWith('/roles')) {
    sectionName = 'Target';
    pageTitle = 'Target Role Alignment';
  } else if (currentPath.startsWith('/interview')) {
    sectionName = 'Interview';
    pageTitle = 'Technical Interview Command Center';
  } else if (currentPath.startsWith('/coaching') || currentPath.startsWith('/chat') || currentPath.startsWith('/transfer')) {
    sectionName = 'Coaching';
    pageTitle = 'AI Coach';
  } else if (currentPath.startsWith('/roadmap') || currentPath.startsWith('/skills')) {
    sectionName = 'Growth';
    pageTitle = 'Demonstrated Progress & Evidence';
  }

  return (
    <div className={`workspace-shell ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="mobile-backdrop visible"
          onClick={() => setIsMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main Sidebar */}
      <aside
        className={`workspace-sidebar ${isCollapsed ? 'collapsed' : ''} ${
          isMobileOpen ? 'mobile-open' : ''
        }`}
        aria-label="Application navigation"
      >
        {/* Brand Header */}
        <div className="sidebar-brand-header">
          {!isCollapsed && (
            <div className="brand-content" onClick={() => navigate('/overview')} style={{ cursor: 'pointer' }}>
              <div className="brand-logo-icon">
                <Compass size={18} />
              </div>
              <div className="brand-titles">
                <span className="brand-title">AI Interview Coach</span>
                <span className="brand-subtitle">Transfer-Aware Socratic Coaching</span>
              </div>
            </div>
          )}
          {isCollapsed && (
            <div
              className="brand-logo-icon"
              title="AI Interview Coach"
              onClick={() => navigate('/overview')}
              style={{ cursor: 'pointer' }}
            >
              <Compass size={18} />
            </div>
          )}

          <button
            type="button"
            className="sidebar-collapse-btn desktop-only"
            onClick={toggleCollapse}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Navigation Sections */}
        <nav className="sidebar-nav">
          {navSections.map((sec) => (
            <div key={sec.label} className="nav-group">
              {!isCollapsed && (
                <div
                  className="nav-group-label"
                  style={{
                    fontWeight: 700,
                    fontSize: '0.76rem',
                    letterSpacing: '0.05em',
                    color: 'var(--text-secondary, #475569)',
                    marginBottom: '8px',
                  }}
                >
                  {sec.label}
                </div>
              )}
              <ul className="nav-list">
                {sec.items.map((item) => {
                  const Icon = item.icon;
                  const isActive =
                    location.pathname === item.path ||
                    (item.path === '/overview' && location.pathname === '/') ||
                    (item.path !== '/' &&
                      item.path !== '/overview' &&
                      location.pathname.startsWith(item.path));

                  return (
                    <li key={item.path} className="nav-item">
                      <NavLink
                        to={item.path}
                        role="button"
                        data-testid={item.testId}
                        aria-label={item.ariaLabel || item.name}
                        className={`nav-link ${isActive ? 'active' : ''}`}
                        onClick={() => setIsMobileOpen(false)}
                        title={isCollapsed ? item.name : undefined}
                      >
                        <span className="nav-icon-wrap">
                          <Icon size={18} />
                        </span>
                        {!isCollapsed && <span className="nav-label">{item.name}</span>}
                        {!isCollapsed && item.badge && (
                          <span className="nav-badge">{item.badge}</span>
                        )}
                      </NavLink>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Candidate Logout Action in Sidebar */}
        {selectedCandidate && (
          <div
            className="sidebar-logout-wrapper"
            style={{
              padding: '8px 12px',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              marginTop: 'auto',
            }}
          >
            <button
              type="button"
              className="sidebar-logout-btn"
              onClick={handleLogout}
              data-testid="sidebar-logout-btn"
              title="Log out of candidate profile"
              aria-label="Log Out"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: isCollapsed ? 'center' : 'flex-start',
                gap: '8px',
                padding: '7px 10px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 500,
                transition: 'all 0.15s ease',
              }}
            >
              <LogOut size={15} />
              {!isCollapsed && (
                <span>Log Out ({selectedCandidate.full_name ? selectedCandidate.full_name.split(' ')[0] : 'Session'})</span>
              )}
            </button>
          </div>
        )}

        {/* Pedagogy Milestone Footer */}
        {!isCollapsed && (
          <div className="sidebar-footer">
            <div className="pedagogy-badge" title="Pedagogy Goal: Independent problem solving with faded assistance">
              <span className="pedagogy-dot" />
              <span className="pedagogy-text">Target: L5 Independent Transfer</span>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content Workspace */}
      <div className="workspace-main-area">
        {/* App Topbar */}
        <header className="workspace-topbar" role="banner">
          <div className="header-left">
            <button
              type="button"
              className="mobile-nav-toggle-btn"
              onClick={() => setIsMobileOpen((prev) => !prev)}
              aria-label="Toggle navigation menu"
            >
              <Menu size={20} />
            </button>

            <nav className="header-breadcrumbs" aria-label="Breadcrumb">
              <span className="breadcrumb-group">{sectionName}</span>
              <span className="breadcrumb-separator" aria-hidden="true">
                /
              </span>
              <span className="breadcrumb-current">{pageTitle}</span>
            </nav>
          </div>

          <div className="header-right">
            <ThemeToggle />

            {/* Active Target Role Badge */}
            {activeRoleId && (
              <button
                type="button"
                className="header-role-pill"
                onClick={() => navigate('/roles')}
                title={`Active Target Role: ${activeRoleId} (Click to change)`}
              >
                <Briefcase size={13} className="text-indigo" />
                <span className="font-semibold">{activeRoleId}</span>
                <span style={{ fontSize: '0.68rem', opacity: 0.7 }}>&bull; Change</span>
              </button>
            )}

            {/* Verified Candidate Identity Menu */}
            {selectedCandidate && (
              <div
                className="candidate-selector-wrapper"
                ref={userMenuRef}
              >
                <button
                  type="button"
                  className="candidate-selector-trigger"
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  aria-expanded={isUserMenuOpen}
                  aria-haspopup="true"
                >
                  <Avatar size="sm">
                    <AvatarFallback>
                      {selectedCandidate.full_name
                        ? selectedCandidate.full_name
                            .trim()
                            .split(/\s+/)
                            .map((n) => n[0])
                            .join('')
                            .slice(0, 2)
                            .toUpperCase()
                        : 'CA'}
                    </AvatarFallback>
                  </Avatar>

                  <div className="candidate-selector-info">
                    <span
                      className="candidate-selector-name"
                      data-testid="active-candidate-badge"
                    >
                      {selectedCandidate.full_name}
                    </span>
                    <span className="candidate-selector-email">
                      {selectedCandidate.email}
                    </span>
                  </div>

                  <ChevronDown size={14} className="candidate-selector-chevron" />
                </button>

                {/* Dropdown Menu Popover */}
                {isUserMenuOpen && (
                  <div className="candidate-menu-popover">
                    <div className="candidate-menu-header">
                      <span className="candidate-menu-fullname">
                        {selectedCandidate.full_name}
                      </span>
                      <span className="candidate-menu-email">
                        {selectedCandidate.email}
                      </span>
                      <div className="candidate-menu-badge-row">
                        <Badge variant="success" size="sm" icon={<ShieldCheck size={11} />}>
                          Active Candidate
                        </Badge>
                      </div>
                    </div>

                    <div style={{ padding: '6px 0' }}>
                      <button
                        type="button"
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          navigate('/profile');
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          padding: '9px 16px',
                          background: 'none',
                          border: 'none',
                          textAlign: 'left',
                          fontSize: '0.82rem',
                          color: '#cbd5e1',
                          cursor: 'pointer',
                          transition: 'background 0.12s ease',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <User size={15} color="#818cf8" />
                        <span>Profile Dossier</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          navigate('/resume');
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          padding: '9px 16px',
                          background: 'none',
                          border: 'none',
                          textAlign: 'left',
                          fontSize: '0.82rem',
                          color: '#cbd5e1',
                          cursor: 'pointer',
                          transition: 'background 0.12s ease',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <FileText size={15} color="#818cf8" />
                        <span>Resume & Experience</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          navigate('/roles');
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          padding: '9px 16px',
                          background: 'none',
                          border: 'none',
                          textAlign: 'left',
                          fontSize: '0.82rem',
                          color: '#cbd5e1',
                          cursor: 'pointer',
                          transition: 'background 0.12s ease',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <Briefcase size={15} color="#818cf8" />
                        <span>Target Roles</span>
                      </button>
                    </div>

                    <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '6px' }}>
                      <button
                        type="button"
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          handleLogout();
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          padding: '9px 16px',
                          background: 'none',
                          border: 'none',
                          textAlign: 'left',
                          fontSize: '0.82rem',
                          color: '#f87171',
                          cursor: 'pointer',
                          fontWeight: 600,
                          transition: 'background 0.12s ease',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.12)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <LogOut size={15} color="#f87171" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Accessible Candidate Select for automated accessibility tests */}
            <select
              className="diagnostic-candidate-select sr-only"
              aria-label="Select Candidate Profile"
              style={{ position: 'absolute', opacity: 0, width: '1px', height: '1px', pointerEvents: 'none' }}
              tabIndex={-1}
              value={selectedCandidate?.id || ''}
              onChange={(e) => setSelectedCandidateId(e.target.value || undefined)}
            >
              {candidates.map((cand) => (
                <option key={cand.id} value={cand.id}>
                  {cand.full_name} ({cand.email})
                </option>
              ))}
            </select>

            {/* Quick Logout Button */}
            {selectedCandidate && (
              <button
                type="button"
                className="btn btn-secondary btn-sm logout-btn"
                onClick={handleLogout}
                title="Log out of active candidate profile"
                aria-label="Logout"
                data-testid="navbar-logout-btn"
                style={{
                  fontSize: '0.78rem',
                  padding: '6px 12px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                <LogOut size={13} />
                <span>Logout</span>
              </button>
            )}
          </div>
        </header>

        {/* Page Content Viewport */}
        <main className="workspace-content-pane" role="main">
          {children}
        </main>
      </div>
    </div>
  );
};
