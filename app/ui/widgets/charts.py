"""Lightweight, hand-painted charts with hover tooltips (no extra dependencies)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from app.core import formatting as fmt
from app.ui.theme import tokens as t
from app.ui.theme.fonts import font
from app.ui.widgets.common import ColorDot, clear_layout


@dataclass
class BarPoint:
    label: str
    tooltip: str
    value: int
    highlight: bool = False


def _nice_step(max_minutes: int) -> int:
    """Gridline step in minutes, chosen so there are ~3-4 lines."""
    for step in (15, 30, 60, 120, 180, 240, 360, 480, 600, 1200, 2400, 6000, 12000, 30000):
        if max_minutes / step <= 4:
            return step
    return 60000


def _axis_label(minutes: int) -> str:
    if minutes % 60 == 0:
        return fmt.digits(f"{minutes // 60}س")
    return fmt.digits(f"{minutes}د")


class BarChart(QWidget):
    def __init__(self, parent: QWidget | None = None, height: int = 220):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._points: list[BarPoint] = []
        self._hover = -1
        self._bars: list[QRectF] = []
        self._empty_text = "داده‌ای برای نمایش وجود ندارد"

    def set_data(self, points: list[BarPoint]) -> None:
        self._points = points
        self._hover = -1
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(480, self.minimumHeight())

    def _rtl(self) -> bool:
        return self.layoutDirection() == Qt.LayoutDirection.RightToLeft

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setLayoutDirection(self.layoutDirection())
        small = font(11)
        fm = QFontMetrics(small)
        p.setFont(small)

        n = len(self._points)
        max_value = max((pt.value for pt in self._points), default=0)
        step = _nice_step(max(max_value, 60))
        top_value = max(step, math.ceil(max(max_value, 1) / step) * step)

        axis_w = fm.horizontalAdvance(_axis_label(top_value)) + 12
        label_h = fm.height() + 10
        plot = QRectF(0, 8, self.width(), self.height() - 8 - label_h)
        if self._rtl():
            plot.setRight(self.width() - axis_w)
        else:
            plot.setLeft(axis_w)

        # gridlines
        p.setPen(QPen(QColor(t.BORDER_SUBTLE), 1, Qt.PenStyle.DashLine))
        lines = int(top_value / step)
        for i in range(lines + 1):
            y = plot.bottom() - plot.height() * (i * step / top_value)
            p.setPen(QPen(QColor(t.BORDER_SUBTLE), 1, Qt.PenStyle.SolidLine if i == 0 else Qt.PenStyle.DashLine))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(t.TEXT_MUTED))
            text_rect = QRectF(plot.right() + 6, y - 9, axis_w - 6, 18) if self._rtl() else QRectF(0, y - 9, axis_w - 6, 18)
            p.drawText(text_rect, (Qt.AlignmentFlag.AlignRight if self._rtl() else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter, _axis_label(i * step))

        self._bars = []
        if n == 0 or max_value == 0:
            p.setPen(QColor(t.TEXT_MUTED))
            p.setFont(font(12))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, self._empty_text)
            if n == 0:
                return

        slot = plot.width() / n
        bar_w = max(4.0, min(36.0, slot * 0.56))
        label_every = max(1, math.ceil(n / max(1, plot.width() / 34)))
        for i, pt in enumerate(self._points):
            index = n - 1 - i if self._rtl() else i
            cx = plot.left() + slot * index + slot / 2
            h = 0 if top_value == 0 else plot.height() * pt.value / top_value
            h = max(h, 3.0) if pt.value else 2.0
            rect = QRectF(cx - bar_w / 2, plot.bottom() - h, bar_w, h)
            self._bars.append(QRectF(cx - slot / 2, plot.top(), slot, plot.height() + label_h))

            color = QColor(t.ACCENT_PRIMARY)
            if not pt.value:
                color = QColor(t.BORDER_STRONG)
            elif i == self._hover:
                color = QColor(t.ACCENT_HOVER)
            elif not pt.highlight:
                color.setAlphaF(0.55)
            if i == self._hover:
                hover_bg = QColor(t.TEXT_PRIMARY)
                hover_bg.setAlphaF(0.035)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(hover_bg)
                p.drawRoundedRect(QRectF(cx - slot / 2 + 2, plot.top(), slot - 4, plot.height()), 6, 6)

            radius = min(6.0, bar_w / 2, h / 2)
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)
            # square off the bottom corners
            path.addRect(QRectF(rect.left(), rect.bottom() - radius, rect.width(), radius))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawPath(path.simplified())

            if i % label_every == 0 or pt.highlight:
                p.setPen(QColor(t.TEXT_PRIMARY if pt.highlight else t.TEXT_MUTED))
                p.drawText(QRectF(cx - slot, plot.bottom() + 6, slot * 2, label_h - 6), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, pt.label)

    def mouseMoveEvent(self, event):
        pos = event.position()
        hover = -1
        for i, rect in enumerate(self._bars):
            if rect.contains(pos):
                hover = i
                break
        if hover != self._hover:
            self._hover = hover
            self.update()
        if hover >= 0:
            pt = self._points[hover]
            QToolTip.showText(event.globalPosition().toPoint(), f"{pt.tooltip}\n{fmt.fmt_duration(pt.value)}", self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, _):
        self._hover = -1
        QToolTip.hideText()
        self.update()


@dataclass
class Segment:
    name: str
    color: str
    value: int


class DonutChart(QWidget):
    def __init__(self, size: int = 168, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFixedSize(size, size)
        self._segments: list[Segment] = []
        self._hover = -1
        self._center_value = ""
        self._center_caption = ""

    def set_data(self, segments: list[Segment], center_value: str, center_caption: str) -> None:
        self._segments = [s for s in segments if s.value > 0]
        self._center_value = center_value
        self._center_caption = center_caption
        self._hover = -1
        self.update()

    def _angles(self):
        total = sum(s.value for s in self._segments)
        start = 90.0
        for i, seg in enumerate(self._segments):
            span = 360.0 * seg.value / total if total else 0
            yield i, seg, start, span
            start -= span

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        thickness = 16
        rect = QRectF(thickness / 2 + 4, thickness / 2 + 4, self.width() - thickness - 8, self.height() - thickness - 8)

        track = QPen(QColor(t.BG_ELEVATED), thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        p.setPen(track)
        p.drawArc(rect, 0, 360 * 16)

        gap = 1.6 if len(self._segments) > 1 else 0
        for i, seg, start, span in self._angles():
            if span <= 0:
                continue
            width = thickness + (4 if i == self._hover else 0)
            color = QColor(seg.color)
            if self._hover not in (-1, i):
                color.setAlphaF(0.45)
            p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            draw_span = max(span - gap, 0.6)
            p.drawArc(rect, int((start - gap / 2) * 16), int(-draw_span * 16))

        p.setPen(QColor(t.TEXT_PRIMARY))
        p.setFont(font(19, QFont.Weight.Bold))
        center = QRectF(0, self.height() / 2 - 22, self.width(), 26)
        p.drawText(center, Qt.AlignmentFlag.AlignCenter, self._center_value)
        p.setPen(QColor(t.TEXT_MUTED))
        p.setFont(font(11))
        p.drawText(QRectF(0, self.height() / 2 + 6, self.width(), 18), Qt.AlignmentFlag.AlignCenter, self._center_caption)

    def mouseMoveEvent(self, event):
        pos = event.position()
        c = QPointF(self.width() / 2, self.height() / 2)
        dx, dy = pos.x() - c.x(), c.y() - pos.y()
        dist = math.hypot(dx, dy)
        outer = self.width() / 2 - 2
        hover = -1
        if outer - 26 <= dist <= outer:
            angle = math.degrees(math.atan2(dy, dx))
            for i, _seg, start, span in self._angles():
                a = (start - angle) % 360
                if 0 <= a <= span:
                    hover = i
                    break
        if hover != self._hover:
            self._hover = hover
            self.update()
        if hover >= 0:
            seg = self._segments[hover]
            total = sum(s.value for s in self._segments)
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"{seg.name}\n{fmt.fmt_duration(seg.value)} · {fmt.fmt_percent(seg.value / total)}",
                self,
            )
        else:
            QToolTip.hideText()

    def leaveEvent(self, _):
        self._hover = -1
        QToolTip.hideText()
        self.update()


class Legend(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

    def set_data(self, segments: list[Segment]) -> None:
        clear_layout(self._layout)
        total = sum(s.value for s in segments) or 1
        for seg in segments:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(ColorDot(seg.color, 8))
            name = QLabel(seg.name)
            name.setProperty("role", "small")
            name.setStyleSheet(f"color: {t.TEXT_PRIMARY};")
            name.setMinimumWidth(40)
            row.addWidget(name, 1)
            value = QLabel(f"{fmt.fmt_clock(seg.value)}  ·  {fmt.fmt_percent(seg.value / total)}")
            value.setProperty("role", "caption")
            row.addWidget(value)
            self._layout.addLayout(row)
        self._layout.addStretch(1)


class HBarList(QWidget):
    """Rows of «name — value» with a thin proportional bar underneath."""

    ROW_H = 46

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._rows: list[Segment] = []
        self._hover = -1
        self._empty_text = "داده‌ای برای نمایش وجود ندارد"

    def set_data(self, rows: list[Segment]) -> None:
        self._rows = rows
        self.setMinimumHeight(max(80, len(rows) * self.ROW_H))
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(320, max(80, len(self._rows) * self.ROW_H))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setLayoutDirection(self.layoutDirection())
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        if not self._rows:
            p.setPen(QColor(t.TEXT_MUTED))
            p.setFont(font(12))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._empty_text)
            return
        top_value = max(r.value for r in self._rows) or 1
        total = sum(r.value for r in self._rows) or 1
        w = self.width()
        for i, row in enumerate(self._rows):
            y = i * self.ROW_H
            p.setFont(font(13, QFont.Weight.Medium))
            p.setPen(QColor(t.TEXT_PRIMARY))
            name_rect = QRectF(0, y + 2, w, 22)
            p.drawText(name_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter if rtl else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, row.name)
            p.setFont(font(12))
            p.setPen(QColor(t.TEXT_SECONDARY))
            value_text = f"{fmt.fmt_clock(row.value)}  ·  {fmt.fmt_percent(row.value / total)}"
            p.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter if rtl else Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, value_text)

            track = QRectF(0, y + 30, w, 6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(t.BG_ELEVATED))
            p.drawRoundedRect(track, 3, 3)
            fill_w = max(6.0, w * row.value / top_value) if row.value else 0
            fill = QRectF(w - fill_w if rtl else 0, y + 30, fill_w, 6)
            color = QColor(row.color)
            if self._hover not in (-1, i):
                color.setAlphaF(0.5)
            p.setBrush(color)
            p.drawRoundedRect(fill, 3, 3)

    def mouseMoveEvent(self, event):
        hover = int(event.position().y() // self.ROW_H)
        hover = hover if 0 <= hover < len(self._rows) else -1
        if hover != self._hover:
            self._hover = hover
            self.update()
        if hover >= 0:
            row = self._rows[hover]
            QToolTip.showText(event.globalPosition().toPoint(), f"{row.name}\n{fmt.fmt_duration(row.value)}", self)

    def leaveEvent(self, _):
        self._hover = -1
        QToolTip.hideText()
        self.update()
