from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.core.database import Base, UTCDateTime
from app.domain.enums import BacktestStatus, ExitReason, PositionSide, StrategyType, Timeframe
from app.models.base import Money, TimestampMixin, UUIDMixin


class Backtest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtests"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    strategy_id: Mapped[str | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType, native_enum=False, length=30))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    timeframe: Mapped[Timeframe] = mapped_column(
        Enum(Timeframe, native_enum=False, length=5, values_callable=lambda e: [m.value for m in e])
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Money, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[BacktestStatus] = mapped_column(
        Enum(BacktestStatus, native_enum=False, length=20), default=BacktestStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    equity_curve: Mapped[list[dict[str, Any]] | None] = deferred(mapped_column(JSON))
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    trades: Mapped[list[BacktestTrade]] = relationship(
        back_populates="backtest",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="BacktestTrade.entry_time",
    )


class BacktestTrade(UUIDMixin, Base):
    __tablename__ = "backtest_trades"

    backtest_id: Mapped[str] = mapped_column(ForeignKey("backtests.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[PositionSide] = mapped_column(Enum(PositionSide, native_enum=False, length=10))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    exit_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    entry_price: Mapped[float] = mapped_column(Money, nullable=False)
    exit_price: Mapped[float] = mapped_column(Money, nullable=False)
    gross_pnl: Mapped[float] = mapped_column(Money, nullable=False)
    charges: Mapped[float] = mapped_column(Money, nullable=False)
    net_pnl: Mapped[float] = mapped_column(Money, nullable=False)
    exit_reason: Mapped[ExitReason] = mapped_column(Enum(ExitReason, native_enum=False, length=20))

    backtest: Mapped[Backtest] = relationship(back_populates="trades")
