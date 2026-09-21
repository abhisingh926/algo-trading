"""ZerodhaBroker: Kite Connect has no sandbox, so this adapter only exists in the LIVE environment
and every order method is behind the live guard."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence

from app.brokers.base import BrokerInterface
from app.brokers.zerodha.client import ZerodhaClient
from app.brokers.zerodha.market_data import ZerodhaMarketData
from app.brokers.zerodha.orders import ZerodhaOrdersApi
from app.core.exceptions import LiveTradingDisabledError
from app.domain.enums import BrokerEnvironment, BrokerType
from app.domain.types import (
    BrokerFunds,
    BrokerHolding,
    BrokerOrder,
    BrokerPosition,
    BrokerProfile,
    InstrumentRef,
    OrderModification,
    OrderRequest,
    Quote,
)


class ZerodhaBroker(BrokerInterface):
    broker_type = BrokerType.ZERODHA
    environment = BrokerEnvironment.LIVE

    def __init__(self, client: ZerodhaClient, live_guard: Callable[[], bool] = lambda: False) -> None:
        self._client = client
        self._orders = ZerodhaOrdersApi(client)
        self._market_data = ZerodhaMarketData(client)
        self._live_guard = live_guard

    def _assert_may_trade(self) -> None:
        if not self._live_guard():
            raise LiveTradingDisabledError(
                "Live trading is not enabled - refusing to send an order to Zerodha"
            )

    async def get_profile(self) -> BrokerProfile:
        raw = await self._client.request("GET", "/user/profile") or {}
        user_id = str(raw.get("user_id", ""))
        return BrokerProfile(
            "ZERODHA", f"{'*' * max(len(user_id) - 2, 0)}{user_id[-2:]}", raw.get("user_shortname")
        )

    async def get_funds(self) -> BrokerFunds:
        return await self._orders.funds()

    async def get_positions(self) -> list[BrokerPosition]:
        return await self._orders.positions()

    async def get_holdings(self) -> list[BrokerHolding]:
        return await self._orders.holdings()

    async def get_orders(self) -> list[BrokerOrder]:
        return await self._orders.list()

    async def place_order(self, order: OrderRequest) -> BrokerOrder:
        self._assert_may_trade()
        return await self._orders.place(order)

    async def modify_order(self, order_id: str, data: OrderModification) -> BrokerOrder:
        self._assert_may_trade()
        return await self._orders.modify(order_id, data)

    async def cancel_order(self, order_id: str) -> BrokerOrder:
        return await self._orders.cancel(order_id)

    async def get_order_status(self, order_id: str) -> BrokerOrder:
        return await self._orders.get(order_id)

    def subscribe_market_data(self, instruments: Sequence[InstrumentRef]) -> AsyncIterator[Quote]:
        return self._market_data.subscribe(instruments)

    async def close(self) -> None:
        await self._client.close()
