"""Post-market calibration: measuring what actually followed each research score."""

from datetime import date, timedelta

import pytest

from app.research import calibration as cal
from tests.research_helpers import ist, make_session


def candidate(score=80.0, direction="BULLISH", as_of=None, symbol="TEST"):  # noqa: ANN001, ANN201
    return cal.ScoredCandidate(
        run_id="run-1",
        symbol=symbol,
        as_of=as_of or ist(2026, 1, 5, 11, 0),
        research_score=score,
        data_confidence=70.0,
        risk_score=30.0,
        direction=direction,
    )


def rising_session(day=date(2026, 1, 5), start=100.0, step=0.5):  # noqa: ANN001, ANN201
    return make_session(day, start, path=lambda i, n: start + step * (i + 1), bars=25, minutes=15, spread=0.0)


class TestMeasurement:
    def test_entry_is_the_first_bar_that_starts_after_the_score(self):
        bars = rising_session()
        outcome = cal.measure(candidate(as_of=ist(2026, 1, 5, 11, 0)), bars, "15m")
        assert outcome is not None
        assert outcome.entry_time == ist(2026, 1, 5, 11, 0)
        # the bar starting 11:00 is the eighth of the session and opens at the previous close
        assert outcome.entry_price == pytest.approx(103.5)

    def test_nothing_before_the_score_is_used(self):
        """Bars from earlier in the session must not affect the result."""
        bars = rising_session()
        full = cal.measure(candidate(as_of=ist(2026, 1, 5, 11, 0)), bars, "15m")
        trimmed = cal.measure(
            candidate(as_of=ist(2026, 1, 5, 11, 0)),
            [b for b in bars if b.timestamp >= ist(2026, 1, 5, 10, 30)],
            "15m",
        )
        assert full is not None and trimmed is not None
        assert full.entry_price == trimmed.entry_price and full.returns == trimmed.returns

    def test_horizons_are_measured_from_the_entry(self):
        outcome = cal.measure(candidate(as_of=ist(2026, 1, 5, 10, 0)), rising_session(), "15m")
        assert outcome is not None
        entry = outcome.entry_price
        # entering at the open, 15 minutes later is that same bar's close, an hour later is four bars on
        assert outcome.returns["15m"] == pytest.approx((0.5 / entry) * 100, abs=1e-3)
        assert outcome.returns["1h"] == pytest.approx((2.0 / entry) * 100, abs=1e-3)
        assert outcome.returns["5m"] is None  # finer than the bar size available
        assert outcome.horizons_complete == 3

    def test_direction_is_applied_so_a_bearish_call_wins_when_price_falls(self):
        falling = make_session(date(2026, 1, 5), 100.0, path=lambda i, n: 100 - 0.5 * (i + 1), spread=0.0)
        bullish = cal.measure(candidate(direction="BULLISH", as_of=ist(2026, 1, 5, 10, 0)), falling, "15m")
        bearish = cal.measure(candidate(direction="BEARISH", as_of=ist(2026, 1, 5, 10, 0)), falling, "15m")
        assert bullish is not None and bearish is not None
        assert bullish.returns["1h"] < 0 < bearish.returns["1h"]
        assert bearish.returns["1h"] == pytest.approx(-bullish.returns["1h"])

    def test_the_hour_never_crosses_the_close(self):
        """Late in the day the short horizons still fit, but the hour does not and is left empty."""
        bars = rising_session()
        late = cal.measure(candidate(as_of=ist(2026, 1, 5, 15, 0)), bars, "15m")
        assert late is not None
        assert late.returns["15m"] is not None and late.returns["30m"] is not None
        assert late.returns["1h"] is None and late.primary is None

    def test_a_score_with_no_following_data_is_unmeasurable_not_flat(self):
        assert cal.measure(candidate(as_of=ist(2026, 1, 6, 10, 0)), rising_session(), "15m") is None

    def test_mfe_and_mae_for_long_and_short(self):
        # up to 102 then down to 98, entering at 100
        path = [101.0, 102.0, 99.0, 98.0, 100.0]
        bars = make_session(
            date(2026, 1, 5), 100.0, path=lambda i, n: path[i] if i < len(path) else 100.0, bars=8, spread=0.0
        )
        long = cal.measure(candidate(direction="BULLISH", as_of=bars[0].timestamp), bars, "15m")
        short = cal.measure(candidate(direction="BEARISH", as_of=bars[0].timestamp), bars, "15m")
        assert long is not None and short is not None
        assert long.mfe_pct == pytest.approx(2.0, abs=0.01) and long.mae_pct == pytest.approx(-2.0, abs=0.01)
        assert short.mfe_pct == pytest.approx(2.0, abs=0.01) and short.mae_pct == pytest.approx(
            -2.0, abs=0.01
        )
        assert long.mae_pct <= 0 and short.mae_pct <= 0


