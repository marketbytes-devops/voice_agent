from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models."""
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazy initialize async database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazy initialize session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db(clinic_id: uuid.UUID | str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency with Row-Level Security (RLS) enforcement.
    If clinic_id is provided, sets PostgreSQL local setting 'app.clinic_id'
    so that all tenant isolation RLS policies are activated for the transaction.
    """
    factory = get_session_factory()
    async with factory() as session:
        if clinic_id:
            # Set PostgreSQL session-local variable for RLS
            str_clinic_id = str(clinic_id)
            await session.execute(text(f"SET LOCAL app.clinic_id = '{str_clinic_id}'"))
        try:
            yield session
        finally:
            await session.close()
