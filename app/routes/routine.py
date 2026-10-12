from datetime import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from app.audit import log_audit
from app.auth import require_admin
from app.database import get_session
from app.models.batch import Batch, Section
from app.models.routine import RoutineSlot
from app.models.user import User
from app.routine_validation import validate_routine_slot
from app.security import get_csrf_token, verify_csrf
from app.utils import (
    WEEKDAYS,
    format_dt,
    format_time,
    get_current_local_date_and_weekday,
)

router = APIRouter(tags=["Routine"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["format_dt"] = format_dt
templates.env.globals["format_time"] = format_time


@router.get("/routine", response_class=HTMLResponse)
def get_weekly_routine(
    request: Request,
    batch_id: str | None = None,
    section_id: str | None = None,
    session: Session = Depends(get_session),
):
    parsed_batch_id = int(batch_id) if batch_id and batch_id.strip().isdigit() else None
    parsed_section_id = (
        int(section_id) if section_id and section_id.strip().isdigit() else None
    )
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()

    # Default to first batch if none chosen
    selected_batch_id = (
        parsed_batch_id if parsed_batch_id else (batches[0].id if batches else None)
    )
    selected_batch = (
        session.get(Batch, selected_batch_id) if selected_batch_id else None
    )

    # Load sections for selected batch
    sections = []
    if selected_batch_id:
        sections = session.exec(
            select(Section)
            .where(Section.batch_id == selected_batch_id)
            .order_by(col(Section.name).asc())
        ).all()

    # Query routine slots for the selected batch
    grid_data = {day: [] for day in WEEKDAYS}
    if selected_batch_id:
        statement = select(RoutineSlot).where(RoutineSlot.batch_id == selected_batch_id)
        if parsed_section_id:
            statement = statement.where(
                (RoutineSlot.section_id == parsed_section_id)
                | (RoutineSlot.section_id == None)  # noqa: E711
            )
        statement = statement.order_by(col(RoutineSlot.start_time).asc())
        slots = session.exec(statement).all()

        for slot in slots:
            if slot.weekday in grid_data:
                grid_data[slot.weekday].append(slot)

    csrf_token = get_csrf_token(request)
    is_admin = bool(request.session.get("user_id"))

    return templates.TemplateResponse(
        request=request,
        name="routine/grid.html",
        context={
            "csrf_token": csrf_token,
            "batches": batches,
            "selected_batch": selected_batch,
            "selected_batch_id": selected_batch_id,
            "sections": sections,
            "selected_section_id": parsed_section_id,
            "grid_data": grid_data,
            "weekdays": WEEKDAYS,
            "is_admin": is_admin,
        },
    )


@router.get("/today", response_class=HTMLResponse)
def get_today_routine(
    request: Request,
    batch_id: str | None = None,
    section_id: str | None = None,
    session: Session = Depends(get_session),
):
    parsed_batch_id = int(batch_id) if batch_id and batch_id.strip().isdigit() else None
    parsed_section_id = (
        int(section_id) if section_id and section_id.strip().isdigit() else None
    )
    # Compute local date and weekday in TIMEZONE
    local_date, local_weekday = get_current_local_date_and_weekday()

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    selected_batch_id = (
        parsed_batch_id if parsed_batch_id else (batches[0].id if batches else None)
    )
    selected_batch = (
        session.get(Batch, selected_batch_id) if selected_batch_id else None
    )

    sections = []
    if selected_batch_id:
        sections = session.exec(
            select(Section)
            .where(Section.batch_id == selected_batch_id)
            .order_by(col(Section.name).asc())
        ).all()

    slots = []
    if selected_batch_id:
        statement = (
            select(RoutineSlot)
            .where(RoutineSlot.batch_id == selected_batch_id)
            .where(RoutineSlot.weekday == local_weekday)
        )
        if parsed_section_id:
            statement = statement.where(
                (RoutineSlot.section_id == parsed_section_id)
                | (RoutineSlot.section_id == None)  # noqa: E711
            )
        statement = statement.order_by(col(RoutineSlot.start_time).asc())
        slots = session.exec(statement).all()

    csrf_token = get_csrf_token(request)
    is_admin = bool(request.session.get("user_id"))

    return templates.TemplateResponse(
        request=request,
        name="routine/today.html",
        context={
            "csrf_token": csrf_token,
            "batches": batches,
            "selected_batch": selected_batch,
            "selected_batch_id": selected_batch_id,
            "sections": sections,
            "selected_section_id": parsed_section_id,
            "local_date": local_date,
            "local_weekday": local_weekday,
            "slots": slots,
            "is_admin": is_admin,
        },
    )


# --- Admin Routine CRUD ---


@router.get("/admin/routine", response_class=HTMLResponse)
def admin_list_routine(
    request: Request,
    batch_id: str | None = None,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    parsed_batch_id = int(batch_id) if batch_id and batch_id.strip().isdigit() else None
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    selected_batch_id = (
        parsed_batch_id if parsed_batch_id else (batches[0].id if batches else None)
    )

    statement = select(RoutineSlot)
    if selected_batch_id:
        statement = statement.where(RoutineSlot.batch_id == selected_batch_id)
    statement = statement.order_by(
        col(RoutineSlot.weekday).asc(),
        col(RoutineSlot.start_time).asc(),
    )
    slots = session.exec(statement).all()

    return templates.TemplateResponse(
        request=request,
        name="routine/admin_list.html",
        context={
            "csrf_token": get_csrf_token(request),
            "batches": batches,
            "selected_batch_id": selected_batch_id,
            "slots": slots,
            "is_admin": True,
        },
    )


@router.get("/admin/routine/new", response_class=HTMLResponse)
def admin_new_slot_page(
    request: Request,
    batch_id: str | None = None,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    parsed_batch_id = int(batch_id) if batch_id and batch_id.strip().isdigit() else None
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    selected_batch = parsed_batch_id or (batches[0].id if batches else None)
    sections = (
        session.exec(
            select(Section)
            .where(Section.batch_id == selected_batch)
            .order_by(col(Section.name).asc())
        ).all()
        if selected_batch
        else []
    )

    return templates.TemplateResponse(
        request=request,
        name="routine/form.html",
        context={
            "csrf_token": get_csrf_token(request),
            "slot": None,
            "batches": batches,
            "selected_batch_id": selected_batch,
            "sections": sections,
            "weekdays": WEEKDAYS,
            "is_admin": True,
        },
    )


@router.post(
    "/admin/routine/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_create_slot(
    request: Request,
    batch_id: int = Form(...),
    section_id: str | None = Form(None),
    weekday: str = Form(...),
    start_time_str: str = Form(..., alias="start_time"),
    end_time_str: str = Form(..., alias="end_time"),
    course_code: str = Form(...),
    course_title: str = Form(...),
    teacher: str = Form(...),
    room: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    try:
        sh, sm = map(int, start_time_str.split(":"))
        eh, em = map(int, end_time_str.split(":"))
        start_time_val = time(sh, sm)
        end_time_val = time(eh, em)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid time format. Use HH:MM."
        ) from None

    parsed_section_id = int(section_id) if section_id and section_id.isdigit() else None

    conflict_err = validate_routine_slot(
        session=session,
        weekday=weekday,
        start_time=start_time_val,
        end_time=end_time_val,
        batch_id=batch_id,
        section_id=parsed_section_id,
        teacher=teacher,
        room=room,
    )

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    sections = session.exec(
        select(Section)
        .where(Section.batch_id == batch_id)
        .order_by(col(Section.name).asc())
    ).all()

    if conflict_err:
        return templates.TemplateResponse(
            request=request,
            name="routine/form.html",
            context={
                "csrf_token": get_csrf_token(request),
                "slot": None,
                "batches": batches,
                "selected_batch_id": batch_id,
                "sections": sections,
                "weekdays": WEEKDAYS,
                "form_data": {
                    "batch_id": batch_id,
                    "section_id": parsed_section_id,
                    "weekday": weekday,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "course_code": course_code,
                    "course_title": course_title,
                    "teacher": teacher,
                    "room": room,
                },
                "error": conflict_err,
                "is_admin": True,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    slot = RoutineSlot(
        batch_id=batch_id,
        section_id=parsed_section_id,
        weekday=weekday,
        start_time=start_time_val,
        end_time=end_time_val,
        course_code=course_code.strip(),
        course_title=course_title.strip(),
        teacher=teacher.strip(),
        room=room.strip(),
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)

    t_str = f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"
    log_audit(
        session=session,
        actor=current_user.email,
        action="CREATE",
        entity="RoutineSlot",
        entity_id=slot.id,
        summary=f"Created routine slot: {slot.course_code} ({slot.weekday} {t_str})",
    )
    session.commit()

    return RedirectResponse(
        url=f"/admin/routine?batch_id={batch_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/admin/routine/{slot_id}/edit", response_class=HTMLResponse)
def admin_edit_slot_page(
    request: Request,
    slot_id: int,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    slot = session.get(RoutineSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    sections = session.exec(
        select(Section)
        .where(Section.batch_id == slot.batch_id)
        .order_by(col(Section.name).asc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="routine/form.html",
        context={
            "csrf_token": get_csrf_token(request),
            "slot": slot,
            "batches": batches,
            "selected_batch_id": slot.batch_id,
            "sections": sections,
            "weekdays": WEEKDAYS,
            "is_admin": True,
        },
    )


@router.post(
    "/admin/routine/{slot_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_update_slot(
    request: Request,
    slot_id: int,
    batch_id: int = Form(...),
    section_id: str | None = Form(None),
    weekday: str = Form(...),
    start_time_str: str = Form(..., alias="start_time"),
    end_time_str: str = Form(..., alias="end_time"),
    course_code: str = Form(...),
    course_title: str = Form(...),
    teacher: str = Form(...),
    room: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    slot = session.get(RoutineSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    try:
        sh, sm = map(int, start_time_str.split(":"))
        eh, em = map(int, end_time_str.split(":"))
        start_time_val = time(sh, sm)
        end_time_val = time(eh, em)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid time format. Use HH:MM."
        ) from None

    parsed_section_id = int(section_id) if section_id and section_id.isdigit() else None

    conflict_err = validate_routine_slot(
        session=session,
        weekday=weekday,
        start_time=start_time_val,
        end_time=end_time_val,
        batch_id=batch_id,
        section_id=parsed_section_id,
        teacher=teacher,
        room=room,
        exclude_slot_id=slot_id,
    )

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    sections = session.exec(
        select(Section)
        .where(Section.batch_id == batch_id)
        .order_by(col(Section.name).asc())
    ).all()

    if conflict_err:
        return templates.TemplateResponse(
            request=request,
            name="routine/form.html",
            context={
                "csrf_token": get_csrf_token(request),
                "slot": slot,
                "batches": batches,
                "selected_batch_id": batch_id,
                "sections": sections,
                "weekdays": WEEKDAYS,
                "error": conflict_err,
                "is_admin": True,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    slot.batch_id = batch_id
    slot.section_id = parsed_section_id
    slot.weekday = weekday
    slot.start_time = start_time_val
    slot.end_time = end_time_val
    slot.course_code = course_code.strip()
    slot.course_title = course_title.strip()
    slot.teacher = teacher.strip()
    slot.room = room.strip()

    session.add(slot)
    session.commit()

    log_audit(
        session=session,
        actor=current_user.email,
        action="UPDATE",
        entity="RoutineSlot",
        entity_id=slot.id,
        summary=f"Updated routine slot: {slot.course_code} ({slot.weekday})",
    )
    session.commit()

    return RedirectResponse(
        url=f"/admin/routine?batch_id={batch_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/admin/routine/{slot_id}/delete",
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_delete_slot(
    slot_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    slot = session.get(RoutineSlot, slot_id)
    batch_id = slot.batch_id if slot else None
    if slot:
        slot_code = slot.course_code
        slot_day = slot.weekday
        session.delete(slot)
        session.commit()

        log_audit(
            session=session,
            actor=current_user.email,
            action="DELETE",
            entity="RoutineSlot",
            entity_id=slot_id,
            summary=f"Deleted routine slot: {slot_code} ({slot_day})",
        )
        session.commit()

    redirect_url = (
        f"/admin/routine?batch_id={batch_id}" if batch_id else "/admin/routine"
    )
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
