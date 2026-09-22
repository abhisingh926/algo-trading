from datetime import date

import pytest

from app.domain.types import Candle
from app.research import indicators as ind
from app.research import sessions as ses
from tests.research_helpers import ist, make_history, make_session, trading_days

# Wilder's classic RSI sample series. The expected values are recomputed inside the test from first
# principles (the seed average, then Wilder smoothing). Separately, all indicators were cross-checked against the
# `ta` library on a 400-bar series and agreed to six decimal places once warmed up.
WILDER_CLOSES = [
    44.34,
    44.09,
    44.15,
    43.61,
    44.33,
    44.83,
    45.10,
    45.42,
    45.84,
    46.08,
    45.89,
    46.03,
    45.61,
    46.28,
    46.28,
    46.00,
    46.03,
    46.41,
    46.22,
    45.64,
]


class TestIndicators:
    def test_rsi_matches_first_principles(self):
        values = ind.rsi(WILDER_CLOSES, 14)
        assert all(v is None for v in values[:14])
        changes = [WILDER_CLOSES[i] - WILDER_CLOSES[i - 1] for i in range(1, len(WILDER_CLOSES))]
        avg_gain = sum(max(c, 0) for c in changes[:14]) / 14
        avg_loss = sum(max(-c, 0) for c in changes[:14]) / 14
        expected = [100 - 100 / (1 + avg_gain / avg_loss)]
        for change in changes[14:]:
            avg_gain = (avg_gain * 13 + max(change, 0)) / 14
            avg_loss = (avg_loss * 13 + max(-change, 0)) / 14
            expected.append(100 - 100 / (1 + avg_gain / avg_loss))
        assert values[14:] == [pytest.approx(v) for v in expected]
        assert round(values[14], 2) == 70.46

    def test_rsi_extremes(self):
        assert ind.rsi(list(range(1, 40)), 14)[-1] == 100.0
        assert ind.rsi([10.0] * 40, 14)[-1] == 50.0
        assert ind.rsi(list(range(40, 1, -1)), 14)[-1] == pytest.approx(0.0)

    def test_sma_and_ema_warm_up(self):
        assert ind.sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]
        e = ind.ema([1, 2, 3, 4, 5, 6], 3)
        assert e[:2] == [None, None] and e[2] == 2.0 and e[3] == pytest.approx(3.0)

    def test_atr_of_constant_range(self):
        highs, lows, closes = [102.0] * 30, [100.0] * 30, [101.0] * 30
        assert ind.atr(highs, lows, closes, 14)[-1] == pytest.approx(2.0)

    def test_adx_separates_trend_from_chop(self):
        up = [100 + i for i in range(80)]
        strong = ind.adx([c + 0.5 for c in up], [c - 0.5 for c in up], up, 14)[0][-1]
        chop = [100 + (1 if i % 2 else -1) for i in range(80)]
        weak = ind.adx([c + 0.5 for c in chop], [c - 0.5 for c in chop], chop, 14)[0][-1]
        assert strong > 40 and weak < 15

    def test_macd_signs(self):
        line, _, hist = ind.macd([100 + i * 0.5 for i in range(80)])
        assert line[-1] > 0 and line[24] is None and hist[-1] is not None
        down_line, _, _ = ind.macd([200 - i * 0.5 for i in range(80)])
        assert down_line[-1] < 0

    def test_bollinger_flat_and_expanding(self):
        assert ind.bollinger([50.0] * 30)[3][-1] == 0
        noisy = [50 + (5 if i % 2 else -5) for i in range(30)]
        assert ind.bollinger(noisy)[3][-1] > 10

    def test_roc(self):
        assert ind.roc([100, 110, 121], 1)[1:] == [pytest.approx(10.0), pytest.approx(10.0)]

    def test_supertrend_follows_and_flips(self):
        closes = [100 + i for i in range(40)] + [140 - 4 * i for i in range(30)]
        highs, lows = [c + 1 for c in closes], [c - 1 for c in closes]
        line, direction = ind.supertrend(highs, lows, closes, 10, 3.0)
        assert direction[35] == 1 and direction[-1] == -1 and line[35] < closes[35] and line[-1] > closes[-1]

    def test_historical_volatility(self):
        assert ind.historical_volatility([100.0] * 30, 20) == pytest.approx(0.0)
        assert ind.historical_volatility([100 * (1.01 if i % 2 else 0.99) ** i for i in range(30)], 20) > 0
        assert ind.historical_volatility([1, 2, 3], 20) is None

    def test_swing_points_and_levels(self):
        highs = [1, 2, 3, 2, 1, 2, 4, 2, 1]
        lows = [h - 0.5 for h in highs]
        swing_highs, swing_lows = ind.swing_points(highs, lows, 2, 2)
        assert [i for i, _ in swing_highs] == [2, 6] and [i for i, _ in swing_lows] == [4]
        levels = ind.cluster_levels([100, 100.2, 100.3, 110, 120, 120.1], 0.5)
        assert levels[0][1] == 3 and round(levels[0][0], 1) == 100.2


