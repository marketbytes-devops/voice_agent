from __future__ import annotations

import datetime
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    clinic_id: uuid.UUID | None = None
    name: str
    email: EmailStr
    role: str
    status: str


class WorkingHours(BaseModel):
    # e.g., {"0": {"start": "09:00", "end": "17:00"}, ...}
    schedule: dict[str, Any] = Field(default_factory=dict)


class ClinicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    name: str
    address: str | None = None
    timezone: str
    working_hours: dict[str, Any]
    languages: list[str]
    fallback_phone: str | None = None


class ResolveClinicRequest(BaseModel):
    dialed_number: str  # E.164 phone number dialed by caller


class ResolveClinicResponse(BaseModel):
    clinic_id: uuid.UUID
    clinic_name: str
    timezone: str
    working_hours: dict[str, Any]
    languages: list[str]
    fallback_phone: str | None
    greeting_ml: str | None
    greeting_en: str | None
    providers: dict[str, Any]
    doctors: list[dict[str, Any]]
    treatments: list[dict[str, Any]]
    faqs: list[dict[str, Any]]


class CallCreate(BaseModel):
    clinic_id: uuid.UUID
    caller_number: str | None = None
    language: str | None = "ml-IN"


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID | None = None
    caller_number: str | None = None
    language: str | None = None
    started_at: datetime.datetime
    outcome: str | None = None
    summary: str | None = None


class CallEventIn(BaseModel):
    call_id: uuid.UUID
    clinic_id: uuid.UUID
    type: str
    data: dict[str, Any] | None = None


class PatientCreate(BaseModel):
    name: str
    phone: str
    name_ml: str | None = None
    alt_phone: str | None = None
    age: int | None = None
    gender: str | None = None
    place: str | None = None
    preferred_language: str = "ml-IN"
    notes: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    name: str
    name_ml: str | None = None
    phone: str
    age: int | None = None
    gender: str | None = None
    place: str | None = None
    preferred_language: str
    created_at: datetime.datetime
