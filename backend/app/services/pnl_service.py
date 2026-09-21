from __future__ import annotations

from datetime import timedelta

from app.backtesting.metrics import max_drawdown, trade_stats
from app.domain.enums import StrategyStatus, TradingMode
from app.models.daily_pnl import DailyPnL
from app.models.trade import Trade
from app.repositories.pnl_repository import PnlRepository
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.dashboard import (
    DailyPnlRead,
    DashboardSummary,
    EquityPointRead,
    Performance,
    PnlSeries,
    StrategyPerformance,
)
from app.trading.portfolio_manager import PortfolioManager
from app.utils.time import ist_date, ist_day_start_utc, ist_today, utcnow

_PERFORMANCE_TRADE_CAP = 20_000


def _win_rate(wins: float, trades: float) -> float:
    return round(wins / trades * 100, 2) if trades else 0.0


class PnlService:
    def __init__(
        self,
        pnl: PnlRepository,
        trades: TradeRepository,
        strategies: StrategyRepository,
        portfolio: PortfolioManager,
        mode: TradingMode,
    ) -> None:
        self.pnl = pnl
        self.trades = trades
        self.strategies = strategies
        self.portfolio = portfolio
        self.mode = mode

    async def record_trade(self, trade: Trade) -> None:
        """Roll a closed trade into the daily P&L row (called by the PositionManager)."""
        day = ist_date(trade.exit_time)
        row = await self.pnl.get_day(day, trade.trading_mode)
        if row is None:
            row = await self.pnl.create(
                DailyPnL(
                    trade_date=day,
                    trading_mode=trade.trading_mode,
                    realized_pnl=0,
                    unrealized_pnl=0,
                    charges=0,
                    net_pnl=0,
                    trades=0,
                    wins=0,
                    losses=0,
                )
            )
        row.realized_pnl += trade.gross_pnl
        row.charges += trade.charges
        row.net_pnl += trade.net_pnl
        row.trades += 1
        row.wins += 1 if trade.net_pnl > 0 else 0
        row.losses += 1 if trade.net_pnl < 0 else 0
        await self.pnl.update(row)

    async def mark_unrealized(self, unrealized: float) -> None:
        row = await self.pnl.get_day(ist_today(), self.mode)
        if row is not None and abs(row.unrealized_pnl - unrealized) >= 0.01:
            row.unrealized_pnl = round(unrealized, 2)
            await self.pnl.update(row)

    async def summary(self) -> DashboardSummary:
        state = await self.portfolio.state(self.mode)
        today = await self.trades.aggregate(mode=self.mode, since=ist_day_start_utc())
        overall = await self.trades.aggregate(mode=self.mode)
        return DashboardSummary(
            capital=state.capital,
            available=state.available,
            used_margin=state.used_margin,
            todays_pnl=round(today["net_pnl"] + state.unrealized_pnl, 2),
            realized_pnl_today=round(today["net_pnl"], 2),
            open_pnl=state.unrealized_pnl,
            total_pnl=round(overall["net_pnl"] + state.unrealized_pnl, 2),
            win_rate=_win_rate(overall["wins"], overall["trades"]),
            trades_today=int(today["trades"]),
            open_positions=state.open_positions,
            running_strategies=await self.strategies.count_by_status(StrategyStatus.RUNNING),
            trading_mode=self.mode,
        )

    async def series(self, days: int) -> PnlSeries:
        since_day = ist_today() - timedelta(days=days)
        daily = await self.pnl.list_days(since_day, self.mode)
        snapshots = await self.pnl.list_snapshots(utcnow() - timedelta(days=days), self.mode)
        return PnlSeries(
            daily=[
                DailyPnlRead(
                    date=d.trade_date,
                    realized_pnl=d.realized_pnl,
                    unrealized_pnl=d.unrealized_pnl,
                    charges=d.charges,
                    net_pnl=d.net_pnl,
                    trades=d.trades,
                    wins=d.wins,
                    losses=d.losses,
                )
                for d in daily
            ],
            equity_curve=[
                EquityPointRead(
                    timestamp=s.timestamp,
                    equity=s.equity,
                    realized_pnl=s.realized_pnl,
                    unrealized_pnl=s.unrealized_pnl,
                )
                for s in snapshots
            ],
        )

    async def performance(self) -> Performance:
        trades = [
            t
            for t in await self.trades.list_trades(limit=_PERFORMANCE_TRADE_CAP, ascending=True)
            if t.trading_mode is self.mode
        ]
        stats = trade_stats(trades)
        equity, running = [self.portfolio.starting_capital], self.portfolio.starting_capital
        for trade in trades:
            running += trade.net_pnl
            equity.append(running)
        dd_amount, dd_pct = max_drawdown(equity)

        names = {s.id: s.name for s in await self.strategies.get_all()}
        by_strategy = [
            StrategyPerformance(
                strategy_id=sid,
                strategy_name=names.get(sid, "Deleted strategy"),
                trades=int(agg["trades"]),
                win_rate=_win_rate(agg["wins"], agg["trades"]),
                net_pnl=round(agg["net_pnl"], 2),
            )
            for sid, agg in (await self.trades.aggregate_by_strategy()).items()
        ]
        return Performance(
            **stats.to_dict(),
            max_drawdown=round(dd_amount, 2),
            max_drawdown_pct=round(dd_pct, 3),
            total_charges=round(sum(t.charges for t in trades), 2),
            by_strategy=sorted(by_strategy, key=lambda s: s.net_pnl, reverse=True),
        )
