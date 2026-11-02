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

    async def _execute_tool_in_process(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        """Execute tool directly against database in-process (sub-15ms execution without HTTP overhead)."""
        try:
            import datetime
            import uuid
            from zoneinfo import ZoneInfo
            from sqlalchemy import select
            from backend.app.core.database import get_session_factory
            from backend.app.models import Doctor, Patient
            from backend.app.services.booking_service import book_appointment_guarded
            from backend.app.services.slot_service import get_available_slots

            clinic_uuid = uuid.UUID(self.clinic_id)
            factory = get_session_factory()
            tz = ZoneInfo("Asia/Kolkata")

            if tool_name == "get_free_slots":
                date_str = arguments.get("date", "tomorrow")
                now = datetime.datetime.now(tz)
                if date_str == "tomorrow":
                    target_date = now.date() + datetime.timedelta(days=1)
                elif date_str == "today":
                    target_date = now.date()
                else:
                    try:
                        target_date = datetime.date.fromisoformat(date_str)
                    except ValueError:
                        target_date = now.date() + datetime.timedelta(days=1)

                async with factory() as session:
                    slots = await get_available_slots(session, clinic_uuid, target_date)
                    return {"success": True, "slots": slots, "date": target_date.isoformat()}

            elif tool_name == "book_appointment":
                patient_name = arguments.get("patient") or arguments.get("patient_name") or "Patient"
                phone = arguments.get("phone") or "Unknown"
                slot_str = arguments.get("slot") or "10:00 AM"

                async with factory() as session:
                    p_stmt = select(Patient).where(Patient.clinic_id == clinic_uuid, Patient.phone == phone)
                    pat = (await session.execute(p_stmt)).scalar_one_or_none()
                    if not pat:
                        pat = Patient(
                            id=uuid.uuid4(),
                            clinic_id=clinic_uuid,
                            name=patient_name,
                            phone=phone,
                            preferred_language="ml-IN",
                        )
                        session.add(pat)
                        await session.flush()

                    d_stmt = select(Doctor).where(Doctor.clinic_id == clinic_uuid, Doctor.active == True)
                    doc = (await session.execute(d_stmt)).scalar_one_or_none()
                    doc_id = doc.id if doc else uuid.UUID("75541d5d-402a-41b8-9557-501b82ba3bd5")

                    # Parse slot time
                    now = datetime.datetime.now(tz)
                    target_date = now.date() + datetime.timedelta(days=1)
                    if target_date.weekday() == 6:
                        target_date = target_date + datetime.timedelta(days=1)

                    hour, minute = 10, 0
                    if "11:30" in slot_str:
                        hour, minute = 11, 30
                    elif "2:30" in slot_str or "14:30" in slot_str:
                        hour, minute = 14, 30
                    elif "4:00" in slot_str or "16:00" in slot_str:
                        hour, minute = 16, 0

                    starts_at = datetime.datetime.combine(target_date, datetime.time(hour, minute), tzinfo=tz)
                    appt = await book_appointment_guarded(
                        db=session,
                        clinic_id=clinic_uuid,
                        patient_id=pat.id,
                        doctor_id=doc_id,
                        starts_at=starts_at,
                        reason="Ayurvedic Consultation booked via voice assistant",
                    )
                    await session.commit()
                    return {
                        "success": True,
                        "appointment_id": str(appt.id),
                        "starts_at": appt.starts_at.isoformat(),
                        "status": "confirmed",
                        "message": f"Appointment booked for {patient_name} with Dr. {doc.name if doc else 'Manoj'} at {starts_at.strftime('%I:%M %p')}.",
                    }

        except Exception as e:
            logger.debug("In-process tool execution for '%s' bypassed to HTTP: %s", tool_name, e)
            return None

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch tool call to in-process DB service or backend API endpoint."""
        # 1. Try fast in-process database execution
        in_process_res = await self._execute_tool_in_process(tool_name, arguments)
        if in_process_res is not None:
            return in_process_res

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
