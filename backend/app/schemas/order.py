from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import (
    BrokerType,
    OrderSide,
    OrderSource,
    OrderStatus,
    OrderType,
    ProductType,
    TradingMode,
)
from app.schemas.common import ORMModel


class OrderCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    exchange: str = Field(default="NSE", max_length=10)
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    product_type: ProductType = ProductType.INTRADAY
    quantity: int = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    trigger_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    target: float | None = Field(default=None, gt=0)

    @field_validator("symbol", "exchange")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def _prices_match_type(self) -> OrderCreate:
        if self.order_type in (OrderType.LIMIT, OrderType.SL) and self.price is None:
            raise ValueError(f"price is required for {self.order_type.value} orders")
        if self.order_type in (OrderType.SL, OrderType.SL_M) and self.trigger_price is None:
            raise ValueError(f"trigger_price is required for {self.order_type.value} orders")
        return self


class OrderModify(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)
    trigger_price: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _not_empty(self) -> OrderModify:
        if self.quantity is None and self.price is None and self.trigger_price is None:
            raise ValueError("Provide at least one of quantity, price, trigger_price")
        return self


class OrderEventRead(ORMModel):
    id: str
    order_id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    message: str | None
    payload: dict[str, Any] | None
    created_at: datetime


class OrderRead(ORMModel):
    id: str
    broker_order_id: str | None
    broker_account_id: str | None
    broker_type: BrokerType
    strategy_id: str | None
    strategy_name: str | None
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    product_type: ProductType
    quantity: int
    filled_quantity: int
    pending_quantity: int
    price: float | None
    trigger_price: float | None
    average_fill_price: float | None
    stop_loss: float | None
    target: float | None
    status: OrderStatus
    status_message: str | None
    trading_mode: TradingMode
    source: OrderSource
    retry_count: int
    created_at: datetime
    updated_at: datetime


class OrderDetail(OrderRead):
    events: list[OrderEventRead] = Field(default_factory=list)
