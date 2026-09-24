"""Risk layer.

Produces a **Risk Score from 0 to 100 where higher means more risk**, built from measured components so it can
be explained line by line. A component with no data source is not guessed: it is reported as not assessed and
excluded from the weighted average, and the coverage figure says how much of the weight could be measured.

Flags are the named reasons behind the components, so they are not added on top of the score a second time.
"""

from __future__ import annotations

from typing import Any

from app.research.contracts import (
    EvidenceItem,
    MarketContext,
    Provenance,
    RiskAssessment,
    RiskComponent,
    RiskFlag,
    RiskLevel,
    VerificationReport,
)
from app.research.features import TechnicalBundle
from app.research.scoring import clip, interpolate

NOT_CHECKED = [
    "Circuit limits and price bands",
    "ASM / GSM surveillance status",
    "Earnings and corporate-event proximity",
    "Regulatory actions and trading restrictions",
]
# Relative importance of each risk dimension. Event and corporate risk stay in the table with no data source so
# the coverage figure keeps showing what the score could not see.
RISK_WEIGHTS: dict[str, float] = {
    "liquidity": 25,
    "volatility": 20,
    "activity": 15,
    "data": 20,
    "market": 10,
    "event": 10,
}
RISK_LABELS: dict[str, str] = {
    "liquidity": "Liquidity risk",
    "volatility": "Volatility risk",
    "activity": "Unusual activity",
    "data": "Data risk",
    "market": "Market risk",
    "event": "Event and corporate risk",
}
LOW_BELOW, MEDIUM_BELOW = 30.0, 60.0
# The score is never less than this share of the worst single component.
WORST_COMPONENT_FLOOR = 0.8
SEVERE_DATA_FLOOR, STALE_DATA_FLOOR = 60.0, 40.0


def level_of(score: float | None) -> RiskLevel:
    if score is None:
        return "UNKNOWN"
    return "LOW" if score < LOW_BELOW else "MEDIUM" if score < MEDIUM_BELOW else "HIGH"


def _component(key: str, score: float | None, summary: str, evidence: list[EvidenceItem]) -> RiskComponent:
    return RiskComponent(
        key=key,
        label=RISK_LABELS[key],
        score=None if score is None else round(clip(score, 0, 100), 1),
        level=level_of(score),
        weight=RISK_WEIGHTS[key],
        summary=summary,
        evidence=evidence,
    )


def market_risk_level(market: MarketContext) -> RiskLevel:
    return level_of(_market_score(market)[0])


def _market_score(market: MarketContext) -> tuple[float | None, list[EvidenceItem]]:
    regime = market.regime
    evidence: list[EvidenceItem] = []
    if regime.label == "UNKNOWN":
        return None, [EvidenceItem(label="Market regime", value="could not be determined", passed=None)]
    # A falling market is riskier for a long setup; a rising one is riskier for a short. The regime score runs
    # -1 (bearish) to +1 (bullish), so distance below neutral is the risk contribution.
    by_regime = {
        "STRONG_BEARISH": 80.0,
        "BEARISH": 60.0,
        "RANGE": 40.0,
        "BULLISH": 25.0,
        "STRONG_BULLISH": 20.0,
    }
    score = by_regime[regime.label]
    evidence.append(
        EvidenceItem(
            label="Market regime", value=regime.label.replace("_", " ").lower(), passed=score < LOW_BELOW
        )
    )
    if regime.volatility == "HIGH":
        score += 40
        evidence.append(EvidenceItem(label="Index volatility (India VIX)", value="high", passed=False))
    elif regime.volatility == "LOW":
        score -= 5
        evidence.append(EvidenceItem(label="Index volatility (India VIX)", value="low", passed=True))
    return score, evidence


