"""Order pipeline through real services + SQLite + PaperBroker (fake market data)."""

import pytest

from app.brokers.paper.broker import PaperBroker
from app.core.exceptions import BrokerConnectionError, ConflictError, OrderRejectedError
from app.domain.enums import (
    ExitReason,
    OrderSide,
    OrderSource,
    OrderStatus,
    OrderType,
    PositionStatus,
    TradingMode,
)
from app.domain.types import OrderModification
from app.services.order_service import PlaceOrderCommand


def buy(quantity=10, **kw) -> PlaceOrderCommand:
    return PlaceOrderCommand(symbol="RELIANCE", side=OrderSide.BUY, quantity=quantity, **kw)


def sell(quantity=10, **kw) -> PlaceOrderCommand:
    return PlaceOrderCommand(symbol="RELIANCE", side=OrderSide.SELL, quantity=quantity, **kw)


async def test_order_creation_fills_and_opens_position(services):
    order = await services.orders.place_order(buy(stop_loss=980, target=1040))
    assert (order.status, order.filled_quantity, order.average_fill_price) == (OrderStatus.FILLED, 10, 1000)
    assert (order.trading_mode, order.broker_type.value) == (TradingMode.PAPER, "PAPER")
    assert order.broker_order_id.startswith("PAPER-")

    (position,) = await services.positions.list_positions("open")
    assert (position.quantity, position.average_entry_price, position.stop_loss, position.target) == (
        10,
        1000,
        980,
        1040,
    )

    detail = await services.orders.get_order(order.id, with_events=True)
    assert [e.event_type for e in detail.events] == ["order_created", "order_submitted", "order_filled"]


async def test_round_trip_creates_trade_with_charges_and_daily_pnl(services, market_data):
    await services.orders.place_order(buy())
    market_data.set_price("RELIANCE", 1050)
    await services.orders.place_order(sell())

    (trade,) = await services.trades.list_trades()
    assert (trade.entry_price, trade.exit_price, trade.gross_pnl, trade.exit_reason) == (
        1000,
        1050,
        500,
        ExitReason.MANUAL,
    )
    assert trade.charges > 0 and trade.net_pnl == pytest.approx(500 - trade.charges)
    assert (await services.positions.list_positions("open")) == []
    (closed,) = await services.positions.list_positions("closed")
    assert closed.status is PositionStatus.CLOSED and closed.realized_pnl == pytest.approx(trade.net_pnl)

    summary = await services.pnl.summary()
    assert summary.realized_pnl_today == pytest.approx(trade.net_pnl, abs=0.01) and summary.trades_today == 1
    assert summary.win_rate == 100 and summary.capital == pytest.approx(500_000 + trade.net_pnl, abs=0.01)


async def test_risk_rejection_is_persisted_and_raised(services):
    await services.risk.update_config({"max_order_value": 5_000})
    with pytest.raises(OrderRejectedError, match="maximum order value") as exc:
        await services.orders.place_order(buy())
    rejected = await services.orders.get_order(exc.value.data["order_id"], with_events=True)
    assert (
        rejected.status is OrderStatus.REJECTED and rejected.broker_order_id is None
    )  # never reached a broker
    assert "maximum order value" in rejected.status_message
    events = await services.events.list_events(event_type="risk_check_failed")
    assert len(events) == 1


async def test_max_open_positions_and_daily_trade_limits(services):
    await services.risk.update_config({"max_open_positions": 1})
    await services.orders.place_order(buy())
    with pytest.raises(OrderRejectedError, match="Maximum open positions"):
        await services.orders.place_order(PlaceOrderCommand(symbol="INFY", side=OrderSide.BUY, quantity=1))
    await services.risk.update_config({"max_open_positions": 5, "max_trades_per_day": 1})
    with pytest.raises(OrderRejectedError, match="Maximum trades per day"):
        await services.orders.place_order(PlaceOrderCommand(symbol="INFY", side=OrderSide.BUY, quantity=1))


async def test_unknown_instrument(services):
    from app.core.exceptions import ValidationFailedError

    with pytest.raises(ValidationFailedError, match="Unknown instrument"):
        await services.orders.place_order(PlaceOrderCommand(symbol="NOPE", side=OrderSide.BUY, quantity=1))


