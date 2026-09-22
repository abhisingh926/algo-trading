"""Trading-session helpers. Research works on regular NSE sessions (09:15 to 15:30 IST) only, whatever the
market data provider returns, so every analytic (VWAP, gap, opening range, relative volume) is consistent."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.domain.types import Candle
from app.utils.time import IST, MARKET_CLOSE, MARKET_OPEN, ensure_utc, in_market_session

SESSION_MINUTES = (MARKET_CLOSE.hour * 60 + MARKET_CLOSE.minute) - (
    MARKET_OPEN.hour * 60 + MARKET_OPEN.minute
)  # 375


@dataclass(frozen=True, slots=True)
class Session:
    day: date
    bars: list[Candle]


def ist_day(ts: datetime) -> date:
    return ensure_utc(ts).astimezone(IST).date()


def minutes_into_session(ts: datetime) -> int:
    local = ensure_utc(ts).astimezone(IST)
    return local.hour * 60 + local.minute - (MARKET_OPEN.hour * 60 + MARKET_OPEN.minute)


def filter_session(bars: list[Candle]) -> list[Candle]:
    return [c for c in bars if in_market_session(c.timestamp)]


def closed_before(bars: list[Candle], as_of: datetime, minutes: int) -> list[Candle]:
    """Bars that were complete at `as_of`. This is the look-ahead guard: nothing later can leak in."""
    limit = ensure_utc(as_of) - timedelta(minutes=minutes)
    return [c for c in bars if ensure_utc(c.timestamp) <= limit]


def group_sessions(bars: list[Candle]) -> list[Session]:
    by_day: dict[date, list[Candle]] = defaultdict(list)
    for bar in sorted(bars, key=lambda c: c.timestamp):
        by_day[ist_day(bar.timestamp)].append(bar)
    return [Session(day, by_day[day]) for day in sorted(by_day)]


def aggregate(bars: list[Candle], timestamp: datetime | None = None) -> Candle:
    return Candle(
        timestamp or bars[0].timestamp,
        bars[0].open,
        max(b.high for b in bars),
        min(b.low for b in bars),
        bars[-1].close,
        sum(b.volume for b in bars),
    )


def resample(bars: list[Candle], minutes: int) -> list[Candle]:
    """Merge session bars into larger session-anchored bars (buckets start at 09:15 IST)."""
    buckets: dict[tuple[date, int], list[Candle]] = {}
    for bar in sorted(bars, key=lambda c: c.timestamp):
        buckets.setdefault(
            (ist_day(bar.timestamp), minutes_into_session(bar.timestamp) // minutes), []
        ).append(bar)
    return [aggregate(group) for _, group in sorted(buckets.items())]


def to_daily(sessions: list[Session]) -> list[Candle]:
    return [aggregate(s.bars) for s in sessions if s.bars]


def to_weekly(daily: list[Candle]) -> list[Candle]:
    weeks: dict[tuple[int, int], list[Candle]] = {}
    for bar in daily:
        iso = ist_day(bar.timestamp).isocalendar()
        weeks.setdefault((iso.year, iso.week), []).append(bar)
    return [aggregate(group) for _, group in sorted(weeks.items())]


def vwap_series(session_bars: list[Candle]) -> list[float]:
    """Cumulative VWAP of ONE session, using the typical price."""
    out: list[float] = []
    cum_pv = cum_v = 0.0
    for bar in session_bars:
        typical = (bar.high + bar.low + bar.close) / 3
        weight = bar.volume if bar.volume > 0 else 1.0
        cum_pv += typical * weight
        cum_v += weight
        out.append(cum_pv / cum_v)
    return out


def opening_range(session_bars: list[Candle], minutes: int) -> tuple[float, float] | None:
    """High and low of the first `minutes` of the session, or None until that window has completed."""
    if not session_bars:
        return None
    step = _bar_minutes(session_bars)
    count = max(minutes // step, 1)
    window = session_bars[:count]
    if len(window) < count:
        return None
    return max(b.high for b in window), min(b.low for b in window)


def _bar_minutes(bars: list[Candle]) -> int:
    if len(bars) >= 2:
        return max(int((bars[1].timestamp - bars[0].timestamp).total_seconds() // 60), 1)
    return 15


def market_state(now: datetime) -> str:
    """OPEN, PRE_MARKET, POST_MARKET or CLOSED (weekend). Exchange holidays are detected from missing data."""
    local = ensure_utc(now).astimezone(IST)
    if local.weekday() >= 5:
        return "CLOSED"
    if local.time() < MARKET_OPEN:
        return "PRE_MARKET"
    if local.time() >= MARKET_CLOSE:
        return "POST_MARKET"
    return "OPEN"
