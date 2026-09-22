"""All Dhan-specific vocabulary lives here. Nothing outside brokers/dhan knows these strings."""

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
    OrderModification,
    OrderRequest,
    Quote,
)

ORDER_TYPE_TO_DHAN = {
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
    OrderType.SL: "STOP_LOSS",
    OrderType.SL_M: "STOP_LOSS_MARKET",
}
PRODUCT_TO_DHAN = {ProductType.INTRADAY: "INTRADAY", ProductType.DELIVERY: "CNC"}
EXCHANGE_SEGMENT = {"NSE": "NSE_EQ", "BSE": "BSE_EQ"}
STATUS_FROM_DHAN = {
    "TRANSIT": OrderStatus.SUBMITTED,
    "PENDING": OrderStatus.OPEN,
    "PART_TRADED": OrderStatus.PARTIALLY_FILLED,
    "TRADED": OrderStatus.FILLED,
    "REJECTED": OrderStatus.REJECTED,
    "CANCELLED": OrderStatus.CANCELLED,
    "EXPIRED": OrderStatus.EXPIRED,
    "TRIGGERED": OrderStatus.OPEN,
    "CONFIRM": OrderStatus.OPEN,
}
INTRADAY_INTERVAL = {Timeframe.M1: "1", Timeframe.M5: "5", Timeframe.M15: "15", Timeframe.H1: "60"}


def segment(ref: InstrumentRef) -> str:
    if ref.segment == "INDEX":
        return "IDX_I"
    try:
        return EXCHANGE_SEGMENT[ref.exchange.upper()]
    except KeyError as exc:
        raise BrokerError(f"Exchange {ref.exchange} is not supported by the Dhan adapter") from exc


def security_id(ref: InstrumentRef) -> str:
    if not ref.exchange_token:
        raise BrokerError(
            f"Instrument {ref.key} has no exchange token (Dhan securityId). Add it to the instrument master."
        )
    return str(ref.exchange_token)


def to_order_payload(order: OrderRequest, client_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dhanClientId": client_id,
        "correlationId": order.correlation_id.replace("-", "")[:25],
        "transactionType": order.side.value,
        "exchangeSegment": segment(order.instrument),
        "productType": PRODUCT_TO_DHAN[order.product_type],
        "orderType": ORDER_TYPE_TO_DHAN[order.order_type],
        "validity": "DAY",
        "securityId": security_id(order.instrument),
        "quantity": order.quantity,
        "disclosedQuantity": 0,
        "price": float(order.price or 0),
        "afterMarketOrder": False,
    }
    if order.order_type in (OrderType.SL, OrderType.SL_M):
        payload["triggerPrice"] = float(order.trigger_price or 0)
    return payload


def to_modify_payload(
    order_id: str, client_id: str, current: dict[str, Any], data: OrderModification
) -> dict[str, Any]:
    return {
        "dhanClientId": client_id,
        "orderId": order_id,
        "orderType": current.get("orderType", "LIMIT"),
        "legName": "ENTRY_LEG",
        "quantity": data.quantity if data.quantity is not None else current.get("quantity"),
        "price": data.price if data.price is not None else current.get("price", 0),
        "triggerPrice": (
            data.trigger_price if data.trigger_price is not None else current.get("triggerPrice", 0)
        ),
        "disclosedQuantity": 0,
        "validity": current.get("validity", "DAY"),
    }


def to_broker_order(raw: dict[str, Any], *, fallback_quantity: int = 0) -> BrokerOrder:
    status = STATUS_FROM_DHAN.get(str(raw.get("orderStatus", "")).upper(), OrderStatus.SUBMITTED)
    filled = int(raw.get("filledQty") or raw.get("filled_qty") or 0)
    avg = raw.get("averageTradedPrice") or raw.get("tradedPrice")
    return BrokerOrder(
        broker_order_id=str(raw.get("orderId", "")),
        status=status,
        quantity=int(raw.get("quantity") or fallback_quantity),
        filled_quantity=filled,
        average_fill_price=float(avg) if avg else None,
        message=raw.get("omsErrorDescription") or raw.get("errorMessage") or None,
        correlation_id=raw.get("correlationId"),
        symbol=raw.get("tradingSymbol"),
    )


def to_position(raw: dict[str, Any]) -> BrokerPosition | None:
    net = int(raw.get("netQty") or 0)
    if net == 0:
        return None
    side = PositionSide.LONG if net > 0 else PositionSide.SHORT
    avg = raw.get("buyAvg") if net > 0 else raw.get("sellAvg")
    return BrokerPosition(
        symbol=str(raw.get("tradingSymbol", "")),
        exchange=str(raw.get("exchangeSegment", "NSE_EQ")).split("_")[0],
        side=side,
        quantity=abs(net),
        average_price=float(avg or raw.get("costPrice") or 0),
        unrealized_pnl=float(raw.get("unrealizedProfit") or 0),
        realized_pnl=float(raw.get("realizedProfit") or 0),
    )


def to_holding(raw: dict[str, Any]) -> BrokerHolding:
    return BrokerHolding(
        symbol=str(raw.get("tradingSymbol", "")),
        exchange=str(raw.get("exchange", "NSE")),
        quantity=int(raw.get("totalQty") or 0),
        average_price=float(raw.get("avgCostPrice") or 0),
        last_price=float(raw["lastTradedPrice"]) if raw.get("lastTradedPrice") else None,
    )


def to_funds(raw: dict[str, Any]) -> BrokerFunds:
    # "availabelBalance" is Dhan's own spelling.
    available = float(raw.get("availabelBalance") or raw.get("availableBalance") or 0)
    used = float(raw.get("utilizedAmount") or 0)
    return BrokerFunds(available=available, used_margin=used, total=available + used)


def to_quote(ref: InstrumentRef, raw: dict[str, Any], now: datetime) -> Quote:
    ohlc = raw.get("ohlc") or {}
    ltp = float(raw.get("last_price") or 0)
    depth = raw.get("depth") or {}
    bids, asks = depth.get("buy") or [], depth.get("sell") or []
    bid = float(bids[0]["price"]) if bids and bids[0].get("price") else None
    ask = float(asks[0]["price"]) if asks and asks[0].get("price") else None
    return Quote(
        symbol=ref.symbol,
        exchange=ref.exchange,
        ltp=ltp,
        open=float(ohlc.get("open") or ltp),
        high=float(ohlc.get("high") or ltp),
        low=float(ohlc.get("low") or ltp),
        close=float(ohlc.get("close") or ltp),
        volume=int(raw.get("volume") or 0),
        timestamp=now,
        source="dhan",
        bid=bid,
        ask=ask,
    )


def to_candles(raw: dict[str, Any]) -> list[Candle]:
    timestamps = raw.get("timestamp") or []
    return [
        Candle(
            datetime.fromtimestamp(float(ts), UTC),
            float(raw["open"][i]),
            float(raw["high"][i]),
            float(raw["low"][i]),
            float(raw["close"][i]),
            int(raw["volume"][i]) if raw.get("volume") else 0,
        )
        for i, ts in enumerate(timestamps)
    ]
