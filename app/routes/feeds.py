from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, col, select

from app.config import settings
from app.database import get_session
from app.feeds import generate_atom_feed, generate_batch_ics
from app.models.batch import Batch
from app.models.exam import Exam
from app.models.notice import Notice, NoticeStatus
from app.models.routine import RoutineSlot

router = APIRouter(prefix="/feeds", tags=["Feeds"])


@router.get("/notices.atom")
def get_notices_atom(session: Session = Depends(get_session)) -> Response:
    """Return Atom 1.0 feed for the latest 30 published notices."""
    notices = session.exec(
        select(Notice)
        .where(Notice.status == NoticeStatus.PUBLISHED)
        .order_by(col(Notice.published_at).desc(), col(Notice.id).desc())
        .limit(30)
    ).all()

    xml_content = generate_atom_feed(
        notices=list(notices),
        base_url=settings.PUBLIC_BASE_URL,
        feed_title="DeptHub Notices",
    )
    return Response(
        content=xml_content,
        media_type="application/atom+xml; charset=utf-8",
    )


@router.get("/batch/{batch_id}.ics")
def get_batch_ics(batch_id: int, session: Session = Depends(get_session)) -> Response:
    """Return iCalendar (.ics) feed for a batch's recurring routine and exams."""
    batch = session.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    slots = session.exec(
        select(RoutineSlot)
        .where(RoutineSlot.batch_id == batch_id)
        .order_by(RoutineSlot.weekday, RoutineSlot.start_time)
    ).all()

    exams = session.exec(
        select(Exam)
        .where(Exam.batch_id == batch_id)
        .order_by(Exam.date, Exam.start_time)
    ).all()

    ics_bytes = generate_batch_ics(
        batch=batch,
        slots=list(slots),
        exams=list(exams),
        settings=settings,
    )

    return Response(
        content=ics_bytes,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="batch_{batch_id}.ics"'},
    )
