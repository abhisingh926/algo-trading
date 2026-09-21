from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime
from app.models.base import Money, Ratio, TimestampMixin, UUIDMixin


class RiskConfiguration(UUIDMixin, TimestampMixin, Base):
    """Single global row: risk limits + the persisted kill switch state."""

    __tablename__ = "risk_configurations"

    max_risk_per_trade: Mapped[float] = mapped_column(Ratio, nullable=False)
    max_daily_loss: Mapped[float] = mapped_column(Money, nullable=False)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    max_open_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    max_position_size: Mapped[int] = mapped_column(Integer, nullable=False)
    max_order_value: Mapped[float] = mapped_column(Money, nullable=False)
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False)
    max_strategy_drawdown: Mapped[float] = mapped_column(Ratio, nullable=False)
    close_positions_on_kill_switch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kill_switch_activated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    kill_switch_reason: Mapped[str | None] = mapped_column(Text)
