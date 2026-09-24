"""Runs post-market calibration: loads the market that followed each research score and measures it."""

from __future__ import annotations

from datetime import timedelta

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.enums import Timeframe
from app.domain.types import Candle, InstrumentRef
from app.models.research import ResearchCalibrationResult, ResearchRun
from app.research import calibration as cal
from app.services.market_data_service import MarketDataService
from app.services.research_store import ResearchStore
from app.utils.time import utcnow

# 5-minute bars give every horizon; 15-minute bars are the fallback once the finer history has rolled off.
PREFERRED = (Timeframe.M5, Timeframe.M15)
LOOKAHEAD = timedelta(hours=3)


class CalibrationService:
    def __init__(self, store: ResearchStore, market_data: MarketDataService) -> None:
        self.store = store
        self.market_data = market_data

    async def _forward_bars(self, ref: InstrumentRef, as_of) -> tuple[list[Candle], str]:  # noqa: ANN001
        """Session bars covering the hour after `as_of`, fetching them once if they are not stored yet."""
        end = as_of + LOOKAHEAD
        for timeframe in PREFERRED:
            ranges = await self.market_data.plan_candle_fetch(ref, timeframe, as_of, end)
            if ranges:
                fetched: dict = {}
                for begin, finish in ranges:
                    for candle in await self.market_data.provider.get_historical_data(
                        ref, timeframe, begin, finish, session_only=True
                    ):
                        fetched[candle.timestamp] = candle
                await self.market_data.store_session_candles(
                    ref, timeframe, [fetched[t] for t in sorted(fetched)]
                )
            bars = await self.market_data.read_candles(ref, timeframe, as_of, end)
            if bars:
                return bars, timeframe.value
        return [], PREFERRED[0].value

    async def calibrate_run(self, run_id: str, *, force: bool = False) -> dict:
        run = await self.store.runs.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Research run not found")
        if run.status != "COMPLETED":
            raise ConflictError(
                f"Run #{run.run_number} is {run.status.lower()}; only a completed run can be calibrated"
            )
        ready_at = cal.horizon_end(run.as_of)
        if utcnow() < ready_at and not force:
            raise ConflictError(
                f"Run #{run.run_number} cannot be calibrated yet: the hour after it ends at "
                f"{ready_at.isoformat()}. Wait for the market to move on."
            )
        scores = await self.store.scores.list_for_run(run_id, limit=500)
        if not scores:
            raise ConflictError(f"Run #{run.run_number} has no scored candidates to calibrate")

        rows: list[ResearchCalibrationResult] = []
        outcomes: list[cal.Outcome] = []
        for score in scores:
            if score.research_score is None:
                continue
            candidate = cal.ScoredCandidate(
                run_id=run_id,
                symbol=score.symbol,
                as_of=score.as_of,
                research_score=score.research_score,
                data_confidence=score.data_confidence,
                risk_score=score.risk_score,
                direction=score.direction,
            )
            try:
                ref = await self.market_data.resolve(score.symbol, "NSE")
                bars, source = await self._forward_bars(ref, score.as_of)
            except Exception:  # a symbol whose data cannot be loaded is recorded as unmeasurable, not skipped
                bars, source = [], PREFERRED[0].value
            outcome = cal.measure(candidate, bars, source) if bars else None
            if outcome is not None:
                outcomes.append(outcome)
            rows.append(_row(run_id, candidate, outcome, source))
        await self.store.calibration.replace_for_run(run_id, rows)
        return self._summary_payload(run, outcomes, rows)

    def _summary_payload(
        self, run: ResearchRun, outcomes: list[cal.Outcome], rows: list
    ) -> dict:  # noqa: ANN001
        summary = cal.summarise(outcomes)
        return {
            "run_id": run.id,
            "run_number": run.run_number,
            "as_of": run.as_of,
            "is_synthetic": run.is_synthetic,
            "candidates": len(rows),
            "summary": _summary_dict(summary),
            "results": [_result_dict(r) for r in rows],
        }

    async def run_results(self, run_id: str) -> dict:
        run = await self.store.runs.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Research run not found")
        rows = await self.store.calibration.for_run(run_id)
        if not rows:
            raise NotFoundError(
                f"Run #{run.run_number} has not been calibrated yet. Calibrate it once an hour of trading has passed."
            )
        return self._summary_payload(run, _outcomes_from_rows(rows), list(rows))

    async def overall(self) -> dict:
        rows = await self.store.calibration.all_results()
        outcomes = _outcomes_from_rows(rows)
        summary = cal.summarise(outcomes)
        runs = {r.run_id for r in rows}
        return {
            "runs_calibrated": len(runs),
            "results": len(rows),
            "summary": _summary_dict(summary),
        }

    async def pending_runs(self) -> list[dict]:
        """Completed runs that are old enough to calibrate but have not been."""
        done = await self.store.calibration.calibrated_run_ids()
        now = utcnow()
        out = []
        for run in await self.store.runs.list_recent(limit=100):
            if run.status == "COMPLETED" and run.id not in done and cal.horizon_end(run.as_of) <= now:
                out.append({"run_id": run.id, "run_number": run.run_number, "as_of": run.as_of})
        return out


