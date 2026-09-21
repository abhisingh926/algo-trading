"""Small, dependency-free technical indicators."""

from __future__ import annotations

from collections.abc import Sequence


def ema(values: Sequence[float], period: int) -> list[float]:
    """Exponential moving average seeded with the SMA of the first `period` values.

    Returns a list aligned with `values`; entries before `period - 1` are NaN-free placeholders
    equal to the running SMA so callers can index safely.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []
    k = 2 / (period + 1)
    out: list[float] = []
    running = 0.0
    for i, value in enumerate(values):
        if i < period:
            running += value
            out.append(running / (i + 1))
        else:
            out.append(value * k + out[-1] * (1 - k))
    return out


def vwap(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], volumes: Sequence[float]
) -> list[float]:
    """Cumulative volume weighted average price using the typical price."""
    out: list[float] = []
    cum_pv = cum_v = 0.0
    for h, l, c, v in zip(highs, lows, closes, volumes, strict=True):  # noqa: E741
        typical = (h + l + c) / 3
        weight = v if v > 0 else 1.0
        cum_pv += typical * weight
        cum_v += weight
        out.append(cum_pv / cum_v)
    return out
