"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.container import AppContainer
from app.core.config import APP_VERSION, Settings, get_settings
from app.core.exceptions import envelope, register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.trading.engine import TradingEngine
from app.workers.runner import build_workers

logger = get_logger("app")


def _startup_banner(settings: Settings) -> str:
    live = "ENABLED" if settings.live_trading_enabled else "DISABLED"
    return (
        "\n" + "=" * 46 + f"\n  Trading Mode: {settings.trading_mode.value}\n\n  LIVE TRADING: {live}\n"
        f"  Market data : {settings.market_data_provider}\n" + "=" * 46
    )


def create_app(settings: Settings | None = None, container: AppContainer | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or AppContainer.build(settings)
        engine = TradingEngine(app.state.container)
        print(_startup_banner(settings), flush=True)  # noqa: T201 - intentional, human readable safety banner
        logger.info(
            "application_started",
            extra={
                "trading_mode": settings.trading_mode.value,
                "live_trading_enabled": settings.live_trading_enabled,
                "app_env": settings.app_env,
            },
        )
        if settings.uses_ephemeral_secret:
            logger.warning("SECRET_KEY is not set: using an ephemeral key, logins will not survive a restart")
        await engine.bootstrap()
        workers = build_workers(engine) if settings.run_workers else []
        for worker in workers:
            worker.start()
        try:
            yield
        finally:
            for worker in workers:
                await worker.stop()
            await app.state.container.close()

    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        description="Algo trading platform for Indian markets. Default mode is PAPER; live trading is disabled unless explicitly enabled.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["System"])
    async def health() -> dict:
        db_ok = await app.state.container.db.ping()
        data = {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "trading_mode": settings.trading_mode.value,
            "live_trading_enabled": settings.live_trading_enabled,
        }
        return envelope(True, "Service is healthy" if db_ok else "Service is degraded", 200, "OK", data)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return envelope(
            True, settings.app_name, 200, "See /docs for the API", {"docs": "/docs", "health": "/health"}
        )

    return app


app = create_app()
