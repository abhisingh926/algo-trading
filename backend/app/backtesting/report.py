"""Assembles the backtest report payload served by GET /backtests/{id}/report."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Protocol

from app.utils.time import IST, ensure_utc


class _TradeLike(Protocol):
    exit_time: Any
    net_pnl: float


def monthly_returns(trades: Sequence[_TradeLike]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"net_pnl": 0.0, "trades": 0})
    for trade in trades:
        month = ensure_utc(trade.exit_time).astimezone(IST).strftime("%Y-%m")
        buckets[month]["net_pnl"] += float(trade.net_pnl)
        buckets[month]["trades"] += 1
    return [
        {"month": month, "net_pnl": round(v["net_pnl"], 2), "trades": int(v["trades"])}
        for month, v in sorted(buckets.items())
    ]
