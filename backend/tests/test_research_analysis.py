"""Verification, risk, market regime, scanner and score-change explanations."""

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.types import Candle
from app.research import market as mkt
from app.research import risk as risk_mod
from app.research import scanner
from app.research import verification as ver
from app.research.config import DEFAULT_THRESHOLDS
from app.research.contracts import Breadth, IndexSnapshot, VerificationClaim
from app.research.explain import explain_change
from tests.research_helpers import ist, make_bundle, make_history, market_context, provenance

NOW = datetime(2026, 1, 20, 6, 30, tzinfo=UTC)


def obs(value, origin="dhan", reliability=0.9, age_minutes=1.0):  # noqa: ANN001, ANN201
    return ver.Observation(f"{origin} feed", origin, value, NOW - timedelta(minutes=age_minutes), reliability)


class TestVerification:
    def test_no_observation_is_unverified_with_zero_confidence(self):
        claim = ver.verify_numeric("price", "Price", [], 0.5, NOW)
        assert claim.status == "UNVERIFIED" and claim.confidence == 0 and claim.sources_checked == 0

    def test_single_source_cannot_be_cross_checked(self):
        claim = ver.verify_numeric("price", "Price", [obs(100.0)], 0.5, NOW)
        assert claim.status == "UNVERIFIED" and "one source" in claim.detail

    def test_two_feeds_from_one_provider_are_not_independent(self):
        claim = ver.verify_numeric("price", "Price", [obs(100.0), obs(100.1)], 0.5, NOW)
        assert (
            claim.status == "PARTIALLY_VERIFIED"
            and claim.independent_origins == 1
            and claim.sources_checked == 2
        )
        assert claim.confidence == pytest.approx(0.9 * 0.6)
        assert "single provider" in claim.detail

    def test_two_independent_origins_that_agree_are_verified(self):
        claim = ver.verify_numeric("price", "Price", [obs(100.0, "dhan"), obs(100.2, "zerodha")], 0.5, NOW)
        assert claim.status == "VERIFIED" and claim.independent_origins == 2
        assert claim.confidence == pytest.approx(1 - (1 - 0.81) ** 2, abs=0.01)

    def test_conflicts_are_reported_never_resolved_silently(self):
        claim = ver.verify_numeric(
            "revenue", "Revenue", [obs(10_000.0, "nse"), obs(9_800.0, "reuters")], 0.5, NOW
        )
        assert (
            claim.status == "CONFLICTING"
            and claim.resolution == "Awaiting verification. No value was chosen."
        )
        assert {v.value for v in claim.values} == {10_000.0, 9_800.0} and claim.confidence < 0.3
        assert "differ by 2.02%" in claim.detail

    def test_stale_when_every_source_is_old(self):
        claim = ver.verify_numeric(
            "price",
            "Price",
            [obs(100.0, age_minutes=90), obs(100.0, "zerodha", age_minutes=80)],
            0.5,
            NOW,
            max_age_minutes=60,
        )
        assert claim.status == "STALE"

    def test_integrity_check_finds_bad_bars(self):
        bars = make_history(30, seed=2)
        good = ver.verify_integrity(bars, "dhan", 0.9)
        assert good.status == "PARTIALLY_VERIFIED" and "consistency check on one source" in good.detail
        broken = list(bars)
        broken[5] = Candle(broken[5].timestamp, 100, 90, 110, 100, 10)  # high below low
        broken.append(broken[7])  # duplicated timestamp
        bad = ver.verify_integrity(broken, "dhan", 0.9)
        assert bad.status == "CONFLICTING" and "inconsistent" in bad.detail and "duplicated" in bad.detail

    def test_missing_bars_in_recent_sessions_are_detected(self):
        bars = make_history(30, seed=2)
        day = bars[100].timestamp.astimezone(ist(2026, 1, 1).tzinfo).date()
        gapped = [
            b
            for b in bars
            if not (
                b.timestamp.astimezone(ist(2026, 1, 1).tzinfo).date()
                == bars[-60].timestamp.astimezone(ist(2026, 1, 1).tzinfo).date()
                and b.timestamp.minute == 15
            )
        ]
        assert any("missing bars" in i for i in ver.integrity_issues(gapped)) and day

    def test_freshness_rules(self):
        as_of = ist(2026, 1, 20, 11, 0)
        assert ver.freshness(as_of, as_of - timedelta(minutes=10), "OPEN") == (1.0, False, None)
        score, stale, message = ver.freshness(as_of, as_of - timedelta(minutes=45), "OPEN")
        assert stale and score == 0.6 and "45 minutes old" in message
        # market closed on Tuesday evening: data from that day is fresh, data from last Friday is not
        evening = ist(2026, 1, 20, 18, 0)
        assert ver.freshness(evening, ist(2026, 1, 20, 15, 30), "POST_MARKET")[1] is False
        stale_score, stale_flag, msg = ver.freshness(evening, ist(2026, 1, 16, 15, 30), "POST_MARKET")
        assert stale_flag and stale_score < 1 and "behind" in msg

    def test_expected_last_session_skips_weekends(self):
        assert (
            ver.expected_last_session(ist(2026, 1, 5, 8, 0)).isoformat() == "2026-01-02"
        )  # Monday before the open -> Friday
        assert ver.expected_last_session(ist(2026, 1, 3, 12, 0)).isoformat() == "2026-01-02"  # Saturday
        assert ver.expected_last_session(ist(2026, 1, 6, 10, 0)).isoformat() == "2026-01-06"


