"""Broker-neutral value objects passed between engine, brokers, strategies and market data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums import OrderSide, OrderStatus, OrderType, PositionSide, ProductType, SignalType


@dataclass(frozen=True, slots=True)
class InstrumentRef:
    symbol: str
    exchange: str = "NSE"
    exchange_token: str | None = None

    @property
    def key(self) -> str:
        return f"{self.exchange}:{self.symbol}"


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    exchange: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    source: str


@dataclass(frozen=True, slots=True)
class SignalResult:
    type: SignalType
    price: float
    reason: str = ""
    indicators: dict[str, float] = field(default_factory=dict)

    @classmethod
    def hold(cls, price: float, reason: str = "", **indicators: float) -> SignalResult:
        return cls(SignalType.HOLD, price, reason, indicators)


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """What the engine asks a broker to do. `correlation_id` is our own order id (idempotency key)."""

    correlation_id: str
    instrument: InstrumentRef
    side: OrderSide
    order_type: OrderType
    product_type: ProductType
    quantity: int
    price: float | None = None
    trigger_price: float | None = None


@dataclass(frozen=True, slots=True)
class OrderModification:
    quantity: int | None = None
    price: float | None = None
    trigger_price: float | None = None


@dataclass(slots=True)
class BrokerOrder:
    """A broker's view of an order, normalised by the adapter's mapper."""

    broker_order_id: str
    status: OrderStatus
    quantity: int
    filled_quantity: int = 0
    average_fill_price: float | None = None
    message: str | None = None
    correlation_id: str | None = None
    symbol: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class BrokerPosition:
    symbol: str
    exchange: str
    side: PositionSide
    quantity: int
    average_price: float
    last_price: float | None = None
    unrealized_pnl: float | None = None
    realized_pnl: float | None = None


@dataclass(frozen=True, slots=True)
class BrokerHolding:
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    last_price: float | None = None


@dataclass(frozen=True, slots=True)
class BrokerFunds:
    available: float
    used_margin: float
    total: float


@dataclass(frozen=True, slots=True)
class BrokerProfile:
    """Deliberately tiny: never carries tokens or secrets."""

    broker: str
    client_id_masked: str | None = None
    name: str | None = None
