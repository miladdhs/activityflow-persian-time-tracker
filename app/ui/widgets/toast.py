"""Short, non-blocking notifications shown at the bottom of the window."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from app.ui.theme import tokens as t
from app.ui.widgets.common import IconButton, IconTile, button

KINDS = {
    "success": ("tick-square", t.SUCCESS),
    "error": ("danger", t.DANGER),
    "warning": ("info-circle", t.WARNING),
    "info": ("info-circle", t.INFO),
}


class Toast(QFrame):
    def __init__(self, parent: QWidget, message: str, kind: str = "success", duration: int = 3600,
                 action: tuple[str, Callable[[], None]] | None = None):
        super().__init__(parent)
        self.setObjectName("Toast")
        icon_name, color = KINDS.get(kind, KINDS["info"])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 10, 10)
        layout.setSpacing(12)
        layout.addWidget(IconTile(icon_name, color, 32, 18))
        text = QLabel(message)
        text.setWordWrap(True)
        text.setMaximumWidth(420)
        text.setMinimumWidth(min(text.fontMetrics().horizontalAdvance(message) + 8, 360))
        text.setStyleSheet("font-weight: 500;")
        layout.addWidget(text, 1)
        if action:
            action_text, callback = action
            act = button(action_text, "ghost", size="sm")
            act.clicked.connect(lambda: (callback(), self.dismiss()))
            layout.addWidget(act)
            duration = max(duration, 6000)
        close = IconButton("close", "بستن", size=28, icon_px=16)
        close.clicked.connect(self.dismiss)
        layout.addWidget(close)
        self.setAccessibleName(message)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._fade = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade.setDuration(t.MOTION_OPEN)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(duration)
        self._timer.timeout.connect(self.dismiss)
        self._closing = False
        self.adjustSize()

    def appear(self) -> None:
        self.show()
        self.raise_()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._timer.start()

    def enterEvent(self, event):
        self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._closing:
            self._timer.start(1800)
        super().leaveEvent(event)

    def dismiss(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._fade.stop()
        self._fade.setStartValue(self._effect.opacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.deleteLater)
        self._fade.start()


class ToastManager(QObject):
    MAX = 3

    def __init__(self, host: QWidget):
        super().__init__(host)
        self._host = host
        self._toasts: list[Toast] = []
        host.installEventFilter(self)

    def show(self, message: str, kind: str = "success", action: tuple | None = None) -> None:
        toast = Toast(self._host, message, kind, action=action)
        toast.destroyed.connect(lambda *_: self._forget(toast))
        self._toasts.append(toast)
        while len(self._toasts) > self.MAX:
            self._toasts.pop(0).dismiss()
        self._layout()
        toast.appear()

    def _forget(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._layout()

    def _layout(self) -> None:
        try:
            bottom = self._host.height() - 24
        except RuntimeError:  # host window already destroyed during shutdown
            return
        for toast in reversed(self._toasts):
            try:
                toast.adjustSize()
                size = toast.sizeHint()
                width = max(320, min(size.width(), 520))
                toast.resize(width, size.height())
                x = (self._host.width() - width) // 2
                bottom -= toast.height()
                toast.move(QPoint(x, bottom))
                bottom -= 10
            except RuntimeError:
                continue

    def eventFilter(self, obj, event):
        if obj is self._host and event.type() == QEvent.Type.Resize:
            self._layout()
        return False
