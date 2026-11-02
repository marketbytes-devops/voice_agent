# ClinicVoice Technical Project Audit

**Date of Audit:** October 2026  
**Audited Target:** `voice-agent` repository  
**Target Client:** Sreerudra Ayurveda Hospital & Research Centre, Alappuzha, Kerala  
**Auditor:** Automated Agentic System (Strict Read-Only Inspection)

---

## 1. Repository Map

### 1.1 Directory Structure (3-Level Tree)

```text
voice-agent/
├── AGENTS.md                          # Coding standards, style rules, security and testing policies
├── README.md                          # Project introduction and quickstart guide
├── PROGRESS.md                        # Phase-by-phase completion roadmap
├── docker-compose.yml                 # Local development environment (Postgres, Redis, MinIO)
├── requirements.txt                   # Top-level Python dependency pointer (-r backend/requirements.txt)
├── .env.example                       # Committed template of configuration variable names
│
├── docs/                              # Project documentation and specifications
│   ├── SPEC.md                        # Master functional and technical specification (source of truth)
│   ├── ARCHITECTURE.md                # System topology, sequence diagrams, and architecture blueprints
│   ├── DECISIONS.md                   # Architectural Decision Records (ADRs) and provider benchmarks
│   ├── CHANGELOG.md                   # Chronological feature and bugfix changelog
│   ├── RUNBOOK.md                     # Deployment and operational instructions
│   └── PROJECT_AUDIT.md               # Current comprehensive technical audit report
│
├── backend/                           # Python 3.12 backend services
│   ├── requirements.txt               # Backend dependencies (FastAPI, SQLAlchemy, LiveKit, etc.)
│   ├── alembic.ini                    # Database migration configuration
│   ├── alembic/                       # PostgreSQL schema migrations and Row-Level Security (RLS)
│   │   ├── env.py
│   │   └── versions/                  # Migration version scripts
│   ├── app/                           # Core FastAPI application
│   │   ├── main.py                    # Application entrypoint, CORS setup, and API routes
│   │   ├── core/                      # Global configuration, database session, security, and logging
│   │   │   ├── config.py              # Pydantic Settings loading environment variables
│   │   │   ├── database.py            # SQLAlchemy async session management
│   │   │   ├── logging.py             # Phone-masking sensitive log filter and memory buffer
│   │   │   └── security.py            # JWT authentication and internal service token verification
│   │   ├── models/                    # SQLAlchemy 2.0 ORM domain models
│   │   │   └── __init__.py            # Organisations, Clinics, Doctors, Appointments, Calls, etc.
│   │   ├── schemas/                   # Pydantic v2 validation and transfer schemas
│   │   │   └── __init__.py
│   │   ├── services/                  # Encapsulated business and clinical domain services
│   │   │   ├── booking_service.py     # Guarded booking, cancellation, and reschedule logic
│   │   │   ├── slot_service.py        # Calendar calculation, leave filtering, and break exclusion
│   │   │   ├── patient_service.py     # Patient record lookup and deduplication
│   │   │   ├── retention_sweeper.py   # Automated 30-day recording purge worker
│   │   │   └── audit_service.py       # DPDP Act audit logging service
│   │   └── api/                       # REST and WebSocket route controllers
│   │       ├── agent_tools.py         # Internal authenticated tools called by LLM
│   │       ├── webhooks_exotel.py     # Live Exotel WebSocket AudioStreams gateway & telephony webhooks
│   │       ├── appointments.py        # Public/Staff appointment endpoints
│   │       └── auth.py                # User login and token refresh
│   ├── agent/                         # Voice bot agent runtime
│   │   ├── session.py                 # Turn-by-turn conversation session lifecycle
│   │   ├── tools.py                   # Tool dispatch executor (REST bridge to backend tools)
│   │   ├── language.py                # Malayalam/English script detection and language manager
│   │   ├── recording.py               # Consent-gated audio recording controller
│   │   ├── knowledge/                 # Hospital facts and knowledge base
│   │   │   └── hospital_knowledge.json# Sreerudra doctors, slots, packages, and FAQs
│   │   └── providers/                 # Pluggable speech and language model adapters
│   │       ├── factory.py             # Provider factory loading configured vendors
│   │       ├── llm_provider.py        # Google Gemini 3.5 Flash Lite & OpenAI adapter
│   │       ├── sarvam_stt.py          # Sarvam AI Saaras v3 speech-to-text adapter
│   │       ├── sarvam_tts.py          # Sarvam AI Bulbul v3 text-to-speech adapter
│   │       ├── livekit_worker.py      # LiveKit Agents SIP worker implementation
│   │       └── mock_providers.py      # Deterministic offline mock adapters for tests
│   ├── evals/                         # Voice benchmarks and synthetic dialogue evaluation
│   │   ├── voice_evals.py             # Scripted hospital dialogue scenarios
│   │   ├── stt_bench/                 # Word Error Rate (WER) and Character Error Rate (CER) evals
│   │   ├── tts_bench/                 # Voice latency and RTF evaluation
│   │   └── llm_tool_bench/            # Slot extraction and tool calling accuracy tests
│   └── tests/                         # Unit and integration test suite
│       ├── test_phase0_evals.py       # Metrics, CER/WER, and evaluation harness tests
│       ├── test_phase1_foundation.py  # Model constraints, auth, and database schemas
│       ├── test_phase4_security_and_retention.py # PII masking, token validation, retention purges
│       ├── test_phase5_pilot_and_telephony.py # End-to-end simulated phone call and Exotel webhooks
│       └── test_slot_service.py       # Timezone, double booking, and leave calendar logic
│
├── frontend/                          # Next.js 14 Staff Web Dashboard
│   ├── package.json                   # React 18, Next 14, Tailwind CSS dependencies
│   ├── tsconfig.json                  # TypeScript strict mode configuration
│   ├── tailwind.config.js             # Styling tokens and color palette
│   ├── public/                        # Static assets, pre-rendered audio greetings
│   │   └── audio/
│   │       └── hospital_welcome_ml.wav# 8kHz 16-bit mono welcome greeting WAV
│   └── src/
│       ├── app/                       # Next.js App Router pages
│       │   ├── page.tsx               # Dashboard Home (overview, quick stats, today's schedule)
│       │   ├── layout.tsx             # Root dashboard navigation layout
│       │   ├── calls/page.tsx         # Call history, waveform player, and bilingual transcript viewer
│       │   ├── appointments/page.tsx  # Doctor timetables and appointment calendar grid
│       │   ├── knowledge/page.tsx     # Hospital treatment and FAQ management
│       │   └── settings/page.tsx      # Receptionist voice persona and greeting configuration
│       ├── components/                # Modular UI components
│       │   ├── pages/                 # Specialized domain page sections
│       │   └── ui/                    # Atomic primitives (Card, Badge, Button, AudioPlayer)
│       └── lib/
│           └── mockData.ts            # Baseline clinical data structures and fallback mocks
│
└── storage/                           # Persistent file storage
    ├── recordings/                    # Output directory for telephone WAV recordings
    └── live_calls.json                # JSON metadata and turn transcripts of captured calls
```

