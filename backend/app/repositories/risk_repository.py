from __future__ import annotations

from sqlalchemy import select

from app.models.risk import RiskConfiguration
from app.repositories.base import BaseRepository


class RiskRepository(BaseRepository[RiskConfiguration]):
    model = RiskConfiguration

    async def get_active(self) -> RiskConfiguration | None:
        stmt = select(RiskConfiguration).order_by(RiskConfiguration.created_at.asc()).limit(1)
        return await self.session.scalar(stmt)
