"""
Transfer Failure Root-Cause Diagnostics.

Defines the diagnostic taxonomy for classifying why a candidate failed
to successfully transfer competence to an unseen interview scenario.
"""

from enum import Enum


class TransferFailureType(str, Enum):
    """
    Classifies the hypothesized primary root cause of transfer failure.
    These classes are empirically testable and drive targeted coaching interventions.
    """
    SURFACE_PATTERN_DEPENDENCE = "SURFACE_PATTERN_DEPENDENCE"
    """Candidate relied on memorized keywords/architecture from training; fails when domain surface changes."""

    MISSING_CONCEPTUAL_MODEL = "MISSING_CONCEPTUAL_MODEL"
    """Candidate lacks fundamental conceptual understanding of the underlying mechanism."""

    WEAK_REQUIREMENT_ANALYSIS = "WEAK_REQUIREMENT_ANALYSIS"
    """Candidate jumps into implementation without analyzing invariants, constraints, or edge cases."""

    POOR_ABSTRACTION = "POOR_ABSTRACTION"
    """Candidate cannot separate core theoretical invariants from incidental implementation details."""

    REASONING_FAILURE = "REASONING_FAILURE"
    """Candidate exhibits invalid logical deductions, erroneous trade-off proofs, or flawed complexity analysis."""

    COMMUNICATION_BREAKDOWN = "COMMUNICATION_BREAKDOWN"
    """Candidate possesses conceptual knowledge but fails to structure, articulate, or defend the thesis."""

    COGNITIVE_OVERLOAD = "COGNITIVE_OVERLOAD"
    """Candidate demonstrates high hesitation, erratic progression, or breakdown under increased task complexity."""

    EXCESSIVE_SCAFFOLD_DEPENDENCY = "EXCESSIVE_SCAFFOLD_DEPENDENCY"
    """Candidate solves sub-steps only when continuously prompted, showing inability to operate independently."""

    NONE = "NONE"
    """No transfer failure detected; candidate demonstrated successful independent transfer."""
