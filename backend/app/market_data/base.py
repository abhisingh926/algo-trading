"""Market data abstraction. Strategies, the paper broker and the backtester only ever see this interface."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from datetime import datetime

from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef, Quote


class MarketDataProvider(ABC):
    name: str = "base"
    poll_interval_seconds: float = 1.0

    @abstractmethod
    async def get_quote(self, symbols: Sequence[InstrumentRef]) -> list[Quote]:
        """Latest LTP / OHLC / volume / timestamp for each instrument."""

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: InstrumentRef,
        interval: Timeframe,
        start: datetime,
        end: datetime,
        *,
        session_only: bool = False,
    ) -> list[Candle]:
        """Closed and in-progress candles with start <= timestamp <= end, oldest first.

        `session_only` is a hint that the caller only needs regular exchange-session bars, so a provider that
        would otherwise produce bars outside the session (the 24x7 simulated feed) can skip them."""

    async def subscribe(self, symbols: Sequence[InstrumentRef]) -> AsyncIterator[Quote]:
        """Stream of quotes. Default implementation polls `get_quote`; adapters with a real
        WebSocket feed override this without changing any consumer."""
        while True:
            for quote in await self.get_quote(symbols):
                yield quote
            await asyncio.sleep(self.poll_interval_seconds)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:  # noqa: B027
        pass
