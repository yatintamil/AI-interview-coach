import React, { useEffect, useRef } from 'react';
import { ConversationMessageDTO, Candidate } from '../../types';
import { StructuredResponseRenderer } from './StructuredResponseRenderer';
import {
  User,
  Bot,
  Compass,
  Lightbulb,
  GitBranch,
  Award,
  HelpCircle,
  Clock,
} from 'lucide-react';

interface ChatMessageListProps {
  messages: ConversationMessageDTO[];
  candidate: Candidate | null;
  activeRole?: string;
  isSending: boolean;
  onSelectPrompt: (promptText: string) => void;
}

export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  candidate,
  activeRole,
  isSending,
  onSelectPrompt,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const quickStarters = [
    {
      icon: <HelpCircle size={16} className="starter-icon text-indigo" />,
      title: 'Practice Interview',
      prompt: `Start a mock interview practice for ${activeRole || 'Software Engineer'}`,
      desc: 'Get an in-depth technical inquiry with expected core invariants.',
    },
    {
      icon: <GitBranch size={16} className="starter-icon text-cyan" />,
      title: 'Transfer Challenge',
      prompt: 'Test me on an unfamiliar transfer problem with structural invariants',
      desc: 'Challenge your schema induction on novel system problems.',
    },
    {
      icon: <Lightbulb size={16} className="starter-icon text-amber" />,
      title: 'Socratic Hint',
      prompt: 'Can you give me a hint on designing an idempotency layer?',
      desc: 'Receive scaffolded reasoning without giving away solutions.',
    },
    {
      icon: <Compass size={16} className="starter-icon text-emerald" />,
      title: 'Learning Roadmap',
      prompt: 'Show my learning roadmap',
      desc: 'Inspect your curriculum milestones and competency gaps.',
    },
    {
      icon: <Award size={16} className="starter-icon text-violet" />,
      title: 'Skill Progress',
      prompt: 'Show my progress and mastery level',
      desc: 'Check your verified mastery estimates across competencies.',
    },
  ];

  const formatMessageTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const renderContentText = (text: string) => {
    // Process markdown-like lines: bold, paragraphs
    const paragraphs = text.split('\n\n');
    return paragraphs.map((p, pIdx) => {
      const lines = p.split('\n');
      return (
        <p key={pIdx} className="message-paragraph">
          {lines.map((line, lIdx) => {
            // Replace **bold** with <strong>
            const parts = line.split(/(\*\*.*?\*\*)/g);
            return (
              <React.Fragment key={lIdx}>
                {parts.map((part, ptIdx) => {
                  if (part.startsWith('**') && part.endsWith('**')) {
                    return <strong key={ptIdx}>{part.slice(2, -2)}</strong>;
                  }
                  return part;
                })}
                {lIdx < lines.length - 1 && <br />}
              </React.Fragment>
            );
          })}
        </p>
      );
    });
  };

  if (messages.length === 0) {
    return (
      <div className="chat-empty-stream" data-testid="chat-empty-stream">
        <div className="welcome-banner">
          <div className="welcome-avatar">
            <Compass size={24} />
          </div>
          <h2 className="welcome-title">
            Welcome{candidate ? `, ${candidate.full_name}` : ''}!
          </h2>
          <p className="welcome-subtitle">
            I am your Transfer-Aware AI Interview Coach. Ask technical questions, practice realistic
            interview turns, request Socratic scaffolding, or tackle cross-domain transfer tasks.
          </p>
        </div>

        <div className="quick-starters-grid">
          {quickStarters.map((qs, idx) => (
            <button
              key={idx}
              type="button"
              className="quick-starter-card"
              onClick={() => onSelectPrompt(qs.prompt)}
              data-testid={`starter-card-${idx}`}
            >
              <div className="starter-header">
                {qs.icon}
                <span className="starter-title">{qs.title}</span>
              </div>
              <p className="starter-desc">{qs.desc}</p>
              <span className="starter-action">Ask Coach &rarr;</span>
            </button>
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
    );
  }

  return (
    <div className="chat-message-stream" data-testid="chat-message-stream">
      {messages.map((msg) => {
        const isUser = msg.role === 'user';

        return (
          <div
            key={msg.id || `${msg.role}-${msg.sequence}`}
            className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}
            data-testid={`message-${msg.role}-${msg.sequence}`}
          >
            <div className="message-avatar">
              {isUser ? (
                <div className="avatar-circle user-avatar">
                  <User size={15} />
                </div>
              ) : (
                <div className="avatar-circle coach-avatar">
                  <Bot size={15} />
                </div>
              )}
            </div>

            <div className="message-body">
              <div className="message-meta-header">
                <span className="sender-name">
                  {isUser ? candidate?.full_name || 'Candidate' : 'AI Interview Coach'}
                </span>
                {!isUser && msg.intent && (
                  <span className="intent-badge">
                    {msg.intent.replace(/_/g, ' ')}
                  </span>
                )}
                {!isUser && (msg.ui_payload?.is_fallback || msg.content.includes('Offline Adaptive Curriculum Fallback')) && (
                  <span
                    className="intent-badge fallback-indicator-badge"
                    data-testid="fallback-indicator"
                    style={{
                      background: 'rgba(217, 119, 6, 0.15)',
                      color: '#d97706',
                      borderColor: 'rgba(217, 119, 6, 0.3)',
                    }}
                  >
                    Offline Fallback Curriculum
                  </span>
                )}
                {!isUser && msg.ui_payload?.provider_used && (
                  <span
                    className="provider-badge"
                    data-testid="provider-indicator"
                    style={{
                      fontSize: '0.68rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: 'rgba(100, 116, 139, 0.1)',
                      color: '#64748b',
                    }}
                  >
                    {msg.ui_payload.is_fallback ? 'Engine: Offline Adaptive' : `Live: ${msg.ui_payload.provider_used.split(':')[0]}`}
                  </span>
                )}
                {msg.created_at && (
                  <span className="message-timestamp">
                    <Clock size={11} className="meta-icon" />
                    {formatMessageTime(msg.created_at)}
                  </span>
                )}
              </div>

              <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
                {renderContentText(msg.content)}
              </div>

              {/* Structured UI Card */}
              {msg.ui_payload && (
                <div className="message-payload-container" data-testid="message-payload">
                  <StructuredResponseRenderer payload={msg.ui_payload} />
                </div>
              )}
            </div>
          </div>
        );
      })}

      {isSending && (
        <div className="message-row assistant-row typing-row" data-testid="typing-indicator">
          <div className="message-avatar">
            <div className="avatar-circle coach-avatar pulse">
              <Bot size={15} />
            </div>
          </div>
          <div className="message-body">
            <div className="typing-indicator-bubble">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
              <span className="typing-label">Analyzing invariants & synthesizing response...</span>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
