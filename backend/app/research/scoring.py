"""Deterministic research scoring. Every number comes from explicit rules over measured data. There is no LLM
and no free-form judgement anywhere in this module; each component returns its evidence so it can be audited.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.research.config import COMPONENT_LABELS, COMPONENT_ORDER, RISK_DEDUCTION
from app.research.contracts import (
    EvidenceItem,
    HistoricalAnalysis,
    MarketContext,
    PriceBlock,
    RiskFlag,
    ScoreComponent,
    ScoreResult,
    SectorSnapshot,
    TechnicalAnalysis,
    TimeframeTechnical,
    VolatilityBlock,
)


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def lin(x: float, lo: float, hi: float) -> float:
    return clip((x - lo) / (hi - lo)) if hi != lo else 0.0


def trapezoid(x: float, zero_low: float, ideal_low: float, ideal_high: float, zero_high: float) -> float:
    if x <= zero_low or x >= zero_high:
        return 0.0
    if x < ideal_low:
        return (x - zero_low) / (ideal_low - zero_low)
    if x <= ideal_high:
        return 1.0
    return (zero_high - x) / (zero_high - ideal_high)


def interpolate(x: float, points: list[tuple[float, float]]) -> float:
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def tick(score: float) -> bool | None:
    """Evidence mark that follows the sub-score: a tick when favourable, a cross when clearly not, else neutral."""
    return True if score >= 0.6 else False if score <= 0.3 else None


def rating_of(fraction: float, available: bool = True) -> str:
    if not available:
        return "UNAVAILABLE"
    return (
        "EXCELLENT"
        if fraction >= 0.8
        else "GOOD" if fraction >= 0.6 else "FAIR" if fraction >= 0.4 else "POOR"
    )


@dataclass(slots=True)
class ScoringInput:
    price: PriceBlock
    volatility: VolatilityBlock
    technical: TechnicalAnalysis
    historical: HistoricalAnalysis | None
    risk_flags: list[RiskFlag]
    unavailable_checks: list[str]
    market: MarketContext
    sector: SectorSnapshot | None
    source_key: str
    thresholds: dict[str, Any]
    extra_notes: list[str] = field(default_factory=list)


def _direction_sign(direction: str) -> int:
    return 1 if direction == "BULLISH" else -1 if direction == "BEARISH" else 0


def _tf(technical: TechnicalAnalysis, name: str) -> TimeframeTechnical | None:
    return next((t for t in technical.timeframes if t.timeframe == name and t.bars >= 15), None)


def _component(
    key: str,
    weights: dict[str, float],
    fraction: float | None,
    summary: str,
    evidence: list[EvidenceItem],
    metrics: dict[str, Any],
    source: str | None,
) -> ScoreComponent:
    available = fraction is not None
    frac = clip(fraction) if fraction is not None else 0.0
    return ScoreComponent(
        key=key,
        label=COMPONENT_LABELS[key],
        points=round(frac * weights[key], 2),
        max_points=weights[key],
        available=available,
        rating=rating_of(frac, available),
        summary=summary,
        evidence=evidence,
        metrics=metrics,
        sources=[source] if source and available else [],
    )


def _mean_weighted(parts: list[tuple[float, float]]) -> float | None:
    total = sum(w for _, w in parts)
    return sum(v * w for v, w in parts) / total if total else None


# ---- components ----------------------------------------------------------------------------------------------
def score_liquidity(inp: ScoringInput, weights: dict[str, float]) -> ScoreComponent:
    t, p = inp.thresholds, inp.price
    parts, evidence = [], []
    value = p.avg_traded_value_cr
    if value:
        sub = lin(
            math.log10(max(value, 1e-6)),
            math.log10(t["liquidity_value_lo_cr"]),
            math.log10(t["liquidity_value_hi_cr"]),
        )
        parts.append((sub, 0.6))
        evidence.append(
            EvidenceItem(
                label="Average daily traded value (20 sessions)",
                value=f"₹{value:,.1f} crore",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    if p.avg_volume:
        sub = lin(
            math.log10(max(p.avg_volume, 1)),
            math.log10(t["liquidity_volume_lo"]),
            math.log10(t["liquidity_volume_hi"]),
        )
        parts.append((sub, 0.2))
        evidence.append(
            EvidenceItem(
                label="Average daily volume",
                value=f"{p.avg_volume:,.0f} shares",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    if p.spread_bps is not None:
        sub = 1 - lin(p.spread_bps, t["spread_good_bps"], t["spread_bad_bps"])
        parts.append((sub, 0.2))
        evidence.append(
            EvidenceItem(
                label="Bid/ask spread",
                value=f"{p.spread_bps:.1f} bps",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    else:
        evidence.append(
            EvidenceItem(label="Bid/ask spread", value="not available from this data source", passed=None)
        )
    fraction = _mean_weighted(parts)
    summary = (
        "Liquidity could not be measured."
        if fraction is None
        else f"Average traded value ₹{value:,.1f} crore per day."
    )
    return _component(
        "liquidity",
        weights,
        fraction,
        summary,
        evidence,
        {"avg_traded_value_cr": value, "avg_volume": p.avg_volume, "spread_bps": p.spread_bps},
        inp.source_key,
    )


_STRUCTURE_TEXT = {
    "HIGHER_HIGHS_LOWS": "higher highs and higher lows",
    "LOWER_HIGHS_LOWS": "lower highs and lower lows",
    "MIXED": "mixed highs and lows",
}


def score_price_action(inp: ScoringInput, weights: dict[str, float], d: int) -> ScoreComponent:
    tech, p = inp.technical, inp.price
    pa, lv = tech.price_action, tech.levels
    parts, evidence = [], []
    if d == 0:
        base = 0.35 + (0.15 if pa.consolidation else 0.0)
        evidence.append(
            EvidenceItem(label="Directional bias", value="neutral: the signals disagree", passed=None)
        )
        evidence.append(
            EvidenceItem(
                label="Consolidation (energy building)",
                value="yes" if pa.consolidation else "no",
                passed=None,
            )
        )
        return _component(
            "price_action",
            weights,
            base,
            "No clear direction: price action is mixed, so only a partial score is given.",
            evidence,
            {"direction": "NEUTRAL"},
            inp.source_key,
        )
    bull = d > 0
    if pa.structure != "UNKNOWN":
        structure = {
            "HIGHER_HIGHS_LOWS": 1.0 if bull else 0.0,
            "LOWER_HIGHS_LOWS": 0.0 if bull else 1.0,
            "MIXED": 0.5,
        }[pa.structure]
        parts.append((structure, 1.0))
        evidence.append(
            EvidenceItem(
                label="Daily swing structure",
                value=_STRUCTURE_TEXT[pa.structure],
                passed=tick(structure),
                source_key=inp.source_key,
            )
        )
    if lv.vwap_distance_pct is not None:
        aligned = d * lv.vwap_distance_pct
        sub = lin(aligned, 0.0, 0.3)
        parts.append((sub, 1.0))
        evidence.append(
            EvidenceItem(
                label="Price vs VWAP",
                value=f"{lv.vwap_distance_pct:+.2f}% ({lv.vwap_position.lower() if lv.vwap_position else '?'})",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    breakout_aligned = (pa.breakout == "UP" and bull) or (pa.breakout == "DOWN" and not bull)
    levels = lv.resistance if bull else lv.support
    blocked = bool(levels and inp.volatility.atr and abs(levels[0] - p.price) < 0.3 * inp.volatility.atr)
    level_score = (0.7 if blocked else 1.0) if breakout_aligned else 0.3 if blocked else 0.6
    parts.append((level_score, 1.0))
    evidence.append(
        EvidenceItem(
            label="Breakout of prior-day / opening range",
            value="yes, in the setup direction" if breakout_aligned else "no",
            passed=True if breakout_aligned else None,
            source_key=inp.source_key,
        )
    )
    if blocked:
        evidence.append(
            EvidenceItem(
                label=f"Nearby {'resistance' if bull else 'support'} level",
                value=f"₹{levels[0]:,.2f} is within 0.3 ATR of price",
                passed=False,
                source_key=inp.source_key,
            )
        )
    if lv.gap_direction != "NONE":
        aligned_gap = (lv.gap_direction == "UP") == bull
        filled = bool(lv.gap_filled_today)
        gap_score = (0.5 if filled else 1.0) if aligned_gap else 0.1
        parts.append((gap_score, 1.0))
        evidence.append(
            EvidenceItem(
                label="Gap behaviour",
                value=f"gap {lv.gap_direction.lower()} {abs(lv.gap_pct or 0):.1f}%, {'filled' if filled else 'holding'}",
                passed=tick(gap_score),
                source_key=inp.source_key,
            )
        )
    fraction = _mean_weighted(parts)
    return _component(
        "price_action",
        weights,
        fraction,
        f"{'Bullish' if bull else 'Bearish'} structure checked against VWAP, key levels and the gap.",
        evidence,
        {"direction": tech.direction, "structure": pa.structure, "breakout": pa.breakout},
        inp.source_key,
    )


def _rsi_score(rsi: float, bull: bool) -> float:
    value = rsi if bull else 100 - rsi
    return interpolate(
        value,
        [(0, 0.0), (40, 0.05), (45, 0.3), (50, 0.4), (55, 0.7), (62, 1.0), (70, 1.0), (80, 0.6), (100, 0.3)],
    )


def score_momentum(inp: ScoringInput, weights: dict[str, float], d: int) -> ScoreComponent:
    tech = inp.technical
    t15, tday = _tf(tech, "15m"), _tf(tech, "daily")
    rsis = [t.rsi for t in (t15, tday) if t and t.rsi is not None]
    dm = d or (1 if rsis and sum(rsis) / len(rsis) >= 50 else -1)
    bull = dm > 0
    parts, evidence = [], []
    if rsis:
        avg_rsi = sum(rsis) / len(rsis)
        sub = _rsi_score(avg_rsi, bull)
        parts.append((sub, 1.0))
        evidence.append(
            EvidenceItem(
                label="RSI (15m / daily)",
                value=" / ".join(f"{t.rsi:.0f}" for t in (t15, tday) if t and t.rsi is not None),
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    if t15 and t15.macd_hist is not None:
        aligned = t15.macd_hist * dm > 0
        line_aligned = t15.macd is not None and t15.macd * dm > 0
        sub = 0.8 * aligned + 0.2 * (aligned and line_aligned)
        parts.append((sub, 1.0))
        evidence.append(
            EvidenceItem(
                label="MACD histogram (15m)",
                value=f"{t15.macd_hist:+.3f}",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    adx_values = [t.adx for t in (t15, tday) if t and t.adx is not None]
    if adx_values:
        adx_avg = sum(adx_values) / len(adx_values)
        di_ok = all(
            ((t.plus_di or 0) > (t.minus_di or 0)) == bull for t in (t15, tday) if t and t.plus_di is not None
        )
        sub = interpolate(adx_avg, [(0, 0.0), (15, 0.15), (20, 0.4), (25, 0.85), (35, 1.0)]) * (
            1.0 if di_ok else 0.5
        )
        parts.append((sub, 1.0))
        evidence.append(
            EvidenceItem(
                label="ADX (trend strength)",
                value=f"{adx_avg:.0f}" + ("" if di_ok else " (directional lines disagree)"),
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    if tday and tday.roc is not None:
        sub = lin(dm * tday.roc, 0.0, 5.0)
        parts.append((sub, 1.0))
        evidence.append(
            EvidenceItem(
                label="10-day rate of change",
                value=f"{tday.roc:+.1f}%",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    nifty = next(
        (i for i in inp.market.indices if i.symbol == "NIFTY" and i.available and i.change_pct is not None),
        None,
    )
    if nifty and inp.price.change_pct is not None:
        relative = (inp.price.change_pct - nifty.change_pct) * dm
        sub = lin(relative, -1.0, 1.5)
        parts.append((sub, 1.0))
        evidence.append(
            EvidenceItem(
                label="Day return vs NIFTY",
                value=f"{inp.price.change_pct - nifty.change_pct:+.2f} percentage points",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    fraction = _mean_weighted(parts)
    return _component(
        "momentum",
        weights,
        fraction,
        f"Momentum measured in the {'bullish' if bull else 'bearish'} direction.",
        evidence,
        {"direction_used": "BULLISH" if bull else "BEARISH"},
        inp.source_key,
    )


def score_volume(inp: ScoringInput, weights: dict[str, float], d: int) -> ScoreComponent:
    p = inp.price
    parts, evidence = [], []
    if p.rel_volume is not None:
        sub = interpolate(
            p.rel_volume, [(0, 0.0), (0.5, 0.05), (1.0, 0.45), (1.5, 0.75), (2.0, 0.95), (3.0, 1.0)]
        )
        parts.append((sub, 0.6))
        evidence.append(
            EvidenceItem(
                label="Relative volume (vs same time of day)",
                value=f"{p.rel_volume:.2f}x",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
        if p.volume_spike:
            parts.append((1.0, 0.1))
            evidence.append(
                EvidenceItem(
                    label="Volume spike on the latest bar",
                    value="yes",
                    passed=True,
                    source_key=inp.source_key,
                )
            )
        relation = inp.technical.price_action.price_volume
        table = {
            "PRICE_UP_VOLUME_UP": (1.0, 0.1),
            "PRICE_UP_VOLUME_DOWN": (0.4, 0.3),
            "PRICE_DOWN_VOLUME_UP": (0.1, 1.0),
            "PRICE_DOWN_VOLUME_DOWN": (0.3, 0.4),
        }
        if relation in table:
            bull_score, bear_score = table[relation]
            sub = 0.4 if d == 0 else bull_score if d > 0 else bear_score
            parts.append((sub, 0.3))
            evidence.append(
                EvidenceItem(
                    label="Price / volume relationship",
                    value=relation.replace("_", " ")
                    .lower()
                    .replace("price ", "price ")
                    .replace(" volume ", " and volume "),
                    passed=tick(sub),
                    source_key=inp.source_key,
                )
            )
    fraction = _mean_weighted(parts)
    return _component(
        "volume",
        weights,
        fraction,
        (
            "Volume compared with the average for this point in the session."
            if fraction is not None
            else "Volume could not be measured."
        ),
        evidence,
        {"rel_volume": p.rel_volume, "volume_spike": p.volume_spike},
        inp.source_key,
    )


def score_volatility(inp: ScoringInput, weights: dict[str, float]) -> ScoreComponent:
    t, v = inp.thresholds, inp.volatility
    parts, evidence = [], []
    if v.atr_pct is not None:
        sub = trapezoid(
            v.atr_pct,
            t["atr_pct_zero_low"],
            t["atr_pct_ideal_low"],
            t["atr_pct_ideal_high"],
            t["atr_pct_zero_high"],
        )
        parts.append((sub, 0.7))
        evidence.append(
            EvidenceItem(
                label="Daily ATR",
                value=f"{v.atr_pct:.2f}% of price",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    if v.intraday_range_pct is not None and v.avg_daily_range_pct:
        ratio = v.intraday_range_pct / v.avg_daily_range_pct
        sub = interpolate(ratio, [(0, 0.2), (0.3, 0.5), (0.5, 1.0), (1.3, 1.0), (2.0, 0.4), (3.0, 0.1)])
        parts.append((sub, 0.3))
        evidence.append(
            EvidenceItem(
                label="Today's range vs average daily range",
                value=f"{ratio:.2f}x",
                passed=tick(sub),
                source_key=inp.source_key,
            )
        )
    if v.hist_vol_pct is not None:
        evidence.append(
            EvidenceItem(
                label="Historical volatility (20d, annualised)",
                value=f"{v.hist_vol_pct:.1f}%",
                passed=None,
                source_key=inp.source_key,
            )
        )
    fraction = _mean_weighted(parts)
    return _component(
        "volatility",
        weights,
        fraction,
        f"Suitable volatility for intraday means enough movement without extremes (a daily ATR between {t['atr_pct_ideal_low']}% and {t['atr_pct_ideal_high']}% scores highest).",
        evidence,
        {"atr_pct": v.atr_pct},
        inp.source_key,
    )


def score_technical(inp: ScoringInput, weights: dict[str, float], d: int) -> ScoreComponent:
    tech = inp.technical
    if d == 0:
        pa = tech.price_action
        frac = 0.35 + (0.15 if pa.consolidation else 0.0)
        ev = [EvidenceItem(label="Timeframe alignment", value="no common direction", passed=None)]
        return _component(
            "technical_setup",
            weights,
            frac,
            "Timeframes do not agree on a direction.",
            ev,
            {"direction": "NEUTRAL"},
            inp.source_key,
        )
    bull = d > 0
    weights_tf = {"15m": 0.3, "30m": 0.2, "1h": 0.2, "daily": 0.3}
    parts, evidence = [], []
    for name, w in weights_tf.items():
        t = _tf(tech, name)
        if not t or t.trend == "UNKNOWN":
            continue
        trend_ok = (t.trend == "UP") == bull and t.trend != "SIDEWAYS"
        stack_ok = (t.ema_stack == "BULLISH") == bull and t.ema_stack in ("BULLISH", "BEARISH")
        score = 1.0 if trend_ok and stack_ok else 0.6 if trend_ok else 0.3 if t.trend == "SIDEWAYS" else 0.0
        parts.append((score, w))
        evidence.append(
            EvidenceItem(
                label=f"{name} trend / EMA stack",
                value=f"{t.trend.lower()} / {t.ema_stack.lower()}",
                passed=trend_ok,
                source_key=inp.source_key,
            )
        )
    alignment = _mean_weighted(parts)
    if alignment is None:
        return _component(
            "technical_setup",
            weights,
            None,
            "Not enough data on any timeframe.",
            evidence,
            {},
            inp.source_key,
        )
    st_flags = [
        (t.supertrend_dir == 1) == bull
        for t in (_tf(tech, "15m"), _tf(tech, "daily"))
        if t and t.supertrend_dir is not None
    ]
    st_score = sum(st_flags) / len(st_flags) if st_flags else None
    if st_score is not None:
        evidence.append(
            EvidenceItem(
                label="Supertrend agrees (15m, daily)",
                value=f"{sum(st_flags)} of {len(st_flags)}",
                passed=st_score >= 0.5,
                source_key=inp.source_key,
            )
        )
    fraction = alignment if st_score is None else 0.7 * alignment + 0.3 * st_score
    pa = tech.price_action
    if (pa.breakout == "UP" and bull) or (pa.breakout == "DOWN" and not bull):
        fraction += 0.15
        evidence.append(
            EvidenceItem(
                label="Breakout in the trade direction", value="yes", passed=True, source_key=inp.source_key
            )
        )
    if (pa.stretched == "OVERBOUGHT" and bull) or (pa.stretched == "OVERSOLD" and not bull):
        fraction -= 0.2
        evidence.append(
            EvidenceItem(
                label="Already stretched in this direction (chasing risk)",
                value=pa.stretched.lower(),
                passed=False,
                source_key=inp.source_key,
            )
        )
    return _component(
        "technical_setup",
        weights,
        fraction,
        "Agreement of trend, EMA stack and Supertrend across timeframes.",
        evidence,
        {"alignment": round(alignment, 3)},
        inp.source_key,
    )


def score_market_regime(inp: ScoringInput, weights: dict[str, float], d: int) -> ScoreComponent:
    regime = inp.market.regime
    if regime.label == "UNKNOWN":
        return _component(
            "market_regime", weights, None, "Market regime could not be determined.", [], {}, None
        )
    alignment = 0.0 if d == 0 else clip(d * regime.score, -1.0, 1.0)
    fraction = 0.5 + 0.5 * alignment
    if d == 0:
        fraction = 0.5
    if regime.volatility == "HIGH":
        fraction *= 0.85
    evidence = [
        EvidenceItem(
            label="Market regime",
            value=f"{regime.label.replace('_', ' ').lower()} (confidence {regime.confidence * 100:.0f}%)",
            passed=None,
        )
    ]
    evidence += [EvidenceItem(label=f.name, value=f.value, passed=f.bullish) for f in regime.factors]
    return _component(
        "market_regime",
        weights,
        fraction,
        f"Market is {regime.label.replace('_', ' ').lower()}; the setup direction is {'aligned with' if alignment > 0.1 else 'against' if alignment < -0.1 else 'neutral to'} it.",
        evidence,
        {"regime": regime.label, "score": regime.score},
        None,
    )


def score_news(weights: dict[str, float]) -> ScoreComponent:
    return _component(
        "news_catalyst",
        weights,
        None,
        "News and catalysts were not assessed: no news source is connected yet.",
        [EvidenceItem(label="News / corporate announcements", value="not assessed", passed=None)],
        {},
        None,
    )


def score_historical(inp: ScoringInput, weights: dict[str, float]) -> ScoreComponent:
    h = inp.historical
    if h is None:
        return _component(
            "historical_setup",
            weights,
            None,
            "Historical setup statistics were not run at this research depth.",
            [],
            {},
            None,
        )
    m = h.matched
    if m is None or m.success_rate is None or m.avg_return_net_pct is None:
        evidence = [
            EvidenceItem(
                label="Sample of today's setup",
                value=f"{h.setups[0].occurrences if h.setups else 0} occurrences, below the minimum of {inp.thresholds['min_sample']}",
                passed=False,
                source_key=inp.source_key,
            )
        ]
        return _component(
            "historical_setup",
            weights,
            None,
            "No historical sample of today's setup is large enough to score, so no historical edge is claimed.",
            evidence,
            {},
            None,
        )
    rate_score = lin(m.success_rate, 45.0, 65.0)
    edge_score = lin(m.avg_return_net_pct, -0.10, 0.25)
    fraction = 0.5 * rate_score + 0.5 * edge_score
    evidence = [
        EvidenceItem(
            label="Sample size",
            value=f"{m.occurrences} occurrences ({m.period_start} to {m.period_end})",
            passed=True,
            source_key=inp.source_key,
        ),
        EvidenceItem(
            label="Historical success rate (1h)",
            value=f"{m.success_rate:.1f}%",
            passed=m.success_rate > 55,
            source_key=inp.source_key,
        ),
        EvidenceItem(
            label="Average return after trading costs",
            value=f"{m.avg_return_net_pct:+.3f}%",
            passed=m.avg_return_net_pct > 0,
            source_key=inp.source_key,
        ),
    ]
    return _component(
        "historical_setup",
        weights,
        fraction,
        f"{m.label}: {m.occurrences} past occurrences.",
        evidence,
        {
            "occurrences": m.occurrences,
            "success_rate": m.success_rate,
            "avg_return_net_pct": m.avg_return_net_pct,
        },
        inp.source_key,
    )


def score_risk(inp: ScoringInput, weights: dict[str, float]) -> ScoreComponent:
    deduction = sum(RISK_DEDUCTION[f.severity] for f in inp.risk_flags)
    fraction = clip(1.0 - deduction)
    evidence = [EvidenceItem(label=f.message, value=f.severity.lower(), passed=False) for f in inp.risk_flags]
    if not inp.risk_flags:
        evidence.append(
            EvidenceItem(
                label="No risk flags raised by the checks that could be run", value="clear", passed=True
            )
        )
    evidence += [
        EvidenceItem(label=f"Not checked: {c}", value="no data source", passed=None)
        for c in inp.unavailable_checks
    ]
    return _component(
        "risk",
        weights,
        fraction,
        f"{len(inp.risk_flags)} risk flag(s) reduce this component; unchecked risks are listed separately.",
        evidence,
        {"flags": [f.code for f in inp.risk_flags]},
        None,
    )


# ---- aggregation ---------------------------------------------------------------------------------------------
def score_symbol(
    inp: ScoringInput,
    weights: dict[str, float],
    weight_set_id: str | None = None,
    weight_set_version: int | None = None,
) -> ScoreResult:
    d = _direction_sign(inp.technical.direction)
    builders = {
        "market_regime": lambda: score_market_regime(inp, weights, d),
        "liquidity": lambda: score_liquidity(inp, weights),
        "price_action": lambda: score_price_action(inp, weights, d),
        "momentum": lambda: score_momentum(inp, weights, d),
        "volume": lambda: score_volume(inp, weights, d),
        "volatility": lambda: score_volatility(inp, weights),
        "technical_setup": lambda: score_technical(inp, weights, d),
        "news_catalyst": lambda: score_news(weights),
        "historical_setup": lambda: score_historical(inp, weights),
        "risk": lambda: score_risk(inp, weights),
    }
    components = [builders[key]() for key in COMPONENT_ORDER]
    available = [c for c in components if c.available and c.max_points > 0]
    total = sum(weights.values())
    available_points = sum(c.max_points for c in available)
    earned = sum(c.points for c in available)
    raw = earned / available_points * 100 if available_points else None
    score, capped, reason = raw, False, None
    cap = float(inp.thresholds["risk_cap_score"])
    if raw is not None and any(f.severity == "HIGH" for f in inp.risk_flags) and raw > cap:
        score, capped = cap, True
        reason = f"A high-severity risk flag caps the score at {cap:g}."
    quality = "UNKNOWN"
    if score is not None:
        quality = (
            "STRONG"
            if score >= inp.thresholds["setup_strong"]
            else "MODERATE" if score >= inp.thresholds["setup_moderate"] else "WEAK"
        )
    return ScoreResult(
        research_score=None if score is None else round(score, 1),
        raw_score=None if raw is None else round(raw, 1),
        capped=capped,
        cap_reason=reason,
        available_points=round(available_points, 2),
        total_points=round(total, 2),
        coverage_pct=round(available_points / total * 100, 1) if total else 0.0,
        components=components,
        weight_set_id=weight_set_id,
        weight_set_version=weight_set_version,
        setup_quality=quality,
        direction=inp.technical.direction,
    )
