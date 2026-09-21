from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta

from app.core.cache import QuoteCache
from app.core.exceptions import ConflictError, MarketDataError, ValidationFailedError
from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef, Quote
from app.market_data.base import MarketDataProvider
from app.models.instrument import Instrument
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.utils.time import ist_day_end_utc, ist_day_start_utc, utcnow

_COVERAGE_TOLERANCE = timedelta(days=4)  # weekends + exchange holidays

# NSE large caps with their exchange tokens (Dhan securityId == NSE token).
DEFAULT_INSTRUMENTS: tuple[tuple[str, str, str], ...] = (
    ("RELIANCE", "Reliance Industries", "2885"),
    ("TCS", "Tata Consultancy Services", "11536"),
    ("INFY", "Infosys", "1594"),
    ("HDFCBANK", "HDFC Bank", "1333"),
    ("ICICIBANK", "ICICI Bank", "4963"),
    ("SBIN", "State Bank of India", "3045"),
    ("ITC", "ITC", "1660"),
    ("LT", "Larsen & Toubro", "11483"),
    ("AXISBANK", "Axis Bank", "5900"),
    ("KOTAKBANK", "Kotak Mahindra Bank", "1922"),
    ("BHARTIARTL", "Bharti Airtel", "10604"),
    ("HINDUNILVR", "Hindustan Unilever", "1394"),
    ("MARUTI", "Maruti Suzuki", "10999"),
    ("WIPRO", "Wipro", "3787"),
)


class MarketDataService:
    def __init__(
        self,
        provider: MarketDataProvider,
        cache: QuoteCache,
        candles: MarketDataRepository,
        instruments: InstrumentRepository,
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.candles = candles
        self.instruments = instruments

    # ---- instruments ---------------------------------------------------------------------------
    async def seed_instruments(self) -> int:
        created = 0
        for symbol, name, token in DEFAULT_INSTRUMENTS:
            if await self.instruments.get_by_symbol(symbol, "NSE") is None:
                await self.instruments.create(
                    Instrument(symbol=symbol, exchange="NSE", name=name, exchange_token=token)
                )
                created += 1
        return created

    async def search_instruments(self, query: str, limit: int) -> Sequence[Instrument]:
        return await self.instruments.search(query, limit)

    async def create_instrument(self, **values: object) -> Instrument:
        if await self.instruments.get_by_symbol(str(values["symbol"]), str(values["exchange"])) is not None:
            raise ConflictError(f"Instrument {values['exchange']}:{values['symbol']} already exists")
        return await self.instruments.create(Instrument(**values))

    async def get_instrument(self, symbol: str, exchange: str = "NSE") -> Instrument:
        instrument = await self.instruments.get_by_symbol(symbol, exchange)
        if instrument is None or not instrument.is_active:
            raise ValidationFailedError(
                f"Unknown instrument {exchange}:{symbol}. Add it under market-data/instruments first."
            )
        return instrument

    async def resolve(self, symbol: str, exchange: str = "NSE") -> InstrumentRef:
        instrument = await self.get_instrument(symbol, exchange)
        return InstrumentRef(instrument.symbol, instrument.exchange, instrument.exchange_token)

    # ---- quotes --------------------------------------------------------------------------------
    async def refresh_quotes(self, refs: Sequence[InstrumentRef]) -> list[Quote]:
        quotes = await self.provider.get_quote(list(refs)) if refs else []
        for quote in quotes:
            await self.cache.set(quote)
        return quotes

    async def get_quotes(self, symbols: Sequence[str], exchange: str = "NSE") -> list[Quote]:
        return await self.refresh_quotes([await self.resolve(s, exchange) for s in symbols])

    async def get_ltp(self, ref: InstrumentRef, max_age_seconds: float = 5) -> float:
        cached = await self.cache.get(ref.symbol, ref.exchange, max_age_seconds)
        if cached is not None:
            return cached.ltp
        quotes = await self.refresh_quotes([ref])
        if not quotes or quotes[0].ltp <= 0:
            raise MarketDataError(f"No price available for {ref.key}")
        return quotes[0].ltp

    # ---- candles -------------------------------------------------------------------------------
    async def get_candles(
        self, ref: InstrumentRef, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        return await self.provider.get_historical_data(ref, timeframe, start, end)

    async def sync_historical(
        self, ref: InstrumentRef, timeframe: Timeframe, start_date: date, end_date: date
    ) -> tuple[int, int, str]:
        start, end = ist_day_start_utc(start_date), min(ist_day_end_utc(end_date), utcnow())
        fetched = await self.provider.get_historical_data(ref, timeframe, start, end)
        now = utcnow()
        closed = [
            c for c in fetched if c.timestamp + timedelta(minutes=timeframe.minutes) <= now
        ]  # never store a forming bar
        stored = await self.candles.save_candles(
            ref.symbol, ref.exchange, timeframe, closed, self.provider.name
        )
        return stored, len(closed), self.provider.name

    async def load_for_backtest(
        self, ref: InstrumentRef, timeframe: Timeframe, start_date: date, end_date: date
    ) -> tuple[list[Candle], str]:
        """Historical bars from MySQL, fetching + storing from the provider when coverage is missing."""
        start, end = ist_day_start_utc(start_date), min(ist_day_end_utc(end_date), utcnow())
        count, first, last, source = await self.candles.coverage(
            ref.symbol, ref.exchange, timeframe, start, end
        )
        complete = (
            count > 0
            and first is not None
            and last is not None
            and (first - start <= _COVERAGE_TOLERANCE and end - last <= _COVERAGE_TOLERANCE)
        )
        if not complete:
            await self.sync_historical(ref, timeframe, start_date, end_date)
            source = self.provider.name
        return (
            await self.candles.get_candles(ref.symbol, ref.exchange, timeframe, start, end),
            source or self.provider.name,
        )
