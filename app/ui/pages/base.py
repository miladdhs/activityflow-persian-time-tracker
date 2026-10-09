from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.core.errors import AppError
from app.ui.events import events
from app.ui.theme import tokens as t
from app.ui.widgets.common import scroll_page
from app.ui.widgets.dialogs import MessageDialog

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow

log = logging.getLogger(__name__)


class BasePage(QWidget):
    key = ""
    title = ""
    subtitle = ""
    topics: set[str] = set()
    scrollable = True

    def __init__(self, window: MainWindow):
        super().__init__()
        self.window_ = window
        self._dirty = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.content = QWidget()
        self.layout_ = QVBoxLayout(self.content)
        m = t.PAGE_MARGIN
        self.layout_.setContentsMargins(m, 24, m, m)
        self.layout_.setSpacing(t.SPACE_6)
        outer.addWidget(scroll_page(self.content) if self.scrollable else self.content)
        events.data_changed.connect(self._on_data_changed)

    def header_actions(self) -> list[QWidget]:
        return []

    def _on_data_changed(self, topic: str) -> None:
        if topic == "all" or topic in self.topics:
            self._dirty = True
            if self.isVisible():
                self.refresh_now()

    def on_show(self) -> None:
        if self._dirty:
            self.refresh_now()

    def refresh_now(self) -> None:
        self._dirty = False
        try:
            self.refresh()
        except AppError as exc:
            MessageDialog.error(self, exc.message)
        except Exception:  # noqa: BLE001 - keep the UI alive and log the cause
            log.exception("Refreshing page %s failed", self.key)
            MessageDialog.error(self, "بارگذاری اطلاعات این صفحه با خطا مواجه شد. جزئیات در فایل گزارش خطا ذخیره شد.")

    def refresh(self) -> None:
        pass
