"""Versioned schema migrations and first-run seed data.

Each migration runs once inside its own transaction and bumps
``schema_version``; new versions are appended to ``MIGRATIONS``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.core.settings_keys import DEFAULTS, Key
from app.core.text import normalize_name
from app.database.engine import get_engine, write_session
from app.models import AppSetting, Base, Category, Unit

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

DEFAULT_CATEGORIES = [
    ("برنامه‌نویسی", "#8B5CF6"),
    ("توسعه هوش مصنوعی", "#60A5FA"),
    ("طراحی", "#F472B6"),
    ("جلسه", "#FBBF24"),
    ("آموزش", "#34D399"),
    ("تحقیق و توسعه", "#2DD4BF"),
    ("پشتیبانی", "#FB923C"),
    ("سایر فعالیت‌ها", "#94A3B8"),
]

DEFAULT_UNITS = ["عدد", "کلیپ", "عکس", "صفحه", "بسته", "مورد", "کیلوگرم"]


def _migration_1(conn: Connection) -> None:
    Base.metadata.create_all(conn)


MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (1, _migration_1),
]


def current_version() -> int:
    with get_engine().begin() as conn:
        conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        value = conn.exec_driver_sql("SELECT MAX(version) FROM schema_version").scalar()
    return int(value or 0)


def run_migrations() -> int:
    version = current_version()
    for target, migrate in MIGRATIONS:
        if target <= version:
            continue
        log.info("Applying migration %s", target)
        with get_engine().begin() as conn:
            migrate(conn)
            conn.exec_driver_sql("INSERT INTO schema_version (version) VALUES (?)", (target,))
        version = target
    return version


def seed_defaults() -> None:
    """Insert defaults once; items the user deletes later are not re-created."""
    with write_session() as session:
        existing = set(session.scalars(select(AppSetting.key)))
        if Key.SEEDED not in existing:
            if session.scalar(select(Category.id).limit(1)) is None:
                for order, (name, color) in enumerate(DEFAULT_CATEGORIES):
                    session.add(
                        Category(name=name, normalized_name=normalize_name(name), color=color, sort_order=order)
                    )
            if session.scalar(select(Unit.id).limit(1)) is None:
                for name in DEFAULT_UNITS:
                    session.add(Unit(name=name, normalized_name=normalize_name(name)))
            session.add(AppSetting(key=Key.SEEDED, value="1"))
        for key, value in DEFAULTS.items():
            if key not in existing:
                session.add(AppSetting(key=key, value=value))


def initialize_database() -> None:
    run_migrations()
    seed_defaults()
