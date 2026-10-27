from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import get_current_user
from backend.app.core.database import get_db
from backend.app.models import Patient, User
from backend.app.schemas import PatientCreate, PatientOut

router = APIRouter(prefix="/patients", tags=["Patients"])


async def get_tenant_db(
    current_user: User = Depends(get_current_user),
) -> AsyncSession:
    """Provides a database session with the authenticated user's clinic_id set for RLS."""
    if not current_user.clinic_id and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with a clinic tenant",
        )
    async for session in get_db(clinic_id=current_user.clinic_id):
        yield session


@router.post("/", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
async def create_patient(
    req: PatientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientOut:
    """Create a new patient record within the user's clinic tenant."""
    # Enforce tenant clinic_id
    patient = Patient(
        clinic_id=current_user.clinic_id,
        name=req.name,
        name_ml=req.name_ml,
        phone=req.phone,
        alt_phone=req.alt_phone,
        age=req.age,
        gender=req.gender,
        place=req.place,
        preferred_language=req.preferred_language,
        notes=req.notes,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/", response_model=list[PatientOut])
async def list_patients(
    query: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[PatientOut]:
    """List patients for the active clinic tenant. RLS prevents cross-clinic leakage."""
    stmt = select(Patient)
    if current_user.clinic_id:
        stmt = stmt.where(Patient.clinic_id == current_user.clinic_id)
    if query:
        stmt = stmt.where(Patient.name.ilike(f"%{query}%") | Patient.phone.contains(query))

    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientOut:
    """Retrieve specific patient. Protected by tenant ownership and RLS."""
    stmt = select(Patient).where(Patient.id == patient_id)
    if current_user.clinic_id:
        stmt = stmt.where(Patient.clinic_id == current_user.clinic_id)

    res = await db.execute(stmt)
    patient = res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    from backend.app.services.audit_service import record_audit_event
    await record_audit_event(
        db,
        action="view_patient_record",
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        record=f"Patient {patient.id}",
    )
    await db.commit()
    return patient
