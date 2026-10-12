from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    actor: str = Field(max_length=255, index=True)
    action: str = Field(max_length=50, index=True)
    entity: str = Field(max_length=100, index=True)
    entity_id: int | None = Field(default=None, index=True)
    time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
    )
    summary: str = Field(max_length=500)
