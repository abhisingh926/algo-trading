"""Async SQLAlchemy engine/session management + shared column types."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC (MySQL DATETIME has no tz) and always returns tz-aware UTC datetimes."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime())

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Database:
    """Owns the engine and session factory; one instance per process (or per test)."""

    def __init__(self, url: str, echo: bool = False) -> None:
        kwargs: dict[str, Any] = {"echo": echo}
        if url.startswith("sqlite"):
            kwargs.update(poolclass=StaticPool, connect_args={"check_same_thread": False})
        else:
            kwargs.update(pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=20)
        self.engine: AsyncEngine = create_async_engine(url, **kwargs)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Request-scoped session: commit on success, rollback on error."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def ping(self) -> bool:
        from sqlalchemy import text

        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def create_all(self) -> None:
        import app.models  # noqa: F401  (register mappers)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
