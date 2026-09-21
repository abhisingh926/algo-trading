from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.domain.enums import EventLevel
from app.models.event import SystemEvent
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[SystemEvent]):
    model = SystemEvent

    async def list_events(
        self,
        *,
        event_type: str | None = None,
        level: EventLevel | None = None,
        strategy_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[SystemEvent]:
        stmt = select(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(limit).offset(offset)
        if event_type:
            stmt = stmt.where(SystemEvent.event_type == event_type)
        if level:
            stmt = stmt.where(SystemEvent.level == level)
        if strategy_id:
            stmt = stmt.where(SystemEvent.strategy_id == strategy_id)
        return (await self.session.scalars(stmt)).all()
