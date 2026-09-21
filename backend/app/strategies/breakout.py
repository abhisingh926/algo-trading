from __future__ import annotations

from collections.abc import Sequence

from app.domain.enums import SignalType, StrategyType
from app.domain.types import Candle, SignalResult
from app.strategies.base import ParameterSpec, Strategy


class BreakoutStrategy(Strategy):
    strategy_type = StrategyType.BREAKOUT
    display_name = "Breakout"
    description = "BUY when the close breaks the highest high of the lookback window, SELL on a break of the lowest low."
    parameter_specs = (
        ParameterSpec(
            "lookback_period", "Lookback bars", "int", 20, 2, 500, "Bars used for the high/low channel"
        ),
        ParameterSpec(
            "buffer_pct", "Buffer (fraction)", "float", 0.0, 0, 0.05, "Extra distance beyond the channel"
        ),
    )

    @property
    def lookback_bars(self) -> int:
        return int(self.params["lookback_period"]) + 1

    def generate_signal(self, market_data: Sequence[Candle]) -> SignalResult:
        lookback = int(self.params["lookback_period"])
        price = market_data[-1].close if market_data else 0.0
        if len(market_data) < lookback + 1:
            return SignalResult.hold(price, f"Need {lookback + 1} bars, have {len(market_data)}")

        window = market_data[-lookback - 1 : -1]  # excludes the bar being evaluated
        upper = max(c.high for c in window) * (1 + float(self.params["buffer_pct"]))
        lower = min(c.low for c in window) * (1 - float(self.params["buffer_pct"]))
        indicators = {"channel_high": round(upper, 4), "channel_low": round(lower, 4)}
        if price > upper:
            return SignalResult(SignalType.BUY, price, f"Close broke above {lookback}-bar high", indicators)
        if price < lower:
            return SignalResult(SignalType.SELL, price, f"Close broke below {lookback}-bar low", indicators)
        return SignalResult(SignalType.HOLD, price, "Inside channel", indicators)
