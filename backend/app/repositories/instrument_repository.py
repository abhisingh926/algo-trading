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

    async def find_by_isin(self, isin: str) -> Sequence[Instrument]:
        stmt = select(Instrument).where(Instrument.isin == isin, Instrument.is_active.is_(True))
        return (await self.session.scalars(stmt)).all()

    async def find_by_token(self, token: str, exchange: str = "NSE") -> Sequence[Instrument]:
        stmt = select(Instrument).where(
            Instrument.exchange_token == token,
            Instrument.exchange == exchange.upper(),
            Instrument.is_active.is_(True),
        )
        return (await self.session.scalars(stmt)).all()

    async def find_by_name(self, name: str) -> Sequence[Instrument]:
        stmt = select(Instrument).where(Instrument.name.ilike(name.strip()), Instrument.is_active.is_(True))
        return (await self.session.scalars(stmt)).all()
