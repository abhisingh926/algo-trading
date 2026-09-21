"""Run the workers as a dedicated process:  python -m app.workers.runner

Use this together with RUN_WORKERS=false on the API when scaling the API horizontally - exactly
ONE worker process must run, otherwise strategies would be evaluated twice.
"""

from __future__ import annotations

import asyncio
import signal

from app.container import AppContainer
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.trading.engine import TradingEngine
from app.workers import market_data_worker, order_monitor_worker, strategy_worker
from app.workers.base import PeriodicWorker


def build_workers(engine: TradingEngine) -> list[PeriodicWorker]:
    return [
        market_data_worker.build(engine),
        order_monitor_worker.build(engine),
        strategy_worker.build(engine),
    ]


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    container = AppContainer.build(settings)
    engine = TradingEngine(container)
    await engine.bootstrap()
    workers = build_workers(engine)
    for worker in workers:
        worker.start()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    for worker in workers:
        await worker.stop()
    await container.close()


if __name__ == "__main__":
    asyncio.run(main())
