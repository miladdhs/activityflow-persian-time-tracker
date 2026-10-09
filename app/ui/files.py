"""File dialogs and shell helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QWidget

from app.core.settings_keys import Key
from app.services import settings_service


def _start_dir() -> Path:
    saved = settings_service.get(Key.LAST_EXPORT_DIR)
    if saved and Path(saved).is_dir():
        return Path(saved)
    docs = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(docs) if docs else Path.home()


def ask_save_path(parent: QWidget | None, title: str, file_name: str, file_filter: str) -> Path | None:
    path, _ = QFileDialog.getSaveFileName(parent, title, str(_start_dir() / file_name), file_filter)
    if not path:
        return None
    result = Path(path)
    suffix = Path(file_name).suffix
    if suffix and result.suffix.lower() != suffix.lower():
        result = result.with_name(result.name + suffix)
    settings_service.set(Key.LAST_EXPORT_DIR, str(result.parent))
    return result


def ask_open_path(parent: QWidget | None, title: str, start: Path, file_filter: str) -> Path | None:
    path, _ = QFileDialog.getOpenFileName(parent, title, str(start), file_filter)
    return Path(path) if path else None


def open_folder(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal_file(path: Path) -> None:
    """Show a file selected in Explorer (falls back to opening its folder)."""
    if sys.platform == "win32" and path.exists():
        try:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])  # noqa: S603,S607
            return
        except OSError:
            pass
    open_folder(path.parent)
