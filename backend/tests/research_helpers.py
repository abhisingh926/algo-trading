"""Builders for research tests: realistic multi-session candle data with a controllable shape."""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.types import Candle

IST = ZoneInfo("Asia/Kolkata")


def ist(year: int, month: int, day: int, hour: int = 9, minute: int = 15) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=IST).astimezone(UTC)


def trading_days(start: date, count: int) -> list[date]:
    days, cursor = [], start
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def make_session(
    day: date,
    open_price: float,
    path: Callable[[int, int], float] | None = None,
    bars: int = 25,
    minutes: int = 15,
    volume: int = 10_000,
    spread: float = 0.002,
    volume_of: Callable[[int], int] | None = None,
) -> list[Candle]:
    """One session of `bars` bars. `path(i, n)` returns the close of bar i (default: flat at open_price)."""
    out, previous = [], open_price
    start = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST).astimezone(UTC)
    for i in range(bars):
        close = path(i, bars) if path else open_price
        high = max(previous, close) * (1 + spread)
        low = min(previous, close) * (1 - spread)
        vol = volume_of(i) if volume_of else volume
        out.append(Candle(start + timedelta(minutes=minutes * i), previous, high, low, close, vol))
        previous = close
    return out


def make_history(
    sessions: int,
    start: date = date(2025, 1, 1),
    base: float = 1000.0,
    drift: float = 0.0004,
    noise: float = 0.004,
    seed: int = 1,
    volume: int = 20_000,
    minutes: int = 15,
) -> list[Candle]:
    """A random-walk history of `sessions` regular sessions, returned oldest first."""
    rng = random.Random(seed)
    bars_per_day = 375 // minutes
    price, out = base, []
    for day in trading_days(start, sessions):
        day_start = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST).astimezone(UTC)
        price *= 1 + rng.gauss(0, 0.004)  # overnight gap
        previous = price
        for i in range(bars_per_day):
            price *= 1 + rng.gauss(drift / bars_per_day, noise / math.sqrt(bars_per_day) * 2)
            high = max(previous, price) * (1 + abs(rng.gauss(0, 0.0008)))
            low = min(previous, price) * (1 - abs(rng.gauss(0, 0.0008)))
            out.append(
                Candle(
                    day_start + timedelta(minutes=minutes * i),
                    previous,
                    high,
                    low,
                    price,
                    int(volume * rng.uniform(0.6, 1.4)),
                )
            )
            previous = price
    return out


# ---- builders used by the research unit tests ---------------------------------------------------------------
from app.domain.types import InstrumentRef  # noqa: E402
from app.research import market as mkt  # noqa: E402
from app.research.config import DEFAULT_THRESHOLDS  # noqa: E402
from app.research.contracts import Breadth, IndexSnapshot, Provenance  # noqa: E402
from app.research.features import SymbolInput, build_bundle  # noqa: E402

TF_FULL = ["5m", "15m", "30m", "1h", "daily", "weekly"]


def provenance(
    source: str = "test-feed", source_type: str = "MARKET_DATA_PROVIDER", confidence: float = 0.9
):  # noqa: ANN201
    now = datetime(2026, 1, 20, 6, 30, tzinfo=UTC)
    return Provenance(source=source, source_type=source_type, retrieved_at=now, data_as_of=now, confidence=confidence)  # type: ignore[arg-type]


def cut_session(bars: list[Candle], keep_last_session_bars: int) -> list[Candle]:
    """Drop bars so that the final session has only `keep_last_session_bars` bars (a mid-session snapshot)."""
    last_day = bars[-1].timestamp.astimezone(IST).date()
    day_bars = [b for b in bars if b.timestamp.astimezone(IST).date() == last_day]
    return [b for b in bars if b not in day_bars] + day_bars[:keep_last_session_bars]


def symbol_input(
    bars: list[Candle],
    *,
    as_of: datetime | None = None,
    bars_5m: list[Candle] | None = None,
    source_type: str = "MARKET_DATA_PROVIDER",
    reliability: float = 0.9,
    quote=None,
) -> SymbolInput:  # noqa: ANN001
    end = bars[-1].timestamp + timedelta(minutes=15)
    return SymbolInput(
        "TEST",
        "Test Co",
        "IT",
        InstrumentRef("TEST"),
        bars,
        bars_5m or [],
        quote,
        "test-feed",
        source_type,
        reliability,
        as_of or end,
        as_of or end,
    )


def make_bundle(
    sessions: int = 80,
    keep_bars: int | None = 12,
    seed: int = 3,
    timeframes: list[str] | None = None,
    **history: object,
):  # noqa: ANN201
    bars = make_history(sessions, seed=seed, **history)  # type: ignore[arg-type]
    if keep_bars is not None:
        bars = cut_session(bars, keep_bars)
    inp = symbol_input(bars)
    return inp, build_bundle(inp, timeframes or ["15m", "30m", "1h", "daily"])


def market_context(nifty_up: bool = True, vix: float = 14.0):  # noqa: ANN201
    def snap(symbol: str, up: bool):  # noqa: ANN202
        base = 1000.0
        return IndexSnapshot(
            symbol=symbol,
            name=symbol,
            available=True,
            price=base * (1.02 if up else 0.98),
            change_pct=0.6 if up else -0.6,
            ema20=base,
            ema50=base * (0.99 if up else 1.01),
            trend="UP" if up else "DOWN",
            rsi=60 if up else 40,
            ret_5d_pct=1.0 if up else -1.0,
        )

    vix_snap = IndexSnapshot(symbol="INDIAVIX", name="INDIA VIX", available=True, price=vix, change_pct=0.0)
    breadth = Breadth(
        advances=35 if nifty_up else 10,
        declines=15 if nifty_up else 40,
        unchanged=0,
        universe_size=50,
        pct_above_vwap=60,
        pct_above_ema20=65 if nifty_up else 30,
    )
    return mkt.build_context(
        datetime(2026, 1, 20, 6, 30, tzinfo=UTC),
        "OPEN",
        "open",
        [snap("NIFTY", nifty_up), snap("BANKNIFTY", nifty_up)],
        vix_snap,
        breadth,
        [],
        provenance(),
        DEFAULT_THRESHOLDS,
    )
