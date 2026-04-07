# -*- coding: utf-8 -*-
import sys
import configparser
import logging
import traceback
import os
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import pyodbc
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.theme_toggle import (
    ThemeToggle as SharedThemeToggle,
    is_dark_theme,
    theme as apply_theme,
    load_saved_theme,
    resolve_icon_path,
    apply_dark_titlebar,
    create_back_button,
    PALETTE,
    _ensure_white_copy,
)
from shared.dialogs import show_dialog, wire_dialog_button_box, wire_message_box_buttons

set_window_title_bar_dark = apply_dark_titlebar
ThemeToggle = SharedThemeToggle

from odbc import (
    ODBCConnectionManager,
    ODBCConfig,
    ODBCError,
    classify_odbc_error,
    check_odbc_environment,
    get_process_bitness,
    run_diagnostics,
    ODBCDriver,
)

from tls import (
    TLSManager,
    TLSConfig,
    TLSError,
    TLSDiagnostics,
    classify_ssl_error,
    get_tls_manager,
    is_production_environment,
)

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from PySide6.QtCore import Qt, QThread, Signal, QSize, QPropertyAnimation, Property, QRectF, QPointF, QEventLoop, QEasingCurve, QPoint, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QCheckBox,
    QProgressBar, QMessageBox, QFileDialog, QGroupBox, QToolButton,
    QStyleOptionButton, QStyle,
    QDialog, QDialogButtonBox, QRadioButton, QButtonGroup, QGraphicsDropShadowEffect, QSizePolicy
)
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests.adapters

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ICON_DIR = os.path.join(_BASE_DIR, "icon")



def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = _BASE_DIR
    return os.path.join(base, *parts)


def icon_file(*parts):
    path = os.path.join(ICON_DIR, *parts)
    if os.path.exists(path):
        return path
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = _BASE_DIR
    return os.path.join(base, "icon", *parts)


def _dialog_icon_path(icon_name: str, is_dark: bool) -> str:
    path = icon_file(f"{icon_name}.png")
    if path and os.path.exists(path) and is_dark:
        no_tint = {"warning"}
        if icon_name not in no_tint:
            return _ensure_white_copy(path, ICON_DIR)
    return path


def _trim_transparent_pixmap(pm: QPixmap) -> QPixmap:
    if pm.isNull():
        return pm
    img = pm.toImage()
    left = img.width()
    top = img.height()
    right = -1
    bottom = -1
    for y in range(img.height()):
        for x in range(img.width()):
            if img.pixelColor(x, y).alpha() > 0:
                if x < left:
                    left = x
                if y < top:
                    top = y
                if x > right:
                    right = x
                if y > bottom:
                    bottom = y
    if right < left or bottom < top:
        return pm
    return pm.copy(left, top, right - left + 1, bottom - top + 1)


def _square_icon_pixmap(pm: QPixmap, size: int) -> QPixmap:
    if pm.isNull():
        return pm
    fitted = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    canvas = QPixmap(size, size)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    x = (size - fitted.width()) // 2
    y = (size - fitted.height()) // 2
    painter.drawPixmap(x, y, fitted)
    painter.end()
    return canvas


def _make_pwd_action_icon(visible: bool, is_dark: bool) -> QIcon:
    icon_name = "free-icon-eye-2455724.png" if visible else "free-icon-hide-11238328.png"
    icon_path = icon_file(icon_name)
    if os.path.exists(icon_path):
        pm = QPixmap(icon_path)
        pm = _trim_transparent_pixmap(pm)
        pm = _square_icon_pixmap(pm, 18)
        if is_dark:
            painter = QPainter(pm)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pm.rect(), QColor(255, 255, 255))
            painter.end()
        return QIcon(pm)
    return QIcon()


class _InlinePasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._eye_btn = QToolButton(self)
        self._eye_btn.setCursor(Qt.PointingHandCursor)
        self._eye_btn.setStyleSheet("QToolButton { border: none; background: transparent; padding: 0px; margin: 0px; }")
        self._eye_btn.setFixedSize(20, 20)
        self.setTextMargins(0, 0, 28, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        x = self.width() - self._eye_btn.width() - 8
        y = (self.height() - self._eye_btn.height()) // 2
        self._eye_btn.move(x, y)

    def set_eye_clicked(self, callback):
        self._eye_btn.clicked.connect(callback)

    def set_eye_icon(self, icon: QIcon):
        self._eye_btn.setIcon(icon)
        self._eye_btn.setIconSize(QSize(18, 18))
        self._eye_btn.setVisible(not icon.isNull())

    def set_eye_tooltip(self, text: str):
        self._eye_btn.setToolTip(text)


def app_window_icon_path():
    preferred_paths = [
        icon_file("Viewer logo.png"),
        icon_file("Larix Viewer logo.png"),
        icon_file("logo.ico"),
    ]
    for path in preferred_paths:
        if os.path.exists(path):
            return path
    return ""


def mode_menu_logo_path(is_dark):
    preferred_paths = [
        icon_file("Larix Viewer_white.png") if is_dark else icon_file("Larix Viewer_black.png"),
        icon_file("larix viewer.png"),
    ]
    for path in preferred_paths:
        if os.path.exists(path):
            return path
    return ""


def _icon_file_for_qss(*parts):
    return icon_file(*parts).replace("\\", "/")


def _resolve_stylesheet_icon_paths(stylesheet):
    import re

    return re.sub(
        r'url\("icon/([^"]+)"\)',
        lambda match: f'url("{_icon_file_for_qss(*match.group(1).split("/"))}")',
        stylesheet,
    )

_thread_local = threading.local()
PROPERTY_COLUMN_MAPPING = {}
MAX_COLUMN_NAME_LENGTH = 128

TLS_MANAGER: Optional[TLSManager] = None
TLS_CONFIG_DICT: dict = {}

def get_session():
    if not hasattr(_thread_local, 'session'):
        global TLS_MANAGER
        if TLS_MANAGER is None:
            TLS_MANAGER = get_tls_manager(TLS_CONFIG_DICT if TLS_CONFIG_DICT else None)
        
        TLS_MANAGER.check_insecure_and_warn(log_info)
        session = TLS_MANAGER.create_session()
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        _thread_local.session = session
    return _thread_local.session


def normalize_column_name(property_path: str) -> str:
    import re
    normalized = re.sub(r'[^a-zA-Z0-9_]', '_', property_path)
    normalized = re.sub(r'_+', '_', normalized)
    normalized = normalized.strip('_')
    if not normalized:
        normalized = "col"
    if normalized[0].isdigit():
        normalized = "_" + normalized
    return normalized[:MAX_COLUMN_NAME_LENGTH]


def build_property_column_mapping(property_paths: list) -> dict:
    global PROPERTY_COLUMN_MAPPING
    mapping = {}
    used_names = set(PROPERTY_COLUMN_MAPPING.values()) if PROPERTY_COLUMN_MAPPING else set()
    
    for prop_path in property_paths:
        if prop_path in PROPERTY_COLUMN_MAPPING:
            mapping[prop_path] = PROPERTY_COLUMN_MAPPING[prop_path]
            continue
            
        base_name = normalize_column_name(prop_path)
        col_name = base_name
        counter = 1
        while col_name in used_names:
            suffix = f"_{counter}"
            max_base = MAX_COLUMN_NAME_LENGTH - len(suffix)
            col_name = base_name[:max_base] + suffix
            counter += 1
        mapping[prop_path] = col_name
        used_names.add(col_name)
    
    PROPERTY_COLUMN_MAPPING.update(mapping)
    return mapping


def log_timing(stage: str, start_time: float, count: int = 0):
    elapsed = time.time() - start_time
    if count > 0:
        rate = count / elapsed if elapsed > 0 else 0
        log_info(f"[TIMING] {stage}: {elapsed:.2f} сек, {count} записей, {rate:.0f} записей/сек")
    else:
        log_info(f"[TIMING] {stage}: {elapsed:.2f} сек")

CONFIG = {}
ODBC_MANAGER: Optional[ODBCConnectionManager] = None
df_all_projects = pd.DataFrame()
selected_project_ids = []
project_models = {}
sync_time_str = ""

CONFIG_FILE = "config.txt"
LOG_FILE = "bim_sync.log"

BATCH_SIZE = 500
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
SAVE_EMPTY_PROPERTIES = True


def is_empty_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return False
    if isinstance(value, str):
        return value.strip() == ""
    return False


class MultiSelectionManager:
    """
    Менеджер мультивыбора строк (не зависит от состояния чекбоксов).
    Поддерживает:
    - Shift + клик: выбор диапазона от последней активной строки до текущей
    - Ctrl/Cmd + клик: добавление/удаление строки из набора выбранных
    """
    
    def __init__(self):
        self._selected_indices = set()
        self._last_clicked_index = None
        self._all_items = []
    
    def set_items(self, items):
        self._all_items = list(items)
    
    def get_items(self):
        return self._all_items
    
    def clear_selection(self):
        self._selected_indices.clear()
        self._last_clicked_index = None
    
    def is_selected(self, index):
        return index in self._selected_indices
    
    def get_selected_indices(self):
        return set(self._selected_indices)
    
    def get_selected_count(self):
        return len(self._selected_indices)
    
    def has_selection(self):
        return len(self._selected_indices) > 0
    
    def handle_click(self, index, modifiers, item_count):
        ctrl_pressed = modifiers & Qt.KeyboardModifier.ControlModifier
        shift_pressed = modifiers & Qt.KeyboardModifier.ShiftModifier
        
        if ctrl_pressed and not shift_pressed:
            if index in self._selected_indices:
                self._selected_indices.discard(index)
            else:
                self._selected_indices.add(index)
            self._last_clicked_index = index
        elif shift_pressed and self._last_clicked_index is not None:
            start = min(self._last_clicked_index, index)
            end = max(self._last_clicked_index, index)
            self._selected_indices = set(range(start, end + 1))
        elif shift_pressed and self._last_clicked_index is None:
            self._selected_indices = {index}
            self._last_clicked_index = index
        else:
            self._selected_indices = {index}
            self._last_clicked_index = index


SELECTION_COLORS = {
    'hover_light': 'rgba(247, 146, 30, 0.10)',
    'hover_dark': 'rgba(247, 146, 30, 0.15)',
    'selected_light': 'rgba(247, 146, 30, 0.28)',
    'selected_dark': 'rgba(247, 146, 30, 0.22)',
    'pressed_light': 'rgba(247, 146, 30, 0.20)',
    'pressed_dark': 'rgba(247, 146, 30, 0.20)',
}


class SelectableRowWidget(QFrame):
    """
    Виджет-строка с поддержкой визуального выбора.
    - Hover подсвечивает строку оранжевым
    - Выбранная строка подсвечена оранжевым
    - Выбор строки НЕ меняет состояние чекбокса
    """
    row_clicked = Signal(object, object)
    
    def __init__(self, content_widget, index, is_dark=False, parent=None):
        super().__init__(parent)
        self._content_widget = content_widget
        self._index = index
        self._is_dark = is_dark
        self._is_selected = False
        self._is_hovered = False
        
        self._setup_ui()
        self._update_style()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        layout.addWidget(self._content_widget)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _update_style(self):
        if self._is_selected:
            bg = SELECTION_COLORS['selected_dark'] if self._is_dark else SELECTION_COLORS['selected_light']
        elif self._is_hovered:
            bg = SELECTION_COLORS['hover_dark'] if self._is_dark else SELECTION_COLORS['hover_light']
        else:
            bg = 'transparent'
        
        self.setStyleSheet(f"""
            SelectableRowWidget {{
                background: {bg};
                border-radius: 4px;
                border: none;
            }}
            SelectableRowWidget > QWidget {{
                background: transparent;
            }}
            SelectableRowWidget QCheckBox {{
                background: transparent;
            }}
            SelectableRowWidget QCheckBox::indicator {{
                background: transparent;
            }}
        """)
    
    def set_selected(self, selected):
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_style()
    
    def is_selected(self):
        return self._is_selected
    
    def set_theme(self, is_dark):
        self._is_dark = is_dark
        self._update_style()
    
    def get_index(self):
        return self._index
    
    def enterEvent(self, event):
        self._is_hovered = True
        self._update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_style()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child != self._content_widget and not self._is_checkbox_or_child(child):
                self.row_clicked.emit(self, event)
                event.accept()
                return
        super().mousePressEvent(event)
    
    def _is_checkbox_or_child(self, widget):
        if widget is None:
            return False
        if widget == self._content_widget:
            return True
        parent = widget.parent()
        while parent is not None and parent != self:
            if parent == self._content_widget:
                return True
            parent = parent.parent()
        return False


class IndicatorOnlyCheckBox(QCheckBox):
    """
    Чекбокс, который переключается только при клике по индикатору.
    Клик по тексту/области строки используется как клик по строке.
    """
    row_click_requested = Signal(object)

    def _indicator_rect(self):
        option = QStyleOptionButton()
        self.initStyleOption(option)
        return self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)

    def _is_indicator_click(self, pos):
        return self._indicator_rect().contains(pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._is_indicator_click(event.position().toPoint()):
            self.row_click_requested.emit(event.modifiers())
            event.accept()
            return
        super().mousePressEvent(event)


class HeaderSelectAllCheckBox(QCheckBox):
    """
    Чекбокс для заголовка таблицы с поддержкой tri-state.
    PartiallyChecked может быть установлен только программно.
    По клику пользователя переключается только между Unchecked <-> Checked.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTristate(True)
    
    def nextCheckState(self):
        if self.checkState() == Qt.CheckState.Checked:
            self.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.setCheckState(Qt.CheckState.Checked)


def init_log():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== Larix — Синхронизация Log ===\n")
        f.write(f"Запуск: {timestamp}\n")
        f.write("=" * 60 + "\n")
    
    diag = run_diagnostics()
    log_info(f"Process bitness: {diag.process_bitness}")
    log_info(f"Available ODBC drivers: {', '.join(diag.available_drivers) or 'none'}")
    if diag.selected_driver:
        log_info(f"Selected ODBC driver: {diag.selected_driver}")
    else:
        log_info("No SQL Server ODBC driver found - will show error on DB connect")


def log_info(message):
    """Логирование информации"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[INFO] {timestamp} | {message}\n")


def log_debug(message):
    """Логирование отладочной информации"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[DEBUG] {timestamp} | {message}\n")


def log_error(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[ОШИБКА] {timestamp}\n")
        f.write(f"{message}\n")
        f.write("-" * 40 + "\n")

THEME_LIGHT = "light"
THEME_DARK = "dark"

LIGHT_STYLESHEET = """
* {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
    color: #222;
    outline: none;
}

*:focus {
    outline: none;
}

QMainWindow {
    background: #FFFFFF;
}

QWidget {
    background: #FFFFFF;
}

QLabel {
    color: #222;
}

QLineEdit {
    background: #FFFFFF;
    border: 1px solid #dcdcdc;
    padding: 8px 12px;
    border-radius: 8px;
    color: #222;
}

QLineEdit:focus {
    border-color: #F7921E;
}

QPushButton {
    background: #FFFFFF;
    color: #222;
    border: 1px solid #dcdcdc;
    border-radius: 14px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background: rgba(247, 146, 30, 0.10);
    border-color: #FFA74B;
}

QPushButton:pressed {
    background: rgba(247, 146, 30, 0.20);
    border-color: #E07E12;
}

QPushButton:disabled {
    background: #f0f0f0;
    color: #9b9b9b;
    border-color: #e6e6e6;
}

QScrollArea {
    border: none;
    background: #FFFFFF;
}

QScrollBar:vertical {
    background: #FFFFFF;
    width: 12px;
    margin: 16px 0;
    border: none;
}

QScrollBar::handle:vertical {
    background: rgba(247, 146, 30, 0.12);
    min-height: 24px;
    border-radius: 6px;
    border: 1px solid #FFA74B;
}

QScrollBar::handle:vertical:hover {
    background: rgba(247, 146, 30, 0.20);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    subcontrol-origin: margin;
    border: none;
    border-radius: 0;
    image: none;
}

QScrollBar::add-line:vertical {
    subcontrol-position: bottom;
    height: 16px;
    background: #FFFFFF;
}

QScrollBar::sub-line:vertical {
    subcontrol-position: top;
    height: 16px;
    background: #FFFFFF;
}

QScrollBar::down-arrow:vertical {
    image: url("icon/arrow-down.png");
    width: 12px;
    height: 12px;
}

QScrollBar::up-arrow:vertical {
    image: url("icon/arrow-up.png");
    width: 12px;
    height: 12px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: #FFFFFF;
}

QScrollBar:horizontal {
    background: #FFFFFF;
    height: 12px;
    margin: 0 16px;
    border: none;
}

QScrollBar::handle:horizontal {
    background: rgba(247, 146, 30, 0.12);
    min-width: 24px;
    border-radius: 6px;
    border: 1px solid #FFA74B;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(247, 146, 30, 0.20);
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    subcontrol-origin: margin;
    border: none;
    border-radius: 0;
    image: none;
}

QScrollBar::add-line:horizontal {
    subcontrol-position: right;
    width: 16px;
    background: #FFFFFF;
}

QScrollBar::sub-line:horizontal {
    subcontrol-position: left;
    width: 16px;
    background: #FFFFFF;
}

QScrollBar::right-arrow:horizontal {
    image: url("icon/arrow-right.png");
    width: 12px;
    height: 12px;
}

QScrollBar::left-arrow:horizontal {
    image: url("icon/arrow-left.png");
    width: 12px;
    height: 12px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: #FFFFFF;
}

QScrollBar::sub-line:vertical {
    subcontrol-position: top;
    subcontrol-origin: margin;
    height: 16px;
    background: #FFFFFF;
    border: none;
}

QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
    background: rgba(247, 146, 30, 0.15);
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: #FFFFFF;
}

QCheckBox {
    color: #222;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QCheckBox::indicator:unchecked {
    image: url("icon/check.png");
}

QCheckBox::indicator:checked {
    image: url("icon/select.png");
}

QCheckBox::indicator:unchecked:hover {
    image: url("icon/check.png");
}

QCheckBox::indicator:indeterminate {
    image: url("icon/poloska.png");
}

QCheckBox::indicator:hover {
    background: transparent;
    border-radius: 0;
}

QRadioButton {
    color: #222;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 20px;
    height: 20px;
}

QRadioButton::indicator:unchecked {
    image: url("icon/circle2.png");
}

QRadioButton::indicator:checked {
    image: url("icon/circle dot.png");
}

QRadioButton::indicator:unchecked:hover {
    image: url("icon/circle2.png");
}

QRadioButton::indicator:hover {
    background: transparent;
    border-radius: 0;
}

QProgressBar {
    border: none;
    border-radius: 8px;
    text-align: center;
    background: rgba(0, 0, 0, 0.06);
    min-height: 6px;
    max-height: 6px;
    color: transparent;
    font-size: 0px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F7921E, stop:1 #FFA74B);
    border-radius: 8px;
}

QGroupBox {
    font-weight: 600;
    border: 1px solid #dcdcdc;
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 16px;
    background: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #222;
    background: #FFFFFF;
}

QToolTip {
    font-size: 9pt;
    padding: 4px 8px;
    border-radius: 4px;
}
"""

DARK_STYLESHEET = """
* {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
    color: #e0e0e0;
    outline: none;
}

*:focus {
    outline: none;
}

QMainWindow {
    background: #121212;
}

QWidget {
    background: #121212;
}

QLabel {
    color: #e0e0e0;
}

QLineEdit {
    background: #1e1e1e;
    border: 1px solid #404040;
    padding: 8px 12px;
    border-radius: 8px;
    color: #e0e0e0;
}

QLineEdit:focus {
    border-color: #F7921E;
}

QPushButton {
    background: #2a2a2a;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 14px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background: rgba(247, 146, 30, 0.20);
    border-color: #FFA74B;
    color: #e0e0e0;
}

QPushButton:pressed {
    background: rgba(247, 146, 30, 0.30);
    border-color: #E07E12;
    color: #e0e0e0;
}

QPushButton:disabled {
    background: #1e1e1e;
    color: #666;
    border-color: #333;
}

QScrollArea {
    border: none;
    background: #121212;
}

QScrollBar:vertical {
    background: #121212;
    width: 12px;
    margin: 16px 0;
    border: none;
}

QScrollBar::handle:vertical {
    background: rgba(247, 146, 30, 0.25);
    min-height: 24px;
    border-radius: 6px;
    border: 1px solid #FFA74B;
}

QScrollBar::handle:vertical:hover {
    background: rgba(247, 146, 30, 0.35);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    subcontrol-origin: margin;
    border: none;
    border-radius: 0;
    image: none;
}

QScrollBar::add-line:vertical {
    subcontrol-position: bottom;
    height: 16px;
    background: #121212;
}

QScrollBar::sub-line:vertical {
    subcontrol-position: top;
    height: 16px;
    background: #121212;
}

QScrollBar::down-arrow:vertical {
    image: url("icon/white/arrow-down.png");
    width: 12px;
    height: 12px;
}

QScrollBar::up-arrow:vertical {
    image: url("icon/white/arrow-up.png");
    width: 12px;
    height: 12px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: #121212;
}

QScrollBar:horizontal {
    background: #121212;
    height: 12px;
    margin: 0 16px;
    border: none;
}

QScrollBar::handle:horizontal {
    background: rgba(247, 146, 30, 0.25);
    min-width: 24px;
    border-radius: 6px;
    border: 1px solid #FFA74B;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(247, 146, 30, 0.35);
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    subcontrol-origin: margin;
    border: none;
    border-radius: 0;
    image: none;
}

QScrollBar::add-line:horizontal {
    subcontrol-position: right;
    width: 16px;
    background: #121212;
}

QScrollBar::sub-line:horizontal {
    subcontrol-position: left;
    width: 16px;
    background: #121212;
}

QScrollBar::right-arrow:horizontal {
    image: url("icon/white/arrow-right.png");
    width: 12px;
    height: 12px;
}

QScrollBar::left-arrow:horizontal {
    image: url("icon/white/arrow-left.png");
    width: 12px;
    height: 12px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: #121212;
}

QScrollBar::sub-line:vertical {
    subcontrol-position: top;
    subcontrol-origin: margin;
    height: 16px;
    background: #121212;
    border: none;
}

QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
    background: rgba(247, 146, 30, 0.20);
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: #121212;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QCheckBox::indicator:unchecked {
    image: url("icon/white/check.png");
}

QCheckBox::indicator:checked {
    image: url("icon/white/select.png");
}

