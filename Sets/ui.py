# -*- coding: utf-8 -*-
"""
Sets/ui.py
Standalone: embedded nik_style; uses external icon/ and shared/excel_template.py.
Интеграция: функциональный файл использует nik_style как единственный источник дизайна.

Допущения:
- "nik_style.py" лежит рядом (или в sys.path) и содержит ThemeSwitch, set_header_logo, apply_themed_icon.
- Внешние PNG-иконки лежат в папке "icon" рядом с .py (как в nik_style).
- Функциональность исходного Larix_set сохранена; правки касаются только слоя стиля/темы и замены зависимостей на nik_style.
- Никаких новых логических функций не добавлено; UI-обёртка Section реализована локально как QGroupBox для совместимости.
"""

from __future__ import annotations
import sys, os, re, json, tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Callable

# Qt
try:
    from PySide6 import QtWidgets, QtGui, QtCore
except Exception:
    from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.theme_toggle import (
    ThemeToggle, theme, is_dark_theme, create_back_button, go_to_main_menu,
    resolve_icon_path, apply_dark_titlebar,
    load_saved_theme, enable_theme_sync,
    RowHoverDelegate, install_viewport_row_highlighter,
    nik_icon, PALETTE,
)
from shared.dialogs import show_dialog, wire_message_box_buttons

# Third-party (optional)
try:
    import pandas as pd
except Exception:
    pd = None

try:
    import requests
except Exception:
    requests = None

# ---- Embedded Nik Style (from nik_style.py) ----
class Palette:
    BG_LIGHT: str = "#FFFFFF"
    BG_DARK: str = "#1E1E1E"
    FG_LIGHT: str = "#222222"
    FG_DARK: str = "#FFFFFF"
    ACCENT: str = "#F7921E"
    ACCENT_HOVER: str = "#FFA74B"
    ACCENT_PRESSED: str = "#E07E12"
    GRAY: str = "#D9D9D9"
    GRAY_DARK: str = "#3A3A3A"
    BORDER_LIGHT: str = "#dcdcdc"
    BORDER_DARK: str = "#3A3A3A"
    SOFT_HOVER: str = "#FFE3C2"   # светло-оранжевый подсветки
    SELECTED: str = "#FFC37A"
    SCROLL_TRACK_LIGHT: str = "#FAFAFA"
    SCROLL_TRACK_DARK: str = "#252525"
    CHECKBOX_HOVER: str = "#E5E5E5"  # светло-серая подсветка для чекбоксов

PALETTE = Palette()

_BASE_FONT_FAMILY = "Segoe UI"
_BASE_FONT_SIZE_PT = 10

def _resource_path(*parts: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return str(base.joinpath(*parts))

DEFAULT_ICON_DIR = _resource_path("icon")
_CACHE_SUBDIR = "nik_style_cache"
SYNC_ROLE = QtCore.Qt.UserRole + 1111  # custom role to mark items needing a sync indicator

# --------------------------------------------------
# Реестр PNG-иконок из Dekstop + доп. sun/moon
# --------------------------------------------------
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
    "error":       ["error.png"],
    "alert":       ["alert.png"],
    "structure":   ["structure.png"],
    "insert":      ["insert.png"],
    "back":        ["back.png"],
    # badge / overlay assets
    "sync":        ["sync.png"],
    # Стрелки и сорт строго PNG
    "arrow_down":  ["arrow-down.png", "free-icon-down-arrow-3889508.png"],
    "arrow_up":    ["arrow-up.png"],
    "arrow_right": ["arrow-right.png"],
    "arrow_left":  ["arrow-left.png"],  # при отсутствии создадим из arrow-right
    "sort_up":     ["arrow-up.png"],
    "sort_down":   ["arrow-down.png", "free-icon-down-arrow-3889508.png"],
    "arrow_down_free": ["free-icon-down-arrow-3889508.png"],
    # rotate icons
    "rotate_left":  ["rotate-left.png", "free-icon-rotate-left.png"],
    "rotate_right": ["rotate-right.png", "free-icon-rotate-right.png"],
    # Иконки свитча темы - опционально
    "sun":         ["sun.png"],
    "moon":        ["moon.png"],
    "check":       ["check.png"],
    "select":      ["select.png"],
    "circle2":     ["krug.png"],
    "circle_dot":  ["krug_galka.png"],
    "poloska":     ["poloska.png"],
    # status icons
    "ok":          ["ok.png"],
    "none":        ["none.png"],
    # additional UI icons requested
    "1":           ["1.png"],
    "2":           ["2.png"],
    "extend":      ["extend.png"],
    "arrow_oba":   ["arrow-oba.png"],
    "navigation":  ["navigation.png"],
    "move":        ["move.png"],
    "compare":     ["compare.png"],
}

# ---------------------------
# Вспомогательные функции png
# ---------------------------

def _cache_dir(icon_dir: str) -> str:
    base = os.path.abspath(icon_dir or DEFAULT_ICON_DIR)
    root = os.path.join(tempfile.gettempdir(), _CACHE_SUBDIR)
    os.makedirs(root, exist_ok=True)
    sub = os.path.join(root, os.path.basename(base) or "icon")
    os.makedirs(sub, exist_ok=True)
    return sub


def _qss_url(path: str) -> str:
    # Экранируем обратный слеш
    return (path or "").replace("\\", "/")


def _first_existing(names: list[str], icon_dir: str) -> str:
    for name in names:
        p = os.path.join(icon_dir or DEFAULT_ICON_DIR, name)
        if os.path.exists(p):
            return p
    return ""


def _tint_pixmap(pm: QtGui.QPixmap, color: QtGui.QColor) -> QtGui.QPixmap:
    if pm.isNull():
        return pm
    out = QtGui.QPixmap(pm.size())
    out.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(out)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.drawPixmap(0, 0, pm)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        painter.fillRect(out.rect(), color)
    finally:
        painter.end()
    return out


def _pad_pixmap(pm: QtGui.QPixmap, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> QtGui.QPixmap:
    try:
        left = max(0, int(left)); top = max(0, int(top)); right = max(0, int(right)); bottom = max(0, int(bottom))
    except Exception:
        left = top = right = bottom = 0
    if pm.isNull() or (left == 0 and top == 0 and right == 0 and bottom == 0):
        return pm
    w = pm.width() + left + right
    h = pm.height() + top + bottom
    out = QtGui.QPixmap(w, h)
    out.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(out)
    try:
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.drawPixmap(left, top, pm)
    finally:
        p.end()
    return out


def _ensure_white_copy(src_path: str, icon_dir: str) -> str:
    try:
        if not src_path or not os.path.exists(src_path):
            return src_path
        out_dir = _cache_dir(icon_dir)
        base = os.path.basename(src_path)
        dst = os.path.join(out_dir, f"__white__{base}")
        if os.path.exists(dst):
            return dst
        pm = QtGui.QPixmap(src_path)
        if pm.isNull():
            return src_path
        white_pm = _tint_pixmap(pm, QtGui.QColor("#FFFFFF"))
        white_pm.save(dst)
        return dst
    except Exception:
        return src_path


def _ensure_black_copy(src_path: str, icon_dir: str) -> str:
    """Return a cached black-tinted copy of the given icon for light theme.

    Falls back to original path if any step fails.
    """
    try:
        out_dir = _cache_dir(icon_dir)
        base = os.path.basename(src_path)
        dst = os.path.join(out_dir, f"__black__{base}")
        if os.path.exists(dst):
            return dst
        pm = QtGui.QPixmap(src_path)
        if pm.isNull():
            return src_path
        black_pm = _tint_pixmap(pm, QtGui.QColor("#000000"))
        black_pm.save(dst)
        return dst
    except Exception:
        return src_path


def _ensure_gray_copy(src_path: str, icon_dir: str) -> str:
    try:
        if not src_path or not os.path.exists(src_path):
            return src_path
        out_dir = _cache_dir(icon_dir)
        base = os.path.basename(src_path)
        dst = os.path.join(out_dir, f"__gray__{base}")
        if os.path.exists(dst):
            return dst
        pm = QtGui.QPixmap(src_path)
        if pm.isNull():
            return src_path
        gray_pm = _tint_pixmap(pm, QtGui.QColor("#8f8f8f"))
        gray_pm.save(dst)
        return dst
    except Exception:
        return src_path


def _ensure_rotated_left(icon_dir: str) -> str:
    src = _first_existing(["arrow-left.png"], icon_dir)
    if src:
        return src
    right = _first_existing(["arrow-right.png"], icon_dir)
    if not right:
        return ""
    out_dir = _cache_dir(icon_dir)
    dst = os.path.join(out_dir, "arrow-left.png")
    if os.path.exists(dst):
        return dst
    pm = QtGui.QPixmap(right)
    if pm.isNull():
        return ""
    rot = pm.transformed(QtGui.QTransform().rotate(180), QtCore.Qt.SmoothTransformation)
    rot.save(dst)
    return dst

# -------------------------------------------------
# Публичный API: resolve_icon_path / nik_icon / logo
# -------------------------------------------------

def is_dark_theme(app: QtWidgets.QApplication | None = None) -> bool:
    app = app or QtWidgets.QApplication.instance()
    if not app:
        return False
    prop = app.property("nik_theme")
    if isinstance(prop, str):
        return prop.lower() == "dark"
    pal = app.palette()
    base = pal.color(QtGui.QPalette.Window)
    return (0.299 * base.red() + 0.587 * base.green() + 0.114 * base.blue()) < 128


def resolve_icon_path(name: str, icon_dir: str = DEFAULT_ICON_DIR, *, app: QtWidgets.QApplication | None = None) -> str:
    app = app or QtWidgets.QApplication.instance()
    dark = is_dark_theme(app) if app else False
    spec = _DEKSTOP_ICON_FILES.get(name)
    if isinstance(spec, list):
        candidates = spec
    elif isinstance(spec, str):
        candidates = [spec]
    else:
        candidates = []
    # логотипы: белый файл в тёмной теме
    if name == "logo" and dark:
        candidates = _DEKSTOP_ICON_FILES.get("logo_white", []) + candidates
    path = _first_existing(candidates, icon_dir)
    if name == "arrow_left" and not path:
        path = _ensure_rotated_left(icon_dir)
    if not path:
        return ""
    # In dark theme, avoid whitening for a set of icons that must keep original colors
    NO_TINT_DARK = {"logo", "logo_white", "ok", "none", "warning", "refresh", "gear", "folder"}
    return _ensure_white_copy(path, icon_dir) if dark and name not in NO_TINT_DARK else path


def nik_icon(name: str, app: QtWidgets.QApplication | None = None, icon_dir: str = DEFAULT_ICON_DIR) -> QtGui.QIcon:
    p = resolve_icon_path(name, icon_dir, app=app)
    return QtGui.QIcon(p) if p else QtGui.QIcon()


def compose_badged_icon(base_icon: QtGui.QIcon, badge_name_or_path: str,
                        *, icon_dir: str = DEFAULT_ICON_DIR,
                        sizes: tuple[int, ...] = (16, 20, 24, 28, 32, 40, 48)) -> QtGui.QIcon:
    """Return a new icon with a small badge overlaid at bottom-right.

    - base_icon: the original icon (e.g., folder)
    - badge_name_or_path: either logical name from this module (e.g., 'sync') or a direct file path
    - icon_dir: directory to resolve resources
    - sizes: pixmap sizes to generate for crisp scaling
    """
    try:
        if base_icon.isNull():
            return base_icon
        # resolve badge path by name or use absolute/relative path directly
        if os.path.exists(badge_name_or_path):
            badge_path = badge_name_or_path
        else:
            badge_path = resolve_icon_path(str(badge_name_or_path), icon_dir)
        if not badge_path or not os.path.exists(badge_path):
            return base_icon
        badge_pm_orig = QtGui.QPixmap(badge_path)
        if badge_pm_orig.isNull():
            return base_icon
        out = QtGui.QIcon()
        for size in sizes:
            base_pm = base_icon.pixmap(size, size)
            if base_pm.isNull():
                continue
            canvas = QtGui.QPixmap(size, size)
            canvas.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(canvas)
            try:
                p.setRenderHint(QtGui.QPainter.Antialiasing, True)
                p.drawPixmap(0, 0, base_pm)
                # badge ~60% of base size; small margin 6%
                b = max(10, int(size * 0.60))
                badge_pm = badge_pm_orig.scaled(b, b, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                m = max(1, int(size * 0.06))
                x = size - badge_pm.width() - m
                y = size - badge_pm.height() - m
                p.drawPixmap(x, y, badge_pm)
            finally:
                p.end()
            out.addPixmap(canvas)
        return out if not out.isNull() else base_icon
    except Exception:
        return base_icon


class SyncBadgeTreeDelegate(QtWidgets.QStyledItemDelegate):
    """Tree delegate that draws a small 'sync' icon to the right of the item text
    when the model index carries SYNC_ROLE set to True.
    """
    def __init__(self, parent: QtWidgets.QWidget | None = None, *, icon_dir: str = DEFAULT_ICON_DIR):
        super().__init__(parent)
        self.icon_dir = icon_dir

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        is_sync = bool(index.data(SYNC_ROLE))

        # Reserve space on the right for the badge to avoid overlapping text
        original_rect = QtCore.QRect(opt.rect)
        badge_size = min(max(12, original_rect.height() - 4), 20)
        margin = max(2, int(original_rect.height() * 0.08))
        # Estimate a TAB width as a few spaces so the icon sits after a "tab"
        try:
            fm_reserved = QtGui.QFontMetrics(opt.font)
        except Exception:
            fm_reserved = painter.fontMetrics()
        tab_px_reserved = max(fm_reserved.horizontalAdvance("    "), int(badge_size * 0.25))
        if is_sync:
            opt.rect = QtCore.QRect(original_rect.x(), original_rect.y(),
                                    max(0, original_rect.width() - (badge_size + margin + tab_px_reserved)),
                                    original_rect.height())

        style = opt.widget.style() if getattr(opt, 'widget', None) else QtWidgets.QApplication.style()
        # Draw the item first, but we will compute text rect and its actual drawn width
        text_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, opt, getattr(opt, 'widget', None))
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, getattr(opt, 'widget', None))

        if is_sync:
            # Draw the sync badge aligned to the right, centered vertically
            badge_icon = nik_icon("sync")
            if not badge_icon.isNull():
                pm = badge_icon.pixmap(badge_size, badge_size)
                if not pm.isNull():
                    # Compute the elided text that was drawn and measure its width
                    try:
                        fm = QtGui.QFontMetrics(opt.font)
                    except Exception:
                        fm = painter.fontMetrics()
                    elide_mode = getattr(opt, 'textElideMode', QtCore.Qt.ElideRight)
                    drawn_text = fm.elidedText(opt.text, elide_mode, max(0, text_rect.width()))
                    text_width = fm.horizontalAdvance(drawn_text)
                    # Place the badge immediately after the drawn text + one TAB width
                    tab_px = max(fm.horizontalAdvance("    "), int(badge_size * 0.25))
                    x = min(original_rect.right() - badge_size - margin, text_rect.x() + text_width + tab_px)
                    y = original_rect.y() + (original_rect.height() - badge_size) // 2
                    painter.save()
                    try:
                        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                        painter.drawPixmap(x, y, pm)
                    finally:
                        painter.restore()

    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        base = super().sizeHint(option, index)
        if bool(index.data(SYNC_ROLE)):
            badge_size = min(max(12, base.height() - 4), 20)
            margin = max(2, int(base.height() * 0.08))
            fm = QtGui.QFontMetrics(option.font)
            tab_px = max(fm.horizontalAdvance("    "), int(badge_size * 0.25))
            return QtCore.QSize(base.width() + badge_size + margin + tab_px, base.height())
        return base


