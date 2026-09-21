"""Dhan market data (REST). Read-only: it can never place an order.

`subscribe` uses the polling default from MarketDataProvider. Dhan's binary WebSocket feed can be
added here later by overriding `subscribe` - no consumer changes.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from app.brokers.dhan import mapper
from app.brokers.dhan.client import DhanClient
from app.core.exceptions import MarketDataError
from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef, Quote
from app.market_data.base import MarketDataProvider
from app.utils.time import IST, ensure_utc, utcnow

_CHUNK = timedelta(days=85)  # Dhan serves at most ~90 days of intraday data per request


class DhanMarketData(MarketDataProvider):
    name = "dhan"
    poll_interval_seconds = 1.0

    def __init__(self, client: DhanClient) -> None:
        self._client = client

    async def get_quote(self, symbols: Sequence[InstrumentRef]) -> list[Quote]:
        if not symbols:
            return []
        body: dict[str, list[int]] = {}
        for ref in symbols:
            body.setdefault(mapper.segment(ref), []).append(int(mapper.security_id(ref)))
        raw = await self._client.request("POST", "/marketfeed/quote", json=body)
        data = (raw or {}).get("data") or {}
        now, quotes = utcnow(), []
        for ref in symbols:
            entry = (data.get(mapper.segment(ref)) or {}).get(mapper.security_id(ref))
            if entry:
                quotes.append(mapper.to_quote(ref, entry, now))
        return quotes

    async def get_historical_data(
        self, symbol: InstrumentRef, interval: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        start, end = ensure_utc(start), ensure_utc(end)
        base = {
            "securityId": mapper.security_id(symbol),
            "exchangeSegment": mapper.segment(symbol),
            "instrument": "EQUITY",
        }
        candles: list[Candle] = []
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + _CHUNK, end)
            if interval is Timeframe.D1:
                path = "/charts/historical"
                body = base | {
                    "expiryCode": 0,
                    "fromDate": cursor.astimezone(IST).strftime("%Y-%m-%d"),
                    "toDate": (chunk_end.astimezone(IST) + timedelta(days=1)).strftime("%Y-%m-%d"),
                }
            else:
                if interval not in mapper.INTRADAY_INTERVAL:
                    raise MarketDataError(f"Dhan does not support timeframe {interval.value}")
                path = "/charts/intraday"
                body = base | {
                    "interval": mapper.INTRADAY_INTERVAL[interval],
                    "fromDate": cursor.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S"),
                    "toDate": chunk_end.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S"),
                }
            candles.extend(mapper.to_candles(await self._client.request("POST", path, json=body) or {}))
            cursor = chunk_end + timedelta(seconds=1)
        unique = {c.timestamp: c for c in candles if start <= c.timestamp <= end}
        return [unique[ts] for ts in sorted(unique)]

    async def ping(self) -> bool:
        try:
            await self._client.request("GET", "/profile")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.close()
