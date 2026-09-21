from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import StrategyStatus, StrategyType, Timeframe, TradingMode
from app.schemas.common import ORMModel


class StrategyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    strategy_type: StrategyType
    symbol: str = Field(min_length=1, max_length=50)
    exchange: str = Field(default="NSE", max_length=10)
    timeframe: Timeframe
    capital: float = Field(gt=0)
    risk_per_trade: float = Field(
        gt=0, le=0.2, description="Fraction of capital risked per trade (0.01 = 1%)"
    )
    stop_loss_pct: float = Field(gt=0, lt=0.5, description="Fraction (0.01 = 1%)")
    target_pct: float | None = Field(default=None, gt=0, lt=5)
    allow_short: bool = False
    trading_mode: TradingMode = TradingMode.PAPER
    broker_account_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol", "exchange")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("trading_mode")
    @classmethod
    def _no_backtest_mode(cls, value: TradingMode) -> TradingMode:
        if value is TradingMode.BACKTEST:
            raise ValueError(
                "Use the backtesting API for backtests; strategies run in PAPER, SANDBOX or LIVE"
            )
        return value


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    strategy_type: StrategyType | None = None
    symbol: str | None = None
    exchange: str | None = None
    timeframe: Timeframe | None = None
    capital: float | None = Field(default=None, gt=0)
    risk_per_trade: float | None = Field(default=None, gt=0, le=0.2)
    stop_loss_pct: float | None = Field(default=None, gt=0, lt=0.5)
    target_pct: float | None = Field(default=None, gt=0, lt=5)
    allow_short: bool | None = None
    trading_mode: TradingMode | None = None
    broker_account_id: str | None = None
    parameters: dict[str, Any] | None = None


class StrategyStats(BaseModel):
    todays_pnl: float = 0.0
    total_pnl: float = 0.0
    trades: int = 0
    win_rate: float = 0.0
    open_position_qty: int = 0


class StrategyRead(ORMModel):
    id: str
    name: str
    strategy_type: StrategyType
    status: StrategyStatus
    symbol: str
    exchange: str
    timeframe: Timeframe
    capital: float
    risk_per_trade: float
    stop_loss_pct: float
    target_pct: float | None
    allow_short: bool
    trading_mode: TradingMode
    broker_account_id: str | None
    broker_name: str | None
    parameters: dict[str, Any]
    last_signal_at: datetime | None
    last_evaluated_at: datetime | None
    last_error: str | None
    stats: StrategyStats = Field(default_factory=StrategyStats)
    created_at: datetime
    updated_at: datetime


class ParameterSpecRead(BaseModel):
    key: str
    label: str
    type: str
    default: float
    min: float
    max: float
    description: str


class StrategyTypeInfo(BaseModel):
    type: StrategyType
    name: str
    description: str
    parameters: list[ParameterSpecRead]
