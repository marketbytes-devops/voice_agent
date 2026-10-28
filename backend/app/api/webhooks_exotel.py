from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path
import struct
import time
from typing import Any, AsyncGenerator
import wave

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.providers.factory import build_providers
from backend.agent.session import CallSession


from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models import Clinic, PhoneNumber

logger = logging.getLogger("clinicvoice")


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
                select(PhoneNumber).where(PhoneNumber.e164 == To, PhoneNumber.status == "active")
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
    ]
    for p in audio_paths:
        if p.exists():
            try:
                with wave.open(str(p), "rb") as w:
                    return w.readframes(w.getnframes())
            except Exception as e:
                logger.warning("Failed reading audio file %s: %s", p, e)
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
    pcm_greeting = _load_pcm_greeting()

    # Initialize clinical session context
    clinic_context = {
        "clinic_id": "clinic-sreerudra-01",
        "clinic_name": "Sreerudra Ayurveda Hospital & Research Centre",
        "timezone": "Asia/Kolkata",
        "working_hours": {"0": {"start": "09:00", "end": "17:00"}},
        "languages": ["ml-IN", "en-IN"],
        "doctors": [
            {
                "id": "doc-manoj-01",
                "name": "Dr. Manoj",
                "qualification": "BAMS, MD (Ayurveda)",
                "specialties": ["Panchakarma", "General Ayurveda"],
            }
        ],
        "treatments": [
            {"name": "Panchakarma Consultation", "duration_minutes": 30},
            {"name": "General Ayurveda Consultation", "duration_minutes": 15},
        ],
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
                await stream_audio_to_caller(pcm_first, stream_sid, is_welcome=False)

            # Stream remaining sentences smoothly if caller hasn't interrupted
            if rest_task and stream_sid and not was_interrupted:
                rest_audio = await rest_task
                if rest_audio and not was_interrupted:
                    pcm_rest = _to_raw_pcm(rest_audio)
                    await stream_audio_to_caller(pcm_rest, stream_sid, is_welcome=False)

        except Exception as e:
            logger.error("Exotel Voicebot: Error during conversation turn: %s", e)
        finally:
            is_processing_turn = False

    async def _silence_detector() -> None:
        """Wait for 0.45s pause in caller speech before triggering turn processing."""
        await asyncio.sleep(0.45)
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
                logger.info("Exotel Voicebot session started: StreamSid=%s CallSid=%s", stream_sid, call_sid)

                # Stream initial hospital greeting without interruption
                if pcm_greeting:
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


