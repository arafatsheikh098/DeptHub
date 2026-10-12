from datetime import UTC, datetime

from sqlmodel import Session

from app.models.audit import AuditLog


def log_audit(
    session: Session,
    actor: str,
    action: str,
    entity: str,
    entity_id: int | None,
    summary: str,
) -> AuditLog:
    """Record an audit trail event for state mutations."""
    entry = AuditLog(
        actor=actor,
        action=action.upper(),
        entity=entity,
        entity_id=entity_id,
        time=datetime.now(UTC),
        summary=summary[:500],
    )
    session.add(entry)
    return entry
