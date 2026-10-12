from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)


def init_db() -> None:
    """Create all tables in the database (used in testing and initial setup)."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    with Session(engine) as session:
        yield session
