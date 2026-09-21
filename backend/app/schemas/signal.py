from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.enums import SignalStatus, SignalType
from app.schemas.common import ORMModel


class SignalRead(ORMModel):
    id: str
    strategy_id: str
    strategy_name: str | None
    symbol: str
    exchange: str
    signal_type: SignalType
    price: float
    reason: str
    indicators: dict[str, Any]
    status: SignalStatus
    status_reason: str | None
    order_id: str | None
    candle_time: datetime | None
    created_at: datetime
