"""Database backup, restore and JSON export.

Backups use SQLite's online backup API, which produces a consistent copy
even while the application is running. Before a restore, the current data
is always saved to a safety backup first.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from sqlalchemy import select

from app import APP_NAME, APP_VERSION
from app.core.errors import StorageError, ValidationError
from app.core.paths import backups_dir, db_path
from app.core.settings_keys import Key
from app.database import dispose_engine, init_engine, initialize_database, read_session
from app.models import Activity, ActivityTitle, Category, Project, Unit
from app.services import settings_service

log = logging.getLogger(__name__)

AUTO_PREFIX = "auto-"
KEEP_AUTO_BACKUPS = 10
REQUIRED_TABLES = {"projects", "activities", "activity_titles", "categories", "units", "app_settings"}
SQLITE_HEADER = b"SQLite format 3\x00"
_INVALID_BACKUP = f"فایل انتخاب‌شده یک نسخه پشتیبان معتبر {APP_NAME} نیست."


@dataclass
class BackupInfo:
    path: Path
    created: datetime
    size: int
    automatic: bool


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _copy_database(source: Path, target: Path) -> None:
    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
            # A self-contained file (no -wal/-shm companions) is safe to copy around.
            dst.execute("PRAGMA journal_mode=DELETE")
        finally:
            dst.close()
    finally:
        src.close()


def create_backup(target: Path | None = None, prefix: str = "backup-") -> Path:
    target = Path(target) if target else backups_dir() / f"{prefix}{_stamp()}.sqlite3"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    try:
        _copy_database(db_path(), target)
    except (sqlite3.Error, OSError) as exc:
        log.exception("Backup failed")
        raise StorageError("تهیه نسخه پشتیبان با خطا مواجه شد. فضای دیسک و مسیر ذخیره را بررسی کنید.") from exc
    return target


def list_backups() -> list[BackupInfo]:
    items = []
    for path in backups_dir().glob("*.sqlite3"):
        stat = path.stat()
        items.append(
            BackupInfo(path, datetime.fromtimestamp(stat.st_mtime), stat.st_size, path.name.startswith(AUTO_PREFIX))
        )
    items.sort(key=lambda b: b.created, reverse=True)
    return items


def auto_backup_if_due(today: date | None = None) -> Path | None:
    if not settings_service.get_bool(Key.AUTO_BACKUP):
        return None
    today = today or date.today()
    if settings_service.get(Key.LAST_AUTO_BACKUP) == today.isoformat():
        return None
    if not db_path().exists():
        return None
    path = create_backup(prefix=AUTO_PREFIX)
    settings_service.set(Key.LAST_AUTO_BACKUP, today.isoformat())
    automatic = [b for b in list_backups() if b.automatic]
    for old in automatic[KEEP_AUTO_BACKUPS:]:
        try:
            old.path.unlink()
        except OSError:
            log.warning("Could not remove old backup %s", old.path)
    return path


def validate_backup_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise ValidationError("فایل انتخاب‌شده پیدا نشد.")
    try:
        with open(path, "rb") as fh:
            header = fh.read(16)
        if header != SQLITE_HEADER:
            raise ValidationError(_INVALID_BACKUP)
        conn = sqlite3.connect(str(path))
        try:
            check = conn.execute("PRAGMA integrity_check").fetchone()
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise ValidationError("فایل پشتیبان خراب است یا قابل خواندن نیست.") from exc
    if not check or check[0] != "ok":
        raise ValidationError("فایل پشتیبان آسیب دیده است و قابل بازیابی نیست.")
    if not REQUIRED_TABLES.issubset(tables):
        raise ValidationError(_INVALID_BACKUP)


def restore_backup(source: Path) -> Path:
    """Replace the current data with ``source``. Returns the safety backup path."""
    source = Path(source)
    validate_backup_file(source)
    safety = create_backup(prefix="pre-restore-")
    dispose_engine()
    try:
        _copy_database(source, db_path())
    except (sqlite3.Error, OSError) as exc:
        log.exception("Restore failed; rolling back to safety copy")
        try:
            _copy_database(safety, db_path())
        except (sqlite3.Error, OSError):
            log.exception("Rollback after failed restore also failed")
        init_engine()
        raise StorageError("بازیابی اطلاعات با خطا مواجه شد. اطلاعات قبلی حفظ شده است.") from exc
    init_engine()
    initialize_database()
    settings_service.invalidate()
    return safety


def _json_value(value):
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    return value


def _rows(session, model) -> list[dict]:
    columns = [c.key for c in model.__table__.columns]
    return [{c: _json_value(getattr(obj, c)) for c in columns} for obj in session.scalars(select(model))]


def export_json(target: Path) -> Path:
    with read_session() as session:
        payload = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "projects": _rows(session, Project),
            "categories": _rows(session, Category),
            "units": _rows(session, Unit),
            "activity_titles": _rows(session, ActivityTitle),
            "activities": _rows(session, Activity),
        }
    try:
        Path(target).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise StorageError("ذخیره فایل JSON با خطا مواجه شد.") from exc
    return Path(target)
