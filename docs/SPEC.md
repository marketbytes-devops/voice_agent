# ClinicVoice: Technical Specification
**Version:** 1.0 (Draft)  
**First Customer / Design Partner:** Sreerudra Ayurveda Hospital and Research Centre, Alappuzha, Kerala  

---

## 4.1 Goals and Non-Goals
### Goals
- Reliable inbound answering in Malayalam (`ml-IN`) and English (`en-IN`) 24/7.
- Correct appointment booking, rescheduling, and cancellation against real doctor schedules.
- Strict security and privacy for patient sensitive health data (DPDP Act, 2023 alignment).
- Usable staff web dashboard for appointments, calls, patients, doctor schedules, and knowledge base.
- Multi-tenant architecture from day one: add new clinics via configuration without code changes.

### Non-Goals for Version 1
- Self-service onboarding and automated billing.
- WhatsApp automation and outbound marketing campaigns.
- Automated reminder calls.
- Deep integration with legacy Hospital Management Software (HMS/EHR).

---

## 4.2 Repository Layout
```
clinicvoice/
  AGENTS.md
  README.md
  PROGRESS.md
  docker-compose.yml
  .env.example
  docs/
    SPEC.md
    ARCHITECTURE.md
    DECISIONS.md
    CHANGELOG.md
    RUNBOOK.md
  backend/
    app/                  FastAPI backend
      main.py
      core/               settings, security, db session, logging
      models/             SQLAlchemy 2.0 async models
      schemas/            Pydantic v2 schemas
      api/                routers (auth, clinics, doctors, patients, appointments, calls, tasks, faq)
      services/           slots, booking, patients, calls, recordings, messaging
    agent/                LiveKit voice agent worker & mock caller
      main.py             worker entrypoint
      mock_caller.py      telephony mock caller
      session.py          call lifecycle
      providers/          stt, llm, tts interfaces + implementations
      tools.py            function tools that call the backend
      prompts/            prompt builder (ml/en rules, boundaries)
      language.py         language selection and switching
      recording.py        consent-gated recording
    evals/                scripted voice conversations & benchmarks
      voice_evals.py      8 realistic clinic dialogue evaluations
      stt_bench/
      tts_bench/
      llm_tool_bench/
    alembic/              PostgreSQL database migrations with RLS
    tests/                unit & integration test suite
  frontend/               Next.js 14 staff web dashboard (App Router)
    src/
      app/                pages (home, calls, appointments, knowledge, settings)
      components/pages/   modular page sections (home, calls, appointments, knowledge, settings)
      components/ui/      reusable atomic UI primitives (Button, Card, Badge, AudioPlayer)
    tests/                dashboard routes verification
```

---

## 4.3 Architecture
```
Caller -> Exotel -> SIP -> LiveKit room -> Agent worker
                                            |-- Silero VAD
                                            |-- STT provider   (Sarvam first)
                                            |-- LLM provider   (chosen after tests)
                                            |-- TTS provider   (Sarvam Bulbul first)
                                            |-- Tools -> Backend API (FastAPI) -> PostgreSQL
Backend -> Redis queue -> workers: summary, SMS, retention
Backend -> Object storage: recordings (private MinIO / S3)
Dashboard (Next.js) -> Backend API
```
*Note on future evolution:* Structured to allow swapping VAD+STT+LLM+TTS with a unified Realtime Audio model (e.g. Gemini Live) without changing tools, database, or dashboard.

---

## 4.4 Call Lifecycle
1. **Inbound Call:** Exotel sends call over SIP to LiveKit room; LiveKit dispatches agent worker.
2. **Context Resolution:** Worker reads dialed number, resolves clinic via `/internal/agent/resolve-clinic`, and loads clinic working hours, doctors, treatments, and FAQs.
3. **Caller Lookup:** Worker queries caller's phone number and creates a `calls` record.
4. **Greeting & Consent:** Agent greets in Malayalam and English, announces AI identity, and requests recording consent. Consent is logged in `consent_log`. Audio recording starts ONLY if consent is given.
5. **Streaming Conversation:** VAD + STT + LLM + TTS. Interruptions immediately stop agent playback, cancel generation, and trim history to what was actually spoken.
6. **Backend Tools:** Agent executes function tools via authenticated backend API calls.
7. **Call Wrap-up:** Worker closes call. Backend enqueues after-call jobs: save transcript, store recording key, generate structured summary/outcome, and enqueue confirmation SMS.
8. **Dashboard Visibility:** Staff immediately view call records, recordings, and appointments.

*Failure & Edge Cases:*
- Provider failure/timeout: short fallback apology + transfer to clinic fallback phone or callback creation.
- Caller silence: prompt twice politely, then end call and log callback task.
- Consent refused: continue call normally with recording disabled.

---

## 4.5 Provider Interface (Python)
```python
from __future__ import annotations
from typing import Protocol

class SpeechToText(Protocol):
    name: str
    languages: list[str]  # e.g. ["ml-IN", "en-IN"]

class LanguageModel(Protocol):
    name: str
    supports_tools: bool

class TextToSpeech(Protocol):
    name: str
    def voice_for(self, language: str) -> str: ...

class ProviderSet:
    stt: SpeechToText
    llm: LanguageModel
    tts: TextToSpeech

def build_providers(clinic_settings: AgentSettings) -> ProviderSet:
    """Instantiate providers based on per-clinic database configuration."""
    ...
```

---

## 4.6 Agent Tools
All tools are asynchronous, authenticated via internal service token, and return generic safe messages.

