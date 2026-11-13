import React, { useState } from 'react';
import { ConversationDTO } from '../../types';
import {
  MessageSquare,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  Search,
  AlertCircle,
  Loader2,
  Clock,
} from 'lucide-react';

interface ChatSidebarProps {
  conversations: ConversationDTO[];
  activeConversationId?: string;
  isLoading: boolean;
  error?: string | null;
  onSelectConversation: (id: string) => void;
  onCreateConversation: () => void;
  onRenameConversation: (id: string, newTitle: string) => Promise<void>;
  onDeleteConversation: (id: string) => Promise<void>;
  onRetry: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  activeConversationId,
  isLoading,
  error,
  onSelectConversation,
  onCreateConversation,
  onRenameConversation,
  onDeleteConversation,
  onRetry,
  isMobileOpen,
  onCloseMobile,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleStartRename = (c: ConversationDTO, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(c.id);
    setEditTitle(c.title);
  };

  const handleConfirmRename = async (id: string, e: React.MouseEvent | React.FormEvent) => {
    e.stopPropagation();
    if (!editTitle.trim()) {
      setEditingId(null);
      return;
    }
    setIsRenaming(true);
    try {
      await onRenameConversation(id, editTitle.trim());
      setEditingId(null);
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    } finally {
      setIsRenaming(false);
    }
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
    setEditTitle('');
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation thread?')) {
      setDeletingId(id);
      try {
        await onDeleteConversation(id);
      } catch (err) {
        console.error('Failed to delete conversation:', err);
      } finally {
        setDeletingId(null);
      }
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="chat-sidebar-backdrop"
          onClick={onCloseMobile}
          data-testid="sidebar-backdrop"
          aria-hidden="true"
        />
      )}

      <aside
        className={`chat-sidebar ${isMobileOpen ? 'mobile-open' : ''}`}
        data-testid="chat-sidebar"
      >
        <div className="chat-sidebar-header">
          <div className="sidebar-title-row">
            <div className="sidebar-brand">
              <MessageSquare size={18} className="brand-icon" />
              <span className="brand-text">Conversations</span>
            </div>
            <button
              type="button"
              className="btn-close-mobile d-md-none"
              onClick={onCloseMobile}
              aria-label="Close sidebar"
            >
              <X size={18} />
            </button>
          </div>

          <button
            type="button"
            className="btn btn-primary btn-new-chat"
            onClick={() => {
              onCreateConversation();
              if (isMobileOpen) onCloseMobile();
            }}
            data-testid="new-conversation-btn"
          >
            <Plus size={16} />
            <span>New Conversation</span>
          </button>

          {conversations.length > 3 && (
            <div className="sidebar-search-box">
              <Search size={14} className="search-icon" />
              <input
                type="text"
                placeholder="Search threads..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
                data-testid="conversation-search-input"
              />
            </div>
          )}
        </div>

        <div className="chat-sidebar-body">
          {isLoading && conversations.length === 0 && (
            <div className="sidebar-state-box" data-testid="sidebar-loading">
              <Loader2 size={20} className="spinner" />
              <span>Loading threads...</span>
            </div>
          )}

          {error && (
            <div className="sidebar-state-box error-box" data-testid="sidebar-error">
              <AlertCircle size={18} />
              <span>{error}</span>
              <button
                type="button"
                className="btn btn-secondary btn-xs"
                onClick={onRetry}
              >
                Retry
              </button>
            </div>
          )}

          {!isLoading && !error && conversations.length === 0 && (
            <div className="sidebar-empty-state" data-testid="sidebar-empty">
              <MessageSquare size={28} className="empty-icon text-muted" />
              <p className="empty-text">No conversation threads yet.</p>
              <span className="empty-hint">Create one to begin personalized coaching.</span>
            </div>
          )}

          {!error && filtered.length > 0 && (
            <ul className="conversation-list" role="list">
              {filtered.map((convo) => {
                const isActive = convo.id === activeConversationId;
                const isEditing = editingId === convo.id;
                const isDeleting = deletingId === convo.id;

                return (
                  <li
                    key={convo.id}
                    className={`conversation-item ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      if (!isEditing) {
                        onSelectConversation(convo.id);
                        if (isMobileOpen) onCloseMobile();
                      }
                    }}
                    data-testid={`conversation-item-${convo.id}`}
                  >
                    {isEditing ? (
                      <form
                        onSubmit={(e) => handleConfirmRename(convo.id, e)}
                        className="rename-form"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="rename-input"
                          autoFocus
                          disabled={isRenaming}
                          data-testid="rename-input"
                        />
                        <button
                          type="button"
                          className="icon-action-btn check-btn"
                          onClick={(e) => handleConfirmRename(convo.id, e)}
                          title="Save title"
                          disabled={isRenaming}
                        >
                          <Check size={14} />
                        </button>
                        <button
                          type="button"
                          className="icon-action-btn cancel-btn"
                          onClick={handleCancelRename}
                          title="Cancel"
                          disabled={isRenaming}
                        >
                          <X size={14} />
                        </button>
                      </form>
                    ) : (
                      <>
                        <div className="item-main">
                          <span className="item-title" title={convo.title}>
                            {convo.title}
                          </span>
                          <div className="item-meta">
                            <span className="item-time">
                              <Clock size={11} className="meta-icon" />
                              {formatDate(convo.updated_at || convo.created_at)}
                            </span>
                            {convo.messages_count !== undefined && convo.messages_count > 0 && (
                              <span className="item-badge">{convo.messages_count} msgs</span>
                            )}
                          </div>
                        </div>

                        <div className="item-actions">
                          <button
                            type="button"
                            className="item-btn"
                            onClick={(e) => handleStartRename(convo, e)}
                            title="Rename thread"
                            data-testid={`rename-btn-${convo.id}`}
                          >
                            <Edit2 size={13} />
                          </button>
                          <button
                            type="button"
                            className="item-btn delete-btn"
                            onClick={(e) => handleDelete(convo.id, e)}
                            title="Delete thread"
                            disabled={isDeleting}
                            data-testid={`delete-btn-${convo.id}`}
                          >
                            {isDeleting ? <Loader2 size={13} className="spinner" /> : <Trash2 size={13} />}
                          </button>
                        </div>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
};
