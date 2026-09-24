"""Builds the research report from the agents' structured outputs. It only re-arranges measured facts:
every sentence below is generated from a number or a flag that an earlier stage produced."""

from __future__ import annotations

from datetime import datetime

from app.research.config import COMPONENT_LABELS
from app.research.contracts import (
    AGENT_LABELS,
    UNAVAILABLE_AGENTS,
    AgentOutput,
    AgentTrace,
    HistoricalAnalysis,
    MarketContext,
    ReportOverview,
    ResearchReport,
    ResearchWarning,
    RiskAssessment,
    RiskFlag,
    ScannerCandidate,
    ScoreResult,
    SectorSnapshot,
    SourceRef,
    VerificationReport,
)
from app.research.features import TechnicalBundle

NOT_ASSESSED_ALWAYS = [
    "News and catalysts",
    "Corporate announcements, results calendar and corporate actions",
    "Fundamentals, valuation and shareholding",
    "Institutional (FII/DII) activity",
    "Global markets, currencies and commodities",
]
_RATING_TEXT = {
    "EXCELLENT": "Excellent",
    "GOOD": "Good",
    "FAIR": "Fair",
    "POOR": "Poor",
    "UNAVAILABLE": "Not assessed",
}
_SEVERITY = {"HIGH": "HIGH", "WARNING": "WARNING", "INFO": "INFO"}


def _component(score: ScoreResult, key: str):  # noqa: ANN202
    return next(c for c in score.components if c.key == key)


def build_labels(
    score: ScoreResult,
    bundle: TechnicalBundle,
    historical: HistoricalAnalysis | None,
    market: MarketContext,
    sector: SectorSnapshot | None,
    risk_level: str,
) -> dict[str, str]:
    def fraction(key: str) -> float:
        c = _component(score, key)
        return c.points / c.max_points if c.available and c.max_points else 0.0

    p, v = bundle.price, bundle.volatility
    momentum = _component(score, "momentum")
    frac = fraction("momentum")
    matched = historical.matched if historical else None
    hist_label = "Not assessed"
    if historical is not None:
        hist_label = (
            "Insufficient sample"
            if matched is None
            else (
                "Favorable"
                if fraction("historical_setup") >= 0.6
                else "Neutral" if fraction("historical_setup") >= 0.4 else "Unfavorable"
            )
        )
    atr = v.atr_pct
    vol_label = (
        "Unknown" if atr is None else "Too low" if atr < 0.8 else "Suitable" if atr <= 3.0 else "Too high"
    )
    sector_label = "Not available"
    if sector and sector.rel_strength_1d is not None:
        sector_label = (
            "Positive"
            if sector.rel_strength_1d > 0.3
            else "Negative" if sector.rel_strength_1d < -0.3 else "Neutral"
        )
    return {
        "intraday_setup": {"STRONG": "Strong", "MODERATE": "Moderate", "WEAK": "Weak", "UNKNOWN": "Unknown"}[
            score.setup_quality
        ],
        "market_regime": market.regime.label.replace("_", " ").title(),
        "sector": sector_label,
        "liquidity": _RATING_TEXT[_component(score, "liquidity").rating],
        "momentum": (
            ("Strong" if frac >= 0.7 else "Moderate" if frac >= 0.45 else "Weak")
            if momentum.available
            else "Not assessed"
        ),
        "volume": f"{p.rel_volume:.1f}x average" if p.rel_volume is not None else "Unknown",
        "volatility": vol_label,
        "news_catalyst": "Not assessed",
        "technical_structure": _RATING_TEXT[_component(score, "technical_setup").rating],
        "historical_setup": hist_label,
        "risk": risk_level.title(),
    }


