from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.domain.enums import SignalStatus
from app.domain.types import SignalResult
from app.models.signal import Signal
from app.models.strategy import Strategy
from app.repositories.signal_repository import SignalRepository
from app.services.event_service import EventService


class SignalService:
    def __init__(self, signals: SignalRepository, events: EventService) -> None:
        self.signals = signals
        self.events = events

    async def list_recent(self, strategy_id: str | None = None, limit: int = 50) -> Sequence[Signal]:
        return await self.signals.list_recent(strategy_id, limit)

    async def record(self, strategy: Strategy, result: SignalResult, candle_time: datetime) -> Signal:
        signal = await self.signals.create(
            Signal(
                strategy_id=strategy.id,
                strategy=strategy,
                symbol=strategy.symbol,
                exchange=strategy.exchange,
                signal_type=result.type,
                price=result.price,
                reason=result.reason,
                indicators=result.indicators,
                candle_time=candle_time,
            )
        )
        await self.events.record(
            "signal_generated",
            f"{strategy.name}: {result.type.value} {strategy.symbol} @ {result.price:.2f} - {result.reason}",
            strategy_id=strategy.id,
            symbol=strategy.symbol,
            signal_type=result.type.value,
            price=result.price,
            **result.indicators,
        )
        return signal

    async def resolve(
        self, signal: Signal, status: SignalStatus, reason: str | None = None, order_id: str | None = None
    ) -> None:
        await self.signals.update(
            signal, {"status": status, "status_reason": reason, "order_id": order_id or signal.order_id}
        )
