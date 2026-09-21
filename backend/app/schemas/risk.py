from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RiskConfigurationUpdate(BaseModel):
    max_risk_per_trade: float | None = Field(default=None, gt=0, le=1)
    max_daily_loss: float | None = Field(default=None, gt=0)
    max_trades_per_day: int | None = Field(default=None, ge=1)
    max_open_positions: int | None = Field(default=None, ge=1)
    max_position_size: int | None = Field(default=None, ge=1)
    max_order_value: float | None = Field(default=None, gt=0)
    max_consecutive_losses: int | None = Field(default=None, ge=1)
    max_strategy_drawdown: float | None = Field(default=None, gt=0, le=1)
    close_positions_on_kill_switch: bool | None = None


class RiskConfigurationRead(ORMModel):
    id: str
    max_risk_per_trade: float
    max_daily_loss: float
    max_trades_per_day: int
    max_open_positions: int
    max_position_size: int
    max_order_value: float
    max_consecutive_losses: int
    max_strategy_drawdown: float
    close_positions_on_kill_switch: bool
    kill_switch_active: bool
    kill_switch_activated_at: datetime | None
    kill_switch_reason: str | None
    updated_at: datetime


class RiskUsage(BaseModel):
    key: str
    label: str
    current: float
    limit: float
    utilization: float
    breached: bool
    unit: str


class RiskStatus(BaseModel):
    kill_switch_active: bool
    system_state: str
    trading_allowed: bool
    blocked_reasons: list[str]
    usage: list[RiskUsage]


class KillSwitchRequest(BaseModel):
    activate: bool
    confirm: bool = False
    reason: str | None = Field(default=None, max_length=500)


class KillSwitchResult(BaseModel):
    kill_switch_active: bool
    strategies_stopped: int = 0
    orders_cancelled: int = 0
    positions_closed: int = 0
    message: str
