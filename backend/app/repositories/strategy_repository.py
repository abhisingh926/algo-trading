from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, update

from app.domain.enums import StrategyStatus
from app.models.strategy import Strategy, StrategyParameter
from app.repositories.base import BaseRepository


class StrategyRepository(BaseRepository[Strategy]):
    model = Strategy

    async def get_by_name(self, name: str) -> Strategy | None:
        return await self.session.scalar(select(Strategy).where(Strategy.name == name))

    async def list_by_status(self, status: StrategyStatus) -> Sequence[Strategy]:
        return (await self.session.scalars(select(Strategy).where(Strategy.status == status))).all()

    async def count_by_status(self, status: StrategyStatus) -> int:
        return len(await self.list_by_status(status))

    async def replace_parameters(self, strategy: Strategy, parameters: dict[str, Any]) -> None:
        existing = {row.key: row for row in strategy.parameter_rows}
        for key, row in existing.items():
            if key not in parameters:
                strategy.parameter_rows.remove(row)
        for key, value in parameters.items():
            if key in existing:
                existing[key].value = value
            else:
                strategy.parameter_rows.append(StrategyParameter(key=key, value=value))
        await self.session.flush()

    async def stop_all(self) -> int:
        result = await self.session.execute(
            update(Strategy)
            .where(Strategy.status == StrategyStatus.RUNNING)
            .values(status=StrategyStatus.STOPPED)
        )
        return int(result.rowcount or 0)
