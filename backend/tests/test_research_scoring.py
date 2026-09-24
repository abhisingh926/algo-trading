"""Scoring behaviour required by the specification: liquidity, risk, missing/conflicting/stale data, small samples."""

import dataclasses

import pytest

from app.research import risk as risk_mod
from app.research import verification as ver
from app.research.config import DEFAULT_THRESHOLDS, DEFAULT_WEIGHTS, validate_weights
from app.research.contracts import VerificationClaim
from app.research.historical import analyze
from app.research.scoring import ScoringInput, score_symbol
from tests.research_helpers import make_bundle, market_context, provenance

WEIGHTS = dict(DEFAULT_WEIGHTS)


def scoring_input(bundle, market=None, historical=None, flags=None, **overrides):  # noqa: ANN001, ANN201
    price = overrides.pop("price", bundle.price)
    changed = dataclasses.replace(
        bundle, price=price, volatility=overrides.pop("volatility", bundle.volatility)
    )
    risk = risk_mod.assess_risk(
        changed, market or market_context(), DEFAULT_THRESHOLDS, provenance(), verification=None
    )
    if flags:
        risk = risk.model_copy(update={"flags": [*risk.flags, *flags]})
    return ScoringInput(
        price=price,
        volatility=changed.volatility,
        technical=bundle.technical,
        historical=historical,
        risk=risk,
        market=market or market_context(),
        sector=None,
        source_key="candles_15m",
        thresholds=DEFAULT_THRESHOLDS,
    )


@pytest.fixture(scope="module")
def bundle():  # noqa: ANN201
    return make_bundle(sessions=90, keep_bars=14, seed=8)[1]


def component(result, key):  # noqa: ANN001, ANN201
    return next(c for c in result.components if c.key == key)


def test_weights_add_up_to_100_and_are_validated():
    assert sum(DEFAULT_WEIGHTS.values()) == 100
    assert validate_weights(DEFAULT_WEIGHTS) == []
    assert "add up to 100" in validate_weights({**DEFAULT_WEIGHTS, "liquidity": 20})[0]
    assert any("Unknown" in e for e in validate_weights({**DEFAULT_WEIGHTS, "magic": 1}))
    assert any("negative" in e for e in validate_weights({**DEFAULT_WEIGHTS, "liquidity": -5, "risk": 25}))


def test_higher_liquidity_scores_higher(bundle):
    low = score_symbol(
        scoring_input(
            bundle, price=bundle.price.model_copy(update={"avg_traded_value_cr": 2.5, "avg_volume": 150_000})
        ),
        WEIGHTS,
    )
    high = score_symbol(
        scoring_input(
            bundle,
            price=bundle.price.model_copy(update={"avg_traded_value_cr": 400.0, "avg_volume": 8_000_000}),
        ),
        WEIGHTS,
    )
    assert component(high, "liquidity").points > component(low, "liquidity").points + 8
    assert high.research_score > low.research_score


def test_extreme_risk_reduces_the_score_and_can_cap_it(bundle):
    """Risk is measured from the data, so the score falls when the data itself is severe."""
    clean = score_symbol(scoring_input(bundle), WEIGHTS)
    risky = score_symbol(
        scoring_input(
            bundle,
            volatility=bundle.volatility.model_copy(update={"atr_pct": 8.0}),
            price=bundle.price.model_copy(update={"avg_traded_value_cr": 1.0}),
        ),
        WEIGHTS,
    )
    inp_cap = float(DEFAULT_THRESHOLDS["risk_cap_score"])
    clean_risk, risky_risk = component(clean, "risk"), component(risky, "risk")
    assert risky_risk.metrics["risk_score"] > clean_risk.metrics["risk_score"] + 25
    assert risky_risk.points < clean_risk.points
    assert risky.research_score < clean.research_score
    # A high-severity flag means the score can never exceed the cap, whether or not it was already below it.
    assert risky.research_score <= inp_cap and (risky.raw_score <= inp_cap or risky.capped)


def test_missing_components_lower_coverage_and_are_not_scored_as_zero(bundle):
    result = score_symbol(scoring_input(bundle, historical=None), WEIGHTS)
    news, historical = component(result, "news_catalyst"), component(result, "historical_setup")
    assert not news.available and news.points == 0 and news.rating == "UNAVAILABLE"
    assert not historical.available
    assert result.coverage_pct == 85.0 and result.available_points == 85
    # normalising over what could be assessed: the score is earned/available, so 'not assessed' is not a penalty
    earned = sum(c.points for c in result.components if c.available)
    assert result.research_score == pytest.approx(earned / 85 * 100, abs=0.1)


def test_weights_are_configurable_and_change_the_outcome(bundle):
    base = score_symbol(scoring_input(bundle), WEIGHTS)
    liquidity_heavy = {
        **WEIGHTS,
        "liquidity": 50,
        "price_action": 5,
        "momentum": 5,
        "volume": 5,
        "technical_setup": 5,
        "market_regime": 0,
    }
    assert validate_weights(liquidity_heavy) == []
    other = score_symbol(scoring_input(bundle), liquidity_heavy)
    assert (
        other.total_points == 100
        and component(other, "liquidity").max_points == 50
        and other.research_score != base.research_score
    )


