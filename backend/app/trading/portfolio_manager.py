"""Portfolio level numbers: capital, margin in use, equity, snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import PositionStatus, TradingMode
from app.models.daily_pnl import PortfolioSnapshot
from app.repositories.pnl_repository import PnlRepository
from app.repositories.position_repository import PositionRepository
from app.repositories.trade_repository import TradeRepository


@dataclass(frozen=True, slots=True)
class PortfolioState:
    capital: float  # starting capital + all realised net P&L
    used_margin: float
    available: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int

    @property
    def equity(self) -> float:
        return self.capital + self.unrealized_pnl


class PortfolioManager:
    def __init__(
        self,
        positions: PositionRepository,
        trades: TradeRepository,
        pnl: PnlRepository,
        starting_capital: float,
    ) -> None:
        self.positions = positions
        self.trades = trades
        self.pnl = pnl
        self.starting_capital = starting_capital

    async def state(self, mode: TradingMode) -> PortfolioState:
        totals = await self.trades.aggregate(mode=mode)
        open_positions = [
            p for p in await self.positions.list_positions(PositionStatus.OPEN) if p.trading_mode is mode
        ]
        used = sum(p.quantity * p.average_entry_price for p in open_positions)
        unrealized = sum(p.unrealized_pnl for p in open_positions)
        capital = self.starting_capital + totals["net_pnl"]
        return PortfolioState(
            capital=round(capital, 2),
            used_margin=round(used, 2),
            available=round(capital - used, 2),
            realized_pnl=round(totals["net_pnl"], 2),
            unrealized_pnl=round(unrealized, 2),
            open_positions=len(open_positions),
        )

    async def snapshot(self, mode: TradingMode, *, force: bool = False) -> PortfolioSnapshot | None:
        """Persist an equity point, skipping it when nothing changed since the last one."""
        state = await self.state(mode)
        last = await self.pnl.latest_snapshot(mode)
        if (
            not force
            and last is not None
            and abs(last.equity - state.equity) < 0.01
            and last.open_positions == state.open_positions
        ):
            return None
        return await self.pnl.add_snapshot(
            PortfolioSnapshot(
                trading_mode=mode,
                equity=round(state.equity, 2),
                realized_pnl=state.realized_pnl,
                unrealized_pnl=state.unrealized_pnl,
                open_positions=state.open_positions,
            )
        )
