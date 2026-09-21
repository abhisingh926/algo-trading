from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.domain.enums import EventLevel, TradingMode
from app.schemas.common import ORMModel


class DashboardSummary(BaseModel):
    capital: float
    available: float
    used_margin: float
    todays_pnl: float
    realized_pnl_today: float
    open_pnl: float
    total_pnl: float
    win_rate: float
    trades_today: int
    open_positions: int
    running_strategies: int
    trading_mode: TradingMode
    currency: str = "INR"


class DailyPnlRead(BaseModel):
    date: date
    realized_pnl: float
    unrealized_pnl: float
    charges: float
    net_pnl: float
    trades: int
    wins: int
    losses: int


class EquityPointRead(BaseModel):
    timestamp: datetime
    equity: float
    realized_pnl: float
    unrealized_pnl: float


class PnlSeries(BaseModel):
    daily: list[DailyPnlRead]
    equity_curve: list[EquityPointRead]


class StrategyPerformance(BaseModel):
    strategy_id: str
    strategy_name: str
    trades: int
    win_rate: float
    net_pnl: float


class Performance(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_pnl: float
    profit_factor: float | None
    average_trade: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    max_drawdown_pct: float
    total_charges: float
    by_strategy: list[StrategyPerformance]


class ComponentStatus(BaseModel):
    key: str
    name: str
    status: str
    detail: str | None = None


class SystemStatus(BaseModel):
    trading_mode: TradingMode
    live_trading_enabled: bool
    kill_switch_active: bool
    system_state: str
    market_data_provider: str
    server_time: datetime
    components: list[ComponentStatus]


class SystemConfig(BaseModel):
    app_name: str
    app_env: str
    version: str
    trading_mode: TradingMode
    live_trading_enabled: bool
    auth_enabled: bool
    workers_enabled: bool
    market_data_provider: str
    paper_initial_capital: float
    paper_slippage_pct: float
    strategy_poll_seconds: float
    order_monitor_poll_seconds: float
    market_data_poll_seconds: float
    default_charges: dict[str, float]
    brokers_configured: dict[str, bool]


class SystemEventRead(ORMModel):
    id: str
    event_type: str
    level: EventLevel
    message: str
    payload: dict[str, Any] | None
    strategy_id: str | None
    order_id: str | None
    symbol: str | None
    created_at: datetime