def _row(
    run_id: str, c: cal.ScoredCandidate, outcome: cal.Outcome | None, source: str
) -> ResearchCalibrationResult:
    returns = outcome.returns if outcome else {}
    return ResearchCalibrationResult(
        run_id=run_id,
        symbol=c.symbol,
        as_of=c.as_of,
        research_score=c.research_score,
        data_confidence=c.data_confidence,
        risk_score=c.risk_score,
        direction=c.direction,
        bucket=cal.bucket_of(c.research_score),
        entry_time=outcome.entry_time if outcome else None,
        entry_price=outcome.entry_price if outcome else None,
        ret_5m=returns.get("5m"),
        ret_15m=returns.get("15m"),
        ret_30m=returns.get("30m"),
        ret_1h=returns.get("1h"),
        mfe_pct=outcome.mfe_pct if outcome else None,
        mae_pct=outcome.mae_pct if outcome else None,
        horizons_complete=outcome.horizons_complete if outcome else 0,
        directionless=outcome.directionless if outcome else c.direction not in ("BULLISH", "BEARISH"),
        measurable=bool(outcome and outcome.primary is not None),
        bars_source=source,
        note=None if outcome else "No market data after this score, so the outcome could not be measured.",
    )


def _outcomes_from_rows(rows) -> list[cal.Outcome]:  # noqa: ANN001
    out = []
    for r in rows:
        if r.entry_time is None or r.entry_price is None:
            continue
        candidate = cal.ScoredCandidate(
            run_id=r.run_id,
            symbol=r.symbol,
            as_of=r.as_of,
            research_score=r.research_score,
            data_confidence=r.data_confidence,
            risk_score=r.risk_score,
            direction=r.direction,
        )
        out.append(
            cal.Outcome(
                candidate=candidate,
                entry_time=r.entry_time,
                entry_price=r.entry_price,
                returns={"5m": r.ret_5m, "15m": r.ret_15m, "30m": r.ret_30m, "1h": r.ret_1h},
                mfe_pct=r.mfe_pct,
                mae_pct=r.mae_pct,
                bars_source=r.bars_source or "15m",
                horizons_complete=r.horizons_complete,
                directionless=r.directionless,
            )
        )
    return out


def _summary_dict(summary: cal.CalibrationSummary) -> dict:
    return {
        "measured": summary.measured,
        "directionless_excluded": summary.directionless_excluded,
        "unmeasurable": summary.unmeasurable,
        "adequate_buckets": summary.adequate_buckets,
        "ordered_as_expected": summary.ordered_as_expected,
        "period_start": summary.period_start,
        "period_end": summary.period_end,
        "verdict": summary.verdict,
        "caveats": summary.caveats,
        "min_sample": cal.MIN_BUCKET_SAMPLE,
        "buckets": [
            {
                "bucket": b.bucket,
                "occurrences": b.occurrences,
                "sample_adequate": b.sample_adequate,
                "win_rate": b.win_rate,
                "mean_returns": b.mean_returns,
                "median_return_1h": b.median_return_1h,
                "mean_mfe_pct": b.mean_mfe_pct,
                "mean_mae_pct": b.mean_mae_pct,
                "mean_score": b.mean_score,
                "note": b.note,
            }
            for b in summary.buckets
        ],
    }


def _result_dict(r: ResearchCalibrationResult) -> dict:
    return {
        "symbol": r.symbol,
        "research_score": r.research_score,
        "data_confidence": r.data_confidence,
        "risk_score": r.risk_score,
        "direction": r.direction,
        "bucket": r.bucket,
        "entry_time": r.entry_time,
        "entry_price": r.entry_price,
        "ret_5m": r.ret_5m,
        "ret_15m": r.ret_15m,
        "ret_30m": r.ret_30m,
        "ret_1h": r.ret_1h,
        "mfe_pct": r.mfe_pct,
        "mae_pct": r.mae_pct,
        "measurable": r.measurable,
        "directionless": r.directionless,
        "note": r.note,
    }
