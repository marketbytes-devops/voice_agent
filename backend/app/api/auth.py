from __future__ import annotations

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import auth_rate_limiter
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    verify_password,
)
from backend.app.models import User
from backend.app.schemas import LoginRequest, Token, UserOut
from backend.app.services.audit_service import record_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to retrieve and authenticate user from Bearer JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user subject",
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID format")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_roles(*allowed_roles: str):
    """Dependency factory enforcing specific user roles."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles and user.role != "platform_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for current role",
            )
        return user
    return role_checker


@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limiter)])
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate user with email and password with brute-force rate limiting."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    await record_audit_event(
        db,
        action="user_login",
        clinic_id=user.clinic_id,
        user_id=user.id,
        record=f"User {user.email} logged in",
    )
    await db.commit()

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "clinic_id": str(user.clinic_id) if user.clinic_id else None,
            "organisation_id": str(user.organisation_id),
        }
    )
    return Token(access_token=access_token, expires_in=86400)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Retrieve details of currently logged-in user."""
    return current_user
