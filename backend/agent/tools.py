from __future__ import annotations

import logging
from typing import Any
import httpx

logger = logging.getLogger("clinicvoice")


class AgentToolExecutor:
    """Executes backend function tools called by the Language Model during a call."""

    def __init__(self, api_base_url: str, service_token: str, clinic_id: str, call_id: str) -> None:
        self.api_base_url = api_base_url
        self.headers = {"X-Service-Token": service_token}
        self.clinic_id = clinic_id
        self.call_id = call_id

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch tool call to corresponding backend endpoint."""
        endpoint_map = {
            "find_or_create_patient": "find-or-create-patient",
            "get_free_slots": "get-free-slots",
            "book_appointment": "book-appointment",
            "reschedule_appointment": "reschedule-appointment",
            "cancel_appointment": "cancel-appointment",
            "get_clinic_info": "get-clinic-info",
            "transfer_call": "transfer-call",
            "request_callback": "request-callback",
            "escalate_emergency": "escalate-emergency",
        }

        path = endpoint_map.get(tool_name)
        if not path:
            return {"error": f"Unknown tool: {tool_name}"}

        payload = arguments.copy()
        payload["clinic_id"] = self.clinic_id
        if "call_id" not in payload:
            payload["call_id"] = self.call_id

        url = f"{self.api_base_url}/internal/agent/tools/{path}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Backend tool execution failed for '%s': %s", tool_name, e)
            # Return safe, generic error message to LLM (Rule in AGENTS.md)
            return {"error": "The hospital backend system is momentarily busy. Please try again or suggest a callback."}
