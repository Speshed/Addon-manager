from __future__ import annotations

import json
import os
import sys
import tempfile
import subprocess
import platform
import ctypes
from pathlib import Path
from typing import Any, Mapping

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Qt, Property as _QtProperty, QSize, QEasingCurve, QRectF
    from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPen, QBrush, QTransform, QLinearGradient, QRadialGradient
    from PySide6.QtWidgets import QApplication, QAbstractButton, QPushButton
    QT_API = "PySide6"
    Signal = QtCore.Signal
except Exception:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtCore import Qt, pyqtProperty as _QtProperty, QSize, QEasingCurve, QRectF
    from PyQt5.QtGui import QColor, QPixmap, QIcon, QPainter, QPen, QBrush, QTransform, QLinearGradient, QRadialGradient
    from PyQt5.QtWidgets import QApplication, QAbstractButton, QPushButton
    QT_API = "PyQt5"
    Signal = QtCore.pyqtSignal

_module_dir = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ICON_DIR = os.path.join(_module_dir, "icon")
_THEME_PREF_PATH = os.path.join(_module_dir, ".theme_pref.json")
_CACHE_SUBDIR = "nik_style_cache"

_back_to_menu_callback = None

def set_back_to_menu_callback(callback):
    global _back_to_menu_callback
    _back_to_menu_callback = callback

_larix_theme_path = os.path.join(os.path.dirname(_module_dir), "larix_theme")
if _larix_theme_path not in sys.path:
    sys.path.insert(0, os.path.dirname(_larix_theme_path))

try:
    from larix_theme import (
        apply_theme as _apply_theme,
        is_dark_theme as _is_dark_theme,
        load_saved_theme as _load_saved_theme_base,
        themed_icon,
        rsrc_path,
        THEME_LIGHT,
        THEME_DARK,
        RowHoverDelegate,
        install_viewport_row_highlighter,
        setup_hover_tracking,
    )
    _HAS_LARIX_THEME = True
except ImportError:
    _HAS_LARIX_THEME = False
    THEME_LIGHT = "light"
    RowHoverDelegate = None
    install_viewport_row_highlighter = None
    setup_hover_tracking = None
    THEME_DARK = "dark"


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


PALETTE = Palette()

_ICON_FILES: dict[str, list[str]] = {
    "logo": ["Manager-scaled.png", "logo.png"],
    "logo_white": ["Manager-scaled_white.png", "logo.png"],
    "app_icon": ["logo.ico", "logo.png", "Manager-scaled.png"],
    "sun": ["sun.png"],
    "moon": ["moon.png"],
    "back": ["back.png"],
    "arrow_left": ["arrow-left.png", "arrow_left.png"],
}


def register_icon_files(mapping: Mapping[str, Any]) -> None:
    for name, files in (mapping or {}).items():
        if not name:
            continue
        if isinstance(files, (list, tuple)):
            file_list = [str(x) for x in files if x]
        else:
            file_list = [str(files)] if files else []
        if not file_list:
            continue
        existing = _ICON_FILES.get(str(name), [])
        merged = []
        for f in file_list + existing:
            if f and f not in merged:
                merged.append(f)
        _ICON_FILES[str(name)] = merged


def _cache_dir(icon_dir: str | None) -> str:
    base = icon_dir if (icon_dir and os.path.isdir(icon_dir)) else DEFAULT_ICON_DIR
    try:
        p = os.path.join(base, _CACHE_SUBDIR)
        os.makedirs(p, exist_ok=True)
        return p
    except Exception:
        p = os.path.join(tempfile.gettempdir(), _CACHE_SUBDIR)
        os.makedirs(p, exist_ok=True)
        return p


def _safe_exists(path: str | None) -> bool:
    try:
        return bool(path) and os.path.exists(path)
    except Exception:
        return False


def load_saved_theme(default: bool = False) -> bool:
    if _HAS_LARIX_THEME:
        return _load_saved_theme_base(default)
    try:
        with open(_THEME_PREF_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("dark", default))
    except Exception:
        return bool(default)


