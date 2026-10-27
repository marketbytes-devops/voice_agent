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

# CORS configuration for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    }
