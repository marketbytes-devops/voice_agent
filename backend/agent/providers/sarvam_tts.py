from __future__ import annotations

import base64
import logging
import os
import struct
import httpx

logger = logging.getLogger("clinicvoice")


class SarvamTTSAdapter:
    """Sarvam AI Bulbul Text-to-Speech provider adapter."""
    name = "sarvam_bulbul"

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

    def voice_for(self, language: str) -> str:
        # Default Malayalam female voice in bulbul:v3: kavya or anushka
        return "kavya" if language == "ml-IN" else "kavya"

    async def synthesize(self, text: str, language: str = "ml-IN", voice: str | None = None) -> bytes:
        speaker = voice or self.voice_for(language)

        if not self.api_key:
            logger.error("CRITICAL: SARVAM_API_KEY is missing in environment variables! Live TTS disabled, generating silent fallback.")
            # Fallback mock audio generation (0.5s valid WAV)
            sample_rate = 8000
            num_samples = 4000
            data_size = num_samples * 2
            header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF", data_size + 36, b"WAVE", b"fmt ",
                16, 1, 1, sample_rate, sample_rate * 2, 2, 16, b"data", data_size,
            )
            return header + (b"\x00" * data_size)

        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text],
            "target_language_code": language,
            "speaker": speaker,
            "speech_sample_rate": 8000,
            "model": "bulbul:v3",
            "pace": 1.05,
        }

        client = self._get_client()
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        audios = resp.json().get("audios", [])
        return base64.b64decode(audios[0]) if audios else b""
