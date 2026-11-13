export { CANONICAL_TRANSFER_LABELS, formatTransferLevel } from './coaching';

export type ChatRole = 'user' | 'assistant' | 'system' | 'tool';

export type ChatIntent =
  | 'GENERAL_CHAT'
  | 'INTERVIEW'
  | 'EVALUATION'
  | 'SKILL_GAP'
  | 'ROADMAP'
  | 'TRANSFER'
  | 'COACHING'
  | 'SESSION_STATUS';

export interface StructuredUIPayload {
  type: string;
  role?: string;
  topic?: string;
  expected_invariants?: string[];
  core_invariants?: string[];
  invariants?: string[];
  transfer_level?: string;
  scaffold_level?: string;
  guiding_question?: string;
  hint?: string;
  hint_level?: number;
  top_gaps?: Array<{
    skill_id: string;
    skill_name: string;
    gap: number;
  }>;
  skills?: Array<{
    skill: string;
    mastery: number;
    transfer_level: string;
  }>;
  score?: number;
  feedback?: string;
  rubric_breakdown?: Record<string, any>;
  [key: string]: any;
}

export interface ConversationMessageDTO {
  id: string;
  conversation_id: string;
  role: ChatRole | string;
  content: string;
  message_type: 'text' | 'card' | string;
  ui_payload?: StructuredUIPayload | null;
  intent?: ChatIntent | string | null;
  sequence: number;
  created_at: string;
}

export interface ConversationDTO {
  id: string;
  candidate_id?: string | null;
  title: string;
  status: string;
  metadata?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  messages_count?: number;
}

export interface ConversationDetailDTO {
  id: string;
  candidate_id?: string | null;
  title: string;
  status: string;
  metadata?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  messages: ConversationMessageDTO[];
}

export interface CreateConversationRequest {
  candidate_id?: string;
  title?: string;
  metadata?: Record<string, any>;
}

export interface RenameConversationRequest {
  title: string;
}

export interface SendMessageRequest {
  content: string;
  candidate_id?: string;
  target_role?: string;
  focus_skill?: string;
  metadata?: Record<string, any>;
}

export interface SendMessageResponse {
  conversation_id: string;
  user_message: ConversationMessageDTO;
  assistant_message: ConversationMessageDTO;
  detected_intent: ChatIntent | string;
  is_fallback?: boolean;
  provider_used?: string;
  stage_timings?: Record<string, any>;
}

export interface InitiateCoachingRequest {
  candidate_id?: string;
  conversation_id?: string;
  target_role?: string;
  focus_skill?: string;
  interview_session_id?: string;
  question_id?: string;
}

export interface InitiateCoachingResponse {
  conversation: ConversationDetailDTO;
  focus_skill: string;
  learning_objective: string;
  why_it_matters: string;
  target_role: string;
  scaffold_level: string;
  active_phase: string;
  is_resumed: boolean;
}
