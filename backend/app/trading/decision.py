"""Translates a strategy signal + current position into actions. Shared by live engine and backtester."""

from __future__ import annotations

from enum import StrEnum

from app.domain.enums import PositionSide, SignalType


class Action(StrEnum):
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT = "EXIT"


def decide_actions(signal: SignalType, position: PositionSide | None, allow_short: bool) -> list[Action]:
    if signal is SignalType.BUY:
        if position is None:
            return [Action.ENTER_LONG]
        if position is PositionSide.SHORT:
            return [Action.EXIT, Action.ENTER_LONG]
    elif signal is SignalType.SELL:
        if position is PositionSide.LONG:
            return [Action.EXIT, Action.ENTER_SHORT] if allow_short else [Action.EXIT]
        if position is None and allow_short:
            return [Action.ENTER_SHORT]
    return []


def protective_levels(
    side: PositionSide, entry_price: float, stop_loss_pct: float, target_pct: float | None
) -> tuple[float, float | None]:
    """Stop loss / target prices for an entry."""
    stop = entry_price * (1 - stop_loss_pct * side.sign)
    target = entry_price * (1 + target_pct * side.sign) if target_pct else None
    return round(stop, 2), round(target, 2) if target is not None else None
