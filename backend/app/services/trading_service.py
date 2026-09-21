"""Signal -> risk -> order pipeline for strategies, protective exits and the kill switch."""

from __future__ import annotations

from datetime import timedelta

from app.core.exceptions import AppError
from app.domain.enums import (
    EventLevel,
    ExitReason,
    OrderSide,
    OrderSource,
    OrderStatus,
    PositionSide,
    PositionStatus,
    SignalStatus,
    SignalType,
    StrategyStatus,
)
from app.domain.types import SignalResult
from app.models.order import Order
from app.models.signal import Signal
from app.models.strategy import Strategy
from app.repositories.position_repository import PositionRepository
from app.repositories.strategy_repository import StrategyRepository
from app.risk.position_sizer import PositionSizer
from app.schemas.risk import KillSwitchResult
from app.services.event_service import EventService
from app.services.market_data_service import MarketDataService
from app.services.order_service import OrderService, PlaceOrderCommand
from app.services.position_service import PositionService
from app.services.risk_service import RiskService
from app.services.signal_service import SignalService
from app.strategies.registry import create_strategy
from app.trading.decision import Action, decide_actions, protective_levels
from app.trading.portfolio_manager import PortfolioManager
from app.utils.time import floor_time, utcnow

_MIN_HISTORY = timedelta(days=4)  # spans a weekend for session-based feeds


