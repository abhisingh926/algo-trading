from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime
from app.domain.enums import Timeframe
from app.models.base import Money


class CandleRecord(Base):
    """Historical OHLCV bars kept for backtesting.

    Ticks are intentionally NOT persisted here: live quotes only flow through the quote cache. The
    MarketDataRepository is the single seam to swap when bars/ticks move to a time-series store.
    """

    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "timeframe", "timestamp", name="uq_candles_bar"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    timeframe: Mapped[Timeframe] = mapped_column(
        Enum(Timeframe, native_enum=False, length=5, values_callable=lambda e: [m.value for m in e])
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    open: Mapped[float] = mapped_column(Money, nullable=False)
    high: Mapped[float] = mapped_column(Money, nullable=False)
    low: Mapped[float] = mapped_column(Money, nullable=False)
    close: Mapped[float] = mapped_column(Money, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="simulated", nullable=False)
