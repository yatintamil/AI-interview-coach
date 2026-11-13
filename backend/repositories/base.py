"""
Abstract Base Async Repository Interface with generic CRUD operations.
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

ModelType = TypeVar("ModelType", bound=Any)


class BaseRepository(Generic[ModelType]):
    """
    Base generic repository for Async SQLAlchemy CRUD operations.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: Union[str, UUID]) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == str(id))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, id: Union[str, UUID]) -> Optional[ModelType]:
        return await self.get(id)

    async def create(self, obj_in: ModelType) -> ModelType:
        self.session.add(obj_in)
        await self.session.flush()
        return obj_in

    async def delete(self, id: Union[str, UUID]) -> bool:
        stmt = delete(self.model).where(self.model.id == str(id))
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
