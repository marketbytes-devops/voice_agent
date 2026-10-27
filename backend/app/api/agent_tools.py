from __future__ import annotations

import datetime
import uuid
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import verify_internal_service_token
from backend.app.models import (
    CallbackTask,
    Clinic,
    FAQEntry,
    Patient,
    Treatment,
)
from backend.app.services.booking_service import (
    BookingValidationError,
    book_appointment_guarded,
    cancel_appointment_guarded,
    reschedule_appointment_guarded,
)
from backend.app.services.slot_service import get_available_slots

router = APIRouter(
    prefix="/internal/agent/tools",
    tags=["Agent Tools Internal"],
    dependencies=[Depends(verify_internal_service_token)],
)


# Request schemas for tools
class FindOrCreatePatientRequest(BaseModel):
    clinic_id: uuid.UUID
    name: str
    phone: str
    age: int | None = None
    gender: str | None = None
    place: str | None = None
    preferred_language: str = "ml-IN"
    confirmed: bool = False


class GetFreeSlotsRequest(BaseModel):
    clinic_id: uuid.UUID
    doctor_id: uuid.UUID | None = None
    date: str  # YYYY-MM-DD


class BookAppointmentRequest(BaseModel):
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    start: str  # ISO 8601
    treatment_id: uuid.UUID | None = None
    reason: str | None = None
    visit_type: str = "in_person"
    call_id: uuid.UUID | None = None


class RescheduleAppointmentRequest(BaseModel):
    clinic_id: uuid.UUID
    appointment_id: uuid.UUID
    new_start: str  # ISO 8601
    caller_phone: str | None = None


class CancelAppointmentRequest(BaseModel):
    clinic_id: uuid.UUID
    appointment_id: uuid.UUID
    caller_phone: str | None = None


class GetClinicInfoRequest(BaseModel):
    clinic_id: uuid.UUID
    topic: str | None = None
    question: str


class TransferCallRequest(BaseModel):
    clinic_id: uuid.UUID
    reason: str


class RequestCallbackRequest(BaseModel):
    clinic_id: uuid.UUID
    call_id: uuid.UUID | None = None
    patient_id: uuid.UUID | None = None
    reason: str
    preferred_time: str | None = None


class EscalateEmergencyRequest(BaseModel):
    clinic_id: uuid.UUID
    call_id: uuid.UUID | None = None
    summary: str


# 1. find_or_create_patient
@router.post("/find-or-create-patient")
async def find_or_create_patient(
    req: FindOrCreatePatientRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    if not req.confirmed:
        return {
            "success": False,
            "message": "Patient details must be read back and explicitly confirmed by caller before saving.",
        }

    # Match by phone within clinic tenant
    stmt = select(Patient).where(Patient.clinic_id == req.clinic_id, Patient.phone == req.phone)
    res = await db.execute(stmt)
    patient = res.scalar_one_or_none()

    if patient:
        return {
            "success": True,
            "patient_id": str(patient.id),
            "is_returning": True,
            "name": patient.name,
            "phone": patient.phone,
        }

    # Create new patient
    new_patient = Patient(
        clinic_id=req.clinic_id,
        name=req.name,
        phone=req.phone,
        age=req.age,
        gender=req.gender,
        place=req.place,
        preferred_language=req.preferred_language,
    )
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)

    return {
        "success": True,
        "patient_id": str(new_patient.id),
        "is_returning": False,
        "name": new_patient.name,
        "phone": new_patient.phone,
    }


