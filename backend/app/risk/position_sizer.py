"""Risk based position sizing: quantity = (capital * risk%) / |entry - stop|, then capped."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SizingResult:
    quantity: int
    risk_per_share: float
    max_risk_amount: float
    risk_amount: float  # actual risk taken with the (possibly capped) quantity
    capped_by: str | None = None


class PositionSizer:
    def __init__(self, max_position_size: int | None = None, max_order_value: float | None = None) -> None:
        self.max_position_size = max_position_size
        self.max_order_value = max_order_value

    def size(
        self,
        capital: float,
        risk_fraction: float,
        entry_price: float,
        stop_loss_price: float,
        *,
        available_capital: float | None = None,
        lot_size: int = 1,
    ) -> SizingResult:
        if capital <= 0 or entry_price <= 0:
            raise ValueError("capital and entry_price must be positive")
        if not 0 < risk_fraction <= 1:
            raise ValueError("risk_fraction must be in (0, 1]")
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            raise ValueError("stop_loss_price must differ from entry_price")

        max_risk = capital * risk_fraction
        quantity = math.floor(max_risk / risk_per_share + 1e-9)
        capped_by: str | None = None

        caps = {
            "max_position_size": self.max_position_size,
            "max_order_value": (
                math.floor(self.max_order_value / entry_price) if self.max_order_value else None
            ),
            "available_capital": (
                math.floor(min(available_capital, capital) / entry_price)
                if available_capital is not None
                else math.floor(capital / entry_price)
            ),
        }
        for name, cap in caps.items():
            if cap is not None and quantity > cap:
                quantity, capped_by = max(int(cap), 0), name

        lot_size = max(lot_size, 1)
        quantity -= quantity % lot_size
        return SizingResult(
            quantity,
            round(risk_per_share, 4),
            round(max_risk, 2),
            round(quantity * risk_per_share, 2),
            capped_by,
        )
