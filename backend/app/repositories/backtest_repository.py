from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.orm import undefer

from app.models.backtest import Backtest, BacktestTrade
from app.repositories.base import BaseRepository


class BacktestRepository(BaseRepository[Backtest]):
    model = Backtest

    async def list_recent(self, limit: int = 50) -> Sequence[Backtest]:
        return (
            await self.session.scalars(select(Backtest).order_by(Backtest.created_at.desc()).limit(limit))
        ).all()

    async def get_with_equity_curve(self, backtest_id: str) -> Backtest | None:
        stmt = select(Backtest).where(Backtest.id == backtest_id).options(undefer(Backtest.equity_curve))
        return await self.session.scalar(stmt.execution_options(populate_existing=True))

    async def add_trades(self, rows: list[dict[str, Any]]) -> None:
        if rows:
            await self.session.execute(insert(BacktestTrade), rows)

    async def list_trades(self, backtest_id: str) -> Sequence[BacktestTrade]:
        stmt = (
            select(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)
            .order_by(BacktestTrade.entry_time)
        )
        return (await self.session.scalars(stmt)).all()
