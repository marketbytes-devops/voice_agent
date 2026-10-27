from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from jose import jwt

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.logging import PHONE_MASK_REGEX, SensitiveDataFilter
from backend.app.core.security import (
    UserRole,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_internal_service_token,
    verify_password,
)
from backend.app.main import app
from backend.app.models import Clinic, Patient, User
from backend.app.schemas import ResolveClinicResponse


class TestPhase1Foundation(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.mock_db = AsyncMock()
        # By default override get_db so tests don't try to connect to a real PostgreSQL instance
        app.dependency_overrides[get_db] = self._override_get_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    async def _override_get_db(self):
        yield self.mock_db

    # 1. Health Checks
    def test_health_endpoint(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app"], settings.APP_NAME)

    def test_ready_endpoint(self) -> None:
        self.mock_db.execute.return_value = None
        resp = self.client.get("/ready")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("database", data)

    # 2. Authentication & Password Hashing
    def test_password_hashing_and_verification(self) -> None:
        raw_pw = "Sreerudra@2026!"
        hashed = get_password_hash(raw_pw)
        self.assertNotEqual(raw_pw, hashed)
        self.assertTrue(verify_password(raw_pw, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))

    def test_jwt_token_generation_and_decoding(self) -> None:
        user_id = str(uuid.uuid4())
        clinic_id = str(uuid.uuid4())
        token = create_access_token(
            data={"sub": user_id, "role": UserRole.RECEPTIONIST.value, "clinic_id": clinic_id}
        )
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], user_id)
        self.assertEqual(payload["role"], UserRole.RECEPTIONIST.value)
        self.assertEqual(payload["clinic_id"], clinic_id)
        self.assertIn("exp", payload)

    # 3. Privacy & Sensitive Data Masking (AGENTS.md Rule)
    def test_phone_number_masking_in_logs(self) -> None:
        log_filter = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "Incoming call received from 9876543210 for appointment"
        log_filter.filter(record)
        self.assertNotIn("9876543210", record.msg)
        self.assertIn("98****3210", record.msg)

    # 4. Internal Service Token Protection
    def test_service_token_validation(self) -> None:
        # Missing token
        resp = self.client.post("/internal/agent/resolve-clinic", json={"dialed_number": "+919876500001"})
        self.assertEqual(resp.status_code, 422)  # missing required header

        # Invalid token
        resp = self.client.post(
            "/internal/agent/resolve-clinic",
            json={"dialed_number": "+919876500001"},
            headers={"X-Service-Token": "wrong_token"},
        )
        self.assertEqual(resp.status_code, 403)

    # 5. Tenant Isolation Logic (AGENTS.md Rule: Cross-clinic reads must fail)
    def test_tenant_isolation_patient_access(self) -> None:
        clinic_a_id = uuid.uuid4()
        clinic_b_id = uuid.uuid4()

        # Patient belonging to Clinic A
        patient_a = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_a_id,
            name="Rahul Nair",
            name_ml="രാഹുൽ നായർ",
            phone="9876543210",
            preferred_language="ml-IN",
            created_at=datetime.now(timezone.utc),
        )

        # User belonging to Clinic B (different clinic)
        user_b = User(
            id=uuid.uuid4(),
            organisation_id=uuid.uuid4(),
            clinic_id=clinic_b_id,
            name="Clinic B Receptionist",
            email="receptionist@clinicb.com",
            password_hash="hash",
            role=UserRole.RECEPTIONIST.value,
            status="active",
        )

        # Mock DB session where querying patient_a with user_b's clinic_id returns None (RLS block)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        # Simulate query: when clinic_id is clinic_b, patient_a is filtered out by RLS / query clause
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from backend.app.api.auth import get_current_user
        from backend.app.api.patients import get_tenant_db

        app.dependency_overrides[get_current_user] = lambda: user_b
        async def _override_tenant():
            yield mock_db
        app.dependency_overrides[get_tenant_db] = _override_tenant

        try:
            # Clinic B tries to read Clinic A's patient
            resp = self.client.get(f"/patients/{patient_a.id}")
            # Must return 404 (Not Found / Hidden by Tenant Isolation)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.json()["detail"], "Patient not found")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_tenant_db, None)

    # 6. Clinic Resolution Endpoint (Bilingual Context for Agent)
    def test_clinic_resolution_success(self) -> None:
        clinic_id = uuid.uuid4()
        mock_db = AsyncMock()

        # Mock phone number with clinic attached
        mock_phone = MagicMock()
        mock_clinic = MagicMock()
        mock_clinic.id = clinic_id
        mock_clinic.name = "Sreerudra Ayurveda Hospital"
        mock_clinic.timezone = "Asia/Kolkata"
        mock_clinic.working_hours = {"0": {"start": "09:00", "end": "17:00"}}
        mock_clinic.languages = ["ml-IN", "en-IN"]
        mock_clinic.fallback_phone = "+919876599999"
        mock_phone.clinic = mock_clinic

        # Setup mock returns for queries: phone, agent_settings, doctors, treatments, faqs
        phone_res = MagicMock()
        phone_res.scalar_one_or_none.return_value = mock_phone

        settings_mock = MagicMock()
        settings_mock.greeting_ml = "നമസ്കാരം! ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിലേക്ക് സ്വാഗതം."
        settings_mock.greeting_en = "Hello! Welcome to Sreerudra Ayurveda Hospital."
        settings_mock.providers = {"stt": "sarvam", "tts": "sarvam_bulbul"}
        settings_res = MagicMock()
        settings_res.scalar_one_or_none.return_value = settings_mock

        docs_res = MagicMock()
        docs_res.scalars.return_value.all.return_value = []

        treatments_res = MagicMock()
        treatments_res.scalars.return_value.all.return_value = []

        faqs_res = MagicMock()
        faqs_res.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [phone_res, settings_res, docs_res, treatments_res, faqs_res]

        async def _override_clinic_db():
            yield mock_db
        app.dependency_overrides[get_db] = _override_clinic_db
        try:
            resp = self.client.post(
                "/internal/agent/resolve-clinic",
                json={"dialed_number": "+919876500001"},
                headers={"X-Service-Token": settings.INTERNAL_SERVICE_TOKEN},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["clinic_name"], "Sreerudra Ayurveda Hospital")
            self.assertIn("ശ്രീരുദ്ര", data["greeting_ml"])
            self.assertIn("Sreerudra", data["greeting_en"])
            self.assertEqual(data["languages"], ["ml-IN", "en-IN"])
        finally:
            app.dependency_overrides.pop(get_db, None)


if __name__ == "__main__":
    unittest.main()
