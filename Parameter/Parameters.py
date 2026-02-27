# -*- coding: utf-8 -*-
"""
Parameters_nik_ready_v2.py
Изменения по запросу:
1) Вернул «сохранение JSON» — отдельный нижний блок в главном окне (кроме того, кнопки остаются и в диалоге сопоставления).
2) В «Файлы Excel» оставил только «Наименование профиля» и «Куда сохранить файл» (убрал выбор файла и листа).
3) «Действия»: сверху — «Сопоставление листов» и справа «Сопоставление параметров», ниже крупной кнопкой «Сгенерировать профиль». Ещё ниже — отдельный блок JSON.
   Убрал «Готов к работе» и любые статус-лейблы из главного окна.
4) «Проект и модели» перенёс под блок файлов.
"""

from __future__ import annotations
import importlib.util
import os, sys, tempfile, shutil, types, ctypes, math
from typing import NamedTuple
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Qt
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except Exception:
    from PyQt5 import QtWidgets, QtCore, QtGui  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.theme_toggle import ThemeToggle, theme, is_dark_theme, create_back_button, go_to_main_menu, load_saved_theme, enable_theme_sync
import shared.theme_toggle as _theme

# 3rd-party
try:
    import pandas as pd
except Exception:
    pd = None

try:
    import requests
except Exception:
    requests = None

try:
    from Excel_template import export_common_excel
    EXCEL_TEMPLATE_AVAILABLE = True
except Exception:
    export_common_excel = None
    EXCEL_TEMPLATE_AVAILABLE = False

APP_DIR = os.path.abspath(os.path.dirname(__file__))
APP_ROOT_DIR = os.path.dirname(APP_DIR)
ICON_DIR = os.path.join(APP_ROOT_DIR, "icon")
LOGO_LIGHT_REL = os.path.join("icon", "Manager-scaled.png")
LOGO_DARK_REL = os.path.join("icon", "Manager-scaled_white.png")
TITLEBAR_ICON_REL = os.path.join("icon", "logo.ico")


def _load_std_json_module() -> "types.ModuleType":
    """Load the stdlib json module even if a shadow module exists alongside the app."""
    try:
        import json as json_mod  # type: ignore
        if getattr(json_mod, "loads", None) and getattr(json_mod, "dumps", None):
            return json_mod
        raise ImportError("shadowed json without core api")
    except Exception:
        sys.modules.pop("json", None)
        spec = importlib.util.find_spec("json")
        if spec is None or spec.loader is None:
            raise ImportError("Unable to locate stdlib json module")
        module = importlib.util.module_from_spec(spec)
        loader = spec.loader
        if hasattr(loader, "exec_module"):
            loader.exec_module(module)  # type: ignore[attr-defined]
        else:
            module = loader.load_module(spec.name)  # type: ignore[call-arg,attr-defined]
        sys.modules["json"] = module
        return module


json = _load_std_json_module()


class _MappingRow(NamedTuple):
    label: "QtWidgets.QLabel"
    combo: "QtWidgets.QComboBox"
    status: "QtWidgets.QLabel"
    container: "QtWidgets.QWidget"


def _normalize_mapping_payload(raw: dict | None) -> dict[str, dict]:
    normalized: dict[str, dict] = {}
    for key, value in (raw or {}).items():
        try:
            name = str(key).strip()
        except Exception:
            name = ""
        if not name:
            continue
        if isinstance(value, dict):
            code = value.get("code", "")
            try:
                code = str(code or "").strip()
            except Exception:
                code = ""
            normalized[name] = {
                "code": code,
                "isNumeric": bool(value.get("isNumeric", False))
            }
        elif isinstance(value, str):
            normalized[name] = {"code": value.strip(), "isNumeric": False}
    return normalized

# --- Local style helpers (no nik_style dependency) ---
_BASE_FONT_FAMILY = "Segoe UI"
_BASE_FONT_SIZE_PT = 10
_CACHE_SUBDIR = "nik_style_cache"

class _Palette:
    BG_LIGHT = "#FFFFFF"
    BG_DARK = "#1E1E1E"
    FG_LIGHT = "#000000"
    FG_DARK = "#FFFFFF"
    ACCENT = "#F7921E"
    ACCENT_HOVER = "#FFA74B"
    ACCENT_PRESSED = "#E07E12"
    GRAY = "#D9D9D9"
    GRAY_DARK = "#3A3A3A"
    BORDER_LIGHT = "#dcdcdc"
    BORDER_DARK = "#3A3A3A"
    SOFT_HOVER = "#FFE3C2"
    SELECTED = "#FFC37A"
    SCROLL_TRACK_LIGHT = "#FAFAFA"
    SCROLL_TRACK_DARK = "#252525"
    CHECKBOX_HOVER = "#E5E5E5"

PALETTE = _Palette()

_DEKSTOP_ICON_FILES = {
    "logo":        ["Manager-scaled.png"],
    "logo_white":  ["Manager-scaled_white.png"],
    "login":       ["free-icon-login-2623062.png"],
    "folder":      ["folder_icon_variant_1.png"],
    "save":        ["free-icon-download-126488.png"],
    "plus":        ["free-icon-plus-3303893.png"],
    "gear":        ["free-icon-setting-3288004.png"],
    "eye_open":    ["free-icon-eye-2455724.png"],
    "eye_closed":  ["free-icon-hide-11238328.png"],
    "no_folder":   ["no folder.png"],
    "delete":      ["delete.png"],
    "edit":        ["edit.png"],
    "refresh":     ["free-icon-refresh-5234214.png"],
    "cad":         ["free-icon-cad-8304395.png"],
    "filter":      ["filter.png"],
    "flash":       ["flash.png"],
    "warning":     ["warning.png"],
    "structure":   ["structure.png"],
    "insert":      ["insert.png"],
    "back":        ["back.png"],
    "sync":        ["sync.png"],
    "arrow_down":  ["arrow-down.png"],
    "arrow_up":    ["arrow-up.png"],
    "arrow_right": ["arrow-right.png"],
    "arrow_left":  ["arrow-left.png"],
    "sort_up":     ["arrow-up.png"],
    "sort_down":   ["arrow-down.png"],
    "arrow_down_free": ["arrow-down.png"],
    "rotate_left":  ["rotate-left.png", "free-icon-rotate-left.png"],
    "rotate_right": ["rotate-right.png", "free-icon-rotate-right.png"],
    "sun":         ["sun.png"],
    "moon":        ["moon.png"],
    "check":       ["check.png"],
    "select":      ["select.png"],
    "circle2":     ["krug.png"],
    "circle_dot":  ["krug_galka.png"],
    "poloska":     ["poloska.png"],
    "ok":          ["ok.png"],
    "none":        ["none.png"],
    "1":           ["1.png"],
    "2":           ["2.png"],
    "extend":      ["extend.png"],
    "arrow_oba":   ["arrow-oba.png"],
    "navigation":  ["navigation.png"],
    "move":        ["move.png"],
    "compare":     ["compare.png"],
}


def _cache_dir(icon_dir: str) -> str:
    base = os.path.abspath(icon_dir or ICON_DIR)
    root = os.path.join(tempfile.gettempdir(), _CACHE_SUBDIR)
    os.makedirs(root, exist_ok=True)
    sub = os.path.join(root, os.path.basename(base) or "icon")
    os.makedirs(sub, exist_ok=True)
    return sub


def _qss_url(path: str) -> str:
    return (path or "").replace("\\", "/")


def resolve_icon_path(name: str, icon_dir: str = ICON_DIR, app=None) -> str:
    if not name:
        return ""
    if os.path.exists(name):
        return os.path.abspath(name)
    candidates = _DEKSTOP_ICON_FILES.get(name, [])
    for fname in candidates:
        path = os.path.join(icon_dir, fname)
        if os.path.exists(path):
            return path
    direct = os.path.join(icon_dir, f"{name}.png")
    if os.path.exists(direct):
        return direct
    return ""


def _tint_pixmap(pm: QtGui.QPixmap, color: QtGui.QColor) -> QtGui.QPixmap:
    if pm.isNull():
        return pm
    tinted = QtGui.QPixmap(pm.size())
    tinted.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(tinted)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    painter.drawPixmap(0, 0, pm)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()
    return tinted


def _ensure_color_copy(src_path: str, icon_dir: str, color: QtGui.QColor, suffix: str) -> str:
    if not src_path or not os.path.exists(src_path):
        return src_path
    cache = _cache_dir(icon_dir)
    base = os.path.basename(src_path)
    name, ext = os.path.splitext(base)
    dst = os.path.join(cache, f"{name}_{suffix}{ext}")
    if os.path.exists(dst):
        return dst
    pm = QtGui.QPixmap(src_path)
    if pm.isNull():
        return src_path
    pm = _tint_pixmap(pm, color)
    try:
        pm.save(dst)
        return dst
    except Exception:
        return src_path


def _ensure_white_copy(src_path: str, icon_dir: str) -> str:
    return _ensure_color_copy(src_path, icon_dir, QtGui.QColor("#FFFFFF"), "white")


def _ensure_black_copy(src_path: str, icon_dir: str) -> str:
    return _ensure_color_copy(src_path, icon_dir, QtGui.QColor("#000000"), "black")


def is_dark_theme(app: QtWidgets.QApplication | None) -> bool:
    if app is None:
        app = QtWidgets.QApplication.instance()
    if app is None:
        return False
    try:
        theme_prop = str(app.property("nik_theme") or "").strip().lower()
        if theme_prop in ("dark", "night"):
            return True
        if theme_prop in ("light", "day"):
            return False
    except Exception:
        pass
    try:
        col = app.palette().color(QtGui.QPalette.Window)
        return col.lightness() < 128
    except Exception:
        return False


def apply_themed_icon(widget_or_action, name, icon_dir=None):
    path = resolve_icon_path(name, icon_dir or ICON_DIR)
    icon = QtGui.QIcon(path) if path else QtGui.QIcon()
    try:
        widget_or_action.setIcon(icon)
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


