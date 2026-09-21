from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.enums import ACTIVE_ORDER_STATUSES, OrderSide, OrderStatus
from app.models.order import Order, OrderEvent
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def get_with_events(self, order_id: str) -> Order | None:
        stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.events))
        return await self.session.scalar(stmt.execution_options(populate_existing=True))

    async def get_for_update(self, order_id: str) -> Order | None:
        stmt = select(Order).where(Order.id == order_id).with_for_update()
        return await self.session.scalar(stmt.execution_options(populate_existing=True))

    async def list_orders(
        self,
        *,
        statuses: Iterable[OrderStatus] | None = None,
        symbol: str | None = None,
        strategy_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Order]:
        stmt = select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
        if statuses is not None:
            stmt = stmt.where(Order.status.in_(list(statuses)))
        if symbol:
            stmt = stmt.where(Order.symbol == symbol.upper())
        if strategy_id:
            stmt = stmt.where(Order.strategy_id == strategy_id)
        return (await self.session.scalars(stmt)).all()

    async def list_active(self) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(Order.status.in_(list(ACTIVE_ORDER_STATUSES)))
            .order_by(Order.created_at.asc())
        )
        return (await self.session.scalars(stmt)).all()

    async def has_active_order(
        self, symbol: str, strategy_id: str | None, side: OrderSide | None = None
    ) -> bool:
        stmt = select(Order.id).where(Order.symbol == symbol, Order.status.in_(list(ACTIVE_ORDER_STATUSES)))
        stmt = (
            stmt.where(Order.strategy_id == strategy_id)
            if strategy_id
            else stmt.where(Order.strategy_id.is_(None))
        )
        if side is not None:
            stmt = stmt.where(Order.side == side)
        return (await self.session.scalar(stmt.limit(1))) is not None

    async def add_event(self, event: OrderEvent) -> OrderEvent:
        self.session.add(event)
        await self.session.flush()
        return event
