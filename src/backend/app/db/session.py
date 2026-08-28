"""Engine and session factory.

SQLite via SQLAlchemy: zero setup, seeded from the repo's fixtures, swappable
for Postgres later behind the ORM. `reconfigure()` exists so tests can point the
engine at a temp file after changing DATABASE_URL.

`SessionLocal` is created once and re-bound in place by `reconfigure()`, never
replaced. That matters: callers do `from app.db.session import SessionLocal`,
which copies the reference into their own namespace, so rebinding this module's
global would leave every importer holding a sessionmaker bound to the old
engine — and seeding would then write to the wrong database.
"""

from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings

engine: Engine | None = None

# Unbound at first; reconfigure() below binds it before anything can use it.
SessionLocal: sessionmaker[Session] = sessionmaker(
    class_=Session, autoflush=False, expire_on_commit=False
)


def reconfigure() -> None:
    """(Re)build the engine from current settings and re-bind SessionLocal."""
    global engine
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    SessionLocal.configure(bind=engine)


reconfigure()


def init_db() -> None:
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with SessionLocal() as db:
        yield db