class TestSessions:
    def test_only_regular_session_bars_survive(self):
        monday = date(2026, 1, 5)
        regular = make_session(monday, 100)
        pre_market = [Candle(ist(2026, 1, 5, 8, 0), 1, 1, 1, 1, 1)]
        weekend = [Candle(ist(2026, 1, 3, 10, 0), 1, 1, 1, 1, 1)]
        after_close = [Candle(ist(2026, 1, 5, 15, 30), 1, 1, 1, 1, 1)]
        kept = ses.filter_session([*pre_market, *regular, *weekend, *after_close])
        assert (
            len(kept) == 25
            and kept[0].timestamp == ist(2026, 1, 5, 9, 15)
            and kept[-1].timestamp == ist(2026, 1, 5, 15, 15)
        )

    def test_resample_is_anchored_to_the_open(self):
        bars = make_session(date(2026, 1, 5), 100, volume=1000)
        thirty = ses.resample(bars, 30)
        assert len(thirty) == 13  # 12 full 30-minute buckets and the final 15-minute remainder
        assert thirty[0].timestamp == ist(2026, 1, 5, 9, 15) and thirty[1].timestamp == ist(2026, 1, 5, 9, 45)
        assert thirty[0].volume == 2000 and thirty[-1].volume == 1000
        hourly = ses.resample(bars, 60)
        assert hourly[0].timestamp == ist(2026, 1, 5, 9, 15) and hourly[1].timestamp == ist(
            2026, 1, 5, 10, 15
        )

    def test_daily_and_weekly_aggregation(self):
        days = trading_days(date(2026, 1, 5), 10)  # two full weeks
        bars = [b for d in days for b in make_session(d, 100 + days.index(d), volume=100)]
        sessions = ses.group_sessions(bars)
        daily = ses.to_daily(sessions)
        assert len(daily) == 10 and daily[0].volume == 2500 and daily[3].open == pytest.approx(103)
        weekly = ses.to_weekly(daily)
        assert len(weekly) == 2 and weekly[0].volume == 5 * 2500

    def test_closed_before_blocks_look_ahead(self):
        bars = make_session(date(2026, 1, 5), 100)
        as_of = ist(2026, 1, 5, 10, 0)
        visible = ses.closed_before(bars, as_of, 15)
        assert visible[-1].timestamp == ist(2026, 1, 5, 9, 45)  # the 09:45 bar closes exactly at 10:00
        assert all(b.timestamp + __import__("datetime").timedelta(minutes=15) <= as_of for b in visible)
        assert ses.closed_before(bars, ist(2026, 1, 5, 9, 20), 15) == []

    def test_vwap_and_opening_range(self):
        bars = [
            Candle(ist(2026, 1, 5, 9, 15), 100, 102, 99, 101, 1000),
            Candle(ist(2026, 1, 5, 9, 30), 101, 103, 100, 102, 3000),
        ]
        vwap = ses.vwap_series(bars)
        assert vwap[0] == pytest.approx((102 + 99 + 101) / 3)
        assert vwap[1] == pytest.approx(((102 + 99 + 101) / 3 * 1000 + (103 + 100 + 102) / 3 * 3000) / 4000)
        assert ses.opening_range(bars, 15) == (102, 99) and ses.opening_range(bars, 30) == (103, 99)
        assert ses.opening_range(bars[:1], 30) is None  # window not complete yet

    def test_market_state(self):
        assert ses.market_state(ist(2026, 1, 5, 11, 0)) == "OPEN"
        assert ses.market_state(ist(2026, 1, 5, 8, 0)) == "PRE_MARKET"
        assert ses.market_state(ist(2026, 1, 5, 16, 0)) == "POST_MARKET"
        assert ses.market_state(ist(2026, 1, 3, 11, 0)) == "CLOSED"

    def test_history_builder_produces_regular_sessions(self):
        history = make_history(30)
        sessions = ses.group_sessions(ses.filter_session(history))
        assert len(sessions) == 30 and all(len(s.bars) == 25 for s in sessions)
