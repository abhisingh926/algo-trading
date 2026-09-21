"""All Kite-specific vocabulary lives here."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import BrokerError
from app.domain.enums import OrderStatus, OrderType, PositionSide, ProductType, Timeframe
from app.domain.types import (
    BrokerFunds,
    BrokerHolding,
    BrokerOrder,
    BrokerPosition,
    Candle,
    InstrumentRef,
    OrderRequest,
    Quote,
)

ORDER_TYPE_TO_KITE = {
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
    OrderType.SL: "SL",
    OrderType.SL_M: "SL-M",
}
PRODUCT_TO_KITE = {ProductType.INTRADAY: "MIS", ProductType.DELIVERY: "CNC"}
INTERVAL_TO_KITE = {
    Timeframe.M1: "minute",
    Timeframe.M5: "5minute",
    Timeframe.M15: "15minute",
    Timeframe.H1: "60minute",
    Timeframe.D1: "day",
}
_EXCHANGE_SEGMENT_CODE = {"NSE": 1, "BSE": 3}


def status_from_kite(raw: str) -> OrderStatus:
    status = raw.upper()
    if status == "COMPLETE":
        return OrderStatus.FILLED
    if status in ("CANCELLED", "REJECTED"):
        return OrderStatus(status)
    if status == "TRIGGER PENDING":
        return OrderStatus.TRIGGER_PENDING
    if status == "OPEN":
        return OrderStatus.OPEN
    return OrderStatus.SUBMITTED  # the various "... PENDING" / "REQ RECEIVED" transit states


def instrument_token(ref: InstrumentRef) -> int:
    if not ref.exchange_token:
        raise BrokerError(f"Instrument {ref.key} has no exchange token")
    try:
        return int(ref.exchange_token) * 256 + _EXCHANGE_SEGMENT_CODE[ref.exchange.upper()]
    except KeyError as exc:
        raise BrokerError(f"Exchange {ref.exchange} is not supported by the Zerodha adapter") from exc


def to_order_form(order: OrderRequest) -> dict[str, Any]:
    form: dict[str, Any] = {
        "tradingsymbol": order.instrument.symbol,
        "exchange": order.instrument.exchange,
        "transaction_type": order.side.value,
        "order_type": ORDER_TYPE_TO_KITE[order.order_type],
        "product": PRODUCT_TO_KITE[order.product_type],
        "quantity": order.quantity,
        "validity": "DAY",
        "tag": order.correlation_id.replace("-", "")[:20],
    }
    if order.price:
        form["price"] = order.price
    if order.trigger_price:
        form["trigger_price"] = order.trigger_price
    return form


def to_broker_order(raw: dict[str, Any]) -> BrokerOrder:
    filled = int(raw.get("filled_quantity") or 0)
    status = status_from_kite(str(raw.get("status", "")))
    if status is OrderStatus.OPEN and filled > 0:
        status = OrderStatus.PARTIALLY_FILLED
    avg = raw.get("average_price")
    return BrokerOrder(
        broker_order_id=str(raw.get("order_id", "")),
        status=status,
        quantity=int(raw.get("quantity") or 0),
        filled_quantity=filled,
        average_fill_price=float(avg) if avg else None,
        message=raw.get("status_message"),
        correlation_id=raw.get("tag"),
        symbol=raw.get("tradingsymbol"),
    )


def to_position(raw: dict[str, Any]) -> BrokerPosition | None:
    net = int(raw.get("quantity") or 0)
    if net == 0:
        return None
    return BrokerPosition(
        symbol=str(raw.get("tradingsymbol", "")),
        exchange=str(raw.get("exchange", "NSE")),
        side=PositionSide.LONG if net > 0 else PositionSide.SHORT,
        quantity=abs(net),
        average_price=float(raw.get("average_price") or 0),
        last_price=float(raw.get("last_price") or 0),
        unrealized_pnl=float(raw.get("unrealised") or 0),
        realized_pnl=float(raw.get("realised") or 0),
    )


def to_holding(raw: dict[str, Any]) -> BrokerHolding:
    return BrokerHolding(
        symbol=str(raw.get("tradingsymbol", "")),
        exchange=str(raw.get("exchange", "NSE")),
        quantity=int(raw.get("quantity") or 0),
        average_price=float(raw.get("average_price") or 0),
        last_price=float(raw.get("last_price") or 0),
    )


def to_funds(raw: dict[str, Any]) -> BrokerFunds:
    equity = raw.get("equity") or {}
    available = float((equity.get("available") or {}).get("live_balance") or equity.get("net") or 0)
    used = float((equity.get("utilised") or {}).get("debits") or 0)
    return BrokerFunds(available=available, used_margin=used, total=available + used)


def to_quote(ref: InstrumentRef, raw: dict[str, Any], now: datetime) -> Quote:
    ohlc = raw.get("ohlc") or {}
    ltp = float(raw.get("last_price") or 0)
    return Quote(
        ref.symbol,
        ref.exchange,
        ltp,
        float(ohlc.get("open") or ltp),
        float(ohlc.get("high") or ltp),
        float(ohlc.get("low") or ltp),
        float(ohlc.get("close") or ltp),
        int(raw.get("volume") or 0),
        now,
        "zerodha",
    )


def to_candles(raw: dict[str, Any]) -> list[Candle]:
    out = []
    for ts, o, h, l, c, v, *_ in raw.get("candles") or []:  # noqa: E741
        stamp = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(UTC)
        out.append(Candle(stamp, float(o), float(h), float(l), float(c), int(v)))
    return out
