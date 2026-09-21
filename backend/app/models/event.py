from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.enums import EventLevel
from app.models.base import TimestampMixin, UUIDMixin


class SystemEvent(UUIDMixin, TimestampMixin, Base):
    """Persisted audit log of trading actions (mirrors the structured log stream)."""

    __tablename__ = "system_events"
    __table_args__ = (Index("ix_system_events_created", "created_at"),)

    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    level: Mapped[EventLevel] = mapped_column(
        Enum(EventLevel, native_enum=False, length=10), default=EventLevel.INFO
    )
    message: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    strategy_id: Mapped[str | None] = mapped_column(String(36), index=True)
    order_id: Mapped[str | None] = mapped_column(String(36))
    symbol: Mapped[str | None] = mapped_column(String(50))
