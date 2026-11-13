"""
Constants and Configuration Parameters for Skill Gap Analysis and Prioritization.
Enforces deterministic, transparent, and explainable calculations.
"""

from backend.domain.role.models import CompetencyImportance
from backend.domain.transfer.taxonomy import TransferLevel

# Prioritization Formula Weights (Sum = 1.0)
# P = w_gap * effective_gap + w_role * role_score + w_fail * recurring_fail_score + w_unc * uncertainty
WEIGHT_EFFECTIVE_GAP: float = 0.45
WEIGHT_ROLE_IMPORTANCE: float = 0.30
WEIGHT_RECURRING_FAILURE: float = 0.15
WEIGHT_EPISTEMIC_UNCERTAINTY: float = 0.10

# Normalized numerical scale for role importance
ROLE_IMPORTANCE_SCORES = {
    CompetencyImportance.CORE: 1.0,
    CompetencyImportance.SECONDARY: 0.70,
    CompetencyImportance.SPECIALIZED: 0.50,
    CompetencyImportance.CROSS_FUNCTIONAL: 0.40,
}

# Baseline required mastery by importance tier
BASE_REQUIRED_MASTERY = {
    CompetencyImportance.CORE: 0.80,
    CompetencyImportance.SECONDARY: 0.65,
    CompetencyImportance.SPECIALIZED: 0.60,
    CompetencyImportance.CROSS_FUNCTIONAL: 0.60,
}

# Seniority adjustments to required mastery
SENIORITY_MASTERY_MODIFIERS = {
    "junior": -0.10,
    "entry": -0.10,
    "mid": 0.0,
    "intermediate": 0.0,
    "senior": 0.05,
    "lead": 0.08,
    "staff": 0.10,
    "principal": 0.10,
}

# Transfer deficit penalties by highest demonstrated transfer level
# Accounts for gap between "can answer in interview" and "can independently apply in unseen context"
TRANSFER_DEFICIT_PENALTIES = {
    TransferLevel.L0_RECALL: 0.35,
    TransferLevel.L1_DIRECT_APPLICATION: 0.25,
    TransferLevel.L2_NEAR_TRANSFER: 0.15,
    TransferLevel.L3_FAR_TRANSFER: 0.08,
    TransferLevel.L4_AMBIGUOUS_TRANSFER: 0.03,
    TransferLevel.L5_INDEPENDENT_TRANSFER: 0.0,
}

# Priority Classification Thresholds
THRESHOLD_CRITICAL: float = 0.70
THRESHOLD_HIGH: float = 0.50
THRESHOLD_MEDIUM: float = 0.30

# Satisfaction Criteria Thresholds
MAX_SATISFIED_GAP: float = 0.05
MAX_SATISFIED_ADI: float = 0.25
