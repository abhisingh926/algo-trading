"""The safety contract: PAPER can never reach a real broker; LIVE needs every guard."""

import httpx
import pytest

from app.brokers.dhan.broker import DhanBroker
from app.brokers.dhan.client import DhanClient
from app.brokers.paper.broker import PaperBroker
from app.brokers.registry import AccountRef, BrokerRegistry
from app.core.config import LIVE_CONFIRMATION_PHRASE, Settings
from app.core.exceptions import (
    BrokerNotConfiguredError,
    LiveTradingDisabledError,
    OrderRejectedError,
    TradingHaltedError,
)
from app.domain.enums import (
    BrokerEnvironment,
    BrokerType,
    OrderSide,
    OrderType,
    ProductType,
    StrategyStatus,
    TradingMode,
)
from app.domain.types import InstrumentRef, OrderRequest
from app.schemas.strategy import StrategyCreate
from app.services.factory import Services
from app.services.order_service import PlaceOrderCommand
from tests.conftest import build_container, make_settings

DHAN_CREDS = {"dhan_client_id": "1000000001", "dhan_access_token": "fake-token-for-tests"}
LIVE_ENV = {
    "trading_mode": "LIVE",
    "enable_live_trading": True,
    "live_trading_confirmation": LIVE_CONFIRMATION_PHRASE,
}
LIVE_ACCOUNT = AccountRef("acc-live", BrokerType.DHAN, BrokerEnvironment.LIVE, live_armed=True)
SANDBOX_ACCOUNT = AccountRef("acc-sbx", BrokerType.DHAN, BrokerEnvironment.SANDBOX)


