from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import Money, TimestampMixin, UUIDMixin


class Instrument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("symbol", "exchange"),)

    symbol: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    segment: Mapped[str] = mapped_column(String(20), default="EQUITY", nullable=False)
    # Exchange-assigned token. Dhan uses it directly as securityId; Zerodha derives instrument_token from it.
    exchange_token: Mapped[str | None] = mapped_column(String(32), index=True)
    isin: Mapped[str | None] = mapped_column(String(12))
    lot_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tick_size: Mapped[float] = mapped_column(Money, default=0.05, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
