"""SQLAlchemy engine/session management for SQLite."""
from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        url = settings().database_url
        kwargs: dict = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _fk_pragma(dbapi_conn, _):  # enforce foreign keys in SQLite
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_session() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def _ensure_legacy_sqlite_migration() -> None:
    if not settings().database_url.startswith("sqlite"):
        return
    engine = get_engine()
    with engine.begin() as conn:
        table_exists = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='uploaded_images'")
        ).scalar()
        if not table_exists:
            return
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(uploaded_images)")).all()]
        if "sha256" not in columns and "sha26" in columns:
            conn.execute(text("ALTER TABLE uploaded_images RENAME COLUMN sha26 TO sha256"))


def init_db() -> None:
    from backend.models import models  # noqa: F401  (register tables)
    Base.metadata.create_all(bind=get_engine())
    _ensure_legacy_sqlite_migration()
