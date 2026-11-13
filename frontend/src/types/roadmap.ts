/**
 * Phase 2 Personalized Learning Roadmap and Skill Gap TypeScript Definitions.
 */

export type SkillGapPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'SATISFIED';
export type RoadmapItemStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'PRACTICING' | 'COMPLETED';
export type RoadmapStatus = 'ACTIVE' | 'ARCHIVED' | 'COMPLETED';

export interface SkillGapDTO {
  skill_id: string;
  skill_name: string;
  role_importance: string;
  candidate_mastery: number;
  mastery_uncertainty: number;
  required_mastery: number;
  raw_gap: number;
  highest_transfer_level: string;
  transfer_deficit: number;
  effective_gap: number;
  assistance_dependency: number;
  recurring_failure_types: string[];
  priority_score: number;
  priority: SkillGapPriority;
  priority_rank: number;
  proficiency_state?: 'DEMONSTRATED_COMPETENCY' | 'PARTIALLY_DEMONSTRATED' | 'DEMONSTRATED_WEAKNESS' | 'NOT_ASSESSED' | 'NO_EVIDENCE' | string;
  is_measured_proficiency?: boolean;
  reasoning: string;
  learning_objective: string;
  core_invariants: string[];
  actionable_steps: string[];
}

export interface ExcludedCompetencyInfo {
  skill_id: string;
  skill_name: string;
  reason: string;
  classification?: string;
}

export interface SkillGapAnalysisResult {
  candidate_id: string;
  target_role: string;
  seniority: string;
  total_competencies_evaluated: number;
  satisfied_competencies: number;
  gaps_detected: number;
  total_role_competencies?: number;
  assessed_competencies_count?: number;
  unassessed_competencies_count?: number;
  excluded_competencies?: ExcludedCompetencyInfo[];
  gaps: SkillGapDTO[];
  analyzed_at: string;
}

export interface RoadmapItemDTO {
  id: string;
  roadmap_id: string;
  skill_id: string;
  skill_title: string;
  role_importance: string;
  priority: SkillGapPriority;
  sequence_order: number;
  learning_objective: string;
  rationale: string;
  current_mastery: number;
  target_mastery: number;
  current_transfer_level: string;
  target_transfer_level: string;
  assistance_dependency: number;
  status: RoadmapItemStatus;
  coaching_session_id?: string | null;
  core_invariants: string[];
  recurring_failures: string[];
  actionable_steps: string[];
  topics_to_study?: string[];
  practical_exercises?: string[];
  implementation_task?: {
    title: string;
    description: string;
    technology_stack: string[];
    acceptance_criteria: string[];
  };
  expected_deliverables?: string[];
  estimated_duration?: string;
  difficulty_level?: string;
  evaluation_criteria?: string[];
  evidence_required?: string | null;
  prerequisite_milestone_ids?: string[];
  mapping_status?: string;
  is_flagged_for_review?: boolean;
  progression_tier?: string;
  proficiency_state?: string;
  is_measured_proficiency?: boolean;
  notes?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonalizedRoadmapDTO {
  id: string;
  candidate_id: string;
  target_role: string;
  seniority: string;
  status: RoadmapStatus;
  overall_progress: number;
  total_items: number;
  completed_items: number;
  total_role_competencies?: number;
  assessed_competencies_count?: number;
  unassessed_competencies_count?: number;
  identified_gaps_count?: number;
  milestones_generated_count?: number;
  excluded_competencies?: ExcludedCompetencyInfo[];
  summary?: string | null;
  items: RoadmapItemDTO[];
  meta_info?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface StartCoachingFromRoadmapResponse {
  item_id: string;
  roadmap_id: string;
  skill_id: string;
  coaching_session_id: string;
  orchestrator_state: Record<string, any>;
  training_context: Record<string, any>;
}