# -------------------------------
# QTree branch arrows (chevrons)
# -------------------------------

_BRANCH_BASE_PIXMAP_CACHE: dict[tuple[str, int, str], QtGui.QPixmap] = {}
_BRANCH_TINTED_PIXMAP_CACHE: dict[tuple[str, int, int, str], QtGui.QPixmap] = {}


def _branch_arrow_pixmap(direction: str, color: QtGui.QColor, size: int,
                         *, icon_dir: str = DEFAULT_ICON_DIR,
                         app: QtWidgets.QApplication | None = None) -> QtGui.QPixmap:
    """Return a themed branch arrow pixmap oriented 'right' or 'down'.

    - Uses the existing down-arrow PNG from icon_dir (same assets as Dekstop.py)
    - Rotates to 'right' when needed
    - Caches scaled and tinted variants for performance
    """
    app = app or QtWidgets.QApplication.instance()
    size = max(1, int(size))
    orient = "down" if direction == "down" else "right"

    # Base pixmap cache key: (orientation, size, icon-path)
    base_icon_path = resolve_icon_path("sort_down", icon_dir, app=app) or resolve_icon_path("arrow_down", icon_dir, app=app)
    if not base_icon_path:
        return QtGui.QPixmap()
    base_key = (orient, size, base_icon_path)
    base_pm = _BRANCH_BASE_PIXMAP_CACHE.get(base_key)
    if base_pm is None:
        src = QtGui.QPixmap(base_icon_path)
        if orient == "right" and not src.isNull():
            try:
                src = src.transformed(QtGui.QTransform().rotate(-90), QtCore.Qt.SmoothTransformation)
            except Exception:
                pass
        if src.isNull():
            base_pm = QtGui.QPixmap()
        else:
            base_pm = src.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        _BRANCH_BASE_PIXMAP_CACHE[base_key] = base_pm

    if base_pm.isNull():
        return base_pm

    # Decide tint color if invalid
    if not isinstance(color, QtGui.QColor) or not color.isValid():
        dark = is_dark_theme(app)
        color = QtGui.QColor("#e0e0e0" if dark else "#222222")

    tint_key = (orient, size, int(color.rgba()), base_icon_path)
    tinted = _BRANCH_TINTED_PIXMAP_CACHE.get(tint_key)
    if tinted is None:
        tinted = _tint_pixmap(base_pm, color)
        _BRANCH_TINTED_PIXMAP_CACHE[tint_key] = tinted
    return tinted


class TreeBranchProxyStyle(QtWidgets.QProxyStyle):
    """Proxy style to draw QTreeView/QTreeWidget branch arrows like in Dekstop.py.

    - Closed => right chevron
    - Open => down chevron
    - Uses orange accent on hover/selection for visibility
    - Auto-adapts to light/dark theme (nik_style.is_dark_theme)
    """

    def drawPrimitive(self, element, option, painter, widget=None):  # type: ignore[override]
        if element == QtWidgets.QStyle.PE_IndicatorBranch:
            # If no children, let default draw (usually nothing)
            if not (option.state & QtWidgets.QStyle.State_Children):
                return super().drawPrimitive(element, option, painter, widget)

            # Color selection
            try:
                dark = is_dark_theme(QtWidgets.QApplication.instance())
            except Exception:
                dark = False
            col = QtGui.QColor("#e0e0e0" if dark else "#222222")
            if option.state & (QtWidgets.QStyle.State_MouseOver | QtWidgets.QStyle.State_Selected):
                col = QtGui.QColor(PALETTE.ACCENT)

            rect = option.rect.adjusted(1, 1, -1, -1)
            icon_sz = int(max(8, min(rect.width(), rect.height(), 10)))
            direction = "down" if (option.state & QtWidgets.QStyle.State_Open) else "right"
            pm = _branch_arrow_pixmap(direction, col, icon_sz)
            if not pm.isNull():
                painter.save()
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                x = rect.x() + (rect.width() - pm.width()) // 2
                y = rect.y() + (rect.height() - pm.height()) // 2
                painter.drawPixmap(int(x), int(y), pm)
                painter.restore()
                return
        return super().drawPrimitive(element, option, painter, widget)


def apply_tree_branch_style(tree: QtWidgets.QAbstractItemView) -> None:
    """Apply TreeBranchProxyStyle to a QTreeWidget/QTreeView (and its viewport)."""
    try:
        prox = TreeBranchProxyStyle(getattr(tree, "style", lambda: None)())
        if hasattr(tree, "setStyle"):
            tree.setStyle(prox)
        if hasattr(tree, "viewport") and callable(tree.viewport) and tree.viewport():
            tree.viewport().setStyle(prox)
    except Exception:
        pass

def load_logo(icon_dir: str = DEFAULT_ICON_DIR) -> QtGui.QPixmap:
    app = QtWidgets.QApplication.instance()
    dark = is_dark_theme(app)
    p = LOGO_PATH_WHITE if dark else LOGO_PATH
    if not (p and os.path.exists(p)):
        name = "logo"
        p = resolve_icon_path(name, icon_dir, app=app)
    pm = QtGui.QPixmap(p)
    return pm if not pm.isNull() else QtGui.QPixmap()


class _IconHoverFilter(QtCore.QObject):
    """Делает иконку на кнопке чёрной при наведении (hover)."""
    def __init__(self, target: QtWidgets.QAbstractButton, name: str, icon_dir: str):
        super().__init__(target)
        self._w = target
        self._name = name
        self._icon_dir = icon_dir
        self._normal = QtGui.QIcon()
        self._hover = QtGui.QIcon()
        self._rebuild()

    def _rebuild(self):
        app = QtWidgets.QApplication.instance()
        base_path = resolve_icon_path(self._name, self._icon_dir, app=app)
        # обычная иконка — как по теме
        self._normal = QtGui.QIcon(base_path) if base_path else QtGui.QIcon()
        # hover — та же картинка, но перекрашенная в чёрный
        pm = QtGui.QPixmap(base_path) if base_path else QtGui.QPixmap()
        if not pm.isNull():
            hover_pm = _tint_pixmap(pm, QtGui.QColor("#000000"))
            self._hover = QtGui.QIcon(hover_pm)
        else:
            self._hover = self._normal

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QtCore.QEvent.Enter, QtCore.QEvent.HoverEnter, QtCore.QEvent.FocusIn, QtCore.QEvent.MouseMove):
            if isinstance(self._w, QtWidgets.QAbstractButton):
                self._w.setIcon(self._hover)
        elif t in (QtCore.QEvent.Leave, QtCore.QEvent.HoverLeave, QtCore.QEvent.FocusOut):
            if isinstance(self._w, QtWidgets.QAbstractButton):
                self._w.setIcon(self._normal)
        elif t == QtCore.QEvent.EnabledChange:
            if isinstance(self._w, QtWidgets.QAbstractButton):
                self._w.setIcon(self._normal)
        return False