def _liquidity_score(
    bundle: TechnicalBundle, thresholds: dict[str, Any]
) -> tuple[float | None, list[EvidenceItem]]:
    p = bundle.price
    evidence: list[EvidenceItem] = []
    parts: list[tuple[float, float]] = []
    value = p.avg_traded_value_cr
    if value is not None:
        # 200 crore a day is unproblematic; 2 crore or less is severe.
        score = interpolate(value, [(0, 100), (2, 85), (10, 60), (25, 35), (75, 15), (200, 5), (1000, 0)])
        parts.append((score, 0.75))
        evidence.append(
            EvidenceItem(
                label="Average daily traded value (20 sessions)",
                value=f"₹{value:,.1f} crore",
                passed=score < LOW_BELOW,
            )
        )
    if p.spread_bps is not None:
        score = interpolate(p.spread_bps, [(0, 0), (2, 10), (10, 40), (30, 80), (60, 100)])
        parts.append((score, 0.25))
        evidence.append(
            EvidenceItem(label="Bid/ask spread", value=f"{p.spread_bps:.1f} bps", passed=score < LOW_BELOW)
        )
    else:
        evidence.append(
            EvidenceItem(label="Bid/ask spread", value="not available from this data source", passed=None)
        )
    if not parts:
        return None, evidence
    total = sum(w for _, w in parts)
    _ = thresholds
    return sum(s * w for s, w in parts) / total, evidence


def _volatility_score(bundle: TechnicalBundle) -> tuple[float | None, list[EvidenceItem]]:
    v = bundle.volatility
    if v.atr_pct is None:
        return None, [EvidenceItem(label="Daily ATR", value="not available", passed=None)]
    # Risk rises with movement. A very quiet stock is not risky, only unsuitable, which the research score judges.
    score = interpolate(v.atr_pct, [(0, 5), (1, 15), (2.5, 35), (4, 65), (6, 90), (10, 100)])
    evidence = [
        EvidenceItem(label="Daily ATR", value=f"{v.atr_pct:.2f}% of price", passed=score < LOW_BELOW),
    ]
    if v.hist_vol_pct is not None:
        evidence.append(
            EvidenceItem(
                label="Historical volatility (20d, annualised)", value=f"{v.hist_vol_pct:.1f}%", passed=None
            )
        )
    return score, evidence


def _activity_score(bundle: TechnicalBundle, thresholds: dict[str, Any]) -> tuple[float, list[EvidenceItem]]:
    """How abnormal today is. An unusual session is harder to reason about and to trade."""
    p, v = bundle.price, bundle.volatility
    parts: list[float] = []
    evidence: list[EvidenceItem] = []
    gap = abs(p.gap_pct or 0.0)
    gap_score = interpolate(gap, [(0, 0), (1, 15), (3, 50), (6, 85), (12, 100)])
    parts.append(gap_score)
    evidence.append(
        EvidenceItem(label="Opening gap", value=f"{p.gap_pct or 0:+.2f}%", passed=gap_score < LOW_BELOW)
    )
    if p.rel_volume is not None:
        rvol_score = interpolate(p.rel_volume, [(0, 20), (1, 5), (2, 20), (5, 70), (10, 100)])
        parts.append(rvol_score)
        evidence.append(
            EvidenceItem(
                label="Relative volume", value=f"{p.rel_volume:.2f}x normal", passed=rvol_score < LOW_BELOW
            )
        )
    if v.atr_pct and p.change_pct is not None:
        in_atr = abs(p.change_pct) / v.atr_pct
        move_score = interpolate(in_atr, [(0, 0), (1, 20), (2.5, 65), (5, 100)])
        parts.append(move_score)
        evidence.append(
            EvidenceItem(
                label="Day move measured in ATR",
                value=f"{in_atr:.1f}x the daily ATR",
                passed=move_score < LOW_BELOW,
            )
        )
    _ = thresholds
    return sum(parts) / len(parts), evidence


def _data_score(
    verification: VerificationReport | None, is_synthetic: bool, stale: bool, stale_message: str | None
) -> tuple[float | None, list[EvidenceItem]]:
    evidence: list[EvidenceItem] = []
    if verification is None:
        return None, [
            EvidenceItem(label="Data verification", value="not run at this research depth", passed=None)
        ]
    # Data confidence already runs 0 to 100 where higher is better, so risk is its mirror image.
    score = 100 - verification.data_confidence
    evidence.append(
        EvidenceItem(
            label="Data confidence",
            value=f"{verification.data_confidence:.0f} of 100",
            passed=score < LOW_BELOW,
        )
    )
    # Fake or self-contradictory data is a serious problem whatever the rest of the picture looks like, so these
    # set a floor rather than nudging an average that other terms could dilute.
    floors: list[float] = []
    if is_synthetic:
        floors.append(SEVERE_DATA_FLOOR)
        evidence.append(
            EvidenceItem(label="Data source", value="synthetic test data, not the real market", passed=False)
        )
    conflicts = verification.conflicts_found
    if conflicts:
        score = min(100.0, score + 15 * conflicts)
        floors.append(SEVERE_DATA_FLOOR)
        evidence.append(
            EvidenceItem(label="Conflicting sources", value=f"{conflicts} claim(s)", passed=False)
        )
    if stale:
        score = min(100.0, score + 15)
        floors.append(STALE_DATA_FLOOR)
        evidence.append(EvidenceItem(label="Freshness", value=stale_message or "data is stale", passed=False))
    return max([score, *floors]), evidence


