"""
SQLAlchemy ORM models package initialization.
Exports all database entity models to ensure unified metadata registration and prevent circular mapper errors.
"""

from backend.models.base import Base
from backend.models.candidate import CandidateModel, CandidateProfileModel
from backend.models.resume import ResumeModel
from backend.models.embedding import ResumeChunkModel
from backend.models.interview import (
    InterviewSessionModel,
    QuestionModel,
    AnswerModel,
    EvaluationModel,
    SessionReportModel,
)
from backend.models.resume_claim import CandidateClaimModel
from backend.models.skill_state import CandidateSkillStateModel
from backend.models.transfer_task import TransferTaskModel, TransferAttemptModel
from backend.models.transfer_diagnosis import TransferDiagnosisModel
from backend.models.experiment import (
    ExperimentSessionModel,
    ExperimentTrialModel,
    ExperimentParticipantAssignmentModel,
    ExperimentConsentModel,
    ExperimentRetentionScheduleModel,
)
from backend.models.roadmap import PersonalizedRoadmapModel, RoadmapItemModel
from backend.models.conversation import ConversationModel, ConversationMessageModel

__all__ = [
    "Base",
    "CandidateModel",
    "CandidateProfileModel",
    "ResumeModel",
    "ResumeChunkModel",
    "InterviewSessionModel",
    "QuestionModel",
    "AnswerModel",
    "EvaluationModel",
    "SessionReportModel",
    "CandidateClaimModel",
    "CandidateSkillStateModel",
    "TransferTaskModel",
    "TransferAttemptModel",
    "TransferDiagnosisModel",
    "CoachingInterventionEventModel",
    "ExperimentSessionModel",
    "ExperimentTrialModel",
    "ExperimentParticipantAssignmentModel",
    "ExperimentConsentModel",
    "ExperimentRetentionScheduleModel",
    "PersonalizedRoadmapModel",
    "RoadmapItemModel",
    "ConversationModel",
    "ConversationMessageModel",
]

