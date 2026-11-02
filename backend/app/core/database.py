from __future__ import annotations

import re
import urllib.parse
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
    """Lazy initialize async database engine with robust URI normalization and IPv4 pooler fallback."""
    global _engine
    if _engine is None:
        raw_url = str(settings.DATABASE_URL).strip()
        # Ensure async driver for SQLAlchemy 2.0 + asyncpg
        if raw_url.startswith("postgresql://"):
            raw_url = "postgresql+asyncpg://" + raw_url[len("postgresql://"):]
        elif raw_url.startswith("postgres://"):
            raw_url = "postgresql+asyncpg://" + raw_url[len("postgres://"):]

        # Handle unescaped '@' in password if present
        try:
            proto, sep, rest = raw_url.partition("://")
            if "@" in rest:
                user_pass, _, host_db = rest.rpartition("@")
                if ":" in user_pass:
                    user, _, pwd = user_pass.partition(":")
                    clean_pwd = urllib.parse.quote(urllib.parse.unquote(pwd), safe="")
                    raw_url = f"{proto}://{user}:{clean_pwd}@{host_db}"
        except Exception:
            pass

        # Resolve Supabase IPv6 direct domain to IPv4 Pooler for cloud environments (like Render Free tier without IPv6 egress)
        try:
            m = re.search(r"db\.([a-zA-Z0-9_-]+)\.supabase\.co", raw_url)
            if m:
                project_ref = m.group(1)
                raw_url = raw_url.replace(f"db.{project_ref}.supabase.co", "aws-0-ap-south-1.pooler.supabase.com")
                if "://postgres:" in raw_url:
                    raw_url = raw_url.replace("://postgres:", f"://postgres.{project_ref}:", 1)
        except Exception:
            pass

        _engine = create_async_engine(
            raw_url,
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
            str_clinic_id = str(clinic_id)
            await session.execute(text(f"SET LOCAL app.clinic_id = '{str_clinic_id}'"))
        try:
            yield session
        finally:
            await session.close()