QCheckBox::indicator:unchecked:hover {
    image: url("icon/white/check.png");
}

QCheckBox::indicator:indeterminate {
    image: url("icon/white/poloska.png");
}

QCheckBox::indicator:hover {
    background: transparent;
    border-radius: 0;
}

QRadioButton {
    color: #e0e0e0;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #888;
    border-radius: 10px;
    background: transparent;
}

QRadioButton::indicator:unchecked {
    border: 2px solid #888;
    background: transparent;
}

QRadioButton::indicator:checked {
    border: 2px solid #F7921E;
    background: #F7921E;
}

QRadioButton::indicator:unchecked:hover {
    border: 2px solid #bbb;
}

QRadioButton::indicator:hover {
    background: transparent;
}

QProgressBar {
    border: none;
    border-radius: 8px;
    text-align: center;
    background: rgba(255, 255, 255, 0.08);
    min-height: 6px;
    max-height: 6px;
    color: transparent;
    font-size: 0px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F7921E, stop:1 #FFA74B);
    border-radius: 8px;
}

QGroupBox {
    font-weight: 600;
    border: 1px solid #404040;
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 16px;
    background: #1e1e1e;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #e0e0e0;
    background: #1e1e1e;
}

QMessageBox {
    background: #1e1e1e;
}

QMessageBox QLabel {
    color: #e0e0e0;
    background: transparent;
}

QMessageBox QPushButton {
    background: #2a2a2a;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 14px;
    padding: 6px 12px;
    min-height: 24px;
    font-weight: 600;
}

QMessageBox QPushButton:hover {
    background: rgba(247, 146, 30, 0.15);
    border-color: #FFA74B;
}

QMessageBox QPushButton:pressed {
    background: rgba(247, 146, 30, 0.25);
    border-color: #E07E12;
}

