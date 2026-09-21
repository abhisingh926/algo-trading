from fastapi import APIRouter

from app.core.dependencies import CurrentUser, ServicesDep, user_id_of
from app.schemas.broker import (
    ArmLiveRequest,
    BrokerAccountCreate,
    BrokerAccountRead,
    BrokerAccountUpdate,
    BrokerStatus,
    BrokerTestRequest,
    BrokerTestResult,
)
from app.schemas.common import ApiResponse, ok

router = APIRouter(prefix="/brokers", tags=["Brokers"])


@router.get("", response_model=ApiResponse[list[BrokerAccountRead]])
async def list_brokers(services: ServicesDep):
    return ok(
        [services.brokers.to_read(a) for a in await services.brokers.list_accounts()], "Broker accounts"
    )


@router.post("", response_model=ApiResponse[BrokerAccountRead], status_code=201)
async def create_broker(body: BrokerAccountCreate, services: ServicesDep, user: CurrentUser):
    account = await services.brokers.create(user_id_of(user), **body.model_dump())
    return ok(
        services.brokers.to_read(account),
        "Broker account created successfully",
        201,
        "Broker account created",
    )


@router.get("/status", response_model=ApiResponse[BrokerStatus])
async def broker_status(services: ServicesDep):
    return ok(await services.brokers.status(), "Broker status")


@router.post("/test", response_model=ApiResponse[BrokerTestResult])
async def test_broker(body: BrokerTestRequest, services: ServicesDep):
    result = await services.brokers.test_connection(body.broker_account_id)
    return ok(
        result,
        "Connection successful" if result.connected else "Connection failed",
        description=result.detail,
    )


@router.put("/{account_id}", response_model=ApiResponse[BrokerAccountRead])
async def update_broker(account_id: str, body: BrokerAccountUpdate, services: ServicesDep):
    account = await services.brokers.update(account_id, body.model_dump(exclude_unset=True))
    return ok(services.brokers.to_read(account), "Broker account updated")


@router.post("/{account_id}/arm-live", response_model=ApiResponse[BrokerAccountRead])
async def arm_live(account_id: str, body: ArmLiveRequest, services: ServicesDep):
    """Application-level live trading guard (in addition to the three environment guards)."""
    account = await services.brokers.arm_live(account_id, body.armed, body.confirmation)
    return ok(
        services.brokers.to_read(account), "Live trading armed" if body.armed else "Live trading disarmed"
    )


@router.delete("/{account_id}", response_model=ApiResponse[None])
async def delete_broker(account_id: str, services: ServicesDep):
    await services.brokers.delete(account_id)
    return ok(None, "Broker account deleted")