# -----------------------
# StatusIndicator: иконка + текст
# -----------------------
class StatusIndicator(QtWidgets.QWidget):
    def __init__(self, parent=None, icon_dir: str = DEFAULT_ICON_DIR):
        super().__init__(parent)
        self._icon_dir = icon_dir
        self._icon = QtWidgets.QLabel(self)
        self._icon.setFixedSize(18, 18)
        self._icon.setScaledContents(True)
        self._label = QtWidgets.QLabel(self)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(6)
        lay.addWidget(self._icon, 0)
        lay.addWidget(self._label, 1)

        # Привязываемся к смене темы для обновления окраски иконок
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self.set_neutral("Статус не задан")

    def eventFilter(self, obj, ev):
        # При смене палитры/темы просто перерисуем текущую иконку
        if ev.type() in (QtCore.QEvent.ApplicationPaletteChange, QtCore.QEvent.PaletteChange):
            self._apply_current_icon()
        return super().eventFilter(obj, ev)

    def _resolve_icon(self, key: str) -> QtGui.QPixmap:
        p = resolve_icon_path(key, self._icon_dir, app=QtWidgets.QApplication.instance())
        pm = QtGui.QPixmap(p) if p else QtGui.QPixmap()
        if not pm.isNull():
            pm = pm.scaled(18, 18, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        return pm

    def _apply_current_icon(self):
        if getattr(self, "_state", None) == "ok":
            self._icon.setPixmap(self._resolve_icon("ok"))
        elif getattr(self, "_state", None) == "error":
            # Оставляем, как просили: иконка none.png в нижнем индикаторе
            self._icon.setPixmap(self._resolve_icon("none"))
        else:
            self._icon.setPixmap(QtGui.QPixmap())

    def set_ok(self, text: str):
        self._state = "ok"
        self._label.setText(text)
        self._apply_current_icon()

    def set_error(self, text: str):
        self._state = "error"
        self._label.setText(text)
        self._apply_current_icon()

    def set_neutral(self, text: str = ""):
        self._state = "neutral"
        self._label.setText(text)
        self._apply_current_icon()

    def refresh_for_theme(self):
        self._rebuild()
        if isinstance(self._w, QtWidgets.QAbstractButton):
            self._w.setIcon(self._normal)


def show_error_dialog(text: str,
                      *,
                      title: str = "Ошибка",
                      icon_dir: str = DEFAULT_ICON_DIR,
                      parent: QtWidgets.QWidget | None = None,
                      modal: bool = True) -> None:
    """Показывает отдельное окно ошибки с картинкой error.png.

    - Использует `QMessageBox` и подменяет иконку через `setIconPixmap`.
    - Если `modal=True` — модально (`exec()`), иначе — немодально (`open()`).
    """
    app = QtWidgets.QApplication.instance()
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    p = resolve_icon_path("error", icon_dir, app=app)
    pm = QtGui.QPixmap(p) if p else QtGui.QPixmap()
    if not pm.isNull():
        msg.setIconPixmap(pm.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
    else:
        msg.setIcon(QtWidgets.QMessageBox.Critical)
    try:
        msg.setStyleSheet("QLabel#qt_msgbox_label{margin-top:10px;} QLabel#qt_msgbox_informativelabel{margin-top:10px;}")
    except Exception:
        pass
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    wire_message_box_buttons(msg)
    show_dialog(msg, modal=modal)


def show_info_dialog(text: str,
                     *,
                     title: str = "Информация",
                     icon_dir: str = DEFAULT_ICON_DIR,
                     parent: QtWidgets.QWidget | None = None,
                     modal: bool = True) -> None:
    """Показывает информационное окно с картинкой alert.png.

    - Использует `QMessageBox` и подменяет иконку через `setIconPixmap`.
    - Если `modal=True` — модально (`exec()`), иначе — немодально (`open()`).
    """
    app = QtWidgets.QApplication.instance()
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    p = resolve_icon_path("alert", icon_dir, app=app)
    pm = QtGui.QPixmap(p) if p else QtGui.QPixmap()
    if not pm.isNull():
        msg.setIconPixmap(pm.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
    else:
        msg.setIcon(QtWidgets.QMessageBox.Information)
    try:
        msg.setStyleSheet("QLabel#qt_msgbox_label{margin-top:10px;} QLabel#qt_msgbox_informativelabel{margin-top:10px;}")
    except Exception:
        pass
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    wire_message_box_buttons(msg)
    show_dialog(msg, modal=modal)


def show_warning_dialog(text: str,
                        *,
                        title: str = "Внимание",
                        icon_dir: str = DEFAULT_ICON_DIR,
                        parent: QtWidgets.QWidget | None = None,
                        modal: bool = True) -> None:
    """Показывает предупреждение с картинкой warning.png."""
    app = QtWidgets.QApplication.instance()
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    p = resolve_icon_path("warning", icon_dir, app=app)
    pm = QtGui.QPixmap(p) if p else QtGui.QPixmap()
    if not pm.isNull():
        msg.setIconPixmap(pm.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
    else:
        msg.setIcon(QtWidgets.QMessageBox.Warning)
    try:
        msg.setStyleSheet("QLabel#qt_msgbox_label{margin-top:10px;} QLabel#qt_msgbox_informativelabel{margin-top:10px;}")
    except Exception:
        pass
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    wire_message_box_buttons(msg)
    show_dialog(msg, modal=modal)


def apply_themed_icon(widget: QtWidgets.QAbstractButton, name: str, icon_dir: str = DEFAULT_ICON_DIR) -> None:
    """Присваивает иконку и ставит фильтр: на hover иконка становится чёрной."""
    app = QtWidgets.QApplication.instance()
    path = resolve_icon_path(name, icon_dir, app=app)
    widget.setIcon(QtGui.QIcon(path) if path else QtGui.QIcon())
    # храним метаданные на виджете
    setattr(widget, "_nik_icon_name", name)
    setattr(widget, "_nik_icon_dir", icon_dir)
    # переставим фильтр (если уже был)
    old = getattr(widget, "_nik_hover_filter", None)
    if isinstance(old, QtCore.QObject):
        try:
            widget.removeEventFilter(old)
        except Exception:
            pass
    filt = _IconHoverFilter(widget, name, icon_dir)
    setattr(widget, "_nik_hover_filter", filt)
    widget.setMouseTracking(True)
    widget.installEventFilter(filt)


def apply_rotate_button(widget: QtWidgets.QAbstractButton, *, direction: str = "left", icon_dir: str = DEFAULT_ICON_DIR) -> None:
    """Назначает на кнопку иконку поворота (rotate_left/right) с автообновлением по теме.

    direction: "left" или "right"
    """
    name = "rotate_left" if str(direction).lower().startswith("l") else "rotate_right"
    apply_themed_icon(widget, name, icon_dir)
    try:
        widget.setIconSize(QtCore.QSize(16, 16))
    except Exception:
        pass


def apply_rotate_left_button(widget: QtWidgets.QAbstractButton, icon_dir: str = DEFAULT_ICON_DIR) -> None:
    apply_rotate_button(widget, direction="left", icon_dir=icon_dir)


def apply_rotate_right_button(widget: QtWidgets.QAbstractButton, icon_dir: str = DEFAULT_ICON_DIR) -> None:
    apply_rotate_button(widget, direction="right", icon_dir=icon_dir)


def apply_themed_icon_with_arrow(widget: QtWidgets.QAbstractButton, 
                                  name: str = "arrow_right", 
                                  icon_dir: str = DEFAULT_ICON_DIR,
                                  icon_size: tuple = (8, 8),
                                  padding_top: int = 8) -> None:
    """Присваивает иконку-стрелку справа с настраиваемым отступом сверху.
    
    Args:
        widget: Кнопка для применения иконки
        name: Имя иконки (по умолчанию "arrow_right")
        icon_dir: Папка с иконками
        icon_size: Размер иконки в пикселях (ширина, высота)
        padding_top: Отступ сверху для позиционирования иконки
    """
    widget.setLayoutDirection(QtCore.Qt.RightToLeft)
    apply_themed_icon(widget, name, icon_dir)
    widget.setIconSize(QtCore.QSize(icon_size[0], icon_size[1]))
    widget.setStyleSheet(f"padding-top: {padding_top}px;")


def apply_add_selected_button(widget: QtWidgets.QAbstractButton,
                              *,
                              icon_dir: str = DEFAULT_ICON_DIR,
                              direction: str = "left",
                              icon_size: tuple = (8, 8),
                              padding_top: int = 4) -> None:
    """Оформляет кнопку как «Добавить отмеченные» со стрелкой справа.

    - Текст: «Добавить отмеченные»
    - Иконка: ``arrow_left`` или ``arrow_right`` (по параметру ``direction``)
    - Иконка располагается справа от текста и выровнена по центру по высоте

    Пример использования (по аналогии с Larix_set):
        btn = QtWidgets.QPushButton()
        apply_add_selected_button(btn, direction="left", icon_dir=ICON_DIR)
    """
    try:
        widget.setText("Добавить отмеченные")
    except Exception:
        pass
    icon_name = "arrow_left" if str(direction).lower().startswith("l") else "arrow_right"
    # Place icon to the right of text
    try:
        widget.setLayoutDirection(QtCore.Qt.RightToLeft)
    except Exception:
        pass
    app = QtWidgets.QApplication.instance()
    path = resolve_icon_path(icon_name, icon_dir, app=app)
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
    # Remove previous hover filter (if any) to avoid overriding our icons
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
    # Ensure we don't push text down
    try:
        widget.setStyleSheet("")
    except Exception:
        pass

# -----------------------
# CSS/QSS построитель стиля
# -----------------------

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

    # В дарке фон скроллбара как у общего фона (не отдельный трек, как просили «как в Dekstop»)
    TRACK_BG = BG if dark else PALETTE.SCROLL_TRACK_LIGHT

    chk_off = _qss_url(chk_off)
    chk_on = _qss_url(chk_on)
    chk_mid = _qss_url(chk_mid)
    rchk_off = _qss_url(rchk_off)
    rchk_on = _qss_url(rchk_on)
    # Ensure list-hover icon paths are QSS-safe
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
    QWidget {{ background: {BG}; }}  /* фон везде единый под тему */

    /* Хедер/статус/меню тоже на общем фоне */
    QStatusBar, QMenuBar, QToolBar, QMenu, QDockWidget::title {{ background: {BG}; border: 1px solid {BORDER}; }}
    QTabBar::pane {{ background: {BG}; border: none; }}
    #header {{ background: {BG}; border: none; }}
    QTabWidget::pane {{ border: none; border-radius: 12px; margin-top: 8px; }}
    QTabBar::tab {{ background: {BG}; color: {FG}; border: 1px solid {BORDER}; border-bottom-color: {BORDER};
                   padding: 6px 14px; border-top-left-radius: 10px; border-top-right-radius: 10px; margin: 0 4px; }}
    QTabBar::tab:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_text}; border-color: {PALETTE.ACCENT}; }}
    QTabBar::tab:selected {{ background: {PALETTE.SELECTED}; color: {hover_text}; border-color: {PALETTE.ACCENT}; }}
    QTabBar::tab:!selected {{ margin-top: 6px; }}

    /* Кнопки: белые (в тёмной теме — тёмные), hover - светло-оранжевый */
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

    /* Крупные кнопки (например, "Загрузить проекты") */
    QPushButton[largeButton="true"] {{
        font-size: {_BASE_FONT_SIZE_PT + 2}pt;
        font-weight: 600;
        padding: 8px 14px;
    }}

    /* Вторичные кнопки можно получить стилем class=btn-secondary при необходимости */
    .btn-secondary {{
        background: {BG}; color: {FG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 5px 10px;
    }}
    .btn-secondary:hover {{ background: rgba(247, 146, 30, 0.15); border: 1px solid {PALETTE.ACCENT}; }}

    /* Комбо */
    QComboBox {{
        border: 1px solid {BORDER}; border-radius: 12px; padding: 3px 28px 3px 8px;
        background: {BG}; selection-background-color: {PALETTE.SELECTED}; selection-color: #000000;
    }}
    QComboBox::drop-down {{ width: 26px; border: none; }}
    QComboBox::down-arrow {{ image: url('{cmb_down}'); width: 12px; height: 12px; }}

    /* Строки ввода — стиль в точности как у QComboBox */
    QLineEdit,
    QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit, QDateTimeEdit {{
        border: 1px solid {BORDER}; border-radius: 12px; padding: 3px 8px;
        background: {BG}; selection-background-color: {PALETTE.SELECTED};
    }}
    /* hover отключён для строк ввода */
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

    /* Popup выпадающего списка — подсветки как у кнопок */
    QComboBox QAbstractItemView {{ background: {BG}; border: 1px solid {BORDER}; outline: none; selection-background-color: {PALETTE.SELECTED}; }}
    QComboBox QAbstractItemView::item {{ padding: 4px 8px; border-radius: 8px; margin: 1px 4px; border: none; }}
    QComboBox QAbstractItemView::item:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_text}; border-radius: 8px; border: none; }}
    QComboBox QAbstractItemView::item:selected {{ background: {PALETTE.SELECTED}; color: {hover_text}; border-radius: 8px; border: none; }}
    QComboBox QAbstractItemView::item:focus {{ outline: none; border: none; }}

    /* Списки (QListView, QListWidget) — подсветка элементов как в выпадающем списке */
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
    /* Убираем дополнительный focus рамку */
    QListView::item:selected:active, QListWidget::item:selected:active {{
        background: {PALETTE.SELECTED};
    }}
    /* Чекбоксы в списках — используем те же PNG иконки, что и у обычных чекбоксов */
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
    /* Подсветка только индикатора при наведении */
    /* Убрали подсветку чекбоксов при наведении в списках */
    QListView::indicator:hover, QListWidget::indicator:hover {{
        background: transparent;
        border-radius: 0;
    }}

    /* Чекбоксы через PNG иконки */
    QCheckBox {{ padding: 2px; color: {FG}; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QCheckBox::indicator:unchecked {{ image: url('{chk_off}'); }}
    QCheckBox::indicator:checked   {{ image: url('{chk_on}'); }}
    QCheckBox::indicator:indeterminate {{ image: url('{chk_mid}'); }}
    /* Подсветка только индикатора чекбокса при наведении */
    /* Убрали подсветку чекбоксов при наведении */
    QCheckBox::indicator:hover {{
        background: transparent;
        border-radius: 0;
    }}

    /* Круглые чекбоксы (property round=true) */
    QCheckBox[round="true"]::indicator {{ width: 18px; height: 18px; }}
    /* use defaults; no image override for round=true states */
    /* Подсветка только индикатора круглого чекбокса при наведении */
    QCheckBox[round="true"]::indicator:hover {{
        background: transparent;
        border-radius: 0;
    }}
    /* Preserve readable text color for checkboxes and radios on hover */
    QCheckBox:hover {{ color: {FG}; background: transparent; }}
    QRadioButton:hover {{ color: {FG}; background: transparent; }}

    /* Date/Time spin arrows and calendar dropdown */
    QAbstractSpinBox::up-arrow    {{ image: url('{ar_up}');   width: 12px; height: 12px; }}
    QAbstractSpinBox::down-arrow  {{ image: url('{ar_down}'); width: 12px; height: 12px; }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ background: transparent; border: none; }}

    /* Убираем квадратную подложку у стрелки календаря */
    QDateEdit::drop-down, QDateTimeEdit::drop-down {{ background: transparent; border: none; width: 22px; }}
    QDateEdit::down-arrow, QDateTimeEdit::down-arrow {{ image: url('{ar_down}'); width: 12px; height: 12px; margin-right: 4px; }}

    /* Календарь: стрелки влево/вправо */
    QCalendarWidget {{ background: {BG}; border: 1px solid {BORDER}; }}
    QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {BG}; border: none; }}
    QCalendarWidget QToolButton {{ background: transparent; border: none; }}
    QCalendarWidget QToolButton#qt_calendar_prevmonth {{ qproperty-icon: url('{ar_left}'); icon-size: 12px 12px; }}
    QCalendarWidget QToolButton#qt_calendar_nextmonth {{ qproperty-icon: url('{ar_right}'); icon-size: 12px 12px; }}
    QCalendarWidget QToolButton::menu-indicator {{ image: none; }}
    /* Calendar day cells: hover like table rows */
    QCalendarWidget QAbstractItemView {{
        background: {BG};
        selection-background-color: {PALETTE.SELECTED};
        selection-color: {hover_text};
        outline: none;
    }}
    QCalendarWidget QAbstractItemView::item {{
        padding: 4px;
        border-radius: 6px;
    }}
    QCalendarWidget QAbstractItemView::item:hover {{
        background: {PALETTE.SOFT_HOVER};
        color: {hover_text};
    }}
    QCalendarWidget QAbstractItemView::item:selected {{
        background: {PALETTE.SELECTED};
        color: {hover_text};
    }}
    /* Таблицы/деревья */
    QHeaderView::section {{
        background: {BG};
        color: {FG};
        /* Keep box size stable so hover border doesn't shift layout */
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
    /* Подсветка заголовков таблиц при hover/pressed — как в Dekstop.py */
    QHeaderView::section:hover {{ background: #FFF3E6; color: {hover_text}; border-color: #FFD1A0; }}
    QHeaderView::section:pressed {{ background: #ffca91; color: {hover_text}; border-color: #FFA74B; }}
    /* Скругления при наведении/нажатии, повторяют Desktop */
    QHeaderView::section:hover,
    QHeaderView::section:pressed {{ border-radius: 8px; }}
    QHeaderView::section:first:hover,
    QHeaderView::section:first:pressed {{ border-top-left-radius: 8px; }}
    QHeaderView::section:last:hover,
    QHeaderView::section:last:pressed  {{ border-top-right-radius: 8px; }}

    /* Отдельно для demo-таблицы: без бросающихся в глаза сеток */
    QTableView#list_table {{ gridline-color: transparent; }}
    QHeaderView#list_table_header::section {{
        border: 1px solid {BORDER};
        border-left: none;
        background: {BG};
        padding: 6px 8px;
    }}
    QHeaderView#list_table_header::section:hover {{ background: #FFF3E6; color: {hover_text}; border-color: #FFD1A0; }}
    QHeaderView#list_table_header::section:pressed {{ background: #ffca91; color: {hover_text}; border-color: #FFA74B; }}

    /* Скроллбары 12px со стрелками PNG */
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

    /* Меню */
    QAbstractScrollArea::corner {{ background: {TRACK_BG}; }}
    QMenu {{ border-radius: 12px; padding: 6px; }}
    QMenu::item {{ padding: 6px 10px; border-radius: 8px; }}
    QMenu::item:selected {{ background: {PALETTE.SOFT_HOVER}; }}

    /* Блоки (QGroupBox) — скруглённая рамка и заголовок внутри верхней линии */
    QGroupBox {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
        margin-top: 16px;   /* место под заголовок */
        padding-top: 8px;   /* небольшой внутренний отступ сверху */
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;                /* отступ текста от левого края рамки */
        padding: 0 8px;            /* «плашка» под текстом */
        background-color: {BG};    /* чтобы заголовок «перерезал» линию рамки */
        color: {FG};
    }}

    /* Многострочные поля под стиль инпутов */
    QTextEdit, QPlainTextEdit {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        background: {BG};
        selection-background-color: {PALETTE.SELECTED};
        selection-color: #000000;
    }}


    /* Псевдо-табличные строки: без рамок вокруг каждого блока */
    QWidget[rowlike="true"] {{ background: {BG}; border: none; border-radius: 12px; padding: 6px 8px; }}
    QWidget[rowlike="true"]:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_text}; }}
    QWidget[rowlike="true"] QLabel {{ background: transparent; }}
    """
    qss += f"""
    /* Нормализуем верхний левый угол таблицы */
    QTableCornerButton::section, QTableView QTableCornerButton::section {{
        background: {BG};
        border: none;
    }}
"""
    # Ensure round checkboxes use round icons that follow theme (light/dark)
    qss += f"""
    /* Round checkbox explicit images to recolor like Nik Style */
    QCheckBox[round="true"]::indicator:unchecked {{ image: url('{rchk_off}'); }}
    QCheckBox[round="true"]::indicator:checked   {{ image: url('{rchk_on}'); }}
    QCheckBox[round="true"]::indicator:indeterminate {{ image: url('{chk_mid}'); }}
    """
    qss += f"""
    /* Keep checkbox icons the same on hover (no black tint in dark) */
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

    # Per-window override: when ancestor has noCheckHoverRecolor=true,
    # keep list indicators the same on hover even in dark theme.
    qss += f"""
    *[noCheckHoverRecolor="true"] QListView::indicator:unchecked:hover, *[noCheckHoverRecolor="true"] QListWidget::indicator:unchecked:hover {{ image: url('{chk_off}'); }}
    *[noCheckHoverRecolor="true"] QListView::indicator:checked:hover,   *[noCheckHoverRecolor="true"] QListWidget::indicator:checked:hover   {{ image: url('{chk_on}'); }}
    *[noCheckHoverRecolor="true"] QListView::indicator:indeterminate:hover, *[noCheckHoverRecolor="true"] QListWidget::indicator:indeterminate:hover {{ image: url('{chk_mid}'); }}
    """
    return qss


# ----------------------
# Применение стиля к app
# ----------------------

# --- Windows: тёмный заголовок/фрейм через WinAPI ---
if sys.platform == "win32":
    import ctypes
    _DwmSetWindowAttribute = None
    try:
        _DwmSetWindowAttribute = ctypes.windll.dwmapi.DwmSetWindowAttribute  # type: ignore[attr-defined]
    except Exception:
        _DwmSetWindowAttribute = None

    def _win_set_attr(hwnd: int, attr: int, value: int) -> None:
        if not _DwmSetWindowAttribute or not hwnd:
            return
        v = ctypes.c_int(value)
        _DwmSetWindowAttribute(ctypes.c_void_p(hwnd), ctypes.c_int(attr), ctypes.byref(v), ctypes.sizeof(v))

    def _win_apply_titlebar(hwnd: int, dark: bool) -> None:
        """Темним нативную верхнюю часть окна (titlebar) как в Dekstop.
        - DWMWA_USE_IMMERSIVE_DARK_MODE: 20 (Win10 1903+) или 19 (Win10 1809)
        - DWMWA_SYSTEMBACKDROP_TYPE (38): 2 = MainWindow (Win11) / 1 = None
        """
        if not hwnd:
            return
        # Dark caption
        _win_set_attr(hwnd, 20, 1 if dark else 0)
        _win_set_attr(hwnd, 19, 1 if dark else 0)
        # Backdrop (Win11): 2 = MainWindow (минимальный аналог Mica у системного заголовка)
        _win_set_attr(hwnd, 38, 2 if dark else 1)

    def _win_apply_titlebar_all(app: QtWidgets.QApplication, dark: bool) -> None:
        # Применяем только к настоящим top-level окнам: QMainWindow / QDialog
        for w in app.topLevelWidgets():
            try:
                if not isinstance(w, (QtWidgets.QMainWindow, QtWidgets.QDialog)):
                    continue
                if not w.isWindow() or w.parentWidget() is not None:
                    continue
                handle = w.windowHandle()
                if handle is None:
                    continue
                hwnd = int(handle.winId())
                if hwnd:
                    _win_apply_titlebar(hwnd, dark)
            except Exception:
                continue