### 1.2 Technology and Framework Versions

- **Python Runtime:** Python 3.12 (`from __future__ import annotations` standard across all modules)
- **Backend Framework:** FastAPI `>=0.110.0`, ASGI Server: Uvicorn `>=0.28.0`
- **Data Validation & Settings:** Pydantic v2 `>=2.6.0`, Pydantic Settings `>=2.2.0`
- **Database ORM & Driver:** SQLAlchemy 2.0 (Asyncio) `>=2.0.28`, `asyncpg>=0.29.0`, Alembic `>=1.13.1`
- **Web Frontend:** Next.js `14.2.15` (App Router), React `18.3.1`, TypeScript `5.6.3` (Strict Mode)
- **Styling:** Tailwind CSS `3.4.14`, PostCSS `8.4.47`, Lucide React `0.453.0`
- **Speech & AI Providers:**
  - Speech-to-Text: Sarvam AI `saaras:v3`
  - Text-to-Speech: Sarvam AI `bulbul:v3` (speaker: `kavya`, sample rate: 8000Hz)
  - Reasoning (LLM): Google Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`)
  - Telephony Gateway: Exotel AudioStreams (Full-duplex WebSocket) & Exotel SIP

### 1.3 Implementation Status vs `docs/SPEC.md` and `docs/ARCHITECTURE.md`

| System Component | Status in Codebase | Notes / Gaps |
| :--- | :--- | :--- |
| **FastAPI Core & DB Schemas** | **Finished** | Full SQLAlchemy 2.0 async models for organisations, clinics, doctors, schedules, appointments, calls, events, consent, and audit logs. |
| **Booking & Slot Service** | **Finished** | Full calendar engine accounting for working hours, timezone (`Asia/Kolkata`), doctor leave, breaks, past-time rejection, and transactional row locking. |
| **Exotel Direct AudioStreams** | **Finished** | Direct WebSocket bridge in `backend/app/api/webhooks_exotel.py` handling 8kHz PCM streaming, turn detection, pipelined TTS, and auto-hangup. |
| **LiveKit Agent Worker** | **Partly Done** | Framework and adapter exist in `backend/agent/providers/livekit_worker.py`; currently bypassed in production in favor of direct Exotel WebSocket streaming. |
| **Bilingual Language Detection** | **Partly Done** | Character Unicode block regex (`\u0D00-\u0D7F`) and Manglish keyword matching working; lacks phonetic number/date normalisation. |
| **LLM Reasoning & Guardrails** | **Partly Done** | Gemini 3.5 Flash Lite prompt loaded with `hospital_knowledge.json`; slot extraction done via text prompting rather than OpenAI-compatible structured tool calls. |
| **Call Recording & Transcript Store** | **Partly Done** | PCM chunks saved to local disk `storage/recordings/` and `storage/live_calls.json`. Remote S3/MinIO upload and background sweeper are modeled and tested, but live WebSocket handler writes locally. |
| **Staff Web Dashboard** | **Partly Done** | Next.js 14 UI complete for Calls, Appointments, Knowledge Base, and Settings. Connected to `/api/calls/live` for real calls; other pages currently display baseline mock structures. |
| **SMS / WhatsApp Messaging** | **Missing / Deferred** | Database table `messages` modeled, but live integration with Exotel SMS/DLT templates is not yet connected to the live call wrap-up trigger. |
| **Multi-Tenant Routing in WebSocket** | **Missing** | The direct WebSocket endpoint currently hardcodes clinic ID `clinic-sreerudra-01` rather than querying DB by inbound virtual number. |

---

## 2. Live Call Flow as Implemented Today

The live call flow executes inside `backend/app/api/webhooks_exotel.py` via the `handle_exotel_voicebot_websocket` endpoint.

```text
[Exotel Telecom] (8kHz PCM)
       │
       ▼ WebSocket: ws://.../webhooks/exotel/voicebot
1. event: "connected"
2. event: "start"  ──► Extracts StreamSid, CallSid, Caller Phone
       │           ──► Plays pre-rendered greeting (hospital_welcome_ml.wav)
       │
       ▼
3. event: "media"  ──► Buffers 1600-byte chunks (100ms)
       │           ──► RMS Energy VAD (Speech >= 260.0, Silence < 190.0)
       │           ──► Silence Detector: 380ms pause triggers turn
       │
       ▼ process_caller_speech()
4. Sarvam STT      ──► POST https://api.sarvam.ai/speech-to-text (model: saaras:v3, ml-IN)
       │
       ▼
