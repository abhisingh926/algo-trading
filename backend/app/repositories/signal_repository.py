from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.models.signal import Signal
from app.repositories.base import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    model = Signal

    async def list_recent(self, strategy_id: str | None = None, limit: int = 50) -> Sequence[Signal]:
        stmt = select(Signal).order_by(Signal.created_at.desc()).limit(limit)
        if strategy_id:
            stmt = stmt.where(Signal.strategy_id == strategy_id)
        return (await self.session.scalars(stmt)).all()
