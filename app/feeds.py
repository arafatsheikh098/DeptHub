import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Timezone, TimezoneStandard, vUTCOffset

from app.config import Settings
from app.models.batch import Batch
from app.models.exam import Exam
from app.models.notice import Notice
from app.models.routine import RoutineSlot
from app.utils import WEEKDAY_CODES, WEEKDAY_NUMBERS


def format_atom_datetime(dt: datetime | None) -> str:
    """Format datetime as RFC 3339 / ISO 8601 UTC string (e.g. 2026-10-12T14:00:00Z)."""
    if dt is None:
        dt = datetime.now(UTC)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_atom_feed(
    notices: list[Notice],
    base_url: str,
    feed_title: str = "DeptHub Notices",
) -> str:
    """Generate a valid Atom 1.0 XML feed string for the provided notices."""
    base_url = base_url.rstrip("/")
    root = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")

    title_elem = ET.SubElement(root, "title")
    title_elem.text = feed_title

    id_elem = ET.SubElement(root, "id")
    id_elem.text = f"{base_url}/feeds/notices.atom"

    latest_updated = notices[0].published_at if notices else None
    updated_elem = ET.SubElement(root, "updated")
    updated_elem.text = format_atom_datetime(latest_updated)

    ET.SubElement(
        root,
        "link",
        rel="self",
        href=f"{base_url}/feeds/notices.atom",
        type="application/atom+xml",
    )
    ET.SubElement(root, "link", rel="alternate", href=f"{base_url}/", type="text/html")

    author_elem = ET.SubElement(root, "author")
    name_elem = ET.SubElement(author_elem, "name")
    name_elem.text = "DeptHub"

    for notice in notices:
        entry = ET.SubElement(root, "entry")

        entry_title = ET.SubElement(entry, "title")
        entry_title.text = notice.title

        entry_id = ET.SubElement(entry, "id")
        entry_id.text = f"{base_url}/notices/{notice.id}"

        ET.SubElement(
            entry,
            "link",
            rel="alternate",
            href=f"{base_url}/notices/{notice.id}",
            type="text/html",
        )

        entry_published = ET.SubElement(entry, "published")
        entry_published.text = format_atom_datetime(notice.published_at)

        entry_updated = ET.SubElement(entry, "updated")
        entry_updated.text = format_atom_datetime(notice.published_at)

        if notice.category:
            ET.SubElement(entry, "category", term=notice.category)

        entry_summary = ET.SubElement(entry, "summary")
        entry_summary.text = notice.body

        entry_content = ET.SubElement(entry, "content", type="text")
        entry_content.text = notice.body

        entry_author = ET.SubElement(entry, "author")
        entry_author_name = ET.SubElement(entry_author, "name")
        entry_author_name.text = "DeptHub"

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def generate_batch_ics(
    batch: Batch,
    slots: list[RoutineSlot],
    exams: list[Exam],
    settings: Settings,
) -> bytes:
    """Generate an iCalendar (.ics) stream for a given batch's routine and exams."""
    cal = Calendar()
    cal.add("prodid", "-//DeptHub//DeptHub Schedule//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"DeptHub - {batch.name} Schedule")
    cal.add("x-wr-timezone", settings.TIMEZONE)

    try:
        tz = ZoneInfo(settings.TIMEZONE)
    except Exception:
        tz = ZoneInfo("Asia/Dhaka")

    try:
        term_start = date.fromisoformat(settings.TERM_START)
    except Exception:
        term_start = date(2026, 1, 1)

    try:
        term_end = date.fromisoformat(settings.TERM_END)
    except Exception:
        term_end = date(2026, 6, 30)

    # Standard VTIMEZONE component
    tz_comp = Timezone()
    tz_comp.add("tzid", settings.TIMEZONE)
    tz_std = TimezoneStandard()
    tz_std.add("dtstart", datetime(1970, 1, 1, 0, 0, 0))
    tz_std.add("tzname", "LOCAL")
    ref_dt = datetime(2026, 1, 1)
    offset = tz.utcoffset(ref_dt)
    if offset is not None:
        tz_std.add("tzoffsetfrom", vUTCOffset(offset))
        tz_std.add("tzoffsetto", vUTCOffset(offset))
    tz_comp.add_component(tz_std)
    cal.add_component(tz_comp)

    until_utc = datetime.combine(term_end, time(23, 59, 59), tzinfo=UTC)

    # 1. Weekly Routine Slots
    for slot in slots:
        byday = WEEKDAY_CODES.get(slot.weekday)
        target_weekday = WEEKDAY_NUMBERS.get(slot.weekday)
        if not byday or target_weekday is None:
            continue

        days_ahead = (target_weekday - term_start.weekday()) % 7
        first_date = term_start + timedelta(days=days_ahead)
        dtstart = datetime.combine(first_date, slot.start_time, tzinfo=tz)
        dtend = datetime.combine(first_date, slot.end_time, tzinfo=tz)

        sec_title = f" ({slot.section.name})" if slot.section else ""
        summary = f"{slot.course_code}: {slot.course_title}{sec_title}"

        event = Event()
        event.add("uid", f"routine-slot-{slot.id}@depthub.local")
        dtstamp = slot.created_at if slot.created_at else datetime.now(UTC)
        event.add("dtstamp", dtstamp)
        event.add("dtstart", dtstart)
        event.add("dtend", dtend)
        event.add("summary", summary)
        if slot.room:
            event.add("location", slot.room)

        desc_lines = [
            f"Course: {slot.course_code} - {slot.course_title}",
            f"Teacher: {slot.teacher}",
        ]
        if slot.section:
            desc_lines.append(f"Section: {slot.section.name}")
        event.add("description", "\n".join(desc_lines))

        event.add("rrule", {"FREQ": "WEEKLY", "UNTIL": until_utc, "BYDAY": byday})
        cal.add_component(event)

    # 2. One-off Exam Events
    for exam in exams:
        event = Event()
        event.add("uid", f"exam-{exam.id}@depthub.local")
        dtstamp = exam.created_at if exam.created_at else datetime.now(UTC)
        event.add("dtstamp", dtstamp)

        dtstart = datetime.combine(exam.date, exam.start_time, tzinfo=tz)
        dtend = dtstart + timedelta(hours=2)
        event.add("dtstart", dtstart)
        event.add("dtend", dtend)
        event.add("summary", f"[{exam.type}] {exam.course}")
        if exam.room:
            event.add("location", exam.room)

        desc = exam.note or f"{exam.type} examination for {exam.course}"
        event.add("description", desc)
        cal.add_component(event)

    return cal.to_ical()
