from __future__ import annotations

import datetime
import uuid
from typing import Any
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Appointment, Clinic, Doctor, DoctorLeave, DoctorSchedule


class SlotCalculationError(Exception):
    """Raised when slot calculation fails or encounters invalid input."""
    pass


async def get_available_slots(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    target_date: datetime.date,
    doctor_id: uuid.UUID | None = None,
    treatment_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """
    Calculate real available appointment slots for a given date.
    Strictly accounts for:
    1. Clinic timezone (Asia/Kolkata)
    2. Rejection of past dates/times
    3. Doctor weekday schedules (start_time, end_time, slot_minutes)
    4. Doctor break intervals (break_start, break_end)
    5. Approved doctor leave (starts_at, ends_at)
    6. Existing bookings (excluding cancelled appointments)
    """
    # 1. Resolve clinic timezone
    clinic_res = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_res.scalar_one_or_none()
    tz_str = clinic.timezone if clinic else "Asia/Kolkata"
    tz = ZoneInfo(tz_str)

    now_tz = datetime.datetime.now(tz)
    today_tz = now_tz.date()

    # Reject past dates
    if target_date < today_tz:
        return []

    # 2. Query active doctors for clinic
    doc_stmt = select(Doctor).where(Doctor.clinic_id == clinic_id, Doctor.active == True)
    if doctor_id:
        doc_stmt = doc_stmt.where(Doctor.id == doctor_id)

    doc_res = await db.execute(doc_stmt)
    doctors = list(doc_res.scalars().all())
    if not doctors:
        return []

    available_slots: list[dict[str, Any]] = []

    # Weekday in Python: Monday is 0, Sunday is 6
    target_weekday = target_date.weekday()

    for doctor in doctors:
        # 3. Check if doctor is on approved leave for this date
        start_of_day = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=tz)
        end_of_day = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=tz)

        leave_stmt = select(DoctorLeave).where(
            DoctorLeave.clinic_id == clinic_id,
            DoctorLeave.doctor_id == doctor.id,
            DoctorLeave.starts_at <= end_of_day,
            DoctorLeave.ends_at >= start_of_day,
        )
        leave_res = await db.execute(leave_stmt)
        active_leaves = list(leave_res.scalars().all())
        if active_leaves:
            # Doctor is on leave for the entire/part day
            continue

        # 4. Check doctor weekly schedule for this weekday
        sched_stmt = select(DoctorSchedule).where(
            DoctorSchedule.clinic_id == clinic_id,
            DoctorSchedule.doctor_id == doctor.id,
            DoctorSchedule.weekday == target_weekday,
        )
        sched_res = await db.execute(sched_stmt)
        schedules = list(sched_res.scalars().all())
        if not schedules:
            continue

        # 5. Fetch existing booked appointments for doctor on target date
        appt_stmt = select(Appointment).where(
            Appointment.clinic_id == clinic_id,
            Appointment.doctor_id == doctor.id,
            Appointment.starts_at >= start_of_day,
            Appointment.starts_at <= end_of_day,
            Appointment.status != "cancelled",
        )
        appt_res = await db.execute(appt_stmt)
        existing_appts = list(appt_res.scalars().all())
        booked_starts = {a.starts_at for a in existing_appts}

        for sched in schedules:
            slot_delta = datetime.timedelta(minutes=sched.slot_minutes or 15)
            current_time = sched.start_time

            while current_time < sched.end_time:
                slot_start_dt = datetime.datetime.combine(target_date, current_time, tzinfo=tz)
                slot_end_dt = slot_start_dt + slot_delta

                # Ensure slot does not exceed doctor end_time
                if slot_end_dt.time() > sched.end_time:
                    break

                # Exclude slots that have already passed if target_date is today
                if target_date == today_tz and slot_start_dt <= now_tz:
                    current_time = (slot_start_dt + slot_delta).time()
                    continue

                # Exclude doctor break intervals
                in_break = False
                if sched.break_start and sched.break_end:
                    if not (current_time >= sched.break_end or slot_end_dt.time() <= sched.break_start):
                        in_break = True

                # Exclude already booked slots
                is_booked = any(
                    abs((slot_start_dt - b_start).total_seconds()) < 60
                    for b_start in booked_starts
                )

                if not in_break and not is_booked:
                    available_slots.append(
                        {
                            "doctor_id": str(doctor.id),
                            "doctor_name": doctor.name,
                            "starts_at": slot_start_dt.isoformat(),
                            "ends_at": slot_end_dt.isoformat(),
                            "time_str": current_time.strftime("%I:%M %p"),
                            "weekday": target_weekday,
                        }
                    )

                # Advance to next slot
                current_time = (slot_start_dt + slot_delta).time()

    return available_slots
