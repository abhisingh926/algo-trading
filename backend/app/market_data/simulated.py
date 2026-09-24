"""Deterministic synthetic market data.

Price is a pure function of (symbol, time): a sum of sinusoids of different periods plus smooth
value-noise. That makes live quotes and historical candles mutually consistent without any state,
so paper trading and backtests work out of the box with no broker credentials.

THIS IS NOT REAL MARKET DATA. Every candle/quote produced here is tagged source="simulated".
"""

from __future__ import annotations

import asyncio
import hashlib
import math
from collections.abc import Sequence
from datetime import datetime, timedelta

from app.core.exceptions import MarketDataError
from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef, Quote
from app.market_data.base import MarketDataProvider
from app.utils.time import IST, MARKET_CLOSE, MARKET_OPEN, ensure_utc, floor_time, in_market_session, utcnow

_BASE_PRICES = {
    "RELIANCE": 1420.0,
    "TCS": 3150.0,
    "INFY": 1510.0,
    "HDFCBANK": 960.0,
    "ICICIBANK": 1400.0,
    "SBIN": 850.0,
    "ITC": 410.0,
    "LT": 3600.0,
    "AXISBANK": 1120.0,
    "KOTAKBANK": 2000.0,
    "BHARTIARTL": 1900.0,
    "HINDUNILVR": 2600.0,
    "MARUTI": 15000.0,
    "WIPRO": 250.0,
    "TATAMOTORS": 700.0,
    "NIFTYBEES": 280.0,
    "NIFTY": 24500.0,
    "BANKNIFTY": 53000.0,
    "INDIAVIX": 14.0,
    "FINNIFTY": 23500.0,
}
# (period in minutes, amplitude in log-price)
_WAVES = (
    (23, 0.0005),
    (61, 0.0009),
    (173, 0.0022),
    (510, 0.0045),
    (1900, 0.0080),
    (7200, 0.0180),
    (40000, 0.0450),
)
_NOISE_AMP = 0.00025
_MAX_CANDLES = 300_000
_TWO_PI = 2 * math.pi


def _unit_hash(n: int, seed: int) -> float:
    """Cheap integer hash -> [-1, 1)."""
    x = (n ^ seed) & 0xFFFFFFFF
    x = ((x ^ (x >> 16)) * 0x45D9F3B) & 0xFFFFFFFF
    x = ((x ^ (x >> 16)) * 0x45D9F3B) & 0xFFFFFFFF
    x ^= x >> 16
    return x / 0x80000000 - 1.0


class _SymbolModel:
    __slots__ = ("base_log", "index", "phases", "seed")

    def __init__(self, key: str, symbol: str, index: bool = False) -> None:
        self.index = index
        digest = hashlib.md5(key.encode(), usedforsecurity=False).digest()
        self.seed = int.from_bytes(digest[:4], "big")
        base = _BASE_PRICES.get(symbol) or 150.0 + (self.seed % 2850)
        self.base_log = math.log(base)
        self.phases = [digest[4 + i] / 255 * _TWO_PI for i in range(len(_WAVES))]

    def price(self, minutes: float) -> float:
        value = self.base_log
        for (period, amp), phase in zip(_WAVES, self.phases, strict=True):
            value += amp * math.sin(_TWO_PI * minutes / period + phase)
        n = math.floor(minutes)
        frac = minutes - n
        value += _NOISE_AMP * (_unit_hash(n, self.seed) * (1 - frac) + _unit_hash(n + 1, self.seed) * frac)
        return round(math.exp(value), 2)

    def volume(self, minute: int, span_minutes: int) -> int:
        if self.index:
            return 0  # indices do not trade
        return int((0.6 + 0.4 * (_unit_hash(minute, self.seed ^ 0x9E3779B9) + 1)) * 2500 * span_minutes)


