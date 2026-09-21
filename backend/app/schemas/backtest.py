from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import BacktestStatus, ExitReason, PositionSide, StrategyType, Timeframe
from app.schemas.common import ORMModel


class BacktestCreate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    strategy_id: str | None = None
    strategy_type: StrategyType | None = None
    parameters: dict[str, Any] | None = None
    symbol: str | None = None
    exchange: str | None = None
    timeframe: Timeframe | None = None
    risk_per_trade: float | None = Field(default=None, gt=0, le=0.2)
    stop_loss_pct: float | None = Field(default=None, gt=0, lt=0.5)
    target_pct: float | None = Field(default=None, gt=0, lt=5)
    allow_short: bool | None = None

    start_date: date
    end_date: date
    initial_capital: float = Field(gt=0)
    brokerage_per_order: float = Field(default=20.0, ge=0)
    brokerage_pct: float = Field(default=0.0003, ge=0, le=0.05)
    slippage_pct: float = Field(default=0.0005, ge=0, le=0.05)
    include_statutory_charges: bool = True

    @model_validator(mode="after")
    def _check(self) -> BacktestCreate:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if self.strategy_id is None and (
            self.strategy_type is None or self.symbol is None or self.timeframe is None
        ):
            raise ValueError("Provide strategy_id, or strategy_type + symbol + timeframe")
        return self


class BacktestRead(ORMModel):
    id: str
    name: str
    strategy_id: str | None
    strategy_type: StrategyType
    parameters: dict[str, Any]
    symbol: str
    exchange: str
    timeframe: Timeframe
    start_date: date
    end_date: date
    status: BacktestStatus
    error_message: str | None
    initial_capital: float
    config: dict[str, Any]
    metrics: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None


class BacktestTradeRead(ORMModel):
    id: str
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: PositionSide
    entry_price: float
    exit_price: float
    quantity: int
    gross_pnl: float
    charges: float
    net_pnl: float
    exit_reason: ExitReason


class BacktestEquityPoint(BaseModel):
    timestamp: datetime
    equity: float
    drawdown: float
    drawdown_pct: float


class MonthlyReturn(BaseModel):
    month: str
    net_pnl: float
    trades: int


class BacktestReport(BaseModel):
    backtest: BacktestRead
    trades: list[BacktestTradeRead]
    equity_curve: list[BacktestEquityPoint]
    monthly_returns: list[MonthlyReturn]
