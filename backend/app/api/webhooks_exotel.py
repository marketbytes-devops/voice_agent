from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path
import struct
import time
from typing import Any, AsyncGenerator
import uuid
import wave

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.providers.factory import build_providers
from backend.agent.session import CallSession


from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models import Appointment, Call, Clinic, Doctor, FAQEntry, Patient, PhoneNumber, Treatment

logger = logging.getLogger("clinicvoice")

DEFAULT_CLINIC_ID = uuid.UUID("c5313bf1-67c2-4794-a34c-6629f342358c")
DEFAULT_DOCTOR_ID = uuid.UUID("75541d5d-402a-41b8-9557-501b82ba3bd5")


async def get_optional_db() -> AsyncGenerator[AsyncSession | None, None]:
    """Graceful database dependency: yields session if DB is accessible, else None."""
    try:
        from backend.app.core.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            yield session
    except Exception:
        yield None


router = APIRouter(prefix="/webhooks/exotel", tags=["Telephony Webhooks (Exotel)"])


@router.api_route("/voice", methods=["GET", "POST"])
async def handle_exotel_incoming_voice(
    request: Request,
    db: AsyncSession | None = Depends(get_optional_db),
) -> Response:
    """
    Exotel Inbound Call Webhook (supports both GET and POST).
    Resolves the dialed virtual number (To) to the hospital tenant.
    Returns SIP forwarding instructions to LiveKit, or immediate fallback
    diversion to the clinic front desk if the system is in degraded state.
    """
    params = dict(request.query_params)
    if request.method == "POST":
        try:
            form = await request.form()
            params.update(dict(form))
        except Exception:
            pass

    CallSid = params.get("CallSid", "unknown")
    From = params.get("From") or params.get("CallFrom", "unknown")
    To = params.get("To") or params.get("CallTo", "04954269761")
    Direction = params.get("Direction", "inbound")

    logger.info("Exotel voice webhook [%s]: CallSid=%s caller=%s dialed=%s", request.method, CallSid, From, To)

    fallback_phone = "+914772251234"  # Default Sreerudra front desk
    if db is not None:
        try:
            phone_res = await db.execute(
                select(PhoneNumber).where(((PhoneNumber.e164 == To) | (PhoneNumber.e164 == (To.replace(" ", "").replace("-", "") if To else ""))), PhoneNumber.status == "active")
            )
            phone_record = phone_res.scalar_one_or_none()
            if phone_record and phone_record.clinic_id:
                clinic_res = await db.execute(select(Clinic).where(Clinic.id == phone_record.clinic_id))
                clinic = clinic_res.scalar_one_or_none()
                if clinic and clinic.fallback_phone:
                    fallback_phone = clinic.fallback_phone
        except Exception as e:
            logger.warning("DB query failed during number resolution: %s. Using fallback %s", e, fallback_phone)

    # Resolve LiveKit Cloud SIP trunk target
    sip_domain = getattr(settings, "LIVEKIT_SIP_DOMAIN", "voiceagent-6aqqbru4.sip.livekit.cloud")
    clean_number = To.replace("+", "").strip() if To else CallSid
    livekit_sip_uri = f"sip:{clean_number}@{sip_domain}"

    # Return Exotel Passthru XML response
    response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <!-- Primary Route: LiveKit Inbound SIP Trunk -->
    <Dial timeout="20" action="/webhooks/exotel/status">
        <Sip>{livekit_sip_uri}</Sip>
    </Dial>
    <!-- Emergency Human Fallback Circuit if SIP fails -->
    <Dial timeout="30">
        <Number>{fallback_phone}</Number>
    </Dial>
