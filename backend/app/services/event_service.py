"""Records trading events twice: structured log line (for SigNoz/OTel later) + system_events row (for the UI)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.logging import get_logger, log_event, redact
from app.domain.enums import EventLevel
from app.models.event import SystemEvent
from app.repositories.event_repository import EventRepository

logger = get_logger("trading.events")
_LEVELS = {
    EventLevel.INFO: logging.INFO,
    EventLevel.WARNING: logging.WARNING,
    EventLevel.ERROR: logging.ERROR,
}


class EventService:
    def __init__(self, repository: EventRepository) -> None:
        self.repository = repository

    async def record(
        self,
        event_type: str,
        message: str = "",
        *,
        level: EventLevel = EventLevel.INFO,
        strategy_id: str | None = None,
        order_id: str | None = None,
        symbol: str | None = None,
        **payload: Any,
    ) -> None:
        safe_payload = redact(payload) or None
        log_event(
            logger,
            event_type,
            _LEVELS[level],
            detail=message,
            strategy_id=strategy_id,
            order_id=order_id,
            symbol=symbol,
            **(safe_payload or {}),
        )
        await self.repository.create(
            SystemEvent(
                event_type=event_type,
                level=level,
                message=message,
                payload=safe_payload,
                strategy_id=strategy_id,
                order_id=order_id,
                symbol=symbol,
            )
        )

    async def list_events(self, **filters: Any) -> Any:
        return await self.repository.list_events(**filters)
