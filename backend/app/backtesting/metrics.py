"""Performance statistics. Pure functions over trades and an equity curve."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Protocol

from app.utils.time import ist_date

MIN_DAILY_RETURNS_FOR_SHARPE = 20
TRADING_DAYS_PER_YEAR = 252


class _HasNetPnl(Protocol):
    net_pnl: float


@dataclass(frozen=True, slots=True)
class TradeStats:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # percent
    gross_profit: float  # sum of winning trades (net of charges)
    gross_loss: float  # sum of losing trades (negative number)
    net_pnl: float
    profit_factor: float | None
    average_trade: float
    largest_win: float
    largest_loss: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def trade_stats(trades: Sequence[_HasNetPnl]) -> TradeStats:
    pnls = [float(t.net_pnl) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit, gross_loss = sum(wins), sum(losses)
    total = len(pnls)
    return TradeStats(
        total_trades=total,
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=round(len(wins) / total * 100, 2) if total else 0.0,
        gross_profit=round(gross_profit, 2),
        gross_loss=round(gross_loss, 2),
        net_pnl=round(gross_profit + gross_loss, 2),
        profit_factor=round(gross_profit / abs(gross_loss), 3) if gross_loss < 0 else None,
        average_trade=round((gross_profit + gross_loss) / total, 2) if total else 0.0,
        largest_win=round(max(wins), 2) if wins else 0.0,
        largest_loss=round(min(losses), 2) if losses else 0.0,
    )


def drawdown_series(equity: Sequence[float]) -> tuple[list[float], list[float]]:
    """Per-point drawdown in currency and percent (both <= 0)."""
    amounts, percents, peak = [], [], -math.inf
    for value in equity:
        peak = max(peak, value)
        dd = value - peak
        amounts.append(round(dd, 2))
        percents.append(round(dd / peak * 100, 4) if peak > 0 else 0.0)
    return amounts, percents


def max_drawdown(equity: Sequence[float]) -> tuple[float, float]:
    """(max drawdown in currency, in percent) as positive numbers."""
    if not equity:
        return 0.0, 0.0
    amounts, percents = drawdown_series(equity)
    return abs(min(amounts)), abs(min(percents))


def sharpe_ratio(timestamps: Sequence[datetime], equity: Sequence[float]) -> float | None:
    """Annualised Sharpe from DAILY equity returns (risk-free = 0).

    Returns None when there are too few daily observations or no variance - a Sharpe computed from
    a handful of points is noise, not information."""
    daily: dict[Any, float] = {}
    for ts, value in zip(timestamps, equity, strict=True):
        daily[ist_date(ts)] = value  # last equity of each day
    values = list(daily.values())
    returns = [values[i] / values[i - 1] - 1 for i in range(1, len(values)) if values[i - 1] > 0]
    if len(returns) < MIN_DAILY_RETURNS_FOR_SHARPE:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    if variance <= 0:
        return None
    return round(mean / math.sqrt(variance) * math.sqrt(TRADING_DAYS_PER_YEAR), 3)
