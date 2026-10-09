"""Main application window: sidebar navigation, page header and page stack."""

from __future__ import annotations

import ctypes
import logging
import sys
from datetime import date

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import APP_NAME, APP_NAME_FA
from app.core import formatting as fmt
from app.ui import icons
from app.ui.events import events
from app.ui.pages.activity_entry import ActivityEntryPage
from app.ui.pages.base import BasePage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.history import HistoryPage
from app.ui.pages.projects import ProjectsPage
from app.ui.pages.reports import ReportsPage
from app.ui.pages.settings import SettingsPage
from app.ui.theme import fonts
from app.ui.theme import tokens as t
from app.ui.widgets.common import button, label
from app.ui.widgets.toast import ToastManager

log = logging.getLogger(__name__)

NAV_ITEMS = [
    ("dashboard", "داشبورد", "home"),
    ("entry", "ثبت فعالیت", "paper-plus"),
    ("history", "تاریخچه فعالیت‌ها", "time-circle"),
    ("projects", "پروژه‌ها", "folder"),
    ("reports", "گزارش‌ها", "chart"),
    ("settings", "تنظیمات", "setting"),
]


class NavButton(QAbstractButton):
    """Sidebar navigation item, painted for crisp RTL alignment and a soft active state."""

    def __init__(self, text: str, icon_name: str, shortcut: str = ""):
        super().__init__()
        self.setText(text)
        self._icon = icon_name
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(46)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setToolTip(f"{text}  ({shortcut})" if shortcut else text)
        self.setAccessibleName(text)
        self._hover = False

    def sizeHint(self) -> QSize:
        return QSize(200, 46)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        active = self.isChecked()
        if active or self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(t.ACCENT_SOFT) if active else QColor(t.BG_SURFACE_HOVER))
            p.drawRoundedRect(rect, 10, 10)
        if active:
            p.setBrush(QColor(t.ACCENT_PRIMARY))
            p.drawRoundedRect(QRectF(rect.right() - 3, rect.top() + 12, 3, rect.height() - 24), 1.5, 1.5)
        if self.hasFocus():
            p.setPen(QColor(t.FOCUS_RING))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)

        color = t.TEXT_PRIMARY if active else (t.TEXT_PRIMARY if self._hover else t.TEXT_SECONDARY)
        icon_color = t.ACCENT_TEXT if active else color
        size = 20
        x_icon = self.width() - 16 - size
        p.drawPixmap(int(x_icon), int((self.height() - size) / 2), icons.pixmap(self._icon, icon_color, size))
        font = fonts.font(t.FONT_BODY, QFont.Weight.DemiBold if active else QFont.Weight.Medium)
        p.setFont(font)
        p.setPen(QColor(color))
        text_rect = QRectF(12, 0, x_icon - 12 - 12, self.height())
        p.drawText(text_rect, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), self.text())


