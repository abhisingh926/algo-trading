from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import PositionSide, PositionStatus, TradingMode
from app.schemas.common import ORMModel


class PositionUpdate(BaseModel):
    stop_loss: float | None = Field(default=None, gt=0)
    target: float | None = Field(default=None, gt=0)


class PositionRead(ORMModel):
    id: str
    symbol: str
    exchange: str
    strategy_id: str | None
    strategy_name: str | None
    side: PositionSide
    quantity: int
    average_entry_price: float
    last_price: float | None
    unrealized_pnl: float
    realized_pnl: float
    stop_loss: float | None
    target: float | None
    status: PositionStatus
    trading_mode: TradingMode
    opened_at: datetime
    closed_at: datetime | None
    updated_at: datetime
