"""Request/worker scoped object graph: wires repositories -> managers -> services for ONE session."""

from __future__ import annotations

from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from app.container import AppContainer
from app.repositories.backtest_repository import BacktestRepository
from app.repositories.broker_repository import BrokerRepository
from app.repositories.event_repository import EventRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.pnl_repository import PnlRepository
from app.repositories.position_repository import PositionRepository
from app.repositories.risk_repository import RiskRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.backtest_service import BacktestService
from app.services.broker_service import BrokerService
from app.services.event_service import EventService
from app.services.guide_service import GuideService
from app.services.market_data_service import MarketDataService
from app.services.order_service import OrderService
from app.services.pnl_service import PnlService
from app.services.position_service import PositionService
from app.services.risk_service import RiskService
from app.services.signal_service import SignalService
from app.services.strategy_service import StrategyService
from app.services.system_service import SystemService
from app.services.trade_service import TradeService
from app.services.trading_service import TradingService
from app.trading.charges import ChargesCalculator, ChargesConfig
from app.trading.order_manager import OrderManager
from app.trading.portfolio_manager import PortfolioManager
from app.trading.position_manager import PositionManager


class Services:
    def __init__(self, session: AsyncSession, container: AppContainer) -> None:
        self.session = session
        self.container = container
        self.settings = container.settings

    # ---- repositories --------------------------------------------------------------------------
    @cached_property
    def user_repo(self) -> UserRepository:
        return UserRepository(self.session)  # noqa: E704

    @cached_property
    def broker_repo(self) -> BrokerRepository:
        return BrokerRepository(self.session)  # noqa: E704

    @cached_property
    def instrument_repo(self) -> InstrumentRepository:
        return InstrumentRepository(self.session)  # noqa: E704

    @cached_property
    def strategy_repo(self) -> StrategyRepository:
        return StrategyRepository(self.session)  # noqa: E704

    @cached_property
    def signal_repo(self) -> SignalRepository:
        return SignalRepository(self.session)  # noqa: E704

    @cached_property
    def order_repo(self) -> OrderRepository:
        return OrderRepository(self.session)  # noqa: E704

    @cached_property
    def position_repo(self) -> PositionRepository:
        return PositionRepository(self.session)  # noqa: E704

    @cached_property
    def trade_repo(self) -> TradeRepository:
        return TradeRepository(self.session)  # noqa: E704

    @cached_property
    def backtest_repo(self) -> BacktestRepository:
        return BacktestRepository(self.session)  # noqa: E704

    @cached_property
    def risk_repo(self) -> RiskRepository:
        return RiskRepository(self.session)  # noqa: E704

    @cached_property
    def pnl_repo(self) -> PnlRepository:
        return PnlRepository(self.session)  # noqa: E704

    @cached_property
    def candle_repo(self) -> MarketDataRepository:
        return MarketDataRepository(self.session)  # noqa: E704

    @cached_property
    def event_repo(self) -> EventRepository:
        return EventRepository(self.session)  # noqa: E704

    # ---- engine pieces -------------------------------------------------------------------------
    @cached_property
    def charges(self) -> ChargesCalculator:
        s = self.settings
        return ChargesCalculator(
            ChargesConfig(
                s.brokerage_per_order,
                s.brokerage_pct,
                s.stt_sell_pct,
                s.exchange_txn_pct,
                s.sebi_pct,
                s.stamp_duty_buy_pct,
                s.gst_pct,
            )
        )

    @cached_property
    def portfolio(self) -> PortfolioManager:
        return PortfolioManager(
            self.position_repo, self.trade_repo, self.pnl_repo, self.settings.paper_initial_capital
        )

    @cached_property
    def position_manager(self) -> PositionManager:
        return PositionManager(
            self.position_repo, self.trade_repo, self.events, on_trade_closed=self.pnl.record_trade
        )

    @cached_property
    def order_manager(self) -> OrderManager:
        s = self.settings
        return OrderManager(
            self.order_repo,
            self.position_manager,
            self.events,
            self.charges,
            max_retries=s.order_submit_max_retries,
            retry_backoff_seconds=s.order_retry_backoff_seconds,
            fill_lock=self.container.fill_lock,
        )

    # ---- services ------------------------------------------------------------------------------
    @cached_property
    def events(self) -> EventService:
        return EventService(self.event_repo)

    @cached_property
    def auth(self) -> AuthService:
        return AuthService(self.user_repo, self.settings)

    @cached_property
    def market_data(self) -> MarketDataService:
        return MarketDataService(
            self.container.market_data, self.container.quote_cache, self.candle_repo, self.instrument_repo
        )

    @cached_property
    def brokers(self) -> BrokerService:
        return BrokerService(self.broker_repo, self.container.brokers, self.events, self.settings)

    @cached_property
    def pnl(self) -> PnlService:
        return PnlService(
            self.pnl_repo, self.trade_repo, self.strategy_repo, self.portfolio, self.settings.trading_mode
        )

    @cached_property
    def risk(self) -> RiskService:
        return RiskService(
            self.risk_repo, self.trade_repo, self.position_repo, self.portfolio, self.events, self.settings
        )

    @cached_property
    def orders(self) -> OrderService:
        return OrderService(
            self.order_repo,
            self.position_repo,
            self.order_manager,
            self.risk,
            self.market_data,
            self.brokers,
            self.container.brokers,
            self.events,
            self.settings,
        )

    @cached_property
    def positions(self) -> PositionService:
        return PositionService(self.position_repo, self.order_repo, self.orders, self.market_data)

    @cached_property
    def trades(self) -> TradeService:
        return TradeService(self.trade_repo)

    @cached_property
    def signals(self) -> SignalService:
        return SignalService(self.signal_repo, self.events)

    @cached_property
    def strategies(self) -> StrategyService:
        return StrategyService(
            self.strategy_repo,
            self.trade_repo,
            self.position_repo,
            self.market_data,
            self.brokers,
            self.risk,
            self.events,
            self.settings,
        )

    @cached_property
    def trading(self) -> TradingService:
        return TradingService(
            self.strategy_repo,
            self.position_repo,
            self.orders,
            self.positions,
            self.signals,
            self.risk,
            self.market_data,
            self.portfolio,
            self.events,
        )

    @cached_property
    def backtests(self) -> BacktestService:
        return BacktestService(
            self.backtest_repo, self.strategy_repo, self.market_data, self.events, self.settings
        )

    @cached_property
    def guide(self) -> GuideService:
        return GuideService(
            self.strategy_repo,
            self.backtest_repo,
            self.trade_repo,
            self.order_repo,
            self.event_repo,
            self.risk,
            self.portfolio,
            self.settings,
        )

    @cached_property
    def system(self) -> SystemService:
        return SystemService(self.container, self.risk)
