"""Broker abstraction. The trading engine depends on this interface only - never on a concrete broker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

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


class BrokerInterface(ABC):
    broker_type: BrokerType
    environment: BrokerEnvironment

    @property
    def is_real_money(self) -> bool:
        return self.environment is BrokerEnvironment.LIVE

    @abstractmethod
    async def get_profile(self) -> BrokerProfile: ...

    @abstractmethod
    async def get_funds(self) -> BrokerFunds: ...

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]: ...

    @abstractmethod
    async def get_holdings(self) -> list[BrokerHolding]: ...

    @abstractmethod
    async def get_orders(self) -> list[BrokerOrder]: ...

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> BrokerOrder:
        """Business rejections are returned as a BrokerOrder with status REJECTED.
        Transport problems raise BrokerConnectionError (retryable); anything else raises BrokerError."""

    @abstractmethod
    async def modify_order(self, order_id: str, data: OrderModification) -> BrokerOrder: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> BrokerOrder: ...

    @abstractmethod
    async def get_order_status(self, order_id: str) -> BrokerOrder: ...

    @abstractmethod
    def subscribe_market_data(self, instruments: Sequence[InstrumentRef]) -> AsyncIterator[Quote]: ...

    async def close(self) -> None:  # noqa: B027
        pass
