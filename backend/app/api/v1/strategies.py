from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, ServicesDep, user_id_of
from app.schemas.common import ApiResponse, ok
from app.schemas.signal import SignalRead
from app.schemas.strategy import StrategyCreate, StrategyRead, StrategyTypeInfo, StrategyUpdate

router = APIRouter(tags=["Strategies"])


@router.get("/strategies/types", response_model=ApiResponse[list[StrategyTypeInfo]])
async def strategy_types(services: ServicesDep):
    return ok(services.strategies.types(), "Strategy types")


@router.get("/strategies", response_model=ApiResponse[list[StrategyRead]])
async def list_strategies(services: ServicesDep):
    return ok(await services.strategies.list_read(), "Strategies")


@router.post("/strategies", response_model=ApiResponse[StrategyRead], status_code=201)
async def create_strategy(body: StrategyCreate, services: ServicesDep, user: CurrentUser):
    strategy = await services.strategies.create(user_id_of(user), body.model_dump())
    return ok(
        await services.strategies.to_read(strategy), "Strategy created successfully", 201, "Strategy created"
    )


@router.get("/strategies/{strategy_id}", response_model=ApiResponse[StrategyRead])
async def get_strategy(strategy_id: str, services: ServicesDep):
    return ok(await services.strategies.to_read(await services.strategies.get(strategy_id)), "Strategy")


@router.put("/strategies/{strategy_id}", response_model=ApiResponse[StrategyRead])
async def update_strategy(strategy_id: str, body: StrategyUpdate, services: ServicesDep):
    strategy = await services.strategies.update(strategy_id, body.model_dump(exclude_unset=True))
    return ok(await services.strategies.to_read(strategy), "Strategy updated successfully")


@router.delete("/strategies/{strategy_id}", response_model=ApiResponse[None])
async def delete_strategy(strategy_id: str, services: ServicesDep):
    await services.strategies.delete(strategy_id)
    return ok(None, "Strategy deleted")


@router.post("/strategies/{strategy_id}/start", response_model=ApiResponse[StrategyRead])
async def start_strategy(strategy_id: str, services: ServicesDep):
    strategy = await services.strategies.start(strategy_id)
    return ok(
        await services.strategies.to_read(strategy),
        "Strategy started",
        description=f"Running in {strategy.trading_mode.value} mode",
    )


@router.post("/strategies/{strategy_id}/stop", response_model=ApiResponse[StrategyRead])
async def stop_strategy(strategy_id: str, services: ServicesDep):
    return ok(
        await services.strategies.to_read(await services.strategies.stop(strategy_id)), "Strategy stopped"
    )


@router.get("/strategies/{strategy_id}/signals", response_model=ApiResponse[list[SignalRead]])
async def strategy_signals(strategy_id: str, services: ServicesDep, limit: int = Query(50, ge=1, le=500)):
    await services.strategies.get(strategy_id)
    return ok(
        [SignalRead.model_validate(s) for s in await services.signals.list_recent(strategy_id, limit)],
        "Signals",
    )


@router.get("/signals", response_model=ApiResponse[list[SignalRead]])
async def list_signals(services: ServicesDep, limit: int = Query(50, ge=1, le=500)):
    return ok(
        [SignalRead.model_validate(s) for s in await services.signals.list_recent(None, limit)], "Signals"
    )
