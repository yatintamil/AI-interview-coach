/**
 * Strongly-typed contracts for Transfer-Aware Coaching & Research.
 * Strictly aligned with backend Phase 4, Phase 5A, and Phase 5B DTOs.
 */

export type CoachingState =
  | 'IDLE'
  | 'TRAINING'
  | 'UNDERSTANDING_CHECK'
  | 'TRAINING_EVALUATION'
  | 'TRANSFER_ATTEMPT'
  | 'TRANSFER_DIAGNOSIS'
  | 'COACHING_DECISION'
  | 'INTERVENTION'
  | 'RETRY'
  | 'RETRY_EVALUATION'
  | 'INDEPENDENT_TRANSFER'
  | 'COMPLETED'
  | 'FAILED';

export type CoachingLoopOutcome =
  | 'TRAINING_SUCCESS'
  | 'TRANSFER_SUCCESS'
  | 'TRANSFER_FAILURE'
  | 'RETRY_SUCCESS'
  | 'RETRY_FAILURE'
  | 'RETRY_LIMIT_REACHED'
  | 'INDEPENDENT_SUCCESS'
  | 'INDEPENDENT_FAILURE';

export type TransferLevel =
  | 'L0_RECALL'
  | 'L1_DIRECT_APPLICATION'
  | 'L2_NEAR_TRANSFER'
  | 'L3_FAR_TRANSFER'
  | 'L4_AMBIGUOUS_TRANSFER'
  | 'L5_INDEPENDENT_TRANSFER';

export const CANONICAL_TRANSFER_LABELS: Record<TransferLevel, string> = {
  L0_RECALL: 'L0 Recall',
  L1_DIRECT_APPLICATION: 'L1 Direct Application',
  L2_NEAR_TRANSFER: 'L2 Near Transfer',
  L3_FAR_TRANSFER: 'L3 Far Transfer',
  L4_AMBIGUOUS_TRANSFER: 'L4 Ambiguous Transfer',
  L5_INDEPENDENT_TRANSFER: 'L5 Independent Transfer',
};

export function formatTransferLevel(level?: string | null): string {
  if (!level) return 'L3 Far Transfer';
  const normalized = level.trim().toUpperCase();
  if (normalized in CANONICAL_TRANSFER_LABELS) {
    return CANONICAL_TRANSFER_LABELS[normalized as TransferLevel];
  }
  // Safe canonical format fallback (e.g. L0 Recall, L1 Direct Application, etc.)
  return normalized
    .replace(/^L(\d)_/, 'L$1 ')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/^L(\d)\s/, 'L$1 ');
}

export type ScaffoldLevel =
  | 'HIGH_ASSISTANCE'
  | 'MEDIUM_ASSISTANCE'
  | 'LOW_ASSISTANCE'
  | 'INDEPENDENT';

export type CoachingInterventionType =
  | 'HINT'
  | 'DIRECT_EXPLANATION'
  | 'WORKED_EXAMPLE'
  | 'ANALOGY'
  | 'COUNTEREXAMPLE'
  | 'SOCRATIC_QUESTION'
  | 'METACOGNITIVE_PROMPT'
  | 'CONCEPT_MAP'
  | 'DECOMPOSITION'
  | 'CONSTRAINT_RELAXATION'
  | 'ERROR_IDENTIFICATION'
  | 'PARSONS_PROBLEM'
  | 'TRANSFER_CHALLENGE';

export type TransferFailureType =
  | 'SURFACE_FEATURE_OVERFITTING'
  | 'INVARIANT_VIOLATION'
  | 'MISAPPLIED_ANALOGY'
  | 'NEGATIVE_TRANSFER'
  | 'PREMATURE_GENERALIZATION'
  | 'WEAK_REQUIREMENT_ANALYSIS'
  | 'OVER_ENGINEERING'
  | 'UNDER_SPECIFICATION'
  | 'MISSING_CONCEPTUAL_MODEL'
  | 'ALGORITHMIC_INCORRECTNESS'
  | 'INEFFICIENT_COMPLEXITY'
  | 'REASONING_FAILURE'
  | 'NONE';

export interface EvidenceItemDTO {
  claim: string;
  basis: string;
}

export interface TransferTaskDTO {
  id: string;
  parent_task_id?: string | null;
  skill_id: string;
  transfer_level: TransferLevel;
  surface_context: string;
  core_invariants: string[];
  surface_distractors?: string[];
  expected_concepts: string[];
  rubric_id?: string | null;
  prompt_template?: string | null;
}

export interface CoachingEvaluationDTO {
  overall_score: number;
  correctness?: number;
  completeness?: number;
  relevance?: number;
  technical_depth?: number;
  reasoning?: number;
  strengths?: string[];
  weaknesses?: string[];
  missing_concepts?: string[];
  recommendations?: string[];
  exemplar_answer?: string;
  coach_note?: string;
}

export interface TransferDiagnosisDTO {
  failure_type: TransferFailureType;
  confidence: number;
  affected_skill: string;
  deterministic_signals?: Record<string, unknown>;
  evidence?: EvidenceItemDTO[];
  recommended_intervention: CoachingInterventionType;
  diagnostic_reasoning: string;
}