def assess_risk(
    bundle: TechnicalBundle,
    market: MarketContext,
    thresholds: dict[str, Any],
    provenance: Provenance,
    *,
    verification: VerificationReport | None = None,
    is_synthetic: bool = False,
    stale: bool = False,
    stale_message: str | None = None,
    historical_adequate: bool | None = None,
) -> RiskAssessment:
    p, v = bundle.price, bundle.volatility
    flags: list[RiskFlag] = []
    unavailable = list(NOT_CHECKED)

    # ---- named reasons (flags) ------------------------------------------------------------------------
    value = p.avg_traded_value_cr
    if value is not None:
        if value < thresholds["flag_very_low_liquidity_cr"]:
            flags.append(
                RiskFlag(
                    code="LOW_LIQUIDITY",
                    severity="HIGH",
                    message=f"Very low liquidity: ₹{value:.1f} crore traded per day",
                    metric="avg_traded_value_cr",
                    value=value,
                )
            )
        elif value < thresholds["flag_low_liquidity_cr"]:
            flags.append(
                RiskFlag(
                    code="LOW_LIQUIDITY",
                    severity="WARNING",
                    message=f"Low liquidity: ₹{value:.1f} crore traded per day",
                    metric="avg_traded_value_cr",
                    value=value,
                )
            )
    if p.spread_bps is None:
        unavailable.append("Bid/ask spread (not provided by this data source)")
    elif p.spread_bps > thresholds["flag_wide_spread_bps"]:
        flags.append(
            RiskFlag(
                code="LARGE_SPREAD",
                severity="WARNING",
                message=f"Wide bid/ask spread of {p.spread_bps:.1f} bps",
                metric="spread_bps",
                value=p.spread_bps,
            )
        )
    if v.atr_pct is not None and v.atr_pct > thresholds["flag_extreme_atr_pct"]:
        flags.append(
            RiskFlag(
                code="EXTREME_VOLATILITY",
                severity="HIGH",
                message=f"Extreme volatility: daily ATR is {v.atr_pct:.1f}% of price",
                metric="atr_pct",
                value=v.atr_pct,
            )
        )
    gap = abs(p.gap_pct or 0.0)
    if gap > thresholds["flag_large_gap_pct"] * 2:
        flags.append(
            RiskFlag(
                code="LARGE_GAP",
                severity="HIGH",
                message=f"Very large opening gap of {p.gap_pct:+.1f}%",
                metric="gap_pct",
                value=p.gap_pct,
            )
        )
    elif gap > thresholds["flag_large_gap_pct"]:
        flags.append(
            RiskFlag(
                code="LARGE_GAP",
                severity="WARNING",
                message=f"Large opening gap of {p.gap_pct:+.1f}%",
                metric="gap_pct",
                value=p.gap_pct,
            )
        )
    if v.atr_pct and p.change_pct is not None:
        move = abs(p.change_pct) / v.atr_pct
        if move > thresholds["flag_unusual_move_atr"]:
            flags.append(
                RiskFlag(
                    code="UNUSUAL_PRICE_MOVE",
                    severity="WARNING",
                    message=f"Unusual price move: {p.change_pct:+.1f}% is {move:.1f}x the daily ATR",
                    metric="move_in_atr",
                    value=move,
                )
            )
    if p.rel_volume is not None and p.rel_volume > thresholds["flag_unusual_rvol"]:
        flags.append(
            RiskFlag(
                code="UNUSUAL_VOLUME",
                severity="WARNING",
                message=f"Unusual volume: {p.rel_volume:.1f}x the normal level for this time of day",
                metric="rel_volume",
                value=p.rel_volume,
            )
        )
    flags.extend(data_flags(verification, is_synthetic, historical_adequate, stale, stale_message))

    # ---- measured components --------------------------------------------------------------------------
    liquidity, liquidity_evidence = _liquidity_score(bundle, thresholds)
    volatility, volatility_evidence = _volatility_score(bundle)
    activity, activity_evidence = _activity_score(bundle, thresholds)
    data, data_evidence = _data_score(verification, is_synthetic, stale, stale_message)
    market_score, market_evidence = _market_score(market)
    components = [
        _component(
            "liquidity",
            liquidity,
            (
                "Can it be traded in size without moving the price?"
                if liquidity is not None
                else "Not measurable."
            ),
            liquidity_evidence,
        ),
        _component(
            "volatility",
            volatility,
            "How large are the daily swings?" if volatility is not None else "Not measurable.",
            volatility_evidence,
        ),
        _component(
            "activity", activity, "How abnormal is today compared with a normal session?", activity_evidence
        ),
        _component(
            "data",
            data,
            (
                "How much can the underlying data be trusted?"
                if data is not None
                else "Verification did not run."
            ),
            data_evidence,
        ),
        _component("market", market_score, "What is the backdrop doing?", market_evidence),
        _component(
            "event",
            None,
            "Results, corporate actions, surveillance and regulatory status are not assessed: no data source.",
            [
                EvidenceItem(label=f"Not checked: {c}", value="no data source", passed=None)
                for c in NOT_CHECKED
            ],
        ),
    ]
    assessed = [c for c in components if c.score is not None]
    weight = sum(c.weight for c in assessed)
    risk_score = None
    if weight:
        average = sum(c.score * c.weight for c in assessed) / weight  # type: ignore[operator]
        # Risk is not an average: one severe dimension is not cancelled out by calm elsewhere, so the score is
        # lifted towards the worst single component.
        worst = max(c.score for c in assessed)  # type: ignore[type-var]
        risk_score = round(max(average, worst * WORST_COMPONENT_FLOOR), 1)
    by_key = {c.key: c for c in components}
    return RiskAssessment(
        risk_score=risk_score,
        coverage_pct=round(weight / sum(RISK_WEIGHTS.values()) * 100, 1),
        components=components,
        flags=flags,
        liquidity_risk=by_key["liquidity"].level,
        volatility_risk=by_key["volatility"].level,
        activity_risk=by_key["activity"].level,
        event_risk="UNKNOWN",
        corporate_risk="UNKNOWN",
        data_risk=by_key["data"].level,
        market_risk=by_key["market"].level,
        overall=level_of(risk_score),
        unavailable_checks=unavailable,
        provenance=provenance,
    )


