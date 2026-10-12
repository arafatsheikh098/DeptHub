from datetime import UTC, datetime, time, timedelta

from sqlmodel import Session, select

from app.auth import get_password_hash
from app.database import engine, init_db
from app.models.batch import Batch, Section
from app.models.exam import Exam, ExamType
from app.models.notice import Notice, NoticeCategory, NoticeStatus
from app.models.routine import RoutineSlot
from app.models.user import User
from app.utils import get_current_local_date_and_weekday


def seed_database(session: Session) -> dict[str, int]:
    """Idempotently seed the database with initial demo data.

    Returns count of newly created records per entity.
    """
    counts = {
        "users": 0,
        "batches": 0,
        "sections": 0,
        "notices": 0,
        "routine_slots": 0,
        "exams": 0,
    }

    # 1. Admin User
    admin_email = "admin@dept.local"
    admin_user = session.exec(select(User).where(User.email == admin_email)).first()
    if not admin_user:
        admin_user = User(
            email=admin_email,
            password_hash=get_password_hash("AdminPass123!"),
        )
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        counts["users"] += 1

    # 2. Batches & Sections
    batch_data = [
        {"name": "21-22 Session", "sections": ["A", "B"]},
        {"name": "22-23 Session", "sections": ["A", "B"]},
    ]
    batch_map: dict[str, Batch] = {}
    section_map: dict[str, dict[str, Section]] = {}

    for b_item in batch_data:
        batch = session.exec(select(Batch).where(Batch.name == b_item["name"])).first()
        if not batch:
            batch = Batch(name=b_item["name"])
            session.add(batch)
            session.commit()
            session.refresh(batch)
            counts["batches"] += 1
        batch_map[b_item["name"]] = batch
        section_map[b_item["name"]] = {}

        for sec_name in b_item["sections"]:
            sec = session.exec(
                select(Section).where(
                    Section.batch_id == batch.id, Section.name == sec_name
                )
            ).first()
            if not sec:
                sec = Section(batch_id=batch.id, name=sec_name)
                session.add(sec)
                session.commit()
                session.refresh(sec)
                counts["sections"] += 1
            section_map[b_item["name"]][sec_name] = sec

    # 3. Notices (10 total: 9 published with 2 pinned, 1 draft)
    base_time = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    notices_data = [
        {
            "title": "Welcome to DeptHub - Department Information Portal",
            "body": (
                "Welcome faculty and students to the official Department Portal.\n"
                "Find real-time notice updates, class schedules, and exam dates."
            ),
            "category": NoticeCategory.GENERAL,
            "is_pinned": True,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=10),
            "external_link": None,
            "batch_name": None,
        },
        {
            "title": "Spring 2026 Academic Calendar and Guidelines",
            "body": (
                "The Spring 2026 term commences Jan 1 and concludes June 30.\n"
                "Please check your class timetables and subscribe to your batch."
            ),
            "category": NoticeCategory.ACADEMIC,
            "is_pinned": True,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=9),
            "external_link": None,
            "batch_name": None,
        },
        {
            "title": "Midterm Examination Schedule Announcement for 21-22 Session",
            "body": (
                "Midterms for 21-22 batch will start from April 15, 2026.\n"
                "Students must bring valid university identity cards to exam halls."
            ),
            "category": NoticeCategory.EXAM,
            "is_pinned": False,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=8),
            "external_link": None,
            "batch_name": "21-22 Session",
        },
        {
            "title": "Midterm Examination Schedule Announcement for 22-23 Session",
            "body": (
                "Midterm exams for 22-23 batch will take place in Room 401 and Lab 2.\n"
                "Check the exam schedule tab for detailed course timings."
            ),
            "category": NoticeCategory.EXAM,
            "is_pinned": False,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=7),
            "external_link": None,
            "batch_name": "22-23 Session",
        },
        {
            "title": "Annual Department Programming Contest 2026",
            "body": (
                "Registrations are open for the Programming Contest (ADPC 2026).\n"
                "Form teams of 3 and participate in the preliminary round."
            ),
            "category": NoticeCategory.EVENT,
            "is_pinned": False,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=6),
            "external_link": "https://example.com/contest-registration",
            "batch_name": None,
        },
        {
            "title": "Merit Scholarship Applications Open for Academic Year 2025-26",
            "body": (
                "Department Merit Scholarship applications are open for students.\n"
                "Submit transcripts and recommendation letters to the dept office."
            ),
            "category": NoticeCategory.SCHOLARSHIP,
            "is_pinned": False,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=5),
            "external_link": None,
            "batch_name": None,
        },
        {
            "title": "Campus Recruitment Drive: Software Engineering Internships",
            "body": (
                "Tech enterprises will conduct on-campus internship interviews.\n"
                "Graduating students and 3rd-year students are eligible to apply."
            ),
            "category": NoticeCategory.JOB,
            "is_pinned": False,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=4),
            "external_link": "https://example.com/recruitment-drive",
            "batch_name": None,
        },
        {
            "title": "Research Seminar: Advances in Neural Computing and Deep Learning",
            "body": (
                "Guest lecture by Dr. Alan Turing on emerging neural architectures.\n"
                "All faculty members and graduate students are cordially invited."
            ),
            "category": NoticeCategory.EVENT,
            "is_pinned": False,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=3),
            "external_link": None,
            "batch_name": None,
        },
        {
            "title": "Library Book Return and Renewal Deadline",
            "body": (
                "All departmental library books borrowed during the previous term\n"
                "must be returned or renewed by the end of this week."
            ),
            "category": NoticeCategory.GENERAL,
            "is_pinned": False,
            "status": NoticeStatus.PUBLISHED,
            "published_at": base_time + timedelta(days=2),
            "external_link": None,
            "batch_name": None,
        },
        {
            "title": "Internal Draft: Upcoming Department Curriculum Committee Meeting",
            "body": (
                "Draft agenda for syllabus modernization and lab equipment.\n"
                "Strictly confidential until ratified by the academic council."
            ),
            "category": NoticeCategory.ACADEMIC,
            "is_pinned": False,
            "status": NoticeStatus.DRAFT,
            "published_at": None,
            "external_link": None,
            "batch_name": None,
        },
    ]

    for n_data in notices_data:
        existing_notice = session.exec(
            select(Notice).where(Notice.title == n_data["title"])
        ).first()
        if not existing_notice:
            b_id = batch_map[n_data["batch_name"]].id if n_data["batch_name"] else None
            notice = Notice(
                title=n_data["title"],
                body=n_data["body"],
                category=n_data["category"],
                is_pinned=n_data["is_pinned"],
                status=n_data["status"],
                published_at=n_data["published_at"],
                external_link=n_data["external_link"],
                batch_id=b_id,
            )
            session.add(notice)
            counts["notices"] += 1
    session.commit()

    # 4. Weekly Routine Slots
    # Full weekly schedule for 21-22 Session and 22-23 Session
    b1 = batch_map["21-22 Session"]
    b2 = batch_map["22-23 Session"]
    sec_b1_a = section_map["21-22 Session"]["A"]
    sec_b1_b = section_map["21-22 Session"]["B"]
    sec_b2_a = section_map["22-23 Session"]["A"]

    routine_data = [
        # 21-22 Session Slots
        {
            "batch_id": b1.id,
            "section_id": sec_b1_a.id,
            "weekday": "Monday",
            "start_time": time(9, 0),
            "end_time": time(10, 30),
            "course_code": "CSE-301",
            "course_title": "Database Systems",
            "teacher": "Dr. Codd",
            "room": "Room 301",
        },
        {
            "batch_id": b1.id,
            "section_id": sec_b1_b.id,
            "weekday": "Monday",
            "start_time": time(9, 0),
            "end_time": time(10, 30),
            "course_code": "CSE-302",
            "course_title": "Database Systems Lab",
            "teacher": "Mr. Stonebraker",
            "room": "Lab 1",
        },
        {
            "batch_id": b1.id,
            "section_id": None,
            "weekday": "Monday",
            "start_time": time(11, 0),
            "end_time": time(12, 30),
            "course_code": "CSE-303",
            "course_title": "Operating Systems",
            "teacher": "Prof. Tanenbaum",
            "room": "Auditorium",
        },
        {
            "batch_id": b1.id,
            "section_id": None,
            "weekday": "Tuesday",
            "start_time": time(10, 0),
            "end_time": time(11, 30),
            "course_code": "CSE-305",
            "course_title": "Software Engineering",
            "teacher": "Dr. Brooks",
            "room": "Room 301",
        },
        {
            "batch_id": b1.id,
            "section_id": None,
            "weekday": "Wednesday",
            "start_time": time(9, 0),
            "end_time": time(10, 30),
            "course_code": "CSE-307",
            "course_title": "Computer Networks",
            "teacher": "Prof. Cerf",
            "room": "Room 301",
        },
        {
            "batch_id": b1.id,
            "section_id": None,
            "weekday": "Thursday",
            "start_time": time(14, 0),
            "end_time": time(15, 30),
            "course_code": "CSE-309",
            "course_title": "Artificial Intelligence",
            "teacher": "Prof. Russell",
            "room": "Room 302",
        },
        # 22-23 Session Slots
        {
            "batch_id": b2.id,
            "section_id": sec_b2_a.id,
            "weekday": "Sunday",
            "start_time": time(10, 0),
            "end_time": time(11, 30),
            "course_code": "CSE-101",
            "course_title": "Structured Programming",
            "teacher": "Dr. Ritchie",
            "room": "Room 201",
        },
        {
            "batch_id": b2.id,
            "section_id": None,
            "weekday": "Monday",
            "start_time": time(13, 0),
            "end_time": time(14, 30),
            "course_code": "MATH-101",
            "course_title": "Differential Calculus",
            "teacher": "Dr. Euler",
            "room": "Room 201",
        },
        {
            "batch_id": b2.id,
            "section_id": None,
            "weekday": "Tuesday",
            "start_time": time(9, 0),
            "end_time": time(10, 30),
            "course_code": "PHY-101",
            "course_title": "Engineering Physics",
            "teacher": "Dr. Feynman",
            "room": "Room 202",
        },
        {
            "batch_id": b2.id,
            "section_id": None,
            "weekday": "Wednesday",
            "start_time": time(11, 0),
            "end_time": time(12, 30),
            "course_code": "CSE-103",
            "course_title": "Discrete Mathematics",
            "teacher": "Dr. Knuth",
            "room": "Room 201",
        },
    ]

    for r_item in routine_data:
        existing_slot = session.exec(
            select(RoutineSlot).where(
                RoutineSlot.batch_id == r_item["batch_id"],
                RoutineSlot.weekday == r_item["weekday"],
                RoutineSlot.start_time == r_item["start_time"],
                RoutineSlot.course_code == r_item["course_code"],
            )
        ).first()
        if not existing_slot:
            slot = RoutineSlot(**r_item)
            session.add(slot)
            counts["routine_slots"] += 1
    session.commit()

    local_today, _ = get_current_local_date_and_weekday()

    # 5. Exams (4 exams across types: 3 upcoming, 1 past)
    exams_data = [
        {
            "batch_id": b1.id,
            "course": "CSE-301 Database Systems",
            "type": ExamType.MIDTERM,
            "date": local_today + timedelta(days=14),
            "start_time": time(10, 0),
            "room": "Auditorium",
            "note": "Syllabus: Chapters 1 to 5. Calculators permitted.",
        },
        {
            "batch_id": b1.id,
            "course": "CSE-303 Operating Systems",
            "type": ExamType.FINAL,
            "date": local_today + timedelta(days=45),
            "start_time": time(9, 30),
            "room": "Room 301 & 302",
            "note": "Comprehensive final examination. Duration 3 hours.",
        },
        {
            "batch_id": b2.id,
            "course": "CSE-101 Structured Programming",
            "type": ExamType.CLASS_TEST,
            "date": local_today - timedelta(days=7),
            "start_time": time(11, 0),
            "room": "Room 201",
            "note": "Class Test on pointers and dynamic memory allocation.",
        },
        {
            "batch_id": b2.id,
            "course": "CSE-102 Programming Lab",
            "type": ExamType.LAB,
            "date": local_today + timedelta(days=28),
            "start_time": time(14, 0),
            "room": "Lab 2",
            "note": "On-system hands-on programming assessment.",
        },
    ]

    for e_item in exams_data:
        existing_exam = session.exec(
            select(Exam).where(
                Exam.batch_id == e_item["batch_id"],
                Exam.course == e_item["course"],
                Exam.date == e_item["date"],
            )
        ).first()
        if not existing_exam:
            exam = Exam(**e_item)
            session.add(exam)
            counts["exams"] += 1
    session.commit()

    return counts


def main() -> None:
    init_db()
    with Session(engine) as session:
        counts = seed_database(session)
        print("Database seed completed successfully:")
        for entity, count in counts.items():
            print(f"  - {entity}: +{count} created")


if __name__ == "__main__":
    main()
