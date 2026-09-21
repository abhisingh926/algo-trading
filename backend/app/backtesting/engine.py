"""Event-driven bar backtester.

Realism rules:
  * A signal computed on the close of bar N is executed at the OPEN of bar N+1 (no look-ahead).
  * Every fill pays slippage and the full charges model.
  * Stop loss / target are checked intrabar on high/low; if both are touched in one bar the STOP is
    assumed to have been hit first (conservative). Gaps through a level fill at the bar open.
  * Position size comes from the same PositionSizer the live engine uses.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.backtesting.broker_simulator import BrokerSimulator, SimTrade
from app.backtesting.metrics import drawdown_series, max_drawdown, sharpe_ratio, trade_stats
from app.domain.enums import ExitReason, PositionSide
from app.domain.types import Candle
from app.risk.position_sizer import PositionSizer
from app.strategies.base import Strategy
from app.trading.charges import ChargesCalculator, ChargesConfig
from app.trading.decision import Action, decide_actions, protective_levels

MAX_EQUITY_POINTS = 1500


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    symbol: str
    initial_capital: float
    risk_per_trade: float
    stop_loss_pct: float
    target_pct: float | None = None
    allow_short: bool = False
    slippage_pct: float = 0.0005
    charges: ChargesConfig = field(default_factory=ChargesConfig)
    max_position_size: int | None = None
    max_order_value: float | None = None


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: datetime
    equity: float
    drawdown: float
    drawdown_pct: float


@dataclass(slots=True)
class BacktestResult:
    trades: list[SimTrade]
    equity_curve: list[EquityPoint]
    metrics: dict[str, Any]


class BacktestEngine:
    def __init__(self, strategy: Strategy, config: BacktestConfig) -> None:
        if config.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not 0 < config.stop_loss_pct < 1:
            raise ValueError("stop_loss_pct must be between 0 and 1")
        self.strategy = strategy
        self.config = config
        self.sizer = PositionSizer(config.max_position_size, config.max_order_value)

    def run(self, candles: Sequence[Candle]) -> BacktestResult:
        cfg = self.config
        sim = BrokerSimulator(
            cfg.symbol, cfg.initial_capital, cfg.slippage_pct, ChargesCalculator(cfg.charges)
        )
        lookback = self.strategy.lookback_bars
        pending: list[Action] = []
        timestamps: list[datetime] = []
        equity: list[float] = []

        for i, bar in enumerate(candles):
            self._execute(sim, pending, bar)
            self._check_protective_exit(sim, bar)
            timestamps.append(bar.timestamp)
            equity.append(round(sim.equity(bar.close), 2))
            if i < len(candles) - 1:
                window = candles[max(0, i + 1 - lookback) : i + 1]
                signal = self.strategy.generate_signal(window)
                side = sim.position.side if sim.position else None
                pending = decide_actions(signal.type, side, cfg.allow_short)

        if sim.position is not None and candles:
            sim.close(candles[-1].close, candles[-1].timestamp, ExitReason.END_OF_DATA)
            equity[-1] = round(sim.realized_equity, 2)

        return BacktestResult(
            sim.trades, self._curve(timestamps, equity), self._metrics(sim, timestamps, equity, len(candles))
        )

    # ---- execution -----------------------------------------------------------------------------
    def _execute(self, sim: BrokerSimulator, actions: list[Action], bar: Candle) -> None:
        for action in actions:
            if action is Action.EXIT:
                if sim.position is not None:
                    sim.close(bar.open, bar.timestamp, ExitReason.SIGNAL)
            elif sim.position is None:
                self._enter(
                    sim, PositionSide.LONG if action is Action.ENTER_LONG else PositionSide.SHORT, bar
                )

    def _enter(self, sim: BrokerSimulator, side: PositionSide, bar: Candle) -> None:
        cfg = self.config
        capital = sim.realized_equity
        if capital <= 0:
            return
        stop, target = protective_levels(side, bar.open, cfg.stop_loss_pct, cfg.target_pct)
        quantity = self.sizer.size(
            capital, cfg.risk_per_trade, bar.open, stop, available_capital=capital
        ).quantity
        if quantity > 0:
            sim.open(side, quantity, bar.open, bar.timestamp, stop, target)

    @staticmethod
    def _check_protective_exit(sim: BrokerSimulator, bar: Candle) -> None:
        p = sim.position
        if p is None:
            return
        long = p.side is PositionSide.LONG
        stop_hit = bar.low <= p.stop_loss if long else bar.high >= p.stop_loss
        if stop_hit:
            gapped = bar.open <= p.stop_loss if long else bar.open >= p.stop_loss
            sim.close(bar.open if gapped else p.stop_loss, bar.timestamp, ExitReason.STOP_LOSS)
            return
        if p.target is not None and (bar.high >= p.target if long else bar.low <= p.target):
            gapped = bar.open >= p.target if long else bar.open <= p.target
            sim.close(bar.open if gapped else p.target, bar.timestamp, ExitReason.TARGET)

    # ---- reporting -----------------------------------------------------------------------------
    @staticmethod
    def _curve(timestamps: list[datetime], equity: list[float]) -> list[EquityPoint]:
        amounts, percents = drawdown_series(equity)
        n = len(equity)
        stride = max(1, -(-n // MAX_EQUITY_POINTS))
        indexes = sorted(set(range(0, n, stride)) | ({n - 1} if n else set()))
        return [EquityPoint(timestamps[i], equity[i], amounts[i], percents[i]) for i in indexes]

    def _metrics(
        self, sim: BrokerSimulator, timestamps: list[datetime], equity: list[float], bars: int
    ) -> dict[str, Any]:
        initial = self.config.initial_capital
        final = round(sim.realized_equity, 2)
        dd_amount, dd_pct = max_drawdown([initial, *equity])
        return {
            **trade_stats(sim.trades).to_dict(),
            "final_capital": final,
            "net_pnl": round(final - initial, 2),
            "total_return_pct": round((final / initial - 1) * 100, 3),
            "max_drawdown": round(dd_amount, 2),
            "max_drawdown_pct": round(dd_pct, 3),
            "sharpe_ratio": sharpe_ratio(timestamps, equity),
            "total_charges": round(sim.total_charges, 2),
            "total_slippage": round(sim.total_slippage, 2),
            "candles_processed": bars,
        }
