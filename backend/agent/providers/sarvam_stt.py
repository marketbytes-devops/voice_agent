from __future__ import annotations

import logging
import os
from typing import Any
import httpx

logger = logging.getLogger("clinicvoice")


class SarvamSTTAdapter:
    """Sarvam AI Speech-to-Text provider adapter with mock fallback."""
    name = "sarvam_stt"
    languages = ["ml-IN", "en-IN"]

    def __init__(self, api_key: str | None = None) -> None:
        from backend.app.core.config import settings
        self.api_key = api_key or os.getenv("SARVAM_API_KEY") or settings.SARVAM_API_KEY
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=15.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def transcribe(self, audio_data: bytes, language: str = "ml-IN") -> str:
        if not self.api_key:
            logger.error("CRITICAL: SARVAM_API_KEY is missing in environment variables! Live STT disabled.")
            # Fallback mock for testing
            return "നമസ്കാരം, എനിക്ക് നാളെ ഡോക്ടർ മനോജിന് ഒരു അപ്പോയിന്റ്മെന്റ് വേണം"

        url = "https://api.sarvam.ai/speech-to-text"
        headers = {"api-subscription-key": self.api_key}

        # Dynamically detect audio container format from magic bytes
        filename = "audio.wav"
        mime_type = "audio/wav"
        if audio_data.startswith(b"\x1a\x45\xdf\xa3"):  # WebM / Matroska EBML header
            filename = "audio.webm"
            mime_type = "audio/webm"
        elif audio_data.startswith(b"ID3") or audio_data.startswith(b"\xff\xfb"):
            filename = "audio.mp3"
            mime_type = "audio/mp3"
        elif audio_data.startswith(b"OggS"):
            filename = "audio.ogg"
            mime_type = "audio/ogg"

        files = {"file": (filename, audio_data, mime_type)}
        data = {"language_code": language, "model": "saaras:v3"}

        try:
            client = self._get_client()
            resp = await client.post(url, headers=headers, files=files, data=data)
            resp.raise_for_status()
            return resp.json().get("transcript", "")
        except Exception as e:
            logger.error("Sarvam STT failed: %s", e)
            return ""
