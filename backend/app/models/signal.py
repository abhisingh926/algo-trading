from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime
from app.domain.enums import SignalStatus, SignalType
from app.models.base import Money, TimestampMixin, UUIDMixin
from app.models.strategy import Strategy


class Signal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "signals"
    __table_args__ = (Index("ix_signals_strategy_created", "strategy_id", "created_at"),)

    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[str | None] = mapped_column(String(36), index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType, native_enum=False, length=10))
    price: Mapped[float] = mapped_column(Money, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    indicators: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[SignalStatus] = mapped_column(
        Enum(SignalStatus, native_enum=False, length=20), default=SignalStatus.GENERATED
    )
    status_reason: Mapped[str | None] = mapped_column(Text)
    candle_time: Mapped[datetime | None] = mapped_column(UTCDateTime)

    strategy: Mapped[Strategy] = relationship(lazy="selectin")

    @property
    def strategy_name(self) -> str | None:
        return self.strategy.name if self.strategy else None
