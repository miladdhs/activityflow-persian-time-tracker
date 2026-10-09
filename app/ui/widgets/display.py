"""Display components: stat cards, empty states, color swatches and a pager."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.core import formatting as fmt
from app.ui.theme import tokens as t
from app.ui.widgets.common import Card, IconButton, IconTile, button, label
from app.ui.widgets.inputs import ComboBox


class StatCard(Card):
    def __init__(self, title: str, icon_name: str, color: str = t.ACCENT_PRIMARY):
        super().__init__(padding=t.CARD_PADDING, spacing=t.SPACE_3)
        head = QHBoxLayout()
        head.setSpacing(t.SPACE_3)
        self.title = label(title, "small")
        head.addWidget(self.title, 1, Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(IconTile(icon_name, color, 38, 20))
        self.body.addLayout(head)
        self.value = QLabel("—")
        self.value.setTextFormat(Qt.TextFormat.RichText)
        self.value.setMinimumHeight(40)
        self.body.addWidget(self.value)
        self.note = label("", "caption")
        self.note.setTextFormat(Qt.TextFormat.RichText)
        self.body.addWidget(self.note)
        self.setMinimumHeight(142)

    @staticmethod
    def _big(text: str) -> str:
        return f'<span style="font-size:{t.FONT_DISPLAY - 2}px; font-weight:700; color:{t.TEXT_PRIMARY};">{text}</span>'

    @staticmethod
    def _unit(text: str) -> str:
        return f'<span style="font-size:13px; color:{t.TEXT_SECONDARY};">&nbsp;{text}&nbsp;&nbsp;</span>'

    def set_number(self, value: str, unit: str = "") -> None:
        self.value.setText(self._big(value) + (self._unit(unit) if unit else ""))

    def set_duration(self, minutes: int) -> None:
        parts = fmt.duration_parts(minutes)
        self.value.setText("".join(self._big(v) + self._unit(u) for v, u in parts))

    def set_note(self, text: str, tone: str | None = None) -> None:
        color = {"up": t.SUCCESS, "down": t.DANGER, "accent": t.ACCENT_TEXT}.get(tone or "", t.TEXT_MUTED)
        self.note.setText(f'<span style="color:{color};">{text}</span>')


def delta_note(current: int, previous: int, period: str) -> tuple[str, str | None]:
    if previous <= 0:
        return ("", None) if current <= 0 else (f"شروع خوب {period}", "accent")
    change = (current - previous) / previous
    if abs(change) < 0.005:
        return f"بدون تغییر نسبت به {period}", None
    direction = "بیشتر" if change > 0 else "کمتر"
    return f"{fmt.fmt_percent(abs(change))} {direction} از {period}", "up" if change > 0 else "down"


class EmptyState(QWidget):
    action_clicked = Signal()

    def __init__(self, icon_name: str, title: str, description: str = "", action_text: str = "", action_icon: str | None = "plus"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 40, 24, 40)
        layout.setSpacing(10)
        layout.addStretch(1)
        tile = IconTile(icon_name, t.ACCENT_PRIMARY, 64, 30)
        layout.addWidget(tile, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        self.title = label(title, "h3")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        self.description = label(description, "secondary", wrap=True)
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description.setMaximumWidth(440)
        self.description.setVisible(bool(description))
        # A layout alignment flag would break height-for-width wrapping, so center with stretches.
        centered = QHBoxLayout()
        centered.addStretch(1)
        centered.addWidget(self.description, 100)
        centered.addStretch(1)
        layout.addLayout(centered)
        self.action = button(action_text, "primary", action_icon) if action_text else None
        if self.action:
            layout.addSpacing(8)
            self.action.clicked.connect(self.action_clicked)
            layout.addWidget(self.action, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

    def set_texts(self, title: str, description: str = "", action_text: str | None = None) -> None:
        self.title.setText(title)
        self.description.setText(description)
        self.description.setVisible(bool(description))
        if self.action is not None:
            if action_text is not None:
                self.action.setText(action_text)
            self.action.setVisible(action_text != "")


class ColorSwatch(QAbstractButton):
    def __init__(self, color: str):
        super().__init__()
        self.color = color
        self.setCheckable(True)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(color)
        self.setAccessibleName(f"رنگ {color}")

    def sizeHint(self) -> QSize:
        return QSize(30, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        if self.isChecked() or self.hasFocus():
            p.setPen(QPen(QColor(t.TEXT_PRIMARY if self.isChecked() else t.FOCUS_RING), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rect)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.color))
        inset = 5 if self.isChecked() else 4
        p.drawEllipse(rect.adjusted(inset, inset, -inset, -inset))


class ColorPicker(QWidget):
    color_changed = Signal(str)

    def __init__(self, colors: list[str], current: str | None = None):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._group = QButtonGroup(self)
        self._swatches: dict[str, ColorSwatch] = {}
        for color in colors:
            swatch = ColorSwatch(color)
            swatch.clicked.connect(lambda _=False, c=color: self.color_changed.emit(c))
            self._group.addButton(swatch)
            self._swatches[color.upper()] = swatch
            layout.addWidget(swatch)
        layout.addStretch(1)
        self.set_color(current or colors[0])

    def color(self) -> str:
        checked = self._group.checkedButton()
        return checked.color if checked else next(iter(self._swatches.values())).color

    def set_color(self, color: str) -> None:
        swatch = self._swatches.get((color or "").upper())
        if swatch is None:
            swatch = next(iter(self._swatches.values()))
        swatch.setChecked(True)


class Pager(QWidget):
    page_changed = Signal(int)
    page_size_changed = Signal(int)

    def __init__(self, sizes: tuple[int, ...]):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.summary = label("", "small")
        layout.addWidget(self.summary)
        layout.addStretch(1)
        layout.addWidget(label("تعداد در صفحه", "caption"))
        self.size_combo = ComboBox(size="sm")
        self.size_combo.setMinimumContentsLength(3)
        for s in sizes:
            self.size_combo.addItem(fmt.digits(s), s)
        self.size_combo.currentIndexChanged.connect(lambda _: self.page_size_changed.emit(self.size_combo.currentData()))
        layout.addWidget(self.size_combo)
        layout.addSpacing(8)
        self.prev = IconButton("arrow-right", "صفحه قبل", size=32, icon_px=16)
        self.next = IconButton("arrow-left", "صفحه بعد", size=32, icon_px=16)
        self.page_label = label("", "small")
        self.page_label.setMinimumWidth(70)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prev.clicked.connect(lambda: self.page_changed.emit(self._page - 1))
        self.next.clicked.connect(lambda: self.page_changed.emit(self._page + 1))
        layout.addWidget(self.prev)
        layout.addWidget(self.page_label)
        layout.addWidget(self.next)
        self._page = 1

    def set_page_size(self, size: int) -> None:
        self.size_combo.blockSignals(True)
        index = self.size_combo.findData(size)
        self.size_combo.setCurrentIndex(index if index >= 0 else 1)
        self.size_combo.blockSignals(False)

    def update_state(self, page: int, page_count: int, total: int, page_size: int) -> None:
        self._page = page
        start = 0 if total == 0 else (page - 1) * page_size + 1
        end = min(total, page * page_size)
        self.summary.setText(f"نمایش {fmt.fmt_int(start)} تا {fmt.fmt_int(end)} از {fmt.fmt_int(total)} فعالیت")
        self.page_label.setText(f"{fmt.digits(page)} از {fmt.digits(page_count)}")
        self.prev.setEnabled(page > 1)
        self.next.setEnabled(page < page_count)
