from __future__ import annotations

import datetime
import uuid
from typing import Any
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Appointment, Clinic, Doctor, Patient
from backend.app.services.slot_service import get_available_slots


class BookingValidationError(Exception):
    """Raised when a booking request fails business validation rules."""

    def __init__(self, message: str, corrective_suggestion: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.corrective_suggestion = corrective_suggestion


async def book_appointment_guarded(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    starts_at: datetime.datetime,
    treatment_id: uuid.UUID | None = None,
    visit_type: str = "in_person",
    reason: str | None = None,
    call_id: uuid.UUID | None = None,
) -> Appointment:
    """
    Guarded appointment booking with strict transactional validation:
    1. Validates patient belongs to clinic.
    2. Validates doctor belongs to clinic and is active.
    3. Re-validates slot availability at write time.
    4. Enforces database row lock to prevent race conditions / double bookings.
    """
    # 1. Validate Patient
    pat_res = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.clinic_id == clinic_id)
    )
    patient = pat_res.scalar_one_or_none()
    if not patient:
        raise BookingValidationError("Patient record not found for this clinic.")

    # 2. Validate Doctor
    doc_res = await db.execute(
        select(Doctor).where(Doctor.id == doctor_id, Doctor.clinic_id == clinic_id, Doctor.active == True)
    )
    doctor = doc_res.scalar_one_or_none()
    if not doctor:
        raise BookingValidationError("Requested doctor is not available or inactive.")

    # 3. Timezone conversion and past-time rejection
    clinic_res = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_res.scalar_one_or_none()
    tz = ZoneInfo(clinic.timezone if clinic else "Asia/Kolkata")

    # Ensure starts_at is timezone-aware
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=tz)
    else:
        starts_at = starts_at.astimezone(tz)

    now_tz = datetime.datetime.now(tz)
    if starts_at <= now_tz:
        raise BookingValidationError(
            "Cannot book an appointment in the past.",
            corrective_suggestion="Please choose an upcoming date and time.",
        )

    # 4. Check for double booking race conditions inside transaction
    conflict_stmt = select(Appointment).where(
        Appointment.clinic_id == clinic_id,
        Appointment.doctor_id == doctor_id,
        Appointment.starts_at == starts_at,
        Appointment.status != "cancelled",
    ).with_for_update()

    conflict_res = await db.execute(conflict_stmt)
    existing_conflict = conflict_res.scalar_one_or_none()
    if existing_conflict:
        # Check nearby available slots for a helpful corrective suggestion
        nearby = await get_available_slots(db, clinic_id, starts_at.date(), doctor_id)
        suggested_time = nearby[0]["time_str"] if nearby else "another day"
        raise BookingValidationError(
            f"Doctor {doctor.name} is already booked at {starts_at.strftime('%I:%M %p')}.",
            corrective_suggestion=f"The next available time with Dr. {doctor.name} is {suggested_time}.",
        )

    # 5. Calculate slot end time (default 15 minutes unless specified by treatment)
    ends_at = starts_at + datetime.timedelta(minutes=15)

    appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        treatment_id=treatment_id,
        visit_type=visit_type,
        reason=reason,
        starts_at=starts_at,
        ends_at=ends_at,
        status="booked",
        source="voice_agent",
        call_id=call_id,
    )
    db.add(appointment)

    try:
        await db.commit()
        await db.refresh(appointment)
        return appointment
    except IntegrityError:
        await db.rollback()
        raise BookingValidationError(
            "Slot conflict occurred while completing the booking. Please choose another slot."
        )


async def reschedule_appointment_guarded(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    appointment_id: uuid.UUID,
    new_starts_at: datetime.datetime,
    caller_phone: str | None = None,
) -> Appointment:
    """Reschedule an existing appointment, verifying patient ownership and slot availability."""
    appt_stmt = (
        select(Appointment)
        .join(Patient, Appointment.patient_id == Patient.id)
        .where(Appointment.id == appointment_id, Appointment.clinic_id == clinic_id)
    )
    if caller_phone:
        appt_stmt = appt_stmt.where(Patient.phone == caller_phone)

    appt_res = await db.execute(appt_stmt)
    appointment = appt_res.scalar_one_or_none()
    if not appointment:
        raise BookingValidationError("Appointment not found or does not belong to this caller.")

    if appointment.status == "cancelled":
        raise BookingValidationError("Cannot reschedule an already cancelled appointment.")

    # Re-book with new start time
    clinic_res = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_res.scalar_one_or_none()
    tz = ZoneInfo(clinic.timezone if clinic else "Asia/Kolkata")

    if new_starts_at.tzinfo is None:
        new_starts_at = new_starts_at.replace(tzinfo=tz)
    else:
        new_starts_at = new_starts_at.astimezone(tz)

    now_tz = datetime.datetime.now(tz)
    if new_starts_at <= now_tz:
        raise BookingValidationError("New appointment time cannot be in the past.")

    # Check conflict
    conflict_stmt = select(Appointment).where(
        Appointment.clinic_id == clinic_id,
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.starts_at == new_starts_at,
        Appointment.id != appointment.id,
        Appointment.status != "cancelled",
    )
    conflict_res = await db.execute(conflict_stmt)
    if conflict_res.scalar_one_or_none():
        raise BookingValidationError("The requested reschedule slot is already booked.")

    duration = appointment.ends_at - appointment.starts_at
    appointment.starts_at = new_starts_at
    appointment.ends_at = new_starts_at + duration
    appointment.status = "rescheduled"

    await db.commit()
    await db.refresh(appointment)
    return appointment


async def cancel_appointment_guarded(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    appointment_id: uuid.UUID,
    caller_phone: str | None = None,
) -> Appointment:
    """Cancel an existing appointment after ownership verification."""
    appt_stmt = (
        select(Appointment)
        .join(Patient, Appointment.patient_id == Patient.id)
        .where(Appointment.id == appointment_id, Appointment.clinic_id == clinic_id)
    )
    if caller_phone:
        appt_stmt = appt_stmt.where(Patient.phone == caller_phone)

    appt_res = await db.execute(appt_stmt)
    appointment = appt_res.scalar_one_or_none()
    if not appointment:
        raise BookingValidationError("Appointment not found or does not belong to this caller.")

    appointment.status = "cancelled"
    await db.commit()
    await db.refresh(appointment)
    return appointment
