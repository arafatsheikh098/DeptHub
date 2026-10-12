from datetime import date, time

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from app.auth import require_admin
from app.database import get_session
from app.models.batch import Batch
from app.models.exam import Exam, ExamType
from app.security import get_csrf_token, verify_csrf
from app.utils import (
    format_date,
    format_dt,
    format_time,
    get_current_local_date_and_weekday,
)

router = APIRouter(tags=["Exams"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["format_dt"] = format_dt
templates.env.globals["format_date"] = format_date
templates.env.globals["format_time"] = format_time


@router.get("/exams", response_class=HTMLResponse)
def list_public_exams(
    request: Request,
    batch_id: int | None = None,
    show_past: bool = False,
    session: Session = Depends(get_session),
):
    local_today, _ = get_current_local_date_and_weekday()
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()

    statement = select(Exam)
    if batch_id:
        statement = statement.where(Exam.batch_id == batch_id)

    # Filter past exams unless show_past is True
    if not show_past:
        statement = statement.where(col(Exam.date) >= local_today)

    statement = statement.order_by(
        col(Exam.date).asc(),
        col(Exam.start_time).asc(),
    )
    exams = session.exec(statement).all()

    csrf_token = get_csrf_token(request)
    is_admin = bool(request.session.get("user_id"))

    return templates.TemplateResponse(
        request=request,
        name="exams/index.html",
        context={
            "csrf_token": csrf_token,
            "exams": exams,
            "batches": batches,
            "selected_batch_id": batch_id,
            "show_past": show_past,
            "local_today": local_today,
            "is_admin": is_admin,
        },
    )


# --- Admin Exam CRUD ---


@router.get("/admin/exams", response_class=HTMLResponse)
def admin_list_exams(
    request: Request,
    batch_id: int | None = None,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    selected_batch = batch_id or (batches[0].id if batches else None)

    statement = select(Exam)
    if selected_batch:
        statement = statement.where(Exam.batch_id == selected_batch)
    statement = statement.order_by(col(Exam.date).asc(), col(Exam.start_time).asc())
    exams = session.exec(statement).all()

    return templates.TemplateResponse(
        request=request,
        name="exams/admin_list.html",
        context={
            "csrf_token": get_csrf_token(request),
            "exams": exams,
            "batches": batches,
            "selected_batch_id": selected_batch,
            "is_admin": True,
        },
    )


@router.get("/admin/exams/new", response_class=HTMLResponse)
def admin_new_exam_page(
    request: Request,
    batch_id: int | None = None,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    selected_batch = batch_id or (batches[0].id if batches else None)

    return templates.TemplateResponse(
        request=request,
        name="exams/form.html",
        context={
            "csrf_token": get_csrf_token(request),
            "exam": None,
            "batches": batches,
            "selected_batch_id": selected_batch,
            "exam_types": ExamType.ALL,
            "is_admin": True,
        },
    )


@router.post(
    "/admin/exams/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_create_exam(
    request: Request,
    batch_id: int = Form(...),
    course: str = Form(...),
    exam_type: str = Form(..., alias="type"),
    exam_date_str: str = Form(..., alias="date"),
    start_time_str: str = Form(..., alias="start_time"),
    room: str = Form(...),
    note: str | None = Form(None),
    session: Session = Depends(get_session),
):
    try:
        y, m, d = map(int, exam_date_str.split("-"))
        exam_date_val = date(y, m, d)
        sh, sm = map(int, start_time_str.split(":"))
        start_time_val = time(sh, sm)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid date or time format."
        ) from None

    exam = Exam(
        batch_id=batch_id,
        course=course.strip(),
        type=exam_type,
        date=exam_date_val,
        start_time=start_time_val,
        room=room.strip(),
        note=note.strip() if note and note.strip() else None,
    )
    session.add(exam)
    session.commit()

    return RedirectResponse(
        url=f"/admin/exams?batch_id={batch_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/admin/exams/{exam_id}/edit", response_class=HTMLResponse)
def admin_edit_exam_page(
    request: Request,
    exam_id: int,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    exam = session.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    return templates.TemplateResponse(
        request=request,
        name="exams/form.html",
        context={
            "csrf_token": get_csrf_token(request),
            "exam": exam,
            "batches": batches,
            "selected_batch_id": exam.batch_id,
            "exam_types": ExamType.ALL,
            "is_admin": True,
        },
    )


@router.post(
    "/admin/exams/{exam_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_update_exam(
    request: Request,
    exam_id: int,
    batch_id: int = Form(...),
    course: str = Form(...),
    exam_type: str = Form(..., alias="type"),
    exam_date_str: str = Form(..., alias="date"),
    start_time_str: str = Form(..., alias="start_time"),
    room: str = Form(...),
    note: str | None = Form(None),
    session: Session = Depends(get_session),
):
    exam = session.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    try:
        y, m, d = map(int, exam_date_str.split("-"))
        exam_date_val = date(y, m, d)
        sh, sm = map(int, start_time_str.split(":"))
        start_time_val = time(sh, sm)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid date or time format."
        ) from None

    exam.batch_id = batch_id
    exam.course = course.strip()
    exam.type = exam_type
    exam.date = exam_date_val
    exam.start_time = start_time_val
    exam.room = room.strip()
    exam.note = note.strip() if note and note.strip() else None

    session.add(exam)
    session.commit()

    return RedirectResponse(
        url=f"/admin/exams?batch_id={batch_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/admin/exams/{exam_id}/delete",
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_delete_exam(
    exam_id: int,
    session: Session = Depends(get_session),
):
    exam = session.get(Exam, exam_id)
    batch_id = exam.batch_id if exam else None
    if exam:
        session.delete(exam)
        session.commit()

    redirect_url = f"/admin/exams?batch_id={batch_id}" if batch_id else "/admin/exams"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
