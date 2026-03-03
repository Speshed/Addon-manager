# -*- coding: utf-8 -*-
"""
BIM Sync Tool - nativeId Sync (Qt Adapter UI)
v12: В логах вместо "Контейнер N" показываются наименования соответствующих моделей.
Сопоставление по базовому имени (без расширений/регистра/символов).
"""

import sys, json, requests, os, re, tempfile


# --- Qt imports ---
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QCheckBox,
    QTextEdit, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtGui import QIcon, QFont, QPixmap, QTextCursor
from PySide6.QtCore import Qt
PYSIDE = True

APP_DIR = os.path.abspath(os.path.dirname(__file__))
APP_ROOT_DIR = os.path.dirname(APP_DIR)
ICON_DIR = os.path.join(APP_ROOT_DIR, "icon")
WINDOW_ICON_NAME = "app_icon"
LOGO_NAME = "logo"
LOGO_LIGHT_REL = os.path.join("icon", "Manager-scaled.png")
LOGO_DARK_REL = os.path.join("icon", "Manager-scaled_white.png")
TITLEBAR_ICON_REL = os.path.join("icon", "logo.ico")

# --- Import from theme_toggle ---
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.theme_toggle import (
    ThemeToggle, apply_themed_icon, theme, is_dark_theme, resolve_icon_path, nik_icon, PALETTE,
    load_saved_theme, enable_theme_sync, apply_dark_titlebar,
    create_back_button, go_to_main_menu,
    register_icon_files, _ensure_white_copy, _ensure_black_copy, _tint_pixmap, _qss_url
)
from shared.dialogs import show_dialog, wire_message_box_buttons


# --- Additional icon files specific to Viewer ---
_VIEWER_ICON_FILES = {
    "1":           ["1.png"],
    "2":           ["2.png"],
    "extend":      ["extend.png"],
    "arrow_oba":   ["arrow-oba.png"],
    "navigation":  ["navigation.png"],
    "move":        ["move.png"],
    "compare":     ["compare.png"],
}

register_icon_files(_VIEWER_ICON_FILES)

def apply_window_icon(widget_or_app, *, icon_dir: str = ICON_DIR) -> None:
    icon_path = os.path.join(APP_ROOT_DIR, TITLEBAR_ICON_REL)
    ic = QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()
    if ic.isNull():
        app = QtWidgets.QApplication.instance()
        ic = nik_icon(WINDOW_ICON_NAME, app=app, icon_dir=icon_dir)
    if ic.isNull():
        app = QtWidgets.QApplication.instance()
        ic = nik_icon(LOGO_NAME, app=app, icon_dir=icon_dir)
    try:
        widget_or_app.setWindowIcon(ic)
    except Exception:
        pass


def _pad_pixmap(pm: QtGui.QPixmap, left: int, top: int, right: int, bottom: int) -> QtGui.QPixmap:
    if pm.isNull():
        return pm
    out = QtGui.QPixmap(pm.width() + left + right, pm.height() + top + bottom)
    out.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(out)
    painter.drawPixmap(left, top, pm)
    painter.end()
    return out


