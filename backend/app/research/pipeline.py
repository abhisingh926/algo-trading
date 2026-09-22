"""Per-symbol research pipeline composed from the pure stages. The orchestrator calls this after the data has
been loaded and normalised, so it can be unit-tested end to end without a database or a network."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.research import historical as hist
from app.research import risk as risk_mod
from app.research import synthesis, verification
from app.research.config import merge_thresholds
from app.research.contracts import (
    AgentOutput,
    HistoricalAnalysis,
    MarketContext,
    ResearchReport,
    RiskAssessment,
    ScannerCandidate,
    ScoreResult,
    SectorSnapshot,
    SourceRef,
    VerificationClaim,
)
from app.research.features import SymbolInput, TechnicalBundle
from app.research.scoring import ScoringInput, score_symbol
from app.research.sessions import ist_day, market_state

DEPTHS: dict[str, dict[str, Any]] = {
    "QUICK": {
        "limit": 10,
        "historical": False,
        "verification": False,
        "timeframes": ["15m", "30m", "1h", "daily"],
        "load_5m": False,
    },
    "STANDARD": {
        "limit": 20,
        "historical": True,
        "verification": True,
        "timeframes": ["5m", "15m", "30m", "1h", "daily"],
        "load_5m": True,
    },
    "DEEP": {
        "limit": 50,
        "historical": True,
        "verification": True,
        "timeframes": ["5m", "15m", "30m", "1h", "daily", "weekly"],
        "load_5m": True,
    },
}


_FIVE, _FIFTEEN = timedelta(minutes=5), timedelta(minutes=15)


def _bars_end(bars: list, minutes: int) -> datetime:  # type: ignore[type-arg]
    return bars[-1].timestamp + timedelta(minutes=minutes)


def _same_day(bar: Any, day_iso: str) -> bool:
    return ist_day(bar.timestamp).isoformat() == day_iso


@dataclass(slots=True)
class SymbolOutcome:
    report: ResearchReport
    outputs: dict[str, AgentOutput]
    historical: HistoricalAnalysis | None
    risk: RiskAssessment
    score: ScoreResult
    claims: list[VerificationClaim]
    timings_ms: dict[str, int] = field(default_factory=dict)


def envelope(
    agent: str,
    symbol: str | None,
    status: str,
    confidence: float,
    now: datetime,
    started: float,
    findings: list[str],
    metrics: dict[str, Any],
    risks: list[str] | None = None,
    sources: list[SourceRef] | None = None,
    warnings: list[str] | None = None,
) -> AgentOutput:
    return AgentOutput(
        agent=agent,
        symbol=symbol,
        status=status,
        confidence=round(confidence, 2),
        timestamp=now,
        duration_ms=int((time.perf_counter() - started) * 1000),
        findings=findings,
        metrics=metrics,
        risks=risks or [],
        sources=sources or [],
        warnings=warnings or [],
    )


def source_refs(inp: SymbolInput, has_5m: bool, has_quote: bool) -> list[SourceRef]:
    origin = inp.source_name
    base = dict(
        source_type=inp.source_type,
        tier=2 if inp.source_type == "MARKET_DATA_PROVIDER" else 3,
        reliability=inp.source_reliability,
        origin=origin,
    )
    refs = [SourceRef(key="candles_15m", name=f"{origin} 15-minute candles", retrieved_at=inp.retrieved_at, note="Regular-session bars, stored in MySQL", **base)]  # type: ignore[arg-type]
    if has_5m:
        refs.append(SourceRef(key="candles_5m", name=f"{origin} 5-minute candles", retrieved_at=inp.retrieved_at, **base))  # type: ignore[arg-type]
    if has_quote:
        refs.append(SourceRef(key="quote", name=f"{origin} live quote", retrieved_at=inp.retrieved_at, **base))  # type: ignore[arg-type]
    return refs


def run_verification(
    inp: SymbolInput, bundle: TechnicalBundle, thresholds: dict[str, Any], now: datetime, state: str
) -> tuple[list[VerificationClaim], float, bool, str | None]:
    """Cross-check what can be cross-checked. Returns (claims, freshness score, stale?, stale message)."""
    origin, rel = inp.source_name, inp.source_reliability
    synthetic = inp.source_type == "SIMULATED"
    claims: list[VerificationClaim] = []

    # Price: every feed we hold for the latest price. The live quote is only comparable while the market is open.
    price_obs = [
        verification.Observation(
            "15-minute candles", origin, inp.bars_15m[-1].close, _bars_end(inp.bars_15m, 15), rel
        )
    ]
    if inp.bars_5m:
        price_obs.append(
            verification.Observation(
                "5-minute candles", origin, inp.bars_5m[-1].close, _bars_end(inp.bars_5m, 5), rel
            )
        )
    if inp.quote is not None and state == "OPEN":
        price_obs.append(
            verification.Observation("live quote", origin, inp.quote.ltp, inp.quote.timestamp, rel)
        )
    max_age = thresholds["stale_minutes_open"] * 3 if state == "OPEN" else None
    claims.append(verification.verify_numeric("price", "Current price", price_obs, 0.5, now, max_age))

    # Session volume: compare the 5m and 15m series over the same window. A synthetic feed generates them
    # independently, so the comparison would only measure the generator; say so instead of pretending.
    if inp.bars_5m and not synthetic:
        limit = _bars_end(inp.bars_15m, 15)
        day = bundle.price.session_date
        v15 = sum(b.volume for b in inp.bars_15m if _same_day(b, day))
        v5 = sum(b.volume for b in inp.bars_5m if _same_day(b, day) and b.timestamp + _FIVE <= limit)
        claims.append(
            verification.verify_numeric(
                "session_volume",
                "Session volume so far",
                [
                    verification.Observation("15-minute candles", origin, float(v15), limit, rel),
                    verification.Observation("5-minute candles", origin, float(v5), limit, rel),
                ],
                2.0,
                now,
            )
        )
    else:
        detail = (
            "Synthetic feed: volumes at different timeframes are generated independently, so they cannot be compared."
            if synthetic
            else "Only one volume series was loaded."
        )
        claims.append(
            VerificationClaim(
                key="session_volume",
                claim="Session volume so far",
                status="UNVERIFIED",
                confidence=round(rel * 0.5, 2),
                sources_checked=1,
                independent_origins=1,
                values=[],
                detail=detail,
            )
        )
    claims.append(verification.verify_integrity(inp.bars_15m[-2500:], origin, rel))
    score, stale, message = verification.freshness(
        now, bundle.data_as_of, state, thresholds["stale_minutes_open"]
    )
    return claims, score, stale, message


def analyze_symbol(
    *,
    inp: SymbolInput,
    bundle: TechnicalBundle,
    market: MarketContext,
    sector: SectorSnapshot | None,
    candidate: ScannerCandidate | None,
    depth: str,
    thresholds: dict[str, Any],
    weights: dict[str, float],
    weight_set: tuple[str | None, int | None],
    run_id: str,
    now: datetime,
) -> SymbolOutcome:
    thresholds = merge_thresholds(thresholds)
    config = DEPTHS[depth]
    state = market_state(inp.as_of) if inp.as_of else "CLOSED"
    synthetic = inp.source_type == "SIMULATED"
    outputs: dict[str, AgentOutput] = {}
    timings: dict[str, int] = {}
    provenance = bundle.technical.provenance
    sources = source_refs(inp, bool(inp.bars_5m), inp.quote is not None)

    # -- MarketScannerAgent (the scan itself is run level; this records what it found for this stock) ---------
    if candidate is not None:
        t0 = time.perf_counter()
        outputs["MarketScannerAgent"] = envelope(
            "MarketScannerAgent",
            inp.symbol,
            "SUCCESS",
            provenance.confidence,
            now,
            t0,
            [
                f"Initial scanner score {candidate.initial_score:g} of 100. It only decides which stocks are analysed and is not the research score."
            ]
            + [f"{reason}." for reason in candidate.reasons],
            {"candidate": candidate.model_dump(mode="json")},
        )

    # -- HistoricalTechnicalAgent ------------------------------------------------------------------------
    t0 = time.perf_counter()
    historical: HistoricalAnalysis | None = None
    if config["historical"]:
        historical = hist.analyze(
            bundle.sessions,
            provenance,
            int(thresholds["min_sample"]),
            float(thresholds["round_trip_cost_pct"]),
        )
    tech = bundle.technical
    findings = [
        f"Direction {tech.direction.lower()} ({bundle.direction_score:+d} of 5 signals)."
    ] + tech.price_action.tags
    if historical and historical.matched:
        findings.append(
            f"Best-supported historical match: {historical.matched.label} ({historical.matched.occurrences} occurrences)."
        )
    warnings = (
        historical.warnings if historical else ["Historical setup statistics were skipped at this depth."]
    )
    outputs["HistoricalTechnicalAgent"] = envelope(
        "HistoricalTechnicalAgent",
        inp.symbol,
        "SUCCESS" if historical or not config["historical"] else "PARTIAL",
        provenance.confidence,
        now,
        t0,
        findings,
        {
            "technical": tech.model_dump(mode="json"),
            "historical": historical.model_dump(mode="json") if historical else None,
        },
        sources=[s for s in sources if s.key.startswith("candles")],
        warnings=warnings,
    )
    timings["HistoricalTechnicalAgent"] = outputs["HistoricalTechnicalAgent"].duration_ms

    # -- MarketRiskAgent ---------------------------------------------------------------------------------
    t0 = time.perf_counter()
    risk = risk_mod.assess_risk(bundle, market, thresholds, provenance)
    outputs["MarketRiskAgent"] = envelope(
        "MarketRiskAgent",
        inp.symbol,
        "SUCCESS",
        provenance.confidence,
        now,
        t0,
        [f"Overall risk {risk.overall.lower()}; {len(risk.flags)} flag(s)."]
        + [f.message for f in risk.flags],
        {"risk": risk.model_dump(mode="json")},
        risks=[f.message for f in risk.flags],
        sources=sources[:1],
        warnings=[f"Not checked: {c}" for c in risk.unavailable_checks],
    )
    timings["MarketRiskAgent"] = outputs["MarketRiskAgent"].duration_ms

    # -- DataVerificationAgent ---------------------------------------------------------------------------
    t0 = time.perf_counter()
    claims: list[VerificationClaim] = []
    freshness_score, stale, stale_message = verification.freshness(
        now, bundle.data_as_of, state, thresholds["stale_minutes_open"]
    )
    if config["verification"]:
        claims, freshness_score, stale, stale_message = run_verification(inp, bundle, thresholds, now, state)
        outputs["DataVerificationAgent"] = envelope(
            "DataVerificationAgent",
            inp.symbol,
            "SUCCESS",
            sum(c.confidence for c in claims) / len(claims),
            now,
            t0,
            [
                f"{c.claim}: {c.status.replace('_', ' ').lower()} ({c.sources_checked} source(s), {c.independent_origins} independent)."
                for c in claims
            ],
            {"claims": [c.model_dump(mode="json") for c in claims]},
            sources=sources,
            warnings=[c.detail for c in claims if c.status in ("CONFLICTING", "STALE")],
        )
        timings["DataVerificationAgent"] = outputs["DataVerificationAgent"].duration_ms

    # -- QuantScoringAgent -------------------------------------------------------------------------------
    t0 = time.perf_counter()
    preliminary = verification.finalize(
        claims,
        inp.source_reliability,
        freshness_score,
        1.0,
        bool(historical and historical.matched),
        synthetic,
        provenance,
    )
    flags = risk.flags + risk_mod.data_flags(
        preliminary, synthetic, (historical.matched is not None) if historical else None, stale, stale_message
    )
    scoring_input = ScoringInput(
        price=bundle.price,
        volatility=bundle.volatility,
        technical=tech,
        historical=historical,
        risk_flags=flags,
        unavailable_checks=risk.unavailable_checks,
        market=market,
        sector=sector,
        source_key="candles_15m",
        thresholds=thresholds,
    )
    score = score_symbol(scoring_input, weights, weight_set[0], weight_set[1])
    final_verification = verification.finalize(
        claims,
        inp.source_reliability,
        freshness_score,
        score.coverage_pct / 100,
        bool(historical and historical.matched),
        synthetic,
        provenance,
    )
    risk = risk.model_copy(
        update={"flags": flags, "data_risk": risk_mod.data_risk_level(final_verification, synthetic, stale)}
    )
    risk = risk.model_copy(
        update={
            "overall": risk_mod.overall_level(
                flags, [risk.liquidity_risk, risk.volatility_risk, risk.market_risk, risk.data_risk]
            )
        }
    )
    outputs["QuantScoringAgent"] = envelope(
        "QuantScoringAgent",
        inp.symbol,
        "SUCCESS" if score.research_score is not None else "PARTIAL",
        final_verification.data_confidence / 100,
        now,
        t0,
        [
            f"Research score {score.research_score if score.research_score is not None else 'n/a'} of 100 over {score.coverage_pct:.0f}% of the scoring weights."
        ]
        + [f"{c.label}: {c.points:g}/{c.max_points:g}" for c in score.components if c.available],
        {"score": score.model_dump(mode="json")},
        warnings=[score.cap_reason] if score.cap_reason else [],
    )
    timings["QuantScoringAgent"] = outputs["QuantScoringAgent"].duration_ms

    # -- ResearchSynthesizerAgent ------------------------------------------------------------------------
    t0 = time.perf_counter()
    report = synthesis.assemble(
        symbol=inp.symbol,
        company=inp.company,
        sector=inp.sector,
        run_id=run_id,
        generated_at=now,
        as_of=inp.as_of,
        data_source=inp.source_name,
        is_synthetic=synthetic,
        bundle=bundle,
        historical=historical,
        risk=risk,
        verification=final_verification,
        score=score,
        market=market,
        sector_snapshot=sector,
        candidate=candidate,
        outputs=outputs,
        sources=sources,
    )
    outputs["ResearchSynthesizerAgent"] = envelope(
        "ResearchSynthesizerAgent",
        inp.symbol,
        "SUCCESS",
        final_verification.data_confidence / 100,
        now,
        t0,
        [f"Assembled the report from {len(outputs)} agent outputs without adding new facts."],
        {"why_listed": report.why_listed, "invalidation": report.invalidation},
    )
    report.agents = synthesis.build_traces(outputs)
    timings["ResearchSynthesizerAgent"] = outputs["ResearchSynthesizerAgent"].duration_ms
    return SymbolOutcome(report, outputs, historical, risk, score, claims, timings)
