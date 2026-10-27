from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class SpeechToText(Protocol):
    name: str
    languages: list[str]  # e.g. ["ml-IN", "en-IN"]

    async def transcribe(self, audio_data: bytes, language: str) -> str:
        """Transcribe audio chunk/file and return text."""
        ...


class LanguageModel(Protocol):
    name: str
    supports_tools: bool

    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """Generate assistant response text or tool calls."""
        ...


class TextToSpeech(Protocol):
    name: str

    def voice_for(self, language: str) -> str:
        """Return the speaker voice name for a language."""
        ...

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        """Synthesize text into speech audio bytes."""
        ...


@dataclass
class ProviderSet:
    stt: SpeechToText
    llm: LanguageModel
    tts: TextToSpeech
