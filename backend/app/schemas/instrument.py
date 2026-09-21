from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import Timeframe
from app.schemas.common import ORMModel


class InstrumentCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    exchange: str = Field(default="NSE", max_length=10)
    name: str = Field(default="", max_length=255)
    exchange_token: str | None = Field(default=None, max_length=32)
    lot_size: int = Field(default=1, ge=1)
    tick_size: float = Field(default=0.05, gt=0)

    @field_validator("symbol", "exchange")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()


class InstrumentRead(ORMModel):
    id: str
    symbol: str
    exchange: str
    name: str
    segment: str
    exchange_token: str | None
    lot_size: int
    tick_size: float
    is_active: bool


class QuoteRead(ORMModel):
    symbol: str
    exchange: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    source: str


class CandleRead(ORMModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalSyncRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    timeframe: Timeframe
    start_date: date
    end_date: date


class HistoricalSyncResult(BaseModel):
    stored: int
    total: int
    source: str
