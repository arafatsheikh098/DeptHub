import re
from datetime import time

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.models.batch import Batch
from app.models.routine import RoutineSlot
from app.models.user import User


def get_auth_client(client: TestClient, session: Session) -> tuple[TestClient, str]:
    user = session.exec(
        select(User).where(User.email == "batchadmin@example.com")
    ).first()
    if not user:
        user = User(
            email="batchadmin@example.com",
            password_hash=get_password_hash("Pass1234!"),
        )
        session.add(user)
        session.commit()

    resp = client.get("/auth/login")
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', resp.text).group(1)

    client.post(
        "/auth/login",
        data={
            "email": "batchadmin@example.com",
            "password": "Pass1234!",
            "csrf_token": csrf_token,
        },
    )
    return client, csrf_token


def test_batch_and_section_creation(client: TestClient, session: Session):
    auth_client, csrf_token = get_auth_client(client, session)

    # 1. Create batch
    resp_batch = auth_client.post(
        "/admin/batches/new",
        data={"name": "22-23 Session", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert resp_batch.status_code == 303
    batch = session.exec(select(Batch).where(Batch.name == "22-23 Session")).first()
    assert batch is not None

    # 2. Add section A
    resp_sec = auth_client.post(
        f"/admin/batches/{batch.id}/sections/new",
        data={"name": "A", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert resp_sec.status_code == 303
    session.refresh(batch)
    assert len(batch.sections) == 1
    assert batch.sections[0].name == "A"


def test_delete_batch_with_slots_is_blocked(client: TestClient, session: Session):
    auth_client, csrf_token = get_auth_client(client, session)

    # Batch with a routine slot
    batch = Batch(name="20-21 Session")
    session.add(batch)
    session.commit()
    session.refresh(batch)

    slot = RoutineSlot(
        batch_id=batch.id,
        weekday="Monday",
        start_time=time(10, 0),
        end_time=time(11, 0),
        course_code="CSE-101",
        course_title="Intro to CS",
        teacher="Prof. X",
        room="Room 101",
    )
    session.add(slot)
    session.commit()

    # Attempt delete: Must be blocked per decision D003
    resp_del = auth_client.post(
        f"/admin/batches/{batch.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert resp_del.status_code == 200
    assert "Cannot delete batch" in resp_del.text

    # Batch must still exist in database
    existing_batch = session.get(Batch, batch.id)
    assert existing_batch is not None

    # Now remove the slot and delete batch
    session.delete(slot)
    session.commit()

    resp_del_ok = auth_client.post(
        f"/admin/batches/{batch.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert resp_del_ok.status_code == 200
    assert session.get(Batch, batch.id) is None
