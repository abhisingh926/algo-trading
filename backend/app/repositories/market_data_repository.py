from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, insert, select

from app.domain.enums import Timeframe
from app.domain.types import Candle
from app.models.market_data import CandleRecord
from app.repositories.base import BaseRepository

_CHUNK = 2000


class MarketDataRepository(BaseRepository[CandleRecord]):
    """The only place that knows where bars are stored (swap here for a time-series database)."""

    model = CandleRecord

    def _range(
        self,
        symbol: str,
        exchange: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        source: str | None = None,
    ):  # noqa: ANN202
        """Filter for one instrument/timeframe window. `source` keeps real and synthetic bars apart."""
        conditions = [
            CandleRecord.symbol == symbol,
            CandleRecord.exchange == exchange,
            CandleRecord.timeframe == timeframe,
            CandleRecord.timestamp >= start,
            CandleRecord.timestamp <= end,
        ]
        if source is not None:
            conditions.append(CandleRecord.source == source)
        return tuple(conditions)

    async def get_candles(
        self,
        symbol: str,
        exchange: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        source: str | None = None,
    ) -> list[Candle]:
        stmt = (
            select(
                CandleRecord.timestamp,
                CandleRecord.open,
                CandleRecord.high,
                CandleRecord.low,
                CandleRecord.close,
                CandleRecord.volume,
            )
            .where(*self._range(symbol, exchange, timeframe, start, end, source))
            .order_by(CandleRecord.timestamp.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            Candle(r.timestamp, float(r.open), float(r.high), float(r.low), float(r.close), int(r.volume))
            for r in rows
        ]

    async def coverage(
        self,
        symbol: str,
        exchange: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        source: str | None = None,
    ) -> tuple[int, datetime | None, datetime | None, str | None]:
        stmt = select(
            func.count(),
            func.min(CandleRecord.timestamp),
            func.max(CandleRecord.timestamp),
            func.max(CandleRecord.source),
        ).where(*self._range(symbol, exchange, timeframe, start, end, source))
        count, first, last, found_source = (await self.session.execute(stmt)).one()
        return int(count or 0), first, last, found_source

    async def save_candles(
        self, symbol: str, exchange: str, timeframe: Timeframe, candles: Sequence[Candle], source: str
    ) -> int:
        """Insert only bars that are not stored yet. Returns number of new rows."""
        if not candles:
            return 0
        start, end = candles[0].timestamp, candles[-1].timestamp
        stmt = select(CandleRecord.timestamp).where(
            *self._range(symbol, exchange, timeframe, start, end, source)
        )
        existing = {ts for (ts,) in (await self.session.execute(stmt)).all()}
        rows = [
            {
                "symbol": symbol,
                "exchange": exchange,
                "timeframe": timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "source": source,
            }
            for c in candles
            if c.timestamp not in existing
        ]
        for i in range(0, len(rows), _CHUNK):
            await self.session.execute(insert(CandleRecord), rows[i : i + _CHUNK])
        return len(rows)