5. Gemini LLM      ──► POST Gemini 3.5 Flash Lite (prompt + hospital_knowledge.json + turns)
       │
       ▼
6. Pipelined TTS   ──► Sentence 1 synthesized immediately via Sarvam Bulbul (bulbul:v3, kavya)
       │           ──► Sentence 2+ dispatched to background asyncio.Task
       │           ──► 4-chunk burst (400ms) + 75ms paced delivery to Exotel
       │
       ▼
7. Interruption?   ──► If caller speaks during agent reply (RMS > 650.0), stop playback
       │
       ▼
8. Disconnect      ──► If reply contains [END_CALL] or farewell phrase, close WebSocket
       │
       ▼ finally:
9. Persistence     ──► Write combined PCM to storage/recordings/{id}.wav
                   ──► Update storage/live_calls.json with transcript and outcome
```

### Step-by-Step Code Walkthrough

1. **Connection & Handshake:**
   - Exotel initiates a full-duplex WebSocket connection to `/webhooks/exotel/voicebot`.
   - The server accepts the socket via `await websocket.accept()` (`webhooks_exotel.py:231`).
   - Exotel sends a JSON message `{"event": "connected"}` (`webhooks_exotel.py:460`).

2. **Call Initialization (`event: "start"`):**
   - Exotel delivers session metadata: `stream_sid`, `call_sid`, and caller phone number (`from`) (`webhooks_exotel.py:464-485`).
   - The endpoint initializes a `CallSession` (`backend/agent/session.py:38`) with clinical context for Sreerudra Hospital (`webhooks_exotel.py:245-270`).

3. **Playing the Initial Greeting:**
   - The system calls `_load_pcm_greeting()` (`webhooks_exotel.py:126`), which searches for `frontend/public/audio/hospital_welcome_ml.wav` (pre-rendered 8kHz 16-bit mono PCM).
   - If found, it dispatches `stream_audio_to_caller(pcm_greeting, stream_sid, is_welcome=True)` (`webhooks_exotel.py:504`).
   - If missing, it dynamically synthesizes the welcome text using Sarvam Bulbul TTS as a fallback (`webhooks_exotel.py:490`).
   - Greeting text:
     > *"നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു AI അസിസ്റ്റന്റാണ്. ഈ കോൾ ഗുണനിലവാരത്തിനായി റെക്കോർഡ് ചെയ്യപ്പെടുന്നുണ്ട്. ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?"*
   - Audio streaming buffers a burst of 4 chunks (400ms) to prevent carrier buffer underrun, followed by chunks paced at 75ms intervals (`webhooks_exotel.py:293-326`). The greeting is flagged as non-interruptible (`is_welcome=True`).

4. **Audio Buffering & Voice Activity Detection (VAD):**
   - Inbound telephone audio arrives as base64-encoded raw linear PCM in 100ms chunks (1600 bytes at 8000Hz 16-bit mono) (`webhooks_exotel.py:288`).
   - Each chunk's Root Mean Square (RMS) energy is computed via `_calculate_rms()` (`webhooks_exotel.py:150-159`).
   - **Thresholds:**
     - Speech threshold: `SPEECH_RMS_THRESHOLD = 260.0` (`webhooks_exotel.py:280`)
     - Silence threshold: `SILENCE_RMS_THRESHOLD = 190.0` (`webhooks_exotel.py:281`)
     - Max speech duration cap: `4.5 seconds` (`webhooks_exotel.py:535`) to prevent buffer starvation during background noise.
   - **Turn Detection:** When caller speech is followed by silence, `_silence_detector()` pauses for **0.38 seconds** (`await asyncio.sleep(0.38)`, `webhooks_exotel.py:447`). If no further speech arrives, it triggers `process_caller_speech()`.

5. **Speech-to-Text (STT):**
   - The raw linear PCM buffer is packed into an in-memory 8kHz 16-bit WAV container (`webhooks_exotel.py:354-360`).
   - Dispatched to `SarvamSTTAdapter.transcribe()` (`backend/agent/providers/sarvam_stt.py:29`).
   - **Protocol:** HTTP REST POST to `https://api.sarvam.ai/speech-to-text`.
   - **Parameters:** `model: "saaras:v3"`, `language_code: "ml-IN"`, timeout: 15.0s, connection pooling via persistent `httpx.AsyncClient`.

6. **Language Model Reasoning (LLM):**
   - The transcribed text is routed to `CallSession.handle_caller_utterance()` (`backend/agent/session.py:70`) and `GeminiLLMProvider.generate_response()` (`backend/agent/providers/llm_provider.py:55`).
   - **Protocol:** HTTP REST POST to `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent`.
   - **Parameters:** `model: "gemini-3.5-flash-lite"`, `maxOutputTokens: 55`, `temperature: 0.2`.
   - Dynamic prompt injection adds `hospital_knowledge.json` and the last 4 turns of conversation history (`llm_provider.py:84-90`).

7. **Text-to-Speech (TTS) & Pipelined Streaming:**
   - To achieve low latency, the response text is split into sentences using regex `(?<=[.?!।\n])\s+` (`webhooks_exotel.py:393`).
   - **Sentence 1** is sent immediately to `SarvamTTSAdapter.synthesize()` (`backend/agent/providers/sarvam_tts.py:33`).
   - **Sentence 2+** is dispatched concurrently as a background `asyncio.Task` (`webhooks_exotel.py:407`).
   - **Parameters:** `model: "bulbul:v3"`, `speaker: "kavya"`, `speech_sample_rate: 8000`, `pace: 1.05`, target language: `ml-IN`.
   - The first sentence audio begins playing to the caller within ~1.0–1.4 seconds, while subsequent audio is streamed seamlessly as soon as the background task finishes (`webhooks_exotel.py:410-425`).

