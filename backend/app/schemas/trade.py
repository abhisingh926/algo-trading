from __future__ import annotations

from datetime import datetime

from app.domain.enums import ExitReason, PositionSide, TradingMode
from app.schemas.common import ORMModel


class TradeRead(ORMModel):
    id: str
    position_id: str | None
    strategy_id: str | None
    strategy_name: str | None
    symbol: str
    exchange: str
    side: PositionSide
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    gross_pnl: float
    charges: float
    net_pnl: float
    exit_reason: ExitReason
    trading_mode: TradingMode
    created_at: datetime