class TestRisk:
    @pytest.fixture(scope="class")
    def bundle(self):  # noqa: ANN201
        return make_bundle(sessions=90, keep_bars=14, seed=8)[1]

    def assess(self, bundle, **price_changes):  # noqa: ANN001, ANN201
        changed = dataclasses.replace(bundle, price=bundle.price.model_copy(update=price_changes))
        return risk_mod.assess_risk(changed, market_context(), DEFAULT_THRESHOLDS, provenance())

    def codes(self, risk):  # noqa: ANN001, ANN201
        return {(f.code, f.severity) for f in risk.flags}

    def test_liquidity_flags(self, bundle):
        assert ("LOW_LIQUIDITY", "HIGH") in self.codes(self.assess(bundle, avg_traded_value_cr=1.0))
        assert ("LOW_LIQUIDITY", "WARNING") in self.codes(self.assess(bundle, avg_traded_value_cr=6.0))
        assert not any(
            c == "LOW_LIQUIDITY" for c, _ in self.codes(self.assess(bundle, avg_traded_value_cr=90.0))
        )
        assert self.assess(bundle, avg_traded_value_cr=90.0).liquidity_risk == "LOW"

    def test_spread_gap_and_unusual_activity(self, bundle):
        assert ("LARGE_SPREAD", "WARNING") in self.codes(self.assess(bundle, spread_bps=45.0))
        assert ("LARGE_GAP", "HIGH") in self.codes(self.assess(bundle, gap_pct=7.5))
        assert ("LARGE_GAP", "WARNING") in self.codes(self.assess(bundle, gap_pct=-4.0))
        assert ("UNUSUAL_VOLUME", "WARNING") in self.codes(self.assess(bundle, rel_volume=6.0))
        assert any(c == "UNUSUAL_PRICE_MOVE" for c, _ in self.codes(self.assess(bundle, change_pct=15.0)))

    def test_extreme_volatility_is_a_high_flag(self, bundle):
        changed = dataclasses.replace(
            bundle, volatility=bundle.volatility.model_copy(update={"atr_pct": 7.0})
        )
        risk = risk_mod.assess_risk(changed, market_context(), DEFAULT_THRESHOLDS, provenance())
        assert (
            ("EXTREME_VOLATILITY", "HIGH") in self.codes(risk)
            and risk.overall == "HIGH"
            and risk.volatility_risk == "HIGH"
        )

    def test_checks_without_a_data_source_are_listed_not_guessed(self, bundle):
        risk = self.assess(bundle)
        text = " ".join(risk.unavailable_checks).lower()
        assert "asm" in text and "circuit" in text and "earnings" in text and "spread" in text
        assert risk.event_risk == "UNKNOWN" and risk.corporate_risk == "UNKNOWN"
        assert "Not checked" not in " ".join(f.message for f in risk.flags)

    def test_market_risk_follows_the_regime(self, bundle):
        assert risk_mod.market_risk_level(market_context(nifty_up=True)) == "LOW"
        assert risk_mod.market_risk_level(market_context(nifty_up=False)) in ("MEDIUM", "HIGH")
        assert risk_mod.market_risk_level(market_context(vix=30)) == "HIGH"


