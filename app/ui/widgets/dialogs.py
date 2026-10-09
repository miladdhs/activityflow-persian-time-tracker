"""Modal dialogs: a themed frameless base, confirmation and simple prompts."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import AppError
from app.ui.theme import tokens as t
from app.ui.widgets.common import IconButton, IconTile, button, label


class _Backdrop(QWidget):
    """Dims the main window behind a modal dialog."""

    def __init__(self, host: QWidget):
        super().__init__(host)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(host.rect())
        self.show()
        self.raise_()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(4, 4, 8, 150))


class BaseDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, subtitle: str = "", width: int = 520):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._drag_from: QPoint | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        self.frame = QFrame()
        self.frame.setObjectName("DialogFrame")
        self.frame.setFixedWidth(width)
        shadow = QGraphicsDropShadowEffect(self.frame)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.frame.setGraphicsEffect(shadow)
        outer.addWidget(self.frame)

        root = QVBoxLayout(self.frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QWidget()
        head = QHBoxLayout(self.header)
        head.setContentsMargins(24, 20, 16, 8)
        head.setSpacing(12)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        self.title_label = label(title, "h3")
        titles.addWidget(self.title_label)
        self.subtitle_label = label(subtitle, "small", wrap=True)
        self.subtitle_label.setVisible(bool(subtitle))
        titles.addWidget(self.subtitle_label)
        head.addLayout(titles, 1)
        close = IconButton("close", "بستن (Esc)", size=32, icon_px=18)
        close.clicked.connect(self.reject)
        close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(self.header)

        body_holder = QWidget()
        self.body = QVBoxLayout(body_holder)
        self.body.setContentsMargins(24, 12, 24, 20)
        self.body.setSpacing(t.SPACE_4)
        root.addWidget(body_holder, 1)

        self.footer = QFrame()
        self.footer.setObjectName("DialogFooter")
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(24, 14, 24, 16)
        self.footer_layout.setSpacing(t.SPACE_2)
        self.footer_layout.addStretch(1)
        root.addWidget(self.footer)

        self._backdrop: _Backdrop | None = None
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(t.MOTION_OPEN)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    def add_button(self, text: str, variant: str = "secondary", icon_name: str | None = None) -> QPushButton:
        btn = button(text, variant, icon_name)
        btn.setAutoDefault(False)
        self.footer_layout.addWidget(btn)
        return btn

    def show_error(self, exc: Exception) -> None:
        message = exc.message if isinstance(exc, AppError) else "عملیات با خطا مواجه شد."
        MessageDialog.error(self, message)

    # window behavior ----------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        host = self.parentWidget().window() if self.parentWidget() else None
        if host is not None and self._backdrop is None and host.isVisible():
            self._backdrop = _Backdrop(host)
        self.adjustSize()
        if host is not None:
            geo = host.frameGeometry()
            self.move(geo.center() - self.rect().center())
        self.setWindowOpacity(0.0)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def done(self, result: int) -> None:
        if self._backdrop is not None:
            self._backdrop.deleteLater()
            self._backdrop = None
        super().done(result)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.header.geometry().contains(
            self.frame.mapFrom(self, event.position().toPoint())
        ):
            self._drag_from = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_from is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_from)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_from = None
        super().mouseReleaseEvent(event)


class MessageDialog(BaseDialog):
    TONES = {
        "danger": ("danger", t.DANGER),
        "warning": ("info-circle", t.WARNING),
        "info": ("info-circle", t.INFO),
        "success": ("tick-square", t.SUCCESS),
        "accent": ("info-circle", t.ACCENT_PRIMARY),
    }

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        message: str,
        confirm_text: str = "متوجه شدم",
        cancel_text: str | None = None,
        tone: str = "info",
        confirm_variant: str = "primary",
        details: str = "",
    ):
        super().__init__(parent, title, width=460)
        self.subtitle_label.hide()
        icon_name, color = self.TONES.get(tone, self.TONES["info"])
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(IconTile(icon_name, color, 44, 22), 0, Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(8)
        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {t.TEXT_SECONDARY}; line-height: 150%;")
        texts.addWidget(msg)
        if details:
            extra = label(details, "caption", wrap=True)
            extra.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            texts.addWidget(extra)
        row.addLayout(texts, 1)
        self.body.addLayout(row)

        if cancel_text:
            cancel = self.add_button(cancel_text, "secondary")
            cancel.clicked.connect(self.reject)
        ok = self.add_button(confirm_text, confirm_variant)
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
        ok.setFocus()

    @classmethod
    def confirm(
        cls,
        parent: QWidget | None,
        title: str,
        message: str,
        confirm_text: str = "تأیید",
        danger: bool = True,
        details: str = "",
    ) -> bool:
        dialog = cls(
            parent,
            title,
            message,
            confirm_text=confirm_text,
            cancel_text="انصراف",
            tone="danger" if danger else "accent",
            confirm_variant="danger-solid" if danger else "primary",
            details=details,
        )
        return dialog.exec() == QDialog.DialogCode.Accepted

    @classmethod
    def error(cls, parent: QWidget | None, message: str, title: str = "عملیات انجام نشد") -> None:
        cls(parent, title, message, tone="danger").exec()

    @classmethod
    def info(cls, parent: QWidget | None, title: str, message: str, details: str = "") -> None:
        cls(parent, title, message, tone="success", details=details).exec()
