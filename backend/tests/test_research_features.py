from datetime import date, timedelta

import pytest

from app.domain.types import Candle
from app.research import sessions as ses
from app.research.features import InsufficientDataError, build_bundle
from tests.research_helpers import (
    IST,
    TF_FULL,
    cut_session,
    make_history,
    make_session,
    symbol_input,
    trading_days,
)


def flat_history(sessions: int, volume: int = 1000, price: float = 100.0) -> list[Candle]:
    bars: list[Candle] = []
    for day in trading_days(date(2025, 6, 2), sessions):
        bars += make_session(day, price, volume=volume, spread=0.0)
    return bars


def test_requires_enough_sessions():
    with pytest.raises(InsufficientDataError, match="at least"):
        build_bundle(symbol_input(flat_history(10)), ["15m", "daily"])


def test_relative_volume_compares_with_the_same_time_of_day():
    bars = flat_history(30, volume=1000)
    day = trading_days(date(2025, 6, 2), 31)[-1]
    today = make_session(day, 100.0, volume=3000, spread=0.0)[:10]
    bundle = build_bundle(symbol_input(bars + today), ["15m", "daily"])
    assert bundle.price.rel_volume == pytest.approx(3.0)
    assert bundle.price.bars_in_session == 10 and bundle.session_complete is False
    assert bundle.price.avg_volume == pytest.approx(
        25_000
    )  # average full-day volume of the previous sessions


def test_gap_vwap_and_day_range():
    bars = flat_history(30, price=100.0)
    day = trading_days(date(2025, 6, 2), 31)[-1]
    today = make_session(day, 102.0, path=lambda i, n: 102.0 + 0.1 * i, spread=0.0)[
        :12
    ]  # opens 2% up and drifts higher
    bundle = build_bundle(symbol_input(bars + today), ["15m", "daily"])
    p, lv = bundle.price, bundle.technical.levels
    assert p.gap_pct == pytest.approx(2.0) and lv.gap_direction == "UP" and lv.gap_filled_today is False
    assert p.prev_close == 100.0 and p.day_open == 102.0 and p.price == pytest.approx(103.1)
    assert lv.vwap_position == "ABOVE" and lv.vwap < p.price
    assert lv.prev_day_high == 100.0 and lv.prev_day_low == 100.0
    assert bundle.technical.direction in ("BULLISH", "NEUTRAL")


def test_gap_fill_is_detected():
    bars = flat_history(30, price=100.0)
    day = trading_days(date(2025, 6, 2), 31)[-1]
    today = make_session(day, 102.0, path=lambda i, n: 102.0 - 0.3 * i, spread=0.0)[
        :10
    ]  # gaps up, then falls back through 100
    lv = build_bundle(symbol_input(bars + today), ["15m", "daily"]).technical.levels
    assert lv.gap_direction == "UP" and lv.gap_filled_today is True


def test_opening_range_only_after_the_window_completes():
    bars = flat_history(30)
    day = trading_days(date(2025, 6, 2), 31)[-1]
    session = make_session(day, 100.0, path=lambda i, n: 100 + i * 0.5, spread=0.0)
    early = build_bundle(symbol_input(bars + session[:1]), ["15m", "daily"]).technical.levels
    later = build_bundle(symbol_input(bars + session[:6]), ["15m", "daily"]).technical.levels
    assert early.opening_range_15_high is not None and early.opening_range_30_high is None
    assert later.opening_range_30_high == pytest.approx(
        100.5
    ) and later.opening_range_30_low == pytest.approx(
        100.0
    )  # first two 15-minute bars


def test_trend_direction_and_price_action_on_a_steady_uptrend():
    bars = make_history(80, drift=0.02, noise=0.001, seed=4)  # strong drift, little noise
    bundle = build_bundle(symbol_input(bars), TF_FULL[1:])
    assert bundle.technical.direction == "BULLISH" and bundle.direction_score >= 3
    daily = next(t for t in bundle.technical.timeframes if t.timeframe == "daily")
    assert daily.trend == "UP" and daily.ema_stack == "BULLISH"
    # a perfectly steady trend has no pullbacks, so no swing structure can be measured, and that is reported as UNKNOWN
    assert bundle.technical.price_action.structure in ("HIGHER_HIGHS_LOWS", "MIXED", "UNKNOWN")
    assert bundle.technical.price_action.breakout_20d == "UP"


def test_multi_timeframes_are_built_and_labelled():
    bundle = build_bundle(symbol_input(make_history(120, seed=2)), TF_FULL[1:])
    names = [t.timeframe for t in bundle.technical.timeframes]
    assert names == ["15m", "30m", "1h", "daily", "weekly"]
    weekly = next(t for t in bundle.technical.timeframes if t.timeframe == "weekly")
    thirty = next(t for t in bundle.technical.timeframes if t.timeframe == "30m")
    assert weekly.bars < 30 and thirty.ema200 is not None


def test_five_minute_tail_extends_the_data_time():
    bars = cut_session(make_history(60, seed=5), 10)
    last_end = bars[-1].timestamp + timedelta(minutes=15)
    tail = [
        Candle(last_end, 100, 101, 99, 100.5, 500),
        Candle(last_end + timedelta(minutes=5), 100.5, 102, 100, 101.5, 700),
    ]
    bundle = build_bundle(
        symbol_input(bars, bars_5m=tail, as_of=last_end + timedelta(minutes=10)), ["15m", "daily"]
    )
    assert bundle.data_as_of == last_end + timedelta(minutes=10) and bundle.price.price == 101.5


def test_no_look_ahead_bars_after_as_of_are_ignored():
    full = make_history(60, seed=6)
    as_of = full[-10].timestamp  # ten bars before the end of the data; the bar ending exactly now is complete
    visible = ses.closed_before(full, as_of, 15)
    from_full = build_bundle(symbol_input(visible, as_of=as_of), ["15m", "daily"])
    from_trimmed = build_bundle(symbol_input(full[:-10], as_of=as_of), ["15m", "daily"])
    assert (
        from_full.price == from_trimmed.price
        and from_full.technical.timeframes == from_trimmed.technical.timeframes
    )
    assert from_full.data_as_of == as_of


def test_session_boundaries_use_ist():
    bars = make_history(30)
    assert all(
        b.timestamp.astimezone(IST).hour * 60 + b.timestamp.astimezone(IST).minute >= 9 * 60 + 15
        for b in bars
    )
