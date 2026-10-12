from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.batch import Batch


class NoticeCategory:
    GENERAL = "General"
    ACADEMIC = "Academic"
    EXAM = "Exam"
    EVENT = "Event"
    SCHOLARSHIP = "Scholarship"
    JOB = "Job"

    ALL: ClassVar[list[str]] = [GENERAL, ACADEMIC, EXAM, EVENT, SCHOLARSHIP, JOB]


class NoticeStatus:
    DRAFT = "draft"
    PUBLISHED = "published"

    ALL: ClassVar[list[str]] = [DRAFT, PUBLISHED]


class Notice(SQLModel, table=True):
    __tablename__ = "notices"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=150)
    body: str = Field()
    category: str = Field(default=NoticeCategory.GENERAL, max_length=50, index=True)
    is_pinned: bool = Field(default=False, index=True)
    external_link: str | None = Field(default=None, max_length=500)
    batch_id: int | None = Field(default=None, foreign_key="batches.id", index=True)
    status: str = Field(default=NoticeStatus.PUBLISHED, max_length=20, index=True)
    published_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    batch: Batch | None = Relationship(back_populates="notices")
