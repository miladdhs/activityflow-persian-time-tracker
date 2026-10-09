"""Form inputs tuned for Persian users.

Number and time inputs accept Persian, Arabic and Latin digits, and show
digits according to the user's display preference.
"""

from __future__ import annotations

import re
from datetime import time

from PySide6.QtCore import QRegularExpression, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core import formatting as fmt
from app.core.text import to_latin_digits
from app.ui import icons
from app.ui.theme import tokens as t
from app.ui.widgets.common import repolish

_DIGIT = "0-9۰-۹٠-٩"


def dot_icon(color: str, size: int = 10) -> QIcon:
    ratio = 2.0
    pm = QPixmap(int(16 * ratio), int(16 * ratio))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    offset = (16 - size) / 2 * ratio
    p.drawEllipse(int(offset), int(offset), int(size * ratio), int(size * ratio))
    p.end()
    pm.setDevicePixelRatio(ratio)
    return QIcon(pm)


def set_error_state(widget: QWidget, has_error: bool) -> None:
    if bool(widget.property("error")) != has_error:
        widget.setProperty("error", has_error)
        repolish(widget)


class _DigitsMixin:
    """Converts typed digits to the preferred digit set while keeping the cursor."""

    def _convert_digits(self: QLineEdit, text: str) -> None:
        converted = fmt.digits(to_latin_digits(text))
        if converted != text:
            pos = self.cursorPosition()
            self.blockSignals(True)
            self.setText(converted)
            self.blockSignals(False)
            self.setCursorPosition(pos)


class LineEdit(QLineEdit):
    def __init__(self, placeholder: str = "", size: str | None = None, max_length: int = 0):
        super().__init__()
        self.setPlaceholderText(placeholder)
        if size:
            self.setProperty("size", size)
        if max_length:
            self.setMaxLength(max_length)


class NumberInput(_DigitsMixin, QLineEdit):
    value_edited = Signal()

    def __init__(self, placeholder: str = "", decimals: int = 0, max_digits: int = 10, size: str | None = None):
        super().__init__()
        self.setPlaceholderText(placeholder)
        if size:
            self.setProperty("size", size)
        pattern = f"^[{_DIGIT}]{{0,{max_digits}}}"
        if decimals:
            pattern += f"([.,٫/][{_DIGIT}]{{0,{decimals}}})?"
        self.setValidator(QRegularExpressionValidator(QRegularExpression(pattern + "$"), self))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.textEdited.connect(self._on_edited)

    def _on_edited(self, text: str) -> None:
        self._convert_digits(text)
        self.value_edited.emit()

    def raw(self) -> str:
        return to_latin_digits(self.text()).strip()

    def int_value(self) -> int:
        raw = self.raw()
        return int(raw) if raw.isdigit() else 0

    def set_value(self, value) -> None:
        if value is None or value == "":
            self.clear()
        elif isinstance(value, int):
            self.setText(fmt.digits(value))
        else:
            self.setText(fmt.fmt_decimal(value).replace("٬", "").replace(",", ""))


_TIME_RE = re.compile(r"^(\d{1,2})(?:[:.٫/ ]?(\d{1,2}))?$")


def parse_time(text: str) -> time | None:
    """Parse «9»، «930»، «9:5»، «۱۴:۳۰» into a time. Raises ValueError if invalid."""
    raw = to_latin_digits(text or "").strip()
    if not raw:
        return None
    if raw.isdigit() and len(raw) in (3, 4):
        raw = f"{raw[:-2]}:{raw[-2:]}"
    match = _TIME_RE.match(raw)
    if not match:
        raise ValueError("invalid time")
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    if hour == 24 and minute == 0:
        hour, minute = 23, 59
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("invalid time")
    return time(hour, minute)


