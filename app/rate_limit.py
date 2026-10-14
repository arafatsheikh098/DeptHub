from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.models.rate_limit import LoginAttempt

RATE_LIMIT_WINDOW_MINUTES = 15
MAX_FAILED_ATTEMPTS = 5
# Cap on failures per email across all source IPs. The per-IP limit above is
# keyed on (ip, email), so a caller able to vary its apparent IP -- e.g. by
# sending X-Forwarded-For -- would otherwise get a fresh budget per IP and
# could guess passwords for a single known account without limit.
MAX_FAILED_ATTEMPTS_PER_EMAIL = 10


def is_login_rate_limited(session: Session, ip_address: str, email: str) -> bool:
    """Return True if this IP+email, or the email alone, is over its limit."""
    window_start = datetime.now(UTC) - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
    clean_email = email.lower().strip()

    statement = (
        select(LoginAttempt)
        .where(LoginAttempt.ip_address == ip_address)
        .where(LoginAttempt.email == clean_email)
        .where(LoginAttempt.success == False)  # noqa: E712
        .where(col(LoginAttempt.attempted_at) >= window_start)
    )
    failed_count = len(session.exec(statement).all())
    # If 5 or more failures already exist, the 6th attempt is blocked
    if failed_count >= MAX_FAILED_ATTEMPTS:
        return True

    email_statement = (
        select(LoginAttempt)
        .where(LoginAttempt.email == clean_email)
        .where(LoginAttempt.success == False)  # noqa: E712
        .where(col(LoginAttempt.attempted_at) >= window_start)
    )
    email_failed_count = len(session.exec(email_statement).all())
    return email_failed_count >= MAX_FAILED_ATTEMPTS_PER_EMAIL


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
