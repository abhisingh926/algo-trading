from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from app.backtesting.engine import BacktestConfig, BacktestEngine
from app.backtesting.report import monthly_returns
from app.core.config import Settings
from app.core.database import new_uuid
from app.core.exceptions import AppError, NotFoundError, ValidationFailedError
from app.core.logging import get_logger
from app.domain.enums import BacktestStatus
from app.models.backtest import Backtest, BacktestTrade
from app.repositories.backtest_repository import BacktestRepository
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.backtest import BacktestCreate
from app.services.event_service import EventService
from app.services.market_data_service import MarketDataService
from app.strategies.base import StrategyConfigError
from app.strategies.registry import create_strategy
from app.trading.charges import ChargesConfig
from app.utils.time import utcnow

logger = get_logger(__name__)


class BacktestService:
    def __init__(
        self,
        backtests: BacktestRepository,
        strategies: StrategyRepository,
        market_data: MarketDataService,
        events: EventService,
        settings: Settings,
    ) -> None:
        self.backtests = backtests
        self.strategies = strategies
        self.market_data = market_data
        self.events = events
        self.settings = settings

    def _charges(self, request: BacktestCreate) -> ChargesConfig:
        s = self.settings
        config = ChargesConfig(
            brokerage_per_order=request.brokerage_per_order,
            brokerage_pct=request.brokerage_pct,
            stt_sell_pct=s.stt_sell_pct,
            exchange_txn_pct=s.exchange_txn_pct,
            sebi_pct=s.sebi_pct,
            stamp_duty_buy_pct=s.stamp_duty_buy_pct,
            gst_pct=s.gst_pct,
        )
        return config if request.include_statutory_charges else config.without_statutory()

    async def _resolve(self, request: BacktestCreate) -> dict[str, Any]:
        """Merge the request with the referenced strategy (request values win)."""
        base: dict[str, Any] = {}
        if request.strategy_id:
            strategy = await self.strategies.get_by_id(request.strategy_id)
            if strategy is None:
                raise NotFoundError("Strategy not found")
            base = {
                "strategy_type": strategy.strategy_type,
                "parameters": strategy.parameters,
                "symbol": strategy.symbol,
                "exchange": strategy.exchange,
                "timeframe": strategy.timeframe,
                "risk_per_trade": strategy.risk_per_trade,
                "stop_loss_pct": strategy.stop_loss_pct,
                "target_pct": strategy.target_pct,
                "allow_short": strategy.allow_short,
                "strategy_name": strategy.name,
            }
        overrides = request.model_dump(
            include={
                "strategy_type",
                "parameters",
                "symbol",
                "exchange",
                "timeframe",
                "risk_per_trade",
                "stop_loss_pct",
                "target_pct",
                "allow_short",
            },
            exclude_none=True,
        )
        merged = (
            {"exchange": "NSE", "allow_short": False, "target_pct": None, "parameters": {}} | base | overrides
        )
        for required in ("risk_per_trade", "stop_loss_pct"):
            if merged.get(required) is None:
                raise ValidationFailedError(f"{required} is required when no strategy_id is given")
        merged["symbol"] = str(merged["symbol"]).upper()
        return merged

    async def run(self, request: BacktestCreate, user_id: str | None = None) -> Backtest:
        spec = await self._resolve(request)
        try:
            logic = create_strategy(spec["strategy_type"], spec["parameters"])
        except StrategyConfigError as exc:
            raise ValidationFailedError(str(exc)) from exc
        ref = await self.market_data.resolve(spec["symbol"], spec["exchange"])
        charges = self._charges(request)
        config = BacktestConfig(
            symbol=ref.symbol,
            initial_capital=request.initial_capital,
            risk_per_trade=spec["risk_per_trade"],
            stop_loss_pct=spec["stop_loss_pct"],
            target_pct=spec["target_pct"],
            allow_short=spec["allow_short"],
            slippage_pct=request.slippage_pct,
            charges=charges,
        )
        backtest = await self.backtests.create(
            Backtest(
                user_id=user_id,
                strategy_id=request.strategy_id,
                name=request.name
                or f"{spec.get('strategy_name') or logic.display_name} · {ref.symbol} · {spec['timeframe'].value}",
                strategy_type=spec["strategy_type"],
                parameters=dict(logic.params),
                symbol=ref.symbol,
                exchange=ref.exchange,
                timeframe=spec["timeframe"],
                start_date=request.start_date,
                end_date=request.end_date,
                initial_capital=request.initial_capital,
                status=BacktestStatus.RUNNING,
                config={
                    "risk_per_trade": config.risk_per_trade,
                    "stop_loss_pct": config.stop_loss_pct,
                    "target_pct": config.target_pct,
                    "allow_short": config.allow_short,
                    "slippage_pct": config.slippage_pct,
                    "charges": charges.to_dict(),
                },
            )
        )
        try:
            candles, source = await self.market_data.load_for_backtest(
                ref, spec["timeframe"], request.start_date, request.end_date
            )
            if len(candles) < logic.lookback_bars // 4 + 2:
                raise ValidationFailedError(
                    f"Only {len(candles)} candles available for {ref.key} {spec['timeframe'].value} in the selected range"
                )
            result = await asyncio.to_thread(BacktestEngine(logic, config).run, candles)
        except AppError as exc:
            return await self._fail(backtest, exc.description)
        except Exception as exc:  # engine bugs must surface as a FAILED backtest, not a 500
            logger.exception("backtest_failed", extra={"backtest_id": backtest.id})
            return await self._fail(backtest, f"{type(exc).__name__}: {exc}")

        await self.backtests.add_trades(
            [{"id": new_uuid(), "backtest_id": backtest.id, **asdict(t)} for t in result.trades]
        )
        backtest.metrics = result.metrics | {"data_source": source}
        backtest.equity_curve = [
            {
                "timestamp": p.timestamp.isoformat(),
                "equity": p.equity,
                "drawdown": p.drawdown,
                "drawdown_pct": p.drawdown_pct,
            }
            for p in result.equity_curve
        ]
        backtest.status, backtest.completed_at = BacktestStatus.COMPLETED, utcnow()
        await self.backtests.update(backtest)
        await self.events.record(
            "backtest_completed",
            f"{backtest.name}: net P&L {result.metrics['net_pnl']:.2f} over {result.metrics['total_trades']} trades",
            strategy_id=backtest.strategy_id,
            symbol=backtest.symbol,
            backtest_id=backtest.id,
        )
        return backtest

    async def _fail(self, backtest: Backtest, error: str) -> Backtest:
        backtest.status, backtest.error_message, backtest.completed_at = (
            BacktestStatus.FAILED,
            error[:2000],
            utcnow(),
        )
        return await self.backtests.update(backtest)

    # ---- queries -------------------------------------------------------------------------------
    async def list_recent(self, limit: int = 50) -> Sequence[Backtest]:
        return await self.backtests.list_recent(limit)

    async def get(self, backtest_id: str) -> Backtest:
        backtest = await self.backtests.get_by_id(backtest_id)
        if backtest is None:
            raise NotFoundError("Backtest not found")
        return backtest

    async def trades(self, backtest_id: str) -> Sequence[BacktestTrade]:
        await self.get(backtest_id)
        return await self.backtests.list_trades(backtest_id)

    async def equity_curve(self, backtest_id: str) -> list[dict[str, Any]]:
        backtest = await self.backtests.get_with_equity_curve(backtest_id)
        if backtest is None:
            raise NotFoundError("Backtest not found")
        return backtest.equity_curve or []

    async def report(self, backtest_id: str) -> dict[str, Any]:
        trades = await self.trades(backtest_id)
        return {
            "backtest": await self.get(backtest_id),
            "trades": trades,
            "equity_curve": await self.equity_curve(backtest_id),
            "monthly_returns": monthly_returns(trades),
        }

    async def delete(self, backtest_id: str) -> None:
        await self.backtests.delete_entity(await self.get(backtest_id))