else:
    def _win_apply_titlebar_all(app: QtWidgets.QApplication, dark: bool) -> None:  # no-op для не-Windows
        return


def style(app: QtWidgets.QApplication, *, theme: str | None = None, icon_dir: str = DEFAULT_ICON_DIR) -> None:
    if theme is not None:
        app.setProperty("nik_theme", theme.lower())
    dark = is_dark_theme(app)

    # Apply shared Larix Nexus-like base style first.
    try:
        theme_fn = globals().get("theme")
        if callable(theme_fn):
            theme_fn(app, dark, icon_dir=icon_dir, persist=False)
    except Exception:
        pass

    ar_down = resolve_icon_path("arrow_down", icon_dir, app=app)
    ar_up = resolve_icon_path("arrow_up", icon_dir, app=app)
    ar_right = resolve_icon_path("arrow_right", icon_dir, app=app)
    ar_left = resolve_icon_path("arrow_left", icon_dir, app=app) or _ensure_rotated_left(icon_dir)
    if dark and ar_left:
        ar_left = _ensure_white_copy(ar_left, icon_dir)

    # Стрелка для выпадающего списка — строго этот PNG
    cmb_down = resolve_icon_path("arrow_down_free", icon_dir, app=app) or ar_down

    # Чекбоксы (PNG): unchecked = check.png, checked = select.png
    chk_off = resolve_icon_path("check", icon_dir, app=app)
    chk_on = resolve_icon_path("select", icon_dir, app=app)
    # indeterminate state icon (dash)
    chk_mid = resolve_icon_path("poloska", icon_dir, app=app)
    # Ensure contrast: in light theme tint to black; in dark theme resolve_icon_path already returns white copies
    if not dark:
        if chk_off:
            chk_off = _ensure_black_copy(chk_off, icon_dir)
        if chk_on:
            chk_on = _ensure_black_copy(chk_on, icon_dir)
        if chk_mid:
            chk_mid = _ensure_black_copy(chk_mid, icon_dir)

    # Круглые чекбоксы (PNG): unchecked = circle2.png, checked = circle dot.png
    rchk_off = resolve_icon_path("circle2", icon_dir, app=app)
    rchk_on = resolve_icon_path("circle_dot", icon_dir, app=app)

    # List hover icons: in dark theme, tint to black on hover
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

    # Темним нативный заголовок/рамку на Windows
    _win_apply_titlebar_all(app, dark)

    # Авто-увеличение кнопки "Загрузить проекты" по тексту
    try:
        class _LoadProjectsBooster(QtCore.QObject):
            def _maybe_mark(self, btn: QtWidgets.QPushButton):
                try:
                    txt = (btn.text() or "").strip().lower()
                    objn = (btn.objectName() or "").strip().lower()
                except Exception:
                    return
                if txt in ("проект", "проект") or objn in ("load_btn", "loadprojects", "loadprojectsbutton"):
                    if btn.property("largeButton") is not True:
                        btn.setProperty("largeButton", True)
                        btn.style().unpolish(btn); btn.style().polish(btn)

            def eventFilter(self, obj, ev):
                t = ev.type()
                if t in (QtCore.QEvent.Show, QtCore.QEvent.Polish):
                    if isinstance(obj, QtWidgets.QPushButton):
                        self._maybe_mark(obj)
                elif t == QtCore.QEvent.ChildAdded:
                    try:
                        ch = ev.child()
                    except Exception:
                        ch = None
                    if isinstance(ch, QtWidgets.QPushButton):
                        self._maybe_mark(ch)
                return False

        booster = _LoadProjectsBooster(app)
        app.installEventFilter(booster)
        # Сразу отметить уже существующие
        for w in app.allWidgets():
            if isinstance(w, QtWidgets.QPushButton):
                booster._maybe_mark(w)
        # Не дать сборщику мусора удалить фильтр
        setattr(app, "_nik_load_projects_booster", booster)
    except Exception:
        pass


# ---------------------------------
# Красивый свитч темы с анимацией
# ---------------------------------
class ThemeSwitch(QtWidgets.QAbstractButton):
    """Свитч темы как в Dekstop: серый трек, оранжевое выделение активной иконки,
    без бегунка; иконки меняются местами при переключении."""
    toggledTheme = QtCore.Signal(str) if hasattr(QtCore, "Signal") else QtCore.pyqtSignal(str)
    _anim_t = 0.0

    def __init__(self, parent=None, icon_dir: str = DEFAULT_ICON_DIR):
        super().__init__(parent)
        self.setCheckable(True)
        self._icon_dir = icon_dir
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Переключить тему")
        self.setFixedSize(66, 28)
        self._anim = QtCore.QPropertyAnimation(self, b"anim_t", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.toggled.connect(self._on_toggled)
        app = QtWidgets.QApplication.instance()
        self.setChecked(is_dark_theme(app))

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
        new_theme = "dark" if checked else "light"
        theme(app, new_theme == "dark", self._icon_dir)
        self.toggledTheme.emit(new_theme)

    def sizeHint(self):
        return QtCore.QSize(66, 28)

    def _load_icon_pm(self, name: str) -> QtGui.QPixmap:
        p = resolve_icon_path(name, self._icon_dir)
        if p and os.path.exists(p):
            pm = QtGui.QPixmap(p)
            if not pm.isNull():
                return pm
        # фолбэк: эмодзи
        pm = QtGui.QPixmap(24, 24)
        pm.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pm)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            font = painter.font(); font.setPointSize(16); painter.setFont(font)
            painter.drawText(pm.rect(), QtCore.Qt.AlignCenter, "☀" if name == "sun" else "🌙")
        finally:
            painter.end()
        return pm

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        try:
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            rect = self.rect()
            track = rect.adjusted(1, 1, -1, -1)
            p.setClipRect(track)

            dark = self.isChecked()  # checked => dark

            # 1) Трек
            track_bg = QtGui.QColor("#3d3d3d" if dark else "#d5d5d5")
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(track_bg)
            p.drawRoundedRect(track, track.height()/2.0, track.height()/2.0)

            # Геометрия
            icon_size = int(track.height() * 0.55)
            center_y = track.center().y()
            pad = 6
            left_x = track.left() + pad
            right_x = track.right() - icon_size - pad

            # Иконки меняются местами по анимации (как в Dekstop)
            sun_on_left = (self._anim_t >= 0.5)
            sun_x = left_x if sun_on_left else right_x
            moon_x = right_x if sun_on_left else left_x
            # 2) Подложку неактивной темы убираем - без чёрного круга

            # 3) Оранжевое выделение активной темы — под соответствующей иконкой
            hl_d = icon_size + 8
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor("#F7921E"))  # фирменный оранжевый
            if dark:
                # в тёмной теме выделяем ЛУНУ
                p.drawEllipse(QtCore.QRectF(moon_x - (hl_d - icon_size)/2, center_y - hl_d/2, hl_d, hl_d))
            else:
                # в светлой — СОЛНЦЕ
                p.drawEllipse(QtCore.QRectF(sun_x - (hl_d - icon_size)/2, center_y - hl_d/2, hl_d, hl_d))

            # 4) Иконки сверху, с тинтом как в Dekstop (#222 в лайте, белые в дарке)
            sun_pm = self._load_icon_pm("sun").scaled(icon_size, icon_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            moon_pm = self._load_icon_pm("moon").scaled(icon_size, icon_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            tint_col = QtGui.QColor("#FFFFFF" if dark else "#222222")
            if not sun_pm.isNull():
                sun_pm = _tint_pixmap(sun_pm, tint_col)
            if not moon_pm.isNull():
                moon_pm = _tint_pixmap(moon_pm, tint_col)
            p.setOpacity(1.0)
            p.drawPixmap(int(sun_x), int(center_y - icon_size/2), sun_pm)
            p.drawPixmap(int(moon_x), int(center_y - icon_size/2), moon_pm)
        finally:
            p.end()

SunMoonSwitch = ThemeSwitch

# -----------------
# Утилиты для лого
# -----------------

def set_header_logo(label: QtWidgets.QLabel, icon_dir: str = DEFAULT_ICON_DIR, *, height: int = 52) -> None:
    pm = load_logo(icon_dir)
    if not pm.isNull():
        label.setPixmap(pm.scaledToHeight(height, QtCore.Qt.SmoothTransformation))
        label.setAlignment(QtCore.Qt.AlignCenter)


# -----------------------
# Подсветка строки таблицы при hover (делегат)
# -----------------------
class _RowHoverDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, table: QtWidgets.QAbstractItemView, hover_row_ref):
        super().__init__(table)
        self._table = table
        self._hover_row_ref = hover_row_ref
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        opt = QtWidgets.QStyleOptionViewItem(option)
        # Если строка под курсором и она не выделена — подсветим как кнопка (SOFT_HOVER) и сделаем чёрный текст
        if index.row() == self._hover_row_ref[0] and not (opt.state & QtWidgets.QStyle.State_Selected):
            painter.save()
            painter.fillRect(opt.rect, QtGui.QColor(PALETTE.SOFT_HOVER))
            painter.restore()
            opt.palette.setColor(QtGui.QPalette.Text, QtGui.QColor("#000000"))
        super().paint(painter, opt, index)

def enable_row_hover(table: QtWidgets.QTableWidget) -> None:
    table.setMouseTracking(True)
    # Храним текущую строку под курсором в одном элементе списка (чтобы был по ссылке)
    hover_row = [-1]
    # Делегат, который рисует подсветку
    table.setItemDelegate(_RowHoverDelegate(table, hover_row))
    # Фильтр событий на viewport для отслеживания наведения/ухода курсора
    class _HoverFilter(QtCore.QObject):
        def eventFilter(self, obj, ev):
            t = ev.type()
            if t == QtCore.QEvent.MouseMove:
                idx = table.indexAt(ev.pos())
                r = idx.row() if idx.isValid() else -1
                if r != hover_row[0]:
                    hover_row[0] = r
                    table.viewport().update()
            elif t == QtCore.QEvent.Leave:
                if hover_row[0] != -1:
                    hover_row[0] = -1
                    table.viewport().update()
            return False
    filt = _HoverFilter(table)
    table.viewport().installEventFilter(filt)
    # Сохраним ссылку, чтобы GC не съел
    setattr(table, "_nik_rowhover_filter", filt)

# -----------------------
# Пример демо - можно удалить
# -----------------------


# XML processing
from xml.etree import ElementTree as ET

# ----------------- Константы проекта -----------------
SEGOE_10   = QtGui.QFont("Segoe UI", 10)

# Пути логотипов используются только как фолбэк; основной механизм — set_header_logo(icon_dir="icon")
LOGO_PATH = _resource_path("icon", "Manager-scaled.png")
LOGO_PATH_WHITE = _resource_path("icon", "Manager-scaled_white.png")
LOGO_H = 52
APP_ICON_PATH = _resource_path("icon", "logo.ico")

# Поля Excel
GROUP_COL_DEFAULT = "Элементы модели"
CAT_COL_DEFAULT   = "Категория Revit"
IFC_COL_DEFAULT   = "Пример Класса IFC"
CLASSIF_CODE_COL_DEFAULT = "Код по классификатору"

FIELD_NAME_DEFAULT_CATEGORY = "Категория:\\"
FIELD_NAME_DEFAULT_CLASSIF  = "Тип:\\Код по классификатору"
FIELD_NAME_DEFAULT_IFC      = "IfcClass"
FIELD_NAME_SUGGESTIONS = [
    FIELD_NAME_DEFAULT_CATEGORY,
    FIELD_NAME_DEFAULT_CLASSIF,
    FIELD_NAME_DEFAULT_IFC,
]



API_BASE_URL_DEFAULT = "http://localhost:5000"


def _runtime_api_base_url() -> str:
    return (os.environ.get("LARIX_API_BASE_URL") or API_BASE_URL_DEFAULT).rstrip("/")

ICON_DIR = DEFAULT_ICON_DIR  # папка с PNG

# -------- Hover delegate for table (highlight full row on hover) --------
class _RowHoverDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, get_hover_row: Callable[[], int], parent=None):
        super().__init__(parent)
        self._get_hover_row = get_hover_row
        self._hover_color = QtGui.QColor("#FFE3C2")

    def paint(self, painter, option, index):
        try:
            hover_row = int(self._get_hover_row() or -1)
        except Exception:
            hover_row = -1
        opt = QtWidgets.QStyleOptionViewItem(option)
        if hover_row >= 0 and index.row() == hover_row and not (opt.state & QtWidgets.QStyle.State_Selected):
            painter.save()
            painter.fillRect(opt.rect, self._hover_color)
            painter.restore()
            pal = QtGui.QPalette(opt.palette)
            black = QtGui.QColor("#000000")
            for role in (QtGui.QPalette.Text, QtGui.QPalette.WindowText, QtGui.QPalette.ButtonText, QtGui.QPalette.HighlightedText):
                pal.setColor(QtGui.QPalette.Active, role, black)
                pal.setColor(QtGui.QPalette.Inactive, role, black)
            opt.palette = pal
        super().paint(painter, opt, index)


def sanitize_str(x) -> str:
    if x is None or (isinstance(x, float) and (pd is not None) and pd.isna(x)):
        return ""
    s = str(x).replace("\\xa0", " ").strip()
    return "" if s.lower() == "nan" else re.sub(r"\\s+", " ", s)


def split_tokens(val: str) -> List[str]:
    s = sanitize_str(val)
    if not s:
        return []
    s = re.sub(r"[;\\n|/\\\\]+", ",", s)
    tokens = [t.strip() for t in s.split(",")]
    bad = {"", "уточняется в пим", "уточняется", "пим"}
    out, seen = [], set()
    for t in tokens:
        k = t.lower()
        if t and k not in bad and k not in seen:
            seen.add(k); out.append(t)
    return out


class ReorderListWidget(QtWidgets.QListWidget):
    reordered = QtCore.Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    def dropEvent(self, e):
        super().dropEvent(e)
        try:
            self.reordered.emit()
        except Exception:
            pass
# ----------------- Простая секция (совместимость со старым Section) -----------------
class Section(QtWidgets.QGroupBox):
    """Минимальная совместимость: .frame_l - это QGridLayout для размещения контента."""
    def __init__(self, title: str = "", parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(title, parent)
        lay = QtWidgets.QGridLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)
        self.frame_l = lay

# ----------------- API helpers -----------------
def _check_requests():
    if requests is None:
        raise RuntimeError("Нужен 'requests': pip install requests")


