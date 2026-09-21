from __future__ import annotations

from app.brokers.zerodha import mapper
from app.brokers.zerodha.client import ZerodhaClient
from app.core.exceptions import BrokerError
from app.domain.enums import OrderStatus
from app.domain.types import (
    BrokerFunds,
    BrokerHolding,
    BrokerOrder,
    BrokerPosition,
    OrderModification,
    OrderRequest,
)


class ZerodhaOrdersApi:
    def __init__(self, client: ZerodhaClient) -> None:
        self._client = client

    async def place(self, order: OrderRequest) -> BrokerOrder:
        try:
            raw = await self._client.request("POST", "/orders/regular", data=mapper.to_order_form(order))
        except BrokerError as exc:
            if type(exc) is BrokerError and (exc.data or {}).get("http_status") == 400:
                return BrokerOrder("", OrderStatus.REJECTED, order.quantity, message=exc.description)
            raise
        return BrokerOrder(str((raw or {}).get("order_id", "")), OrderStatus.SUBMITTED, order.quantity)

    async def get(self, order_id: str) -> BrokerOrder:
        history = await self._client.request("GET", f"/orders/{order_id}") or []
        if not history:
            raise BrokerError(f"Zerodha returned no order for id {order_id}")
        return mapper.to_broker_order(history[-1])

    async def list(self) -> list[BrokerOrder]:
        return [mapper.to_broker_order(o) for o in await self._client.request("GET", "/orders") or []]

    async def modify(self, order_id: str, data: OrderModification) -> BrokerOrder:
        form = {
            k: v
            for k, v in (
                ("quantity", data.quantity),
                ("price", data.price),
                ("trigger_price", data.trigger_price),
            )
            if v is not None
        }
        await self._client.request("PUT", f"/orders/regular/{order_id}", data=form)
        return await self.get(order_id)

    async def cancel(self, order_id: str) -> BrokerOrder:
        await self._client.request("DELETE", f"/orders/regular/{order_id}")
        return await self.get(order_id)

    async def positions(self) -> list[BrokerPosition]:
        raw = await self._client.request("GET", "/portfolio/positions") or {}
        return [p for p in (mapper.to_position(r) for r in raw.get("net") or []) if p is not None]

    async def holdings(self) -> list[BrokerHolding]:
        return [mapper.to_holding(r) for r in await self._client.request("GET", "/portfolio/holdings") or []]

    async def funds(self) -> BrokerFunds:
        return mapper.to_funds(await self._client.request("GET", "/user/margins") or {})
