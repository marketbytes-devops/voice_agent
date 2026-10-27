from __future__ import annotations

import difflib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

logger = logging.getLogger("clinicvoice")


class STTProvider(Protocol):
    """Protocol for Speech-to-Text providers in the benchmark harness."""
    name: str

    async def transcribe(self, audio_path: Path, language: str) -> str:
        """Transcribe an audio file and return the transcript string."""
        ...


@dataclass
class STTResult:
    audio_file: str
    reference: str
    hypothesis: str
    wer: float
    cer: float
    entity_metrics: dict[str, bool] = field(default_factory=dict)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate (WER) using Levenshtein distance on words."""
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
    distance = sum(
        max(tag_len_a, tag_len_b)
        for tag, alo, ahi, blo, bhi in matcher.get_opcodes()
        if tag != "equal"
        for tag_len_a, tag_len_b in [(ahi - alo, bhi - blo)]
    )
    return round(min(1.0, distance / len(ref_words)), 4)


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate (CER) on normalized text."""
    ref_chars = list(re.sub(r"\s+", "", reference.strip()))
    hyp_chars = list(re.sub(r"\s+", "", hypothesis.strip()))

    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    matcher = difflib.SequenceMatcher(None, ref_chars, hyp_chars)
    distance = sum(
        max(tag_len_a, tag_len_b)
        for tag, alo, ahi, blo, bhi in matcher.get_opcodes()
        if tag != "equal"
        for tag_len_a, tag_len_b in [(ahi - alo, bhi - blo)]
    )
    return round(min(1.0, distance / len(ref_chars)), 4)


MALAYALAM_DIGIT_MAP = {
    "പൂജ്യം": "0",
    "ഒന്ന്": "1",
    "രണ്ട്": "2",
    "മൂന്ന്": "3",
    "നാല്": "4",
    "അഞ്ച്": "5",
    "ആറ്": "6",
    "ഏഴ്": "7",
    "എട്ട്": "8",
    "ഒൻപത്": "9",
}


def normalize_malayalam_text(text: str) -> str:
    """Normalize Malayalam text by mapping spoken digit words to numbers, collapsing digit spaces, and cleaning spaces."""
    normalized = text
    for word, digit in MALAYALAM_DIGIT_MAP.items():
        normalized = normalized.replace(word, digit)
    # Collapse spaces between consecutive single digits (e.g., "9 8 7" -> "987")
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
    # Remove excessive punctuation/spaces
    normalized = re.sub(r"[,\.!?]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract standard clinic entities: phone numbers, times, and key tokens."""
    norm = normalize_malayalam_text(text)
    # Normalized digits
    phones = re.findall(r"\b(?:\+91|0)?[6-9]\d{9}\b", norm)
    # Basic time patterns (e.g., 10:00, 10 AM, 10 മണിക്ക്)
    times = re.findall(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM|മണിക്ക്|മണി)?\b", norm)

    return {
        "phone_numbers": phones,
        "times": times,
    }


def evaluate_entities(reference: str, hypothesis: str, expected_entities: dict[str, str]) -> dict[str, bool]:
    """Check whether critical entities appear in hypothesis, accounting for Malayalam inflections."""
    results: dict[str, bool] = {}
    norm_hyp = normalize_malayalam_text(hypothesis).lower()

    for entity_type, expected_val in expected_entities.items():
        norm_expected = normalize_malayalam_text(expected_val).lower()
        if norm_expected in norm_hyp:
            results[entity_type] = True
            continue

        # Handle Malayalam noun case inflections (e.g., മനോജ് -> മനോജിനെ / മനോജിന്റെ)
        # Strip trailing virama / chandrakkala (\u0D4D) from root
        root = norm_expected.rstrip("\u0D4D")
        if len(root) >= 2 and root in norm_hyp:
            results[entity_type] = True
        else:
            results[entity_type] = False

    return results


class MockSTTProvider:
    """Mock STT provider for offline verification without API costs."""
    name = "mock_stt"

    def __init__(self, simulated_error_rate: float = 0.05) -> None:
        self.simulated_error_rate = simulated_error_rate

    async def transcribe(self, audio_path: Path, language: str) -> str:
        # Check if paired reference transcript exists
        ref_path = audio_path.with_suffix(".txt")
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip()
        return "നമസ്കാരം, ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റൽ ഡോക്ടർ അപ്പോയിന്റ്മെന്റ് വേണം 9876543210"


class SarvamSTTProvider:
    """Sarvam AI STT provider (Saaras model) for Malayalam & Indian English."""
    name = "sarvam_saaras"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    async def transcribe(self, audio_path: Path, language: str = "ml-IN") -> str:
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable is not set.")

        import httpx  # type: ignore

        url = "https://api.sarvam.ai/speech-to-text"
        headers = {"api-subscription-key": self.api_key}

        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/wav")}
                data = {"language_code": language, "model": "saaras:v1"}
                response = await client.post(url, headers=headers, files=files, data=data)
                response.raise_for_status()
                payload = response.json()
                return payload.get("transcript", "")


async def run_stt_benchmark(
    dataset_dir: Path,
    provider: STTProvider,
    language: str = "ml-IN"
) -> dict[str, any]:
    """Run full benchmark across dataset directory."""
    gt_file = dataset_dir / "ground_truth.json"
    if not gt_file.exists():
        raise FileNotFoundError(f"Missing ground_truth.json in {dataset_dir}")

    samples = json.loads(gt_file.read_text(encoding="utf-8"))
    results: list[STTResult] = []

    for item in samples:
        audio_name = item["audio_file"]
        reference = item["reference"]
        expected_entities = item.get("entities", {})
        audio_path = dataset_dir / audio_name

        try:
            hypothesis = await provider.transcribe(audio_path, language=language)
        except Exception as e:
            logger.error("Failed to transcribe %s: %s", audio_name, e)
            hypothesis = ""

        norm_ref = normalize_malayalam_text(reference)
        norm_hyp = normalize_malayalam_text(hypothesis)
        wer = calculate_wer(norm_ref, norm_hyp)
        cer = calculate_cer(norm_ref, norm_hyp)
        ent_metrics = evaluate_entities(reference, hypothesis, expected_entities)

        results.append(
            STTResult(
                audio_file=audio_name,
                reference=reference,
                hypothesis=hypothesis,
                wer=wer,
                cer=cer,
                entity_metrics=ent_metrics,
            )
        )

    # Aggregate metrics
    avg_wer = sum(r.wer for r in results) / len(results) if results else 0.0
    avg_cer = sum(r.cer for r in results) / len(results) if results else 0.0

    all_entities = [m for r in results for m in r.entity_metrics.values()]
    entity_acc = sum(1 for m in all_entities if m) / len(all_entities) if all_entities else 0.0

    return {
        "provider": provider.name,
        "language": language,
        "sample_count": len(results),
        "avg_wer": round(avg_wer, 4),
        "avg_cer": round(avg_cer, 4),
        "entity_accuracy": round(entity_acc, 4),
        "details": [
            {
                "file": r.audio_file,
                "reference": r.reference,
                "hypothesis": r.hypothesis,
                "wer": r.wer,
                "cer": r.cer,
                "entities": r.entity_metrics,
            }
            for r in results
        ],
    }
