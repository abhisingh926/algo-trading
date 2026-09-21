from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from app.domain.enums import PositionStatus, TradingMode
from app.models.position import Position
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    model = Position

    async def list_positions(
        self, status: PositionStatus | None = PositionStatus.OPEN, limit: int = 500
    ) -> Sequence[Position]:
        stmt = select(Position).order_by(Position.opened_at.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(Position.status == status)
        return (await self.session.scalars(stmt)).all()

    async def list_open_by_symbol(self, symbol: str) -> Sequence[Position]:
        stmt = select(Position).where(
            Position.symbol == symbol.upper(), Position.status == PositionStatus.OPEN
        )
        return (await self.session.scalars(stmt)).all()

    async def get_open(
        self, symbol: str, exchange: str, strategy_id: str | None, trading_mode: TradingMode
    ) -> Position | None:
        stmt = select(Position).where(
            Position.symbol == symbol,
            Position.exchange == exchange,
            Position.status == PositionStatus.OPEN,
            Position.trading_mode == trading_mode,
        )
        stmt = (
            stmt.where(Position.strategy_id == strategy_id)
            if strategy_id
            else stmt.where(Position.strategy_id.is_(None))
        )
        return await self.session.scalar(stmt.limit(1))

    async def count_open(self) -> int:
        stmt = select(func.count()).select_from(Position).where(Position.status == PositionStatus.OPEN)
        return int(await self.session.scalar(stmt) or 0)

    async def count_opened_since(self, since: datetime, mode: TradingMode | None = None) -> int:
        stmt = select(func.count()).select_from(Position).where(Position.opened_at >= since)
        if mode is not None:
            stmt = stmt.where(Position.trading_mode == mode)
        return int(await self.session.scalar(stmt) or 0)

    async def get_for_update(self, position_id: str) -> Position | None:
        stmt = select(Position).where(Position.id == position_id).with_for_update()
        return await self.session.scalar(stmt.execution_options(populate_existing=True))