8. **Interruption Handling (Barge-In):**
   - While the agent is speaking a regular conversational response (`is_speaking=True`, `is_greeting=False`), incoming audio chunks are continuously monitored.
   - If the caller's audio RMS exceeds **650.0** (`webhooks_exotel.py:516`), the server logs barge-in, sets `was_interrupted = True` and `is_speaking = False`, and immediately halts further audio transmission.

9. **Call Completion & Hang-Up:**
   - If the LLM generates `[END_CALL]` or the caller utters closing phrases ("ശരി", "നന്ദി", "ഓക്കേ", "thank you", "bye", "കാണാം"), `session.py:148` sets `type: "hangup"`.
   - The agent finishes playing the farewell audio sentence, pauses for **0.6 seconds** (`await asyncio.sleep(0.6)`, `webhooks_exotel.py:433`), and invokes `await websocket.close()`.
   - Closing the WebSocket causes Exotel's telephony server to terminate the cellular call.

10. **Audio Recording and Persistence:**
    - On WebSocket disconnect or closure (`finally` block, `webhooks_exotel.py:560-627`):
    - All session PCM chunks (`session_audio_chunks`) are assembled into an 8kHz 16-bit mono WAV file and written to disk at `storage/recordings/call-{epoch}.wav`.
    - A structured record containing caller phone, patient name, duration, outcome, and turn-by-turn transcripts is saved to `storage/live_calls.json`.

---

## 3. The "Brain" Today

### 3.1 State and Entity Tracking

Conversation state is managed across turns inside `CallSession` (`backend/agent/session.py`):
- **Turn History:** Maintained as a list of dicts: `[{"role": "user" | "assistant", "content": "..."}]`.
- **Entity Extraction:** Name, doctor, and slot selection are extracted using in-prompt reasoning in Gemini 3.5 Flash Lite rather than formal JSON schema parameter binding.
- **Silence & Consent State:** Tracked via `consecutive_silence_count` (`session.py:71`) and `self.recorder.consent_given` (`session.py:105`).

### 3.2 Exact System Prompt

Quoted directly from `backend/agent/providers/llm_provider.py` (lines 68–81):

```text
You are the warm, polite Malayalam voice receptionist at Sreerudra Ayurveda Hospital & Research Centre, Alappuzha.
Hospital Knowledge Base:
{kb_context}

CRITICAL VOICE & CONVERSATION RULES:
1. Reply in 1-2 short, spoken sentences in natural Malayalam suited for telephone conversation (maximum 15-20 words total).
2. Understand both pure Malayalam and English/Manglish transliterated phrases (e.g., 'appointment', 'timing', 'doctor').
3. Answer directly without repeating introductory greetings on every turn.
4. For appointment inquiries: Confirm Dr. Manoj is available tomorrow (10:00 AM, 11:30 AM, 2:30 PM, 4:00 PM) and ask which slot they prefer.
5. When an appointment is confirmed: Ask for the patient's name if not yet provided, then confirm the booking.
6. CALL COMPLETION & FAREWELL:
   If the caller says goodbye, confirms completion, or says closing phrases (e.g., 'ശരി', 'നന്ദി', 'ഓക്കേ', 'ok', 'thank you', 'bye', 'കാണാം'):
   Reply with a polite farewell (e.g., 'നന്ദി! നല്ലൊരു ദിവസം ആശംസിക്കുന്നു.') and append [END_CALL] at the end.
7. Never prescribe or invent medicines. For emergencies, advise immediate emergency care.
```

### 3.3 Few-Shot / Fallback Deterministic Examples

Quoted directly from `backend/agent/providers/llm_provider.py` (lines 119–135):

```python
if "മരുന്ന്" in last_msg or "medicine" in last_msg or "പനി" in last_msg:
    return (
        "ക്ഷമിക്കണം, എനിക്ക് മരുന്നുകൾ നിർദ്ദേശിക്കാൻ അനുവാദമില്ല. ഡോക്ടറെ നേരിട്ട് കണ്ട് സംസാരിക്കുന്നതിനായി കൺസൾട്ടേഷൻ ബുക്ക് ചെയ്യാം. നാളെ ലഭ്യമായ സമയം പരിശോധിക്കട്ടെ?",
        [],
    )
if "നെഞ്ചിൽ" in last_msg or "ശ്വാസം" in last_msg or "emergency" in last_msg:
    return (
        "അടിയന്തിര സാഹചര്യങ്ങളിൽ ദയവായി തൊട്ടടുത്തുള്ള ആശുപത്രിയിലെ എമർജൻസി വിഭാഗത്തിൽ ഉടൻ ചികിത്സ തേടുക.",
        [],
    )
if "മനോജ്" in last_msg or "ഡോക്ടർ" in last_msg or "നാളെ" in last_msg or "ലഭ്യമാണോ" in last_msg:
    return (
        "അതെ, ഡോക്ടർ മനോജ് നാളെ ലഭ്യമാണ്. രാവിലെ പത്ത് മണിക്കും, പതിനൊന്നരയ്ക്കും, ഉച്ചയ്ക്ക് രണ്ടരയ്ക്കും സ്ലോട്ടുകൾ ലഭ്യമാണ്. ഏത് സമയമാണ് സൗകര്യം?",
        [],
    )

return "നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിലേക്ക് സ്വാഗതം. ഞാൻ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?", []
```

### 3.4 History Construction

Extracted from `backend/agent/providers/llm_provider.py` (lines 84–90):

```python
recent_turns = []
for m in messages[-4:]:
    role = "Caller" if m["role"] == "user" else "Assistant"
    recent_turns.append(f"{role}: {m['content']}")
history_str = "\n".join(recent_turns)

combined_prompt = (
    f"{hospital_context}\n\n"
    f"Conversation so far:\n{history_str}\n\n"
    f"Caller: {user_msg}\n"
    f"Assistant (in 1-2 spoken Malayalam sentences):"
)
```