def index(symbol, price, ema20, ema50, change=0.5, ret_5d=1.0):  # noqa: ANN001, ANN201
    return IndexSnapshot(
        symbol=symbol,
        name=symbol,
        available=True,
        price=price,
        ema20=ema20,
        ema50=ema50,
        change_pct=change,
        ret_5d_pct=ret_5d,
        trend="UP",
    )


class TestMarketRegime:
    def test_bullish_factors_and_explained_label(self):
        regime = mkt.compute_regime(
            index("NIFTY", 105, 100, 98, 0.8),
            index("BANKNIFTY", 55, 52, 50),
            13.0,
            Breadth(advances=35, declines=15, unchanged=0, universe_size=50, pct_above_ema20=70),
        )
        assert (
            regime.label in ("BULLISH", "STRONG_BULLISH")
            and regime.volatility == "NORMAL"
            and regime.confidence > 0.5
        )
        names = [f.name for f in regime.factors]
        assert (
            "NIFTY vs 20-day EMA" in names and "India VIX" in names and all(f.detail for f in regime.factors)
        )

    def test_bearish_and_range(self):
        bearish = mkt.compute_regime(
            index("NIFTY", 90, 100, 102, -1.0),
            None,
            22.0,
            Breadth(advances=10, declines=40, unchanged=0, universe_size=50, pct_above_ema20=20),
        )
        assert bearish.label in ("BEARISH", "STRONG_BEARISH") and bearish.volatility == "HIGH"
        # two supportive factors (above the 20-day EMA, BANK NIFTY above its EMA) against two negative ones: balanced
        mixed = mkt.compute_regime(
            index("NIFTY", 101, 100, 102, 0.0),
            index("BANKNIFTY", 55, 52, 50),
            15.0,
            Breadth(advances=25, declines=25, unchanged=0, universe_size=50, pct_above_ema20=50),
        )
        assert mixed.label == "RANGE"

    def test_unknown_without_data_is_not_guessed(self):
        regime = mkt.compute_regime(None, None, None, None)
        assert regime.label == "UNKNOWN" and regime.confidence == 0

    def test_vix_bands(self):
        assert mkt.compute_regime(index("NIFTY", 101, 100, 99), None, 11.0, None).volatility == "LOW"
        assert mkt.compute_regime(index("NIFTY", 101, 100, 99), None, 25.0, None).volatility == "HIGH"

    def test_breadth_counts(self):
        pts = [
            mkt.StockPoint(str(i), "IT", c, None, None, None, v, e)
            for i, (c, v, e) in enumerate(
                [(1.0, True, True), (-1.0, False, False), (0.0, None, None), (2.0, True, False)]
            )
        ]
        breadth = mkt.compute_breadth(pts)
        assert (breadth.advances, breadth.declines, breadth.unchanged, breadth.universe_size) == (2, 1, 1, 4)
        assert breadth.pct_above_vwap == pytest.approx(66.7, abs=0.1) and "scanned universe" in breadth.note

    def test_sector_rotation_ranks_by_relative_strength(self):
        pts = [
            mkt.StockPoint("A", "IT", 2.0, 4.0, 1.8, 62, True, True),
            mkt.StockPoint("B", "IT", 1.0, 3.0, 1.4, 58, True, True),
            mkt.StockPoint("C", "Banking", -1.0, -2.0, 0.9, 40, False, False),
            mkt.StockPoint("D", "Banking", -0.5, -1.0, 1.0, 42, False, False),
        ]
        sectors = mkt.compute_sectors(pts, index("NIFTY", 100, 99, 98, change=0.2, ret_5d=0.5))
        assert [s.sector for s in sectors] == ["IT", "Banking"] and [s.rank for s in sectors] == [1, 2]
        it = sectors[0]
        assert (
            it.rel_strength_1d == pytest.approx(1.3)
            and it.trend == "UP"
            and sectors[1].trend == "DOWN"
            and it.breadth_pct == 100
        )

    def test_state_note_is_honest_about_closed_markets(self):
        assert "not live" in mkt.state_note("POST_MARKET", "2026-01-20")
        assert "latest completed bar" in mkt.state_note("OPEN", "2026-01-20")


