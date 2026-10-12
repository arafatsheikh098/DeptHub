import re
from datetime import date, time

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.models.batch import Batch
from app.models.exam import Exam, ExamType
from app.models.user import User


def get_auth_client(client: TestClient, session: Session) -> tuple[TestClient, str]:
    user = session.exec(
        select(User).where(User.email == "examadmin@example.com")
    ).first()
    if not user:
        user = User(
            email="examadmin@example.com",
            password_hash=get_password_hash("ExamPass123!"),
        )
        session.add(user)
        session.commit()

    resp = client.get("/auth/login")
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', resp.text).group(1)

    client.post(
        "/auth/login",
        data={
            "email": "examadmin@example.com",
            "password": "ExamPass123!",
            "csrf_token": csrf_token,
        },
    )
    return client, csrf_token


def test_exam_sorting_and_show_past_toggle(client: TestClient, session: Session):
    batch = Batch(name="2026 Batch")
    session.add(batch)
    session.commit()

    # Past exam
    e_past = Exam(
        batch_id=batch.id,
        course="CSE-101 Past Exam",
        type=ExamType.CLASS_TEST,
        date=date(2025, 1, 15),
        start_time=time(10, 0),
        room="Room 101",
    )
    # Future exam 1
    e_future_1 = Exam(
        batch_id=batch.id,
        course="CSE-201 Future Midterm",
        type=ExamType.MIDTERM,
        date=date(2027, 2, 10),
        start_time=time(10, 0),
        room="Room 202",
    )
    # Future exam 2 (later)
    e_future_2 = Exam(
        batch_id=batch.id,
        course="CSE-301 Future Final",
        type=ExamType.FINAL,
        date=date(2027, 5, 20),
        start_time=time(9, 30),
        room="Auditorium",
    )
    session.add_all([e_past, e_future_1, e_future_2])
    session.commit()

    # 1. Default: past exams hidden
    resp_default = client.get("/exams")
    assert resp_default.status_code == 200
    assert "CSE-101 Past Exam" not in resp_default.text
    assert "CSE-201 Future Midterm" in resp_default.text
    assert "CSE-301 Future Final" in resp_default.text

    # Verify sorting: future 1 before future 2
    pos1 = resp_default.text.find("CSE-201 Future Midterm")
    pos2 = resp_default.text.find("CSE-301 Future Final")
    assert pos1 < pos2

    # 2. Show past toggle: past exam visible
    resp_past = client.get("/exams?show_past=true")
    assert resp_past.status_code == 200
    assert "CSE-101 Past Exam" in resp_past.text
    assert "Completed" in resp_past.text


def test_admin_exam_crud_workflow(client: TestClient, session: Session):
    auth_client, csrf_token = get_auth_client(client, session)

    batch = Batch(name="Exam Batch")
    session.add(batch)
    session.commit()

    # Create exam
    resp_create = auth_client.post(
        "/admin/exams/new",
        data={
            "batch_id": batch.id,
            "course": "CSE-401 Compiler Design",
            "type": ExamType.FINAL,
            "date": "2026-11-20",
            "start_time": "14:00",
            "room": "Room 501",
            "note": "Calculator allowed",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp_create.status_code == 303

    exam = session.exec(
        select(Exam).where(Exam.course == "CSE-401 Compiler Design")
    ).first()
    assert exam is not None
    assert exam.room == "Room 501"

    # Edit exam
    resp_edit = auth_client.post(
        f"/admin/exams/{exam.id}/edit",
        data={
            "batch_id": batch.id,
            "course": "CSE-401 Compiler Design Updated",
            "type": ExamType.FINAL,
            "date": "2026-11-22",
            "start_time": "14:30",
            "room": "Room 502",
            "note": "Open book",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp_edit.status_code == 303
    session.refresh(exam)
    assert exam.course == "CSE-401 Compiler Design Updated"
    assert exam.room == "Room 502"

    # Delete exam
    resp_del = auth_client.post(
        f"/admin/exams/{exam.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert resp_del.status_code == 303
    assert session.get(Exam, exam.id) is None
