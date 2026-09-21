"""Time helpers. Storage is UTC; the Indian trading day is defined in IST."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def ist_date(value: datetime) -> date:
    return ensure_utc(value).astimezone(IST).date()


def ist_day_number(value: datetime) -> int:
    """Fast integer day key in IST (fixed +05:30 offset, no DST) for hot loops."""
    return int((value.timestamp() + 19800) // 86400)


def ist_today() -> date:
    return ist_date(utcnow())


def ist_day_start_utc(day: date | None = None) -> datetime:
    day = day or ist_today()
    return datetime.combine(day, time.min, tzinfo=IST).astimezone(UTC)


def ist_day_end_utc(day: date) -> datetime:
    return ist_day_start_utc(day) + timedelta(days=1) - timedelta(microseconds=1)


def floor_time(value: datetime, minutes: int) -> datetime:
    """Floor to a bar boundary. Daily bars are anchored to the IST midnight."""
    value = ensure_utc(value)
    if minutes >= 1440:
        return ist_day_start_utc(ist_date(value))
    epoch = int(value.timestamp())
    return datetime.fromtimestamp(epoch - epoch % (minutes * 60), UTC)


def in_market_session(value: datetime) -> bool:
    local = ensure_utc(value).astimezone(IST)
    return local.weekday() < 5 and MARKET_OPEN <= local.time() < MARKET_CLOSE
