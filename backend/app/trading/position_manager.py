"""Turns order fills into positions and closed trades."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.domain.enums import ExitReason, OrderSide, OrderSource, PositionSide, PositionStatus
from app.models.order import Order
from app.models.position import Position
from app.models.trade import Trade
from app.repositories.position_repository import PositionRepository
from app.repositories.trade_repository import TradeRepository
from app.services.event_service import EventService
from app.utils.time import utcnow

TradeListener = Callable[[Trade], Awaitable[None]]

_DEFAULT_EXIT_REASON = {
    OrderSource.STRATEGY: ExitReason.SIGNAL,
    OrderSource.KILL_SWITCH: ExitReason.KILL_SWITCH,
    OrderSource.MANUAL: ExitReason.MANUAL,
    OrderSource.RISK_EXIT: ExitReason.STOP_LOSS,
}


class PositionManager:
    def __init__(
        self,
        positions: PositionRepository,
        trades: TradeRepository,
        events: EventService,
        on_trade_closed: TradeListener | None = None,
    ) -> None:
        self.positions = positions
        self.trades = trades
        self.events = events
        self.on_trade_closed = on_trade_closed

    async def apply_fill(self, order: Order, quantity: int, price: float, charges: float) -> Position:
        """Apply one (partial) fill. Handles open, scale-in, reduce, close and flip-through-zero."""
        position = await self.positions.get_open(
            order.symbol, order.exchange, order.strategy_id, order.trading_mode
        )
        fill_side = PositionSide.LONG if order.side is OrderSide.BUY else PositionSide.SHORT

        if position is None:
            return await self._open(order, fill_side, quantity, price, charges)
        if position.side is fill_side:
            return await self._increase(position, quantity, price, charges)

        closing = min(quantity, position.quantity)
        closing_charges = charges * closing / quantity
        await self._reduce(position, order, closing, price, closing_charges)
        remainder = quantity - closing
        if remainder > 0:  # flipped through zero: the rest opens the opposite position
            return await self._open(order, fill_side, remainder, price, charges - closing_charges)
        return position

    async def _open(
        self, order: Order, side: PositionSide, quantity: int, price: float, charges: float
    ) -> Position:
        position = Position(
            strategy_id=order.strategy_id,
            strategy=order.strategy,
            broker_account_id=order.broker_account_id,
            symbol=order.symbol,
            exchange=order.exchange,
            side=side,
            quantity=quantity,
            average_entry_price=price,
            last_price=price,
            charges_accrued=charges,
            stop_loss=order.stop_loss,
            target=order.target,
            trading_mode=order.trading_mode,
        )
        await self.positions.create(position)
        await self.events.record(
            "position_opened",
            f"{side.value} {quantity} {order.symbol} @ {price:.2f}",
            strategy_id=order.strategy_id,
            order_id=order.id,
            symbol=order.symbol,
            quantity=quantity,
            price=price,
            stop_loss=order.stop_loss,
            target=order.target,
        )
        return position

    async def _increase(self, position: Position, quantity: int, price: float, charges: float) -> Position:
        total = position.quantity + quantity
        position.average_entry_price = round(
            (position.average_entry_price * position.quantity + price * quantity) / total, 4
        )
        position.quantity = total
        position.charges_accrued += charges
        position.mark(price)
        return await self.positions.update(position)

    async def _reduce(
        self, position: Position, order: Order, quantity: int, price: float, exit_charges: float
    ) -> Trade:
        entry_charges = position.charges_accrued * quantity / position.quantity
        gross = (price - position.average_entry_price) * quantity * position.side.sign
        charges = entry_charges + exit_charges
        now = utcnow()
        trade = await self.trades.create(
            Trade(
                position_id=position.id,
                strategy_id=position.strategy_id,
                strategy=position.strategy,
                exit_order_id=order.id,
                symbol=position.symbol,
                exchange=position.exchange,
                side=position.side,
                quantity=quantity,
                entry_price=position.average_entry_price,
                exit_price=price,
                entry_time=position.opened_at,
                exit_time=now,
                gross_pnl=round(gross, 4),
                charges=round(charges, 4),
                net_pnl=round(gross - charges, 4),
                exit_reason=order.exit_reason or _DEFAULT_EXIT_REASON[order.source],
                trading_mode=position.trading_mode,
            )
        )
        position.quantity -= quantity
        position.charges_accrued -= entry_charges
        position.realized_pnl += trade.net_pnl
        if position.quantity == 0:
            position.status, position.closed_at, position.unrealized_pnl, position.last_price = (
                PositionStatus.CLOSED,
                now,
                0.0,
                price,
            )
            await self.events.record(
                "position_closed",
                f"{position.symbol} closed @ {price:.2f}, net P&L {trade.net_pnl:.2f}",
                strategy_id=position.strategy_id,
                order_id=order.id,
                symbol=position.symbol,
                net_pnl=trade.net_pnl,
                exit_reason=trade.exit_reason.value,
            )
        else:
            position.mark(price)
        await self.positions.update(position)
        if self.on_trade_closed is not None:
            await self.on_trade_closed(trade)
        return trade