class TestSummary:
    def outcomes(self, spec):  # noqa: ANN001, ANN201
        """spec: list of (score, drift per bar). Builds one measured outcome per entry."""
        out = []
        for i, (score, drift) in enumerate(spec):
            day = date(2026, 1, 5) + timedelta(days=i % 5)
            bars = make_session(day, 100.0, path=lambda k, n, d=drift: 100 + d * (k + 1), spread=0.0)
            measured = cal.measure(candidate(score=score, as_of=bars[0].timestamp), bars, "15m")
            assert measured is not None
            out.append(measured)
        return out

    def test_buckets_need_an_adequate_sample_before_a_rate_is_shown(self):
        summary = cal.summarise(self.outcomes([(85.0, 0.1)] * 5), min_sample=30)
        bucket = next(b for b in summary.buckets if b.bucket == "80-89")
        assert bucket.occurrences == 5 and not bucket.sample_adequate
        assert bucket.win_rate is None and bucket.mean_returns["1h"] is None
        assert "at least 30" in bucket.note
        assert summary.adequate_buckets == 0 and "Not enough measured outcomes" in summary.verdict

    def test_an_informative_score_shows_higher_buckets_doing_better(self):
        spec = [(95.0, 0.20)] * 30 + [(85.0, 0.10)] * 30 + [(65.0, -0.05)] * 30
        summary = cal.summarise(self.outcomes(spec), min_sample=30)
        top = next(b for b in summary.buckets if b.bucket == "90-100")
        bottom = next(b for b in summary.buckets if b.bucket == "60-69")
        assert top.sample_adequate and top.win_rate == 100.0
        assert top.mean_returns["1h"] > bottom.mean_returns["1h"]
        assert summary.ordered_as_expected is True and "consistent with" in summary.verdict
        assert "not proof" in summary.verdict

    def test_a_useless_score_is_reported_as_such(self):
        spec = [(95.0, -0.20)] * 30 + [(65.0, 0.20)] * 30
        summary = cal.summarise(self.outcomes(spec), min_sample=30)
        assert summary.ordered_as_expected is False
        assert "did NOT show better" in summary.verdict and "caution" in summary.verdict

    def test_neutral_setups_are_measured_but_kept_out_of_the_aggregates(self):
        bars = rising_session()
        neutral = cal.measure(candidate(direction="NEUTRAL", as_of=bars[0].timestamp), bars, "15m")
        assert neutral is not None and neutral.directionless
        summary = cal.summarise([neutral])
        assert summary.measured == 0 and summary.directionless_excluded == 1
        assert any("Neutral setups" in c for c in summary.caveats)

    def test_unmeasurable_candidates_are_counted_not_hidden(self):
        bars = rising_session()
        late = cal.measure(candidate(as_of=ist(2026, 1, 5, 15, 15)), bars, "15m")
        assert late is not None and late.primary is None
        summary = cal.summarise([late])
        assert summary.unmeasurable == 1 and summary.measured == 0

    def test_caveats_always_state_that_costs_are_excluded(self):
        summary = cal.summarise(self.outcomes([(85.0, 0.1)] * 3))
        assert any("brokerage, taxes and slippage" in c for c in summary.caveats)
        assert any("not a prediction" in c for c in summary.caveats)

    def test_bucket_boundaries(self):
        assert cal.bucket_of(100.0) == "90-100" and cal.bucket_of(90.0) == "90-100"
        assert cal.bucket_of(89.9) == "80-89" and cal.bucket_of(50.0) == "50-59"
        assert cal.bucket_of(49.9) == "below-50" and cal.bucket_of(0.0) == "below-50"
