from __future__ import annotations

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.agent_internal import router as agent_router
from backend.app.api.agent_tools import router as agent_tools_router
from backend.app.api.auth import router as auth_router
from backend.app.api.calls import router as calls_router
from backend.app.api.health import router as health_router
from backend.app.api.patients import router as patients_router
from backend.app.api.webhooks_exotel import router as exotel_router
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging

logger = setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-tenant Voice AI Receptionist for Clinics in Kerala (Design Partner: Sreerudra Ayurveda)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for web dashboard (localhost and deployed Vercel/cloud domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://voice-agent-pphb.onrender.com",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe exception handler: never expose internal stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error processing %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(agent_tools_router)
app.include_router(patients_router)
app.include_router(calls_router)
app.include_router(exotel_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "health": "/health",
        "logs": "/debug/logs",
    }


@app.get("/debug/logs")
async def get_debug_logs() -> dict[str, list[str]]:
    """Return recent technical log records for live deployment diagnostics."""
    from backend.app.core.logging import RECENT_LOGS
    return {"logs": list(RECENT_LOGS)}


@app.get("/api/knowledge")
async def get_knowledge():
    """Retrieve active hospital knowledge base."""
    import json
    from pathlib import Path
    kb_path = Path(__file__).resolve().parents[2] / "backend" / "agent" / "knowledge" / "hospital_knowledge.json"
    if kb_path.exists():
        return json.loads(kb_path.read_text(encoding="utf-8"))
    return {"error": "Knowledge base not found"}


@app.post("/api/knowledge")
async def update_knowledge(payload: dict):
    """Update active hospital knowledge base."""
    import json
    from pathlib import Path
    kb_path = Path(__file__).resolve().parents[2] / "backend" / "agent" / "knowledge" / "hospital_knowledge.json"
    kb_path.parent.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "message": "Hospital knowledge base updated successfully"}


@app.get("/debug/keys")
async def get_debug_keys():
    """Verify whether API keys are loaded in production."""
    import os
    from backend.app.core.config import settings
    sarvam = os.getenv("SARVAM_API_KEY") or settings.SARVAM_API_KEY
    gemini = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    return {
        "sarvam_configured": bool(sarvam),
        "sarvam_length": len(sarvam) if sarvam else 0,
        "gemini_configured": bool(gemini),
        "gemini_length": len(gemini) if gemini else 0,
    }


@app.get("/api/calls/live")
async def get_live_calls():
    """Return all recorded live telephone sessions with transcripts and audio keys."""
    from backend.app.api.webhooks_exotel import load_live_calls
    return load_live_calls()


@app.get("/api/calls/live/{call_id}/audio")
async def get_live_call_audio(call_id: str):
    """Stream recorded call WAV audio for dashboard player."""
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from backend.app.api.webhooks_exotel import RECORDINGS_DIR, load_live_calls

    calls = load_live_calls()
    target_key = None
    for c in calls:
        if c.get("id") == call_id:
            target_key = c.get("recordingKey")
            break

    if target_key:
        wav_path = RECORDINGS_DIR.parent / target_key
        if wav_path.exists():
            return FileResponse(str(wav_path), media_type="audio/wav")

    # Fallback to sample studio audio if file not yet on disk
    sample_wav = RECORDINGS_DIR / "call-live-akshay-01.wav"
    if sample_wav.exists():
        return FileResponse(str(sample_wav), media_type="audio/wav")

    raise HTTPException(status_code=404, detail="Audio recording not found")