class TestScanner:
    @pytest.fixture(scope="class")
    def bundle(self):  # noqa: ANN201
        return make_bundle(sessions=90, keep_bars=14, seed=8)[1]

    def test_prefilter_excludes_illiquid_and_penny_stocks(self, bundle):
        thin = dataclasses.replace(bundle, price=bundle.price.model_copy(update={"avg_traded_value_cr": 0.4}))
        assert "below the ₹2 crore minimum" in scanner.prefilter(thin, DEFAULT_THRESHOLDS)
        penny = dataclasses.replace(bundle, price=bundle.price.model_copy(update={"price": 8.0}))
        assert "minimum" in scanner.prefilter(penny, DEFAULT_THRESHOLDS)
        assert scanner.prefilter(bundle, DEFAULT_THRESHOLDS) is None

    def test_initial_score_is_bounded_and_carries_reasons(self, bundle):
        boosted = dataclasses.replace(bundle, price=bundle.price.model_copy(update={"rel_volume": 3.2}))
        candidate = scanner.scan("TEST", "Test Co", "IT", boosted, None)
        assert 0 <= candidate.initial_score <= 100
        assert any("Relative volume 3.2x" in r for r in candidate.reasons)
        quiet = scanner.scan(
            "TEST",
            "Test Co",
            "IT",
            dataclasses.replace(bundle, price=bundle.price.model_copy(update={"rel_volume": 0.6})),
            None,
        )
        assert candidate.initial_score > quiet.initial_score


def report_dict(  # noqa: ANN201
    score,
    rvol,
    vwap,
    regime,
    flags,
    confidence=60.0,
    volume_points=8.0,
    atr=2.0,
    weights=1,
    coverage=90.0,
    volume_max=10.0,
    historical=None,  # noqa: ANN001
):
    return {
        "as_of": "2026-01-20T06:30:00Z",
        "research_score": score,
        "direction": "BULLISH",
        "data_confidence": confidence,
        "score_coverage_pct": coverage,
        "price": {"rel_volume": rvol},
        "technical": {"levels": {"vwap_position": vwap}},
        "market_context": {"regime": {"label": regime}},
        "sector_context": {"rel_strength_1d": 0.8},
        "volatility": {"atr_pct": atr},
        "risk": {"flags": [{"code": c} for c in flags]},
        "historical": historical,
        "score": {
            "weight_set_version": weights,
            "components": [
                {
                    "key": "volume",
                    "label": "Volume",
                    "points": volume_points,
                    "max_points": volume_max,
                    "available": True,
                },
                {"key": "risk", "label": "Risk", "points": 5.0, "max_points": 5.0, "available": True},
            ],
        },
    }


