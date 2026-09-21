"""Kite Connect v3 REST client."""

from __future__ import annotations

from typing import Any

import httpx

from app.brokers.http import BrokerHttpClient


class ZerodhaClient(BrokerHttpClient):
    broker_name = "Zerodha"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        access_token: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"X-Kite-Version": "3", "Authorization": f"token {api_key}:{access_token}"}
        super().__init__(base_url, headers, timeout, transport)

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        body = await super().request(method, path, **kwargs)
        return body.get("data") if isinstance(body, dict) and "data" in body else body
