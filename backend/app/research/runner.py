"""Keeps research runs alive as background tasks. Imports are lazy to avoid a cycle with the container."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.container import AppContainer

logger = get_logger(__name__)


class ResearchRunner:
    def __init__(self) -> None:
        self._container: AppContainer | None = None
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def bind(self, container: AppContainer) -> None:
        self._container = container

    def submit(self, run_id: str) -> None:
        if self._container is None:
            raise RuntimeError("ResearchRunner is not bound to a container")
        from app.research.orchestrator import ResearchOrchestrator

        orchestrator = ResearchOrchestrator(self._container)
        task = asyncio.create_task(orchestrator.execute(run_id), name=f"research-run-{run_id}")
        self._tasks[run_id] = task
        task.add_done_callback(lambda _t, rid=run_id: self._tasks.pop(rid, None))

    def is_running(self, run_id: str) -> bool:
        return run_id in self._tasks

    async def wait(self, run_id: str) -> None:
        task = self._tasks.get(run_id)
        if task is not None:
            await asyncio.shield(task)

    async def shutdown(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()
        for task in list(self._tasks.values()):
            try:
                await task
            except (asyncio.CancelledError, Exception):
                logger.info("research_task_stopped")
        self._tasks.clear()
