"""Default scoring weights and thresholds. The live values are stored in the database (research_weight_sets) so
they are configurable; these defaults seed the first set and fill any missing key."""

from __future__ import annotations

from typing import Any

COMPONENT_ORDER = [
    "market_regime",
    "liquidity",
    "price_action",
    "momentum",
    "volume",
    "volatility",
    "technical_setup",
    "news_catalyst",
    "historical_setup",
    "risk",
]
COMPONENT_LABELS = {
    "market_regime": "Market Regime",
    "liquidity": "Liquidity",
    "price_action": "Price Action",
    "momentum": "Momentum",
    "volume": "Volume",
    "volatility": "Volatility Suitability",
    "technical_setup": "Technical Setup",
    "news_catalyst": "News / Catalyst",
    "historical_setup": "Historical Setup Quality",
    "risk": "Risk",
}
DEFAULT_WEIGHTS: dict[str, float] = {
    "market_regime": 10,
    "liquidity": 15,
    "price_action": 15,
    "momentum": 10,
    "volume": 10,
    "volatility": 10,
    "technical_setup": 10,
    "news_catalyst": 10,
    "historical_setup": 5,
    "risk": 5,
}
DEFAULT_THRESHOLDS: dict[str, Any] = {
    "liquidity_value_lo_cr": 2.0,
    "liquidity_value_hi_cr": 200.0,
    "liquidity_volume_lo": 100_000,
    "liquidity_volume_hi": 5_000_000,
    "spread_good_bps": 2.0,
    "spread_bad_bps": 30.0,
    "atr_pct_zero_low": 0.3,
    "atr_pct_ideal_low": 1.0,
    "atr_pct_ideal_high": 2.5,
    "atr_pct_zero_high": 6.0,
    "min_sample": 30,
    "risk_cap_score": 70.0,
    "round_trip_cost_pct": 0.10,
    "setup_strong": 75.0,
    "setup_moderate": 55.0,
    "prefilter_min_traded_value_cr": 2.0,
    "prefilter_min_price": 20.0,
    "flag_low_liquidity_cr": 10.0,
    "flag_very_low_liquidity_cr": 2.0,
    "flag_wide_spread_bps": 20.0,
    "flag_extreme_atr_pct": 5.0,
    "flag_large_gap_pct": 3.0,
    "flag_unusual_rvol": 5.0,
    "flag_unusual_move_atr": 2.5,
    "stale_minutes_open": 20.0,
    "vix_high": 20.0,
    "vix_low": 12.0,
}
# Fraction of the Risk component's points removed per flag severity.
RISK_DEDUCTION = {"HIGH": 0.5, "WARNING": 0.2, "INFO": 0.05}


def merge_thresholds(stored: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_THRESHOLDS, **(stored or {})}


def validate_weights(weights: dict[str, float]) -> list[str]:
    errors = []
    unknown = set(weights) - set(DEFAULT_WEIGHTS)
    missing = set(DEFAULT_WEIGHTS) - set(weights)
    if unknown:
        errors.append(f"Unknown components: {', '.join(sorted(unknown))}")
    if missing:
        errors.append(f"Missing components: {', '.join(sorted(missing))}")
    if any(v < 0 for v in weights.values()):
        errors.append("Weights cannot be negative")
    total = sum(weights.values())
    if abs(total - 100) > 1e-6:
        errors.append(f"Weights must add up to 100 (they add up to {total:g})")
    return errors
