"""Admin landing page route.

Provides /admin — a directory of all admin-only sections. Acts as the
top-level hub that the top-nav "Admin" link points to. Each section
links to its own management page.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app.auth import require_admin
from app.database import get_session
from app.models.audit import AuditLog
from app.models.batch import Batch
from app.models.exam import Exam
from app.models.notice import Notice
from app.models.routine import RoutineSlot

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def admin_home(
    request: Request,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    """Admin landing page with summary cards and links to each section."""
    notice_count = session.exec(select(func.count(Notice.id))).one()
    batch_count = session.exec(select(func.count(Batch.id))).one()
    routine_count = session.exec(select(func.count(RoutineSlot.id))).one()
    exam_count = session.exec(select(func.count(Exam.id))).one()
    audit_count = session.exec(select(func.count(AuditLog.id))).one()

    return templates.TemplateResponse(
        request=request,
        name="admin/home.html",
        context={
            "csrf_token": request.session.get("csrf_token", ""),
            "is_admin": True,
            "counts": {
                "notices": notice_count,
                "batches": batch_count,
                "routine": routine_count,
                "exams": exam_count,
                "audit": audit_count,
            },
        },
    )
