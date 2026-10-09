"""SQLite engine and transactional session helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import AppError, StorageError
from app.core.paths import db_path

log = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionFactory = sessionmaker(expire_on_commit=False)


def _on_connect(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_engine(path: Path | None = None) -> Engine:
    global _engine
    dispose_engine()
    target = Path(path) if path else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{target.as_posix()}",
        connect_args={"timeout": 15, "check_same_thread": False},
    )
    event.listen(engine, "connect", _on_connect)
    _SessionFactory.configure(bind=engine)
    _engine = engine
    return engine


def get_engine() -> Engine:
    if _engine is None:
        return init_engine()
    return _engine


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def _storage_error(exc: Exception) -> StorageError:
    log.exception("Database error", exc_info=exc)
    text = str(exc).lower()
    if isinstance(exc, OperationalError) and "locked" in text:
        return StorageError("پایگاه داده موقتاً در دسترس نیست. چند لحظه بعد دوباره تلاش کنید.")
    if "disk" in text or "readonly" in text:
        return StorageError("امکان نوشتن اطلاعات روی دیسک وجود ندارد. فضای دیسک و دسترسی‌ها را بررسی کنید.")
    return StorageError("ذخیره اطلاعات با خطا مواجه شد.")


@contextmanager
def write_session() -> Iterator[Session]:
    """A session wrapped in a transaction: commits on success, rolls back on error."""
    get_engine()
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except AppError:
        session.rollback()
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        raise _storage_error(exc) from exc
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def read_session() -> Iterator[Session]:
    get_engine()
    session = _SessionFactory()
    try:
        yield session
    except SQLAlchemyError as exc:
        raise _storage_error(exc) from exc
    finally:
        session.close()