class TimeInput(_DigitsMixin, QLineEdit):
    time_edited = Signal()

    def __init__(self, placeholder: str = "مثلاً ۰۹:۳۰"):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setMaxLength(5)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setValidator(QRegularExpressionValidator(QRegularExpression(f"^[{_DIGIT}:.٫/ ]{{0,5}}$"), self))
        self.setToolTip("ساعت را به شکل ۰۹:۳۰ وارد کنید. کلیدهای بالا و پایین زمان را ۵ دقیقه تغییر می‌دهند.")
        self.textEdited.connect(self._on_edited)
        self.editingFinished.connect(self.normalize)

    def _on_edited(self, text: str) -> None:
        self._convert_digits(text)
        self.time_edited.emit()

    def time(self) -> time | None:
        return parse_time(self.text())

    def is_valid(self) -> bool:
        try:
            parse_time(self.text())
            return True
        except ValueError:
            return False

    def set_time(self, value: time | None) -> None:
        self.setText(fmt.fmt_time(value) if value else "")
        self.time_edited.emit()

    def normalize(self) -> None:
        try:
            value = parse_time(self.text())
        except ValueError:
            return
        formatted = fmt.fmt_time(value) if value else ""
        if formatted != self.text():
            self.setText(formatted)
            self.time_edited.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            try:
                current = parse_time(self.text()) or time(9, 0)
            except ValueError:
                current = time(9, 0)
            step = 5 if event.key() == Qt.Key.Key_Up else -5
            total = (current.hour * 60 + current.minute + step) % (24 * 60)
            self.set_time(time(total // 60, total % 60))
            return
        super().keyPressEvent(event)


class TextArea(QPlainTextEdit):
    def __init__(self, placeholder: str = "", height: int = 92):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(height)
        self.setTabChangesFocus(True)


class ComboBox(QComboBox):
    """Combo box with a themed, rounded popup; ignores the wheel unless focused."""

    def __init__(self, size: str | None = None, min_width: int = 0):
        super().__init__()
        view = QListView()
        view.setUniformItemSizes(True)
        self.setView(view)
        popup = self.view().window()
        popup.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        )
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMaxVisibleItems(10)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setIconSize(QSize(16, 16))
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)
        if size:
            self.setProperty("size", size)
        if min_width:
            self.setMinimumWidth(min_width)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    def set_items(self, items: list[tuple], keep_current: bool = True) -> None:
        """``items``: (text, data) or (text, data, color) tuples."""
        current = self.currentData() if keep_current else None
        self.blockSignals(True)
        self.clear()
        for item in items:
            text, data = item[0], item[1]
            color = item[2] if len(item) > 2 else None
            if color:
                self.addItem(dot_icon(color), text, data)
            else:
                self.addItem(text, data)
        index = self.index_of(current) if keep_current else -1
        self.setCurrentIndex(index if index >= 0 else 0)
        self.blockSignals(False)

    def index_of(self, data) -> int:
        """Like ``findData`` but also matches ``None`` items reliably."""
        for i in range(self.count()):
            if self.itemData(i) == data:
                return i
        return -1

    def set_current_data(self, data) -> bool:
        index = self.index_of(data)
        if index >= 0:
            self.setCurrentIndex(index)
            return True
        return False


class SearchInput(QLineEdit):
    search_changed = Signal(str)

    def __init__(self, placeholder: str = "جست‌وجو", delay_ms: int = 250, size: str | None = None):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.addAction(icons.icon("search", t.TEXT_MUTED, 18), QLineEdit.ActionPosition.LeadingPosition)
        self.setClearButtonEnabled(True)
        if size:
            self.setProperty("size", size)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(lambda: self.search_changed.emit(self.text()))
        self.textChanged.connect(lambda _: self._timer.start())


class FormField(QWidget):
    """Label above the input, optional hint, and an inline error message below."""

    def __init__(self, label_text: str, widget: QWidget, required: bool = False, hint: str = ""):
        super().__init__()
        self.widget = widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(4)
        title = QLabel(label_text)
        title.setProperty("role", "label")
        head.addWidget(title)
        if required:
            star = QLabel("*")
            star.setStyleSheet(f"color: {t.DANGER}; font-weight: 600;")
            star.setToolTip("الزامی")
            head.addWidget(star)
        head.addStretch(1)
        self.hint_label = QLabel(hint)
        self.hint_label.setProperty("role", "caption")
        self.hint_label.setVisible(bool(hint))
        head.addWidget(self.hint_label)
        layout.addLayout(head)

        layout.addWidget(widget)
        title.setBuddy(widget)
        widget.setAccessibleName(label_text)

        self.error_label = QLabel()
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

    def set_hint(self, text: str) -> None:
        self.hint_label.setText(text)
        self.hint_label.setVisible(bool(text))

    def set_error(self, message: str | None) -> None:
        self.error_label.setText(message or "")
        self.error_label.setVisible(bool(message))
        set_error_state(self.widget, bool(message))

    def clear_error(self) -> None:
        self.set_error(None)
