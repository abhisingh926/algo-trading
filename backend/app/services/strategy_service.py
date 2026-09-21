from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, TradingHaltedError, ValidationFailedError
from app.domain.enums import PositionStatus, StrategyStatus, StrategyType, Timeframe, TradingMode
from app.models.strategy import Strategy
from app.repositories.position_repository import PositionRepository
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.strategy import StrategyRead, StrategyStats
from app.services.broker_service import BrokerService
from app.services.event_service import EventService
from app.services.market_data_service import MarketDataService
from app.services.risk_service import RiskService
from app.strategies.base import StrategyConfigError
from app.strategies.registry import create_strategy, describe_strategies
from app.utils.time import ist_day_start_utc


class StrategyService:
    def __init__(
        self,
        strategies: StrategyRepository,
        trades: TradeRepository,
        positions: PositionRepository,
        market_data: MarketDataService,
        brokers: BrokerService,
        risk: RiskService,
        events: EventService,
        settings: Settings,
    ) -> None:
        self.strategies = strategies
        self.trades = trades
        self.positions = positions
        self.market_data = market_data
        self.brokers = brokers
        self.risk = risk
        self.events = events
        self.settings = settings

    @staticmethod
    def types() -> list[dict[str, Any]]:
        return describe_strategies()

    # ---- validation ----------------------------------------------------------------------------
    @staticmethod
    def _validated_parameters(
        strategy_type: StrategyType, parameters: dict[str, Any], timeframe: Timeframe
    ) -> dict[str, Any]:
        try:
            params = dict(create_strategy(strategy_type, parameters).params)
        except StrategyConfigError as exc:
            raise ValidationFailedError(str(exc)) from exc
        if strategy_type is StrategyType.VWAP and timeframe is Timeframe.D1 and not params.get("window"):
            raise ValidationFailedError(
                "Session VWAP needs an intraday timeframe; set a rolling 'window' for daily bars"
            )
        return params

    async def _validate_references(self, values: dict[str, Any]) -> None:
        """Checks symbol + broker account and pins the relationship so it never lazy-loads."""
        if "symbol" in values or "exchange" in values:
            await self.market_data.get_instrument(values["symbol"], values.get("exchange", "NSE"))
        if "broker_account_id" in values:
            account_id = values["broker_account_id"]
            values["broker_account"] = await self.brokers.get(account_id) if account_id else None

    # ---- CRUD ----------------------------------------------------------------------------------
    async def get(self, strategy_id: str) -> Strategy:
        strategy = await self.strategies.get_by_id(strategy_id)
        if strategy is None:
            raise NotFoundError("Strategy not found")
        return strategy

    async def create(self, user_id: str | None, values: dict[str, Any]) -> Strategy:
        if await self.strategies.get_by_name(values["name"]) is not None:
            raise ConflictError(f"A strategy named '{values['name']}' already exists")
        await self._validate_references(values)
        parameters = self._validated_parameters(
            values["strategy_type"], values.pop("parameters", {}), values["timeframe"]
        )
        values.setdefault("broker_account", None)
        strategy = await self.strategies.create(Strategy(user_id=user_id, parameter_rows=[], **values))
        await self.strategies.replace_parameters(strategy, parameters)
        return strategy

    async def update(self, strategy_id: str, values: dict[str, Any]) -> Strategy:
        strategy = await self.get(strategy_id)
        if strategy.status is StrategyStatus.RUNNING:
            raise ConflictError("Stop the strategy before editing it")
        if (
            "name" in values
            and values["name"] != strategy.name
            and await self.strategies.get_by_name(values["name"])
        ):
            raise ConflictError(f"A strategy named '{values['name']}' already exists")
        if "symbol" in values or "exchange" in values:
            values.setdefault("symbol", strategy.symbol)
            values.setdefault("exchange", strategy.exchange)
        await self._validate_references(values)

        parameters = values.pop("parameters", None)
        strategy_type = values.get("strategy_type", strategy.strategy_type)
        timeframe = values.get("timeframe", strategy.timeframe)
        if parameters is None and strategy_type is not strategy.strategy_type:
            parameters = {}  # type changed: fall back to the new type's defaults
        checked = self._validated_parameters(
            strategy_type, parameters if parameters is not None else strategy.parameters, timeframe
        )
        await self.strategies.update(strategy, values)
        await self.strategies.replace_parameters(strategy, checked)
        return strategy

    async def delete(self, strategy_id: str) -> None:
        strategy = await self.get(strategy_id)
        if strategy.status is StrategyStatus.RUNNING:
            raise ConflictError("Stop the strategy before deleting it")
        await self.strategies.delete_entity(strategy)

    # ---- lifecycle -----------------------------------------------------------------------------
    async def start(self, strategy_id: str) -> Strategy:
        strategy = await self.get(strategy_id)
        if await self.risk.is_halted():
            raise TradingHaltedError("Kill switch is active. Resume trading before starting a strategy.")
        mode, global_mode = strategy.trading_mode, self.settings.trading_mode
        if mode is not TradingMode.PAPER and mode is not global_mode:
            raise ConflictError(
                f"Strategy mode {mode.value} cannot run while TRADING_MODE={global_mode.value}"
            )
        if mode is not TradingMode.PAPER:
            account = await self.brokers.resolve_account(mode, strategy.broker_account_id)
            # Fails loudly now rather than on the first order.
            self.brokers.registry.resolve_for_order(mode, self.brokers.ref(account) if account else None)
        create_strategy(strategy.strategy_type, strategy.parameters)  # parameters still valid
        await self.strategies.update(
            strategy, {"status": StrategyStatus.RUNNING, "last_error": None, "last_candle_at": None}
        )
        await self.events.record(
            "strategy_started",
            f"{strategy.name} started in {mode.value} mode",
            strategy_id=strategy.id,
            symbol=strategy.symbol,
            trading_mode=mode.value,
            timeframe=strategy.timeframe.value,
            parameters=strategy.parameters,
        )
        return strategy

    async def stop(self, strategy_id: str, reason: str = "Stopped by user") -> Strategy:
        strategy = await self.get(strategy_id)
        await self.strategies.update(strategy, {"status": StrategyStatus.STOPPED})
        await self.events.record(
            "strategy_stopped", f"{strategy.name}: {reason}", strategy_id=strategy.id, symbol=strategy.symbol
        )
        return strategy

    # ---- read models ---------------------------------------------------------------------------
    async def to_read_many(self, strategies: list[Strategy]) -> list[StrategyRead]:
        total = await self.trades.aggregate_by_strategy()
        today = await self.trades.aggregate_by_strategy(since=ist_day_start_utc())
        open_qty: dict[str, int] = {}
        unrealized: dict[str, float] = {}
        for p in await self.positions.list_positions(PositionStatus.OPEN):
            if p.strategy_id:
                open_qty[p.strategy_id] = open_qty.get(p.strategy_id, 0) + p.quantity * p.side.sign
                unrealized[p.strategy_id] = unrealized.get(p.strategy_id, 0.0) + p.unrealized_pnl
        out = []
        for s in strategies:
            agg, day = total.get(s.id, {}), today.get(s.id, {})
            read = StrategyRead.model_validate(s)
            read.stats = StrategyStats(
                todays_pnl=round(day.get("net_pnl", 0.0) + unrealized.get(s.id, 0.0), 2),
                total_pnl=round(agg.get("net_pnl", 0.0) + unrealized.get(s.id, 0.0), 2),
                trades=int(agg.get("trades", 0)),
                win_rate=round(agg["wins"] / agg["trades"] * 100, 2) if agg.get("trades") else 0.0,
                open_position_qty=open_qty.get(s.id, 0),
            )
            out.append(read)
        return out

    async def list_read(self) -> list[StrategyRead]:
        return await self.to_read_many(list(await self.strategies.get_all()))

    async def to_read(self, strategy: Strategy) -> StrategyRead:
        return (await self.to_read_many([strategy]))[0]
