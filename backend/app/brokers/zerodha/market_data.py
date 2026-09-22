from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from app.brokers.zerodha import mapper
from app.brokers.zerodha.client import ZerodhaClient
from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef, Quote
from app.market_data.base import MarketDataProvider
from app.utils.time import IST, ensure_utc, utcnow

_CHUNK = timedelta(days=55)  # Kite caps minute data at 60 days per request


class ZerodhaMarketData(MarketDataProvider):
    name = "zerodha"

    def __init__(self, client: ZerodhaClient) -> None:
        self._client = client

    async def get_quote(self, symbols: Sequence[InstrumentRef]) -> list[Quote]:
        if not symbols:
            return []
        raw = await self._client.request("GET", "/quote", params=[("i", ref.key) for ref in symbols]) or {}
        now = utcnow()
        return [mapper.to_quote(ref, raw[ref.key], now) for ref in symbols if ref.key in raw]

    async def get_historical_data(
        self,
        symbol: InstrumentRef,
        interval: Timeframe,
        start: datetime,
        end: datetime,
        *,
        session_only: bool = False,
    ) -> list[Candle]:
        start, end = ensure_utc(start), ensure_utc(end)
        token, kite_interval = mapper.instrument_token(symbol), mapper.INTERVAL_TO_KITE[interval]
        candles: dict[datetime, Candle] = {}
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + _CHUNK, end)
            params = {
                "from": cursor.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "to": chunk_end.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S"),
            }
            raw = await self._client.request(
                "GET", f"/instruments/historical/{token}/{kite_interval}", params=params
            )
            candles.update({c.timestamp: c for c in mapper.to_candles(raw or {})})
            cursor = chunk_end + timedelta(seconds=1)
        return [candles[ts] for ts in sorted(candles) if start <= ts <= end]

    async def ping(self) -> bool:
        try:
            await self._client.request("GET", "/user/profile")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.close()