def _save_theme_pref(dark: bool) -> None:
    try:
        with open(_THEME_PREF_PATH, "w", encoding="utf-8") as f:
            json.dump({"dark": bool(dark)}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def is_dark_theme(app: QApplication | None = None) -> bool:
    if _HAS_LARIX_THEME:
        return _is_dark_theme(app)
    try:
        if app is None:
            app = QApplication.instance()
        if app:
            val = app.property("nik_dark_theme")
            if val is not None:
                return bool(val)
    except Exception:
        pass
    return load_saved_theme(default=False)


def theme(
    app: QApplication,
    dark: bool,
    icon_dir: str | None = None,
    *,
    persist: bool = True,
) -> None:
    if _HAS_LARIX_THEME:
        _apply_theme(app, dark=dark, icon_dir=icon_dir or "", persist=persist)
    else:
        try:
            app.setProperty("nik_dark_theme", dark)
            app.setProperty("nik_theme", THEME_DARK if dark else THEME_LIGHT)
        except Exception:
            pass
        if persist:
            _save_theme_pref(dark)


def _resolve_icon_candidates(name: str, icon_dir: str) -> list[str]:
    if not name:
        return []
    candidates: list[str] = []
    for fname in _ICON_FILES.get(name, []):
        candidates.append(os.path.join(icon_dir, fname))
    candidates.append(os.path.join(icon_dir, f"{name}.png"))
    candidates.append(os.path.join(icon_dir, f"{name}.ico"))
    candidates.append(os.path.join(icon_dir, f"{name}.svg"))
    candidates.append(os.path.join(icon_dir, name))
    seen: set[str] = set()
    out: list[str] = []
    for p in candidates:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def resolve_icon_path(
    name: str,
    icon_dir: str | None = None,
    *,
    app: QApplication | None = None,
    tint_in_dark: bool = True,
) -> str:
    base_dir = icon_dir if (icon_dir and os.path.isdir(icon_dir)) else DEFAULT_ICON_DIR
    for p in _resolve_icon_candidates(str(name or ""), base_dir):
        if _safe_exists(p):
            if not tint_in_dark:
                return p
            dark = is_dark_theme(app)
            ext = os.path.splitext(p)[1].lower()
            if ext in {".ico", ".svg"}:
                return p
            if dark:
                return _ensure_white_copy(p, icon_dir=base_dir)
            return p
    return ""


def _tint_pixmap(pm: QPixmap, color: QColor) -> QPixmap:
    if pm is None or pm.isNull():
        return QPixmap()
    out = QPixmap(pm.size())
    out.fill(Qt.transparent)
    painter = QPainter(out)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.drawPixmap(0, 0, pm)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(out.rect(), QBrush(color))
    finally:
        painter.end()
    return out


def _cached_path(src_path: str, suffix: str, icon_dir: str | None) -> str:
    src = Path(src_path)
    cache = Path(_cache_dir(icon_dir))
    try:
        mtime = int(src.stat().st_mtime)
    except Exception:
        mtime = 0
    safe_base = f"{src.stem}.{mtime}{suffix}{src.suffix}"
    return str(cache / safe_base)


def _ensure_tinted_copy(src_path: str, *, color: QColor, suffix: str, icon_dir: str | None) -> str:
    if not _safe_exists(src_path):
        return ""
    dst = _cached_path(src_path, suffix, icon_dir)
    try:
        if _safe_exists(dst):
            return dst
        pm = QPixmap(src_path)
        if pm.isNull():
            return src_path
        tinted = _tint_pixmap(pm, color)
        if tinted.isNull():
            return src_path
        tinted.save(dst)
        return dst
    except Exception:
        return src_path


def _ensure_white_copy(src_path: str, *, icon_dir: str | None = None) -> str:
    return _ensure_tinted_copy(
        src_path,
        color=QColor("#FFFFFF"),
        suffix="__white",
        icon_dir=icon_dir,
    )


def _ensure_black_copy(src_path: str, *, icon_dir: str | None = None) -> str:
    return _ensure_tinted_copy(
        src_path,
        color=QColor("#000000"),
        suffix="__black",
        icon_dir=icon_dir,
    )


def _ensure_rotated_left(src_path: str, *, icon_dir: str | None = None) -> str:
    if not _safe_exists(src_path):
        return ""
    dst = _cached_path(src_path, "__rotleft", icon_dir)
    try:
        if _safe_exists(dst):
            return dst
        pm = QPixmap(src_path)
        if pm.isNull():
            return src_path
        tr = QTransform().rotate(-90)
        rotated = pm.transformed(tr, Qt.SmoothTransformation)
        rotated.save(dst)
        return dst
    except Exception:
        return src_path


def nik_icon(
    name: str,
    *,
    app: QApplication | None = None,
    icon_dir: str | None = None,
    tint_in_dark: bool = True,
) -> QIcon:
    path = resolve_icon_path(name, icon_dir, app=app, tint_in_dark=tint_in_dark)
    try:
        return QIcon(path) if path else QIcon()
    except Exception:
        return QIcon()


def apply_themed_icon(widget_or_action, name: str, icon_dir: str | None = None) -> None:
    app = QApplication.instance()
    ic = nik_icon(name, app=app, icon_dir=icon_dir)
    try:
        widget_or_action.setIcon(ic)
    except Exception:
        return


def apply_dark_titlebar(widget: QtWidgets.QWidget | None, dark: bool | None = None) -> None:
    try:
        if widget is None:
            return
        if sys.platform != "win32" or platform.system().lower() != "windows":
            return
        if dark is None:
            dark = is_dark_theme(QApplication.instance())
        if not hasattr(widget, "winId"):
            return
        hwnd = int(widget.winId())
        if hwnd == 0:
            return
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
        use_dark = ctypes.c_int(1 if dark else 0)
        dwm = ctypes.windll.dwmapi
        res = dwm.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(use_dark),
            ctypes.sizeof(use_dark),
        )
        if int(res) != 0:
            dwm.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD),
                ctypes.byref(use_dark),
                ctypes.sizeof(use_dark),
            )
    except Exception:
        pass


