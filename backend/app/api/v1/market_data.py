from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from app.core.dependencies import ServicesDep
from app.domain.enums import Timeframe
from app.schemas.common import ApiResponse, ok
from app.schemas.instrument import (
    CandleRead,
    HistoricalSyncRequest,
    HistoricalSyncResult,
    InstrumentCreate,
    InstrumentRead,
    QuoteRead,
)
from app.utils.time import ensure_utc, utcnow

router = APIRouter(prefix="/market-data", tags=["Market Data"])


@router.get("/instruments", response_model=ApiResponse[list[InstrumentRead]])
async def search_instruments(services: ServicesDep, search: str = "", limit: int = Query(50, ge=1, le=500)):
    return ok(
        [
            InstrumentRead.model_validate(i)
            for i in await services.market_data.search_instruments(search, limit)
        ],
        "Instruments",
    )


@router.post("/instruments", response_model=ApiResponse[InstrumentRead], status_code=201)
async def create_instrument(body: InstrumentCreate, services: ServicesDep):
    instrument = await services.market_data.create_instrument(**body.model_dump())
    return ok(InstrumentRead.model_validate(instrument), "Instrument created", 201)


@router.get("/quotes", response_model=ApiResponse[list[QuoteRead]])
async def quotes(
    services: ServicesDep,
    symbols: str = Query(..., description="Comma separated, e.g. RELIANCE,INFY"),
    exchange: str = "NSE",
):
    names = [s.strip().upper() for s in symbols.split(",") if s.strip()][:50]
    return ok(
        [QuoteRead.model_validate(q) for q in await services.market_data.get_quotes(names, exchange.upper())],
        "Quotes",
    )


@router.get("/candles", response_model=ApiResponse[list[CandleRead]])
async def candles(
    services: ServicesDep,
    symbol: str,
    exchange: str = "NSE",
    timeframe: Timeframe = Timeframe.M5,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(500, ge=1, le=5000),
):
    end_at = ensure_utc(end) if end else utcnow()
    start_at = ensure_utc(start) if start else end_at - timedelta(minutes=timeframe.minutes * limit)
    ref = await services.market_data.resolve(symbol, exchange)
    bars = await services.market_data.get_candles(ref, timeframe, start_at, end_at)
    return ok([CandleRead.model_validate(c) for c in bars[-limit:]], "Candles")


@router.post("/historical/sync", response_model=ApiResponse[HistoricalSyncResult])
async def sync_historical(body: HistoricalSyncRequest, services: ServicesDep):
    ref = await services.market_data.resolve(body.symbol, body.exchange)
    stored, total, source = await services.market_data.sync_historical(
        ref, body.timeframe, body.start_date, body.end_date
    )
    return ok(HistoricalSyncResult(stored=stored, total=total, source=source), f"Stored {stored} new candles")
