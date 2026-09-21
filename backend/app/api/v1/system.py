from fastapi import APIRouter, Query

from app.core.dependencies import ServicesDep
from app.domain.enums import EventLevel
from app.schemas.common import ApiResponse, ok
from app.schemas.dashboard import SystemConfig, SystemEventRead, SystemStatus

router = APIRouter(tags=["System"])


@router.get("/system/status", response_model=ApiResponse[SystemStatus])
async def system_status(services: ServicesDep):
    return ok(await services.system.status(), "System status")


@router.get("/system/config", response_model=ApiResponse[SystemConfig])
async def system_config(services: ServicesDep):
    return ok(services.system.config(), "System configuration")


@router.get("/events", response_model=ApiResponse[list[SystemEventRead]])
async def list_events(
    services: ServicesDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: str | None = None,
    level: EventLevel | None = None,
    strategy_id: str | None = None,
):
    events = await services.events.list_events(
        event_type=event_type or None,
        level=level,
        strategy_id=strategy_id or None,
        limit=limit,
        offset=offset,
    )
    return ok([SystemEventRead.model_validate(e) for e in events], "Events")
