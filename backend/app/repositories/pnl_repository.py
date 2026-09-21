from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select

from app.domain.enums import TradingMode
from app.models.daily_pnl import DailyPnL, PortfolioSnapshot
from app.repositories.base import BaseRepository


class PnlRepository(BaseRepository[DailyPnL]):
    model = DailyPnL

    async def get_day(self, trade_date: date, mode: TradingMode) -> DailyPnL | None:
        stmt = select(DailyPnL).where(DailyPnL.trade_date == trade_date, DailyPnL.trading_mode == mode)
        return await self.session.scalar(stmt)

    async def list_days(self, since: date, mode: TradingMode) -> Sequence[DailyPnL]:
        stmt = (
            select(DailyPnL)
            .where(DailyPnL.trade_date >= since, DailyPnL.trading_mode == mode)
            .order_by(DailyPnL.trade_date.asc())
        )
        return (await self.session.scalars(stmt)).all()

    async def add_snapshot(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def latest_snapshot(self, mode: TradingMode) -> PortfolioSnapshot | None:
        stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.trading_mode == mode)
            .order_by(PortfolioSnapshot.timestamp.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def list_snapshots(
        self, since: datetime, mode: TradingMode, limit: int = 5000
    ) -> Sequence[PortfolioSnapshot]:
        stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.timestamp >= since, PortfolioSnapshot.trading_mode == mode)
            .order_by(PortfolioSnapshot.timestamp.asc())
            .limit(limit)
        )
        return (await self.session.scalars(stmt)).all()
