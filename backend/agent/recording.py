from __future__ import annotations

import logging
from typing import Any
import httpx

logger = logging.getLogger("clinicvoice")


class ConsentGatedRecorder:
    """Manages recording consent gating adhering to healthcare privacy requirements."""

    def __init__(self, api_base_url: str, service_token: str, clinic_id: str, call_id: str) -> None:
        self.api_base_url = api_base_url
        self.headers = {"X-Service-Token": service_token}
        self.clinic_id = clinic_id
        self.call_id = call_id
        self.consent_given: bool | None = None
        self.is_recording = False

    async def log_consent(self, given: bool) -> None:
        """Persist recording consent decision to backend consent_log table."""
        self.consent_given = given
        self.is_recording = given

        logger.info(
            "Consent decision for Call %s: %s",
            self.call_id,
            "GRANTED (Recording Started)" if given else "REFUSED (Recording Disabled)",
        )

        url = f"{self.api_base_url}/internal/agent/call-events"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    url,
                    json={
                        "clinic_id": self.clinic_id,
                        "call_id": self.call_id,
                        "type": "recording_consent_logged",
                        "data": {"consent_given": given},
                    },
                    headers=self.headers,
                )
        except Exception as e:
            logger.warning("Could not persist consent log to backend: %s", e)

    def should_record_audio(self) -> bool:
        """Only returns True if caller explicitly agreed to call recording."""
        return self.is_recording is True
