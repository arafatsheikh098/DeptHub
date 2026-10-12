from datetime import time

from sqlmodel import Session, select

from app.models.routine import RoutineSlot


def times_overlap(s1: time, e1: time, s2: time, e2: time) -> bool:
    """Return True if two time intervals strictly overlap.

    Touching boundaries like 10:00-11:00 and 11:00-12:00 do not overlap.
    """
    return max(s1, s2) < min(e1, e2)


def validate_routine_slot(
    session: Session,
    weekday: str,
    start_time: time,
    end_time: time,
    batch_id: int,
    section_id: int | None,
    teacher: str,
    room: str,
    exclude_slot_id: int | None = None,
) -> str | None:
    """Validate a routine slot against existing slots.

    Returns an error message describing the conflict, or None if valid.
    """
    # 1. End must be strictly after start
    if end_time <= start_time:
        return "End time must be strictly after start time."

    clean_teacher = teacher.strip().lower()
    clean_room = room.strip().lower()

    # Query all slots on the same weekday
    existing_slots = session.exec(
        select(RoutineSlot).where(RoutineSlot.weekday == weekday)
    ).all()

    for slot in existing_slots:
        if exclude_slot_id and slot.id == exclude_slot_id:
            continue

        if not times_overlap(start_time, end_time, slot.start_time, slot.end_time):
            continue

        t_start = slot.start_time.strftime("%H:%M")
        t_end = slot.end_time.strftime("%H:%M")
        time_str = f"{t_start} - {t_end}"

        # 2. Batch & section overlap
        if slot.batch_id == batch_id and (
            section_id is None
            or slot.section_id is None
            or section_id == slot.section_id
        ):
            return (
                f"Batch schedule conflict: Overlaps with {slot.course_code} "
                f"'{slot.course_title}' ({time_str})"
            )

        # 3. Room double-booking (case-insensitive, across any batch)
        if slot.room.strip().lower() == clean_room:
            return (
                f"Room double-booking conflict: Room '{slot.room}' is already "
                f"occupied by {slot.course_code} ({time_str})"
            )

        # 4. Teacher double-booking (case-insensitive, across any batch)
        if slot.teacher.strip().lower() == clean_teacher:
            return (
                f"Teacher double-booking conflict: Teacher '{slot.teacher}' is already "
                f"teaching {slot.course_code} ({time_str})"
            )

    return None
