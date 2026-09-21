"""PaperBroker: behaves like a real broker but fills orders against market data. Never touches a network broker."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, replace

from app.brokers.base import BrokerInterface
from app.core.exceptions import BrokerError, MarketDataError
from app.domain.enums import (
    ACTIVE_ORDER_STATUSES,
    BrokerEnvironment,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
)
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
from app.market_data.base import MarketDataProvider


@dataclass(slots=True)
class _PaperOrder:
    request: OrderRequest
    state: BrokerOrder
    triggered: bool = False


@dataclass(slots=True)
class _NetPosition:
    instrument: InstrumentRef
    quantity: int = 0  # signed
    average_price: float = 0.0
    realized_pnl: float = 0.0


class PaperBroker(BrokerInterface):
    broker_type = BrokerType.PAPER
    environment = BrokerEnvironment.PAPER

    def __init__(
        self,
        market_data: MarketDataProvider,
        *,
        initial_capital: float = 500_000,
        slippage_pct: float = 0.0005,
        max_fill_qty_per_tick: int = 0,
    ) -> None:
        self._market_data = market_data
        self._initial_capital = initial_capital
        self._slippage_pct = slippage_pct
        self._max_fill = max_fill_qty_per_tick
        self._orders: dict[str, _PaperOrder] = {}
        self._positions: dict[str, _NetPosition] = {}

    # ---- account -------------------------------------------------------------------------------
    async def get_profile(self) -> BrokerProfile:
        return BrokerProfile(broker="PAPER", client_id_masked="PAPER", name="Paper Trading Account")

    async def get_funds(self) -> BrokerFunds:
        used = sum(abs(p.quantity) * p.average_price for p in self._positions.values())
        total = self._initial_capital + sum(p.realized_pnl for p in self._positions.values())
        return BrokerFunds(
            available=round(total - used, 2), used_margin=round(used, 2), total=round(total, 2)
        )

    async def get_positions(self) -> list[BrokerPosition]:
        return [
            BrokerPosition(
                symbol=p.instrument.symbol,
                exchange=p.instrument.exchange,
                side=PositionSide.LONG if p.quantity > 0 else PositionSide.SHORT,
                quantity=abs(p.quantity),
                average_price=round(p.average_price, 4),
                realized_pnl=round(p.realized_pnl, 2),
            )
            for p in self._positions.values()
            if p.quantity != 0
        ]

    async def get_holdings(self) -> list[BrokerHolding]:
        return []

    async def get_orders(self) -> list[BrokerOrder]:
        return [replace(o.state) for o in self._orders.values()]

    # ---- orders --------------------------------------------------------------------------------
    @staticmethod
    def _validate(order: OrderRequest) -> str | None:
        if order.quantity <= 0:
            return "Quantity must be positive"
        if order.order_type in (OrderType.LIMIT, OrderType.SL) and not (order.price and order.price > 0):
            return f"{order.order_type.value} order requires a price"
        if order.order_type in (OrderType.SL, OrderType.SL_M) and not (
            order.trigger_price and order.trigger_price > 0
        ):
            return f"{order.order_type.value} order requires a trigger price"
        return None

    async def place_order(self, order: OrderRequest) -> BrokerOrder:
        broker_order_id = f"PAPER-{uuid.uuid4().hex[:12].upper()}"
        state = BrokerOrder(
            broker_order_id=broker_order_id,
            status=OrderStatus.OPEN,
            quantity=order.quantity,
            correlation_id=order.correlation_id,
            symbol=order.instrument.symbol,
        )
        record = _PaperOrder(order, state)
        self._orders[broker_order_id] = record

        error = self._validate(order)
        if error is None:
            try:
                quote = (await self._market_data.get_quote([order.instrument]))[0]
            except (MarketDataError, IndexError):
                error = f"No market data for {order.instrument.key}"
        if error is not None:
            state.status, state.message = OrderStatus.REJECTED, error
            return replace(state)

        if order.order_type in (OrderType.SL, OrderType.SL_M):
            state.status = OrderStatus.TRIGGER_PENDING
        self._match(record, quote.ltp)
        return replace(state)

    async def modify_order(self, order_id: str, data: OrderModification) -> BrokerOrder:
        record = self._active(order_id)
        quantity = data.quantity if data.quantity is not None else record.request.quantity
        if quantity < max(record.state.filled_quantity, 1):
            raise BrokerError("Quantity cannot be lower than the filled quantity")
        record.request = replace(
            record.request,
            quantity=quantity,
            price=data.price if data.price is not None else record.request.price,
            trigger_price=(
                data.trigger_price if data.trigger_price is not None else record.request.trigger_price
            ),
        )
        record.state.quantity = quantity
        if record.state.filled_quantity >= quantity:
            record.state.status = OrderStatus.FILLED
        return replace(record.state)

    async def cancel_order(self, order_id: str) -> BrokerOrder:
        record = self._active(order_id)
        record.state.status, record.state.message = OrderStatus.CANCELLED, "Cancelled by user"
        return replace(record.state)

    async def get_order_status(self, order_id: str) -> BrokerOrder:
        return replace(self._get(order_id).state)

    def restore_order(self, order: OrderRequest, state: BrokerOrder) -> None:
        """Re-register a working order after a process restart (paper state is in-memory)."""
        if state.broker_order_id not in self._orders:
            self._orders[state.broker_order_id] = _PaperOrder(order, replace(state))

    async def match_open_orders(self) -> int:
        """Try to fill every working order against the latest prices. Returns number of orders touched."""
        working = [o for o in self._orders.values() if o.state.status in ACTIVE_ORDER_STATUSES]
        if not working:
            return 0
        instruments = list({o.request.instrument.key: o.request.instrument for o in working}.values())
        prices = {f"{q.exchange}:{q.symbol}": q.ltp for q in await self._market_data.get_quote(instruments)}
        touched = 0
        for record in working:
            ltp = prices.get(record.request.instrument.key)
            if ltp is not None and self._match(record, ltp):
                touched += 1
        return touched

    # ---- matching engine -----------------------------------------------------------------------
    def _execution_price(self, record: _PaperOrder, ltp: float) -> float | None:
        req = record.request
        buy = req.side is OrderSide.BUY
        order_type = req.order_type
        if order_type in (OrderType.SL, OrderType.SL_M):
            if not record.triggered:
                assert req.trigger_price is not None
                if (buy and ltp >= req.trigger_price) or (not buy and ltp <= req.trigger_price):
                    record.triggered = True
                    record.state.status = OrderStatus.OPEN
                else:
                    return None
            order_type = OrderType.LIMIT if order_type is OrderType.SL else OrderType.MARKET
        if order_type is OrderType.MARKET:
            return round(ltp * (1 + self._slippage_pct * req.side.sign), 2)
        assert req.price is not None
        marketable = ltp <= req.price if buy else ltp >= req.price
        return ltp if marketable else None  # limit orders fill at the limit or better, no slippage

    def _match(self, record: _PaperOrder, ltp: float) -> bool:
        state = record.state
        price = self._execution_price(record, ltp)
        if price is None:
            return False
        remaining = state.quantity - state.filled_quantity
        fill_qty = min(remaining, self._max_fill) if self._max_fill > 0 else remaining
        if fill_qty <= 0:
            return False
        filled_value = (state.average_fill_price or 0.0) * state.filled_quantity + price * fill_qty
        state.filled_quantity += fill_qty
        state.average_fill_price = round(filled_value / state.filled_quantity, 4)
        state.status = (
            OrderStatus.FILLED if state.filled_quantity >= state.quantity else OrderStatus.PARTIALLY_FILLED
        )
        self._book_fill(record.request, fill_qty, price)
        return True

    def _book_fill(self, req: OrderRequest, quantity: int, price: float) -> None:
        pos = self._positions.setdefault(req.instrument.key, _NetPosition(req.instrument))
        signed = quantity * req.side.sign
        if pos.quantity == 0 or (pos.quantity > 0) == (signed > 0):
            total = abs(pos.quantity) + quantity
            pos.average_price = (pos.average_price * abs(pos.quantity) + price * quantity) / total
            pos.quantity += signed
            return
        closing = min(quantity, abs(pos.quantity))
        direction = 1 if pos.quantity > 0 else -1
        pos.realized_pnl += (price - pos.average_price) * closing * direction
        pos.quantity += signed
        if pos.quantity == 0:
            pos.average_price = 0.0
        elif (pos.quantity > 0) != (direction > 0):  # flipped through zero
            pos.average_price = price

    def _get(self, order_id: str) -> _PaperOrder:
        try:
            return self._orders[order_id]
        except KeyError as exc:
            raise BrokerError(f"Unknown paper order {order_id}") from exc

    def _active(self, order_id: str) -> _PaperOrder:
        record = self._get(order_id)
        if record.state.status not in ACTIVE_ORDER_STATUSES:
            raise BrokerError(f"Order is already {record.state.status.value}")
        return record

    def subscribe_market_data(self, instruments: Sequence[InstrumentRef]) -> AsyncIterator[Quote]:
        return self._market_data.subscribe(instruments)
