"""BrokerRegistry: the ONLY place that decides which broker adapter receives an order.

Safety rules enforced here (and tested in tests/test_safety.py):
  * PAPER orders always go to PaperBroker - no matter which broker credentials are configured.
  * SANDBOX orders need TRADING_MODE=SANDBOX and a SANDBOX broker account.
  * LIVE orders need TRADING_MODE=LIVE + ENABLE_LIVE_TRADING=true + the confirmation phrase
    (environment) AND a LIVE broker account that was explicitly armed in the database (application).
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.brokers.base import BrokerInterface
from app.brokers.dhan.broker import DhanBroker
from app.brokers.dhan.client import DhanClient
from app.brokers.paper.broker import PaperBroker
from app.brokers.zerodha.broker import ZerodhaBroker
from app.brokers.zerodha.client import ZerodhaClient
from app.core.config import Settings
from app.core.exceptions import BrokerNotConfiguredError, LiveTradingDisabledError
from app.domain.enums import BrokerEnvironment, BrokerType, TradingMode
from app.market_data.base import MarketDataProvider

# broker -> environments its adapter supports
SUPPORTED_ENVIRONMENTS: dict[BrokerType, tuple[BrokerEnvironment, ...]] = {
    BrokerType.PAPER: (BrokerEnvironment.PAPER,),
    BrokerType.DHAN: (BrokerEnvironment.SANDBOX, BrokerEnvironment.LIVE),
    BrokerType.ZERODHA: (BrokerEnvironment.LIVE,),
    BrokerType.FYERS: (),  # adapter not implemented yet
}


@dataclass(frozen=True, slots=True)
class AccountRef:
    """The few BrokerAccount fields routing needs (keeps this module free of ORM imports)."""

    id: str
    broker_type: BrokerType
    environment: BrokerEnvironment
    live_armed: bool = False


class BrokerRegistry:
    def __init__(
        self,
        settings: Settings,
        market_data: MarketDataProvider,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport  # tests inject httpx.MockTransport here
        self.paper = PaperBroker(
            market_data,
            initial_capital=settings.paper_initial_capital,
            slippage_pct=settings.paper_slippage_pct,
            max_fill_qty_per_tick=settings.paper_max_fill_qty_per_tick,
        )
        self._adapters: dict[tuple[BrokerType, BrokerEnvironment], BrokerInterface] = {}

    # ---- routing -------------------------------------------------------------------------------
    def resolve_for_order(self, mode: TradingMode, account: AccountRef | None) -> BrokerInterface:
        if mode is TradingMode.PAPER:
            return self.paper
        if mode is TradingMode.BACKTEST:
            raise LiveTradingDisabledError("Orders cannot be placed in BACKTEST mode")
        if mode is not self._settings.trading_mode:
            raise LiveTradingDisabledError(
                f"{mode.value} orders are not allowed while TRADING_MODE={self._settings.trading_mode.value}"
            )
        if account is None:
            raise BrokerNotConfiguredError(f"No active {mode.value} broker account is configured")
        if account.environment.value != mode.value:
            raise LiveTradingDisabledError(
                f"Broker account environment {account.environment.value} does not match trading mode {mode.value}"
            )
        if mode is TradingMode.LIVE:
            if not self._settings.live_trading_enabled:
                raise LiveTradingDisabledError("Live trading environment guards are not all satisfied")
            if not account.live_armed:
                raise LiveTradingDisabledError("This LIVE broker account has not been armed for live trading")
        return self.get_adapter(account.broker_type, account.environment)

    def resolve_for_existing_order(self, broker_type: BrokerType, mode: TradingMode) -> BrokerInterface:
        """Adapter for status sync / cancel of an order that already exists (never places orders)."""
        if broker_type is BrokerType.PAPER or mode is TradingMode.PAPER:
            return self.paper
        return self.get_adapter(broker_type, BrokerEnvironment(mode.value))

    # ---- adapters ------------------------------------------------------------------------------
    def get_adapter(self, broker_type: BrokerType, environment: BrokerEnvironment) -> BrokerInterface:
        if broker_type is BrokerType.PAPER:
            return self.paper
        if environment not in SUPPORTED_ENVIRONMENTS.get(broker_type, ()):
            raise BrokerNotConfiguredError(
                f"{broker_type.value} adapter does not support the {environment.value} environment"
            )
        if not self._settings.broker_credentials_configured(broker_type):
            raise BrokerNotConfiguredError(f"{broker_type.value} credentials are not set in the environment")
        key = (broker_type, environment)
        if key not in self._adapters:
            self._adapters[key] = self._build(broker_type, environment)
        return self._adapters[key]

    def _build(self, broker_type: BrokerType, environment: BrokerEnvironment) -> BrokerInterface:
        s = self._settings

        def live_guard() -> bool:
            return s.live_trading_enabled

        if broker_type is BrokerType.DHAN:
            base_url = (
                s.dhan_live_base_url if environment is BrokerEnvironment.LIVE else s.dhan_sandbox_base_url
            )
            client = DhanClient(
                base_url,
                s.dhan_client_id,
                s.dhan_access_token.get_secret_value(),
                s.broker_http_timeout_seconds,
                self._transport,
            )
            return DhanBroker(client, environment, live_guard)
        if broker_type is BrokerType.ZERODHA:
            client_z = ZerodhaClient(
                s.zerodha_base_url,
                s.zerodha_api_key.get_secret_value(),
                s.zerodha_access_token.get_secret_value(),
                s.broker_http_timeout_seconds,
                self._transport,
            )
            return ZerodhaBroker(client_z, live_guard)
        raise BrokerNotConfiguredError(f"{broker_type.value} adapter is not implemented")

    async def close(self) -> None:
        for adapter in self._adapters.values():
            await adapter.close()
        self._adapters.clear()
