"""Shared HTTP plumbing for broker REST adapters: error mapping without ever logging credentials."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.exceptions import BrokerConnectionError, BrokerError
from app.core.logging import get_logger

logger = get_logger(__name__)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class BrokerHttpClient:
    """Thin wrapper over httpx.AsyncClient. Auth headers are set once and never logged."""

    broker_name = "broker"

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str],
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url, headers=headers, timeout=timeout, transport=transport
        )

    def extract_error(self, body: Any) -> str:
        if isinstance(body, dict):
            for key in ("errorMessage", "message", "error", "remarks", "errorCode"):
                if body.get(key):
                    return str(body[key])
        return "Unknown broker error"

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._http.request(method, path, **kwargs)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            logger.warning(
                "broker_http_transport_error",
                extra={"broker": self.broker_name, "path": path, "error": type(exc).__name__},
            )
            raise BrokerConnectionError(f"{self.broker_name} is unreachable ({type(exc).__name__})") from exc

        try:
            body: Any = response.json() if response.content else None
        except ValueError:
            body = None

        if response.status_code in _RETRYABLE_STATUS:
            raise BrokerConnectionError(f"{self.broker_name} returned HTTP {response.status_code}")
        if response.status_code >= 400:
            detail = self.extract_error(body)
            logger.warning(
                "broker_http_error",
                extra={
                    "broker": self.broker_name,
                    "path": path,
                    "status": response.status_code,
                    "detail": detail,
                },
            )
            raise BrokerError(
                f"{self.broker_name} rejected the request: {detail}",
                data={"http_status": response.status_code},
            )
        return body

    async def close(self) -> None:
        await self._http.aclose()
