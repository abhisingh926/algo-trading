"""The single pipeline every order goes through: validate -> persist -> RISK -> route -> submit."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.brokers.registry import BrokerRegistry
from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError, OrderRejectedError, ValidationFailedError
from app.domain.enums import (
    ORDER_STATUS_GROUPS,
    BrokerType,
    EventLevel,
    ExitReason,
    OrderSide,
    OrderSource,
    OrderStatus,
    OrderType,
    PositionSide,
    ProductType,
    TradingMode,
)
from app.domain.types import OrderModification
from app.models.order import Order, OrderEvent
from app.models.strategy import Strategy
from app.repositories.order_repository import OrderRepository
from app.repositories.position_repository import PositionRepository
from app.risk.limits import OrderIntent
from app.services.broker_service import BrokerService
from app.services.event_service import EventService
from app.services.market_data_service import MarketDataService
from app.services.risk_service import RiskService
from app.trading.order_manager import OrderManager


@dataclass(frozen=True, slots=True)
class PlaceOrderCommand:
    symbol: str
    side: OrderSide
    quantity: int
    exchange: str = "NSE"
    order_type: OrderType = OrderType.MARKET
    product_type: ProductType = ProductType.INTRADAY
    price: float | None = None
    trigger_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    trading_mode: TradingMode | None = None  # None -> global TRADING_MODE
    source: OrderSource = OrderSource.MANUAL
    strategy: Strategy | None = None
    broker_account_id: str | None = None
    exit_reason: ExitReason | None = None
    user_id: str | None = None


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        positions: PositionRepository,
        manager: OrderManager,
        risk: RiskService,
        market_data: MarketDataService,
        brokers: BrokerService,
        registry: BrokerRegistry,
        events: EventService,
        settings: Settings,
    ) -> None:
        self.orders = orders
        self.positions = positions
        self.manager = manager
        self.risk = risk
        self.market_data = market_data
        self.brokers = brokers
        self.registry = registry
        self.events = events
        self.settings = settings

    # ---- queries -------------------------------------------------------------------------------
    async def list_orders(
        self,
        status_group: str = "all",
        symbol: str | None = None,
        strategy_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Order]:
        if status_group != "all" and status_group not in ORDER_STATUS_GROUPS:
            raise ValidationFailedError(f"status_group must be one of: all, {', '.join(ORDER_STATUS_GROUPS)}")
        statuses = ORDER_STATUS_GROUPS.get(status_group)
        return await self.orders.list_orders(
            statuses=statuses, symbol=symbol, strategy_id=strategy_id, limit=limit, offset=offset
        )

    async def get_order(self, order_id: str, with_events: bool = False) -> Order:
        order = await (
            self.orders.get_with_events(order_id) if with_events else self.orders.get_by_id(order_id)
        )
        if order is None:
            raise NotFoundError("Order not found")
        return order

    # ---- placement -----------------------------------------------------------------------------
    async def place_order(self, cmd: PlaceOrderCommand) -> Order:
        mode = cmd.trading_mode or self.settings.trading_mode
        ref = await self.market_data.resolve(cmd.symbol, cmd.exchange)
        strategy_id = cmd.strategy.id if cmd.strategy else None
        account = await self.brokers.resolve_account(
            mode, cmd.broker_account_id or (cmd.strategy.broker_account_id if cmd.strategy else None)
        )

        order = await self.orders.create(
            Order(
                user_id=cmd.user_id,
                broker_account_id=account.id if account else None,
                strategy_id=strategy_id,
                strategy=cmd.strategy,
                broker_type=account.broker_type if account else BrokerType.PAPER,
                symbol=ref.symbol,
                exchange=ref.exchange,
                side=cmd.side,
                order_type=cmd.order_type,
                product_type=cmd.product_type,
                quantity=cmd.quantity,
                price=cmd.price,
                trigger_price=cmd.trigger_price,
                stop_loss=cmd.stop_loss,
                target=cmd.target,
                trading_mode=mode,
                source=cmd.source,
                exit_reason=cmd.exit_reason,
            )
        )
        await self.orders.add_event(
            OrderEvent(order_id=order.id, event_type="order_created", to_status=OrderStatus.CREATED.value)
        )

        try:
            reference_price = cmd.price or cmd.trigger_price or await self.market_data.get_ltp(ref)
            position = await self.positions.get_open(ref.symbol, ref.exchange, strategy_id, mode)
            reducing = (
                position is not None
                and position.side is (PositionSide.LONG if cmd.side is OrderSide.SELL else PositionSide.SHORT)
                and cmd.quantity <= position.quantity
            )
            intent = OrderIntent(
                ref.symbol, cmd.quantity, reference_price, cmd.stop_loss, is_reducing=reducing
            )
            decision = await self.risk.evaluate(intent, mode, cmd.strategy, order.id)
            if not decision.approved:
                raise OrderRejectedError(decision.reason)
            broker = self.registry.resolve_for_order(mode, self.brokers.ref(account) if account else None)
        except AppError as exc:
            await self._reject(order, exc.description)
            raise OrderRejectedError(exc.description, data={"order_id": order.id}) from exc

        await self.manager.submit(order, broker, self.manager.to_request(order, ref.exchange_token))
        if order.status in (OrderStatus.REJECTED, OrderStatus.FAILED):
            await self.orders.commit()
            raise OrderRejectedError(
                order.status_message or f"Order {order.status.value.lower()} by broker",
                data={"order_id": order.id},
            )
        return order

    async def _reject(self, order: Order, reason: str) -> None:
        """Persist the rejection even though the caller is about to see an error."""
        await self.manager.transition(order, OrderStatus.REJECTED, "order_rejected", reason)
        await self.events.record(
            "order_rejected",
            reason,
            level=EventLevel.WARNING,
            strategy_id=order.strategy_id,
            order_id=order.id,
            symbol=order.symbol,
        )
        await self.orders.commit()

    # ---- lifecycle -----------------------------------------------------------------------------
    def _broker_of(self, order: Order):  # noqa: ANN202
        return self.registry.resolve_for_existing_order(order.broker_type, order.trading_mode)

    async def cancel_order(self, order_id: str, reason: str = "Cancelled by user") -> Order:
        order = await self.get_order(order_id)
        return await self.manager.cancel(order, self._broker_of(order), reason)

    async def modify_order(self, order_id: str, data: OrderModification) -> Order:
        order = await self.get_order(order_id)
        if data.quantity is not None and data.quantity < max(order.filled_quantity, 1):
            raise ValidationFailedError("Quantity cannot be lower than the filled quantity")
        return await self.manager.modify(order, self._broker_of(order), data)

    async def sync_active_orders(self) -> int:
        """Poll brokers for every working order (called by the order monitor worker)."""
        synced = 0
        for order in await self.orders.list_active():
            try:
                await self.manager.sync(order, self._broker_of(order))
                synced += 1
            except AppError as exc:
                await self.events.record(
                    "order_sync_failed",
                    exc.description,
                    level=EventLevel.WARNING,
                    order_id=order.id,
                    symbol=order.symbol,
                )
        return synced

    async def cancel_all_active(self, reason: str) -> int:
        cancelled = 0
        for order in await self.orders.list_active():
            try:
                await self.manager.cancel(order, self._broker_of(order), reason)
                cancelled += 1
            except AppError as exc:
                await self.events.record(
                    "order_cancel_failed",
                    exc.description,
                    level=EventLevel.ERROR,
                    order_id=order.id,
                    symbol=order.symbol,
                )
        return cancelled
