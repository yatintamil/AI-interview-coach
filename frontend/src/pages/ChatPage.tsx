import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAppSession } from '../context/AppSessionContext';
import {
  ConversationDTO,
  ConversationDetailDTO,
  ConversationMessageDTO,
} from '../types';
import { ChatSidebar } from '../components/chat/ChatSidebar';
import { ChatHeader } from '../components/chat/ChatHeader';
import { ChatMessageList } from '../components/chat/ChatMessageList';
import { ChatMessageComposer } from '../components/chat/ChatMessageComposer';
import { AlertCircle, Loader2, MessageSquarePlus } from 'lucide-react';

export const ChatPage: React.FC = () => {
  const { conversationId } = useParams<{ conversationId?: string }>();
  const navigate = useNavigate();
  const { selectedCandidate, selectedCandidateId, activeRoleId } = useAppSession();
  const effectiveCandidateId = selectedCandidate?.id || selectedCandidateId;

  // Sidebar conversations state
  const [conversations, setConversations] = useState<ConversationDTO[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  // Active conversation state
  const [activeConversation, setActiveConversation] = useState<ConversationDetailDTO | null>(null);
  const [isLoadingConvo, setIsLoadingConvo] = useState(false);
  const [convoError, setConvoError] = useState<string | null>(null);

  // Message sending state
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  // Mobile drawer state
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // 1. Fetch conversations list for selected candidate
  const fetchConversations = useCallback(async () => {
    setIsLoadingList(true);
    setListError(null);
    try {
      const list = await api.listConversations(effectiveCandidateId);
      setConversations(list);
      return list;
    } catch (err: any) {
      setListError(err.message || 'Failed to load conversations.');
      return [];
    } finally {
      setIsLoadingList(false);
    }
  }, [effectiveCandidateId]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // 2. Fetch active conversation details if conversationId exists
  const candidateIdRef = React.useRef(effectiveCandidateId);
  useEffect(() => {
    candidateIdRef.current = effectiveCandidateId;
  }, [effectiveCandidateId]);

  const fetchActiveConversation = useCallback(
    async (id: string) => {
      setIsLoadingConvo(true);
      setConvoError(null);
      try {
        const detail = await api.getConversation(id, candidateIdRef.current);
        setActiveConversation(detail);
      } catch (err: any) {
        setConvoError(err.message || 'Failed to load conversation history.');
        setActiveConversation(null);
      } finally {
        setIsLoadingConvo(false);
      }
    },
    []
  );

  useEffect(() => {
    if (conversationId) {
      fetchActiveConversation(conversationId);
    } else {
      setActiveConversation(null);
    }
  }, [conversationId, fetchActiveConversation]);

  // If on /chat with no conversationId and conversations exist, redirect to most recent
  useEffect(() => {
    if (!conversationId && conversations.length > 0 && !isLoadingList) {
      navigate(`/chat/${conversations[0].id}`, { replace: true });
    }
  }, [conversationId, conversations, isLoadingList, navigate]);

  // 3. Create conversation handler
  const handleCreateConversation = async (initialTitle?: string): Promise<string> => {
    const title = initialTitle || 'New Conversation';
    try {
      const newConvo = await api.createConversation({
        candidate_id: effectiveCandidateId,
        title,
        metadata: {
          target_role: activeRoleId || 'Software Engineer',
        },
      });
      await fetchConversations();
      navigate(`/chat/${newConvo.id}`);
      return newConvo.id;
    } catch (err: any) {
      alert(`Could not create conversation: ${err.message}`);
      throw err;
    }
  };

  // 4. Rename conversation handler
  const handleRenameConversation = async (id: string, newTitle: string) => {
    try {
      await api.renameConversation(id, newTitle, effectiveCandidateId);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
      );
      if (activeConversation && activeConversation.id === id) {
        setActiveConversation({ ...activeConversation, title: newTitle });
      }
    } catch (err: any) {
      alert(`Failed to rename conversation: ${err.message}`);
      throw err;
    }
  };

  // 5. Delete conversation handler
  const handleDeleteConversation = async (id: string) => {
    try {
      await api.deleteConversation(id, effectiveCandidateId);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (conversationId === id) {
        if (remaining.length > 0) {
          navigate(`/chat/${remaining[0].id}`, { replace: true });
        } else {
          setActiveConversation(null);
          navigate('/chat', { replace: true });
        }
      }
    } catch (err: any) {
      alert(`Failed to delete conversation: ${err.message}`);
      throw err;
    }
  };

  // 6. Send message handler (duplicate submission prevention built-in)
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isSending) return;

    setIsSending(true);
    setSendError(null);

    let targetConvoId = conversationId;

    try {
      // If no active conversation exists yet, create one first
      if (!targetConvoId) {
        const generatedTitle = text.length > 35 ? `${text.slice(0, 32)}...` : text;
        targetConvoId = await handleCreateConversation(generatedTitle);
      }

      // Optimistically show user message while processing
      const tempUserMsg: ConversationMessageDTO = {
        id: `temp-${Date.now()}`,
        conversation_id: targetConvoId,
        role: 'user',
        content: text,
        message_type: 'text',
        sequence: (activeConversation?.messages.length || 0) + 1,
        created_at: new Date().toISOString(),
      };

      if (activeConversation) {
        setActiveConversation({
          ...activeConversation,
          messages: [...activeConversation.messages, tempUserMsg],
        });
      }

      const response = await api.sendChatMessage(targetConvoId, {
        content: text,
        candidate_id: effectiveCandidateId,
        target_role: activeRoleId || 'Software Engineer',
      });

      // Update active conversation with authoritative persisted turns
      setActiveConversation((prev) => {
        if (!prev) {
          return {
            id: response.conversation_id,
            candidate_id: effectiveCandidateId,
            title: text.slice(0, 30),
            status: 'ACTIVE',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            messages: [response.user_message, response.assistant_message],
          };
        }
        // Filter out temporary optimistic message and append authoritative turns
        const filtered = prev.messages.filter((m) => !m.id.startsWith('temp-'));
        return {
          ...prev,
          messages: [...filtered, response.user_message, response.assistant_message],
        };
      });

      // Update conversation list count & timestamp
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConvoId
            ? {
                ...c,
                messages_count: (c.messages_count || 0) + 2,
                updated_at: new Date().toISOString(),
              }
            : c
        )
      );
    } catch (err: any) {
      setSendError(err.message || 'Error sending message. Please try again.');
      // Revert optimistic user message if failed
      if (activeConversation) {
        setActiveConversation({
          ...activeConversation,
          messages: activeConversation.messages.filter((m) => !m.id.startsWith('temp-')),
        });
      }
      throw err;
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="chat-page-layout" data-testid="chat-page">
      {/* Sidebar: Conversation Thread History */}
      <ChatSidebar
        conversations={conversations}
        activeConversationId={conversationId}
        isLoading={isLoadingList}
        error={listError}
        onSelectConversation={(id) => navigate(`/chat/${id}`)}
        onCreateConversation={() => handleCreateConversation()}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        onRetry={fetchConversations}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Conversation Area */}
      <div className="chat-main-area" data-testid="chat-main-area">

        <ChatHeader
          conversation={activeConversation}
          candidate={selectedCandidate}
          activeRole={activeRoleId}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen((prev) => !prev)}
          onRenameConversation={(newTitle) =>
            conversationId ? handleRenameConversation(conversationId, newTitle) : Promise.resolve()
          }
          onDeleteConversation={() =>
            conversationId ? handleDeleteConversation(conversationId) : Promise.resolve()
          }
        />

        {convoError ? (
          <div className="chat-error-state" data-testid="chat-error-state">
            <AlertCircle size={32} className="text-danger" />
            <h3 className="error-title">Failed to load conversation history</h3>
            <p className="error-detail">{convoError}</p>
            <div className="error-actions">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => conversationId && fetchActiveConversation(conversationId)}
              >
                Retry
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => handleCreateConversation()}
              >
                <MessageSquarePlus size={14} />
                <span>Start New Thread</span>
              </button>
            </div>
          </div>
        ) : isLoadingConvo ? (
          <div className="chat-loading-state" data-testid="chat-loading-state">
            <Loader2 size={32} className="spinner" />
            <p>Loading dialogue history...</p>
          </div>
        ) : (
          <div className="chat-messages-container">
            <ChatMessageList
              messages={activeConversation?.messages || []}
              candidate={selectedCandidate}
              activeRole={activeRoleId}
              isSending={isSending}
              onSelectPrompt={handleSendMessage}
            />
          </div>
        )}

        {sendError && (
          <div className="chat-send-error-toast" data-testid="send-error-toast">
            <AlertCircle size={15} />
            <span>{sendError}</span>
            <button
              type="button"
              className="toast-close-btn"
              onClick={() => setSendError(null)}
            >
              &times;
            </button>
          </div>
        )}

        {/* Message Composer */}
        <ChatMessageComposer
          onSendMessage={handleSendMessage}
          isSending={isSending}
          disabled={isLoadingConvo || Boolean(convoError)}
          activeRole={activeRoleId}
        />
      </div>
    </div>
  );
};
