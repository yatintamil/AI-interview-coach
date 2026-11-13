"""
Project Domain Transfer Taxonomy.

NOTICE:
The L0-L5 hierarchy defined here represents our configurable PROJECT DOMAIN TAXONOMY
for categorizing situational transfer distance in technical interviews,
not an established universal psychometric measurement scale.
"""

from enum import Enum
from typing import Dict


class TransferLevel(str, Enum):
    """
    Categorizes the degree of situational distance between a training task
    and an evaluation task.
    """
    L0_RECALL = "L0_RECALL"
    """Direct retrieval of concepts, definitions, or established facts with no variation."""

    L1_DIRECT_APPLICATION = "L1_DIRECT_APPLICATION"
    """Application of the trained skill to an identical domain with the same structural setup."""

    L2_NEAR_TRANSFER = "L2_NEAR_TRANSFER"
    """Same underlying invariants and mechanics, but minor surface context or framing change."""

    L3_FAR_TRANSFER = "L3_FAR_TRANSFER"
    """Different application domain requiring the candidate to identify and map structural invariants."""

    L4_AMBIGUOUS_TRANSFER = "L4_AMBIGUOUS_TRANSFER"
    """Incomplete requirements, noisy constraints, or conflicting trade-offs requiring disambiguation."""

    L5_INDEPENDENT_TRANSFER = "L5_INDEPENDENT_TRANSFER"
    """Novel, unseen scenario presented with zero scaffolding, assessing autonomous capability."""


TRANSFER_LEVEL_RANKS: Dict[TransferLevel, int] = {
    TransferLevel.L0_RECALL: 0,
    TransferLevel.L1_DIRECT_APPLICATION: 1,
    TransferLevel.L2_NEAR_TRANSFER: 2,
    TransferLevel.L3_FAR_TRANSFER: 3,
    TransferLevel.L4_AMBIGUOUS_TRANSFER: 4,
    TransferLevel.L5_INDEPENDENT_TRANSFER: 5,
}


def is_higher_transfer_level(a: TransferLevel, b: TransferLevel) -> bool:
    """Returns True if transfer level `a` represents a greater situational distance than `b`."""
    rank_a = TRANSFER_LEVEL_RANKS.get(a, -1)
    rank_b = TRANSFER_LEVEL_RANKS.get(b, -1)
    return rank_a > rank_b

