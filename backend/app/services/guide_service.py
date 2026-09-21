"""Best-practice reviews and the getting-started checklist for new users."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.domain.enums import TradingMode
from app.models.backtest import Backtest
from app.repositories.backtest_repository import BacktestRepository
from app.repositories.event_repository import EventRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.trade_repository import TradeRepository
from app.risk.strategy_review import (
    BacktestEvidence,
    PaperRecord,
    Review,
    ReviewInput,
    Severity,
    config_matches,
    review_strategy,
)
from app.schemas.guide import (
    Onboarding,
    OnboardingStep,
    ReviewCheck,
    ReviewCounts,
    ReviewRequest,
    StrategyReview,
)
from app.services.risk_service import RiskService
from app.strategies.base import StrategyConfigError
from app.strategies.registry import create_strategy
from app.trading.portfolio_manager import PortfolioManager

_STEPS: tuple[tuple[str, str, str, str, bool], ...] = (
    (
        "paper_mode",
        "Stay in paper mode while learning",
        "Paper mode sends orders to a simulated broker, so no real money is ever at risk. It is the default.",
        "/settings",
        False,
    ),
    (
        "review_risk",
        "Review your risk limits",
        "Set the daily loss, maximum open positions and other limits that every order must pass.",
        "/risk",
        False,
    ),
    (
        "create_strategy",
        "Create your first strategy",
        "Pick a strategy type such as EMA Crossover, choose a symbol and timeframe, and set risk per trade and a stop loss.",
        "/strategies/new",
        False,
    ),
    (
        "run_backtest",
        "Backtest it",
        "Replay the strategy on historical candles with brokerage, taxes and slippage included.",
        "/backtesting",
        False,
    ),
    (
        "start_strategy",
        "Start it in paper mode",
        "The engine checks each newly closed candle, sizes the order from your risk, and sends it to the paper broker.",
        "/strategies",
        False,
    ),
    (
        "first_order",
        "Watch your first simulated order",
        "Orders appear with their full event history: created, risk checked, submitted, filled.",
        "/orders",
        False,
    ),
    (
        "first_trade",
        "See a closed trade and its P&L",
        "A trade is a completed round trip. Profit and loss are shown after brokerage, taxes and fees.",
        "/trades",
        False,
    ),
    (
        "test_kill_switch",
        "Practise the kill switch",
        "Trigger it once in paper mode so you know how to halt trading fast, then resume.",
        "/risk",
        True,
    ),
)


class GuideService:
    def __init__(
        self,
        strategies: StrategyRepository,
        backtests: BacktestRepository,
        trades: TradeRepository,
        orders: OrderRepository,
        events: EventRepository,
        risk: RiskService,
        portfolio: PortfolioManager,
        settings: Settings,
    ) -> None:
        self.strategies = strategies
        self.backtests = backtests
        self.trades = trades
        self.orders = orders
        self.events = events
        self.risk = risk
        self.portfolio = portfolio
        self.settings = settings

    # ---- strategy review -----------------------------------------------------------------------
    async def _review_input(self, request: ReviewRequest) -> ReviewInput:
        config_error = None
        try:
            parameters = dict(create_strategy(request.strategy_type, request.parameters).params)
        except StrategyConfigError as exc:
            parameters, config_error = dict(request.parameters), str(exc)
        risk_config = await self.risk.get_config()
        state = await self.portfolio.state(TradingMode.PAPER)
        return ReviewInput(
            strategy_type=request.strategy_type,
            timeframe=request.timeframe,
            capital=request.capital,
            risk_per_trade=request.risk_per_trade,
            stop_loss_pct=request.stop_loss_pct,
            target_pct=request.target_pct,
            allow_short=request.allow_short,
            trading_mode=request.trading_mode,
            parameters=parameters,
            account_capital=state.capital,
            platform_max_risk_per_trade=risk_config.max_risk_per_trade,
            config_error=config_error,
        )

    @staticmethod
    def _evidence(backtest: Backtest, inp: ReviewInput, request: ReviewRequest) -> BacktestEvidence | None:
        metrics = backtest.metrics or {}
        if not metrics:
            return None
        stale = not config_matches(
            backtest.config or {},
            backtest.parameters or {},
            inp,
            symbol_matches=backtest.symbol == request.symbol and backtest.exchange == request.exchange,
            timeframe_matches=backtest.timeframe == request.timeframe,
        )
        period_days = max((backtest.end_date - backtest.start_date).days, 0) + 1
        return BacktestEvidence(
            trades=int(metrics.get("total_trades", 0)),
            net_pnl=float(metrics.get("net_pnl", 0)),
            profit_factor=metrics.get("profit_factor"),
            max_drawdown_pct=float(metrics.get("max_drawdown_pct", 0)),
            gross_profit=float(metrics.get("gross_profit", 0)),
            total_charges=float(metrics.get("total_charges", 0)),
            data_source=str(metrics.get("data_source", "unknown")),
            period_days=period_days,
            sharpe_ratio=metrics.get("sharpe_ratio"),
            stale=stale,
        )

    async def review(self, request: ReviewRequest) -> StrategyReview:
        inp = await self._review_input(request)
        evidence, paper, backtest_id = None, None, None
        if request.strategy_id:
            backtest = await self.backtests.latest_completed_for_strategy(request.strategy_id)
            if backtest is not None:
                evidence, backtest_id = self._evidence(backtest, inp, request), backtest.id
            totals = await self.trades.aggregate(mode=TradingMode.PAPER, strategy_id=request.strategy_id)
            paper = PaperRecord(int(totals["trades"]), float(totals["net_pnl"]))
        return self._to_schema(review_strategy(inp, evidence, paper), evidence is not None, backtest_id)

    @staticmethod
    def _to_schema(review: Review, has_backtest: bool, backtest_id: str | None) -> StrategyReview:
        return StrategyReview(
            verdict=review.verdict.value,
            summary=review.summary,
            counts=ReviewCounts(
                good=review.count(Severity.GOOD),
                info=review.count(Severity.INFO),
                warn=review.count(Severity.WARN),
                risk=review.count(Severity.RISK),
            ),
            checks=[
                ReviewCheck(
                    key=c.key,
                    category=c.category,
                    severity=c.severity.value,
                    title=c.title,
                    detail=c.detail,
                    suggestion=c.suggestion,
                )
                for c in review.checks
            ],
            has_backtest=has_backtest,
            backtest_id=backtest_id,
        )

    async def review_saved(self, strategy_id: str) -> StrategyReview:
        strategy = await self.strategies.get_by_id(strategy_id)
        if strategy is None:
            raise NotFoundError("Strategy not found")
        return await self.review(
            ReviewRequest(
                strategy_id=strategy.id,
                strategy_type=strategy.strategy_type,
                symbol=strategy.symbol,
                exchange=strategy.exchange,
                timeframe=strategy.timeframe,
                capital=strategy.capital,
                risk_per_trade=strategy.risk_per_trade,
                stop_loss_pct=strategy.stop_loss_pct,
                target_pct=strategy.target_pct,
                allow_short=strategy.allow_short,
                trading_mode=strategy.trading_mode,
                parameters=strategy.parameters,
            )
        )

    # ---- getting started -----------------------------------------------------------------------
    async def onboarding(self) -> Onboarding:
        done = {
            "paper_mode": self.settings.trading_mode is TradingMode.PAPER,
            "review_risk": await self.events.count_by_type("risk_config_updated") > 0,
            "create_strategy": await self.strategies.count() > 0,
            "run_backtest": await self.backtests.count_completed() > 0,
            "start_strategy": await self.events.count_by_type("strategy_started") > 0,
            "first_order": await self.orders.count() > 0,
            "first_trade": await self.trades.count() > 0,
            "test_kill_switch": await self.events.count_by_type("kill_switch_activated") > 0,
        }
        steps = [
            OnboardingStep(
                key=key, title=title, description=text, href=href, done=done[key], optional=optional
            )
            for key, title, text, href, optional in _STEPS
        ]
        required = [s for s in steps if not s.optional]
        completed = sum(1 for s in required if s.done)
        next_step = next((s.key for s in required if not s.done), None)
        return Onboarding(
            steps=steps,
            completed=completed,
            total=len(required),
            percent=round(completed / len(required) * 100),
            next_step=next_step,
            all_done=next_step is None,
        )
