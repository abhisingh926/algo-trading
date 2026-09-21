from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime
from app.domain.enums import ExitReason, PositionSide, TradingMode
from app.models.base import Money, TimestampMixin, UUIDMixin
from app.models.strategy import Strategy


class Trade(UUIDMixin, TimestampMixin, Base):
    """A closed round trip (entry + exit), the unit every P&L statistic is computed from."""

    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_exit_time", "exit_time"),
        Index("ix_trades_strategy_exit", "strategy_id", "exit_time"),
    )

    position_id: Mapped[str | None] = mapped_column(
        ForeignKey("positions.id", ondelete="SET NULL"), index=True
    )
    strategy_id: Mapped[str | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"))
    exit_order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    symbol: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    side: Mapped[PositionSide] = mapped_column(Enum(PositionSide, native_enum=False, length=10))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[float] = mapped_column(Money, nullable=False)
    exit_price: Mapped[float] = mapped_column(Money, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    exit_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    gross_pnl: Mapped[float] = mapped_column(Money, nullable=False)
    charges: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    net_pnl: Mapped[float] = mapped_column(Money, nullable=False)
    exit_reason: Mapped[ExitReason] = mapped_column(Enum(ExitReason, native_enum=False, length=20))
    trading_mode: Mapped[TradingMode] = mapped_column(Enum(TradingMode, native_enum=False, length=20))

    strategy: Mapped[Strategy | None] = relationship(lazy="selectin")

    @property
    def strategy_name(self) -> str | None:
        return self.strategy.name if self.strategy else None
