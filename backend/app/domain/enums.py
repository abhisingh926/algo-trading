"""Domain enumerations shared by every layer."""

from enum import StrEnum


class TradingMode(StrEnum):
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"


class BrokerType(StrEnum):
    PAPER = "PAPER"
    DHAN = "DHAN"
    ZERODHA = "ZERODHA"
    FYERS = "FYERS"


class BrokerEnvironment(StrEnum):
    PAPER = "PAPER"
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"


class ConnectionStatus(StrEnum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNKNOWN = "UNKNOWN"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def sign(self) -> int:
        return 1 if self is OrderSide.BUY else -1

    @property
    def opposite(self) -> "OrderSide":
        return OrderSide.SELL if self is OrderSide.BUY else OrderSide.BUY


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class ProductType(StrEnum):
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    TRIGGER_PENDING = "TRIGGER_PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


ACTIVE_ORDER_STATUSES = frozenset(
    {
        OrderStatus.CREATED,
        OrderStatus.SUBMITTED,
        OrderStatus.OPEN,
        OrderStatus.TRIGGER_PENDING,
        OrderStatus.PARTIALLY_FILLED,
    }
)
TERMINAL_ORDER_STATUSES = frozenset(set(OrderStatus) - ACTIVE_ORDER_STATUSES)

ORDER_STATUS_GROUPS: dict[str, frozenset[OrderStatus]] = {
    "open": ACTIVE_ORDER_STATUSES,
    "filled": frozenset({OrderStatus.FILLED}),
    "rejected": frozenset({OrderStatus.REJECTED, OrderStatus.FAILED}),
    "cancelled": frozenset({OrderStatus.CANCELLED, OrderStatus.EXPIRED}),
}


class OrderSource(StrEnum):
    MANUAL = "MANUAL"
    STRATEGY = "STRATEGY"
    RISK_EXIT = "RISK_EXIT"
    KILL_SWITCH = "KILL_SWITCH"


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self is PositionSide.LONG else -1

    @property
    def exit_order_side(self) -> OrderSide:
        return OrderSide.SELL if self is PositionSide.LONG else OrderSide.BUY


class PositionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ExitReason(StrEnum):
    SIGNAL = "SIGNAL"
    STOP_LOSS = "STOP_LOSS"
    TARGET = "TARGET"
    MANUAL = "MANUAL"
    KILL_SWITCH = "KILL_SWITCH"
    END_OF_DATA = "END_OF_DATA"


class SignalType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStatus(StrEnum):
    GENERATED = "GENERATED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    IGNORED = "IGNORED"


class StrategyType(StrEnum):
    EMA_CROSSOVER = "EMA_CROSSOVER"
    VWAP = "VWAP"
    BREAKOUT = "BREAKOUT"


class StrategyStatus(StrEnum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class BacktestStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"

    @property
    def minutes(self) -> int:
        return {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}[self.value]

    @property
    def is_intraday(self) -> bool:
        return self is not Timeframe.D1


class EventLevel(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
