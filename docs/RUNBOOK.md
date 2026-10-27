# ClinicVoice: Operational Runbook & Disaster Recovery (RUNBOOK.md)

**Product Working Name:** ClinicVoice  
**Launch Partner:** Sreerudra Ayurveda Hospital & Research Centre, Alappuzha, Kerala  
**Version:** 1.0 (Phase 4 Security & Compliance Standard)  

---

## 1. System Overview & Service Level Objectives (SLOs)

ClinicVoice provides an automated bilingual (Malayalam/English) AI phone receptionist for Ayurvedic hospitals and clinics. 

### Critical SLOs:
* **Liveness Probe (`/health`):** p99 < 15ms.
* **Readiness Probe (`/ready`):** Database & Redis ping < 50ms.
* **Call Answer Latency (TTFA):** < 1200ms from SIP invite to first bilingual greeting.
* **Audio Interruption Latency:** < 250ms silence-to-cutoff on caller voice detection (Silero VAD).
* **Audio Retention Maximum:** 30 Days default (`RECORDING_RETENTION_DAYS=30`).

---

## 2. Exotel SIP Trunk & Telephony Setup

### 2.1 DLT (Distributed Ledger Technology) & Telecom Registration (India)
1. **Entity Registration:** Sreerudra Ayurveda Hospital registers as Principal Entity on Airtel / Jio DLT portal.
2. **Sender ID (Header):** Register approved 6-character alphanumeric SMS sender ID (e.g., `SRDRCL` or `CLNVOI`).
3. **SMS Service Implicit / Explicit Templates:** Register appointment confirmation and reminder templates in Malayalam and English:
   - *Malayalam:* `നമസ്കാരം {#var#}, ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിൽ ഡോ. മനോജുമായുള്ള താങ്കളുടെ അപ്പോയിന്റ്മെന്റ് {#var#} ന് സ്ഥിരീകരിച്ചിരിക്കുന്നു. റഫറൻസ് ഐഡി: {#var#}.`
   - *English:* `Hello {#var#}, your appointment with Dr. Manoj at Sreerudra Ayurveda Hospital has been confirmed for {#var#}. Reference ID: {#var#}.`

### 2.2 Exotel Virtual Number & Inbound SIP Forwarding
1. Purchase Kerala DID / Mobile E.164 number (e.g., `+91 98765 00001`).
2. In Exotel Dashboard -> **Applets** -> create **Passthru / SIP Flow**:
   - **SIP URI:** `sip:inbound@voice.clinicvoice.internal:5060`
   - **Protocol:** TLS / SRTP encrypted audio.
   - **SIP Headers Forwarded:**
     - `X-Exotel-Call-Sid`: Unique telecom session ID.
     - `From`: Caller's mobile number in E.164 (`+91XXXXXXXXXX`).
     - `To`: Clinic virtual number (`+919876500001`).
3. **Webhook URL (Events):** `https://api.clinicvoice.in/webhooks/exotel/voice`

---

## 3. Emergency Human Override & Fallback Routing

If the voice agent encounters an unexpected exception, degraded dependencies, or network latency exceeding safety limits, the system triggers the **Emergency Fallback Circuit**.

```
Inbound Telecom Call
      │
      ▼
Exotel Virtual Number
      │
      ├─► Health Check `/ready` OK? ──► [LiveKit Room -> AI Voice Receptionist]
      │
      └─► Degraded / Timeout? ────────► [Immediate Call Forwarding]
                                               │
                                               ▼
                         Sreerudra Hospital Front Desk Landline
                               (+91 477 225 1234)
```

### 3.1 Failure Modes & Fallback Actions:
| Failure Mode | Detection | Automated Action | Alerting |
| :--- | :--- | :--- | :--- |
| **Backend Unreachable** | `/health` or `/ready` fails HTTP 5xx | Exotel failover applet dials fallback clinic number immediately. | PagerDuty / Telegram alert to on-call engineer. |
| **STT / TTS Provider Down** | Timeout > 2500ms on initial audio | Agent plays cached local audio: *"ക്ഷമിക്കണം, താൽക്കാലിക തടസ്സം നേരിടുന്നു. ഞാൻ കോൾ സ്റ്റാഫിലേക്ക് മാറ്റാം."* and dials fallback phone. | Sentry error logged with provider code. |
| **Caller Inactivity / Silence** | 2 consecutive silence windows (10s) | Agent prompts: *"ഹലോ, കേൾക്കാമോ?"*. If no response, ends call safely and logs `callback_tasks`. | Status logged in dashboard under Callbacks. |

---

## 4. Audio Data Retention & Automated Sweeper

To comply with the **Digital Personal Data Protection (DPDP) Act 2023** and medical ethics guidelines, raw caller voice recordings must NOT be retained indefinitely.

### 4.1 Policy Rules:
1. **Audio Recordings:** Retained for exactly **30 Days** (`RECORDING_RETENTION_DAYS=30`) in encrypted object storage (`ap-south-1`).
2. **Metadata & Structured Transcripts:** Preserved permanently for doctor reference and patient appointment records unless patient explicitly requests erasure.
3. **Consent Refusal:** If caller says *"No"* to recording consent, audio recording is never uploaded to storage; only textual appointment details are stored.

### 4.2 Running the Retention Sweeper:
Run the sweeper nightly via cron (or scheduled background worker):

```bash
# Nightly Linux Cron (Every day at 2:00 AM IST)
0 2 * * * /usr/local/bin/python -m backend.app.services.retention_sweeper >> /var/log/clinicvoice/retention.log 2>&1
```

```powershell
# Windows PowerShell Execution
python -m backend.app.services.retention_sweeper --days 30

# Dry-run inspection without deleting
python -m backend.app.services.retention_sweeper --dry-run
```

---

## 5. India DPDP Act (2023) Compliance Verification

| Requirement | Implementation in ClinicVoice | Audit Evidence |
| :--- | :--- | :--- |
| **Data Residency** | All databases, Redis, and MinIO/S3 hosted in India (`ap-south-1` Mumbai). | AWS Region configuration & DB IP. |
| **Notice & Consent** | Agent states AI identity upfront and explicitly asks for recording consent in Malayalam and English before recording starts. | `consent_log` table timestamped with `given: true/false`. |
| **Purpose Limitation** | Data collected (name, phone, symptom overview) is strictly used for booking doctor consultations. | No external marketing or ad trackers. |
| **Data Minimization** | Audio purged after 30 days. Technical logs (stdout/stderr) mask all caller phone numbers via `SensitiveDataFilter`. | Verified in `backend/app/core/logging.py`. |
| **Right to Erasure** | Tenant admin can trigger soft/hard deletion of patient records upon written notice. | `DELETE /patients/{id}` cascades to PII while preserving anonymized count. |
| **Immutable Audit Log** | Every staff access to patient records, call transcripts, or audio playback is recorded. | Verified in `audit_log` table and `audit_service.py`. |

---

## 6. Database Backup & Disaster Recovery Drill

### 6.1 Executing an Automated Backup:
```powershell
# Windows PowerShell
.\scripts\backup_db.ps1 -DbName clinicvoice_db -BackupDir backups
```
```bash
# Linux / macOS
./scripts/backup_db.sh backups
```

### 6.2 Executing a Recovery Drill (Quarterly Requirement):
```powershell
# Windows PowerShell
.\scripts\restore_db.ps1 -BackupFile backups\clinicvoice_backup_20261026_160000.sql
```
```bash
# Linux / macOS
./scripts/restore_db.sh backups/clinicvoice_backup_20261026_160000.dump
```
