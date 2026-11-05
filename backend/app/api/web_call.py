from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path
import time
from typing import Any, AsyncGenerator
import uuid
import wave

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.providers.factory import build_providers
from backend.agent.session import CallSession
from backend.app.core.config import settings
from backend.app.models import Appointment, Call, Clinic, Doctor, FAQEntry, Patient, Treatment

logger = logging.getLogger("clinicvoice")

DEFAULT_CLINIC_ID = uuid.UUID("c5313bf1-67c2-4794-a34c-6629f342358c")
DEFAULT_DOCTOR_ID = uuid.UUID("75541d5d-402a-41b8-9557-501b82ba3bd5")

RECORDINGS_DIR = Path(__file__).resolve().parents[3] / "storage" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
LIVE_CALLS_FILE = Path(__file__).resolve().parents[3] / "storage" / "live_calls.json"

router = APIRouter(prefix="/api/voice", tags=["Web Audio Voice Testing"])


def _save_live_call(record: dict[str, Any]) -> None:
    """Save call to local live_calls.json store for staff dashboard fallback."""
    calls: list[dict[str, Any]] = []
    if LIVE_CALLS_FILE.exists():
        try:
            calls = json.loads(LIVE_CALLS_FILE.read_text(encoding="utf-8"))
        except Exception:
            calls = []
    calls = [c for c in calls if c.get("id") != record.get("id")]
    calls.insert(0, record)
    calls = calls[:50]
    try:
        LIVE_CALLS_FILE.write_text(json.dumps(calls, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not persist live_calls.json: %s", e)


async def _persist_call_to_supabase(
    record: dict[str, Any],
    transcript: list[dict[str, str]],
    clinic_id: uuid.UUID = DEFAULT_CLINIC_ID,
) -> None:
    """Safely commit web test session and any booked appointment to Supabase."""
    try:
        from backend.app.core.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text(f"SET LOCAL app.clinic_id = '{str(clinic_id)}'"))
            caller_phone = record.get("callerNumber", "Web Tester")
            patient_name = record.get("patientName", "Web Tester")
            patient_id = None

            if caller_phone:
                p_stmt = select(Patient).where(Patient.clinic_id == clinic_id, Patient.phone == caller_phone)
                pat = (await session.execute(p_stmt)).scalar_one_or_none()
                if not pat:
                    pat = Patient(
                        id=uuid.uuid4(),
                        clinic_id=clinic_id,
                        name=patient_name,
                        phone=caller_phone,
                        preferred_language=record.get("language", "ml-IN"),
                    )
                    session.add(pat)
                    await session.flush()
                patient_id = pat.id

            call_id = uuid.uuid4()
            call = Call(
                id=call_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                caller_number=caller_phone,
                language=record.get("language", "ml-IN"),
                duration_sec=record.get("durationSec", 0),
                outcome=record.get("outcome", "Inquiry Answered"),
                summary=record.get("summary", ""),
                transcript={"turns": transcript},
                recording_key=record.get("recordingKey"),
            )
            session.add(call)

            # If appointment was booked, persist to Supabase appointments table
            if record.get("outcome") == "Booked" and patient_id:
                import datetime
                from zoneinfo import ZoneInfo
                tz = ZoneInfo("Asia/Kolkata")
                now = datetime.datetime.now(tz)
                target_date = now.date() + datetime.timedelta(days=1)
                if target_date.weekday() == 6:  # Sunday -> Monday
                    target_date = target_date + datetime.timedelta(days=1)

                existing_appts = (await session.execute(
                    select(Appointment.starts_at).where(
                        Appointment.doctor_id == DEFAULT_DOCTOR_ID,
                        Appointment.status != "cancelled"
                    )
                )).scalars().all()
                existing_times = {a.astimezone(tz) for a in existing_appts}

                slot_hour = 10
                slot_min = 0
                starts_at = datetime.datetime.combine(target_date, datetime.time(10, 0), tzinfo=tz)
                while True:
                    candidate = datetime.datetime.combine(target_date, datetime.time(slot_hour, slot_min), tzinfo=tz)
                    if candidate not in existing_times:
                        starts_at = candidate
                        break
                    slot_min += 15
                    if slot_min >= 60:
                        slot_min = 0
                        slot_hour += 1
                    if slot_hour >= 17:
                        break

                ends_at = starts_at + datetime.timedelta(minutes=15)
                appt = Appointment(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=DEFAULT_DOCTOR_ID,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    status="booked",
                    source="web_voice_tester",
                    call_id=call_id,
                    reason="Ayurvedic Consultation with Dr. Manoj (via Web Tester)",
                )
                session.add(appt)
                logger.info("Persisted confirmed web-test appointment to Supabase for %s at %s", patient_name, starts_at)

            await session.commit()
            logger.info("Successfully persisted web test call record to Supabase (Call ID: %s)", call_id)
    except Exception as e:
        logger.warning("Could not persist web test call to Supabase: %s", e)


@router.websocket("/web-call")
async def handle_web_voice_call_websocket(websocket: WebSocket) -> None:
    """
    Direct Interactive Web Voice Receptionist WebSocket.
    Allows real-time microphone conversation with the AI in Malayalam:
    Browser Mic -> Sarvam STT -> Gemini LLM -> Hospital Database Tools -> Sarvam TTS -> Browser Speaker.
    Supports instant client-side barge-in / interruption and clarification.
    """
    await websocket.accept()
    logger.info("Web Voice Tester: WebSocket connected.")

    providers = build_providers()
    session_audio_chunks: list[bytes] = []
    session_transcript: list[dict[str, str]] = []
    session_start_epoch: float = time.time()
    call_id = f"web-test-{int(time.time())}"

    # Load live dynamic doctors and treatments from Supabase
    db_doctors = [
        {
            "id": str(DEFAULT_DOCTOR_ID),
            "name": "Dr. Manoj",
            "qualification": "BAMS, MD (Ayurveda)",
            "specialties": ["Panchakarma", "General Ayurveda"],
        }
    ]
    db_treatments = [
        {"name": "Panchakarma Consultation", "duration_minutes": 30},
        {"name": "General Ayurveda Consultation", "duration_minutes": 15},
    ]
    faq_knowledge_lines: list[str] = []

    try:
        from backend.app.core.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session_db:
            await session_db.execute(text(f"SET LOCAL app.clinic_id = '{DEFAULT_CLINIC_ID}'"))
            d_res = (await session_db.execute(
                select(Doctor).where(Doctor.clinic_id == DEFAULT_CLINIC_ID, Doctor.active == True)
            )).scalars().all()
            if d_res:
                db_doctors = [
                    {
                        "id": str(d.id),
                        "name": d.name,
                        "qualification": d.qualification or "BAMS, MD",
                        "specialties": d.specialties or ["General Ayurveda"],
                    }
                    for d in d_res
                ]
            t_res = (await session_db.execute(
                select(Treatment).where(Treatment.clinic_id == DEFAULT_CLINIC_ID, Treatment.active == True)
            )).scalars().all()
            if t_res:
                db_treatments = [{"name": t.name_en, "duration_minutes": t.duration_minutes} for t in t_res]

            f_res = (await session_db.execute(
                select(FAQEntry).where(FAQEntry.clinic_id == DEFAULT_CLINIC_ID, FAQEntry.active == True)
            )).scalars().all()
            if f_res:
                for f in f_res:
                    faq_knowledge_lines.append(f"Q: {f.question}\nA: {f.answer}")
    except Exception as e:
        logger.warning("Web Voice Tester: Could not load dynamic context from Supabase: %s", e)

    faq_notes = ("\n\nApproved Hospital FAQs:\n" + "\n".join(faq_knowledge_lines)) if faq_knowledge_lines else ""

    clinic_context = {
        "clinic_id": str(DEFAULT_CLINIC_ID),
        "clinic_name": "Sreerudra Ayurveda Hospital & Research Centre",
        "timezone": "Asia/Kolkata",
        "working_hours": {"0": {"start": "09:00", "end": "17:00"}},
        "languages": ["ml-IN", "en-IN"],
        "doctors": db_doctors,
        "treatments": db_treatments,
        "prompt_additions": faq_notes,
    }

    call_session = CallSession(
        call_id=call_id,
        clinic_context=clinic_context,
        providers=providers,
    )

    is_interrupted = False
    caller_phone: str = "+91 99473 84437"
    patient_name: str = "Akshay"

    # Send initial welcome greeting immediately upon connection
    welcome_text = "നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?"
    try:
        greeting_audio = await providers.tts.synthesize(welcome_text, language="ml-IN")
        if greeting_audio:
            session_audio_chunks.append(greeting_audio)
            session_transcript.append({"speaker": "Agent", "text": welcome_text})
            await websocket.send_text(json.dumps({
                "event": "agent_speech",
                "text": welcome_text,
                "audio_base64": base64.b64encode(greeting_audio).decode("ascii"),
                "speaker": "Agent",
                "turn_type": "greeting",
            }))
    except Exception as e:
        logger.error("Web Voice Tester: Error generating greeting: %s", e)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except Exception:
                continue

            event = msg.get("event")

            # 0. Caller Profile Configuration on Session Start
            if event == "start":
                caller_phone = msg.get("caller_phone") or caller_phone
                patient_name = msg.get("caller_name") or patient_name
                logger.info("Web Voice Tester session profile: caller=%s patient=%s", caller_phone, patient_name)
                continue

            # 1. User Interrupted AI (Barge-in from browser)
            elif event == "user_interrupted":
                logger.info("Web Voice Tester: User interrupted AI playback.")
                is_interrupted = True
                continue

            # 2. User Sent Audio Utterance from Microphone
            elif event == "user_audio":
                is_interrupted = False
                audio_b64 = msg.get("audio_base64", "")
                if not audio_b64:
                    continue

                user_audio_bytes = base64.b64decode(audio_b64)
                session_audio_chunks.append(user_audio_bytes)

                # Transcribe with Sarvam AI STT
                await websocket.send_text(json.dumps({"event": "status", "state": "transcribing"}))
                t_stt = time.time()
                transcript = await providers.stt.transcribe(user_audio_bytes, language="ml-IN")
                transcript = transcript.strip()
                logger.info("Web Voice Tester: STT transcribed in %.2fs: '%s'", time.time() - t_stt, transcript)

                # Send transcript immediately to browser so user sees live text
                clean_t = transcript.strip().replace(".", "").replace("?", "").replace("!", "").strip()
                await websocket.send_text(json.dumps({
                    "event": "user_transcript",
                    "text": transcript or "[Inaudible]",
                }))

                # Handle inaudible speech politely
                if not clean_t or (len(clean_t) <= 2 and clean_t not in ["ഹാ", "ഓ", "ആം", "യെസ്"]):
                    repeat_text = "ക്ഷമിക്കണം, പറഞ്ഞത് വ്യക്തമായി കേട്ടില്ല. ഒന്നുകൂടി പറയാമോ?"
                    session_transcript.append({"speaker": "Caller", "text": transcript or "..."})
                    session_transcript.append({"speaker": "Agent", "text": repeat_text})
                    repeat_audio = await providers.tts.synthesize(repeat_text, language="ml-IN")
                    await websocket.send_text(json.dumps({
                        "event": "agent_speech",
                        "text": repeat_text,
                        "audio_base64": base64.b64encode(repeat_audio).decode("ascii") if repeat_audio else "",
                        "turn_type": "clarification",
                    }))
                    continue

                session_transcript.append({"speaker": "Caller", "text": transcript})

                # Process utterance via Gemini LLM and hospital tools
                await websocket.send_text(json.dumps({"event": "status", "state": "thinking"}))
                t_llm = time.time()
                result = await call_session.handle_caller_utterance(transcript, synthesize_audio=False)
                reply_text = result.get("text", "")
                logger.info("Web Voice Tester: Gemini generated reply in %.2fs: '%s'", time.time() - t_llm, reply_text)

                # If an appointment was booked during this turn, extract the patient name dynamically
                for tr in result.get("tool_results", []):
                    if tr.get("tool") == "book_appointment":
                        res_data = tr.get("result", {})
                        if res_data.get("patient_name"):
                            patient_name = res_data["patient_name"]
                            logger.info("Web Voice Tester: Updated patient name from booking: %s", patient_name)

                if is_interrupted:
                    logger.info("Web Voice Tester: Utterance processing cancelled due to newer interruption.")
                    continue

                # Pipelined Sub-Second Streaming TTS:
                # Deliver Sentence 1 audio in <800ms while synthesizing subsequent sentences in parallel
                import re
                sentences = [s.strip() for s in re.split(r"(?<=[.?!।\n])\s+", reply_text) if s.strip()]
                if not sentences:
                    sentences = [reply_text]

                if len(sentences) > 1 and len(sentences[0]) < 22:
                    sentences = [sentences[0] + " " + sentences[1]] + sentences[2:]

                first_sentence = sentences[0]
                rest_sentence = " ".join(sentences[1:]).strip() if len(sentences) > 1 else ""

                rest_task: asyncio.Task | None = None
                if rest_sentence:
                    rest_task = asyncio.create_task(providers.tts.synthesize(rest_sentence, language="ml-IN"))

                t_tts = time.time()
                first_audio = await providers.tts.synthesize(first_sentence, language="ml-IN")
                logger.info("Web Voice Tester: First sentence ready in %.2fs (%d chars, %d bytes)", time.time() - t_tts, len(first_sentence), len(first_audio))

                if first_audio and not is_interrupted:
                    session_audio_chunks.append(first_audio)
                    await websocket.send_text(json.dumps({
                        "event": "agent_speech",
                        "text": first_sentence,
                        "audio_base64": base64.b64encode(first_audio).decode("ascii"),
                        "turn_type": result.get("type", "speech"),
                    }))

                if rest_task and not is_interrupted:
                    rest_audio = await rest_task
                    if rest_audio and not is_interrupted:
                        session_audio_chunks.append(rest_audio)
                        await websocket.send_text(json.dumps({
                            "event": "agent_speech_continue",
                            "text": rest_sentence,
                            "audio_base64": base64.b64encode(rest_audio).decode("ascii"),
                            "turn_type": result.get("type", "speech"),
                        }))

                session_transcript.append({"speaker": "Agent", "text": reply_text})

            # 3. User Sent Manual Text Prompt (for quick testing)
            elif event == "user_text":
                text_input = msg.get("text", "").strip()
                if not text_input:
                    continue

                session_transcript.append({"speaker": "Caller", "text": text_input})
                await websocket.send_text(json.dumps({
                    "event": "user_transcript",
                    "text": text_input,
                }))

                result = await call_session.handle_caller_utterance(text_input, synthesize_audio=False)
                reply_text = result.get("text", "")

                for tr in result.get("tool_results", []):
                    if tr.get("tool") == "book_appointment":
                        res_data = tr.get("result", {})
                        if res_data.get("patient_name"):
                            patient_name = res_data["patient_name"]

                reply_audio = await providers.tts.synthesize(reply_text, language="ml-IN")
                session_audio_chunks.append(reply_audio)
                session_transcript.append({"speaker": "Agent", "text": reply_text})

                await websocket.send_text(json.dumps({
                    "event": "agent_speech",
                    "text": reply_text,
                    "audio_base64": base64.b64encode(reply_audio).decode("ascii") if reply_audio else "",
                    "turn_type": result.get("type", "speech"),
                }))

            # 4. User Hung Up Call
            elif event == "hangup":
                logger.info("Web Voice Tester: Caller ended session.")
                break

    except WebSocketDisconnect:
        logger.info("Web Voice Tester: Client disconnected.")
    except Exception as e:
        logger.error("Web Voice Tester: Error in session: %s", e, exc_info=True)
    finally:
        # Only persist session if caller actively spoke (at least 1 caller turn)
        has_caller_turn = any(t.get("speaker") in ("Caller", "user") for t in session_transcript)
        if has_caller_turn and len(session_transcript) >= 2:
            import datetime
            duration_sec = max(5, int(time.time() - session_start_epoch))
            wav_filename = f"{call_id}.wav"
            wav_filepath = RECORDINGS_DIR / wav_filename

            all_audio = b"".join(session_audio_chunks)
            if all_audio:
                try:
                    wav_filepath.write_bytes(all_audio)
                except Exception as e:
                    logger.warning("Could not write audio file: %s", e)

            outcome = "Inquiry Answered"
            for t in session_transcript:
                txt = t.get("text", "").lower()
                if t.get("speaker") == "Agent" and ("ബുക്ക്" in txt or "booked" in txt or "അപ്പോയിന്റ്മെന്റ്" in txt or "slot" in txt):
                    outcome = "Booked"
                    break

            clean_patient_name = patient_name if patient_name and patient_name not in ("Web Tester", "Patient") else "Akshay"
            clean_caller_phone = caller_phone if caller_phone and caller_phone not in ("Web Live Tester", "Web Tester") else "+91 99473 84437"

            # Dynamic Malayalam name resolution
            name_map = {
                "akshay": "അക്ഷയ്",
                "lakshmi": "ലക്ഷ്മി",
                "rashmi": "രശ്മി",
                "rahul": "രാഹുൽ",
                "sneha": "സ്നേഹ",
                "manoj": "മനോജ്",
                "anoop": "അനൂപ്",
            }
            pat_name_lower = clean_patient_name.lower()
            patient_name_ml = ""
            for k, v in name_map.items():
                if k in pat_name_lower:
                    patient_name_ml = v
                    break
            if not patient_name_ml:
                patient_name_ml = clean_patient_name if any('\u0d00' <= char <= '\u0d7f' for char in clean_patient_name) else "രോഗി"

            now_str = datetime.datetime.now().strftime("%I:%M %p")
            record = {
                "id": call_id,
                "callerNumber": clean_caller_phone,
                "patientName": clean_patient_name,
                "patientNameMl": patient_name_ml,
                "language": "ml-IN",
                "durationSec": duration_sec,
                "outcome": outcome,
                "timestamp": f"Today at {now_str}",
                "consentGiven": True,
                "recordingKey": f"recordings/{wav_filename}" if all_audio else None,
                "audioUrl": f"/api/calls/live/{call_id}/audio",
                "summary": f"Inbound telephone consultation ({duration_sec}s). Outcome: {outcome}. Patient: {clean_patient_name}.",
                "transcript": session_transcript,
            }
            _save_live_call(record)
            await _persist_call_to_supabase(record, session_transcript, DEFAULT_CLINIC_ID)
            logger.info("Web Voice Tester: Session successfully saved for %s (%s, outcome=%s)", clean_patient_name, clean_caller_phone, outcome)

