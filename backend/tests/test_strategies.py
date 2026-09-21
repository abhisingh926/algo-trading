import pytest

from app.domain.enums import SignalType
from app.strategies.base import StrategyConfigError
from app.strategies.registry import create_strategy, describe_strategies
from tests.conftest import make_candles


class TestEmaCrossover:
    def test_buy_when_fast_crosses_above_slow(self):
        strategy = create_strategy("EMA_CROSSOVER", {"fast_period": 3, "slow_period": 6})
        closes = [100.0] * 10 + [99, 98, 97, 96, 95] + [96, 98, 101, 105]
        signals = [
            strategy.generate_signal(make_candles(closes[: i + 1])).type for i in range(6, len(closes))
        ]
        assert SignalType.BUY in signals
        assert signals.index(SignalType.BUY) > signals.index(
            SignalType.SELL
        )  # down-cross first, then up-cross

    def test_signal_fires_only_on_the_crossover_bar(self):
        strategy = create_strategy("EMA_CROSSOVER", {"fast_period": 3, "slow_period": 6})
        closes = [100.0] * 10 + [101, 103, 106, 110, 115, 121]
        signals = [
            strategy.generate_signal(make_candles(closes[: i + 1])).type for i in range(6, len(closes))
        ]
        assert signals.count(SignalType.BUY) == 1

    def test_sell_when_fast_crosses_below_slow(self):
        strategy = create_strategy("EMA_CROSSOVER", {"fast_period": 3, "slow_period": 6})
        closes = [100.0] * 10 + [101, 102, 103] + [100, 96, 92]
        result = [strategy.generate_signal(make_candles(closes[: i + 1])) for i in range(6, len(closes))]
        sells = [r for r in result if r.type is SignalType.SELL]
        assert len(sells) == 1 and sells[0].indicators["fast_ema"] < sells[0].indicators["slow_ema"]

    def test_hold_with_insufficient_data(self):
        strategy = create_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 20})
        assert strategy.generate_signal(make_candles([100.0] * 10)).type is SignalType.HOLD

    def test_parameters_are_validated(self):
        with pytest.raises(StrategyConfigError, match="smaller"):
            create_strategy("EMA_CROSSOVER", {"fast_period": 50, "slow_period": 20})
        with pytest.raises(StrategyConfigError, match="Unknown parameter"):
            create_strategy("EMA_CROSSOVER", {"fast": 5})
        with pytest.raises(StrategyConfigError, match="between"):
            create_strategy("EMA_CROSSOVER", {"fast_period": 1, "slow_period": 20})

    def test_defaults_come_from_specs_not_code_paths(self):
        assert create_strategy("EMA_CROSSOVER").params == {"fast_period": 20, "slow_period": 50}


class TestVwap:
    def test_buy_on_cross_above_vwap(self):
        strategy = create_strategy("VWAP", {"band_pct": 0.001, "min_bars": 3})
        candles = make_candles([100, 99.5, 99, 98.8, 98.9, 101.5])
        result = strategy.generate_signal(candles)
        assert result.type is SignalType.BUY and result.price > result.indicators["upper"]

    def test_sell_on_cross_below_vwap(self):
        strategy = create_strategy("VWAP", {"band_pct": 0.001, "min_bars": 3})
        assert (
            strategy.generate_signal(make_candles([100, 100.5, 101, 101.2, 101.1, 98.5])).type
            is SignalType.SELL
        )

    def test_hold_while_price_stays_on_one_side(self):
        strategy = create_strategy("VWAP", {"band_pct": 0.001, "min_bars": 3})
        assert strategy.generate_signal(make_candles([100, 101, 102, 103, 104, 105])).type is SignalType.HOLD

    def test_session_anchor_ignores_previous_day(self):
        strategy = create_strategy("VWAP", {"min_bars": 3})
        yesterday = make_candles([500.0] * 20)
        today = make_candles([100, 99.5, 99, 98.8, 98.9, 101.5], start=yesterday[0].timestamp.replace(day=6))
        result = strategy.generate_signal([*yesterday, *today])
        assert result.indicators["vwap"] < 110  # 500-level bars from yesterday are excluded

    def test_rolling_window_mode(self):
        strategy = create_strategy("VWAP", {"window": 4, "band_pct": 0.0})
        assert strategy.generate_signal(make_candles([100, 99, 98, 97, 96, 101])).type is SignalType.BUY


class TestBreakout:
    def test_buy_on_break_of_lookback_high(self):
        strategy = create_strategy("BREAKOUT", {"lookback_period": 5})
        result = strategy.generate_signal(make_candles([100, 101, 100, 99, 100, 101, 104]))
        assert result.type is SignalType.BUY and result.price > result.indicators["channel_high"]

    def test_sell_on_break_of_lookback_low(self):
        strategy = create_strategy("BREAKOUT", {"lookback_period": 5})
        assert (
            strategy.generate_signal(make_candles([100, 101, 100, 99, 100, 99, 95])).type is SignalType.SELL
        )

    def test_hold_inside_channel(self):
        strategy = create_strategy("BREAKOUT", {"lookback_period": 5})
        assert (
            strategy.generate_signal(make_candles([100, 101, 100, 99, 100, 101, 100.5])).type
            is SignalType.HOLD
        )

    def test_lookback_is_configurable(self):
        candles = make_candles([110, 100, 101, 100, 99, 100, 101, 104])
        assert (
            create_strategy("BREAKOUT", {"lookback_period": 5}).generate_signal(candles).type
            is SignalType.BUY
        )
        assert (
            create_strategy("BREAKOUT", {"lookback_period": 7}).generate_signal(candles).type
            is SignalType.HOLD
        )

    def test_buffer_requires_a_larger_break(self):
        candles = make_candles([100, 101, 100, 99, 100, 101, 102])
        assert (
            create_strategy("BREAKOUT", {"lookback_period": 5, "buffer_pct": 0.02})
            .generate_signal(candles)
            .type
            is SignalType.HOLD
        )


def test_registry_describes_all_strategies_for_the_ui():
    described = {d["type"]: d for d in describe_strategies()}
    assert set(described) == {"EMA_CROSSOVER", "VWAP", "BREAKOUT"}
    assert {p["key"] for p in described["EMA_CROSSOVER"]["parameters"]} == {"fast_period", "slow_period"}
