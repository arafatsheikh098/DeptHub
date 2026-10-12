import re
from datetime import time

from fastapi.testclient import TestClient
from freezegun import freeze_time
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.models.batch import Batch
from app.models.routine import RoutineSlot
from app.models.user import User


def get_auth_client(client: TestClient, session: Session) -> tuple[TestClient, str]:
    user = session.exec(
        select(User).where(User.email == "routineadmin@example.com")
    ).first()
    if not user:
        user = User(
            email="routineadmin@example.com",
            password_hash=get_password_hash("RoutinePass123!"),
        )
        session.add(user)
        session.commit()

    resp = client.get("/auth/login")
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', resp.text).group(1)

    client.post(
        "/auth/login",
        data={
            "email": "routineadmin@example.com",
            "password": "RoutinePass123!",
            "csrf_token": csrf_token,
        },
    )
    return client, csrf_token


def test_routine_overlap_and_boundary_rules(client: TestClient, session: Session):
    auth_client, csrf_token = get_auth_client(client, session)

    batch_a = Batch(name="Batch A")
    batch_b = Batch(name="Batch B")
    session.add_all([batch_a, batch_b])
    session.commit()

    # Slot 1: Monday 10:00 - 11:00 in Room 101 with Teacher T1
    resp_base = auth_client.post(
        "/admin/routine/new",
        data={
            "batch_id": batch_a.id,
            "weekday": "Monday",
            "start_time": "10:00",
            "end_time": "11:00",
            "course_code": "CSE-101",
            "course_title": "CS One",
            "teacher": "Dr. Smith",
            "room": "Room 101",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp_base.status_code == 303

    # Case 1 (Touching boundary allowed): 11:00 - 12:00 in same room or batch
    resp_touching = auth_client.post(
        "/admin/routine/new",
        data={
            "batch_id": batch_a.id,
            "weekday": "Monday",
            "start_time": "11:00",
            "end_time": "12:00",
            "course_code": "CSE-102",
            "course_title": "CS Two",
            "teacher": "Dr. Smith",
            "room": "Room 101",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp_touching.status_code == 303

    # Case 2 (Identical interval blocked): 10:00 - 11:00 for Batch A
    resp_identical = auth_client.post(
        "/admin/routine/new",
        data={
            "batch_id": batch_a.id,
            "weekday": "Monday",
            "start_time": "10:00",
            "end_time": "11:00",
            "course_code": "CSE-103",
            "course_title": "CS Three",
            "teacher": "Dr. Jones",
            "room": "Room 102",
            "csrf_token": csrf_token,
        },
    )
    assert resp_identical.status_code == 400
    assert "Batch schedule conflict" in resp_identical.text

    # Case 3 (Contained interval blocked): 10:15 - 10:45 in Batch A
    resp_contained = auth_client.post(
        "/admin/routine/new",
        data={
            "batch_id": batch_a.id,
            "weekday": "Monday",
            "start_time": "10:15",
            "end_time": "10:45",
            "course_code": "CSE-104",
            "course_title": "CS Four",
            "teacher": "Dr. Jones",
            "room": "Room 102",
            "csrf_token": csrf_token,
        },
    )
    assert resp_contained.status_code == 400
    assert "Batch schedule conflict" in resp_contained.text

    # Case 4 (Same room in another batch blocked):
    # Batch B trying Room 101 at 10:30-11:30
    resp_room_conflict = auth_client.post(
        "/admin/routine/new",
        data={
            "batch_id": batch_b.id,
            "weekday": "Monday",
            "start_time": "10:30",
            "end_time": "11:30",
            "course_code": "EEE-201",
            "course_title": "Circuits",
            "teacher": "Dr. Taylor",
            "room": "Room 101",  # Same room
            "csrf_token": csrf_token,
        },
    )
    assert resp_room_conflict.status_code == 400
    assert "Room double-booking conflict" in resp_room_conflict.text

    # Case 5 (Same teacher in another batch blocked):
    # Batch B with Dr. Smith at 10:30-11:30
    resp_teacher_conflict = auth_client.post(
        "/admin/routine/new",
        data={
            "batch_id": batch_b.id,
            "weekday": "Monday",
            "start_time": "10:30",
            "end_time": "11:30",
            "course_code": "EEE-202",
            "course_title": "Signals",
            "teacher": "dr. smith ",  # Same teacher trimmed/case-insensitive
            "room": "Room 205",
            "csrf_token": csrf_token,
        },
    )
    assert resp_teacher_conflict.status_code == 400
    assert "Teacher double-booking conflict" in resp_teacher_conflict.text


def test_today_page_computed_in_timezone_across_midnight(
    client: TestClient, session: Session
):
    batch = Batch(name="2026 Batch")
    session.add(batch)
    session.commit()

    # Slot on Monday
    mon_slot = RoutineSlot(
        batch_id=batch.id,
        weekday="Monday",
        start_time=time(10, 0),
        end_time=time(11, 30),
        course_code="MON-101",
        course_title="Monday Course",
        teacher="Teacher M",
        room="Room M",
    )
    # Slot on Tuesday
    tue_slot = RoutineSlot(
        batch_id=batch.id,
        weekday="Tuesday",
        start_time=time(10, 0),
        end_time=time(11, 30),
        course_code="TUE-101",
        course_title="Tuesday Course",
        teacher="Teacher T",
        room="Room T",
    )
    session.add_all([mon_slot, tue_slot])
    session.commit()

    # TIMEZONE is Asia/Dhaka (+06:00).
    # 2026-10-12 17:30:00 UTC == 2026-10-12 23:30:00 Dhaka (Monday night)
    with freeze_time("2026-10-12 17:30:00"):
        resp_mon = client.get(f"/today?batch_id={batch.id}")
        assert resp_mon.status_code == 200
        assert "Today: Monday" in resp_mon.text
        assert "MON-101" in resp_mon.text
        assert "TUE-101" not in resp_mon.text

    # 2026-10-12 18:30:00 UTC == 2026-10-13 00:30:00 Dhaka (Tuesday morning!)
    with freeze_time("2026-10-12 18:30:00"):
        resp_tue = client.get(f"/today?batch_id={batch.id}")
        assert resp_tue.status_code == 200
        assert "Today: Tuesday" in resp_tue.text
        assert "TUE-101" in resp_tue.text
        assert "MON-101" not in resp_tue.text


def test_grid_renders_with_0_1_and_8_slots(client: TestClient, session: Session):
    batch = Batch(name="Heavy Batch")
    session.add(batch)
    session.commit()

    # Wednesday: 1 slot
    s_wed = RoutineSlot(
        batch_id=batch.id,
        weekday="Wednesday",
        start_time=time(9, 0),
        end_time=time(10, 0),
        course_code="WED-01",
        course_title="Wed Course",
        teacher="T1",
        room="R1",
    )
    session.add(s_wed)

    # Thursday: 8 slots
    for i in range(8):
        s_thu = RoutineSlot(
            batch_id=batch.id,
            weekday="Thursday",
            start_time=time(8 + i, 0),
            end_time=time(8 + i, 50),
            course_code=f"THU-0{i}",
            course_title=f"Thu Course {i}",
            teacher=f"Teacher {i}",
            room=f"Room {i}",
        )
        session.add(s_thu)
    session.commit()

    resp = client.get(f"/routine?batch_id={batch.id}")
    assert resp.status_code == 200

    # Friday has 0 slots: verify empty state text for Friday
    assert "routine-day-friday" in resp.text
    assert "No classes scheduled." in resp.text

    # Wednesday has 1 slot
    assert "WED-01" in resp.text

    # Thursday has 8 slots
    for i in range(8):
        assert f"THU-0{i}" in resp.text
