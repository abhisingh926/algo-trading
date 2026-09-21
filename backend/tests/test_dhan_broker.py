"""Dhan / Zerodha adapters against httpx.MockTransport - no network, no real broker."""

import json
import logging
from datetime import UTC, datetime

import httpx
import pytest

from app.brokers.dhan.broker import DhanBroker
from app.brokers.dhan.client import DhanClient
from app.brokers.dhan.market_data import DhanMarketData
from app.brokers.zerodha import mapper as kite_mapper
from app.brokers.zerodha.broker import ZerodhaBroker
from app.brokers.zerodha.client import ZerodhaClient
from app.core.exceptions import BrokerConnectionError, BrokerError
from app.core.logging import JsonFormatter, redact
from app.domain.enums import (
    BrokerEnvironment,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    ProductType,
    Timeframe,
)
from app.domain.types import InstrumentRef, OrderModification, OrderRequest

REL = InstrumentRef("RELIANCE", "NSE", "2885")
TOKEN = "super-secret-access-token"


def order(order_type=OrderType.MARKET, price=None, trigger=None) -> OrderRequest:
    return OrderRequest(
        "7b1f6c1e-aaaa-bbbb-cccc-1234567890ab",
        REL,
        OrderSide.BUY,
        order_type,
        ProductType.INTRADAY,
        10,
        price,
        trigger,
    )


def dhan(handler, environment=BrokerEnvironment.SANDBOX, live_guard=lambda: False) -> DhanBroker:
    client = DhanClient(
        "https://sandbox.dhan.co/v2", "1000000001", TOKEN, transport=httpx.MockTransport(handler)
    )
    return DhanBroker(client, environment, live_guard)


async def test_place_order_maps_payload_and_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["headers"], seen["body"] = (
            str(request.url),
            request.headers,
            json.loads(request.content),
        )
        return httpx.Response(200, json={"orderId": "112111182198", "orderStatus": "PENDING"})

    result = await dhan(handler).place_order(order(OrderType.SL, price=1001, trigger=1000))
    assert (result.broker_order_id, result.status, result.quantity) == ("112111182198", OrderStatus.OPEN, 10)
    assert seen["url"] == "https://sandbox.dhan.co/v2/orders"
    assert seen["headers"]["access-token"] == TOKEN and seen["headers"]["client-id"] == "1000000001"
    body = seen["body"]
    assert (body["orderType"], body["productType"], body["exchangeSegment"], body["securityId"]) == (
        "STOP_LOSS",
        "INTRADAY",
        "NSE_EQ",
        "2885",
    )
    assert (body["transactionType"], body["quantity"], body["price"], body["triggerPrice"]) == (
        "BUY",
        10,
        1001,
        1000,
    )
    assert body["correlationId"] == "7b1f6c1eaaaabbbbcccc12345" and body["dhanClientId"] == "1000000001"


@pytest.mark.parametrize(
    "dhan_status, expected",
    [
        ("TRANSIT", OrderStatus.SUBMITTED),
        ("PENDING", OrderStatus.OPEN),
        ("PART_TRADED", OrderStatus.PARTIALLY_FILLED),
        ("TRADED", OrderStatus.FILLED),
        ("REJECTED", OrderStatus.REJECTED),
        ("CANCELLED", OrderStatus.CANCELLED),
        ("EXPIRED", OrderStatus.EXPIRED),
    ],
)
async def test_order_status_mapping(dhan_status, expected):
    payload = {
        "orderId": "1",
        "orderStatus": dhan_status,
        "quantity": 10,
        "filledQty": 4,
        "averageTradedPrice": 1002.5,
        "omsErrorDescription": "",
    }
    result = await dhan(lambda r: httpx.Response(200, json=payload)).get_order_status("1")
    assert (result.status, result.filled_quantity, result.average_fill_price) == (expected, 4, 1002.5)


async def test_business_rejection_is_returned_not_raised():
    def handler(_request: httpx.Request) -> httpx.Response:
        body = {"errorType": "Order_Error", "errorCode": "DH-906", "errorMessage": "Insufficient funds"}
        return httpx.Response(400, json=body)

    result = await dhan(handler).place_order(order())
    assert result.status is OrderStatus.REJECTED and "Insufficient funds" in result.message


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_retryable_http_statuses_raise_connection_error(status):
    with pytest.raises(BrokerConnectionError):
        await dhan(lambda r: httpx.Response(status, json={})).place_order(order())


async def test_transport_failure_raises_connection_error_without_leaking_token():
    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(BrokerConnectionError) as exc:
        await dhan(handler).get_funds()
    assert TOKEN not in str(exc.value) and TOKEN not in exc.value.description


async def test_auth_failure_is_a_broker_error():
    with pytest.raises(BrokerError, match="Invalid token"):
        await dhan(lambda r: httpx.Response(401, json={"errorMessage": "Invalid token"})).get_funds()


