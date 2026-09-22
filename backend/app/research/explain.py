"""Explains why a research score changed between two runs, from the stored reports only (no new facts)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ComponentChange(BaseModel):
    key: str
    label: str
    from_points: float
    to_points: float
    delta: float


class ScoreChange(BaseModel):
    from_run_id: str
    to_run_id: str
    from_as_of: str
    to_as_of: str
    from_score: float | None
    to_score: float | None
    delta: float | None
    reasons: list[str]
    component_changes: list[ComponentChange]


def _get(d: dict[str, Any] | None, *path: str) -> Any:
    for key in path:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def explain_change(prev: dict[str, Any], curr: dict[str, Any], prev_run: str, curr_run: str) -> ScoreChange:
    a, b = _get(prev, "research_score"), _get(curr, "research_score")
    delta = None if a is None or b is None else round(b - a, 1)
    reasons: list[str] = []

    # Causes that are about HOW the score was produced come first: they are the most common reason for a jump.
    wa, wb = _get(prev, "score", "weight_set_version"), _get(curr, "score", "weight_set_version")
    if wa is not None and wb is not None and wa != wb:
        reasons.append(f"Scoring weights changed from version {wa} to version {wb}")
    ca_cov, cb_cov = _get(prev, "score_coverage_pct"), _get(curr, "score_coverage_pct")
    if ca_cov is not None and cb_cov is not None and abs(cb_cov - ca_cov) >= 1:
        reasons.append(
            f"The score now covers {cb_cov:.0f}% of the scoring weights (it covered {ca_cov:.0f}%)"
        )

    ra, rb = _get(prev, "price", "rel_volume"), _get(curr, "price", "rel_volume")
    if ra is not None and rb is not None and abs(rb - ra) >= 0.3:
        reasons.append(f"Relative volume {'increased' if rb > ra else 'fell'} from {ra:.1f}x to {rb:.1f}x")
    va, vb = _get(prev, "technical", "levels", "vwap_position"), _get(
        curr, "technical", "levels", "vwap_position"
    )
    if va and vb and va != vb:
        reasons.append(
            "Price reclaimed VWAP"
            if vb == "ABOVE"
            else (
                "Price lost VWAP"
                if vb == "BELOW"
                else f"Price moved from {va.lower()} VWAP to {vb.lower()} VWAP"
            )
        )
    da, db = _get(prev, "direction"), _get(curr, "direction")
    if da and db and da != db:
        reasons.append(f"Setup direction changed from {da.lower()} to {db.lower()}")
    ga, gb = _get(prev, "market_context", "regime", "label"), _get(curr, "market_context", "regime", "label")
    if ga and gb and ga != gb:
        reasons.append(
            f"Market regime changed from {ga.replace('_', ' ').lower()} to {gb.replace('_', ' ').lower()}"
        )
    sa, sb = _get(prev, "sector_context", "rel_strength_1d"), _get(curr, "sector_context", "rel_strength_1d")
    if sa is not None and sb is not None and (sa > 0.3) != (sb > 0.3) and abs(sb - sa) >= 0.3:
        reasons.append("Sector momentum improved" if sb > sa else "Sector momentum weakened")
    aa, ab = _get(prev, "volatility", "atr_pct"), _get(curr, "volatility", "atr_pct")
    if aa and ab and abs(ab - aa) / aa >= 0.25:
        reasons.append(
            f"Volatility {'increased' if ab > aa else 'decreased'} (daily ATR {aa:.1f}% to {ab:.1f}%)"
        )
    fa = {f["code"] for f in _get(prev, "risk", "flags") or []}
    fb = {f["code"] for f in _get(curr, "risk", "flags") or []}
    for code in sorted(fb - fa):
        reasons.append(f"New risk flag: {code.replace('_', ' ').lower()}")
    for code in sorted(fa - fb):
        reasons.append(f"Risk flag cleared: {code.replace('_', ' ').lower()}")
    ca, cb = _get(prev, "data_confidence"), _get(curr, "data_confidence")
    if ca is not None and cb is not None and abs(cb - ca) >= 10:
        reasons.append(f"Data confidence {'rose' if cb > ca else 'fell'} from {ca:.0f} to {cb:.0f}")
    prev_hist, curr_hist = _get(prev, "historical"), _get(curr, "historical")
    if bool(prev_hist) != bool(curr_hist):
        reasons.append(
            "Historical setup statistics were run in this scan"
            if curr_hist
            else "Historical setup statistics were not run in this scan (a shallower research depth)"
        )
    elif prev_hist and curr_hist and bool(prev_hist.get("matched")) != bool(curr_hist.get("matched")):
        reasons.append(
            "A historical sample of the setup became large enough to use"
            if curr_hist.get("matched")
            else "The historical sample of the setup is no longer large enough to use"
        )

    prev_components = {c["key"]: c for c in _get(prev, "score", "components") or []}
    changes: list[ComponentChange] = []
    for c in _get(curr, "score", "components") or []:
        before = prev_components.get(c["key"])
        if (
            before is None
            or not (before["available"] and c["available"])
            or not before["max_points"]
            or not c["max_points"]
        ):
            continue
        # compare the share of each component's maximum, at the current weight, so a re-weighting is not mistaken for a market change
        before_at_current_weight = before["points"] / before["max_points"] * c["max_points"]
        d = round(c["points"] - before_at_current_weight, 2)
        if abs(d) >= 0.5:
            changes.append(
                ComponentChange(
                    key=c["key"],
                    label=c["label"],
                    from_points=round(before_at_current_weight, 2),
                    to_points=c["points"],
                    delta=d,
                )
            )
    changes.sort(key=lambda x: -abs(x.delta))
    if not reasons and changes:
        reasons = [
            f"{ch.label} {'rose' if ch.delta > 0 else 'fell'} by {abs(ch.delta):.1f} points"
            for ch in changes[:3]
        ]
    if not reasons:
        reasons = ["No material change in the underlying measurements"]
    return ScoreChange(
        from_run_id=prev_run,
        to_run_id=curr_run,
        from_as_of=str(_get(prev, "as_of")),
        to_as_of=str(_get(curr, "as_of")),
        from_score=a,
        to_score=b,
        delta=delta,
        reasons=reasons,
        component_changes=changes[:5],
    )
