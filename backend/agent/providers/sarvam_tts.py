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

    def voice_for(self, language: str) -> str:
        # Default Malayalam female voice in bulbul:v3: kavya or anushka
        return "kavya" if language == "ml-IN" else "kavya"

    async def synthesize(self, text: str, language: str = "ml-IN", voice: str | None = None) -> bytes:
        speaker = voice or self.voice_for(language)

        if not self.api_key:
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
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            audios = resp.json().get("audios", [])
            return base64.b64decode(audios[0]) if audios else b""
