from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.domain.enums import EventLevel, TradingMode
from app.models.risk import RiskConfiguration
from app.models.strategy import Strategy
from app.repositories.position_repository import PositionRepository
from app.repositories.risk_repository import RiskRepository
from app.repositories.trade_repository import TradeRepository
from app.risk.limits import OrderIntent, RiskContext, RiskDecision, RiskLimits
from app.risk.risk_manager import RiskManager
from app.schemas.risk import RiskStatus, RiskUsage
from app.services.event_service import EventService
from app.trading.portfolio_manager import PortfolioManager
from app.utils.time import ist_day_start_utc, utcnow


class RiskService:
    def __init__(
        self,
        risk: RiskRepository,
        trades: TradeRepository,
        positions: PositionRepository,
        portfolio: PortfolioManager,
        events: EventService,
        settings: Settings,
    ) -> None:
        self.risk = risk
        self.trades = trades
        self.positions = positions
        self.portfolio = portfolio
        self.events = events
        self.settings = settings

    # ---- configuration -------------------------------------------------------------------------
    async def get_config(self) -> RiskConfiguration:
        config = await self.risk.get_active()
        if config is None:  # first start: seed from environment defaults
            s = self.settings
            config = await self.risk.create(
                RiskConfiguration(
                    max_risk_per_trade=s.max_risk_per_trade,
                    max_daily_loss=s.max_daily_loss,
                    max_trades_per_day=s.max_trades_per_day,
                    max_open_positions=s.max_open_positions,
                    max_position_size=s.max_position_size,
                    max_order_value=s.max_order_value,
                    max_consecutive_losses=s.max_consecutive_losses,
                    max_strategy_drawdown=s.max_strategy_drawdown,
                )
            )
        return config

    async def update_config(self, values: dict[str, Any]) -> RiskConfiguration:
        config = await self.risk.update(await self.get_config(), values)
        await self.events.record("risk_config_updated", "Risk limits updated", **values)
        return config

    @staticmethod
    def limits_of(config: RiskConfiguration) -> RiskLimits:
        return RiskLimits(
            config.max_risk_per_trade,
            config.max_daily_loss,
            config.max_trades_per_day,
            config.max_open_positions,
            config.max_position_size,
            config.max_order_value,
            config.max_consecutive_losses,
            config.max_strategy_drawdown,
        )

    async def is_halted(self) -> bool:
        return (await self.get_config()).kill_switch_active

    async def set_kill_switch(self, active: bool, reason: str | None) -> RiskConfiguration:
        config = await self.get_config()
        return await self.risk.update(
            config,
            {
                "kill_switch_active": active,
                "kill_switch_activated_at": utcnow() if active else None,
                "kill_switch_reason": reason if active else None,
            },
        )

    # ---- evaluation ----------------------------------------------------------------------------
    async def _consecutive_losses(self, mode: TradingMode) -> int:
        streak = 0
        for trade in await self.trades.list_trades(since=ist_day_start_utc(), limit=200):
            if trade.trading_mode is not mode:
                continue
            if trade.net_pnl >= 0:
                break
            streak += 1
        return streak

    async def _strategy_drawdown(self, strategy_id: str) -> float:
        peak = running = 0.0
        for trade in await self.trades.list_trades(strategy_id=strategy_id, limit=None, ascending=True):
            running += trade.net_pnl
            peak = max(peak, running)
        return peak - running

    async def build_context(
        self, mode: TradingMode, strategy: Strategy | None, config: RiskConfiguration
    ) -> RiskContext:
        state = await self.portfolio.state(mode)
        since = ist_day_start_utc()
        today = await self.trades.aggregate(mode=mode, since=since)
        return RiskContext(
            capital=state.capital,
            available_capital=state.available,
            daily_pnl=today["net_pnl"] + state.unrealized_pnl,
            trades_today=await self.positions.count_opened_since(since, mode),
            open_positions=state.open_positions,
            consecutive_losses=await self._consecutive_losses(mode),
            kill_switch_active=config.kill_switch_active,
            strategy_capital=strategy.capital if strategy else None,
            strategy_drawdown=await self._strategy_drawdown(strategy.id) if strategy else 0.0,
        )

    async def evaluate(
        self, intent: OrderIntent, mode: TradingMode, strategy: Strategy | None, order_id: str | None = None
    ) -> RiskDecision:
        config = await self.get_config()
        decision = RiskManager(self.limits_of(config)).evaluate(
            intent, await self.build_context(mode, strategy, config)
        )
        await self.events.record(
            "risk_check_passed" if decision.approved else "risk_check_failed",
            decision.reason,
            level=EventLevel.INFO if decision.approved else EventLevel.WARNING,
            strategy_id=strategy.id if strategy else None,
            order_id=order_id,
            symbol=intent.symbol,
            quantity=intent.quantity,
            price=intent.price,
            reducing=intent.is_reducing,
        )
        return decision

    # ---- status --------------------------------------------------------------------------------
    async def status(self, mode: TradingMode) -> RiskStatus:
        config = await self.get_config()
        ctx = await self.build_context(mode, None, config)

        def usage(key: str, label: str, current: float, limit: float, unit: str) -> RiskUsage:
            return RiskUsage(
                key=key,
                label=label,
                current=round(current, 2),
                limit=limit,
                utilization=round(min(max(current / limit, 0), 1), 4) if limit else 0.0,
                breached=current >= limit,
                unit=unit,
            )

        rows = [
            usage("daily_loss", "Daily loss", max(-ctx.daily_pnl, 0), config.max_daily_loss, "INR"),
            usage("trades_today", "Trades today", ctx.trades_today, config.max_trades_per_day, "count"),
            usage("open_positions", "Open positions", ctx.open_positions, config.max_open_positions, "count"),
            usage(
                "consecutive_losses",
                "Consecutive losses",
                ctx.consecutive_losses,
                config.max_consecutive_losses,
                "count",
            ),
        ]
        reasons = [f"{row.label} limit reached" for row in rows if row.breached]
        if config.kill_switch_active:
            reasons.insert(
                0,
                "Kill switch is active"
                + (f": {config.kill_switch_reason}" if config.kill_switch_reason else ""),
            )
        return RiskStatus(
            kill_switch_active=config.kill_switch_active,
            system_state="HALTED" if config.kill_switch_active else "RUNNING",
            trading_allowed=not reasons,
            blocked_reasons=reasons,
            usage=rows,
        )
