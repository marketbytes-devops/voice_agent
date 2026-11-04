# Changelog (CHANGELOG.md)

All notable changes to the ClinicVoice platform will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Phase 8] - 2026-11-04
### Added
- **Automatic Client-Side VAD & 16kHz WAV Encoding:** Implemented real-time Web Audio API voice activity detection (VAD) and in-memory 16-bit 16kHz linear PCM WAV encoder, enabling automatic speech transmission on 600ms pause without requiring button presses.
- **Dynamic Audio Format Detection for Sarvam STT:** Added magic byte detection in `SarvamSTTAdapter` to dynamically identify WebM, WAV, MP3, and OGG formats before sending to Sarvam Saaras v3.
- **Direct Live Web Voice Call Tester (Option A):** Built full-duplex WebSocket endpoint (`/api/voice/web-call`) and interactive web call studio (`frontend/src/app/test-call/page.tsx`), enabling zero-PIN, zero-delay testing directly with microphone and speakers.
- **Client-Side Instant Barge-in:** Real-time audio halt in browser when user speaks during AI speech, synchronizing with Sarvam AI and Gemini.
- **Interactive Testing Studio:** Live Malayalam transcript, visual voice activity meter, quick test prompts for Dr. Manoj's schedule, appointment bookings, treatment inquiries, and emergency escalation.
- **Instant Human-like Interruption (Real-Time Barge-in):** Lowered voice activity threshold from 650.0 to 340.0 RMS, sent carrier-level `event: clear` on interruption to immediately flush telecom gateway audio buffers, and captured initial interruption audio frame directly into the new caller speech turn.
- **Natural Clarification Handling:** Added detection for inaudible, garbled, or noisy speech, automatically requesting polite Malayalam clarification (*"ക്ഷമിക്കണം, പറഞ്ഞത് വ്യക്തമായി കേട്ടില്ല. ഒന്നുകൂടി പറയാമോ?"*) instead of hallucinating or hanging up.
- **Line Check Handling:** Direct warm acknowledgment for connectivity queries ("ഹലോ", "കേൾക്കാമോ?"): *"നമസ്കാരം, ഞാൻ കേൾക്കുന്നുണ്ട്. പറയൂ, എന്താണ് അറിയേണ്ടത്?"*.
- **Tuned Turn-taking VAD:** Extended silence detection from 0.38s to 0.55s, giving callers conversational breathing room and preventing mid-sentence cut-offs.
- **Conversational Receptionist Guardrails:** Injected strict conversational guidelines in Malayalam and English system prompts enforcing 1-2 sentence concise answers and forbidding disconnects on conversational filler words ("ശരി", "ഓക്കേ").
- **Extended Silence Tolerance:** Increased silence threshold to 4 consecutive turns before triggering a callback offer, eliminating ghost disconnects.

---

## [Phase 7] - 2026-11-02
### Added
- **Managed Cloud Database (Supabase Mumbai / ap-south-1):** Provisioned PostgreSQL 17 in AWS Mumbai for ultra-low latency with Indian cellular lines, creating all 18 tables with Row-Level Security (RLS) tenant isolation.
- **Automated Schema & Seeding Engine:** Created `backend/scripts/init_db.py` and `backend/scripts/seed_clinic.py` seeding Sreerudra Ayurveda Hospital, Dr. Manoj, Monday–Saturday schedules (9 AM – 5 PM with lunch break exclusion), treatments, and bilingual FAQs.
- **In-Process Database Tool Execution:** Upgraded `AgentToolExecutor` (`backend/agent/tools.py`) to execute `get_free_slots` and `book_appointment` directly against Supabase in sub-15ms without HTTP loopback latency.
- **Dynamic Telephony Persistence:** Updated `backend/app/api/webhooks_exotel.py` to persist completed call records, turn-by-turn transcripts, and confirmed bookings with row-level locks directly into Supabase `calls` and `appointments` tables.
- **Dashboard Data Endpoints:** Added `/api/appointments` and `/api/doctors` to `backend/app/main.py` enabling the staff dashboard to retrieve live calendar data.
- **Live Next.js Dashboard Calendar:** Connected appointments timetable (`frontend/src/app/appointments`) and today's schedule (`frontend/src/components/pages/home`) to dynamic backend endpoints with live Supabase status indicator and doctor filter.

---

## [Phase 6] - 2026-10-28
### Added
- **Live Exotel Telephony AudioStreams Gateway:** Built full-duplex WebSocket bridge (`/webhooks/exotel/voicebot`) interfacing telecom virtual number (`04954269761`) directly with Sarvam AI and Gemini.
- **Pipelined Low-Latency Streaming TTS:** Pipelined sentence-by-sentence audio synthesis via Sarvam Bulbul TTS, delivering first-sentence audio playback in ~1.0s while synthesizing subsequent sentences concurrently.
- **Automatic Call Completion & Disconnect:** Added intelligent farewell detector and `[END_CALL]` signal triggering clean telecom carrier hangup when caller concludes the inquiry with closing phrases ("ശരി", "നന്ദി", "ഓക്കേ", "thank you").
- **Dynamic Hospital Knowledge Base:** Integrated centralized `hospital_knowledge.json` for Sreerudra Ayurveda Hospital into Gemini prompts with `/api/knowledge` upload endpoints.
- **Production Connection Pooling:** Reusable `httpx.AsyncClient` connection pools across Sarvam STT, Gemini LLM, and Sarvam TTS eliminating SSL handshake latencies.

