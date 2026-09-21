from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select

from app.models.instrument import Instrument
from app.repositories.base import BaseRepository


class InstrumentRepository(BaseRepository[Instrument]):
    model = Instrument

    async def get_by_symbol(self, symbol: str, exchange: str = "NSE") -> Instrument | None:
        stmt = select(Instrument).where(
            Instrument.symbol == symbol.upper(), Instrument.exchange == exchange.upper()
        )
        return await self.session.scalar(stmt)

    async def search(self, query: str = "", limit: int = 50) -> Sequence[Instrument]:
        stmt = select(Instrument).where(Instrument.is_active.is_(True))
        if query:
            like = f"%{query.upper()}%"
            stmt = stmt.where(or_(Instrument.symbol.like(like), Instrument.name.ilike(f"%{query}%")))
        return (await self.session.scalars(stmt.order_by(Instrument.symbol).limit(limit))).all()
