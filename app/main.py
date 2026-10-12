from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, text
from starlette.middleware.sessions import SessionMiddleware

from app.auth import get_password_hash
from app.config import settings
from app.database import engine, get_session, init_db
from app.models.user import User
from app.routes.admin import router as admin_router
from app.routes.audit import router as audit_router
from app.routes.auth import router as auth_router
from app.routes.batches import router as batches_router
from app.routes.exams import router as exams_router
from app.routes.feeds import router as feeds_router
from app.routes.notices import router as notices_router
from app.routes.routine import router as routine_router
from app.routes.theme import router as theme_router
from app.security import SecurityHeadersMiddleware

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Production secret validation
    if settings.ENV == "production" and (
        not settings.SECRET_KEY
        or settings.SECRET_KEY == "insecure-dev-secret-key-change-in-production"
        or "insecure" in settings.SECRET_KEY
    ):
        msg = "Production refuses to start with default or insecure SECRET_KEY"
        raise ValueError(msg)

    # Startup: ensure tables exist in dev/test, or check db
    init_db()

    # Optional initial admin user seeding
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        with Session(engine) as session:
            clean_email = settings.ADMIN_EMAIL.lower().strip()
            existing = session.exec(
                select(User).where(User.email == clean_email)
            ).first()
            if not existing:
                admin_user = User(
                    email=clean_email,
                    password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                )
                session.add(admin_user)
                session.commit()

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="DeptHub",
        description="Department Notice Board, Routine, and Exam Schedule",
        lifespan=lifespan,
    )

    # Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Session Middleware with secure signed cookie
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="depthub_session",
        max_age=14 * 86400,
        same_site="lax",
        https_only=(settings.ENV == "production"),
    )

    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Include routes
    app.include_router(auth_router)
    app.include_router(notices_router)
    app.include_router(batches_router)
    app.include_router(routine_router)
    app.include_router(exams_router)
    app.include_router(feeds_router)
    app.include_router(audit_router)
    app.include_router(admin_router)
    app.include_router(theme_router)

    @app.get("/health", tags=["Operations"])
    def health_check(session: Session = Depends(get_session)):
        try:
            session.exec(text("SELECT 1"))
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={"status": "ok"}
            )
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "detail": str(exc)},
            )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return templates.TemplateResponse(
                request=request,
                name="errors/404.html",
                context={"is_admin": False},
                status_code=404,
            )
        detail = getattr(exc, "detail", "Not Found")
        return JSONResponse(status_code=404, content={"detail": detail})

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc: Exception):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return templates.TemplateResponse(
                request=request,
                name="errors/500.html",
                context={"is_admin": False},
                status_code=500,
            )
        return JSONResponse(
            status_code=500, content={"detail": "Internal Server Error"}
        )

    return app


app = create_app()
