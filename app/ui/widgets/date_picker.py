"""Date field with a popup month calendar (Jalali or Gregorian, Saturday-first)."""

from __future__ import annotations

import calendar as _calendar
from datetime import date, timedelta

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core import formatting as fmt
from app.core import jalali
from app.ui import icons
from app.ui.theme import tokens as t
from app.ui.widgets.common import IconButton, button, repolish

WEEK_HEADER = ["ش", "ی", "د", "س", "چ", "پ", "ج"]


def _sat_index(d: date) -> int:
    """Column of ``d`` in a Saturday-first week (Saturday == 0)."""
    return (d.weekday() + 2) % 7


def _month_bounds(year: int, month: int) -> tuple[date, int]:
    if fmt.prefs.is_jalali:
        return jalali.from_jalali(year, month, 1), jalali.jalali_month_length(year, month)
    return date(year, month, 1), _calendar.monthrange(year, month)[1]


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


class CalendarPopup(QWidget):
    picked = Signal(object)  # date | None

    def __init__(self, selected: date | None, max_date: date | None, allow_empty: bool, parent: QWidget):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._selected = selected
        self._max = max_date
        self._today = date.today()
        anchor = selected or min(self._today, max_date or self._today)
        self._year, self._month, _ = fmt.date_parts(anchor)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("PopupFrame")
        outer.addWidget(frame)
        root = QVBoxLayout(frame)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        head = QHBoxLayout()
        self._prev = IconButton("arrow-right", "ماه قبل", size=30, icon_px=16)
        self._next = IconButton("arrow-left", "ماه بعد", size=30, icon_px=16)
        self._title = QLabel()
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("font-weight: 600; font-size: 14px;")
        self._prev.clicked.connect(lambda: self._shift(-1))
        self._next.clicked.connect(lambda: self._shift(1))
        head.addWidget(self._prev)
        head.addWidget(self._title, 1)
        head.addWidget(self._next)
        root.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(2)
        for col, name in enumerate(WEEK_HEADER):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setProperty("role", "caption")
            lbl.setFixedHeight(22)
            grid.addWidget(lbl, 0, col)
        self._cells: list[QToolButton] = []
        for i in range(42):
            cell = QToolButton()
            cell.setObjectName("DayCell")
            cell.setFixedSize(36, 34)
            cell.setCursor(Qt.CursorShape.PointingHandCursor)
            cell.clicked.connect(lambda _=False, c=cell: self._pick(c.property("day")))
            grid.addWidget(cell, 1 + i // 7, i % 7)
            self._cells.append(cell)
        root.addLayout(grid)

        foot = QHBoxLayout()
        today_btn = button("امروز", "ghost", size="sm")
        today_btn.clicked.connect(lambda: self._pick(self._today))
        today_btn.setEnabled(max_date is None or self._today <= max_date)
        foot.addWidget(today_btn)
        foot.addStretch(1)
        if allow_empty:
            clear_btn = button("پاک کردن", "ghost", size="sm")
            clear_btn.clicked.connect(lambda: self._pick(None, allow_none=True))
            foot.addWidget(clear_btn)
        root.addLayout(foot)
        self._render()

    def _shift(self, delta: int) -> None:
        self._year, self._month = _add_months(self._year, self._month, delta)
        self._render()

    def _render(self) -> None:
        self._title.setText(fmt.fmt_month_year(self._year, self._month))
        first, length = _month_bounds(self._year, self._month)
        offset = _sat_index(first)
        start = first - timedelta(days=offset)
        for i, cell in enumerate(self._cells):
            day = start + timedelta(days=i)
            in_month = 0 <= (day - first).days < length
            _, _, number = fmt.date_parts(day)
            cell.setText(fmt.digits(number))
            cell.setProperty("day", day)
            cell.setProperty("outside", not in_month)
            cell.setProperty("today", day == self._today)
            cell.setProperty("selected", day == self._selected)
            cell.setProperty("weekend", day.weekday() == 4)
            cell.setEnabled(self._max is None or day <= self._max)
            cell.setToolTip(fmt.fmt_date_with_weekday(day))
            repolish(cell)
        self._next.setEnabled(self._max is None or _month_bounds(*_add_months(self._year, self._month, 1))[0] <= self._max)

    def _pick(self, day, allow_none: bool = False) -> None:
        if day is None and not allow_none:
            return
        self.picked.emit(day)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_PageUp:
            self._shift(-1)
        elif event.key() == Qt.Key.Key_PageDown:
            self._shift(1)
        else:
            super().keyPressEvent(event)

    def show_for(self, anchor: QWidget) -> None:
        self.adjustSize()
        size = self.sizeHint()
        global_pos = anchor.mapToGlobal(QPoint(anchor.width() - size.width(), anchor.height() + 6))
        screen = QGuiApplication.screenAt(anchor.mapToGlobal(QPoint(0, 0))) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        x = min(max(global_pos.x(), area.left() + 8), area.right() - size.width() - 8)
        y = global_pos.y()
        if y + size.height() > area.bottom() - 8:
            y = anchor.mapToGlobal(QPoint(0, 0)).y() - size.height() - 6
        self.move(x, max(area.top() + 8, y))
        self.show()


class DateField(QPushButton):
    date_changed = Signal(object)

    def __init__(
        self,
        value: date | None = None,
        allow_empty: bool = False,
        placeholder: str = "انتخاب تاریخ",
        max_date: date | None = None,
        long_format: bool = False,
        size: str | None = None,
    ):
        super().__init__()
        self.setObjectName("DateField")
        if size:
            self.setProperty("size", size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(icons.icon("calendar", t.TEXT_MUTED, 18))
        self.setIconSize(QSize(18, 18))
        self._allow_empty = allow_empty
        self._placeholder = placeholder
        self._max = max_date
        self._long = long_format
        self._value: date | None = None
        self._popup: CalendarPopup | None = None
        self.clicked.connect(self.open_popup)
        self.setToolTip("برای تغییر روز از کلیدهای بالا و پایین استفاده کنید.")
        self.set_date(value if value or allow_empty else date.today(), emit=False)

    def date(self) -> date | None:
        return self._value

    def set_max_date(self, value: date | None) -> None:
        self._max = value

    def set_date(self, value: date | None, emit: bool = True) -> None:
        if value is None and not self._allow_empty:
            return
        if value and self._max and value > self._max:
            value = self._max
        changed = value != self._value
        self._value = value
        self.refresh_text()
        if emit and changed:
            self.date_changed.emit(value)

    def refresh_text(self) -> None:
        if self._value is None:
            self.setText(f"  {self._placeholder}")
        else:
            self.setText("  " + (fmt.fmt_date_with_weekday(self._value) if self._long else fmt.fmt_date(self._value)))
        self.setProperty("empty", self._value is None)
        repolish(self)

    def open_popup(self) -> None:
        self._popup = CalendarPopup(self._value, self._max, self._allow_empty, self)
        self._popup.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        self._popup.picked.connect(lambda d: self.set_date(d))
        self._popup.destroyed.connect(self._popup_closed)
        self.setProperty("open", True)
        repolish(self)
        self._popup.show_for(self)

    def _popup_closed(self) -> None:
        self._popup = None
        self.setProperty("open", False)
        repolish(self)

    def keyPressEvent(self, event):
        key = event.key()
        base = self._value or date.today()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.set_date(base + timedelta(days=1 if key == Qt.Key.Key_Up else -1))
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self._allow_empty:
            self.set_date(None)
        elif key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F4):
            self.open_popup()
        else:
            super().keyPressEvent(event)
