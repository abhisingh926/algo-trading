from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from app.brokers.registry import SUPPORTED_ENVIRONMENTS, AccountRef, BrokerRegistry
from app.core.config import LIVE_CONFIRMATION_PHRASE, Settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, ValidationFailedError
from app.domain.enums import BrokerEnvironment, BrokerType, ConnectionStatus, EventLevel, TradingMode
from app.models.broker import BrokerAccount
from app.repositories.broker_repository import BrokerRepository
from app.schemas.broker import BrokerAccountRead, BrokerStatus, BrokerTestResult, LiveGuard, SupportedBroker
from app.services.event_service import EventService
from app.utils.time import utcnow

PAPER_ACCOUNT_NAME = "Paper Broker"


class BrokerService:
    def __init__(
        self, brokers: BrokerRepository, registry: BrokerRegistry, events: EventService, settings: Settings
    ) -> None:
        self.brokers = brokers
        self.registry = registry
        self.events = events
        self.settings = settings

    def to_read(self, account: BrokerAccount) -> BrokerAccountRead:
        read = BrokerAccountRead.model_validate(account)
        read.credentials_configured = self.settings.broker_credentials_configured(account.broker_type)
        return read

    @staticmethod
    def ref(account: BrokerAccount) -> AccountRef:
        return AccountRef(account.id, account.broker_type, account.environment, account.live_armed)

    # ---- accounts ------------------------------------------------------------------------------
    async def ensure_paper_account(self) -> BrokerAccount:
        existing = await self.brokers.find(BrokerType.PAPER, BrokerEnvironment.PAPER)
        if existing:
            return existing[0]
        return await self.brokers.create(
            BrokerAccount(
                name=PAPER_ACCOUNT_NAME,
                broker_type=BrokerType.PAPER,
                environment=BrokerEnvironment.PAPER,
                is_default=True,
                connection_status=ConnectionStatus.CONNECTED,
            )
        )

    async def list_accounts(self) -> Sequence[BrokerAccount]:
        return await self.brokers.list_accounts()

    async def get(self, account_id: str) -> BrokerAccount:
        account = await self.brokers.get_by_id(account_id)
        if account is None:
            raise NotFoundError("Broker account not found")
        return account

    async def create(self, user_id: str | None, **values: Any) -> BrokerAccount:
        broker_type, environment = values["broker_type"], values["environment"]
        if environment not in SUPPORTED_ENVIRONMENTS.get(broker_type, ()):
            supported = (
                ", ".join(e.value for e in SUPPORTED_ENVIRONMENTS.get(broker_type, ()))
                or "none (adapter not implemented yet)"
            )
            raise ValidationFailedError(
                f"{broker_type.value} does not support the {environment.value} environment. Supported: {supported}"
            )
        if values.get("is_default"):
            await self.brokers.clear_default(environment)
        status = (
            ConnectionStatus.CONNECTED
            if broker_type is BrokerType.PAPER
            else (
                ConnectionStatus.UNKNOWN
                if self.settings.broker_credentials_configured(broker_type)
                else ConnectionStatus.NOT_CONFIGURED
            )
        )
        return await self.brokers.create(BrokerAccount(user_id=user_id, connection_status=status, **values))

    async def update(self, account_id: str, values: dict[str, Any]) -> BrokerAccount:
        account = await self.get(account_id)
        if values.get("is_default"):
            await self.brokers.clear_default(account.environment)
        return await self.brokers.update(account, values)

    async def delete(self, account_id: str) -> None:
        account = await self.get(account_id)
        if account.broker_type is BrokerType.PAPER and len(await self.brokers.find(BrokerType.PAPER)) <= 1:
            raise ConflictError("The last paper broker account cannot be deleted")
        await self.brokers.delete_entity(account)

    async def arm_live(self, account_id: str, armed: bool, confirmation: str) -> BrokerAccount:
        """Application-level live guard. Disarming is always allowed; arming needs the typed phrase."""
        account = await self.get(account_id)
        if armed:
            if account.environment is not BrokerEnvironment.LIVE:
                raise ValidationFailedError("Only LIVE broker accounts can be armed")
            if confirmation != LIVE_CONFIRMATION_PHRASE:
                raise ValidationFailedError("Confirmation phrase does not match")
        account = await self.brokers.update(account, {"live_armed": armed})
        await self.events.record(
            "live_trading_armed" if armed else "live_trading_disarmed",
            f"Broker account '{account.name}'",
            level=EventLevel.WARNING,
            broker_account_id=account.id,
        )
        return account

    async def resolve_account(self, mode: TradingMode, account_id: str | None) -> BrokerAccount | None:
        """Account an order in `mode` should use. PAPER always maps to the paper account."""
        if mode in (TradingMode.PAPER, TradingMode.BACKTEST):
            return await self.ensure_paper_account()
        if account_id:
            account = await self.brokers.get_by_id(account_id)
            if account is not None and account.is_active and account.environment.value == mode.value:
                return account
        candidates = await self.brokers.find(environment=BrokerEnvironment(mode.value))
        return candidates[0] if candidates else None

    # ---- status --------------------------------------------------------------------------------
    async def status(self) -> BrokerStatus:
        s = self.settings
        guards = [
            LiveGuard(name=name, passed=passed, detail=detail) for name, passed, detail in s.live_env_guards
        ]
        armed = [a for a in await self.brokers.find(environment=BrokerEnvironment.LIVE) if a.live_armed]
        guards.append(
            LiveGuard(
                name="LIVE broker account armed in application",
                passed=bool(armed),
                detail=f"armed: {armed[0].name}" if armed else "no armed LIVE account",
            )
        )
        routing = {
            TradingMode.PAPER: "All orders are routed to PaperBroker. No real broker API can be reached.",
            TradingMode.BACKTEST: "Order placement is disabled in BACKTEST mode.",
            TradingMode.SANDBOX: "SANDBOX orders go to the broker sandbox API; PAPER strategies still use PaperBroker.",
            TradingMode.LIVE: "LIVE orders reach the real broker ONLY when every live guard passes; otherwise they are rejected.",
        }[s.trading_mode]
        return BrokerStatus(
            trading_mode=s.trading_mode,
            live_trading_enabled=s.live_trading_enabled and bool(armed),
            live_guards=guards,
            order_routing=routing,
            supported=[
                SupportedBroker(
                    broker_type=bt,
                    implemented=bool(envs),
                    credentials_configured=s.broker_credentials_configured(bt),
                    environments=[e.value for e in envs],
                )
                for bt, envs in SUPPORTED_ENVIRONMENTS.items()
            ],
        )

    async def test_connection(self, account_id: str) -> BrokerTestResult:
        """Read-only connectivity check (profile call). Never places an order."""
        account = await self.get(account_id)
        started = time.perf_counter()
        try:
            adapter = self.registry.get_adapter(account.broker_type, account.environment)
            profile = await adapter.get_profile()
            connected, detail = True, f"Connected to {profile.broker}" + (
                f" ({profile.client_id_masked})" if profile.client_id_masked else ""
            )
            status = ConnectionStatus.CONNECTED
        except AppError as exc:
            connected, detail = False, exc.description
            configured = self.settings.broker_credentials_configured(account.broker_type)
            status = ConnectionStatus.DISCONNECTED if configured else ConnectionStatus.NOT_CONFIGURED
        latency = round((time.perf_counter() - started) * 1000, 1)
        await self.brokers.update(
            account,
            {
                "connection_status": status,
                "last_checked_at": utcnow(),
                "last_error": None if connected else detail,
            },
        )
        await self.events.record(
            "broker_connected" if connected else "broker_disconnected",
            f"{account.name}: {detail}",
            level=EventLevel.INFO if connected else EventLevel.WARNING,
            broker=account.broker_type.value,
        )
        return BrokerTestResult(
            broker_account_id=account.id,
            broker_type=account.broker_type,
            connected=connected,
            latency_ms=latency if connected else None,
            detail=detail,
        )
