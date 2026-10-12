from sqlmodel import Session, select

from app.models.batch import Batch, Section
from app.models.exam import Exam
from app.models.notice import Notice
from app.models.routine import RoutineSlot
from app.models.user import User
from app.seed import seed_database


def test_seed_database_is_idempotent(session: Session):
    # First seed execution
    counts_first = seed_database(session)
    assert counts_first["batches"] == 2
    assert counts_first["sections"] == 4
    assert counts_first["notices"] == 10
    assert counts_first["routine_slots"] == 10
    assert counts_first["exams"] == 4
    assert counts_first["users"] >= 1

    # Record total database rows after first seed
    total_batches = len(session.exec(select(Batch)).all())
    total_sections = len(session.exec(select(Section)).all())
    total_notices = len(session.exec(select(Notice)).all())
    total_slots = len(session.exec(select(RoutineSlot)).all())
    total_exams = len(session.exec(select(Exam)).all())
    total_users = len(session.exec(select(User)).all())

    # Second seed execution (Acceptance A5: running seed twice creates no duplicates)
    counts_second = seed_database(session)
    assert counts_second["batches"] == 0
    assert counts_second["sections"] == 0
    assert counts_second["notices"] == 0
    assert counts_second["routine_slots"] == 0
    assert counts_second["exams"] == 0
    assert counts_second["users"] == 0

    # Ensure totals are completely unchanged
    assert len(session.exec(select(Batch)).all()) == total_batches
    assert len(session.exec(select(Section)).all()) == total_sections
    assert len(session.exec(select(Notice)).all()) == total_notices
    assert len(session.exec(select(RoutineSlot)).all()) == total_slots
    assert len(session.exec(select(Exam)).all()) == total_exams
    assert len(session.exec(select(User)).all()) == total_users
