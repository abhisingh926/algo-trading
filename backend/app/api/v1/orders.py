from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, ServicesDep, user_id_of
from app.domain.types import OrderModification
from app.schemas.common import ApiResponse, ok
from app.schemas.order import OrderCreate, OrderDetail, OrderModify, OrderRead
from app.services.order_service import PlaceOrderCommand

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=ApiResponse[list[OrderRead]])
async def list_orders(
    services: ServicesDep,
    status_group: str = "all",
    symbol: str | None = None,
    strategy_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    orders = await services.orders.list_orders(
        status_group, symbol or None, strategy_id or None, limit, offset
    )
    return ok([OrderRead.model_validate(o) for o in orders], "Orders")


@router.post("", response_model=ApiResponse[OrderRead], status_code=201)
async def place_order(body: OrderCreate, services: ServicesDep, user: CurrentUser):
    """Routed by TRADING_MODE. In PAPER mode this can only ever reach PaperBroker."""
    order = await services.orders.place_order(
        PlaceOrderCommand(**body.model_dump(), user_id=user_id_of(user))
    )
    return ok(
        OrderRead.model_validate(order),
        "Order placed successfully",
        201,
        f"{order.trading_mode.value} order {order.status.value} via {order.broker_type.value}",
    )


@router.get("/{order_id}", response_model=ApiResponse[OrderDetail])
async def get_order(order_id: str, services: ServicesDep):
    return ok(
        OrderDetail.model_validate(await services.orders.get_order(order_id, with_events=True)), "Order"
    )


@router.put("/{order_id}", response_model=ApiResponse[OrderRead])
async def modify_order(order_id: str, body: OrderModify, services: ServicesDep):
    order = await services.orders.modify_order(order_id, OrderModification(**body.model_dump()))
    return ok(OrderRead.model_validate(order), "Order modified")


@router.post("/{order_id}/cancel", response_model=ApiResponse[OrderRead])
async def cancel_order(order_id: str, services: ServicesDep):
    return ok(OrderRead.model_validate(await services.orders.cancel_order(order_id)), "Order cancelled")