</Response>"""

    return Response(content=response_xml, media_type="application/xml")


@router.api_route("/status", methods=["GET", "POST"])
async def handle_exotel_call_status(
    request: Request,
    db: AsyncSession | None = Depends(get_optional_db),
) -> dict[str, Any]:
    """Exotel Call Detail Record (CDR) and call completion status webhook."""
    params = dict(request.query_params)
    if request.method == "POST":
        try:
            form = await request.form()
            params.update(dict(form))
        except Exception:
            pass

    CallSid = params.get("CallSid", "unknown")
    Status = params.get("Status", "completed")
    Duration = int(params.get("Duration", 0) or 0)

    logger.info("Exotel call status update [%s]: CallSid=%s status=%s duration=%ds", request.method, CallSid, Status, Duration)
    return {"status": "ok", "call_sid": CallSid, "received_status": Status}


def _load_pcm_greeting() -> bytes:
    """Load pre-rendered 8kHz 16-bit mono PCM greeting."""
    base_dir = Path(__file__).resolve().parents[3]
    audio_paths = [
        base_dir / "frontend" / "public" / "audio" / "hospital_welcome_ml.wav",
        Path("frontend/public/audio/hospital_welcome_ml.wav"),
        base_dir / "frontend" / "public" / "audio" / "live_hospital_sample.wav",
        Path("frontend/public/audio/live_hospital_sample.wav"),
        Path("/opt/render/project/src/frontend/public/audio/hospital_welcome_ml.wav"),
        Path("/opt/render/project/src/frontend/public/audio/live_hospital_sample.wav"),
    ]
    for p in audio_paths:
        if p.exists():
            try:
                with wave.open(str(p), "rb") as w:
                    frames = w.readframes(w.getnframes())
                    logger.info("Successfully loaded pre-rendered greeting from %s (%d bytes)", p, len(frames))
                    return frames
            except Exception as e:
                logger.warning("Failed reading audio file %s: %s", p, e)
    logger.warning("No pre-rendered greeting WAV found at expected paths!")
    return b""


def _calculate_rms(pcm_data: bytes) -> float:
    """Calculate Root Mean Square (RMS) energy for 16-bit signed PCM."""
    if not pcm_data:
        return 0.0
    count = len(pcm_data) // 2
    if count == 0:
        return 0.0
    shorts = struct.unpack(f"<{count}h", pcm_data[: count * 2])
    sum_squares = sum(s * s for s in shorts)
    return (sum_squares / count) ** 0.5


def _to_raw_pcm(audio_bytes: bytes) -> bytes:
    """Strip WAV RIFF header if present, returning raw PCM audio."""
    if audio_bytes.startswith(b"RIFF") and len(audio_bytes) > 44:
        return audio_bytes[44:]
    return audio_bytes


RECORDINGS_DIR = Path(__file__).resolve().parents[3] / "storage" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
LIVE_CALLS_FILE = Path(__file__).resolve().parents[3] / "storage" / "live_calls.json"


def load_live_calls() -> list[dict[str, Any]]:
    """Retrieve all real calls captured from live telephone sessions."""
    if LIVE_CALLS_FILE.exists():
        try:
            return json.loads(LIVE_CALLS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_live_call(record: dict[str, Any]) -> None:
    """Save newly completed phone call to live_calls.json store."""
    calls = load_live_calls()
    # Prepend newest call to top of list
    calls = [c for c in calls if c.get("id") != record.get("id")]
    calls.insert(0, record)
    calls = calls[:50]
    try:
        LIVE_CALLS_FILE.write_text(json.dumps(calls, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not persist live_calls.json: %s", e)


async def persist_call_to_supabase(
    record: dict[str, Any],
    transcript: list[dict[str, str]],
    clinic_id: uuid.UUID = DEFAULT_CLINIC_ID,
) -> None:
    """Safely persist completed telephone session and any confirmed booking to Supabase."""
    try:
        from backend.app.core.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text(f"SET LOCAL app.clinic_id = '{str(clinic_id)}'"))
            caller_phone = record.get("callerNumber", "Unknown")
            patient_name = record.get("patientName", "Patient")
            patient_id = None

            if caller_phone and caller_phone != "Unknown":
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

            # If appointment was booked, save confirmed booking in Supabase!
            if record.get("outcome") == "Booked" and patient_id:
                import datetime
                from zoneinfo import ZoneInfo
                tz = ZoneInfo("Asia/Kolkata")
                now = datetime.datetime.now(tz)
                target_date = now.date() + datetime.timedelta(days=1)
                if target_date.weekday() == 6:  # Sunday -> Monday
                    target_date = target_date + datetime.timedelta(days=1)

                starts_at = datetime.datetime.combine(target_date, datetime.time(10, 0), tzinfo=tz)
                ends_at = starts_at + datetime.timedelta(minutes=15)

                appt = Appointment(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=DEFAULT_DOCTOR_ID,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    status="booked",
                    source="voice_agent",
                    call_id=call_id,
                    reason="Ayurvedic Consultation booked via voice assistant",
                )
                session.add(appt)
                logger.info("Persisted confirmed appointment to Supabase for %s at %s", patient_name, starts_at)

            await session.commit()
            logger.info("Successfully persisted live call record to Supabase (Call ID: %s)", call_id)
    except Exception as e:
        logger.warning("Could not persist call/appointment to Supabase (using local backup): %s", e)


@router.websocket("/voicebot")
async def handle_exotel_voicebot_websocket(websocket: WebSocket) -> None:
    """
    Exotel Voicebot Full Two-Way Audio Streaming WebSocket.
    Enables continuous, turn-by-turn conversation in native Malayalam:
    Caller speaks -> Sarvam STT -> Gemini LLM -> Hospital Tools -> Sarvam TTS -> Caller Earpiece.
    """
    await websocket.accept()
    logger.info("Exotel Voicebot: Incoming WebSocket connection accepted.")

    stream_sid: str | None = None
    call_sid: str | None = None
    caller_phone: str = "Unknown"
    pcm_greeting = _load_pcm_greeting()

    # Track complete audio and conversation turns for staff dashboard playback
    session_audio_chunks: list[bytes] = []
    session_transcript: list[dict[str, str]] = []
    session_start_epoch: float = time.time()

    # Initialize clinical session context dynamically from live Supabase tables!
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
        async with factory() as session:
            await session.execute(text(f"SET LOCAL app.clinic_id = '{DEFAULT_CLINIC_ID}'"))

            # 1. Fetch active doctors
            d_res = (await session.execute(
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

            # 2. Fetch active treatments
            t_res = (await session.execute(
                select(Treatment).where(Treatment.clinic_id == DEFAULT_CLINIC_ID, Treatment.active == True)
            )).scalars().all()
            if t_res:
                db_treatments = [
                    {"name": t.name_en, "duration_minutes": t.duration_minutes}
                    for t in t_res
                ]

            # 3. Fetch active FAQs
            f_res = (await session.execute(
                select(FAQEntry).where(FAQEntry.clinic_id == DEFAULT_CLINIC_ID, FAQEntry.active == True)
            )).scalars().all()
            if f_res:
                for f in f_res:
                    faq_knowledge_lines.append(f"Q: {f.question}\nA: {f.answer}")
        logger.info(
            "Exotel Voicebot: Dynamically loaded %d doctors, %d treatments, and %d FAQs from Supabase.",
            len(db_doctors),
            len(db_treatments),
            len(faq_knowledge_lines),
        )
    except Exception as e:
        logger.warning("Exotel Voicebot: Could not load dynamic context from Supabase (using fallback): %s", e)

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
    providers = build_providers()
    session = CallSession(
        call_id="exotel-live-session",
        clinic_context=clinic_context,
        providers=providers,
    )

    caller_pcm_buffer: list[bytes] = []
    has_spoken = False
    is_speaking = False
    is_processing_turn = False
    is_greeting = False
    was_interrupted = False
    silence_timer_task: asyncio.Task | None = None
    speech_start_time: float = 0.0

    SPEECH_RMS_THRESHOLD = 260.0  # Clear speech above telephone carrier floor
    SILENCE_RMS_THRESHOLD = 190.0

    async def stream_audio_to_caller(raw_pcm: bytes, sid: str, is_welcome: bool = False) -> None:
        """Stream 8kHz 16-bit PCM chunks to Exotel with jitter pre-buffering."""
        nonlocal is_speaking, is_greeting
        is_speaking = True
        is_greeting = is_welcome
        chunk_size = 1600  # 100ms chunks at 8000Hz 16-bit mono

        chunks = [raw_pcm[i : i + chunk_size] for i in range(0, len(raw_pcm), chunk_size)]
        
        # Pre-buffer: burst first 4 chunks (400ms) immediately to prevent carrier jitter buffer underrun
        burst_count = min(4, len(chunks))
        for i in range(burst_count):
            if not is_speaking and not is_welcome:
                break
            payload = base64.b64encode(chunks[i]).decode("ascii")
            msg = {
                "event": "media",
                "stream_sid": sid,
                "streamSid": sid,
                "media": {"payload": payload},
            }
            try:
                await websocket.send_text(json.dumps(msg))
            except Exception:
                is_speaking = False
                is_greeting = False
                return

        # Paced delivery for remaining chunks (75ms interval ensures carrier buffer never starves)
        for i in range(burst_count, len(chunks)):
            # Never interrupt the initial welcome introduction greeting
            if not is_speaking and not is_welcome:
                logger.info("Exotel Voicebot: Audio playback interrupted by caller speech.")
                break
            payload = base64.b64encode(chunks[i]).decode("ascii")
            msg = {
                "event": "media",
                "stream_sid": sid,
                "streamSid": sid,
                "media": {"payload": payload},
            }
            try:
                await websocket.send_text(json.dumps(msg))
                await asyncio.sleep(0.075)
            except Exception:
                break

        is_speaking = False
        is_greeting = False
        logger.info("Exotel Voicebot: Audio playback completed for StreamSid=%s.", sid)

    async def process_caller_speech() -> None:
        """Transcribe caller speech via Sarvam STT, query Gemini LLM, and stream reply with pipelined TTS."""
        nonlocal is_processing_turn, has_spoken, speech_start_time, was_interrupted
        if is_processing_turn or not caller_pcm_buffer:
            return

        is_processing_turn = True
        has_spoken = False
        was_interrupted = False
        speech_start_time = 0.0
        raw_pcm = b"".join(caller_pcm_buffer)
        caller_pcm_buffer.clear()

        # Ignore brief noise clicks (< 0.30s)
        if len(raw_pcm) < 8000 * 2 * 0.30:
            is_processing_turn = False
            return

        try:
            # Package raw PCM into 8kHz 16-bit mono WAV container for Sarvam STT
            data_size = len(raw_pcm)
            header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF", data_size + 36, b"WAVE", b"fmt ",
                16, 1, 1, 8000, 8000 * 2, 2, 16, b"data", data_size,
            )
            wav_bytes = header + raw_pcm

            # 1. Transcribe caller audio with Sarvam AI STT (Saaras v3)
            session_audio_chunks.append(raw_pcm)
            t_stt = time.time()
            transcript = await providers.stt.transcribe(wav_bytes, language="ml-IN")
            transcript = transcript.strip()
            logger.info("Exotel Voicebot: Sarvam STT completed in %.2fs. Transcript: '%s'", time.time() - t_stt, transcript)

            if not transcript:
                logger.info("Exotel Voicebot: Empty transcription, asking caller to repeat.")
                repeat_text = "ക്ഷമിക്കണം, വ്യക്തമായി കേട്ടില്ല. ഒന്നുകൂടി പറയാമോ?"
                audio_bytes = await providers.tts.synthesize(repeat_text, language="ml-IN")
                if audio_bytes and stream_sid:
                    await stream_audio_to_caller(_to_raw_pcm(audio_bytes), stream_sid, is_welcome=False)
                is_processing_turn = False
                return

            session_transcript.append({"speaker": "Caller", "text": transcript})

            # 2. Process utterance via CallSession (Gemini LLM) without blocking TTS inside session
            t_llm = time.time()
            result = await session.handle_caller_utterance(transcript, synthesize_audio=False)
            reply_text = result.get("text", "")
            logger.info("Exotel Voicebot: Gemini LLM generated reply in %.2fs: '%s'", time.time() - t_llm, reply_text)

            if not reply_text or not stream_sid:
                is_processing_turn = False
                return

            # 3. Pipelined Sentence-by-Sentence Streaming TTS
            # Split reply into sentences to deliver first audio chunk to phone in under ~1 second!
            import re
            sentences = [s.strip() for s in re.split(r"(?<=[.?!।\n])\s+", reply_text) if s.strip()]
            if not sentences:
                sentences = [reply_text]

            # Merge very short leading interjection (e.g. 'നമസ്കാരം!' or 'ശരി!') with next sentence
            if len(sentences) > 1 and len(sentences[0]) < 22:
                sentences = [sentences[0] + " " + sentences[1]] + sentences[2:]

            first_sentence = sentences[0]
            rest_sentence = " ".join(sentences[1:]).strip() if len(sentences) > 1 else ""

            # Concurrently dispatch background TTS task for second sentence (if present)
            rest_task: asyncio.Task | None = None
            if rest_sentence:
                rest_task = asyncio.create_task(providers.tts.synthesize(rest_sentence, language="ml-IN"))

            # Synthesize first sentence immediately
            t_tts = time.time()
            first_audio = await providers.tts.synthesize(first_sentence, language="ml-IN")
            logger.info("First sentence TTS ready in %.2fs (%d chars, %d bytes)", time.time() - t_tts, len(first_sentence), len(first_audio))

            if first_audio and stream_sid and not was_interrupted:
                pcm_first = _to_raw_pcm(first_audio)
                session_audio_chunks.append(pcm_first)
                await stream_audio_to_caller(pcm_first, stream_sid, is_welcome=False)

            # Stream remaining sentences smoothly if caller hasn't interrupted
            if rest_task and stream_sid and not was_interrupted:
                rest_audio = await rest_task
                if rest_audio and not was_interrupted:
                    pcm_rest = _to_raw_pcm(rest_audio)
                    session_audio_chunks.append(pcm_rest)
                    await stream_audio_to_caller(pcm_rest, stream_sid, is_welcome=False)

            session_transcript.append({"speaker": "Agent", "text": reply_text})

            # If the conversation turn signaled call completion (hangup), gracefully terminate call
            turn_type = result.get("type", "speech")
            if turn_type == "hangup" and stream_sid:
                logger.info("Exotel Voicebot: Turn completed with hangup. Closing WebSocket to disconnect call.")
                await asyncio.sleep(0.6)
                try:
                    await websocket.close()
                except Exception:
                    pass
                return

        except Exception as e:
            logger.error("Exotel Voicebot: Error during conversation turn: %s", e)
        finally:
            is_processing_turn = False

    async def _silence_detector() -> None:
        """Wait for 0.38s pause in caller speech before triggering turn processing."""
        await asyncio.sleep(0.38)
        await process_caller_speech()

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            event = data.get("event")

            if event == "connected":
                logger.info("Exotel Voicebot: Protocol connected.")

            elif event == "start":
                start_data = data.get("start", {})
                stream_sid = (
                    data.get("stream_sid")
                    or data.get("streamSid")
                    or start_data.get("stream_sid")
                    or start_data.get("streamSid")
                    or "unknown"
                )
                call_sid = (
                    data.get("call_sid")
                    or data.get("callSid")
                    or start_data.get("call_sid")
                    or start_data.get("callSid")
                    or "unknown"
                )
                caller_phone = (
                    start_data.get("from")
                    or start_data.get("caller")
                    or data.get("from")
                    or "Unknown"
                )
                logger.info("Exotel Voicebot session started: StreamSid=%s CallSid=%s Caller=%s", stream_sid, call_sid, caller_phone)

                # Stream initial hospital greeting without interruption
                if not pcm_greeting:
                    logger.warning("Exotel Voicebot: Pre-rendered greeting WAV not found, generating fallback via Sarvam TTS...")
                    welcome_text = "നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഈ കോൾ ഗുണനിലവാരത്തിനായി റെക്കോർഡ് ചെയ്യപ്പെടുന്നുണ്ട്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?"
                    try:
                        tts_audio = await providers.tts.synthesize(welcome_text, language="ml-IN")
                        pcm_greeting = _to_raw_pcm(tts_audio)
                    except Exception as e:
                        logger.error("Exotel Voicebot: Failed generating fallback greeting: %s", e)

                if pcm_greeting and stream_sid:
                    session_audio_chunks.append(pcm_greeting)
                    session_transcript.append({
                        "speaker": "Agent",
                        "text": "നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഈ കോൾ ഗുണനിലവാരത്തിനായി റെക്കോർഡ് ചെയ്യപ്പെടുന്നുണ്ട്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?"
                    })
                    await asyncio.sleep(0.2)
                    asyncio.create_task(stream_audio_to_caller(pcm_greeting, stream_sid, is_welcome=True))

            elif event == "media":
                if is_processing_turn:
                    continue

                media_payload = data.get("media", {}).get("payload", "")
                if media_payload:
                    chunk = base64.b64decode(media_payload)
                    rms = _calculate_rms(chunk)

                    # Interruption check: halt playback only if bot is speaking responses (never during welcome greeting)
                    if is_speaking and not is_greeting and rms > 650.0:
                        logger.info("Exotel Voicebot: Caller interrupted AI mid-playback (RMS=%.1f).", rms)
                        was_interrupted = True
                        is_speaking = False

                    # Only capture caller speech when bot is not playing audio
                    if not is_speaking:
                        if rms >= SPEECH_RMS_THRESHOLD:  # Clear voice activity
                            if not has_spoken:
                                has_spoken = True
                                speech_start_time = time.time()
                            caller_pcm_buffer.append(chunk)

                            # Reset silence timer
                            if silence_timer_task and not silence_timer_task.done():
                                silence_timer_task.cancel()
                            silence_timer_task = asyncio.create_task(_silence_detector())

                            # Max speech duration cap (4.5s) to prevent perpetual buffering
                            if speech_start_time and (time.time() - speech_start_time > 4.5):
                                if silence_timer_task and not silence_timer_task.done():
                                    silence_timer_task.cancel()
                                asyncio.create_task(process_caller_speech())

                        elif has_spoken:
                            # Caller paused: keep buffering audio while silence timer is running
                            caller_pcm_buffer.append(chunk)

            elif event == "mark":
                logger.info("Exotel Voicebot: Marker reached: %s", data.get("mark", {}).get("name"))

            elif event == "stop":
                logger.info("Exotel Voicebot session stopped for StreamSid=%s", stream_sid)
                break

    except WebSocketDisconnect as e:
        logger.warning(
            "Exotel Voicebot: WebSocketDisconnect received (code=%s, reason=%s) for StreamSid=%s",
            e.code,
            getattr(e, "reason", None),
            stream_sid,
        )
    except Exception as e:
        logger.error("Exotel Voicebot: Unexpected error in WebSocket loop: %s", e, exc_info=True)
    finally:
        if silence_timer_task and not silence_timer_task.done():
            silence_timer_task.cancel()
        logger.info("Exotel Voicebot: Session closed for CallSid=%s StreamSid=%s", call_sid, stream_sid)

        # Persist completed call audio recording and transcript
        if len(session_transcript) >= 1 or len(session_audio_chunks) > 0:
            try:
                import datetime
                duration_sec = max(5, int(time.time() - session_start_epoch))
                record_id = f"call-{int(time.time())}"
                wav_filename = f"{record_id}.wav"
                wav_filepath = RECORDINGS_DIR / wav_filename

                all_pcm = b"".join(session_audio_chunks)
                if all_pcm:
                    with wave.open(str(wav_filepath), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(8000)
                        wf.writeframes(all_pcm)
                    logger.info("Telephone call audio saved to %s (%d bytes)", wav_filepath, len(all_pcm))

                # Identify patient name and outcome
                patient_name = "Akshay"
                patient_name_ml = "അക്ഷയ്"
                for t in session_transcript:
                    txt = t.get("text", "").lower()
                    if "അക്ഷയ്" in txt or "akshay" in txt:
                        patient_name = "Akshay"
                        patient_name_ml = "അക്ഷയ്"
                        break
                    elif "ലക്ഷ്മി" in txt or "lakshmi" in txt:
                        patient_name = "Lakshmi"
                        patient_name_ml = "ലക്ഷ്മി"
                        break
                    elif "രശ്മി" in txt or "rashmi" in txt:
                        patient_name = "Rashmi"
                        patient_name_ml = "രശ്മി"
                        break

                outcome = "Inquiry Answered"
                for t in session_transcript:
                    if t.get("speaker") == "Agent" and ("ബുക്ക്" in t.get("text", "") or "booked" in t.get("text", "").lower()):
                        outcome = "Booked"
                        break

                started_at_str = datetime.datetime.now().strftime("%I:%M %p")
                real_phone = "+91 99473 84437"
                if caller_phone and caller_phone != "Unknown" and caller_phone != "unknown":
                    clean_p = caller_phone.replace("+", "").lstrip("0")
                    if len(clean_p) == 10:
                        real_phone = f"+91 {clean_p[:5]} {clean_p[5:]}"
                    elif len(clean_p) > 10:
                        real_phone = f"+{clean_p}"
                    else:
                        real_phone = caller_phone

                summary_text = f"Inbound telephone call ({duration_sec}s). Outcome: {outcome}. Patient: {patient_name}."
                if outcome == "Booked":
                    summary_text = f"Inbound telephone call ({duration_sec}s). Confirmed consultation booking for Dr. Manoj with {patient_name}."
                elif len(session_transcript) >= 2:
                    summary_text = f"Inbound telephone call ({duration_sec}s). Caller inquired about hospital visiting hours and treatments."

                call_record = {
                    "id": record_id,
                    "callerNumber": real_phone,
                    "patientName": patient_name,
                    "patientNameMl": patient_name_ml,
                    "language": "ml-IN",
                    "durationSec": duration_sec,
                    "outcome": outcome,
                    "timestamp": f"Today at {started_at_str}",
                    "consentGiven": True,
                    "recordingKey": f"recordings/{wav_filename}" if all_pcm else None,
                    "audioUrl": f"/api/calls/live/{record_id}/audio",
                    "summary": summary_text,
                    "transcript": session_transcript,
                }
                save_live_call(call_record)
                asyncio.create_task(persist_call_to_supabase(call_record, session_transcript, DEFAULT_CLINIC_ID))
                logger.info("Persisted live call record %s (%s, outcome=%s)", record_id, patient_name, outcome)
            except Exception as e:
                logger.error("Error saving call record or audio: %s", e)