class TestScoreChangeExplanation:
    def test_reasons_come_from_measured_differences(self):
        prev = report_dict(84.0, 2.3, "ABOVE", "BULLISH", [], volume_points=9.0)
        curr = report_dict(
            67.0, 1.1, "BELOW", "RANGE", ["LARGE_GAP"], confidence=40.0, volume_points=4.0, atr=3.5
        )
        change = explain_change(prev, curr, "run-a", "run-b")
        assert change.delta == -17.0 and change.from_score == 84.0 and change.to_score == 67.0
        text = " | ".join(change.reasons)
        assert (
            "Relative volume fell from 2.3x to 1.1x" in text
            and "Price lost VWAP" in text
            and "Market regime changed from bullish to range" in text
        )
        assert (
            "New risk flag: large gap" in text
            and "Data confidence fell" in text
            and "Volatility increased" in text
        )
        assert change.component_changes[0].key == "volume" and change.component_changes[0].delta == -5.0

    def test_no_change_is_stated_plainly(self):
        same = report_dict(70.0, 1.5, "ABOVE", "BULLISH", [])
        change = explain_change(same, same, "a", "b")
        assert change.delta == 0 and change.reasons == ["No material change in the underlying measurements"]

    def test_a_change_of_weights_is_named_and_not_mistaken_for_a_market_change(self):
        prev = report_dict(70.0, 1.5, "ABOVE", "BULLISH", [], volume_points=5.0, volume_max=10.0)
        curr = report_dict(
            74.0, 1.5, "ABOVE", "BULLISH", [], volume_points=10.0, volume_max=20.0, weights=2
        )  # same 50% share, doubled weight
        change = explain_change(prev, curr, "a", "b")
        assert change.reasons[0] == "Scoring weights changed from version 1 to version 2"
        assert change.component_changes == []  # like for like, nothing moved

    def test_depth_and_coverage_differences_are_explained(self):
        prev = report_dict(80.0, 1.5, "ABOVE", "BULLISH", [], historical={"matched": {"key": "SETUP_EXACT"}})
        curr = report_dict(83.0, 1.5, "ABOVE", "BULLISH", [], coverage=85.0, historical=None)
        text = " | ".join(explain_change(prev, curr, "a", "b").reasons)
        assert "not run in this scan" in text and "covers 85% of the scoring weights (it covered 90%)" in text
        assert "no longer large enough" not in text

    def test_a_small_sample_is_only_blamed_when_statistics_actually_ran(self):
        prev = report_dict(80.0, 1.5, "ABOVE", "BULLISH", [], historical={"matched": {"key": "SETUP_EXACT"}})
        curr = report_dict(78.0, 1.5, "ABOVE", "BULLISH", [], historical={"matched": None})
        assert "no longer large enough" in " | ".join(explain_change(prev, curr, "a", "b").reasons)

    def test_falls_back_to_component_changes(self):
        prev = report_dict(70.0, 1.5, "ABOVE", "BULLISH", [], volume_points=8.0)
        curr = report_dict(74.0, 1.5, "ABOVE", "BULLISH", [], volume_points=5.0)
        change = explain_change(prev, curr, "a", "b")
        assert change.reasons == ["Volume fell by 3.0 points"]