QToolTip {
    font-size: 9pt;
    padding: 4px 8px;
    border-radius: 4px;
    background: #2a2a2a;
    color: #e0e0e0;
    border: 1px solid #404040;
}
"""

LIGHT_STYLESHEET = _resolve_stylesheet_icon_paths(LIGHT_STYLESHEET)
DARK_STYLESHEET = _resolve_stylesheet_icon_paths(DARK_STYLESHEET)


class AnimatedProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._display_value = 0.0
        self._indeterminate = False
        self._indeterminate_pos = 0.0
        self._shimmer_offset = 0.0
        self._is_dark_theme = False
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.timeout.connect(self._update_shimmer)
        self._shimmer_timer.setInterval(33)
        self._anim = QPropertyAnimation(self, b"displayValue", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumHeight(6)
        self.setMaximumHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _get_display_value(self):
        return self._display_value

    def _set_display_value(self, val):
        self._display_value = max(0.0, min(100.0, float(val)))
        self.update()

    displayValue = Property(float, _get_display_value, _set_display_value)

    def setValue(self, value):
        value = max(0, min(100, int(value)))
        if self._value == value:
            return
        self._value = value
        if self._indeterminate:
            return
        if self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self._display_value)
            self._anim.setEndValue(float(value))
            self._anim.start()
        else:
            self._display_value = float(value)
            self.update()

    def value(self):
        return self._value

    def setRange(self, minimum, maximum):
        pass

    def setIndeterminate(self, enabled):
        self._indeterminate = bool(enabled)
        if self._indeterminate:
            self._indeterminate_pos = -0.3
            self._start_timers()
        else:
            self._display_value = float(self._value)
        self.update()

    def isIndeterminate(self):
        return self._indeterminate

    def setTheme(self, is_dark):
        self._is_dark_theme = is_dark
        self.update()

    def _update_shimmer(self):
        if not self.isVisible():
            self._stop_timers()
            return
        self._shimmer_offset += 0.03
        if self._shimmer_offset > 2.0:
            self._shimmer_offset = -1.0
        if self._indeterminate:
            self._indeterminate_pos += 0.02
            if self._indeterminate_pos > 1.3:
                self._indeterminate_pos = -0.3
        self.update()

    def _start_timers(self):
        if not self._shimmer_timer.isActive():
            self._shimmer_timer.start()

    def _stop_timers(self):
        self._shimmer_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._start_timers()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_timers()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        if w <= 0 or h <= 0:
            p.end()
            return
        radius = min(3.0, h / 2.0)
        track_color = QColor(255, 255, 255, 20) if self._is_dark_theme else QColor(0, 0, 0, 15)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)
        if self._indeterminate:
            self._draw_indeterminate(p, w, h, radius)
        else:
            self._draw_determinate(p, w, h, radius)
        p.end()

    def _draw_indeterminate(self, p, w, h, radius):
        segment_w = w * 0.35
        x = self._indeterminate_pos * w
        fill_grad = QLinearGradient(0, 0, segment_w, 0)
        fill_grad.setColorAt(0, QColor("#F7921E"))
        fill_grad.setColorAt(1, QColor("#FFA74B"))
        p.setBrush(fill_grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(x, 0, segment_w, h), radius, radius)
        shimmer_w = segment_w * 0.4
        shimmer_x = x + (self._shimmer_offset % 1.0) * segment_w - shimmer_w / 2
        shimmer_grad = QLinearGradient(shimmer_x, 0, shimmer_x + shimmer_w, 0)
        shimmer_grad.setColorAt(0, QColor(255, 255, 255, 0))
        shimmer_grad.setColorAt(0.5, QColor(255, 255, 255, 80))
        shimmer_grad.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(shimmer_grad)
        p.setClipRect(QRectF(x, 0, segment_w, h))
        p.drawRect(QRectF(shimmer_x, 0, shimmer_w, h))
        p.setClipping(False)

    def _draw_determinate(self, p, w, h, radius):
        if self._display_value <= 0:
            return
        fill_w = max(0, (self._display_value / 100.0) * w)
        fill_grad = QLinearGradient(0, 0, fill_w, 0)
        fill_grad.setColorAt(0, QColor("#F7921E"))
        fill_grad.setColorAt(1, QColor("#FFA74B"))
        p.setBrush(fill_grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, fill_w, h), radius, radius)
        shimmer_w = max(1, w * 0.15)
        shimmer_x = self._shimmer_offset * fill_w
        shimmer_grad = QLinearGradient(shimmer_x, 0, shimmer_x + shimmer_w, 0)
        shimmer_grad.setColorAt(0, QColor(255, 255, 255, 0))
        shimmer_grad.setColorAt(0.5, QColor(255, 255, 255, 70))
        shimmer_grad.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(shimmer_grad)
        p.setClipRect(QRectF(0, 0, fill_w, h))
        p.drawRect(QRectF(shimmer_x, 0, shimmer_w, h))
        p.setClipping(False)


class RetryableError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


def validate_config(config):
    required = ["site", "server", "database"]
    missing = [k for k in required if not config.get(k, "").strip()]
    if missing:
        raise ValueError(f"Отсутствуют обязательные параметры: {', '.join(missing)}")
    if not config["site"].startswith(("http://", "https://")):
        raise ValueError("URL сайта должен начинаться с http:// или https://")


def get_connection_string(db_config, use_windows_auth=False, manager=None):
    if manager is None:
        manager = ODBC_MANAGER or ODBCConnectionManager()
    return manager.build_connection_string(
        server=db_config.get("server", ""),
        database=db_config.get("database", ""),
        username=db_config.get("username") if not use_windows_auth else None,
        password=db_config.get("password") if not use_windows_auth else None,
    )


def get_odbc_manager(config_dict=None):
    global ODBC_MANAGER
    if config_dict:
        odbc_config = ODBCConfig.from_dict(config_dict)
        ODBC_MANAGER = ODBCConnectionManager(odbc_config)
    elif ODBC_MANAGER is None:
        ODBC_MANAGER = ODBCConnectionManager()
    return ODBC_MANAGER


def test_db_connection(db_config, manager=None):
    try:
        if manager is None:
            manager = get_odbc_manager()
        success, message, driver = manager.test_connection(
            server=db_config.get("server", ""),
            database=db_config.get("database", ""),
            username=db_config.get("username"),
            password=db_config.get("password"),
        )
        if success and driver:
            log_info(f"ODBC test OK: driver={driver.value}, bitness={get_process_bitness()}")
        return success, message
    except ODBCError as e:
        log_error(f"ODBC error: {e.error_type} - {e.detail}")
        return False, e.get_user_message()
    except pyodbc.Error as e:
        odbc_error = classify_odbc_error(
            e, 
            db_config.get("server", ""), 
            db_config.get("database", "")
        )
        log_error(f"ODBC pyodbc error: {odbc_error.error_type}")
        return False, odbc_error.get_user_message()
    except Exception as e:
        log_error(f"DB connection error: {e}")
        return False, str(e)


def normalize_token(token):
    token = token.strip()
    if token.lower().startswith("bearer"):
        token = token[6:].lstrip()
    return token


def test_api_connection(site, token):
    token = normalize_token(token)
    try:
        url = f"{site}/api/projects/all"
        headers = {"Authorization": f"Bearer {token}"}
        
        session = get_session()
        response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 401 or response.status_code == 403:
            return False, f"Ошибка авторизации (код {response.status_code}). Проверьте токен."
        if response.status_code == 404:
            return False, f"Эндпоинт не найден (404). Проверьте URL сайта."
        if not response.ok:
            return False, f"Ошибка сервера: код {response.status_code}"
        return True, "Успешно"
    except requests.exceptions.SSLError as e:
        tls_error = classify_ssl_error(e, site)
        log_error(f"TLS/SSL ошибка при подключении к {site}: {tls_error.detail}")
        return False, tls_error.get_user_message()
    except requests.Timeout:
        return False, "Превышено время ожидания ответа от сервера"
    except requests.ConnectionError:
        return False, "Не удалось подключиться к серверу. Проверьте URL."
    except Exception as e:
        return False, str(e)


def get_all_projects(site, token):
    log_debug(f"get_all_projects: Начало запроса, site={site}")
    token = normalize_token(token)
    url = f"{site}/api/projects/all"
    headers = {"Authorization": f"Bearer {token}"}
    
    log_debug(f"get_all_projects: Отправка GET запроса на {url}")
    session = get_session()
    response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    log_debug(f"get_all_projects: Ответ получен, статус={response.status_code}")
    
    response.raise_for_status()
    
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        text = response.text[:500]
        if "<!DOCTYPE html>" in text or "<html" in text.lower():
            raise ValueError("Сервер вернул HTML-страницу. Проверьте URL сайта и токен авторизации.")
        raise ValueError(f"Сервер вернул не JSON. Ответ: {text[:200]}")
    
    text = response.text.strip()
    if not text:
        raise ValueError("Сервер вернул пустой ответ")
    
    try:
        data = response.json()
    except ValueError:
        raise ValueError(f"Не удалось разобрать JSON. Ответ сервера: {text[:200]}...")
    
    if not data:
        raise ValueError("API вернул пустой список проектов")
    
    log_info(f"get_all_projects: Получено {len(data)} проектов")
    df = pd.json_normalize(data)
    required_cols = ["id", "name", "description", "created_at", "updated_at"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    df = df[required_cols]
    df = df.rename(columns={"id": "idProject"})
    return df


def get_models_by_project_id(site, token, project_id):
    log_debug(f"get_models_by_project_id: Начало запроса для project_id={project_id}")
    token = normalize_token(token)
    url = f"{site}/api/jimc/projectid?projectId={project_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    log_debug(f"get_models_by_project_id: Отправка GET запроса на {url}")
    session = get_session()
    response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    log_debug(f"get_models_by_project_id: Ответ получен, статус={response.status_code}, project_id={project_id}")
    
    response.raise_for_status()
    data = response.json()
    if not data:
        log_debug(f"get_models_by_project_id: Нет моделей для project_id={project_id}")
        return pd.DataFrame()
    
    log_debug(f"get_models_by_project_id: Получено {len(data)} моделей для project_id={project_id}")
    df = pd.json_normalize(data)
    required_cols = ["id", "modelName", "fileHash", "status"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    df = df[required_cols]
    df["idProject"] = project_id
    return df


def get_elements_for_jimc_id(site, token, jimc_id):
    """Получение элементов модели через /api/element/jimcid"""
    log_debug(f"get_elements_for_jimc_id: Начало загрузки модели jimc_id={jimc_id}")
    token = normalize_token(token)
    all_elements = []
    page = 0
    page_size = 1000
    total_elements = 0
    
    session = get_session()
    while True:
        try:
            log_debug(f"get_elements_for_jimc_id: Запрос страницы {page}, jimc_id={jimc_id}")
            body = {"pagination": {"page": page, "pageSize": page_size}}
            
            url = f"{site}/api/element/jimcid"
            log_debug(f"get_elements_for_jimc_id: Отправка POST запроса на {url}")
            log_debug(f"get_elements_for_jimc_id: Таймаут={REQUEST_TIMEOUT} сек, jimc_id={jimc_id}")
            
            start_time = time.time()
            response = session.post(
                url,
                params={"jimcId": str(jimc_id)},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
                timeout=REQUEST_TIMEOUT
            )
            elapsed = time.time() - start_time
            
            log_debug(f"get_elements_for_jimc_id: Ответ получен за {elapsed:.2f} сек, статус={response.status_code}, jimc_id={jimc_id}, страница={page}")
            
            response.raise_for_status()
            json_data = response.json()
            data_list = json_data.get("data", [])
            
            log_debug(f"get_elements_for_jimc_id: Получено {len(data_list)} элементов, jimc_id={jimc_id}, страница={page}")
            
            if not data_list:
                if page == 0:
                    log_debug(f"get_elements_for_jimc_id: Первая страница пустая — модель jimc_id={jimc_id} не содержит элементов или не существует")
                else:
                    log_debug(f"get_elements_for_jimc_id: Данных больше нет, выход из цикла, jimc_id={jimc_id}")
                break
                
            df_page = pd.json_normalize(data_list)
            all_elements.append(df_page)
            total_elements += len(data_list)
            
            if len(data_list) < page_size:
                log_debug(f"get_elements_for_jimc_id: Последняя страница (получено < page_size), jimc_id={jimc_id}")
                break
            page += 1
            
        except requests.Timeout as e:
            log_error(f"get_elements_for_jimc_id: Таймаут запроса (>{REQUEST_TIMEOUT} сек), jimc_id={jimc_id}, страница={page}\n{e}")
            break
        except requests.ConnectionError as e:
            log_error(f"get_elements_for_jimc_id: Ошибка соединения, jimc_id={jimc_id}, страница={page}\n{e}")
            break
        except Exception as e:
            log_error(f"get_elements_for_jimc_id: Ошибка при загрузке элементов модели {jimc_id}, страница={page}\n{traceback.format_exc()}")
            break
    
    log_info(f"Загружено {total_elements} элементов для модели jimc_id={jimc_id} за {page + 1} страниц")
    
    if total_elements == 0:
        log_debug(f"get_elements_for_jimc_id: Модель jimc_id={jimc_id} не содержит элементов (пустой ответ API)")
    
    return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame()


def get_element_properties(site, token, jimc_id, eid_arr):
    """Получение свойств элементов через /api/element/jimcid-eidarr"""
    if not eid_arr:
        return []
    
    token = normalize_token(token)
    url = f"{site}/api/element/jimcid-eidarr"
    body = {"jimcId": jimc_id, "eidArr": eid_arr}
    
    try:
        session = get_session()
        response = session.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code in (401, 403):
            raise TokenExpiredError(f"Ошибка авторизации (код {response.status_code})")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_error(f"Ошибка получения свойств элементов: {e}")
        return []


def get_sample_properties(site, token, jimc_id):
    """Получение списка доступных параметров из одного элемента модели"""
    token = normalize_token(token)
    url = f"{site}/api/element/jimcid-eidarr"
    body = {"jimcId": jimc_id, "eidArr": [1]}
    
    try:
        session = get_session()
        response = session.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code in (401, 403):
            raise TokenExpiredError(f"Ошибка авторизации (код {response.status_code})")
        
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            pvs = data[0].get("pvs", [])
            return [pv.get("c", "") for pv in pvs if pv.get("c")]
        return []
    except Exception as e:
        log_error(f"Ошибка получения списка параметров для модели {jimc_id}: {e}")
        return []


def extract_property_value(pv_item):
    """Извлечение значения из элемента pvs"""
    ov = pv_item.get("ov", {})
    if ov:
        if "s" in ov:
            return ov["s"]
        elif "d" in ov:
            return ov["d"]
        elif "n" in ov:
            return str(ov["n"])
    return None


def get_connection_str(db_config, manager=None):
    if manager is None:
        manager = get_odbc_manager()
    use_windows_auth = not db_config.get("username") or not db_config.get("password")
    return manager.build_connection_string(
        server=db_config.get("server", ""),
        database=db_config.get("database", ""),
        username=db_config.get("username") if not use_windows_auth else None,
        password=db_config.get("password") if not use_windows_auth else None,
    )


INSERT_CHUNK_SIZE = 10000

def save_properties_to_sql(df_properties, schema="staging", db_config=None):
    if df_properties.empty:
        return
    
    sql_start = time.time()
    conn_str = get_connection_str(db_config)
    table_name = f"{schema}.ElementProperties"
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA {schema}')")
        conn.commit()
        
        create_sql = f"""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'{table_name}') AND type = 'U')
        CREATE TABLE {table_name} (
            [idElement] BIGINT,
            [idModel] BIGINT,
            [idProject] BIGINT,
            [propertyPath] NVARCHAR(MAX),
            [propertyValue] NVARCHAR(MAX),
            [last_updated] DATETIME2
        )
        """
        cursor.execute(create_sql)
        conn.commit()
        
        df_clean = df_properties.where(pd.notnull(df_properties), None)
        records = [tuple(row) for row in df_clean.values]
        placeholders = ", ".join(["?" for _ in df_properties.columns])
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        
        cursor.fast_executemany = True
        total_inserted = 0
        for i in range(0, len(records), INSERT_CHUNK_SIZE):
            chunk = records[i:i + INSERT_CHUNK_SIZE]
            cursor.executemany(insert_sql, chunk)
            total_inserted += len(chunk)
            log_debug(f"EAV insert: chunk {i//INSERT_CHUNK_SIZE + 1}, {len(chunk)} записей")
        conn.commit()
    
    log_timing("EAV INSERT (ElementProperties)", sql_start, total_inserted)


def save_properties_wide_to_sql(properties_list, property_paths, schema="staging", db_config=None, include_empty_rows=False, df_elements=None):
    if not properties_list and not (include_empty_rows and df_elements is not None and not df_elements.empty):
        return
    
    sql_start = time.time()
    col_mapping = build_property_column_mapping(property_paths)
    
    conn_str = get_connection_str(db_config)
    table_name = f"{schema}.ElementPropertiesWide"
    
    elements_dict = {}
    
    if include_empty_rows and df_elements is not None and not df_elements.empty:
        for _, row in df_elements.iterrows():
            key = (row.get("el_id"), row.get("idModel"), row.get("idProject"))
            if key not in elements_dict:
                elements_dict[key] = {
                    "idElement": row.get("el_id"),
                    "idModel": row.get("idModel"),
                    "idProject": row.get("idProject"),
                    "last_updated": row.get("last_updated")
                }
    
    for prop in properties_list:
        key = (prop["idElement"], prop["idModel"], prop["idProject"])
        if key not in elements_dict:
            elements_dict[key] = {
                "idElement": prop["idElement"],
                "idModel": prop["idModel"],
                "idProject": prop["idProject"],
                "last_updated": prop["last_updated"]
            }
        col_name = col_mapping.get(prop["propertyPath"])
        if col_name:
            elements_dict[key][col_name] = prop["propertyValue"]
    
    if not elements_dict:
        return
    
    all_columns = ["idElement", "idModel", "idProject", "last_updated"] + [col_mapping[p] for p in property_paths]
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA {schema}')")
        conn.commit()
        
        existing_cols = []
        try:
            cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = 'ElementPropertiesWide'")
            existing_cols = [row[0] for row in cursor.fetchall()]
        except Exception:
            pass
        
        if not existing_cols:
            cols_def = ["[idElement] BIGINT", "[idModel] BIGINT", "[idProject] BIGINT", "[last_updated] DATETIME2"]
            for prop_path in property_paths:
                col_name = col_mapping[prop_path]
                cols_def.append(f"[{col_name}] NVARCHAR(MAX)")
            create_sql = f"""
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'{table_name}') AND type = 'U')
            CREATE TABLE {table_name} ({', '.join(cols_def)})
            """
            cursor.execute(create_sql)
            conn.commit()
        else:
            for prop_path in property_paths:
                col_name = col_mapping[prop_path]
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE {table_name} ADD [{col_name}] NVARCHAR(MAX)")
                    conn.commit()
        
        records = []
        for elem_data in elements_dict.values():
            row = []
            for col in all_columns:
                row.append(elem_data.get(col))
            records.append(tuple(row))
        
        placeholders = ", ".join(["?" for _ in all_columns])
        col_names = ", ".join([f"[{c}]" for c in all_columns])
        insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        
        cursor.fast_executemany = True
        total_inserted = 0
        for i in range(0, len(records), INSERT_CHUNK_SIZE):
            chunk = records[i:i + INSERT_CHUNK_SIZE]
            cursor.executemany(insert_sql, chunk)
            total_inserted += len(chunk)
            log_debug(f"Wide insert: chunk {i//INSERT_CHUNK_SIZE + 1}, {len(chunk)} записей")
        conn.commit()
    
    log_timing(f"Wide INSERT (ElementPropertiesWide), {len(property_paths)} столбцов", sql_start, total_inserted)


def save_to_csv(df, output_path, filename):
    if df.empty:
        return 0
    filepath = os.path.join(output_path, filename)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    log_info(f"Сохранён файл: {filepath} ({len(df)} записей)")
    return len(df)


def save_to_parquet(df, output_path, filename):
    if df.empty:
        return 0
    filepath = os.path.join(output_path, filename)
    df.to_parquet(filepath, index=False, engine='pyarrow')
    log_info(f"Сохранён файл: {filepath} ({len(df)} записей)")
    return len(df)


def save_to_sqlite(df, conn, table_name):
    if df.empty:
        return 0
    import sqlite3
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    log_info(f"Сохранена таблица: {table_name} ({len(df)} записей)")
    return len(df)


def save_all_to_sqlite(df_projects, df_models, df_elements, df_properties, output_path, selected_properties=None, include_empty_rows=False):
    import sqlite3
    os.makedirs(output_path, exist_ok=True)
    db_path = os.path.join(output_path, "bim_data.db")
    conn = sqlite3.connect(db_path)
    
    total_records = 0
    total_records += save_to_sqlite(df_projects, conn, "projects")
    total_records += save_to_sqlite(df_models, conn, "models")
    total_records += save_to_sqlite(df_elements, conn, "elements")
    
    if not df_properties.empty:
        save_to_sqlite(df_properties, conn, "properties_eav")
        
        if selected_properties:
            col_mapping = build_property_column_mapping(selected_properties)
            
            elements_dict = {}
            
            if include_empty_rows and not df_elements.empty:
                for _, row in df_elements.iterrows():
                    key = (row.get("el_id"), row.get("idModel"), row.get("idProject"))
                    if key not in elements_dict:
                        elements_dict[key] = {
                            "idElement": row.get("el_id"),
                            "idModel": row.get("idModel"),
                            "idProject": row.get("idProject"),
                            "last_updated": row.get("last_updated")
                        }
            
            for _, row in df_properties.iterrows():
                key = (row["idElement"], row["idModel"], row["idProject"])
                if key not in elements_dict:
                    elements_dict[key] = {
                        "idElement": row["idElement"],
                        "idModel": row["idModel"],
                        "idProject": row["idProject"],
                        "last_updated": row["last_updated"]
                    }
                col_name = col_mapping.get(row["propertyPath"])
                if col_name:
                    elements_dict[key][col_name] = row["propertyValue"]
            
            if elements_dict:
                all_columns = ["idElement", "idModel", "idProject", "last_updated"] + \
                              [col_mapping[p] for p in selected_properties]
                df_wide = pd.DataFrame(list(elements_dict.values()))
                for col in all_columns:
                    if col not in df_wide.columns:
                        df_wide[col] = None
                df_wide = df_wide[all_columns]
                save_to_sqlite(df_wide, conn, "properties_wide")
                total_records += len(df_wide)
    
    conn.close()
    log_info(f"Создана база SQLite: {db_path} (всего {total_records} записей)")
    return total_records


def save_all_to_files(df_projects, df_models, df_elements, df_properties, output_path, selected_properties=None, format_type="csv", include_empty_rows=False):
    if format_type == "sqlite":
        return save_all_to_sqlite(df_projects, df_models, df_elements, df_properties, output_path, selected_properties, include_empty_rows)
    
    os.makedirs(output_path, exist_ok=True)
    
    ext = "parquet" if format_type == "parquet" else "csv"
    save_func = save_to_parquet if format_type == "parquet" else save_to_csv
    
    total_records = 0
    total_records += save_func(df_projects, output_path, f"projects.{ext}")
    total_records += save_func(df_models, output_path, f"models.{ext}")
    total_records += save_func(df_elements, output_path, f"elements.{ext}")
    
    if not df_properties.empty:
        save_func(df_properties, output_path, f"properties_eav.{ext}")
        
        if selected_properties:
            col_mapping = build_property_column_mapping(selected_properties)
            
            elements_dict = {}
            
            if include_empty_rows and not df_elements.empty:
                for _, row in df_elements.iterrows():
                    key = (row.get("el_id"), row.get("idModel"), row.get("idProject"))
                    if key not in elements_dict:
                        elements_dict[key] = {
                            "idElement": row.get("el_id"),
                            "idModel": row.get("idModel"),
                            "idProject": row.get("idProject"),
                            "last_updated": row.get("last_updated")
                        }
            
            for _, row in df_properties.iterrows():
                key = (row["idElement"], row["idModel"], row["idProject"])
                if key not in elements_dict:
                    elements_dict[key] = {
                        "idElement": row["idElement"],
                        "idModel": row["idModel"],
                        "idProject": row["idProject"],
                        "last_updated": row["last_updated"]
                    }
                col_name = col_mapping.get(row["propertyPath"])
                if col_name:
                    elements_dict[key][col_name] = row["propertyValue"]
            
            if elements_dict:
                all_columns = ["idElement", "idModel", "idProject", "last_updated"] + \
                              [col_mapping[p] for p in selected_properties]
                df_wide = pd.DataFrame(list(elements_dict.values()))
                for col in all_columns:
                    if col not in df_wide.columns:
                        df_wide[col] = None
                df_wide = df_wide[all_columns]
                save_func(df_wide, output_path, f"properties_wide.{ext}")
                total_records += len(df_wide)
    
    log_info(f"Всего записей в {ext.upper()}: {total_records}")
    return total_records


def get_elements_tree_table(site, token, jimc_id):
    token = normalize_token(token)
    all_elements = []
    page = 1
    page_size = 500
    total_elements = 0
    
    session = get_session()
    while True:
        try:
            log_debug(f"get_elements_tree_table: Запрос страницы {page}, jimc_id={jimc_id}")
            body = {"order": [], "pagination": {"page": page, "pageSize": page_size}}
            
            url = f"{site}/api/tree-table/elements"
            log_debug(f"get_elements_tree_table: Отправка POST запроса на {url}?jimcIdArr={jimc_id}")
            
            start_time = time.time()
            response = session.post(
                url,
                params={"jimcIdArr": str(jimc_id)},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
                timeout=REQUEST_TIMEOUT
            )
            elapsed = time.time() - start_time
            
            log_debug(f"get_elements_tree_table: Ответ получен за {elapsed:.2f} сек, статус={response.status_code}, jimc_id={jimc_id}, страница={page}")
            
            if response.status_code in (401, 403):
                log_error(f"get_elements_tree_table: Токен истёк или недействителен (статус {response.status_code}), jimc_id={jimc_id}")
                raise TokenExpiredError(f"Ошибка авторизации (код {response.status_code})")
            
            response.raise_for_status()
            json_data = response.json()
            data_list = json_data.get("data", [])
            
            log_debug(f"get_elements_tree_table: Получено {len(data_list)} элементов, jimc_id={jimc_id}, страница={page}")
            
            if not data_list:
                if page == 1:
                    log_debug(f"get_elements_tree_table: Первая страница пустая — модель jimc_id={jimc_id} не содержит элементов")
                else:
                    log_debug(f"get_elements_tree_table: Данных больше нет, выход из цикла, jimc_id={jimc_id}")
                break
                
            df_page = pd.json_normalize(data_list)
            all_elements.append(df_page)
            total_elements += len(data_list)
            
            if len(data_list) < page_size:
                log_debug(f"get_elements_tree_table: Последняя страница (получено {len(data_list)} < {page_size}), jimc_id={jimc_id}")
                break
            page += 1
            
        except TokenExpiredError:
            raise
        except requests.Timeout as e:
            log_error(f"get_elements_tree_table: Таймаут запроса (>{REQUEST_TIMEOUT} сек), jimc_id={jimc_id}, страница={page}\n{e}")
            break
        except requests.ConnectionError as e:
            log_error(f"get_elements_tree_table: Ошибка соединения, jimc_id={jimc_id}, страница={page}\n{e}")
            break
        except Exception as e:
            log_error(f"get_elements_tree_table: Ошибка при загрузке элементов модели {jimc_id}, страница={page}\n{traceback.format_exc()}")
            break
    
    log_info(f"get_elements_tree_table: Загружено {total_elements} элементов для модели jimc_id={jimc_id} за {page} страниц")
    
    if total_elements == 0:
        log_debug(f"get_elements_tree_table: Модель jimc_id={jimc_id} не содержит элементов")
    
    return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame()


def save_table_to_sql(df, table_name, schema="staging", key_columns=None, db_config=None):
    if df.empty:
        return
    conn_str = get_connection_str(db_config)
    full_name = f"{schema}.{table_name}"
    temp_name = f"{schema}.#temp_{table_name}_{int(datetime.now().timestamp())}"
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA {schema}')")
        conn.commit()

        cols_def = []
        for col in df.columns:
            if df[col].dtype in ['int64', 'Int64']:
                cols_def.append(f"[{col}] BIGINT")
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                cols_def.append(f"[{col}] DATETIME2")
            else:
                cols_def.append(f"[{col}] NVARCHAR(MAX)")
        create_sql = f"""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'{full_name}') AND type = 'U')
        CREATE TABLE {full_name} ({', '.join(cols_def)})
        """
        cursor.execute(create_sql)
        conn.commit()

        cursor.execute(f"SELECT TOP 0 * INTO {temp_name} FROM {full_name}")
        conn.commit()

        df_clean = df.where(pd.notnull(df), None)
        records = [tuple(row) for row in df_clean.values]
        placeholders = ", ".join(["?" for _ in df.columns])
        cursor.executemany(f"INSERT INTO {temp_name} VALUES ({placeholders})", records)
        conn.commit()

        if key_columns:
            key_columns = [f"[{k}]" for k in key_columns]
            update_cols = [f"T.[{col}] = S.[{col}]" for col in df.columns if f"[{col}]" not in key_columns]
            insert_cols = ", ".join([f"[{col}]" for col in df.columns])
            source_cols = ", ".join([f"S.[{col}]" for col in df.columns])
            merge_condition = " AND ".join([f"T.{k} = S.{k}" for k in key_columns])
            if update_cols:
                merge_sql = f"""
                MERGE {full_name} AS T
                USING {temp_name} AS S
                ON ({merge_condition})
                WHEN MATCHED THEN UPDATE SET {", ".join(update_cols)}
                WHEN NOT MATCHED BY TARGET THEN INSERT ({insert_cols}) VALUES ({source_cols});
                """
            else:
                merge_sql = f"""
                MERGE {full_name} AS T
                USING {temp_name} AS S
                ON ({merge_condition})
                WHEN NOT MATCHED BY TARGET THEN INSERT ({insert_cols}) VALUES ({source_cols});
                """
            cursor.execute(merge_sql)
            conn.commit()
        else:
            cursor.execute(f"INSERT INTO {full_name} SELECT * FROM {temp_name}")
            conn.commit()

        cursor.execute(f"DROP TABLE {temp_name}")
        conn.commit()


def replace_elements_by_model_ids(df_elements, model_ids, schema="staging", db_config=None):
    if not model_ids and df_elements.empty:
        return
    conn_str = get_connection_str(db_config)
    table_name = f"{schema}.Elements"
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        if not df_elements.empty:
            cols_def = []
            for col in df_elements.columns:
                if df_elements[col].dtype in ['int64', 'Int64']:
                    cols_def.append(f"[{col}] BIGINT")
                elif pd.api.types.is_datetime64_any_dtype(df_elements[col]):
                    cols_def.append(f"[{col}] DATETIME2")
                else:
                    cols_def.append(f"[{col}] NVARCHAR(MAX)")
            create_sql = f"""
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'{table_name}') AND type = 'U')
            CREATE TABLE {table_name} ({', '.join(cols_def)})
            """
            cursor.execute(create_sql)
            conn.commit()

        if model_ids:
            placeholders = ','.join('?' * len(model_ids))
            cursor.execute(f"DELETE FROM {table_name} WHERE [idModel] IN ({placeholders})", model_ids)
            conn.commit()

        if not df_elements.empty:
            df_clean = df_elements.where(pd.notnull(df_elements), None)
            if "idModel" in df_clean.columns:
                df_clean = df_clean.dropna(subset=["idModel"])
                df_clean["idModel"] = df_clean["idModel"].astype(int)
            records = [tuple(row) for row in df_clean.values]
            placeholders = ", ".join(["?" for _ in df_elements.columns])
            cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", records)
            conn.commit()


class SyncWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)
    token_expired = Signal()

    def __init__(self, config, projects_df, proj_models, selected_ids, selected_models_per_project=None, selected_properties=None, include_empty_rows=False):
        super().__init__()
        self.config = config
        self.projects_df = projects_df
        self.proj_models = proj_models
        self.selected_ids = selected_ids
        self.selected_models_per_project = selected_models_per_project or {}
        self.selected_properties = selected_properties or []
        self.include_empty_rows = include_empty_rows
        self._token_updated = threading.Event()
        self._token_lock = threading.Lock()
        self._token_dialog_active = False
        self._cancel_requested = False

    def set_new_token(self, token):
        self.config["token"] = token
        self._token_updated.set()

    def request_cancel(self):
        self._cancel_requested = True
        self._token_updated.set()

    def _wait_for_token_update(self):
        while not self._cancel_requested:
            if self._token_updated.wait(timeout=0.5):
                return True
        return False

    def _get_elements_with_retry(self, site, token, jimc_id, start_page=1):
        all_elements = []
        page = start_page
        page_size = 500
        max_retries = 3
        retry_delay = 3
        
        session = get_session()
        while True:
            if self._cancel_requested:
                return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, True
            
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    log_debug(f"Запрос страницы {page}, jimc_id={jimc_id}" + (f", попытка {retry_count + 1}" if retry_count > 0 else ""))
                    body = {"order": [], "pagination": {"page": page, "pageSize": page_size}}
                    
                    url = f"{site}/api/tree-table/elements"
                    current_token = normalize_token(self.config["token"])
                    
                    start_time = time.time()
                    response = session.post(
                        url,
                        params={"jimcIdArr": str(jimc_id)},
                        headers={"Authorization": f"Bearer {current_token}", "Content-Type": "application/json"},
                        json=body,
                        timeout=REQUEST_TIMEOUT
                    )
                    elapsed = time.time() - start_time
                    
                    log_debug(f"Ответ получен за {elapsed:.2f} сек, статус={response.status_code}, jimc_id={jimc_id}, страница={page}")
                    
                    if response.status_code in (401, 403):
                        log_info(f"Токен истёк (статус {response.status_code}), запрос нового токена...")
                        self._token_updated.clear()
                        self.token_expired.emit()
                        if not self._wait_for_token_update():
                            return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, True
                        
                        if self._cancel_requested:
                            return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, True
                        
                        log_info("Токен обновлён, продолжаем загрузку...")
                        continue
                    
                    response.raise_for_status()
                    json_data = response.json()
                    data_list = json_data.get("data", [])
                    
                    log_debug(f"Получено {len(data_list)} элементов, jimc_id={jimc_id}, страница={page}")
                    
                    if not data_list:
                        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
                        
                    df_page = pd.json_normalize(data_list)
                    all_elements.append(df_page)
                    success = True
                    
                    if len(data_list) < page_size:
                        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
                    page += 1
                    
                except (requests.Timeout, requests.ConnectionError) as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        log_error(f"Ошибка соединения (попытка {retry_count}/{max_retries}), jimc_id={jimc_id}, страница={page}\n{e}")
                        time.sleep(retry_delay)
                    else:
                        log_error(f"Превышено количество попыток, jimc_id={jimc_id}, страница={page}\n{e}")
                        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
                except Exception as e:
                    log_error(f"Ошибка при загрузке элементов модели {jimc_id}, страница={page}\n{traceback.format_exc()}")
                    return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
        
        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False

    def _get_properties_with_retry(self, site, jimc_id, eid_arr):
        """Получение свойств элементов с обработкой истёкшего токена"""
        if not eid_arr:
            return []
        
        max_retries = 5
        retry_delay = 3
        
        for attempt in range(max_retries):
            if self._cancel_requested:
                return []
            
            try:
                current_token = normalize_token(self.config["token"])
                url = f"{site}/api/element/jimcid-eidarr"
                body = {"jimcId": jimc_id, "eidArr": eid_arr}
                
                session = get_session()
                response = session.post(
                    url,
                    headers={"Authorization": f"Bearer {current_token}", "Content-Type": "application/json"},
                    json=body,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code in (401, 403):
                    with self._token_lock:
                        if self._token_dialog_active:
                            pass
                        else:
                            self._token_dialog_active = True
                            self._token_updated.clear()
                            self.token_expired.emit()
                    
                    got_token = self._wait_for_token_update()
                    
                    with self._token_lock:
                        self._token_dialog_active = False
                    
                    if not got_token or self._cancel_requested:
                        return []
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < max_retries - 1:
                    log_error(f"Ошибка соединения (попытка {attempt + 1}/{max_retries}), jimc_id={jimc_id}, элементов={len(eid_arr)}")
                    time.sleep(retry_delay)
                else:
                    log_error(f"Превышено количество попыток для свойств, jimc_id={jimc_id}")
                    return []
            except Exception as e:
                log_error(f"Ошибка при запросе свойств: {e}")
                return []
        
        return []

    def run(self):
        global sync_time_str
        start_time = time.time()
        try:
            log_info("=" * 60)
            log_info("НАЧАЛО СИНХРОНИЗАЦИИ")
            log_info("=" * 60)
            
            sync_time = datetime.now()
            sync_time_str = sync_time.strftime("%Y-%m-%d %H:%M:%S")
            log_info(f"Время начала: {sync_time_str}")
            log_info(f"Выбрано проектов: {len(self.selected_ids)}")

            all_projects = []
            all_models = []
            all_elements = []
            all_properties = []
            
            load_properties = bool(self.selected_properties)
            if load_properties:
                log_info(f"Выбрано параметров для выгрузки: {len(self.selected_properties)}")

            project_name_map = dict(zip(self.projects_df["idProject"], self.projects_df["name"]))
            total_projects = len(self.selected_ids)
            total_models_overall = 0

            self.progress.emit(5, "Подсчёт моделей...")
            log_debug("Подсчёт общего количества моделей...")

            for proj_id in self.selected_ids:
                all_models_list = self.proj_models.get(proj_id, [])
                selected_model_ids = self.selected_models_per_project.get(proj_id)
                
                if selected_model_ids is not None:
                    models = [m for m in all_models_list if m.get("idModel") in selected_model_ids]
                    cnt = len(models)
                    log_debug(f"Проект {proj_id}: выбрано {cnt} из {len(all_models_list)} моделей")
                else:
                    models = all_models_list
                    cnt = len(models)
                    
                total_models_overall += cnt
                proj_name = project_name_map.get(proj_id, "(неизвестный)")
                log_debug(f"Проект {proj_name} (ID={proj_id}): {cnt} моделей для обработки")

            log_info(f"Всего моделей для обработки: {total_models_overall}")

            if total_models_overall == 0:
                total_models_overall = 1

            processed_models = 0
            total_skipped_props = 0
            total_saved_props = 0
            for i, proj_id in enumerate(self.selected_ids, 1):
                proj_name = project_name_map.get(proj_id, "(неизвестный)")
                log_info(f"-- Проект {i}/{total_projects}: {proj_name} (ID={proj_id}) --")
                
                proj_row = self.projects_df[self.projects_df["idProject"] == proj_id].copy()
                if not proj_row.empty:
                    proj_row["last_updated"] = sync_time_str
                    all_projects.append(proj_row)

                all_models_list = self.proj_models.get(proj_id, [])
                selected_model_ids = self.selected_models_per_project.get(proj_id)
                
                if selected_model_ids is not None:
                    models = [m for m in all_models_list if m.get("idModel") in selected_model_ids]
                else:
                    models = all_models_list
                    
                if models:
                    df_models = pd.DataFrame(models)
                    df_models["last_updated"] = sync_time_str
                    all_models.append(df_models)

                    for j, mrow in enumerate(models, 1):
                        processed_models += 1
                        jimc_id = mrow["idModel"]
                        model_name = mrow.get("NameM", "(без названия)")
                        project_name = project_name_map.get(proj_id, "(неизвестный проект)")

                        progress_pct = 10 + (processed_models / total_models_overall) * 70
                        progress_msg = f"Проект {i}/{total_projects} — Модель {j}/{len(models)}"
                        self.progress.emit(int(progress_pct), progress_msg)
                        
                        log_debug(f"Обработка модели {processed_models}/{total_models_overall}: {model_name} (jimc_id={jimc_id})")
                        log_debug(f"Прогресс: {progress_pct:.1f}%")

                        elem_count = 0
                        props_count = 0
                        try:
                            if pd.notna(jimc_id) and jimc_id != "":
                                elem_start = time.time()
                                log_debug(f"Запрос элементов для модели jimc_id={jimc_id}")
                                df_elems, last_page, cancelled = self._get_elements_with_retry(
                                    self.config["site"], self.config["token"], jimc_id
                                )
                                
                                if cancelled:
                                    log_info("Синхронизация отменена пользователем")
                                    self.error.emit("Синхронизация отменена пользователем")
                                    return
                                
                                if df_elems.empty:
                                    log_info(f"МОДЕЛЬ БЕЗ ЭЛЕМЕНТОВ: {model_name} (jimc_id={jimc_id}) — API вернул пустой ответ")
                                else:
                                    df_elems["idProject"] = proj_id
                                    df_elems["idModel"] = jimc_id
                                    df_elems["last_updated"] = sync_time_str
                                    elem_cols = ["idProject", "idModel", "id", "eid", "nid", "nuid", "elementName", "last_updated"]
                                    for col in elem_cols:
                                        if col not in df_elems.columns:
                                            df_elems[col] = ""
                                    df_elems = df_elems[elem_cols].rename(columns={
                                        "id": "el_id", "eid": "el_eid", "nid": "el_nid",
                                        "nuid": "el_nuid", "elementName": "el_elementName"
                                    })
                                    elem_count = len(df_elems)
                                    all_elements.append(df_elems)
                                    log_timing(f"API elements {model_name}", elem_start, elem_count)
                                    
                                    if load_properties and elem_count > 0:
                                        props_start = time.time()
                                        progress_msg = f"Проект {i}/{total_projects} — Модель {j}/{len(models)} — свойства"
                                        self.progress.emit(int(progress_pct), progress_msg)
                                        log_debug(f"Загрузка свойств для {elem_count} элементов...")
                                        
                                        eid_list = df_elems["el_eid"].dropna().astype(int).tolist()
                                        element_ids = df_elems["el_id"].dropna().astype(int).tolist()
                                        eid_to_element_id = dict(zip(eid_list, element_ids))
                                        
                                        batch_size = 200
                                        max_workers = 8
                                        batches = [eid_list[bs:bs + batch_size] for bs in range(0, len(eid_list), batch_size)]
                                        total_batches = len(batches)
                                        log_debug(f"Параллельная загрузка: {total_batches} батчей, {len(eid_list)} элементов, {max_workers} потоков")
                                        
                                        completed_batches = 0
                                        props_lock = threading.Lock()
                                        skipped_props = 0
                                        
                                        def fetch_batch(batch_idx, batch_eids):
                                            if self._cancel_requested:
                                                return batch_idx, None, [], 0, 0
                                            try:
                                                props_data = self._get_properties_with_retry(
                                                    self.config["site"], jimc_id, batch_eids
                                                )
                                                results = []
                                                batch_skipped = 0
                                                batch_saved = 0
                                                if props_data:
                                                    for elem_data in props_data:
                                                        eid = elem_data.get("eid")
                                                        element_id = eid_to_element_id.get(eid)
                                                        if not element_id:
                                                            continue
                                                        
                                                        pvs = elem_data.get("pvs", [])
                                                        pvs_dict = {pv.get("c", ""): extract_property_value(pv) for pv in pvs}
                                                        
                                                        for prop_path in self.selected_properties:
                                                            prop_value = pvs_dict.get(prop_path, "")
                                                            
                                                            if not SAVE_EMPTY_PROPERTIES and is_empty_value(prop_value):
                                                                batch_skipped += 1
                                                                continue
                                                            
                                                            results.append({
                                                                "idElement": element_id,
                                                                "idModel": jimc_id,
                                                                "idProject": proj_id,
                                                                "propertyPath": prop_path,
                                                                "propertyValue": prop_value,
                                                                "last_updated": sync_time_str
                                                            })
                                                            batch_saved += 1
                                                return batch_idx, None, results, batch_skipped, batch_saved
                                            except Exception as e:
                                                return batch_idx, e, [], 0, 0
                                        
                                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                                            futures = {
                                                executor.submit(fetch_batch, idx, batch): idx 
                                                for idx, batch in enumerate(batches)
                                            }
                                            
                                            for future in as_completed(futures):
                                                if self._cancel_requested:
                                                    executor.shutdown(wait=False, cancel_futures=True)
                                                    log_info("Синхронизация отменена при загрузке свойств")
                                                    self.error.emit("Синхронизация отменена пользователем")
                                                    return
                                                
                                                batch_idx, error, results, batch_skipped, batch_saved = future.result()
                                                completed_batches += 1
                                                
                                                if error:
                                                    log_error(f"Ошибка в батче {batch_idx}: {error}")
                                                
                                                if results:
                                                    with props_lock:
                                                        all_properties.extend(results)
                                                        props_count += len(results)
                                                        skipped_props += batch_skipped
                                                
                                                if completed_batches % 5 == 0 or completed_batches == total_batches:
                                                    log_debug(f"Обработано батчей: {completed_batches}/{total_batches}, свойств: {props_count}")
                                        
                                        log_timing(f"API properties {model_name}", props_start, props_count)
                                        if not SAVE_EMPTY_PROPERTIES:
                                            log_info(f"Фильтрация пустых значений: сохранено {props_count}, пропущено {skipped_props}")
                                            total_skipped_props += skipped_props
                                        total_saved_props += props_count
                            else:
                                log_info(f"МОДЕЛЬ ПРОПУЩЕНА: {model_name} — jimc_id пустой или None")
                        except Exception as e:
                            log_error(f"Ошибка загрузки модели {jimc_id} ({model_name}):\n{traceback.format_exc()}")

                        log_info(f"{project_name} | {model_name} | {elem_count} элементов | {props_count} свойств")

            self.progress.emit(90, "Сохранение в базу данных...")
            log_info("Сохранение данных в базу данных...")
            
            df_projects = pd.concat(all_projects, ignore_index=True) if all_projects else pd.DataFrame()
            df_models = pd.concat(all_models, ignore_index=True) if all_models else pd.DataFrame()
            df_elements = pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame()
            df_properties = pd.DataFrame(all_properties) if all_properties else pd.DataFrame()

            log_info(f"Данные для сохранения: проектов={len(df_projects)}, моделей={len(df_models)}, элементов={len(df_elements)}, свойств={len(df_properties)}")

            model_ids = df_models["idModel"].dropna().astype(int).unique().tolist() if not df_models.empty else []

            t1 = time.time()
            log_debug("Сохранение таблицы Projects...")
            save_table_to_sql(df_projects, "Projects", key_columns=["idProject"], db_config=self.config)
            log_timing("SQL INSERT Projects", t1, len(df_projects))
            
            t2 = time.time()
            log_debug("Сохранение таблицы Models...")
            save_table_to_sql(df_models, "Models", key_columns=["idModel"], db_config=self.config)
            log_timing("SQL INSERT Models", t2, len(df_models))
            
            t3 = time.time()
            log_debug("Сохранение таблицы Elements...")
            replace_elements_by_model_ids(df_elements, model_ids, db_config=self.config)
            log_timing("SQL INSERT Elements", t3, len(df_elements))
            
            if not df_properties.empty:
                t4 = time.time()
                log_debug("Сохранение таблицы ElementProperties (EAV)...")
                save_properties_to_sql(df_properties, db_config=self.config)
                
                t5 = time.time()
                log_debug("Сохранение таблицы ElementPropertiesWide...")
                save_properties_wide_to_sql(all_properties, self.selected_properties, db_config=self.config, include_empty_rows=self.include_empty_rows, df_elements=df_elements)
                log_timing("SQL INSERT Wide Table", t5, len(df_properties))

            if not SAVE_EMPTY_PROPERTIES and total_saved_props > 0:
                log_info(f"ИТОГО свойств: сохранено {total_saved_props}, пропущено пустых {total_skipped_props}")
            elif total_saved_props > 0:
                log_info(f"ИТОГО свойств сохранено: {total_saved_props}")

            log_info("Синхронизация завершена успешно!")
            elapsed = time.time() - start_time
            self.progress.emit(100, "Завершено!")
            self.finished.emit({
                "projects": len(df_projects),
                "models": len(df_models),
                "elements": len(df_elements),
                "properties": len(df_properties),
                "failed": [],
                "elapsed": elapsed
            })
        except requests.Timeout:
            self.error.emit("Превышено время ожидания ответа от сервера.\nПроверьте подключение к интернету.")
        except requests.ConnectionError:
            self.error.emit("Не удалось подключиться к серверу.\nПроверьте подключение к интернету.")
        except requests.exceptions.SSLError as e:
            tls_error = classify_ssl_error(e, self.config.get("site", ""))
            log_error(f"TLS Error [{tls_error.error_type.value}]: {tls_error.detail}")
            self.error.emit(tls_error.get_user_message())
        except TLSError as e:
            log_error(f"TLS Error [{e.error_type.value}]: {e.detail}")
            self.error.emit(e.get_user_message())
        except ODBCError as e:
            log_error(f"ODBC Error [{e.error_type}]: {e.detail}")
            self.error.emit(e.get_user_message())
        except pyodbc.Error as e:
            odbc_err = classify_odbc_error(e)
            log_error(f"pyodbc Error: {str(e)}")
            self.error.emit(odbc_err.get_user_message())
        except ValueError as e:
            self.error.emit(str(e))
        except Exception as e:
            logging.error(f"Критическая ошибка синхронизации: {e}\n{traceback.format_exc()}")
            self.error.emit(f"Сбой синхронизации:\n{str(e)}\n\nПодробности в {LOG_FILE}")


class PropertiesSelectDialog(QDialog):
    """Диалог выбора параметров для выгрузки"""
    
    def __init__(self, available_properties, is_dark=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор параметров")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        self.selected_properties = []
        self.is_dark = is_dark
        self.property_checkboxes = {}
        self._property_rows = []
        self._property_to_index = {}
        self._selection_manager = MultiSelectionManager()
        self._is_handling_checkbox = False
        self._is_handling_master_checkbox = False
        
        self._build_ui(available_properties)
        
        if is_dark:
            self.setStyleSheet(DARK_STYLESHEET)
        else:
            self.setStyleSheet(LIGHT_STYLESHEET)
        set_window_title_bar_dark(self, is_dark)
    
    def _build_ui(self, properties):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Выберите параметры для выгрузки:")
        header.setStyleSheet("font-weight: 600; font-size: 12pt;")
        layout.addWidget(header)
        
        highlight_frame = QFrame()
        highlight_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #FF8C00;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        highlight_layout = QHBoxLayout(highlight_frame)
        highlight_layout.setContentsMargins(8, 4, 8, 4)
        
        self.include_empty_checkbox = QCheckBox("Выгрузить пустые элементы")
        self.include_empty_checkbox.setToolTip(
            "Если отмечено: в properties_wide попадут ВСЕ элементы, включая те,\n"
            "у которых нет ни одного из выбранных параметров (параметры будут пустыми).\n\n"
            "Если снято (по умолчанию): только элементы хотя бы с одним заполненным параметром."
        )
        self.include_empty_checkbox.setStyleSheet("font-weight: bold;")
        highlight_layout.addWidget(self.include_empty_checkbox)
        layout.addWidget(highlight_frame)
        
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Введите текст для поиска...")
        self.search_edit.textChanged.connect(self._filter_properties)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        header_row = QFrame()
        header_row.setStyleSheet("QFrame { background: transparent; border: none; }")
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(9, 2, 4, 2)
        header_layout.setSpacing(4)
        
        self.master_checkbox = HeaderSelectAllCheckBox()
        self.master_checkbox.setStyleSheet("background: transparent;")
        self.master_checkbox.stateChanged.connect(self._on_master_checkbox_changed)
        header_layout.addWidget(self.master_checkbox)
        
        header_label = QLabel("Наименование параметров")
        header_label.setStyleSheet("font-weight: 600; background: transparent;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        layout.addWidget(header_row)
        
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.properties_container = QWidget()
        self.properties_layout = QVBoxLayout(self.properties_container)
        self.properties_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.properties_layout.setSpacing(2)
        self.properties_layout.setContentsMargins(4, 4, 4, 4)
        
        for idx, prop in enumerate(sorted(properties)):
            cb = IndicatorOnlyCheckBox(prop)
            cb.setProperty("property_path", prop)
            cb.setStyleSheet("background: transparent;")
            cb.stateChanged.connect(lambda state, p=prop: self._on_checkbox_state_changed(p, state))
            cb.row_click_requested.connect(lambda modifiers, row_index=idx: self._on_property_row_area_clicked(row_index, modifiers))
            
            row_widget = SelectableRowWidget(cb, idx, is_dark=self.is_dark)
            row_widget.row_clicked.connect(self._on_row_clicked)
            self.properties_layout.addWidget(row_widget)
            
            self.property_checkboxes[prop] = cb
            self._property_to_index[prop] = idx
            self._property_rows.append(row_widget)
        
        self._selection_manager.set_items(self._property_rows)
        self._update_master_checkbox_state()
        
        scroll.setWidget(self.properties_container)
        layout.addWidget(scroll, 1)
        
        self.count_label = QLabel(f"Выбрано: 0 из {len(properties)}")
        layout.addWidget(self.count_label)
        
        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog_buttons.button(QDialogButtonBox.StandardButton.Ok).setText("ОК")
        dialog_buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        wire_dialog_button_box(dialog_buttons, self.accept, self.reject)
        layout.addWidget(dialog_buttons)
    
    def _on_row_clicked(self, row_widget, event):
        index = row_widget.get_index()
        modifiers = event.modifiers()
        
        self._selection_manager.handle_click(index, modifiers, len(self._property_rows))
        self._update_row_selections()
    
    def _on_property_row_area_clicked(self, index, modifiers):
        self._selection_manager.handle_click(index, modifiers, len(self._property_rows))
        self._update_row_selections()
    
    def _update_row_selections(self):
        for idx, row in enumerate(self._property_rows):
            row.set_selected(self._selection_manager.is_selected(idx))
    
    def _on_checkbox_state_changed(self, prop, state):
        if self._is_handling_checkbox:
            return
        
        clicked_index = self._property_to_index.get(prop)
        if clicked_index is None:
            self._update_count()
            return
        
        selected_indices = self._selection_manager.get_selected_indices()
        is_clicked_selected = clicked_index in selected_indices
        selected_count = len(selected_indices)
        
        if is_clicked_selected and selected_count > 1:
            self._is_handling_checkbox = True
            try:
                is_checked = (state == Qt.CheckState.Checked.value)
                for sel_idx in selected_indices:
                    if sel_idx < len(self._property_rows):
                        row_widget = self._property_rows[sel_idx]
                        cb = row_widget._content_widget
                        if cb.isEnabled():
                            cb.blockSignals(True)
                            cb.setChecked(is_checked)
                            cb.blockSignals(False)
            finally:
                self._is_handling_checkbox = False
        
        self._update_count()
    
    def _filter_properties(self, text):
        text = text.lower()
        for prop, cb in self.property_checkboxes.items():
            visible = text in prop.lower()
            idx = self._property_to_index.get(prop)
            if idx is not None and idx < len(self._property_rows):
                self._property_rows[idx].setVisible(visible)
        self._update_master_checkbox_state()
    
    def _on_master_checkbox_changed(self, state):
        if self._is_handling_master_checkbox:
            return
        
        if state == Qt.CheckState.PartiallyChecked.value:
            return
        
        is_checked = (state == Qt.CheckState.Checked.value)
        self._is_handling_master_checkbox = True
        try:
            for idx, row in enumerate(self._property_rows):
                if row.isVisible():
                    cb = row._content_widget
                    if cb.isEnabled():
                        cb.blockSignals(True)
                        cb.setChecked(is_checked)
                        cb.blockSignals(False)
        finally:
            self._is_handling_master_checkbox = False
        
        self._update_count()
    
    def _update_master_checkbox_state(self):
        if self._is_handling_master_checkbox:
            return
        
        visible_count = 0
        checked_count = 0
        for idx, row in enumerate(self._property_rows):
            if row.isVisible():
                visible_count += 1
                cb = row._content_widget
                if cb.isChecked():
                    checked_count += 1
        
        self._is_handling_master_checkbox = True
        try:
            if visible_count == 0 or checked_count == 0:
                self.master_checkbox.setCheckState(Qt.CheckState.Unchecked)
            elif checked_count == visible_count:
                self.master_checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                self.master_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        finally:
            self._is_handling_master_checkbox = False
    
    def _update_count(self):
        count = sum(1 for cb in self.property_checkboxes.values() if cb.isChecked())
        self.count_label.setText(f"Выбрано: {count} из {len(self.property_checkboxes)}")
        self._update_master_checkbox_state()
    
    def get_selected_properties(self):
        return [prop for prop, cb in self.property_checkboxes.items() if cb.isChecked()]
    
    def get_include_empty_rows(self):
        return self.include_empty_checkbox.isChecked()


class ProjectCard(QFrame):
    toggled = Signal()
    
    def __init__(self, project_id, project_name, models, is_dark=False, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.models = models
        self.model_checkboxes = {}
        self._model_id_to_index = {}
        self._model_rows = []
        self.is_expanded = True
        self.is_dark = is_dark
        self._selection_manager = MultiSelectionManager()
        self._is_handling_checkbox = False
        self._card_selected = False

        self._update_style()
        self._build_ui(project_name, models)

    def _update_style(self):
        if self._card_selected:
            bg = SELECTION_COLORS['selected_dark'] if self.is_dark else SELECTION_COLORS['selected_light']
            border = "#F7921E"
        else:
            bg = "transparent"
            border = "#404040" if self.is_dark else "#EAEAEA"
        self.setStyleSheet(f"""
            ProjectCard {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 12px;
                margin: 4px;
            }}
        """)
    
    def set_card_selected(self, selected):
        if self._card_selected != selected:
            self._card_selected = selected
            self._update_style()
    
    def is_card_selected(self):
        return self._card_selected

    def _build_ui(self, project_name, models):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet("QToolButton { background: transparent; border: none; padding: 0; }")
        self.toggle_btn.clicked.connect(self._toggle_expand)
        self._update_toggle_icon()
        header_layout.addWidget(self.toggle_btn)

        self.project_checkbox = QCheckBox(project_name)
        self.project_checkbox.setTristate(True)
        self.project_checkbox.setStyleSheet("font-weight: 600; font-size: 11pt;")
        self.project_checkbox.stateChanged.connect(self._on_project_toggled)
        header_layout.addWidget(self.project_checkbox)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        self.models_container = QWidget()
        models_layout = QVBoxLayout(self.models_container)
        models_layout.setContentsMargins(28, 0, 0, 4)
        models_layout.setSpacing(2)

        self._model_rows = []
        for idx, m in enumerate(self.models):
            model_id = m.get("idModel")
            model_name = m.get("NameM", "(без названия)")
            
            cb = IndicatorOnlyCheckBox(model_name)
            text_color = "#b0b0b0" if self.is_dark else "#555"
            cb.setStyleSheet(f"color: {text_color}; background: transparent;")
            cb.stateChanged.connect(lambda state, mid=model_id: self._on_model_toggled(mid, state))
            cb.row_click_requested.connect(lambda modifiers, row_index=idx: self._on_model_row_area_clicked(row_index, modifiers))
            
            row_widget = SelectableRowWidget(cb, idx, is_dark=self.is_dark)
            row_widget.row_clicked.connect(self._on_row_clicked)
            models_layout.addWidget(row_widget)
            
            self.model_checkboxes[model_id] = cb
            self._model_id_to_index[model_id] = idx
            self._model_rows.append(row_widget)
        
        self._selection_manager.set_items(self._model_rows)

        if not self.models:
            no_models = QLabel("Нет моделей")
            text_color = "#666" if self.is_dark else "#999"
            no_models.setStyleSheet(f"color: {text_color};")
            models_layout.addWidget(no_models)

        layout.addWidget(self.models_container)

    def _on_row_clicked(self, row_widget, event):
        self._on_model_row_area_clicked(row_widget.get_index(), event.modifiers())

    def _on_model_row_area_clicked(self, index, modifiers):
        self._selection_manager.handle_click(index, modifiers, len(self._model_rows))
        self._update_row_selections()
    
    def _update_row_selections(self):
        for idx, row in enumerate(self._model_rows):
            row.set_selected(self._selection_manager.is_selected(idx))

    def _update_toggle_icon(self):
        arrow_name = "arrow-down.png" if self.is_expanded else "arrow-right.png"
        if self.is_dark:
            icon_path = icon_file("white", arrow_name)
        else:
            icon_path = icon_file(arrow_name)
        if os.path.exists(icon_path):
            self.toggle_btn.setIcon(QIcon(icon_path))

    def _toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.models_container.setVisible(self.is_expanded)
        self._update_toggle_icon()
        self.toggled.emit()

    def set_theme(self, is_dark):
        self.is_dark = is_dark
        self._update_style()
        self._update_toggle_icon()
        text_color = "#b0b0b0" if is_dark else "#555"
        for row in self._model_rows:
            cb = row._content_widget
            cb.setStyleSheet(f"color: {text_color}; background: transparent;")
            row.set_theme(is_dark)
        self._update_project_checkbox_state()

    def _update_project_checkbox_state(self):
        total = len(self.model_checkboxes)
        if total == 0:
            self.project_checkbox.blockSignals(True)
            self.project_checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.project_checkbox.blockSignals(False)
            return
        
        checked = sum(1 for cb in self.model_checkboxes.values() if cb.isChecked())
        
        self.project_checkbox.blockSignals(True)
        if checked == 0:
            self.project_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked == total:
            self.project_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self.project_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.project_checkbox.blockSignals(False)

    def _on_project_toggled(self, state):
        has_checked = any(cb.isChecked() for cb in self.model_checkboxes.values())
        should_check = not has_checked
        
        for cb in self.model_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(should_check)
            cb.blockSignals(False)
        
        self._update_project_checkbox_state()
        self.toggled.emit()

    def _on_model_toggled(self, model_id, state):
        if self._is_handling_checkbox:
            return
        
        clicked_index = self._model_id_to_index.get(model_id)
        if clicked_index is None:
            self._update_project_checkbox_state()
            self.toggled.emit()
            return
        
        selected_indices = self._selection_manager.get_selected_indices()
        is_clicked_selected = clicked_index in selected_indices
        selected_count = len(selected_indices)
        
        if is_clicked_selected and selected_count > 1:
            self._is_handling_checkbox = True
            try:
                is_checked = (state == Qt.CheckState.Checked.value)
                for sel_idx in selected_indices:
                    if sel_idx < len(self._model_rows):
                        row_widget = self._model_rows[sel_idx]
                        cb = row_widget._content_widget
                        if cb.isEnabled():
                            cb.blockSignals(True)
                            cb.setChecked(is_checked)
                            cb.blockSignals(False)
            finally:
                self._is_handling_checkbox = False
        
        self._update_project_checkbox_state()
        self.toggled.emit()

    def is_selected(self):
        if self.project_checkbox.isChecked():
            return True
        return any(cb.isChecked() for cb in self.model_checkboxes.values())

    def get_selected_model_ids(self):
        return [mid for mid, cb in self.model_checkboxes.items() if cb.isChecked()]

    def select_all(self, checked):
        for cb in self.model_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._update_project_checkbox_state()


class DBAuthDialog(QDialog):
    def __init__(self, parent=None, site="", server="", database="", username="", password="", is_dark=False):
        super().__init__(parent)
        self.setWindowTitle("Авторизация в БД")
        self.setMinimumWidth(450)
        self.setModal(True)
        self._is_dark = is_dark
        
        if is_dark:
            self.setStyleSheet(DARK_STYLESHEET)
        set_window_title_bar_dark(self, is_dark)
        
        icon_path = app_window_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        site_row = QFrame()
        site_layout = QHBoxLayout(site_row)
        site_layout.setContentsMargins(0, 0, 0, 0)
        site_layout.setSpacing(10)
        site_layout.addWidget(QLabel("Сайт:"))
        self.site_edit = QLineEdit()
        self.site_edit.setPlaceholderText("https://viewer.larix.ru/")
        self.site_edit.setText(site if site else "https://viewer.larix.ru/")
        site_layout.addWidget(self.site_edit, 1)
        layout.addWidget(site_row)
        
        server_row = QFrame()
        server_layout = QHBoxLayout(server_row)
        server_layout.setContentsMargins(0, 0, 0, 0)
        server_layout.setSpacing(10)
        server_layout.addWidget(QLabel("Сервер:"))
        self.server_edit = QLineEdit()
        self.server_edit.setPlaceholderText(".\\SQLEXPRESS")
        self.server_edit.setText(server)
        server_layout.addWidget(self.server_edit, 1)
        layout.addWidget(server_row)
        
        db_row = QFrame()
        db_layout = QHBoxLayout(db_row)
        db_layout.setContentsMargins(0, 0, 0, 0)
        db_layout.setSpacing(10)
        db_layout.addWidget(QLabel("База данных:"))
        self.database_edit = QLineEdit()
        self.database_edit.setPlaceholderText("viewer_old")
        self.database_edit.setText(database)
        db_layout.addWidget(self.database_edit, 1)
        layout.addWidget(db_row)
        
        user_row = QFrame()
        user_layout = QHBoxLayout(user_row)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(10)
        user_layout.addWidget(QLabel("Имя пользователя:"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("login_ibim (пусто = Windows Auth)")
        self.username_edit.setText(username)
        user_layout.addWidget(self.username_edit, 1)
        layout.addWidget(user_row)
        
        pass_row = QFrame()
        pass_layout = QHBoxLayout(pass_row)
        pass_layout.setContentsMargins(0, 0, 0, 0)
        pass_layout.setSpacing(10)
        pass_layout.addWidget(QLabel("Пароль:"))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("passw_ibim")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setText(password)
        pass_layout.addWidget(self.password_edit, 1)
        self._password_visible = False
        self._pwd_btn = QToolButton()
        self._pwd_btn.setCursor(Qt.PointingHandCursor)
        self._pwd_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self._pwd_btn.setFixedSize(28, 28)
        self._pwd_btn.clicked.connect(self._toggle_password_visibility)
        pass_layout.addWidget(self._pwd_btn)
        self._update_password_icon()
        layout.addWidget(pass_row)
        
        buttons_row = QFrame()
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)
        btn_import = QPushButton("Импорт")
        btn_import.clicked.connect(self._import_config)
        buttons_layout.addWidget(btn_import)
        btn_template = QPushButton("Скачать конфиг")
        btn_template.clicked.connect(self._save_template_from_fields)
        buttons_layout.addWidget(btn_template)
        btn_example = QPushButton("Скачать пример")
        btn_example.clicked.connect(self._download_example)
        buttons_layout.addWidget(btn_example)
        layout.addWidget(buttons_row)
        
        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        wire_dialog_button_box(dialog_buttons, self.accept, self.reject)
        layout.addWidget(dialog_buttons)
    
    def _toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._update_password_icon()
    
    def _update_password_icon(self):
        icon_name = "free-icon-eye-2455724.png" if self._password_visible else "free-icon-hide-11238328.png"
        icon_path = icon_file(icon_name)
        if os.path.exists(icon_path):
            pm = QPixmap(icon_path)
            pm = pm.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if self._is_dark:
                painter = QPainter(pm)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(pm.rect(), QColor(255, 255, 255))
                painter.end()
            self._pwd_btn.setIcon(QIcon(pm))
            self._pwd_btn.setIconSize(QSize(22, 22))
    
    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите config.txt", "", "Text files (*.txt);;All files (*)"
        )
        if not path:
            return
        try:
            config = configparser.ConfigParser()
            config.read(path, encoding="utf-8")
            self.site_edit.setText(config.get("API", "site", fallback=""))
            self.server_edit.setText(config.get("DATABASE", "server", fallback=""))
            self.database_edit.setText(config.get("DATABASE", "database", fallback=""))
            self.username_edit.setText(config.get("DATABASE", "username", fallback=""))
            self.password_edit.setText(config.get("DATABASE", "password", fallback=""))
            msg = QMessageBox(self)
            icon_path = _dialog_icon_path("alert", self._is_dark)
            if icon_path and os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                msg.setIconPixmap(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Импорт")
            msg.setText(f"Конфигурация загружена из:\n{path}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if self._is_dark:
                msg.setStyleSheet(DARK_STYLESHEET)
            set_window_title_bar_dark(msg, self._is_dark)
            wire_message_box_buttons(msg)
            show_dialog(msg, modal=True)
        except Exception as e:
            msg = QMessageBox(self)
            icon_path = _dialog_icon_path("error", self._is_dark)
            if icon_path and os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                msg.setIconPixmap(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось загрузить файл:\n{e}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if self._is_dark:
                msg.setStyleSheet(DARK_STYLESHEET)
            set_window_title_bar_dark(msg, self._is_dark)
            wire_message_box_buttons(msg)
            show_dialog(msg, modal=True)
    
    def _save_template_from_fields(self):
        site = self.site_edit.text().strip()
        server = self.server_edit.text().strip()
        database = self.database_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not site or not server or not database:
            msg = QMessageBox(self)
            icon_path = _dialog_icon_path("warning", self._is_dark)
            if icon_path and os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                msg.setIconPixmap(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Внимание")
            msg.setText("Заполните поля: Сайт, Сервер и База данных.")
            msg.setInformativeText("Если хотите скачать заполненный пример, нажмите кнопку «Скачать пример».")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if self._is_dark:
                msg.setStyleSheet(DARK_STYLESHEET)
            set_window_title_bar_dark(msg, self._is_dark)
            wire_message_box_buttons(msg)
            show_dialog(msg, modal=True)
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить конфигурацию", "config.txt", "Text files (*.txt)"
        )
        if not file_path:
            return
        
        content = f"""[API]