### Changed
- **Sarvam STT Model:** Upgraded from `saaras:v1` to `saaras:v3` for improved Malayalam speech recognition.
- **Voice Tempo & Cadence:** Configured Sarvam Bulbul pace to `1.10` for brisk, natural conversational delivery.
- **Silence VAD:** Tuned pause threshold from 800ms down to 380ms for responsive turn turnaround.

---

## [Phase 5] - 2026-10-26
### Added
- **Exotel Inbound Telephony Webhook:** Implemented `POST /webhooks/exotel/voice` returning LiveKit Inbound SIP forwarding URI (`backend/app/api/webhooks_exotel.py`).
- **Emergency Human Fallback Circuit:** Built dual-dial fallback into Exotel responses, automatically diverting caller to Sreerudra hospital front desk (`+91 477 225 1234`) if voice agent is degraded.
- **Exotel Call Status & CDR Webhook:** Added `POST /webhooks/exotel/status` tracking call completion and telecom metrics.
- **End-to-End Pilot Call Simulator:** Built multi-turn interactive simulator (`backend/agent/pilot_call_simulator.py`) covering greeting, Malayalam consent, schedule inquiry, slot booking, and reference ID readback.
- **Phase 5 Automated Test Suite:** Added unit and integration tests (`backend/tests/test_phase5_pilot_and_telephony.py`) verifying Exotel webhook routing, fallback, and pilot simulation.

---

## [Phase 4] - 2026-10-26
### Added
- **Audio Retention Sweeper:** Automated service (`backend/app/services/retention_sweeper.py`) deleting audio recordings older than 30 days while preserving metadata and transcripts.
- **Storage Service:** Validated storage key generator (`backend/app/services/storage_service.py`) supporting 15-minute signed URLs.
- **Rate Limiting:** Sliding-window rate limiter middleware (`backend/app/core/rate_limit.py`) on `/auth/login` and sensitive endpoints.
- **Audit Logging Service:** Automated immutable audit log generator (`backend/app/services/audit_service.py`) tracking access to patient records, calls, and audio playback.
- **Calls & Recording API:** Added `/calls`, `/calls/{id}`, and `/calls/{id}/recording-link` routers (`backend/app/api/calls.py`).
- **Disaster Recovery Scripts:** Created automated backup/restore scripts (`scripts/backup_db.ps1`, `scripts/backup_db.sh`, `scripts/restore_db.ps1`, `scripts/restore_db.sh`).
- **Operational Runbook:** Added comprehensive production runbook (`docs/RUNBOOK.md`) covering Exotel SIP, human fallback, DPDP Act compliance, and recovery drills.
- **Phase 4 Automated Tests:** Added 5 new security, retention, and rate-limiting tests (`backend/tests/test_phase4_security_and_retention.py`).

### Changed
- **Log Sanitization:** Enhanced `SensitiveDataFilter` to mask all variations of Indian phone numbers (`+91 98****3210`).
- **Main Router:** Mounted `calls_router` in `backend/app/main.py`.

---

## [Phase 3] - 2026-10-26
### Added
- Next.js 14 App Router staff dashboard in `frontend/`.
- 5 modular page sections under `src/components/pages/home/` (`QuickStatsSection`, `TodayAppointmentsSection`, `RecentCallsSection`, `CallbackTasksSection`, `LiveAgentStatusSection`).
- Calls player with waveform animation and bilingual transcript viewer (`/calls`).
- Doctor calendar and slot management (`/appointments`).
- Dual-language treatments and FAQ editor (`/knowledge`).
- Voice model timbre and greeting selector (`/settings`).
- Standardized top-level layout into clean `backend/` and `frontend/` directories.

---

## [Phase 2] - 2026-10-26
### Added
- Voice Agent Core with Silero VAD, streaming dialogue, and interruption handling.
- Guarded booking engine with row-lock transactions preventing slot double-booking.
- Malayalam, English, and Manglish intent detection and language switching.
- Safety guardrails: strict medical advice refusal and life-threatening emergency escalation.
- 8 automated voice evaluation scenarios (`backend/evals/voice_evals.py`).
- Interactive voice sandbox (`backend/agent/sandbox/index.html`).

---

## [Phase 1] - 2026-10-26
### Added
- Multi-tenant PostgreSQL database schema with Row-Level Security (RLS).
- FastAPI backend application with authentication and role-based permissions.
- Telephony mock caller (`backend/agent/mock_caller.py`).
- Docker Compose setup for PostgreSQL, Redis, and MinIO.

---

## [Phase 0] - 2026-10-26
### Added
- Technical specification (`docs/SPEC.md`).
- Operational decisions log (`docs/DECISIONS.md`).
- Malayalam speech-to-text and text-to-speech benchmark evaluations.
