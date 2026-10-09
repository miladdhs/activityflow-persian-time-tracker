"""Small reusable building blocks shared by all screens."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui import icons
from app.ui.theme import tokens as t


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def label(text: str = "", role: str | None = None, wrap: bool = False, selectable: bool = False) -> QLabel:
    lbl = QLabel(text)
    if role:
        lbl.setProperty("role", role)
    lbl.setWordWrap(wrap)
    if selectable:
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lbl


def hbox(*items, spacing: int = t.SPACE_3, margins=(0, 0, 0, 0)) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    _fill(layout, items)
    return layout


def vbox(*items, spacing: int = t.SPACE_3, margins=(0, 0, 0, 0)) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    _fill(layout, items)
    return layout


def _fill(layout, items: Iterable) -> None:
    for item in items:
        if item is None:
            layout.addStretch(1)
        elif isinstance(item, int):
            layout.addSpacing(item)
        elif isinstance(item, QLayout):
            layout.addLayout(item)
        else:
            layout.addWidget(item)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, padding: int = t.CARD_PADDING, spacing: int = t.SPACE_4):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(spacing)


class SectionCard(Card):
    """A card with a title row (title, optional subtitle, actions on the far side)."""

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None, padding: int = t.CARD_PADDING):
        super().__init__(parent, padding)
        self.head = head = QHBoxLayout()
        head.setSpacing(t.SPACE_3)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title_label = label(title, "h3")
        titles.addWidget(self.title_label)
        self.subtitle_label = label(subtitle, "small")
        self.subtitle_label.setVisible(bool(subtitle))
        titles.addWidget(self.subtitle_label)
        head.addLayout(titles, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(t.SPACE_2)
        head.addLayout(self.actions)
        self.body.addLayout(head)

    def add_action(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))


class Divider(QFrame):
    def __init__(self, vertical: bool = False):
        super().__init__()
        self.setObjectName("Divider")
        if vertical:
            self.setFixedWidth(1)
        else:
            self.setFixedHeight(1)


class Button(QPushButton):
    """Push button that keeps a comfortable gap between its icon and text."""

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API
        super().setText(f"  {text}" if text and not self.icon().isNull() else text)

    def label_text(self) -> str:
        return self.text().strip()


def button(
    text: str,
    variant: str = "secondary",
    icon_name: str | None = None,
    size: str | None = None,
    tooltip: str = "",
    parent: QWidget | None = None,
) -> QPushButton:
    btn = Button(parent)
    btn.setProperty("variant", variant)
    if size:
        btn.setProperty("size", size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_name:
        set_button_icon(btn, icon_name, variant, 16 if size == "sm" else 18)
    btn.setText(text)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def set_button_icon(btn: QPushButton, icon_name: str, variant: str = "secondary", size: int = 18) -> None:
    color = {
        "primary": t.TEXT_PRIMARY,
        "danger": t.DANGER,
        "danger-solid": "#1B0A10",
        "ghost": t.TEXT_SECONDARY,
    }.get(variant, t.TEXT_PRIMARY)
    btn.setIcon(icons.icon(icon_name, color, size, active=t.TEXT_PRIMARY if variant == "ghost" else color))
    btn.setIconSize(QSize(size, size))


class IconButton(QToolButton):
    def __init__(
        self,
        icon_name: str,
        tooltip: str,
        tone: str = "default",
        size: int = 34,
        icon_px: int = 18,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.setProperty("tone", tone)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        hover = t.DANGER if tone == "danger" else t.TEXT_PRIMARY
        self._icon_args = (icon_name, icon_px, hover)
        self.setIcon(icons.icon(icon_name, t.TEXT_SECONDARY, icon_px, active=hover))
        self.setIconSize(QSize(icon_px, icon_px))
        self.setAutoRaise(True)

    def enterEvent(self, event):
        name, px, hover = self._icon_args
        self.setIcon(icons.icon(name, hover, px))
        super().enterEvent(event)

    def leaveEvent(self, event):
        name, px, hover = self._icon_args
        self.setIcon(icons.icon(name, t.TEXT_SECONDARY, px, active=hover))
        super().leaveEvent(event)


class Badge(QLabel):
    def __init__(self, text: str = "", kind: str = "neutral"):
        super().__init__(text)
        self.setProperty("badge", kind)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_kind(self, text: str, kind: str) -> None:
        self.setText(text)
        self.setProperty("badge", kind)
        repolish(self)


STATUS_BADGE = {"active": "success", "paused": "warning", "completed": "info", "archived": "neutral"}


class ColorDot(QWidget):
    def __init__(self, color: str = t.ACCENT_PRIMARY, size: int = 10, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(size, size)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(self.rect())


class IconTile(QWidget):
    """An icon on a softly tinted rounded square."""

    def __init__(self, icon_name: str, color: str = t.ACCENT_PRIMARY, size: int = 40, icon_px: int = 20):
        super().__init__()
        self.setFixedSize(size, size)
        self._icon = icon_name
        self._color = color
        self._px = icon_px

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(self._color)
        bg.setAlphaF(0.14)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(self.rect()), 10, 10)
        pm = icons.pixmap(self._icon, self._color, self._px)
        x = (self.width() - self._px) / 2
        y = (self.height() - self._px) / 2
        p.drawPixmap(int(x), int(y), pm)


class SegmentedControl(QFrame):
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], current: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Segmented")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for key, text in options:
            btn = QPushButton(text)
            btn.setProperty("seg", True)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self._on_click(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            layout.addWidget(btn)
        self._current = None
        self.set_current(current or options[0][0], emit=False)

    def _on_click(self, key: str) -> None:
        if key != self._current:
            self._current = key
            self.changed.emit(key)

    def current(self) -> str:
        return self._current

    def set_current(self, key: str, emit: bool = False) -> None:
        if key not in self._buttons:
            return
        self._buttons[key].setChecked(True)
        changed = key != self._current
        self._current = key
        if emit and changed:
            self.changed.emit(key)

    def set_label(self, key: str, text: str) -> None:
        if key in self._buttons:
            self._buttons[key].setText(text)


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 24)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(t.MOTION_STATE)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _get_knob(self) -> float:
        return self._pos

    def _set_knob(self, value: float) -> None:
        self._pos = value
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - Qt API
        super().setChecked(checked)
        self._pos = 1.0 if checked else 0.0
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        off, on = QColor("#2A2A3A"), QColor(t.ACCENT_PRIMARY)
        track = QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
        )
        p.setBrush(track)
        p.setPen(QPen(QColor(t.FOCUS_RING), 1.5) if self.hasFocus() else Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        d = self.height() - 6
        travel = self.width() - d - 6
        progress = 1 - self._pos if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self._pos
        x = 3 + travel * progress
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 3, d, d))


class Menu(QMenu):
    """Context/popup menu with rounded translucent corners and icon helpers."""

    def __init__(self, parent: QWidget | None = None, title: str = ""):
        super().__init__(title, parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def item(self, text: str, callback, icon_name: str | None = None, danger: bool = False, enabled: bool = True) -> QAction:
        color = t.DANGER if danger else t.TEXT_SECONDARY
        action = QAction(icons.icon(icon_name, color, 18), text, self) if icon_name else QAction(text, self)
        action.setEnabled(enabled)
        action.triggered.connect(lambda _=False: callback())
        self.addAction(action)
        return action

    def submenu(self, text: str, icon_name: str | None = None) -> Menu:
        sub = Menu(self, text)
        if icon_name:
            sub.setIcon(icons.icon(icon_name, t.TEXT_SECONDARY, 18))
        self.addMenu(sub)
        return sub


def scroll_page(content: QWidget) -> QScrollArea:
    content.setObjectName("ScrollContent")
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(content)
    area.viewport().setAutoFillBackground(False)
    content.setAutoFillBackground(False)
    return area


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())
