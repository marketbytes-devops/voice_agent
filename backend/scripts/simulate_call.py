"""
Interactive / Automated Test Call Simulation Script for ClinicVoice.
Simulates a complete patient telephone session:
1. Greets in native Malayalam.
2. Answers visiting hours dynamically from Supabase FAQ.
3. Books a 10:00 AM consultation with Dr. Manoj.
4. Persists the call, audio, and booking with PostgreSQL RLS.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import sys
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, text
from backend.app.core.database import get_session_factory
from backend.app.models import Appointment, Call, Doctor, FAQEntry, Patient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clinicvoice")

DEFAULT_CLINIC_ID = uuid.UUID("c5313bf1-67c2-4794-a34c-6629f342358c")


async def simulate_call(caller_name: str = "Ananthakrishnan Nair (അനന്തകൃഷ്ണൻ നായർ)") -> dict[str, str]:
    factory = get_session_factory()
    clinic_id_str = str(DEFAULT_CLINIC_ID)
    tz = ZoneInfo("Asia/Kolkata")
    now = datetime.datetime.now(tz)

    logger.info("Connecting to Supabase for live consultation simulation...")
    async with factory() as session:
        await session.execute(text(f"SET LOCAL app.clinic_id = '{clinic_id_str}'"))

        # 1. Fetch Doctor
        d_stmt = select(Doctor).where(Doctor.clinic_id == DEFAULT_CLINIC_ID, Doctor.active == True)
        doctor = (await session.execute(d_stmt)).scalars().first()
        doc_id = doctor.id if doctor else uuid.uuid4()
        doc_name = doctor.name if doctor else "Dr. Manoj"

        # 2. Fetch Knowledge Base FAQ for visiting hours
        f_stmt = select(FAQEntry).where(FAQEntry.clinic_id == DEFAULT_CLINIC_ID, FAQEntry.active == True)
        faqs = (await session.execute(f_stmt)).scalars().all()
        visiting_faq = next((f for f in faqs if "4:00" in f.answer or "സന്ദർശന" in f.question), None)
        visiting_answer = visiting_faq.answer if visiting_faq else "സന്ദർശന സമയം ദിവസവും വൈകുന്നേരം 4:00 മണി മുതൽ 7:00 മണി വരെയാണ്."

        # 3. Create or Fetch Patient (handles deduplication)
        p_stmt = select(Patient).where(Patient.clinic_id == DEFAULT_CLINIC_ID, Patient.phone == "+91 98765 43210")
        patient = (await session.execute(p_stmt)).scalars().first()
        if not patient:
            pat_id = uuid.uuid4()
            patient = Patient(
                id=pat_id,
                clinic_id=DEFAULT_CLINIC_ID,
                name=caller_name,
                phone="+91 98765 43210",
                preferred_language="ml-IN",
            )
            session.add(patient)
            await session.flush()
        else:
            pat_id = patient.id

        # 4. Create Call Record
        call_id = uuid.uuid4()
        call = Call(
            id=call_id,
            clinic_id=DEFAULT_CLINIC_ID,
            patient_id=pat_id,
            caller_number="+91 98****3210",
            language="ml-IN",
            started_at=now,
            ended_at=now + datetime.timedelta(seconds=78),
            duration_sec=78,
            outcome="Booked",
            summary=f"Inquired about hospital visiting hours (provided: {visiting_answer}). Confirmed consultation booking with {doc_name} for tomorrow 10:00 AM.",
            transcript={
                "turns": [
                    {
                        "speaker": "Agent",
                        "text": "നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?"
                    },
                    {
                        "speaker": "Caller",
                        "text": "സന്ദർശന സമയം എപ്പോഴാണ്? പിന്നെ ഡോക്ടർ മനോജിന് നാളെ ഒരു അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്യണം."
                    },
                    {
                        "speaker": "Agent",
                        "text": f"{visiting_answer} തീർച്ചയായും, നാളെ രാവിലെ 10:00 മണിക്ക് ഡോക്ടർ മനോജിന്റെ കൺസൾട്ടേഷൻ ലഭ്യമാണ്."
                    },
                    {
                        "speaker": "Caller",
                        "text": f"എന്റെ പേര് {caller_name.split(' ')[0]}. 10:00 മണി ഉറപ്പിച്ചോളൂ."
                    },
                    {
                        "speaker": "Agent",
                        "text": f"നന്ദി! നാളെ രാവിലെ 10:00 മണിക്ക് ഡോക്ടർ മനോജിന്റെ അപ്പോയിന്റ്മെന്റ് വിജയകരമായി രേഖപ്പെടുത്തിയിട്ടുണ്ട്."
                    }
                ]
            },
            recording_key="recordings/call-live-sample.wav",
        )
        session.add(call)

        # 5. Create Confirmed Appointment (Find next available slot avoiding double booking)
        tomorrow = now.date() + datetime.timedelta(days=1)
        if tomorrow.weekday() == 6:  # Skip Sunday
            tomorrow += datetime.timedelta(days=1)

        existing_appts = (await session.execute(
            select(Appointment.starts_at).where(
                Appointment.doctor_id == doc_id,
                Appointment.status != "cancelled"
            )
        )).scalars().all()
        existing_times = {a.astimezone(tz) for a in existing_appts}

        slot_hour = 10
        slot_min = 0
        while True:
            candidate = datetime.datetime.combine(tomorrow, datetime.time(slot_hour, slot_min), tzinfo=tz)
            if candidate not in existing_times:
                starts_at = candidate
                break
            slot_min += 15
            if slot_min >= 60:
                slot_min = 0
                slot_hour += 1
            if slot_hour >= 17:
                break

        slot_str = starts_at.strftime("%I:%M %p")

        appt = Appointment(
            id=uuid.uuid4(),
            clinic_id=DEFAULT_CLINIC_ID,
            patient_id=pat_id,
            doctor_id=doc_id,
            starts_at=starts_at,
            ends_at=starts_at + datetime.timedelta(minutes=15),
            status="booked",
            source="voice_agent",
            call_id=call_id,
            reason=f"Ayurvedic Consultation with {doc_name}",
        )
        session.add(appt)
        await session.commit()

        logger.info("✓ Simulated call committed successfully to Supabase! (Call ID: %s)", call_id)
        logger.info("✓ Confirmed appointment booked for %s with %s at %s", caller_name, doc_name, starts_at)

        return {
            "call_id": str(call_id),
            "doctor": doc_name,
            "patient": caller_name,
            "time": starts_at.strftime("%I:%M %p, %A, %d %b %Y"),
        }


if __name__ == "__main__":
    result = asyncio.run(simulate_call())
    print("\n" + "="*50)
    print("SIMULATED CALL COMPLETED SUCCESSFULLY!")
    print(f"Doctor: {result['doctor']}")
    print(f"Patient: {result['patient'].encode('ascii', 'backslashreplace').decode('ascii')}")
    print(f"Slot Booked: {result['time']}")
    print("Refresh http://localhost:3000 to see the live updates!")
    print("="*50)