### 3.5 `hospital_knowledge.json` Structure and Samples

The knowledge base is stored in `backend/agent/knowledge/hospital_knowledge.json`.  
**Top-Level Schema Keys:** `hospital`, `doctors`, `treatments`, `faqs`, `policies`.

**Sample Entry 1: Doctor Profile (Masked):**
```json
{
  "id": "doc-manoj-01",
  "name": "Dr. M****",
  "name_ml": "ഡോക്ടർ മ****",
  "qualification": "BAMS, MD (Ayurveda)",
  "department": "Panchakarma & General Ayurveda",
  "specialties": ["Panchakarma", "Spine & Joint Disorders", "Arthritis", "Rheumatoid Care", "Rejuvenation"],
  "consultation_days": "Monday to Saturday",
  "consultation_timings": "9:00 AM to 5:00 PM",
  "available_slots_tomorrow": ["10:00 AM", "11:30 AM", "2:30 PM", "4:00 PM"]
}
```

**Sample Entry 2: FAQ Entry:**
```json
{
  "question_ml": "ഹോസ്പിറ്റൽ എവിടെയാണ് സ്ഥിതി ചെയ്യുന്നത്?",
  "answer_ml": "ആലപ്പുഴ ജനറൽ ഹോസ്പിറ്റൽ ജംഗ്ഷന് സമീപമാണ് ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റൽ പ്രവർത്തിക്കുന്നത്."
}
```

---

## 4. Tools and Backend

### 4.1 Tools List (`backend/agent/tools.py` & `backend/app/api/agent_tools.py`)

The LLM interface defines 9 backend callable tools:

| Tool Name | Parameters | Purpose / Action |
| :--- | :--- | :--- |
| `find_or_create_patient` | `clinic_id`, `name`, `phone`, `age`, `gender`, `place`, `preferred_language`, `confirmed` | Looks up existing patient by phone number or creates a new patient record. |
| `get_free_slots` | `clinic_id`, `doctor_id` (optional), `date` (`YYYY-MM-DD`) | Computes real bookable slots excluding breaks, leave, and existing appointments. |
| `book_appointment` | `clinic_id`, `patient_id`, `doctor_id`, `start` (ISO 8601), `treatment_id`, `reason`, `visit_type`, `call_id` | Executes atomic booking with database row locks. |
| `reschedule_appointment`| `clinic_id`, `appointment_id`, `new_start` (ISO 8601), `caller_phone` | Validates appointment ownership and reassigns slot. |
| `cancel_appointment` | `clinic_id`, `appointment_id`, `caller_phone` | Verifies phone ownership and sets status to `cancelled`. |
| `get_clinic_info` | `clinic_id`, `question`, `topic` | Searches approved hospital FAQ entries and treatment catalog. |
| `transfer_call` | `clinic_id`, `reason` | Returns hospital front desk phone number (`+91 477 225 1234`) for SIP transfer. |
| `request_callback` | `clinic_id`, `call_id`, `patient_id`, `reason`, `preferred_time` | Logs an actionable callback task in `callback_tasks`. |
| `escalate_emergency` | `clinic_id`, `call_id`, `summary` | Creates emergency callback record and provides Malayalam casualty disclaimer. |

### 4.2 Database Tables and Schema (`backend/app/models/__init__.py`)

- **`organisations`:** Multi-tenant enterprise accounts (`id`, `name`, `plan`, `status`).
- **`clinics`:** Clinic branches (`id`, `organisation_id`, `name`, `timezone`, `working_hours`, `fallback_phone`).
- **`users`:** Staff and admin accounts (`id`, `email`, `password_hash`, `role`).
- **`phone_numbers`:** Telecom number routing table (`id`, `clinic_id`, `e164`, `provider`, `status`).
- **`agent_settings`:** Custom prompt additions, voice timbre, and greeting per clinic.
- **`doctors` & `doctor_schedules`:** Physician directory and weekly recurring shifts (`weekday`, `start_time`, `end_time`, `break_start`, `break_end`).
- **`doctor_leave`:** Approved physician time off (`starts_at`, `ends_at`, `reason`).
- **`treatments` & `faq_entries`:** Clinical therapy catalog and bilingual FAQ database.
- **`patients`:** Patient registry (`name`, `phone`, `alt_phone`, `age`, `gender`, `preferred_language`).
- **`appointments`:** Confirmed bookings with unique constraint: `uq_appointment_doctor_start` on `(doctor_id, starts_at)`.
- **`calls` & `call_events`:** Call detail records, duration, summary, recording key, and stage events.
- **`callback_tasks`:** Front-desk reception task queue (`open`, `in_progress`, `resolved`).
- **`consent_log`:** Explicit audit trail of audio recording consent (`call_id`, `given`, `at`).
- **`messages`:** Outbound SMS / WhatsApp notification logs.
- **`audit_log`:** DPDP Act access logging tracking staff reads and data modifications.

### 4.3 Validation Rules and Locations

1. **Past Date Rejection:** Handled in `backend/app/services/slot_service.py:45` and `booking_service.py:70`. Validates that target date/time is strictly greater than `datetime.datetime.now(tz)`.
2. **Double Booking Prevention:** Enforced at two layers:
   - *Application Transaction Layer:* `booking_service.py:77-85` executes `select(Appointment)...with_for_update()` to lock the doctor's calendar during slot reservation.
   - *Database Constraint Layer:* `uq_appointment_doctor_start` constraint in PostgreSQL schema prevents overlapping rows.
3. **Working Hours & Breaks:** Handled in `slot_service.py:108-144`. Loops through schedule slots, discarding any slot falling between `break_start` and `break_end`.
4. **Doctor Leave:** Handled in `slot_service.py:68-78`. Queries `doctor_leave` table for overlapping intervals; if on leave, zero slots are returned.

