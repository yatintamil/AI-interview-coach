export interface SkillEntity {
  name: string;
  category: string;
  proficiency?: string;
  years_of_experience?: number;
}

export interface ProjectEntity {
  title: string;
  description: string;
  role?: string;
  technologies_used: string[];
  key_achievements: string[];
  project_url?: string;
}

export interface ExperienceEntity {
  company_name: string;
  designation: string;
  location?: string;
  start_date: string;
  end_date?: string;
  is_current?: boolean;
  domain?: string;
  responsibilities: string[];
  key_accomplishments: string[];
  technologies_used: string[];
}

export interface EducationEntity {
  institution: string;
  degree: string;
  field_of_study: string;
  start_year?: number;
  end_year?: number;
  gpa_or_score?: string;
  honors: string[];
}

export interface CandidateProfile {
  full_name: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  skills: SkillEntity[];
  projects: ProjectEntity[];
  experience: ExperienceEntity[];
  education: EducationEntity[];
  technologies: string[];
  domains: string[];
  soft_skills?: string[];
  certifications?: { name: string; issuing_organization?: string; issue_date?: string }[];
  achievements?: { title: string; description?: string }[];
  seniority_level?: string;
  recommended_roles?: string[];
  total_years_experience?: number;
  total_years_exp?: number;
  extraction_confidence_score: number;
  personalized_dossier?: {
    candidate_id: string;
    candidate_name: string;
    target_role: string;
    researched_skills: {
      skill_name: string;
      formal_title: string;
      web_summary: string;
      core_principles: string[];
      sample_interview_inquiries: string[];
      source_urls: string[];
    }[];
    custom_curriculum: {
      stage_index: number;
      stage_name: string;
      focus_skill: string;
      domain_inquiry: string;
      expected_concepts: string[];
      pedagogical_goal: string;
    }[];
    web_sources_consulted: string[];
    total_skills_researched: number;
  };
}

export interface ResumeSummary {
  id: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  processing_status: string;
  is_active: boolean;
  created_at: string;
  uploaded_at?: string;
}

export type CandidateReadinessState =
  | 'NO_RESUME'
  | 'RESUME_PROCESSING'
  | 'PROFILE_READY'
  | 'ROLE_READY'
  | 'ASSESSMENT_READY'
  | 'COACHING_READY'
  | 'TRANSFER_READY';

export interface CandidateReadinessResponse {
  candidate_id: string;
  readiness_state: CandidateReadinessState;
  is_resume_uploaded: boolean;
  is_resume_processed: boolean;
  is_profile_ready: boolean;
  is_role_selected: boolean;
  target_role?: string | null;
  is_assessment_ready: boolean;
  completed_interviews_count: number;
  is_coaching_ready: boolean;
  is_transfer_ready: boolean;
  allowed_features: string[];
  blocked_features: Record<string, string>;
  next_action: {
    action: string;
    route: string;
    title: string;
    rationale: string;
  };
}

export interface Candidate {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
  resumes: ResumeSummary[];
  has_profile: boolean;
  skills_summary: string[];
  total_years_exp: number;
  readiness_state?: CandidateReadinessState;
  target_role?: string | null;
}

export interface RoleRecommendation {
  role_key: string;
  display_name: string;
  match_score: number;
  match_percentage: number;
  is_recommended: boolean;
  recommendation_rationale: string;
  supporting_evidence: string[];
  unverified_concepts: string[];
  uncertainty_note: string;
}

export interface RoleRecommendationsResponse {
  candidate_id: string;
  has_resume_evidence: boolean;
  readiness_state: string;
  total_recommendations?: number;
  message?: string;
  recommendations: RoleRecommendation[];
}

export interface Question {
  id: string;
  session_id: string;
  question_index: number;
  question_text: string;
  category: string;
  topic: string;
  difficulty: string;
  stage_name?: string;
  stage_index?: number;
  total_stages?: number;
  target_competency?: string;
  assessment_objective?: string;
  is_followup?: boolean;
  resume_evidence?: string;
  expected_concepts: string[];
  coach_lead_in?: string;
  researched_skill?: string;
  created_at: string;
}

export interface EvidenceItem {
  claim: string;
  basis: string;
}

export interface TurnEvaluation {
  id: string;
  answer_id: string;
  question_id: string;
  session_id: string;
  overall_score: number;
  correctness: number;
  completeness: number;
  relevance: number;
  technical_depth: number;
  reasoning: number;
  strengths: string[];
  weaknesses: string[];
  missing_concepts: string[];
  evidence: EvidenceItem[];
  recommendations: string[];
  exemplar_answer?: string;
  coach_note?: string;
  detected_feeling?: string;
  coach_conversational_response?: string;
  socratic_scaffold?: string;
  created_at: string;
}