def apply_themed_icon_with_arrow(widget, name: str = "arrow_right", icon_dir: str = ICON_DIR, icon_size: tuple = (8, 8), padding_top: int = 8):
    try:
        widget.setLayoutDirection(QtCore.Qt.RightToLeft)
    except Exception:
        pass
    app = QtWidgets.QApplication.instance()
    path = resolve_icon_path(name, icon_dir, app=app)
    pm = QtGui.QPixmap(path) if path else QtGui.QPixmap()
    if not pm.isNull():
        pm = pm.scaled(icon_size[0], icon_size[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
    normal_pm = _pad_pixmap(pm, 0, max(0, int(padding_top)), 0, 0) if not pm.isNull() else QtGui.QPixmap()
    hover_raw = _tint_pixmap(pm, QtGui.QColor("#000000")) if not pm.isNull() else QtGui.QPixmap()
    hover_pm = _pad_pixmap(hover_raw, 0, max(0, int(padding_top)), 0, 0) if not hover_raw.isNull() else QtGui.QPixmap()

    normal_icon = QtGui.QIcon(normal_pm) if not normal_pm.isNull() else QtGui.QIcon()
    hover_icon = QtGui.QIcon(hover_pm) if not hover_pm.isNull() else normal_icon
    widget.setIcon(normal_icon)
    if not normal_pm.isNull():
        widget.setIconSize(QtCore.QSize(normal_pm.width(), normal_pm.height()))
    try:
        old = getattr(widget, "_nik_hover_filter", None)
        if isinstance(old, QtCore.QObject):
            widget.removeEventFilter(old)
    except Exception:
        pass
    class _PaddedIconHover(QtCore.QObject):
        def __init__(self, btn, normal, hover):
            super().__init__(btn); self._btn = btn; self._normal = normal; self._hover = hover
        def eventFilter(self, obj, ev):
            t = ev.type()
            if t in (QtCore.QEvent.Enter, QtCore.QEvent.HoverEnter, QtCore.QEvent.FocusIn, QtCore.QEvent.MouseMove):
                self._btn.setIcon(self._hover)
            elif t in (QtCore.QEvent.Leave, QtCore.QEvent.HoverLeave, QtCore.QEvent.FocusOut, QtCore.QEvent.EnabledChange):
                self._btn.setIcon(self._normal)
            return False
    filt = _PaddedIconHover(widget, normal_icon, hover_icon)
    try:
        widget.setMouseTracking(True)
    except Exception:
        pass
    widget.installEventFilter(filt)
    setattr(widget, "_nik_hover_filter", filt)
    try:
        widget.setStyleSheet("")
    except Exception:
        pass


def load_logo(icon_dir: str = ICON_DIR) -> QtGui.QPixmap:
    app = QtWidgets.QApplication.instance()
    dark = is_dark_theme(app)
    rel = LOGO_DARK_REL if dark else LOGO_LIGHT_REL
    p = os.path.join(APP_ROOT_DIR, rel)
    if not os.path.exists(p):
        name = "logo_white" if dark else "logo"
        p = resolve_icon_path(name, icon_dir)
    if not p:
        p = resolve_icon_path("logo", icon_dir)
    pm = QtGui.QPixmap(p) if p else QtGui.QPixmap()
    return pm if not pm.isNull() else QtGui.QPixmap()



def set_header_logo(label: QtWidgets.QLabel, icon_dir: str, height: int = 48):
    pm = load_logo(icon_dir)
    if not pm.isNull():
        pm = pm.scaledToHeight(height, QtCore.Qt.SmoothTransformation)
        label.setPixmap(pm)
        label.setAlignment(QtCore.Qt.AlignCenter)

def show_error_dialog(text: str, *, title: str = "Ошибка", icon_dir: str | None = None, parent=None, modal: bool = True):
    if icon_dir is None:
        icon_dir = ICON_DIR
    if parent is None:
        try:
            parent = QtWidgets.QApplication.activeWindow()
        except Exception:
            parent = None
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    app = QtWidgets.QApplication.instance()
    p = resolve_icon_path("error", icon_dir, app=app)
    pm = QPixmap(p) if p else QPixmap()
    if not pm.isNull():
        msg.setIconPixmap(pm.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        msg.setIcon(QtWidgets.QMessageBox.Critical)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    try:
        msg.setStyleSheet("QLabel#qt_msgbox_label{margin-top:10px;} QLabel#qt_msgbox_informativelabel{margin-top:10px;}")
    except Exception:
        pass
    wire_message_box_buttons(msg)
    show_dialog(msg, modal=modal)


def show_info_dialog(text: str, *, title: str = "Информация", icon_dir: str | None = None, parent=None, modal: bool = True):
    if icon_dir is None:
        icon_dir = ICON_DIR
    if parent is None:
        try:
            parent = QtWidgets.QApplication.activeWindow()
        except Exception:
            parent = None
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    app = QtWidgets.QApplication.instance()
    p = resolve_icon_path("alert", icon_dir, app=app)
    pm = QPixmap(p) if p else QPixmap()
    if not pm.isNull():
        msg.setIconPixmap(pm.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    try:
        msg.setStyleSheet("QLabel#qt_msgbox_label{margin-top:10px;} QLabel#qt_msgbox_informativelabel{margin-top:10px;}")
    except Exception:
        pass
    wire_message_box_buttons(msg)
    show_dialog(msg, modal=modal)


def _qss_common(ar_down: str, ar_up: str, ar_left: str, ar_right: str, cmb_down: str,
                chk_off: str, chk_on: str, chk_mid: str,
                rchk_off: str, rchk_on: str,
                list_hover_off: str, list_hover_on: str, list_hover_mid: str,
                *, dark: bool) -> str:
    BG = PALETTE.BG_DARK if dark else PALETTE.BG_LIGHT
    FG = PALETTE.FG_DARK if dark else PALETTE.FG_LIGHT
    BORDER = PALETTE.BORDER_DARK if dark else PALETTE.BORDER_LIGHT
    TRACK = PALETTE.SCROLL_TRACK_DARK if dark else PALETTE.SCROLL_TRACK_LIGHT

    ar_down = _qss_url(ar_down)
    ar_up = _qss_url(ar_up)
    ar_left = _qss_url(ar_left)
    ar_right = _qss_url(ar_right)
    cmb_down = _qss_url(cmb_down)
    TRACK_BG = BG if dark else PALETTE.SCROLL_TRACK_LIGHT

    chk_off = _qss_url(chk_off)
    chk_on = _qss_url(chk_on)
    chk_mid = _qss_url(chk_mid)
    rchk_off = _qss_url(rchk_off)
    rchk_on = _qss_url(rchk_on)
    list_hover_off = _qss_url(list_hover_off)
    list_hover_on = _qss_url(list_hover_on)
    list_hover_mid = _qss_url(list_hover_mid)

    hover_text = "#000000"

    qss = f"""
    * {{
        font-family: '{_BASE_FONT_FAMILY}';
        font-size: {_BASE_FONT_SIZE_PT}pt;
        color: {FG};
        selection-background-color: {PALETTE.SELECTED};
        selection-color: #000000;
        outline: none;
    }}
    *:focus {{ outline: none; }}
    QWidget {{ background: {BG}; }}
    QStatusBar, QMenuBar, QToolBar, QMenu, QDockWidget::title {{ background: {BG}; border: 1px solid {BORDER}; }}
    QTabBar::pane {{ background: {BG}; border: none; }}
    #header {{ background: {BG}; border: none; }}
    QTabWidget::pane {{ border: none; border-radius: 12px; margin-top: 8px; }}
    QTabBar::tab {{ background: {BG}; color: {FG}; border: 1px solid {BORDER}; border-bottom-color: {BORDER};
                   padding: 6px 14px; border-top-left-radius: 10px; border-top-right-radius: 10px; margin: 0 4px; }}
    QTabBar::tab:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_text}; border-color: {PALETTE.ACCENT}; }}
    QTabBar::tab:selected {{ background: {PALETTE.SELECTED}; color: {hover_text}; border-color: {PALETTE.ACCENT}; }}
    QTabBar::tab:!selected {{ margin-top: 6px; }}

    QPushButton {{
        background: {BG};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{ background: rgba(247, 146, 30, 0.15); color: {FG}; border: 1px solid {PALETTE.ACCENT}; }}
    QPushButton:pressed {{ background: rgba(247, 146, 30, 0.25); border: 1px solid {PALETTE.ACCENT}; }}
    QPushButton:disabled {{ background: {'#2A2A2A' if dark else '#f0f0f0'}; color: {'#8f8f8f' if dark else '#9b9b9b'}; }}

    QPushButton[largeButton="true"] {{
        font-size: {_BASE_FONT_SIZE_PT + 2}pt;
        font-weight: 600;
        padding: 8px 14px;
    }}

    .btn-secondary {{
        background: {BG}; color: {FG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 5px 10px;
    }}
    .btn-secondary:hover {{ background: rgba(247, 146, 30, 0.15); border: 1px solid {PALETTE.ACCENT}; }}

    QComboBox {{
        border: 1px solid {BORDER}; border-radius: 12px; padding: 3px 28px 3px 8px;
        background: {BG}; selection-background-color: {PALETTE.SELECTED}; selection-color: #000000;
    }}
    QComboBox::drop-down {{ width: 26px; border: none; }}
    QComboBox::down-arrow {{ image: url('{cmb_down}'); width: 12px; height: 12px; }}

    QLineEdit,
    QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit, QDateTimeEdit {{
        border: 1px solid {BORDER}; border-radius: 12px; padding: 3px 8px;
        background: {BG}; selection-background-color: {PALETTE.SELECTED};
    }}
    QLineEdit:hover,
    QSpinBox:hover, QDoubleSpinBox:hover,
    QDateEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover {{
        background: {BG}; color: {FG};
    }}
    QLineEdit:disabled,
    QSpinBox:disabled, QDoubleSpinBox:disabled,
    QDateEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{
        background: {'#2A2A2A' if dark else '#f0f0f0'}; color: {'#8f8f8f' if dark else '#9b9b9b'};
    }}

    QComboBox QAbstractItemView {{ background: {BG}; border: 1px solid {BORDER}; outline: none; selection-background-color: {PALETTE.SELECTED}; }}
    QComboBox QAbstractItemView::item {{ padding: 4px 8px; border-radius: 8px; margin: 1px 4px; border: none; }}
    QComboBox QAbstractItemView::item:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_text}; border-radius: 8px; border: none; }}
    QComboBox QAbstractItemView::item:selected {{ background: {PALETTE.SELECTED}; color: {hover_text}; border-radius: 8px; border: none; }}
    QComboBox QAbstractItemView::item:focus {{ outline: none; border: none; }}

    QListView, QListWidget {{
        background: {BG};
        border: 1px solid {BORDER};
        outline: none;
        selection-background-color: {PALETTE.SELECTED};
        selection-color: {hover_text};
    }}
    QListView::item, QListWidget::item {{
        padding: 6px 8px;
        border-radius: 8px;
        margin: 1px 4px;
        border: none;
    }}
    QListView::item:hover, QListWidget::item:hover {{
        background: {PALETTE.SOFT_HOVER};
        color: {hover_text};
        border-radius: 8px;
    }}
    QListView::item:selected, QListWidget::item:selected {{
        background: {PALETTE.SELECTED};
        color: {hover_text};
        border-radius: 8px;
    }}
    QListView::item:selected:active, QListWidget::item:selected:active {{
        background: {PALETTE.SELECTED};
    }}
    QListView::indicator, QListWidget::indicator {{
        width: 18px;
        height: 18px;
    }}
    QListView::indicator:unchecked, QListWidget::indicator:unchecked {{
        image: url('{chk_off}');
    }}
    QListView::indicator:checked, QListWidget::indicator:checked {{
        image: url('{chk_on}');
    }}
    QListView::indicator:indeterminate, QListWidget::indicator:indeterminate {{
        image: url('{chk_mid}');
    }}
    QListView::indicator:hover, QListWidget::indicator:hover {{
        background: transparent;
        border-radius: 0;
    }}

    QCheckBox {{ padding: 2px; color: {FG}; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QCheckBox::indicator:unchecked {{ image: url('{chk_off}'); }}
    QCheckBox::indicator:checked   {{ image: url('{chk_on}'); }}
    QCheckBox::indicator:indeterminate {{ image: url('{chk_mid}'); }}
    QCheckBox::indicator:hover {{
        background: transparent;
        border-radius: 0;
    }}
    QCheckBox[round="true"]::indicator {{ width: 18px; height: 18px; }}
    QCheckBox[round="true"]::indicator:hover {{
        background: transparent;
        border-radius: 0;
    }}
    QCheckBox:hover {{ color: {FG}; background: transparent; }}
    QRadioButton:hover {{ color: {FG}; background: transparent; }}

    QAbstractSpinBox::up-arrow    {{ image: url('{ar_up}');   width: 12px; height: 12px; }}
    QAbstractSpinBox::down-arrow  {{ image: url('{ar_down}'); width: 12px; height: 12px; }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ background: transparent; border: none; }}

    QDateEdit::drop-down, QDateTimeEdit::drop-down {{ background: transparent; border: none; width: 22px; }}
    QDateEdit::down-arrow, QDateTimeEdit::down-arrow {{ image: url('{ar_down}'); width: 12px; height: 12px; margin-right: 4px; }}

    QHeaderView::section {{
        background: {BG};
        color: {FG};
        border: 1px solid transparent;
        padding: 6px 8px;
    }}
    QTableView, QTreeView {{
        gridline-color: transparent;
        outline: none;
        border: none;
        selection-background-color: {PALETTE.SELECTED};
    }}
    QHeaderView::up-arrow {{ image: url('{ar_up}'); width: 12px; height: 12px; }}
    QHeaderView::down-arrow {{ image: url('{ar_down}'); width: 12px; height: 12px; }}
    QHeaderView::section:hover {{ background: #FFF3E6; color: {hover_text}; border-color: #FFD1A0; }}
    QHeaderView::section:pressed {{ background: #ffca91; color: {hover_text}; border-color: #FFA74B; }}
    QHeaderView::section:hover,
    QHeaderView::section:pressed {{ border-radius: 8px; }}
    QHeaderView::section:first:hover,
    QHeaderView::section:first:pressed {{ border-top-left-radius: 8px; }}
    QHeaderView::section:last:hover,
    QHeaderView::section:last:pressed  {{ border-top-right-radius: 8px; }}

    QScrollBar:vertical {{ background: {TRACK_BG}; width: 12px; margin: 16px 0 16px 0; border: none; }}
    QScrollBar::handle:vertical {{ background: rgba(247,146,30,0.12); min-height: 24px; border-radius: 6px; border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:vertical:hover {{ background: rgba(247,146,30,0.15); border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:vertical:pressed {{ background: rgba(247,146,30,0.25); border: 1px solid {PALETTE.ACCENT_PRESSED}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ background: {TRACK_BG}; height: 16px; subcontrol-origin: margin; border: none; border-radius: 0; image: none; }}
    QScrollBar::add-line:vertical {{ subcontrol-position: bottom; border: none; }}
    QScrollBar::sub-line:vertical {{ subcontrol-position: top; border: none; }}
    QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {{ background: rgba(247,146,30,0.15); }}
    QScrollBar::add-line:vertical:pressed, QScrollBar::sub-line:vertical:pressed {{ background: rgba(247,146,30,0.25); }}
    QScrollBar::up-arrow:vertical   {{ image: url('{ar_up}');   width: 12px; height: 12px; }}
    QScrollBar::down-arrow:vertical {{ image: url('{ar_down}'); width: 12px; height: 12px; }}
    QScrollBar::add-page:vertical,   QScrollBar::sub-page:vertical   {{ background: {TRACK_BG}; margin: 0; border: none; }}

    QScrollBar:horizontal {{ background: {TRACK_BG}; height: 12px; margin: 0 16px 0 16px; border: none; }}
    QScrollBar::handle:horizontal {{ background: rgba(247,146,30,0.12); min-width: 24px; border-radius: 6px; border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:horizontal:hover {{ background: rgba(247,146,30,0.15); border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:horizontal:pressed {{ background: rgba(247,146,30,0.25); border: 1px solid {PALETTE.ACCENT_PRESSED}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ background: {TRACK_BG}; width: 16px; subcontrol-origin: margin; border: none; border-radius: 0; image: none; }}
    QScrollBar::add-line:horizontal {{ subcontrol-position: right; border: none; }}
    QScrollBar::sub-line:horizontal {{ subcontrol-position: left; border: none; }}
    QScrollBar::add-line:horizontal:hover, QScrollBar::sub-line:horizontal:hover {{ background: rgba(247,146,30,0.15); }}
    QScrollBar::add-line:horizontal:pressed, QScrollBar::sub-line:horizontal:pressed {{ background: rgba(247,146,30,0.25); }}
    QScrollBar::left-arrow:horizontal  {{ image: url('{ar_left}');  width: 12px; height: 12px; }}
    QScrollBar::right-arrow:horizontal {{ image: url('{ar_right}'); width: 12px; height: 12px; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {TRACK_BG}; margin: 0; border: none; }}

    QAbstractScrollArea::corner {{ background: {TRACK_BG}; }}
    QMenu {{ border-radius: 12px; padding: 6px; }}
    QMenu::item {{ padding: 6px 10px; border-radius: 8px; }}
    QMenu::item:selected {{ background: {PALETTE.SOFT_HOVER}; }}

    QGroupBox {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
        margin-top: 22px;
        padding-top: 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 8px 2px 8px;
        background-color: {BG};
        color: {FG};
    }}

    QTextEdit, QPlainTextEdit {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        background: {BG};
        selection-background-color: {PALETTE.SELECTED};
        selection-color: #000000;
    }}

    QWidget[rowlike="true"] {{ background: {BG}; border: none; border-radius: 12px; padding: 6px 8px; }}
    QWidget[rowlike="true"]:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_text}; }}
    QWidget[rowlike="true"] QLabel {{ background: transparent; }}
    """
    qss += f"""
    QTableCornerButton::section, QTableView QTableCornerButton::section {{
        background: {BG};
        border: none;
    }}
    """
    qss += f"""
    QCheckBox[round="true"]::indicator:unchecked {{ image: url('{rchk_off}'); }}
    QCheckBox[round="true"]::indicator:checked   {{ image: url('{rchk_on}'); }}
    QCheckBox[round="true"]::indicator:indeterminate {{ image: url('{chk_mid}'); }}
    """
    qss += f"""
    QCheckBox::indicator:unchecked:hover {{ image: url('{chk_off}'); }}
    QCheckBox::indicator:checked:hover   {{ image: url('{chk_on}'); }}
    QCheckBox::indicator:indeterminate:hover {{ image: url('{chk_mid}'); }}
    QCheckBox[round="true"]::indicator:unchecked:hover {{ image: url('{rchk_off}'); }}
    QCheckBox[round="true"]::indicator:checked:hover   {{ image: url('{rchk_on}'); }}
    QCheckBox[round="true"]::indicator:indeterminate:hover {{ image: url('{chk_mid}'); }}
    """
    if dark:
        qss += f"""
        QListView::indicator:unchecked:hover, QListWidget::indicator:unchecked:hover {{ image: url('{list_hover_off}'); }}
        QListView::indicator:checked:hover,   QListWidget::indicator:checked:hover   {{ image: url('{list_hover_on}'); }}
        QListView::indicator:indeterminate:hover, QListWidget::indicator:indeterminate:hover {{ image: url('{list_hover_mid}'); }}
        """
    else:
        qss += f"""
        QListView::indicator:unchecked:hover, QListWidget::indicator:unchecked:hover {{ image: url('{chk_off}'); }}
        QListView::indicator:checked:hover,   QListWidget::indicator:checked:hover   {{ image: url('{chk_on}'); }}
        QListView::indicator:indeterminate:hover, QListWidget::indicator:indeterminate:hover {{ image: url('{chk_mid}'); }}
        """

    qss += f"""
    *[noCheckHoverRecolor="true"] QListView::indicator:unchecked:hover, *[noCheckHoverRecolor="true"] QListWidget::indicator:unchecked:hover {{ image: url('{chk_off}'); }}
    *[noCheckHoverRecolor="true"] QListView::indicator:checked:hover,   *[noCheckHoverRecolor="true"] QListWidget::indicator:checked:hover   {{ image: url('{chk_on}'); }}
    *[noCheckHoverRecolor="true"] QListView::indicator:indeterminate:hover, *[noCheckHoverRecolor="true"] QListWidget::indicator:indeterminate:hover {{ image: url('{chk_mid}'); }}
    """
    return qss


def apply_app_style(app: QtWidgets.QApplication, *, theme: str | None = None, icon_dir: str = ICON_DIR) -> None:
    if theme is not None:
        dark = str(theme).lower() == "dark"
    else:
        dark = is_dark_theme(app)
    theme(app, bool(dark), icon_dir=icon_dir)


class ThemeSwitch(QtWidgets.QAbstractButton):
    toggledTheme = QtCore.Signal(str) if hasattr(QtCore, "Signal") else QtCore.pyqtSignal(str)
    _anim_t = 0.0

    def __init__(self, parent=None, icon_dir: str = ICON_DIR):
        super().__init__(parent)
        self.setObjectName("themeToggle")
        self.setCheckable(True)
        self._icon_dir = icon_dir
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setToolTip("Переключить тему")
        self.setMinimumSize(58, 26)
        self.setMaximumHeight(28)
        self._anim = QtCore.QPropertyAnimation(self, b"anim_t", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.toggled.connect(self._on_toggled)
        app = QtWidgets.QApplication.instance()
        self.setChecked(is_dark_theme(app))
        self._sun_icon = self._load_icon_pm("sun")
        self._moon_icon = self._load_icon_pm("moon")

    @QtCore.Property(float)
    def anim_t(self):
        return self._anim_t

    @anim_t.setter
    def anim_t(self, v: float):
        self._anim_t = max(0.0, min(1.0, float(v)))
        self.update()

    def _on_toggled(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._anim_t)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        new_theme = "dark" if checked else "light"
        apply_app_style(app, theme=new_theme, icon_dir=self._icon_dir)
        self.toggledTheme.emit(new_theme)

    def sizeHint(self):
        return QtCore.QSize(66, 28)

    def minimumSizeHint(self):
        return QtCore.QSize(58, 26)

    def _load_icon_pm(self, name: str) -> QtGui.QPixmap:
        p = resolve_icon_path(name, self._icon_dir)
        if not p:
            candidate = os.path.join(self._icon_dir, f"{name}.png")
            if os.path.exists(candidate):
                p = candidate
        if p and os.path.exists(p):
            pm = QtGui.QPixmap(p)
            if not pm.isNull():
                return pm
        pm = QtGui.QPixmap(24, 24)
        pm.fill(QtCore.Qt.transparent)
        return pm

    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            rect = self.rect()
            track_rect = QtCore.QRectF(rect.adjusted(1, 1, -1, -1))
            dark = self.isChecked()

            track_color = QtGui.QColor("#555555") if dark else QtGui.QColor("#e8e8e8")
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(track_color)
            radius = track_rect.height() / 2.0
            painter.drawRoundedRect(track_rect, radius, radius)

            knob_margin = 3
            knob_d = track_rect.height() - knob_margin * 2
            knob_x = track_rect.left() + knob_margin + (track_rect.width() - 2 * knob_margin - knob_d) * self._anim_t
            knob_rect = QtCore.QRectF(knob_x, track_rect.top() + knob_margin, knob_d, knob_d)
            knob_color = QtGui.QColor("#101010") if dark else QtGui.QColor("#fdfdfd")
            painter.setBrush(knob_color)
            painter.drawEllipse(knob_rect)

            icon_size = int(track_rect.height() * 0.5)
            center_y = track_rect.center().y()
            left_x = track_rect.left() + 6
            right_x = track_rect.right() - icon_size - 6
            sun_on_left = self._anim_t >= 0.5
            sun_x = left_x if sun_on_left else right_x
            moon_x = right_x if sun_on_left else left_x
            if icon_size > 0:
                sun_pm = QtGui.QPixmap()
                moon_pm = QtGui.QPixmap()
                tint = QtGui.QColor(QtCore.Qt.white) if dark else QtGui.QColor("#222222")
                if not self._sun_icon.isNull():
                    _sun = self._sun_icon.scaled(icon_size, icon_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    sun_pm = _tint_pixmap(_sun, tint)
                if not self._moon_icon.isNull():
                    _moon = self._moon_icon.scaled(icon_size, icon_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    moon_pm = _tint_pixmap(_moon, tint)

                painter.save()
                painter.setPen(QtCore.Qt.NoPen)
                if not dark and not sun_pm.isNull():
                    highlight_size = icon_size + 8
                    painter.setBrush(QtGui.QColor("#F7921E"))
                    painter.drawEllipse(QtCore.QRectF(
                        sun_x - (highlight_size - icon_size) / 2,
                        center_y - highlight_size / 2,
                        highlight_size,
                        highlight_size
                    ))
                elif dark and not moon_pm.isNull():
                    highlight_size = icon_size + 8
                    painter.setBrush(QtGui.QColor("#F7921E"))
                    painter.drawEllipse(QtCore.QRectF(
                        moon_x - (highlight_size - icon_size) / 2,
                        center_y - highlight_size / 2,
                        highlight_size,
                        highlight_size
                    ))
                painter.restore()

                if not sun_pm.isNull():
                    painter.drawPixmap(int(sun_x), int(center_y - sun_pm.height() / 2), sun_pm)
                if not moon_pm.isNull():
                    painter.drawPixmap(int(moon_x), int(center_y - moon_pm.height() / 2), moon_pm)
        finally:
            painter.end()

def _style_pix(name: str) -> QtGui.QPixmap:
    try:
        ic = nik_icon(name, ICON_DIR)
        if isinstance(ic, QtGui.QIcon):
            pm = ic.pixmap(18,18)
            if not pm.isNull():
                return pm
    except Exception:
        pass
    # fallback - from icon/name.png
    p = os.path.join(ICON_DIR, f"{name}.png")
    pm = QtGui.QPixmap(p)
    if not pm.isNull():
        pm = pm.scaled(18, 18, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
    return pm


def _popup_error(parent, text: str, title: str = "Ошибка"):
    try:
        show_error_dialog(text, title=title, icon_dir=ICON_DIR, parent=parent, modal=True)
    except Exception:
        try:
            QtWidgets.QMessageBox.critical(parent, title, text)
        except Exception:
            pass

# --- Режимы ---

# --- Constants / Config ---
EXTERNAL_BASE_URL = "https://bwv.testing.bim-info.ru"
ACCESS_TOKEN = ""
EXTERNAL_HEADERS = {}
INTERNAL_HEADERS = {"accept": "*/*", "Content-Type": "application/json"}


def _internal_base_url() -> str:
    base = (os.environ.get("LARIX_API_BASE_URL") or "http://localhost:5000").rstrip("/")
    return f"{base}/api"


# --- Utils ---
def api_get(url, headers, params=None, timeout=10):
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def exec_app(app):
    return app.exec() if PYSIDE else app.exec_()

def normalize_name(name: str) -> str:
    base = os.path.basename(name or "").strip()
    if "." in base:
        base = base.rsplit(".", 1)[0]
    base = base.lower()
    base = re.sub(r"[^0-9a-zа-яё]", "", base, flags=re.IGNORECASE)
    return base


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Создание статусов")
        self.setMinimumSize(1160, 700)
        self.resize(1240, 760)
        apply_window_icon(self, icon_dir=ICON_DIR)

        self.schema_data = {}
        self.checked_models = {}       # mid -> QCheckBox (text = model name)
        self.checked_containers = {}   # cid -> QCheckBox (text = container title)
        self.container_titles = {}     # cid -> title (для логов)
        self.model_titles = {}         # mid -> title

        central = QWidget()
        grid = QGridLayout(central)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(8)

        # --- Header with back button + theme switch ---
        header = QWidget(); header.setObjectName("header")
        hl = QHBoxLayout(header); hl.setContentsMargins(8, 8, 8, 8)
        try:
            self._btn_back = create_back_button(self, size=32, icon_dir=ICON_DIR)
            self._btn_back.clicked.connect(lambda: go_to_main_menu(self))
            hl.addWidget(self._btn_back, 0, Qt.AlignLeft)
        except Exception:
            self._btn_back = None
        hl.addStretch(1)
        self._logo_label = None
        try:
            app = QtWidgets.QApplication.instance()
            self.theme_toggle = ThemeToggle()
            self.theme_toggle.toggled.connect(self._on_theme_toggled)
            self.theme_toggle.setChecked(bool(is_dark_theme(app)), animate=False)
            hl.addWidget(self.theme_toggle)
        except Exception:
            self.theme_toggle = None
        grid.addWidget(header, 0, 0, 1, 2)

        # --- 0. Token (top section) ---
        token_group = QGroupBox("Доступ к внешнему API (введите токен)")
        tlayout = QVBoxLayout(token_group)
        self._configure_section_layout(tlayout)
        try:
            token_group.setFlat(True)
        except Exception:
            pass

        trow = QHBoxLayout()
        self._configure_row_layout(trow)
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("Bearer xxxxx...")
        self.auth_status = QLabel("Не подключено")
        self.auth_status.setObjectName("statusBad")
        self.auth_status_icon = QLabel()
        self.auth_status_icon.setFixedSize(16, 16)
        self.auth_status_icon.setVisible(False)
        self._auth_ok = False
        token_btn = QPushButton("Ввод")
        token_btn.clicked.connect(self.try_auth)
        self._token_btn = token_btn
        # Themed icons for buttons (update on theme toggle)
        try:
            apply_themed_icon(token_btn, "login", ICON_DIR)
            if self.theme_toggle is not None:
                self.theme_toggle.toggled.connect(lambda _checked, b=token_btn: apply_themed_icon(b, "login", ICON_DIR))
        except Exception:
            pass

        trow.addWidget(self.token_edit, stretch=1)
        trow.addWidget(token_btn)
        trow.addWidget(self.auth_status_icon)
        trow.addWidget(self.auth_status)
        tlayout.addLayout(trow)
        self._lock_control_heights(self.token_edit, token_btn)

        # --- 1. Viewer Projects/Models ---
        viewer_group = QGroupBox("Модели во вьювере")
        vlayout = QVBoxLayout(viewer_group)
        self._configure_section_layout(vlayout)
        try:
            viewer_group.setFlat(True)
        except Exception:
            pass

        proj_row = QHBoxLayout()
        self._configure_row_layout(proj_row)
        proj_row.addWidget(QLabel("Проект:"))
        self.proj_combo = QComboBox()
        self.proj_combo.setMinimumWidth(360)
        proj_row.addWidget(self.proj_combo, stretch=1)
        self.load_projects_btn = QPushButton("Загрузить проекты")
        self.load_projects_btn.clicked.connect(self.load_projects)
        proj_row.addWidget(self.load_projects_btn)
        # Icons removed per request
        vlayout.addLayout(proj_row)
        self._lock_control_heights(self.proj_combo, self.load_projects_btn)

        self.models_scroll = QScrollArea()
        self.models_scroll.setWidgetResizable(True)
        try:
            self.models_scroll.setFrameShape(QFrame.NoFrame)
        except Exception:
            pass
        self.models_host = QWidget()
        self.models_layout = QVBoxLayout(self.models_host)
        self.models_layout.addStretch(1)
        self.models_scroll.setWidget(self.models_host)
        vlayout.addWidget(self.models_scroll)

        self.proj_combo.currentIndexChanged.connect(self._on_project_changed)

        # --- 2. Schemas/Attributes ---
        attr_group = QGroupBox("Атрибут")
        alayout = QVBoxLayout(attr_group)
        self._configure_section_layout(alayout)
        try:
            attr_group.setFlat(True)
        except Exception:
            pass

        srow = QHBoxLayout()
        self._configure_row_layout(srow)
        srow.addWidget(QLabel("Схема:"))
        self.schema_combo = QComboBox()
        self.schema_combo.setMinimumWidth(360)
        srow.addWidget(self.schema_combo, stretch=1)
        self.schema_combo.currentIndexChanged.connect(self.on_schema_changed)
        self.load_schemas_btn = QPushButton("Загрузить схемы")
        self.load_schemas_btn.clicked.connect(self.load_schemas_attrs)
        srow.addWidget(self.load_schemas_btn)
        # Icons removed per request
        alayout.addLayout(srow)
        self._lock_control_heights(self.schema_combo, self.load_schemas_btn)

        arow = QHBoxLayout()
        self._configure_row_layout(arow)
        arow.addWidget(QLabel("Атрибут:"))
        self.attr_combo = QComboBox()
        self.attr_combo.setMinimumWidth(360)
        arow.addWidget(self.attr_combo, stretch=1)
        alayout.addLayout(arow)
        self._lock_control_heights(self.attr_combo)

        # --- 3. Local Containers ---
        local_group = QGroupBox("Локальные контейнеры")
        llayout = QVBoxLayout(local_group)
        self._configure_section_layout(llayout)
        try:
            local_group.setFlat(True)
        except Exception:
            pass

        code_row = QHBoxLayout()
        self._configure_row_layout(code_row)
        code_row.addWidget(QLabel("Код параметра:"))
        self.param_code = QLineEdit()  # пусто
        code_row.addWidget(self.param_code, stretch=1)
        llayout.addLayout(code_row)
        self._lock_control_heights(self.param_code)

        val_row = QHBoxLayout()
        self._configure_row_layout(val_row)
        val_row.addWidget(QLabel("Устанавливаемое значение:"))
        self.value_entry = QLineEdit()  # пусто
        val_row.addWidget(self.value_entry, stretch=1)
        llayout.addLayout(val_row)
        self._lock_control_heights(self.value_entry)

        lproj_row = QHBoxLayout()
        self._configure_row_layout(lproj_row)
        lproj_row.addWidget(QLabel("Проект:"))
        self.local_proj_combo = QComboBox()
        self.local_proj_combo.setMinimumWidth(360)
        lproj_row.addWidget(self.local_proj_combo, stretch=1)
        self.local_proj_combo.currentIndexChanged.connect(self.load_local_containers)
        self.load_local_btn = QPushButton("Загрузить локальные")
        self.load_local_btn.clicked.connect(self.load_local_projects)
        lproj_row.addWidget(self.load_local_btn)
        # Icons removed per request
        llayout.addLayout(lproj_row)
        self._lock_control_heights(self.local_proj_combo, self.load_local_btn)

        self.container_scroll = QScrollArea()
        self.container_scroll.setWidgetResizable(True)
        try:
            self.container_scroll.setFrameShape(QFrame.NoFrame)
        except Exception:
            pass
        self.container_host = QWidget()
        self.container_layout = QVBoxLayout(self.container_host)
        self.container_layout.addStretch(1)
        self.container_scroll.setWidget(self.container_host)
        llayout.addWidget(self.container_scroll)

        # --- Start button ---
        self.start_btn = QPushButton("Запустить синхронизацию")
        self.start_btn.clicked.connect(self.start_sync)
        self._lock_control_heights(self.start_btn, minimum=40)
        # Icons removed per request

        # place in grid
        grid.addWidget(token_group, 1, 0, 1, 2)
        grid.addWidget(viewer_group, 2, 0, 1, 1)
        grid.addWidget(attr_group,   3, 0, 1, 1)
        grid.addWidget(local_group,  2, 1, 2, 1)
        grid.addWidget(self.start_btn, 4, 0, 1, 2)

        grid.setRowStretch(2, 1)
        grid.setRowStretch(3, 0)
        grid.setRowStretch(4, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.setCentralWidget(central)

    def _configure_section_layout(self, layout):
        try:
            layout.setContentsMargins(12, 18, 12, 12)
            layout.setSpacing(10)
        except Exception:
            pass

    def _configure_row_layout(self, layout):
        try:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
        except Exception:
            pass

    def _lock_control_heights(self, *widgets, minimum=34):
        for widget in widgets:
            if widget is None:
                continue
            try:
                widget.setFixedHeight(max(int(minimum), int(widget.sizeHint().height())))
            except Exception:
                pass

    # --- UI helpers ---
    def _on_theme_toggled(self, dark: bool) -> None:
        try:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                theme(app, bool(dark), icon_dir=ICON_DIR)
                apply_dark_titlebar(self, bool(dark))
        except Exception:
            pass
        try:
            apply_window_icon(self, icon_dir=ICON_DIR)
        except Exception:
            pass
        try:
            if getattr(self, "_token_btn", None) is not None:
                apply_themed_icon(self._token_btn, "login", ICON_DIR)
        except Exception:
            pass
        try:
            self._set_auth_status_icon(bool(getattr(self, "_auth_ok", False)))
        except Exception:
            pass

    def _make_section_title(self, text):
        # Заголовки теперь задаются через QGroupBox.setTitle; вспомогательный метод не используется
        return QLabel(text)

    def log(self, msg):
        # Логи отключены — ничего не делаем
        return

    def _refresh_status_style(self):
        self.auth_status.style().unpolish(self.auth_status); self.auth_status.style().polish(self.auth_status)

    def _set_auth_status_icon(self, ok: bool):
        self._auth_ok = bool(ok)
        if not ok:
            self.auth_status_icon.setPixmap(QPixmap())
            self.auth_status_icon.setVisible(False)
            return
        path = resolve_icon_path("ok", ICON_DIR, app=QtWidgets.QApplication.instance())
        pm = QPixmap(path) if path else QPixmap()
        if not pm.isNull():
            pm = pm.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.auth_status_icon.setPixmap(pm)
        self.auth_status_icon.setVisible(not pm.isNull())

    def _current_combo_id(self, combo):
        data = combo.currentData()
        if data is not None:
            try:
                return int(data)
            except Exception:
                return data
        if combo.count() == 0:
            return None
        txt = combo.currentText()
        if " | " not in txt:
            return None
        try:
            return int(txt.split(" | ")[0])
        except Exception:
            return None

    # --- Token flow ---
    def try_auth(self):
        global ACCESS_TOKEN, EXTERNAL_HEADERS
        raw = self.token_edit.text().strip()
        if len(raw) <= 7:
            self.auth_status.setText("Не подключено")
            self.auth_status.setObjectName("statusBad")
            self._refresh_status_style()
            self._set_auth_status_icon(False)
            _popup_error(self, "Введите корректный токен (Bearer ...)")
            return

        ACCESS_TOKEN = raw[7:].strip()
        EXTERNAL_HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}

        try:
            r = requests.get(f"{EXTERNAL_BASE_URL}/api/projects/all", headers=EXTERNAL_HEADERS, timeout=5)
            if r.status_code == 200:
                self.auth_status.setText("Авторизован")
                self.auth_status.setObjectName("statusOk")
                self._refresh_status_style()
                self._set_auth_status_icon(True)
                show_info_dialog("Авторизация прошла успешно.", title="Успех", parent=self)
            else:
                self.auth_status.setText("Не подключено")
                self.auth_status.setObjectName("statusBad")
                self._refresh_status_style()
                self._set_auth_status_icon(False)
                _popup_error(self, f"Не удалось авторизоваться: {r.status_code}")
        except Exception as e:
            self.auth_status.setText("Не подключено")
            self.auth_status.setObjectName("statusBad")
            self._refresh_status_style()
            self._set_auth_status_icon(False)
            _popup_error(self, f"Не удалось подключиться: {e}")

    # --- Viewer projects/models ---
    def load_projects(self):
        data = api_get(f"{EXTERNAL_BASE_URL}/api/projects/all", EXTERNAL_HEADERS)
        if not data:
            _popup_error(self, "Не удалось загрузить проекты")
            return
        self.proj_combo.clear()
        for p in data:
            self.proj_combo.addItem(p['name'], p['id'])
        if data:
            self.load_models(data[0]["id"])

    def _on_project_changed(self, _idx):
        pid = self._current_combo_id(self.proj_combo)
        if pid is not None:
            self.load_models(pid)

    def load_models(self, proj_id):
        for i in reversed(range(self.models_layout.count()-1)):
            item = self.models_layout.itemAt(i)
            w = item.widget()
            if w: w.setParent(None)
        self.checked_models.clear()
        self.model_titles.clear()

        data = api_get(f"{EXTERNAL_BASE_URL}/api/jimc/projectid", EXTERNAL_HEADERS, {"projectId": proj_id})
        if not data:
            return
        for m in data:
            mid = m["id"]
            name = m.get("modelName", "Без названия")
            cb = QCheckBox(f"{name}")
            cb.toggled.connect(self.refresh_container_highlights)  # обновлять при отметке
            self.models_layout.insertWidget(self.models_layout.count()-1, cb)
            self.checked_models[mid] = cb
            self.model_titles[mid] = name

    # --- Schemas / Attributes ---
    def load_schemas_attrs(self):
        models = [mid for mid, cb in self.checked_models.items() if cb.isChecked()]
        self.schema_data.clear()
        self.schema_combo.clear()
        self.attr_combo.clear()

        if not models:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы одну модель.")
            return

        proj_id = self._current_combo_id(self.proj_combo)
        if proj_id is None:
            QMessageBox.critical(self, "Ошибка", "Сначала загрузите проекты и выберите проект.")
            return

        for mid in models:
            schemas = api_get(f"{EXTERNAL_BASE_URL}/api/attribute-schema/projectid-jimcid",
                              EXTERNAL_HEADERS, {"projectId": proj_id, "jimcId": mid}) or []
            for s in schemas:
                sid = s["id"]
                if sid not in self.schema_data:
                    self.schema_data[sid] = {"title": s["title"], "attributes": {}}
                attrs = api_get(f"{EXTERNAL_BASE_URL}/api/attribute/attributeschemaid-jimcid",
                                EXTERNAL_HEADERS, {"attributeSchemaId": sid, "jimcId": mid}) or []
                for a in attrs:
                    aid = a["id"]
                    self.schema_data[sid]["attributes"].setdefault(aid, a["title"])

        if not self.schema_data:
            show_info_dialog("Нет доступных схем для выбранных моделей", title="Инфо", parent=self)
            return

        for sid, s in self.schema_data.items():
            self.schema_combo.addItem(s['title'], sid)
        self.on_schema_changed(self.schema_combo.currentIndex())

    def on_schema_changed(self, _idx):
        self.attr_combo.clear()
        sid = self._current_combo_id(self.schema_combo)
        if sid is None or sid not in self.schema_data:
            return
        for aid, title in self.schema_data[sid]["attributes"].items():
            self.attr_combo.addItem(title, aid)

    # --- Local projects/containers ---
    def load_local_projects(self):
        data = api_get(f"{_internal_base_url()}/project/projects", {"accept": "application/json"})
        if not data:
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить локальные проекты")
            return
        projects = data if isinstance(data, list) else [data]
        self.local_proj_combo.clear()
        for p in projects:
            if 'id' in p:
                self.local_proj_combo.addItem(p.get('title', 'Без названия'), p['id'])
        self.load_local_containers()

    def load_local_containers(self):
        for i in reversed(range(self.container_layout.count()-1)):
            item = self.container_layout.itemAt(i)
            w = item.widget()
            if w: w.setParent(None)
        self.checked_containers.clear()
        self.container_titles.clear()

        proj_id = self._current_combo_id(self.local_proj_combo)
        if proj_id is None:
            return

        data = api_get(f"{_internal_base_url()}/imcContainer/getProjectImcContainers/{proj_id}",
                       {"accept": "application/json"}) or []

        containers = data if isinstance(data, list) else [data]
        for c in containers:
            cid = c["id"]
            title = c.get("title", "Без названия")
            cb = QCheckBox(f"{title}")
            self.container_layout.insertWidget(self.container_layout.count()-1, cb)
            self.checked_containers[cid] = cb
            self.container_titles[cid] = title

        self.refresh_container_highlights()

    # --- Matching & highlighting ---
    def refresh_container_highlights(self):
        """Подсветка и сортировка контейнеров по совпадению базовых имён с отмеченными моделями."""
        selected_norms = {normalize_name(cb.text()) for cb in self.checked_models.values() if cb.isChecked()}

        widgets = []
        for i in range(self.container_layout.count()-1):
            w = self.container_layout.itemAt(i).widget()
            if isinstance(w, QCheckBox):
                widgets.append(w)

        for w in widgets:
            is_match = normalize_name(w.text()) in selected_norms
            w.setProperty("matched", is_match)
            w.style().unpolish(w); w.style().polish(w)

        widgets_sorted = sorted(widgets, key=lambda x: (0 if x.property("matched") else 1, x.text().lower()))

        for w in widgets_sorted:
            self.container_layout.removeWidget(w)
        for idx, w in enumerate(widgets_sorted):
            self.container_layout.insertWidget(idx, w)

    # --- Sync ---
    def start_sync(self):
        code = self.param_code.text().strip()
        value = self.value_entry.text().strip()
        if not code or not value:
            _popup_error(self, "Заполните параметры")
            return
        if self.attr_combo.count() == 0:
            _popup_error(self, "Выберите атрибут")
            return

        schema_id = self._current_combo_id(self.schema_combo)
        attr_id = self._current_combo_id(self.attr_combo)
        if None in (schema_id, attr_id):
            _popup_error(self, "Не удалось получить ID схемы/атрибута")
            return

        selected_models = [(mid, cb.text()) for mid, cb in self.checked_models.items() if cb.isChecked()]
        if not selected_models:
            _popup_error(self, "Выберите модели")
            return

        selected_containers = [(cid, self.container_titles.get(cid, "")) for cid, cb in self.checked_containers.items() if cb.isChecked()]
        if not selected_containers:
            _popup_error(self, "Выберите контейнеры")
            return

        self.log("✅ Начинаем синхронизацию")

        # Собираем nativeId по каждой модели отдельно (для более точных логов)
        model_native = {}  # mid -> set(nativeIds)
        union_native = set()
        for mid, _name in selected_models:
            values = api_get(
                f"{EXTERNAL_BASE_URL}/api/attribute-value/jimcid-attributeid",
                EXTERNAL_HEADERS, {"jimcId": mid, "attributeId": attr_id}
            ) or []
            s = set()
            for v in values:
                if v.get("nid") is not None and v.get("value") is not None:
                    s.add(str(v["nid"]))
            model_native[mid] = s
            union_native |= s

        if not union_native:
            self.log("🟡 Нет элементов с заполненным атрибутом")
            return

        self.log(f"✅ Найдено {len(union_native)} элементов с значением")

        # Подготовим мапу: нормализованное имя -> список моделей с таким именем
        norm_to_models = {}
        for mid, name in selected_models:
            norm = normalize_name(name)
            norm_to_models.setdefault(norm, []).append(name)

        total = 0
        for container_id, container_title in selected_containers:
            # Пытаемся определить имя модели для логов по совпадению названий
            matched_model_names = norm_to_models.get(normalize_name(container_title), [])
            pretty_model = ", ".join(matched_model_names) if matched_model_names else None

            elements = api_get(f"{_internal_base_url()}/imcElement/imcElements/{container_id}",
                               {"accept": "application/json"}) or []
            if not isinstance(elements, list):
                continue

            # Сопоставляем по union натив-идов (оставляя логи по модели при наличии имени)
            matched_ids = [
                (e.get("id") or e.get("Id"))
                for e in elements
                if str(e.get("nativeId") or e.get("NativeId")) in union_native
            ]
            matched_ids = [x for x in matched_ids if x is not None]

            if not matched_ids:
                if pretty_model:
                    self.log(f"🟡 Модель {pretty_model}: нет совпадений")
                else:
                    self.log(f"🟡 Нет совпадений (контейнер: {container_title})")
                continue

            # Создание параметра, если нет
            params = api_get(f"{_internal_base_url()}/imcParameterDefinition/imcParameterDefinitions",
                             {"accept": "application/json"}, {"containerIds": container_id}) or []
            exists = any(p.get("code") == code for p in params)
            if not exists:
                create_data = {
                    "code": code, "isNumeric": False, "layer": 2, "reportColumnType": 3,
                    "title": "Создан через GUI",
                    "elementMaps": [{"containerId": container_id, "elementIds": matched_ids}],
                    "stringValue": value
                }
                create_resp = requests.post(
                    f"{_internal_base_url()}/imcParameterDefinition/imcParameterDefinition",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(create_data, ensure_ascii=False)
                )
                if create_resp.status_code in (200, 201):
                    self.log("✅ Параметр создан")
                else:
                    self.log(f"❌ Ошибка создания: {create_resp.text}")
            else:
                self.log(f"📌 Параметр '{code}' уже существует")

            # Обновление значений
            update_data = {
                "containerIds": [{"containerId": container_id, "elementIds": matched_ids}],
                "parameterCode": code,
                "isNumeric": False,
                "stringValue": value
            }
            update_resp = requests.post(
                f"{_internal_base_url()}/imcParameterValue/setAlternateValueByElements",
                headers=INTERNAL_HEADERS,
                data=json.dumps(update_data, ensure_ascii=False)
            )
            if update_resp.status_code in (200, 201):
                total += len(matched_ids)
                if pretty_model:
                    self.log(f"✅ Обновлено {len(matched_ids)} элементов — модель {pretty_model}")
                else:
                    self.log(f"✅ Обновлено {len(matched_ids)} элементов — контейнер {container_title}")
            else:
                if pretty_model:
                    self.log(f"❌ Ошибка обновления для модели {pretty_model}: {update_resp.text}")
                else:
                    self.log(f"❌ Ошибка обновления (контейнер {container_title}): {update_resp.text}")

        self.log(f"\n✅ Готово! Обновлено: {total} значений")




# --- Main ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_window_icon(app, icon_dir=ICON_DIR)
    try:
        theme(app, load_saved_theme(False), icon_dir=ICON_DIR, persist=False)
        enable_theme_sync(app, ICON_DIR)
    except Exception:
        pass
    w = MainWindow()
    w.show()
    apply_dark_titlebar(w, is_dark_theme(app))
    sys.exit(exec_app(app))
