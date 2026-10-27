from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models import Call, User
from backend.app.services.audit_service import record_audit_event
from backend.app.services.storage_service import storage_service

router = APIRouter(prefix="/calls", tags=["Calls & Audio Recordings"])


@router.get("", response_model=list[dict[str, Any]])
async def list_calls(
    current_user: User = Depends(require_roles("staff", "doctor", "clinic_admin")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List calls for the authenticated user's clinic tenant."""
    query = select(Call).where(Call.clinic_id == current_user.clinic_id).order_by(desc(Call.started_at)).limit(50)
    res = await db.execute(query)
    calls = res.scalars().all()

    return [
        {
            "id": str(c.id),
            "clinic_id": str(c.clinic_id),
            "patient_id": str(c.patient_id) if c.patient_id else None,
            "caller_number": c.caller_number,
            "language": c.language,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "duration_sec": c.duration_sec,
            "outcome": c.outcome,
            "summary": c.summary,
            "has_recording": bool(c.recording_key),
        }
        for c in calls
    ]


@router.get("/{call_id}", response_model=dict[str, Any])
async def get_call_detail(
    call_id: uuid.UUID,
    current_user: User = Depends(require_roles("staff", "doctor", "clinic_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve call details and transcript. Automatically records an audit log entry."""
    query = select(Call).where(Call.id == call_id, Call.clinic_id == current_user.clinic_id)
    res = await db.execute(query)
    call = res.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call record not found")

    await record_audit_event(
        db,
        action="view_call_transcript",
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        record=f"Call {call.id}",
    )
    await db.commit()

    return {
        "id": str(call.id),
        "clinic_id": str(call.clinic_id),
        "patient_id": str(call.patient_id) if call.patient_id else None,
        "caller_number": call.caller_number,
        "language": call.language,
        "started_at": call.started_at.isoformat() if call.started_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "duration_sec": call.duration_sec,
        "outcome": call.outcome,
        "summary": call.summary,
        "transcript": call.transcript,
        "has_recording": bool(call.recording_key),
    }


@router.get("/{call_id}/recording-link", response_model=dict[str, str])
async def get_recording_signed_link(
    call_id: uuid.UUID,
    current_user: User = Depends(require_roles("staff", "doctor", "clinic_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Generate a 15-minute short-lived signed URL for audio playback.
    Strictly tenant-scoped with immutable audit logging.
    """
    query = select(Call).where(Call.id == call_id, Call.clinic_id == current_user.clinic_id)
    res = await db.execute(query)
    call = res.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call record not found")

    if not call.recording_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not available or was purged per data retention policy",
        )

    signed_url = await storage_service.generate_signed_url(call.recording_key, expires_seconds=900)

    await record_audit_event(
        db,
        action="listen_call_recording",
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        record=f"Call {call.id} recording accessed",
    )
    await db.commit()

    return {
        "call_id": str(call.id),
        "signed_url": signed_url,
        "expires_in_seconds": "900",
    }
