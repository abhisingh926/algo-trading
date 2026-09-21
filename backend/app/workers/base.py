"""Tiny periodic-task runner used by all workers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.container import WorkerRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)


class PeriodicWorker:
    def __init__(
        self,
        name: str,
        interval_seconds: float,
        job: Callable[[], Awaitable[object]],
        registry: WorkerRegistry,
    ) -> None:
        self.name = name
        self.interval = max(interval_seconds, 0.2)
        self._job = job
        self._registry = registry
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        logger.info("worker_started", extra={"worker": self.name, "interval": self.interval})
        while True:
            try:
                await self._job()
                self._registry.beat(self.name, self.interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # a worker must never die because one cycle failed
                logger.exception("worker_cycle_failed", extra={"worker": self.name})
                self._registry.beat(self.name, self.interval, error=f"{type(exc).__name__}: {exc}"[:300])
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name=self.name)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("worker_stopped", extra={"worker": self.name})
