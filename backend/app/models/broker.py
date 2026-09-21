from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime
from app.domain.enums import BrokerEnvironment, BrokerType, ConnectionStatus
from app.models.base import TimestampMixin, UUIDMixin


class BrokerAccount(UUIDMixin, TimestampMixin, Base):
    """A configured broker connection. Credentials are NOT stored here - they come from the environment."""

    __tablename__ = "broker_accounts"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    broker_type: Mapped[BrokerType] = mapped_column(
        Enum(BrokerType, native_enum=False, length=20), index=True
    )
    environment: Mapped[BrokerEnvironment] = mapped_column(
        Enum(BrokerEnvironment, native_enum=False, length=20)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Application-level live guard: a LIVE account must be explicitly armed before it may send orders.
    live_armed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    connection_status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, native_enum=False, length=20), default=ConnectionStatus.UNKNOWN
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
