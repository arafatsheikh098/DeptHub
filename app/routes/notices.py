from datetime import UTC, datetime
from math import ceil

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from app.audit import log_audit
from app.auth import require_admin
from app.database import get_session
from app.models.batch import Batch
from app.models.notice import Notice, NoticeCategory, NoticeStatus
from app.models.user import User
from app.security import get_csrf_token, verify_csrf
from app.utils import format_dt, is_safe_external_url

router = APIRouter(tags=["Notices"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["format_dt"] = format_dt

PAGE_SIZE = 10


@router.get("/", response_class=HTMLResponse)
def list_public_notices(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    batch_id: str | None = None,
    page: int = Query(default=1, ge=1),
    session: Session = Depends(get_session),
):
    parsed_batch_id = int(batch_id) if batch_id and batch_id.strip().isdigit() else None

    # Base query: only published notices for public view
    statement = select(Notice).where(Notice.status == NoticeStatus.PUBLISHED)

    # 1. Search filter: title or body case-insensitive
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        statement = statement.where(
            col(Notice.title).ilike(search_term) | col(Notice.body).ilike(search_term)
        )

    # 2. Category filter
    if category and category.strip():
        statement = statement.where(Notice.category == category.strip())

    # 3. Batch filter: target batch or empty batch (for all batches)
    if parsed_batch_id:
        statement = statement.where(
            (Notice.batch_id == parsed_batch_id) | (Notice.batch_id == None)  # noqa: E711
        )

    # Ordering: Pinned first, then newest published_at, then newest id
    statement = statement.order_by(
        col(Notice.is_pinned).desc(),
        col(Notice.published_at).desc(),
        col(Notice.id).desc(),
    )

    all_notices = session.exec(statement).all()
    total_count = len(all_notices)
    total_pages = max(1, ceil(total_count / PAGE_SIZE))

    # Decision D002: If page exceeds total_pages, redirect to last available page
    if page > total_pages and total_count > 0:
        query_params = []
        if q:
            query_params.append(f"q={q}")
        if category:
            query_params.append(f"category={category}")
        if parsed_batch_id:
            query_params.append(f"batch_id={parsed_batch_id}")
        query_params.append(f"page={total_pages}")
        return RedirectResponse(
            url=f"/?{'&'.join(query_params)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Slice for current page
    start_idx = (page - 1) * PAGE_SIZE
    page_notices = all_notices[start_idx : start_idx + PAGE_SIZE]

    # Batches for filter dropdown
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()

    csrf_token = get_csrf_token(request)
    is_admin = bool(request.session.get("user_id"))

    context = {
        "csrf_token": csrf_token,
        "notices": page_notices,
        "total_count": total_count,
        "current_page": page,
        "total_pages": total_pages,
        "query": q or "",
        "selected_category": category or "",
        "selected_batch": parsed_batch_id,
        "categories": NoticeCategory.ALL,
        "batches": batches,
        "is_admin": is_admin,
    }

    # HTMX partial rendering support
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="notices/_list_partial.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="notices/index.html",
        context=context,
    )


@router.get("/notices/{notice_id}", response_class=HTMLResponse)
def get_notice_detail(
    request: Request,
    notice_id: int,
    session: Session = Depends(get_session),
):
    notice = session.get(Notice, notice_id)
    is_admin = bool(request.session.get("user_id"))

    # Drafts never appear to public visitors
    if not notice or (notice.status == NoticeStatus.DRAFT and not is_admin):
        return templates.TemplateResponse(
            request=request,
            name="errors/404.html",
            context={
                "csrf_token": get_csrf_token(request),
                "is_admin": is_admin,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return templates.TemplateResponse(
        request=request,
        name="notices/detail.html",
        context={
            "csrf_token": get_csrf_token(request),
            "notice": notice,
            "is_admin": is_admin,
        },
    )


# --- Admin Notice CRUD ---


@router.get("/admin/notices", response_class=HTMLResponse)
def admin_list_notices(
    request: Request,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    statement = select(Notice).order_by(
        col(Notice.is_pinned).desc(),
        col(Notice.created_at).desc(),
    )
    notices = session.exec(statement).all()
    return templates.TemplateResponse(
        request=request,
        name="notices/admin_list.html",
        context={
            "csrf_token": get_csrf_token(request),
            "notices": notices,
            "is_admin": True,
        },
    )


@router.get("/admin/notices/new", response_class=HTMLResponse)
def admin_new_notice_page(
    request: Request,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    return templates.TemplateResponse(
        request=request,
        name="notices/form.html",
        context={
            "csrf_token": get_csrf_token(request),
            "notice": None,
            "categories": NoticeCategory.ALL,
            "batches": batches,
            "is_admin": True,
        },
    )


@router.post(
    "/admin/notices/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_create_notice(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    category: str = Form(...),
    batch_id: str | None = Form(None),
    external_link: str | None = Form(None),
    status_choice: str = Form("published", alias="status"),
    is_pinned: bool = Form(False),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    clean_title = title.strip()
    clean_link = (
        external_link.strip() if external_link and external_link.strip() else None
    )

    # Validations
    errors = []
    if not clean_title:
        errors.append("Title is required.")
    elif len(clean_title) > 150:
        errors.append("Title cannot exceed 150 characters.")

    if clean_link and not is_safe_external_url(clean_link):
        errors.append("External link must start with http:// or https://")

    if category not in NoticeCategory.ALL:
        errors.append(f"Invalid category '{category}'.")

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()

    if errors:
        parsed_batch = int(batch_id) if batch_id and batch_id.isdigit() else None
        return templates.TemplateResponse(
            request=request,
            name="notices/form.html",
            context={
                "csrf_token": get_csrf_token(request),
                "notice": None,
                "form_data": {
                    "title": clean_title,
                    "body": body,
                    "category": category,
                    "batch_id": parsed_batch,
                    "external_link": clean_link,
                    "is_pinned": is_pinned,
                },
                "categories": NoticeCategory.ALL,
                "batches": batches,
                "error": " ".join(errors),
                "is_admin": True,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    parsed_batch_id = int(batch_id) if batch_id and batch_id.isdigit() else None
    now_utc = datetime.now(UTC)

    notice = Notice(
        title=clean_title,
        body=body,
        category=category,
        batch_id=parsed_batch_id,
        external_link=clean_link,
        status=status_choice,
        is_pinned=is_pinned,
        published_at=now_utc if status_choice == NoticeStatus.PUBLISHED else None,
        created_at=now_utc,
        updated_at=now_utc,
    )
    session.add(notice)
    session.commit()
    session.refresh(notice)

    log_audit(
        session=session,
        actor=current_user.email,
        action="CREATE",
        entity="Notice",
        entity_id=notice.id,
        summary=f"Created notice: '{notice.title}' ({notice.category})",
    )
    session.commit()

    return RedirectResponse(url="/admin/notices", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/notices/{notice_id}/edit", response_class=HTMLResponse)
def admin_edit_notice_page(
    request: Request,
    notice_id: int,
    session: Session = Depends(get_session),
    _user=Depends(require_admin),
):
    notice = session.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()
    return templates.TemplateResponse(
        request=request,
        name="notices/form.html",
        context={
            "csrf_token": get_csrf_token(request),
            "notice": notice,
            "categories": NoticeCategory.ALL,
            "batches": batches,
            "is_admin": True,
        },
    )


@router.post(
    "/admin/notices/{notice_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_update_notice(
    request: Request,
    notice_id: int,
    title: str = Form(...),
    body: str = Form(...),
    category: str = Form(...),
    batch_id: str | None = Form(None),
    external_link: str | None = Form(None),
    status_choice: str = Form("published", alias="status"),
    is_pinned: bool = Form(False),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    notice = session.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    clean_title = title.strip()
    clean_link = (
        external_link.strip() if external_link and external_link.strip() else None
    )

    errors = []
    if not clean_title:
        errors.append("Title is required.")
    elif len(clean_title) > 150:
        errors.append("Title cannot exceed 150 characters.")

    if clean_link and not is_safe_external_url(clean_link):
        errors.append("External link must start with http:// or https://")

    if category not in NoticeCategory.ALL:
        errors.append(f"Invalid category '{category}'.")

    batches = session.exec(select(Batch).order_by(col(Batch.name).asc())).all()

    if errors:
        return templates.TemplateResponse(
            request=request,
            name="notices/form.html",
            context={
                "csrf_token": get_csrf_token(request),
                "notice": notice,
                "categories": NoticeCategory.ALL,
                "batches": batches,
                "error": " ".join(errors),
                "is_admin": True,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    parsed_batch_id = int(batch_id) if batch_id and batch_id.isdigit() else None
    now_utc = datetime.now(UTC)

    notice.title = clean_title
    notice.body = body
    notice.category = category
    notice.batch_id = parsed_batch_id
    notice.external_link = clean_link
    notice.is_pinned = is_pinned
    notice.updated_at = now_utc

    # If transitioning to published for first time, set published_at
    is_now_pub = status_choice == NoticeStatus.PUBLISHED
    if is_now_pub and notice.status != NoticeStatus.PUBLISHED:
        notice.published_at = now_utc
    notice.status = status_choice

    session.add(notice)
    session.commit()

    log_audit(
        session=session,
        actor=current_user.email,
        action="UPDATE",
        entity="Notice",
        entity_id=notice.id,
        summary=f"Updated notice: '{notice.title}' ({notice.category})",
    )
    session.commit()

    return RedirectResponse(url="/admin/notices", status_code=status.HTTP_303_SEE_OTHER)


@router.post(
    "/admin/notices/{notice_id}/delete",
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def admin_delete_notice(
    notice_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    notice = session.get(Notice, notice_id)
    if notice:
        notice_title = notice.title
        session.delete(notice)
        session.commit()
        log_audit(
            session=session,
            actor=current_user.email,
            action="DELETE",
            entity="Notice",
            entity_id=notice_id,
            summary=f"Deleted notice: '{notice_title}'",
        )
        session.commit()

    return RedirectResponse(url="/admin/notices", status_code=status.HTTP_303_SEE_OTHER)
