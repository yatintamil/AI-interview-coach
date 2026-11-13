"""
Candidate Longitudinal Skill State Repository.
Handles persistence and queries for candidate competency tracking, mastery estimation,
and assistance dependency indices.
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.skill_state import CandidateSkillStateModel
import backend.models.candidate  # noqa: F401
from backend.repositories.base import BaseRepository


class CandidateSkillStateRepository(BaseRepository[CandidateSkillStateModel]):
    """
    Repository managing longitudinal CandidateSkillState entities.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(CandidateSkillStateModel, session)

    async def get_by_candidate_and_skill(
        self, candidate_id: str, skill_name: str
    ) -> Optional[CandidateSkillStateModel]:
        """
        Retrieve the longitudinal skill state for a specific candidate and competency.
        Checks exact match, lowercase, underscored, and normalized canonical skill key.
        """
        from backend.domain.transfer.skill_mapping import normalize_skill
        canonical_key, _ = normalize_skill(skill_name)
        
        lookup_keys = [skill_name]
        for candidate_key in [canonical_key, skill_name.lower().strip(), skill_name.lower().strip().replace(" ", "_")]:
            if candidate_key and candidate_key not in lookup_keys:
                lookup_keys.append(candidate_key)

        stmt = (
            select(CandidateSkillStateModel)
            .where(
                CandidateSkillStateModel.candidate_id == candidate_id,
                CandidateSkillStateModel.skill_name.in_(lookup_keys),
            )
            .options(selectinload(CandidateSkillStateModel.candidate))
        )
        res = await self.session.execute(stmt)
        results = list(res.scalars().all())
        if not results:
            return None
        # Prefer exact match or canonical match if multiple exist
        for r in results:
            if r.skill_name == canonical_key:
                return r
        for r in results:
            if r.skill_name == skill_name:
                return r
        return results[0]

    async def list_by_candidate(
        self, candidate_id: str, skip: int = 0, limit: int = 100
    ) -> List[CandidateSkillStateModel]:
        """List all tracked competencies for a given candidate ordered by recency."""
        stmt = (
            select(CandidateSkillStateModel)
            .where(CandidateSkillStateModel.candidate_id == candidate_id)
            .order_by(CandidateSkillStateModel.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_state(
        self,
        skill_state_id: str,
        mastery_estimate: Optional[float] = None,
        mastery_uncertainty: Optional[float] = None,
        highest_transfer_level: Optional[str] = None,
        assistance_dependency_index: Optional[float] = None,
        recurring_failure_types: Optional[List[str]] = None,
        increment_attempts: bool = False,
        assessed_at: Optional[datetime] = None,
    ) -> Optional[CandidateSkillStateModel]:
        """
        Updates longitudinal skill state fields while maintaining audit timestamps.
        """
        state = await self.get(skill_state_id)
        if not state:
            return None

        if mastery_estimate is not None:
            state.mastery_estimate = mastery_estimate
        if mastery_uncertainty is not None:
            state.mastery_uncertainty = mastery_uncertainty
        if highest_transfer_level is not None:
            from backend.domain.transfer.taxonomy import is_higher_transfer_level
            if is_higher_transfer_level(highest_transfer_level, state.highest_transfer_level):
                state.highest_transfer_level = highest_transfer_level
        if assistance_dependency_index is not None:
            state.assistance_dependency_index = assistance_dependency_index
        if recurring_failure_types is not None:
            state.recurring_failure_types = recurring_failure_types
        if increment_attempts:
            state.total_attempts += 1
        if assessed_at is not None:
            state.last_assessed_at = assessed_at

        await self.session.flush()
        return state

    async def upsert_skill_state(
        self,
        candidate_id: str,
        skill_name: str,
        mastery_estimate: float,
        mastery_uncertainty: float,
        highest_transfer_level: str = "L0_RECALL",
        assistance_dependency_index: float = 0.0,
        recurring_failure_types: Optional[List[str]] = None,
        assessed_at: Optional[datetime] = None,
    ) -> CandidateSkillStateModel:
        """
        Creates a skill state if not exists, or updates the existing one.
        """
        from backend.domain.transfer.taxonomy import is_higher_transfer_level, TransferLevel

        existing = await self.get_by_candidate_and_skill(candidate_id, skill_name)
        if existing:
            existing.mastery_estimate = mastery_estimate
            existing.mastery_uncertainty = mastery_uncertainty
            # Preserve higher transfer level achievements: never downgrade
            if is_higher_transfer_level(highest_transfer_level, existing.highest_transfer_level):
                existing.highest_transfer_level = highest_transfer_level
            existing.assistance_dependency_index = assistance_dependency_index
            if recurring_failure_types is not None:
                merged = list(existing.recurring_failure_types or [])
                for f in recurring_failure_types:
                    if f not in merged:
                        merged.append(f)
                existing.recurring_failure_types = merged
            existing.total_attempts += 1
            if assessed_at is not None:
                existing.last_assessed_at = assessed_at
            await self.session.flush()
            return existing

        new_state = CandidateSkillStateModel(
            candidate_id=candidate_id,
            skill_name=skill_name,
            mastery_estimate=mastery_estimate,
            mastery_uncertainty=mastery_uncertainty,
            highest_transfer_level=highest_transfer_level,
            assistance_dependency_index=assistance_dependency_index,
            recurring_failure_types=recurring_failure_types or [],
            total_attempts=1,
            last_assessed_at=assessed_at,
        )
        self.session.add(new_state)
        await self.session.flush()
        return new_state
