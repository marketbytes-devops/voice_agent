from __future__ import annotations

import datetime
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import AuditLog

logger = logging.getLogger("clinicvoice")


async def record_audit_event(
    db: AsyncSession,
    action: str,
    clinic_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    record: str | None = None,
) -> AuditLog:
    """
    Creates an immutable audit log entry for security and regulatory compliance (DPDP Act).
    Audit logs record staff access to patient health data, audio recordings, and lifecycle purges.
    """
    entry = AuditLog(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        user_id=user_id,
        action=action,
        record=record,
        at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(entry)
    await db.flush()
    logger.info("AUDIT: action=%s clinic_id=%s user_id=%s record=%s", action, clinic_id, user_id, record)
    return entry