def build_why(
    candidate: ScannerCandidate | None, score: ScoreResult, historical: HistoricalAnalysis | None
) -> list[str]:
    lines: list[str] = []
    strong = sorted(
        (c for c in score.components if c.available and c.rating in ("EXCELLENT", "GOOD")),
        key=lambda c: -c.points,
    )
    for comp in strong:
        passed = [e for e in comp.evidence if e.passed is True]
        if passed:
            lines.append(f"{comp.label}: " + "; ".join(f"{e.label} {e.value}" for e in passed[:2]) + ".")
    if historical and historical.matched and historical.matched.success_rate is not None:
        m = historical.matched
        lines.append(
            f"In {m.occurrences} similar past sessions ({m.period_start} to {m.period_end}) the setup was followed by a gain {m.success_rate:.0f}% of the time over the next hour; the average result after costs was {m.avg_return_net_pct:+.2f}%."
        )
    if not lines and candidate:
        lines = [f"{r}." for r in candidate.reasons[:4]]
    return lines[:6] or ["No component scored well enough to list as a strength."]


def build_risks(flags: list[RiskFlag], score: ScoreResult, unavailable_checks: list[str]) -> list[str]:
    risks = [f.message + "." for f in flags]
    for comp in score.components:
        if comp.available and comp.rating == "POOR":
            failed = [e for e in comp.evidence if e.passed is False]
            if failed:
                risks.append(
                    f"{comp.label} is weak: " + "; ".join(f"{e.label} {e.value}" for e in failed[:2]) + "."
                )
    if unavailable_checks:
        risks.append(
            "Not checked (no data source): " + "; ".join(c.lower() for c in unavailable_checks[:4]) + "."
        )
    return risks or ["No specific risk flags were raised by the checks that could be run."]


def build_invalidation(bundle: TechnicalBundle, market: MarketContext) -> list[str]:
    tech = bundle.technical
    lv = tech.levels
    lines: list[str] = []
    if tech.direction == "BULLISH":
        if lv.vwap:
            lines.append(f"Price closes back below VWAP (₹{lv.vwap:,.2f}).")
        floor = lv.opening_range_30_low or lv.prev_day_low
        if floor:
            lines.append(
                f"Price falls below the {'opening-range low' if lv.opening_range_30_low else 'prior-day low'} (₹{floor:,.2f})."
            )
        if lv.support:
            lines.append(f"The nearest support at ₹{lv.support[0]:,.2f} fails.")
        lines.append("Relative volume fades below 1.0x, so the move loses participation.")
        lines.append("The market regime turns bearish (for example NIFTY closing below its 20-day EMA).")
    elif tech.direction == "BEARISH":
        if lv.vwap:
            lines.append(f"Price closes back above VWAP (₹{lv.vwap:,.2f}).")
        ceiling = lv.opening_range_30_high or lv.prev_day_high
        if ceiling:
            lines.append(
                f"Price rises above the {'opening-range high' if lv.opening_range_30_high else 'prior-day high'} (₹{ceiling:,.2f})."
            )
        if lv.resistance:
            lines.append(f"The nearest resistance at ₹{lv.resistance[0]:,.2f} is reclaimed.")
        lines.append("Relative volume fades below 1.0x, so the move loses participation.")
        lines.append("The market regime turns bullish.")
    else:
        lines.append("There is no directional setup to invalidate: signals disagree.")
        if lv.resistance and lv.support:
            lines.append(
                f"A close above ₹{lv.resistance[0]:,.2f} or below ₹{lv.support[0]:,.2f}, with rising volume, would resolve the neutral picture."
            )
    return lines


def build_warnings(
    symbol: str,
    flags: list[RiskFlag],
    market: MarketContext,
    score: ScoreResult,
    verification: VerificationReport,
) -> list[ResearchWarning]:
    warnings = [
        ResearchWarning(code=f.code, severity=_SEVERITY[f.severity], message=f.message, symbol=symbol)
        for f in flags
    ]
    if market.market_state != "OPEN":
        warnings.append(
            ResearchWarning(
                code="MARKET_CLOSED", severity="INFO", message=market.market_state_note, symbol=symbol
            )
        )
    if score.capped and score.cap_reason:
        warnings.append(
            ResearchWarning(code="SCORE_CAPPED", severity="WARNING", message=score.cap_reason, symbol=symbol)
        )
    if score.coverage_pct < 100:
        missing = ", ".join(COMPONENT_LABELS[c.key] for c in score.components if not c.available)
        warnings.append(
            ResearchWarning(
                code="PARTIAL_COVERAGE",
                severity="INFO",
                message=f"The score covers {score.coverage_pct:.0f}% of the scoring weights. Not assessed: {missing}.",
                symbol=symbol,
            )
        )
    for claim in verification.claims:
        if claim.status in ("CONFLICTING", "STALE"):
            warnings.append(
                ResearchWarning(
                    code=f"{claim.status}_{claim.key.upper()}",
                    severity="WARNING",
                    message=f"{claim.claim}: {claim.detail}",
                    symbol=symbol,
                )
            )
    return warnings


