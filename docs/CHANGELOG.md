# Changelog (CHANGELOG.md)

All notable changes to the ClinicVoice platform will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