site = {site}

[DATABASE]
server = {server}
database = {database}
username = {username}
password = {password}

[ODBC]
encrypt = yes
trust_server_certificate = yes
connection_timeout = 30

[TLS]
verify = true
ca_bundle_path = 
allow_insecure_dev = false
request_timeout = 30
"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            msg = QMessageBox(self)
            icon_path = _dialog_icon_path("alert", self._is_dark)
            if icon_path and os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                msg.setIconPixmap(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Успех")
            msg.setText(f"Конфигурация сохранена в:\n{file_path}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if self._is_dark:
                msg.setStyleSheet(DARK_STYLESHEET)
            set_window_title_bar_dark(msg, self._is_dark)
            wire_message_box_buttons(msg)
            show_dialog(msg, modal=True)
        except Exception as e:
            msg = QMessageBox(self)
            icon_path = _dialog_icon_path("error", self._is_dark)
            if icon_path and os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                msg.setIconPixmap(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось сохранить файл:\n{e}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if self._is_dark:
                msg.setStyleSheet(DARK_STYLESHEET)
            set_window_title_bar_dark(msg, self._is_dark)
            wire_message_box_buttons(msg)
            show_dialog(msg, modal=True)
    
    def _download_example(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить пример конфигурации", "config_example.txt", "Text files (*.txt)"
        )
        if not file_path:
            return
        
        content = """[API]
site = https://viewer.larix.ru

[DATABASE]
server = .\\SQLEXPRESS
database = viewer_old
username = login_ibim
password = passw_ibim
"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            msg = QMessageBox(self)
            icon_path = _dialog_icon_path("alert", self._is_dark)
            if icon_path and os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                msg.setIconPixmap(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Успех")
            msg.setText(f"Пример конфигурации сохранён в:\n{file_path}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if self._is_dark:
                msg.setStyleSheet(DARK_STYLESHEET)
            set_window_title_bar_dark(msg, self._is_dark)
            wire_message_box_buttons(msg)
            show_dialog(msg, modal=True)
        except Exception as e:
            msg = QMessageBox(self)
            icon_path = _dialog_icon_path("error", self._is_dark)
            if icon_path and os.path.exists(icon_path):
                pm = QPixmap(icon_path)
                msg.setIconPixmap(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось сохранить файл:\n{e}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if self._is_dark:
                msg.setStyleSheet(DARK_STYLESHEET)
            set_window_title_bar_dark(msg, self._is_dark)
            wire_message_box_buttons(msg)
            show_dialog(msg, modal=True)
    
    def get_config(self):
        return {
            "site": self.site_edit.text().strip(),
            "server": self.server_edit.text().strip(),
            "database": self.database_edit.text().strip(),
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text().strip(),
        }


class BimSyncWindow(QMainWindow):
    back_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Larix — Синхронизация — Выгрузка в БД")
        self.setMinimumSize(900, 700)
        
        icon_path = app_window_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.is_dark_theme = False
        set_window_title_bar_dark(self, False)

        self.project_cards = []
        self.worker: Optional[SyncWorker] = None
        self._token_check_timer = QTimer(self)
        self._token_check_timer.timeout.connect(self._check_token_periodically)
        self._token_check_timer.setInterval(60000)
        self._is_connected = False
        self._return_to_mode_select = False
        self._card_selection_manager = MultiSelectionManager()
        self._is_handling_card_checkbox = False

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_back = create_back_button(self, icon_dir=ICON_DIR)
        self.btn_back.clicked.connect(self._go_back)
        header_layout.addWidget(self.btn_back)
        
        header_layout.addStretch()

        self.theme_toggle = ThemeToggle()
        self.theme_toggle.toggled.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_toggle)

        main_layout.addWidget(header_frame)

        token_frame = QFrame()
        token_layout = QVBoxLayout(token_frame)
        token_layout.setContentsMargins(0, 0, 0, 0)
        token_layout.setSpacing(6)

        self._sync_auth = None
        self._sync_use_token = True

        self._sync_token_row = QHBoxLayout()
        self._sync_token_row.setSpacing(10)
        self._sync_token_row.addWidget(QLabel("Токен:"))
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwi...")
        self.token_edit.setMinimumWidth(600)
        self._sync_token_row.addWidget(self.token_edit, 1)
        token_layout.addLayout(self._sync_token_row)

        self._sync_token_mode_cb = QCheckBox("Вход по логину и паролю")
        self._sync_token_mode_cb.toggled.connect(self._sync_toggle_auth_mode)
        token_layout.addWidget(self._sync_token_mode_cb)

        self._sync_login_row = QHBoxLayout()
        self._sync_login_row.setSpacing(10)
        self._sync_login_row.addWidget(QLabel("Логин:"))
        self._sync_username_edit = QLineEdit()
        self._sync_username_edit.setPlaceholderText("email или username")
        self._sync_username_edit.setEnabled(False)
        self._sync_login_row.addWidget(self._sync_username_edit, 1)
        token_layout.addLayout(self._sync_login_row)

        self._sync_pass_row = QHBoxLayout()
        self._sync_pass_row.setSpacing(10)
        self._sync_pass_row.addWidget(QLabel("Пароль:"))
        self._sync_password_edit = QLineEdit()
        self._sync_password_edit.setPlaceholderText("Пароль")
        self._sync_password_edit.setEchoMode(QLineEdit.Password)
        self._sync_password_edit.setEnabled(False)
        self._sync_pass_row.addWidget(self._sync_password_edit, 1)
        self._sync_pwd_visible = False
        self._sync_pwd_btn = QToolButton()
        self._sync_pwd_btn.setCursor(Qt.PointingHandCursor)
        self._sync_pwd_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self._sync_pwd_btn.setFixedSize(28, 28)
        self._sync_pwd_btn.clicked.connect(lambda: self._toggle_line_password(
            self._sync_password_edit, "_sync_pwd_visible", self._sync_pwd_btn
        ))
        self._sync_pass_row.addWidget(self._sync_pwd_btn)
        self._update_line_pwd_icon(self._sync_password_edit, False, self._sync_pwd_btn)
        token_layout.addLayout(self._sync_pass_row)

        self._sync_apply_disabled_style()

        main_layout.addWidget(token_frame)
        
        main_layout.addSpacing(20)
        
        db_config_row = QFrame()
        db_config_layout = QHBoxLayout(db_config_row)
        db_config_layout.setContentsMargins(0, 0, 0, 0)
        db_config_layout.setSpacing(10)
        db_config_layout.addStretch()
        
        self.btn_db_auth = QPushButton("Авторизация в БД")
        self.btn_db_auth.setMinimumHeight(40)
        self.btn_db_auth.setMinimumWidth(180)
        self.btn_db_auth.clicked.connect(self._open_db_auth_dialog)
        db_config_layout.addWidget(self.btn_db_auth)
        db_config_layout.addStretch()
        main_layout.addWidget(db_config_row)
        
        self._db_config = {"site": "", "server": "", "database": "", "username": "", "password": ""}
        
        connect_row = QFrame()
        connect_layout = QHBoxLayout(connect_row)
        connect_layout.setContentsMargins(0, 0, 0, 0)
        connect_layout.addStretch()
        self.btn_connect = QPushButton("Подключить")
        self.btn_connect.setMinimumHeight(40)
        self.btn_connect.setMinimumWidth(150)
        self.btn_connect.clicked.connect(self._load_config)
        connect_layout.addWidget(self.btn_connect)
        connect_layout.addStretch()
        main_layout.addWidget(connect_row)

        self.status_label = QLabel()
        self._update_label_style(self.status_label, "#888")
        main_layout.addWidget(self.status_label)

        select_frame = QFrame()
        select_layout = QHBoxLayout(select_frame)
        select_layout.setContentsMargins(0, 0, 0, 0)

        self.select_all_checkbox = QCheckBox("Выбрать все проекты и модели")
        self.select_all_checkbox.setTristate(True)
        self.select_all_checkbox.stateChanged.connect(self._toggle_select_all)
        select_layout.addWidget(self.select_all_checkbox)
        select_layout.addStretch()

        self.projects_count_label = QLabel()
        self._update_label_style(self.projects_count_label, "#888")
        select_layout.addWidget(self.projects_count_label)

        self.select_frame = select_frame
        self.select_frame.setVisible(False)
        main_layout.addWidget(self.select_frame)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.projects_container = QWidget()
        self.projects_layout = QVBoxLayout(self.projects_container)
        self.projects_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.projects_layout.setSpacing(8)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.projects_container)
        main_layout.addWidget(scroll, 1)

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Готово: 0%")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_label)

        self.btn_sync = QPushButton("Загрузить в базу")
        self.btn_sync.setMinimumHeight(40)
        self.btn_sync.setStyleSheet("font-size: 12pt; padding: 10px 24px;")
        self.btn_sync.clicked.connect(self._start_sync)
        self.btn_sync.setEnabled(False)
        main_layout.addWidget(self.btn_sync)

        self.toggle_clear_btn = QPushButton()
        self.toggle_clear_btn.setFixedSize(30, 20)
        self.toggle_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_clear_btn.setStyleSheet("border: none; background: transparent;")
        self._set_toggle_icon(self.toggle_clear_btn, False)
        self.toggle_clear_btn.clicked.connect(self._toggle_clear_section)
        main_layout.addWidget(self.toggle_clear_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.clear_frame = QWidget()
        clear_layout = QVBoxLayout(self.clear_frame)
        clear_layout.setContentsMargins(0, 5, 0, 0)
        
        self.btn_clear_db = QPushButton("Очистить базу данных")
        self.btn_clear_db.setMinimumHeight(35)
        self.btn_clear_db.setStyleSheet("font-size: 10pt; padding: 8px 20px;")
        self.btn_clear_db.clicked.connect(self._clear_database)
        self.btn_clear_db.setEnabled(False)
        clear_layout.addWidget(self.btn_clear_db)
        
        self.clear_frame.setVisible(False)
        main_layout.addWidget(self.clear_frame)
        
        status_row = QFrame()
        status_row_layout = QHBoxLayout(status_row)
        status_row_layout.setContentsMargins(0, 15, 0, 0)
        
        self.db_status_icon = QLabel()
        self.db_status_icon.setFixedSize(20, 20)
        self._set_status_icon(self.db_status_icon, False)
        self.db_status_label = QLabel("БД")
        status_row_layout.addWidget(self.db_status_icon)
        status_row_layout.addWidget(self.db_status_label)
        
        status_row_layout.addStretch()
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setMinimumHeight(30)
        self.btn_cancel.clicked.connect(self._cancel_operations)
        self.btn_cancel.setVisible(False)
        status_row_layout.addWidget(self.btn_cancel)
        
        status_row_layout.addStretch()
        
        self.api_status_label = QLabel("API")
        self.api_status_icon = QLabel()
        self.api_status_icon.setFixedSize(20, 20)
        self._set_status_icon(self.api_status_icon, False)
        status_row_layout.addWidget(self.api_status_label)
        status_row_layout.addWidget(self.api_status_icon)
        
        main_layout.addWidget(status_row)

        QTimer.singleShot(0, self._sync_apply_disabled_style)

    def _update_label_style(self, label, color):
        label.setStyleSheet(f"color: {color};")

    def _set_status_icon(self, icon_label, is_ok):
        icon_path = icon_file("ok.png") if is_ok else icon_file("none.png")
        pm = QPixmap(icon_path)
        if not pm.isNull():
            scaled = pm.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(scaled)

    def _sync_toggle_auth_mode(self, checked: bool):
        self._sync_use_token = not checked
        self._sync_username_edit.setEnabled(checked)
        self._sync_password_edit.setEnabled(checked)
        self.token_edit.setEnabled(not checked)
        if checked:
            self.token_edit.clear()
        else:
            self._sync_username_edit.clear()
            self._sync_password_edit.clear()
        self._sync_apply_disabled_style()

    def _sync_apply_disabled_style(self):
        disabled = "background-color: #f0f0f0; color: #a0a0a0;" if not self.is_dark_theme else "background-color: #2a2a2a; color: #606060;"
        enabled = ""
        for w in (self._sync_username_edit, self._sync_password_edit):
            w.setStyleSheet(disabled if not w.isEnabled() else enabled)
        self.token_edit.setStyleSheet(disabled if not self.token_edit.isEnabled() else enabled)

    def _toggle_line_password(self, line_edit, visible_attr, btn=None):
        new_val = not getattr(self, visible_attr, False)
        setattr(self, visible_attr, new_val)
        if new_val:
            line_edit.setEchoMode(QLineEdit.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.Password)
        self._update_line_pwd_icon(line_edit, new_val, btn)

    def _update_line_pwd_icon(self, line_edit, visible, btn=None):
        icon = _make_pwd_action_icon(visible, self.is_dark_theme)
        if hasattr(line_edit, "set_eye_icon"):
            line_edit.set_eye_icon(icon)
            if hasattr(line_edit, "set_eye_tooltip"):
                line_edit.set_eye_tooltip("Скрыть пароль" if visible else "Показать пароль")
        if btn is not None:
            btn.setIcon(icon)
            btn.setIconSize(QSize(22, 22))

    def _sync_do_login(self) -> bool:
        username = self._sync_username_edit.text().strip()
        password = self._sync_password_edit.text().strip()
        if not username or not password:
            self._show_warning("Внимание", "Введите логин и пароль")
            return False
        from Viewer.keycloak_auth import KeycloakAuth
        if self._sync_auth is None:
            self._sync_auth = KeycloakAuth()
        ok, msg = self._sync_auth.login_password(username, password)
        if not ok:
            self._show_error("Ошибка авторизации", msg)
            return False
        token = self._sync_auth.access_token
        self.token_edit.setText(token)
        CONFIG["token"] = token
        return True

    def _check_token_periodically(self):
        global CONFIG
        if not self._is_connected or not CONFIG:
            return
        try:
            if not self._sync_use_token and self._sync_auth is not None:
                token = self._sync_auth.get_valid_token()
                if token:
                    CONFIG["token"] = token
                    self.token_edit.setText(token)
            api_ok, _ = test_api_connection(CONFIG.get("site", ""), CONFIG.get("token", ""))
            self._set_status_icon(self.api_status_icon, api_ok)
            if not api_ok:
                self.status_label.setText("Токен истёк или недействителен")
                self._show_warning("Токен истёк", "Токен авторизации истёк или недействителен.\nПожалуйста, введите новый токен.")
                self._token_check_timer.stop()
        except Exception:
            pass

    def _cancel_operations(self):
        if self.worker:
            self.worker.request_cancel()
        self.btn_cancel.setVisible(False)
        self.btn_sync.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Отменено")
        self._show_info("Отмена", "Вы отменили все операции, работа прекращена.")

    def _toggle_theme(self, checked):
        self.is_dark_theme = checked
        app = QApplication.instance()
        if app:
            apply_theme(app, checked, icon_dir=ICON_DIR)
        set_window_title_bar_dark(self, self.is_dark_theme)
        for card in self.project_cards:
            card.set_theme(self.is_dark_theme)
        label_color = "#888" if not self.is_dark_theme else "#a0a0a0"
        self._update_label_style(self.status_label, label_color)
        self._update_label_style(self.projects_count_label, label_color)
        self.progress_bar.setTheme(self.is_dark_theme)
        self._set_toggle_icon(self.toggle_clear_btn, self.clear_frame.isVisible())
        self._sync_apply_disabled_style()
        self._update_line_pwd_icon(self._sync_password_edit, self._sync_pwd_visible, self._sync_pwd_btn)

    def _go_back(self):
        self._return_to_mode_select = True
        self.close()

    def closeEvent(self, event):
        self._token_check_timer.stop()
        self._is_connected = False
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()
            self.worker.wait(3000)
        self.back_requested.emit()
        super().closeEvent(event)

    def _open_db_auth_dialog(self):
        dialog = DBAuthDialog(
            self,
            site=self._db_config.get("site", ""),
            server=self._db_config.get("server", ""),
            database=self._db_config.get("database", ""),
            username=self._db_config.get("username", ""),
            password=self._db_config.get("password", ""),
            is_dark=self.is_dark_theme
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._db_config = dialog.get_config()

    def _load_config(self):
        global CONFIG

        if not self._sync_use_token:
            if not self._sync_do_login():
                return

        site = self._db_config.get("site", "")
        server = self._db_config.get("server", "")
        database = self._db_config.get("database", "")
        username = self._db_config.get("username", "")
        password = self._db_config.get("password", "")
        token = self.token_edit.text().strip()
        
        if not site:
            self._show_warning("Внимание", "Укажите сайт.")
            return
        if not server:
            self._show_warning("Внимание", "Укажите сервер.")
            return
        if not database:
            self._show_warning("Внимание", "Укажите базу данных.")
            return
        if not token:
            self._show_warning("Внимание", "Укажите токен авторизации.")
            return
        
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Проверка...")
        QApplication.processEvents()
        
        try:
            odbc_config_dict = {
                "encrypt": True,
                "trust_server_certificate": True,
                "connection_timeout": 30,
            }
            get_odbc_manager(odbc_config_dict)
            
            global TLS_CONFIG_DICT, TLS_MANAGER
            TLS_CONFIG_DICT = {
                "verify": True,
                "request_timeout": 30,
                "connect_timeout": 10,
                "max_retries": 3,
            }
            TLS_MANAGER = get_tls_manager(TLS_CONFIG_DICT)
            
            CONFIG = {
                "site": site,
                "token": token,
                "server": server,
                "database": database,
                "username": username,
                "password": password,
            }

            validate_config(CONFIG)

            self.status_label.setText("Проверка подключения к API...")
            self._set_status_icon(self.api_status_icon, False)
            QApplication.processEvents()
            api_ok, api_message = test_api_connection(CONFIG["site"], CONFIG["token"])
            self._set_status_icon(self.api_status_icon, api_ok)

            self.status_label.setText("Проверка подключения к БД...")
            self._set_status_icon(self.db_status_icon, False)
            QApplication.processEvents()
            db_ok, db_message = test_db_connection(CONFIG)
            self._set_status_icon(self.db_status_icon, db_ok)

            if not api_ok:
                self._show_error("Ошибка API", f"Не удалось подключиться к API:\n{api_message}")
                self.status_label.setText("")
                return

            if not db_ok:
                self._show_error("Ошибка БД", f"Не удалось подключиться к базе данных:\n{db_message}")
                self.status_label.setText("")
                return

            auth_type = "Windows Auth" if not CONFIG.get("username") else "SQL Auth"
            self.status_label.setText(f"Подключено: {CONFIG['database']} ({auth_type})")
            self.btn_clear_db.setEnabled(True)
            self._is_connected = True
            self._token_check_timer.start()
            
            if TLS_MANAGER:
                log_info(f"[TLS] {TLS_MANAGER.get_config_summary().replace(chr(10), ' | ')}")
            
            self._show_info("Успех", "Подключение к API и БД успешно установлено!")
            
            self._fetch_projects()
        except FileNotFoundError as e:
            self._show_error("Ошибка", str(e))
        except configparser.Error as e:
            self._show_error("Ошибка конфигурации", str(e))
        except ValueError as e:
            self._show_error("Ошибка", str(e))
        except Exception as e:
            log_error(f"Ошибка загрузки конфига: {e}\n{traceback.format_exc()}")
            self._show_error("Ошибка", f"Не удалось загрузить конфиг:\n{str(e)}")
        finally:
            self.btn_connect.setEnabled(True)
            self.btn_connect.setText("Подключить")

    def _fetch_projects(self):
        global df_all_projects, project_models
        log_info("Начало загрузки проектов...")
        self.status_label.setText("Загрузка проектов...")
        QApplication.processEvents()

        try:
            log_debug("Запрос списка проектов...")
            df_all_projects = get_all_projects(CONFIG["site"], CONFIG["token"])
            log_info(f"Получено проектов: {len(df_all_projects)}")
            
            project_models = {}
            total = len(df_all_projects)
            for idx, row in df_all_projects.iterrows():
                proj_id = row["idProject"]
                proj_name = row.get("name", "(без названия)")
                log_debug(f"Загрузка моделей для проекта {idx+1}/{total}: {proj_name}")
                
                models_df = get_models_by_project_id(CONFIG["site"], CONFIG["token"], proj_id)
                if not models_df.empty:
                    models_df = models_df.rename(columns={"id": "idModel", "modelName": "NameM"})
                    project_models[proj_id] = models_df.to_dict('records')
                    log_debug(f"Проект '{proj_name}': {len(models_df)} моделей")
                else:
                    project_models[proj_id] = []
                    log_debug(f"Проект '{proj_name}': нет моделей")
            
            log_info(f"Загрузка завершена. Всего проектов: {total}")
            self._show_projects()
        except requests.exceptions.SSLError as e:
            tls_error = classify_ssl_error(e, CONFIG.get("site", ""))
            log_error(f"Ошибка TLS/SSL: {tls_error.error_type.value}\n{tls_error.detail}")
            self._show_error(tls_error.get_title(), tls_error.get_user_message())
        except TLSError as e:
            log_error(f"Ошибка TLS: {e.error_type.value}\n{e.detail}")
            self._show_error(e.get_title(), e.get_user_message())
        except Exception as e:
            log_error(f"Ошибка получения проектов:\n{traceback.format_exc()}")
            self._show_error("Ошибка", f"Не удалось получить проекты:\n{e}")
        finally:
            self.status_label.setText("")

    def _show_projects(self):
        for card in self.project_cards:
            card.deleteLater()
        self.project_cards.clear()
        self._card_selection_manager.clear_selection()

        for idx, (_, row) in enumerate(df_all_projects.iterrows()):
            proj_id = row["idProject"]
            proj_name = str(row.get("name", "")).strip() or "(без названия)"
            models = project_models.get(proj_id, [])

            card = ProjectCard(proj_id, proj_name, models, is_dark=self.is_dark_theme)
            card._card_index = idx
            card.project_checkbox.installEventFilter(self)
            card.installEventFilter(self)
            card.toggled.connect(lambda c=card: self._on_card_toggled(c))
            self.projects_layout.addWidget(card)
            self.project_cards.append(card)
        
        self._card_selection_manager.set_items(self.project_cards)

        self.projects_count_label.setText(f"Всего проектов: {len(self.project_cards)}")
        self.btn_sync.setEnabled(True)
        self.select_frame.setVisible(True)
    
    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            for idx, card in enumerate(self.project_cards):
                if obj == card.project_checkbox:
                    self._handle_card_checkbox_click(idx, card, event)
                    break
                elif obj == card:
                    self._handle_card_click(idx, card, event)
                    break
        return super().eventFilter(obj, event)
    
    def _handle_card_click(self, index, card, event):
        del index, card, event
    
    def _update_card_selection_visual(self):
        pass
    
    def _handle_card_checkbox_click(self, index, card, event):
        del index, card, event
    
    def _on_card_toggled(self, card):
        del card
        self._update_select_all_checkbox_state()

    def _toggle_select_all(self, state):
        has_checked = any(
            cb.isChecked() 
            for card in self.project_cards 
            for cb in card.model_checkboxes.values()
        )
        should_check = not has_checked
        for card in self.project_cards:
            card.select_all(should_check)
        self._update_select_all_checkbox_state()

    def _update_select_all_checkbox_state(self):
        if not self.project_cards:
            return
        total = sum(len(card.model_checkboxes) for card in self.project_cards)
        if total == 0:
            self.select_all_checkbox.blockSignals(True)
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.select_all_checkbox.blockSignals(False)
            return
        checked = sum(
            1 for card in self.project_cards for cb in card.model_checkboxes.values() if cb.isChecked()
        )
        self.select_all_checkbox.blockSignals(True)
        if checked == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked == total:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.select_all_checkbox.blockSignals(False)

    def _start_sync(self):
        global selected_project_ids
        selected_project_ids = []
        selected_models_per_project = {}

        for card in self.project_cards:
            if card.is_selected():
                selected_project_ids.append(card.project_id)
                selected_model_ids = card.get_selected_model_ids()
                if selected_model_ids:
                    selected_models_per_project[card.project_id] = selected_model_ids
                else:
                    selected_models_per_project[card.project_id] = None

        if not selected_project_ids:
            self._show_warning("Внимание", "Не выбрано ни одного проекта или модели!")
            return

        log_info(f"Выбрано проектов: {len(selected_project_ids)}")
        for proj_id in selected_project_ids:
            model_ids = selected_models_per_project.get(proj_id)
            if model_ids:
                log_info(f"Проект {proj_id}: выбрано {len(model_ids)} моделей: {model_ids}")
            else:
                log_info(f"Проект {proj_id}: выбраны все модели")

        reply = self._question_yes_no_cancel(
            "Загрузка свойств",
            "Загрузить свойства элементов?\n\n"
            "Это позволит выгрузить дополнительные параметры (например, размеры, отметки и т.д.)\n"
            "в отдельную таблицу ElementProperties."
        )
        
        if reply == "cancel":
            return
        
        props_to_load = []
        include_empty_rows = False
        if reply == "yes":
            self.btn_sync.setEnabled(False)
            self.progress_label.setText("Сбор доступных параметров...")
            self.progress_bar.setIndeterminate(True)
            QApplication.processEvents()
            
            all_properties = self._collect_all_properties(selected_project_ids, selected_models_per_project)
            
            self.progress_bar.setIndeterminate(False)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Готово: 0%")
            self.btn_sync.setEnabled(True)
            QApplication.processEvents()
            
            if not all_properties:
                self._show_warning("Внимание", "Не удалось получить список параметров. Возможно, элементы пусты или ошибка соединения.")
                return
            
            dialog = PropertiesSelectDialog(all_properties, self.is_dark_theme, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            props_to_load = dialog.get_selected_properties()
            include_empty_rows = dialog.get_include_empty_rows()
            if not props_to_load:
                cont = self._question_yes_no(
                    "Подтверждение",
                    "Не выбрано ни одного параметра. Продолжить без загрузки свойств?"
                )
                if cont != "yes":
                    return
            
            log_info(f"Будут загружены свойства: {len(props_to_load)} параметров")

        self.btn_sync.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Готово: 0%")
        self.btn_cancel.setVisible(True)

        self.worker = SyncWorker(CONFIG, df_all_projects, project_models, selected_project_ids, selected_models_per_project, props_to_load, include_empty_rows)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.token_expired.connect(self._on_token_expired)
        self.worker.start()

    def _collect_all_properties(self, selected_project_ids, selected_models_per_project):
        """Сбор всех уникальных параметров из выбранных моделей"""
        global CONFIG
        all_properties = set()
        
        total_models = 0
        for proj_id in selected_project_ids:
            all_models_list = project_models.get(proj_id, [])
            selected_model_ids = selected_models_per_project.get(proj_id)
            if selected_model_ids is not None:
                total_models += len([m for m in all_models_list if m.get("idModel") in selected_model_ids])
            else:
                total_models += len(all_models_list)
        
        if total_models == 0:
            return []
        
        self.progress_bar.setIndeterminate(False)
        processed = 0
        
        for proj_id in selected_project_ids:
            all_models_list = project_models.get(proj_id, [])
            selected_model_ids = selected_models_per_project.get(proj_id)
            
            if selected_model_ids is not None:
                models = [m for m in all_models_list if m.get("idModel") in selected_model_ids]
            else:
                models = all_models_list
            
            for model in models:
                jimc_id = model.get("idModel")
                if not jimc_id:
                    continue
                
                processed += 1
                percent = int((processed / total_models) * 100)
                self.progress_bar.setValue(percent)
                self.progress_label.setText(f"Сбор параметров: {processed}/{total_models}...")
                QApplication.processEvents()
                
                try:
                    props = get_sample_properties(CONFIG["site"], CONFIG["token"], jimc_id)
                    for p in props:
                        all_properties.add(p)
                except TokenExpiredError:
                    while True:
                        dialog = QDialog(self)
                        dialog.setWindowTitle("Токен истёк")
                        dialog.setMinimumWidth(500)
                        dialog.setModal(True)
                        
                        layout = QVBoxLayout(dialog)
                        layout.setSpacing(12)
                        layout.setContentsMargins(20, 20, 20, 20)
                        
                        header = QLabel("Срок действия токена истёк.\nВведите новый токен для продолжения:")
                        header.setWordWrap(True)
                        layout.addWidget(header)
                        
                        token_edit = QLineEdit()
                        token_edit.setPlaceholderText("bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwi...")
                        token_edit.setMinimumWidth(450)
                        layout.addWidget(token_edit)
                        
                        status_label = QLabel()
                        status_icon = QLabel()
                        status_icon.setFixedSize(20, 20)
                        status_row = QHBoxLayout()
                        status_row.addWidget(status_icon)
                        status_row.addWidget(status_label, 1)
                        layout.addLayout(status_row)
                        
                        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
                        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("ОК")
                        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
                        layout.addWidget(buttons)
                        
                        def on_accept():
                            new_token = token_edit.text().strip()
                            if not new_token:
                                status_label.setText("Введите токен")
                                status_label.setStyleSheet("color: #ff6b6b;")
                                return
                            
                            status_label.setText("Проверка токена...")
                            status_label.setStyleSheet("color: #F7921E;")
                            QApplication.processEvents()
                            
                            ok, msg = test_api_connection(CONFIG["site"], new_token)
                            if ok:
                                pm = QPixmap(icon_file("ok.png"))
                                if not pm.isNull():
                                    status_icon.setPixmap(pm.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                                status_label.setText("Подключение к БД прошло успешно")
                                status_label.setStyleSheet("color: #4CAF50;")
                                QApplication.processEvents()
                                dialog.setProperty("token", new_token)
                                dialog.accept()
                            else:
                                status_label.setText(f"Ошибка: {msg}")
                                status_label.setStyleSheet("color: #ff6b6b;")
                        
                        wire_dialog_button_box(buttons, on_accept, dialog.reject)
                        
                        dialog.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
                        set_window_title_bar_dark(dialog, self.is_dark_theme)
                        
                        if dialog.exec() == QDialog.DialogCode.Accepted:
                            new_token = dialog.property("token")
                            if new_token:
                                CONFIG["token"] = new_token
                                self.token_edit.setText(new_token)
                                self.progress_label.setText("Токен обновлён, продолжение сбора параметров...")
                                QApplication.processEvents()
                                log_info("Токен обновлён, продолжение сбора параметров")
                                break
                        else:
                            return list(all_properties)
                except Exception as e:
                    log_debug(f"Ошибка получения параметров из модели {jimc_id}: {e}")
                    continue
        
        return sorted(list(all_properties))

    def _on_token_expired(self):
        self._set_status_icon(self.api_status_icon, False)
        self._token_check_timer.stop()
        while True:
            dialog = QDialog(self)
            dialog.setWindowTitle("Токен истёк")
            dialog.setMinimumWidth(500)
            dialog.setModal(True)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)
            
            header = QLabel("Срок действия токена истёк.\nВведите новый токен для продолжения:")
            header.setWordWrap(True)
            layout.addWidget(header)
            
            token_edit = QLineEdit()
            token_edit.setPlaceholderText("bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwi...")
            token_edit.setMinimumWidth(450)
            layout.addWidget(token_edit)
            
            status_label = QLabel()
            status_icon = QLabel()
            status_icon.setFixedSize(20, 20)
            status_row = QHBoxLayout()
            status_row.addWidget(status_icon)
            status_row.addWidget(status_label, 1)
            layout.addLayout(status_row)
            
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText("ОК")
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
            layout.addWidget(buttons)
            
            def on_accept():
                new_token = token_edit.text().strip()
                if not new_token:
                    status_label.setText("Введите токен")
                    status_label.setStyleSheet("color: #ff6b6b;")
                    return
                
                status_label.setText("Проверка токена...")
                status_label.setStyleSheet("color: #F7921E;")
                QApplication.processEvents()
                
                ok, msg = test_api_connection(CONFIG["site"], new_token)
                if ok:
                    pm = QPixmap(icon_file("ok.png"))
                    if not pm.isNull():
                        status_icon.setPixmap(pm.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    status_label.setText("Подключение к БД прошло успешно")
                    status_label.setStyleSheet("color: #4CAF50;")
                    QApplication.processEvents()
                    dialog.setProperty("token", new_token)
                    dialog.accept()
                else:
                    status_label.setText(f"Ошибка: {msg}")
                    status_label.setStyleSheet("color: #ff6b6b;")
            
            wire_dialog_button_box(buttons, on_accept, dialog.reject)
            
            dialog.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
            set_window_title_bar_dark(dialog, self.is_dark_theme)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_token = dialog.property("token")
                if new_token:
                    global CONFIG
                    CONFIG["token"] = new_token
                    self.token_edit.setText(new_token)
                    self.worker.set_new_token(new_token)
                    self.status_label.setText("Токен обновлён, продолжение загрузки...")
                    log_info("Токен обновлён, продолжение синхронизации")
                    break
            else:
                self.worker.request_cancel()
                break

    def _toggle_clear_section(self):
        visible = self.clear_frame.isVisible()
        self.clear_frame.setVisible(not visible)
        self._set_toggle_icon(self.toggle_clear_btn, not visible)

    def _set_toggle_icon(self, btn, is_expanded):
        white_path = icon_file("white", "arrow-up.png") if is_expanded else icon_file("white", "arrow-down.png")
        dark_path = icon_file("arrow-up.png") if is_expanded else icon_file("arrow-down.png")
        icon_path = white_path if self.is_dark_theme else dark_path
        pm = QPixmap(icon_path)
        if not pm.isNull():
            scaled = pm.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            btn.setIcon(QIcon(scaled))

    def _clear_database(self):
        reply = self._question_yes_no(
            "Подтверждение", 
            "Вы уверены, что хотите очистить таблицы в базе данных?\n\n"
            "Будут удалены все данные из:\n"
            "• staging.Projects\n"
            "• staging.Models\n"
            "• staging.Elements\n"
            "• staging.ElementProperties\n"
            "• staging.ElementPropertiesWide"
        )
        if reply != "yes":
            return

        self.btn_clear_db.setEnabled(False)
        self.btn_clear_db.setText("Очистка...")

        try:
            use_windows_auth = not CONFIG.get("username") or not CONFIG.get("password")
            conn_str = get_connection_string(CONFIG, use_windows_auth)

            tables = ["staging.Projects", "staging.Models", "staging.Elements", "staging.ElementProperties", "staging.ElementPropertiesWide"]
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                for table in tables:
                    try:
                        cursor.execute(f"TRUNCATE TABLE {table}")
                    except Exception:
                        pass
                conn.commit()

            QMessageBox.information(self, "Готово", "База данных успешно очищена.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось очистить базу данных:\n{e}")
        finally:
            self.btn_clear_db.setEnabled(True)
            self.btn_clear_db.setText("Очистить базу данных")

    def _on_progress(self, percent, text):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"Готово: {percent}% — {text}")

    def _on_finished(self, result):
        self.btn_cancel.setVisible(False)
        self.btn_sync.setEnabled(True)

        failed = result.get('failed', [])
        props_count = result.get('properties', 0)
        elapsed = result.get('elapsed', 0)
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        time_str = f"{minutes} мин {seconds} сек" if minutes > 0 else f"{seconds} сек"

        if failed:
            self._show_warning("Внимание", f"Не удалось загрузить {len(failed)} моделей. Подробности в {LOG_FILE}")
            msg = (
                f"Выгружено с ошибками:\n"
                f"Проектов: {result['projects']}\n"
                f"Моделей: {result['models']}\n"
                f"Элементов: {result['elements']}\n"
            )
            if props_count > 0:
                msg += f"Свойств: {props_count}\n"
            msg += f"\nНе удалось загрузить {len(failed)} моделей.\nПодробности в {LOG_FILE}"
            self._show_warning("Завершено с ошибками", msg)
        else:
            msg = (
                f"Выгружено успешно:\n"
                f"Проектов: {result['projects']}\n"
                f"Моделей: {result['models']}\n"
                f"Элементов: {result['elements']}\n"
            )
            if props_count > 0:
                msg += f"Свойств: {props_count}\n"
            msg += f"\nВремя: {time_str}\nЛог: {LOG_FILE}"
            self._show_info("Готово", msg)

    def _on_error(self, error_msg):
        self.btn_cancel.setVisible(False)
        self.btn_sync.setEnabled(True)
        self._show_error("Ошибка", error_msg)

    def _msg_box(self, icon_type, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        if icon_type == "critical":
            icon_path = _dialog_icon_path("error", self.is_dark_theme)
        elif icon_type == "information":
            icon_path = _dialog_icon_path("ok", self.is_dark_theme)
        else:
            icon_path = _dialog_icon_path("warning", self.is_dark_theme)
        if icon_path and os.path.exists(icon_path):
            pm = QPixmap(icon_path)
            scaled_pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            msg.setIconPixmap(scaled_pm)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
        set_window_title_bar_dark(msg, self.is_dark_theme)
        wire_message_box_buttons(msg)
        return show_dialog(msg, modal=True)

    def _show_warning(self, title, text):
        return self._msg_box("warning", title, text)

    def _show_error(self, title, text):
        return self._msg_box("critical", title, text)

    def _show_info(self, title, text):
        return self._msg_box("information", title, text)
    
    def _question_yes_no_cancel(self, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        btn_yes = msg.addButton("Да", QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        btn_cancel = msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_yes)
        icon_path = _dialog_icon_path("warning", self.is_dark_theme)
        if icon_path and os.path.exists(icon_path):
            pm = QPixmap(icon_path)
            scaled_pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            msg.setIconPixmap(scaled_pm)
        msg.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
        set_window_title_bar_dark(msg, self.is_dark_theme)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_yes:
            return "yes"
        elif clicked == btn_no:
            return "no"
        else:
            return "cancel"
    
    def _question_yes_no(self, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        btn_yes = msg.addButton("Да", QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(btn_yes)
        icon_path = _dialog_icon_path("warning", self.is_dark_theme)
        if icon_path and os.path.exists(icon_path):
            pm = QPixmap(icon_path)
            scaled_pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            msg.setIconPixmap(scaled_pm)
        msg.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
        set_window_title_bar_dark(msg, self.is_dark_theme)
        msg.exec()
        return "yes" if msg.clickedButton() == btn_yes else "no"


class AnimatableShadowEffect(QGraphicsDropShadowEffect):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animBlurRadius = 0.0
        self._animOffsetY = 0.0
    
    def getAnimBlurRadius(self):
        return self._animBlurRadius
    
    def setAnimBlurRadius(self, value):
        self._animBlurRadius = value
        self.setBlurRadius(int(value))
    
    animBlurRadius = Property(float, getAnimBlurRadius, setAnimBlurRadius)
    
    def getAnimOffsetY(self):
        return self._animOffsetY
    
    def setAnimOffsetY(self, value):
        self._animOffsetY = value
        self.setOffset(0, value)
    
    animOffsetY = Property(float, getAnimOffsetY, setAnimOffsetY)


class ModeCard(QFrame):
    clicked = Signal(str)
    
    def __init__(self, mode_id, title, description, is_dark=False, parent=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self.is_dark = is_dark
        self._selected = False
        self._hovered = False
        self._base_pos = None
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 12pt; font-weight: 600;")
        layout.addWidget(self.title_label)
        
        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #888; font-size: 9pt;")
        layout.addWidget(self.desc_label)
        
        self._shadow = AnimatableShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self._shadow)
        
        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(180)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._shadow_blur_anim = QPropertyAnimation(self._shadow, b"animBlurRadius")
        self._shadow_blur_anim.setDuration(180)
        self._shadow_blur_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._shadow_offset_anim = QPropertyAnimation(self._shadow, b"animOffsetY")
        self._shadow_offset_anim.setDuration(180)
        self._shadow_offset_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._update_style()
    
    def setSelected(self, selected):
        self._selected = selected
        self._update_style()
    
    def isSelected(self):
        return self._selected
    
    def setTheme(self, is_dark):
        self.is_dark = is_dark
        self._update_style()
    
    def _update_style(self):
        if self.is_dark:
            bg_normal = "#1e1e1e"
            bg_hover = "#252220"
            bg_selected = "#28241f"
            border_normal = "#404040"
            border_hover = "#8a5520"
            border_selected = "#b86a15"
            text_color = "#e0e0e0"
        else:
            bg_normal = "#ffffff"
            bg_hover = "#fdf8f3"
            bg_selected = "#faf5ef"
            border_normal = "#e0e0e0"
            border_hover = "#d99030"
            border_selected = "#c97a1c"
            text_color = "#222"
        
        if self._selected:
            bg = bg_selected
            border = border_selected
        elif self._hovered:
            bg = bg_hover
            border = border_hover
        else:
            bg = bg_normal
            border = border_normal
        
        self.setStyleSheet(f"""
            ModeCard {{
                background: {bg};
                border: 2px solid {border};
                border-radius: 12px;
            }}
        """)
        self.title_label.setStyleSheet(f"font-size: 12pt; font-weight: 600; color: {text_color}; background: transparent;")
        desc_color = "#b86a15" if self._selected else "#888"
        self.desc_label.setStyleSheet(f"color: {desc_color}; font-size: 9pt; background: transparent;")
    
    def _animate_to(self, hover):
        if self._base_pos is None:
            self._base_pos = self.pos()
        
        self.raise_()
        
        current_pos = self.pos()
        target_y = self._base_pos.y() - 8 if hover else self._base_pos.y()
        
        if current_pos.y() != target_y:
            self._pos_anim.stop()
            self._pos_anim.setStartValue(current_pos)
            self._pos_anim.setEndValue(QPoint(self._base_pos.x(), target_y))
            self._pos_anim.start()
        
        target_blur = 25.0 if hover else 0.0
        target_offset = 8.0 if hover else 0.0
        
        if abs(self._shadow.getAnimBlurRadius() - target_blur) > 0.5:
            self._shadow_blur_anim.stop()
            self._shadow_blur_anim.setStartValue(self._shadow.getAnimBlurRadius())
            self._shadow_blur_anim.setEndValue(target_blur)
            self._shadow_blur_anim.start()
        
        if abs(self._shadow.getAnimOffsetY() - target_offset) > 0.5:
            self._shadow_offset_anim.stop()
            self._shadow_offset_anim.setStartValue(self._shadow.getAnimOffsetY())
            self._shadow_offset_anim.setEndValue(target_offset)
            self._shadow_offset_anim.start()
    
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        self._animate_to(True)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        self._animate_to(False)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.mode_id)
        super().mousePressEvent(event)


class ModeSelectWidget(QWidget):
    mode_selected = Signal(str)
    back_requested = Signal()
    
    def __init__(self, is_dark=False, parent=None):
        super().__init__(parent)
        self.selected_mode = None
        self.is_dark = is_dark
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header_layout = QHBoxLayout()
        
        self.btn_back = create_back_button(self, icon_dir=ICON_DIR)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.btn_back)
        
        header_layout.addStretch()
        
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.setChecked(self.is_dark)
        self.theme_toggle.toggled.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_toggle)
        
        layout.addLayout(header_layout)
        
        title = QLabel("Выберите режим работы")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        cards_container = QWidget()
        cards_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setSpacing(20)
        cards_layout.setContentsMargins(0, 10, 0, 10)
        
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        
        self.card_csv = ModeCard("powerbi", "Выгрузить в файлы (CSV)", "Данные в файлах .csv\nдля Power BI, Excel и др.", self.is_dark)
        self.card_csv.setMinimumHeight(90)
        self.card_csv.clicked.connect(self._on_card_clicked)
        row1.addWidget(self.card_csv)
        
        self.card_db = ModeCard("database", "Выгрузить в SQL Server", "Данные в таблицы SQL Server\nstaging.Projects и др.", self.is_dark)
        self.card_db.setMinimumHeight(90)
        self.card_db.clicked.connect(self._on_card_clicked)
        row1.addWidget(self.card_db)
        
        cards_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.setSpacing(20)
        
        self.card_parquet = ModeCard("parquet", "Parquet", "Импорт в Power BI:\nПолучить данные → Другие → Папка", self.is_dark)
        self.card_parquet.setMinimumHeight(90)
        self.card_parquet.clicked.connect(self._on_card_clicked)
        row2.addWidget(self.card_parquet)
        
        self.card_sqlite = ModeCard("sqlite", "База данных", "Файл .db", self.is_dark)
        self.card_sqlite.setMinimumHeight(90)
        self.card_sqlite.clicked.connect(self._on_card_clicked)
        row2.addWidget(self.card_sqlite)
        
        cards_layout.addLayout(row2)
        
        layout.addWidget(cards_container)
        layout.addStretch()
        
        self.selected_mode = None
    
    def _on_card_clicked(self, mode_id):
        self.selected_mode = mode_id
        self.card_csv.setSelected(mode_id == "powerbi")
        self.card_db.setSelected(mode_id == "database")
        self.card_parquet.setSelected(mode_id == "parquet")
        self.card_sqlite.setSelected(mode_id == "sqlite")
        self.mode_selected.emit(mode_id)
    
    def _clear_selection(self):
        self.selected_mode = None
        self.card_csv.setSelected(False)
        self.card_db.setSelected(False)
        self.card_parquet.setSelected(False)
        self.card_sqlite.setSelected(False)
    
    def _toggle_theme(self, checked):
        self.is_dark = checked
        app = QApplication.instance()
        if app:
            apply_theme(app, checked, icon_dir=ICON_DIR)
        self.card_csv.setTheme(checked)
        self.card_db.setTheme(checked)
        self.card_parquet.setTheme(checked)
        self.card_sqlite.setTheme(checked)


class ModeSelectDialog(QDialog):
    def __init__(self, is_dark=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Larix — Синхронизация")
        self.setMinimumSize(600, 400)
        self.setModal(True)
        self.selected_mode = None
        self.is_dark = is_dark
        
        icon_path = app_window_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self._build_ui()
        set_window_title_bar_dark(self, is_dark)
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header_layout = QHBoxLayout()
        
        self.btn_back = create_back_button(self, icon_dir=ICON_DIR)
        self.btn_back.clicked.connect(self.reject)
        header_layout.addWidget(self.btn_back)
        
        header_layout.addStretch()
        
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.setChecked(self.is_dark)
        self.theme_toggle.toggled.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_toggle)
        
        layout.addLayout(header_layout)
        
        title = QLabel("Выберите режим работы")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        cards_container = QWidget()
        cards_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setSpacing(20)
        cards_layout.setContentsMargins(0, 10, 0, 10)
        
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        
        self.card_csv = ModeCard("powerbi", "Выгрузить в файлы (CSV)", "Данные в файлах .csv\nдля Power BI, Excel и др.", self.is_dark)
        self.card_csv.setMinimumHeight(90)
        self.card_csv.clicked.connect(self._on_card_clicked)
        row1.addWidget(self.card_csv)
        
        self.card_db = ModeCard("database", "Выгрузить в SQL Server", "Данные в таблицы SQL Server\nstaging.Projects и др.", self.is_dark)
        self.card_db.setMinimumHeight(90)
        self.card_db.clicked.connect(self._on_card_clicked)
        row1.addWidget(self.card_db)
        
        cards_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.setSpacing(20)
        
        self.card_parquet = ModeCard("parquet", "Parquet", "Импорт в Power BI:\nПолучить данные → Другие → Папка", self.is_dark)
        self.card_parquet.setMinimumHeight(90)
        self.card_parquet.clicked.connect(self._on_card_clicked)
        row2.addWidget(self.card_parquet)
        
        self.card_sqlite = ModeCard("sqlite", "База данных", "Файл .db", self.is_dark)
        self.card_sqlite.setMinimumHeight(90)
        self.card_sqlite.clicked.connect(self._on_card_clicked)
        row2.addWidget(self.card_sqlite)
        
        cards_layout.addLayout(row2)
        
        layout.addWidget(cards_container)
        layout.addStretch()
        
        self.selected_mode = None
    
    def _on_card_clicked(self, mode_id):
        self.selected_mode = mode_id
        self.card_csv.setSelected(mode_id == "powerbi")
        self.card_db.setSelected(mode_id == "database")
        self.card_parquet.setSelected(mode_id == "parquet")
        self.card_sqlite.setSelected(mode_id == "sqlite")
        self.accept()
    
    def _clear_selection(self):
        self.selected_mode = None
        self.card_csv.setSelected(False)
        self.card_db.setSelected(False)
        self.card_parquet.setSelected(False)
        self.card_sqlite.setSelected(False)
    
    def mousePressEvent(self, event):
        child = self.childAt(event.position().toPoint())
        if not isinstance(child, ModeCard):
            parent = child.parent() if child else None
            while parent:
                if isinstance(parent, ModeCard):
                    break
                parent = parent.parent()
            if not parent:
                self._clear_selection()
        super().mousePressEvent(event)
    
    def _toggle_theme(self, checked):
        self.is_dark = checked
        app = QApplication.instance()
        if app:
            apply_theme(app, checked, icon_dir=ICON_DIR)
        self.card_csv.setTheme(checked)
        self.card_db.setTheme(checked)
        self.card_parquet.setTheme(checked)
        self.card_sqlite.setTheme(checked)
        set_window_title_bar_dark(self, checked)


class PowerBiExportWindow(QMainWindow):
    back_requested = Signal()
    
    def __init__(self, format_type="csv"):
        super().__init__()
        self.format_type = format_type
        format_names = {"csv": "CSV", "parquet": "Parquet", "sqlite": "SQLite"}
        format_name = format_names.get(format_type, "CSV")
        self.setWindowTitle(f"Larix — Синхронизация — Выгрузка в файлы ({format_name})")
        self.setMinimumSize(900, 700)
        
        icon_path = app_window_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.is_dark_theme = False
        set_window_title_bar_dark(self, False)
        
        self.project_cards = []
        self.worker: Optional[PowerBiSyncWorker] = None
        self._return_to_mode_select = False
        self._card_selection_manager = MultiSelectionManager()
        self._is_handling_card_checkbox = False
        
        self._build_ui()
    
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 12)
        main_layout.setSpacing(12)
        
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_back = create_back_button(self, icon_dir=ICON_DIR)
        self.btn_back.clicked.connect(self._go_back)
        header_layout.addWidget(self.btn_back)
        
        header_layout.addStretch()
        
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.toggled.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_toggle)
        main_layout.addWidget(header_frame)
        
        api_frame = QFrame()
        api_layout = QVBoxLayout(api_frame)
        api_layout.setSpacing(10)
        
        site_layout = QHBoxLayout()
        site_layout.addWidget(QLabel("Сайт API:"))
        self.site_edit = QLineEdit()
        self.site_edit.setText("https://viewer.larix.ru/")
        self.site_edit.setPlaceholderText("https://viewer.larix.ru/")
        self.site_edit.setMinimumWidth(400)
        site_layout.addWidget(self.site_edit, 1)
        api_layout.addLayout(site_layout)
        
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Токен:"))
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwi...")
        self.token_edit.setMinimumWidth(400)
        token_layout.addWidget(self.token_edit, 1)
        api_layout.addLayout(token_layout)

        self._pbi_auth = None
        self._pbi_use_token = True

        pbi_mode_row = QHBoxLayout()
        self._pbi_token_mode_cb = QCheckBox("Вход по логину и паролю")
        self._pbi_token_mode_cb.toggled.connect(self._pbi_toggle_auth_mode)
        pbi_mode_row.addWidget(self._pbi_token_mode_cb)
        pbi_mode_row.addStretch()
        api_layout.addLayout(pbi_mode_row)

        pbi_login_row = QHBoxLayout()
        pbi_login_row.addWidget(QLabel("Логин:"))
        self._pbi_username_edit = QLineEdit()
        self._pbi_username_edit.setPlaceholderText("email или username")
        self._pbi_username_edit.setEnabled(False)
        pbi_login_row.addWidget(self._pbi_username_edit, 1)
        api_layout.addLayout(pbi_login_row)

        pbi_pass_row = QHBoxLayout()
        pbi_pass_row.addWidget(QLabel("Пароль:"))
        self._pbi_password_edit = _InlinePasswordLineEdit()
        self._pbi_password_edit.setPlaceholderText("Пароль")
        self._pbi_password_edit.setEchoMode(QLineEdit.Password)
        self._pbi_password_edit.setEnabled(False)
        self._pbi_password_edit.set_eye_clicked(
            lambda: self._toggle_line_password(self._pbi_password_edit, "_pbi_pwd_visible")
        )
        pbi_pass_row.addWidget(self._pbi_password_edit, 1)
        self._pbi_pwd_visible = False
        self._update_line_pwd_icon(self._pbi_password_edit, False)
        api_layout.addLayout(pbi_pass_row)
        
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Папка для выгрузки:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Выберите папку...")
        self.output_edit.setMinimumWidth(350)
        output_layout.addWidget(self.output_edit, 1)
        btn_browse = QPushButton("Выбрать")
        btn_browse.clicked.connect(self._browse_folder)
        output_layout.addWidget(btn_browse)
        api_layout.addLayout(output_layout)
        
        main_layout.addWidget(api_frame)
        
        self.btn_connect = QPushButton("Подключить")
        self.btn_connect.setMinimumWidth(120)
        self.btn_connect.clicked.connect(self._connect)
        main_layout.addWidget(self.btn_connect)
        
        select_frame = QFrame()
        select_layout = QHBoxLayout(select_frame)
        select_layout.setContentsMargins(0, 0, 0, 0)
        
        self.select_all_checkbox = QCheckBox("Выбрать все проекты и модели")
        self.select_all_checkbox.setTristate(True)
        self.select_all_checkbox.stateChanged.connect(self._toggle_select_all)
        select_layout.addWidget(self.select_all_checkbox)
        select_layout.addStretch()
        
        self.projects_count_label = QLabel()
        self._update_label_style(self.projects_count_label, "#888")
        select_layout.addWidget(self.projects_count_label)
        
        self.select_frame = select_frame
        self.select_frame.setVisible(False)
        main_layout.addWidget(self.select_frame)
        
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.projects_container = QWidget()
        self.projects_layout = QVBoxLayout(self.projects_container)
        self.projects_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.projects_layout.setSpacing(8)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.projects_container)
        main_layout.addWidget(scroll, 1)
        
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Готово: 0%")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_label)
        
        format_labels = {"csv": "CSV", "parquet": "Parquet", "sqlite": "SQLite"}
        format_label = format_labels.get(self.format_type, "CSV")
        self.btn_sync = QPushButton(f"Выгрузить в {format_label}")
        self.btn_sync.setMinimumHeight(40)
        self.btn_sync.setStyleSheet("font-size: 12pt; padding: 10px 24px;")
        self.btn_sync.clicked.connect(self._start_sync)
        self.btn_sync.setEnabled(False)
        main_layout.addWidget(self.btn_sync)
        
        status_bar = QFrame()
        status_bar.setMinimumHeight(36)
        status_bar_layout = QHBoxLayout(status_bar)
        status_bar_layout.setContentsMargins(10, 10, 10, 10)
        
        self.api_status_icon = QLabel()
        self.api_status_icon.setFixedSize(20, 20)
        self._set_status_icon(self.api_status_icon, False)
        status_bar_layout.addWidget(self.api_status_icon)
        
        self.status_label = QLabel("Не подключено")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt;")
        status_bar_layout.addWidget(self.status_label)
        
        status_bar_layout.addStretch()
        
        main_layout.addWidget(status_bar)
    
        QTimer.singleShot(0, self._pbi_apply_disabled_style)

    def _update_label_style(self, label, color):
        label.setStyleSheet(f"color: {color};")
    
    def _set_status_icon(self, label, success):
        icon_path = icon_file("ok.png") if success else icon_file("none.png")
        if os.path.exists(icon_path):
            pm = QPixmap(icon_path)
            label.setPixmap(pm.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            label.setText("✓" if success else "✗")
    
    def _go_back(self):
        self._return_to_mode_select = True
        self.close()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()
            self.worker.wait(3000)
        self.back_requested.emit()
        super().closeEvent(event)
    
    def _toggle_theme(self, checked):
        self.is_dark_theme = checked
        app = QApplication.instance()
        if app:
            apply_theme(app, checked, icon_dir=ICON_DIR)
        set_window_title_bar_dark(self, self.is_dark_theme)
        for card in self.project_cards:
            card.set_theme(self.is_dark_theme)
        label_color = "#888" if not self.is_dark_theme else "#a0a0a0"
        self._update_label_style(self.projects_count_label, label_color)
        self.progress_bar.setTheme(self.is_dark_theme)
        self._update_line_pwd_icon(self._pbi_password_edit, self._pbi_pwd_visible)
    
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для выгрузки")
        if folder:
            self.output_edit.setText(folder)
    
    def _pbi_toggle_auth_mode(self, checked):
        self._pbi_use_token = not checked
        self._pbi_username_edit.setEnabled(checked)
        self._pbi_password_edit.setEnabled(checked)
        self.token_edit.setEnabled(not checked)
        if checked:
            self.token_edit.clear()
        else:
            self._pbi_username_edit.clear()
            self._pbi_password_edit.clear()
        self._pbi_apply_disabled_style()

    def _pbi_apply_disabled_style(self):
        disabled = "background-color: #f0f0f0; color: #a0a0a0;" if not self.is_dark_theme else "background-color: #2a2a2a; color: #606060;"
        enabled = ""
        for w in (self._pbi_username_edit, self._pbi_password_edit):
            w.setStyleSheet(disabled if not w.isEnabled() else enabled)
        self.token_edit.setStyleSheet(disabled if not self.token_edit.isEnabled() else enabled)

    def _toggle_line_password(self, line_edit, visible_attr, btn=None):
        new_val = not getattr(self, visible_attr, False)
        setattr(self, visible_attr, new_val)
        if new_val:
            line_edit.setEchoMode(QLineEdit.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.Password)
        self._update_line_pwd_icon(line_edit, new_val, btn)

    def _update_line_pwd_icon(self, line_edit, visible, btn=None):
        icon = _make_pwd_action_icon(visible, self.is_dark_theme)
        if hasattr(line_edit, "set_eye_icon"):
            line_edit.set_eye_icon(icon)
            if hasattr(line_edit, "set_eye_tooltip"):
                line_edit.set_eye_tooltip("Скрыть пароль" if visible else "Показать пароль")
        if btn is not None:
            btn.setIcon(icon)
            btn.setIconSize(QSize(22, 22))

    def _pbi_do_login(self) -> bool:
        username = self._pbi_username_edit.text().strip()
        password = self._pbi_password_edit.text().strip()
        if not username or not password:
            self._show_warning("Внимание", "Введите логин и пароль")
            return False
        from Viewer.keycloak_auth import KeycloakAuth
        if self._pbi_auth is None:
            self._pbi_auth = KeycloakAuth()
        ok, msg = self._pbi_auth.login_password(username, password)
        if not ok:
            self._show_error("Ошибка авторизации", msg)
            return False
        self.token_edit.setText(self._pbi_auth.access_token)
        return True

    def _connect(self):
        if not self._pbi_use_token:
            if not self._pbi_do_login():
                return

        site = self.site_edit.text().strip()
        token = self.token_edit.text().strip()
        
        if not site:
            self._show_warning("Внимание", "Укажите URL сайта.")
            return
        if not token:
            self._show_warning("Внимание", "Укажите токен авторизации.")
            return
        if not site.startswith(("http://", "https://")):
            self._show_warning("Внимание", "URL должен начинаться с http:// или https://")
            return
        
        global CONFIG
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Проверка...")
        self._set_status_icon(self.api_status_icon, False)
        QApplication.processEvents()
        
        try:
            CONFIG = {
                "site": site,
                "token": token,
            }
            
            self.status_label.setText("Проверка подключения...")
            self.status_label.setStyleSheet("color: #F7921E; font-size: 9pt;")
            QApplication.processEvents()
            api_ok, api_message = test_api_connection(site, token)
            self._set_status_icon(self.api_status_icon, api_ok)
            
            if not api_ok:
                self._show_error("Ошибка API", f"Не удалось подключиться к API:\n{api_message}")
                self.status_label.setText("Ошибка подключения")
                self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
                return
            
            self.status_label.setText("Подключено")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 9pt;")
            self._fetch_projects()
        except Exception as e:
            log_error(f"Ошибка подключения: {e}\n{traceback.format_exc()}")
            self._show_error("Ошибка", f"Не удалось подключиться:\n{str(e)}")
            self.status_label.setText("Ошибка подключения")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
        finally:
            self.btn_connect.setEnabled(True)
            self.btn_connect.setText("Подключить")
    
    def _fetch_projects(self):
        global df_all_projects, project_models
        log_info("Начало загрузки проектов...")
        self.status_label.setText("Загрузка проектов...")
        self.status_label.setStyleSheet("color: #F7921E; font-size: 9pt;")
        QApplication.processEvents()
        
        try:
            df_all_projects = get_all_projects(CONFIG["site"], CONFIG["token"])
            log_info(f"Получено проектов: {len(df_all_projects)}")
            
            project_models = {}
            total = len(df_all_projects)
            for idx, row in df_all_projects.iterrows():
                proj_id = row["idProject"]
                proj_name = row.get("name", "(без названия)")
                log_debug(f"Загрузка моделей для проекта {idx+1}/{total}: {proj_name}")
                
                models_df = get_models_by_project_id(CONFIG["site"], CONFIG["token"], proj_id)
                if not models_df.empty:
                    models_df = models_df.rename(columns={"id": "idModel", "modelName": "NameM"})
                    project_models[proj_id] = models_df.to_dict('records')
                else:
                    project_models[proj_id] = []
            
            self.status_label.setText(f"Подключено • {len(df_all_projects)} проектов")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 9pt;")
            self._show_projects()
        except Exception as e:
            log_error(f"Ошибка получения проектов:\n{traceback.format_exc()}")
            self._show_error("Ошибка", f"Не удалось получить проекты:\n{e}")
    
    def _show_projects(self):
        for card in self.project_cards:
            card.deleteLater()
        self.project_cards.clear()
        self._card_selection_manager.clear_selection()
        
        for idx, (_, row) in enumerate(df_all_projects.iterrows()):
            proj_id = row["idProject"]
            proj_name = str(row.get("name", "")).strip() or "(без названия)"
            models = project_models.get(proj_id, [])
            
            card = ProjectCard(proj_id, proj_name, models, is_dark=self.is_dark_theme)
            card._card_index = idx
            card.project_checkbox.installEventFilter(self)
            card.installEventFilter(self)
            card.toggled.connect(lambda c=card: self._on_card_toggled(c))
            self.projects_layout.addWidget(card)
            self.project_cards.append(card)
        
        self._card_selection_manager.set_items(self.project_cards)
        
        self.projects_count_label.setText(f"Всего проектов: {len(self.project_cards)}")
        self.btn_sync.setEnabled(True)
        self.select_frame.setVisible(True)
    
    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            for idx, card in enumerate(self.project_cards):
                if obj == card.project_checkbox:
                    self._handle_card_checkbox_click(idx, card, event)
                    break
                elif obj == card:
                    self._handle_card_click(idx, card, event)
                    break
        return super().eventFilter(obj, event)
    
    def _handle_card_click(self, index, card, event):
        del index, card, event
    
    def _update_card_selection_visual(self):
        pass
    
    def _handle_card_checkbox_click(self, index, card, event):
        del index, card, event
    
    def _on_card_toggled(self, card):
        del card
        self._update_select_all_checkbox_state()
    
    def _toggle_select_all(self, state):
        has_checked = any(
            cb.isChecked() 
            for card in self.project_cards 
            for cb in card.model_checkboxes.values()
        )
        should_check = not has_checked
        for card in self.project_cards:
            card.select_all(should_check)
        self._update_select_all_checkbox_state()
    
    def _update_select_all_checkbox_state(self):
        if not self.project_cards:
            return
        total = sum(len(card.model_checkboxes) for card in self.project_cards)
        if total == 0:
            self.select_all_checkbox.blockSignals(True)
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.select_all_checkbox.blockSignals(False)
            return
        checked = sum(
            1 for card in self.project_cards for cb in card.model_checkboxes.values() if cb.isChecked()
        )
        self.select_all_checkbox.blockSignals(True)
        if checked == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked == total:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self.select_all_checkbox.blockSignals(False)
    
    def _start_sync(self):
        global selected_project_ids
        selected_project_ids = []
        selected_models_per_project = {}
        
        for card in self.project_cards:
            if card.is_selected():
                selected_project_ids.append(card.project_id)
                selected_model_ids = card.get_selected_model_ids()
                if selected_model_ids:
                    selected_models_per_project[card.project_id] = selected_model_ids
                else:
                    selected_models_per_project[card.project_id] = None
        
        if not selected_project_ids:
            self._show_warning("Внимание", "Не выбрано ни одного проекта или модели!")
            return
        
        output_path = self.output_edit.text().strip()
        if not output_path:
            self._show_warning("Внимание", "Выберите папку для выгрузки!")
            return
        
        reply = self._question_yes_no_cancel(
            "Загрузка свойств",
            "Загрузить свойства элементов?\n\n"
            "Это позволит выгрузить дополнительные параметры в отдельные файлы."
        )
        
        if reply == "cancel":
            return
        
        props_to_load = []
        include_empty_rows = False
        if reply == "yes":
            self.btn_sync.setEnabled(False)
            self.progress_label.setText("Сбор доступных параметров...")
            self.progress_bar.setIndeterminate(True)
            QApplication.processEvents()
            
            all_properties = self._collect_all_properties(selected_project_ids, selected_models_per_project)
            
            self.progress_bar.setIndeterminate(False)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Готово: 0%")
            self.btn_sync.setEnabled(True)
            QApplication.processEvents()
            
            if not all_properties:
                self._show_warning("Внимание", "Не удалось получить список параметров.")
                return
            
            dialog = PropertiesSelectDialog(all_properties, self.is_dark_theme, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            props_to_load = dialog.get_selected_properties()
            include_empty_rows = dialog.get_include_empty_rows()
        
        self.btn_sync.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Готово: 0%")
        
        self.worker = PowerBiSyncWorker(
            CONFIG, df_all_projects, project_models, 
            selected_project_ids, selected_models_per_project, 
            props_to_load, output_path, self.format_type, include_empty_rows
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.token_expired.connect(self._on_token_expired)
        self.worker.start()
    
    def _collect_all_properties(self, selected_project_ids, selected_models_per_project):
        global CONFIG
        all_properties = set()
        
        total_models = 0
        for proj_id in selected_project_ids:
            all_models_list = project_models.get(proj_id, [])
            selected_model_ids = selected_models_per_project.get(proj_id)
            if selected_model_ids is not None:
                total_models += len([m for m in all_models_list if m.get("idModel") in selected_model_ids])
            else:
                total_models += len(all_models_list)
        
        if total_models == 0:
            return []
        
        self.progress_bar.setIndeterminate(False)
        processed = 0
        
        for proj_id in selected_project_ids:
            all_models_list = project_models.get(proj_id, [])
            selected_model_ids = selected_models_per_project.get(proj_id)
            
            if selected_model_ids is not None:
                models = [m for m in all_models_list if m.get("idModel") in selected_model_ids]
            else:
                models = all_models_list
            
            for model in models:
                jimc_id = model.get("idModel")
                if not jimc_id:
                    continue
                
                processed += 1
                percent = int((processed / total_models) * 100)
                self.progress_bar.setValue(percent)
                self.progress_label.setText(f"Сбор параметров: {processed}/{total_models}...")
                QApplication.processEvents()
                
                try:
                    props = get_sample_properties(CONFIG["site"], CONFIG["token"], jimc_id)
                    for p in props:
                        all_properties.add(p)
                except TokenExpiredError:
                    pass
                except Exception as e:
                    log_debug(f"Ошибка получения параметров из модели {jimc_id}: {e}")
                    continue
        
        return sorted(list(all_properties))
    
    def _on_token_expired(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Токен истёк")
        dialog.setMinimumWidth(500)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Срок действия токена истёк.\nВведите новый токен для продолжения:")
        header.setWordWrap(True)
        layout.addWidget(header)
        
        token_edit = QLineEdit()
        token_edit.setPlaceholderText("bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwi...")
        token_edit.setMinimumWidth(450)
        layout.addWidget(token_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("ОК")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        layout.addWidget(buttons)
        
        def on_accept():
            new_token = token_edit.text().strip()
            if new_token:
                dialog.setProperty("token", new_token)
                dialog.accept()
        
        wire_dialog_button_box(buttons, on_accept, dialog.reject)
        
        dialog.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
        set_window_title_bar_dark(dialog, self.is_dark_theme)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_token = dialog.property("token")
            if new_token:
                global CONFIG
                CONFIG["token"] = new_token
                self.token_edit.setText(new_token)
                self.worker.set_new_token(new_token)
        else:
            self.worker.request_cancel()
    
    def _on_progress(self, percent, text):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"Готово: {percent}% — {text}")
    
    def _on_finished(self, result):
        self.btn_sync.setEnabled(True)
        
        props_count = result.get('properties', 0)
        elapsed = result.get('elapsed', 0)
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        time_str = f"{minutes} мин {seconds} сек" if minutes > 0 else f"{seconds} сек"
        output_path = result.get('output_path', '')
        
        msg = (
            f"Выгружено успешно:\n"
            f"Проектов: {result['projects']}\n"
            f"Моделей: {result['models']}\n"
            f"Элементов: {result['elements']}\n"
        )
        if props_count > 0:
            msg += f"Свойств: {props_count}\n"
        msg += f"\nПапка: {output_path}\nВремя: {time_str}"
        self._show_info("Готово", msg)
    
    def _on_error(self, error_msg):
        self.btn_sync.setEnabled(True)
        self._show_error("Ошибка", error_msg)
    
    def _msg_box(self, icon_type, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        if icon_type == "critical":
            icon_path = _dialog_icon_path("error", self.is_dark_theme)
        elif icon_type == "information":
            icon_path = _dialog_icon_path("ok", self.is_dark_theme)
        else:
            icon_path = _dialog_icon_path("warning", self.is_dark_theme)
        if icon_path and os.path.exists(icon_path):
            pm = QPixmap(icon_path)
            scaled_pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            msg.setIconPixmap(scaled_pm)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
        set_window_title_bar_dark(msg, self.is_dark_theme)
        wire_message_box_buttons(msg)
        return show_dialog(msg, modal=True)
    
    def _show_warning(self, title, text):
        return self._msg_box("warning", title, text)
    
    def _show_error(self, title, text):
        return self._msg_box("critical", title, text)
    
    def _show_info(self, title, text):
        return self._msg_box("information", title, text)
    
    def _question_yes_no_cancel(self, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        btn_yes = msg.addButton("Да", QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        btn_cancel = msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_yes)
        icon_path = _dialog_icon_path("warning", self.is_dark_theme)
        if icon_path and os.path.exists(icon_path):
            pm = QPixmap(icon_path)
            scaled_pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            msg.setIconPixmap(scaled_pm)
        msg.setStyleSheet(DARK_STYLESHEET if self.is_dark_theme else LIGHT_STYLESHEET)
        set_window_title_bar_dark(msg, self.is_dark_theme)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_yes:
            return "yes"
        elif clicked == btn_no:
            return "no"
        else:
            return "cancel"


class PowerBiSyncWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)
    token_expired = Signal()

    def __init__(self, config, projects_df, proj_models, selected_ids, selected_models_per_project=None, selected_properties=None, output_path=None, format_type="csv", include_empty_rows=False):
        super().__init__()
        self.config = config
        self.projects_df = projects_df
        self.proj_models = proj_models
        self.selected_ids = selected_ids
        self.selected_models_per_project = selected_models_per_project or {}
        self.selected_properties = selected_properties or []
        self.output_path = output_path
        self.format_type = format_type
        self.include_empty_rows = include_empty_rows
        self._token_updated = threading.Event()
        self._token_lock = threading.Lock()
        self._token_dialog_active = False
        self._cancel_requested = False

    def set_new_token(self, token):
        self.config["token"] = token
        self._token_updated.set()

    def request_cancel(self):
        self._cancel_requested = True
        self._token_updated.set()

    def _wait_for_token_update(self):
        while not self._cancel_requested:
            if self._token_updated.wait(timeout=0.5):
                return True
        return False

    def _get_elements_with_retry(self, site, token, jimc_id, start_page=1):
        all_elements = []
        page = start_page
        page_size = 500
        max_retries = 3
        retry_delay = 3
        
        session = get_session()
        while True:
            if self._cancel_requested:
                return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, True
            
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    body = {"order": [], "pagination": {"page": page, "pageSize": page_size}}
                    url = f"{site}/api/tree-table/elements"
                    current_token = normalize_token(self.config["token"])
                    
                    response = session.post(
                        url,
                        params={"jimcIdArr": str(jimc_id)},
                        headers={"Authorization": f"Bearer {current_token}", "Content-Type": "application/json"},
                        json=body,
                        timeout=REQUEST_TIMEOUT
                    )
                    
                    if response.status_code in (401, 403):
                        self._token_updated.clear()
                        self.token_expired.emit()
                        if not self._wait_for_token_update():
                            return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, True
                        
                        if self._cancel_requested:
                            return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, True
                        
                        continue
                    
                    response.raise_for_status()
                    json_data = response.json()
                    data_list = json_data.get("data", [])
                    
                    if not data_list:
                        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
                        
                    df_page = pd.json_normalize(data_list)
                    all_elements.append(df_page)
                    success = True
                    
                    if len(data_list) < page_size:
                        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
                    page += 1
                    
                except (requests.Timeout, requests.ConnectionError) as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(retry_delay)
                    else:
                        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
                except Exception as e:
                    log_error(f"Ошибка при загрузке элементов модели {jimc_id}:\n{traceback.format_exc()}")
                    return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False
        
        return pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame(), page, False

    def _get_properties_with_retry(self, site, jimc_id, eid_arr):
        if not eid_arr:
            return []
        
        max_retries = 5
        retry_delay = 3
        
        for attempt in range(max_retries):
            if self._cancel_requested:
                return []
            
            try:
                current_token = normalize_token(self.config["token"])
                url = f"{site}/api/element/jimcid-eidarr"
                body = {"jimcId": jimc_id, "eidArr": eid_arr}
                
                session = get_session()
                response = session.post(
                    url,
                    headers={"Authorization": f"Bearer {current_token}", "Content-Type": "application/json"},
                    json=body,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code in (401, 403):
                    with self._token_lock:
                        if not self._token_dialog_active:
                            self._token_dialog_active = True
                            self._token_updated.clear()
                            self.token_expired.emit()
                    
                    got_token = self._wait_for_token_update()
                    
                    with self._token_lock:
                        self._token_dialog_active = False
                    
                    if not got_token or self._cancel_requested:
                        return []
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return []
            except Exception as e:
                log_error(f"Ошибка при запросе свойств: {e}")
                return []
        
        return []

    def run(self):
        start_time = time.time()
        try:
            log_info("=" * 60)
            log_info("НАЧАЛО СИНХРОНИЗАЦИИ (Power BI)")
            log_info("=" * 60)
            
            sync_time = datetime.now()
            sync_time_str = sync_time.strftime("%Y-%m-%d %H:%M:%S")
            log_info(f"Время начала: {sync_time_str}")
            log_info(f"Выбрано проектов: {len(self.selected_ids)}")

            all_projects = []
            all_models = []
            all_elements = []
            all_properties = []
            
            load_properties = bool(self.selected_properties)
            if load_properties:
                log_info(f"Выбрано параметров для выгрузки: {len(self.selected_properties)}")

            project_name_map = dict(zip(self.projects_df["idProject"], self.projects_df["name"]))
            total_projects = len(self.selected_ids)
            total_models_overall = 0

            self.progress.emit(5, "Подсчёт моделей...")
            
            for proj_id in self.selected_ids:
                all_models_list = self.proj_models.get(proj_id, [])
                selected_model_ids = self.selected_models_per_project.get(proj_id)
                
                if selected_model_ids is not None:
                    models = [m for m in all_models_list if m.get("idModel") in selected_model_ids]
                else:
                    models = all_models_list
                    
                total_models_overall += len(models)

            log_info(f"Всего моделей для обработки: {total_models_overall}")

            if total_models_overall == 0:
                total_models_overall = 1

            processed_models = 0
            total_skipped_props = 0
            total_saved_props = 0
            
            for i, proj_id in enumerate(self.selected_ids, 1):
                proj_name = project_name_map.get(proj_id, "(неизвестный)")
                log_info(f"-- Проект {i}/{total_projects}: {proj_name} (ID={proj_id}) --")
                
                proj_row = self.projects_df[self.projects_df["idProject"] == proj_id].copy()
                if not proj_row.empty:
                    proj_row["last_updated"] = sync_time_str
                    all_projects.append(proj_row)

                all_models_list = self.proj_models.get(proj_id, [])
                selected_model_ids = self.selected_models_per_project.get(proj_id)
                
                if selected_model_ids is not None:
                    models = [m for m in all_models_list if m.get("idModel") in selected_model_ids]
                else:
                    models = all_models_list
                    
                if models:
                    df_models = pd.DataFrame(models)
                    df_models["last_updated"] = sync_time_str
                    all_models.append(df_models)

                    for j, mrow in enumerate(models, 1):
                        processed_models += 1
                        jimc_id = mrow["idModel"]
                        model_name = mrow.get("NameM", "(без названия)")
                        project_name = project_name_map.get(proj_id, "(неизвестный проект)")

                        progress_pct = 10 + (processed_models / total_models_overall) * 70
                        progress_msg = f"Проект {i}/{total_projects} — Модель {j}/{len(models)}"
                        self.progress.emit(int(progress_pct), progress_msg)

                        elem_count = 0
                        props_count = 0
                        try:
                            if pd.notna(jimc_id) and jimc_id != "":
                                elem_start = time.time()
                                df_elems, last_page, cancelled = self._get_elements_with_retry(
                                    self.config["site"], self.config["token"], jimc_id
                                )
                                
                                if cancelled:
                                    log_info("Синхронизация отменена пользователем")
                                    self.error.emit("Синхронизация отменена пользователем")
                                    return
                                
                                if not df_elems.empty:
                                    df_elems["idProject"] = proj_id
                                    df_elems["idModel"] = jimc_id
                                    df_elems["last_updated"] = sync_time_str
                                    elem_cols = ["idProject", "idModel", "id", "eid", "nid", "nuid", "elementName", "last_updated"]
                                    for col in elem_cols:
                                        if col not in df_elems.columns:
                                            df_elems[col] = ""
                                    df_elems = df_elems[elem_cols].rename(columns={
                                        "id": "el_id", "eid": "el_eid", "nid": "el_nid",
                                        "nuid": "el_nuid", "elementName": "el_elementName"
                                    })
                                    elem_count = len(df_elems)
                                    all_elements.append(df_elems)
                                    log_timing(f"API elements {model_name}", elem_start, elem_count)
                                    
                                    if load_properties and elem_count > 0:
                                        props_start = time.time()
                                        
                                        eid_list = df_elems["el_eid"].dropna().astype(int).tolist()
                                        element_ids = df_elems["el_id"].dropna().astype(int).tolist()
                                        eid_to_element_id = dict(zip(eid_list, element_ids))
                                        
                                        batch_size = 200
                                        max_workers = 8
                                        batches = [eid_list[bs:bs + batch_size] for bs in range(0, len(eid_list), batch_size)]
                                        total_batches = len(batches)
                                        
                                        completed_batches = 0
                                        props_lock = threading.Lock()
                                        skipped_props = 0
                                        
                                        def fetch_batch(batch_idx, batch_eids):
                                            if self._cancel_requested:
                                                return batch_idx, None, [], 0, 0
                                            try:
                                                props_data = self._get_properties_with_retry(
                                                    self.config["site"], jimc_id, batch_eids
                                                )
                                                results = []
                                                batch_skipped = 0
                                                batch_saved = 0
                                                if props_data:
                                                    for elem_data in props_data:
                                                        eid = elem_data.get("eid")
                                                        element_id = eid_to_element_id.get(eid)
                                                        if not element_id:
                                                            continue
                                                        
                                                        pvs = elem_data.get("pvs", [])
                                                        pvs_dict = {pv.get("c", ""): extract_property_value(pv) for pv in pvs}
                                                        
                                                        for prop_path in self.selected_properties:
                                                            prop_value = pvs_dict.get(prop_path, "")
                                                            
                                                            if not SAVE_EMPTY_PROPERTIES and is_empty_value(prop_value):
                                                                batch_skipped += 1
                                                                continue
                                                            
                                                            results.append({
                                                                "idElement": element_id,
                                                                "idModel": jimc_id,
                                                                "idProject": proj_id,
                                                                "propertyPath": prop_path,
                                                                "propertyValue": prop_value,
                                                                "last_updated": sync_time_str
                                                            })
                                                            batch_saved += 1
                                                return batch_idx, None, results, batch_skipped, batch_saved
                                            except Exception as e:
                                                return batch_idx, e, [], 0, 0
                                        
                                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                                            futures = {
                                                executor.submit(fetch_batch, idx, batch): idx 
                                                for idx, batch in enumerate(batches)
                                            }
                                            
                                            for future in as_completed(futures):
                                                if self._cancel_requested:
                                                    executor.shutdown(wait=False, cancel_futures=True)
                                                    self.error.emit("Синхронизация отменена пользователем")
                                                    return
                                                
                                                batch_idx, error, results, batch_skipped, batch_saved = future.result()
                                                completed_batches += 1
                                                
                                                if error:
                                                    log_error(f"Ошибка в батче {batch_idx}: {error}")
                                                
                                                if results:
                                                    with props_lock:
                                                        all_properties.extend(results)
                                                        props_count += len(results)
                                                        skipped_props += batch_skipped
                                        
                                        log_timing(f"API properties {model_name}", props_start, props_count)
                                        if not SAVE_EMPTY_PROPERTIES:
                                            log_info(f"Фильтрация пустых значений: сохранено {props_count}, пропущено {skipped_props}")
                                            total_skipped_props += skipped_props
                                        total_saved_props += props_count
                        except Exception as e:
                            log_error(f"Ошибка загрузки модели {jimc_id} ({model_name}):\n{traceback.format_exc()}")

                        log_info(f"{project_name} | {model_name} | {elem_count} элементов | {props_count} свойств")

            self.progress.emit(90, "Сохранение данных...")
            log_info(f"Сохранение данных в {self.format_type.upper()}...")
            
            df_projects = pd.concat(all_projects, ignore_index=True) if all_projects else pd.DataFrame()
            df_models = pd.concat(all_models, ignore_index=True) if all_models else pd.DataFrame()
            df_elements = pd.concat(all_elements, ignore_index=True) if all_elements else pd.DataFrame()
            df_properties = pd.DataFrame(all_properties) if all_properties else pd.DataFrame()

            log_info(f"Данные для сохранения: проектов={len(df_projects)}, моделей={len(df_models)}, элементов={len(df_elements)}, свойств={len(df_properties)}")

            t_save = time.time()
            save_all_to_files(df_projects, df_models, df_elements, df_properties, self.output_path, self.selected_properties, self.format_type, self.include_empty_rows)
            log_timing(f"{self.format_type.upper()} save", t_save, len(df_projects) + len(df_models) + len(df_elements) + len(df_properties))

            if not SAVE_EMPTY_PROPERTIES and total_saved_props > 0:
                log_info(f"ИТОГО свойств: сохранено {total_saved_props}, пропущено пустых {total_skipped_props}")

            log_info("Синхронизация завершена успешно!")
            elapsed = time.time() - start_time
            self.progress.emit(100, "Завершено!")
            self.finished.emit({
                "projects": len(df_projects),
                "models": len(df_models),
                "elements": len(df_elements),
                "properties": len(df_properties),
                "failed": [],
                "elapsed": elapsed,
                "output_path": self.output_path
            })
        except requests.Timeout:
            self.error.emit("Превышено время ожидания ответа от сервера.")
        except requests.ConnectionError:
            self.error.emit("Не удалось подключиться к серверу.")
        except Exception as e:
            logging.error(f"Критическая ошибка синхронизации: {e}\n{traceback.format_exc()}")
            self.error.emit(f"Сбой синхронизации:\n{str(e)}\n\nПодробности в {LOG_FILE}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app_icon_path = app_window_icon_path()
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    
    is_dark = False
    while True:
        mode_dialog = ModeSelectDialog(is_dark=is_dark)
        if mode_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        
        is_dark = mode_dialog.is_dark
        
        if mode_dialog.selected_mode == "powerbi":
            window = PowerBiExportWindow("csv")
        elif mode_dialog.selected_mode == "parquet":
            window = PowerBiExportWindow("parquet")
        elif mode_dialog.selected_mode == "sqlite":
            window = PowerBiExportWindow("sqlite")
        else:
            window = BimSyncWindow()
        
        if is_dark:
            window._toggle_theme(True)
            window.theme_toggle.setChecked(True)
        
        loop = QEventLoop()
        window.back_requested.connect(loop.quit)
        window.show()
        loop.exec()

        is_dark = window.is_dark_theme
        if getattr(window, "_return_to_mode_select", False):
            continue

        sys.exit(0)


if __name__ == "__main__":
    init_log()
    logging.basicConfig(level=logging.WARNING)
    main()
