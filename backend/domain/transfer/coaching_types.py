"""
Coaching Intervention Taxonomy and Scaffold Levels.

Defines the 13-tier controlled intervention ladder and assistance levels
designed for minimum effective intervention and systematic scaffold fading.
"""

from enum import Enum
from typing import Dict


class CoachingInterventionType(str, Enum):
    """
    Controlled intervention ladder ordered conceptually from least intrusive
    (maximum candidate autonomy) to most intrusive (explicit instruction).
    """
    WAIT = "WAIT"
    """Deliberate silence or neutral encouragement allowing the candidate space to self-correct."""

    CLARIFICATION = "CLARIFICATION"
    """Restatement or clarification of the problem constraints without suggesting solutions."""

    PROMPT = "PROMPT"
    """Gentle direction to focus attention on a specific neglected aspect or requirement."""

    MINIMAL_HINT = "MINIMAL_HINT"
    """High-level conceptual nudge without providing algorithmic details or solutions."""

    SOCRATIC_QUESTION = "SOCRATIC_QUESTION"
    """Targeted question designed to lead the candidate to discover the missing principle themselves."""

    DECOMPOSITION = "DECOMPOSITION"
    """Guiding the candidate to break the complex problem into smaller, tractable sub-problems."""

    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    """Presenting an edge case or scenario where the candidate's current assumption breaks down."""

    ANALOGY = "ANALOGY"
    """Mapping the difficult concept to a familiar conceptual domain to rebuild intuition."""

    WORKED_EXAMPLE = "WORKED_EXAMPLE"
    """Demonstrating the resolution of a structurally parallel problem with explicit step-by-step reasoning."""

    EXPLANATION = "EXPLANATION"
    """Direct instructional explanation of the theoretical mechanism or missing conceptual model."""

    REFLECTION = "REFLECTION"
    """Prompting the candidate to critically evaluate their own solution, trade-offs, and invariants."""

    RETRY = "RETRY"
    """Requesting the candidate re-attempt the task or variant with learned insights."""

    TRANSFER_CHALLENGE = "TRANSFER_CHALLENGE"
    """Advancing the candidate to a novel unseen transfer test at higher situational distance."""


class ScaffoldLevel(str, Enum):
    """
    Assistance intensity tier, monitored to evaluate assistance dependency (H3)
    and drive scaffold fading.
    """
    HIGH_ASSISTANCE = "HIGH_ASSISTANCE"
    """Direct explanations, worked examples, explicit structural solutions."""

    MEDIUM_ASSISTANCE = "MEDIUM_ASSISTANCE"
    """Decomposition, counterexamples, analogies."""

    LOW_ASSISTANCE = "LOW_ASSISTANCE"
    """Socratic questions, minimal hints, directional prompts."""

    INDEPENDENT = "INDEPENDENT"
    """Zero AI hints or guidance; unassisted autonomous candidate execution."""


DEFAULT_INTERVENTION_SCAFFOLD: Dict[CoachingInterventionType, ScaffoldLevel] = {
    CoachingInterventionType.WAIT: ScaffoldLevel.INDEPENDENT,
    CoachingInterventionType.CLARIFICATION: ScaffoldLevel.LOW_ASSISTANCE,
    CoachingInterventionType.PROMPT: ScaffoldLevel.LOW_ASSISTANCE,
    CoachingInterventionType.MINIMAL_HINT: ScaffoldLevel.LOW_ASSISTANCE,
    CoachingInterventionType.SOCRATIC_QUESTION: ScaffoldLevel.LOW_ASSISTANCE,
    CoachingInterventionType.DECOMPOSITION: ScaffoldLevel.MEDIUM_ASSISTANCE,
    CoachingInterventionType.COUNTEREXAMPLE: ScaffoldLevel.MEDIUM_ASSISTANCE,
    CoachingInterventionType.ANALOGY: ScaffoldLevel.MEDIUM_ASSISTANCE,
    CoachingInterventionType.WORKED_EXAMPLE: ScaffoldLevel.HIGH_ASSISTANCE,
    CoachingInterventionType.EXPLANATION: ScaffoldLevel.HIGH_ASSISTANCE,
    CoachingInterventionType.REFLECTION: ScaffoldLevel.LOW_ASSISTANCE,
    CoachingInterventionType.RETRY: ScaffoldLevel.LOW_ASSISTANCE,
    CoachingInterventionType.TRANSFER_CHALLENGE: ScaffoldLevel.INDEPENDENT,
}


class CoachingLoopOutcome(str, Enum):
    """
    Standard outcome classifications distinguishing assisted and independent performance
    across the transfer coaching lifecycle.
    """
    TRAINING_SUCCESS = "TRAINING_SUCCESS"
    TRANSFER_SUCCESS = "TRANSFER_SUCCESS"
    TRANSFER_FAILURE = "TRANSFER_FAILURE"
    RETRY_SUCCESS = "RETRY_SUCCESS"
    RETRY_FAILURE = "RETRY_FAILURE"
    INDEPENDENT_SUCCESS = "INDEPENDENT_SUCCESS"
    INDEPENDENT_FAILURE = "INDEPENDENT_FAILURE"
    RETRY_LIMIT_REACHED = "RETRY_LIMIT_REACHED"