---

## 5. Language Handling

### 5.1 Malayalam, English, and Code-Switching (Manglish)

- **Language Detection (`backend/agent/language.py`):**
  - Evaluates ratio of Malayalam Unicode script characters (`\u0D00-\u0D7F`) against total alphabetical characters (`language.py:16-24`). If Malayalam characters exceed 15%, language is classified as `ml-IN`.
  - Scans for Romanized Malayalam (Manglish) marker words:
    ```python
    manglish_markers = [
        "namaskaram", "doctor", "varaan", "kaanan", "samayam",
        "appointment", "venam", "pattumo", "aano", "enthinaanu",
        "aale", "alle", "nanni", "alappuzha", "cherthala"
    ]
    ```
    If any marker matches, the system locks to `ml-IN` output.
- **Language Switching:** Handled turn-by-turn via `LanguageManager.process_turn()` (`language.py:47-60`). If the caller changes from English to Malayalam, the language mode dynamically switches.

### 5.2 Normalisation and Vocabulary Deficits

- **Number & Digit Normalisation:** **None.** There is currently no text pre-processor or phonetizer converting numbers (e.g. `10:00 AM` to *"രാവിലെ പത്ത് മണി"*). The LLM output is fed directly into Sarvam TTS.
- **Date Normalisation:** **None.** Date terms like "നാളെ" (tomorrow) are parsed solely via the LLM's internal context without calendar date grounding.
- **Phone Number Normalisation:** **None.** Transcribed telephone digits are passed as raw text.
- **STT Speech Hints / Glossary:** **None.** Sarvam STT REST API payload (`sarvam_stt.py:38`) sends only `language_code` and `model`. It does not provide custom speech hints or phonetic biasing for doctor names ("Manoj", "Sreerudra", "Abhyangam", "Kizhi").

---

## 6. Safety

### 6.1 Medical Advice Prohibition

**Rule Enforcement:**
1. **Prompt Guardrail:** Rule 7 in `backend/agent/providers/llm_provider.py:80`:
   > *"Never prescribe or invent medicines. For emergencies, advise immediate emergency care."*
2. **Deterministic Code Fallback:** In `backend/agent/providers/llm_provider.py:119-123`:
   ```python
   if "മരുന്ന്" in last_msg or "medicine" in last_msg or "പനി" in last_msg:
       return (
           "ക്ഷമിക്കണം, എനിക്ക് മരുന്നുകൾ നിർദ്ദേശിക്കാൻ അനുവാദമില്ല. ഡോക്ടറെ നേരിട്ട് കണ്ട് സംസാരിക്കുന്നതിനായി കൺസൾട്ടേഷൻ ബുക്ക് ചെയ്യാം. നാളെ ലഭ്യമായ സമയം പരിശോധിക്കട്ടെ?",
           [],
       )
   ```

### 6.2 Emergency Escalation

1. **Prompt Guardrail:** Policies section in `hospital_knowledge.json:56`:
   > *"അടിയന്തിര സാഹചര്യങ്ങളിൽ ദയവായി തൊട്ടടുത്തുള്ള ജനറൽ ആശുപത്രിയിലെ എമർജൻസി വിഭാഗത്തിൽ പ്രവേശിക്കുക."*
2. **Deterministic Code Fallback:** In `backend/agent/providers/llm_provider.py:124-128`:
   ```python
   if "നെഞ്ചിൽ" in last_msg or "ശ്വാസം" in last_msg or "emergency" in last_msg:
       return (
           "അടിയന്തിര സാഹചര്യങ്ങളിൽ ദയവായി തൊട്ടടുത്തുള്ള ആശുപത്രിയിലെ എമർജൻസി വിഭാഗത്തിൽ ഉടൻ ചികിത്സ തേടുക.",
           [],
       )
   ```
3. **Backend Tool:** `escalate_emergency` in `backend/app/api/agent_tools.py:330` creates an immediate callback record flagged `priority="urgent"` and returns the official casualty contact number (`0477-2251234`).

---

## 7. Performance Evidence

### 7.1 Measured Turn-by-Turn Timings (Repository Traces)

From live execution logs and test traces across real calls:

| Pipeline Stage | Measured Latency Range | Contributing Factors |
| :--- | :--- | :--- |
| **Silence Detection (VAD)** | **0.38s** | Fixed timer in `webhooks_exotel.py:447` |
| **Speech-to-Text (Sarvam `saaras:v3`)** | **1.00s – 1.32s** | REST API network transit + full audio WAV upload |
| **LLM Reasoning (Gemini 3.5 Flash Lite)**| **0.62s – 1.10s** | REST API transit to Google + generation of 15–20 words |
| **Text-to-Speech (Sarvam `bulbul:v3`)** | **1.30s – 2.00s** | Synthesis of first sentence (approx. 40 characters) |
| **Total Turnaround Time (Perceived)** | **3.30s – 4.80s** | Caller silence to first audio packet heard on phone |

### 7.2 Root Causes of Latency Loss

1. **Sequential REST HTTP Roundtrips:** The pipeline operates on sequential blocking HTTP calls (Exotel $\rightarrow$ Sarvam REST $\rightarrow$ Gemini REST $\rightarrow$ Sarvam REST $\rightarrow$ Exotel). Each hop incurs TLS handshake and network serialization overhead.
2. **Geographical Cross-Continent Penalty:** The backend API is hosted on Render in Oregon, USA (`us-west`), while Exotel carrier infrastructure, Sarvam AI servers, and callers are located in India. Each network round-trip adds 350ms–450ms of pure speed-of-light transit latency.
3. **Absence of Real-Time Streaming:** Neither STT nor TTS currently streams over WebSockets. STT requires the complete audio file before returning a single word.

---

