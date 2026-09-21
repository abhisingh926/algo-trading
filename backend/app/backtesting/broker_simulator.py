"""Execution simulator for backtests: slippage, charges, one position at a time, equity accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import ExitReason, OrderSide, PositionSide
from app.trading.charges import ChargesCalculator


@dataclass(slots=True)
class SimPosition:
    side: PositionSide
    quantity: int
    entry_price: float
    entry_time: datetime
    entry_charges: float
    stop_loss: float
    target: float | None


@dataclass(frozen=True, slots=True)
class SimTrade:
    symbol: str
    side: PositionSide
    quantity: int
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    gross_pnl: float
    charges: float
    net_pnl: float
    exit_reason: ExitReason


class BrokerSimulator:
    def __init__(
        self, symbol: str, initial_capital: float, slippage_pct: float, charges: ChargesCalculator
    ) -> None:
        self.symbol = symbol
        self.realized_equity = (
            initial_capital  # initial capital + closed net P&L - entry charges of the open position
        )
        self.slippage_pct = slippage_pct
        self.charges = charges
        self.position: SimPosition | None = None
        self.trades: list[SimTrade] = []
        self.total_charges = 0.0
        self.total_slippage = 0.0

    def _fill_price(self, side: OrderSide, reference: float, quantity: int) -> float:
        price = round(reference * (1 + self.slippage_pct * side.sign), 4)
        self.total_slippage += abs(price - reference) * quantity
        return price

    def equity(self, mark_price: float) -> float:
        if self.position is None:
            return self.realized_equity
        p = self.position
        return self.realized_equity + (mark_price - p.entry_price) * p.quantity * p.side.sign

    def open(
        self,
        side: PositionSide,
        quantity: int,
        reference_price: float,
        when: datetime,
        stop_loss: float,
        target: float | None,
    ) -> SimPosition:
        order_side = OrderSide.BUY if side is PositionSide.LONG else OrderSide.SELL
        price = self._fill_price(order_side, reference_price, quantity)
        fees = self.charges.compute(order_side, price, quantity)
        self.realized_equity -= fees
        self.total_charges += fees
        self.position = SimPosition(side, quantity, price, when, fees, stop_loss, target)
        return self.position

    def close(self, reference_price: float, when: datetime, reason: ExitReason) -> SimTrade:
        p = self.position
        assert p is not None, "no open position"
        price = self._fill_price(p.side.exit_order_side, reference_price, p.quantity)
        exit_fees = self.charges.compute(p.side.exit_order_side, price, p.quantity)
        gross = (price - p.entry_price) * p.quantity * p.side.sign
        self.realized_equity += gross - exit_fees
        self.total_charges += exit_fees
        charges = p.entry_charges + exit_fees
        trade = SimTrade(
            self.symbol,
            p.side,
            p.quantity,
            p.entry_time,
            when,
            p.entry_price,
            price,
            round(gross, 4),
            round(charges, 4),
            round(gross - charges, 4),
            reason,
        )
        self.trades.append(trade)
        self.position = None
        return trade