def build_traces(outputs: dict[str, AgentOutput]) -> list[AgentTrace]:
    traces = []
    for agent, label in AGENT_LABELS.items():
        out = outputs.get(agent)
        if out is None:
            reason = UNAVAILABLE_AGENTS.get(agent, "Not run at this research depth.")
            traces.append(
                AgentTrace(
                    agent=agent,
                    label=label,
                    status="NOT_AVAILABLE" if agent in UNAVAILABLE_AGENTS else "SKIPPED",
                    summary=reason,
                )
            )
            continue
        traces.append(
            AgentTrace(
                agent=agent,
                label=label,
                status=out.status,
                confidence=out.confidence,
                timestamp=out.timestamp,
                duration_ms=out.duration_ms,
                summary=out.findings[0] if out.findings else "No findings.",
                findings=out.findings,
                warnings=out.warnings,
            )
        )
    return traces


def assemble(
    *,
    symbol: str,
    company: str,
    sector: str | None,
    run_id: str,
    generated_at: datetime,
    as_of: datetime,
    data_source: str,
    is_synthetic: bool,
    bundle: TechnicalBundle,
    historical: HistoricalAnalysis | None,
    risk: RiskAssessment,
    verification: VerificationReport,
    score: ScoreResult,
    market: MarketContext,
    sector_snapshot: SectorSnapshot | None,
    candidate: ScannerCandidate | None,
    outputs: dict[str, AgentOutput],
    sources: list[SourceRef],
    thresholds_note: str | None = None,
) -> ResearchReport:
    labels = build_labels(score, bundle, historical, market, sector_snapshot, risk.overall)
    not_assessed = list(NOT_ASSESSED_ALWAYS)
    if bundle.price.spread_bps is None:
        not_assessed.append("Bid/ask spread and market depth")
    if historical is None:
        not_assessed.append("Historical setup statistics (not run at this depth)")
    not_assessed += [c for c in risk.unavailable_checks if "spread" not in c.lower()]
    return ResearchReport(
        symbol=symbol,
        company=company,
        sector=sector,
        run_id=run_id,
        generated_at=generated_at,
        as_of=as_of,
        market_state=market.market_state,
        data_source=data_source,
        is_synthetic=is_synthetic,
        research_score=score.research_score,
        data_confidence=verification.data_confidence,
        risk_score=risk.risk_score,
        score_coverage_pct=score.coverage_pct,
        direction=score.direction,
        setup_quality=score.setup_quality,
        risk_level=risk.overall,
        labels=labels,
        overview=ReportOverview(
            price=bundle.price.price,
            change=bundle.price.change,
            change_pct=bundle.price.change_pct,
            volume=bundle.price.volume,
            avg_volume=bundle.price.avg_volume,
            sector=sector,
        ),
        price=bundle.price,
        volatility=bundle.volatility,
        score=score,
        technical=bundle.technical,
        historical=historical,
        risk=risk,
        verification=verification,
        market_context=market,
        sector_context=sector_snapshot,
        why_listed=build_why(candidate, score, historical),
        risks=build_risks(risk.flags, score, risk.unavailable_checks),
        invalidation=build_invalidation(bundle, market),
        warnings=build_warnings(symbol, risk.flags, market, score, verification),
        sources=sources,
        agents=build_traces(outputs),
        not_assessed=not_assessed,
    )