# 2. get_free_slots
@router.post("/get-free-slots")
async def get_free_slots(
    req: GetFreeSlotsRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        target_date = datetime.date.fromisoformat(req.date)
    except ValueError:
        return {"success": False, "message": "Invalid date format. Use YYYY-MM-DD."}

    slots = await get_available_slots(db, req.clinic_id, target_date, req.doctor_id)
    return {
        "success": True,
        "date": req.date,
        "slot_count": len(slots),
        "slots": slots,
    }


# 3. book_appointment
@router.post("/book-appointment")
async def book_appointment(
    req: BookAppointmentRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        starts_at = datetime.datetime.fromisoformat(req.start)
    except ValueError:
        return {"success": False, "message": "Invalid start datetime format. Must be ISO 8601."}

    try:
        appt = await book_appointment_guarded(
            db=db,
            clinic_id=req.clinic_id,
            patient_id=req.patient_id,
            doctor_id=req.doctor_id,
            starts_at=starts_at,
            treatment_id=req.treatment_id,
            visit_type=req.visit_type,
            reason=req.reason,
            call_id=req.call_id,
        )
        return {
            "success": True,
            "appointment_id": str(appt.id),
            "starts_at": appt.starts_at.isoformat(),
            "status": appt.status,
            "message": "Appointment booked successfully.",
        }
    except BookingValidationError as e:
        return {
            "success": False,
            "error": e.message,
            "corrective_suggestion": e.corrective_suggestion,
        }


# 4. reschedule_appointment
@router.post("/reschedule-appointment")
async def reschedule_appointment(
    req: RescheduleAppointmentRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        new_starts_at = datetime.datetime.fromisoformat(req.new_start)
    except ValueError:
        return {"success": False, "message": "Invalid new_start datetime format."}

    try:
        appt = await reschedule_appointment_guarded(
            db=db,
            clinic_id=req.clinic_id,
            appointment_id=req.appointment_id,
            new_starts_at=new_starts_at,
            caller_phone=req.caller_phone,
        )
        return {
            "success": True,
            "appointment_id": str(appt.id),
            "new_starts_at": appt.starts_at.isoformat(),
            "message": "Appointment rescheduled successfully.",
        }
    except BookingValidationError as e:
        return {"success": False, "error": e.message}


# 5. cancel_appointment
@router.post("/cancel-appointment")
async def cancel_appointment(
    req: CancelAppointmentRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        appt = await cancel_appointment_guarded(
            db=db,
            clinic_id=req.clinic_id,
            appointment_id=req.appointment_id,
            caller_phone=req.caller_phone,
        )
        return {
            "success": True,
            "appointment_id": str(appt.id),
            "status": "cancelled",
            "message": "Appointment cancelled successfully.",
        }
    except BookingValidationError as e:
        return {"success": False, "error": e.message}


# 6. get_clinic_info
@router.post("/get-clinic-info")
async def get_clinic_info(
    req: GetClinicInfoRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    # Query approved FAQs
    q = req.question.lower()
    faq_stmt = select(FAQEntry).where(FAQEntry.clinic_id == req.clinic_id, FAQEntry.active == True)
    faq_res = await db.execute(faq_stmt)
    faqs = list(faq_res.scalars().all())

    for f in faqs:
        if any(word in f.question.lower() for word in q.split() if len(word) > 3):
            return {"found": True, "answer": f.answer, "source": "faq"}

    # Query approved treatments
    treat_stmt = select(Treatment).where(Treatment.clinic_id == req.clinic_id, Treatment.active == True)
    treat_res = await db.execute(treat_stmt)
    treatments = list(treat_res.scalars().all())

    for t in treatments:
        name_en = (t.name_en or "").lower()
        name_ml = (t.name_ml or "").lower()
        if name_en in q or (name_ml and name_ml in req.question):
            desc = t.description_ml or t.description_en or f"{t.name_en} treatment is available."
            return {"found": True, "answer": desc, "source": "treatment"}

    return {
        "found": False,
        "message": "This specific question is not in our approved knowledge base. Offer a staff callback.",
    }


# 7. transfer_call
@router.post("/transfer-call")
async def transfer_call(
    req: TransferCallRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    clinic_res = await db.execute(select(Clinic).where(Clinic.id == req.clinic_id))
    clinic = clinic_res.scalar_one_or_none()
    if not clinic:
        return {"can_transfer": False, "fallback": "create_callback", "reason": "Clinic not found"}

    # In production, check current time against clinic.working_hours
    return {
        "can_transfer": True,
        "transfer_to": clinic.fallback_phone or "front_desk",
        "reason": req.reason,
    }


# 8. request_callback
@router.post("/request-callback")
async def request_callback(
    req: RequestCallbackRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    task = CallbackTask(
        clinic_id=req.clinic_id,
        call_id=req.call_id,
        patient_id=req.patient_id,
        reason=req.reason,
        preferred_time=req.preferred_time,
        status="open",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "success": True,
        "task_id": str(task.id),
        "message": "Callback task created for clinic reception staff.",
    }


# 9. escalate_emergency
@router.post("/escalate-emergency")
async def escalate_emergency(
    req: EscalateEmergencyRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    # Log emergency task
    task = CallbackTask(
        clinic_id=req.clinic_id,
        call_id=req.call_id,
        reason=f"EMERGENCY: {req.summary}",
        status="urgent_open",
    )
    db.add(task)
    await db.commit()

    return {
        "success": True,
        "disclaimer_ml": "ഇതൊരു അത്യാഹിത സാഹചര്യമാണെങ്കിൽ ദയവായി തൊട്ടടുത്തുള്ള ആശുപത്രിയിലെ എമർജൻസി വിഭാഗവുമായി ഉടൻ ബന്ധപ്പെടുക.",
        "disclaimer_en": "If this is a medical emergency, please immediately contact the nearest hospital emergency department.",
        "action": "transfer_to_emergency_staff",
    }
