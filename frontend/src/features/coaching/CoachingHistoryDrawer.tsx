import React, { useState } from 'react';
import {
  MessageSquare,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  TrendingUp,
  Video,
  Map,
  ChevronRight,
} from 'lucide-react';
import { ConversationDTO, Candidate } from '../../types';

interface CoachingHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: ConversationDTO[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onCreateNewConversation: () => void;
  onRenameConversation: (id: string, newTitle: string) => Promise<void>;
  onDeleteConversation: (id: string) => Promise<void>;
  isLoadingList: boolean;
  selectedCandidate: Candidate | null;
  onNavigateToRoadmap?: () => void;
  onNavigateToInterview?: () => void;
  activeSessionId?: string | null;
}

export const CoachingHistoryDrawer: React.FC<CoachingHistoryDrawerProps> = ({
  isOpen,
  onClose,
  conversations,
  activeConversationId,
  onSelectConversation,
  onCreateNewConversation,
  onRenameConversation,
  onDeleteConversation,
  isLoadingList,
  selectedCandidate,
  onNavigateToRoadmap,
  onNavigateToInterview,
  activeSessionId,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  const handleStartRename = (convo: ConversationDTO, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(convo.id);
    setEditingTitle(convo.title);
  };

  const handleSaveRename = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editingTitle.trim()) {
      await onRenameConversation(id, editingTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this coaching thread?')) {
      await onDeleteConversation(id);
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="coaching-drawer-backdrop visible"
          data-testid="sidebar-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Main Drawer Panel */}
      <aside
        className={`coaching-history-drawer ${isOpen ? 'open' : 'closed'}`}
        data-testid="chat-sidebar"
        aria-label="Coaching conversation history"
      >
        <div className="drawer-header-pane">
          <div className="drawer-title-row">
            <span className="drawer-heading">Sessions & History</span>
            <button
              type="button"
              className="drawer-close-btn"
              onClick={onClose}
              title="Close drawer"
              aria-label="Close drawer"
            >
              <X size={16} />
            </button>
          </div>

          <button
            type="button"
            className="btn-new-coaching-session"
            data-testid="new-conversation-btn"
            onClick={onCreateNewConversation}
          >
            <Plus size={16} />
            <span>New Coaching Session</span>
          </button>
        </div>

        {/* Conversation Threads List */}
        <div className="drawer-scroll-section">
          <div className="drawer-subhead">
            <span>Conversations</span>
            <span className="badge-count">{conversations.length}</span>
          </div>

          {isLoadingList ? (
            <div className="drawer-loading-state">
              <span className="loading-spinner-small"></span>
              <span>Loading sessions...</span>
            </div>
          ) : conversations.length === 0 ? (
            <div className="drawer-empty-state">
              <p>No active coaching threads.</p>
              <button
                type="button"
                className="btn-link-start"
                onClick={onCreateNewConversation}
              >
                Start a session
              </button>
            </div>
          ) : (
            <ul className="drawer-thread-list">
              {conversations.map((c) => {
                const isActive = c.id === activeConversationId;
                const isEditing = c.id === editingId;

                return (
                  <li
                    key={c.id}
                    className={`drawer-thread-item ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      if (!isEditing) onSelectConversation(c.id);
                    }}
                    role="button"
                    tabIndex={0}
                    data-testid={`conversation-item-${c.id}`}
                  >
                    <div className="thread-icon">
                      <MessageSquare size={14} />
                    </div>

                    {isEditing ? (
                      <div className="thread-rename-row">
                        <input
                          type="text"
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          className="input-rename-field"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(c.id, e as any);
                            if (e.key === 'Escape') handleCancelRename(e as any);
                          }}
                        />
                        <button
                          type="button"
                          className="btn-icon-save"
                          onClick={(e) => handleSaveRename(c.id, e)}
                        >
                          <Check size={13} />
                        </button>
                        <button
                          type="button"
                          className="btn-icon-cancel"
                          onClick={handleCancelRename}
                        >
                          <X size={13} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="thread-content-block">
                          <span className="thread-title" title={c.title}>
                            {c.title}
                          </span>
                          <span className="thread-meta">
                            {new Date(c.updated_at).toLocaleDateString([], {
                              month: 'short',
                              day: 'numeric',
                            })}
                            {c.messages_count !== undefined && c.messages_count > 0 && (
                              <> • {c.messages_count} msgs</>
                            )}
                          </span>
                        </div>

                        <div className="thread-actions">
                          <button
                            type="button"
                            className="btn-thread-action"
                            onClick={(e) => handleStartRename(c, e)}
                            title="Rename"
                            aria-label="Rename conversation"
                          >
                            <Edit2 size={12} />
                          </button>
                          <button
                            type="button"
                            className="btn-thread-action delete"
                            onClick={(e) => handleDelete(c.id, e)}
                            title="Delete"
                            aria-label="Delete conversation"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}

          {/* Quick Learning Goals & Growth Bridge */}
          <div className="drawer-growth-bridge-card">
            <div className="growth-card-title">
              <TrendingUp size={14} />
              <span>Skill Progress & Goals</span>
            </div>
            <p className="growth-card-desc">
              Transfer coaching directly updates your verified skill evidence and adapts your interview readiness.
            </p>

            <div className="growth-card-actions">
              {onNavigateToRoadmap && (
                <button
                  type="button"
                  className="btn-growth-action"
                  onClick={onNavigateToRoadmap}
                >
                  <Map size={13} />
                  <span>Personalized Roadmap</span>
                  <ChevronRight size={12} />
                </button>
              )}
              {onNavigateToInterview && (
                <button
                  type="button"
                  className="btn-growth-action"
                  onClick={onNavigateToInterview}
                >
                  <Video size={13} />
                  <span>Interview Command Center</span>
                  <ChevronRight size={12} />
                </button>
              )}
            </div>

            {selectedCandidate && (
              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle, #e2e8f0)', fontSize: '0.75rem', color: 'var(--text-tertiary, #64748b)' }}>
                <span>Active Candidate: {selectedCandidate.full_name}</span>
                {activeSessionId && (
                  <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted, #94a3b8)', marginTop: '2px' }}>
                    Session: {activeSessionId.slice(0, 8)}...
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
};