def test_market_regime_alignment_affects_the_score(bundle):
    bullish = score_symbol(scoring_input(bundle, market=market_context(nifty_up=True)), WEIGHTS)
    bearish = score_symbol(scoring_input(bundle, market=market_context(nifty_up=False)), WEIGHTS)
    a, b = component(bullish, "market_regime"), component(bearish, "market_regime")
    assert a.available and b.available and a.points != b.points


def test_insufficient_historical_sample_is_unscored_with_a_warning(bundle):
    history = analyze(bundle.sessions, provenance(), min_sample=100_000)
    result = score_symbol(scoring_input(bundle, historical=history), WEIGHTS)
    comp = component(result, "historical_setup")
    assert not comp.available and "no historical edge is claimed" in comp.summary
    assert any("no historical edge is claimed" in w for w in history.warnings)
    flags = risk_mod.data_flags(
        ver.finalize([], 0.9, 1.0, 1.0, False, False, provenance()), False, False, False, None
    )
    assert any(f.code == "LOW_SAMPLE" for f in flags)


def test_evidence_marks_follow_the_subscores(bundle):
    result = score_symbol(scoring_input(bundle), WEIGHTS)
    for comp in result.components:
        for item in comp.evidence:
            assert item.passed in (True, False, None)
    volatility = component(result, "volatility")
    atr_item = next(e for e in volatility.evidence if e.label == "Daily ATR")
    assert (atr_item.passed is True) == (
        volatility.points / volatility.max_points > 0.6
    ) or atr_item.passed is None


def test_setup_quality_labels_follow_the_configured_thresholds(bundle):
    result = score_symbol(scoring_input(bundle), WEIGHTS)
    assert result.setup_quality in ("STRONG", "MODERATE", "WEAK")
    strict = dataclasses.replace(
        scoring_input(bundle), thresholds={**DEFAULT_THRESHOLDS, "setup_strong": 99.0, "setup_moderate": 98.0}
    )
    assert score_symbol(strict, WEIGHTS).setup_quality == "WEAK"


class TestDataConfidence:
    """Research Score and Data Confidence are separate: missing, conflicting or synthetic data lowers confidence only."""

    def claims(self, status):  # noqa: ANN001, ANN201
        return [
            VerificationClaim(
                key="price",
                claim="Current price",
                status=status,
                confidence=0.5,
                sources_checked=2,
                independent_origins=1,
                values=[],
                detail="",
            )
        ]

    def confidence(
        self, claims, completeness=1.0, synthetic=False, freshness=1.0, sample=True, reliability=0.9
    ):  # noqa: ANN001, ANN201
        return ver.finalize(
            claims, reliability, freshness, completeness, sample, synthetic, provenance()
        ).data_confidence

    def test_missing_data_lowers_confidence(self):
        assert self.confidence(self.claims("PARTIALLY_VERIFIED"), completeness=0.6) < self.confidence(
            self.claims("PARTIALLY_VERIFIED"), completeness=1.0
        )

    def test_conflicting_data_lowers_confidence(self):
        assert (
            self.confidence(self.claims("CONFLICTING"))
            < self.confidence(self.claims("PARTIALLY_VERIFIED")) - 5
        )

    def test_stale_data_lowers_confidence_and_warns(self):
        assert self.confidence(self.claims("PARTIALLY_VERIFIED"), freshness=0.2) < self.confidence(
            self.claims("PARTIALLY_VERIFIED")
        )
        score, stale, message = ver.freshness(
            provenance().retrieved_at,
            provenance().retrieved_at - __import__("datetime").timedelta(minutes=50),
            "OPEN",
        )
        assert stale and score < 1 and "50 minutes old" in message

    def test_small_sample_lowers_confidence(self):
        assert self.confidence(self.claims("PARTIALLY_VERIFIED"), sample=False) < self.confidence(
            self.claims("PARTIALLY_VERIFIED")
        )

    def test_synthetic_data_is_capped_low_whatever_else_is_perfect(self):
        report = ver.finalize(self.claims("VERIFIED"), 1.0, 1.0, 1.0, True, True, provenance())
        assert (
            report.data_confidence == ver.SYNTHETIC_CONFIDENCE_CAP and report.breakdown.synthetic_cap_applied
        )

    def test_data_flags_for_conflicts_synthetic_and_stale(self):
        report = ver.finalize(self.claims("CONFLICTING"), 0.9, 1.0, 1.0, True, False, provenance())
        codes = {f.code for f in risk_mod.data_flags(report, True, True, True, "Data is 50 minutes old")}
        assert codes == {"CONFLICTING_DATA", "SYNTHETIC_DATA", "STALE_DATA"}
        assert risk_mod.data_risk_level(report, False, False) == "HIGH"
