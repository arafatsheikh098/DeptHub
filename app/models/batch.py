from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.exam import Exam
    from app.models.notice import Notice
    from app.models.routine import RoutineSlot


class Section(SQLModel, table=True):
    __tablename__ = "sections"

    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="batches.id", index=True)
    name: str = Field(max_length=50)

    batch: Optional["Batch"] = Relationship(back_populates="sections")
    routine_slots: list["RoutineSlot"] = Relationship(
        back_populates="section",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Batch(SQLModel, table=True):
    __tablename__ = "batches"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    sections: list[Section] = Relationship(
        back_populates="batch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    routine_slots: list["RoutineSlot"] = Relationship(
        back_populates="batch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    exams: list["Exam"] = Relationship(
        back_populates="batch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    notices: list["Notice"] = Relationship(
        back_populates="batch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