class SimulatedMarketDataProvider(MarketDataProvider):
    name = "simulated"

    def __init__(self, always_open: bool = True, poll_interval_seconds: float = 1.0) -> None:
        self.always_open = always_open
        self.poll_interval_seconds = poll_interval_seconds
        self._models: dict[str, _SymbolModel] = {}

    def _model(self, ref: InstrumentRef) -> _SymbolModel:
        if ref.key not in self._models:
            self._models[ref.key] = _SymbolModel(ref.key, ref.symbol, ref.segment == "INDEX")
        return self._models[ref.key]

    def price_at(self, ref: InstrumentRef, when: datetime) -> float:
        return self._model(ref).price(ensure_utc(when).timestamp() / 60)

    # ---- candles -------------------------------------------------------------------------------
    def _bar(self, model: _SymbolModel, start: datetime, span: timedelta, now: datetime) -> Candle:
        t0 = start.timestamp() / 60
        span_min = span.total_seconds() / 60
        t1 = min(t0 + span_min, now.timestamp() / 60)  # in-progress bar stops at "now"
        steps = max(2, min(int(span_min * 4), 16))
        prices = [model.price(t0 + (t1 - t0) * i / steps) for i in range(steps + 1)]
        return Candle(
            start,
            prices[0],
            max(prices),
            min(prices),
            prices[-1],
            model.volume(int(t0), max(int(span_min), 1)),
        )

    def _daily_window(self, day_start: datetime) -> tuple[datetime, timedelta] | None:
        if self.always_open:
            return day_start, timedelta(days=1)
        local = day_start.astimezone(IST)
        if local.weekday() >= 5:
            return None
        open_at = local.replace(hour=MARKET_OPEN.hour, minute=MARKET_OPEN.minute)
        close_at = local.replace(hour=MARKET_CLOSE.hour, minute=MARKET_CLOSE.minute)
        return open_at, close_at - open_at

    def _generate(
        self,
        ref: InstrumentRef,
        interval: Timeframe,
        start: datetime,
        end: datetime,
        session_only: bool = False,
    ) -> list[Candle]:
        model, now = self._model(ref), utcnow()
        start, end = ensure_utc(start), min(ensure_utc(end), now)
        step = timedelta(minutes=interval.minutes)
        cursor = floor_time(start, interval.minutes)
        if cursor < start:
            cursor += step
        if end < cursor:
            return []
        if (end - cursor) / step > _MAX_CANDLES:
            raise MarketDataError(f"Requested range is too large for timeframe {interval.value}")

        candles: list[Candle] = []
        while cursor <= end:
            if interval is Timeframe.D1:
                window = self._daily_window(cursor)
                if window is not None:
                    bar = self._bar(model, window[0], window[1], now)
                    candles.append(Candle(cursor, bar.open, bar.high, bar.low, bar.close, bar.volume))
                cursor = floor_time(cursor + timedelta(hours=30), 1440)  # next IST midnight, DST-free
            else:
                if (self.always_open and not session_only) or in_market_session(cursor):
                    candles.append(self._bar(model, cursor, step, now))
                cursor += step
        return candles

    async def get_historical_data(
        self,
        symbol: InstrumentRef,
        interval: Timeframe,
        start: datetime,
        end: datetime,
        *,
        session_only: bool = False,
    ) -> list[Candle]:
        return await asyncio.to_thread(self._generate, symbol, interval, start, end, session_only)

    # ---- quotes --------------------------------------------------------------------------------
    def _quote(self, ref: InstrumentRef, now: datetime) -> Quote:
        model = self._model(ref)
        day_start = floor_time(now, 1440)
        t0, t1 = day_start.timestamp() / 60, now.timestamp() / 60
        steps = max(1, int((t1 - t0) // 5))
        samples = [model.price(t0 + (t1 - t0) * i / steps) for i in range(steps + 1)]
        ltp = samples[-1]
        return Quote(
            symbol=ref.symbol,
            exchange=ref.exchange,
            ltp=ltp,
            open=samples[0],
            high=max(samples),
            low=min(samples),
            close=model.price(t0 - 1),
            volume=model.volume(int(t0), max(int(t1 - t0), 1)),
            timestamp=now,
            source=self.name,
        )

    async def get_quote(self, symbols: Sequence[InstrumentRef]) -> list[Quote]:
        now = utcnow()
        return [self._quote(ref, now) for ref in symbols]
