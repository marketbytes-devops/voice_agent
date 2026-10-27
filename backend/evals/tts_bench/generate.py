from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import struct
import sys
from pathlib import Path
from typing import Protocol

logger = logging.getLogger("clinicvoice")


class TTSProvider(Protocol):
    """Protocol for Text-to-Speech providers in the evaluation harness."""
    name: str

    async def synthesize(self, text: str, language: str, speaker: str) -> bytes:
        """Synthesize text and return raw audio bytes (WAV/MP3)."""
        ...


class MockTTSProvider:
    """Generates a minimal valid PCM WAV file for offline testing."""
    name = "mock_tts"

    async def synthesize(self, text: str, language: str, speaker: str) -> bytes:
        # Create 0.5s of 8000Hz 16-bit mono silence with standard WAV header
        sample_rate = 8000
        num_channels = 1
        bits_per_sample = 16
        num_samples = int(sample_rate * 0.5)
        byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
        block_align = num_channels * (bits_per_sample // 8)
        data_size = num_samples * block_align
        header_size = 44

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            data_size + header_size - 8,
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            num_channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b"data",
            data_size,
        )
        silence = b"\x00" * data_size
        return header + silence


class SarvamTTSProvider:
    """Sarvam AI Bulbul TTS provider."""
    name = "sarvam_bulbul"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    async def synthesize(self, text: str, language: str = "ml-IN", speaker: str = "meera") -> bytes:
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable is not set.")

        import base64
        import httpx  # type: ignore

        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text],
            "target_language_code": language,
            "speaker": speaker,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "model": "bulbul:v1",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            audios = data.get("audios", [])
            if not audios:
                raise RuntimeError("No audio returned from Sarvam TTS")
            return base64.b64decode(audios[0])


def generate_rating_sheet(samples: list[dict[str, str]], output_dir: Path) -> Path:
    """Generate Markdown score sheet for native Malayalam speakers to evaluate audio."""
    sheet_lines = [
        "# Sreerudra Ayurveda Hospital - TTS Audio Evaluation Score Sheet",
        "",
        "Please listen to the audio files in this directory and score each sentence on a scale of 1-5:",
        "- **Naturalness (1-5):** Does the voice sound natural or robotic?",
        "- **Malayalam Pronunciation (1-5):** Are Ayurvedic and Kerala terms pronounced accurately?",
        "- **Pacing (1-5):** Is the speed comfortable for a phone call?",
        "- **Pass / Fail:** Overall recommendation for live clinic calls.",
        "",
        "| ID | Category | Sentence (Malayalam / English) | Audio File | Naturalness (1-5) | Pronunciation (1-5) | Pacing (1-5) | Decision (Pass/Fail) | Notes |",
        "| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |",
    ]

    for item in samples:
        audio_name = f"{item['id']}.wav"
        escaped_text = item["text"].replace("|", "/")
        sheet_lines.append(
            f"| `{item['id']}` | {item['category']} | {escaped_text} | [{audio_name}]({audio_name}) |  |  |  |  |  |"
        )

    sheet_lines.append("")
    sheet_lines.append("### Evaluator Details:")
    sheet_lines.append("- **Evaluator Name:** _______________________")
    sheet_lines.append("- **Native Malayalam Speaker:** [ ] Yes  [ ] No")
    sheet_lines.append("- **Date:** _______________________")
    sheet_lines.append("")

    sheet_path = output_dir / "ratings_sheet.md"
    sheet_path.write_text("\n".join(sheet_lines), encoding="utf-8")
    return sheet_path


async def run_tts_generation(
    sentences_file: Path,
    output_dir: Path,
    provider: TTSProvider,
    speaker: str = "meera",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sentences = json.loads(sentences_file.read_text(encoding="utf-8"))

    print(f"Generating {len(sentences)} audio samples with provider '{provider.name}' (speaker: {speaker})...")

    for item in sentences:
        audio_path = output_dir / f"{item['id']}.wav"
        safe_snippet = item["text"][:35].encode("ascii", errors="replace").decode("ascii")
        print(f" -> Synthesizing [{item['id']}]: {safe_snippet}...")
        audio_bytes = await provider.synthesize(
            text=item["text"],
            language=item.get("language", "ml-IN"),
            speaker=speaker,
        )
        audio_path.write_bytes(audio_bytes)

    sheet_path = generate_rating_sheet(sentences, output_dir)
    print(f"\nCompleted! Generated {len(sentences)} audio files in {output_dir}")
    print(f"Rating sheet generated at: {sheet_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ClinicVoice TTS Evaluation Generator")
    parser.add_argument("--provider", choices=["mock", "sarvam"], default="mock")
    parser.add_argument("--speaker", default="meera", help="Sarvam speaker voice (meera, ananya, arvind)")
    parser.add_argument(
        "--sentences",
        type=Path,
        default=Path(__file__).parent / "sentences.json",
        help="Path to sentences.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "output",
        help="Directory to save generated audio files and rating sheet",
    )

    args = parser.parse_args()

    if args.provider == "sarvam":
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            print("ERROR: SARVAM_API_KEY environment variable not set. To test offline, use --provider mock.")
            sys.exit(1)
        provider = SarvamTTSProvider(api_key=api_key)
    else:
        provider = MockTTSProvider()

    asyncio.run(run_tts_generation(args.sentences, args.output_dir, provider, speaker=args.speaker))


if __name__ == "__main__":
    main()
