import React, { useState } from 'react';
import { ConversationDTO, Candidate } from '../../types';
import {
  Menu,
  Edit2,
  Check,
  X,
  Trash2,
  Layers,
  Video,
  Compass,
  User,
  Briefcase,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ChatHeaderProps {
  conversation?: ConversationDTO | null;
  candidate: Candidate | null;
  activeRole?: string;
  onToggleMobileSidebar: () => void;
  onRenameConversation: (newTitle: string) => Promise<void>;
  onDeleteConversation: () => Promise<void>;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  conversation,
  candidate,
  activeRole,
  onToggleMobileSidebar,
  onRenameConversation,
  onDeleteConversation,
}) => {
  const navigate = useNavigate();
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [isSubmittingRename, setIsSubmittingRename] = useState(false);

  const startRename = () => {
    if (!conversation) return;
    setEditTitle(conversation.title);
    setIsEditingTitle(true);
  };

  const handleSaveRename = async () => {
    if (!editTitle.trim() || !conversation) {
      setIsEditingTitle(false);
      return;
    }
    setIsSubmittingRename(true);
    try {
      await onRenameConversation(editTitle.trim());
      setIsEditingTitle(false);
    } catch (err) {
      console.error('Failed to rename conversation title:', err);
    } finally {
      setIsSubmittingRename(false);
    }
  };

  const handleDelete = async () => {
    if (!conversation) return;
    if (window.confirm('Delete this conversation thread permanently?')) {
      await onDeleteConversation();
    }
  };

  return (
    <header className="chat-main-header" data-testid="chat-header">
      <div className="header-left">
        <button
          type="button"
          className="btn-toggle-sidebar d-md-none"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle conversation sidebar"
          data-testid="toggle-sidebar-btn"
        >
          <Menu size={20} />
        </button>

        <div className="title-and-context">
          {conversation ? (
            isEditingTitle ? (
              <div className="header-title-edit-form">
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="header-rename-input"
                  autoFocus
                  disabled={isSubmittingRename}
                  data-testid="header-rename-input"
                />
                <button
                  type="button"
                  className="header-icon-btn check"
                  onClick={handleSaveRename}
                  disabled={isSubmittingRename}
                  title="Save title"
                >
                  <Check size={15} />
                </button>
                <button
                  type="button"
                  className="header-icon-btn cancel"
                  onClick={() => setIsEditingTitle(false)}
                  disabled={isSubmittingRename}
                  title="Cancel"
                >
                  <X size={15} />
                </button>
              </div>
            ) : (
              <div className="header-title-row">
                <h1 className="header-thread-title">{conversation.title}</h1>
                <button
                  type="button"
                  className="header-icon-btn edit-thread-btn"
                  onClick={startRename}
                  title="Rename thread"
                  data-testid="header-rename-btn"
                >
                  <Edit2 size={14} />
                </button>
              </div>
            )
          ) : (
            <h1 className="header-thread-title">New Conversation</h1>
          )}

          <div className="header-context-tags">
            {candidate && (
              <span className="context-chip">
                <User size={12} className="chip-icon" />
                <span>{candidate.full_name}</span>
              </span>
            )}
            <span className="context-chip">
              <Briefcase size={12} className="chip-icon" />
              <span>{activeRole || 'Software Engineer'}</span>
            </span>
          </div>
        </div>
      </div>

      <div className="header-actions">
        {/* Quick Cross-Module Jump Links */}
        <div className="header-module-shortcuts">
          <button
            type="button"
            className="btn btn-outline btn-sm shortcut-btn"
            onClick={() => navigate('/coaching')}
            title="Switch to AI Coaching Studio"
          >
            <Layers size={13} />
            <span className="d-none d-lg-inline">Coaching Studio</span>
          </button>
          <button
            type="button"
            className="btn btn-outline btn-sm shortcut-btn"
            onClick={() => navigate('/interview')}
            title="Switch to Interview Command Center"
          >
            <Video size={13} />
            <span className="d-none d-lg-inline">Interview Studio</span>
          </button>
          <button
            type="button"
            className="btn btn-outline btn-sm shortcut-btn"
            onClick={() => navigate('/roadmap')}
            title="Switch to Skill Gaps & Roadmap"
          >
            <Compass size={13} />
            <span className="d-none d-lg-inline">Roadmap</span>
          </button>
        </div>

        {conversation && (
          <button
            type="button"
            className="btn btn-danger-outline btn-sm"
            onClick={handleDelete}
            title="Delete this thread"
            data-testid="header-delete-btn"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </header>
  );
};
