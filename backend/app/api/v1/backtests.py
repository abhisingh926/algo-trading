from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, ServicesDep, user_id_of
from app.domain.enums import BacktestStatus
from app.schemas.backtest import (
    BacktestCreate,
    BacktestEquityPoint,
    BacktestRead,
    BacktestReport,
    BacktestTradeRead,
)
from app.schemas.common import ApiResponse, ok

router = APIRouter(prefix="/backtests", tags=["Backtesting"])


@router.post("", response_model=ApiResponse[BacktestRead], status_code=201)
async def run_backtest(body: BacktestCreate, services: ServicesDep, user: CurrentUser):
    backtest = await services.backtests.run(body, user_id_of(user))
    completed = backtest.status is BacktestStatus.COMPLETED
    return ok(
        BacktestRead.model_validate(backtest),
        "Backtest completed" if completed else "Backtest failed",
        201,
        "Backtest completed" if completed else (backtest.error_message or "Backtest failed"),
    )


@router.get("", response_model=ApiResponse[list[BacktestRead]])
async def list_backtests(services: ServicesDep, limit: int = Query(50, ge=1, le=200)):
    return ok(
        [BacktestRead.model_validate(b) for b in await services.backtests.list_recent(limit)], "Backtests"
    )


@router.get("/{backtest_id}", response_model=ApiResponse[BacktestRead])
async def get_backtest(backtest_id: str, services: ServicesDep):
    return ok(BacktestRead.model_validate(await services.backtests.get(backtest_id)), "Backtest")


@router.get("/{backtest_id}/trades", response_model=ApiResponse[list[BacktestTradeRead]])
async def backtest_trades(backtest_id: str, services: ServicesDep):
    return ok(
        [BacktestTradeRead.model_validate(t) for t in await services.backtests.trades(backtest_id)],
        "Backtest trades",
    )


@router.get("/{backtest_id}/equity-curve", response_model=ApiResponse[list[BacktestEquityPoint]])
async def backtest_equity_curve(backtest_id: str, services: ServicesDep):
    return ok(await services.backtests.equity_curve(backtest_id), "Equity curve")


@router.get("/{backtest_id}/report", response_model=ApiResponse[BacktestReport])
async def backtest_report(backtest_id: str, services: ServicesDep):
    return ok(
        BacktestReport.model_validate(await services.backtests.report(backtest_id), from_attributes=True),
        "Backtest report",
    )


@router.delete("/{backtest_id}", response_model=ApiResponse[None])
async def delete_backtest(backtest_id: str, services: ServicesDep):
    await services.backtests.delete(backtest_id)
    return ok(None, "Backtest deleted")
