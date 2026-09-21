"""Dhan order / portfolio endpoints."""

from __future__ import annotations

from typing import Any

from app.brokers.dhan import mapper
from app.brokers.dhan.client import DhanClient
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


class DhanOrdersApi:
    def __init__(self, client: DhanClient) -> None:
        self._client = client

    async def place(self, order: OrderRequest) -> BrokerOrder:
        payload = mapper.to_order_payload(order, self._client.client_id)
        try:
            raw = await self._client.request("POST", "/orders", json=payload)
        except BrokerError as exc:
            if type(exc) is BrokerError and (exc.data or {}).get("http_status") in (400, 422):
                # Dhan signals business rejections (margin, RMS, bad params) with 4xx.
                return BrokerOrder("", OrderStatus.REJECTED, order.quantity, message=exc.description)
            raise
        return mapper.to_broker_order(raw or {}, fallback_quantity=order.quantity)

    async def _raw(self, order_id: str) -> dict[str, Any]:
        raw = await self._client.request("GET", f"/orders/{order_id}")
        if isinstance(raw, list):
            raw = raw[0] if raw else {}
        if not raw:
            raise BrokerError(f"Dhan returned no order for id {order_id}")
        return raw

    async def get(self, order_id: str) -> BrokerOrder:
        return mapper.to_broker_order(await self._raw(order_id))

    async def list(self) -> list[BrokerOrder]:
        return [mapper.to_broker_order(o) for o in (await self._client.request("GET", "/orders")) or []]

    async def modify(self, order_id: str, data: OrderModification) -> BrokerOrder:
        current = await self._raw(order_id)
        payload = mapper.to_modify_payload(order_id, self._client.client_id, current, data)
        await self._client.request("PUT", f"/orders/{order_id}", json=payload)
        return await self.get(order_id)

    async def cancel(self, order_id: str) -> BrokerOrder:
        raw = await self._client.request("DELETE", f"/orders/{order_id}")
        result = mapper.to_broker_order(raw or {"orderId": order_id, "orderStatus": "CANCELLED"})
        if not result.broker_order_id:
            result.broker_order_id = order_id
        return result

    async def positions(self) -> list[BrokerPosition]:
        raw = await self._client.request("GET", "/positions")
        return [p for p in (mapper.to_position(r) for r in raw or []) if p is not None]

    async def holdings(self) -> list[BrokerHolding]:
        try:
            raw = await self._client.request("GET", "/holdings")
        except BrokerError as exc:
            if type(exc) is BrokerError:  # Dhan answers "no holdings" with an error payload
                return []
            raise
        return [mapper.to_holding(r) for r in raw or []]

    async def funds(self) -> BrokerFunds:
        return mapper.to_funds(await self._client.request("GET", "/fundlimit") or {})
