"""Mixins shared by all models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import UTCDateTime, new_uuid, utcnow

# DECIMAL in MySQL (exact storage), float in Python (simple maths / JSON).
Money = Numeric(18, 4, asdecimal=False)
Ratio = Numeric(10, 6, asdecimal=False)


class UUIDMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False)
