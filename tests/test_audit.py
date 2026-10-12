import re

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.auth import get_password_hash
from app.models.audit import AuditLog
from app.models.batch import Batch
from app.models.exam import ExamType
from app.models.notice import NoticeCategory
from app.models.user import User


def get_auth_client(
    client: TestClient, session: Session
) -> tuple[TestClient, str, User]:
    user = session.exec(
        select(User).where(User.email == "auditadmin@example.com")
    ).first()
    if not user:
        user = User(
            email="auditadmin@example.com",
            password_hash=get_password_hash("AuditPass123!"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    resp = client.get("/auth/login")
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', resp.text).group(1)

    client.post(
        "/auth/login",
        data={
            "email": "auditadmin@example.com",
            "password": "AuditPass123!",
            "csrf_token": csrf_token,
        },
    )
    return client, csrf_token, user


def test_notice_mutations_create_audit_logs(client: TestClient, session: Session):
    auth_client, csrf, admin = get_auth_client(client, session)

    # 1. Create notice
    initial_count = len(session.exec(select(AuditLog)).all())
    resp_create = auth_client.post(
        "/admin/notices/new",
        data={
            "title": "Audited Notice",
            "body": "Audited notice body",
            "category": NoticeCategory.GENERAL,
            "status": "published",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert resp_create.status_code == 303
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 1
    create_log = logs[0]
    assert create_log.actor == admin.email
    assert create_log.action == "CREATE"
    assert create_log.entity == "Notice"
    assert "Audited Notice" in create_log.summary

    notice_id = create_log.entity_id
    assert notice_id is not None

    # 2. Update notice
    resp_edit = auth_client.post(
        f"/admin/notices/{notice_id}/edit",
        data={
            "title": "Audited Notice Updated",
            "body": "Updated body",
            "category": NoticeCategory.ACADEMIC,
            "status": "published",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert resp_edit.status_code == 303
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 2
    edit_log = logs[0]
    assert edit_log.actor == admin.email
    assert edit_log.action == "UPDATE"
    assert edit_log.entity == "Notice"
    assert edit_log.entity_id == notice_id

    # 3. Delete notice
    resp_del = auth_client.post(
        f"/admin/notices/{notice_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp_del.status_code == 303
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 3
    del_log = logs[0]
    assert del_log.actor == admin.email
    assert del_log.action == "DELETE"
    assert del_log.entity == "Notice"
    assert del_log.entity_id == notice_id


def test_batch_and_section_mutations_create_audit_logs(
    client: TestClient, session: Session
):
    auth_client, csrf, admin = get_auth_client(client, session)

    # 1. Create batch
    initial_count = len(session.exec(select(AuditLog)).all())
    auth_client.post(
        "/admin/batches/new",
        data={"name": "Audit Session 2026", "csrf_token": csrf},
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 1
    batch_log = logs[0]
    assert batch_log.actor == admin.email
    assert batch_log.action == "CREATE"
    assert batch_log.entity == "Batch"
    batch_id = batch_log.entity_id

    # 2. Create section
    auth_client.post(
        f"/admin/batches/{batch_id}/sections/new",
        data={"name": "X", "csrf_token": csrf},
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 2
    sec_log = logs[0]
    assert sec_log.actor == admin.email
    assert sec_log.action == "CREATE"
    assert sec_log.entity == "Section"
    sec_id = sec_log.entity_id

    # 3. Delete section
    auth_client.post(
        f"/admin/sections/{sec_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 3
    del_sec_log = logs[0]
    assert del_sec_log.action == "DELETE"
    assert del_sec_log.entity == "Section"

    # 4. Delete batch
    auth_client.post(
        f"/admin/batches/{batch_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 4
    del_batch_log = logs[0]
    assert del_batch_log.action == "DELETE"
    assert del_batch_log.entity == "Batch"


def test_routine_slot_and_exam_mutations_create_audit_logs(
    client: TestClient, session: Session
):
    auth_client, csrf, admin = get_auth_client(client, session)

    batch = Batch(name="Audit Batch 2")
    session.add(batch)
    session.commit()
    session.refresh(batch)

    # 1. Create RoutineSlot
    initial_count = len(session.exec(select(AuditLog)).all())
    auth_client.post(
        "/admin/routine/new",
        data={
            "batch_id": batch.id,
            "weekday": "Monday",
            "start_time": "08:00",
            "end_time": "09:00",
            "course_code": "AUD-101",
            "course_title": "Auditing Basics",
            "teacher": "Prof. Auditor",
            "room": "Room A1",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 1
    slot_log = logs[0]
    assert slot_log.action == "CREATE"
    assert slot_log.entity == "RoutineSlot"
    slot_id = slot_log.entity_id

    # 2. Delete RoutineSlot
    auth_client.post(
        f"/admin/routine/{slot_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 2
    del_slot_log = logs[0]
    assert del_slot_log.action == "DELETE"
    assert del_slot_log.entity == "RoutineSlot"

    # 3. Create Exam
    auth_client.post(
        "/admin/exams/new",
        data={
            "batch_id": batch.id,
            "course": "AUD-101 Auditing Exam",
            "type": ExamType.MIDTERM,
            "date": "2026-05-10",
            "start_time": "10:00",
            "room": "Room A1",
            "note": "Audit test note",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 3
    exam_log = logs[0]
    assert exam_log.action == "CREATE"
    assert exam_log.entity == "Exam"
    exam_id = exam_log.entity_id

    # 4. Delete Exam
    auth_client.post(
        f"/admin/exams/{exam_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    logs = session.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).all()
    assert len(logs) == initial_count + 4
    del_exam_log = logs[0]
    assert del_exam_log.action == "DELETE"
    assert del_exam_log.entity == "Exam"


def test_admin_audit_viewer_page(client: TestClient, session: Session):
    auth_client, _csrf, admin = get_auth_client(client, session)

    # 1. Empty state
    resp_empty = auth_client.get("/admin/audit")
    assert resp_empty.status_code == 200
    assert "Administrative Audit Trail" in resp_empty.text
    assert "audit-empty-state" in resp_empty.text

    # 2. Add an audit log and verify populated table
    from app.audit import log_audit

    log_audit(
        session=session,
        actor=admin.email,
        action="CREATE",
        entity="Notice",
        entity_id=1,
        summary="Test audit entry for page view",
    )
    session.commit()

    resp_table = auth_client.get("/admin/audit")
    assert resp_table.status_code == 200
    assert "audit-table" in resp_table.text
    assert "Test audit entry for page view" in resp_table.text
