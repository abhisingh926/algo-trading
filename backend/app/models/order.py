from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import (
    BrokerType,
    ExitReason,
    OrderSide,
    OrderSource,
    OrderStatus,
    OrderType,
    ProductType,
    TradingMode,
)
from app.models.base import Money, TimestampMixin, UUIDMixin
from app.models.strategy import Strategy


def _values(enum_cls: Any) -> list[str]:
    return [m.value for m in enum_cls]


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_symbol_created", "symbol", "created_at"),
    )

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    broker_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="SET NULL")
    )
    strategy_id: Mapped[str | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), index=True
    )
    broker_type: Mapped[BrokerType] = mapped_column(Enum(BrokerType, native_enum=False, length=20))
    broker_order_id: Mapped[str | None] = mapped_column(String(64), index=True)

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide, native_enum=False, length=10))
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, native_enum=False, length=10, values_callable=_values)
    )
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType, native_enum=False, length=20))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price: Mapped[float | None] = mapped_column(Money)
    trigger_price: Mapped[float | None] = mapped_column(Money)
    average_fill_price: Mapped[float | None] = mapped_column(Money)
    # Protective levels to attach to the position this order opens.
    stop_loss: Mapped[float | None] = mapped_column(Money)
    target: Mapped[float | None] = mapped_column(Money)

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=20), default=OrderStatus.CREATED
    )
    status_message: Mapped[str | None] = mapped_column(Text)
    trading_mode: Mapped[TradingMode] = mapped_column(Enum(TradingMode, native_enum=False, length=20))
    source: Mapped[OrderSource] = mapped_column(
        Enum(OrderSource, native_enum=False, length=20), default=OrderSource.MANUAL
    )
    exit_reason: Mapped[ExitReason | None] = mapped_column(Enum(ExitReason, native_enum=False, length=20))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    strategy: Mapped[Strategy | None] = relationship(lazy="selectin")
    events: Mapped[list[OrderEvent]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderEvent.created_at", lazy="noload"
    )

    @property
    def pending_quantity(self) -> int:
        return max(self.quantity - self.filled_quantity, 0)

    @property
    def strategy_name(self) -> str | None:
        return self.strategy.name if self.strategy else None


class OrderEvent(UUIDMixin, TimestampMixin, Base):
    """Append-only audit trail of every state transition of an order."""

    __tablename__ = "order_events"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    order: Mapped[Order] = relationship(back_populates="events")
