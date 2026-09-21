from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select, update

from app.domain.enums import BrokerEnvironment, BrokerType
from app.models.broker import BrokerAccount
from app.repositories.base import BaseRepository


class BrokerRepository(BaseRepository[BrokerAccount]):
    model = BrokerAccount

    async def list_accounts(self) -> Sequence[BrokerAccount]:
        stmt = select(BrokerAccount).order_by(BrokerAccount.created_at.asc())
        return (await self.session.scalars(stmt)).all()

    async def find(
        self, broker_type: BrokerType | None = None, environment: BrokerEnvironment | None = None
    ) -> Sequence[BrokerAccount]:
        stmt = select(BrokerAccount).where(BrokerAccount.is_active.is_(True))
        if broker_type is not None:
            stmt = stmt.where(BrokerAccount.broker_type == broker_type)
        if environment is not None:
            stmt = stmt.where(BrokerAccount.environment == environment)
        stmt = stmt.order_by(BrokerAccount.is_default.desc(), BrokerAccount.created_at.asc())
        return (await self.session.scalars(stmt)).all()

    async def clear_default(self, environment: BrokerEnvironment) -> None:
        await self.session.execute(
            update(BrokerAccount).where(BrokerAccount.environment == environment).values(is_default=False)
        )
