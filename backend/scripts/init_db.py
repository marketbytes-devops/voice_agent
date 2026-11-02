from __future__ import annotations

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import settings
from backend.app.core.database import Base
import backend.app.models  # Ensure all SQLAlchemy models are registered

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clinicvoice")

RLS_TABLES = [
    "patients",
    "doctors",
    "doctor_schedules",
    "doctor_leave",
    "treatments",
    "faq_entries",
    "appointments",
    "calls",
    "call_events",
    "callback_tasks",
    "consent_log",
    "messages",
    "agent_settings",
    "phone_numbers",
]


async def init_database() -> None:
    logger.info("Initializing database on: %s", settings.DATABASE_URL.split("@")[-1])
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        logger.info("Creating all tables via SQLAlchemy metadata...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All 18 tables created successfully.")

        # Enable Row-Level Security (RLS) on clinic-owned tables
        logger.info("Enforcing PostgreSQL Row-Level Security (RLS)...")
        for table_name in RLS_TABLES:
            try:
                await conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
                await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name};"))
                await conn.execute(
                    text(
                        f"""
                        CREATE POLICY tenant_isolation_{table_name} ON {table_name}
                        AS RESTRICTIVE
                        USING (clinic_id = NULLIF(current_setting('app.clinic_id', true), '')::uuid);
                        """
                    )
                )
                logger.info("Enabled RLS policy on table: %s", table_name)
            except Exception as e:
                logger.warning("Could not apply RLS on %s: %s", table_name, e)

        # Create alembic_version table to track migration state
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                );
                """
            )
        )
        await conn.execute(text("DELETE FROM alembic_version;"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema_and_rls');"))
        logger.info("Recorded alembic revision '0001_initial_schema_and_rls'.")

    await engine.dispose()
    logger.info("Database schema and RLS initialization completed successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())

