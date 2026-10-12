import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, time

import icalendar
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.batch import Batch, Section
from app.models.exam import Exam, ExamType
from app.models.notice import Notice, NoticeCategory, NoticeStatus
from app.models.routine import RoutineSlot


def test_atom_feed_schema_and_exclusion_of_drafts(client: TestClient, session: Session):
    # Create 2 published notices and 1 draft notice
    published_1 = Notice(
        title="Published Notice 1",
        body="This is published notice 1 body.",
        category=NoticeCategory.GENERAL,
        status=NoticeStatus.PUBLISHED,
        published_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
    )
    published_2 = Notice(
        title="Published Notice 2",
        body="This is published notice 2 body.",
        category=NoticeCategory.ACADEMIC,
        status=NoticeStatus.PUBLISHED,
        published_at=datetime(2026, 2, 5, 12, 0, tzinfo=UTC),
    )
    draft_notice = Notice(
        title="Secret Draft Notice",
        body="This must NOT be in the atom feed.",
        category=NoticeCategory.GENERAL,
        status=NoticeStatus.DRAFT,
        published_at=None,
    )
    session.add_all([published_1, published_2, draft_notice])
    session.commit()

    resp = client.get("/feeds/notices.atom")
    assert resp.status_code == 200
    assert "application/atom+xml" in resp.headers["content-type"]

    # Verify standard XML parsing (A3)
    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    assert root.tag == f"{{{ns['atom']}}}feed"

    title_elem = root.find("atom:title", ns)
    assert title_elem is not None
    assert title_elem.text == "DeptHub Notices"

    entries = root.findall("atom:entry", ns)
    assert len(entries) == 2

    titles = [e.find("atom:title", ns).text for e in entries]
    assert "Published Notice 2" in titles
    assert "Published Notice 1" in titles
    assert "Secret Draft Notice" not in titles

    # Verify absolute URLs
    for entry in entries:
        entry_id = entry.find("atom:id", ns).text
        link = entry.find("atom:link", ns).get("href")
        assert entry_id.startswith("http://") or entry_id.startswith("https://")
        assert link.startswith("http://") or link.startswith("https://")


def test_atom_feed_caps_at_30_notices(client: TestClient, session: Session):
    # Clear existing notices and insert 35 published notices
    for i in range(35):
        session.add(
            Notice(
                title=f"Notice #{i}",
                body=f"Body #{i}",
                category=NoticeCategory.GENERAL,
                status=NoticeStatus.PUBLISHED,
                published_at=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
            )
        )
    session.commit()

    resp = client.get("/feeds/notices.atom")
    assert resp.status_code == 200
    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    assert len(entries) == 30


def test_ics_feed_for_batch(client: TestClient, session: Session):
    batch = Batch(name="23-24 Session")
    session.add(batch)
    session.commit()
    session.refresh(batch)

    sec = Section(name="A", batch_id=batch.id)
    session.add(sec)
    session.commit()
    session.refresh(sec)

    # 1 routine slot
    slot = RoutineSlot(
        batch_id=batch.id,
        section_id=sec.id,
        weekday="Monday",
        start_time=time(10, 0),
        end_time=time(11, 30),
        course_code="CSE-101",
        course_title="Computer Programming",
        teacher="Prof. Turing",
        room="Room 302",
    )
    # 1 exam
    exam = Exam(
        batch_id=batch.id,
        course="CSE-101 Programming Lab",
        type=ExamType.MIDTERM,
        date=date(2026, 4, 15),
        start_time=time(14, 0),
        room="Lab 2",
        note="Bring ID card",
    )
    session.add_all([slot, exam])
    session.commit()

    # Request ICS feed
    resp = client.get(f"/feeds/batch/{batch.id}.ics")
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers["content-type"]

    # Parse with icalendar (A1)
    cal = icalendar.Calendar.from_ical(resp.content)
    assert cal.name == "VCALENDAR"
    assert "Asia/Dhaka" in str(cal.get("x-wr-timezone", ""))

    events = [comp for comp in cal.subcomponents if comp.name == "VEVENT"]
    assert len(events) == 2

    # Verify routine slot event
    routine_event = next(e for e in events if "CSE-101:" in str(e.get("summary")))
    assert "Prof. Turing" in str(routine_event.get("description"))
    assert str(routine_event.get("location")) == "Room 302"
    assert "RRULE" in routine_event
    assert "WEEKLY" in str(routine_event["rrule"])
    assert "MO" in str(routine_event["rrule"])
    assert routine_event.get("uid") == f"routine-slot-{slot.id}@depthub.local"

    # Verify exam event
    exam_event = next(e for e in events if "[Midterm]" in str(e.get("summary")))
    assert str(exam_event.get("location")) == "Lab 2"
    assert "Bring ID card" in str(exam_event.get("description"))
    assert exam_event.get("uid") == f"exam-{exam.id}@depthub.local"


def test_ics_feed_stable_uids_and_unique_events(client: TestClient, session: Session):
    # Acceptance A2: UIDs are stable across requests and unique per event
    batch = Batch(name="24-25 Session")
    session.add(batch)
    session.commit()
    session.refresh(batch)

    slot_1 = RoutineSlot(
        batch_id=batch.id,
        weekday="Sunday",
        start_time=time(9, 0),
        end_time=time(10, 0),
        course_code="MATH-101",
        course_title="Calculus",
        teacher="Dr. Euler",
        room="Room 101",
    )
    slot_2 = RoutineSlot(
        batch_id=batch.id,
        weekday="Monday",
        start_time=time(11, 0),
        end_time=time(12, 0),
        course_code="PHY-101",
        course_title="Physics",
        teacher="Dr. Newton",
        room="Room 102",
    )
    session.add_all([slot_1, slot_2])
    session.commit()

    resp_1 = client.get(f"/feeds/batch/{batch.id}.ics")
    cal_1 = icalendar.Calendar.from_ical(resp_1.content)
    events_1 = [comp for comp in cal_1.subcomponents if comp.name == "VEVENT"]

    resp_2 = client.get(f"/feeds/batch/{batch.id}.ics")
    cal_2 = icalendar.Calendar.from_ical(resp_2.content)
    events_2 = [comp for comp in cal_2.subcomponents if comp.name == "VEVENT"]

    uids_1 = [str(e.get("uid")) for e in events_1]
    uids_2 = [str(e.get("uid")) for e in events_2]

    # Unique per event
    assert len(uids_1) == len(set(uids_1))
    # Stable across requests
    assert uids_1 == uids_2


def test_ics_feed_returns_404_for_unknown_batch(client: TestClient):
    # Acceptance A5: Unknown batch id returns 404
    resp = client.get("/feeds/batch/999999.ics")
    assert resp.status_code == 404
    assert "Batch not found" in resp.json()["detail"]
