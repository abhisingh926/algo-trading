"""Historical setup statistics. Answers questions such as "how did this stock behave after a gap-up with high
volume above VWAP?" strictly from data the platform holds.

Rules enforced here:
  * statistics are only stated when the sample reaches `min_sample`; below that only the count is shown,
  * the current (incomplete) session is never part of the sample, so nothing looks into the future,
  * every stat reports its sample size, period, and the average return after estimated trading costs.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from app.research import sessions as ses
from app.research.contracts import HistoricalAnalysis, PatternStat, Provenance
from app.utils.time import IST

HORIZONS = {"15m": 1, "30m": 2, "1h": 4}  # in 15-minute bars
PRIMARY = "1h"
REACH_LEVELS = (0.3, 0.5, 1.0)
GAP_THRESHOLD = 0.3  # percent
HIGH_RVOL = 1.5
NORMAL_RVOL = 0.8


@dataclass(slots=True)
class Outcome:
    day: date
    returns: dict[str, float]  # aligned percent return at each horizon
    mfe: float  # best aligned excursion within the primary horizon
    mae: float  # worst aligned excursion (<= 0)


@dataclass(slots=True)
class SessionCache:
    session: ses.Session
    vwap: list[float]
    cum_volume: list[float]  # cum_volume[k] = volume of the first k bars
    prev_close: float | None


def ses_time(bar: object) -> str:
    from datetime import timedelta

    return (bar.timestamp + timedelta(minutes=15)).astimezone(IST).strftime("%H:%M")  # type: ignore[attr-defined]


def _cache(sessions: list[ses.Session]) -> list[SessionCache]:
    out, prev_close = [], None
    for s in sessions:
        cum, total = [0.0], 0.0
        for b in s.bars:
            total += b.volume
            cum.append(total)
        out.append(SessionCache(s, ses.vwap_series(s.bars), cum, prev_close))
        prev_close = s.bars[-1].close
    return out


def _rvol_at(caches: list[SessionCache], idx: int, k: int) -> float | None:
    past = [c.cum_volume[k] for c in caches[max(0, idx - 20) : idx] if len(c.session.bars) >= k]
    if not past:
        return None
    mean = statistics.fmean(past)
    return caches[idx].cum_volume[k] / mean if mean else None


def _conditions(caches: list[SessionCache], idx: int, k: int) -> tuple[str, str, str] | None:
    """(gap bucket, VWAP side, volume bucket) after the first k bars of session idx."""
    c = caches[idx]
    if k < 1 or k > len(c.session.bars) or not c.prev_close:
        return None
    gap = (c.session.bars[0].open / c.prev_close - 1) * 100
    gap_bucket = "GAP_UP" if gap >= GAP_THRESHOLD else "GAP_DOWN" if gap <= -GAP_THRESHOLD else "NO_GAP"
    side = "ABOVE_VWAP" if c.session.bars[k - 1].close > c.vwap[k - 1] else "BELOW_VWAP"
    rvol = _rvol_at(caches, idx, k)
    if rvol is None:
        return None
    vol_bucket = "HIGH_RVOL" if rvol >= HIGH_RVOL else "NORMAL_RVOL" if rvol >= NORMAL_RVOL else "LOW_RVOL"
    return gap_bucket, side, vol_bucket


def _forward(session: ses.Session, k: int, bias: int) -> Outcome | None:
    """Aligned outcome after a decision taken at the close of bar k-1. None if the future bars do not exist."""
    horizon = max(HORIZONS.values())
    if k < 1 or k + horizon > len(session.bars):
        return None
    p0 = session.bars[k - 1].close
    if not p0:
        return None
    returns = {name: (session.bars[k - 1 + n].close / p0 - 1) * 100 * bias for name, n in HORIZONS.items()}
    window = session.bars[k : k + horizon]
    if bias > 0:
        mfe, mae = (max(b.high for b in window) / p0 - 1) * 100, (min(b.low for b in window) / p0 - 1) * 100
    else:
        mfe, mae = (1 - min(b.low for b in window) / p0) * 100, (1 - max(b.high for b in window) / p0) * 100
    return Outcome(ses.ist_day(session.bars[0].timestamp), returns, mfe, min(mae, 0.0))


def make_stat(
    key: str,
    label: str,
    description: str,
    horizon: str,
    outcomes: list[Outcome],
    min_sample: int,
    cost_pct: float,
    period: tuple[str | None, str | None],
    note: str | None = None,
    horizon_label: str | None = None,
) -> PatternStat:
    n = len(outcomes)
    adequate = n >= min_sample
    base = dict(
        key=key,
        label=label,
        description=description,
        horizon=horizon_label or horizon,
        occurrences=n,
        sample_adequate=adequate,
        min_sample=min_sample,
        period_start=period[0],
        period_end=period[1],
    )
    if not adequate:
        extra = f"Only {n} occurrences; at least {min_sample} are needed before any statistic is shown."
        return PatternStat(**base, note=f"{note} {extra}" if note else extra)
    rets = [o.returns[horizon] for o in outcomes]
    wins = sum(1 for r in rets if r > 0)
    avg = statistics.fmean(rets)
    mfes = [o.mfe for o in outcomes]
    reach = {str(level): round(sum(1 for m in mfes if m >= level) / n * 100, 1) for level in REACH_LEVELS}
    return PatternStat(
        **base,
        successful=wins,
        success_rate=round(wins / n * 100, 1),
        avg_return_pct=round(avg, 3),
        median_return_pct=round(statistics.median(rets), 3),
        avg_return_net_pct=round(avg - cost_pct, 3),
        mfe_pct=round(statistics.fmean(mfes), 3),
        mae_pct=round(statistics.fmean(o.mae for o in outcomes), 3),
        horizon_returns_pct={h: round(statistics.fmean(o.returns[h] for o in outcomes), 3) for h in HORIZONS},
        reach_probability=reach,
        note=note,
    )


def _current_state(caches: list[SessionCache]) -> tuple[int, int, tuple[str, str, str] | None]:
    """(bars actually seen today, bars used for the setup, setup conditions).

    A one-hour outcome needs one hour of session left, so late in the session (or once it has closed) the setup is
    evaluated at the last time of day where that is still possible, and the report says so."""
    idx = len(caches) - 1
    seen = len(caches[idx].session.bars)
    session_bars = max(len(c.session.bars) for c in caches[-10:])
    k = min(seen, session_bars - max(HORIZONS.values()))
    return seen, k, (_conditions(caches, idx, k) if k >= 1 else None)


def analyze(
    sessions: list[ses.Session], provenance: Provenance, min_sample: int = 30, cost_pct: float = 0.10
) -> HistoricalAnalysis:
    """`sessions` must be complete regular sessions plus the current (possibly partial) one as the LAST item."""
    warnings: list[str] = []
    if len(sessions) < 40:
        return HistoricalAnalysis(
            sessions_analyzed=max(len(sessions) - 1, 0),
            period_start=None,
            period_end=None,
            setups=[],
            warnings=[
                f"Only {len(sessions) - 1} historical sessions available; at least 40 are needed for setup statistics."
            ],
            estimated_round_trip_cost_pct=cost_pct,
            provenance=provenance,
        )
    caches = _cache(sessions)
    history = caches[:-1]  # the current session is excluded from every sample
    period = (history[0].session.day.isoformat(), history[-1].session.day.isoformat())
    stats: list[PatternStat] = []
    seen_now, k_now, state = _current_state(caches)

    # 1. today's setup, from the exact condition set down to the loosest one
    current_key = current_label = None
    matched: PatternStat | None = None
    if state:
        gap_b, side, vol_b = state
        bias = 1 if side == "ABOVE_VWAP" else -1
        current_key = f"{gap_b}|{side}|{vol_b}"
        current_label = f"{gap_b.replace('_', ' ').title()}, {vol_b.replace('_', ' ').lower()}, {side.replace('_', ' ').lower()}"
        if k_now < seen_now:
            clock = ses_time(caches[-1].session.bars[k_now - 1])
            warnings.append(
                f"Setup evaluated as of {clock} IST: the last point in the session where a one-hour outcome can still be measured."
            )
        tiers = [
            ("SETUP_EXACT", f"Same setup: {current_label}", lambda c: c == (gap_b, side, vol_b)),
            (
                "SETUP_GAP_VWAP",
                f"Gap and VWAP side: {gap_b.replace('_', ' ').lower()}, {side.replace('_', ' ').lower()}",
                lambda c: c[:2] == (gap_b, side),
            ),
            (
                "SETUP_VWAP",
                f"VWAP side at this time of day: {side.replace('_', ' ').lower()}",
                lambda c: c[1] == side,
            ),
        ]
        for key, label, predicate in tiers:
            outcomes = []
            for i, c in enumerate(history):
                cond = _conditions(caches, i, k_now)
                if cond is None or not predicate(cond):
                    continue
                outcome = _forward(c.session, k_now, bias)
                if outcome:
                    outcomes.append(outcome)
            stat = make_stat(
                key,
                label,
                f"Days that looked like this after {k_now * 15} minutes of trading; outcome measured after the same time of day.",
                PRIMARY,
                outcomes,
                min_sample,
                cost_pct,
                period,
                note=f"Direction assumed {'long' if bias > 0 else 'short'} (price {'above' if bias > 0 else 'below'} VWAP).",
            )
            stats.append(stat)
            if matched is None and stat.sample_adequate:
                matched = stat
    else:
        warnings.append(
            "Today's setup could not be classified yet (not enough volume history at this time of day)."
        )

    # 2. VWAP crosses (all bars, all past sessions)
    for direction, bias in (("UP", 1), ("DOWN", -1)):
        outcomes, reversals = [], 0
        for c in history:
            bars, vwap = c.session.bars, c.vwap
            for i in range(2, len(bars)):
                crossed = (
                    (bars[i - 1].close <= vwap[i - 1] and bars[i].close > vwap[i])
                    if bias > 0
                    else (bars[i - 1].close >= vwap[i - 1] and bars[i].close < vwap[i])
                )
                if not crossed:
                    continue
                outcome = _forward(c.session, i + 1, bias)
                if outcome:
                    outcomes.append(outcome)
                    back = any(
                        (b.close < v) if bias > 0 else (b.close > v)
                        for b, v in zip(bars[i + 1 : i + 5], vwap[i + 1 : i + 5], strict=True)
                    )
                    reversals += 1 if back else 0
        note = (
            f"Price closed back on the other side of VWAP within an hour in {reversals / len(outcomes) * 100:.0f}% of cases."
            if outcomes
            else None
        )
        stats.append(
            make_stat(
                f"VWAP_CROSS_{direction}",
                f"Cross {'above' if bias > 0 else 'below'} VWAP",
                "A close crossing VWAP, measured over the next hour.",
                PRIMARY,
                outcomes,
                min_sample,
                cost_pct,
                period,
                note,
            )
        )

    # 3. opening range breakouts (first 30 minutes)
    for direction, bias in (("UP", 1), ("DOWN", -1)):
        outcomes = []
        for c in history:
            bars = c.session.bars
            if len(bars) < 8:
                continue
            high, low = max(b.high for b in bars[:2]), min(b.low for b in bars[:2])
            for i in range(2, len(bars)):
                if (bias > 0 and bars[i].close > high) or (bias < 0 and bars[i].close < low):
                    outcome = _forward(c.session, i + 1, bias)
                    if outcome:
                        outcomes.append(outcome)
                    break  # first breakout of the day only
        stats.append(
            make_stat(
                f"ORB_{direction}",
                f"Opening-range breakout {'up' if bias > 0 else 'down'}",
                "First close beyond the 09:15 to 09:45 range, measured over the next hour.",
                PRIMARY,
                outcomes,
                min_sample,
                cost_pct,
                period,
            )
        )

    # 4. gap behaviour (session level)
    for direction, bias in (("UP", 1), ("DOWN", -1)):
        gap_days = []
        for c in history:
            if not c.prev_close:
                continue
            gap = (c.session.bars[0].open / c.prev_close - 1) * 100
            if (bias > 0 and gap >= GAP_THRESHOLD) or (bias < 0 and gap <= -GAP_THRESHOLD):
                gap_days.append(c)
        n = len(gap_days)
        if n >= min_sample:
            filled = sum(
                1
                for c in gap_days
                if (
                    min(b.low for b in c.session.bars) <= c.prev_close
                    if bias > 0
                    else max(b.high for b in c.session.bars) >= c.prev_close
                )
            )
            cont = [(c.session.bars[-1].close / c.session.bars[0].open - 1) * 100 * bias for c in gap_days]
            stats.append(
                PatternStat(
                    key=f"GAP_{direction}_FILL",
                    label=f"Gap {direction.lower()} fill",
                    description="Share of gap days on which price returned to the previous close within the session.",
                    horizon="session",
                    occurrences=n,
                    successful=filled,
                    success_rate=round(filled / n * 100, 1),
                    avg_return_pct=round(statistics.fmean(cont), 3),
                    median_return_pct=round(statistics.median(cont), 3),
                    avg_return_net_pct=round(statistics.fmean(cont) - cost_pct, 3),
                    sample_adequate=True,
                    min_sample=min_sample,
                    period_start=period[0],
                    period_end=period[1],
                    note=f"Return shown is open to close in the direction of the gap; {sum(1 for r in cont if r > 0) / n * 100:.0f}% of gaps continued to the close.",
                )
            )
        else:
            stats.append(
                make_stat(
                    f"GAP_{direction}_FILL",
                    f"Gap {direction.lower()} fill",
                    "Share of gap days on which price returned to the previous close.",
                    "session",
                    [],
                    min_sample,
                    cost_pct,
                    period,
                    f"{n} gap days found.",
                )
            )
            stats[-1].occurrences = n

    # 5. daily breakouts: does a 20-day high/low break continue the next session?
    daily = [c.session for c in history]
    d_out_up: list[Outcome] = []
    d_out_dn: list[Outcome] = []
    for i in range(21, len(daily) - 1):
        today, nxt = daily[i].bars, daily[i + 1].bars
        prior = daily[i - 20 : i]
        close = today[-1].close
        prior_high, prior_low = max(b.high for s in prior for b in s.bars), min(
            b.low for s in prior for b in s.bars
        )
        for bias, hit, sink in ((1, close > prior_high, d_out_up), (-1, close < prior_low, d_out_dn)):
            if hit:
                nxt_close = nxt[-1].close
                r = (nxt_close / close - 1) * 100 * bias
                hi, lo = max(b.high for b in nxt), min(b.low for b in nxt)
                mfe = ((hi / close - 1) if bias > 0 else (1 - lo / close)) * 100
                mae = min(((lo / close - 1) if bias > 0 else (1 - hi / close)) * 100, 0.0)
                sink.append(Outcome(daily[i + 1].day, {"15m": r, "30m": r, "1h": r}, mfe, mae))
    stats.append(
        make_stat(
            "BREAKOUT_20D_UP",
            "20-day high breakout",
            "Daily close above the prior 20-day high, measured to the next session's close.",
            PRIMARY,
            d_out_up,
            min_sample,
            cost_pct,
            period,
            "Horizon is the next session, not one hour.",
            horizon_label="next session",
        )
    )
    stats.append(
        make_stat(
            "BREAKOUT_20D_DOWN",
            "20-day low breakdown",
            "Daily close below the prior 20-day low, measured to the next session's close.",
            PRIMARY,
            d_out_dn,
            min_sample,
            cost_pct,
            period,
            "Horizon is the next session, not one hour.",
            horizon_label="next session",
        )
    )

    # 6. how far does this stock normally move?
    baseline: dict[str, float] = {}
    for name, n in HORIZONS.items():
        moves = [
            abs(c.session.bars[i + n].close / c.session.bars[i].close - 1) * 100
            for c in history
            for i in range(len(c.session.bars) - n)
        ]
        if moves:
            baseline[name] = round(statistics.fmean(moves), 3)

    thin = [s for s in stats if not s.sample_adequate]
    if matched is None and state:
        warnings.append(
            "No historical sample of today's setup is large enough to be reliable, so no historical edge is claimed."
        )
    if thin:
        warnings.append(
            f"{len(thin)} of {len(stats)} setup statistics have too few occurrences and are shown without rates."
        )
    return HistoricalAnalysis(
        sessions_analyzed=len(history),
        period_start=period[0],
        period_end=period[1],
        current_setup_key=current_key,
        current_setup_label=current_label,
        matched=matched,
        setups=stats,
        baseline_moves=baseline,
        estimated_round_trip_cost_pct=cost_pct,
        warnings=warnings,
        provenance=provenance,
    )
