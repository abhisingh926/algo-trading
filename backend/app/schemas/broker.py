from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import BrokerEnvironment, BrokerType, ConnectionStatus, TradingMode
from app.schemas.common import ORMModel


class BrokerAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    broker_type: BrokerType
    environment: BrokerEnvironment
    is_default: bool = False

    @model_validator(mode="after")
    def _paper_consistency(self) -> BrokerAccountCreate:
        if (self.broker_type is BrokerType.PAPER) != (self.environment is BrokerEnvironment.PAPER):
            raise ValueError("PAPER broker type and PAPER environment must be used together")
        return self


class BrokerAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    is_default: bool | None = None


class BrokerAccountRead(ORMModel):
    id: str
    name: str
    broker_type: BrokerType
    environment: BrokerEnvironment
    is_active: bool
    is_default: bool
    live_armed: bool
    credentials_configured: bool = False
    connection_status: ConnectionStatus
    last_checked_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class BrokerTestRequest(BaseModel):
    broker_account_id: str


class BrokerTestResult(BaseModel):
    broker_account_id: str
    broker_type: BrokerType
    connected: bool
    latency_ms: float | None
    detail: str


class LiveGuard(BaseModel):
    name: str
    passed: bool
    detail: str


class SupportedBroker(BaseModel):
    broker_type: BrokerType
    implemented: bool
    credentials_configured: bool
    environments: list[str]


class BrokerStatus(BaseModel):
    trading_mode: TradingMode
    live_trading_enabled: bool
    live_guards: list[LiveGuard]
    order_routing: str
    supported: list[SupportedBroker]


class ArmLiveRequest(BaseModel):
    armed: bool
    confirmation: str = ""