class Sidebar(QFrame):
    def __init__(self, on_navigate, on_new):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(t.SIDEBAR_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(4)

        brand = QHBoxLayout()
        brand.setContentsMargins(6, 0, 6, 0)
        brand.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(40))
        logo.setFixedSize(40, 40)
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setFont(fonts.font(17, QFont.Weight.Bold))
        name.setStyleSheet(f"color: {t.TEXT_PRIMARY};")
        names.addWidget(name)
        names.addWidget(label(APP_NAME_FA, "caption"))
        brand.addLayout(names, 1)
        layout.addLayout(brand)
        layout.addSpacing(22)

        new_btn = button("فعالیت جدید", "primary", "plus", tooltip="Ctrl+N")
        new_btn.setMinimumHeight(42)
        new_btn.clicked.connect(on_new)
        layout.addWidget(new_btn)
        layout.addSpacing(18)

        caption = label("منوی اصلی", "caption")
        caption.setContentsMargins(10, 0, 10, 6)
        layout.addWidget(caption)

        self.buttons: dict[str, NavButton] = {}
        for i, (key, text, icon_name) in enumerate(NAV_ITEMS, start=1):
            btn = NavButton(text, icon_name, f"Ctrl+{i}")
            btn.clicked.connect(lambda _=False, k=key: on_navigate(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch(1)

        note = QFrame()
        note.setObjectName("StorageNote")
        nl = QHBoxLayout(note)
        nl.setContentsMargins(12, 10, 12, 10)
        nl.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("shield-done", t.SUCCESS, 20))
        nl.addWidget(ic)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addWidget(label("ذخیره‌سازی محلی", "small"))
        texts.addWidget(label("آفلاین و خصوصی", "caption"))
        nl.addLayout(texts, 1)
        layout.addWidget(note)

    def set_active(self, key: str) -> None:
        for k, btn in self.buttons.items():
            btn.setChecked(k == key)


class Header(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Header")
        self.setFixedHeight(t.HEADER_HEIGHT + 8)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(t.PAGE_MARGIN, 0, t.PAGE_MARGIN, 0)
        layout.setSpacing(12)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addStretch(1)
        self.title = label("", "h2")
        self.subtitle = label("", "small")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        titles.addStretch(1)
        layout.addLayout(titles, 1)
        self.actions = QStackedWidget()
        layout.addWidget(self.actions, 0, Qt.AlignmentFlag.AlignVCenter)

        self.chip = QFrame()
        self.chip.setObjectName("DateChip")
        self.chip.setFixedHeight(36)
        cl = QHBoxLayout(self.chip)
        cl.setContentsMargins(14, 0, 14, 0)
        cl.setSpacing(8)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("calendar", t.ACCENT_TEXT, 16))
        cl.addWidget(ic)
        self.date_label = label("", "small")
        cl.addWidget(self.date_label)
        layout.addSpacing(4)
        layout.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignVCenter)
        self.refresh_date()

    def refresh_date(self) -> None:
        self.date_label.setText(fmt.fmt_date_with_weekday(date.today()))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — {APP_NAME_FA}")
        self.setWindowIcon(icons.app_icon())
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumSize(1120, 700)

        root = QWidget()
        root.setObjectName("Root")
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.sidebar = Sidebar(self.go, lambda: self.open_entry())
        h.addWidget(self.sidebar)

        main = QWidget()
        v = QVBoxLayout(main)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.header = Header()
        v.addWidget(self.header)
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        h.addWidget(main, 1)
        self.setCentralWidget(root)

        self.pages: dict[str, BasePage] = {}
        self._action_bars: dict[str, QWidget] = {}
        for cls in (DashboardPage, ActivityEntryPage, HistoryPage, ProjectsPage, ReportsPage, SettingsPage):
            page = cls(self)
            self.pages[page.key] = page
            self.stack.addWidget(page)
            bar = QWidget()
            bl = QHBoxLayout(bar)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(10)
            bl.addStretch(1)
            for widget in page.header_actions():
                bl.addWidget(widget)
            self.header.actions.addWidget(bar)
            self._action_bars[page.key] = bar

        self.toasts = ToastManager(self.centralWidget())
        events.toast.connect(lambda kind, message, action: self.toasts.show(message, kind, action))
        events.data_changed.connect(self._on_data_changed)

        self._fade: QPropertyAnimation | None = None
        self.current_key = ""
        self._install_shortcuts()
        self._fit_to_screen()
        self.go("dashboard", animate=False)

    # navigation ---------------------------------------------------------------------------

    def go(self, key: str, animate: bool = True) -> BasePage:
        page = self.pages[key]
        self.sidebar.set_active(key)
        self.header.title.setText(page.title)
        self.header.subtitle.setText(page.subtitle)
        self.header.actions.setCurrentWidget(self._action_bars[key])
        if key != self.current_key:
            self.current_key = key
            self.stack.setCurrentWidget(page)
            if animate:
                self._animate(page)
        page.on_show()
        return page

    def _animate(self, page: QWidget) -> None:
        if self._fade is not None:
            self._fade.stop()
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(t.MOTION_OPEN)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: page.setGraphicsEffect(None))
        anim.start()
        self._fade = anim

    def open_entry(self, template: dict | None = None) -> None:
        page = self.go("entry")
        page.start_new(template)

    def show_history(self, **filters) -> None:
        page: HistoryPage = self.pages["history"]
        page.set_filter(**filters)
        if self.current_key == "history":
            page.refresh_now()
        else:
            self.go("history")

    def _on_data_changed(self, topic: str) -> None:
        if topic in ("settings", "all"):
            self.header.refresh_date()

    # shortcuts -------------------------------------------------------------------------------

    def _install_shortcuts(self) -> None:
        def add(seq, slot):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(slot)

        add("Ctrl+N", lambda: self.open_entry())
        for i, (key, _, _) in enumerate(NAV_ITEMS, start=1):
            add(f"Ctrl+{i}", lambda k=key: self.go(k))
        add("Ctrl+F", self._focus_search)
        add("F5", lambda: self.pages[self.current_key].refresh_now())

    def _focus_search(self) -> None:
        page = self.pages["history"] if self.current_key != "projects" else self.pages["projects"]
        if page.key != self.current_key:
            self.go(page.key)
        page.search.setFocus()
        page.search.selectAll()

    # window chrome -------------------------------------------------------------------------

    def _fit_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1360, 860)
            return
        geo = screen.availableGeometry()
        width = min(max(1180, int(geo.width() * 0.86)), geo.width())
        height = min(max(740, int(geo.height() * 0.88)), geo.height())
        self.resize(min(width, 1600), min(height, 1000))
        frame = self.frameGeometry()
        frame.moveCenter(geo.center())
        self.move(frame.topLeft())

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            self._dark_title_bar()

    def _dark_title_bar(self) -> None:
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            dwm = ctypes.windll.dwmapi
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (19 on early Windows 10 builds)
            if dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)) != 0:
                dwm.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
            caption = ctypes.c_int(0x00100B0B)  # COLORREF of BG_APP (0x00BBGGRR)
            dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))
        except (AttributeError, OSError):
            log.debug("Dark title bar is not supported on this system")
