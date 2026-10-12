from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class LoginAttempt(SQLModel, table=True):
    __tablename__ = "login_attempts"

    id: int | None = Field(default=None, primary_key=True)
    ip_address: str = Field(index=True, max_length=64)
    email: str = Field(index=True, max_length=255)
    attempted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
    )
    success: bool = Field(default=False)
