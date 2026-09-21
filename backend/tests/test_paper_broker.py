import pytest

from app.brokers.paper.broker import PaperBroker
from app.core.exceptions import BrokerError
from app.domain.enums import OrderSide, OrderStatus, OrderType, PositionSide, ProductType
from app.domain.types import InstrumentRef, OrderModification, OrderRequest

REL = InstrumentRef("RELIANCE", "NSE", "2885")


def req(
    side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10, price=None, trigger=None, cid="o-1"
) -> OrderRequest:
    return OrderRequest(cid, REL, side, order_type, ProductType.INTRADAY, quantity, price, trigger)


@pytest.fixture
def broker(market_data) -> PaperBroker:
    return PaperBroker(market_data, initial_capital=100_000, slippage_pct=0.001)


async def test_market_order_fills_immediately_with_slippage(broker):
    buy = await broker.place_order(req())
    assert (buy.status, buy.filled_quantity, buy.average_fill_price) == (OrderStatus.FILLED, 10, 1001.0)
    sell = await broker.place_order(req(OrderSide.SELL, cid="o-2"))
    assert sell.average_fill_price == 999.0
    assert buy.broker_order_id.startswith("PAPER-")


async def test_limit_order_rests_until_marketable(broker, market_data):
    order = await broker.place_order(req(order_type=OrderType.LIMIT, price=990))
    assert order.status is OrderStatus.OPEN and order.filled_quantity == 0
    assert await broker.match_open_orders() == 0
    market_data.set_price("RELIANCE", 989)
    await broker.match_open_orders()
    filled = await broker.get_order_status(order.broker_order_id)
    assert (filled.status, filled.average_fill_price) == (
        OrderStatus.FILLED,
        989,
    )  # limit or better, no slippage


async def test_stop_loss_market_order_triggers(broker, market_data):
    order = await broker.place_order(req(OrderSide.SELL, OrderType.SL_M, trigger=980))
    assert order.status is OrderStatus.TRIGGER_PENDING
    market_data.set_price("RELIANCE", 985)
    await broker.match_open_orders()
    assert (await broker.get_order_status(order.broker_order_id)).status is OrderStatus.TRIGGER_PENDING
    market_data.set_price("RELIANCE", 979)
    await broker.match_open_orders()
    assert (await broker.get_order_status(order.broker_order_id)).status is OrderStatus.FILLED


async def test_stop_limit_order_becomes_limit_after_trigger(broker, market_data):
    order = await broker.place_order(req(OrderSide.BUY, OrderType.SL, price=1012, trigger=1010))
    market_data.set_price("RELIANCE", 1020)  # triggered, but above the limit -> rests as OPEN
    await broker.match_open_orders()
    assert (await broker.get_order_status(order.broker_order_id)).status is OrderStatus.OPEN
    market_data.set_price("RELIANCE", 1011)
    await broker.match_open_orders()
    assert (await broker.get_order_status(order.broker_order_id)).status is OrderStatus.FILLED


async def test_partial_fills(market_data):
    broker = PaperBroker(market_data, slippage_pct=0, max_fill_qty_per_tick=4)
    order = await broker.place_order(req(quantity=10))
    assert (order.status, order.filled_quantity) == (OrderStatus.PARTIALLY_FILLED, 4)
    market_data.set_price("RELIANCE", 1010)
    await broker.match_open_orders()
    second = await broker.get_order_status(order.broker_order_id)
    assert (second.filled_quantity, second.average_fill_price) == (8, 1005)
    await broker.match_open_orders()
    assert (await broker.get_order_status(order.broker_order_id)).status is OrderStatus.FILLED


@pytest.mark.parametrize(
    "request_, message",
    [
        (req(quantity=0), "Quantity"),
        (req(order_type=OrderType.LIMIT), "requires a price"),
        (req(order_type=OrderType.SL_M), "trigger price"),
    ],
)
async def test_invalid_orders_are_rejected(broker, request_, message):
    result = await broker.place_order(request_)
    assert result.status is OrderStatus.REJECTED and message in result.message


async def test_rejected_without_market_data(broker):
    unknown = OrderRequest(
        "o-9", InstrumentRef("UNKNOWN"), OrderSide.BUY, OrderType.MARKET, ProductType.INTRADAY, 1
    )
    assert (await broker.place_order(unknown)).status is OrderStatus.REJECTED


async def test_modify_and_cancel(broker):
    order = await broker.place_order(req(order_type=OrderType.LIMIT, price=900))
    modified = await broker.modify_order(order.broker_order_id, OrderModification(quantity=20, price=950))
    assert modified.quantity == 20
    cancelled = await broker.cancel_order(order.broker_order_id)
    assert cancelled.status is OrderStatus.CANCELLED
    with pytest.raises(BrokerError, match="already CANCELLED"):
        await broker.cancel_order(order.broker_order_id)
    with pytest.raises(BrokerError, match="Unknown"):
        await broker.get_order_status("PAPER-NOPE")


async def test_positions_and_funds(broker, market_data):
    await broker.place_order(req(quantity=10))  # buy @1001
    (position,) = await broker.get_positions()
    assert (position.side, position.quantity, position.average_price) == (PositionSide.LONG, 10, 1001)
    assert (await broker.get_funds()).used_margin == 10_010
    market_data.set_price("RELIANCE", 1100)
    await broker.place_order(req(OrderSide.SELL, quantity=10, cid="o-2"))  # sell @1098.9
    assert await broker.get_positions() == []
    assert (await broker.get_funds()).total == pytest.approx(100_000 + (1098.9 - 1001) * 10)
    assert len(await broker.get_orders()) == 2 and await broker.get_holdings() == []