def _api_get(url: str, **kwargs):
    _check_requests()
    r = requests.get(url, timeout=30, **kwargs)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return json.loads(r.text)


def api_get_projects(base_url: str) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/project/projects"
    data = _api_get(url) or []
    return [{"id": x.get("id"), "title": x.get("title") or x.get("name") or f"ID {x.get('id')}"} for x in data]


def api_get_containers(base_url: str, project_id: int) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/imcContainer/getProjectImcContainers/{project_id}"
    data = _api_get(url) or []
    return [{"id": x.get("id"), "title": x.get("title") or f"ID {x.get('id')}"} for x in data]


def api_get_parameters(base_url: str, container_ids: List[int]) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/imcParameterDefinition/imcParameterDefinitions"
    params = [("containerIds", cid) for cid in container_ids]
    data = _api_get(url, params=params) or []
    return data

# ----------------- Диалоги API -----------------
def _apply_dark_titlebar_win(widget):
    """Force dark titlebar on Windows if dark theme is active. No-op elsewhere."""
    try:
        import sys, ctypes
        from ctypes import wintypes
        if sys.platform != "win32":
            return
        app = QtWidgets.QApplication.instance()
        dark = is_dark_theme(app) if app else False
        hwnd = int(widget.winId())
        # Best-effort: Windows 10 1903+ uses 20, older 1809 uses 19
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        val = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd),
                                                   ctypes.c_uint(DWMWA_USE_IMMERSIVE_DARK_MODE),
                                                   ctypes.byref(val),
                                                   ctypes.sizeof(val))
        # Try older attribute id if first call had no effect
        if dark:
            DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
            ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd),
                                                       ctypes.c_uint(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD),
                                                       ctypes.byref(val),
                                                       ctypes.sizeof(val))
        # Explicit caption/text/border colors for reliable dark title bar
        if dark:
            caption_color = 0x000000
            text_color = 0xFFFFFF
            border_color = 0x000000
        else:
            caption_color = 0xFFFFFF
            text_color = 0x000000
            border_color = 0xDCDCDC
        for attr, color in ((35, caption_color), (36, text_color), (34, border_color)):
            try:
                cval = ctypes.c_int(color)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd),
                                                           ctypes.c_uint(attr),
                                                           ctypes.byref(cval),
                                                           ctypes.sizeof(cval))
            except Exception:
                pass
    except Exception:
        pass

