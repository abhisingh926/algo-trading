"""Turns raw bars into the facts research needs: price/volume, volatility, multi-timeframe technicals,
price action and intraday levels. Deterministic and side-effect free; `as_of` filtering happens upstream."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.domain.types import Candle, InstrumentRef, Quote
from app.research import indicators as ind
from app.research import sessions as ses
from app.research.contracts import (
    EvidenceItem,
    IntradayLevels,
    PriceAction,
    PriceBlock,
    Provenance,
    TechnicalAnalysis,
    TimeframeTechnical,
    VolatilityBlock,
)
from app.research.sessions import market_state
from app.research.verification import freshness_label

MIN_SESSIONS = 25
LAST_15M_BAR_START = 360  # minutes into the session at which the final 15-minute bar opens (15:15 IST)
FULL_TIMEFRAMES = ["5m", "15m", "30m", "1h", "daily", "weekly"]
_TAIL = 1000


class InsufficientDataError(Exception):
    pass


@dataclass(slots=True)
class SymbolInput:
    symbol: str
    company: str
    sector: str | None
    ref: InstrumentRef
    bars_15m: list[Candle]  # regular-session bars complete at `as_of`, oldest first
    bars_5m: list[Candle]
    quote: Quote | None
    source_name: str
    source_type: str
    source_reliability: float
    retrieved_at: datetime
    as_of: datetime


@dataclass(slots=True)
class TechnicalBundle:
    price: PriceBlock
    volatility: VolatilityBlock
    technical: TechnicalAnalysis
    direction_score: int
    sessions: list[ses.Session]
    daily: list[Candle]
    completed_daily: list[Candle]
    today_bars: list[Candle]  # the finest bars available for the current session
    data_as_of: datetime
    session_complete: bool
    extras: dict[str, float | None] = field(default_factory=dict)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _pct(a: float | None, b: float | None) -> float | None:
    return None if a is None or not b else (a / b - 1) * 100


def _bar_end(bar: Candle, minutes: int) -> datetime:
    return bar.timestamp + timedelta(minutes=minutes)


def _timeframe_bars(name: str, inp: SymbolInput, daily: list[Candle]) -> list[Candle]:
    if name == "5m":
        return inp.bars_5m[-_TAIL:]
    if name == "15m":
        return inp.bars_15m[-_TAIL:]
    if name == "30m":
        return ses.resample(inp.bars_15m[-_TAIL * 2 :], 30)[-_TAIL:]
    if name == "1h":
        return ses.resample(inp.bars_15m[-_TAIL * 4 :], 60)[-_TAIL:]
    if name == "daily":
        return daily
    if name == "weekly":
        return ses.to_weekly(daily)
    raise ValueError(name)


def timeframe_technical(name: str, bars: list[Candle]) -> TimeframeTechnical:
    n = len(bars)
    if n < 15:
        return TimeframeTechnical(timeframe=name, bars=n)
    closes = [b.close for b in bars]
    highs, lows = [b.high for b in bars], [b.low for b in bars]
    volumes = [float(b.volume) for b in bars]

    def at(series: list[float | None]) -> float | None:
        return series[-1]

    e9, e20, e50, e100, e200 = (at(ind.ema(closes, p)) for p in (9, 20, 50, 100, 200))
    line, sig, hist = ind.macd(closes)
    adx_v, plus_di, minus_di = ind.adx(highs, lows, closes)
    _, upper, lower, width = ind.bollinger(closes)
    st_line, st_dir = ind.supertrend(highs, lows, closes)
    vol_ma = at(ind.sma(volumes, 20))
    close = closes[-1]

    stack_values = [v for v in (e9, e20, e50) if v is not None]
    if len(stack_values) < 2:
        stack = "UNKNOWN"
    elif all(a > b for a, b in zip(stack_values, stack_values[1:], strict=False)):
        stack = "BULLISH"
    elif all(a < b for a, b in zip(stack_values, stack_values[1:], strict=False)):
        stack = "BEARISH"
    else:
        stack = "MIXED"
    slow = e50 if e50 is not None else e20
    if slow is None or e20 is None:
        trend = "UNKNOWN"
    elif e20 > slow and close > e20:
        trend = "UP"
    elif e20 < slow and close < e20:
        trend = "DOWN"
    else:
        trend = "SIDEWAYS"
    return TimeframeTechnical(
        timeframe=name,
        bars=n,
        ema9=e9,
        ema20=e20,
        ema50=e50,
        ema100=e100,
        ema200=e200,
        sma20=at(ind.sma(closes, 20)),
        sma50=at(ind.sma(closes, 50)),
        sma200=at(ind.sma(closes, 200)),
        rsi=at(ind.rsi(closes)),
        macd=at(line),
        macd_signal=at(sig),
        macd_hist=at(hist),
        roc=at(ind.roc(closes, 10)),
        adx=at(adx_v),
        plus_di=at(plus_di),
        minus_di=at(minus_di),
        atr=at(ind.atr(highs, lows, closes)),
        bb_upper=at(upper),
        bb_lower=at(lower),
        bb_width_pct=at(width),
        supertrend=at(st_line),
        supertrend_dir=st_dir[-1],
        volume_ma=vol_ma,
        rel_volume=(volumes[-1] / vol_ma if vol_ma else None),
        trend=trend,
        ema_stack=stack,
    )


def _relative_volume(sessions: list[ses.Session]) -> tuple[float | None, float | None, bool, float | None]:
    """(time-of-day relative volume, average daily volume, last-bar spike, average traded value in crore)."""
    current, history = sessions[-1], sessions[-21:-1]
    n = len(current.bars)
    today_cum = sum(b.volume for b in current.bars)
    past_cum = [sum(b.volume for b in s.bars[:n]) for s in history if len(s.bars) >= n]
    rvol = (
        today_cum / _mean([float(v) for v in past_cum])
        if past_cum and _mean([float(v) for v in past_cum])
        else None
    )
    avg_daily = _mean([float(sum(b.volume for b in s.bars)) for s in history])
    last_bar_history = [s.bars[n - 1].volume for s in history if len(s.bars) >= n]
    spike = bool(last_bar_history and current.bars[-1].volume >= 2.5 * statistics.fmean(last_bar_history))
    values = [sum(b.close * b.volume for b in s.bars) / 1e7 for s in history]
    return rvol, avg_daily, spike, _mean(values)


def _swing_structure(daily: list[Candle]) -> tuple[str, int, int, list[float], list[float]]:
    window = daily[-70:]
    highs, lows = [b.high for b in window], [b.low for b in window]
    sh, sl = ind.swing_points(highs, lows, 2, 2)
    structure = "UNKNOWN"
    if len(sh) >= 2 and len(sl) >= 2:
        rising = sh[-1][1] > sh[-2][1] and sl[-1][1] > sl[-2][1]
        falling = sh[-1][1] < sh[-2][1] and sl[-1][1] < sl[-2][1]
        structure = "HIGHER_HIGHS_LOWS" if rising else "LOWER_HIGHS_LOWS" if falling else "MIXED"
    return structure, len(sh), len(sl), [p for _, p in sh], [p for _, p in sl]


def build_bundle(inp: SymbolInput, timeframes: list[str]) -> TechnicalBundle:
    sessions = ses.group_sessions(inp.bars_15m)
    if len(sessions) < MIN_SESSIONS:
        raise InsufficientDataError(
            f"Only {len(sessions)} sessions of data; at least {MIN_SESSIONS} are needed"
        )
    current, previous = sessions[-1], sessions[-2]
    daily = ses.to_daily(sessions)
    complete = ses.minutes_into_session(current.bars[-1].timestamp) >= LAST_15M_BAR_START
    completed_daily = daily if complete else daily[:-1]

    # Finest bars for today: 5m bars extend the picture past the last complete 15m bar.
    last_15_end = _bar_end(current.bars[-1], 15)
    tail_5m = [
        b for b in inp.bars_5m if ses.ist_day(b.timestamp) == current.day and _bar_end(b, 5) > last_15_end
    ]
    today_fine = [b for b in inp.bars_5m if ses.ist_day(b.timestamp) == current.day] or current.bars
    latest_bar = tail_5m[-1] if tail_5m else current.bars[-1]
    data_as_of = _bar_end(latest_bar, 5 if tail_5m else 15)

    price = latest_bar.close
    day_open = current.bars[0].open
    day_high = max([b.high for b in current.bars] + [b.high for b in tail_5m])
    day_low = min([b.low for b in current.bars] + [b.low for b in tail_5m])
    volume = sum(b.volume for b in current.bars) + sum(b.volume for b in tail_5m)
    prev_close = previous.bars[-1].close
    rvol, avg_volume, spike, traded_cr = _relative_volume(sessions)

    closes_daily = [b.close for b in daily]
    ret_5d = _pct(price, closes_daily[-6]) if len(closes_daily) >= 6 else None
    ret_20d = _pct(price, closes_daily[-21]) if len(closes_daily) >= 21 else None
    bid = inp.quote.bid if inp.quote else None
    ask = inp.quote.ask if inp.quote else None
    spread_bps = (ask - bid) / ((ask + bid) / 2) * 10_000 if bid and ask and ask >= bid else None
    price_block = PriceBlock(
        price=price,
        prev_close=prev_close,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        change=price - prev_close,
        change_pct=_pct(price, prev_close),
        gap_pct=_pct(day_open, prev_close),
        ret_5d_pct=ret_5d,
        ret_20d_pct=ret_20d,
        volume=volume,
        avg_volume=avg_volume,
        rel_volume=rvol,
        volume_spike=spike,
        avg_traded_value_cr=traded_cr,
        session_date=current.day.isoformat(),
        bars_in_session=len(current.bars),
        last_bar_time=latest_bar.timestamp,
        bid=bid,
        ask=ask,
        spread_bps=spread_bps,
    )

    cd_closes = [b.close for b in completed_daily]
    cd_high, cd_low = [b.high for b in completed_daily], [b.low for b in completed_daily]
    atr_v = ind.atr(cd_high, cd_low, cd_closes)[-1] if len(completed_daily) > 15 else None
    ranges = [(b.high - b.low) / b.close * 100 for b in completed_daily[-20:] if b.close]
    _, _, _, width = ind.bollinger(closes_daily)
    vol_block = VolatilityBlock(
        atr=atr_v,
        atr_pct=(atr_v / price * 100 if atr_v else None),
        hist_vol_pct=ind.historical_volatility(cd_closes, 20),
        intraday_range_pct=(day_high - day_low) / prev_close * 100 if prev_close else None,
        avg_daily_range_pct=_mean(ranges),
        bb_width_pct=width[-1],
    )

    tf_list = [timeframe_technical(name, _timeframe_bars(name, inp, daily)) for name in timeframes]
    by_name = {t.timeframe: t for t in tf_list}
    daily_tf = by_name.get("daily") or timeframe_technical("daily", daily)

    # ---- intraday levels ------------------------------------------------------------------------------
    vwaps = ses.vwap_series(today_fine)
    vwap = vwaps[-1]
    dist = (price - vwap) / vwap * 100
    or15, or30 = ses.opening_range(today_fine, 15), ses.opening_range(today_fine, 30)
    gap_pct = price_block.gap_pct or 0.0
    gap_dir = "UP" if gap_pct >= 0.3 else "DOWN" if gap_pct <= -0.3 else "NONE"
    gap_filled = (
        None if gap_dir == "NONE" else (day_low <= prev_close if gap_dir == "UP" else day_high >= prev_close)
    )
    structure, n_highs, n_lows, swing_high_prices, swing_low_prices = _swing_structure(completed_daily)
    level_pool = (
        swing_high_prices
        + swing_low_prices
        + [
            previous_high := max(b.high for b in previous.bars),
            previous_low := min(b.low for b in previous.bars),
            prev_close,
        ]
    )
    if or30:
        level_pool += [or30[0], or30[1]]
    clustered = [level for level, _ in ind.cluster_levels(level_pool, 0.4)]
    support = sorted((lv for lv in clustered if lv < price), reverse=True)[:3]
    resistance = sorted(lv for lv in clustered if lv > price)[:3]
    levels = IntradayLevels(
        vwap=vwap,
        vwap_position="AT" if abs(dist) < 0.05 else "ABOVE" if dist > 0 else "BELOW",
        vwap_distance_pct=dist,
        opening_range_15_high=or15[0] if or15 else None,
        opening_range_15_low=or15[1] if or15 else None,
        opening_range_30_high=or30[0] if or30 else None,
        opening_range_30_low=or30[1] if or30 else None,
        prev_day_high=previous_high,
        prev_day_low=previous_low,
        prev_day_close=prev_close,
        gap_pct=gap_pct,
        gap_direction=gap_dir,
        gap_filled_today=gap_filled,
        support=support,
        resistance=resistance,
    )

    # ---- price action ---------------------------------------------------------------------------------
    breakout, breakout_level = None, None
    upper_ref = max(previous_high, or30[0]) if or30 else previous_high
    lower_ref = min(previous_low, or30[1]) if or30 else previous_low
    if price > upper_ref:
        breakout, breakout_level = "UP", upper_ref
    elif price < lower_ref:
        breakout, breakout_level = "DOWN", lower_ref
    prior20 = completed_daily[-21:-1] if complete else completed_daily[-20:]
    breakout_20d = None
    if len(prior20) >= 15:
        breakout_20d = (
            "UP"
            if price > max(b.high for b in prior20)
            else "DOWN" if price < min(b.low for b in prior20) else None
        )
    widths = [w for w in width[-100:] if w is not None]
    squeeze = (
        bool(widths) and width[-1] is not None and width[-1] <= sorted(widths)[max(len(widths) // 4 - 1, 0)]
    )
    recent5 = completed_daily[-5:]
    tight_week = (
        bool(atr_v)
        and len(recent5) == 5
        and (max(b.high for b in recent5) - min(b.low for b in recent5)) < 1.5 * atr_v
    )
    range_expansion = bool(atr_v) and (day_high - day_low) >= 1.2 * atr_v
    rsi_daily = daily_tf.rsi
    stretched = (
        "OVERBOUGHT"
        if rsi_daily and rsi_daily >= 75
        else "OVERSOLD" if rsi_daily and rsi_daily <= 25 else None
    )
    signs = [1 if b.close > v else -1 for b, v in zip(today_fine, vwaps, strict=True)]
    vwap_event = None
    if len(signs) >= 4:
        if signs[-1] == 1 and -1 in signs[-4:-1]:
            vwap_event = "VWAP_RECLAIM"
        elif signs[-1] == -1 and 1 in signs[-4:-1]:
            vwap_event = "VWAP_REJECTION"
    change = price_block.change_pct or 0.0
    hi_vol = (rvol or 0) >= 1.0
    price_volume = (
        "UNKNOWN"
        if rvol is None
        else (
            ("PRICE_UP_VOLUME_UP" if hi_vol else "PRICE_UP_VOLUME_DOWN")
            if change > 0
            else ("PRICE_DOWN_VOLUME_UP" if hi_vol else "PRICE_DOWN_VOLUME_DOWN")
        )
    )
    tags = []
    if gap_dir != "NONE":
        tags.append(f"Gap {gap_dir.lower()} {abs(gap_pct):.1f}%")
    if breakout:
        tags.append(
            f"{'Above' if breakout == 'UP' else 'Below'} prior-day / opening-range {'high' if breakout == 'UP' else 'low'}"
        )
    if breakout_20d:
        tags.append(f"20-day {'high' if breakout_20d == 'UP' else 'low'} broken")
    if vwap_event:
        tags.append("VWAP reclaim" if vwap_event == "VWAP_RECLAIM" else "VWAP rejection")
    if squeeze or tight_week:
        tags.append("Consolidation")
    if range_expansion:
        tags.append("Range expansion")
    action = PriceAction(
        structure=structure,
        swing_highs=n_highs,
        swing_lows=n_lows,
        breakout=breakout,
        breakout_level=breakout_level,
        breakout_20d=breakout_20d,
        consolidation=bool(squeeze or tight_week),
        range_expansion=range_expansion,
        stretched=stretched,
        vwap_event=vwap_event,
        price_volume=price_volume,
        tags=tags,
    )

    # ---- direction ------------------------------------------------------------------------------------
    t15 = by_name.get("15m") or timeframe_technical("15m", inp.bars_15m[-_TAIL:])
    votes: list[tuple[str, int]] = [
        ("Price vs VWAP", 1 if dist > 0.05 else -1 if dist < -0.05 else 0),
        ("15-minute trend", {"UP": 1, "DOWN": -1}.get(t15.trend, 0)),
        ("Daily trend", {"UP": 1, "DOWN": -1}.get(daily_tf.trend, 0)),
        ("15-minute MACD histogram", 0 if t15.macd_hist is None else 1 if t15.macd_hist > 0 else -1),
        ("Day change", 1 if change > 0.15 else -1 if change < -0.15 else 0),
    ]
    score = sum(v for _, v in votes)
    direction = "BULLISH" if score >= 3 else "BEARISH" if score <= -3 else "NEUTRAL"
    vote_items = [
        EvidenceItem(label=name, value=f"{v:+d}", passed=None if v == 0 else v > 0) for name, v in votes
    ]

    stale_minutes = max((inp.as_of - data_as_of).total_seconds() / 60, 0)
    state = market_state(inp.as_of)
    provenance = Provenance(
        source=inp.source_name,
        source_type=inp.source_type,
        data_as_of=data_as_of,
        retrieved_at=inp.retrieved_at,
        confidence=inp.source_reliability,
        stale=False,
        freshness=freshness_label(stale_minutes, state, stale=False),
        age_minutes=round(stale_minutes, 1),
        note=(
            None
            if stale_minutes < 1
            else f"Latest complete bar ended {stale_minutes:.0f} minutes before the analysis time"
        ),
    )
    technical = TechnicalAnalysis(
        timeframes=tf_list,
        price_action=action,
        levels=levels,
        direction=direction,
        direction_votes=vote_items,
        provenance=provenance,
    )
    return TechnicalBundle(
        price=price_block,
        volatility=vol_block,
        technical=technical,
        direction_score=score,
        sessions=sessions,
        daily=daily,
        completed_daily=completed_daily,
        today_bars=today_fine,
        data_as_of=data_as_of,
        session_complete=complete,
        extras={"rsi_daily": rsi_daily, "adx_daily": daily_tf.adx},
    )
