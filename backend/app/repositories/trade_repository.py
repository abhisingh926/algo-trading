from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import case, func, select

from app.domain.enums import TradingMode
from app.models.trade import Trade
from app.repositories.base import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    model = Trade

    async def list_trades(
        self,
        *,
        strategy_id: str | None = None,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int | None = 100,
        offset: int = 0,
        ascending: bool = False,
    ) -> Sequence[Trade]:
        stmt = (
            select(Trade)
            .order_by(Trade.exit_time.asc() if ascending else Trade.exit_time.desc())
            .offset(offset)
        )
        if strategy_id:
            stmt = stmt.where(Trade.strategy_id == strategy_id)
        if symbol:
            stmt = stmt.where(Trade.symbol == symbol.upper())
        if since is not None:
            stmt = stmt.where(Trade.exit_time >= since)
        if limit is not None:
            stmt = stmt.limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def aggregate(
        self,
        *,
        mode: TradingMode | None = None,
        since: datetime | None = None,
        strategy_id: str | None = None,
    ) -> dict[str, float]:
        """count / wins / losses / gross / charges / net in one round trip."""
        stmt = select(
            func.count(Trade.id),
            func.coalesce(func.sum(case((Trade.net_pnl > 0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Trade.net_pnl < 0, 1), else_=0)), 0),
            func.coalesce(func.sum(Trade.gross_pnl), 0),
            func.coalesce(func.sum(Trade.charges), 0),
            func.coalesce(func.sum(Trade.net_pnl), 0),
        )
        if mode is not None:
            stmt = stmt.where(Trade.trading_mode == mode)
        if since is not None:
            stmt = stmt.where(Trade.exit_time >= since)
        if strategy_id is not None:
            stmt = stmt.where(Trade.strategy_id == strategy_id)
        count, wins, losses, gross, charges, net = (await self.session.execute(stmt)).one()
        return {
            "trades": int(count),
            "wins": int(wins),
            "losses": int(losses),
            "gross_pnl": float(gross),
            "charges": float(charges),
            "net_pnl": float(net),
        }

    async def aggregate_by_strategy(self, since: datetime | None = None) -> dict[str, dict[str, float]]:
        stmt = (
            select(
                Trade.strategy_id,
                func.count(Trade.id),
                func.coalesce(func.sum(case((Trade.net_pnl > 0, 1), else_=0)), 0),
                func.coalesce(func.sum(Trade.net_pnl), 0),
            )
            .where(Trade.strategy_id.is_not(None))
            .group_by(Trade.strategy_id)
        )
        if since is not None:
            stmt = stmt.where(Trade.exit_time >= since)
        return {
            sid: {"trades": int(count), "wins": int(wins), "net_pnl": float(net)}
            for sid, count, wins, net in (await self.session.execute(stmt)).all()
        }
