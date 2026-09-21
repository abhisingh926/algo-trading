from __future__ import annotations

from collections.abc import Sequence

from app.core.exceptions import NotFoundError
from app.models.trade import Trade
from app.repositories.trade_repository import TradeRepository


class TradeService:
    def __init__(self, trades: TradeRepository) -> None:
        self.trades = trades

    async def list_trades(
        self, strategy_id: str | None = None, symbol: str | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[Trade]:
        return await self.trades.list_trades(
            strategy_id=strategy_id, symbol=symbol, limit=limit, offset=offset
        )

    async def get(self, trade_id: str) -> Trade:
        trade = await self.trades.get_by_id(trade_id)
        if trade is None:
            raise NotFoundError("Trade not found")
        return trade