export interface CoachingInterventionDTO {
  intervention_type: CoachingInterventionType;
  scaffold_level: ScaffoldLevel;
  content: string;
  pedagogical_intent: string;
  is_faded?: boolean;
  retry_required?: boolean;
}

export interface ScaffoldStateDTO {
  current_level: ScaffoldLevel;
  previous_level: ScaffoldLevel;
  is_faded: boolean;
  assistance_dependency_index: number;
  transition_reason?: string | null;
}

export interface CandidateSkillStateDTO {
  candidate_id: string;
  skill_name: string;
  mastery_estimate: number;
  mastery_uncertainty: number;
  highest_transfer_level: TransferLevel;
  assistance_dependency_index: number;
  recurring_failure_types?: TransferFailureType[];
  total_attempts: number;
  last_assessed_at?: string | null;
}

export interface OrchestratorStepResultDTO {
  state: CoachingState;
  outcome: CoachingLoopOutcome;
  task?: TransferTaskDTO | null;
  training_context?: TrainingContextDTO | null;
  session_id?: string | null;
  candidate_id?: string | null;
  evaluation?: CoachingEvaluationDTO | null;
  diagnosis?: TransferDiagnosisDTO | null;
  intervention?: CoachingInterventionDTO | null;
  scaffold_state?: ScaffoldStateDTO | null;
  retry_count: number;
  retry_limit_reached: boolean;
  candidate_state?: CandidateSkillStateDTO | null;
  transition_reason?: string | null;
}

export interface TrainingContextDTO {
  task_id: string;
  question_text: string;
  skill_id: string;
  core_invariants: string[];
  base_surface_context: string;
  base_expected_concepts: string[];
  topic?: string | null;
  target_role?: string | null;
  weakness?: string | null;
  evidence?: string[] | null;
  current_mastery?: number | null;
  transfer_level?: string | null;
  role_importance?: string | null;
  learning_objective?: string | null;
  teaching_lesson?: string | null;
}

export interface CoachingSessionConfigDTO {
  max_retries?: number;
  transfer_level?: TransferLevel;
  independent_level?: TransferLevel;
  pass_threshold?: number;
  independent_pass_threshold?: number;
  min_independent_distance?: number;
  policy_version?: string;
}

export interface StartCoachingLoopPayload {
  candidate_id: string;
  session_id: string;
  training_context: TrainingContextDTO;
  config?: CoachingSessionConfigDTO | null;
}

export interface CandidateStepInputDTO {
  candidate_answer: string;
  response_time_seconds?: number;
  hints_requested_count?: number;
}

export interface SubmitCoachingStepPayload {
  session_id: string;
  step_input: CandidateStepInputDTO;
}

export interface ResearchTelemetryRecordDTO {
  candidate_id: string;
  session_id: string;
  skill_id: string;
  training_context: TrainingContextDTO;
  transfer_task_id?: string | null;
  transfer_level: TransferLevel;
  independent_task_id?: string | null;
  attempts_history: Array<Record<string, unknown>>;
}

/**
 * UI Presentation state mapped from backend state.
 */
export type UIPresentationState =
  | 'IDLE'
  | 'TRAINING'
  | 'UNDERSTANDING_CHECK'
  | 'EVALUATING'
  | 'TRANSFER'
  | 'COACHING'
  | 'RETRY'
  | 'INDEPENDENT_TRANSFER'
  | 'COMPLETED'
  | 'ERROR';

export interface StartCoachingFromInterviewPayload {
  candidate_id: string;
  interview_session_id: string;
  session_id?: string;
  question_id?: string;
  config?: CoachingSessionConfigDTO;
}

export interface InterviewWeaknessItem {
  question_id: string;
  topic: string;
  category: string;
  skill_id: string;
  is_canonical_skill: boolean;
  overall_score: number;
  weaknesses: string[];
  missing_concepts: string[];
  recommendations: string[];
  training_context: TrainingContextDTO;
}

export interface InterviewWeaknessesResponse {
  session_id: string;
  candidate_id: string;
  total_weaknesses: number;
  weaknesses: InterviewWeaknessItem[];
}

export interface AutonomousCoachingRecommendation {
  candidate_id: string;
  candidate_name: string;
  target_role: string;
  has_evidence: boolean;
  evidence_source: 'INTERVIEW_EVALUATION' | 'ROADMAP_GAP' | 'SKILL_STATE' | 'COLD_START';
  recommended_skill_id: string;
  recommended_skill_title: string;
  justification: string;
  learning_objective: string;
  scaffold_level: ScaffoldLevel | string;
  target_transfer_level: string;
  action_type: 'START_LEARNING' | 'RESUME_COACHING' | 'DIAGNOSTIC_OR_FOUNDATIONAL';
  interview_context?: {
    topic: string;
    score: number;
    question_text: string;
    weaknesses: string[];
    missing_concepts: string[];
    session_id: string;
    question_id: string;
  } | null;
}

