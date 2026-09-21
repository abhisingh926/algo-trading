"""TradingEngine: the periodic work cycles. Broker-agnostic - it only talks to services.

Each cycle runs in its own database session/transaction so one failure never poisons another.
Workers (app/workers) are thin schedulers around these methods.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from app.container import AppContainer
from app.core.logging import get_logger
from app.domain.enums import BrokerType, StrategyStatus
from app.domain.types import BrokerOrder, InstrumentRef
from app.services.factory import Services
from app.utils.time import utcnow

logger = get_logger(__name__)


class TradingEngine:
    def __init__(self, container: AppContainer) -> None:
        self.container = container
        self._last_snapshot: datetime | None = None

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncIterator[Services]:
        async with self.container.db.session_factory() as session:
            try:
                yield Services(session, self.container)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # ---- startup -------------------------------------------------------------------------------
    async def bootstrap(self) -> None:
        """Idempotent seed data + re-register working paper orders (PaperBroker state is in-memory)."""
        async with self.unit_of_work() as services:
            await services.brokers.ensure_paper_account()
            await services.risk.get_config()
            await services.market_data.seed_instruments()
            restored = 0
            for order in await services.order_repo.list_active():
                if order.broker_type is BrokerType.PAPER and order.broker_order_id:
                    instrument = await services.instrument_repo.get_by_symbol(order.symbol, order.exchange)
                    request = services.order_manager.to_request(
                        order, instrument.exchange_token if instrument else None
                    )
                    self.container.brokers.paper.restore_order(
                        request,
                        BrokerOrder(
                            order.broker_order_id,
                            order.status,
                            order.quantity,
                            order.filled_quantity,
                            order.average_fill_price,
                        ),
                    )
                    restored += 1
            if restored:
                logger.info("paper_orders_restored", extra={"count": restored})

    # ---- cycles --------------------------------------------------------------------------------
    async def run_market_data_cycle(self) -> None:
        """Refresh quotes for everything we care about and mark positions to market."""
        async with self.unit_of_work() as services:
            watch: dict[str, InstrumentRef] = {}
            for strategy in await services.strategy_repo.list_by_status(StrategyStatus.RUNNING):
                instrument = await services.instrument_repo.get_by_symbol(strategy.symbol, strategy.exchange)
                if instrument is not None:
                    watch[f"{instrument.exchange}:{instrument.symbol}"] = InstrumentRef(
                        instrument.symbol, instrument.exchange, instrument.exchange_token
                    )
            if watch:
                await services.market_data.refresh_quotes(list(watch.values()))
            _, unrealized = await services.positions.mark_to_market()
            await services.pnl.mark_unrealized(unrealized)

    async def run_order_cycle(self) -> None:
        """Match paper orders, sync working orders, fire protective exits, snapshot equity."""
        await self.container.brokers.paper.match_open_orders()
        async with self.unit_of_work() as services:
            await services.orders.sync_active_orders()
        async with self.unit_of_work() as services:
            await services.trading.check_protective_exits()
        now = utcnow()
        interval = timedelta(seconds=self.container.settings.portfolio_snapshot_seconds)
        if self._last_snapshot is None or now - self._last_snapshot >= interval:
            async with self.unit_of_work() as services:
                await services.portfolio.snapshot(self.container.settings.trading_mode)
            self._last_snapshot = now

    async def run_strategy_cycle(self) -> int:
        """Evaluate every RUNNING strategy. Returns the number of signals produced."""
        async with self.unit_of_work() as services:
            if await services.risk.is_halted():
                return 0
            strategy_ids = [s.id for s in await services.strategy_repo.list_by_status(StrategyStatus.RUNNING)]

        signals = 0
        for strategy_id in strategy_ids:
            try:
                async with self.unit_of_work() as services:
                    strategy = await services.strategy_repo.get_by_id(strategy_id)
                    if (
                        strategy is not None
                        and strategy.status is StrategyStatus.RUNNING
                        and await services.trading.evaluate_strategy(strategy)
                    ):
                        signals += 1
            except Exception as exc:
                logger.exception("strategy_evaluation_failed", extra={"strategy_id": strategy_id})
                async with self.unit_of_work() as services:
                    strategy = await services.strategy_repo.get_by_id(strategy_id)
                    if strategy is not None:
                        await services.trading.mark_strategy_error(strategy, f"{type(exc).__name__}: {exc}")
        return signals
