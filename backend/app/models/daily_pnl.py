from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Enum, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime, utcnow
from app.domain.enums import TradingMode
from app.models.base import Money, TimestampMixin, UUIDMixin


class DailyPnL(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "daily_pnl"
    __table_args__ = (UniqueConstraint("trade_date", "trading_mode"),)

    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    trading_mode: Mapped[TradingMode] = mapped_column(Enum(TradingMode, native_enum=False, length=20))
    realized_pnl: Mapped[float] = mapped_column(Money, default=0, nullable=False)  # gross
    unrealized_pnl: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    charges: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    net_pnl: Mapped[float] = mapped_column(Money, default=0, nullable=False)  # realized - charges
    trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PortfolioSnapshot(UUIDMixin, Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (Index("ix_portfolio_snapshots_mode_ts", "trading_mode", "timestamp"),)

    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    trading_mode: Mapped[TradingMode] = mapped_column(Enum(TradingMode, native_enum=False, length=20))
    equity: Mapped[float] = mapped_column(Money, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Money, default=0, nullable=False)
    open_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
