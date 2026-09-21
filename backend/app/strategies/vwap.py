from __future__ import annotations

from collections.abc import Sequence

from app.domain.enums import SignalType, StrategyType
from app.domain.types import Candle, SignalResult
from app.strategies.base import ParameterSpec, Strategy
from app.utils.indicators import vwap
from app.utils.time import ist_day_number


class VwapStrategy(Strategy):
    strategy_type = StrategyType.VWAP
    display_name = "VWAP"
    description = (
        "BUY when price crosses above VWAP (plus a band), SELL when it crosses below. "
        "VWAP is anchored to the trading session, or rolling when 'window' is set."
    )
    parameter_specs = (
        ParameterSpec(
            "band_pct",
            "Band (fraction)",
            "float",
            0.001,
            0,
            0.05,
            "Distance from VWAP required to confirm a cross",
        ),
        ParameterSpec("min_bars", "Minimum bars", "int", 5, 2, 200, "Bars required before VWAP is trusted"),
        ParameterSpec(
            "window",
            "Rolling window",
            "int",
            0,
            0,
            2000,
            "0 = session anchored VWAP, otherwise rolling N bars",
        ),
    )

    @property
    def lookback_bars(self) -> int:
        window = int(self.params["window"])
        return window + 1 if window > 0 else 400  # a full 1-minute NSE session is 375 bars

    @staticmethod
    def _current_session(bars: Sequence[Candle]) -> Sequence[Candle]:
        if not bars:
            return bars
        day, start = ist_day_number(bars[-1].timestamp), len(bars) - 1
        while start > 0 and ist_day_number(bars[start - 1].timestamp) == day:
            start -= 1
        return bars[start:]

    def _vwap_series(self, bars: Sequence[Candle]) -> list[float]:
        return vwap(
            [c.high for c in bars], [c.low for c in bars], [c.close for c in bars], [c.volume for c in bars]
        )

    def generate_signal(self, market_data: Sequence[Candle]) -> SignalResult:
        price = market_data[-1].close if market_data else 0.0
        window, min_bars = int(self.params["window"]), int(self.params["min_bars"])
        if window > 0:
            if len(market_data) < window + 1:
                return SignalResult.hold(price, f"Need {window + 1} bars, have {len(market_data)}")
            current = self._vwap_series(market_data[-window:])[-1]
            previous = self._vwap_series(market_data[-window - 1 : -1])[-1]
        else:
            session = self._current_session(market_data)
            if len(session) < max(min_bars, 2):
                return SignalResult.hold(price, f"Need {min_bars} session bars, have {len(session)}")
            series = self._vwap_series(session)
            current, previous = series[-1], series[-2]

        band = float(self.params["band_pct"])
        prev_close = market_data[-2].close
        indicators = {
            "vwap": round(current, 4),
            "upper": round(current * (1 + band), 4),
            "lower": round(current * (1 - band), 4),
        }
        if prev_close <= previous * (1 + band) and price > current * (1 + band):
            return SignalResult(SignalType.BUY, price, "Price crossed above VWAP", indicators)
        if prev_close >= previous * (1 - band) and price < current * (1 - band):
            return SignalResult(SignalType.SELL, price, "Price crossed below VWAP", indicators)
        return SignalResult(SignalType.HOLD, price, "No VWAP cross", indicators)