async def test_partial_fill_then_complete(container, services, market_data):
    container.brokers.paper = PaperBroker(market_data, slippage_pct=0, max_fill_qty_per_tick=4)
    order = await services.orders.place_order(buy(quantity=10))
    assert (order.status, order.filled_quantity, order.pending_quantity) == (
        OrderStatus.PARTIALLY_FILLED,
        4,
        6,
    )
    assert (await services.positions.list_positions("open"))[0].quantity == 4

    market_data.set_price("RELIANCE", 1010)
    await container.brokers.paper.match_open_orders()
    await services.orders.sync_active_orders()
    assert (order.filled_quantity, order.average_fill_price) == (8, 1005)
    position = (await services.positions.list_positions("open"))[0]
    assert (position.quantity, position.average_entry_price) == (8, 1005)

    await container.brokers.paper.match_open_orders()
    await services.orders.sync_active_orders()
    assert order.status is OrderStatus.FILLED
    events = [e.event_type for e in (await services.orders.get_order(order.id, with_events=True)).events]
    assert events.count("order_partially_filled") == 1 and events[-1] == "order_filled"


async def test_cancellation(services):
    order = await services.orders.place_order(buy(order_type=OrderType.LIMIT, price=900))
    assert order.status is OrderStatus.OPEN
    cancelled = await services.orders.cancel_order(order.id)
    assert cancelled.status is OrderStatus.CANCELLED
    assert (await services.positions.list_positions("open")) == []
    with pytest.raises(ConflictError):
        await services.orders.cancel_order(order.id)
    assert [o.id for o in await services.orders.list_orders("cancelled")] == [order.id]
    assert await services.orders.list_orders("open") == []


async def test_modification(services, container, market_data):
    order = await services.orders.place_order(buy(order_type=OrderType.LIMIT, price=900))
    modified = await services.orders.modify_order(order.id, OrderModification(quantity=5, price=1000))
    assert (modified.quantity, modified.price) == (5, 1000)
    await container.brokers.paper.match_open_orders()
    await services.orders.sync_active_orders()
    assert (order.status, order.filled_quantity) == (OrderStatus.FILLED, 5)


async def test_transport_errors_are_retried_then_order_fails(container, services, monkeypatch):
    calls = {"n": 0}

    async def flaky(_request):
        calls["n"] += 1
        raise BrokerConnectionError("connection reset")

    monkeypatch.setattr(container.brokers.paper, "place_order", flaky)
    with pytest.raises(OrderRejectedError, match="unreachable after 3 retries") as exc:
        await services.orders.place_order(buy())
    failed = await services.orders.get_order(exc.value.data["order_id"])
    assert (failed.status, failed.retry_count, calls["n"]) == (OrderStatus.FAILED, 4, 4)
    assert (await services.positions.list_positions("open")) == []


async def test_retry_succeeds_after_transient_error(container, services, monkeypatch):
    real, calls = container.brokers.paper.place_order, {"n": 0}

    async def flaky(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise BrokerConnectionError("timeout")
        return await real(request)

    monkeypatch.setattr(container.brokers.paper, "place_order", flaky)
    order = await services.orders.place_order(buy())
    assert (order.status, order.retry_count) == (OrderStatus.FILLED, 1)


async def test_broker_rejection(services, market_data):
    del market_data.prices["TCS"]  # PaperBroker has no quote -> rejects, but risk needs a price first
    with pytest.raises(OrderRejectedError):
        await services.orders.place_order(PlaceOrderCommand(symbol="TCS", side=OrderSide.BUY, quantity=1))
    (rejected,) = await services.orders.list_orders("rejected")
    assert rejected.status is OrderStatus.REJECTED


async def test_protective_exit_on_stop_loss(services, market_data):
    await services.orders.place_order(buy(stop_loss=980, target=1040))
    market_data.set_price("RELIANCE", 975)
    await services.positions.mark_to_market()
    assert await services.trading.check_protective_exits() == 1
    (trade,) = await services.trades.list_trades()
    assert trade.exit_reason is ExitReason.STOP_LOSS and trade.net_pnl < 0
    (exit_order,) = [o for o in await services.orders.list_orders() if o.side is OrderSide.SELL]
    assert exit_order.source is OrderSource.RISK_EXIT