class TradingService:
    def __init__(
        self,
        strategies: StrategyRepository,
        positions: PositionRepository,
        orders: OrderService,
        position_service: PositionService,
        signals: SignalService,
        risk: RiskService,
        market_data: MarketDataService,
        portfolio: PortfolioManager,
        events: EventService,
    ) -> None:
        self.strategies = strategies
        self.positions = positions
        self.orders = orders
        self.position_service = position_service
        self.signals = signals
        self.risk = risk
        self.market_data = market_data
        self.portfolio = portfolio
        self.events = events

    # ---- strategy evaluation -------------------------------------------------------------------
    async def evaluate_strategy(self, strategy: Strategy) -> Signal | None:
        """Evaluate one RUNNING strategy on its latest CLOSED candle. Idempotent per candle."""
        now = utcnow()
        step = timedelta(minutes=strategy.timeframe.minutes)
        latest_closed_start = floor_time(now, strategy.timeframe.minutes) - step
        if strategy.last_candle_at is not None and strategy.last_candle_at >= latest_closed_start:
            return None

        logic = create_strategy(strategy.strategy_type, strategy.parameters)
        ref = await self.market_data.resolve(strategy.symbol, strategy.exchange)
        history = max(step * logic.lookback_bars * 3, _MIN_HISTORY)
        candles = [
            c
            for c in await self.market_data.get_candles(ref, strategy.timeframe, now - history, now)
            if c.timestamp + step <= now
        ]
        strategy.last_evaluated_at = now
        if not candles or (
            strategy.last_candle_at is not None and candles[-1].timestamp <= strategy.last_candle_at
        ):
            await self.strategies.update(strategy)
            return None

        result = logic.generate_signal(candles[-logic.lookback_bars :])
        strategy.last_candle_at = candles[-1].timestamp
        if result.type is SignalType.HOLD:
            await self.strategies.update(strategy)
            return None

        strategy.last_signal_at = now
        await self.strategies.update(strategy)
        signal = await self.signals.record(strategy, result, candles[-1].timestamp)
        await self.process_signal(strategy, signal, result)
        return signal

    async def process_signal(self, strategy: Strategy, signal: Signal, result: SignalResult) -> list[Order]:
        position = await self.positions.get_open(
            strategy.symbol, strategy.exchange, strategy.id, strategy.trading_mode
        )
        actions = decide_actions(result.type, position.side if position else None, strategy.allow_short)
        if not actions:
            await self.signals.resolve(signal, SignalStatus.IGNORED, "No action for the current position")
            return []

        placed: list[Order] = []
        try:
            for action in actions:
                if action is Action.EXIT:
                    assert position is not None
                    order = await self.position_service.close_position(
                        position, ExitReason.SIGNAL, OrderSource.STRATEGY
                    )
                    placed.append(order)
                    if order.status is not OrderStatus.FILLED:
                        break  # never reverse before the exit is confirmed filled
                else:
                    entry = await self._enter(strategy, action, result.price)
                    if entry is not None:
                        placed.append(entry)
        except AppError as exc:
            await self.signals.resolve(
                signal,
                SignalStatus.REJECTED,
                exc.description,
                placed[-1].id if placed else (exc.data or {}).get("order_id"),
            )
            return placed

        if placed:
            await self.signals.resolve(signal, SignalStatus.EXECUTED, order_id=placed[-1].id)
        else:
            await self.signals.resolve(signal, SignalStatus.IGNORED, "Position size computed as zero")
        return placed

    async def _enter(self, strategy: Strategy, action: Action, signal_price: float) -> Order | None:
        side = PositionSide.LONG if action is Action.ENTER_LONG else PositionSide.SHORT
        ref = await self.market_data.resolve(strategy.symbol, strategy.exchange)
        instrument = await self.market_data.get_instrument(strategy.symbol, strategy.exchange)
        price = await self.market_data.get_ltp(ref) or signal_price
        stop, target = protective_levels(side, price, strategy.stop_loss_pct, strategy.target_pct)

        config = await self.risk.get_config()
        state = await self.portfolio.state(strategy.trading_mode)
        sizing = PositionSizer(config.max_position_size, config.max_order_value).size(
            strategy.capital,
            min(strategy.risk_per_trade, config.max_risk_per_trade),
            price,
            stop,
            available_capital=state.available,
            lot_size=instrument.lot_size,
        )
        if sizing.quantity <= 0:
            return None
        return await self.orders.place_order(
            PlaceOrderCommand(
                symbol=strategy.symbol,
                exchange=strategy.exchange,
                side=OrderSide.BUY if side is PositionSide.LONG else OrderSide.SELL,
                quantity=sizing.quantity,
                stop_loss=stop,
                target=target,
                trading_mode=strategy.trading_mode,
                source=OrderSource.STRATEGY,
                strategy=strategy,
            )
        )

    async def mark_strategy_error(self, strategy: Strategy, error: str) -> None:
        await self.strategies.update(strategy, {"status": StrategyStatus.ERROR, "last_error": error[:1000]})
        await self.events.record(
            "strategy_error", f"{strategy.name}: {error}", level=EventLevel.ERROR, strategy_id=strategy.id
        )

    # ---- protective exits ----------------------------------------------------------------------
    async def check_protective_exits(self) -> int:
        """Exit positions whose stop loss / target was crossed by the latest price."""
        exits = 0
        for position in await self.positions.list_positions(PositionStatus.OPEN):
            reason = self.position_service.protective_exit_reason(position)
            if reason is None:
                continue
            try:
                await self.position_service.close_position(position, reason, OrderSource.RISK_EXIT)
                exits += 1
            except AppError as exc:
                if exc.status_code != 409:  # 409 = exit already working
                    await self.events.record(
                        "protective_exit_failed",
                        exc.description,
                        level=EventLevel.ERROR,
                        strategy_id=position.strategy_id,
                        symbol=position.symbol,
                    )
        return exits

    # ---- kill switch ---------------------------------------------------------------------------
    async def set_kill_switch(self, activate: bool, reason: str | None) -> KillSwitchResult:
        if not activate:
            await self.risk.set_kill_switch(False, None)
            await self.events.record(
                "kill_switch_deactivated",
                "Trading resumed. Strategies stay stopped until restarted.",
                level=EventLevel.WARNING,
            )
            return KillSwitchResult(
                kill_switch_active=False,
                message="Trading resumed. Strategies remain stopped until you start them.",
            )

        config = await self.risk.set_kill_switch(True, reason or "Manual activation")
        await self.strategies.commit()  # the halt must survive any failure below
        stopped = await self.strategies.stop_all()
        cancelled = await self.orders.cancel_all_active("Kill switch activated")
        closed = 0
        if config.close_positions_on_kill_switch:
            for position in await self.positions.list_positions(PositionStatus.OPEN):
                try:
                    await self.position_service.close_position(
                        position, ExitReason.KILL_SWITCH, OrderSource.KILL_SWITCH
                    )
                    closed += 1
                except AppError as exc:
                    await self.events.record(
                        "kill_switch_close_failed",
                        exc.description,
                        level=EventLevel.ERROR,
                        symbol=position.symbol,
                    )
        await self.events.record(
            "kill_switch_activated",
            reason or "Manual activation",
            level=EventLevel.ERROR,
            strategies_stopped=stopped,
            orders_cancelled=cancelled,
            positions_closed=closed,
        )
        suffix = (
            f", {closed} positions closed"
            if config.close_positions_on_kill_switch
            else "; open positions were left untouched"
        )
        return KillSwitchResult(
            kill_switch_active=True,
            strategies_stopped=stopped,
            orders_cancelled=cancelled,
            positions_closed=closed,
            message=f"System HALTED: {stopped} strategies stopped, {cancelled} orders cancelled{suffix}",
        )
