"""Post-market calibration: what actually happened after each research score.

This is the only honest way to answer "does the Research Score mean anything". It takes scores that were
produced at a point in time, measures the market that followed, and reports the outcome by score bucket.

Discipline enforced here:
  * the outcome is measured strictly AFTER the moment the score was produced, entering at the open of the first
    bar that starts at or after it, so nothing the score could not have known is used,
  * the measurement stops at the end of the trading session; an hour is never stitched across an overnight gap,
  * a horizon with incomplete data is recorded as missing rather than filled in,
  * results are direction-aligned, so a bearish call is judged on the market falling,
  * a bucket below the minimum sample reports its count and no rates.

Nothing here asserts that a higher score causes a better outcome. It reports what was measured.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.types import Candle
from app.research.sessions import ist_day

HORIZON_MINUTES: dict[str, int] = {"5m": 5, "15m": 15, "30m": 30, "1h": 60}
BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("90-100", 90.0, 100.01),
    ("80-89", 80.0, 90.0),
    ("70-79", 70.0, 80.0),
    ("60-69", 60.0, 70.0),
    ("50-59", 50.0, 60.0),
    ("below-50", -0.01, 50.0),
)
MIN_BUCKET_SAMPLE = 30
NEUTRAL_NOTE = (
    "Neutral setups have no direction to judge, so they are measured but kept out of the aggregates."
)


def bucket_of(score: float) -> str:
    for name, low, high in BUCKETS:
        if low <= score < high:
            return name
    return BUCKETS[-1][0]


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    """What a completed run recorded for one symbol, plus the direction it was judged in."""

    run_id: str
    symbol: str
    as_of: datetime
    research_score: float
    data_confidence: float
    risk_score: float | None
    direction: str  # BULLISH | BEARISH | NEUTRAL


@dataclass(frozen=True, slots=True)
class Outcome:
    candidate: ScoredCandidate
    entry_time: datetime
    entry_price: float
    returns: dict[str, float | None]  # direction-aligned percent per horizon; None when not measurable
    mfe_pct: float | None
    mae_pct: float | None
    bars_source: str
    horizons_complete: int
    directionless: bool

    @property
    def primary(self) -> float | None:
        return self.returns.get("1h")


def _bar_minutes(bars: list[Candle]) -> int:
    if len(bars) >= 2:
        return max(int((bars[1].timestamp - bars[0].timestamp).total_seconds() // 60), 1)
    return 15


def measure(candidate: ScoredCandidate, bars: list[Candle], bars_source: str) -> Outcome | None:
    """Measure the session that followed. `bars` must be regular-session bars, oldest first.

    Returns None when the market that followed is not in the data at all, so an unmeasurable candidate is never
    silently counted as a flat result.
    """
    after = [b for b in bars if b.timestamp >= candidate.as_of]
    if not after:
        return None
    entry = after[0]
    day = ist_day(entry.timestamp)
    session = [b for b in after if ist_day(b.timestamp) == day]
    if entry.open <= 0:
        return None
    step = _bar_minutes(session)
    sign = {"BULLISH": 1.0, "BEARISH": -1.0}.get(candidate.direction, 1.0)
    directionless = candidate.direction not in ("BULLISH", "BEARISH")

    returns: dict[str, float | None] = {}
    for name, minutes in HORIZON_MINUTES.items():
        # Entering at the open of session[0], `minutes` later is the CLOSE of the bar at this index.
        index = minutes // step - 1
        if index < 0 or index >= len(session):
            returns[name] = None  # the horizon is shorter than one bar, or the session ended first
            continue
        returns[name] = round((session[index].close / entry.open - 1) * 100 * sign, 4)
    window = session[: max(HORIZON_MINUTES.values()) // step]
    mfe = mae = None
    if window:
        highs = [(b.high / entry.open - 1) * 100 for b in window]
        lows = [(b.low / entry.open - 1) * 100 for b in window]
        if sign > 0:
            mfe, mae = round(max(highs), 4), round(min(lows), 4)
        else:
            mfe, mae = round(-min(lows), 4), round(-max(highs), 4)
    return Outcome(
        candidate=candidate,
        entry_time=entry.timestamp,
        entry_price=entry.open,
        returns=returns,
        mfe_pct=mfe,
        mae_pct=min(mae, 0.0) if mae is not None else None,
        bars_source=bars_source,
        horizons_complete=sum(1 for v in returns.values() if v is not None),
        directionless=directionless,
    )


# ---- aggregation -------------------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class BucketResult:
    bucket: str
    occurrences: int
    sample_adequate: bool
    min_sample: int
    win_rate: float | None  # share with a positive one-hour result
    mean_returns: dict[str, float | None]
    median_return_1h: float | None
    mean_mfe_pct: float | None
    mean_mae_pct: float | None
    mean_score: float | None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    measured: int
    directionless_excluded: int
    unmeasurable: int
    buckets: list[BucketResult]
    ordered_as_expected: bool | None  # do higher buckets show better one-hour results?
    adequate_buckets: int
    period_start: str | None
    period_end: str | None
    verdict: str
    caveats: list[str]


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 4) if values else None


def summarise(outcomes: list[Outcome], min_sample: int = MIN_BUCKET_SAMPLE) -> CalibrationSummary:
    usable = [o for o in outcomes if not o.directionless and o.primary is not None]
    directionless = sum(1 for o in outcomes if o.directionless)
    unmeasurable = sum(1 for o in outcomes if not o.directionless and o.primary is None)

    by_bucket: dict[str, list[Outcome]] = {name: [] for name, _, _ in BUCKETS}
    for outcome in usable:
        by_bucket[bucket_of(outcome.candidate.research_score)].append(outcome)

    results: list[BucketResult] = []
    for name, _, _ in BUCKETS:
        group = by_bucket[name]
        n = len(group)
        adequate = n >= min_sample
        if not adequate:
            results.append(
                BucketResult(
                    bucket=name,
                    occurrences=n,
                    sample_adequate=False,
                    min_sample=min_sample,
                    win_rate=None,
                    mean_returns={h: None for h in HORIZON_MINUTES},
                    median_return_1h=None,
                    mean_mfe_pct=None,
                    mean_mae_pct=None,
                    mean_score=_mean([o.candidate.research_score for o in group]) if group else None,
                    note=f"{n} measured; at least {min_sample} are needed before a rate is shown.",
                )
            )
            continue
        primaries = [o.primary for o in group if o.primary is not None]
        results.append(
            BucketResult(
                bucket=name,
                occurrences=n,
                sample_adequate=True,
                min_sample=min_sample,
                win_rate=round(sum(1 for r in primaries if r > 0) / len(primaries) * 100, 2),
                mean_returns={
                    h: _mean([o.returns[h] for o in group if o.returns.get(h) is not None])  # type: ignore[misc]
                    for h in HORIZON_MINUTES
                },
                median_return_1h=round(statistics.median(primaries), 4),
                mean_mfe_pct=_mean([o.mfe_pct for o in group if o.mfe_pct is not None]),
                mean_mae_pct=_mean([o.mae_pct for o in group if o.mae_pct is not None]),
                mean_score=_mean([o.candidate.research_score for o in group]),
            )
        )

    adequate = [r for r in results if r.sample_adequate]
    ordered: bool | None = None
    if len(adequate) >= 2:
        # BUCKETS runs from the highest score downwards, so a score that tracked outcomes would fall as we go.
        means = [r.mean_returns["1h"] for r in adequate if r.mean_returns["1h"] is not None]
        ordered = all(a >= b for a, b in zip(means, means[1:], strict=False)) if len(means) >= 2 else None

    days = sorted(ist_day(o.candidate.as_of).isoformat() for o in usable)
    caveats = [
        "Measured outcomes, not a prediction. A pattern here is evidence about the past, not proof the score works.",
        NEUTRAL_NOTE,
        "Returns exclude brokerage, taxes and slippage, so a small positive average is not a profit.",
    ]
    if len(adequate) < 2:
        caveats.append("Too few buckets have an adequate sample to compare them against each other.")
    if unmeasurable:
        caveats.append(
            f"{unmeasurable} candidate(s) could not be measured because the following market data is missing."
        )

    if not adequate:
        verdict = "Not enough measured outcomes yet to say anything about the score."
    elif ordered is True:
        verdict = "Higher score buckets showed better average outcomes over this sample. That is consistent with the score being informative, and is not proof."
    elif ordered is False:
        verdict = "Higher score buckets did NOT show better average outcomes over this sample. Treat the score with caution."
    else:
        verdict = "Only one bucket has an adequate sample, so the buckets cannot be compared yet."

    return CalibrationSummary(
        measured=len(usable),
        directionless_excluded=directionless,
        unmeasurable=unmeasurable,
        buckets=results,
        ordered_as_expected=ordered,
        adequate_buckets=len(adequate),
        period_start=days[0] if days else None,
        period_end=days[-1] if days else None,
        verdict=verdict,
        caveats=caveats,
    )


def horizon_end(as_of: datetime) -> datetime:
    """The earliest moment at which a run can be fully calibrated."""
    return as_of + timedelta(minutes=max(HORIZON_MINUTES.values()))
