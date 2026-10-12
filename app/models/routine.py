from datetime import UTC, datetime, time
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.batch import Batch, Section


class RoutineSlot(SQLModel, table=True):
    __tablename__ = "routine_slots"

    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="batches.id", index=True)
    section_id: Optional[int] = Field(
        default=None, foreign_key="sections.id", index=True
    )
    weekday: str = Field(max_length=20, index=True)  # "Monday", "Tuesday", etc.
    start_time: time = Field()
    end_time: time = Field()
    course_code: str = Field(max_length=50)
    course_title: str = Field(max_length=150)
    teacher: str = Field(max_length=150, index=True)
    room: str = Field(max_length=50, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    batch: Optional["Batch"] = Relationship(back_populates="routine_slots")
    section: Optional["Section"] = Relationship(back_populates="routine_slots")
