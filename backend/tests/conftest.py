"""Shared fixtures. Everything runs on in-memory SQLite with fake market data and mocked broker HTTP -
no test can reach a real broker or a real database."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio

from app.container import AppContainer
from app.core.config import Settings
from app.core.database import Database
from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef, Quote
from app.main import create_app
from app.market_data.base import MarketDataProvider
from app.services.factory import Services
from app.trading.engine import TradingEngine


class FakeMarketData(MarketDataProvider):
    """Deterministic provider: tests set prices and candles explicitly."""

    name = "fake"

    def __init__(self) -> None:
        self.prices: dict[str, float] = {"RELIANCE": 1000.0, "INFY": 1500.0, "TCS": 3000.0}
        self.candles: dict[str, list[Candle]] = {}

    def set_price(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price

    async def get_quote(self, symbols: Sequence[InstrumentRef]) -> list[Quote]:
        now = datetime.now(UTC)
        return [
            Quote(
                r.symbol,
                r.exchange,
                self.prices[r.symbol],
                self.prices[r.symbol],
                self.prices[r.symbol],
                self.prices[r.symbol],
                self.prices[r.symbol],
                1000,
                now,
                self.name,
            )
            for r in symbols
            if r.symbol in self.prices
        ]

    async def get_historical_data(
        self, symbol: InstrumentRef, interval: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        return [c for c in self.candles.get(symbol.symbol, []) if start <= c.timestamp <= end]


def make_candles(
    closes: Sequence[float],
    *,
    start: datetime | None = None,
    minutes: int = 5,
    spread: float = 0.5,
    volume: int = 1000,
) -> list[Candle]:
    """Bars whose open is the previous close; high/low are +/- spread around the body."""
    start = start or datetime(2026, 1, 5, 4, 0, tzinfo=UTC)  # 09:30 IST, a Monday
    candles, previous = [], closes[0]
    for i, close in enumerate(closes):
        candles.append(
            Candle(
                start + timedelta(minutes=minutes * i),
                previous,
                max(previous, close) + spread,
                min(previous, close) - spread,
                close,
                volume,
            )
        )
        previous = close
    return candles


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "auth_enabled": False,
        "run_workers": False,
        "order_retry_backoff_seconds": 0,
        "secret_key": "test-secret-key-not-a-real-secret-0123456789",
        "paper_slippage_pct": 0.0,
        "log_level": "WARNING",
        "log_format": "console",
        "dhan_client_id": "",
        "dhan_access_token": "",
        "zerodha_api_key": "",
        "zerodha_access_token": "",
    }
    return Settings(_env_file=None, **(values | overrides))  # type: ignore[arg-type]


@pytest.fixture
def market_data() -> FakeMarketData:
    return FakeMarketData()


async def build_container(
    settings: Settings, market_data: MarketDataProvider, transport: httpx.AsyncBaseTransport | None = None
) -> AppContainer:
    container = AppContainer.build(
        settings,
        db=Database(settings.database_url),
        market_data=market_data,
        broker_transport=transport,
        use_redis=False,
    )
    await container.db.create_all()
    await TradingEngine(container).bootstrap()
    return container


@pytest_asyncio.fixture
async def container(market_data: FakeMarketData) -> AsyncIterator[AppContainer]:
    container = await build_container(make_settings(), market_data)
    yield container
    await container.close()


@pytest_asyncio.fixture
async def services(container: AppContainer) -> AsyncIterator[Services]:
    async with container.db.session_factory() as session:
        yield Services(session, container)
        await session.commit()


@pytest_asyncio.fixture
async def client(container: AppContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(container.settings, container)
    app.state.container = container  # ASGITransport does not run lifespan; wire the container directly
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
        yield http
