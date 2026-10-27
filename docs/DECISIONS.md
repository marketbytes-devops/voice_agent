# Architecture & Product Decision Log (DECISIONS.md)

This document tracks all architectural, provider, legal, and operational decisions for ClinicVoice.

---

## 1. Provider Comparison Table (Phase 0 Evaluation)

### Speech-to-Text (STT) Providers for Malayalam (`ml-IN`) & English (`en-IN`)
| Provider | Supported Formats | Malayalam WER (%) | Entity Accuracy (Names/Phones) | Latency (p50/p95) | Pricing | Notes / Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sarvam AI (Saaras)** | Streaming / Batch | TBD (Eval) | TBD (Eval) | TBD | ₹ / hr | Primary candidate for Indian accents/Malayalam |
| **OpenAI Whisper (Large-v3 / Turbo)** | Streaming via LiveKit | TBD | TBD | TBD | $0.006 / min | Fallback; higher WER on local dialects |
| **Google Cloud STT (Chirp / v2)** | Streaming gRPC | TBD | TBD | TBD | Tiered | Strong multilingual, but complex streaming setup |
| **Deepgram (Nova-2)** | Streaming WS | TBD | TBD | TBD | $0.0043 / min | Fast, check Malayalam vocabulary depth |

### Text-to-Speech (TTS) Providers for Malayalam
| Provider | Voice Models | Naturalness (1-5) | Latency (TTFB) | Streaming Support | Pricing | Notes / Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sarvam AI (Bulbul: v1/v2)** | `ananya`, `meera`, `arvind` | TBD (Human Rating) | TBD | Yes | ₹ / char | Tailored for Malayalam pronunciation |
| **ElevenLabs** | Multilingual v2 / Turbo | TBD | High | Yes | Premium | High quality, but higher cost and latency |
| **Google Cloud TTS (Neural2 / Journey)** | `ml-IN-Standard/Wavenet` | TBD | Low | Yes | Tiered | Reliable, but voice tone sounds robotic |

### Language Model (LLM) for Tool Calling & Malayalam Dialogue
| Model | Function Calling Reliability | Malayalam Fluency | Latency (TTFT) | Cost (1M Tokens) | Notes / Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Claude 3.5 Sonnet / 3.5 Haiku** | Excellent | Very Good | ~300-500ms | $0.80 - $3.00 | Leading tool reasoning & Malayalam coherence |
| **GPT-4o / GPT-4o-mini** | Very Good | Good | ~250-400ms | $0.15 - $2.50 | Fast, standard function calling format |
| **Gemini 1.5 Flash / 2.0 Flash** | Very Good | Good | ~200-350ms | Very Low | Ultra-fast; candidate for Realtime audio later |

---

## 2. Status of Key Operational Decisions (Section 8)

| # | Question / Decision Area | Status | Chosen Option / Strategy | Notes / Action Item |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Final STT / LLM / TTS provider set | 🟡 Testing | Sarvam STT + Claude 3.5 Haiku / GPT-4o-mini + Sarvam Bulbul TTS | Phase 0 benchmarks will confirm accuracy |
| **2** | Open-source licensing compliance | 🟢 Approved | Borrow patterns/ideas only; zero copy-paste from non-permissive repos | All code is written ground-up clean |
| **3** | Bookable services on Day 1 | 🟡 Pending | General Ayurveda Doctor Consultation, Panchakarma Consultation | Awaiting Sreerudra confirm on specific doctor IDs |
| **4** | Outbound reminders (SMS vs WhatsApp) | 🟢 Approved | Out of scope for v1. SMS confirmation post-call only | WhatsApp integration scheduled for Phase 6 |
| **5** | Audio retention period | 🟢 Approved | 30 Days default in S3; metadata and transcripts retained permanently | Implemented in `retention_sweeper.py` & documented in `RUNBOOK.md` |
| **6** | Hosting region & Data residency | 🟢 Approved | AWS India (`ap-south-1` Mumbai) or local VPS | Ensures compliance with India DPDP Act 2023 |
| **7** | Data ownership agreement | 🟢 Clarified | Sreerudra owns all patient and hospital data; ClinicVoice is data processor | Documented in SLA |
| **8** | Exotel number & DLT registration | 🟡 In Progress | Requires registered Exotel sender ID and DLT templates | Telephony mock used locally during development |
| **9** | Native Malayalam prompt reviewer | 🟡 Pending | Needs native speaker to score Phase 0 TTS samples | Team / Sreerudra partner to review audio clips |
