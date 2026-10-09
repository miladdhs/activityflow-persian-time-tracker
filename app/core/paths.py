"""Filesystem locations for resources and user data.

User data always lives outside the executable (``%LOCALAPPDATA%\\ActivityFlow``)
so replacing the EXE with a newer build never touches the database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app import APP_NAME


def resource_root() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir) / "app" / "resources"
    return Path(__file__).resolve().parent.parent / "resources"


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def _ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    override = os.environ.get("ACTIVITYFLOW_DATA_DIR")
    if override:
        return _ensure(Path(override))
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return _ensure(root / APP_NAME)


def db_path() -> Path:
    return data_dir() / "activityflow.sqlite3"


def backups_dir() -> Path:
    return _ensure(data_dir() / "backups")


def logs_dir() -> Path:
    return _ensure(data_dir() / "logs")


def cache_dir() -> Path:
    return _ensure(data_dir() / "cache")
