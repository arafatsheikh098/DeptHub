from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User

_hasher = PasswordHasher()
# Precomputed dummy hash to prevent timing attack enumeration on nonexistent emails
_DUMMY_HASH = _hasher.hash("depthub_timing_protection_dummy_password")


def get_password_hash(password: str) -> str:
    """Hash password using Argon2."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2 hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    """Authenticate a user.

    Uses identical Argon2 verification code path whether email exists or not.
    """
    clean_email = email.lower().strip()
    user = session.exec(select(User).where(User.email == clean_email)).first()

    if user is None:
        # Compute verify against dummy hash to prevent timing side-channel
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return user


def require_admin(request: Request, session: Session = Depends(get_session)) -> User:
    """Dependency that ensures the current session belongs to an authenticated admin."""
    user_id = request.session.get("user_id")
    if not user_id:
        is_json = request.headers.get("Accept") == "application/json"
        if request.headers.get("HX-Request") or is_json:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/auth/login?next={request.url.path}"},
        )

    user = session.get(User, user_id)
    if not user or not user.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/auth/login"},
        )

    return user
