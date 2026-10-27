from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any
import httpx

# Ensure clinicvoice logger is configured
logger = logging.getLogger("clinicvoice")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class VoiceAgentWorker:
    """Minimal LiveKit Voice Agent worker for Phase 1 foundation."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        service_token: str = "dev_internal_service_token_123",
    ) -> None:
        self.api_base_url = api_base_url
        self.headers = {"X-Service-Token": service_token}

    async def resolve_clinic(self, dialed_number: str) -> dict[str, Any]:
        """Query backend to resolve dialed number to clinic configuration."""
        url = f"{self.api_base_url}/internal/agent/resolve-clinic"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"dialed_number": dialed_number}, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def create_call_record(self, clinic_id: str, caller_number: str) -> dict[str, Any]:
        """Create call entry in PostgreSQL database."""
        url = f"{self.api_base_url}/internal/agent/calls"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json={"clinic_id": clinic_id, "caller_number": caller_number, "language": "ml-IN"},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def log_call_event(self, clinic_id: str, call_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Log event to backend."""
        url = f"{self.api_base_url}/internal/agent/call-events"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                url,
                json={"clinic_id": clinic_id, "call_id": call_id, "type": event_type, "data": data},
                headers=self.headers,
            )

    async def handle_call(self, dialed_number: str, caller_number: str) -> dict[str, Any]:
        """
        Core call lifecycle handler:
        1. Resolve clinic context
        2. Create call row in PostgreSQL
        3. Emit bilingual greeting (Malayalam + English)
        4. Log call_started event
        """
        logger.info("Incoming call received from %s to dialed number %s", caller_number, dialed_number)

        clinic_info = await self.resolve_clinic(dialed_number)
        clinic_id = clinic_info["clinic_id"]
        clinic_name = clinic_info["clinic_name"]

        logger.info("Resolved clinic: '%s' (ID: %s)", clinic_name, clinic_id)

        # Create database record
        call_record = await self.create_call_record(clinic_id, caller_number)
        call_id = call_record["id"]
        logger.info("Created call record in database: Call ID=%s", call_id)

        # Log call started event
        await self.log_call_event(clinic_id, call_id, "call_started", {"caller": caller_number})

        # Compose bilingual greeting
        greeting_ml = clinic_info.get("greeting_ml") or f"നമസ്കാരം! {clinic_name}ലേക്ക് സ്വാഗതം."
        greeting_en = clinic_info.get("greeting_en") or f"Hello! Welcome to {clinic_name}. How can I assist you today?"
        full_greeting = f"{greeting_ml} {greeting_en}"

        logger.info("Agent spoke bilingual greeting: '%s'", full_greeting)
        await self.log_call_event(clinic_id, call_id, "agent_greeted", {"greeting": full_greeting})

        return {
            "call_id": call_id,
            "clinic_id": clinic_id,
            "clinic_name": clinic_name,
            "greeting": full_greeting,
        }


async def main() -> None:
    parser = argparse.ArgumentParser(description="ClinicVoice Minimal Voice Worker")
    parser.add_argument("--dialed", default="+919876500001", help="Dialed clinic number")
    parser.add_argument("--caller", default="+919876543210", help="Caller phone number")
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--simulate", action="store_true", default=True, help="Run standalone simulation call")

    args = parser.parse_args()
    worker = VoiceAgentWorker(api_base_url=args.api_url)

    logger.info("ClinicVoice Voice Agent worker initialized.")
    if args.simulate:
        try:
            summary = await worker.handle_call(dialed_number=args.dialed, caller_number=args.caller)
            logger.info("Simulation call completed successfully: %s", summary)
        except Exception as e:
            logger.error("Simulation call failed: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