def data_flags(
    verification: VerificationReport | None,
    is_synthetic: bool,
    historical_adequate: bool | None,
    stale: bool,
    stale_message: str | None,
) -> list[RiskFlag]:
    """Flags that come from data quality rather than from the market itself."""
    flags: list[RiskFlag] = []
    if is_synthetic:
        flags.append(
            RiskFlag(
                code="SYNTHETIC_DATA",
                severity="WARNING",
                message="Prices and volumes are synthetic test data, not the real market",
            )
        )
    conflicts = [c for c in verification.claims if c.status == "CONFLICTING"] if verification else []
    if conflicts:
        flags.append(
            RiskFlag(
                code="CONFLICTING_DATA",
                severity="WARNING",
                message=f"{len(conflicts)} data check(s) found conflicting values",
                value=float(len(conflicts)),
            )
        )
    if stale:
        flags.append(
            RiskFlag(code="STALE_DATA", severity="WARNING", message=stale_message or "Market data is stale")
        )
    if historical_adequate is False:
        flags.append(
            RiskFlag(
                code="LOW_SAMPLE",
                severity="INFO",
                message="Historical sample of today's setup is too small to rely on",
            )
        )
    return flags


def data_risk_level(verification: VerificationReport, is_synthetic: bool, stale: bool) -> RiskLevel:
    score, _ = _data_score(verification, is_synthetic, stale, None)
    return level_of(score)
