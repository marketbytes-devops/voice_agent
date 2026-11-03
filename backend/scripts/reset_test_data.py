"""
Tenant-scoped database reset script for ClinicVoice testing.
Purges test calls, test appointments, test patients, and callback tasks
so counters reset cleanly to 0 while preserving clinic, doctor, and treatment configs.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from sqlalchemy import text
from backend.app.core.database import get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clinicvoice")

DEFAULT_CLINIC_ID = uuid.UUID("c5313bf1-67c2-4794-a34c-6629f342358c")


async def reset_test_data() -> None:
    factory = get_session_factory()
    clinic_id_str = str(DEFAULT_CLINIC_ID)

    logger.info("Connecting to Supabase to reset test data for clinic %s...", clinic_id_str)
    async with factory() as session:
        # Enable tenant RLS context for safety
        await session.execute(text(f"SET LOCAL app.clinic_id = '{clinic_id_str}'"))

        # 1. Delete appointment records
        res_appts = await session.execute(
            text(f"DELETE FROM appointments WHERE clinic_id = '{clinic_id_str}'")
        )
        logger.info("Purged %d test appointments.", res_appts.rowcount)

        # 2. Delete callback tasks
        res_tasks = await session.execute(
            text(f"DELETE FROM callback_tasks WHERE clinic_id = '{clinic_id_str}'")
        )
        logger.info("Purged %d test callback tasks.", res_tasks.rowcount)

        # 3. Delete call records
        res_calls = await session.execute(
            text(f"DELETE FROM calls WHERE clinic_id = '{clinic_id_str}'")
        )
        logger.info("Purged %d test calls.", res_calls.rowcount)

        # 4. Delete patient records
        res_pats = await session.execute(
            text(f"DELETE FROM patients WHERE clinic_id = '{clinic_id_str}'")
        )
        logger.info("Purged %d test patients.", res_pats.rowcount)

        # 5. Delete consent logs
        res_consent = await session.execute(
            text(f"DELETE FROM consent_log WHERE clinic_id = '{clinic_id_str}'")
        )
        logger.info("Purged %d consent logs.", res_consent.rowcount)

        await session.commit()
        logger.info("Successfully reset all test data for ClinicVoice! All counters are now at 0.")


if __name__ == "__main__":
    asyncio.run(reset_test_data())
