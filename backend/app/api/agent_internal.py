from __future__ import annotations

import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.security import verify_internal_service_token
from backend.app.models import (
    AgentSettings,
    Call,
    CallEvent,
    Clinic,
    Doctor,
    FAQEntry,
    PhoneNumber,
    Treatment,
)
from backend.app.schemas import (
    CallCreate,
    CallEventIn,
    CallOut,
    ResolveClinicRequest,
    ResolveClinicResponse,
)

router = APIRouter(
    prefix="/internal/agent",
    tags=["Agent Internal"],
    dependencies=[Depends(verify_internal_service_token)],
)


@router.post("/resolve-clinic", response_model=ResolveClinicResponse)
async def resolve_clinic(req: ResolveClinicRequest, db: AsyncSession = Depends(get_db)) -> ResolveClinicResponse:
    """
    Called by LiveKit worker at the start of a call.
    Resolves dialed phone number (E.164) to clinic, and loads all context:
    working hours, doctor schedules, treatments, FAQs, and voice settings.
    """
    phone_res = await db.execute(
        select(PhoneNumber)
        .where(PhoneNumber.e164 == req.dialed_number, PhoneNumber.status == "active")
        .options(selectinload(PhoneNumber.clinic))
    )
    phone_record = phone_res.scalar_one_or_none()
    if not phone_record or not phone_record.clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not configured for this dialed phone number",
        )

    clinic = phone_record.clinic

    # Load agent settings
    settings_res = await db.execute(select(AgentSettings).where(AgentSettings.clinic_id == clinic.id))
    agent_settings = settings_res.scalar_one_or_none()

    # Load active doctors
    docs_res = await db.execute(
        select(Doctor).where(Doctor.clinic_id == clinic.id, Doctor.active == True)
    )
    doctors = [
        {"id": str(d.id), "name": d.name, "qualification": d.qualification, "specialties": d.specialties}
        for d in docs_res.scalars().all()
    ]

    # Load active treatments
    treatments_res = await db.execute(
        select(Treatment).where(Treatment.clinic_id == clinic.id, Treatment.active == True)
    )
    treatments = [
        {"id": str(t.id), "name_en": t.name_en, "name_ml": t.name_ml, "duration_minutes": t.duration_minutes}
        for t in treatments_res.scalars().all()
    ]

    # Load FAQs
    faq_res = await db.execute(
        select(FAQEntry).where(FAQEntry.clinic_id == clinic.id, FAQEntry.active == True)
    )
    faqs = [
        {"id": str(f.id), "question": f.question, "answer": f.answer, "language": f.language}
        for f in faq_res.scalars().all()
    ]

    return ResolveClinicResponse(
        clinic_id=clinic.id,
        clinic_name=clinic.name,
        timezone=clinic.timezone,
        working_hours=clinic.working_hours,
        languages=clinic.languages,
        fallback_phone=clinic.fallback_phone,
        greeting_ml=agent_settings.greeting_ml if agent_settings else None,
        greeting_en=agent_settings.greeting_en if agent_settings else None,
        providers=agent_settings.providers if agent_settings else {},
        doctors=doctors,
        treatments=treatments,
        faqs=faqs,
    )


@router.post("/calls", response_model=CallOut)
async def create_call(req: CallCreate, db: AsyncSession = Depends(get_db)) -> CallOut:
    """Initialize a call record upon caller connection."""
    call = Call(
        clinic_id=req.clinic_id,
        caller_number=req.caller_number,
        language=req.language or "ml-IN",
        started_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call


@router.post("/call-events", status_code=status.HTTP_201_CREATED)
async def log_call_event(req: CallEventIn, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Log an audit or lifecycle event for an active call."""
    event = CallEvent(
        clinic_id=req.clinic_id,
        call_id=req.call_id,
        type=req.type,
        data=req.data or {},
    )
    db.add(event)
    await db.commit()
    return {"status": "logged"}
