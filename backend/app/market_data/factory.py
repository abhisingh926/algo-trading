from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.enums import BrokerType
from app.market_data.base import MarketDataProvider
from app.market_data.simulated import SimulatedMarketDataProvider

logger = get_logger(__name__)


def build_market_data_provider(settings: Settings) -> MarketDataProvider:
    """Real providers are read-only data clients; they cannot place orders."""
    choice = settings.market_data_provider
    if choice == "dhan" and settings.broker_credentials_configured(BrokerType.DHAN):
        from app.brokers.dhan.client import DhanClient
        from app.brokers.dhan.market_data import DhanMarketData

        client = DhanClient(
            settings.dhan_live_base_url,
            settings.dhan_client_id,
            settings.dhan_access_token.get_secret_value(),
            settings.broker_http_timeout_seconds,
        )
        return DhanMarketData(client)
    if choice == "zerodha" and settings.broker_credentials_configured(BrokerType.ZERODHA):
        from app.brokers.zerodha.client import ZerodhaClient
        from app.brokers.zerodha.market_data import ZerodhaMarketData

        client_z = ZerodhaClient(
            settings.zerodha_base_url,
            settings.zerodha_api_key.get_secret_value(),
            settings.zerodha_access_token.get_secret_value(),
            settings.broker_http_timeout_seconds,
        )
        return ZerodhaMarketData(client_z)
    if choice != "simulated":
        logger.warning("market_data_provider_fallback", extra={"requested": choice, "using": "simulated"})
    return SimulatedMarketDataProvider(
        always_open=settings.simulated_market_24x7, poll_interval_seconds=settings.market_data_poll_seconds
    )
