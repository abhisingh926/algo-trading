"""Market scanner: cheap, transparent pre-selection. Its score only decides which stocks get a full analysis."""

from __future__ import annotations

import math
from typing import Any

from app.research.contracts import ScannerCandidate, SectorSnapshot
from app.research.features import TechnicalBundle
from app.research.scoring import lin


def prefilter(bundle: TechnicalBundle, thresholds: dict[str, Any]) -> str | None:
    """Reason to exclude a security (extremely illiquid or penny-priced), or None to keep it."""
    p = bundle.price
    if p.price < thresholds["prefilter_min_price"]:
        return f"Price ₹{p.price:,.2f} is below the ₹{thresholds['prefilter_min_price']:g} minimum"
    value = p.avg_traded_value_cr
    if value is None or value < thresholds["prefilter_min_traded_value_cr"]:
        shown = f"₹{value:.1f} crore" if value is not None else "unknown"
        return f"Average traded value {shown} is below the ₹{thresholds['prefilter_min_traded_value_cr']:g} crore minimum"
    return None


def scan(
    symbol: str,
    company: str,
    sector: str | None,
    bundle: TechnicalBundle,
    sector_snapshot: SectorSnapshot | None,
) -> ScannerCandidate:
    p, v, tech = bundle.price, bundle.volatility, bundle.technical
    pa, lv = tech.price_action, tech.levels
    d = 1 if tech.direction == "BULLISH" else -1 if tech.direction == "BEARISH" else 0
    reasons: list[str] = []
    score = 0.0
    if p.rel_volume is not None:
        score += lin(p.rel_volume, 1.0, 3.0) * 25
        if p.rel_volume >= 1.5:
            reasons.append(f"Relative volume {p.rel_volume:.1f}x")
    if d:
        score += abs(bundle.direction_score) / 5 * 15
        if lv.vwap_position in ("ABOVE", "BELOW") and (lv.vwap_position == "ABOVE") == (d > 0):
            reasons.append(f"Price {lv.vwap_position.lower()} VWAP")
    if abs(p.gap_pct or 0) >= 0.5 and (p.gap_pct or 0) * d > 0:
        score += 8
        reasons.append(f"Gap {'up' if (p.gap_pct or 0) > 0 else 'down'} {abs(p.gap_pct or 0):.1f}%")
    if (pa.breakout == "UP" and d > 0) or (pa.breakout == "DOWN" and d < 0):
        score += 12
        reasons.append(
            "Breakout of prior-day / opening range"
            if pa.breakout == "UP"
            else "Breakdown of prior-day / opening range"
        )
    if (pa.breakout_20d == "UP" and d > 0) or (pa.breakout_20d == "DOWN" and d < 0):
        score += 5
        reasons.append("20-day high broken" if pa.breakout_20d == "UP" else "20-day low broken")
    if pa.vwap_event and ((pa.vwap_event == "VWAP_RECLAIM") == (d > 0)) and d:
        score += 5
        reasons.append("VWAP reclaim" if pa.vwap_event == "VWAP_RECLAIM" else "VWAP rejection")
    adx = bundle.extras.get("adx_daily")
    if adx and adx >= 20 and d:
        score += 5
        reasons.append(f"Trend strength ADX {adx:.0f}")
    rsi = bundle.extras.get("rsi_daily")
    if rsi and d and ((d > 0 and 55 <= rsi <= 75) or (d < 0 and 25 <= rsi <= 45)):
        score += 5
    if (
        sector_snapshot
        and sector_snapshot.rel_strength_1d is not None
        and d
        and sector_snapshot.rel_strength_1d * d > 0.3
    ):
        score += 7
        reasons.append(
            f"Sector {sector_snapshot.sector} {'outperforming' if d > 0 else 'underperforming'} NIFTY"
        )
    if v.atr_pct is not None and 0.8 <= v.atr_pct <= 3.5:
        score += 7
    if p.avg_traded_value_cr:
        score += lin(math.log10(max(p.avg_traded_value_cr, 1e-6)), math.log10(2), math.log10(200)) * 8
    return ScannerCandidate(
        symbol=symbol,
        company=company,
        sector=sector,
        stage="SCANNED",
        initial_score=round(min(score, 100.0), 1),
        reasons=reasons,
        tags=pa.tags,
        price=p.price,
        change_pct=p.change_pct,
        rel_volume=p.rel_volume,
        atr_pct=v.atr_pct,
        vwap=lv.vwap,
        vwap_position=lv.vwap_position,
        direction=tech.direction,
    )
