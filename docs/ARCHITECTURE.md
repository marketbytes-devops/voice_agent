# ClinicVoice System Architecture (ARCHITECTURE.md)

**Product Working Name:** ClinicVoice  
**Launch Partner:** Sreerudra Ayurveda Hospital & Research Centre, Alappuzha, Kerala  
**Version:** 1.0 (Phase 4 Complete)  

---

## 1. High-Level Architecture Overview

```text
[ Patient Phone (Kerala) ]
           │
           ▼ (Cellular E.164)
  [ Exotel SIP Trunk ]
           │
           ▼ (SIP over TLS/SRTP)
[ LiveKit Voice Gateway ] ──► [ VoiceAgentWorker ]
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
          [ Speech Pipeline ]                 [ Backend Tools ]
          - Silero VAD                        - find_or_create_patient
          - Sarvam STT (ml-IN / en-IN)        - get_free_slots
          - Claude / GPT / Gemini LLM         - book_appointment
          - Sarvam Bulbul TTS (ananya/meera)  - escalate_emergency
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    ▼
                [ FastAPI Application (Backend API) ]
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
  [ PostgreSQL + RLS ]      [ Redis Caching ]       [ Storage & Sweeper ]
  - Tenant isolation        - Session state         - MinIO / AWS S3
  - Audit logging           - Rate limiting         - 30-day retention
  - Booking locks           - Fast queues           - Purge cron worker
                                    ▲
                                    │ (REST / JSON)
                        [ Next.js Staff Dashboard ]
                        - Realtime quick stats
                        - Call recordings & waveform audio
                        - Turn-by-turn bilingual transcripts
                        - Doctor timetable & calendar slots
```

---

## 2. Core Subsystems

### 2.1 Backend API (`backend/app/`)
* **Framework:** FastAPI with asynchronous ASGI handlers and Python 3.12 strict typing.
* **Security & RLS:** PostgreSQL Row-Level Security ensures that tenant queries are scoped to `app.clinic_id`.
* **Rate Limiting:** Sliding-window limiter on sensitive endpoints (`/auth/login`) protecting against brute force.
* **Audit Logging:** Immutable audit entries recorded in `audit_log` whenever patient data or audio recordings are accessed.
* **Log Sanitization:** Regex-based filter (`SensitiveDataFilter`) redacts all Indian phone numbers (`+91 98****3210`) in technical logs.

### 2.2 Storage & Retention Automation (`backend/app/services/`)
* **Storage Service (`storage_service.py`):** Path traversal validated (`^[a-zA-Z0-9_\-\./]+$`), generates 15-minute expiring signed URLs.
* **Retention Sweeper (`retention_sweeper.py`):** Nightly automated cleanup purging raw audio older than `RECORDING_RETENTION_DAYS` (30 days) while preserving call metadata, summaries, and transcripts.

### 2.3 Voice Agent Core (`backend/agent/`)
* **LiveKit SIP Integration:** Receives inbound telephone streams.
* **Consent Gating (`recording.py`):** Audio is kept in-memory; persisted to storage only if caller gives explicit recording consent.
* **Bilingual Engine (`language.py`):** Dynamic switching between Malayalam (`ml-IN`), English (`en-IN`), and Manglish.
* **Guardrails:** Refuses medical advice / drug prescriptions and escalates life-threatening emergencies immediately.

### 2.4 Staff Web Dashboard (`frontend/`)
* **Framework:** Next.js 14 App Router, React 18, Tailwind CSS, Lucide icons.
* **Pages:** Home (`/`), Calls (`/calls`), Appointments (`/appointments`), Knowledge Base (`/knowledge`), Settings (`/settings`).
* **Audio Player:** Waveform visualization with signed MinIO playback links.
