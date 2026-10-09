"""A themed, read-only data table built on QTableView."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)

from app.ui.theme import tokens as t
from app.ui.widgets.inputs import dot_icon


@dataclass
class Column:
    title: str
    text: Callable[[Any], str] = lambda row: ""
    width: int | None = None  # None → stretch
    align: str = "start"  # start | center | end
    color: Callable[[Any], str | None] | None = None
    tooltip: Callable[[Any], str] | None = None
    muted: Callable[[Any], bool] | None = None
    sort_key: str | None = None
    actions: bool = False


_ALIGN = {
    "start": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    "center": Qt.AlignmentFlag.AlignCenter,
    "end": Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
}


class RowsModel(QAbstractTableModel):
    def __init__(self, columns: list[Column]):
        super().__init__()
        self.columns = columns
        self.rows: list[Any] = []

    def set_rows(self, rows: list[Any]) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent=None):  # noqa: N802
        return 0 if parent is not None and parent.isValid() else len(self.rows)

    def columnCount(self, parent=None):  # noqa: N802
        return 0 if parent is not None and parent.isValid() else len(self.columns)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal:
            col = self.columns[section]
            if role == Qt.ItemDataRole.DisplayRole:
                return col.title
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return int(_ALIGN[col.align])
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        col = self.columns[index.column()]
        if col.actions:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return col.text(row)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(_ALIGN[col.align])
        if role == Qt.ItemDataRole.DecorationRole and col.color:
            color = col.color(row)
            return dot_icon(color) if color else None
        if role == Qt.ItemDataRole.ToolTipRole:
            if col.tooltip:
                return col.tooltip(row)
            return None
        if role == Qt.ItemDataRole.ForegroundRole:
            if col.muted and col.muted(row):
                return QColor(t.TEXT_MUTED)
            return QColor(t.TEXT_PRIMARY)
        return None


class _RowDelegate(QStyledItemDelegate):
    def __init__(self, view: DataTable):
        super().__init__(view)
        self._view = view

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        rect = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = index.row() == self._view.hover_row
        if selected or hovered:
            color = QColor(t.ACCENT_SOFT) if selected else QColor(t.BG_SURFACE_HOVER)
            painter.fillRect(rect, color)
        painter.setPen(QColor(t.BORDER_SUBTLE))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.restore()

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.state &= ~QStyle.StateFlag.State_Selected
        opt.state &= ~QStyle.StateFlag.State_HasFocus
        opt.state &= ~QStyle.StateFlag.State_MouseOver
        opt.rect = QRect(rect.adjusted(12, 0, -12, 0))
        opt.decorationSize = opt.decorationSize.boundedTo(rect.size())
        super().paint(painter, opt, index)


class DataTable(QTableView):
    row_activated = Signal(object)
    context_requested = Signal(object, object)  # row, global QPoint
    sort_requested = Signal(str)

    def __init__(self, columns: list[Column], row_height: int = 52, parent: QWidget | None = None):
        super().__init__(parent)
        self.columns = columns
        self.model_ = RowsModel(columns)
        self.setModel(self.model_)
        self.hover_row = -1
        self._row_widget_factory: Callable[[Any], QWidget] | None = None

        self.setItemDelegate(_RowDelegate(self))
        self.setMouseTracking(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setAlternatingRowColors(False)
        self.setCornerButtonEnabled(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context)
        self.activated.connect(lambda idx: self._emit_row(self.row_activated, idx))

        vh = self.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vh.setDefaultSectionSize(row_height)

        hh = self.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setFixedHeight(44)
        hh.setSectionsClickable(True)
        hh.setMinimumSectionSize(60)
        hh.sectionClicked.connect(self._on_header_click)
        for i, col in enumerate(columns):
            if col.width is None:
                hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                hh.resizeSection(i, col.width)
        self.model_.modelReset.connect(self._install_row_widgets)

    # rows ---------------------------------------------------------------------

    def set_rows(self, rows: list[Any]) -> None:
        self.hover_row = -1
        self.model_.set_rows(rows)

    def rows(self) -> list[Any]:
        return self.model_.rows

    def current_row(self):
        idx = self.currentIndex()
        return self.model_.rows[idx.row()] if idx.isValid() and idx.row() < len(self.model_.rows) else None

    def set_row_widgets(self, factory: Callable[[Any], QWidget]) -> None:
        self._row_widget_factory = factory

    def _install_row_widgets(self) -> None:
        if not self._row_widget_factory:
            return
        action_cols = [i for i, c in enumerate(self.columns) if c.actions]
        for col in action_cols:
            for r, row in enumerate(self.model_.rows):
                holder = QWidget()
                layout = QHBoxLayout(holder)
                layout.setContentsMargins(8, 0, 8, 0)
                layout.setSpacing(2)
                layout.addStretch(1)
                layout.addWidget(self._row_widget_factory(row))
                layout.addStretch(1)
                self.setIndexWidget(self.model_.index(r, col), holder)

    # sorting -------------------------------------------------------------------

    def set_sort_indicator(self, sort_key: str | None, descending: bool) -> None:
        hh = self.horizontalHeader()
        for i, col in enumerate(self.columns):
            if col.sort_key and col.sort_key == sort_key:
                hh.setSortIndicatorShown(True)
                hh.setSortIndicator(i, Qt.SortOrder.DescendingOrder if descending else Qt.SortOrder.AscendingOrder)
                return
        hh.setSortIndicatorShown(False)

    def _on_header_click(self, section: int) -> None:
        key = self.columns[section].sort_key
        if key:
            self.sort_requested.emit(key)
        else:
            self.horizontalHeader().setSortIndicatorShown(self.horizontalHeader().isSortIndicatorShown())

    # interaction -----------------------------------------------------------

    def _emit_row(self, signal, index) -> None:
        if index.isValid() and index.row() < len(self.model_.rows):
            signal.emit(self.model_.rows[index.row()])

    def _on_context(self, pos) -> None:
        index = self.indexAt(pos)
        if index.isValid():
            self.selectRow(index.row())
            self.context_requested.emit(self.model_.rows[index.row()], self.viewport().mapToGlobal(pos))

    def mouseMoveEvent(self, event):
        row = self.rowAt(int(event.position().y()))
        if row != self.hover_row:
            self.hover_row = row
            self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hover_row = -1
        self.viewport().update()
        super().leaveEvent(event)

    def fit_height(self, max_rows: int | None = None) -> None:
        """Size the table to its rows (for tables embedded in scrolling pages)."""
        count = len(self.model_.rows) if max_rows is None else min(len(self.model_.rows), max_rows)
        height = self.horizontalHeader().height() + count * self.verticalHeader().defaultSectionSize() + 4
        self.setFixedHeight(max(height, self.horizontalHeader().height() + 4))