class TestRiskScore:
    """The Risk Score is a third number from 0 to 100 where HIGHER MEANS MORE RISK."""

    @pytest.fixture(scope="class")
    def bundle(self):  # noqa: ANN201
        return make_bundle(sessions=90, keep_bars=14, seed=8)[1]

    def assess(self, bundle, market=None, **kwargs):  # noqa: ANN001, ANN201
        return risk_mod.assess_risk(
            bundle, market or market_context(), DEFAULT_THRESHOLDS, provenance(), **kwargs
        )

    def test_direction_is_stated_and_the_score_is_bounded(self, bundle):
        risk = self.assess(bundle)
        assert "higher means more risk" in risk.risk_direction.lower()
        assert 0 <= risk.risk_score <= 100
        assert risk.overall == risk_mod.level_of(risk.risk_score)

    def test_components_carry_weights_evidence_and_coverage(self, bundle):
        risk = self.assess(bundle)
        keys = {c.key for c in risk.components}
        assert keys == set(risk_mod.RISK_WEIGHTS)
        assert sum(risk_mod.RISK_WEIGHTS.values()) == 100
        assert all(c.evidence for c in risk.components)
        # event and corporate risk have no data source, so they are excluded and coverage says so
        event = next(c for c in risk.components if c.key == "event")
        assert event.score is None and event.level == "UNKNOWN" and "no data source" in event.summary
        # verification did not run here either, so data is unassessed too: 100 - event(10) - data(20)
        assert risk.coverage_pct == 70.0 and risk.event_risk == "UNKNOWN"
        with_data = self.assess(
            bundle, verification=ver.finalize([], 0.9, 1.0, 1.0, True, False, provenance())
        )
        assert with_data.coverage_pct == 90.0

    def test_worse_data_raises_the_score(self, bundle):
        calm = self.assess(bundle)
        illiquid = (
            self.assess(bundle, market=None)
            if False
            else self.assess(
                dataclasses.replace(
                    bundle, price=bundle.price.model_copy(update={"avg_traded_value_cr": 0.8})
                )
            )
        )
        volatile = self.assess(
            dataclasses.replace(bundle, volatility=bundle.volatility.model_copy(update={"atr_pct": 9.0}))
        )
        assert illiquid.risk_score > calm.risk_score and illiquid.liquidity_risk == "HIGH"
        assert volatile.risk_score > calm.risk_score and volatile.volatility_risk == "HIGH"

    def test_one_severe_dimension_is_not_averaged_away(self, bundle):
        """A stock that cannot be traded is risky even when everything else looks calm."""
        illiquid = self.assess(
            dataclasses.replace(bundle, price=bundle.price.model_copy(update={"avg_traded_value_cr": 0.5}))
        )
        worst = max(c.score for c in illiquid.components if c.score is not None)
        assert illiquid.risk_score >= worst * risk_mod.WORST_COMPONENT_FLOOR
        assert illiquid.overall == "HIGH"

    def test_synthetic_and_conflicting_data_floor_the_data_component(self, bundle):
        clean = ver.finalize([], 0.9, 1.0, 1.0, True, False, provenance())
        synthetic = ver.finalize([], 0.1, 1.0, 1.0, True, True, provenance())
        conflicting = ver.finalize(
            [
                VerificationClaim(
                    key="price",
                    claim="Current price",
                    status="CONFLICTING",
                    confidence=0.3,
                    sources_checked=2,
                    independent_origins=2,
                    values=[],
                    detail="",
                )
            ],
            0.9,
            1.0,
            1.0,
            True,
            False,
            provenance(),
        )
        good = self.assess(bundle, verification=clean).components
        fake = self.assess(bundle, verification=synthetic, is_synthetic=True).components
        clashing = self.assess(bundle, verification=conflicting).components
        score_of = lambda comps: next(c.score for c in comps if c.key == "data")  # noqa: E731
        assert score_of(good) < risk_mod.SEVERE_DATA_FLOOR
        assert score_of(fake) >= risk_mod.SEVERE_DATA_FLOOR
        assert score_of(clashing) >= risk_mod.SEVERE_DATA_FLOOR

    def test_stale_data_raises_the_data_component(self, bundle):
        report = ver.finalize([], 0.9, 0.2, 1.0, True, False, provenance())
        fresh = self.assess(bundle, verification=report).components
        stale = self.assess(
            bundle, verification=report, stale=True, stale_message="50 minutes old"
        ).components
        score_of = lambda comps: next(c.score for c in comps if c.key == "data")  # noqa: E731
        assert score_of(stale) > score_of(fresh)

    def test_verification_not_run_means_data_risk_is_not_guessed(self, bundle):
        risk = self.assess(bundle, verification=None)
        data = next(c for c in risk.components if c.key == "data")
        assert data.score is None and risk.data_risk == "UNKNOWN" and risk.coverage_pct == 70.0

    def test_the_research_score_risk_component_mirrors_the_risk_score(self, bundle):
        from app.research.config import DEFAULT_WEIGHTS
        from app.research.scoring import ScoringInput, score_symbol

        risk = self.assess(bundle)
        result = score_symbol(
            ScoringInput(
                price=bundle.price,
                volatility=bundle.volatility,
                technical=bundle.technical,
                historical=None,
                risk=risk,
                market=market_context(),
                sector=None,
                source_key="candles_15m",
                thresholds=DEFAULT_THRESHOLDS,
            ),
            DEFAULT_WEIGHTS,
        )
        component = next(c for c in result.components if c.key == "risk")
        assert component.metrics["risk_score"] == risk.risk_score
        assert component.points == pytest.approx(component.max_points * (1 - risk.risk_score / 100), abs=0.01)
