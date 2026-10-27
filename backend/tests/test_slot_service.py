from __future__ import annotations

import datetime
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

from backend.app.models import Appointment, Clinic, Doctor, DoctorLeave, DoctorSchedule, Patient
from backend.app.services.booking_service import (
    BookingValidationError,
    book_appointment_guarded,
    cancel_appointment_guarded,
    reschedule_appointment_guarded,
)
from backend.app.services.slot_service import get_available_slots


class TestSlotAndBookingService(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.clinic_id = uuid.uuid4()
        self.doctor_id = uuid.uuid4()
        self.patient_id = uuid.uuid4()
        self.tz = ZoneInfo("Asia/Kolkata")

        self.mock_clinic = Clinic(
            id=self.clinic_id,
            organisation_id=uuid.uuid4(),
            name="Sreerudra Ayurveda Hospital",
            timezone="Asia/Kolkata",
            working_hours={},
        )
        self.mock_doctor = Doctor(
            id=self.doctor_id,
            clinic_id=self.clinic_id,
            name="Dr. Manoj",
            active=True,
        )

    # 1. Past Date Rejection
    async def test_past_date_rejected(self) -> None:
        mock_db = AsyncMock()
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        clinic_res = MagicMock()
        clinic_res.scalar_one_or_none.return_value = self.mock_clinic
        mock_db.execute.return_value = clinic_res

        slots = await get_available_slots(mock_db, self.clinic_id, target_date=yesterday)
        self.assertEqual(slots, [])

    # 2. Break Time and Booked Slot Filtering
    async def test_slot_calculation_filters_breaks_and_existing_bookings(self) -> None:
        mock_db = AsyncMock()
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        weekday = tomorrow.weekday()

        # Doctor works 9:00 to 11:00 with break 9:30 to 10:00 (15-min slots)
        # Expected potential slots: 09:00, 09:15, 09:30(break), 09:45(break), 10:00, 10:15, 10:30, 10:45
        schedule = DoctorSchedule(
            id=uuid.uuid4(),
            clinic_id=self.clinic_id,
            doctor_id=self.doctor_id,
            weekday=weekday,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(11, 0),
            slot_minutes=15,
            break_start=datetime.time(9, 30),
            break_end=datetime.time(10, 0),
        )

        # 10:00 slot is already booked
        booked_start = datetime.datetime.combine(tomorrow, datetime.time(10, 0), tzinfo=self.tz)
        existing_appt = Appointment(
            id=uuid.uuid4(),
            clinic_id=self.clinic_id,
            doctor_id=self.doctor_id,
            patient_id=self.patient_id,
            starts_at=booked_start,
            ends_at=booked_start + datetime.timedelta(minutes=15),
            status="booked",
        )

        # Mock query returns
        clinic_res = MagicMock()
        clinic_res.scalar_one_or_none.return_value = self.mock_clinic

        doc_res = MagicMock()
        doc_res.scalars.return_value.all.return_value = [self.mock_doctor]

        leave_res = MagicMock()
        leave_res.scalars.return_value.all.return_value = []  # No leave

        sched_res = MagicMock()
        sched_res.scalars.return_value.all.return_value = [schedule]

        appt_res = MagicMock()
        appt_res.scalars.return_value.all.return_value = [existing_appt]

        mock_db.execute.side_effect = [clinic_res, doc_res, leave_res, sched_res, appt_res]

        slots = await get_available_slots(mock_db, self.clinic_id, target_date=tomorrow, doctor_id=self.doctor_id)

        # Available should be: 09:00, 09:15, 10:15, 10:30, 10:45 (Total: 5)
        self.assertEqual(len(slots), 5)
        times = [s["time_str"] for s in slots]
        self.assertIn("09:00 AM", times)
        self.assertIn("09:15 AM", times)
        self.assertNotIn("09:30 AM", times)  # Break
        self.assertNotIn("09:45 AM", times)  # Break
        self.assertNotIn("10:00 AM", times)  # Booked
        self.assertIn("10:15 AM", times)

    # 3. Doctor on Leave Returns Zero Slots
    async def test_doctor_on_leave_returns_zero_slots(self) -> None:
        mock_db = AsyncMock()
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        leave = DoctorLeave(
            id=uuid.uuid4(),
            clinic_id=self.clinic_id,
            doctor_id=self.doctor_id,
            starts_at=datetime.datetime.combine(tomorrow, datetime.time(0, 0), tzinfo=self.tz),
            ends_at=datetime.datetime.combine(tomorrow, datetime.time(23, 59), tzinfo=self.tz),
        )

        clinic_res = MagicMock()
        clinic_res.scalar_one_or_none.return_value = self.mock_clinic

        doc_res = MagicMock()
        doc_res.scalars.return_value.all.return_value = [self.mock_doctor]

        leave_res = MagicMock()
        leave_res.scalars.return_value.all.return_value = [leave]

        mock_db.execute.side_effect = [clinic_res, doc_res, leave_res]

        slots = await get_available_slots(mock_db, self.clinic_id, target_date=tomorrow, doctor_id=self.doctor_id)
        self.assertEqual(slots, [])

    # 4. Guarded Booking Rejects Past Time
    async def test_booking_past_time_rejected(self) -> None:
        mock_db = AsyncMock()
        past_time = datetime.datetime.now(self.tz) - datetime.timedelta(hours=2)

        pat_res = MagicMock()
        pat_res.scalar_one_or_none.return_value = Patient(id=self.patient_id, clinic_id=self.clinic_id, name="Rahul", phone="9876543210")

        doc_res = MagicMock()
        doc_res.scalar_one_or_none.return_value = self.mock_doctor

        clinic_res = MagicMock()
        clinic_res.scalar_one_or_none.return_value = self.mock_clinic

        mock_db.execute.side_effect = [pat_res, doc_res, clinic_res]

        with self.assertRaises(BookingValidationError) as ctx:
            await book_appointment_guarded(
                db=mock_db,
                clinic_id=self.clinic_id,
                patient_id=self.patient_id,
                doctor_id=self.doctor_id,
                starts_at=past_time,
            )
        self.assertIn("past", str(ctx.exception).lower())

    # 5. Cancellation Ownership Validation
    async def test_cancellation_ownership_check(self) -> None:
        mock_db = AsyncMock()
        appt_id = uuid.uuid4()

        # No appointment matching caller's phone
        empty_res = MagicMock()
        empty_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = empty_res

        with self.assertRaises(BookingValidationError) as ctx:
            await cancel_appointment_guarded(
                db=mock_db,
                clinic_id=self.clinic_id,
                appointment_id=appt_id,
                caller_phone="9999999999",
            )
        self.assertIn("not found", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
