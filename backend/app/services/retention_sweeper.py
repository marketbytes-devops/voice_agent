from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import sys
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_session_factory
from backend.app.models import Call, CallEvent
from backend.app.services.audit_service import record_audit_event
from backend.app.services.storage_service import storage_service

logger = logging.getLogger("clinicvoice")


async def purge_expired_recordings(
    db: AsyncSession,
    retention_days: int | None = None,
    clinic_id: uuid.UUID | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Scans for call recordings older than the retention threshold and securely purges
    the audio files from storage while preserving call metadata, timestamps, and transcripts.
    Adheres to DPDP Act 2023 storage limitation and data minimization principles.
    """
    days = retention_days if retention_days is not None else settings.RECORDING_RETENTION_DAYS
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

    query = select(Call).where(Call.started_at < cutoff, Call.recording_key.isnot(None))
    if clinic_id:
        query = query.where(Call.clinic_id == clinic_id)

    res = await db.execute(query)
    expired_calls = res.scalars().all()

    purged_count = 0
    failed_count = 0
    purged_call_ids: list[str] = []

    logger.info(
        "RETENTION SWEEPER: Found %d recordings older than %s (retention_days=%d, dry_run=%s)",
        len(expired_calls),
        cutoff.isoformat(),
        days,
        dry_run,
    )

    if dry_run:
        return {
            "found_count": len(expired_calls),
            "purged_count": 0,
            "failed_count": 0,
            "cutoff_date": cutoff.isoformat(),
            "dry_run": True,
        }

    for call in expired_calls:
        old_key = call.recording_key
        if not old_key:
            continue

        try:
            success = await storage_service.delete_recording(old_key)
            if success:
                call.recording_key = None
                event = CallEvent(
                    id=uuid.uuid4(),
                    clinic_id=call.clinic_id,
                    call_id=call.id,
                    at=datetime.datetime.now(datetime.timezone.utc),
                    type="recording_purged",
                    data={
                        "purged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "previous_key": old_key,
                        "retention_days": days,
                    },
                )
                db.add(event)
                purged_count += 1
                purged_call_ids.append(str(call.id))
            else:
                failed_count += 1
        except Exception as e:
            logger.error("Failed to purge recording for call %s: %s", call.id, e)
            failed_count += 1

    if purged_count > 0:
        await record_audit_event(
            db,
            action="retention_sweeper_purge",
            clinic_id=clinic_id,
            record=f"Purged {purged_count} recordings older than {days} days",
        )
        await db.commit()

    return {
        "found_count": len(expired_calls),
        "purged_count": purged_count,
        "failed_count": failed_count,
        "purged_call_ids": purged_call_ids,
        "cutoff_date": cutoff.isoformat(),
        "dry_run": False,
    }


async def run_cli() -> None:
    parser = argparse.ArgumentParser(description="ClinicVoice Audio Retention Sweeper")
    parser.add_argument("--days", type=int, default=None, help="Retention period in days")
    parser.add_argument("--clinic-id", type=str, default=None, help="Specific clinic UUID")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without deleting")
    args = parser.parse_args()

    c_id = uuid.UUID(args.clinic_id) if args.clinic_id else None

    factory = get_session_factory()
    async with factory() as session:
        result = await purge_expired_recordings(
            db=session,
            retention_days=args.days,
            clinic_id=c_id,
            dry_run=args.dry_run,
        )
        print("Retention Sweeper Result:")
        for k, v in result.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(run_cli())