def create_back_button(
    parent: QtWidgets.QWidget | None = None,
    *,
    size: int = 28,
    icon_dir: str | None = None,
) -> QPushButton:
    btn = QPushButton(parent)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedSize(int(size), int(size))
    btn.setCheckable(False)
    btn.setFlat(True)
    btn.setStyleSheet(
        "QPushButton{border:0px; border-radius:10px; padding:0px;} QPushButton:hover{background: rgba(247,146,30,35);}"
    )
    try:
        app = QApplication.instance()
        ic = nik_icon("arrow_left", app=app, icon_dir=icon_dir, tint_in_dark=True)
        if ic.isNull():
            ic = nik_icon("back", app=app, icon_dir=icon_dir, tint_in_dark=True)
        btn.setIcon(ic)
        btn.setIconSize(QSize(int(size * 0.65), int(size * 0.65)))
    except Exception:
        pass
    return btn


def go_to_main_menu(widget: QtWidgets.QWidget | None = None) -> None:
    global _back_to_menu_callback
    if _back_to_menu_callback is not None:
        try:
            _back_to_menu_callback()
            return
        except Exception:
            pass
    try:
        if widget is None:
            return
        w = widget.window() if hasattr(widget, "window") else widget
        if hasattr(w, "close"):
            w.close()
    except Exception:
        pass


def enable_theme_sync(
    app: QApplication,
    icon_dir: str | None = None,
    *,
    interval_ms: int = 700,
) -> None:
    if app is None:
        return

    timer = QtCore.QTimer(app)
    timer.setInterval(int(interval_ms))
    timer.setSingleShot(False)

    state = {"mtime": None, "dark": None}

    def _tick():
        try:
            mtime = os.path.getmtime(_THEME_PREF_PATH)
        except Exception:
            mtime = None
        if mtime is None:
            return
        if state["mtime"] is None:
            state["mtime"] = mtime
            state["dark"] = is_dark_theme(app)
            return
        if mtime == state["mtime"]:
            return
        state["mtime"] = mtime
        dark = load_saved_theme(default=False)
        if dark == state["dark"]:
            return
        state["dark"] = dark
        theme(app, dark, icon_dir=icon_dir, persist=False)

    timer.timeout.connect(_tick)
    timer.start()
    try:
        app.setProperty("nik_theme_sync_timer", timer)
    except Exception:
        pass


