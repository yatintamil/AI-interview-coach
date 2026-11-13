export type ExperimentCondition = 'CONDITION_A' | 'CONDITION_B' | 'CONDITION_C';

export interface PerformanceMetrics {
  pretest_mean: number | null;
  training_mean: number | null;
  posttest_mean: number | null;
  transfer_mean: number | null;
  near_transfer_mean: number | null;
  far_transfer_mean: number | null;
  ambiguous_transfer_mean: number | null;
  independent_transfer_mean: number | null;
}

export interface LearningGainMetrics {
  absolute_gain: number | null;
  normalized_gain: number | null;
}

export interface TransferMetrics {
  transfer_delta: number | null;
  independent_transfer_delta: number | null;
  transfer_preservation_ratio: number | null;
  independent_transfer_ratio: number | null;
  transfer_failure_rate: number | null;
  l5_independent_transfer_achieved: boolean;
  retention_ratio: number | null;
  retention_status?: string;
}

export interface RecoveryMetrics {
  retry_attempts: number;
  successful_retries: number;
  retry_recovery_rate: number | null;
  mean_score_improvement_after_intervention: number | null;
  diagnosis_count: number;
  targeted_intervention_count: number;
  diagnosis_specific_recovery_rate: Record<string, number>;
  diagnosis_associated_recovery_rate?: number | null;
  diagnosis_accuracy_rate: number | null;
  diagnosis_accuracy_status?: string;
}

export interface AssistanceMetrics {
  total_hints: number;
  hint_rate: number | null;
  mean_scaffold_level: number | null;
  scaffold_reduction: number | null;
  independent_assistance_rate: number;
  high_assistance_events: number;
  medium_assistance_events: number;
  low_assistance_events: number;
  independent_events: number;
}

export interface LearningEfficiencyMetrics {
  score_gain_per_intervention: number | null;
  score_gain_per_retry: number | null;
  score_gain_per_hint: number | null;
  time_to_success: number | null;
}

export interface CandidateResearchResult {
  candidate_id: string;
  experiment_session_id: string;
  condition: ExperimentCondition;
  skill: string;
  is_completed: boolean;
  total_trials: number;
  performance: PerformanceMetrics;
  learning_gain: LearningGainMetrics;
  transfer: TransferMetrics;
  recovery: RecoveryMetrics;
  assistance: AssistanceMetrics;
  efficiency: LearningEfficiencyMetrics;
}

export interface DescriptiveStats {
  sample_count: number;
  mean: number | null;
  median: number | null;
  standard_deviation: number | null;
  minimum: number | null;
  maximum: number | null;
}

export interface ResearchConditionSummary {
  condition: ExperimentCondition;
  session_count: number;
  completed_session_count: number;
  pretest: DescriptiveStats;
  posttest: DescriptiveStats;
  absolute_gain: DescriptiveStats;
  normalized_gain: DescriptiveStats;
  transfer: DescriptiveStats;
  independent_transfer: DescriptiveStats;
  transfer_failure_rate: DescriptiveStats;
  diagnosis_associated_recovery_rate?: DescriptiveStats;
  diagnosis_accuracy_rate: DescriptiveStats;
  diagnosis_accuracy_status?: string;
  independent_transfer_achievement_rate: number | null;
  retention_ratio: DescriptiveStats;
  retention_status?: string;
  retry_recovery_rate: DescriptiveStats;
  hint_rate: DescriptiveStats;
  scaffold_reduction: DescriptiveStats;
  total_hints_consumed: number;
  total_retries: number;
  total_interventions: number;
  total_diagnoses: number;
}

export interface MetricComparisonRow {
  metric_name: string;
  condition_a: DescriptiveStats;
  condition_b: DescriptiveStats;
  condition_c: DescriptiveStats;
}

export interface ConditionComparison {
  condition_summaries: Record<string, ResearchConditionSummary>;
  metrics: MetricComparisonRow[];
}

export interface StudyInformation {
  study_id: string;
  title: string;
  principal_investigator: string;
  purpose: string;
  procedures: string;
  risks_and_benefits: string;
  voluntary_participation: string;
  data_handling: string;
  ethics_statement: string;
  consent_version: string;
  withdrawal_policy: string;
}

export interface ConsentRecord {
  id: string;
  candidate_id: string;
  consent_status: 'CONSENTED' | 'WITHDRAWN' | 'DECLINED';
  consent_version: string;
  consented_at: string;
  withdrawn_at?: string | null;
  withdrawal_reason?: string | null;
  study_title: string;
}

export interface ExperimentTrialRaw {
  trial_id: string;
  session_id: string;
  task_id: string;
  phase: string;
  transfer_level?: string | null;
  transfer_distance?: number | null;
  difficulty?: string | null;
  attempt_number: number;
  score: number;
  outcome: string;
  response_time_seconds: number;
  feedback_text?: string | null;
  candidate_answer_text?: string | null;
  intervention_type?: string | null;
  scaffold_level?: string | null;
  hints_requested_count: number;
  retry_count: number;
  diagnosis_type?: string | null;
  timestamp: string;
}

export interface ExperimentStepResult {
  session_id: string;
  condition: ExperimentCondition;
  phase: string;
  task_id: string;
  task_prompt: string;
  task_difficulty?: string | null;
  transfer_level?: string | null;
  score?: number | null;
  feedback?: string | null;
  intervention?: string | null;
  scaffold_level?: string | null;
  is_complete: boolean;
  raw_trial?: ExperimentTrialRaw | null;
}

export interface ActiveSessionResponse {
  has_active_session: boolean;
  session?: {
    session_id: string;
    candidate_id: string;
    experiment_name: string;
    condition: ExperimentCondition;
    skill: string;
    current_phase: string;
    status: string;
    trials: ExperimentTrialRaw[];
  } | null;
  current_task_prompt?: string | null;
}

export interface ParticipantWithdrawalResult {
  candidate_id: string;
  status: string;
  withdrawn_at: string;
  sessions_abandoned: number;
  retention_schedules_cancelled: number;
  message: string;
}

export interface RetentionSchedule {
  id: string;
  session_id: string;
  candidate_id: string;
  delay_days: number;
  due_date: string;
  status: string;
  retention_session_id?: string | null;
  created_at: string;
}
