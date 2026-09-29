"""Database engine / session setup (SQLAlchemy 2.x)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    kwargs: dict = {"future": True}
    if is_sqlite(url):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if is_sqlite(url):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """One transaction per request: commit on success, rollback on any error.

    Services only flush; the commit happens exactly once here, so a failure in
    any later step of a request (e.g. order confirmation) rolls back everything.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
