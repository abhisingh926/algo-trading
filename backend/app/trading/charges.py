"""Transaction cost model shared by the paper trading engine and the backtester."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.domain.enums import OrderSide


@dataclass(frozen=True, slots=True)
class ChargesConfig:
    brokerage_per_order: float = 20.0  # flat cap per executed order (INR)
    brokerage_pct: float = 0.0003  # of turnover; brokerage = min(pct * turnover, per_order) when both set
    stt_sell_pct: float = 0.00025
    exchange_txn_pct: float = 0.0000297
    sebi_pct: float = 0.000001
    stamp_duty_buy_pct: float = 0.00003
    gst_pct: float = 0.18  # on brokerage + exchange + SEBI charges

    def without_statutory(self) -> ChargesConfig:
        return ChargesConfig(self.brokerage_per_order, self.brokerage_pct, 0, 0, 0, 0, 0)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChargesCalculator:
    def __init__(self, config: ChargesConfig) -> None:
        self.config = config

    def brokerage(self, turnover: float) -> float:
        cfg = self.config
        if cfg.brokerage_pct > 0 and cfg.brokerage_per_order > 0:
            return min(cfg.brokerage_pct * turnover, cfg.brokerage_per_order)
        return cfg.brokerage_pct * turnover if cfg.brokerage_pct > 0 else cfg.brokerage_per_order

    def compute(self, side: OrderSide, price: float, quantity: int) -> float:
        """Total charges in INR for one executed order."""
        cfg = self.config
        turnover = abs(price * quantity)
        if turnover == 0:
            return 0.0
        brokerage = self.brokerage(turnover)
        exchange = cfg.exchange_txn_pct * turnover
        sebi = cfg.sebi_pct * turnover
        stt = cfg.stt_sell_pct * turnover if side is OrderSide.SELL else 0.0
        stamp = cfg.stamp_duty_buy_pct * turnover if side is OrderSide.BUY else 0.0
        gst = cfg.gst_pct * (brokerage + exchange + sebi)
        return round(brokerage + exchange + sebi + stt + stamp + gst, 4)
