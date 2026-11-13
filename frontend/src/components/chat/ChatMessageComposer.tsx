import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Compass } from 'lucide-react';

interface ChatMessageComposerProps {
  onSendMessage: (text: string) => Promise<void>;
  isSending: boolean;
  disabled?: boolean;
  activeRole?: string;
}

export const ChatMessageComposer: React.FC<ChatMessageComposerProps> = ({
  onSendMessage,
  isSending,
  disabled = false,
  activeRole,
}) => {
  const [inputText, setInputText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const quickPrompts = [
    'Start a mock interview',
    'Give me a Socratic hint',
    'Test me on a transfer challenge',
    'Show my learning roadmap',
  ];

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    const trimmed = inputText.trim();
    if (!trimmed || isSending || disabled) return;

    // Immediately clear input to prevent double submission
    setInputText('');

    try {
      await onSendMessage(trimmed);
    } catch {
      // If error occurs, restore input so candidate does not lose their typed response
      setInputText(trimmed);
    }
  };

  const handleQuickPromptClick = (prompt: string) => {
    if (isSending || disabled) return;
    setInputText(prompt);
    textareaRef.current?.focus();
  };

  // Adjust textarea height dynamically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [inputText]);

  return (
    <div className="chat-composer-container" data-testid="chat-composer">
      {/* Quick Prompts Bar */}
      <div className="composer-quick-chips">
        <Compass size={12} className="chips-icon text-secondary" />
        <span className="chips-label">Quick actions:</span>
        <div className="chips-scroll">
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              type="button"
              className="chip-btn"
              onClick={() => handleQuickPromptClick(p)}
              disabled={isSending || disabled}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="composer-input-row">
        <textarea
          ref={textareaRef}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Message AI Coach... (Targeting ${activeRole || 'Software Engineer'})`}
          rows={1}
          className="composer-textarea"
          disabled={disabled || isSending}
          aria-label="Chat message input"
          data-testid="chat-message-input"
        />

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!inputText.trim() || isSending || disabled}
          className="btn btn-primary btn-send-message"
          aria-label="Send message"
          data-testid="send-message-btn"
        >
          {isSending ? <Loader2 size={16} className="spinner" /> : <Send size={16} />}
        </button>
      </div>

      <div className="composer-footer-hint">
        <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for a new line.</span>
      </div>
    </div>
  );
};
