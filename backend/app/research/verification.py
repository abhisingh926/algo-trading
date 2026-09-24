"""Verification: compare observations of the same fact and never hide a disagreement.

Independence matters. Two feeds from ONE provider are one origin, so they can show internal consistency
(PARTIALLY_VERIFIED) but cannot reach VERIFIED. VERIFIED needs agreement between at least two independent origins.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.domain.types import Candle
from app.research import sessions as ses
from app.research.contracts import (
    ConfidenceBreakdown,
    Provenance,
    SourceValue,
    VerificationClaim,
    VerificationReport,
)
from app.utils.time import IST, ensure_utc

STATUS_WEIGHT = {
    "VERIFIED": 1.0,
    "PARTIALLY_VERIFIED": 0.7,
    "UNVERIFIED": 0.4,
    "CONFLICTING": 0.15,
    "STALE": 0.25,
}
SYNTHETIC_CONFIDENCE_CAP = 30.0


@dataclass(slots=True)
class Observation:
    source: str
    origin: str
    value: float | str | bool
    as_of: datetime | None
    reliability: float


def _values(observations: list[Observation]) -> list[SourceValue]:
    return [
        SourceValue(
            source=o.source, origin=o.origin, value=o.value, data_as_of=o.as_of, reliability=o.reliability
        )
        for o in observations
    ]


def verify_numeric(
    key: str,
    claim: str,
    observations: list[Observation],
    tolerance_pct: float,
    now: datetime,
    max_age_minutes: float | None = None,
) -> VerificationClaim:
    values = _values(observations)
    if not observations:
        return VerificationClaim(
            key=key,
            claim=claim,
            status="UNVERIFIED",
            confidence=0.0,
            sources_checked=0,
            independent_origins=0,
            values=[],
            tolerance_pct=tolerance_pct,
            detail="No source returned a value.",
        )
    origins = {o.origin for o in observations}
    if max_age_minutes is not None:
        dated = [o for o in observations if o.as_of is not None]
        if dated and all((ensure_utc(now) - ensure_utc(o.as_of)).total_seconds() / 60 > max_age_minutes for o in dated):  # type: ignore[arg-type]
            return VerificationClaim(
                key=key,
                claim=claim,
                status="STALE",
                confidence=0.2,
                sources_checked=len(observations),
                independent_origins=len(origins),
                values=values,
                tolerance_pct=tolerance_pct,
                detail=f"Every source is older than {max_age_minutes:g} minutes.",
            )
    if len(observations) == 1:
        o = observations[0]
        return VerificationClaim(
            key=key,
            claim=claim,
            status="UNVERIFIED",
            confidence=round(o.reliability * 0.5, 2),
            sources_checked=1,
            independent_origins=1,
            values=values,
            tolerance_pct=tolerance_pct,
            detail="Only one source, so this cannot be cross-checked.",
        )
    numbers = [float(o.value) for o in observations]  # type: ignore[arg-type]
    mean = sum(numbers) / len(numbers)
    spread_pct = (max(numbers) - min(numbers)) / abs(mean) * 100 if mean else 0.0
    if spread_pct <= tolerance_pct:
        if len(origins) >= 2:
            confidence = 1.0
            for origin in origins:
                r = max(o.reliability for o in observations if o.origin == origin)
                confidence *= 1 - 0.9 * r
            return VerificationClaim(
                key=key,
                claim=claim,
                status="VERIFIED",
                confidence=round(min(0.99, 1 - confidence), 2),
                sources_checked=len(observations),
                independent_origins=len(origins),
                values=values,
                tolerance_pct=tolerance_pct,
                detail=f"{len(origins)} independent origins agree within {spread_pct:.2f}%.",
            )
        origin_reliability = max(o.reliability for o in observations)
        return VerificationClaim(
            key=key,
            claim=claim,
            status="PARTIALLY_VERIFIED",
            confidence=round(origin_reliability * 0.6, 2),
            sources_checked=len(observations),
            independent_origins=1,
            values=values,
            tolerance_pct=tolerance_pct,
            detail=f"{len(observations)} feeds agree within {spread_pct:.2f}%, but they come from a single provider, so this shows internal consistency, not independent confirmation.",
        )
    return VerificationClaim(
        key=key,
        claim=claim,
        status="CONFLICTING",
        confidence=round(0.3 * sum(o.reliability for o in observations) / len(observations), 2),
        sources_checked=len(observations),
        independent_origins=len(origins),
        values=values,
        tolerance_pct=tolerance_pct,
        detail=f"Sources differ by {spread_pct:.2f}%, more than the {tolerance_pct:g}% tolerance.",
        resolution="Awaiting verification. No value was chosen.",
    )


def integrity_issues(bars: list[Candle], recent_sessions: int = 10) -> list[str]:
    """Sanity checks on the bar data itself."""
    issues: list[str] = []
    seen: set[datetime] = set()
    bad_ohlc = negative = duplicates = 0
    for b in bars:
        if b.high < max(b.open, b.close) - 1e-9 or b.low > min(b.open, b.close) + 1e-9 or b.high < b.low:
            bad_ohlc += 1
        if b.volume < 0 or min(b.open, b.high, b.low, b.close) <= 0:
            negative += 1
        if b.timestamp in seen:
            duplicates += 1
        seen.add(b.timestamp)
    if bad_ohlc:
        issues.append(f"{bad_ohlc} bar(s) with inconsistent open/high/low/close")
    if negative:
        issues.append(f"{negative} bar(s) with non-positive prices or negative volume")
    if duplicates:
        issues.append(f"{duplicates} duplicated timestamp(s)")
    sessions = ses.group_sessions(bars)[-(recent_sessions + 1) : -1]
    short = [s.day.isoformat() for s in sessions if len(s.bars) < 20]
    if short:
        issues.append(f"{len(short)} recent session(s) with missing bars ({', '.join(short[:3])})")
    return issues


def verify_integrity(bars: list[Candle], origin: str, reliability: float) -> VerificationClaim:
    issues = integrity_issues(bars)
    observation = [Observation("stored candles", origin, not issues, None, reliability)]
    if issues:
        return VerificationClaim(
            key="data_integrity",
            claim="Price bars are internally consistent",
            status="CONFLICTING",
            confidence=0.2,
            sources_checked=1,
            independent_origins=1,
            values=_values(observation),
            detail="; ".join(issues),
            resolution="Awaiting verification. Bars with problems were not corrected or removed.",
        )
    return VerificationClaim(
        key="data_integrity",
        claim="Price bars are internally consistent",
        status="PARTIALLY_VERIFIED",
        confidence=round(reliability * 0.6, 2),
        sources_checked=1,
        independent_origins=1,
        values=_values(observation),
        detail=f"{len(bars):,} bars passed structural checks (OHLC order, positive prices, no duplicates, no recent gaps). This is a consistency check on one source.",
    )


def expected_last_session(now: datetime) -> date:
    """The most recent regular session that has started by `now` (exchange holidays are not known here)."""
    local = ensure_utc(now).astimezone(IST)
    day = local.date()
    if local.weekday() < 5 and local.time() >= ses.MARKET_OPEN:
        return day
    day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


LIVE_MINUTES = 5.0


def freshness_label(age_minutes: float, state: str, stale: bool) -> str:
    """LIVE, RECENT or STALE. While the market is closed nothing can be live, so the best available is RECENT."""
    if stale:
        return "STALE"
    if state != "OPEN":
        return "RECENT"
    return "LIVE" if age_minutes <= LIVE_MINUTES else "RECENT"


def freshness(
    now: datetime, data_as_of: datetime, state: str, stale_minutes_open: float = 20.0
) -> tuple[float, bool, str | None]:
    """(score 0..1, stale?, message)."""
    age_min = max((ensure_utc(now) - ensure_utc(data_as_of)).total_seconds() / 60, 0.0)
    if state == "OPEN":
        if age_min <= stale_minutes_open:
            return 1.0, False, None
        score = 0.6 if age_min <= 60 else 0.2
        return score, True, f"Data is {age_min:.0f} minutes old while the market is open"
    data_day = ses.ist_day(ensure_utc(data_as_of) - timedelta(seconds=1))
    expected = expected_last_session(now)
    if data_day == expected:
        return 1.0, False, None
    gap = 0
    cursor = expected
    while cursor > data_day and gap < 10:
        cursor -= timedelta(days=1)
        gap += 1 if cursor.weekday() < 5 else 0
    if gap <= 1:
        return (
            0.6,
            True,
            f"Latest data is from {data_day.isoformat()}, but the last session was expected on {expected.isoformat()} (holiday or missing data)",
        )
    return (
        0.2,
        True,
        f"Latest data is from {data_day.isoformat()}, {gap} sessions behind the expected {expected.isoformat()}",
    )


def finalize(
    claims: list[VerificationClaim],
    source_reliability: float,
    freshness_score: float,
    completeness: float,
    sample_adequate: bool,
    is_synthetic: bool,
    provenance: Provenance,
) -> VerificationReport:
    verification = (
        sum(STATUS_WEIGHT[c.status] for c in claims) / len(claims) if claims else STATUS_WEIGHT["UNVERIFIED"]
    )
    sample = 1.0 if sample_adequate else 0.6
    raw = 100 * (
        0.35 * source_reliability
        + 0.20 * freshness_score
        + 0.20 * verification
        + 0.15 * completeness
        + 0.10 * sample
    )
    capped = is_synthetic and raw > SYNTHETIC_CONFIDENCE_CAP
    confidence = min(raw, SYNTHETIC_CONFIDENCE_CAP) if is_synthetic else raw
    return VerificationReport(
        claims=claims,
        conflicts_found=sum(1 for c in claims if c.status == "CONFLICTING"),
        sources_checked=sum(c.sources_checked for c in claims),
        data_confidence=round(confidence, 1),
        provenance=provenance,
        breakdown=ConfidenceBreakdown(
            source_reliability=round(source_reliability, 3),
            freshness=round(freshness_score, 3),
            verification=round(verification, 3),
            completeness=round(completeness, 3),
            sample_adequacy=sample,
            synthetic_cap_applied=capped,
        ),
    )
