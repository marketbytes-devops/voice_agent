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
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"language_code": language, "model": "saaras:v3"}

        try:
            client = self._get_client()
            resp = await client.post(url, headers=headers, files=files, data=data)
            resp.raise_for_status()
            return resp.json().get("transcript", "")
        except Exception as e:
            logger.error("Sarvam STT failed: %s", e)
            return ""
