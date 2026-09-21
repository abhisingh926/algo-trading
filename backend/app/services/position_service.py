from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.domain.enums import ExitReason, OrderSource, PositionSide, PositionStatus
from app.domain.types import InstrumentRef
from app.models.order import Order
from app.models.position import Position
from app.repositories.order_repository import OrderRepository
from app.repositories.position_repository import PositionRepository
from app.services.market_data_service import MarketDataService
from app.services.order_service import OrderService, PlaceOrderCommand

_STATUS_FILTER = {"open": PositionStatus.OPEN, "closed": PositionStatus.CLOSED, "all": None}


class PositionService:
    def __init__(
        self,
        positions: PositionRepository,
        orders: OrderRepository,
        order_service: OrderService,
        market_data: MarketDataService,
    ) -> None:
        self.positions = positions
        self.orders = orders
        self.order_service = order_service
        self.market_data = market_data

    async def list_positions(self, status: str = "open") -> Sequence[Position]:
        if status not in _STATUS_FILTER:
            raise ValidationFailedError("status must be one of: open, closed, all")
        return await self.positions.list_positions(_STATUS_FILTER[status])

    async def list_by_symbol(self, symbol: str) -> Sequence[Position]:
        return await self.positions.list_open_by_symbol(symbol)

    async def get(self, position_id: str) -> Position:
        position = await self.positions.get_by_id(position_id)
        if position is None:
            raise NotFoundError("Position not found")
        return position

    async def update_levels(self, position_id: str, values: dict[str, Any]) -> Position:
        position = await self.get(position_id)
        if position.status is not PositionStatus.OPEN:
            raise ConflictError("Position is already closed")
        return await self.positions.update(position, values)

    async def close_position(
        self, position: Position, reason: ExitReason, source: OrderSource, user_id: str | None = None
    ) -> Order:
        if position.status is not PositionStatus.OPEN:
            raise ConflictError("Position is already closed")
        exit_side = position.side.exit_order_side
        if await self.orders.has_active_order(position.symbol, position.strategy_id, exit_side):
            raise ConflictError("An exit order for this position is already working")
        return await self.order_service.place_order(
            PlaceOrderCommand(
                symbol=position.symbol,
                exchange=position.exchange,
                side=exit_side,
                quantity=position.quantity,
                trading_mode=position.trading_mode,
                source=source,
                strategy=position.strategy,
                exit_reason=reason,
                user_id=user_id,
            )
        )

    async def mark_to_market(self) -> tuple[list[Position], float]:
        """Refresh LTP + unrealised P&L of all open positions. Returns (positions, total unrealised)."""
        open_positions = list(await self.positions.list_positions(PositionStatus.OPEN))
        if not open_positions:
            return [], 0.0
        instruments = {
            p.symbol: await self.market_data.instruments.get_by_symbol(p.symbol, p.exchange)
            for p in open_positions
        }
        refs = [
            InstrumentRef(i.symbol, i.exchange, i.exchange_token)
            for i in instruments.values()
            if i is not None
        ]
        prices = {q.symbol: q.ltp for q in await self.market_data.refresh_quotes(refs)}
        for position in open_positions:
            if position.symbol in prices:
                position.mark(prices[position.symbol])
                await self.positions.update(position)
        return open_positions, sum(p.unrealized_pnl for p in open_positions)

    @staticmethod
    def protective_exit_reason(position: Position) -> ExitReason | None:
        price = position.last_price
        if price is None:
            return None
        long = position.side is PositionSide.LONG
        if position.stop_loss is not None and (
            price <= position.stop_loss if long else price >= position.stop_loss
        ):
            return ExitReason.STOP_LOSS
        if position.target is not None and (price >= position.target if long else price <= position.target):
            return ExitReason.TARGET
        return None
