"""Application-wide signals so every page refreshes after data changes."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AppEvents(QObject):
    # topic: "activities" | "projects" | "lookups" | "settings" | "all"
    data_changed = Signal(str)
    # Request the main window to show a toast: (kind, message, optional (button text, callback))
    toast = Signal(str, str, object)


events = AppEvents()


def notify(topic: str) -> None:
    events.data_changed.emit(topic)


def toast(message: str, kind: str = "success", action: tuple | None = None) -> None:
    events.toast.emit(kind, message, action)
