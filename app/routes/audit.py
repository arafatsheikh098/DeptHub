from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, func, select

from app.auth import require_admin
from app.database import get_session
from app.models.audit import AuditLog
from app.models.user import User
from app.utils import format_dt

router = APIRouter(prefix="/admin/audit", tags=["Audit"])
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["format_dt"] = format_dt

PER_PAGE = 20


@router.get("", response_class=HTMLResponse)
def view_audit_log(
    request: Request,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_session),
    _user: User = Depends(require_admin),
):
    """View paginated administrative audit trail."""
    total_count = session.exec(select(func.count(AuditLog.id))).one()
    total_pages = max(1, (total_count + PER_PAGE - 1) // PER_PAGE)

    if page > total_pages and total_count > 0:
        page = total_pages

    offset = (page - 1) * PER_PAGE
    logs = session.exec(
        select(AuditLog)
        .order_by(col(AuditLog.time).desc(), col(AuditLog.id).desc())
        .offset(offset)
        .limit(PER_PAGE)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="audit/index.html",
        context={
            "logs": logs,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "is_admin": True,
        },
    )
