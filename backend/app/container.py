"""Process-wide singletons (composition root). Everything request-scoped lives in services/factory.py."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.brokers.registry import BrokerRegistry
from app.core.cache import QuoteCache
from app.core.config import Settings
from app.core.database import Database
from app.market_data.base import MarketDataProvider
from app.market_data.factory import build_market_data_provider
from app.research.runner import ResearchRunner
from app.utils.time import utcnow


@dataclass(slots=True)
class _Heartbeat:
    at: datetime
    interval: float
    error: str | None = None


class WorkerRegistry:
    """In-process liveness tracking for background workers (feeds the System Status panel)."""

    def __init__(self) -> None:
        self._beats: dict[str, _Heartbeat] = {}

    def beat(self, name: str, interval: float, error: str | None = None) -> None:
        self._beats[name] = _Heartbeat(utcnow(), interval, error)

    def status(self, name: str) -> tuple[str, str | None]:
        beat = self._beats.get(name)
        if beat is None:
            return "STOPPED", "Worker has not started"
        age = (utcnow() - beat.at).total_seconds()
        if age > max(beat.interval * 4, 15):
            return "STOPPED", f"No heartbeat for {age:.0f}s"
        if beat.error:
            return "DEGRADED", beat.error
        return "RUNNING", None


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    db: Database
    market_data: MarketDataProvider
    quote_cache: QuoteCache
    brokers: BrokerRegistry
    workers: WorkerRegistry = field(default_factory=WorkerRegistry)
    research_runner: ResearchRunner = field(default_factory=ResearchRunner)
    fill_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # Shared by every MarketDataService built from this container, so one process does not re-request a range
    # the provider has already answered. Scoped here rather than to the module so tests and a second database
    # never inherit another container's guard.
    fetch_attempts: dict[tuple[str, str, str], float] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        settings: Settings,
        *,
        db: Database | None = None,
        market_data: MarketDataProvider | None = None,
        broker_transport: httpx.AsyncBaseTransport | None = None,
        use_redis: bool = True,
    ) -> AppContainer:
        provider = market_data or build_market_data_provider(settings)
        container = cls(
            settings=settings,
            db=db or Database(settings.database_url, settings.database_echo),
            market_data=provider,
            quote_cache=QuoteCache(settings.redis_url if use_redis else None),
            brokers=BrokerRegistry(settings, provider, broker_transport),
        )
        container.research_runner.bind(container)
        return container

    async def close(self) -> None:
        await self.research_runner.shutdown()
        await self.brokers.close()
        await self.market_data.close()
        await self.quote_cache.close()
        await self.db.dispose()