export interface CoachHint {
  question_id: string;
  hint_text: string;
  pedagogical_nudge: string;
  key_concept_to_consider: string;
}

export interface TurnAnswerResult {
  evaluation: TurnEvaluation;
  next_question?: Question;
  is_completed: boolean;
  current_question_index: number;
  total_questions: number;
  active_competency_status?: string;
  role_competency_profile?: RoleCompetencyProfile;
  is_followup_probe?: boolean;
  completion_reason?: string;
  evidence_coverage_ratio?: number;
  competencies_assessed_count?: number;
  total_competencies_count?: number;
}

export interface QuestionTurnHistory {
  question: Question;
  answer?: {
    id: string;
    answer_text: string;
    response_time_seconds: number;
    submitted_at: string;
  };
  evaluation?: TurnEvaluation;
}

export interface RoleCompetencyRecord {
  competency_id: string;
  name?: string;
  competency_name?: string;
  description?: string;
  importance?: string;
  coverage_status: 'UNASSESSED' | 'PARTIALLY_ASSESSED' | 'SUFFICIENT_EVIDENCE';
  questions_asked?: number;
  average_score?: number;
  scores?: number[];
  concepts_demonstrated?: string[];
  demonstrated_concepts?: string[];
  missing_concepts?: string[];
  strengths?: string[];
  weaknesses?: string[];
}

export interface RoleCompetencyProfile {
  target_role?: string;
  role_name?: string;
  target_roles?: string[];
  seniority?: string;
  provenance?: string;
  total_competencies?: number;
  sufficient_evidence_count?: number;
  partially_assessed_count?: number;
  unassessed_count?: number;
  competency_coverage_ratio?: number;
  overall_coverage_ratio?: number;
  overall_competency_score?: number;
  competency_records: Record<string, RoleCompetencyRecord>;
}

export interface SessionReport {
  id: string;
  session_id: string;
  final_score: number;
  technical_score: number;
  behavioral_score: number;
  communication_score: number;
  summary_strengths: string[];
  summary_weaknesses: string[];
  key_recommendations: string[];
  role_competency_profile?: RoleCompetencyProfile;
  generated_at: string;
}

export interface InterviewSession {
  id: string;
  candidate_id: string;
  resume_id?: string;
  target_role: string;
  target_roles?: string[];
  custom_role_description?: string;
  interview_type: string;
  difficulty_level: string;
  coaching_mode?: string;
  status: string;
  target_question_count: number;
  current_question_index: number;
  completion_reason?: string;
  evidence_coverage_ratio?: number;
  competencies_assessed_count?: number;
  total_competencies_count?: number;
  start_time?: string;
  end_time?: string;
  created_at: string;
  current_question?: Question;
  history: QuestionTurnHistory[];
  report?: SessionReport;
}

export interface PerformanceTrendPoint {
  session_id: string;
  date: string;
  target_role: string;
  interview_type: string;
  overall_score: number;
  technical_score: number;
  behavioral_score: number;
  communication_score: number;
}

export interface KnowledgeGapItem {
  concept: string;
  occurrences: number;
  topic: string;
  recommendation: string;
}

export interface AnalyticsOverview {
  candidate_id: string;
  total_interviews: number;
  completed_interviews: number;
  overall_average_score: number;
  technical_average_score: number;
  behavioral_average_score: number;
  communication_average_score: number;
  top_strengths: string[];
  common_weaknesses: string[];
  key_recommendations: string[];
  latest_session?: PerformanceTrendPoint;
}

export type ClaimVerificationStatus = 'UNVERIFIED' | 'PROBED' | 'VERIFIED' | 'CONTESTED';

export interface CandidateClaim {
  id: string;
  candidate_id: string;
  resume_id?: string;
  skill_name: string;
  claim_text: string;
  complexity: 'FOUNDATIONAL' | 'INTERMEDIATE' | 'ADVANCED' | 'SYSTEM_LEVEL';
  verification_status: ClaimVerificationStatus;
  confidence_score: number; // 0.0 to 1.0
  verified_quotes: string[];
  supporting_quote?: string;
  evidence_source?: string;
  probe_count: number;
}

export interface CandidateEvidenceGraph {
  candidate_id: string;
  total_claims: number;
  verified_count: number;
  probed_count: number;
  overall_verification_ratio: number;
  claims: CandidateClaim[];
}

export * from './coaching';
export * from './chat';
