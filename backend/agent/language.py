from __future__ import annotations

import re


def detect_language(text: str) -> str:
    """
    Detect whether caller's speech is Malayalam or English.
    Checks for presence of Malayalam Unicode block (\u0D00-\u0D7F)
    or Manglish keywords.
    """
    if not text.strip():
        return "ml-IN"

    # Count Malayalam Unicode script characters
    malayalam_chars = len(re.findall(r"[\u0D00-\u0D7F]", text))
    total_alpha = len(re.findall(r"[a-zA-Z\u0D00-\u0D7F]", text))

    if total_alpha == 0:
        return "ml-IN"

    # If > 15% of characters are Malayalam script, classify as ml-IN
    if (malayalam_chars / total_alpha) > 0.15:
        return "ml-IN"

    # Check for common Romanized Malayalam ("Manglish") terms
    manglish_markers = [
        "namaskaram", "doctor", "varaan", "kaanan", "samayam",
        "appointment", "venam", "pattumo", "aano", "enthinaanu",
        "aale", "alle", "nanni", "alappuzha", "cherthala"
    ]
    lower = text.lower()
    if any(re.search(rf"\b{marker}\b", lower) for marker in manglish_markers):
        # Manglish callers prefer hearing Malayalam response
        return "ml-IN"

    return "en-IN"


class LanguageManager:
    """Tracks caller's active language across conversation turns and triggers switching."""

    def __init__(self, initial_language: str = "ml-IN") -> None:
        self.current_language = initial_language
        self.turn_count = 0

    def process_turn(self, caller_text: str) -> tuple[str, bool]:
        """
        Processes utterance and returns (active_language, did_switch).
        """
        detected = detect_language(caller_text)
        did_switch = False

        if detected != self.current_language:
            self.current_language = detected
            did_switch = True

        self.turn_count += 1
        return self.current_language, did_switch