## 8. Quality Evidence

### 8.1 Offline Test Suite Execution

The repository contains 5 test suites. Running the offline test discovery command:
```bash
python -m unittest discover -s backend/tests -v
```
**Results:**
- **Total Tests Run:** 29
- **Passed:** 29
- **Failed:** 0
- **Errors:** 0
- **Duration:** 34.68 seconds

**Suite Breakdown:**
- `test_phase0_evals.py`: 8 tests (WER, CER, entity evaluation, benchmark harnesses) — **Passed**
- `test_phase1_foundation.py`: 9 tests (database schema, models, auth tokens) — **Passed**
- `test_phase4_security_and_retention.py`: 5 tests (PII masking, rate limiting, retention sweeper) — **Passed**
- `test_phase5_pilot_and_telephony.py`: 3 tests (Exotel webhooks, full pilot call simulation) — **Passed**
- `test_slot_service.py`: 4 tests (calendar calculation, past-time rejection, leave filters) — **Passed**

### 8.2 Real Call Log Transcripts & Odd Replies

From captured telephone sessions (personal names and phone numbers masked):

#### Call 1: Clean Booking Interaction (`call-live-akshay-01`)
- **Caller Number:** `+91 98****3210`
- **Agent:** *"നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ആശുപത്രിയിലേക്ക് സ്വാഗതം... ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?"*
- **Caller:** *"ഡോക്ടർ മനോജ് നാളെ ലഭ്യമാണോ?"*
- **Agent:** *"അതെ, ഡോക്ടർ മനോജ് നാളെ ലഭ്യമാണ്. രാവിലെ 10:00, 11:30, ഉച്ചയ്ക്ക് 2:30, 4:00 എന്നീ സമയങ്ങളിൽ സ്ലോട്ടുകൾ ഉണ്ട്. ഇതിൽ ഏത് സമയമാണ് സൗകര്യം?"*
- **Caller:** *"എന്റെ പേര് A*****"*
- **Agent:** *"നന്ദി A*****, നാളെ രാവിലെ 10:00 മണി മതിയോ?"*
- **Caller:** *"മതി മതി."*
- **Agent:** *"തീർച്ചയായും A*****, നാളെ രാവിലെ 10:00 മണിക്ക് ഡോക്ടർ മനോജിന്റെ അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്തിരിക്കുന്നു."*
- **Caller:** *"ഓക്കേ."*
- **Agent:** *"നന്ദി! നല്ലൊരു ദിവസം ആശംസിക്കുന്നു."* `[Call auto-disconnected cleanly]`

#### Call 2: Odd / Sub-Optimal Replies Observed
1. **Background Noise False Trigger:**
   - **Caller:** `[Short breath / carrier click]`
   - **Agent Reply:** *"ക്ഷമിക്കണം, വ്യക്തമായി കേട്ടില്ല. ഒന്നുകൂടി പറയാമോ?"*
   - **Cause:** Volume-based RMS threshold triggered on line pop, sending empty audio to Sarvam STT.
2. **Ambiguous Pronoun Handling:**
   - **Caller:** *"അവന് തിരിച്ച് വന്നതാ..."* (*"He came back..."*)
   - **Agent Reply:** *"തീർച്ചയായും, താങ്കളുടെ പേരും സൗകര്യപ്രദമായ സമയവും ഒന്ന് പറയാമോ? അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്യാം."*
   - **Cause:** Inability to identify clinical intent from unstructured colloquial statements, defaulting to appointment intake.

---

## 9. Configuration and Deployment

### 9.1 Environment Variable Inventory

Configured in `backend/app/core/config.py` (variable names only, no secret values):
- `APP_ENV`
- `DEBUG`
- `APP_NAME`
- `DATABASE_URL`
- `REDIS_URL`
- `OBJECT_STORAGE_ENDPOINT`
- `OBJECT_STORAGE_BUCKET`
- `OBJECT_STORAGE_KEY`
- `OBJECT_STORAGE_SECRET`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_MINUTES`
- `INTERNAL_SERVICE_TOKEN`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_SIP_DOMAIN`
- `SARVAM_API_KEY`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `LLM_PROVIDER`
- `EXOTEL_SID`
- `EXOTEL_API_KEY`
- `EXOTEL_API_TOKEN`

### 9.2 Hosting and Deployment Topology

- **Backend Hosting:** Render Web Service
  - **Service Name:** `voice-agent-pphb`
  - **Public URL:** `https://voice-agent-pphb.onrender.com`
  - **Deployment Trigger:** Automatic build and deploy on Git push to `main` branch
  - **Region:** Oregon, USA (`us-west`)
- **Free-Tier Limits and Cold Starts:**
  - The Render Web Service runs on a free instance plan that automatically spins down after 15 minutes of inactivity.
  - **Cold Start Delay:** 50 to 90 seconds. If an inbound phone call arrives while the instance is sleeping, Exotel's WebSocket connection times out after 10 seconds, causing dropped calls with no greeting.
  - **Storage Ephemerality:** Disk storage on Render free containers is ephemeral; local recordings in `storage/recordings/` are erased upon container restarts.

---

## 10. Dashboard

The frontend is built using Next.js 14 App Router (`frontend/src/app`):

