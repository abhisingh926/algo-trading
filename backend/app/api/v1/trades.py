from fastapi import APIRouter, Query

from app.core.dependencies import ServicesDep
from app.schemas.common import ApiResponse, ok
from app.schemas.trade import TradeRead

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("", response_model=ApiResponse[list[TradeRead]])
async def list_trades(
    services: ServicesDep,
    strategy_id: str | None = None,
    symbol: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    trades = await services.trades.list_trades(strategy_id or None, symbol or None, limit, offset)
    return ok([TradeRead.model_validate(t) for t in trades], "Trades")


@router.get("/{trade_id}", response_model=ApiResponse[TradeRead])
async def get_trade(trade_id: str, services: ServicesDep):
    return ok(TradeRead.model_validate(await services.trades.get(trade_id)), "Trade")
