from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.agent.pilot_call_simulator import PilotCallSimulator
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models import Clinic, PhoneNumber


class TestPhase5PilotAndTelephony(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.mock_db = AsyncMock()
        self.mock_db.add = MagicMock()
        app.dependency_overrides[get_db] = self._override_get_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    async def _override_get_db(self):
        yield self.mock_db

    # 1. Exotel Inbound Voice Webhook: Returns SIP URI & Emergency Fallback
    def test_exotel_voice_webhook_returns_sip_and_fallback(self) -> None:
        mock_phone = PhoneNumber(
            id=MagicMock(),
            clinic_id=MagicMock(),
            e164="+919876500001",
            status="active",
        )
        mock_clinic = Clinic(
            id=mock_phone.clinic_id,
            organisation_id=MagicMock(),
            name="Sreerudra Ayurveda Hospital",
            fallback_phone="+914772251234",
            working_hours={},
        )

        mock_phone_res = MagicMock()
        mock_phone_res.scalar_one_or_none.return_value = mock_phone

        mock_clinic_res = MagicMock()
        mock_clinic_res.scalar_one_or_none.return_value = mock_clinic

        self.mock_db.execute.side_effect = [mock_phone_res, mock_clinic_res]

        resp = self.client.post(
            "/webhooks/exotel/voice",
            data={
                "CallSid": "exotel_call_abc123",
                "From": "+919876543210",
                "To": "+919876500001",
                "Direction": "inbound",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/xml")
        xml_content = resp.text

        # Verify LiveKit SIP URI is returned
        self.assertIn("<Sip>sip:919876500001@voiceagent-6aqqbru4.sip.livekit.cloud</Sip>", xml_content)
        # Verify Emergency Fallback circuit is returned
        self.assertIn("<Number>+914772251234</Number>", xml_content)

    # 2. Exotel Call Status / CDR Webhook
    def test_exotel_status_webhook(self) -> None:
        resp = self.client.post(
            "/webhooks/exotel/status",
            data={
                "CallSid": "exotel_call_abc123",
                "Status": "completed",
                "Duration": 78,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["call_sid"], "exotel_call_abc123")

    # 3. End-to-End Pilot Simulation Call Run
    async def test_end_to_end_pilot_call_simulation(self) -> None:
        simulator = PilotCallSimulator(caller_number="+919876543210")
        summary = await simulator.run_simulation()

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["outcome"], "Booked")
        self.assertEqual(summary["patient_name"], "Lakshmi")
        self.assertEqual(summary["doctor"], "Dr. Manoj")
        self.assertEqual(summary["slot_time"], "10:15 AM")
        self.assertGreaterEqual(summary["transcript_turns"], 5)


if __name__ == "__main__":
    unittest.main()