class ApiSelectDialog(QtWidgets.QDialog):
    def __init__(self, master: QtWidgets.QWidget, base_url: str,
                 load_projects, load_containers, load_params,
                 on_import, extract_adapted=None, state=None):
        super().__init__(master)
        self.setWindowTitle("Выбор из API")
        self.setModal(True)
        self.resize(960, 660)

        self._load_projects = load_projects
        self._load_containers = load_containers
        self._load_params = load_params
        self._extract_adapted = extract_adapted
        self._on_import = on_import
        self._state = state if isinstance(state, dict) else {}

        self._projects: List[Dict[str, Any]] = []
        self._containers: List[Dict[str, Any]] = []
        self._params_all: List[Dict[str, Any]] = []
        self._params_shown: List[Dict[str, Any]] = []

        self._build_ui()

        self._refresh_projects()
        self._restore_state()

    # Тёмный заголовок в дарк-теме
    def showEvent(self, e):
        try:
            _apply_dark_titlebar_win(self)
        finally:
            try:
                super().showEvent(e)
            except Exception:
                pass

    def event(self, ev):
        try:
            if ev and getattr(ev, "type", lambda: None)() in (QtCore.QEvent.PaletteChange, QtCore.QEvent.StyleChange):
                _apply_dark_titlebar_win(self)
        except Exception:
            pass
        return super().event(ev)

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(10,10,10,10); root.setSpacing(10)
        row0 = QtWidgets.QHBoxLayout(); root.addLayout(row0)
        self.btn_proj = QtWidgets.QPushButton("Обновить проекты"); row0.addWidget(self.btn_proj)
        row0.addStretch(1)

        row1 = QtWidgets.QHBoxLayout(); root.addLayout(row1)
        row1.addWidget(QtWidgets.QLabel("Проект:"))
        self.cmb_projects = QtWidgets.QComboBox(); row1.addWidget(self.cmb_projects, 1)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal); root.addWidget(split, 1)

        left_box = QtWidgets.QGroupBox("Модели (IMC)")
        left_l = QtWidgets.QVBoxLayout(left_box)
        self.lst_cont = QtWidgets.QListWidget()
        self.lst_cont.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lst_cont.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lst_cont.setStyleSheet("border: none;")
        self.lst_cont.setItemDelegate(_ApiModelListDelegate(self.lst_cont, icon_dir=ICON_DIR))
        left_l.addWidget(self.lst_cont, 1)
        split.addWidget(left_box); left_box.setMinimumWidth(260)

        mid = QtWidgets.QWidget(); mid_l = QtWidgets.QVBoxLayout(mid); mid_l.setContentsMargins(6,6,6,6)
        self.btn_load_params = QtWidgets.QPushButton("Загрузить параметры")
        mid_l.addWidget(self.btn_load_params); mid_l.addStretch(1)
        split.addWidget(mid); mid.setMaximumWidth(220)

        right_sec = Section("Параметры"); split.addWidget(right_sec)
        g: QtWidgets.QGridLayout = right_sec.frame_l
        g.setRowStretch(0, 0); g.setRowStretch(1, 1)

        filter_row = QtWidgets.QHBoxLayout()
        g.addLayout(filter_row, 0, 0, 1, 1)
        self.chk_type_num = QtWidgets.QCheckBox("Числовые"); self.chk_type_num.setChecked(True); filter_row.addWidget(self.chk_type_num)
        self.chk_type_str = QtWidgets.QCheckBox("Строковые"); self.chk_type_str.setChecked(True); filter_row.addWidget(self.chk_type_str)
        filter_row.addWidget(QtWidgets.QLabel("Фильтр по наименованию:"))
        self.ed_filter = QtWidgets.QLineEdit(); filter_row.addWidget(self.ed_filter, 1)
        self.btn_find = QtWidgets.QPushButton("Найти"); filter_row.addWidget(self.btn_find)

        self.tbl = QtWidgets.QTableWidget(0, 2)
        self.tbl.setObjectName("apiParamsTable")
        self.tbl.setShowGrid(False)
        self.tbl.setFocusPolicy(QtCore.Qt.NoFocus)
        self.tbl.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tbl.setStyleSheet("border: none;")
        self.tbl.verticalHeader().setVisible(False)

        # Hover всей строки
        self._hover_row = -1
        self.tbl.setMouseTracking(True)
        self.tbl.viewport().setMouseTracking(True)
        self.tbl.viewport().installEventFilter(self)
        self.tbl.setItemDelegate(_RowHoverDelegate(lambda: self._hover_row, self.tbl))

        self.tbl.setHorizontalHeaderLabels(["Наименование", "Тип"])
        header = self.tbl.horizontalHeader()
        header.setSectionsClickable(True)
        header.setHighlightSections(False)
        header.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_params_header_menu)
        try:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        except Exception:
            pass
        self.tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        g.addWidget(self.tbl, 1, 0, 1, 1)

        bottom = QtWidgets.QHBoxLayout(); root.addLayout(bottom)
        bottom.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_import = QtWidgets.QPushButton("Выбрать")
        bottom.addWidget(self.btn_cancel); bottom.addWidget(self.btn_import)

        # Signals
        self.btn_proj.clicked.connect(self._refresh_projects)
        self.cmb_projects.currentIndexChanged.connect(self._on_project_changed)
        self.btn_load_params.clicked.connect(lambda _checked=False: self._load_parameters())
        self.lst_cont.itemDoubleClicked.connect(self._on_model_double_clicked)
        self.lst_cont.itemChanged.connect(self._on_model_item_changed)
        self.ed_filter.textChanged.connect(self._apply_filter)
        self.btn_find.clicked.connect(self._apply_filter)
        self.chk_type_num.toggled.connect(self._apply_filter)
        self.chk_type_str.toggled.connect(self._apply_filter)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_import.clicked.connect(self._do_import)
        self.tbl.itemDoubleClicked.connect(self._on_param_double_clicked)

        self.chk_type_num.hide()
        self.chk_type_str.hide()

    def eventFilter(self, obj, event):
        if obj is self.tbl.viewport():
            t = event.type()
            if t == QtCore.QEvent.MouseMove:
                mi = self.tbl.indexAt((event.position().toPoint() if hasattr(event, "position") else event.pos()))
                row = int(mi.row()) if mi.isValid() else -1
                if row != getattr(self, "_hover_row", -1):
                    self._hover_row = row
                    self.tbl.viewport().update()
            elif t in (QtCore.QEvent.Leave, QtCore.QEvent.HoverLeave):
                if getattr(self, "_hover_row", -1) != -1:
                    self._hover_row = -1
                    self.tbl.viewport().update()
        return super().eventFilter(obj, event)

    def _get_base_url(self) -> str:
        return _runtime_api_base_url()

    def _apply_filter(self):
        text = (self.ed_filter.text() or "").lower()
        rows = self._params_all
        if text:
            rows = [r for r in rows if (text in (r.get("name") or "").lower()) or (text in (r.get("code") or "").lower())]
        include_num = bool(self.chk_type_num.isChecked())
        include_str = bool(self.chk_type_str.isChecked())
        if not (include_num and include_str):
            rows = [r for r in rows if (bool(r.get("isNumeric")) and include_num) or ((not bool(r.get("isNumeric"))) and include_str)]
        self._fill_params(rows)

    def _fill_params(self, rows: List[Dict[str, Any]]):
        self._params_shown = rows[:]
        self.tbl.setRowCount(0)
        for r in rows:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            title = r.get("code", "")
            typ = "число" if r.get("isNumeric") else "текст"
            it0 = QtWidgets.QTableWidgetItem(title); it0.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            it1 = QtWidgets.QTableWidgetItem(typ);   it1.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            self.tbl.setItem(row, 0, it0); self.tbl.setItem(row, 1, it1)

    def _on_params_header_menu(self, pos: QtCore.QPoint):
        header: QtWidgets.QHeaderView = self.tbl.horizontalHeader()
        col = int(header.logicalIndexAt(pos))
        if col != 1:
            return
        menu = QtWidgets.QMenu(self)
        act_num = menu.addAction("Числовые"); act_num.setCheckable(True)
        act_str = menu.addAction("Строковые"); act_str.setCheckable(True)
        act_num.setChecked(self.chk_type_num.isChecked())
        act_str.setChecked(self.chk_type_str.isChecked())
        act_num.toggled.connect(lambda ch: self.chk_type_num.setChecked(ch))
        act_str.toggled.connect(lambda ch: self.chk_type_str.setChecked(ch))
        try:
            menu.exec(header.mapToGlobal(pos))
        except Exception:
            try:
                menu.exec_(header.mapToGlobal(pos))
            except Exception:
                pass

    def _refresh_projects(self) -> None:
        try:
            data = self._load_projects(self._get_base_url()) or []
        except Exception as e:
            _msg_critical(self, "API", f"Не удалось получить проекты:\n{e}"); return
        uniq: Dict[str, Dict[str, Any]] = {}
        for p in data:
            title = (p.get("title") or p.get("name") or f"ID {p.get('id')}").strip()
            k = title.lower()
            if k not in uniq:
                uniq[k] = {"id": p.get("id"), "title": title}
        self._projects = sorted(uniq.values(), key=lambda x: x["title"].lower())
        self.cmb_projects.clear()
        for p in self._projects:
            self.cmb_projects.addItem(p["title"])
        if self._projects:
            self.cmb_projects.setCurrentIndex(0)
            self._refresh_containers()

    def _on_project_changed(self, index: int) -> None:
        if index >= 0:
            self._refresh_containers()

    def _refresh_containers(self) -> None:
        idx = self.cmb_projects.currentIndex()
        if idx < 0:
            return
        pid = int(self._projects[idx]["id"])
        try:
            data = self._load_containers(self._get_base_url(), pid) or []
        except Exception as e:
            _msg_critical(self, "API", f"Не удалось получить модели:\n{e}"); return
        uniq: Dict[str, Dict[str, Any]] = {}
        for c in data:
            title = (c.get("title") or f"ID {c.get('id')}").strip()
            k = title.lower()
            if k not in uniq:
                uniq[k] = {"id": c.get("id"), "title": title}
        self._containers = sorted(uniq.values(), key=lambda x: x["title"].lower())
        self.lst_cont.blockSignals(True)
        self.lst_cont.clear()
        item_all = QtWidgets.QListWidgetItem("Все модели")
        item_all.setFlags(item_all.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        item_all.setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.lst_cont.addItem(item_all)
        for c in self._containers:
            item = QtWidgets.QListWidgetItem(c["title"])
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.lst_cont.addItem(item)
        self.lst_cont.blockSignals(False)

    def _on_model_item_changed(self, item: QtWidgets.QListWidgetItem) -> None:
        item_all = self.lst_cont.item(0)
        if item is item_all:
            state = item.checkState()
            self.lst_cont.blockSignals(True)
            for i in range(1, self.lst_cont.count()):
                self.lst_cont.item(i).setCheckState(state)
            self.lst_cont.blockSignals(False)
        else:
            all_checked = all(
                self.lst_cont.item(i).checkState() == QtCore.Qt.CheckState.Checked
                for i in range(1, self.lst_cont.count())
            )
            self.lst_cont.blockSignals(True)
            item_all.setCheckState(QtCore.Qt.CheckState.Checked if all_checked else QtCore.Qt.CheckState.Unchecked)
            self.lst_cont.blockSignals(False)

    def _on_model_double_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        idx = self.lst_cont.row(item)
        if idx <= 0:
            return
        model_idx = idx - 1
        self._load_parameters(model_indices=[model_idx])

    def _load_parameters(self, model_indices: Optional[List[int]] = None) -> None:
        if isinstance(model_indices, bool):
            model_indices = None
        if model_indices is None:
            checked_indices: List[int] = []
            for i in range(1, self.lst_cont.count()):
                item = self.lst_cont.item(i)
                if item and item.checkState() == QtCore.Qt.CheckState.Checked:
                    checked_indices.append(i - 1)
            if checked_indices:
                target_indices = checked_indices
            else:
                selected_rows = sorted({
                    idx.row() - 1
                    for idx in (self.lst_cont.selectedIndexes() or [])
                    if idx.isValid() and idx.row() > 0
                })
                if not selected_rows:
                    show_warning_dialog("Выберите одну или несколько моделей.", title="API", parent=self, modal=True)
                    return
                target_indices = selected_rows
            ids = [int(self._containers[idx]["id"]) for idx in target_indices]
            titles = [self._containers[idx]["title"] for idx in target_indices]
        else:
            if not model_indices:
                return
            ids = [int(self._containers[idx]["id"]) for idx in model_indices]
            titles = [self._containers[idx]["title"] for idx in model_indices]
        try:
            native = self._load_params(self._get_base_url(), ids) or []
        except Exception as e:
            _msg_critical(self, "API", f"Не удалось получить параметры моделей:\n{e}"); return

        src_unified: List[Dict[str, Any]] = []
        for r in native:
            name = (r.get("title") or r.get("name") or r.get("code") or "").strip()
            src_unified.append({"code": r.get("code") or "", "isNumeric": bool(r.get("isNumeric")), "name": name})

        combined: Dict[str, Dict[str, Any]] = {}
        for r in src_unified:
            code = (r.get("code") or "").lower()
            if not code:
                continue
            if code not in combined:
                combined[code] = r

        self._params_all = sorted(combined.values(), key=lambda x: (x.get("name") or "").lower())
        self._apply_filter()

        self._state["project_title"] = self.cmb_projects.currentText().strip()
        self._state["container_titles"] = titles
        self._state["param_filter"] = self.ed_filter.text()
        self._state["last_base_url"] = _runtime_api_base_url()

    def _on_param_double_clicked(self, item: QtWidgets.QTableWidgetItem):
        try:
            row = int(item.row()) if item is not None else int(self.tbl.currentRow())
        except Exception:
            row = self.tbl.currentRow()
        try:
            if row is not None and row >= 0:
                self.tbl.clearSelection()
                self.tbl.selectRow(row)
        except Exception:
            pass
        self._do_import()

    def _do_import(self) -> None:
        row = self.tbl.currentRow()
        if row < 0 or row >= len(self._params_shown):
            show_warning_dialog("Выберите параметр из списка.", title="API", parent=self, modal=True)
            return
        r = self._params_shown[row]
        result = [{"code": r.get("code",""), "isNumeric": bool(r.get("isNumeric")), "name": r.get("name","")}]
        try:
            self._on_import(result)
        finally:
            self.accept()

    def _restore_state(self) -> None:
        if self._state.get("param_filter"):
            self.ed_filter.setText(self._state["param_filter"])

# ----------------- Helper functions -----------------
def _msg_critical(parent, title: str, text: str):
    """Show critical error message"""
    show_error_dialog(text, title=title, parent=parent, modal=True)

def indent_xml(elem, level: int = 0) -> None:
    """Pretty-print XML with indentation"""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent_xml(e, level + 1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def build_empty_item_block():
    cb = ET.Element("ConditionBlock", {"Type": "Block"})
    ET.SubElement(cb, "Condition", {
        "FieldIsNumeric": "false",
        "TextSpaceSensitive": "true",
        "IsUndefinedFieldName": "false",
    })
    ET.SubElement(cb, "ConditionsBlocks")
    return cb

def build_single_condition_block(value: str, field_name: str):
    b = ET.Element("ConditionsBlock")
    ET.SubElement(b, "Condition", {
        "FieldName": field_name,
        "FieldIsNumeric": "false",
        "Value": value,
        "IsUndefinedFieldName": "false",
    })
    ET.SubElement(b, "ConditionsBlocks")
    return b

def build_flat_condition_block(field_values_pairs: List[Tuple[str, List[str]]]):
    flat_conditions: List[Tuple[str, str]] = []
    for field_name, values in (field_values_pairs or []):
        field = sanitize_str(field_name)
        if not field:
            continue
        for value in (values or []):
            v = sanitize_str(value)
            if v:
                flat_conditions.append((field, v))
    if not flat_conditions:
        return build_empty_item_block()

    cb = ET.Element("ConditionBlock", {"Type": "Block", "LogicalOperator": "Or"})
    ET.SubElement(cb, "Condition", {
        "IsUndefinedFieldName": "false",
    })
    blocks = ET.SubElement(cb, "ConditionsBlocks")
    for field_name, value in flat_conditions:
        blocks.append(build_single_condition_block(value, field_name))
    return cb


def build_grouped_condition_block(field_values_pairs: List[Tuple[str, List[str]]]):
    field_to_values: Dict[str, List[str]] = {}
    field_order: List[str] = []
    for field_name, values in (field_values_pairs or []):
        field = sanitize_str(field_name)
        if not field:
            continue
        bucket = field_to_values.setdefault(field, [])
        if field not in field_order:
            field_order.append(field)
        for value in (values or []):
            v = sanitize_str(value)
            if v and v not in bucket:
                bucket.append(v)
    if not any(field_to_values.values()):
        return build_empty_item_block()

    cb = ET.Element("ConditionBlock", {"Type": "Block", "LogicalOperator": "Or"})
    ET.SubElement(cb, "Condition", {
        "IsUndefinedFieldName": "false",
    })
    blocks = ET.SubElement(cb, "ConditionsBlocks")
    for field_name in field_order:
        values = field_to_values.get(field_name, [])
        if not values:
            continue
        field_block = ET.Element("ConditionsBlock", {"Type": "Block", "LogicalOperator": "Or"})
        ET.SubElement(field_block, "Condition", {
            "IsUndefinedFieldName": "false",
        })
        value_blocks = ET.SubElement(field_block, "ConditionsBlocks")
        for value in values:
            value_blocks.append(build_single_condition_block(value, field_name))
        blocks.append(field_block)
    return cb


def build_mixed_item_condition_block_3(cat_values, cat_field, cls_values, cls_field, ifc_values, ifc_field):
    return build_grouped_condition_block([
        (cat_field, cat_values or []),
        (cls_field, cls_values or []),
        (ifc_field, ifc_values or []),
    ])

def _build_classif_map_from_df(df_cls):
    if pd is None:
        return {}
    for col in df_cls.columns:
        df_cls[col] = df_cls[col].map(sanitize_str)
    result = {}
    for _, row in df_cls.iterrows():
        name = sanitize_str(row.get(GROUP_COL_DEFAULT, ""))
        if not name: 
            continue
        codes = split_tokens(sanitize_str(row.get(CLASSIF_CODE_COL_DEFAULT, "")))
        if not codes:
            continue
        bucket = result.setdefault(name, [])
        for c in codes:
            if c not in bucket:
                bucket.append(c)
    return result

def df_to_items_gui(df, profile_items_el, *, id_start, profile_title, group_column, category_column, ifc_column,
                    auto_number, build_filters, field_name_category, field_name_ifc, filter_mode,
                    classif_map, classif_column, field_name_classif, group_idx_start=0,
                    param_field_map: Optional[Dict[str, str]] = None,
                    active_param_columns: Optional[List[str]] = None,
                    grouped: bool = False):
    if pd is None:
        raise RuntimeError("Нужен pandas: pip install pandas")
    next_id = id_start
    def new_id():
        nonlocal next_id
        next_id += 1
        return next_id
    
    def extract_prefix(s):
        m = re.match(r"^(\d+(?:\.\d+)*)_", s)
        return m.group(1) if m else None
    
    def get_level(prefix):
        return len(prefix.split(".")) if prefix else 0
    
    def get_parent_prefix(prefix):
        return ".".join(prefix.split(".")[:-1]) if "." in (prefix or "") else None
    
    def find_existing_parent(prefix, prefix_to_id_map):
        if not prefix:
            return None
        parts = prefix.split(".")
        for i in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in prefix_to_id_map:
                return candidate
        return None
    
    def strip_prefix(s):
        if not s: return s
        return re.sub(r"^\d+(\.\d+)*_", "", s)

    for col in df.columns:
        df[col] = df[col].map(sanitize_str)

    effective_param_map: Dict[str, str] = {}
    if param_field_map:
        for col, field in param_field_map.items():
            c = str(col or "").strip()
            f = sanitize_str(field)
            if c and f:
                effective_param_map[c] = f

    if not effective_param_map:
        if filter_mode in ("category", "both"):
            if sanitize_str(category_column) and sanitize_str(field_name_category):
                effective_param_map[category_column] = field_name_category
            if sanitize_str(ifc_column) and sanitize_str(field_name_ifc):
                effective_param_map[ifc_column] = field_name_ifc
        if filter_mode in ("classifier", "both") and sanitize_str(classif_column) and sanitize_str(field_name_classif):
            effective_param_map[classif_column] = field_name_classif

    if active_param_columns:
        active_cols = [c for c in active_param_columns if c in effective_param_map]
    else:
        active_cols = list(effective_param_map.keys())

    def _split_values(s: str):
        if not s: return []
        s = re.sub(r"[;\n|/\\]+", ",", s)
        toks = [t.strip() for t in s.split(",") if t.strip()]
        out=[]; seen=set()
        for t in toks:
            if t not in seen: seen.add(t); out.append(t)
        return out

    def _cell_values(row_obj, col_name: str, item_name: str) -> List[str]:
        if not col_name or col_name not in df.columns:
            return []
        if classif_map and col_name == classif_column and item_name in classif_map:
            vals = classif_map[item_name][:]
            return [sanitize_str(v) for v in vals if sanitize_str(v)]
        raw = sanitize_str(row_obj.get(col_name, ""))
        return _split_values(raw)

    def _row_has_params(row_obj, item_name: str) -> bool:
        for col_name in active_cols:
            if _cell_values(row_obj, col_name, item_name):
                return True
        return False

    df = df[df.apply(lambda row_obj: sanitize_str(row_obj.get(group_column, "")) != "" or _row_has_params(row_obj, sanitize_str(row_obj.get(group_column, ""))), axis=1)]

    rows_data = []
    for _, row in df.iterrows():
        name_1st = sanitize_str(row.get(group_column, ""))
        condition_pairs: List[Tuple[str, List[str]]] = []
        has_any_values = False
        for col_name in active_cols:
            field_name = effective_param_map.get(col_name, "")
            values = _cell_values(row, col_name, name_1st)
            if values:
                has_any_values = True
            condition_pairs.append((field_name, values))

        if name_1st == profile_title and not has_any_values:
            continue

        is_root = bool(name_1st and not has_any_values)
        is_razdel = "раздел" in name_1st.lower() and not has_any_values

        prefix = extract_prefix(name_1st)
        level = get_level(prefix)

        rows_data.append({
            "name": name_1st,
            "prefix": prefix,
            "level": level,
            "is_root": is_root,
            "is_razdel": is_razdel,
            "condition_pairs": condition_pairs,
            "orig_idx": len(rows_data),
        })

    razdel_indices = [i for i, r in enumerate(rows_data) if r["is_razdel"]]
    razdel_blocks: List[Tuple[int, int, int]] = []
    for bi, ri in enumerate(razdel_indices):
        start = ri
        end = razdel_indices[bi + 1] if bi + 1 < len(razdel_indices) else len(rows_data)
        razdel_blocks.append((ri, start + 1, end))

    def get_razdel_parent_idx(row_idx: int) -> Optional[int]:
        for razdel_idx, start, end in razdel_blocks:
            if start <= row_idx < end:
                return razdel_idx
        return None

    def _merge_condition_pairs(left_pairs: List[Tuple[str, List[str]]],
                               right_pairs: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        merged: Dict[str, List[str]] = {}
        order: List[str] = []
        for pairs in (left_pairs or [], right_pairs or []):
            for field_name, values in pairs:
                field = sanitize_str(field_name)
                if field not in merged:
                    merged[field] = []
                    order.append(field)
                for value in (values or []):
                    v = sanitize_str(value)
                    if v and v not in merged[field]:
                        merged[field].append(v)
        return [(field, merged[field]) for field in order]

    if grouped:
        merged_rows: List[Dict[str, Any]] = []
        merged_index: Dict[Tuple[Optional[int], str, str, int], Dict[str, Any]] = {}
        for row_data in rows_data:
            if row_data["is_razdel"]:
                merged_rows.append(row_data)
                continue
            section_idx = get_razdel_parent_idx(row_data["orig_idx"])
            merge_key = (
                section_idx,
                sanitize_str(row_data["prefix"] or ""),
                sanitize_str(row_data["name"]),
                int(row_data["level"]),
            )
            existing = merged_index.get(merge_key)
            if existing is None:
                row_copy = dict(row_data)
                row_copy["condition_pairs"] = _merge_condition_pairs([], row_data["condition_pairs"])
                merged_rows.append(row_copy)
                merged_index[merge_key] = row_copy
            else:
                existing["condition_pairs"] = _merge_condition_pairs(existing["condition_pairs"], row_data["condition_pairs"])
        rows_data = merged_rows

    rows_data.sort(key=lambda r: (r["prefix"] or "zzz", r["name"]))

    razdel_rows = [r for r in rows_data if r["is_razdel"]]
    other_rows = [r for r in rows_data if not r["is_razdel"]]

    razdel_orig_idx_to_id: Dict[int, int] = {}
    for ri, _, _ in razdel_blocks:
        razdel_orig_idx_to_id[ri] = None

    prefix_to_id = {}
    group_idx = group_idx_start
    child_counters = {}

    for rd in razdel_rows:
        name_1st = rd["name"]
        orig_idx = rd["orig_idx"]
        condition_pairs = rd["condition_pairs"]

        item = ET.Element("BaseExportProfileItem", {"xsi:type": "SetExportProfileItem"})
        item_id = new_id()
        ET.SubElement(item, "Id").text = str(item_id)
        ET.SubElement(item, "IsFolder").text = "true"
        ET.SubElement(item, "ParentId", {"xsi:nil": "true"})

        clean_name = strip_prefix(name_1st)
        if auto_number:
            group_idx += 1
            code = f"{group_idx:02d}"
            ET.SubElement(item, "Title").text = f"{code}_{clean_name}"
        else:
            ET.SubElement(item, "Title").text = clean_name

        if build_filters:
            builder = build_grouped_condition_block if grouped else build_flat_condition_block
            item.append(builder(condition_pairs))
        else:
            item.append(build_empty_item_block())

        profile_items_el.append(item)
        razdel_orig_idx_to_id[orig_idx] = item_id

    for rd in other_rows:
        name_1st = rd["name"]
        prefix = rd["prefix"]
        level = rd["level"]
        condition_pairs = rd["condition_pairs"]
        orig_idx = rd["orig_idx"]

        item = ET.Element("BaseExportProfileItem", {"xsi:type": "SetExportProfileItem"})
        item_id = new_id()
        ET.SubElement(item, "Id").text = str(item_id)
        ET.SubElement(item, "IsFolder").text = "true"

        razdel_parent_orig_idx = get_razdel_parent_idx(orig_idx)
        razdel_parent_id = razdel_orig_idx_to_id.get(razdel_parent_orig_idx) if razdel_parent_orig_idx is not None else None

        if prefix:
            parent_prefix = find_existing_parent(prefix, prefix_to_id)
            if parent_prefix:
                ET.SubElement(item, "ParentId").text = str(prefix_to_id[parent_prefix])
            elif razdel_parent_id is not None:
                ET.SubElement(item, "ParentId").text = str(razdel_parent_id)
            else:
                ET.SubElement(item, "ParentId", {"xsi:nil": "true"})
        else:
            if razdel_parent_id is not None:
                ET.SubElement(item, "ParentId").text = str(razdel_parent_id)
            else:
                ET.SubElement(item, "ParentId", {"xsi:nil": "true"})

        clean_name = strip_prefix(name_1st)
        if auto_number:
            if prefix:
                ET.SubElement(item, "Title").text = name_1st
                if not grouped or prefix not in prefix_to_id:
                    prefix_to_id[prefix] = item_id
            else:
                parent_prefix = find_existing_parent(prefix, prefix_to_id) if prefix else None
                
                if parent_prefix is None:
                    group_idx += 1
                    code = f"{group_idx:02d}"
                    if not grouped or code not in prefix_to_id:
                        prefix_to_id[code] = item_id
                else:
                    if parent_prefix not in child_counters:
                        child_counters[parent_prefix] = 0
                    child_counters[parent_prefix] += 1
                    code = f"{parent_prefix}.{child_counters[parent_prefix]:02d}"
                    if not grouped or code not in prefix_to_id:
                        prefix_to_id[code] = item_id
                ET.SubElement(item, "Title").text = f"{code}_{clean_name}"
        else:
            ET.SubElement(item, "Title").text = clean_name
            if prefix:
                if not grouped or prefix not in prefix_to_id:
                    prefix_to_id[prefix] = item_id

        if build_filters:
            builder = build_grouped_condition_block if grouped else build_flat_condition_block
            item.append(builder(condition_pairs))
        else:
            item.append(build_empty_item_block())

        profile_items_el.append(item)

    return next_id, group_idx

# ----------------- SheetPicker Dialog -----------------
class _SheetListDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate для списка листов: перекрашивает чекбокс в черный при hover/selected в темной теме."""
    _UNCHECKED_VALUE = getattr(QtCore.Qt.Unchecked, "value", 0)
    _CHECKED_VALUE = getattr(QtCore.Qt.Checked, "value", 2)

    def __init__(self, parent: QtWidgets.QWidget | None = None, *, icon_dir: str = DEFAULT_ICON_DIR):
        super().__init__(parent)
        self.icon_dir = icon_dir
        self._cache: dict[str, QtGui.QPixmap] = {}

    @classmethod
    def _state_value(cls, state) -> int:
        if state is None:
            return cls._UNCHECKED_VALUE
        return getattr(state, "value", state)

    def _get_pixmap(self, name: str, black: bool) -> QtGui.QPixmap:
        key = f"{name}_{'black' if black else 'normal'}"
        if key in self._cache:
            return self._cache[key]
        
        if black:
            spec = _DEKSTOP_ICON_FILES.get(name)
            candidates = spec if isinstance(spec, list) else [spec] if isinstance(spec, str) else []
            path = _first_existing(candidates, self.icon_dir)
            if not path:
                return QtGui.QPixmap()
            pm = QtGui.QPixmap(path)
            if pm.isNull():
                return pm
            pm = _tint_pixmap(pm, QtGui.QColor("#000000"))
        else:
            app = QtWidgets.QApplication.instance()
            path = resolve_icon_path(name, self.icon_dir, app=app)
            if not path:
                return QtGui.QPixmap()
            pm = QtGui.QPixmap(path)
        
        self._cache[key] = pm
        return pm

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        app = QtWidgets.QApplication.instance()
        is_hover = bool(option.state & QtWidgets.QStyle.State_MouseOver)
        is_selected = bool(option.state & QtWidgets.QStyle.State_Selected)
        is_hover_or_selected = is_hover or is_selected
        use_black = is_hover_or_selected

        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        check_state = index.data(QtCore.Qt.CheckStateRole)
        is_checked = self._state_value(check_state) == self._CHECKED_VALUE

        icon_name = "select" if is_checked else "check"
        pm = self._get_pixmap(icon_name, use_black)

        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        orig_rect = QtCore.QRect(option.rect)
        check_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, opt, opt.widget)
        margin = style.pixelMetric(QtWidgets.QStyle.PM_FocusFrameHMargin, None, opt.widget)
        gap = max(4, margin)
        text_x = check_rect.right() + gap
        text_width = orig_rect.right() - text_x

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setFont(opt.font)

        if is_hover_or_selected:
            bg_color = QtGui.QColor(PALETTE.SELECTED if is_selected else PALETTE.SOFT_HOVER)
            row_rect = orig_rect.adjusted(2, 1, -2, -1)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(row_rect, 8, 8)
            text_color = QtGui.QColor("#000000")
        else:
            text_color = QtGui.QColor(PALETTE.FG_DARK if is_dark_theme(app) else PALETTE.FG_LIGHT)

        painter.setPen(text_color)
        text_rect = QtCore.QRect(text_x, orig_rect.top(), text_width, orig_rect.height())
        elided = opt.fontMetrics.elidedText(opt.text, QtCore.Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, elided)
        painter.restore()

        if not pm.isNull():
            sz = min(pm.width(), pm.height(), check_rect.width(), check_rect.height())
            if sz > 0:
                scaled = pm.scaled(sz, sz, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                offset_y = (check_rect.height() - scaled.height()) // 2
                painter.drawPixmap(check_rect.left(), check_rect.top() + offset_y, scaled)

    def editorEvent(self, event: QtCore.QEvent, model: QtCore.QAbstractItemModel, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> bool:
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            opt = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
            check_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, opt, opt.widget)
            if check_rect.contains(event.pos()):
                current = self._state_value(index.data(QtCore.Qt.CheckStateRole))
                new_state = self._UNCHECKED_VALUE if current == self._CHECKED_VALUE else self._CHECKED_VALUE
                model.setData(index, new_state, QtCore.Qt.CheckStateRole)
                return True
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Select):
                current = self._state_value(index.data(QtCore.Qt.CheckStateRole))
                new_state = self._UNCHECKED_VALUE if current == self._CHECKED_VALUE else self._CHECKED_VALUE
                model.setData(index, new_state, QtCore.Qt.CheckStateRole)
                return True
        return super().editorEvent(event, model, option, index)


class _ApiModelListDelegate(_SheetListDelegate):
    """Delegate для списка моделей API: наследует логику _SheetListDelegate (черный чекбокс при hover/selected)."""
    pass


class SheetPickerDialog(QtWidgets.QDialog):
    """
    Простой диалог выбора листов Excel.
    Одна книга, список листов с чекбоксами.
    """
    def __init__(self, master: QtWidgets.QWidget, existing_path: str = "", existing_sheets: list|None = None):
        super().__init__(master)
        self.setWindowTitle("Выбор листа Excel")
        self.resize(500, 400)
        self._selected_path = existing_path
        self._selected_sheets = list(existing_sheets or [])

        self._build_ui()
        if existing_path:
            self._fill_sheet_list(existing_path)

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        row_file = QtWidgets.QHBoxLayout()
        root.addLayout(row_file)
        self.btn_file = QtWidgets.QPushButton("Выбрать книгу...")
        row_file.addWidget(self.btn_file)
        self.ed_path = QtWidgets.QLineEdit()
        self.ed_path.setReadOnly(True)
        if self._selected_path:
            self.ed_path.setText(self._selected_path)
        row_file.addWidget(self.ed_path, 1)

        lbl_sheets = QtWidgets.QLabel("Листы:")
        root.addWidget(lbl_sheets)

        self.lst_sheets = QtWidgets.QListWidget()
        self.lst_sheets.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lst_sheets.setStyleSheet("border: none;")
        self.lst_sheets.setItemDelegate(_SheetListDelegate(self.lst_sheets, icon_dir=DEFAULT_ICON_DIR))
        self.lst_sheets.setMouseTracking(True)
        root.addWidget(self.lst_sheets, 1)

        row_actions = QtWidgets.QHBoxLayout()
        root.addLayout(row_actions)
        self.btn_check_all = QtWidgets.QPushButton("Отметить все")
        self.btn_uncheck_all = QtWidgets.QPushButton("Снять все")
        row_actions.addWidget(self.btn_check_all)
        row_actions.addWidget(self.btn_uncheck_all)
        row_actions.addStretch(1)

        row_ok = QtWidgets.QHBoxLayout()
        root.addLayout(row_ok)
        row_ok.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_ok = QtWidgets.QPushButton("OK")
        self.btn_ok.setDefault(True)
        self.btn_ok.setAutoDefault(True)
        row_ok.addWidget(self.btn_cancel)
        row_ok.addWidget(self.btn_ok)

        self.btn_file.clicked.connect(self._pick_file)
        self.btn_check_all.clicked.connect(lambda: self._check_uncheck_all(True))
        self.btn_uncheck_all.clicked.connect(lambda: self._check_uncheck_all(False))
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._accept)

    def _pick_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выбор книги Excel", "", "Excel (*.xlsx *.xls)")
        if path:
            self._selected_path = path
            self.ed_path.setText(path)
            self._fill_sheet_list(path)

    def _fill_sheet_list(self, path: str):
        self.lst_sheets.clear()
        sheets = []
        try:
            import pandas as pd
            xls = pd.ExcelFile(path)
            sheets = list(xls.sheet_names)
        except Exception:
            sheets = ["Лист1"]
        for name in sheets:
            it = QtWidgets.QListWidgetItem(name)
            it.setFlags(it.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            it.setCheckState(QtCore.Qt.Checked if name in self._selected_sheets else QtCore.Qt.Unchecked)
            self.lst_sheets.addItem(it)

    def _check_uncheck_all(self, state: bool):
        for i in range(self.lst_sheets.count()):
            it = self.lst_sheets.item(i)
            it.setCheckState(QtCore.Qt.Checked if state else QtCore.Qt.Unchecked)

    def _accept(self):
        self._selected_sheets = []
        for i in range(self.lst_sheets.count()):
            it = self.lst_sheets.item(i)
            if it.checkState() == QtCore.Qt.Checked:
                self._selected_sheets.append(it.text())
        if not self._selected_sheets:
            show_error_dialog("Выберите хотя бы один лист.", title="Внимание", parent=self, modal=True)
            return
        self.accept()

    def result(self):
        return self._selected_path, self._selected_sheets


# ----------------- ContentWidget (main UI) -----------------



class _ParamMappingRow(QtWidgets.QWidget):
    def __init__(self, column_name: str, default_value: str, pick_api_callback: Callable[["_ParamMappingRow"], None], parent=None):
        super().__init__(parent)
        self.column_name = str(column_name or "")
        self._pick_api_callback = pick_api_callback

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.chk_active = QtWidgets.QCheckBox()
        self.chk_active.setChecked(True)
        layout.addWidget(self.chk_active)

        self.lbl_column = QtWidgets.QLabel(self.column_name)
        self.lbl_column.setMinimumWidth(260)
        layout.addWidget(self.lbl_column)

        self.cmb_field = QtWidgets.QComboBox()
        self.cmb_field.setEditable(True)
        self.cmb_field.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        for value in FIELD_NAME_SUGGESTIONS:
            self.cmb_field.addItem(value)
        self.cmb_field.setCurrentText(default_value or "")
        line_edit = self.cmb_field.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Ожидание excel")
        layout.addWidget(self.cmb_field, 1)

        self.btn_pick_api = QtWidgets.QPushButton("Выбрать из API...")
        self.btn_pick_api.setMinimumWidth(140)
        sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.btn_pick_api.setSizePolicy(sp)
        layout.addWidget(self.btn_pick_api)

        self.chk_active.toggled.connect(self._refresh_active_style)
        self.btn_pick_api.clicked.connect(lambda: self._pick_api_callback(self))
        self._refresh_active_style(self.chk_active.isChecked())

    def _refresh_active_style(self, active: bool):
        color = "" if active else "color: #8a8a8a;"
        self.lbl_column.setStyleSheet(color)
        self.cmb_field.setEnabled(active)
        self.btn_pick_api.setEnabled(active)

    def mapping_value(self) -> str:
        return sanitize_str(self.cmb_field.currentText())

    def is_active(self) -> bool:
        return bool(self.chk_active.isChecked())


class ContentWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.setProperty("noCheckHoverRecolor", True)
            self.style().unpolish(self); self.style().polish(self)
        except Exception:
            pass
        
        self._excel_path: str = ""
        self._selected_sheets: List[str] = []
        self._excel_param_columns: List[str] = []
        self._excel_column_roles: Dict[str, str] = {}
        self._header_rows_by_sheet: Dict[str, int] = {}
        self._param_rows: List[_ParamMappingRow] = []
        
        self._build_ui()
        
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)
        root.setAlignment(QtCore.Qt.AlignTop)
        
        brand_box = QtWidgets.QHBoxLayout()
        root.addLayout(brand_box)
        self._btn_back = create_back_button(self, icon_dir=DEFAULT_ICON_DIR)
        self._btn_back.clicked.connect(lambda: go_to_main_menu(self.window()))
        brand_box.addWidget(self._btn_back)
        brand_box.addStretch(1)
        self._theme_toggle = ThemeToggle(self)
        self._theme_toggle.setChecked(is_dark_theme(QtWidgets.QApplication.instance()))
        self._theme_toggle.toggled.connect(self._on_theme_toggled)
        brand_box.addWidget(self._theme_toggle)

        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        root.addLayout(form)
        form.addWidget(QtWidgets.QLabel("Наименование профиля:"), 0, 0)
        self.ed_title = QtWidgets.QLineEdit()
        form.addWidget(self.ed_title, 0, 1)

        sec_src = Section("Источник данных", self)
        grp_src_l = sec_src.frame_l
        root.addWidget(sec_src)

        grp_src_l.addWidget(QtWidgets.QLabel("Excel файл:"), 0, 0)
        self.ed_sel_summary = QtWidgets.QLineEdit("Не выбрано")
        self.ed_sel_summary.setReadOnly(True)
        grp_src_l.addWidget(self.ed_sel_summary, 0, 1)
        self.btn_pick = QtWidgets.QPushButton("Выбрать...")
        grp_src_l.addWidget(self.btn_pick, 0, 2)

        sec_params = Section("Параметры из Excel", self)
        self._params_layout = sec_params.frame_l
        root.addWidget(sec_params)
        self._sec_params = sec_params

        self._params_widget = QtWidgets.QWidget()
        self._params_inner = QtWidgets.QVBoxLayout(self._params_widget)
        self._params_inner.setContentsMargins(0, 0, 0, 0)
        self._params_inner.setSpacing(4)
        self._params_inner.setAlignment(QtCore.Qt.AlignTop)
        self._params_layout.addWidget(self._params_widget, 0, 0)
        self._lbl_no_params = QtWidgets.QLabel("Ожидание excel")
        self._lbl_no_params.setStyleSheet("color: gray; font-style: italic;")
        self._params_inner.addWidget(self._lbl_no_params)

        self._params_help = QtWidgets.QLabel("Параметр для (FieldName):")
        self._params_help.setStyleSheet("color: gray;")
        self._params_help.hide()
        self._params_inner.addWidget(self._params_help)

        sec_settings = Section("Настройки", self)
        g = sec_settings.frame_l
        root.addWidget(sec_settings)
        
        self.cb_auto = QtWidgets.QCheckBox("Автонумерация (01_ 01.01_)")
        self.cb_auto.setChecked(False)
        self.cb_auto.setEnabled(False)
        self.cb_auto.setToolTip("Добавляет числовые префиксы к названиям групп и элементов, например 01_ и 01.01_.")
        g.addWidget(self.cb_auto, 0, 0)
        self.cb_filter = QtWidgets.QCheckBox("Фильтр")
        self.cb_filter.setChecked(False)
        self.cb_filter.setEnabled(False)
        self.cb_filter.setToolTip("Создаёт условия отбора параметров в экспортируемом профиле.")
        g.addWidget(self.cb_filter, 0, 1)
        self.cb_grouped = QtWidgets.QCheckBox("Распределить по группам")
        self.cb_grouped.setChecked(False)
        self.cb_grouped.setEnabled(False)
        self._cb_grouped_tooltip = "Если одинаковые параметры встречаются в разных группах, создаёт отдельные элементы в каждой группе, а не объединяет их в один."
        self._cb_grouped_tooltip_disabled = "Сначала включите «Фильтр» для активации этой опции."
        self.cb_grouped.setToolTip(self._cb_grouped_tooltip_disabled)
        g.addWidget(self.cb_grouped, 0, 2)
        
        self._setup_checkbox_disabled_style()
        
        self.cb_filter.toggled.connect(self._on_filter_toggled)

        btns = QtWidgets.QVBoxLayout()
        self.btn_generate = QtWidgets.QPushButton("Сгенерировать профиль")
        self.btn_generate.setMinimumSize(300, 48)
        btns.addWidget(self.btn_generate, alignment=QtCore.Qt.AlignHCenter)
        root.addLayout(btns)
        root.addStretch(1)

        self.btn_pick.clicked.connect(self._open_sheet_dialog)
        self.btn_generate.clicked.connect(self.generate_clicked)

    def _on_filter_toggled(self, checked: bool):
        self.cb_grouped.setEnabled(checked)
        if checked:
            self.cb_grouped.setToolTip(self._cb_grouped_tooltip)
        else:
            self.cb_grouped.setChecked(False)
            self.cb_grouped.setToolTip(self._cb_grouped_tooltip_disabled)

    def _setup_checkbox_disabled_style(self):
        app = QtWidgets.QApplication.instance()
        chk_off = resolve_icon_path("check", DEFAULT_ICON_DIR, app=app)
        chk_on = resolve_icon_path("select", DEFAULT_ICON_DIR, app=app)
        chk_mid = resolve_icon_path("poloska", DEFAULT_ICON_DIR, app=app)
        chk_off_dis = _ensure_gray_copy(chk_off, DEFAULT_ICON_DIR) if chk_off else ""
        chk_on_dis = _ensure_gray_copy(chk_on, DEFAULT_ICON_DIR) if chk_on else ""
        chk_mid_dis = _ensure_gray_copy(chk_mid, DEFAULT_ICON_DIR) if chk_mid else ""
        chk_off_dis_url = _qss_url(chk_off_dis) if chk_off_dis else ""
        chk_on_dis_url = _qss_url(chk_on_dis) if chk_on_dis else ""
        chk_mid_dis_url = _qss_url(chk_mid_dis) if chk_mid_dis else ""
        dis_qss = f"""
        QCheckBox:disabled {{ color: #8f8f8f; }}
        QCheckBox::indicator:unchecked:disabled {{ image: url('{chk_off_dis_url}'); }}
        QCheckBox::indicator:checked:disabled {{ image: url('{chk_on_dis_url}'); }}
        QCheckBox::indicator:indeterminate:disabled {{ image: url('{chk_mid_dis_url}'); }}
        """
        self.cb_auto.setStyleSheet(dis_qss)
        self.cb_filter.setStyleSheet(dis_qss)
        self.cb_grouped.setStyleSheet(dis_qss)

    def _enable_settings_checkboxes(self, enable: bool):
        self.cb_auto.setEnabled(enable)
        self.cb_filter.setEnabled(enable)
        if enable:
            self.cb_auto.setChecked(True)
            self.cb_filter.setChecked(True)
            self.cb_grouped.setEnabled(True)
            self.cb_grouped.setChecked(True)
            self.cb_grouped.setToolTip(self._cb_grouped_tooltip)
        else:
            self.cb_grouped.setEnabled(False)
            self.cb_grouped.setToolTip(self._cb_grouped_tooltip_disabled)

    @staticmethod
    def _normalize_col_name(name: str) -> str:
        s = (name or "").strip().lower()
        return s.replace("ё", "е")

    def _columns_for_params(self, raw_columns: List[str]) -> List[str]:
        if not raw_columns:
            return []
        cols = [c for c in raw_columns if c]
        if len(cols) < 2:
            return []

        result: List[str] = []
        for col in cols[1:]:
            if self._normalize_col_name(col).startswith("loi"):
                break
            result.append(col)
        return result

    def _detect_excel_column_roles(self, columns: List[str]) -> Dict[str, str]:
        norm_map = {c: self._normalize_col_name(c) for c in columns}

        def pick(*needles: str) -> str:
            for col, norm in norm_map.items():
                if all(n in norm for n in needles):
                    return col
            return ""

        role_map: Dict[str, str] = {}
        role_map["group"] = pick("элемент", "модел") or pick("раздел")
        role_map["category"] = pick("категор", "revit") or pick("категор")
        role_map["ifc"] = pick("ifc")
        role_map["classif"] = pick("код", "классифик") or pick("классифик")
        return {k: v for k, v in role_map.items() if v}

    def _detect_header_row_index(self, path: str, sheet: str) -> int:
        import pandas as pd

        preview = pd.read_excel(path, sheet_name=sheet, header=None, nrows=20, dtype=object)
        best_row = 0
        best_score = -1
        probes = (
            "элементы модели",
            "раздел",
            "категория",
            "revit",
            "ifc",
            "классифик",
            "код",
            "loi",
        )

        for r_idx in range(len(preview.index)):
            row_vals = [self._normalize_col_name(str(v)) for v in preview.iloc[r_idx].tolist() if str(v).strip()]
            if not row_vals:
                continue
            score = 0
            for cell in row_vals:
                if any(p in cell for p in probes):
                    score += 1
            if score > best_score:
                best_score = score
                best_row = r_idx

        return best_row if best_score >= 2 else 0

    def _default_field_for_column(self, column_name: str) -> str:
        role_to_default = {
            "category": FIELD_NAME_DEFAULT_CATEGORY,
            "classif": FIELD_NAME_DEFAULT_CLASSIF,
            "ifc": FIELD_NAME_DEFAULT_IFC,
        }
        for role, value in role_to_default.items():
            if self._excel_column_roles.get(role) == column_name:
                return value
        return ""

    def _clear_param_rows(self):
        for row in self._param_rows:
            try:
                row.setParent(None)
                row.deleteLater()
            except Exception:
                pass
        self._param_rows = []

    def _rebuild_param_rows(self):
        self._clear_param_rows()
        has_columns = bool(self._excel_param_columns)
        self._lbl_no_params.setVisible(not has_columns)
        self._params_help.setVisible(has_columns)

        if not has_columns:
            return

        for col in self._excel_param_columns:
            row = _ParamMappingRow(
                col,
                self._default_field_for_column(col),
                self._open_api_select_for_row,
                self._params_widget,
            )
            self._param_rows.append(row)
            self._params_inner.addWidget(row)

    def _param_field_map(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for row in self._param_rows:
            if not row.is_active():
                continue
            value = row.mapping_value()
            if value:
                result[row.column_name] = value
        return result

    def _refresh_for_theme(self):
        pass

    def _on_theme_toggled(self, dark: bool):
        app = QtWidgets.QApplication.instance()
        theme(app, dark, icon_dir=DEFAULT_ICON_DIR)
        self._refresh_for_theme()

    def _open_sheet_dialog(self):
        dlg = SheetPickerDialog(self, self._excel_path, self._selected_sheets)
        ok = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
        if ok:
            self._excel_path, self._selected_sheets = dlg.result()
            if self._selected_sheets:
                self.ed_sel_summary.setText(f"{Path(self._excel_path).name}: {', '.join(self._selected_sheets)}")
            else:
                self.ed_sel_summary.setText("Не выбрано")
            self._load_column_params()
            self._enable_settings_checkboxes(True)

    def _load_column_params(self):
        self._excel_param_columns = []
        self._excel_column_roles = {}
        self._header_rows_by_sheet = {}
        self._lbl_no_params.setText("Ожидание excel")
        self._rebuild_param_rows()

        if not self._excel_path or not self._selected_sheets:
            self._rebuild_param_rows()
            return

        try:
            import pandas as pd

            common_columns: Optional[List[str]] = None
            role_candidates: Dict[str, str] = {}
            for sheet in self._selected_sheets:
                header_row = self._detect_header_row_index(self._excel_path, sheet)
                self._header_rows_by_sheet[sheet] = header_row
                df = pd.read_excel(self._excel_path, sheet_name=sheet, header=header_row, nrows=0, dtype=object)
                all_columns = [str(c).strip() for c in df.columns if str(c).strip()]
                params_columns = self._columns_for_params(all_columns)
                roles = self._detect_excel_column_roles(params_columns)
                for role_name, role_col in roles.items():
                    if role_name not in role_candidates and role_col:
                        role_candidates[role_name] = role_col

                if common_columns is None:
                    common_columns = params_columns[:]
                else:
                    common_set = set(params_columns)
                    common_columns = [c for c in common_columns if c in common_set]

            columns = common_columns or []
            self._excel_param_columns = columns
            self._excel_column_roles = {
                role: col for role, col in role_candidates.items() if col in columns
            }

            if not columns:
                self._lbl_no_params.setText('Не найдены параметры (используются столбцы со 2-го до "LOI", не включая "LOI")')
            self._rebuild_param_rows()
        except Exception as e:
            self._lbl_no_params.setText(f"Ошибка загрузки: {e}")
            self._rebuild_param_rows()

    def get_selected_columns(self) -> List[str]:
        return self._excel_param_columns[:]

    def _pick_out_file(self, default_name: str) -> Optional[Path]:
        base_dir = Path.cwd()
        try:
            if self._excel_path:
                base_dir = Path(self._excel_path).parent
        except Exception:
            base_dir = Path.cwd()
        safe_name = (default_name or "Профиль").strip() or "Профиль"
        default_path = base_dir / f"{safe_name}.set"
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить профиль",
            str(default_path),
            "Set files (*.set);;XML files (*.xml);;All files (*.*)",
        )
        if not fn:
            return None
        path = Path(fn)
        if path.suffix.lower() != ".set":
            path = path.with_suffix(".set")
        return path

    def _open_api_select(self, apply_fn):
        dlg = ApiSelectDialog(
            self, _runtime_api_base_url(),
            api_get_projects, api_get_containers, api_get_parameters,
            on_import=lambda rows: apply_fn(rows[0].get("code", "")) if rows else None,
            state={}
        )
        if getattr(dlg, "exec", None):
            dlg.exec()
        else:
            dlg.exec_()

    def _open_api_select_for_row(self, row: _ParamMappingRow):
        if row is None:
            return
        self._open_api_select(lambda code: row.cmb_field.setCurrentText(code))

    def generate_clicked(self):
        try:
            if pd is None:
                raise RuntimeError("Нужен pandas: pip install pandas")
            
            title = (self.ed_title.text() or "Профиль").strip()
            
            if not self._excel_path or not self._selected_sheets:
                QtWidgets.QMessageBox.warning(self, "Внимание", "Выберите Excel файл и лист.")
                return

            auto_cols = self.get_selected_columns()
            if not auto_cols:
                QtWidgets.QMessageBox.warning(self, "Внимание", "Не найдены параметры в Excel (со 2-го столбца до LOI).")
                return

            out_path = self._pick_out_file(title)
            if not out_path:
                return
            out_path.parent.mkdir(parents=True, exist_ok=True)

            next_id = 10000
            auto_number = self.cb_auto.isChecked()
            build_filters = self.cb_filter.isChecked()
            grouped = self.cb_grouped.isChecked()
            param_field_map = self._param_field_map()

            group_col = self._excel_column_roles.get("group") or GROUP_COL_DEFAULT
            cat_col = self._excel_column_roles.get("category") or (auto_cols[1] if len(auto_cols) > 1 else CAT_COL_DEFAULT)
            ifc_col = self._excel_column_roles.get("ifc") or (auto_cols[2] if len(auto_cols) > 2 else IFC_COL_DEFAULT)
            classif_col = self._excel_column_roles.get("classif") or (auto_cols[3] if len(auto_cols) > 3 else CLASSIF_CODE_COL_DEFAULT)

            root = ET.Element("ExportProfilesCollection", {
                "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
            })
            profiles = ET.SubElement(root, "Profiles")
            base_el = ET.SubElement(profiles, "BaseExportProfile", {"xsi:type": "SetExportProfile"})
            ET.SubElement(base_el, "Id").text = "0"
            ET.SubElement(base_el, "Title").text = title
            profile_items = ET.SubElement(base_el, "ProfileItems")

            group_idx = 0
            for sheet in self._selected_sheets:
                header_row = self._header_rows_by_sheet.get(sheet)
                if header_row is None:
                    header_row = self._detect_header_row_index(self._excel_path, sheet)
                df = pd.read_excel(self._excel_path, sheet_name=sheet, header=header_row, dtype=object)
                next_id, group_idx = df_to_items_gui(
                    df, profile_items,
                    id_start=next_id,
                    profile_title=title,
                    group_column=group_col,
                    category_column=cat_col,
                    ifc_column=ifc_col,
                    auto_number=auto_number,
                    build_filters=build_filters,
                    field_name_category=FIELD_NAME_DEFAULT_CATEGORY,
                    field_name_ifc=FIELD_NAME_DEFAULT_IFC,
                    filter_mode="both",
                    classif_map=None,
                    classif_column=classif_col,
                    field_name_classif=FIELD_NAME_DEFAULT_CLASSIF,
                    group_idx_start=group_idx,
                    param_field_map=param_field_map,
                    active_param_columns=list(param_field_map.keys()),
                    grouped=grouped,
                )

            indent_xml(root)
            ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
            show_info_dialog(f"Файл сохранён:\n{out_path}", title="Успех", parent=self)
        except Exception as e:
            _msg_critical(self, "Ошибка", str(e))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Larix — Наборы")
        try:
            self.setWindowIcon(QtGui.QIcon(APP_ICON_PATH))
        except Exception:
            pass
        self.resize(900, 500)
        self._central = ContentWidget()
        self.setCentralWidget(self._central)

class _DarkTitlebarFilter(QtCore.QObject):
    def eventFilter(self, obj, e):
        try:
            if isinstance(obj, (QtWidgets.QDialog, QtWidgets.QMainWindow)) and e and hasattr(e, "type"):
                if e.type() in (QtCore.QEvent.Show, QtCore.QEvent.PaletteChange, QtCore.QEvent.StyleChange):
                    _apply_dark_titlebar_win(obj)
        except Exception:
            pass
        return False

# ----------------- Entry -----------------

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    try:
        app.setWindowIcon(QtGui.QIcon(APP_ICON_PATH))
    except Exception:
        pass
    dark = load_saved_theme(default=False)
    theme(app, dark, ICON_DIR)
    enable_theme_sync(app, ICON_DIR)
    _dtf = _DarkTitlebarFilter()
    app.installEventFilter(_dtf)
    w = MainWindow()
    w.show()
    apply_dark_titlebar(w, is_dark_theme(app))
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    else:
        sys.exit(app.exec_())

if __name__ == "__main__":
    run_gui()