def nik_icon(name: str, icon_dir: str = ICON_DIR) -> QtGui.QIcon:
    path = resolve_icon_path(name, icon_dir)
    return QtGui.QIcon(path) if path else QtGui.QIcon()

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
    if parent is None:
        try:
            parent = QtWidgets.QApplication.activeWindow()
        except Exception:
            parent = None
    if modal:
        QtWidgets.QMessageBox.critical(parent, title, text)
    else:
        m = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, title, text, QtWidgets.QMessageBox.Ok, parent)
        m.open()


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
    }}
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
    QComboBox:disabled {{
        background: {'#2A2A2A' if dark else '#f0f0f0'};
        color: {'#8f8f8f' if dark else '#9b9b9b'};
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
    QComboBox QAbstractItemView::item {{ padding: 4px 8px; border-radius: 8px; margin: 1px 4px; }}
    QComboBox QAbstractItemView::item:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_text}; border-radius: 8px; }}
    QComboBox QAbstractItemView::item:selected {{ background: {PALETTE.SELECTED}; color: {hover_text}; border-radius: 8px; }}

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
    QScrollBar::handle:vertical {{ background: {PALETTE.SELECTED}; min-height: 24px; border-radius: 6px; border: none; }}
    QScrollBar::handle:vertical:hover {{ background: {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:vertical:pressed {{ background: {PALETTE.ACCENT_PRESSED}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ background: {TRACK_BG}; height: 16px; subcontrol-origin: margin; border: none; margin: 0; }}
    QScrollBar::add-line:vertical {{ subcontrol-position: bottom; border: none; }}
    QScrollBar::sub-line:vertical {{ subcontrol-position: top; border: none; }}

    QScrollBar:horizontal {{ background: {TRACK_BG}; height: 12px; margin: 0 16px 0 16px; border: none; }}
    QScrollBar::handle:horizontal {{ background: {PALETTE.SELECTED}; min-width: 24px; border-radius: 6px; border: none; }}
    QScrollBar::handle:horizontal:hover {{ background: {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:horizontal:pressed {{ background: {PALETTE.ACCENT_PRESSED}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ background: {TRACK_BG}; width: 16px; subcontrol-origin: margin; border: none; margin: 0; }}
    QScrollBar::add-line:horizontal {{ subcontrol-position: right; border: none; }}
    QScrollBar::sub-line:horizontal {{ subcontrol-position: left; border: none; }}

    QScrollBar::up-arrow:vertical   {{ image: url('{ar_up}');   width: 12px; height: 12px; }}
    QScrollBar::down-arrow:vertical {{ image: url('{ar_down}'); width: 12px; height: 12px; }}
    QScrollBar::left-arrow:horizontal  {{ image: url('{ar_left}');  width: 12px; height: 12px; }}
    QScrollBar::right-arrow:horizontal {{ image: url('{ar_right}'); width: 12px; height: 12px; }}

    QScrollBar::add-page:vertical,   QScrollBar::sub-page:vertical   {{ background: {TRACK_BG}; margin: 0; border: none; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {TRACK_BG}; margin: 0; border: none; }}

    QAbstractScrollArea::corner {{ background: {TRACK_BG}; }}
    QMenu {{ border-radius: 12px; padding: 6px; }}
    QMenu::item {{ padding: 6px 10px; border-radius: 8px; }}
    QMenu::item:selected {{ background: {PALETTE.SOFT_HOVER}; }}

    QGroupBox {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
        margin-top: 16px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 8px;
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
        app.setProperty("nik_theme", theme.lower())
    dark = is_dark_theme(app)

    # Apply shared Larix Nexus-like base style first.
    try:
        _theme.theme(app, dark, icon_dir=icon_dir, persist=False)
    except Exception:
        pass

    ar_down = resolve_icon_path("arrow_down", icon_dir, app=app)
    if dark and ar_down:
        ar_down = _ensure_white_copy(ar_down, icon_dir)
    ar_up = resolve_icon_path("arrow_up", icon_dir, app=app)
    ar_right = resolve_icon_path("arrow_right", icon_dir, app=app)
    ar_left = resolve_icon_path("arrow_left", icon_dir, app=app)
    if dark and ar_left:
        ar_left = _ensure_white_copy(ar_left, icon_dir)

    cmb_down = resolve_icon_path("arrow_down", icon_dir, app=app) or ar_down
    if dark and cmb_down:
        cmb_down = _ensure_white_copy(cmb_down, icon_dir)

    chk_off = resolve_icon_path("check", icon_dir, app=app)
    chk_on = resolve_icon_path("select", icon_dir, app=app)
    chk_mid = resolve_icon_path("poloska", icon_dir, app=app)
    if dark:
        if chk_off:
            chk_off = _ensure_white_copy(chk_off, icon_dir)
        if chk_on:
            chk_on = _ensure_white_copy(chk_on, icon_dir)
        if chk_mid:
            chk_mid = _ensure_white_copy(chk_mid, icon_dir)
    else:
        if chk_off:
            chk_off = _ensure_black_copy(chk_off, icon_dir)
        if chk_on:
            chk_on = _ensure_black_copy(chk_on, icon_dir)
        if chk_mid:
            chk_mid = _ensure_black_copy(chk_mid, icon_dir)

    rchk_off = resolve_icon_path("circle2", icon_dir, app=app)
    rchk_on = resolve_icon_path("circle_dot", icon_dir, app=app)
    if dark:
        if rchk_off:
            rchk_off = _ensure_white_copy(rchk_off, icon_dir)
        if rchk_on:
            rchk_on = _ensure_white_copy(rchk_on, icon_dir)

    if dark:
        list_hover_off = _ensure_black_copy(chk_off, icon_dir) if chk_off else ""
        list_hover_on  = _ensure_black_copy(chk_on, icon_dir) if chk_on else ""
        list_hover_mid = _ensure_black_copy(chk_mid, icon_dir) if chk_mid else ""
    else:
        list_hover_off, list_hover_on, list_hover_mid = chk_off or "", chk_on or "", chk_mid or ""

    _ = (
        ar_down,
        ar_up,
        ar_left,
        ar_right,
        cmb_down,
        chk_off,
        chk_on,
        chk_mid,
        rchk_off,
        rchk_on,
        list_hover_off,
        list_hover_on,
        list_hover_mid,
    )


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
MODE_CATEGORY   = "category"
MODE_CLASSIFIER = "classifier"
MODE_BOTH       = "both"
MODE_SELECTED   = MODE_BOTH

# --- Глобальное состояние ---
SELECTED_CONTAINER_IDS = [0]
SELECTED_PROJECT_ID = None
SELECTED_PROJECT_TITLE = ""
GLOBAL_PARAM_MAPPING: dict | None = None
MASTER_MAP_CACHE: dict[str, dict] = {}
GLOBAL_COMPONENT_ID = 1
API_BASE_URL = "http://localhost:5000"

def get_api_base() -> str:
    """Получить базовый URL API."""
    return (os.environ.get("LARIX_API_BASE_URL") or API_BASE_URL).rstrip("/")


def set_api_base(url: str):
    """Установить базовый URL API."""
    global API_BASE_URL
    API_BASE_URL = url.rstrip("/")
    os.environ["LARIX_API_BASE_URL"] = API_BASE_URL

def _wb_id(path: str) -> str:
    try:
        return os.path.normcase(os.path.abspath(path or ""))
    except Exception:
        return path or ""

def _deepcopy_dict(d: dict) -> dict:
    try:
        return json.loads(json.dumps(d, ensure_ascii=False))
    except Exception:
        return dict(d or {})

def fetch_api_param_types(container_ids=None) -> dict:
    """Возвращает { 'СК10.Площадь': True, ... } по API."""
    if requests is None:
        return {}
    url = f"{get_api_base()}/api/imcParameterDefinition/imcParameterDefinitions"
    try:
        ids = container_ids or SELECTED_CONTAINER_IDS
        r = requests.get(url, params={'containerIds': ids}, headers={'accept': 'application/json'}, timeout=10)
        if r.status_code == 200:
            out = {}
            for it in (r.json() or []):
                code = (it or {}).get('code')
                if code:
                    out[code] = bool((it or {}).get('isNumeric', False))
            return out
    except Exception:
        pass
    return {}

def _is_dark_theme_local() -> bool:
    app = QtWidgets.QApplication.instance()
    return is_dark_theme(app)

def _apply_titlebar_theme(widget: QtWidgets.QWidget) -> None:
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        if hwnd == 0:
            return
    except Exception:
        return
    dark = _is_dark_theme_local()
    try:
        use_dark = ctypes.c_int(1 if dark else 0)
        try:
            dwm = ctypes.windll.dwmapi
        except Exception:
            return
        # 20 for newer Windows, 19 for older builds
        for attr in (20, 19):
            try:
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(use_dark), ctypes.sizeof(use_dark))
            except Exception:
                pass
        # Title bar colors (Windows 11+)
        caption_color = 0x000000 if dark else 0xFFFFFF
        text_color = 0xFFFFFF if dark else 0x000000
        border_color = 0x000000 if dark else 0xDCDCDC
        for attr, color in ((35, caption_color), (36, text_color), (34, border_color)):
            try:
                cval = ctypes.c_int(color)
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(cval), ctypes.sizeof(cval))
            except Exception:
                pass
    except Exception:
        pass

def _resolve_icon_path(name: str) -> str:
    candidates = [f"{name}.png"]
    if name == "circle_dot":
        candidates = ["circle dot.png", "circle_dot.png"]
    for fname in candidates:
        path = os.path.join(ICON_DIR, fname)
        if os.path.exists(path):
            return path
    return ""

def _tint_pixmap(pm: QtGui.QPixmap, color: QtGui.QColor) -> QtGui.QPixmap:
    if pm.isNull():
        return pm
    tinted = QtGui.QPixmap(pm.size())
    tinted.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(tinted)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    painter.drawPixmap(0, 0, pm)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()
    return tinted

def _load_icon_pixmap(name: str, size: int, *, tint: QtGui.QColor | None = None) -> QtGui.QPixmap:
    path = _resolve_icon_path(name)
    pm = QtGui.QPixmap(path) if path else QtGui.QPixmap()
    if not pm.isNull():
        pm = pm.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        if tint is not None:
            pm = _tint_pixmap(pm, tint)
    return pm

def _empty_messages():
    return ET.Element("Messages")

def _info_message(text: str):
    msg = ET.Element("Messages")
    sm = ET.SubElement(msg, "SignalMessage")
    ET.SubElement(sm, "Level").text = "Info"
    ET.SubElement(sm, "Text").text = text
    return msg

def save_session_mapping_json(excel_path: str, mapping: dict) -> bool:
    try:
        base_dir = os.path.dirname(excel_path) if excel_path else os.getcwd()
        path = os.path.join(base_dir, "param_mapping.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mapping or {}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_session_mapping_json(excel_path: str) -> dict:
    try:
        base_dir = os.path.dirname(excel_path) if excel_path else os.getcwd()
        path = os.path.join(base_dir, "param_mapping.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def fetch_global_component(gcid: int):
    if requests is None: return None
    url = f"{get_api_base()}/api/globalComponent/globalComponent/{int(gcid)}"
    xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
    xsd_ns = "http://www.w3.org/2001/XMLSchema"
    ET.register_namespace('xsi', xsi_ns)
    ET.register_namespace('xsd', xsd_ns)
    try:
        r = requests.get(url, headers={'accept': 'application/json'}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def _import_adapter_mapping(parent, excel_path: str) -> dict:
    if pd is None:
        _popup_error(parent, "Требуется пакет pandas для импорта адаптера.")
        return {}
    if not excel_path:
        QtWidgets.QMessageBox.warning(parent, "Внимание", "Сначала выберите файл LOIN.")
        return {}
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, "Выбор адаптера", "", "Excel (*.xlsx *.xls)")
    if not path:
        return {}
    try:
        xls = pd.ExcelFile(path)
        sheets = list(xls.sheet_names)
    except Exception as e:
        _popup_error(parent, f"Не удалось открыть файл:\n{e}")
        return {}
    if not sheets:
        _popup_error(parent, "В файле нет листов.")
        return {}
    if len(sheets) == 1:
        sheet = sheets[0]
    else:
        sheet, ok = QtWidgets.QInputDialog.getItem(parent, "Выбор листа", "Лист:", sheets, 0, False)
        if not ok or not sheet:
            return {}
    try:
        df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
    except Exception as e:
        _popup_error(parent, f"Не удалось прочитать лист:\n{e}")
        return {}

    group_name = ""
    header_row = None
    for r_idx in range(len(df_raw)):
        row = df_raw.iloc[r_idx]
        for c_idx, val in enumerate(row):
            if isinstance(val, str) and val.strip().lower() == "укажите группу параметров:":
                try:
                    next_val = row.iloc[c_idx + 1]
                    if isinstance(next_val, str):
                        group_name = next_val.strip()
                    else:
                        group_name = str(next_val).strip() if pd.notna(next_val) else ""
                except Exception:
                    group_name = ""
                break
        if header_row is not None:
            break
        row_vals = [str(v).strip().lower() for v in row.tolist() if pd.notna(v)]
        if "наименование параметра" in row_vals and "параметры" in row_vals:
            header_row = r_idx
    if header_row is None:
        _popup_error(parent, "Не удалось найти строку заголовков ('Наименование параметра' и 'Параметры').")
        return {}

    try:
        df = pd.read_excel(path, sheet_name=sheet, header=header_row)
    except Exception as e:
        _popup_error(parent, f"Не удалось прочитать таблицу:\n{e}")
        return {}

    def _find_col(cols, needle):
        needle = needle.strip().lower()
        for col in cols:
            if str(col).strip().lower() == needle:
                return col
        return None

    col_param = _find_col(df.columns, "параметры")
    col_name = _find_col(df.columns, "наименование параметра")
    if not col_param or not col_name:
        _popup_error(parent, "Не найдены столбцы 'Параметры' и 'Наименование параметра'.")
        return {}

    mapping: dict[str, dict] = {}
    for _, row in df.iterrows():
        raw_param = row.get(col_param, "")
        raw_name = row.get(col_name, "")
        if pd.isna(raw_param) or pd.isna(raw_name):
            continue
        param = str(raw_param).strip()
        name = str(raw_name).strip()
        if not param or not name:
            continue
        full_name = f"{group_name}.{name}" if group_name else name
        mapping[param] = {"code": full_name, "isNumeric": False}
    return mapping

# ----------------- Генерация PV -----------------
def excel_to_pv_profile(excel_path, output_pv_path, profile_title, sheet_name, use_classifier=False, classifier_path=None, mode="both"):
    api_types = fetch_api_param_types()
    if pd is None:
        return False, "ERROR: Требуется пакет pandas"
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=1)
        if df.shape[1] < 3:
            return False, "ERROR: Недостаточно столбцов в файле"
        df.columns = ['Раздел', 'Категория Revit', 'Пример Класса IFC'] + [str(col).strip() for col in df.columns[3:]]
        df = df.dropna(subset=['Раздел']).reset_index(drop=True)
        loi_cols = [c for c in df.columns[3:] if str(c).strip()]

        def _norm_code(text: str) -> str:
            s = (text or "").strip()
            s = s.replace("ё", "е").replace("Ё", "Е")
            for ch in (" ", "-", "/", "\\", ",", ";", ":"):
                s = s.replace(ch, "_")
            for ch in ("(", ")", "[", "]", "{", "}", "'", '"'):
                s = s.replace(ch, "")
            while "__" in s:
                s = s.replace("__", "_")
            return s.strip("_")

        # Читаем файл с кодами классификатора
        codes_map = {}
        if use_classifier and classifier_path:
            try:
                df_codes = pd.read_excel(classifier_path, sheet_name=0, header=0)
                df_codes = df_codes.dropna(how='all')
                # Колонки: 0 - название раздела, 1 - коды через запятую
                for _, row in df_codes.iterrows():
                    section_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                    codes_str = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    if section_name and codes_str:
                        # Разделяем коды по запятой
                        codes_list = [c.strip() for c in codes_str.split(',') if c.strip()]
                        codes_map[section_name] = codes_list
            except Exception as ex:
                print(f"Warning: Could not read classifier codes: {ex}")
                codes_map = {}

        # Сбор параметров
        categories = []
        validation_codes = set()
        # Группируем по разделам и собираем категории Revit
        section_data = {}
        for _, row in df.iterrows():
            section = str(row['Раздел']).strip()
            revit_cat = str(row['Категория Revit']).strip() if pd.notna(row['Категория Revit']) else ""
            
            if section not in section_data:
                section_data[section] = {
                    'revit_categories': set(),
                    'params': {}
                }
            
            # Разделяем категории по запятой
            if revit_cat:
                for cat_part in revit_cat.split(','):
                    cat_part = cat_part.strip()
                    if cat_part:
                        section_data[section]['revit_categories'].add(cat_part)
            
            for col in loi_cols:
                if col in row and pd.notna(row[col]) and str(row[col]).strip() == '+':
                    if isinstance(GLOBAL_PARAM_MAPPING, dict) and col in GLOBAL_PARAM_MAPPING:
                        code = GLOBAL_PARAM_MAPPING[col]['code']
                        is_numeric = GLOBAL_PARAM_MAPPING[col]['isNumeric']
                    else:
                        code = f"\\{col}"
                        is_numeric = col in ['Площадь', 'Объем', 'Длина', 'Ширина', 'Высота', 'Масса']
                    
                    if col not in section_data[section]['params']:
                        section_data[section]['params'][col] = {
                            'title': col, 
                            'field_name': code, 
                            'is_numeric': is_numeric
                        }
                    validation_codes.add((code, is_numeric))
        
        # Формируем итоговый список категорий
        for section, data in section_data.items():
            if data['params']:
                categories.append({
                    'title': section,
                    'revit_categories': sorted(list(data['revit_categories'])),
                    'classifier_codes': codes_map.get(section, []),
                    'params': list(data['params'].values())
                })

        # Генерация XML
        root = ET.Element("ExportProfilesCollection", {
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
        })
        profiles = ET.SubElement(root, "Profiles")
        base_profile = ET.SubElement(profiles, "BaseExportProfile", {"xsi:type": "ParameterValidationExportProfile"})
        ET.SubElement(base_profile, "Id").text = "0"
        ET.SubElement(base_profile, "Title").text = profile_title
        items = ET.SubElement(base_profile, "ProfileItems")
        item_id = 1838

        for cat in categories:
            item_id += 1
            parent_id = item_id
            folder = ET.SubElement(items, "BaseExportProfileItem", {"xsi:type": "ParameterValidationExportProfileItem"})
            ET.SubElement(folder, "Id").text = str(parent_id)
            ET.SubElement(folder, "ParentId", {"xsi:nil": "true"})
            ET.SubElement(folder, "Title").text = cat['title']
            ET.SubElement(folder, "IsFolder").text = "true"
            ET.SubElement(folder, "ExtFieldParamCodes")

            fcb = ET.SubElement(folder, "FilteringConditionBlock", {
                "Type": "Block", "LogicalOperator": "Or", "IsNegative": "false", "IsEnabled": "true"
            })
            fcb_signal = ET.SubElement(fcb, "Signal")
            fcb_signal.append(_empty_messages())
            fcb_condition = ET.SubElement(fcb, "Condition", {
                "FieldName": "", "FieldIsNumeric": "false", "Operator": "Equal", "Value": "",
                "TextCaseSensitive": "false", "TextSpaceSensitive": "true", "IsUndefinedFieldName": "false"
            })
            fcb_condition_signal = ET.SubElement(fcb_condition, "Signal")
            fcb_condition_signal.append(_info_message("Имя не указано"))
            cb = ET.SubElement(fcb, "ConditionsBlocks")
            
            # Логика фильтров в зависимости от mode:
            # "category" - только категории из LOIN
            # "classifier" - только коды из файла Коды
            # "both" - и категории, и коды (через Or)
            
            if mode == "category":
                # Только фильтры по категориям Revit
                for revit_cat in cat['revit_categories']:
                    cat_cond_block = ET.SubElement(cb, "ConditionsBlock", {
                        "Type": "Single", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
                    })
                    cat_cond_signal = ET.SubElement(cat_cond_block, "Signal")
                    cat_cond_signal.append(_empty_messages())
                    
                    cat_condition = ET.SubElement(cat_cond_block, "Condition", {
                        "FieldName": "Категория:\\", 
                        "FieldIsNumeric": "false", 
                        "Operator": "Equal", 
                        "Value": revit_cat,
                        "TextCaseSensitive": "false", 
                        "TextSpaceSensitive": "false", 
                        "IsUndefinedFieldName": "false"
                    })
                    cat_condition_signal = ET.SubElement(cat_condition, "Signal")
                    cat_condition_signal.append(_empty_messages())
                    ET.SubElement(cat_cond_block, "ConditionsBlocks")
                    
            elif mode == "classifier":
                # Только фильтры по кодам классификатора
                for code in cat['classifier_codes']:
                    code_cond_block = ET.SubElement(cb, "ConditionsBlock", {
                        "Type": "Single", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
                    })
                    code_cond_signal = ET.SubElement(code_cond_block, "Signal")
                    code_cond_signal.append(_empty_messages())
                    
                    code_condition = ET.SubElement(code_cond_block, "Condition", {
                        "FieldName": "Тип:\\Код по классификатору", 
                        "FieldIsNumeric": "false", 
                        "Operator": "Equal", 
                        "Value": code,
                        "TextCaseSensitive": "false", 
                        "TextSpaceSensitive": "false", 
                        "IsUndefinedFieldName": "false"
                    })
                    code_condition_signal = ET.SubElement(code_condition, "Signal")
                    code_condition_signal.append(_empty_messages())
                    ET.SubElement(code_cond_block, "ConditionsBlocks")
                    
            elif mode == "both":
                # Сначала фильтры по категориям
                for revit_cat in cat['revit_categories']:
                    cat_cond_block = ET.SubElement(cb, "ConditionsBlock", {
                        "Type": "Single", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
                    })
                    cat_cond_signal = ET.SubElement(cat_cond_block, "Signal")
                    cat_cond_signal.append(_empty_messages())
                    
                    cat_condition = ET.SubElement(cat_cond_block, "Condition", {
                        "FieldName": "Категория:\\", 
                        "FieldIsNumeric": "false", 
                        "Operator": "Equal", 
                        "Value": revit_cat,
                        "TextCaseSensitive": "false", 
                        "TextSpaceSensitive": "false", 
                        "IsUndefinedFieldName": "false"
                    })
                    cat_condition_signal = ET.SubElement(cat_condition, "Signal")
                    cat_condition_signal.append(_empty_messages())
                    ET.SubElement(cat_cond_block, "ConditionsBlocks")
                
                # Потом фильтры по кодам классификатора
                for code in cat['classifier_codes']:
                    code_cond_block = ET.SubElement(cb, "ConditionsBlock", {
                        "Type": "Single", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
                    })
                    code_cond_signal = ET.SubElement(code_cond_block, "Signal")
                    code_cond_signal.append(_empty_messages())
                    
                    code_condition = ET.SubElement(code_cond_block, "Condition", {
                        "FieldName": "Тип:\\Код по классификатору", 
                        "FieldIsNumeric": "false", 
                        "Operator": "Equal", 
                        "Value": code,
                        "TextCaseSensitive": "false", 
                        "TextSpaceSensitive": "false", 
                        "IsUndefinedFieldName": "false"
                    })
                    code_condition_signal = ET.SubElement(code_condition, "Signal")
                    code_condition_signal.append(_empty_messages())
                    ET.SubElement(code_cond_block, "ConditionsBlocks")

            ET.SubElement(folder, "ParentFilteringProfileItemId", {"xsi:nil": "true"})
            vcb = ET.SubElement(folder, "ValidatingConditionBlock", {
                "Type": "Block", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
            })
            vcb_signal = ET.SubElement(vcb, "Signal")
            vcb_signal.append(_info_message("Нет ни одного включенного условия в наборе условий"))
            vcb_condition = ET.SubElement(vcb, "Condition", {
                "FieldName": "", "FieldIsNumeric": "false", "Operator": "Equal", "Value": "",
                "TextCaseSensitive": "false", "TextSpaceSensitive": "true", "IsUndefinedFieldName": "false"
            })
            vcb_condition_signal = ET.SubElement(vcb_condition, "Signal")
            vcb_condition_signal.append(_info_message("Имя не указано"))
            ET.SubElement(vcb, "ConditionsBlocks")

            # Создаем дочерние параметры (всегда, независимо от mode)
            for param in cat['params']:
                item_id += 1
                child = ET.SubElement(items, "BaseExportProfileItem", {"xsi:type": "ParameterValidationExportProfileItem"})
                ET.SubElement(child, "Id").text = str(item_id)
                ET.SubElement(child, "ParentId").text = str(parent_id)
                ET.SubElement(child, "Title").text = param['title']
                ET.SubElement(child, "IsFolder").text = "true"
                ET.SubElement(child, "ExtFieldParamCodes")
                
                # FilteringConditionBlock for child
                fcb_child = ET.SubElement(child, "FilteringConditionBlock", {
                    "Type": "Block", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
                })
                fcb_child_signal = ET.SubElement(fcb_child, "Signal")
                fcb_child_signal.append(_info_message("Нет ни одного включенного условия в наборе условий"))
                fcb_child_condition = ET.SubElement(fcb_child, "Condition", {
                    "FieldName": "", "FieldIsNumeric": "true", "Operator": "Equal", "Value": "",
                    "TextCaseSensitive": "false", "TextSpaceSensitive": "false", "IsUndefinedFieldName": "false"
                })
                fcb_child_condition_signal = ET.SubElement(fcb_child_condition, "Signal")
                fcb_child_condition_signal.append(_info_message("Имя не указано"))
                ET.SubElement(fcb_child, "ConditionsBlocks")
                
                ET.SubElement(child, "ParentFilteringProfileItemId", {"xsi:nil": "true"})
                
                # ValidatingConditionBlock for child
                vcb_child = ET.SubElement(child, "ValidatingConditionBlock", {
                    "Type": "Block", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
                })
                vcb_child_signal = ET.SubElement(vcb_child, "Signal")
                vcb_child_signal.append(_empty_messages())
                vcb_child_condition = ET.SubElement(vcb_child, "Condition", {
                    "FieldName": "", "FieldIsNumeric": "false", "Operator": "Equal", "Value": "",
                    "TextCaseSensitive": "false", "TextSpaceSensitive": "true", "IsUndefinedFieldName": "false"
                })
                vcb_child_condition_signal = ET.SubElement(vcb_child_condition, "Signal")
                vcb_child_condition_signal.append(_info_message("Имя не указано"))
                
                conditions_blocks = ET.SubElement(vcb_child, "ConditionsBlocks")
                single_cond = ET.SubElement(conditions_blocks, "ConditionsBlock", {
                    "Type": "Single", "LogicalOperator": "And", "IsNegative": "false", "IsEnabled": "true"
                })
                single_cond_signal = ET.SubElement(single_cond, "Signal")
                single_cond_signal.append(_empty_messages())
                
                op = "More" if param['is_numeric'] else "Default"
                val = "0" if param['is_numeric'] else ""
                cond = ET.SubElement(single_cond, "Condition", {
                    "FieldName": param['field_name'], "FieldIsNumeric": str(param['is_numeric']).lower(),
                    "Operator": op, "Value": val, "TextCaseSensitive": "false",
                    "TextSpaceSensitive": "false", "Layer": "-1", "IsUndefinedFieldName": "false"
                })
                cond_signal = ET.SubElement(cond, "Signal")
                cond_signal.append(_empty_messages())
                ET.SubElement(single_cond, "ConditionsBlocks")

        # ValidationParameters
        validation_params = ET.SubElement(base_profile, "ValidationParameters")
        param_id = 505
        for code, is_numeric in sorted(validation_codes):
            param_id += 1
            dto = ET.SubElement(validation_params, "ValidationParameterDto")
            ET.SubElement(dto, "Id").text = str(param_id)
            ET.SubElement(dto, "ProfileId").text = "0"
            ET.SubElement(dto, "Code").text = code
            ET.SubElement(dto, "IsNumeric").text = str(is_numeric).lower()

        # Сохранение
        rough = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
        # Удаляем пустые строки
        pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
        # Добавляем пробел перед /> для всех самозакрывающихся тегов
        pretty_xml = pretty_xml.replace('/>', ' />')
        with open(output_pv_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        return True, f"OK: Профиль '{profile_title}' из листа '{sheet_name}' сохранён: {output_pv_path}"
    except Exception as ex:
        return False, f"ERROR: Ошибка генерации: {ex}"


# ----------------- UI -----------------
class _NoWheelFilter(QtCore.QObject):
    def eventFilter(self, obj, e):
        if isinstance(obj, QtWidgets.QComboBox) and e.type() == QtCore.QEvent.Wheel:
            return True
        return super().eventFilter(obj, e)


class ReorderListWidget(QtWidgets.QListWidget):
    reordered = QtCore.Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setStyleSheet("border: none;")
    def dropEvent(self, e):
        super().dropEvent(e)
        try:
            self.reordered.emit()
        except Exception:
            pass
    def eventFilter(self, obj, e):
        if isinstance(obj, QtWidgets.QComboBox) and e.type() == QtCore.QEvent.Wheel:
            return True
        return super().eventFilter(obj, e)

class Section(QtWidgets.QGroupBox):
    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)
        lay = QtWidgets.QGridLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)
        self.frame_l = lay


class MappingDialog(QtWidgets.QDialog):
    def __init__(self, excel_path, sheet_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сопоставление параметров")
        self.resize(760, 780)
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        QtCore.QTimer.singleShot(0, lambda: _apply_titlebar_theme(self))

        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(16,12,16,16); v.setSpacing(8)

        # Заголовок + тема
        top = QtWidgets.QHBoxLayout(); v.addLayout(top)
        # Add icon before title
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setFixedSize(24, 24)
        top.addWidget(icon_lbl)
        lbl = QtWidgets.QLabel(""); top.addWidget(lbl, 1)
        self.btn_import_adapter = QtWidgets.QPushButton("Импорт адаптера")
        top.addWidget(self.btn_import_adapter)
        self.theme_switch = ThemeSwitch(icon_dir=ICON_DIR); top.addWidget(self.theme_switch)
        self.theme_switch.toggledTheme.connect(lambda _: _apply_titlebar_theme(self))

        search_row = QtWidgets.QHBoxLayout(); v.addLayout(search_row, 0)
        search_row.addWidget(QtWidgets.QLabel("Поиск:"), 0)
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Найдите нужные параметры из Excel или API...")
        try:
            self.search_edit.setClearButtonEnabled(True)
        except Exception:
            pass
        search_row.addWidget(self.search_edit, 1)

        # Скролл
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); v.addWidget(scroll, 1)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("border: none;")
        wrap = QtWidgets.QWidget(); self.form = QtWidgets.QFormLayout(wrap)
        self.form.setContentsMargins(12, 10, 12, 10)
        self.form.setHorizontalSpacing(12)
        self.form.setVerticalSpacing(6)
        self.form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.form.setFormAlignment(QtCore.Qt.AlignTop)
        scroll.setWidget(wrap)

        self.rows: list[_MappingRow] = []
        self.search_edit.textChanged.connect(self._apply_param_filter)
        self.search_edit.textChanged.connect(self._apply_param_filter)
        self.mapping = self._load_existing_mapping()
        self.prefill = bool(GLOBAL_PARAM_MAPPING)
        self.excel_params = self._load_excel_params()
        self.api_params = self._load_api_params()
        self.api_codes = [p['code'] for p in self.api_params]

        # Шапка колонок
        self.form.addRow(QtWidgets.QLabel("Параметр из Excel"), QtWidgets.QLabel("Соответствие в API"))

        for name in self.excel_params:
            lbl = QtWidgets.QLabel(name, parent=wrap)
            cmb = QtWidgets.QComboBox(parent=wrap)
            cmb.setStyleSheet(
                "QComboBox QAbstractItemView { background-color: #FFFFFF; selection-background-color: #F4B183; selection-color: #000000; border: 1px solid #F4B183; border-radius: 8px; }"
            )
            cmb.setEditable(False); cmb.addItem("- не выбрано -"); cmb.addItems(self.api_codes)
            if not hasattr(self, "_wf"): self._wf = _NoWheelFilter(self)
            cmb.installEventFilter(self._wf)
            st = QtWidgets.QLabel(parent=wrap)  # статус-иконка ok/none
            st.setFixedSize(20, 20)
            st.setAlignment(QtCore.Qt.AlignCenter)
            st.setScaledContents(True)
            mapping_code = ""
            if self.prefill and isinstance(GLOBAL_PARAM_MAPPING, dict) and name in GLOBAL_PARAM_MAPPING:
                mapping_code = str(GLOBAL_PARAM_MAPPING[name].get("code") or "").strip()
            st.setPixmap(_style_pix("ok") if mapping_code else _style_pix("none"))

            row_widget = QtWidgets.QWidget(parent=wrap)
            h = QtWidgets.QHBoxLayout(row_widget); h.setContentsMargins(4,0,4,0); h.setSpacing(6)
            h.addWidget(cmb, 1); h.addWidget(st)

            self.form.addRow(lbl, row_widget)

            # префилл
            if self.prefill and isinstance(GLOBAL_PARAM_MAPPING, dict) and name in GLOBAL_PARAM_MAPPING and mapping_code:
                if mapping_code not in self.api_codes:
                    cmb.addItem(mapping_code)
                cmb.setCurrentText(mapping_code); st.setPixmap(_style_pix("ok"))
            else:
                cmb.setCurrentIndex(0); st.setPixmap(_style_pix("none"))

            def on_change(idx, s=st, c=cmb):
                txt = c.currentText().strip()
                s.setPixmap(_style_pix("ok") if (idx > 0 and txt and txt != "- не выбрано -") else _style_pix("none"))
            cmb.currentIndexChanged.connect(on_change)

            self.rows.append(_MappingRow(lbl, cmb, st, row_widget))

        self.btn_import_adapter.clicked.connect(self.import_adapter)

        # Нижняя полоса JSON-кнопок (оставляю и тут)
        json_row = QtWidgets.QHBoxLayout(); v.addLayout(json_row, 0)
        json_row.setSpacing(8)
        self.btn_json_save = QtWidgets.QPushButton("Сохранить JSON")
        self.btn_json_import = QtWidgets.QPushButton("Импорт JSON")
        self.btn_json_clear = QtWidgets.QPushButton("Очистить сопоставление")
        json_row.addWidget(self.btn_json_save)
        json_row.addStretch(1)
        json_row.addWidget(self.btn_json_import)
        json_row.addStretch(1)
        json_row.addWidget(self.btn_json_clear)

        # Ок/Отмена
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        v.addWidget(btns)
        btns.accepted.connect(self._save_and_close); btns.rejected.connect(self.reject)

        mw = self.parent() if isinstance(self.parent(), (MainWindow, MainWindowMaster)) else None
        if mw:
            self.btn_json_save.clicked.connect(mw.save_json_master)
            self.btn_json_import.clicked.connect(mw.import_json_master)
            self.btn_json_clear.clicked.connect(mw.clear_master)

    def _apply_mapping_to_rows(self):
        for row in self.rows:
            name = row.label.text()
            code = ""
            if isinstance(GLOBAL_PARAM_MAPPING, dict) and name in GLOBAL_PARAM_MAPPING:
                code = str(GLOBAL_PARAM_MAPPING[name].get("code") or "").strip()
            if code:
                if code not in self.api_codes:
                    row.combo.addItem(code)
                row.combo.setCurrentText(code)
                row.status.setPixmap(_style_pix("ok"))
            else:
                row.combo.setCurrentIndex(0)
                row.status.setPixmap(_style_pix("none"))

    def import_adapter(self):
        mapping = _import_adapter_mapping(self, self.excel_path)
        if not mapping:
            return
        wb = _wb_id(self.excel_path or "")
        MASTER_MAP_CACHE[wb] = _deepcopy_dict(mapping)
        global GLOBAL_PARAM_MAPPING
        GLOBAL_PARAM_MAPPING = _deepcopy_dict(mapping)
        try:
            save_session_mapping_json(self.excel_path, mapping)
        except Exception:
            pass
        self._apply_mapping_to_rows()
        QtWidgets.QMessageBox.information(self, "Готово", f"Импортировано: {len(mapping)} параметров.")

    def _apply_param_filter(self, text: str):
        pattern = (text or "").strip().lower()
        for row in self.rows:
            current = row.combo.currentText()
            row.combo.blockSignals(True)
            row.combo.clear()
            row.combo.addItem("- не выбрано -")
            for code in self.api_codes:
                if not pattern or pattern in str(code).lower():
                    row.combo.addItem(code)
            if current and current != "- не выбрано -" and current not in self.api_codes:
                row.combo.addItem(current)
            row.combo.setCurrentText(current)
            row.combo.blockSignals(False)

    def _load_existing_mapping(self) -> dict:
        try:
            base_dir = os.path.dirname(self.excel_path) if self.excel_path else os.getcwd()
            path = os.path.join(base_dir, "param_mapping.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                m = {}
                for k, v in (loaded or {}).items():
                    if isinstance(v, dict) and 'code' in v:
                        m[k] = {'code': v['code'], 'isNumeric': v.get('isNumeric', False)}
                self.mapping_file = path
                return m
        except Exception:
            pass
        self.mapping_file = os.path.join(os.path.dirname(self.excel_path) if self.excel_path else os.getcwd(), "param_mapping.json")
        return {}

    def _load_excel_params(self) -> list:
        if pd is None: return []
        try:
            df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name, header=1)
            return [str(c).strip() for c in df.columns[3:] if str(c).strip()]
        except Exception:
            return []

    def _load_api_params(self) -> list:
        items = []
        if requests is None: return items
        url = f"{get_api_base()}/api/imcParameterDefinition/imcParameterDefinitions"
        try:
            r = requests.get(url, params={'containerIds': SELECTED_CONTAINER_IDS}, headers={'accept': 'application/json'}, timeout=10)
            if r.status_code == 200:
                for it in (r.json() or []):
                    code = (it or {}).get('code')
                    if code: items.append({'code': code, 'isNumeric': bool((it or {}).get('isNumeric', False))})
        except Exception:
            pass
        try:
            gc = fetch_global_component(GLOBAL_COMPONENT_ID)
            if gc:
                gc_code = gc.get('code') or f"GlobalComponent:{gc.get('id', GLOBAL_COMPONENT_ID)}"
                if all(x['code'] != gc_code for x in items):
                    items.append({'code': gc_code, 'isNumeric': False})
        except Exception:
            pass
        return sorted(items, key=lambda x: x['code'])

    def _save_and_close(self):
        global GLOBAL_PARAM_MAPPING
        new_map = {}
        for row in self.rows:
            name = row.label.text()
            txt = row.combo.currentText().strip()
            if txt == "- не выбрано -" or not txt:
                new_map[name] = {'code': '', 'isNumeric': False}
            else:
                api_item = next((it for it in self.api_params if it['code'] == txt), None)
                if api_item:
                    new_map[name] = {'code': api_item['code'], 'isNumeric': api_item['isNumeric']}
                else:
                    new_map[name] = {'code': txt, 'isNumeric': False}
        GLOBAL_PARAM_MAPPING = new_map
        try:
            save_session_mapping_json(self.excel_path, new_map)
        except Exception:
            pass
        self.accept()

class MappingDialogMaster(MappingDialog):
    def __init__(self, excel_path, sheet_name, parent=None):
        self._wb_id = _wb_id(excel_path)
        global GLOBAL_PARAM_MAPPING
        GLOBAL_PARAM_MAPPING = _deepcopy_dict(MASTER_MAP_CACHE.get(self._wb_id, {}))
        super().__init__(excel_path, sheet_name, parent)

    def _save_and_close(self):
        try:
            new_map = {}
            for row in self.rows:
                name = row.label.text()
                txt = row.combo.currentText().strip()
                if txt == "- не выбрано -" or not txt:
                    new_map[name] = {'code': '', 'isNumeric': False}
                else:
                    api_item = None
                    for it in self.api_params:
                        if it['code'] == txt: api_item = it; break
                    new_map[name] = {'code': (api_item['code'] if api_item else txt), 'isNumeric': bool(api_item and api_item.get('isNumeric', False))}
            MASTER_MAP_CACHE[self._wb_id] = _deepcopy_dict(new_map)
            global GLOBAL_PARAM_MAPPING
            GLOBAL_PARAM_MAPPING = _deepcopy_dict(new_map)
            self.accept()
        except Exception as e:
            _popup_error(self, f"Не удалось сохранить сопоставление:\n{e}")
        
class MappingDialogLarix(QtWidgets.QDialog):
    """Диалог сопоставления параметров в стиле Larix_Set.
    C нуля собирает форму, но использует ту же бизнес-логику.
    """
    def __init__(self, excel_path, sheet_name, parent=None):
        super().__init__(parent)
        self._wb_id = _wb_id(excel_path)
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self.setWindowTitle("Сопоставление параметров")
        self.resize(760, 780)

        # Инициализируем глобальную карту из кеша книги
        global GLOBAL_PARAM_MAPPING
        GLOBAL_PARAM_MAPPING = _deepcopy_dict(MASTER_MAP_CACHE.get(self._wb_id, {}))

        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(16,12,16,16); v.setSpacing(8)
        top = QtWidgets.QHBoxLayout(); v.addLayout(top)
        # Add icon before title
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setFixedSize(24, 24)
        top.addWidget(icon_lbl)
        top.addWidget(QtWidgets.QLabel(""), 1)
        self.btn_import_adapter = QtWidgets.QPushButton("Импорт адаптера")
        top.addWidget(self.btn_import_adapter)
        self.theme_switch = ThemeSwitch(icon_dir=ICON_DIR); top.addWidget(self.theme_switch)
        self.theme_switch.toggledTheme.connect(lambda _: _apply_titlebar_theme(self))
        QtCore.QTimer.singleShot(0, lambda: _apply_titlebar_theme(self))

        search_row = QtWidgets.QHBoxLayout(); v.addLayout(search_row, 0)
        search_row.addWidget(QtWidgets.QLabel("Поиск:"), 0)
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Найдите нужные параметры из Excel или API...")
        try:
            self.search_edit.setClearButtonEnabled(True)
        except Exception:
            pass
        search_row.addWidget(self.search_edit, 1)

        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); v.addWidget(scroll, 1)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("border: none;")
        wrap = QtWidgets.QWidget(); self.form = QtWidgets.QFormLayout(wrap)
        self.form.setContentsMargins(12, 10, 12, 10)
        self.form.setHorizontalSpacing(12)
        self.form.setVerticalSpacing(6)
        self.form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.form.setFormAlignment(QtCore.Qt.AlignTop)
        scroll.setWidget(wrap)

        self.rows: list[_MappingRow] = []
        self.search_edit.textChanged.connect(self._apply_param_filter)
        self.mapping = self._load_existing_mapping()
        self.excel_params = self._load_excel_params()
        self.api_params = self._load_api_params()
        self.api_codes = [p['code'] for p in self.api_params]
        self.prefill = bool(GLOBAL_PARAM_MAPPING)

        # Заголовки
        self.form.addRow(QtWidgets.QLabel("Параметр из Excel"), QtWidgets.QLabel("Соответствие в API"))

        for name in self.excel_params:
            lbl = QtWidgets.QLabel(name, parent=wrap)
            cmb = QtWidgets.QComboBox(parent=wrap)
            cmb.setStyleSheet(
                "QComboBox QAbstractItemView { background-color: #FFFFFF; selection-background-color: #F4B183; selection-color: #000000; border: 1px solid #F4B183; border-radius: 8px; }"
            )
            cmb.setEditable(False); cmb.addItem("- не выбрано -"); cmb.addItems(self.api_codes)
            if not hasattr(self, "_wf"): self._wf = _NoWheelFilter(self)
            cmb.installEventFilter(self._wf)
            st = QtWidgets.QLabel(parent=wrap)
            st.setFixedSize(20, 20)
            st.setAlignment(QtCore.Qt.AlignCenter)
            st.setScaledContents(True)
            mapping_code = ""
            if self.prefill and isinstance(GLOBAL_PARAM_MAPPING, dict) and name in GLOBAL_PARAM_MAPPING:
                mapping_code = str(GLOBAL_PARAM_MAPPING[name].get("code") or "").strip()
            st.setPixmap(_style_pix("ok") if mapping_code else _style_pix("none"))

            row_widget = QtWidgets.QWidget(parent=wrap)
            h = QtWidgets.QHBoxLayout(row_widget); h.setContentsMargins(4,0,4,0); h.setSpacing(6)
            h.addWidget(cmb, 1); h.addWidget(st)
            self.form.addRow(lbl, row_widget)

            # префил
            if self.prefill and isinstance(GLOBAL_PARAM_MAPPING, dict) and name in GLOBAL_PARAM_MAPPING and mapping_code:
                if mapping_code not in self.api_codes:
                    cmb.addItem(mapping_code)
                cmb.setCurrentText(mapping_code)
                st.setPixmap(_style_pix("ok"))
            else:
                cmb.setCurrentIndex(0)
                st.setPixmap(_style_pix("none"))

            def on_change(idx, s=st, c=cmb):
                txt = c.currentText().strip()
                s.setPixmap(_style_pix("ok") if (idx > 0 and txt and txt != "- не выбрано -") else _style_pix("none"))
            cmb.currentIndexChanged.connect(on_change)

            self.rows.append(_MappingRow(lbl, cmb, st, row_widget))

        self.btn_import_adapter.clicked.connect(self.import_adapter)

        # JSON действия
        json_row = QtWidgets.QHBoxLayout(); v.addLayout(json_row, 0)
        json_row.setSpacing(8)
        self.btn_json_save = QtWidgets.QPushButton("Сохранить JSON")
        self.btn_json_import = QtWidgets.QPushButton("Импорт JSON")
        self.btn_json_clear = QtWidgets.QPushButton("Очистить сопоставление")
        json_row.addWidget(self.btn_json_save)
        json_row.addStretch(1)
        json_row.addWidget(self.btn_json_import)
        json_row.addStretch(1)
        json_row.addWidget(self.btn_json_clear)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        v.addWidget(btns)
        btns.accepted.connect(self._save_and_close); btns.rejected.connect(self.reject)

        mw = self.parent() if isinstance(self.parent(), (MainWindow, MainWindowMaster)) else None
        if mw:
            self.btn_json_save.clicked.connect(mw.save_json_master)
            self.btn_json_import.clicked.connect(lambda: self._on_import_from_parent(mw))
            self.btn_json_clear.clicked.connect(lambda: self._on_clear_from_parent(mw))

    def _on_import_from_parent(self, parent_window):
        """Обработчик импорта JSON из родительского окна с обновлением."""
        parent_window.import_json_master()
        # Обновляем данные диалога после импорта
        self._refresh_mapping_from_cache()

    def _on_clear_from_parent(self, parent_window):
        """Обработчик очистки с обновлением."""
        parent_window.clear_master()
        # Обновляем данные диалога после очистки
        self._refresh_mapping_from_cache()

    def _refresh_mapping_from_cache(self):
        """Обновить сопоставления из глобального кеша."""
        global GLOBAL_PARAM_MAPPING
        GLOBAL_PARAM_MAPPING = _deepcopy_dict(MASTER_MAP_CACHE.get(self._wb_id, {}))
        
        # Обновляем все комбобоксы согласно новым данным
        for row in self.rows:
            name = row.label.text()
            if isinstance(GLOBAL_PARAM_MAPPING, dict) and name in GLOBAL_PARAM_MAPPING:
                mapping_data = GLOBAL_PARAM_MAPPING[name]
                code = mapping_data.get("code", "") if isinstance(mapping_data, dict) else str(mapping_data)
                code = code.strip()
                if code and code in self.api_codes:
                    try:
                        idx = 1 + self.api_codes.index(code)
                        row.combo.setCurrentIndex(idx)
                        row.status.setPixmap(_style_pix("ok"))
                    except (ValueError, IndexError):
                        row.combo.setCurrentIndex(0)
                        row.status.setPixmap(_style_pix("none"))
                else:
                    row.combo.setCurrentIndex(0)
                    row.status.setPixmap(_style_pix("none"))
            else:
                row.combo.setCurrentIndex(0)
                row.status.setPixmap(_style_pix("none"))

    def _apply_param_filter(self, text: str):
        pattern = (text or "").strip().lower()
        for row in self.rows:
            current = row.combo.currentText()
            row.combo.blockSignals(True)
            row.combo.clear()
            row.combo.addItem("- не выбрано -")
            for code in self.api_codes:
                if not pattern or pattern in str(code).lower():
                    row.combo.addItem(code)
            if current and current != "- не выбрано -" and current not in self.api_codes:
                row.combo.addItem(current)
            row.combo.setCurrentText(current)
            row.combo.blockSignals(False)

    def _load_existing_mapping(self) -> dict:
        try:
            base_dir = os.path.dirname(self.excel_path) if self.excel_path else os.getcwd()
            path = os.path.join(base_dir, "param_mapping.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                m = {}
                for k, v in (loaded or {}).items():
                    if isinstance(v, dict) and 'code' in v:
                        m[k] = {'code': v['code'], 'isNumeric': v.get('isNumeric', False)}
                self.mapping_file = path
                return m
        except Exception:
            pass
        self.mapping_file = os.path.join(os.path.dirname(self.excel_path) if self.excel_path else os.getcwd(), "param_mapping.json")
        return {}

    def _load_excel_params(self) -> list:
        if pd is None: return []
        try:
            df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name, header=1)
            return [str(c).strip() for c in df.columns[3:] if str(c).strip()]
        except Exception:
            return []

    def _load_api_params(self) -> list:
        items = []
        if requests is None: return items
        url = f"{get_api_base()}/api/imcParameterDefinition/imcParameterDefinitions"
        try:
            r = requests.get(url, params={'containerIds': SELECTED_CONTAINER_IDS}, headers={'accept': 'application/json'}, timeout=10)
            if r.status_code == 200:
                for it in (r.json() or []):
                    code = (it or {}).get('code')
                    if code: items.append({'code': code, 'isNumeric': bool((it or {}).get('isNumeric', False))})
        except Exception:
            pass
        try:
            gc = fetch_global_component(GLOBAL_COMPONENT_ID)
            if gc:
                gc_code = gc.get('code') or f"GlobalComponent:{gc.get('id', GLOBAL_COMPONENT_ID)}"
                if all(x['code'] != gc_code for x in items):
                    items.append({'code': gc_code, 'isNumeric': False})
        except Exception:
            pass
        return sorted(items, key=lambda x: x['code'])

    def _save_and_close(self):
        try:
            new_map = {}
            for row in self.rows:
                name = row.label.text()
                txt = row.combo.currentText().strip()
                if txt == "- не выбрано -" or not txt:
                    new_map[name] = {'code': '', 'isNumeric': False}
                else:
                    api_item = None
                    for it in self.api_params:
                        if it['code'] == txt: api_item = it; break
                    new_map[name] = {'code': (api_item['code'] if api_item else txt), 'isNumeric': bool(api_item and api_item.get('isNumeric', False))}
            MASTER_MAP_CACHE[self._wb_id] = _deepcopy_dict(new_map)
            global GLOBAL_PARAM_MAPPING
            GLOBAL_PARAM_MAPPING = _deepcopy_dict(new_map)
            try:
                save_session_mapping_json(self.excel_path, new_map)
            except Exception:
                pass
            self.accept()
        except Exception as e:
            _popup_error(self, f"Не удалось сохранить сопоставление:\n{e}")

    def _apply_mapping_to_rows(self):
        for row in self.rows:
            name = row.label.text()
            code = ""
            if isinstance(GLOBAL_PARAM_MAPPING, dict) and name in GLOBAL_PARAM_MAPPING:
                code = str(GLOBAL_PARAM_MAPPING[name].get("code") or "").strip()
            if code:
                if code not in self.api_codes:
                    row.combo.addItem(code)
                row.combo.setCurrentText(code)
                row.status.setPixmap(_style_pix("ok"))
            else:
                row.combo.setCurrentIndex(0)
                row.status.setPixmap(_style_pix("none"))

    def import_adapter(self):
        mapping = _import_adapter_mapping(self, self.excel_path)
        if not mapping:
            return
        wb = _wb_id(self.excel_path or "")
        MASTER_MAP_CACHE[wb] = _deepcopy_dict(mapping)
        global GLOBAL_PARAM_MAPPING
        GLOBAL_PARAM_MAPPING = _deepcopy_dict(mapping)
        try:
            save_session_mapping_json(self.excel_path, mapping)
        except Exception:
            pass
        self._apply_mapping_to_rows()
        QtWidgets.QMessageBox.information(self, "Готово", f"Импортировано: {len(mapping)} параметров.")
# --------- Диалог сопоставления листов ---------


class PairPickerDialog(QtWidgets.QDialog):
    """
    Двухпанельный выбор листов (как в Larix_set_nik):
    - Без двойных рамок у списков (NoFrame).
    - Кнопки добавления с иконкой стрелки.
    - Режимы с иконками вместо стандартных кружков.
    - Внизу выбранные списки с нумерацией и перетаскиванием элементов.
    """
    def __init__(self, parent=None, init_mode="both", init_cat=None, init_cls=None):
        super().__init__(parent)
        # Do not recolor checkboxes on hover in dark theme in this dialog
        try:
            self.setProperty("noCheckHoverRecolor", True)
            self.style().unpolish(self); self.style().polish(self)
        except Exception:
            pass
        self.setWindowTitle("Выбор листов Excel - парное сопоставление")
        self.resize(1080, 680)
        self._mode = init_mode
        self._cat_list = [dict(x) for x in (init_cat or [])]
        self._cls_list = [dict(x) for x in (init_cls or [])]
        QtCore.QTimer.singleShot(0, lambda: _apply_titlebar_theme(self))

        v = QtWidgets.QVBoxLayout(self)

        
        # Верх: две панели
        top = QtWidgets.QHBoxLayout(); v.addLayout(top, 1)

        # Левая панель — Категории
        grp_cat = QtWidgets.QGroupBox("Категории / LOI"); top.addWidget(grp_cat, 1)
        gl = QtWidgets.QVBoxLayout(grp_cat); gl.setContentsMargins(8,8,8,8); gl.setSpacing(8)
        row_cat_pick = QtWidgets.QHBoxLayout(); gl.addLayout(row_cat_pick)
        self.ed_cat = QtWidgets.QLineEdit(); self.ed_cat.setReadOnly(True); row_cat_pick.addWidget(self.ed_cat, 1)
        self.btn_cat_file = QtWidgets.QPushButton("Файл"); row_cat_pick.addWidget(self.btn_cat_file)
        self.lst_cat_sheets = QtWidgets.QListWidget(); gl.addWidget(self.lst_cat_sheets, 1)
        self.lst_cat_sheets.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lst_cat_sheets.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lst_cat_sheets.setStyleSheet("border: none;")
        row_cat_actions1 = QtWidgets.QHBoxLayout(); gl.addLayout(row_cat_actions1)
        self.btn_cat_check_all = QtWidgets.QPushButton("Выделить все")
        self.btn_cat_uncheck_all = QtWidgets.QPushButton("Снять все")
        row_cat_actions1.addWidget(self.btn_cat_check_all); row_cat_actions1.addWidget(self.btn_cat_uncheck_all); row_cat_actions1.addStretch(1)
        # gl.addStretch(1)
        row_cat_actions1.addStretch(1)
        self.btn_cat_add_selected = QtWidgets.QPushButton()
        self.btn_cat_add_selected.setText("Добавить отмеченные")
        # toolbutton style not needed for QPushButton
        apply_themed_icon_with_arrow(self.btn_cat_add_selected, "arrow_right", ICON_DIR)
        # row_cat_actions2.addStretch(1)
        row_cat_actions1.addWidget(self.btn_cat_add_selected)

        # Правая панель — Классификатор
        grp_cls = QtWidgets.QGroupBox("Классификатор"); top.addWidget(grp_cls, 1)
        gr = QtWidgets.QVBoxLayout(grp_cls); gr.setContentsMargins(8,8,8,8); gr.setSpacing(8)
        row_cls_pick = QtWidgets.QHBoxLayout(); gr.addLayout(row_cls_pick)
        self.ed_cls = QtWidgets.QLineEdit(); self.ed_cls.setReadOnly(True); row_cls_pick.addWidget(self.ed_cls, 1)
        self.btn_cls_file = QtWidgets.QPushButton("Файл"); row_cls_pick.addWidget(self.btn_cls_file)
        self.lst_cls_sheets = QtWidgets.QListWidget(); gr.addWidget(self.lst_cls_sheets, 1)
        self.lst_cls_sheets.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lst_cls_sheets.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lst_cls_sheets.setStyleSheet("border: none;")
        row_cls_actions1 = QtWidgets.QHBoxLayout(); gr.addLayout(row_cls_actions1)
        self.btn_cls_check_all = QtWidgets.QPushButton("Выделить все")
        self.btn_cls_uncheck_all = QtWidgets.QPushButton("Снять все")
        row_cls_actions1.addWidget(self.btn_cls_check_all); row_cls_actions1.addWidget(self.btn_cls_uncheck_all); row_cls_actions1.addStretch(1)
        # gr.addStretch(1)
        row_cls_actions1.addStretch(1)
        self.btn_cls_add_selected = QtWidgets.QPushButton()
        self.btn_cls_add_selected.setText("Добавить отмеченные")
        # toolbutton style not needed for QPushButton
        apply_themed_icon_with_arrow(self.btn_cls_add_selected, "arrow_right", ICON_DIR)
        # row_cls_actions2.addStretch(1)
        row_cls_actions1.addWidget(self.btn_cls_add_selected)

        # Низ: выбранные листы — перетаскивание + нумерация
        bottom = QtWidgets.QHBoxLayout(); bottom.setSpacing(12); v.addLayout(bottom, 1)
        sec_cat_selected = Section("Выбранные листы (Категории)"); bottom.addWidget(sec_cat_selected, 1)
        self.lst_cat_selected = ReorderListWidget()
        self.lst_cat_selected.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lst_cat_selected.setStyleSheet("border: none;")
        sec_cat_selected.frame_l.addWidget(self.lst_cat_selected, 0, 0)

        center = QtWidgets.QVBoxLayout(); bottom.addLayout(center)
        self.btn_up = QtWidgets.QPushButton("Вверх")
        self.btn_down = QtWidgets.QPushButton("Вниз")
        self.btn_del = QtWidgets.QPushButton("Удалить")
        center.addStretch(1); center.addWidget(self.btn_up); center.addWidget(self.btn_down); center.addWidget(self.btn_del); center.addStretch(1)

        sec_cls_selected = Section("Выбранные листы (Классификатор)"); bottom.addWidget(sec_cls_selected, 1)
        self.lst_cls_selected = ReorderListWidget()
        self.lst_cls_selected.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lst_cls_selected.setStyleSheet("border: none;")
        sec_cls_selected.frame_l.addWidget(self.lst_cls_selected, 0, 0)

        # Низ: ОК/Отмена
        row_ok = QtWidgets.QHBoxLayout(); v.addLayout(row_ok)
        row_ok.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_ok = QtWidgets.QPushButton("OK")
        row_ok.addWidget(self.btn_cancel); row_ok.addWidget(self.btn_ok)

        # Сигналы
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._accept)
        self.btn_cat_file.clicked.connect(lambda: self._pick_file("cat"))
        self.btn_cls_file.clicked.connect(lambda: self._pick_file("cls"))
        self.btn_cat_check_all.clicked.connect(lambda: self._check_all(self.lst_cat_sheets, True))
        self.btn_cat_uncheck_all.clicked.connect(lambda: self._check_all(self.lst_cat_sheets, False))
        self.btn_cls_check_all.clicked.connect(lambda: self._check_all(self.lst_cls_sheets, True))
        self.btn_cls_uncheck_all.clicked.connect(lambda: self._check_all(self.lst_cls_sheets, False))
        self.btn_cat_add_selected.clicked.connect(lambda: self._add_selected(self.lst_cat_sheets, "cat"))
        self.btn_cls_add_selected.clicked.connect(lambda: self._add_selected(self.lst_cls_sheets, "cls"))
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down.clicked.connect(self._move_down)
        self.btn_del.clicked.connect(self._delete_selected)
        self.lst_cat_selected.reordered.connect(lambda: self._renumber_lists())
        self.lst_cls_selected.reordered.connect(lambda: self._renumber_lists())

        # Инициализация
        self._refresh_selected_lists()
        self._apply_mode()

    def _pick_file(self, side: str):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выбор книги Excel", "", "Excel (*.xlsx *.xls)")
        if not path: return
        if side == "cat":
            self.ed_cat.setText(path); self._fill_sheets(path, self.lst_cat_sheets)
        else:
            self.ed_cls.setText(path); self._fill_sheets(path, self.lst_cls_sheets)

    def _fill_sheets(self, path: str, widget: QtWidgets.QListWidget):
        widget.clear()
        names = []
        try:
            import pandas as pd
            names = list(pd.ExcelFile(path).sheet_names)
        except Exception:
            names = []
        for name in names:
            it = QtWidgets.QListWidgetItem(name, widget)
            it.setFlags(it.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            it.setCheckState(QtCore.Qt.Unchecked)

    def _check_all(self, widget: QtWidgets.QListWidget, state: bool):
        for i in range(widget.count()):
            it = widget.item(i); it.setCheckState(QtCore.Qt.Checked if state else QtCore.Qt.Unchecked)

    def _add_selected(self, source: QtWidgets.QListWidget, side: str):
        file_path = self.ed_cat.text() if side == "cat" else self.ed_cls.text()
        if not file_path: return
        added = False
        for i in range(source.count()):
            it = source.item(i)
            if it.checkState() == QtCore.Qt.Checked:
                row = {"path": file_path, "sheet": it.text()}
                store = self._cat_list if side == "cat" else self._cls_list
                if not any((x.get("path")==row["path"] and x.get("sheet")==row["sheet"]) for x in store):
                    store.append(row); added = True
        if added:
            self._refresh_selected_lists()

    def _refresh_selected_lists(self):
        self.lst_cat_selected.clear(); self.lst_cls_selected.clear()
        for idx, row in enumerate(self._cat_list):
            txt = f"{idx+1}. {os.path.basename(row['path'])} - {row['sheet']}"
            self.lst_cat_selected.addItem(txt)
        for idx, row in enumerate(self._cls_list):
            txt = f"{idx+1}. {os.path.basename(row['path'])} - {row['sheet']}"
            self.lst_cls_selected.addItem(txt)

    def _renumber_lists(self):
        # просто пере-подписать согласно текущему порядку
        items = []
        for i in range(self.lst_cat_selected.count()):
            items.append(self.lst_cat_selected.item(i).text())
        # rebuild labels using stored lists
        self._refresh_selected_lists()

    def _focused_list(self) -> QtWidgets.QListWidget|None:
        if self.lst_cat_selected.hasFocus(): return self.lst_cat_selected
        if self.lst_cls_selected.hasFocus(): return self.lst_cls_selected
        return None

    def _move_up(self):
        w = self._focused_list()
        if not w: return
        store = self._cat_list if w is self.lst_cat_selected else self._cls_list
        r = w.currentRow()
        if r > 0:
            store[r-1], store[r] = store[r], store[r-1]
            self._refresh_selected_lists(); w.setCurrentRow(r-1)

    def _move_down(self):
        w = self._focused_list()
        if not w: return
        store = self._cat_list if w is self.lst_cat_selected else self._cls_list
        r = w.currentRow()
        if 0 <= r < len(store)-1:
            store[r+1], store[r] = store[r], store[r+1]
            self._refresh_selected_lists(); w.setCurrentRow(r+1)

    def _delete_selected(self):
        w = self._focused_list()
        # If no focus, try to determine which list has a current item
        if not w:
            if self.lst_cat_selected.currentRow() >= 0:
                w = self.lst_cat_selected
            elif self.lst_cls_selected.currentRow() >= 0:
                w = self.lst_cls_selected
        if not w:
            return
        store = self._cat_list if w is self.lst_cat_selected else self._cls_list
        rows = sorted({i.row() for i in w.selectedIndexes()}, reverse=True)
        # If no selected indexes, use current row
        if not rows and w.currentRow() >= 0:
            rows = [w.currentRow()]
        for r in rows:
            if 0 <= r < len(store):
                store.pop(r)
        self._refresh_selected_lists()

    def _apply_mode(self):
        mode = globals().get("MODE_SELECTED", "both")
        need_cat = (mode in ("category","both"))
        need_cls = (mode in ("classifier","both"))
        # включаем/выключаем панели в зависимости от режима
        for w, need in ((self.lst_cat_sheets, need_cat), (self.lst_cls_sheets, need_cls)):
            parent = w.parentWidget().parentWidget() if hasattr(w.parentWidget(), "parentWidget") else None
            if parent and isinstance(parent, QtWidgets.QGroupBox):
                parent.setEnabled(need)

    def _accept(self):
        # использовать режим из главного окна
        mode = globals().get("MODE_SELECTED", "both")
        need_cat = (mode in ("category", "both"))
        need_cls = (mode in ("classifier", "both"))
        if need_cat and not self._cat_list:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Добавьте хотя бы один лист для категорий."); return
        if need_cls and not self._cls_list:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Добавьте хотя бы один лист для классификатора."); return
        self.accept()

    def result(self):
        mode = globals().get("MODE_SELECTED", "both")
        return {"mode": mode, "cat": self._cat_list, "cls": self._cls_list}

# --------- Окно выбора проекта/моделей ---------
class MultiCheckListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def keyPressEvent(self, e):
        if e.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            sel = self.selectedItems()
            if sel:
                any_un = any(it.checkState() != QtCore.Qt.Checked for it in sel)
                for it in sel: it.setCheckState(QtCore.Qt.Checked if any_un else QtCore.Qt.Unchecked)
                return
        super().keyPressEvent(e)

class ProjectSelectionWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Larix.Manager - Выбор проекта и моделей")
        self.resize(640, 520)
        self.project_list = []
        self._bulk_checking = False
        v = QtWidgets.QVBoxLayout(self)
        # Настройка адреса API
        api_row = QtWidgets.QHBoxLayout(); v.addLayout(api_row)
        api_row.addWidget(QtWidgets.QLabel("API:"))
        self.ed_api_base = QtWidgets.QLineEdit(get_api_base()); api_row.addWidget(self.ed_api_base, 1)
        self.btn_save_api = QtWidgets.QPushButton("Сменить"); api_row.addWidget(self.btn_save_api)
        self.btn_save_api.clicked.connect(self._save_api_base)


        form = QtWidgets.QGridLayout(); v.addLayout(form)
        form.addWidget(QtWidgets.QLabel("Проект:"), 0, 0)
        self.cmb_project = QtWidgets.QComboBox(); form.addWidget(self.cmb_project, 0, 1, 1, 2)
        self.btn_load_containers = QtWidgets.QPushButton("Загрузить модели"); form.addWidget(self.btn_load_containers, 1, 0, 1, 3)

        self.list_containers = MultiCheckListWidget(self); v.addWidget(self.list_containers, 1)
        btn_row = QtWidgets.QHBoxLayout(); v.addLayout(btn_row)
        self.btn_select_all = QtWidgets.QPushButton("Выбрать всё")
        self.btn_clear_selection = QtWidgets.QPushButton("Снять выделение")
        btn_row.addWidget(self.btn_select_all)
        btn_row.addWidget(self.btn_clear_selection)
        btn_row.addStretch(1)
        self.log_lbl = QtWidgets.QLabel("Готов к работе"); v.addWidget(self.log_lbl)
        self.btn_next = QtWidgets.QPushButton("Далее"); v.addWidget(self.btn_next)

        self.btn_load_containers.clicked.connect(self.load_containers)
        self.btn_next.clicked.connect(self.on_next)
        self.list_containers.itemChanged.connect(self._on_container_item_changed)
        self.btn_select_all.clicked.connect(lambda: self._set_all_containers_checked(True))
        self.btn_clear_selection.clicked.connect(lambda: self._set_all_containers_checked(False))
        self.list_containers.itemSelectionChanged.connect(self._on_container_selection_changed)
        QtCore.QTimer.singleShot(0, lambda: _apply_titlebar_theme(self))
        self.load_projects()

    def log(self, t): self.log_lbl.setText(t); QtWidgets.QApplication.processEvents()
    
    def _save_api_base(self):
        url = (self.ed_api_base.text() or "").strip().rstrip("/")
        if not url:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Адрес API пустой"); return
        set_api_base(url)
        self.log(f"API изменен: {url}")
        self.load_projects()

    def _set_all_containers_checked(self, checked: bool):
        self._bulk_checking = True
        try:
            state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            for i in range(self.list_containers.count()):
                it = self.list_containers.item(i)
                if it is not None:
                    it.setCheckState(state)
            if not checked:
                self.list_containers.clearSelection()
        finally:
            self._bulk_checking = False

    def _on_container_item_changed(self, item: QtWidgets.QListWidgetItem):
        if self._bulk_checking:
            return
        if item is None:
            return
        if not item.isSelected():
            item.setSelected(True)
        sel = self.list_containers.selectedItems()
        if len(sel) <= 1:
            return
        self._bulk_checking = True
        try:
            state = item.checkState()
            for it in sel:
                if it is not item:
                    it.setCheckState(state)
        finally:
            self._bulk_checking = False

    def _on_container_selection_changed(self):
        if self._bulk_checking:
            return
        if self.list_containers.selectedItems():
            self._bulk_checking = True
            try:
                self.list_containers.clearSelection()
            finally:
                self._bulk_checking = False


    def load_projects(self):
        if requests is None: self.log("requests не установлен"); return
        url = f"{get_api_base()}/api/project/projects"
        try:
            r = requests.get(url, headers={"accept":"application/json"}); r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                self.project_list = [(p.get("id"), p.get("title")) for p in data]
                self.cmb_project.clear(); self.cmb_project.addItems([t for _, t in self.project_list])
                self.log("Проекты загружены")
            else:
                self.log("Ответ API не список")
        except Exception as e:
            self.log(f"Ошибка: {e}")

    def load_containers(self):
        self.list_containers.clear()
        pid = None
        for _pid, title in self.project_list:
            if title == self.cmb_project.currentText():
                pid = _pid; break
        if not pid: self.log("Не выбран проект"); return
        if requests is None: self.log("requests не установлен"); return
        url = f"{get_api_base()}/api/imcContainer/getProjectImcContainers/{pid}"
        try:
            r = requests.get(url, headers={"accept":"application/json"})
            if r.status_code == 200:
                data = r.json()
                containers = [(it.get("id"), it.get("title")) for it in (data if isinstance(data, list) else [data])]
                for cid, title in containers:
                    it = QtWidgets.QListWidgetItem(title, self.list_containers)
                    it.setFlags(it.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    it.setCheckState(QtCore.Qt.Unchecked); it.setData(QtCore.Qt.UserRole, cid)
                self.log(f"Загружено {len(containers)} моделей")
            else:
                self.log(f"Ошибка: {r.status_code}")
        except Exception as e:
            self.log(f"Ошибка: {e}")

    def on_next(self):
        sel = []
        for i in range(self.list_containers.count()):
            it = self.list_containers.item(i)
            if it.checkState() == QtCore.Qt.Checked: sel.append(it.data(QtCore.Qt.UserRole))
        if not sel:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Выберите хотя бы одну модель."); return
        global SELECTED_CONTAINER_IDS, SELECTED_PROJECT_ID, SELECTED_PROJECT_TITLE
        SELECTED_CONTAINER_IDS = sel
        for pid, title in self.project_list:
            if title == self.cmb_project.currentText():
                SELECTED_PROJECT_ID, SELECTED_PROJECT_TITLE = pid, title; break
        self.accept()

# --------- Главное окно ---------

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Do not recolor checkboxes on hover in dark theme in this window
        try:
            self.setProperty("noCheckHoverRecolor", True)
            self.style().unpolish(self); self.style().polish(self)
        except Exception:
            pass
        self.setWindowTitle("Larix.Manager - Создание профилей проверок")
        self.resize(920, 640)

        # state
        self.input_file = ""
        self.sheet_name = ""
        self.output_file = "ExportProfile.pv"
        self.last_output_dir = ""
        self.profile_title = "Профиль проверки параметров"
        self.classifier_file = ""

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central); v.setContentsMargins(12,10,12,12); v.setSpacing(8)
        v.setAlignment(QtCore.Qt.AlignTop)

        # header with back button and theme toggle
        header = QtWidgets.QHBoxLayout(); v.addLayout(header)
        self._btn_back = create_back_button(self, icon_dir=ICON_DIR)
        self._btn_back.clicked.connect(lambda: go_to_main_menu(self))
        header.addWidget(self._btn_back)
        header.addStretch(1)
        self._theme_toggle = ThemeToggle(self)
        self._theme_toggle.setChecked(is_dark_theme(QtWidgets.QApplication.instance()))
        self._theme_toggle.toggled.connect(self._on_theme_toggled)
        header.addWidget(self._theme_toggle)
        QtCore.QTimer.singleShot(0, lambda: _apply_titlebar_theme(self))

        # --- Файлы (имя профиля + путь сохранения) ---
        files_widget = QtWidgets.QWidget(); form = QtWidgets.QGridLayout(files_widget)
        v.addWidget(files_widget)
        form.setColumnStretch(0, 0)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(2, 0)
        form.addWidget(QtWidgets.QLabel("Наименование профиля:"), 0, 0)
        self.edit_title = QtWidgets.QLineEdit(self.profile_title); form.addWidget(self.edit_title, 0, 1, 1, 2)

        # --- Источник данных (радио + выбор файлов Excel) ---
        grp_source = QtWidgets.QGroupBox("Источник данных"); v.addWidget(grp_source)
        sbox = QtWidgets.QVBoxLayout(grp_source); sbox.setContentsMargins(10,6,10,8)
        sbox.setSpacing(6)
        row_modes = QtWidgets.QHBoxLayout(); sbox.addLayout(row_modes)
        self.rb_cat = QtWidgets.QRadioButton("По категориям")
        self.rb_cls = QtWidgets.QRadioButton("По классификатору")
        self.rb_both = QtWidgets.QRadioButton("Оба")
        sel = globals().get("MODE_SELECTED", MODE_BOTH)
        if sel == MODE_CATEGORY: self.rb_cat.setChecked(True)
        elif sel == MODE_CLASSIFIER: self.rb_cls.setChecked(True)
        else: self.rb_both.setChecked(True)
        for rb in (self.rb_cat, self.rb_cls, self.rb_both):
            try:
                rb.setProperty("noCheckHoverRecolor", True)
            except Exception:
                pass
            row_modes.addWidget(rb)

        # bind radio -> mode
        def _set_mode():
            globals()["MODE_SELECTED"] = MODE_BOTH if self.rb_both.isChecked() else (MODE_CLASSIFIER if self.rb_cls.isChecked() else MODE_CATEGORY)
            self._refresh_source_mode_icons()
            disable_classifier = self.rb_cat.isChecked()
            self.ed_codes_file.setEnabled(not disable_classifier)
            self.btn_codes_file.setEnabled(not disable_classifier)
            self.cmb_codes_sheet.setEnabled(not disable_classifier)
        self.rb_cat.toggled.connect(_set_mode)
        self.rb_cls.toggled.connect(_set_mode)
        self.rb_both.toggled.connect(_set_mode)
        self._hide_source_mode_indicators()
        self._refresh_source_mode_icons()

        # Таблица выбора Excel файлов (4 строки x 3 столбца)
        excel_grid = QtWidgets.QGridLayout(); sbox.addLayout(excel_grid)
        excel_grid.setContentsMargins(0, 8, 0, 0)
        excel_grid.setHorizontalSpacing(12)
        excel_grid.setVerticalSpacing(8)

        # Строка 1: LOIN - файл
        excel_grid.addWidget(QtWidgets.QLabel("LOIN (файл):"), 0, 0)
        self.ed_loin_file = QtWidgets.QLineEdit(); self.ed_loin_file.setReadOnly(True)
        self.ed_loin_file.setPlaceholderText("Выберите файл Excel для LOIN")
        excel_grid.addWidget(self.ed_loin_file, 0, 1)
        self.btn_loin_file = QtWidgets.QPushButton("Выбрать файл"); excel_grid.addWidget(self.btn_loin_file, 0, 2)

        # Строка 2: LOIN - лист
        excel_grid.addWidget(QtWidgets.QLabel("LOIN (лист):"), 1, 0)
        self.cmb_loin_sheet = QtWidgets.QComboBox()
        self.cmb_loin_sheet.setPlaceholderText("Выберите лист")
        excel_grid.addWidget(self.cmb_loin_sheet, 1, 1, 1, 2)

        # Строка 3: Коды - файл
        excel_grid.addWidget(QtWidgets.QLabel("Коды (файл):"), 2, 0)
        self.ed_codes_file = QtWidgets.QLineEdit(); self.ed_codes_file.setReadOnly(True)
        self.ed_codes_file.setPlaceholderText("Выберите файл Excel для Кодов")
        excel_grid.addWidget(self.ed_codes_file, 2, 1)
        self.btn_codes_file = QtWidgets.QPushButton("Выбрать файл"); excel_grid.addWidget(self.btn_codes_file, 2, 2)

        # Строка 4: Коды - лист
        excel_grid.addWidget(QtWidgets.QLabel("Коды (лист):"), 3, 0)
        self.cmb_codes_sheet = QtWidgets.QComboBox()
        self.cmb_codes_sheet.setPlaceholderText("Выберите лист")
        excel_grid.addWidget(self.cmb_codes_sheet, 3, 1, 1, 2)

        # Связываем кнопки
        self.btn_loin_file.clicked.connect(self.select_loin_file)
        self.btn_codes_file.clicked.connect(self.select_codes_file)
        self.cmb_loin_sheet.currentTextChanged.connect(self.on_loin_sheet_changed)
        self.cmb_codes_sheet.currentTextChanged.connect(self.on_codes_sheet_changed)
        _set_mode()

        # --- Выбор моделей (как такая же полоса) ---
        grp_models = QtWidgets.QGroupBox("Выбор моделей"); v.addWidget(grp_models)
        mbox = QtWidgets.QHBoxLayout(grp_models); mbox.setContentsMargins(10,6,10,8)
        mbox.setSpacing(8)
        mbox.addWidget(QtWidgets.QLabel("Модели:"))
        self.ed_models_summary = QtWidgets.QLineEdit(self._models_summary_text()); self.ed_models_summary.setReadOnly(True)
        mbox.addWidget(self.ed_models_summary, 1)
        self.btn_choose_models = QtWidgets.QPushButton("Выбрать")
        mbox.addWidget(self.btn_choose_models)
        self.btn_choose_models.clicked.connect(self.choose_models)

        # --- Сопоставление параметров ---
        grp_map = QtWidgets.QGroupBox("Сопоставление параметров"); v.addWidget(grp_map)
        mapbox = QtWidgets.QHBoxLayout(grp_map); mapbox.setContentsMargins(10,6,10,8)
        mapbox.setSpacing(8)
        mapbox.addWidget(QtWidgets.QLabel("Сопоставление:"))
        self.ed_map_summary = QtWidgets.QLineEdit("Не настроено"); self.ed_map_summary.setReadOnly(True)
        mapbox.addWidget(self.ed_map_summary, 1)
        self.btn_mapping = QtWidgets.QPushButton("Открыть")
        mapbox.addWidget(self.btn_mapping)
        self.btn_mapping.clicked.connect(self.open_mapping)

        # --- Нижняя большая кнопка "Сгенерировать профиль" ---
        self.btn_generate = QtWidgets.QPushButton("Сгенерировать профиль")
        f = self.btn_generate.font(); f.setPointSize(f.pointSize()+10); f.setBold(True); self.btn_generate.setFont(f)
        self.btn_generate.setMinimumHeight(48)
        v.addWidget(self.btn_generate, 0, QtCore.Qt.AlignHCenter)
        for grp in (grp_source, grp_models, grp_map):
            grp.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        v.addStretch(1)
        self.btn_generate.clicked.connect(self._on_generate_click)

        # --- Дополнительный стиль для оранжевой рамки при hover (как в Dekstop.py) ---
        # Этот стиль добавляется поверх базового оформления для усиления визуального эффекта
        extra_button_style = """
            QPushButton:hover { 
                border-color: #FFA74B !important; 
            }
            QPushButton:pressed {
                border-color: #F7921E !important;
            }
        """
        try:
            current_style = self.styleSheet()
            self.setStyleSheet(current_style + extra_button_style)
        except Exception:
            pass

    def _hide_source_mode_indicators(self):
        try:
            try:
                fg = self.palette().color(QtGui.QPalette.Text)
                text_color = fg.name()
            except Exception:
                text_color = "#000000"
            ss = (
                "QRadioButton::indicator{min-width:0px;max-width:0px;min-height:0px;max-height:0px;width:0px;height:0px;margin:0px;padding:0px;border:none;image:none;} "
                "QRadioButton{spacing:6px;padding-left:0px;"
                f"color:{text_color};" "}"
            )
            for rb in (self.rb_cat, self.rb_cls, self.rb_both):
                rb.setStyleSheet(ss)
                rb.setIcon(QtGui.QIcon())
        except Exception:
            pass

    def _apply_source_mode_icon(self, rb: QtWidgets.QRadioButton, icon_name: str):
        try:
            path = resolve_icon_path(icon_name, ICON_DIR)
            if is_dark_theme(QtWidgets.QApplication.instance()) and path:
                path = _ensure_white_copy(path, ICON_DIR)
            rb.setIcon(QtGui.QIcon(path) if path else QtGui.QIcon())
            rb.setIconSize(QtCore.QSize(18, 18))
            filt = getattr(rb, "_nik_hover_filter", None)
            if isinstance(filt, QtCore.QObject):
                try:
                    rb.removeEventFilter(filt)
                except Exception:
                    pass
            setattr(rb, "_nik_hover_filter", None)
            try:
                rb.setMouseTracking(False)
            except Exception:
                pass
            try:
                rb.setProperty("noCheckHoverRecolor", True)
            except Exception:
                pass
            try:
                style = rb.style()
                if style is not None:
                    style.unpolish(rb); style.polish(rb)
            except Exception:
                pass
        except Exception:
            pass

    def _refresh_source_mode_icons(self):
        for rb in (self.rb_cat, self.rb_cls, self.rb_both):
            icon_name = "circle_dot" if rb.isChecked() else "circle2"
            self._apply_source_mode_icon(rb, icon_name)

    def _on_theme_toggled(self, dark: bool):
        app = QtWidgets.QApplication.instance()
        theme(app, dark, icon_dir=ICON_DIR)
        self._refresh_source_mode_icons()
        _apply_titlebar_theme(self)

    # --- helpers ---
    def _models_summary_text(self):
        if SELECTED_PROJECT_TITLE and SELECTED_CONTAINER_IDS and SELECTED_CONTAINER_IDS != [0]:
            return f"Проект: {SELECTED_PROJECT_TITLE} • моделей выбрано: {len(SELECTED_CONTAINER_IDS)}"
        return "Не выбрано"

    def choose_models(self):
        dlg = ProjectSelectionWindow()
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.ed_models_summary.setText(self._models_summary_text())
            self.setWindowTitle(f"Larix.Manager - Профиль: {SELECTED_PROJECT_TITLE or ''}")

    def select_loin_file(self):
        """Выбор Excel файла для LOIN (категорий)."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выбор файла LOIN", "", "Excel (*.xlsx *.xls)")
        if path:
            self.input_file = path
            self.ed_loin_file.setText(os.path.basename(path))
            # Загружаем листы в комбобокс
            self.cmb_loin_sheet.clear()
            try:
                if pd is not None:
                    sheets = list(pd.ExcelFile(path).sheet_names)
                    if sheets:
                        self.cmb_loin_sheet.addItems(sheets)
                        self.cmb_loin_sheet.setCurrentIndex(0)
                        self.sheet_name = sheets[0]
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить листы из файла:\n{e}")

    def select_codes_file(self):
        """Выбор Excel файла для Кодов (классификатора)."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выбор файла Коды", "", "Excel (*.xlsx *.xls)")
        if path:
            self.classifier_file = path
            self.ed_codes_file.setText(os.path.basename(path))
            # Загружаем листы в комбобокс
            self.cmb_codes_sheet.clear()
            try:
                if pd is not None:
                    sheets = list(pd.ExcelFile(path).sheet_names)
                    if sheets:
                        self.cmb_codes_sheet.addItems(sheets)
                        self.cmb_codes_sheet.setCurrentIndex(0)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить листы из файла:\n{e}")

    def on_loin_sheet_changed(self, sheet_name: str):
        """Обработчик изменения выбранного листа LOIN."""
        if sheet_name:
            self.sheet_name = sheet_name

    def on_codes_sheet_changed(self, sheet_name: str):
        """Обработчик изменения выбранного листа Кодов."""
        pass

    def create_loin_template(self):
        """Создать шаблон Excel для LOIN."""
        try:
            fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить шаблон LOIN", "LOI_AR_R_manual.xlsx", "Excel (*.xlsx)")
            if not fn:
                return
            if not fn.lower().endswith('.xlsx'):
                fn += '.xlsx'
            out = _run_add_category_build(fn)
            QtWidgets.QMessageBox.information(self, "Готово", f"Шаблон LOIN сохранён:\n{out}")
            self.input_file = out
            self.ed_loin_file.setText(os.path.basename(out))
            # Загружаем листы в комбобокс
            self.cmb_loin_sheet.clear()
            try:
                if pd is not None:
                    sheets = list(pd.ExcelFile(out).sheet_names)
                    if sheets:
                        self.cmb_loin_sheet.addItems(sheets)
                        self.cmb_loin_sheet.setCurrentIndex(0)
                        self.sheet_name = sheets[0]
            except Exception:
                pass
        except Exception as e:
            _popup_error(self, str(e), title="Ошибка создания шаблона")

    def create_codes_template(self):
        """Создать шаблон Excel для Кодов."""
        try:
            fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить шаблон Коды", "Классификатор_АР_Стадия_Р.xlsx", "Excel (*.xlsx)")
            if not fn:
                return
            if not fn.lower().endswith('.xlsx'):
                fn += '.xlsx'
            out = _run_add_class_build(fn)
            QtWidgets.QMessageBox.information(self, "Готово", f"Шаблон Коды сохранён:\n{out}")
            self.classifier_file = out
            self.ed_codes_file.setText(os.path.basename(out))
            # Загружаем листы в комбобокс
            self.cmb_codes_sheet.clear()
            try:
                if pd is not None:
                    sheets = list(pd.ExcelFile(out).sheet_names)
                    if sheets:
                        self.cmb_codes_sheet.addItems(sheets)
                        self.cmb_codes_sheet.setCurrentIndex(0)
            except Exception:
                pass
        except Exception as e:
            _popup_error(self, str(e), title="Ошибка создания шаблона")

    def open_mapping(self):
        """Открыть диалог сопоставления параметров."""
        if not (SELECTED_CONTAINER_IDS and SELECTED_CONTAINER_IDS != [0]):
            QtWidgets.QMessageBox.warning(self, "Внимание", "Сначала нажмите 'Выбрать' в разделе 'Выбор моделей' и отметьте нужные модели.")
            return
        if not self.input_file or not self.sheet_name:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Сначала выберите файл LOIN.")
            return
        dlg = MappingDialogLarix(self.input_file, self.sheet_name, self)
        if dlg.exec():
            self.ed_map_summary.setText("Сопоставление параметров настроено")


    def save_json_master(self):
        """Сохранить глобальную карту сопоставлений в JSON."""
        wb = _wb_id(getattr(self, "input_file", "") or "")
        data = _deepcopy_dict(MASTER_MAP_CACHE.get(wb, {}))
        if not data:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Глобальная карта пуста.")
            return
        start_dir = os.path.dirname(getattr(self, "input_file", "") or "") or os.getcwd()
        suggested = os.path.join(start_dir, "Маппинг.json")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить JSON (глобальная карта)", suggested, "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(self, "Сохранено", f"Глобальная карта сохранена:\n{path}")

    def import_json_master(self):
        """Импортировать глобальную карту сопоставлений из JSON."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Импортировать JSON (глобальная карта)", "", "JSON (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            _popup_error(self, "Неверный формат JSON.")
            return
        normalized = _normalize_mapping_payload(data)
        wb = _wb_id(getattr(self, "input_file", "") or "")
        MASTER_MAP_CACHE[wb] = _deepcopy_dict(normalized)
        QtWidgets.QMessageBox.information(self, "Импорт", "Глобальная карта импортирована.")

    def clear_master(self):
        """Очистить глобальную карту сопоставлений."""
        wb = _wb_id(getattr(self, "input_file", "") or "")
        MASTER_MAP_CACHE[wb] = {}
        QtWidgets.QMessageBox.information(self, "Очищено", "Глобальная карта очищена для текущей книги.")

    def _on_generate_click(self):
        """Генерация профиля без сопоставления параметров."""
        if not self.input_file or not self.sheet_name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Сначала выберите файл LOIN и убедитесь, что выбран лист.")
            return
        title = (self.edit_title.text() or "Шаблон проверки по LOIN").strip()
        sheet = (self.sheet_name or "").strip()
        mode = globals().get("MODE_SELECTED", "both")
        use_cls = True if mode in ("classifier","both") else False
        cls_path = self.classifier_file if use_cls else None
        base_dir = self.last_output_dir or os.path.dirname(self.input_file or "") or os.getcwd()
        filename = os.path.basename(self.output_file or "ExportProfile.pv")
        suggested = os.path.join(base_dir, filename)
        output_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить как", suggested, "PV (*.pv)")
        if not output_path:
            return
        if not output_path.lower().endswith(".pv"):
            output_path += ".pv"
        self.last_output_dir = os.path.dirname(output_path)
        self.output_file = os.path.basename(output_path)
        ok, msg = excel_to_pv_profile(self.input_file, output_path, title, sheet, use_cls, cls_path, mode)
        QtWidgets.QMessageBox.information(self, "Готово" if ok else "Ошибка", msg)

class MainWindowMaster(MainWindow):
    pass

"""
Auto-injected helpers: Excel template builders for LOI and Classifier.
Mirrors the implementation used in Larix_set.py to build Excel templates
via sidecar scripts: "Add category.py" and "Add class.py".
"""

def _load_add_category_module():
    try:
        from importlib import util as _importlib_util
        from pathlib import Path as _Path
        here = _Path(__file__).resolve().parent
        for name in ["Add category.py", "Add_category.py", "add_category.py"]:
            p = here / name
            if p.exists():
                spec = _importlib_util.spec_from_file_location("add_category", str(p))
                if spec is None or spec.loader is None:
                    continue
                mod = _importlib_util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore
                if hasattr(mod, "build"):
                    return mod
    except Exception:
        pass
    raise FileNotFoundError("Не найден рядом 'Add category.py' с функцией build(out_path).")

def _run_add_category_build(out_path: str) -> str:
    mod = _load_add_category_module()
    res = mod.build(out_path)  # type: ignore
    return str(res or out_path)

def _load_add_class_module():
    try:
        from importlib import util as _importlib_util
        from pathlib import Path as _Path
        here = _Path(__file__).resolve().parent
        for name in ["Add class.py", "Add_class.py", "add_class.py"]:
            p = here / name
            if p.exists():
                spec = _importlib_util.spec_from_file_location("add_class", str(p))
                if spec is None or spec.loader is None:
                    continue
                mod = _importlib_util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore
                if hasattr(mod, "build"):
                    return mod
    except Exception:
        pass
    raise FileNotFoundError("Не найден рядом 'Add class.py' с функцией build(out_path).")

def _run_add_class_build(out_path: str) -> str:
    mod = _load_add_class_module()
    res = mod.build(out_path)  # type: ignore
    return str(res or out_path)

def main():
    app = QtWidgets.QApplication(sys.argv)
    p = os.path.join(APP_ROOT_DIR, TITLEBAR_ICON_REL)
    if not os.path.exists(p):
        p = _theme.resolve_icon_path("app_icon", ICON_DIR, app=app, tint_in_dark=False)
    if p:
        app.setWindowIcon(QtGui.QIcon(p))
    try:
        theme(app, load_saved_theme(False), icon_dir=ICON_DIR, persist=False)
        enable_theme_sync(app, ICON_DIR)
    except Exception:
        pass
    w = MainWindowMaster()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()










