"""Application exceptions + centralised handlers producing the standard response envelope."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    status_code = 500
    message = "Something went wrong"

    def __init__(self, description: str, *, message: str | None = None, data: Any = None) -> None:
        super().__init__(description)
        self.description = description
        self.message = message or type(self).message
        self.data = data


class NotFoundError(AppError):
    status_code = 404
    message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    message = "Request conflicts with current state"


class ValidationFailedError(AppError):
    status_code = 422
    message = "Validation failed"


class AuthenticationError(AppError):
    status_code = 401
    message = "Authentication failed"


class PermissionDeniedError(AppError):
    status_code = 403
    message = "Permission denied"


class OrderRejectedError(AppError):
    status_code = 400
    message = "Unable to place order"


class TradingHaltedError(AppError):
    status_code = 423
    message = "Trading is halted"


class LiveTradingDisabledError(AppError):
    status_code = 403
    message = "Live trading is disabled"


class BrokerError(AppError):
    """Broker refused / failed in a non-retryable way."""

    status_code = 502
    message = "Broker request failed"


class BrokerConnectionError(BrokerError):
    """Transient transport failure - safe to retry."""

    status_code = 503
    message = "Broker is unreachable"


class BrokerNotConfiguredError(BrokerError):
    status_code = 400
    message = "Broker is not configured"


class NotAvailableYetError(AppError):
    """A documented feature whose data source is not connected yet (for example news)."""

    status_code = 501
    message = "Not available yet"


class MarketDataError(AppError):
    status_code = 502
    message = "Market data unavailable"


def envelope(success: bool, message: str, code: int, description: str, data: Any = None) -> dict[str, Any]:
    return {
        "success": success,
        "message": message,
        "status": {"code": code, "description": description},
        "data": data,
    }


def _error(code: int, message: str, description: str, data: Any = None) -> JSONResponse:
    return JSONResponse(status_code=code, content=envelope(False, message, code, description, data))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.message, exc.description, exc.data)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        first = f"{errors[0]['field']}: {errors[0]['message']}" if errors else "Invalid request"
        return _error(422, "Validation failed", first, {"errors": errors})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(exc.status_code, "Request failed", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"path": request.url.path, "method": request.method})
        return _error(500, "Internal server error", "An unexpected error occurred")
