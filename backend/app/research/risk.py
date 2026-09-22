"""Risk layer: liquidity, volatility, gap, unusual-activity and market-level checks, plus the data-quality flags
added after verification. Checks that need a data source we do not have are listed as NOT CHECKED, never guessed.
"""

from __future__ import annotations

from typing import Any

from app.research.contracts import (
    MarketContext,
    Provenance,
    RiskAssessment,
    RiskFlag,
    RiskLevel,
    VerificationReport,
)
from app.research.features import TechnicalBundle

NOT_CHECKED = [
    "Circuit limits and price bands",
    "ASM / GSM surveillance status",
    "Earnings and corporate-event proximity",
    "Regulatory actions and trading restrictions",
]


def market_risk_level(market: MarketContext) -> RiskLevel:
    regime = market.regime
    if regime.label == "UNKNOWN":
        return "UNKNOWN"
    if regime.volatility == "HIGH" or regime.label == "STRONG_BEARISH":
        return "HIGH"
    if regime.label in ("BEARISH", "RANGE"):
        return "MEDIUM"
    return "LOW"


def assess_risk(
    bundle: TechnicalBundle, market: MarketContext, thresholds: dict[str, Any], provenance: Provenance
) -> RiskAssessment:
    p, v = bundle.price, bundle.volatility
    flags: list[RiskFlag] = []
    unavailable = list(NOT_CHECKED)

    value = p.avg_traded_value_cr
    if value is not None:
        if value < thresholds["flag_very_low_liquidity_cr"]:
            flags.append(
                RiskFlag(
                    code="LOW_LIQUIDITY",
                    severity="HIGH",
                    message=f"Very low liquidity: ₹{value:.1f} crore traded per day",
                    metric="avg_traded_value_cr",
                    value=value,
                )
            )
        elif value < thresholds["flag_low_liquidity_cr"]:
            flags.append(
                RiskFlag(
                    code="LOW_LIQUIDITY",
                    severity="WARNING",
                    message=f"Low liquidity: ₹{value:.1f} crore traded per day",
                    metric="avg_traded_value_cr",
                    value=value,
                )
            )
    if p.spread_bps is None:
        unavailable.append("Bid/ask spread (not provided by this data source)")
    elif p.spread_bps > thresholds["flag_wide_spread_bps"]:
        flags.append(
            RiskFlag(
                code="LARGE_SPREAD",
                severity="WARNING",
                message=f"Wide bid/ask spread of {p.spread_bps:.1f} bps",
                metric="spread_bps",
                value=p.spread_bps,
            )
        )
    if v.atr_pct is not None and v.atr_pct > thresholds["flag_extreme_atr_pct"]:
        flags.append(
            RiskFlag(
                code="EXTREME_VOLATILITY",
                severity="HIGH",
                message=f"Extreme volatility: daily ATR is {v.atr_pct:.1f}% of price",
                metric="atr_pct",
                value=v.atr_pct,
            )
        )
    gap = abs(p.gap_pct or 0.0)
    if gap > thresholds["flag_large_gap_pct"] * 2:
        flags.append(
            RiskFlag(
                code="LARGE_GAP",
                severity="HIGH",
                message=f"Very large opening gap of {p.gap_pct:+.1f}%",
                metric="gap_pct",
                value=p.gap_pct,
            )
        )
    elif gap > thresholds["flag_large_gap_pct"]:
        flags.append(
            RiskFlag(
                code="LARGE_GAP",
                severity="WARNING",
                message=f"Large opening gap of {p.gap_pct:+.1f}%",
                metric="gap_pct",
                value=p.gap_pct,
            )
        )
    if v.atr_pct and p.change_pct is not None:
        move = abs(p.change_pct) / v.atr_pct
        if move > thresholds["flag_unusual_move_atr"]:
            flags.append(
                RiskFlag(
                    code="UNUSUAL_PRICE_MOVE",
                    severity="WARNING",
                    message=f"Unusual price move: {p.change_pct:+.1f}% is {move:.1f}x the daily ATR",
                    metric="move_in_atr",
                    value=move,
                )
            )
    if p.rel_volume is not None and p.rel_volume > thresholds["flag_unusual_rvol"]:
        flags.append(
            RiskFlag(
                code="UNUSUAL_VOLUME",
                severity="WARNING",
                message=f"Unusual volume: {p.rel_volume:.1f}x the normal level for this time of day",
                metric="rel_volume",
                value=p.rel_volume,
            )
        )

    liquidity: RiskLevel = (
        "UNKNOWN"
        if value is None
        else "LOW" if value >= 25 else "MEDIUM" if value >= thresholds["flag_low_liquidity_cr"] else "HIGH"
    )
    if p.spread_bps is not None and p.spread_bps > thresholds["flag_wide_spread_bps"] and liquidity == "LOW":
        liquidity = "MEDIUM"
    volatility: RiskLevel = (
        "UNKNOWN"
        if v.atr_pct is None
        else "LOW" if v.atr_pct <= 2.5 else "MEDIUM" if v.atr_pct <= 4.0 else "HIGH"
    )
    market_level = market_risk_level(market)
    return RiskAssessment(
        flags=flags,
        liquidity_risk=liquidity,
        volatility_risk=volatility,
        event_risk="UNKNOWN",
        corporate_risk="UNKNOWN",
        data_risk="UNKNOWN",
        market_risk=market_level,
        overall=overall_level(flags, [liquidity, volatility, market_level]),
        unavailable_checks=unavailable,
        provenance=provenance,
    )


def overall_level(flags: list[RiskFlag], levels: list[RiskLevel]) -> RiskLevel:
    if any(f.severity == "HIGH" for f in flags):
        return "HIGH"
    if any(f.severity == "WARNING" for f in flags) or any(level in ("MEDIUM", "HIGH") for level in levels):
        return "MEDIUM"
    return "LOW"


def data_flags(
    verification: VerificationReport,
    is_synthetic: bool,
    historical_adequate: bool | None,
    stale: bool,
    stale_message: str | None,
) -> list[RiskFlag]:
    """Flags derived from data quality rather than the market itself."""
    flags: list[RiskFlag] = []
    if is_synthetic:
        flags.append(
            RiskFlag(
                code="SYNTHETIC_DATA",
                severity="WARNING",
                message="Prices and volumes are synthetic test data, not the real market",
            )
        )
    conflicts = [c for c in verification.claims if c.status == "CONFLICTING"]
    if conflicts:
        flags.append(
            RiskFlag(
                code="CONFLICTING_DATA",
                severity="WARNING",
                message=f"{len(conflicts)} data check(s) found conflicting values",
                value=float(len(conflicts)),
            )
        )
    if stale:
        flags.append(
            RiskFlag(code="STALE_DATA", severity="WARNING", message=stale_message or "Market data is stale")
        )
    if historical_adequate is False:
        flags.append(
            RiskFlag(
                code="LOW_SAMPLE",
                severity="INFO",
                message="Historical sample of today's setup is too small to rely on",
            )
        )
    return flags


def data_risk_level(verification: VerificationReport, is_synthetic: bool, stale: bool) -> RiskLevel:
    if is_synthetic or any(c.status == "CONFLICTING" for c in verification.claims):
        return "HIGH"
    if stale or verification.data_confidence < 60:
        return "MEDIUM"
    return "LOW"
