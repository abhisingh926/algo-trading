from __future__ import annotations

from app.container import AppContainer
from app.core.config import APP_VERSION
from app.domain.enums import BrokerType, TradingMode
from app.schemas.dashboard import ComponentStatus, SystemConfig, SystemStatus
from app.services.risk_service import RiskService
from app.trading.charges import ChargesConfig
from app.utils.time import utcnow


class SystemService:
    def __init__(self, container: AppContainer, risk: RiskService) -> None:
        self.container = container
        self.risk = risk

    def _worker(self, key: str, name: str, worker: str, halted: bool) -> ComponentStatus:
        if not self.container.settings.run_workers:
            return ComponentStatus(
                key=key, name=name, status="STOPPED", detail="RUN_WORKERS=false in this process"
            )
        status, detail = self.container.workers.status(worker)
        if halted and status == "RUNNING":
            status, detail = "HALTED", "Kill switch is active"
        return ComponentStatus(key=key, name=name, status=status, detail=detail)

    async def status(self) -> SystemStatus:
        c, s = self.container, self.container.settings
        halted = await self.risk.is_halted()
        db_ok = await c.db.ping()
        redis_ok = await c.quote_cache.ping()
        try:
            data_ok = await c.market_data.ping()
        except Exception:
            data_ok = False

        if s.trading_mode in (TradingMode.PAPER, TradingMode.BACKTEST):
            broker = ComponentStatus(
                key="broker",
                name="Broker Connection",
                status="CONNECTED",
                detail="PaperBroker (simulated execution)",
            )
        else:
            configured = [
                b.value for b in (BrokerType.DHAN, BrokerType.ZERODHA) if s.broker_credentials_configured(b)
            ]
            broker = ComponentStatus(
                key="broker",
                name="Broker Connection",
                status="CONNECTED" if configured else "NOT_CONFIGURED",
                detail=(
                    f"Credentials present for: {', '.join(configured)}"
                    if configured
                    else "No broker credentials in environment"
                ),
            )
        components = [
            broker,
            ComponentStatus(
                key="market_data",
                name="Market Data",
                status="CONNECTED" if data_ok else "DISCONNECTED",
                detail=f"provider: {c.market_data.name}",
            ),
            self._worker("strategy_engine", "Strategy Engine", "strategy_worker", halted),
            self._worker("order_engine", "Order Engine", "order_monitor_worker", halted),
            ComponentStatus(key="database", name="Database", status="CONNECTED" if db_ok else "DISCONNECTED"),
            ComponentStatus(
                key="redis",
                name="Redis",
                status={True: "CONNECTED", False: "DISCONNECTED", None: "NOT_CONFIGURED"}[redis_ok],
                detail=None if redis_ok else "Quote cache falls back to in-process memory",
            ),
        ]
        return SystemStatus(
            trading_mode=s.trading_mode,
            live_trading_enabled=s.live_trading_enabled,
            kill_switch_active=halted,
            system_state="HALTED" if halted else "RUNNING",
            market_data_provider=c.market_data.name,
            server_time=utcnow(),
            components=components,
        )

    def config(self) -> SystemConfig:
        s = self.container.settings
        charges = ChargesConfig(
            s.brokerage_per_order,
            s.brokerage_pct,
            s.stt_sell_pct,
            s.exchange_txn_pct,
            s.sebi_pct,
            s.stamp_duty_buy_pct,
            s.gst_pct,
        )
        return SystemConfig(
            app_name=s.app_name,
            app_env=s.app_env,
            version=APP_VERSION,
            trading_mode=s.trading_mode,
            live_trading_enabled=s.live_trading_enabled,
            auth_enabled=s.auth_enabled,
            workers_enabled=s.run_workers,
            market_data_provider=self.container.market_data.name,
            paper_initial_capital=s.paper_initial_capital,
            paper_slippage_pct=s.paper_slippage_pct,
            strategy_poll_seconds=s.strategy_poll_seconds,
            order_monitor_poll_seconds=s.order_monitor_poll_seconds,
            market_data_poll_seconds=s.market_data_poll_seconds,
            default_charges=charges.to_dict(),
            brokers_configured={
                b.value: s.broker_credentials_configured(b)
                for b in (BrokerType.DHAN, BrokerType.ZERODHA, BrokerType.FYERS)
            },
        )
