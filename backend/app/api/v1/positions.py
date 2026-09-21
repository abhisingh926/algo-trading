from fastapi import APIRouter

from app.core.dependencies import CurrentUser, ServicesDep, user_id_of
from app.domain.enums import ExitReason, OrderSource
from app.schemas.common import ApiResponse, ok
from app.schemas.order import OrderRead
from app.schemas.position import PositionRead, PositionUpdate

router = APIRouter(prefix="/positions", tags=["Positions"])


@router.get("", response_model=ApiResponse[list[PositionRead]])
async def list_positions(services: ServicesDep, status: str = "open"):
    return ok(
        [PositionRead.model_validate(p) for p in await services.positions.list_positions(status)], "Positions"
    )


@router.get("/{symbol}", response_model=ApiResponse[list[PositionRead]])
async def positions_for_symbol(symbol: str, services: ServicesDep):
    return ok(
        [PositionRead.model_validate(p) for p in await services.positions.list_by_symbol(symbol)],
        f"Open positions for {symbol.upper()}",
    )


@router.put("/{position_id}", response_model=ApiResponse[PositionRead])
async def update_position(position_id: str, body: PositionUpdate, services: ServicesDep):
    position = await services.positions.update_levels(position_id, body.model_dump(exclude_unset=True))
    return ok(PositionRead.model_validate(position), "Position updated")


@router.post("/{position_id}/close", response_model=ApiResponse[OrderRead])
async def close_position(position_id: str, services: ServicesDep, user: CurrentUser):
    position = await services.positions.get(position_id)
    order = await services.positions.close_position(
        position, ExitReason.MANUAL, OrderSource.MANUAL, user_id_of(user)
    )
    return ok(OrderRead.model_validate(order), "Exit order placed")
