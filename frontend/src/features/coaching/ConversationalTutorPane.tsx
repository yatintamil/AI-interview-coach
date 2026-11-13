import React, { useRef, useEffect } from 'react';
import {
  Send,
  Loader2,
  AlertTriangle,
  RotateCcw,
  MessageSquare,
  User,
  Bot,
} from 'lucide-react';
import { ConversationMessageDTO } from '../../types';
import { StructuredResponseRenderer } from '../../components/chat/StructuredResponseRenderer';
import { MarkdownRenderer } from '../../components/common/MarkdownRenderer';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';

export interface PromptChip {
  label: string;
  prompt: string;
}

interface ConversationalTutorPaneProps {
  messages: ConversationMessageDTO[];
  isSending: boolean;
  onSendMessage: (text: string) => Promise<void>;
  suggestedPrompts: PromptChip[];
  providerFallbackNotice?: string | null;
  onRetryLastTurn?: () => void;
  error?: string | null;
}

export const ConversationalTutorPane: React.FC<ConversationalTutorPaneProps> = ({
  messages,
  isSending,
  onSendMessage,
  suggestedPrompts,
  providerFallbackNotice,
  onRetryLastTurn,
  error,
}) => {
  const [inputText, setInputText] = React.useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const handleSend = async () => {
    if (!inputText.trim() || isSending) return;
    const toSend = inputText;
    setInputText('');
    await onSendMessage(toSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSelectPrompt = (prompt: string) => {
    setInputText(prompt);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  return (
    <div className="conversational-tutor-pane" data-testid="chat-page">
      {/* Provider Fallback Notice Banner */}
      {providerFallbackNotice && (
        <div className="provider-fallback-banner">
          <div className="fallback-banner-content">
            <AlertTriangle size={15} className="fallback-icon" />
            <span>{providerFallbackNotice}</span>
          </div>
          {onRetryLastTurn && (
            <button
              type="button"
              className="btn-retry-fallback"
              onClick={onRetryLastTurn}
              disabled={isSending}
            >
              <RotateCcw size={13} />
              <span>Retry</span>
            </button>
          )}
        </div>
      )}

      {/* General Error Banner */}
      {error && (
        <div className="coaching-error-banner">
          <AlertTriangle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Messages Stream */}
      <div className="tutor-messages-scroll" data-testid="chat-message-list">
        {messages.length === 0 ? (
          <div className="tutor-welcome-empty">
            <Card variant="raised" className="welcome-console-card">
              <CardHeader>
                <div className="welcome-avatar-icon">
                  <MessageSquare size={20} />
                </div>
                <CardTitle>Conversational Learning Workspace</CardTitle>
                <CardDescription>
                  Targeted conceptual coaching and architectural explanations for your active competency.
                  Ask technical questions, request worked examples, or test your reasoning.
                </CardDescription>
              </CardHeader>
              {suggestedPrompts.length > 0 && (
                <CardContent>
                  <div className="welcome-prompt-buttons-wrap">
                    {suggestedPrompts.map((chip, idx) => (
                      <Button
                        key={idx}
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleSelectPrompt(chip.prompt)}
                      >
                        {chip.label}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.role === 'user';

            return (
              <div
                key={msg.id || index}
                className={`message-bubble-row ${isUser ? 'user-turn' : 'coach-turn'}`}
              >
                <div className="message-speaker-avatar">
                  {isUser ? <User size={15} /> : <Bot size={16} />}
                </div>

                <div className="message-content-wrapper">
                  <div className="message-header-line">
                    <span className="speaker-name">{isUser ? 'Candidate' : 'AI Coach'}</span>
                    <span className="message-timestamp">
                      {msg.created_at
                        ? new Date(msg.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : ''}
                    </span>
                  </div>

                  {/* Render Structured UI Card if present */}
                  {msg.ui_payload && (
                    <div className="message-card-slot">
                      <StructuredResponseRenderer
                        payload={msg.ui_payload}
                      />
                    </div>
                  )}

                  {/* Text / Markdown Content */}
                  {msg.content && (
                    <div className="message-text-body">
                      <MarkdownRenderer content={msg.content} />
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {isSending && (
          <div className="message-bubble-row coach-turn" data-testid="typing-indicator">
            <div className="message-speaker-avatar">
              <Bot size={16} />
            </div>
            <div className="message-content-wrapper">
              <div className="typing-pulse-dots">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="typing-label">Reasoning Socratic response...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Chips */}
      {suggestedPrompts.length > 0 && (
        <div className="suggested-prompts-bar">
          <span className="prompts-label">Quick Prompts:</span>
          <div className="prompts-chips-list">
            {suggestedPrompts.map((chip, idx) => (
              <button
                key={idx}
                type="button"
                className="chip-prompt-btn"
                onClick={() => handleSelectPrompt(chip.prompt)}
                disabled={isSending}
              >
                <span>{chip.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message Composer */}
      <div className="tutor-composer-panel" data-testid="chat-composer">
        <div className="composer-input-row">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            data-testid="chat-message-input"
            placeholder="Ask your coach anything, explore invariants, or request a worked example... (Enter to send, Shift+Enter for newline)"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={isSending}
          />

          <button
            type="button"
            className="btn-composer-send"
            data-testid="send-message-btn"
            onClick={handleSend}
            disabled={!inputText.trim() || isSending}
            title="Send message (Enter)"
            aria-label="Send message"
          >
            {isSending ? <Loader2 size={18} className="spin-icon" /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
};
