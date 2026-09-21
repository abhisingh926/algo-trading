from fastapi import APIRouter, Query

from app.core.dependencies import ServicesDep
from app.schemas.common import ApiResponse, ok
from app.schemas.dashboard import DashboardSummary, Performance, PnlSeries

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=ApiResponse[DashboardSummary])
async def summary(services: ServicesDep):
    return ok(await services.pnl.summary(), "Dashboard summary")


@router.get("/pnl", response_model=ApiResponse[PnlSeries])
async def pnl(services: ServicesDep, days: int = Query(30, ge=1, le=365)):
    return ok(await services.pnl.series(days), "P&L series")


@router.get("/performance", response_model=ApiResponse[Performance])
async def performance(services: ServicesDep):
    return ok(await services.pnl.performance(), "Performance")
