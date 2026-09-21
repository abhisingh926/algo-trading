"""DhanBroker: BrokerInterface over DhanHQ v2. Sandbox by default; LIVE only behind the live guard."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence

from app.brokers.base import BrokerInterface
from app.brokers.dhan.client import DhanClient
from app.brokers.dhan.market_data import DhanMarketData
from app.brokers.dhan.orders import DhanOrdersApi
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


def _mask(value: str) -> str:
    return f"{'*' * max(len(value) - 4, 0)}{value[-4:]}" if value else ""


class DhanBroker(BrokerInterface):
    broker_type = BrokerType.DHAN

    def __init__(
        self,
        client: DhanClient,
        environment: BrokerEnvironment,
        live_guard: Callable[[], bool] = lambda: False,
    ) -> None:
        if environment is BrokerEnvironment.PAPER:
            raise ValueError("DhanBroker cannot run in the PAPER environment - use PaperBroker")
        self.environment = environment
        self._client = client
        self._orders = DhanOrdersApi(client)
        self._market_data = DhanMarketData(client)
        self._live_guard = live_guard

    def _assert_may_trade(self) -> None:
        """Second line of defence (the BrokerRegistry is the first)."""
        if self.environment is BrokerEnvironment.LIVE and not self._live_guard():
            raise LiveTradingDisabledError("Live trading is not enabled - refusing to send an order to Dhan")

    async def get_profile(self) -> BrokerProfile:
        raw = await self._client.request("GET", "/profile") or {}
        return BrokerProfile(
            broker="DHAN", client_id_masked=_mask(str(raw.get("dhanClientId") or self._client.client_id))
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
        return await self._orders.cancel(order_id)  # cancelling is always allowed: it only reduces risk

    async def get_order_status(self, order_id: str) -> BrokerOrder:
        return await self._orders.get(order_id)

    def subscribe_market_data(self, instruments: Sequence[InstrumentRef]) -> AsyncIterator[Quote]:
        return self._market_data.subscribe(instruments)

    async def close(self) -> None:
        await self._client.close()
