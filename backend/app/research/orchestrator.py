"""ResearchOrchestrator: runs the funnel.

    load data -> normalise -> market context -> scanner -> per-symbol agents -> persist

Network fetches run concurrently (bounded); every database access goes through one lock in short transactions so
progress is visible to the UI while the run is in flight.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, TypeVar

from app.core.logging import get_logger
from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef, Quote
from app.research import market as mkt
from app.research import scanner
from app.research import sessions as ses
from app.research.contracts import Provenance, ScannerCandidate, SectorSnapshot
from app.research.features import InsufficientDataError, SymbolInput, TechnicalBundle, build_bundle
from app.research.pipeline import DEPTHS, SymbolOutcome, analyze_symbol, envelope
from app.services.research_store import Member, RunContext, RunResults
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.container import AppContainer
    from app.services.factory import Services

logger = get_logger(__name__)
T = TypeVar("T")


class ResearchOrchestrator:
    def __init__(self, container: AppContainer) -> None:
        self.container = container
        self._lock = asyncio.Lock()

    # ---- database access, serialised --------------------------------------------------------------
    @asynccontextmanager
    async def _uow(self):  # noqa: ANN202
        from app.services.factory import Services

        async with self.container.db.session_factory() as session:
            try:
                yield Services(session, self.container)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _db(self, fn: Callable[[Services], Awaitable[T]]) -> T:
        async with self._lock, self._uow() as services:
            return await fn(services)

    async def _agent(self, run_id: str, agent: str, status: str, **fields: Any) -> None:
        await self._db(lambda s: s.research_store.set_agent(run_id, agent, status, **fields))

    # ---- entry point ------------------------------------------------------------------------------
    async def execute(self, run_id: str) -> None:
        started = time.perf_counter()
        try:
            ctx = await self._db(lambda s: s.research_store.load_context(run_id))
            provider = self.container.market_data
            synthetic = provider.name == "simulated"
            state = ses.market_state(ctx.as_of)
            await self._db(lambda s: s.research_store.mark_running(run_id, provider.name, synthetic, state))
            results = await self._run(ctx, synthetic, state)
            duration = int((time.perf_counter() - started) * 1000)
            await self._db(lambda s: s.research_store.save_results(run_id, results, duration))
            logger.info(
                "research_run_completed",
                extra={"run_id": run_id, "analyzed": len(results.outcomes), "duration_ms": duration},
            )
        except asyncio.CancelledError:
            await self._safe_fail(run_id, "Cancelled: the server was shutting down")
            raise
        except Exception as exc:
            logger.exception("research_run_failed", extra={"run_id": run_id})
            await self._safe_fail(run_id, f"{type(exc).__name__}: {exc}")

    async def _safe_fail(self, run_id: str, message: str) -> None:
        try:
            await self._db(lambda s: s.research_store.fail_run(run_id, message))
        except Exception:
            logger.exception("research_fail_mark_failed", extra={"run_id": run_id})

    # ---- data loading -----------------------------------------------------------------------------
    async def _bars(
        self,
        ref: InstrumentRef,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        semaphore: asyncio.Semaphore,
    ) -> list[Candle]:
        ranges = await self._db(lambda s: s.market_data.plan_candle_fetch(ref, timeframe, start, end))
        fetched: dict[datetime, Candle] = {}
        if ranges:
            async with semaphore:
                for begin, finish in ranges:
                    for candle in await self.container.market_data.get_historical_data(
                        ref, timeframe, begin, finish, session_only=True
                    ):
                        fetched[candle.timestamp] = candle
            await self._db(
                lambda s: s.market_data.store_session_candles(
                    ref, timeframe, [fetched[t] for t in sorted(fetched)]
                )
            )
        bars = await self._db(lambda s: s.market_data.read_candles(ref, timeframe, start, end))
        return ses.closed_before(ses.filter_session(bars), end, timeframe.minutes)

    async def _load_symbol(
        self,
        member: Member,
        ctx: RunContext,
        quote: Quote | None,
        semaphore: asyncio.Semaphore,
        need_5m: bool,
        source_type: str,
        retrieved: datetime,
    ) -> SymbolInput:
        assert member.ref is not None
        days = self.container.settings.research_history_days
        bars_15m = await self._bars(
            member.ref, Timeframe.M15, ctx.as_of - timedelta(days=days), ctx.as_of, semaphore
        )
        bars_5m = (
            await self._bars(member.ref, Timeframe.M5, ctx.as_of - timedelta(days=14), ctx.as_of, semaphore)
            if need_5m
            else []
        )
        return SymbolInput(
            symbol=member.symbol,
            company=member.company,
            sector=member.sector,
            ref=member.ref,
            bars_15m=bars_15m,
            bars_5m=bars_5m,
            quote=quote,
            source_name=ctx.provider_name,
            source_type=source_type,
            source_reliability=ctx.provider_reliability,
            retrieved_at=retrieved,
            as_of=ctx.as_of,
        )

    async def _quotes(self, ctx: RunContext) -> dict[str, Quote]:
        if not ctx.is_live:
            return {}
        refs = [m.ref for m in ctx.members if m.ref is not None]
        try:
            quotes = await asyncio.wait_for(self.container.market_data.get_quote(refs), timeout=20)
        except Exception as exc:  # quotes only improve verification; a failure must not fail the run
            logger.warning("research_quotes_unavailable", extra={"error": type(exc).__name__})
            return {}
        return {q.symbol: q for q in quotes}

    # ---- the run ----------------------------------------------------------------------------------
    async def _run(self, ctx: RunContext, synthetic: bool, state: str) -> RunResults:
        run_id, depth = ctx.run_id, DEPTHS[ctx.depth]
        source_type = "SIMULATED" if synthetic else "MARKET_DATA_PROVIDER"
        retrieved = utcnow()
        semaphore = asyncio.Semaphore(self.container.settings.research_fetch_concurrency)
        t_scan = time.perf_counter()
        await self._agent(run_id, "MarketScannerAgent", "RUNNING", message="Loading market data")

        # 1. load
        failures: dict[str, str] = {}
        loadable = [m for m in ctx.members if m.ref is not None]
        for member in ctx.members:
            if member.ref is None:
                failures[member.symbol] = "Not found in the instrument master"
        quotes = await self._quotes(ctx)
        done = 0

        async def load(member: Member) -> tuple[Member, SymbolInput | Exception]:
            nonlocal done
            try:
                inp = await self._load_symbol(
                    member,
                    ctx,
                    quotes.get(member.symbol),
                    semaphore,
                    depth["load_5m"],
                    source_type,
                    retrieved,
                )
                result: SymbolInput | Exception = inp
            except Exception as exc:
                result = exc
            done += 1
            if done % 10 == 0 or done == len(loadable):
                await self._agent(
                    run_id,
                    "MarketScannerAgent",
                    "RUNNING",
                    message=f"Loaded market data for {done} of {len(loadable)} symbols",
                )
            return member, result

        index_bars: dict[str, list[Candle]] = {}

        async def load_index(symbol: str, ref: InstrumentRef) -> None:
            try:
                index_bars[symbol] = await self._bars(
                    ref,
                    Timeframe.M15,
                    ctx.as_of - timedelta(days=self.container.settings.research_history_days),
                    ctx.as_of,
                    semaphore,
                )
            except Exception as exc:
                logger.warning(
                    "research_index_unavailable", extra={"symbol": symbol, "error": type(exc).__name__}
                )

        loaded = await asyncio.gather(
            *[load(m) for m in loadable], *[load_index(sym, ref) for sym, ref in ctx.index_refs.items()]
        )
        inputs: dict[str, SymbolInput] = {}
        for item in loaded[: len(loadable)]:
            member, result = item  # type: ignore[misc]
            if isinstance(result, Exception):
                failures[member.symbol] = f"Data could not be loaded: {type(result).__name__}: {result}"
            else:
                inputs[member.symbol] = result

        # 2. normalise
        bundles: dict[str, TechnicalBundle] = {}
        timeframes = depth["timeframes"]
        for symbol, inp in inputs.items():
            try:
                bundles[symbol] = await asyncio.to_thread(build_bundle, inp, timeframes)
            except InsufficientDataError as exc:
                failures[symbol] = str(exc)
            except Exception as exc:
                failures[symbol] = f"Could not be normalised: {type(exc).__name__}: {exc}"
        if not bundles:
            first = next(iter(failures.values()), "no symbols in the universe")
            raise RuntimeError(
                f"No symbol had enough market data to analyse ({len(failures)} failed). First problem: {first}"
            )

        # 3. market context (MarketRiskAgent, run level)
        t_market = time.perf_counter()
        await self._agent(
            run_id, "MarketRiskAgent", "RUNNING", message="Building market regime and sector context"
        )
        market_ctx, points = self._market_context(ctx, bundles, index_bars, state, source_type, retrieved)
        market_output = envelope(
            "MarketRiskAgent",
            None,
            "SUCCESS",
            ctx.provider_reliability,
            retrieved,
            t_market,
            [
                f"Market regime {market_ctx.regime.label.replace('_', ' ').lower()} (confidence {market_ctx.regime.confidence * 100:.0f}%)."
            ]
            + [f"{f.name}: {f.value}" for f in market_ctx.regime.factors[:4]],
            {"market": market_ctx.model_dump(mode="json")},
            warnings=[f"Not available: {u}" for u in market_ctx.unavailable],
        )

        # 4. scanner
        sector_by_name = {s.sector: s for s in market_ctx.sectors}
        candidates: list[ScannerCandidate] = []
        for symbol, bundle in bundles.items():
            inp = inputs[symbol]
            reason = scanner.prefilter(bundle, ctx.thresholds)
            if reason:
                candidates.append(
                    ScannerCandidate(
                        symbol=symbol,
                        company=inp.company,
                        sector=inp.sector,
                        stage="EXCLUDED",
                        exclusion_reason=reason,
                        price=bundle.price.price,
                    )
                )
                continue
            candidates.append(
                scanner.scan(symbol, inp.company, inp.sector, bundle, sector_by_name.get(inp.sector or ""))
            )
        for symbol, reason in failures.items():
            member = next((m for m in ctx.members if m.symbol == symbol), None)
            candidates.append(
                ScannerCandidate(
                    symbol=symbol,
                    company=member.company if member else symbol,
                    sector=member.sector if member else None,
                    stage="EXCLUDED",
                    exclusion_reason=reason,
                )
            )
        eligible = sorted((c for c in candidates if c.stage == "SCANNED"), key=lambda c: -c.initial_score)
        selected = {c.symbol for c in eligible[: depth["limit"]]}
        for c in candidates:
            if c.symbol in selected:
                c.stage = "SELECTED"
        scan_ms = int((time.perf_counter() - t_scan) * 1000)
        scanner_output = envelope(
            "MarketScannerAgent",
            None,
            "SUCCESS",
            ctx.provider_reliability,
            retrieved,
            t_scan,
            [
                f"Scanned {len(bundles)} of {len(ctx.members)} symbols; {len(selected)} selected for full analysis; {sum(1 for c in candidates if c.stage == 'EXCLUDED')} excluded."
            ],
            {
                "selected": sorted(selected),
                "excluded": {c.symbol: c.exclusion_reason for c in candidates if c.stage == "EXCLUDED"},
            },
            warnings=[f"{s}: {r}" for s, r in failures.items()][:20],
        )
        await self._agent(
            run_id,
            "MarketScannerAgent",
            "SUCCESS",
            message=f"{len(bundles)} scanned, {len(selected)} selected",
            records=len(bundles),
            duration_ms=scan_ms,
        )

        # 5. per-symbol agents
        for agent in ("HistoricalTechnicalAgent", "QuantScoringAgent", "ResearchSynthesizerAgent"):
            await self._agent(run_id, agent, "RUNNING", message=f"Analysing {len(selected)} symbols")
        if depth["verification"]:
            await self._agent(
                run_id, "DataVerificationAgent", "RUNNING", message=f"Verifying {len(selected)} symbols"
            )
        by_symbol = {c.symbol: c for c in candidates}
        outcomes: dict[str, SymbolOutcome] = {}
        now = utcnow()
        for i, symbol in enumerate(sorted(selected, key=lambda s: -by_symbol[s].initial_score), start=1):
            try:
                outcomes[symbol] = await asyncio.to_thread(
                    analyze_symbol,
                    inp=inputs[symbol],
                    bundle=bundles[symbol],
                    market=market_ctx,
                    sector=sector_by_name.get(inputs[symbol].sector or ""),
                    candidate=by_symbol[symbol],
                    depth=ctx.depth,
                    thresholds=ctx.thresholds,
                    weights=ctx.weights,
                    weight_set=(ctx.weight_set_id, ctx.weight_set_version),
                    run_id=ctx.run_id,
                    now=now,
                )
            except Exception as exc:
                logger.exception("research_symbol_failed", extra={"run_id": run_id, "symbol": symbol})
                failures[symbol] = f"Analysis failed: {type(exc).__name__}: {exc}"
            if i % 5 == 0:
                await self._agent(
                    run_id, "QuantScoringAgent", "RUNNING", message=f"Analysed {i} of {len(selected)} symbols"
                )

        # 6. summarise agent stats
        def total(agent: str) -> int:
            return sum(o.timings_ms.get(agent, 0) for o in outcomes.values())

        n = len(outcomes)
        verification_warnings = (
            [w for o in outcomes.values() for w in o.outputs["DataVerificationAgent"].warnings][:20]
            if depth["verification"] and n
            else []
        )
        stats: dict[str, dict[str, Any]] = {
            "MarketRiskAgent": {
                "status": "SUCCESS",
                "records": n + 1,
                "duration_ms": (
                    int((time.perf_counter() - t_market) * 1000)
                    if n == 0
                    else total("MarketRiskAgent") + int(market_output.duration_ms)
                ),
                "message": f"Market regime plus risk checks for {n} symbols",
            },
            "HistoricalTechnicalAgent": {
                "status": "SUCCESS" if n else "FAILED",
                "records": n,
                "duration_ms": total("HistoricalTechnicalAgent"),
                "message": (
                    "Technical analysis and historical setup statistics"
                    if depth["historical"]
                    else "Technical analysis only (historical statistics run at Standard depth and above)"
                ),
            },
            "QuantScoringAgent": {
                "status": "SUCCESS" if n else "FAILED",
                "records": n,
                "duration_ms": total("QuantScoringAgent"),
                "message": f"Scored {n} symbols with the deterministic model",
            },
            "ResearchSynthesizerAgent": {
                "status": "SUCCESS" if n else "FAILED",
                "records": n,
                "duration_ms": total("ResearchSynthesizerAgent"),
                "message": f"Built {n} reports",
            },
            "ResearchQualityAgent": {
                "status": "SUCCESS" if n else "FAILED",
                "records": n,
                "duration_ms": total("ResearchQualityAgent"),
                "message": _quality_message(outcomes),
                "warnings": [
                    f"{symbol}: {c.message}"
                    for symbol, outcome in outcomes.items()
                    for c in outcome.report.quality_checks
                    if c.status != "PASS"
                ][:20],
            },
        }
        if depth["verification"]:
            stats["DataVerificationAgent"] = {
                "status": "SUCCESS",
                "records": n,
                "duration_ms": total("DataVerificationAgent"),
                "message": f"Verified {n} symbols",
                "warnings": verification_warnings,
            }
        return RunResults(
            candidates=candidates,
            outcomes=outcomes,
            run_outputs=[scanner_output, market_output],
            market=market_ctx,
            agent_stats=stats,
            failures=failures,
            data_source=ctx.provider_name,
            is_synthetic=synthetic,
            market_state=state,
        )

    def _market_context(
        self,
        ctx: RunContext,
        bundles: dict[str, TechnicalBundle],
        index_bars: dict[str, list[Candle]],
        state: str,
        source_type: str,
        retrieved: datetime,
    ):  # noqa: ANN202
        indices = [
            mkt.index_snapshot(sym, index_bars[sym]) for sym in ("NIFTY", "BANKNIFTY") if sym in index_bars
        ]
        vix = mkt.index_snapshot("INDIAVIX", index_bars["INDIAVIX"]) if "INDIAVIX" in index_bars else None
        points = []
        for symbol, b in bundles.items():
            daily = next((t for t in b.technical.timeframes if t.timeframe == "daily"), None)
            points.append(
                mkt.StockPoint(
                    symbol=symbol,
                    sector=ctx_sector(ctx, symbol),
                    change_pct=b.price.change_pct,
                    ret_5d_pct=b.price.ret_5d_pct,
                    rel_volume=b.price.rel_volume,
                    rsi=daily.rsi if daily else None,
                    above_vwap=(
                        (b.technical.levels.vwap_position == "ABOVE")
                        if b.technical.levels.vwap_position
                        else None
                    ),
                    above_ema20=(b.price.price > daily.ema20) if daily and daily.ema20 else None,
                )
            )
        nifty = next((i for i in indices if i.symbol == "NIFTY"), None)
        breadth = mkt.compute_breadth(points)
        sectors: list[SectorSnapshot] = mkt.compute_sectors(points, nifty)
        latest_session = None
        if index_bars.get("NIFTY"):
            latest_session = ses.group_sessions(index_bars["NIFTY"])[-1].day.isoformat()
        elif bundles:
            latest_session = next(iter(bundles.values())).price.session_date
        data_as_of = max(
            (bars[-1].timestamp + timedelta(minutes=15) for bars in index_bars.values() if bars),
            default=ctx.as_of,
        )
        provenance = Provenance(source=ctx.provider_name, source_type=source_type, data_as_of=data_as_of, retrieved_at=retrieved, confidence=ctx.provider_reliability)  # type: ignore[arg-type]
        context = mkt.build_context(
            ctx.as_of,
            state,
            mkt.state_note(state, latest_session),
            indices,
            vix,
            breadth,
            sectors,
            provenance,
            ctx.thresholds,
        )
        return context, points


def _quality_message(outcomes: dict[str, SymbolOutcome]) -> str:
    if not outcomes:
        return "No reports to check"
    counts: dict[str, int] = {}
    for outcome in outcomes.values():
        counts[outcome.report.quality_status] = counts.get(outcome.report.quality_status, 0) + 1
    return ", ".join(f"{count} {status}" for status, count in sorted(counts.items()))


def ctx_sector(ctx: RunContext, symbol: str) -> str | None:
    return next((m.sector for m in ctx.members if m.symbol == symbol), None)
