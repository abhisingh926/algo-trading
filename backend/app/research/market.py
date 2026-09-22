"""Market regime, breadth and sector rotation. Rule based: every label shows the factors behind it."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime

from app.domain.types import Candle
from app.research import indicators as ind
from app.research import sessions as ses
from app.research.contracts import (
    Breadth,
    IndexSnapshot,
    MarketContext,
    MarketRegime,
    Provenance,
    RegimeFactor,
    SectorSnapshot,
)

INDEX_NAMES = {"NIFTY": "NIFTY 50", "BANKNIFTY": "BANK NIFTY", "INDIAVIX": "INDIA VIX"}
UNAVAILABLE_MARKET_INPUTS = [
    "US overnight and Asian markets",
    "USD/INR",
    "Crude oil, gold and bond yields",
    "Exchange-wide advance/decline (breadth is computed over the scanned universe)",
]


def index_snapshot(symbol: str, bars_15m: list[Candle]) -> IndexSnapshot:
    name = INDEX_NAMES.get(symbol, symbol)
    sessions = ses.group_sessions(bars_15m)
    if len(sessions) < 5:
        return IndexSnapshot(symbol=symbol, name=name, available=False)
    daily = ses.to_daily(sessions)
    closes = [b.close for b in daily]
    price = bars_15m[-1].close
    prev = sessions[-2].bars[-1].close
    ema20, ema50 = ind.ema(closes, 20)[-1], ind.ema(closes, 50)[-1]
    slow = ema50 if ema50 is not None else ema20
    trend = "UNKNOWN"
    if ema20 is not None and slow is not None:
        trend = (
            "UP"
            if ema20 > slow and price > ema20
            else "DOWN" if ema20 < slow and price < ema20 else "SIDEWAYS"
        )
    return IndexSnapshot(
        symbol=symbol,
        name=name,
        available=True,
        price=price,
        change_pct=(price / prev - 1) * 100 if prev else None,
        ema20=ema20,
        ema50=ema50,
        trend=trend,
        rsi=ind.rsi(closes)[-1],
        ret_5d_pct=(price / closes[-6] - 1) * 100 if len(closes) >= 6 else None,
    )


@dataclass(slots=True)
class StockPoint:
    symbol: str
    sector: str | None
    change_pct: float | None
    ret_5d_pct: float | None
    rel_volume: float | None
    rsi: float | None
    above_vwap: bool | None
    above_ema20: bool | None


def compute_breadth(points: list[StockPoint]) -> Breadth | None:
    if not points:
        return None
    moves = [p.change_pct for p in points if p.change_pct is not None]
    vwap = [p.above_vwap for p in points if p.above_vwap is not None]
    ema20 = [p.above_ema20 for p in points if p.above_ema20 is not None]
    return Breadth(
        advances=sum(1 for m in moves if m > 0.0),
        declines=sum(1 for m in moves if m < 0.0),
        unchanged=sum(1 for m in moves if m == 0.0),
        universe_size=len(points),
        pct_above_vwap=round(sum(vwap) / len(vwap) * 100, 1) if vwap else None,
        pct_above_ema20=round(sum(ema20) / len(ema20) * 100, 1) if ema20 else None,
    )


def compute_sectors(points: list[StockPoint], nifty: IndexSnapshot | None) -> list[SectorSnapshot]:
    by_sector: dict[str, list[StockPoint]] = {}
    for p in points:
        if p.sector:
            by_sector.setdefault(p.sector, []).append(p)
    out: list[SectorSnapshot] = []
    for sector, members in by_sector.items():

        def avg(values: list[float | None]) -> float | None:
            clean = [v for v in values if v is not None]
            return statistics.fmean(clean) if clean else None

        ret_1d, ret_5d = avg([m.change_pct for m in members]), avg([m.ret_5d_pct for m in members])
        moves = [m.change_pct for m in members if m.change_pct is not None]
        breadth = sum(1 for m in moves if m > 0) / len(moves) * 100 if moves else None
        rs_1d = (
            ret_1d - nifty.change_pct
            if ret_1d is not None and nifty and nifty.change_pct is not None
            else None
        )
        rs_5d = (
            ret_5d - nifty.ret_5d_pct
            if ret_5d is not None and nifty and nifty.ret_5d_pct is not None
            else None
        )
        trend = "UNKNOWN"
        if rs_5d is not None and breadth is not None:
            trend = (
                "UP"
                if rs_5d > 0.3 and breadth >= 55
                else "DOWN" if rs_5d < -0.3 and breadth <= 45 else "SIDEWAYS"
            )
        out.append(
            SectorSnapshot(
                sector=sector,
                constituents=len(members),
                ret_1d_pct=ret_1d,
                ret_5d_pct=ret_5d,
                rel_strength_1d=rs_1d,
                rel_strength_5d=rs_5d,
                avg_rel_volume=avg([m.rel_volume for m in members]),
                breadth_pct=breadth,
                momentum=avg([m.rsi for m in members]),
                trend=trend,
            )
        )

    def rotation_key(s: SectorSnapshot) -> tuple[float, float]:
        return 0.5 * (s.rel_strength_1d or 0) + 0.5 * (s.rel_strength_5d or 0), s.ret_1d_pct or 0

    out.sort(key=rotation_key, reverse=True)
    for rank, snapshot in enumerate(out, start=1):
        snapshot.rank = rank
    return out


def compute_regime(
    nifty: IndexSnapshot | None,
    banknifty: IndexSnapshot | None,
    vix: float | None,
    breadth: Breadth | None,
    vix_high: float = 20.0,
    vix_low: float = 12.0,
) -> MarketRegime:
    factors: list[RegimeFactor] = []

    def add(name: str, value: str, bullish: bool | None, detail: str) -> None:
        factors.append(RegimeFactor(name=name, value=value, bullish=bullish, detail=detail))

    if nifty and nifty.available and nifty.price is not None:
        if nifty.ema20 is not None:
            add(
                "NIFTY vs 20-day EMA",
                f"{nifty.price:,.0f} vs {nifty.ema20:,.0f}",
                nifty.price > nifty.ema20,
                "Above the 20-day EMA is bullish",
            )
        if nifty.ema50 is not None:
            add(
                "NIFTY vs 50-day EMA",
                f"{nifty.price:,.0f} vs {nifty.ema50:,.0f}",
                nifty.price > nifty.ema50,
                "Above the 50-day EMA is bullish",
            )
        if nifty.ema20 is not None and nifty.ema50 is not None:
            add(
                "NIFTY 20-day EMA vs 50-day EMA",
                f"{nifty.ema20:,.0f} vs {nifty.ema50:,.0f}",
                nifty.ema20 > nifty.ema50,
                "Fast average above slow is bullish",
            )
        if nifty.change_pct is not None:
            move = nifty.change_pct
            add(
                "NIFTY day change",
                f"{move:+.2f}%",
                True if move > 0.3 else False if move < -0.3 else None,
                "Beyond +/-0.3% counts",
            )
    if banknifty and banknifty.available and banknifty.ema20 is not None and banknifty.price is not None:
        add(
            "BANK NIFTY vs 20-day EMA",
            f"{banknifty.price:,.0f} vs {banknifty.ema20:,.0f}",
            banknifty.price > banknifty.ema20,
            "Banks lead the index",
        )
    if breadth and breadth.advances + breadth.declines > 0:
        share = breadth.advances / (breadth.advances + breadth.declines)
        add(
            "Advance / decline (scanned universe)",
            f"{breadth.advances} up, {breadth.declines} down",
            True if share > 0.6 else False if share < 0.4 else None,
            "Above 60% advancing is bullish, below 40% bearish",
        )
    if breadth and breadth.pct_above_ema20 is not None:
        pct = breadth.pct_above_ema20
        add(
            "Stocks above 20-day EMA (scanned universe)",
            f"{pct:.0f}%",
            True if pct > 60 else False if pct < 40 else None,
            "Above 60% is bullish, below 40% bearish",
        )

    decided = [f for f in factors if f.bullish is not None]
    volatility = (
        "UNKNOWN" if vix is None else "HIGH" if vix >= vix_high else "LOW" if vix <= vix_low else "NORMAL"
    )
    if vix is not None:
        add("India VIX", f"{vix:.1f}", None, f"High at {vix_high:g} or above, low at {vix_low:g} or below")
    if not decided:
        return MarketRegime(
            label="UNKNOWN", volatility=volatility, confidence=0.0, score=0.0, factors=factors
        )
    score = (sum(1 for f in decided if f.bullish) - sum(1 for f in decided if f.bullish is False)) / len(
        decided
    )
    label = (
        "STRONG_BULLISH"
        if score >= 0.7
        else (
            "BULLISH"
            if score >= 0.25
            else "RANGE" if score > -0.25 else "BEARISH" if score > -0.7 else "STRONG_BEARISH"
        )
    )
    coverage = len(decided) / 8
    confidence = min(0.95, min(coverage, 1.0) * (0.5 + 0.5 * abs(score)))
    return MarketRegime(
        label=label,
        volatility=volatility,
        confidence=round(confidence, 2),
        score=round(score, 2),
        factors=factors,
    )


def state_note(state: str, latest_session: str | None) -> str:
    if state == "OPEN":
        return "Market is open. Figures are as of the latest completed bar."
    label = {
        "PRE_MARKET": "The market has not opened yet",
        "POST_MARKET": "The market has closed",
        "CLOSED": "The market is closed",
    }[state]
    return f"{label}. Analysis uses the last regular session ({latest_session or 'unknown'}) and is not live."


def build_context(
    as_of: datetime,
    state: str,
    note: str,
    indices: list[IndexSnapshot],
    vix_snapshot: IndexSnapshot | None,
    breadth: Breadth | None,
    sectors: list[SectorSnapshot],
    provenance: Provenance,
    thresholds: dict[str, float],
) -> MarketContext:
    nifty = next((i for i in indices if i.symbol == "NIFTY"), None)
    bank = next((i for i in indices if i.symbol == "BANKNIFTY"), None)
    vix = vix_snapshot.price if vix_snapshot and vix_snapshot.available else None
    regime = compute_regime(nifty, bank, vix, breadth, thresholds["vix_high"], thresholds["vix_low"])
    return MarketContext(
        as_of=as_of,
        market_state=state,
        market_state_note=note,
        indices=indices,
        india_vix=vix,
        india_vix_change_pct=vix_snapshot.change_pct if vix_snapshot and vix_snapshot.available else None,
        breadth=breadth,
        regime=regime,
        sectors=sectors,
        unavailable=UNAVAILABLE_MARKET_INPUTS,
        provenance=provenance,
    )
