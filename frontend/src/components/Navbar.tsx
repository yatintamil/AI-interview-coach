import React from 'react';
import { Candidate } from '../types';
import { Layers, User, FileText, Video, Compass, BarChart2, UserPlus, MessageSquare, FlaskConical } from 'lucide-react';
import { useAppSession, useSafeLocation, useSafeNavigate } from '../context/AppSessionContext';

interface NavbarProps {
  candidates: Candidate[];
  selectedCandidate: Candidate | null;
  onSelectCandidate: (candidate: Candidate) => void;
  onOpenNewCandidateModal: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onOpenNewCandidateModal,
}) => {
  const location = useSafeLocation();
  const navigate = useSafeNavigate();
  const { interviewSessionId, coachingSessionId } = useAppSession();

  const pathname = location.pathname;

  const isProfileActive = pathname === '/profile' || pathname === '/';
  const isResumeActive = pathname.startsWith('/resume');
  const isInterviewActive = pathname.startsWith('/interview') || pathname.startsWith('/debrief');
  const isRoadmapActive = pathname.startsWith('/roadmap');
  const isCoachingActive = pathname.startsWith('/coaching');
  const isChatActive = pathname.startsWith('/chat');
  const isAnalyticsActive = pathname.startsWith('/analytics');
  const isStudyActive = pathname.startsWith('/study') || pathname.startsWith('/experiment');

  const handleNavigateInterview = () => {
    if (interviewSessionId && interviewSessionId !== 'undefined') {
      navigate(`/interview/${interviewSessionId}`);
    } else {
      navigate('/interview');
    }
  };

  const handleNavigateCoaching = () => {
    if (coachingSessionId && coachingSessionId !== 'undefined') {
      navigate(`/coaching/${coachingSessionId}`);
    } else {
      navigate('/coaching');
    }
  };

  return (
    <header className="studio-navbar">
      <div className="brand-section" onClick={() => navigate('/profile')} style={{ cursor: 'pointer' }}>
        <div className="brand-glyph">
          <Layers size={18} />
        </div>
        <div>
          <div className="brand-title">Multimodal Studio</div>
          <div className="brand-subtitle">Adaptive Interview Intelligence</div>
        </div>
      </div>

      <nav className="nav-switcher">
        <button
          type="button"
          className={`nav-tab-btn ${isProfileActive ? 'active' : ''}`}
          onClick={() => navigate('/profile')}
        >
          <User size={15} />
          <span>Candidate Profiles</span>
        </button>

        <button
          type="button"
          className={`nav-tab-btn ${isResumeActive ? 'active' : ''}`}
          onClick={() => navigate('/resume')}
        >
          <FileText size={15} />
          <span>Resume Claims</span>
        </button>

        <button
          type="button"
          className={`nav-tab-btn ${isInterviewActive ? 'active' : ''}`}
          onClick={handleNavigateInterview}
        >
          <Video size={15} />
          <span>Interview Command Center</span>
        </button>

        <button
          type="button"
          className={`nav-tab-btn ${isRoadmapActive ? 'active' : ''}`}
          onClick={() => navigate('/roadmap')}
        >
          <Compass size={15} />
          <span>Skill Gaps & Roadmap</span>
        </button>

        <button
          type="button"
          className={`nav-tab-btn ${isCoachingActive || isChatActive ? 'active' : ''}`}
          onClick={handleNavigateCoaching}
          data-testid="nav-chat-btn"
        >
          <MessageSquare size={15} />
          <span>AI Coach</span>
        </button>

        <button
          type="button"
          className={`nav-tab-btn ${isAnalyticsActive ? 'active' : ''}`}
          onClick={() => navigate('/analytics')}
        >
          <BarChart2 size={15} />
          <span>Evidence Analytics</span>
        </button>

        <button
          type="button"
          className={`nav-tab-btn ${isStudyActive ? 'active' : ''}`}
          onClick={() => navigate('/study')}
          data-testid="nav-study-btn"
        >
          <FlaskConical size={15} />
          <span>Research Study</span>
        </button>
      </nav>

      <div className="nav-actions">
        <select
          className="form-select candidate-select"
          aria-label="Select Candidate Profile"
          value={selectedCandidate?.id || ''}
          onChange={(e) => {
            const found = candidates.find((c) => c.id === e.target.value);
            if (found) onSelectCandidate(found);
          }}
        >
          {candidates.length === 0 ? (
            <option value="">No Candidates Available</option>
          ) : (
            candidates.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))
          )}
        </select>

        <button
          type="button"
          className="btn btn-secondary btn-add-candidate"
          onClick={onOpenNewCandidateModal}
          title="Create New Candidate Profile"
          aria-label="Add Candidate"
          data-testid="navbar-add-candidate-btn"
        >
          <UserPlus size={14} />
          <span>Add Candidate</span>
        </button>
      </div>
    </header>
  );
};
