"""Application style sheet, generated from design tokens."""

from __future__ import annotations

from app.ui.icons import icon_file
from app.ui.theme import tokens as t
from app.ui.theme.tokens import rgba


def build_stylesheet() -> str:
    chevron = icon_file("arrow-down", t.TEXT_SECONDARY)
    chevron_up = icon_file("arrow-up", t.TEXT_SECONDARY)
    check = icon_file("check", "#FFFFFF")

    return f"""
* {{
    font-family: "Vazirmatn", "Segoe UI", "Tahoma";
}}
QWidget {{
    color: {t.TEXT_PRIMARY};
    font-size: {t.FONT_BODY}px;
    selection-background-color: {rgba(t.ACCENT_PRIMARY, 0.45)};
    selection-color: {t.TEXT_PRIMARY};
}}
QMainWindow, #AppRoot, #ContentArea {{
    background: {t.BG_APP};
}}
QDialog {{
    background: transparent;
}}
QLabel {{
    background: transparent;
}}

/* ---------- typography ---------- */
QLabel[role="display"] {{ font-size: {t.FONT_DISPLAY}px; font-weight: 700; }}
QLabel[role="h1"] {{ font-size: {t.FONT_H1}px; font-weight: 700; }}
QLabel[role="h2"] {{ font-size: {t.FONT_H2}px; font-weight: 600; }}
QLabel[role="h3"] {{ font-size: {t.FONT_H3}px; font-weight: 600; }}
QLabel[role="medium"] {{ font-weight: 500; }}
QLabel[role="secondary"] {{ color: {t.TEXT_SECONDARY}; }}
QLabel[role="muted"] {{ color: {t.TEXT_MUTED}; }}
QLabel[role="small"] {{ font-size: {t.FONT_SMALL}px; color: {t.TEXT_SECONDARY}; }}
QLabel[role="caption"] {{ font-size: {t.FONT_CAPTION}px; color: {t.TEXT_MUTED}; }}
QLabel[role="label"] {{ font-size: 13px; font-weight: 500; color: {t.TEXT_SECONDARY}; }}
QLabel[role="error"] {{ font-size: {t.FONT_SMALL}px; color: {t.DANGER}; }}
QLabel[role="accent"] {{ color: {t.ACCENT_TEXT}; }}

/* ---------- layout surfaces ---------- */
#Sidebar {{
    background: {t.BG_SIDEBAR};
    border: none;
    border-left: 1px solid {t.BORDER_SUBTLE};
}}
#Header {{
    background: {t.BG_APP};
    border: none;
    border-bottom: 1px solid {t.BORDER_SUBTLE};
}}
#Card {{
    background: {t.BG_SURFACE};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: {t.RADIUS_LG}px;
}}
#Card[interactive="true"]:hover {{
    background: {t.BG_SURFACE_HOVER};
    border-color: {t.BORDER_STRONG};
}}
#SoftPanel {{
    background: {t.BG_INPUT};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: {t.RADIUS_MD}px;
}}
#StorageNote {{
    background: {t.BG_SURFACE};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: {t.RADIUS_LG}px;
}}
#DialogFrame {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: {t.RADIUS_XL}px;
}}
#DialogFooter {{
    background: transparent;
    border-top: 1px solid {t.BORDER_SUBTLE};
}}
#Divider {{
    background: {t.BORDER_SUBTLE};
    border: none;
}}
#DateChip {{
    background: {t.BG_SURFACE};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: 17px;
}}
QScrollArea, QScrollArea > QWidget > QWidget#ScrollContent {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget#qt_scrollarea_viewport {{
    background: transparent;
}}

/* ---------- buttons ---------- */
QPushButton {{
    min-height: 42px;
    padding: 0 18px;
    border-radius: {t.RADIUS_MD}px;
    font-size: {t.FONT_BUTTON}px;
    font-weight: 600;
    border: 1px solid {t.BORDER_SUBTLE};
    background: {t.BG_ELEVATED};
    color: {t.TEXT_PRIMARY};
}}
QPushButton:hover {{ background: {t.BG_SURFACE_HOVER}; border-color: {t.BORDER_STRONG}; }}
QPushButton:pressed {{ background: {t.BG_SURFACE}; }}
QPushButton:focus {{ border-color: {t.FOCUS_RING}; }}
QPushButton:disabled {{ color: {t.TEXT_MUTED}; background: {t.BG_SURFACE}; border-color: {t.BORDER_SUBTLE}; }}

QPushButton[variant="primary"] {{
    background: {t.ACCENT_PRIMARY};
    border-color: {t.ACCENT_PRIMARY};
    color: {t.TEXT_PRIMARY};
}}
QPushButton[variant="primary"]:hover {{ background: {t.ACCENT_HOVER}; border-color: {t.ACCENT_HOVER}; }}
QPushButton[variant="primary"]:pressed {{ background: {t.ACCENT_PRESSED}; border-color: {t.ACCENT_PRESSED}; }}
QPushButton[variant="primary"]:focus {{ border-color: {t.FOCUS_RING}; }}
QPushButton[variant="primary"]:disabled {{
    background: {rgba(t.ACCENT_PRIMARY, 0.35)};
    border-color: transparent;
    color: {rgba(t.TEXT_PRIMARY, 0.55)};
}}

QPushButton[variant="ghost"] {{
    background: transparent;
    border-color: transparent;
    color: {t.TEXT_SECONDARY};
}}
QPushButton[variant="ghost"]:hover {{ background: {t.BG_SURFACE_HOVER}; color: {t.TEXT_PRIMARY}; }}
QPushButton[variant="ghost"]:pressed {{ background: {t.BG_SURFACE}; }}
QPushButton[variant="ghost"]:focus {{ border-color: {t.FOCUS_RING}; }}
QPushButton[variant="ghost"]:disabled {{ background: transparent; color: {t.TEXT_MUTED}; }}

QPushButton[variant="danger"] {{
    background: {rgba(t.DANGER, 0.10)};
    border-color: {rgba(t.DANGER, 0.30)};
    color: {t.DANGER};
}}
QPushButton[variant="danger"]:hover {{ background: {rgba(t.DANGER, 0.18)}; border-color: {rgba(t.DANGER, 0.5)}; }}
QPushButton[variant="danger"]:pressed {{ background: {rgba(t.DANGER, 0.26)}; }}
QPushButton[variant="danger"]:focus {{ border-color: {t.DANGER}; }}

QPushButton[variant="danger-solid"] {{
    background: {t.DANGER};
    border-color: {t.DANGER};
    color: #1B0A10;
}}
QPushButton[variant="danger-solid"]:hover {{ background: #FD8A9B; border-color: #FD8A9B; }}
QPushButton[variant="danger-solid"]:pressed {{ background: #E95D74; }}
QPushButton[variant="danger-solid"]:focus {{ border-color: {t.TEXT_PRIMARY}; }}

QPushButton[size="sm"] {{
    min-height: 32px;
    padding: 0 12px;
    border-radius: 8px;
    font-size: 12px;
}}

QPushButton[seg="true"] {{
    min-height: 32px;
    padding: 0 14px;
    border-radius: 7px;
    border: 1px solid transparent;
    background: transparent;
    color: {t.TEXT_SECONDARY};
    font-weight: 500;
}}
QPushButton[seg="true"]:hover {{ color: {t.TEXT_PRIMARY}; background: {rgba(t.TEXT_PRIMARY, 0.04)}; }}
QPushButton[seg="true"]:checked {{
    background: {t.ACCENT_SOFT};
    border-color: {rgba(t.ACCENT_PRIMARY, 0.45)};
    color: {t.TEXT_PRIMARY};
    font-weight: 600;
}}
QPushButton[seg="true"]:focus {{ border-color: {t.FOCUS_RING}; }}
#Segmented {{
    background: {t.BG_INPUT};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: 10px;
}}

QPushButton[chip="true"] {{
    min-height: 26px;
    padding: 0 10px;
    border-radius: 13px;
    font-size: 12px;
    font-weight: 500;
    background: {t.ACCENT_SOFT};
    border: 1px solid {rgba(t.ACCENT_PRIMARY, 0.35)};
    color: {t.ACCENT_TEXT};
}}
QPushButton[chip="true"]:hover {{ border-color: {t.ACCENT_PRIMARY}; color: {t.TEXT_PRIMARY}; }}

QToolButton#IconButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0;
}}
QToolButton#IconButton:hover {{ background: {t.BG_SURFACE_HOVER}; border-color: {t.BORDER_SUBTLE}; }}
QToolButton#IconButton:pressed {{ background: {t.BG_ELEVATED}; }}
QToolButton#IconButton:focus {{ border-color: {t.FOCUS_RING}; }}
QToolButton#IconButton[tone="danger"]:hover {{ background: {rgba(t.DANGER, 0.12)}; border-color: {rgba(t.DANGER, 0.3)}; }}
QToolButton#IconButton::menu-indicator {{ image: none; width: 0; }}

/* ---------- inputs ---------- */
QLineEdit, QPlainTextEdit, QComboBox, #DateField {{
    background: {t.BG_INPUT};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: {t.RADIUS_MD}px;
    padding: 0 12px;
    min-height: 42px;
    color: {t.TEXT_PRIMARY};
}}
QPlainTextEdit {{
    padding: 8px 8px;
}}
QLineEdit:hover, QPlainTextEdit:hover, QComboBox:hover, #DateField:hover {{
    border-color: {t.BORDER_STRONG};
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QComboBox:on, #DateField:focus, #DateField[open="true"] {{
    border-color: {t.FOCUS_RING};
}}
QLineEdit[error="true"], QPlainTextEdit[error="true"], QComboBox[error="true"], #DateField[error="true"] {{
    border-color: {t.DANGER};
}}
QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, #DateField:disabled {{
    color: {t.TEXT_MUTED};
    background: {t.BG_SURFACE};
}}
QLineEdit[size="sm"], QComboBox[size="sm"], #DateField[size="sm"] {{
    min-height: 34px;
    border-radius: 8px;
    padding: 0 10px;
}}
#DateField {{
    text-align: right;
    font-weight: 400;
    font-size: {t.FONT_BODY}px;
}}
QLineEdit[placeholder="true"], #DateField[empty="true"] {{
    color: {t.TEXT_MUTED};
}}

QComboBox {{
    padding: 0 12px 0 8px;
    combobox-popup: 0;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center left;
    width: 26px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url("{chevron}");
    width: 16px;
    height: 16px;
}}
QComboBox::down-arrow:on {{
    image: url("{chevron_up}");
}}
QComboBox QAbstractItemView {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: 10px;
    padding: 6px;
    outline: 0;
    color: {t.TEXT_PRIMARY};
    selection-background-color: {t.ACCENT_SOFT};
}}
QComboBox QAbstractItemView::item {{
    min-height: 34px;
    padding: 0 10px;
    border-radius: 7px;
    border: none;
}}
QComboBox QAbstractItemView::item:hover {{
    background: {t.BG_SURFACE_HOVER};
}}
QComboBox QAbstractItemView::item:selected {{
    background: {t.ACCENT_SOFT};
    color: {t.TEXT_PRIMARY};
}}

QCompleter QAbstractItemView, #CompleterPopup {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: 10px;
    padding: 6px;
    outline: 0;
}}
#CompleterPopup::item {{
    min-height: 34px;
    padding: 0 10px;
    border-radius: 7px;
}}
#CompleterPopup::item:selected, #CompleterPopup::item:hover {{
    background: {t.ACCENT_SOFT};
    color: {t.TEXT_PRIMARY};
}}

QCheckBox {{
    spacing: 10px;
    color: {t.TEXT_PRIMARY};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {t.BORDER_STRONG};
    background: {t.BG_INPUT};
}}
QCheckBox::indicator:hover {{ border-color: {t.FOCUS_RING}; }}
QCheckBox::indicator:checked {{
    background: {t.ACCENT_PRIMARY};
    border-color: {t.ACCENT_PRIMARY};
    image: url("{check}");
}}

/* ---------- table ---------- */
QTableView {{
    background: transparent;
    border: none;
    gridline-color: transparent;
    outline: 0;
    selection-background-color: transparent;
    selection-color: {t.TEXT_PRIMARY};
}}
QTableView::item {{
    border: none;
    padding: 0;
}}
QHeaderView {{
    background: transparent;
    border: none;
}}
QHeaderView::section {{
    background: transparent;
    color: {t.TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {t.BORDER_SUBTLE};
    padding: 0 12px;
    min-height: 44px;
    font-size: {t.FONT_SMALL}px;
    font-weight: 600;
}}
QHeaderView::section:hover {{
    color: {t.TEXT_PRIMARY};
}}
QHeaderView::down-arrow {{
    image: url("{chevron}");
    width: 14px;
    height: 14px;
}}
QHeaderView::up-arrow {{
    image: url("{chevron_up}");
    width: 14px;
    height: 14px;
}}
QTableCornerButton::section {{
    background: transparent;
    border: none;
}}

/* ---------- list ---------- */
QListView, QListWidget {{
    background: transparent;
    border: none;
    outline: 0;
}}
QListWidget::item {{
    min-height: 40px;
    padding: 0 10px;
    border-radius: 8px;
}}
QListWidget::item:hover {{ background: {t.BG_SURFACE_HOVER}; }}
QListWidget::item:selected {{ background: {t.ACCENT_SOFT}; color: {t.TEXT_PRIMARY}; }}

/* ---------- scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 1px;
}}
QScrollBar::handle:vertical {{
    background: #2A2A39;
    border-radius: 4px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{ background: #3A3A50; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 1px 2px;
}}
QScrollBar::handle:horizontal {{
    background: #2A2A39;
    border-radius: 4px;
    min-width: 36px;
}}
QScrollBar::handle:horizontal:hover {{ background: #3A3A50; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ---------- menus & tooltips ---------- */
QMenu {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 14px 8px 18px;
    border-radius: 7px;
    min-width: 150px;
    color: {t.TEXT_PRIMARY};
}}
QMenu::item:selected {{ background: {t.BG_SURFACE_HOVER}; }}
QMenu::item:disabled {{ color: {t.TEXT_MUTED}; }}
QMenu::icon {{ padding: 0 10px; }}
QMenu::separator {{
    height: 1px;
    background: {t.BORDER_SUBTLE};
    margin: 5px 8px;
}}
QMenu[danger="true"]::item:selected {{ color: {t.DANGER}; }}
QToolTip {{
    background: {t.BG_ELEVATED};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: {t.FONT_SMALL}px;
}}

/* ---------- list rows ---------- */
#ListRow {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
}}
#ListRow:hover {{ background: {t.BG_SURFACE_HOVER}; }}
#ListRow:focus {{ border-color: {t.FOCUS_RING}; }}
#Banner {{
    background: qlineargradient(x1:1, y1:0, x2:0, y2:1, stop:0 #1F1733, stop:1 {t.BG_SURFACE});
    border: 1px solid {rgba(t.ACCENT_PRIMARY, 0.28)};
    border-radius: {t.RADIUS_LG}px;
}}
#SettingRow {{
    background: transparent;
    border: none;
    border-bottom: 1px solid {t.BORDER_SUBTLE};
}}
#Kbd {{
    background: {t.BG_INPUT};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: 6px;
    padding: 2px 8px;
    color: {t.TEXT_SECONDARY};
    font-size: {t.FONT_SMALL}px;
}}

/* ---------- popups ---------- */
#PopupFrame {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: {t.RADIUS_LG}px;
}}
QToolButton#DayCell {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: {t.TEXT_PRIMARY};
    font-size: 13px;
}}
QToolButton#DayCell:hover {{ background: {t.BG_SURFACE_HOVER}; }}
QToolButton#DayCell[weekend="true"] {{ color: {rgba(t.DANGER, 0.85)}; }}
QToolButton#DayCell[outside="true"] {{ color: #4B4860; }}
QToolButton#DayCell[today="true"] {{ border-color: {rgba(t.ACCENT_PRIMARY, 0.7)}; color: {t.ACCENT_TEXT}; }}
QToolButton#DayCell[selected="true"] {{
    background: {t.ACCENT_PRIMARY};
    border-color: {t.ACCENT_PRIMARY};
    color: #FFFFFF;
    font-weight: 600;
}}
QToolButton#DayCell:disabled {{ color: #3A3849; background: transparent; }}

/* ---------- toasts ---------- */
#Toast {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: {t.RADIUS_LG}px;
}}

/* ---------- badges ---------- */
QLabel[badge] {{
    border-radius: 11px;
    padding: 0 10px;
    min-height: 22px;
    max-height: 22px;
    font-size: {t.FONT_SMALL}px;
    font-weight: 600;
}}
QLabel[badge="success"] {{ background: {rgba(t.SUCCESS, 0.12)}; color: {t.SUCCESS}; }}
QLabel[badge="warning"] {{ background: {rgba(t.WARNING, 0.12)}; color: {t.WARNING}; }}
QLabel[badge="danger"] {{ background: {rgba(t.DANGER, 0.12)}; color: {t.DANGER}; }}
QLabel[badge="info"] {{ background: {rgba(t.INFO, 0.12)}; color: {t.INFO}; }}
QLabel[badge="accent"] {{ background: {t.ACCENT_SOFT}; color: {t.ACCENT_TEXT}; }}
QLabel[badge="neutral"] {{ background: {rgba(t.TEXT_SECONDARY, 0.10)}; color: {t.TEXT_SECONDARY}; }}
"""
