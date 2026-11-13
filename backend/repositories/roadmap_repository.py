"""
Repository for Personalized Learning Roadmaps and Roadmap Items.
"""

from typing import Optional, List
# pyrefly: ignore [missing-import]
from sqlalchemy import select, delete
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import selectinload

from backend.models.roadmap import PersonalizedRoadmapModel, RoadmapItemModel
from backend.repositories.base import BaseRepository


class RoadmapRepository(BaseRepository[PersonalizedRoadmapModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(PersonalizedRoadmapModel, session)

    async def get_by_candidate(self, candidate_id: str) -> Optional[PersonalizedRoadmapModel]:
        """Fetches the latest active roadmap for a candidate, including all sequenced items."""
        stmt = (
            select(PersonalizedRoadmapModel)
            .where(
                PersonalizedRoadmapModel.candidate_id == candidate_id,
                PersonalizedRoadmapModel.status == "ACTIVE",
            )
            .options(
                selectinload(PersonalizedRoadmapModel.items),
                selectinload(PersonalizedRoadmapModel.candidate),
            )
            .order_by(PersonalizedRoadmapModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_with_items(self, roadmap_id: str) -> Optional[PersonalizedRoadmapModel]:
        """Fetches a specific roadmap by ID including its items."""
        stmt = (
            select(PersonalizedRoadmapModel)
            .where(PersonalizedRoadmapModel.id == roadmap_id)
            .options(
                selectinload(PersonalizedRoadmapModel.items),
                selectinload(PersonalizedRoadmapModel.candidate),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_item(self, item_id: str) -> Optional[RoadmapItemModel]:
        """Fetches an individual roadmap item by ID."""
        stmt = (
            select(RoadmapItemModel)
            .where(RoadmapItemModel.id == item_id)
            .options(selectinload(RoadmapItemModel.roadmap))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_item_by_skill(self, roadmap_id: str, skill_id: str) -> Optional[RoadmapItemModel]:
        """Fetches an item by roadmap ID and canonical skill identifier."""
        stmt = (
            select(RoadmapItemModel)
            .where(
                RoadmapItemModel.roadmap_id == roadmap_id,
                RoadmapItemModel.skill_id == skill_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_candidate(self, candidate_id: str, skip: int = 0, limit: int = 20) -> List[PersonalizedRoadmapModel]:
        """Lists historical roadmaps for a candidate."""
        stmt = (
            select(PersonalizedRoadmapModel)
            .where(PersonalizedRoadmapModel.candidate_id == candidate_id)
            .options(selectinload(PersonalizedRoadmapModel.items))
            .order_by(PersonalizedRoadmapModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
