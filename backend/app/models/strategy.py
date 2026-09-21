from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime
from app.domain.enums import StrategyStatus, StrategyType, Timeframe, TradingMode
from app.models.base import Money, Ratio, TimestampMixin, UUIDMixin
from app.models.broker import BrokerAccount


class Strategy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategies"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    broker_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType, native_enum=False, length=30))
    status: Mapped[StrategyStatus] = mapped_column(
        Enum(StrategyStatus, native_enum=False, length=20), default=StrategyStatus.STOPPED, index=True
    )
    symbol: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    timeframe: Mapped[Timeframe] = mapped_column(
        Enum(Timeframe, native_enum=False, length=5, values_callable=lambda e: [m.value for m in e])
    )
    capital: Mapped[float] = mapped_column(Money, nullable=False)
    risk_per_trade: Mapped[float] = mapped_column(Ratio, nullable=False)
    stop_loss_pct: Mapped[float] = mapped_column(Ratio, nullable=False)
    target_pct: Mapped[float | None] = mapped_column(Ratio)
    allow_short: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trading_mode: Mapped[TradingMode] = mapped_column(
        Enum(TradingMode, native_enum=False, length=20), default=TradingMode.PAPER
    )
    last_candle_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_signal_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_error: Mapped[str | None] = mapped_column(Text)

    parameter_rows: Mapped[list[StrategyParameter]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan", lazy="selectin"
    )
    broker_account: Mapped[BrokerAccount | None] = relationship(lazy="selectin")

    @property
    def parameters(self) -> dict[str, Any]:
        return {row.key: row.value for row in self.parameter_rows}

    @property
    def broker_name(self) -> str | None:
        return self.broker_account.name if self.broker_account else None


class StrategyParameter(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategy_parameters"
    __table_args__ = (UniqueConstraint("strategy_id", "key"),)

    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)

    strategy: Mapped[Strategy] = relationship(back_populates="parameter_rows")
