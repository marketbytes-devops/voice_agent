from __future__ import annotations

import asyncio
import datetime
import logging
import uuid
from sqlalchemy import select

from backend.app.core.database import get_session_factory
from backend.app.core.security import get_password_hash
from backend.app.models import (
    AgentSettings,
    Clinic,
    Doctor,
    DoctorSchedule,
    FAQEntry,
    Organisation,
    PhoneNumber,
    Treatment,
    User,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clinicvoice")


async def seed_sreerudra_clinic() -> None:
    """
    Seeds initial clinic, doctor schedules, treatments, FAQs, and administrative users.
    Idempotent: updates or preserves existing records if already seeded.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        # 1. Create or Find Organisation
        org_name = "Sreerudra Healthcare Group"
        org_stmt = select(Organisation).where(Organisation.name == org_name)
        org_res = await session.execute(org_stmt)
        org = org_res.scalar_one_or_none()

        if not org:
            org = Organisation(
                id=uuid.uuid4(),
                name=org_name,
                plan="enterprise",
                status="active",
            )
            session.add(org)
            await session.flush()
            logger.info("Created Organisation: %s (ID: %s)", org.name, org.id)
        else:
            logger.info("Organisation already exists: %s", org.name)

        # 2. Create or Find Clinic
        clinic_name = "Sreerudra Ayurveda Hospital & Research Centre"
        clinic_stmt = select(Clinic).where(Clinic.name == clinic_name, Clinic.organisation_id == org.id)
        clinic_res = await session.execute(clinic_stmt)
        clinic = clinic_res.scalar_one_or_none()

        working_hours_config = {
            # Monday (0) to Saturday (5): 09:00 - 17:00
            str(i): {"start": "09:00", "end": "17:00", "closed": False} for i in range(6)
        }
        # Sunday (6): Closed
        working_hours_config["6"] = {"start": "00:00", "end": "00:00", "closed": True}

        if not clinic:
            clinic = Clinic(
                id=uuid.uuid4(),
                organisation_id=org.id,
                name=clinic_name,
                address="Near General Hospital Junction, Alappuzha, Kerala - 688001",
                timezone="Asia/Kolkata",
                working_hours=working_hours_config,
                languages=["ml-IN", "en-IN"],
                fallback_phone="+914772251234",
            )
            session.add(clinic)
            await session.flush()
            logger.info("Created Clinic: %s (ID: %s)", clinic.name, clinic.id)
        else:
            logger.info("Clinic already exists: %s", clinic.name)

        # 3. Create Virtual Phone Number Route
        virtual_number = "+9104954269761"  # Exotel virtual inbound number
        phone_stmt = select(PhoneNumber).where(PhoneNumber.e164 == virtual_number)
        phone_res = await session.execute(phone_stmt)
        phone_record = phone_res.scalar_one_or_none()

        if not phone_record:
            phone_record = PhoneNumber(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                e164=virtual_number,
                provider="exotel",
                status="active",
            )
            session.add(phone_record)
            logger.info("Registered Virtual Phone Number: %s -> Clinic %s", virtual_number, clinic.name)

        # 4. Create Receptionist / Admin User
        admin_email = "admin@sreerudraayurveda.com"
        user_stmt = select(User).where(User.email == admin_email)
        user_res = await session.execute(user_stmt)
        admin_user = user_res.scalar_one_or_none()

        if not admin_user:
            admin_user = User(
                id=uuid.uuid4(),
                organisation_id=org.id,
                clinic_id=clinic.id,
                name="Front Desk Reception",
                email=admin_email,
                password_hash=get_password_hash("Sreerudra@2026"),
                role="admin",
                status="active",
            )
            session.add(admin_user)
            logger.info("Created Admin User: %s", admin_email)

        # 5. Create AI Agent Settings
        settings_stmt = select(AgentSettings).where(AgentSettings.clinic_id == clinic.id)
        settings_res = await session.execute(settings_stmt)
        agent_settings = settings_res.scalar_one_or_none()

        if not agent_settings:
            agent_settings = AgentSettings(
                clinic_id=clinic.id,
                greeting_ml="നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഈ കോൾ ഗുണനിലവാരത്തിനായി റെക്കോർഡ് ചെയ്യപ്പെടുന്നുണ്ട്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?",
                greeting_en="Welcome to Sreerudra Ayurveda Hospital. I am an AI assistant. How may I assist you today?",
                voice={"provider": "sarvam", "speaker": "kavya", "pace": 1.05},
                language_mode="auto",
                providers={"llm": "gemini-3.5-flash-lite", "stt": "saaras:v3", "tts": "bulbul:v3"},
                prompt_additions="Hospital is located near General Hospital Junction, Alappuzha. Emergency phone: 0477-2251234.",
                interruption={"enabled": True, "rms_threshold": 650.0},
            )
            session.add(agent_settings)
            logger.info("Configured AI Agent Settings for %s", clinic.name)

        # 6. Create Doctor: Dr. Manoj
        doc_stmt = select(Doctor).where(Doctor.clinic_id == clinic.id, Doctor.name == "Dr. Manoj")
        doc_res = await session.execute(doc_stmt)
        doctor = doc_res.scalar_one_or_none()

        if not doctor:
            doctor = Doctor(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                name="Dr. Manoj",
                qualification="BAMS, MD (Ayurveda)",
                specialties=["Panchakarma", "Spine & Joint Disorders", "Arthritis", "Rheumatoid Care", "Rejuvenation"],
                active=True,
            )
            session.add(doctor)
            await session.flush()
            logger.info("Created Doctor: %s", doctor.name)

            # Create Weekly Schedule for Dr. Manoj (Mon to Sat: 09:00 - 17:00, 15-min slots, 13:00 - 14:00 lunch break)
            for weekday in range(6):  # 0=Monday, 5=Saturday
                schedule = DoctorSchedule(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    doctor_id=doctor.id,
                    weekday=weekday,
                    start_time=datetime.time(9, 0),
                    end_time=datetime.time(17, 0),
                    slot_minutes=15,
                    break_start=datetime.time(13, 0),
                    break_end=datetime.time(14, 0),
                )
                session.add(schedule)
            logger.info("Added Monday-Saturday schedules for %s (with 1 PM - 2 PM lunch break)", doctor.name)

        # 7. Create Core Treatments
        treatments_data = [
            {
                "name_en": "Panchakarma Consultation & Therapy",
                "name_ml": "പഞ്ചകർമ്മ ചികിത്സ",
                "description_en": "Traditional Ayurvedic detoxification therapies including Abhyangam, Shirodhara, and Kizhi.",
                "duration_minutes": 30,
            },
            {
                "name_en": "Spine & Joint Care",
                "name_ml": "സന്ധിവേദന, നടുവേദന ചികിത്സകൾ",
                "description_en": "Specialized Ayurvedic care for disc problems, back pain, and knee arthritis.",
                "duration_minutes": 20,
            },
            {
                "name_en": "General Ayurveda Consultation",
                "name_ml": "ജനറൽ ആയുർവേദ കൺസൾട്ടേഷൻ",
                "description_en": "General health assessment and Ayurvedic lifestyle guidance.",
                "duration_minutes": 15,
            },
        ]

        for t in treatments_data:
            t_stmt = select(Treatment).where(Treatment.clinic_id == clinic.id, Treatment.name_en == t["name_en"])
            t_res = await session.execute(t_stmt)
            if not t_res.scalar_one_or_none():
                treatment = Treatment(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    name_en=t["name_en"],
                    name_ml=t["name_ml"],
                    description_en=t["description_en"],
                    duration_minutes=t["duration_minutes"],
                    active=True,
                )
                session.add(treatment)
                logger.info("Added Treatment: %s", t["name_en"])

        # 8. Create Frequently Asked Questions (Bilingual)
        faqs_data = [
            {
                "question": "ഹോസ്പിറ്റൽ എവിടെയാണ് സ്ഥിതി ചെയ്യുന്നത്?",
                "answer": "ആലപ്പുഴ ജനറൽ ഹോസ്പിറ്റൽ ജംഗ്ഷന് സമീപമാണ് ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റൽ പ്രവർത്തിക്കുന്നത്.",
                "language": "ml-IN",
            },
            {
                "question": "ഡോക്ടർ മനോജ് എപ്പോഴൊക്കെ ലഭ്യമാണ്?",
                "answer": "തിങ്കൾ മുതൽ ശനി വരെ രാവിലെ 9:00 മണി മുതൽ വൈകുന്നേരം 5:00 മണി വരെ ഡോക്ടർ ലഭ്യമാണ്. ഉച്ചയ്ക്ക് 1 മണി മുതൽ 2 മണി വരെ ഇടവേളയാണ്.",
                "language": "ml-IN",
            },
            {
                "question": "അപ്പോയിന്റ്മെന്റ് എങ്ങനെ ബുക്ക് ചെയ്യാം?",
                "answer": "താങ്കളുടെ പേരും സൗകര്യപ്രദമായ സമയവും പറഞ്ഞാൽ ഞങ്ങൾ ഇപ്പോൾ തന്നെ അപ്പോയിന്റ്മെന്റ് രേഖപ്പെടുത്താം.",
                "language": "ml-IN",
            },
        ]

        for f in faqs_data:
            f_stmt = select(FAQEntry).where(FAQEntry.clinic_id == clinic.id, FAQEntry.question == f["question"])
            f_res = await session.execute(f_stmt)
            if not f_res.scalar_one_or_none():
                faq = FAQEntry(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    question=f["question"],
                    answer=f["answer"],
                    language=f["language"],
                    active=True,
                )
                session.add(faq)
                logger.info("Added FAQ: %s", f["question"][:30])

        await session.commit()
        logger.info("Successfully finished database seeding for %s!", clinic.name)


if __name__ == "__main__":
    asyncio.run(seed_sreerudra_clinic())