| Tool | Inputs | Returns | Backend Guardrail |
| :--- | :--- | :--- | :--- |
| `find_or_create_patient` | name, phone, age, gender, place, preferred_language, confirmed (bool) | `patient_id`, `is_returning` | Requires `confirmed=true`; matches by phone within clinic tenant |
| `get_free_slots` | `doctor_id` or `treatment_id`, date or date range | `list[slots]` | Computed from schedules, leave, break hours, and existing bookings |
| `book_appointment` | `patient_id`, `doctor_id`, `treatment_id`, `start`, `reason`, `visit_type` | `appointment_id` or error | DB transaction with row lock; re-validates slot; rejects past/closed dates; unique constraint on `(doctor_id, starts_at)` |
| `reschedule_appointment` | `appointment_id`, `new_start` | `ok` or error | Verifies caller owns appointment; same re-validation rules |
| `cancel_appointment` | `appointment_id` | `ok` or error | Verifies ownership |
| `get_clinic_info` | `topic` or `question` | approved answer or `none` | Strictly from `faq_entries` and `treatments`; `none` prompts offer for callback |
| `transfer_call` | `reason` | `ok` or fallback | Only during working hours; otherwise creates callback task |
| `request_callback` | `reason`, `preferred_time` | `task_id` | Saves in `callback_tasks` |
| `escalate_emergency` | `summary` | `ok` | Plays urgent medical disclaimer and immediately transfers to emergency staff |

---

## 4.7 Database Schema (Core Tables)
PostgreSQL with UUID primary keys, timestamptz stored in UTC, clinic timezone applied at the boundary.

- `organisations` (id, name, plan, status, created_at)
- `clinics` (id, organisation_id, name, address, timezone, working_hours, languages, fallback_phone, created_at)
- `users` (id, organisation_id, clinic_id, name, email, password_hash, role, status)
- `phone_numbers` (id, clinic_id, e164, provider, status)
- `agent_settings` (clinic_id, greeting_ml, greeting_en, voice, language_mode, providers, prompt_additions, interruption)
- `doctors` (id, clinic_id, name, qualification, specialties, active)
- `doctor_schedules` (id, clinic_id, doctor_id, weekday, start_time, end_time, slot_minutes, break_start, break_end)
- `doctor_leave` (id, clinic_id, doctor_id, starts_at, ends_at, reason)
- `treatments` (id, clinic_id, name_en, name_ml, description_en, description_ml, duration_minutes, needs_doctor_review, active)
- `faq_entries` (id, clinic_id, question, answer, language, active)
- `patients` (id, clinic_id, name, name_ml, phone, alt_phone, age, gender, place, preferred_language, notes, created_at)
- `appointments` (id, clinic_id, patient_id, doctor_id, treatment_id, visit_type, reason, starts_at, ends_at, status, source, call_id, created_by)
- `calls` (id, clinic_id, patient_id, caller_number, language, started_at, ended_at, duration_sec, outcome, summary, transcript, recording_key, cost)
- `call_events` (id, clinic_id, call_id, at, type, data)
- `callback_tasks` (id, clinic_id, call_id, patient_id, reason, preferred_time, status, assigned_to)
- `consent_log` (id, clinic_id, call_id, type, given, at)
- `messages` (id, clinic_id, patient_id, channel, template, status, sent_at)
- `audit_log` (id, clinic_id, user_id, action, record, at)

### PostgreSQL Row-Level Security Pattern:
```sql
alter table patients enable row level security;
create policy tenant_isolation on patients
  using (clinic_id = current_setting('app.clinic_id')::uuid);
```

---

## 4.8 API Outline
- **Auth:** `/auth/login`, `/auth/refresh`, `/auth/logout`
- **Clinics & Settings:** `GET / PATCH /clinics/{id}`, `GET / PATCH /clinics/{id}/agent-settings`
- **Doctors & Schedules:** CRUD `/doctors`, `/doctors/{id}/schedules`, `/doctors/{id}/leave`
- **Content:** CRUD `/treatments`, CRUD `/faqs`
- **Patients:** `GET /patients?query=`, `GET / PATCH /patients/{id}`
- **Appointments & Slots:** `GET /appointments`, `POST / PATCH / DELETE /appointments/{id}`, `GET /slots`
- **Calls & Audio:** `GET /calls`, `GET /calls/{id}`, `GET /calls/{id}/recording-link`
- **Tasks:** `GET /callback-tasks`, `PATCH /callback-tasks/{id}`
- **Internal Agent:** `POST /internal/agent/resolve-clinic`, `POST /internal/agent/tools/{tool}`, `POST /internal/agent/call-events`
- **Telephony Webhooks:** `POST /webhooks/exotel/voice`, `POST /webhooks/exotel/status`
- **Health:** `GET /health`, `GET /ready`

---

## 4.9 Language & Localization Rules
- Greet in Malayalam and English. Determine language from caller's response, or politely ask preference.
- Support seamless code-switching (Manglish).
- Read back names, phone numbers, and dates slowly in caller's preferred language; prompt for confirmation.
- Store names in Malayalam script and Roman transliteration.

---

## 4.10 Interruption Handling
- Continuous Silero VAD.
- When caller speaks: cut agent audio immediately, cancel in-flight model stream, drop unvoiced tokens from history.
- Tunable thresholds: minimum speech duration (filter coughs/fillers) and silence window.

---

## 4.11 Recording & Privacy
- Audio kept in memory during call; written to private S3/MinIO bucket only if consent was given.
- S3 key format: `{clinic_id}/{yyyy}/{mm}/{call_id}.ext`.
- Recordings delivered via short-lived signed URLs (15-min expiry) with role-based checks.
- Scheduled retention sweeper purges recordings older than `RECORDING_RETENTION_DAYS`.
- No PII, phone numbers, or transcripts logged in standard stdout/stderr logs.
