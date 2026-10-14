from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.auth import authenticate_user, require_admin
from app.database import get_session
from app.rate_limit import is_login_rate_limited, record_login_attempt
from app.security import get_csrf_token, verify_csrf

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def is_safe_next(next_url: str | None) -> bool:
    """Return True if next_url is a same-site relative path.

    Rejects absolute URLs and protocol-relative ("//host") targets, either of
    which would turn the next= parameter into an open redirect.
    """
    return bool(next_url) and next_url.startswith("/") and not next_url.startswith("//")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None):
    # If already logged in, redirect
    if request.session.get("user_id"):
        redirect_url = next if is_safe_next(next) else "/"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "csrf_token": csrf_token,
            "next_url": next,
            "is_admin": False,
        },
    )


@router.post("/login", response_class=HTMLResponse, dependencies=[Depends(verify_csrf)])
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(None),
    session: Session = Depends(get_session),
):
    ip_address = get_client_ip(request)
    csrf_token = get_csrf_token(request)

    # 1. Check rate limit
    if is_login_rate_limited(session, ip_address, email):
        rate_limit_msg = (
            "Too many failed login attempts. Please try again after 15 minutes."
        )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "csrf_token": csrf_token,
                "email": email,
                "next_url": next,
                "error": rate_limit_msg,
                "is_admin": False,
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # 2. Authenticate
    user = authenticate_user(session, email, password)
    if not user:
        record_login_attempt(session, ip_address, email, success=False)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "csrf_token": csrf_token,
                "email": email,
                "next_url": next,
                "error": "Invalid email or password",
                "is_admin": False,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Success
    record_login_attempt(session, ip_address, email, success=True)
    request.session["user_id"] = user.id
    request.session["user_email"] = user.email

    redirect_url = next if is_safe_next(next) else "/"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post(
    "/logout",
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
