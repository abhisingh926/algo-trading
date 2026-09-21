from __future__ import annotations

from collections.abc import Sequence

from app.domain.enums import SignalType, StrategyType
from app.domain.types import Candle, SignalResult
from app.strategies.base import ParameterSpec, Strategy, StrategyConfigError
from app.utils.indicators import ema


class EmaCrossoverStrategy(Strategy):
    strategy_type = StrategyType.EMA_CROSSOVER
    display_name = "EMA Crossover"
    description = "BUY when the fast EMA crosses above the slow EMA, SELL when it crosses below."
    parameter_specs = (
        ParameterSpec("fast_period", "Fast EMA", "int", 20, 2, 200, "Period of the fast EMA"),
        ParameterSpec("slow_period", "Slow EMA", "int", 50, 3, 500, "Period of the slow EMA"),
    )

    def validate(self) -> None:
        if self.params["fast_period"] >= self.params["slow_period"]:
            raise StrategyConfigError("fast_period must be smaller than slow_period")

    @property
    def lookback_bars(self) -> int:
        # ~4x the slow period lets the EMA recursion converge regardless of the seed.
        return int(self.params["slow_period"]) * 4 + 2

    def generate_signal(self, market_data: Sequence[Candle]) -> SignalResult:
        slow_period = int(self.params["slow_period"])
        price = market_data[-1].close if market_data else 0.0
        if len(market_data) < slow_period + 1:
            return SignalResult.hold(price, f"Need {slow_period + 1} bars, have {len(market_data)}")

        closes = [c.close for c in market_data]
        fast = ema(closes, int(self.params["fast_period"]))
        slow = ema(closes, slow_period)
        indicators = {"fast_ema": round(fast[-1], 4), "slow_ema": round(slow[-1], 4)}
        prev_diff, diff = fast[-2] - slow[-2], fast[-1] - slow[-1]

        if prev_diff <= 0 < diff:
            return SignalResult(SignalType.BUY, price, "Fast EMA crossed above slow EMA", indicators)
        if prev_diff >= 0 > diff:
            return SignalResult(SignalType.SELL, price, "Fast EMA crossed below slow EMA", indicators)
        return SignalResult(SignalType.HOLD, price, "No crossover", indicators)
