# ClinicVoice (ക്ലിനിക്ക് വോയ്‌സ്)
**AI Phone Receptionist for Small Clinics in Kerala**  
*First Customer & Design Partner: Sreerudra Ayurveda Hospital and Research Centre, Alappuzha, Kerala.*

---

## 🚀 Quick Start (Local Run)

### 1. Start Infrastructure via Docker Compose
Starts PostgreSQL 16, Redis 7, MinIO (private S3 with Web Console), and LiveKit WebRTC server:
```bash
docker compose up -d
```
* **MinIO Web Console:** [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)
* **LiveKit Server:** `ws://localhost:7880`

### 2. Run the FastAPI Backend
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start backend server
uvicorn backend.app.main:app --reload --port 8000
```
* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Liveness Probe:** [http://localhost:8000/health](http://localhost:8000/health)

### 3. Run the Next.js Web Dashboard
```bash
cd frontend
npm install
npm run dev
```
* **Staff Dashboard:** [http://localhost:3000](http://localhost:3000)

### 4. Run a Local Mock Phone Call (No phone number needed!)
Simulates an incoming telephone call to Sreerudra Hospital, resolves clinic settings, triggers the bilingual greeting, and stores the call record in PostgreSQL:
```bash
python backend/agent/mock_caller.py --dialed +919876500001 --caller +919876543210
```

---

## 🧪 Testing

Run all unit tests, voice evals, and frontend verification:
```bash
# 1. Run all Backend tests (Database, RLS, Auth, Slot Service, Benchmarks)
python -m unittest discover -s backend/tests

# 2. Run Voice Evals (8 real clinic scenarios in Malayalam & English)
python backend/evals/voice_evals.py

# 3. Run Frontend Dashboard Verification
node frontend/tests/test_dashboard_routes.mjs
```

---

## 📁 Repository Layout
- `backend/`:
  - `app/`: FastAPI async backend with PostgreSQL Row-Level Security (RLS), models, schemas, and booking services
  - `agent/`: LiveKit Voice Agent worker, telephony mock caller, bilingual prompts, and providers
  - `evals/`: Voice evaluation suite, STT/TTS benchmarks, and LLM tool validation
  - `alembic/`: Database migrations with RLS policies
  - `tests/`: Automated test suite for multi-tenant isolation, slot calculation, and auth
- `frontend/`:
  - `src/app/`: Next.js 14 App Router pages (`/`, `/calls`, `/appointments`, `/knowledge`, `/settings`)
  - `src/components/pages/home/`: 5 modular dashboard sections (`QuickStats`, `TodayAppointments`, `RecentCalls`, `CallbackTasks`, `LiveAgentStatus`)
  - `src/components/ui/`: Reusable atomic UI primitives (`Button`, `Card`, `Badge`, `AudioPlayer`)
  - `tests/`: Automated route and modular structure verification suite
- `docs/`: Technical specification (`SPEC.md`), architectural decisions (`DECISIONS.md`), and Exotel SIP setup (`SIP_EXOTEL_SETUP.md`).
