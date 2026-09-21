from fastapi import APIRouter, Depends

from app.api.v1 import (
    auth,
    backtests,
    brokers,
    dashboard,
    guide,
    market_data,
    orders,
    positions,
    risk,
    strategies,
    system,
    trades,
)
from app.core.dependencies import get_current_user

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)  # public endpoints; /auth/me authenticates itself

_protected = [Depends(get_current_user)]
for module in (
    system,
    dashboard,
    brokers,
    guide,
    strategies,
    orders,
    positions,
    trades,
    backtests,
    risk,
    market_data,
):
    api_router.include_router(module.router, dependencies=_protected)
