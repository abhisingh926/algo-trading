"""Generic async repository. Repositories contain persistence only - no business rules."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: str) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def get_all(self, *, limit: int | None = None, offset: int = 0) -> Sequence[ModelT]:
        stmt = select(self.model).offset(offset)
        if hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
        if limit is not None:
            stmt = stmt.limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def count(self) -> int:
        return int(await self.session.scalar(select(func.count()).select_from(self.model)) or 0)

    async def create(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: ModelT, values: dict[str, Any] | None = None) -> ModelT:
        for key, value in (values or {}).items():
            setattr(entity, key, value)
        await self.session.flush()
        return entity

    async def delete(self, entity_id: str) -> None:
        await self.session.execute(delete(self.model).where(self.model.id == entity_id))  # type: ignore[attr-defined]

    async def delete_entity(self, entity: ModelT) -> None:
        """ORM delete (honours relationship cascades)."""
        await self.session.delete(entity)
        await self.session.flush()

    async def commit(self) -> None:
        """Persist immediately. Used when state must survive a subsequently raised error (e.g. rejections)."""
        await self.session.commit()
