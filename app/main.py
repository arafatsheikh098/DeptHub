from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, text

from app.config import settings
from app.database import engine, get_session, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: ensure tables exist in dev/test, or check db
    init_db()

    # Optional initial admin user seeding
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        from app.auth import get_password_hash
        from app.models.user import User

        with Session(engine) as session:
            existing = session.query(User).first()
            if not existing:
                admin_user = User(
                    email=settings.ADMIN_EMAIL,
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

    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

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

    return app


app = create_app()
templates = Jinja2Templates(directory="app/templates")
