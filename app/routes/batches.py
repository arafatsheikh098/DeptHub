from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from app.auth import require_admin
from app.database import get_session
from app.models.batch import Batch, Section
from app.models.exam import Exam
from app.models.routine import RoutineSlot
from app.security import get_csrf_token, verify_csrf

router = APIRouter(prefix="/admin", tags=["Admin Batches"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/batches", response_class=HTMLResponse)
def list_batches(
    request: Request,
    error: str | None = None,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    return templates.TemplateResponse(
        request=request,
        name="batches/index.html",
        context={
            "csrf_token": get_csrf_token(request),
            "batches": batches,
            "error": error,
            "is_admin": True,
        },
    )


@router.post(
    "/batches/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def create_batch(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session),
):
    clean_name = name.strip()
    if not clean_name:
        return RedirectResponse(
            url="/admin/batches?error=Batch+name+is+required",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    existing = session.exec(
        select(Batch).where(col(Batch.name).ilike(clean_name))
    ).first()
    if existing:
        return RedirectResponse(
            url=f"/admin/batches?error=Batch+'{clean_name}'+already+exists",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    batch = Batch(name=clean_name)
    session.add(batch)
    session.commit()
    return RedirectResponse(url="/admin/batches", status_code=status.HTTP_303_SEE_OTHER)


@router.post(
    "/batches/{batch_id}/sections/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def create_section(
    request: Request,
    batch_id: int,
    name: str = Form(...),
    session: Session = Depends(get_session),
):
    clean_name = name.strip().upper()
    batch = session.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    existing = session.exec(
        select(Section)
        .where(Section.batch_id == batch_id)
        .where(col(Section.name).ilike(clean_name))
    ).first()
    if existing:
        return RedirectResponse(
            url=f"/admin/batches?error=Section+'{clean_name}'+already+exists+in+batch",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    section = Section(batch_id=batch_id, name=clean_name)
    session.add(section)
    session.commit()
    return RedirectResponse(url="/admin/batches", status_code=status.HTTP_303_SEE_OTHER)


@router.post(
    "/batches/{batch_id}/delete",
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def delete_batch(
    batch_id: int,
    session: Session = Depends(get_session),
):
    batch = session.get(Batch, batch_id)
    if not batch:
        return RedirectResponse(
            url="/admin/batches", status_code=status.HTTP_303_SEE_OTHER
        )

    # Decision D003: Block deletion if routine slots or exams or sections exist
    slots_count = len(
        session.exec(select(RoutineSlot).where(RoutineSlot.batch_id == batch_id)).all()
    )
    exams_count = len(session.exec(select(Exam).where(Exam.batch_id == batch_id)).all())
    sections_count = len(
        session.exec(select(Section).where(Section.batch_id == batch_id)).all()
    )

    if slots_count > 0 or exams_count > 0 or sections_count > 0:
        err = (
            f"Cannot delete batch '{batch.name}' because it contains "
            f"{slots_count} routine slots, {exams_count} exams, and "
            f"{sections_count} sections. Remove them first."
        )
        return RedirectResponse(
            url=f"/admin/batches?error={err}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    session.delete(batch)
    session.commit()
    return RedirectResponse(url="/admin/batches", status_code=status.HTTP_303_SEE_OTHER)


@router.post(
    "/sections/{section_id}/delete",
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def delete_section(
    section_id: int,
    session: Session = Depends(get_session),
):
    section = session.get(Section, section_id)
    if section:
        # Check if slots reference this section
        slots_count = len(
            session.exec(
                select(RoutineSlot).where(RoutineSlot.section_id == section_id)
            ).all()
        )
        if slots_count > 0:
            err = (
                f"Cannot delete section '{section.name}' because it has "
                f"{slots_count} routine slots assigned."
            )
            return RedirectResponse(
                url=f"/admin/batches?error={err}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        session.delete(section)
        session.commit()

    return RedirectResponse(url="/admin/batches", status_code=status.HTTP_303_SEE_OTHER)
