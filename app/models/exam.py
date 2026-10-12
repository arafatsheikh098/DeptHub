import datetime as dt
from datetime import UTC
from typing import TYPE_CHECKING, ClassVar, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.batch import Batch


class ExamType:
    CLASS_TEST = "Class Test"
    MIDTERM = "Midterm"
    FINAL = "Final"
    LAB = "Lab"

    ALL: ClassVar[list[str]] = [CLASS_TEST, MIDTERM, FINAL, LAB]


class Exam(SQLModel, table=True):
    __tablename__ = "exams"

    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="batches.id", index=True)
    course: str = Field(max_length=150)
    type: str = Field(default=ExamType.MIDTERM, max_length=50)
    date: dt.date = Field(index=True)
    start_time: dt.time = Field()
    room: str = Field(max_length=50)
    note: Optional[str] = Field(default=None, max_length=255)
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(UTC))

    batch: Optional["Batch"] = Relationship(back_populates="exams")
