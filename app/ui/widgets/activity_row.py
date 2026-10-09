"""Compact clickable rows for activity lists (dashboard, today panel)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.core import formatting as fmt
from app.services.activity_service import ActivityRow
from app.ui.theme import tokens as t
from app.ui.widgets.common import ColorDot, label


class ActivityListRow(QFrame):
    clicked = Signal(object)

    def __init__(self, row: ActivityRow, show_day: bool = True):
        super().__init__()
        self.row = row
        self.setObjectName("ListRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip("برای ویرایش کلیک کنید")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.addWidget(ColorDot(row.project_color or row.category_color or t.BORDER_STRONG, 10), 0, Qt.AlignmentFlag.AlignVCenter)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        title = QLabel(row.title)
        title.setStyleSheet("font-weight: 500;")
        texts.addWidget(title)
        meta = [row.project_name or "بدون پروژه"]
        if row.category_name:
            meta.append(row.category_name)
        if show_day:
            meta.append(fmt.relative_day(row.activity_date))
        if row.start_time and row.end_time:
            meta.append(f"{fmt.fmt_time(row.start_time)}–{fmt.fmt_time(row.end_time)}")
        texts.addWidget(label("  ·  ".join(meta), "caption"))
        layout.addLayout(texts, 1)

        side = QVBoxLayout()
        side.setSpacing(2)
        if row.duration_minutes:
            value = QLabel(fmt.fmt_duration_short(row.duration_minutes))
            value.setStyleSheet(f"color: {t.ACCENT_TEXT}; font-weight: 600;")
            value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            side.addWidget(value)
        if row.quantity is not None:
            qty = label(f"{fmt.fmt_decimal(row.quantity)} {row.unit_name}", "caption")
            qty.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            side.addWidget(qty)
        layout.addLayout(side)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.row)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.row)
            return
        super().keyPressEvent(event)
