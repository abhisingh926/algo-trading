"""Order lifecycle: submission with retries, status tracking, fills, modification, cancellation."""

from __future__ import annotations

import asyncio
from typing import Any

from app.brokers.base import BrokerInterface
from app.core.exceptions import BrokerConnectionError, BrokerError, ConflictError
from app.domain.enums import ACTIVE_ORDER_STATUSES, EventLevel, OrderStatus
from app.domain.types import BrokerOrder, InstrumentRef, OrderModification, OrderRequest
from app.models.order import Order, OrderEvent
from app.repositories.order_repository import OrderRepository
from app.services.event_service import EventService
from app.trading.charges import ChargesCalculator
from app.trading.position_manager import PositionManager

_STATUS_EVENTS = {
    OrderStatus.FILLED: "order_filled",
    OrderStatus.PARTIALLY_FILLED: "order_partially_filled",
    OrderStatus.REJECTED: "order_rejected",
    OrderStatus.CANCELLED: "order_cancelled",
    OrderStatus.FAILED: "order_failed",
    OrderStatus.EXPIRED: "order_expired",
}
_PROBLEM_STATUSES = {OrderStatus.REJECTED, OrderStatus.FAILED}


class OrderManager:
    def __init__(
        self,
        orders: OrderRepository,
        positions: PositionManager,
        events: EventService,
        charges: ChargesCalculator,
        *,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.5,
        fill_lock: asyncio.Lock | None = None,
    ) -> None:
        self.orders = orders
        self.positions = positions
        self.events = events
        self.charges = charges
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._fill_lock = fill_lock or asyncio.Lock()

    # ---- helpers -------------------------------------------------------------------------------
    @staticmethod
    def to_request(order: Order, exchange_token: str | None) -> OrderRequest:
        return OrderRequest(
            correlation_id=order.id,
            instrument=InstrumentRef(order.symbol, order.exchange, exchange_token),
            side=order.side,
            order_type=order.order_type,
            product_type=order.product_type,
            quantity=order.quantity,
            price=order.price,
            trigger_price=order.trigger_price,
        )

    async def transition(
        self,
        order: Order,
        status: OrderStatus,
        event_type: str,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        previous = order.status
        order.status = status
        if message is not None:
            order.status_message = message
        await self.orders.update(order)
        await self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                event_type=event_type,
                from_status=previous.value,
                to_status=status.value,
                message=message,
                payload=payload,
            )
        )

    # ---- submission ----------------------------------------------------------------------------
    async def submit(self, order: Order, broker: BrokerInterface, request: OrderRequest) -> Order:
        """Send to the broker. Transport errors are retried with backoff using the same correlation
        id; anything else fails the order. Never raises for broker problems - inspect order.status."""
        attempt = 0
        while True:
            try:
                result = await broker.place_order(request)
                break
            except BrokerConnectionError as exc:
                attempt += 1
                order.retry_count = attempt
                if attempt > self.max_retries:
                    await self._fail(
                        order, f"Broker unreachable after {self.max_retries} retries: {exc.description}"
                    )
                    return order
                await self.orders.add_event(
                    OrderEvent(
                        order_id=order.id,
                        event_type="order_retry",
                        message=f"Attempt {attempt} failed: {exc.description}",
                    )
                )
                await asyncio.sleep(self.retry_backoff_seconds * 2 ** (attempt - 1))
            except BrokerError as exc:
                await self._fail(order, exc.description)
                return order

        order.broker_order_id = result.broker_order_id or None
        await self.transition(
            order,
            OrderStatus.SUBMITTED,
            "order_submitted",
            payload={"broker_order_id": order.broker_order_id},
        )
        await self.events.record(
            "order_submitted",
            f"{order.side.value} {order.quantity} {order.symbol} {order.order_type.value} via {broker.broker_type.value}",
            strategy_id=order.strategy_id,
            order_id=order.id,
            symbol=order.symbol,
            broker=broker.broker_type.value,
            environment=broker.environment.value,
            trading_mode=order.trading_mode.value,
        )
        await self.apply_broker_state(order, result)
        return order

    async def _fail(self, order: Order, reason: str) -> None:
        await self.transition(order, OrderStatus.FAILED, "order_failed", reason)
        await self.events.record(
            "order_failed",
            reason,
            level=EventLevel.ERROR,
            strategy_id=order.strategy_id,
            order_id=order.id,
            symbol=order.symbol,
        )

    # ---- status tracking -----------------------------------------------------------------------
    async def apply_broker_state(self, order: Order, state: BrokerOrder) -> Order:
        """Reconcile our order with the broker's view: book new fills, then move status."""
        async with self._fill_lock:
            delta = min(state.filled_quantity, order.quantity) - order.filled_quantity
            if delta > 0 and state.average_fill_price:
                previous_value = (order.average_fill_price or 0.0) * order.filled_quantity
                fill_price = round(
                    (state.average_fill_price * (order.filled_quantity + delta) - previous_value) / delta, 4
                )
                order.filled_quantity += delta
                order.average_fill_price = state.average_fill_price
                fees = self.charges.compute(order.side, fill_price, delta)
                await self.positions.apply_fill(order, delta, fill_price, fees)

            if (
                state.quantity
                and state.quantity != order.quantity
                and state.quantity >= order.filled_quantity
            ):
                order.quantity = state.quantity
            new_status = state.status
            if order.filled_quantity >= order.quantity:
                new_status = OrderStatus.FILLED
            if new_status is not order.status and order.status in ACTIVE_ORDER_STATUSES | {
                OrderStatus.CREATED
            }:
                event = _STATUS_EVENTS.get(new_status, "order_status_changed")
                await self.transition(
                    order,
                    new_status,
                    event,
                    state.message,
                    {
                        "filled_quantity": order.filled_quantity,
                        "average_fill_price": order.average_fill_price,
                    },
                )
                if new_status in _STATUS_EVENTS:
                    await self.events.record(
                        event,
                        f"{order.symbol} {order.side.value} {order.filled_quantity}/{order.quantity}"
                        + (f" - {state.message}" if state.message else ""),
                        level=EventLevel.WARNING if new_status in _PROBLEM_STATUSES else EventLevel.INFO,
                        strategy_id=order.strategy_id,
                        order_id=order.id,
                        symbol=order.symbol,
                        filled_quantity=order.filled_quantity,
                        average_fill_price=order.average_fill_price,
                    )
            else:
                await self.orders.update(order)
        return order

    async def sync(self, order: Order, broker: BrokerInterface) -> Order:
        if order.status not in ACTIVE_ORDER_STATUSES or not order.broker_order_id:
            return order
        return await self.apply_broker_state(order, await broker.get_order_status(order.broker_order_id))

    # ---- modification / cancellation -----------------------------------------------------------
    async def modify(self, order: Order, broker: BrokerInterface, data: OrderModification) -> Order:
        self._ensure_active(order)
        state = await broker.modify_order(order.broker_order_id or "", data)
        for field in ("quantity", "price", "trigger_price"):
            value = getattr(data, field)
            if value is not None:
                setattr(order, field, value)
        await self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                event_type="order_modified",
                message="Order modified",
                payload={
                    k: v
                    for k, v in (
                        ("quantity", data.quantity),
                        ("price", data.price),
                        ("trigger_price", data.trigger_price),
                    )
                    if v is not None
                },
            )
        )
        return await self.apply_broker_state(order, state)

    async def cancel(self, order: Order, broker: BrokerInterface, reason: str = "Cancelled by user") -> Order:
        self._ensure_active(order)
        if not order.broker_order_id:  # never reached the broker
            await self.transition(order, OrderStatus.CANCELLED, "order_cancelled", reason)
            return order
        state = await broker.cancel_order(order.broker_order_id)
        state.message = state.message or reason
        return await self.apply_broker_state(order, state)

    @staticmethod
    def _ensure_active(order: Order) -> None:
        if order.status not in ACTIVE_ORDER_STATUSES:
            raise ConflictError(
                f"Order is already {order.status.value}", message="Order can no longer be changed"
            )
