from fastapi import APIRouter

from app.core.dependencies import ServicesDep
from app.core.exceptions import ValidationFailedError
from app.schemas.common import ApiResponse, ok
from app.schemas.risk import (
    KillSwitchRequest,
    KillSwitchResult,
    RiskConfigurationRead,
    RiskConfigurationUpdate,
    RiskStatus,
)

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("", response_model=ApiResponse[RiskConfigurationRead])
async def get_risk(services: ServicesDep):
    return ok(RiskConfigurationRead.model_validate(await services.risk.get_config()), "Risk configuration")


@router.put("", response_model=ApiResponse[RiskConfigurationRead])
async def update_risk(body: RiskConfigurationUpdate, services: ServicesDep):
    config = await services.risk.update_config(body.model_dump(exclude_unset=True, exclude_none=True))
    return ok(RiskConfigurationRead.model_validate(config), "Risk configuration updated")


@router.get("/status", response_model=ApiResponse[RiskStatus])
async def risk_status(services: ServicesDep):
    return ok(await services.risk.status(services.settings.trading_mode), "Risk status")


@router.post("/kill-switch", response_model=ApiResponse[KillSwitchResult])
async def kill_switch(body: KillSwitchRequest, services: ServicesDep):
    if not body.confirm:
        raise ValidationFailedError(
            "Set confirm=true to change the kill switch", message="Confirmation required"
        )
    result = await services.trading.set_kill_switch(body.activate, body.reason)
    return ok(
        result,
        "Kill switch activated" if body.activate else "Kill switch deactivated",
        description=result.message,
    )
