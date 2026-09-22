"""Reads the context a research run needs and writes its progress and results. Used by the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.exceptions import NotFoundError
from app.domain.types import InstrumentRef
from app.models.research import (
    ResearchAgentOutput,
    ResearchCandidate,
    ResearchClaim,
    ResearchHistoricalPattern,
    ResearchMarketSnapshot,
    ResearchRiskEvent,
    ResearchScore,
    ResearchScoreComponent,
    ResearchSectorSnapshot,
    ResearchVerification,
)
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.research_repository import (
    ResearchAgentRunRepository,
    ResearchCandidateRepository,
    ResearchClaimRepository,
    ResearchOutputRepository,
    ResearchPatternRepository,
    ResearchRiskEventRepository,
    ResearchRunRepository,
    ResearchScoreRepository,
    ResearchSnapshotRepository,
    ResearchSourceRepository,
    ResearchUniverseRepository,
    ResearchWeightRepository,
)
from app.research.config import DEFAULT_WEIGHTS, merge_thresholds
from app.research.contracts import AgentOutput, MarketContext, ScannerCandidate
from app.research.pipeline import SymbolOutcome
from app.utils.time import utcnow

INDEX_SYMBOLS = ("NIFTY", "BANKNIFTY", "INDIAVIX")


@dataclass(slots=True)
class Member:
    symbol: str
    company: str
    sector: str | None
    ref: InstrumentRef | None  # None when the instrument master has no such symbol


@dataclass(slots=True)
class RunContext:
    run_id: str
    depth: str
    universe: str
    as_of: datetime
    is_live: bool
    weights: dict[str, float]
    thresholds: dict[str, Any]
    weight_set_id: str | None
    weight_set_version: int | None
    members: list[Member]
    index_refs: dict[str, InstrumentRef]
    provider_reliability: float
    provider_name: str = ""


@dataclass(slots=True)
class RunResults:
    candidates: list[ScannerCandidate]
    outcomes: dict[str, SymbolOutcome]
    run_outputs: list[AgentOutput]
    market: MarketContext
    agent_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    data_source: str = ""
    is_synthetic: bool = False
    market_state: str | None = None


class ResearchStore:
    def __init__(
        self,
        runs: ResearchRunRepository,
        agent_runs: ResearchAgentRunRepository,
        candidates: ResearchCandidateRepository,
        scores: ResearchScoreRepository,
        outputs: ResearchOutputRepository,
        claims: ResearchClaimRepository,
        snapshots: ResearchSnapshotRepository,
        patterns: ResearchPatternRepository,
        risk_events: ResearchRiskEventRepository,
        weights: ResearchWeightRepository,
        universe: ResearchUniverseRepository,
        sources: ResearchSourceRepository,
        instruments: InstrumentRepository,
        provider_name: str,
    ) -> None:
        self.runs, self.agent_runs, self.candidates, self.scores = runs, agent_runs, candidates, scores
        self.outputs, self.claims, self.snapshots, self.patterns = outputs, claims, snapshots, patterns
        self.risk_events, self.weights, self.universe, self.sources = risk_events, weights, universe, sources
        self.instruments = instruments
        self.provider_name = provider_name

    # ---- context ------------------------------------------------------------------------------------
    async def load_context(self, run_id: str) -> RunContext:
        run = await self.runs.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Research run not found")
        weight_set = (
            await self.weights.get_by_id(run.weight_set_id)
            if run.weight_set_id
            else await self.weights.active()
        )
        weights = {**DEFAULT_WEIGHTS, **(weight_set.weights if weight_set else {})}
        thresholds = merge_thresholds(weight_set.thresholds if weight_set else None)

        if run.requested_symbols:
            symbols = [s.upper() for s in run.requested_symbols]
            sectors = await self.universe.sector_map(symbols)
        else:
            rows = await self.universe.members(run.universe)
            symbols = [r.symbol for r in rows]
            sectors = {r.symbol: r.sector for r in rows}
        members: list[Member] = []
        for symbol in symbols:
            instrument = await self.instruments.get_by_symbol(symbol, "NSE")
            ref = (
                InstrumentRef(
                    instrument.symbol, instrument.exchange, instrument.exchange_token, instrument.segment
                )
                if instrument
                else None
            )
            members.append(
                Member(symbol, instrument.name if instrument else symbol, sectors.get(symbol), ref)
            )
        index_refs: dict[str, InstrumentRef] = {}
        for symbol in INDEX_SYMBOLS:
            instrument = await self.instruments.get_by_symbol(symbol, "NSE")
            if instrument:
                index_refs[symbol] = InstrumentRef(
                    instrument.symbol, instrument.exchange, instrument.exchange_token, instrument.segment
                )
        source = await self.sources.get_by_key(self.provider_name)
        reliability = (
            source.reliability_score if source else (0.10 if self.provider_name == "simulated" else 0.5)
        )
        return RunContext(
            run_id=run.id,
            depth=run.depth,
            universe=run.universe,
            as_of=run.as_of,
            is_live=run.is_live,
            weights=weights,
            thresholds=thresholds,
            weight_set_id=weight_set.id if weight_set else None,
            weight_set_version=weight_set.version if weight_set else None,
            members=members,
            index_refs=index_refs,
            provider_reliability=reliability,
            provider_name=self.provider_name,
        )

    # ---- progress -----------------------------------------------------------------------------------
    async def mark_running(
        self, run_id: str, data_source: str, is_synthetic: bool, market_state: str
    ) -> None:
        run = await self.runs.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Research run not found")
        run.status, run.started_at = "RUNNING", utcnow()
        run.data_source, run.is_synthetic, run.market_state = data_source, is_synthetic, market_state
        await self.runs.update(run)

    async def set_agent(
        self,
        run_id: str,
        agent: str,
        status: str,
        *,
        message: str | None = None,
        records: int | None = None,
        duration_ms: int | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        row = await self.agent_runs.get(run_id, agent)
        if row is None:
            return
        now = utcnow()
        if status == "RUNNING" and row.started_at is None:
            row.started_at = now
        if status in ("SUCCESS", "PARTIAL", "FAILED"):
            row.finished_at = now
        row.status = status
        if message is not None:
            row.message = message
        if records is not None:
            row.records = records
        if duration_ms is not None:
            row.duration_ms = duration_ms
        if warnings is not None:
            row.warnings = warnings
        await self.agent_runs.update(row)

    async def fail_run(self, run_id: str, message: str) -> None:
        run = await self.runs.get_by_id(run_id)
        if run is None:
            return
        run.status, run.error_message, run.completed_at = "FAILED", message[:2000], utcnow()
        if run.started_at:
            run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        for row in await self.agent_runs.for_run(run_id):
            if row.status in ("PENDING", "RUNNING"):
                row.status, row.message = "FAILED", message[:500]
        await self.runs.update(run)

    # ---- results ------------------------------------------------------------------------------------
    async def save_results(self, run_id: str, results: RunResults, duration_ms: int) -> None:
        run = await self.runs.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Research run not found")
        ranked = sorted(
            results.outcomes.items(),
            key=lambda kv: (kv[1].score.research_score is None, -(kv[1].score.research_score or 0.0), kv[0]),
        )
        ranks = {symbol: i for i, (symbol, _) in enumerate(ranked, start=1)}
        by_symbol = {c.symbol: c for c in results.candidates}

        rows: list[ResearchCandidate] = []
        for candidate in results.candidates:
            stage = "ANALYZED" if candidate.symbol in results.outcomes else candidate.stage
            reason = candidate.exclusion_reason or results.failures.get(candidate.symbol)
            if candidate.symbol in results.failures:
                stage = "EXCLUDED"
            rows.append(
                ResearchCandidate(
                    run_id=run_id,
                    symbol=candidate.symbol,
                    company=candidate.company,
                    sector=candidate.sector,
                    stage=stage,
                    exclusion_reason=reason,
                    initial_score=candidate.initial_score,
                    reasons=candidate.reasons,
                    features=candidate.model_dump(
                        mode="json",
                        include={
                            "price",
                            "change_pct",
                            "rel_volume",
                            "atr_pct",
                            "vwap",
                            "vwap_position",
                            "direction",
                            "tags",
                        },
                    ),
                )
            )
        await self.candidates.add_many(rows)

        outputs: list[ResearchAgentOutput] = []
        for out in results.run_outputs:
            outputs.append(
                ResearchAgentOutput(
                    run_id=run_id,
                    symbol=None,
                    agent=out.agent,
                    status=out.status,
                    confidence=out.confidence,
                    duration_ms=out.duration_ms,
                    structured_data=out.model_dump(mode="json"),
                )
            )
        sources_checked = conflicts = 0
        for symbol, outcome in results.outcomes.items():
            report, candidate = outcome.report, by_symbol.get(symbol)
            score = ResearchScore(
                run_id=run_id,
                symbol=symbol,
                company=report.company,
                sector=report.sector,
                as_of=report.as_of,
                research_score=report.research_score,
                data_confidence=report.data_confidence,
                coverage_pct=report.score_coverage_pct,
                direction=report.direction,
                setup_quality=report.setup_quality,
                risk_level=report.risk_level,
                rank=ranks[symbol],
                capped=outcome.score.capped,
                weight_set_id=run.weight_set_id,
                price=report.price.price,
                change_pct=report.price.change_pct,
                rel_volume=report.price.rel_volume,
                atr_pct=report.volatility.atr_pct,
                vwap=report.technical.levels.vwap,
                vwap_position=report.technical.levels.vwap_position,
                initial_score=candidate.initial_score if candidate else None,
                warning_count=len(report.warnings),
                report=report.model_dump(mode="json"),
            )
            components = [
                ResearchScoreComponent(
                    key=c.key,
                    points=c.points,
                    max_points=c.max_points,
                    available=c.available,
                    rating=c.rating,
                    summary=c.summary,
                    metrics=c.metrics,
                    evidence=[e.model_dump(mode="json") for e in c.evidence],
                )
                for c in outcome.score.components
            ]
            await self.scores.add_with_components(score, components)
            for agent_out in outcome.outputs.values():
                outputs.append(
                    ResearchAgentOutput(
                        run_id=run_id,
                        symbol=symbol,
                        agent=agent_out.agent,
                        status=agent_out.status,
                        confidence=agent_out.confidence,
                        data_as_of=report.as_of,
                        duration_ms=agent_out.duration_ms,
                        structured_data=agent_out.model_dump(mode="json"),
                    )
                )
            for claim in report.verification.claims:
                await self.claims.add_with_verification(
                    ResearchClaim(run_id=run_id, symbol=symbol, claim_key=claim.key, claim_text=claim.claim),
                    ResearchVerification(
                        status=claim.status,
                        confidence=claim.confidence,
                        sources_checked=claim.sources_checked,
                        independent_origins=claim.independent_origins,
                        tolerance_pct=claim.tolerance_pct,
                        detail=claim.detail,
                        resolution=claim.resolution,
                        source_values=[v.model_dump(mode="json") for v in claim.values],
                    ),
                )
            sources_checked += report.verification.sources_checked
            conflicts += report.verification.conflicts_found
            if report.historical:
                await self.patterns.add_many(
                    [
                        ResearchHistoricalPattern(
                            run_id=run_id,
                            symbol=symbol,
                            pattern_key=s.key,
                            label=s.label,
                            horizon=s.horizon,
                            occurrences=s.occurrences,
                            successful=s.successful,
                            success_rate=s.success_rate,
                            avg_return_pct=s.avg_return_pct,
                            median_return_pct=s.median_return_pct,
                            avg_return_net_pct=s.avg_return_net_pct,
                            mfe_pct=s.mfe_pct,
                            mae_pct=s.mae_pct,
                            sample_adequate=s.sample_adequate,
                            min_sample=s.min_sample,
                            period_start=s.period_start,
                            period_end=s.period_end,
                            detail=s.model_dump(
                                mode="json",
                                include={"description", "note", "reach_probability", "horizon_returns_pct"},
                            ),
                        )
                        for s in report.historical.setups
                    ]
                )
            await self.risk_events.add_many(
                [
                    ResearchRiskEvent(
                        run_id=run_id,
                        symbol=symbol,
                        code=f.code,
                        severity=f.severity,
                        message=f.message,
                        metric=f.metric,
                        value=f.value,
                    )
                    for f in report.risk.flags
                ]
            )
        await self.outputs.add_many(outputs)

        m = results.market
        nifty = next((i for i in m.indices if i.symbol == "NIFTY"), None)
        bank = next((i for i in m.indices if i.symbol == "BANKNIFTY"), None)
        await self.snapshots.create(
            ResearchMarketSnapshot(
                run_id=run_id,
                as_of=m.as_of,
                market_state=m.market_state,
                regime=m.regime.label,
                regime_confidence=m.regime.confidence,
                nifty_price=nifty.price if nifty else None,
                nifty_change_pct=nifty.change_pct if nifty else None,
                banknifty_price=bank.price if bank else None,
                banknifty_change_pct=bank.change_pct if bank else None,
                india_vix=m.india_vix,
                advances=m.breadth.advances if m.breadth else None,
                declines=m.breadth.declines if m.breadth else None,
                context=m.model_dump(mode="json"),
            )
        )
        await self.snapshots.add_sectors(
            [
                ResearchSectorSnapshot(
                    run_id=run_id,
                    sector=s.sector,
                    constituents=s.constituents,
                    ret_1d_pct=s.ret_1d_pct,
                    ret_5d_pct=s.ret_5d_pct,
                    rel_strength_1d=s.rel_strength_1d,
                    rel_strength_5d=s.rel_strength_5d,
                    avg_rel_volume=s.avg_rel_volume,
                    breadth_pct=s.breadth_pct,
                    momentum=s.momentum,
                    trend=s.trend,
                    rank=s.rank,
                )
                for s in m.sectors
            ]
        )

        for agent, stats in results.agent_stats.items():
            await self.set_agent(
                run_id,
                agent,
                stats["status"],
                message=stats.get("message"),
                records=stats.get("records"),
                duration_ms=stats.get("duration_ms"),
                warnings=stats.get("warnings"),
            )
        run.status, run.completed_at, run.duration_ms = "COMPLETED", utcnow(), duration_ms
        run.candidates_scanned, run.candidates_analyzed = len(results.candidates), len(results.outcomes)
        run.sources_checked, run.conflicts_found = sources_checked, conflicts
        run.data_source, run.is_synthetic, run.market_state = (
            results.data_source,
            results.is_synthetic,
            results.market_state,
        )
        await self.runs.update(run)
