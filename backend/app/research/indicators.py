"""Technical indicators used by the research agents. Pure functions, no I/O.

Every function returns a list aligned with its input. Entries before an indicator has enough data
are None, so callers never mistake a warm-up value for a real reading.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

Series = list[float | None]


def sma(values: Sequence[float], period: int) -> Series:
    if period <= 0:
        raise ValueError("period must be positive")
    out: Series = [None] * len(values)
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def ema(values: Sequence[float], period: int) -> Series:
    """EMA seeded with the SMA of the first `period` values (the common convention)."""
    if period <= 0:
        raise ValueError("period must be positive")
    out: Series = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = values[i] * k + current * (1 - k)
        out[i] = current
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def rsi(closes: Sequence[float], period: int = 14) -> Series:
    """Wilder's RSI."""
    n = len(closes)
    out: Series = [None] * n
    if n <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, n):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def macd(
    closes: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[Series, Series, Series]:
    """(macd line, signal line, histogram)."""
    fast_ema, slow_ema = ema(closes, fast), ema(closes, slow)
    line: Series = [
        None if f is None or s is None else f - s for f, s in zip(fast_ema, slow_ema, strict=True)
    ]
    first = next((i for i, v in enumerate(line) if v is not None), None)
    signal_line: Series = [None] * len(closes)
    if first is not None:
        valid = [v for v in line[first:] if v is not None]
        for offset, value in enumerate(ema(valid, signal)):
            signal_line[first + offset] = value
    hist: Series = [None if m is None or s is None else m - s for m, s in zip(line, signal_line, strict=True)]
    return line, signal_line, hist


def true_range(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]) -> list[float]:
    out = []
    for i in range(len(closes)):
        if i == 0:
            out.append(highs[0] - lows[0])
        else:
            out.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return out


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> Series:
    """Wilder's Average True Range."""
    n = len(closes)
    out: Series = [None] * n
    if n <= period:
        return out
    tr = true_range(highs, lows, closes)
    current = sum(tr[1 : period + 1]) / period
    out[period] = current
    for i in range(period + 1, n):
        current = (current * (period - 1) + tr[i]) / period
        out[i] = current
    return out


