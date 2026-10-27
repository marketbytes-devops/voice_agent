from __future__ import annotations

import datetime
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException, Request

from backend.app.core.logging import SensitiveDataFilter
from backend.app.core.rate_limit import SlidingWindowRateLimiter
from backend.app.models import Call, CallEvent
from backend.app.services.audit_service import record_audit_event
from backend.app.services.retention_sweeper import purge_expired_recordings
from backend.app.services.storage_service import storage_service


class TestPhase4SecurityAndRetention(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.clinic_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.mock_db = AsyncMock()
        self.mock_db.add = MagicMock()

    # 1. Retention Sweeper: Purges recordings older than 30 days while preserving metadata
    async def test_retention_sweeper_purges_old_recordings(self) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        old_time = now - datetime.timedelta(days=45)

        old_call = Call(
            id=uuid.uuid4(),
            clinic_id=self.clinic_id,
            caller_number="+919876543210",
            language="ml-IN",
            started_at=old_time,
            duration_sec=120,
            outcome="Booked",
            summary="Patient booked consultation",
            recording_key="clinic-1/2026/09/old_audio.wav",
        )

        # Mock db.execute returning old_call
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [old_call]
        self.mock_db.execute.return_value = mock_result

        # Dry-run check first
        dry_res = await purge_expired_recordings(self.mock_db, retention_days=30, dry_run=True)
        self.assertEqual(dry_res["found_count"], 1)
        self.assertEqual(dry_res["purged_count"], 0)
        self.assertTrue(dry_res["dry_run"])
        self.assertEqual(old_call.recording_key, "clinic-1/2026/09/old_audio.wav")

        # Actual purge execution
        purge_res = await purge_expired_recordings(self.mock_db, retention_days=30, dry_run=False)
        self.assertEqual(purge_res["purged_count"], 1)
        self.assertEqual(purge_res["failed_count"], 0)

        # Verify old call recording was cleared and metadata preserved
        self.assertIsNone(old_call.recording_key)
        self.assertEqual(old_call.outcome, "Booked")

        # Verify CallEvent was added
        added_objects = [call_args[0][0] for call_args in self.mock_db.add.call_args_list]
        event_types = [obj.type for obj in added_objects if isinstance(obj, CallEvent)]
        self.assertIn("recording_purged", event_types)

        # Verify db.commit was called
        self.assertTrue(self.mock_db.commit.called)

    # 2. Rate Limiting: Blocks brute-force attempts with HTTP 429
    async def test_sliding_window_rate_limiter(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)

        mock_req = MagicMock(spec=Request)
        mock_req.headers = {}
        mock_client = MagicMock()
        mock_client.host = "192.168.1.50"
        mock_req.client = mock_client

        # Requests 1, 2, 3 must succeed
        await limiter(mock_req)
        await limiter(mock_req)
        await limiter(mock_req)

        # 4th request must raise HTTP 429 Too Many Requests
        with self.assertRaises(HTTPException) as cm:
            await limiter(mock_req)

        self.assertEqual(cm.exception.status_code, 429)
        self.assertIn("Retry-After", cm.exception.headers)

    # 3. Phone Number Masking & PII Redaction
    def test_sensitive_data_phone_masking(self) -> None:
        filter_instance = SensitiveDataFilter()

        samples = [
            ("Caller phone is +919876543210 for Dr. Manoj", "Caller phone is +91 98****3210 for Dr. Manoj"),
            ("Dialing +91 98765 43210 right now", "Dialing +91 98****3210 right now"),
            ("Contact 9876543210 confirmed", "Contact +91 98****3210 confirmed"),
            ("Local 09876543210 recorded", "Local +91 98****3210 recorded"),
            ("Hyphenated +91-98765-43210 in log", "Hyphenated +91 98****3210 in log"),
        ]

        for original, expected in samples:
            masked = filter_instance.mask_phone_string(original)
            self.assertEqual(masked, expected)

    # 4. Storage Key Safety & Path Traversal Prevention
    def test_storage_key_validation(self) -> None:
        # Valid keys
        self.assertTrue(storage_service.validate_key("clinic-uuid/2026/10/call_123.wav"))
        self.assertTrue(storage_service.validate_key("recordings/patient-456.mp3"))

        # Dangerous path traversal attacks must be rejected
        self.assertFalse(storage_service.validate_key("../../etc/shadow"))
        self.assertFalse(storage_service.validate_key("../../../windows/system32/cmd.exe"))
        self.assertFalse(storage_service.validate_key("clinic/key; rm -rf /"))
        self.assertFalse(storage_service.validate_key(""))

    # 5. Audit Logging Service
    async def test_audit_logging_event_creation(self) -> None:
        entry = await record_audit_event(
            self.mock_db,
            action="view_patient_record",
            clinic_id=self.clinic_id,
            user_id=self.user_id,
            record="Patient P-999 accessed by Dr. Manoj",
        )

        self.mock_db.add.assert_called_with(entry)
        self.assertTrue(self.mock_db.flush.called)
        self.assertEqual(entry.action, "view_patient_record")
        self.assertEqual(entry.user_id, self.user_id)
        self.assertEqual(entry.clinic_id, self.clinic_id)
        self.assertIsNotNone(entry.at)


if __name__ == "__main__":
    unittest.main()
