"""DhanHQ v2 REST client."""

from __future__ import annotations

import httpx

from app.brokers.http import BrokerHttpClient


class DhanClient(BrokerHttpClient):
    broker_name = "Dhan"

    def __init__(
        self,
        base_url: str,
        client_id: str,
        access_token: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client_id = client_id
        headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        super().__init__(base_url, headers, timeout, transport)
