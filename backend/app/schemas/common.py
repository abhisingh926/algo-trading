from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class StatusInfo(BaseModel):
    code: int
    description: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    status: StatusInfo
    data: T | None = None


def ok(
    data: Any = None, message: str = "OK", code: int = 200, description: str | None = None
) -> ApiResponse[Any]:
    return ApiResponse(
        success=True,
        message=message,
        status=StatusInfo(code=code, description=description or message),
        data=data,
    )