def adx(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14
) -> tuple[Series, Series, Series]:
    """Wilder's ADX with +DI and -DI. Returns (adx, plus_di, minus_di)."""
    n = len(closes)
    adx_out: Series = [None] * n
    plus_out: Series = [None] * n
    minus_out: Series = [None] * n
    if n < 2 * period:
        return adx_out, plus_out, minus_out
    tr = true_range(highs, lows, closes)
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up, down = highs[i] - highs[i - 1], lows[i - 1] - lows[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
    sum_tr = sum(tr[1 : period + 1])
    sum_plus = sum(plus_dm[1 : period + 1])
    sum_minus = sum(minus_dm[1 : period + 1])
    dx: list[float | None] = [None] * n
    for i in range(period, n):
        if i > period:
            sum_tr = sum_tr - sum_tr / period + tr[i]
            sum_plus = sum_plus - sum_plus / period + plus_dm[i]
            sum_minus = sum_minus - sum_minus / period + minus_dm[i]
        plus_di = 100 * sum_plus / sum_tr if sum_tr else 0.0
        minus_di = 100 * sum_minus / sum_tr if sum_tr else 0.0
        plus_out[i], minus_out[i] = plus_di, minus_di
        total = plus_di + minus_di
        dx[i] = 100 * abs(plus_di - minus_di) / total if total else 0.0
    first = 2 * period - 1
    current = sum(v for v in dx[period : first + 1] if v is not None) / period
    adx_out[first] = current
    for i in range(first + 1, n):
        current = (current * (period - 1) + (dx[i] or 0.0)) / period
        adx_out[i] = current
    return adx_out, plus_out, minus_out


def bollinger(
    closes: Sequence[float], period: int = 20, k: float = 2.0
) -> tuple[Series, Series, Series, Series]:
    """(middle, upper, lower, width as percent of the middle band)."""
    n = len(closes)
    mid = sma(closes, period)
    upper: Series = [None] * n
    lower: Series = [None] * n
    width: Series = [None] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        m = mid[i]
        assert m is not None
        std = math.sqrt(sum((x - m) ** 2 for x in window) / period)
        upper[i], lower[i] = m + k * std, m - k * std
        width[i] = (upper[i] - lower[i]) / m * 100 if m else None  # type: ignore[operator]
    return mid, upper, lower, width


def roc(closes: Sequence[float], period: int = 10) -> Series:
    return [
        None if i < period or closes[i - period] == 0 else (closes[i] / closes[i - period] - 1) * 100
        for i in range(len(closes))
    ]


def supertrend(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 10,
    multiplier: float = 3.0,
) -> tuple[Series, list[int | None]]:
    """(supertrend line, direction) where direction is 1 for an uptrend and -1 for a downtrend."""
    n = len(closes)
    line: Series = [None] * n
    direction: list[int | None] = [None] * n
    atr_values = atr(highs, lows, closes, period)
    start = next((i for i, v in enumerate(atr_values) if v is not None), None)
    if start is None:
        return line, direction
    final_upper = final_lower = 0.0
    for i in range(start, n):
        a = atr_values[i]
        assert a is not None
        mid = (highs[i] + lows[i]) / 2
        basic_upper, basic_lower = mid + multiplier * a, mid - multiplier * a
        if i == start:
            final_upper, final_lower = basic_upper, basic_lower
            direction[i] = 1 if closes[i] > mid else -1
        else:
            prev_close = closes[i - 1]
            final_upper = (
                basic_upper if basic_upper < final_upper or prev_close > final_upper else final_upper
            )
            final_lower = (
                basic_lower if basic_lower > final_lower or prev_close < final_lower else final_lower
            )
            previous = direction[i - 1]
            if previous == -1:
                direction[i] = -1 if closes[i] <= final_upper else 1
            else:
                direction[i] = 1 if closes[i] >= final_lower else -1
        line[i] = final_lower if direction[i] == 1 else final_upper
    return line, direction


def historical_volatility(
    closes: Sequence[float], period: int = 20, periods_per_year: int = 252
) -> float | None:
    """Annualised volatility (percent) from the last `period` log returns."""
    if len(closes) < period + 1:
        return None
    returns = [
        math.log(closes[i] / closes[i - 1])
        for i in range(len(closes) - period, len(closes))
        if closes[i - 1] > 0 and closes[i] > 0
    ]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(periods_per_year) * 100


def swing_points(
    highs: Sequence[float], lows: Sequence[float], left: int = 2, right: int = 2
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Confirmed swing highs and lows as (index, price). The last `right` bars cannot be swings yet."""
    swing_highs: list[tuple[int, float]] = []
    swing_lows: list[tuple[int, float]] = []
    for i in range(left, len(highs) - right):
        if all(highs[i] > highs[j] for j in range(i - left, i)) and all(
            highs[i] >= highs[j] for j in range(i + 1, i + right + 1)
        ):
            swing_highs.append((i, highs[i]))
        if all(lows[i] < lows[j] for j in range(i - left, i)) and all(
            lows[i] <= lows[j] for j in range(i + 1, i + right + 1)
        ):
            swing_lows.append((i, lows[i]))
    return swing_highs, swing_lows


def cluster_levels(prices: Sequence[float], tolerance_pct: float = 0.4) -> list[tuple[float, int]]:
    """Group nearby prices into support/resistance levels. Returns (level, touches), strongest first."""
    groups: list[list[float]] = []
    for price in sorted(prices):
        if groups and abs(price - sum(groups[-1]) / len(groups[-1])) / price * 100 <= tolerance_pct:
            groups[-1].append(price)
        else:
            groups.append([price])
    levels = [(sum(g) / len(g), len(g)) for g in groups]
    return sorted(levels, key=lambda item: (-item[1], item[0]))


def last(series: Sequence[float | None]) -> float | None:
    return series[-1] if series else None
