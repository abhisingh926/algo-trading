from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow
from app.domain.enums import PositionSide, PositionStatus, TradingMode
from app.models.base import Money, TimestampMixin, UUIDMixin
from app.models.strategy import Strategy


class Position(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (Index("ix_positions_status_symbol", "status", "symbol"),)

    strategy_id: Mapped[str | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), index=True
    )
    broker_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="SET NULL")
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    side: Mapped[PositionSide] = mapped_column(Enum(PositionSide, native_enum=False, length=10))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_entry_price: Mapped[float] = mapped_column(Money, nullable=False)
    last_price: Mapped[float | None] = mapped_column(Money)
    unrealized_pnl: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    # Entry-side charges not yet attributed to a closed trade.
    charges_accrued: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    stop_loss: Mapped[float | None] = mapped_column(Money)
    target: Mapped[float | None] = mapped_column(Money)
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus, native_enum=False, length=10), default=PositionStatus.OPEN
    )
    trading_mode: Mapped[TradingMode] = mapped_column(Enum(TradingMode, native_enum=False, length=20))
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    strategy: Mapped[Strategy | None] = relationship(lazy="selectin")

    @property
    def strategy_name(self) -> str | None:
        return self.strategy.name if self.strategy else None

    def mark(self, price: float) -> None:
        self.last_price = price
        self.unrealized_pnl = round((price - self.average_entry_price) * self.quantity * self.side.sign, 4)