| Page Route | Purpose & Displayed Data | Data Acquisition Method |
| :--- | :--- | :--- |
| **`/` (Dashboard Home)** | High-level metrics (total calls, booked appointments, emergency escalations, callback tasks), live agent status banner, and today's schedule overview. | Currently renders structured mock components (`QuickStatsSection`, `TodayAppointmentsSection`). |
| **`/calls` (Call History)** | Chronological list of inbound calls, audio playback waveform bar, caller phone, duration, booking outcome, and turn-by-turn bilingual transcripts. | **Live API Integration:** Fetches real calls from `GET ${NEXT_PUBLIC_API_URL}/api/calls/live`. Falls back to `MOCK_CALLS` if offline. Audio streams from `/api/calls/live/{id}/audio`. |
| **`/appointments`** | Physician weekly schedule, working hours, and calendar slot grid with booking status (`confirmed`, `rescheduled`, `cancelled`). | Renders client components using `MOCK_CLINIC` data structures. |
| **`/knowledge`** | Ayurvedic therapy catalog (Abhyangam, Shirodhara, Kizhi) and dual-language FAQ accordion manager. | Renders `TreatmentsSection` and `FaqManagerSection`; backend endpoint `/api/knowledge` is available. |
| **`/settings`** | AI Receptionist persona configuration, bilingual greeting editor, Sarvam voice timbre picker (`kavya`), and barge-in sensitivity sliders. | Renders `AgentGreetingSection` and `VoiceModelSection`. |

---

## 11. Known Problems and Technical Risks (Top 10 Ranked)

1. **Single-Tenant Hardcoding in Live Telephony Gateway**  
   - **File & Line:** `backend/app/api/webhooks_exotel.py:246`  
   - **Problem:** `clinic_context = {"clinic_id": "clinic-sreerudra-01", ...}` is hardcoded inside the WebSocket handler.  
   - **Impact:** Adding a second clinic or phone number will route all callers into Sreerudra Hospital's doctor schedules.

2. **Ephemeral Local Storage on Cloud Container**  
   - **File & Line:** `backend/app/api/webhooks_exotel.py:169` & `572`  
   - **Problem:** Audio recordings are written to local disk `storage/recordings/` rather than AWS S3 or Cloudflare R2.  
   - **Impact:** Any container restart on Render permanently deletes all patient call recordings and transcripts.

3. **Cloud Instance Cold-Start Call Drops**  
   - **File & Line:** Deployment Infrastructure (`voice-agent-pphb.onrender.com`)  
   - **Problem:** Free-tier instance sleeps after 15 minutes. Cold-start wake-up takes 50–90 seconds.  
   - **Impact:** Telecom providers (Exotel) drop inbound calls if WebSocket connection is not established within 10 seconds.

4. **Sequential REST Pipeline Latency (3.5s+ Perceived Delay)**  
   - **File & Line:** `backend/app/api/webhooks_exotel.py:365, 382, 411`  
   - **Problem:** STT, LLM, and TTS execute as separate sequential HTTP POST requests across continents.  
   - **Impact:** 3.5 to 4.8 seconds of conversational turn latency causes callers to speak over the AI or hang up.

5. **RMS Energy VAD False Triggers on Carrier Line Noise**  
   - **File & Line:** `backend/app/api/webhooks_exotel.py:280, 513`  
   - **Problem:** Audio thresholding relies on basic Root Mean Square mathematical energy (`SPEECH_RMS_THRESHOLD = 260.0`).  
   - **Impact:** Indian PSTN carrier pops, heavy breathing, or background traffic are mistaken for speech, triggering empty STT requests.

6. **PostgreSQL Row-Level Security Bypassed in WebSocket Flow**  
   - **File & Line:** `backend/app/api/webhooks_exotel.py:224-270`  
   - **Problem:** The WebSocket route does not query the PostgreSQL database for clinic settings, bypassing tenant isolation policies.  
   - **Impact:** Breaches the multi-tenant architecture and security constraints mandated in `AGENTS.md`.

7. **Frontend Relies on Static Mock Data for Clinic Operations**  
   - **File & Line:** `frontend/src/app/appointments/page.tsx:4` & `frontend/src/lib/mockData.ts`  
   - **Problem:** The dashboard appointments and doctor timetables display static mock arrays instead of fetching live database state.  
   - **Impact:** Hospital staff cannot manage real doctor bookings from the web dashboard.

8. **Unstructured Entity Extraction in Voicebot Loop**  
   - **File & Line:** `backend/app/api/webhooks_exotel.py:586-601`  
   - **Problem:** Patient name and booking outcome are parsed via basic string search (e.g. `if "akshay" in txt`) rather than formal tool schema parameter binding.  
   - **Impact:** Callers with unlisted names or non-standard phrasing are labeled with generic fallback values.

9. **Missing SMS / WhatsApp DLT Gateway Integration**  
   - **File & Line:** `backend/app/models/__init__.py:270` & `backend/app/services/booking_service.py`  
   - **Problem:** The `messages` table is defined, but no telephony SMS sender is dispatched after a successful booking.  
   - **Impact:** Patients receive no booking confirmation SMS or location link upon hanging up.

10. **Geographical Cross-Continent Hosting Penalty**  
    - **File & Line:** Deployment Infrastructure (`us-west` region)  
    - **Problem:** The backend server resides in Oregon, USA, while Exotel, Sarvam, and the hospital are in India.  
    - **Impact:** Adds 350ms to 450ms of unavoidable round-trip network lag to every voice turn.

---

## 12. Undetermined Items and Open Questions

1. **Production SIP Trunk Credentials:** Are dedicated Exotel SIP trunk credentials available to route directly into a LiveKit Cloud edge cluster in Mumbai, or will calls continue over the WebSocket AudioStreams applet?
2. **DLT Entity & Template ID Status:** Has Sreerudra Hospital registered their Principal Entity and Malayalam SMS templates on the Indian DLT portal (e.g. Jio/Vil DLT) for sending automated booking SMS?
3. **Database Cloud Hosting Selection:** Where will the production PostgreSQL instance with Row-Level Security be hosted (e.g., Supabase India, AWS RDS Mumbai, or Neon)?
4. **Cloud Infrastructure Upgrade:** Is approval granted to transition the Render service to a persistent Indian cloud instance (or AWS Mumbai ECS) with an attached S3/R2 bucket to eliminate cold starts and prevent recording loss?
