from __future__ import annotations

from typing import Any
from backend.agent.providers.base import ProviderSet
from backend.agent.providers.llm_provider import LLMAdapter
from backend.agent.providers.sarvam_stt import SarvamSTTAdapter
from backend.agent.providers.sarvam_tts import SarvamTTSAdapter


def build_providers(clinic_settings: dict[str, Any] | None = None) -> ProviderSet:
    """
    Factory creating STT, LLM, and TTS providers dynamically from clinic configuration.
    Allows changing providers per clinic without altering business or call logic.
    """
    settings = clinic_settings or {}
    providers_config = settings.get("providers", {})

    # STT Provider
    stt_name = providers_config.get("stt", "sarvam")
    stt = SarvamSTTAdapter()

    # LLM Provider
    llm_name = providers_config.get("llm", "openai")
    model = providers_config.get("llm_model", "gpt-4o-mini")
    llm = LLMAdapter(model=model)

    # TTS Provider
    tts_name = providers_config.get("tts", "sarvam_bulbul")
    tts = SarvamTTSAdapter()

    return ProviderSet(stt=stt, llm=llm, tts=tts)