async def test_modify_cancel_positions_holdings_funds_profile():
    def handler(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path.removeprefix("/v2"), request.method
        if path == "/orders/55" and method == "GET":
            return httpx.Response(
                200,
                json={
                    "orderId": "55",
                    "orderStatus": "PENDING",
                    "quantity": 20,
                    "orderType": "LIMIT",
                    "price": 990,
                    "validity": "DAY",
                },
            )
        if path == "/orders/55" and method == "PUT":
            assert json.loads(request.content)["quantity"] == 20
            return httpx.Response(200, json={"orderId": "55", "orderStatus": "TRANSIT"})
        if path == "/orders/55" and method == "DELETE":
            return httpx.Response(200, json={"orderId": "55", "orderStatus": "CANCELLED"})
        if path == "/positions":
            return httpx.Response(
                200,
                json=[
                    {
                        "tradingSymbol": "RELIANCE",
                        "exchangeSegment": "NSE_EQ",
                        "netQty": -5,
                        "sellAvg": 1010,
                        "buyAvg": 0,
                        "unrealizedProfit": 25,
                    },
                    {"tradingSymbol": "TCS", "exchangeSegment": "NSE_EQ", "netQty": 0},
                ],
            )
        if path == "/holdings":
            return httpx.Response(
                200, json=[{"tradingSymbol": "INFY", "exchange": "NSE", "totalQty": 3, "avgCostPrice": 1400}]
            )
        if path == "/fundlimit":
            return httpx.Response(200, json={"availabelBalance": 98440.0, "utilizedAmount": 1560.0})
        if path == "/profile":
            return httpx.Response(200, json={"dhanClientId": "1000000001"})
        return httpx.Response(404, json={"errorMessage": f"unexpected {method} {path}"})

    broker = dhan(handler)
    assert (await broker.modify_order("55", OrderModification(quantity=20))).quantity == 20
    assert (await broker.cancel_order("55")).status is OrderStatus.CANCELLED
    (position,) = await broker.get_positions()
    assert (position.side, position.quantity, position.average_price) == (PositionSide.SHORT, 5, 1010)
    assert (await broker.get_holdings())[0].quantity == 3
    funds = await broker.get_funds()
    assert (funds.available, funds.used_margin, funds.total) == (98440, 1560, 100000)
    profile = await broker.get_profile()
    assert profile.client_id_masked == "******0001"


async def test_market_data_quotes_and_candles():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.path.endswith("/marketfeed/quote"):
            assert body == {"NSE_EQ": [2885]}
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "NSE_EQ": {
                            "2885": {
                                "last_price": 1421.5,
                                "volume": 12345,
                                "ohlc": {"open": 1410, "high": 1425, "low": 1405, "close": 1408},
                            }
                        }
                    },
                },
            )
        assert (
            request.url.path.endswith("/charts/intraday")
            and body["interval"] == "5"
            and body["securityId"] == "2885"
        )
        return httpx.Response(
            200,
            json={
                "open": [100, 101],
                "high": [102, 103],
                "low": [99, 100],
                "close": [101, 102],
                "volume": [500, 600],
                "timestamp": [1767585600, 1767585900],
            },
        )

    provider = DhanMarketData(
        DhanClient("https://api.dhan.co/v2", "1", TOKEN, transport=httpx.MockTransport(handler))
    )
    (quote,) = await provider.get_quote([REL])
    assert (quote.ltp, quote.open, quote.high, quote.volume, quote.source) == (
        1421.5,
        1410,
        1425,
        12345,
        "dhan",
    )
    candles = await provider.get_historical_data(
        REL, Timeframe.M5, datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 1, 6, tzinfo=UTC)
    )
    assert [c.close for c in candles] == [101, 102] and candles[0].timestamp == datetime(
        2026, 1, 5, 4, 0, tzinfo=UTC
    )


async def test_missing_security_id_is_a_clear_error():
    bad = OrderRequest(
        "cid", InstrumentRef("NEWCO", "NSE", None), OrderSide.BUY, OrderType.MARKET, ProductType.INTRADAY, 1
    )
    with pytest.raises(BrokerError, match="exchange token"):
        await dhan(lambda r: httpx.Response(200, json={})).place_order(bad)


async def test_zerodha_adapter_with_mock_api():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            seen["auth"], seen["form"] = request.headers["authorization"], dict(
                httpx.QueryParams(request.content.decode())
            )
            return httpx.Response(200, json={"status": "success", "data": {"order_id": "151220000000000"}})
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": [
                    {"order_id": "151220000000000", "status": "OPEN", "quantity": 10, "filled_quantity": 0},
                    {
                        "order_id": "151220000000000",
                        "status": "COMPLETE",
                        "quantity": 10,
                        "filled_quantity": 10,
                        "average_price": 1420.5,
                    },
                ],
            },
        )

    client = ZerodhaClient("https://api.kite.trade", "key", "tok", transport=httpx.MockTransport(handler))
    broker = ZerodhaBroker(client, live_guard=lambda: True)
    placed = await broker.place_order(order(OrderType.LIMIT, price=1420))
    assert placed.broker_order_id == "151220000000000" and seen["auth"] == "token key:tok"
    assert (seen["form"]["order_type"], seen["form"]["product"], seen["form"]["tradingsymbol"]) == (
        "LIMIT",
        "MIS",
        "RELIANCE",
    )
    status = await broker.get_order_status("151220000000000")
    assert (status.status, status.average_fill_price) == (OrderStatus.FILLED, 1420.5)
    assert kite_mapper.instrument_token(REL) == 738561  # 2885 * 256 + 1


def test_logs_never_contain_secrets():
    assert redact({"access_token": TOKEN, "nested": {"api_key": "k", "password": "p"}, "symbol": "INFY"}) == {
        "access_token": "***REDACTED***",
        "nested": {"api_key": "***REDACTED***", "password": "***REDACTED***"},
        "symbol": "INFY",
    }
    record = logging.LogRecord("t", logging.INFO, "f", 1, "broker_connected", (), None)
    record.access_token, record.client_secret, record.symbol = TOKEN, "s3cr3t", "INFY"
    line = JsonFormatter().format(record)
    assert TOKEN not in line and "s3cr3t" not in line and '"symbol": "INFY"' in line