class ThemeToggle(QAbstractButton):
    def __init__(self, parent: QtWidgets.QWidget | None = None, *, icon_dir: str | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._icon_dir = icon_dir
        self._thumb_x = 0.0
        self._hovered = False
        self._pressed = False
        self._icon_cache: dict[tuple[str, int, float], QPixmap] = {}

        self._sun_source = self._load_icon("sun.png")
        self._moon_source = self._load_icon("moon.png")

        self._anim = QtCore.QPropertyAnimation(self, b"thumbX", self)
        self._anim.setDuration(190)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self.setAttribute(Qt.WA_Hover, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(48, 24)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

    @staticmethod
    def _load_icon(file_name: str) -> QPixmap:
        path = resolve_icon_path(file_name.replace(".png", ""), DEFAULT_ICON_DIR, app=None, tint_in_dark=False)
        if path and os.path.exists(path):
            return QPixmap(path)
        return QPixmap()

    def _scaled_icon(self, key: str, source: QPixmap, size: int) -> QPixmap:
        if source.isNull() or size <= 0:
            return QPixmap()
        dpr = max(1.0, self.devicePixelRatioF())
        cache_key = (key, size, dpr)
        cached = self._icon_cache.get(cache_key)
        if cached is not None:
            return cached
        px = max(1, int(round(size * dpr)))
        scaled = source.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        self._icon_cache[cache_key] = scaled
        return scaled

    def sizeHint(self) -> QSize:
        return QSize(66, 28)

    def minimumSizeHint(self) -> QSize:
        return QSize(48, 24)

    def setChecked(self, checked: bool, animate: bool = True) -> None:
        checked = bool(checked)
        if animate and self.isChecked() != checked:
            start = self._thumb_x
            end = 1.0 if checked else 0.0
            self._anim.stop()
            self._anim.setStartValue(float(start))
            self._anim.setEndValue(float(end))
            super().setChecked(checked)
            self._anim.start()
        else:
            super().setChecked(checked)
            self._thumb_x = 1.0 if checked else 0.0
            self.update()

    def nextCheckState(self) -> None:
        self.setChecked(not self.isChecked(), animate=True)

    def getThumbX(self) -> float:
        return float(self._thumb_x)

    def setThumbX(self, v: float) -> None:
        self._thumb_x = max(0.0, min(1.0, float(v)))
        self.update()

    thumbX = _QtProperty(float, getThumbX, setThumbX)

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed and self.rect().contains(event.position().toPoint()):
                self.setChecked(not self.isChecked())
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.setChecked(not self.isChecked())
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = self.rect()
        track = QRectF(rect.adjusted(1, 1, -1, -1))
        dark = bool(self.isChecked())

        if dark:
            bg_start = QColor("#2c2c2e")
            bg_end = QColor("#1c1c1e")
        else:
            bg_start = QColor("#f5f5f6")
            bg_end = QColor("#e8e9eb")

        grad = QLinearGradient(track.topLeft(), track.bottomLeft())
        grad.setColorAt(0, bg_start)
        grad.setColorAt(1, bg_end)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        radius = track.height() * 0.5
        p.drawRoundedRect(track, radius, radius)

        icon_size = int(track.height() * 0.5)
        center_y = track.center().y()
        left_x = track.left() + 6
        right_x = track.right() - icon_size - 6

        sun_pm = QPixmap()
        moon_pm = QPixmap()

        if not self._sun_source.isNull():
            _sun = self._sun_source.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            sun_pm = self._tint_pixmap(_sun, QColor(0, 0, 0) if not dark else QColor(255, 255, 255))

        if not self._moon_source.isNull():
            _moon = self._moon_source.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            moon_pm = self._tint_pixmap(_moon, QColor(0, 0, 0) if not dark else QColor(255, 255, 255))

        p.save()
        p.setPen(Qt.NoPen)

        if not dark:
            hl_size = icon_size + 8
            p.setBrush(QColor("#F7921E"))
            p.drawEllipse(QRectF(right_x - (hl_size - icon_size) / 2, center_y - hl_size / 2, hl_size, hl_size))
        else:
            hl_size = icon_size + 8
            p.setBrush(QColor("#F7921E"))
            p.drawEllipse(QRectF(left_x - (hl_size - icon_size) / 2, center_y - hl_size / 2, hl_size, hl_size))
        p.restore()

        if not sun_pm.isNull():
            p.setOpacity(1.0 if not dark else 0.4)
            p.drawPixmap(int(right_x), int(center_y - sun_pm.height() / 2), sun_pm)
        if not moon_pm.isNull():
            p.setOpacity(0.4 if not dark else 1.0)
            p.drawPixmap(int(left_x), int(center_y - moon_pm.height() / 2), moon_pm)

        p.end()

    @staticmethod
    def _tint_pixmap(pm: QPixmap, color: QColor) -> QPixmap:
        if pm.isNull():
            return pm
        tinted = QPixmap(pm.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pm)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted


__all__ = [
    "Palette",
    "PALETTE",
    "register_icon_files",
    "load_saved_theme",
    "is_dark_theme",
    "theme",
    "resolve_icon_path",
    "nik_icon",
    "apply_themed_icon",
    "apply_dark_titlebar",
    "create_back_button",
    "go_to_main_menu",
    "enable_theme_sync",
    "ThemeToggle",
    "DEFAULT_ICON_DIR",
    "THEME_LIGHT",
    "THEME_DARK",
    "_ensure_white_copy",
    "_ensure_black_copy",
    "_ensure_rotated_left",
    "RowHoverDelegate",
    "install_viewport_row_highlighter",
]
