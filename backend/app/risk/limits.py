from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskLimits:
    max_risk_per_trade: float  # fraction of capital
    max_daily_loss: float  # INR
    max_trades_per_day: int
    max_open_positions: int
    max_position_size: int  # quantity
    max_order_value: float  # INR
    max_consecutive_losses: int
    max_strategy_drawdown: float  # fraction of the strategy's capital


@dataclass(frozen=True, slots=True)
class RiskContext:
    """Everything the RiskManager needs to judge one order. Built by RiskService from repositories."""

    capital: float
    available_capital: float
    daily_pnl: float  # realised net + unrealised, today
    trades_today: int
    open_positions: int
    consecutive_losses: int
    kill_switch_active: bool = False
    strategy_capital: float | None = None
    strategy_drawdown: float = 0.0  # INR, peak-to-current of the strategy's net P&L


@dataclass(frozen=True, slots=True)
class OrderIntent:
    symbol: str
    quantity: int
    price: float  # expected execution price
    stop_loss: float | None = None
    is_reducing: bool = False  # closes / reduces an existing position

    @property
    def value(self) -> float:
        return self.quantity * self.price

    @property
    def risk_amount(self) -> float | None:
        return None if self.stop_loss is None else abs(self.price - self.stop_loss) * self.quantity


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    violations: tuple[str, ...] = ()

    @property
    def reason(self) -> str:
        return "; ".join(self.violations) if self.violations else "All risk checks passed"
