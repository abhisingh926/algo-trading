"""Application settings. Every secret and tunable comes from the environment (Pydantic Settings)."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import PrivateAttr, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.enums import BrokerType, TradingMode

APP_VERSION = "0.1.0"
LIVE_CONFIRMATION_PHRASE = "I-ACCEPT-REAL-MONEY-RISK"
_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT / ".env", ".env"), env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "Algo Trading Platform"
    app_env: str = "development"
    log_level: str = "INFO"
    log_format: str = "json"  # json | console

    database_url: str = "mysql+aiomysql://algo:algo@localhost:3306/algo_trading"
    database_echo: bool = False
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"

    secret_key: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    auth_enabled: bool = True
    allow_registration: bool = False

    # --- trading safety ---
    trading_mode: TradingMode = TradingMode.PAPER
    enable_live_trading: bool = False
    live_trading_confirmation: str = ""

    # --- market data ---
    market_data_provider: str = "simulated"
    simulated_market_24x7: bool = True

    # --- paper broker ---
    paper_initial_capital: float = 500_000
    paper_slippage_pct: float = 0.0005
    paper_max_fill_qty_per_tick: int = 0  # 0 = fill fully; >0 simulates partial fills

    # --- risk defaults (seed values for the DB risk configuration) ---
    max_daily_loss: float = 5_000
    max_risk_per_trade: float = 0.01
    max_open_positions: int = 5
    max_trades_per_day: int = 20
    max_position_size: int = 5_000
    max_order_value: float = 500_000
    max_consecutive_losses: int = 5
    max_strategy_drawdown: float = 0.10

    # --- charges defaults (Indian intraday equity; all overridable per backtest) ---
    brokerage_per_order: float = 20.0
    brokerage_pct: float = 0.0003
    stt_sell_pct: float = 0.00025
    exchange_txn_pct: float = 0.0000297
    sebi_pct: float = 0.000001
    stamp_duty_buy_pct: float = 0.00003
    gst_pct: float = 0.18

    # --- workers / order handling ---
    run_workers: bool = True
    strategy_poll_seconds: float = 10
    order_monitor_poll_seconds: float = 3
    market_data_poll_seconds: float = 3
    portfolio_snapshot_seconds: float = 60
    order_submit_max_retries: int = 3
    research_fetch_concurrency: int = 4
    research_history_days: int = 400
    order_retry_backoff_seconds: float = 0.5
    broker_http_timeout_seconds: float = 10

    # --- brokers ---
    dhan_client_id: str = ""
    dhan_access_token: SecretStr = SecretStr("")
    dhan_api_key: SecretStr = SecretStr("")
    dhan_api_secret: SecretStr = SecretStr("")
    dhan_sandbox_base_url: str = "https://sandbox.dhan.co/v2"
    dhan_live_base_url: str = "https://api.dhan.co/v2"

    zerodha_api_key: SecretStr = SecretStr("")
    zerodha_api_secret: SecretStr = SecretStr("")
    zerodha_access_token: SecretStr = SecretStr("")
    zerodha_base_url: str = "https://api.kite.trade"

    fyers_client_id: str = ""
    fyers_secret_key: SecretStr = SecretStr("")
    fyers_access_token: SecretStr = SecretStr("")

    _ephemeral_secret: bool = PrivateAttr(default=False)

    @field_validator("trading_mode", mode="before")
    @classmethod
    def _normalise_mode(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper() or TradingMode.PAPER.value
        return value

    @field_validator("market_data_provider", mode="before")
    @classmethod
    def _normalise_provider(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _ensure_secret_key(self) -> Settings:
        if not self.secret_key.get_secret_value():
            if self.is_production:
                raise ValueError("SECRET_KEY must be set when APP_ENV=production")
            # Development convenience: ephemeral key, tokens die on restart.
            self.secret_key = SecretStr(secrets.token_hex(32))
            self._ephemeral_secret = True
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def uses_ephemeral_secret(self) -> bool:
        return self._ephemeral_secret

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def live_env_guards(self) -> list[tuple[str, bool, str]]:
        """Environment-level guards. ALL must pass (plus a DB-armed LIVE account) before a live order."""
        return [
            (
                "TRADING_MODE=LIVE",
                self.trading_mode is TradingMode.LIVE,
                f"current: {self.trading_mode.value}",
            ),
            (
                "ENABLE_LIVE_TRADING=true",
                self.enable_live_trading,
                f"current: {str(self.enable_live_trading).lower()}",
            ),
            (
                "LIVE_TRADING_CONFIRMATION phrase",
                self.live_trading_confirmation == LIVE_CONFIRMATION_PHRASE,
                (
                    "matches"
                    if self.live_trading_confirmation == LIVE_CONFIRMATION_PHRASE
                    else "not set / wrong"
                ),
            ),
        ]

    @property
    def live_trading_enabled(self) -> bool:
        return all(passed for _, passed, _ in self.live_env_guards)

    def broker_credentials_configured(self, broker: BrokerType) -> bool:
        if broker is BrokerType.PAPER:
            return True
        if broker is BrokerType.DHAN:
            return bool(self.dhan_client_id and self.dhan_access_token.get_secret_value())
        if broker is BrokerType.ZERODHA:
            return bool(
                self.zerodha_api_key.get_secret_value() and self.zerodha_access_token.get_secret_value()
            )
        if broker is BrokerType.FYERS:
            return bool(self.fyers_client_id and self.fyers_access_token.get_secret_value())
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
