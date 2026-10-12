from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.models.rate_limit import LoginAttempt

RATE_LIMIT_WINDOW_MINUTES = 15
MAX_FAILED_ATTEMPTS = 5


def is_login_rate_limited(session: Session, ip_address: str, email: str) -> bool:
    """Return True if IP + email has exceeded failed attempts in the window."""
    window_start = datetime.now(UTC) - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
    statement = (
        select(LoginAttempt)
        .where(LoginAttempt.ip_address == ip_address)
        .where(LoginAttempt.email == email.lower().strip())
        .where(LoginAttempt.success == False)  # noqa: E712
        .where(col(LoginAttempt.attempted_at) >= window_start)
    )
    failed_count = len(session.exec(statement).all())
    # If 5 or more failures already exist, the 6th attempt is blocked
    return failed_count >= MAX_FAILED_ATTEMPTS


def record_login_attempt(
    session: Session, ip_address: str, email: str, success: bool
) -> None:
    """Record a login attempt in the database."""
    attempt = LoginAttempt(
        ip_address=ip_address,
        email=email.lower().strip(),
        attempted_at=datetime.now(UTC),
        success=success,
    )
    session.add(attempt)
    session.commit()