class ExplodingTransport(httpx.AsyncBaseTransport):
    """Fails the test if ANY broker HTTP request is attempted."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        raise AssertionError(f"Real broker API was called: {request.method} {request.url}")


def test_defaults_are_safe(monkeypatch):
    for var in ("TRADING_MODE", "ENABLE_LIVE_TRADING", "LIVE_TRADING_CONFIRMATION"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert settings.trading_mode is TradingMode.PAPER
    assert settings.enable_live_trading is False and settings.live_trading_enabled is False


@pytest.mark.parametrize(
    "env",
    [
        {"trading_mode": "LIVE"},
        {"enable_live_trading": True},
        {"trading_mode": "LIVE", "enable_live_trading": True},
        {"trading_mode": "LIVE", "enable_live_trading": True, "live_trading_confirmation": "yes"},
        {
            "trading_mode": "PAPER",
            "enable_live_trading": True,
            "live_trading_confirmation": LIVE_CONFIRMATION_PHRASE,
        },
    ],
)
def test_no_single_or_partial_setting_enables_live(env):
    assert make_settings(**env).live_trading_enabled is False


def test_all_three_env_guards_enable_the_env_level():
    assert make_settings(**LIVE_ENV).live_trading_enabled is True


class TestRegistryRouting:
    def test_paper_mode_always_returns_paper_broker_even_with_credentials(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS), market_data)
        for account in (None, LIVE_ACCOUNT, SANDBOX_ACCOUNT):
            assert isinstance(registry.resolve_for_order(TradingMode.PAPER, account), PaperBroker)

    def test_paper_order_is_paper_even_when_global_mode_is_live(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS, **LIVE_ENV), market_data)
        assert isinstance(registry.resolve_for_order(TradingMode.PAPER, LIVE_ACCOUNT), PaperBroker)

    def test_live_order_rejected_in_paper_mode(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS), market_data)
        with pytest.raises(LiveTradingDisabledError, match="TRADING_MODE=PAPER"):
            registry.resolve_for_order(TradingMode.LIVE, LIVE_ACCOUNT)

    def test_live_needs_env_guards(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS, trading_mode="LIVE"), market_data)
        with pytest.raises(LiveTradingDisabledError, match="guards"):
            registry.resolve_for_order(TradingMode.LIVE, LIVE_ACCOUNT)

    def test_live_needs_application_level_arming(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS, **LIVE_ENV), market_data)
        unarmed = AccountRef("acc", BrokerType.DHAN, BrokerEnvironment.LIVE, live_armed=False)
        with pytest.raises(LiveTradingDisabledError, match="armed"):
            registry.resolve_for_order(TradingMode.LIVE, unarmed)

    def test_live_with_every_guard_returns_live_adapter(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS, **LIVE_ENV), market_data)
        broker = registry.resolve_for_order(TradingMode.LIVE, LIVE_ACCOUNT)
        assert isinstance(broker, DhanBroker) and broker.environment is BrokerEnvironment.LIVE

    def test_live_account_cannot_be_used_for_sandbox_mode(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS, trading_mode="SANDBOX"), market_data)
        with pytest.raises(LiveTradingDisabledError, match="does not match"):
            registry.resolve_for_order(TradingMode.SANDBOX, LIVE_ACCOUNT)

    def test_sandbox_uses_sandbox_url_only(self, market_data):
        registry = BrokerRegistry(make_settings(**DHAN_CREDS, trading_mode="SANDBOX"), market_data)
        broker = registry.resolve_for_order(TradingMode.SANDBOX, SANDBOX_ACCOUNT)
        assert isinstance(broker, DhanBroker) and broker._client.base_url == "https://sandbox.dhan.co/v2"

    def test_missing_credentials_and_unimplemented_brokers(self, market_data):
        registry = BrokerRegistry(make_settings(trading_mode="SANDBOX"), market_data)
        with pytest.raises(BrokerNotConfiguredError, match="credentials"):
            registry.resolve_for_order(TradingMode.SANDBOX, SANDBOX_ACCOUNT)
        with pytest.raises(BrokerNotConfiguredError):
            registry.get_adapter(BrokerType.FYERS, BrokerEnvironment.LIVE)
        with pytest.raises(LiveTradingDisabledError, match="BACKTEST"):
            registry.resolve_for_order(TradingMode.BACKTEST, None)


async def test_live_adapter_refuses_orders_without_guard_second_line_of_defence():
    transport = ExplodingTransport()
    client = DhanClient("https://api.dhan.co/v2", "1000000001", "fake", transport=transport)
    broker = DhanBroker(client, BrokerEnvironment.LIVE, live_guard=lambda: False)
    order = OrderRequest(
        "cid",
        InstrumentRef("RELIANCE", "NSE", "2885"),
        OrderSide.BUY,
        OrderType.MARKET,
        ProductType.INTRADAY,
        1,
    )
    with pytest.raises(LiveTradingDisabledError):
        await broker.place_order(order)
    assert transport.requests == []
    await broker.close()


async def test_post_orders_in_paper_mode_never_calls_a_real_broker(market_data):
    """Dhan + Zerodha credentials are configured, a LIVE armed account exists - PAPER still stays on PaperBroker."""
    transport = ExplodingTransport()
    settings = make_settings(**DHAN_CREDS, zerodha_api_key="k", zerodha_access_token="t")
    container = await build_container(settings, market_data, transport)
    try:
        async with container.db.session_factory() as session:
            services = Services(session, container)
            account = await services.brokers.create(
                None,
                name="Dhan live",
                broker_type=BrokerType.DHAN,
                environment=BrokerEnvironment.LIVE,
                is_default=True,
            )
            account.live_armed = True
            order = await services.orders.place_order(
                PlaceOrderCommand(
                    symbol="RELIANCE", side=OrderSide.BUY, quantity=5, broker_account_id=account.id
                )
            )
            assert order.broker_type is BrokerType.PAPER and order.trading_mode is TradingMode.PAPER
            assert order.broker_order_id.startswith("PAPER-")

            with pytest.raises(OrderRejectedError, match="not allowed while TRADING_MODE=PAPER"):
                await services.orders.place_order(
                    PlaceOrderCommand(
                        symbol="RELIANCE",
                        side=OrderSide.BUY,
                        quantity=5,
                        trading_mode=TradingMode.LIVE,
                        broker_account_id=account.id,
                    )
                )
        assert transport.requests == []
    finally:
        await container.close()


async def test_arming_live_requires_phrase_and_live_account(services):
    from app.core.exceptions import ValidationFailedError

    paper = await services.brokers.ensure_paper_account()
    with pytest.raises(ValidationFailedError, match="Only LIVE"):
        await services.brokers.arm_live(paper.id, True, LIVE_CONFIRMATION_PHRASE)
    live = await services.brokers.create(
        None, name="Dhan live", broker_type=BrokerType.DHAN, environment=BrokerEnvironment.LIVE
    )
    with pytest.raises(ValidationFailedError, match="phrase"):
        await services.brokers.arm_live(live.id, True, "sure")
    assert (await services.brokers.arm_live(live.id, True, LIVE_CONFIRMATION_PHRASE)).live_armed is True
    assert (await services.brokers.arm_live(live.id, False, "")).live_armed is False


class TestKillSwitch:
    async def _running_strategy(self, services):
        body = StrategyCreate(
            name="EMA",
            strategy_type="EMA_CROSSOVER",
            symbol="RELIANCE",
            timeframe="5m",
            capital=100_000,
            risk_per_trade=0.01,
            stop_loss_pct=0.01,
            target_pct=0.02,
            parameters={"fast_period": 5, "slow_period": 10},
        )
        strategy = await services.strategies.create(None, body.model_dump())
        return await services.strategies.start(strategy.id)

    async def test_stops_strategies_cancels_orders_blocks_entries_keeps_positions(self, services):
        strategy = await self._running_strategy(services)
        await services.orders.place_order(
            PlaceOrderCommand(symbol="RELIANCE", side=OrderSide.BUY, quantity=10)
        )
        resting = await services.orders.place_order(
            PlaceOrderCommand(
                symbol="INFY", side=OrderSide.BUY, quantity=1, order_type=OrderType.LIMIT, price=1000
            )
        )
        result = await services.trading.set_kill_switch(True, "test")
        assert (
            result.kill_switch_active,
            result.strategies_stopped,
            result.orders_cancelled,
            result.positions_closed,
        ) == (True, 1, 1, 0)
        await services.session.refresh(strategy)
        assert strategy.status is StrategyStatus.STOPPED and resting.status.value == "CANCELLED"
        assert (
            len(await services.positions.list_positions("open")) == 1
        )  # positions are NOT closed by default
        assert (await services.risk.status(TradingMode.PAPER)).system_state == "HALTED"

        with pytest.raises(OrderRejectedError, match="Kill switch"):
            await services.orders.place_order(
                PlaceOrderCommand(symbol="INFY", side=OrderSide.BUY, quantity=1)
            )
        with pytest.raises(TradingHaltedError):
            await services.strategies.start(strategy.id)

        # reducing risk is still possible while halted
        exit_order = await services.orders.place_order(
            PlaceOrderCommand(symbol="RELIANCE", side=OrderSide.SELL, quantity=10)
        )
        assert exit_order.status.value == "FILLED"

        await services.trading.set_kill_switch(False, None)
        assert (
            await services.orders.place_order(
                PlaceOrderCommand(symbol="INFY", side=OrderSide.BUY, quantity=1)
            )
        ).status.value == "FILLED"

    async def test_optionally_closes_positions(self, services):
        await services.risk.update_config({"close_positions_on_kill_switch": True})
        await services.orders.place_order(
            PlaceOrderCommand(symbol="RELIANCE", side=OrderSide.BUY, quantity=10)
        )
        result = await services.trading.set_kill_switch(True, None)
        assert result.positions_closed == 1 and await services.positions.list_positions("open") == []
        assert (await services.trades.list_trades())[0].exit_reason.value == "KILL_SWITCH"
