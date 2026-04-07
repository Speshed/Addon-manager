# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import sys
import traceback
import tempfile
import ctypes
import platform
from ctypes import wintypes

# Qt bindings: PySide6 -> PyQt5 fallback
try:
    from PySide6 import QtWidgets, QtGui, QtCore  # type: ignore
    QT_API = "PySide6"
    Signal = QtCore.Signal
    Slot = QtCore.Slot
except Exception:
    from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore
    QT_API = "PyQt5"
    Signal = QtCore.pyqtSignal  # type: ignore
    Slot = QtCore.pyqtSlot      # type: ignore

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.theme_toggle import ThemeToggle, theme, is_dark_theme, create_back_button, go_to_main_menu, resolve_icon_path, load_saved_theme, enable_theme_sync
from shared.dialogs import show_warning

import pandas as pd
from collections import defaultdict, Counter

try:
    import requests
except Exception:
    requests = None

# ----- Style constants (Adapter Editor) -----
BG = "#FFFFFF"
FG = "#222222"
ACCENT = "#F7921E"
ACCENT_HOVER = "#FFA74B"
BORDER = "#dcdcdc"
HEADER_BG = "#f5f5f5"

# ---- resource helpers (as in AddUser) ----
def rsrc_path(*segments: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *segments)

def first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

ICON_DIR = rsrc_path("icon")
LOGO_LIGHT_PATH = rsrc_path("icon", "Manager-scaled.png")
LOGO_DARK_PATH = rsrc_path("icon", "Manager-scaled_white.png")
TITLEBAR_ICON_PATH = rsrc_path("icon", "logo.ico")
LOGO_PATH = LOGO_LIGHT_PATH if os.path.exists(LOGO_LIGHT_PATH) else (resolve_icon_path("logo", ICON_DIR) or "")

API_BASE_URL_DEFAULT = "http://localhost:5000"

def _runtime_api_base_url() -> str:
    return (os.environ.get("LARIX_API_BASE_URL") or API_BASE_URL_DEFAULT).rstrip("/")

# API helpers
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
        import json
        return json.loads(r.text)

def api_get_projects(base_url: str):
    url = f"{base_url.rstrip('/')}/api/project/projects"
    data = _api_get(url) or []
    return [{"id": x.get("id"), "title": x.get("title") or x.get("name") or f"ID {x.get('id')}"} for x in data]

def api_get_containers(base_url: str, project_id: int):
    url = f"{base_url.rstrip('/')}/api/imcContainer/getProjectImcContainers/{project_id}"
    data = _api_get(url) or []
    return [{"id": x.get("id"), "title": x.get("title") or f"ID {x.get('id')}"} for x in data]

def api_get_parameters(base_url: str, container_ids: list):
    url = f"{base_url.rstrip('/')}/api/imcParameterDefinition/imcParameterDefinitions"
    params = [("containerIds", cid) for cid in container_ids]
    data = _api_get(url, params=params) or []
    return data

# ----------------- Delegates for API dialog -----------------
class _ApiRowHoverDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, get_hover_row, parent=None):
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
            for role in (QtGui.QPalette.Text, QtGui.QPalette.WindowText, QtGui.QPalette.ButtonText):
                pal.setColor(QtGui.QPalette.Active, role, black)
                pal.setColor(QtGui.QPalette.Inactive, role, black)
            opt.palette = pal
        super().paint(painter, opt, index)


class _ApiModelListDelegate(QtWidgets.QStyledItemDelegate):
    _UNCHECKED_VALUE = 0
    _CHECKED_VALUE = 2

    def __init__(self, parent=None, *, icon_dir: str = ICON_DIR):
        super().__init__(parent)
        self.icon_dir = icon_dir
        self._cache = {}

    @classmethod
    def _state_value(cls, state):
        if state is None:
            return cls._UNCHECKED_VALUE
        return getattr(state, "value", state)

    def _get_pixmap(self, name: str, black: bool) -> QtGui.QPixmap:
        key = f"{name}_{'black' if black else 'normal'}"
        if key in self._cache:
            return self._cache[key]
        path = resolve_icon_path(name, self.icon_dir)
        if not path or not os.path.exists(path):
            return QtGui.QPixmap()
        pm = QtGui.QPixmap(path)
        if pm.isNull():
            return pm
        if black:
            tinted = QtGui.QPixmap(pm.size())
            tinted.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(tinted)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
            p.drawPixmap(0, 0, pm)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), QtGui.QColor("#000000"))
            p.end()
            pm = tinted
        self._cache[key] = pm
        return pm

    def paint(self, painter, option, index):
        app = QtWidgets.QApplication.instance()
        dark = is_dark_theme(app) if app else False
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
            bg_color = QtGui.QColor("#FFC37A" if is_selected else "#FFE3C2")
            row_rect = orig_rect.adjusted(2, 1, -2, -1)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(row_rect, 8, 8)
            text_color = QtGui.QColor("#000000")
        else:
            text_color = QtGui.QColor("#F5F5F5" if dark else "#222222")

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

    def editorEvent(self, event, model, option, index):
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


# ----------------- Dialog for API selection -----------------
class ApiSelectDialogMatrix(QtWidgets.QDialog):
    def __init__(self, parent, base_url: str):
        super().__init__(parent)
        self.setWindowTitle("Выбор из API")
        self.setModal(True)
        self.resize(960, 660)
        self._base_url = base_url
        self._projects = []
        self._containers = []
        self._params_all = []
        self._params_shown = []
        self._selected_data = None
        self._hover_row = -1
        
        self._build_ui()
        self._refresh_projects()
    
    def showEvent(self, e):
        try:
            _apply_native_dark_titlebar(self, True)
        finally:
            try:
                super().showEvent(e)
            except Exception:
                pass
    
    def event(self, ev):
        try:
            if ev and hasattr(ev, "type") and ev.type() in (QtCore.QEvent.PaletteChange, QtCore.QEvent.StyleChange):
                _apply_native_dark_titlebar(self, True)
        except Exception:
            pass
        return super().event(ev)
    
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)
        
        row0 = QtWidgets.QHBoxLayout()
        root.addLayout(row0)
        self.btn_proj = QtWidgets.QPushButton("Обновить проекты")
        row0.addWidget(self.btn_proj)
        row0.addStretch(1)
        
        row1 = QtWidgets.QHBoxLayout()
        root.addLayout(row1)
        row1.addWidget(QtWidgets.QLabel("Проект:"))
        self.cmb_projects = QtWidgets.QComboBox()
        row1.addWidget(self.cmb_projects, 1)
        
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(split, 1)
        
        left_box = QtWidgets.QGroupBox("Модели (IMC)")
        left_l = QtWidgets.QVBoxLayout(left_box)
        self.lst_cont = QtWidgets.QListWidget()
        self.lst_cont.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lst_cont.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lst_cont.setStyleSheet("border: none;")
        self.lst_cont.setItemDelegate(_ApiModelListDelegate(self.lst_cont, icon_dir=ICON_DIR))
        self.lst_cont.setMouseTracking(True)
        left_l.addWidget(self.lst_cont, 1)
        split.addWidget(left_box)
        left_box.setMinimumWidth(260)
        
        mid = QtWidgets.QWidget()
        mid_l = QtWidgets.QVBoxLayout(mid)
        mid_l.setContentsMargins(6, 6, 6, 6)
        self.btn_load_params = QtWidgets.QPushButton("Загрузить параметры")
        mid_l.addWidget(self.btn_load_params)
        mid_l.addStretch(1)
        split.addWidget(mid)
        mid.setMaximumWidth(220)
        
        right_sec = Section("Параметры", self)
        g = right_sec.frame_l
        g.setRowStretch(0, 0)
        g.setRowStretch(1, 1)
        
        filter_row = QtWidgets.QHBoxLayout()
        g.addLayout(filter_row, 0, 0, 1, 1)
        filter_row.addWidget(QtWidgets.QLabel("Фильтр по наименованию:"))
        self.ed_filter = QtWidgets.QLineEdit()
        filter_row.addWidget(self.ed_filter, 1)
        self.btn_find = QtWidgets.QPushButton("Найти")
        filter_row.addWidget(self.btn_find)
        
        self.tbl_params = QtWidgets.QTableWidget(0, 2)
        self.tbl_params.setObjectName("apiParamsTable")
        self.tbl_params.setShowGrid(False)
        self.tbl_params.setFocusPolicy(QtCore.Qt.NoFocus)
        self.tbl_params.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tbl_params.setStyleSheet("border: none;")
        self.tbl_params.verticalHeader().setVisible(False)
        self.tbl_params.setHorizontalHeaderLabels(["Наименование", "Код"])
        
        self.tbl_params.setMouseTracking(True)
        self.tbl_params.viewport().setMouseTracking(True)
        self.tbl_params.viewport().installEventFilter(self)
        self.tbl_params.setItemDelegate(_ApiRowHoverDelegate(lambda: self._hover_row, self.tbl_params))
        
        header = self.tbl_params.horizontalHeader()
        header.setSectionsClickable(True)
        header.setHighlightSections(False)
        header.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        try:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        except Exception:
            pass
        
        self.tbl_params.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_params.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        g.addWidget(self.tbl_params, 1, 0, 1, 1)
        
        split.addWidget(right_sec)
        
        bottom = QtWidgets.QHBoxLayout()
        root.addLayout(bottom)
        bottom.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_select = QtWidgets.QPushButton("Выбрать")
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.btn_select)
        
        self.btn_proj.clicked.connect(self._refresh_projects)
        self.cmb_projects.currentIndexChanged.connect(self._on_project_changed)
        self.btn_load_params.clicked.connect(self._load_parameters)
        self.lst_cont.itemDoubleClicked.connect(self._on_container_double_clicked)
        self.lst_cont.itemChanged.connect(self._on_model_item_changed)
        self.ed_filter.textChanged.connect(self._apply_filter)
        self.btn_find.clicked.connect(self._apply_filter)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_select.clicked.connect(self._on_select)
        self.tbl_params.itemDoubleClicked.connect(self._on_select)
    
    def eventFilter(self, obj, event):
        if obj is self.tbl_params.viewport():
            t = event.type()
            if t == QtCore.QEvent.MouseMove:
                mi = self.tbl_params.indexAt(event.pos() if hasattr(event, "pos") else event.position().toPoint())
                row = int(mi.row()) if mi.isValid() else -1
                if row != self._hover_row:
                    self._hover_row = row
                    self.tbl_params.viewport().update()
            elif t in (QtCore.QEvent.Leave, QtCore.QEvent.HoverLeave):
                if self._hover_row != -1:
                    self._hover_row = -1
                    self.tbl_params.viewport().update()
        return super().eventFilter(obj, event)
    
    def _refresh_projects(self):
        try:
            self._projects = api_get_projects(self._base_url) or []
            self.cmb_projects.clear()
            for p in self._projects:
                self.cmb_projects.addItem(p.get("title", ""))
            if self._projects:
                self._refresh_containers()
        except Exception as e:
            show_warning(self, f"Не удалось загрузить проекты:\n{e}", "API")
    
    def _on_project_changed(self, index):
        if index >= 0:
            self._refresh_containers()
    
    def _refresh_containers(self):
        idx = self.cmb_projects.currentIndex()
        if idx < 0:
            return
        pid = self._projects[idx].get("id")
        try:
            self._containers = api_get_containers(self._base_url, pid) or []
            self.lst_cont.blockSignals(True)
            self.lst_cont.clear()
            item_all = QtWidgets.QListWidgetItem("Все модели")
            item_all.setFlags(item_all.flags() | QtCore.Qt.ItemIsUserCheckable)
            item_all.setCheckState(QtCore.Qt.Unchecked)
            self.lst_cont.addItem(item_all)
            for c in self._containers:
                item = QtWidgets.QListWidgetItem(c.get("title", ""))
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.Unchecked)
                self.lst_cont.addItem(item)
            self.lst_cont.blockSignals(False)
        except Exception as e:
            show_warning(self, f"Не удалось загрузить модели:\n{e}", "API")
    
    def _on_model_item_changed(self, item):
        item_all = self.lst_cont.item(0)
        if item is item_all:
            state = item.checkState()
            self.lst_cont.blockSignals(True)
            for i in range(1, self.lst_cont.count()):
                self.lst_cont.item(i).setCheckState(state)
            self.lst_cont.blockSignals(False)
        else:
            all_checked = all(
                self.lst_cont.item(i).checkState() == QtCore.Qt.Checked
                for i in range(1, self.lst_cont.count())
            )
            self.lst_cont.blockSignals(True)
            item_all.setCheckState(QtCore.Qt.Checked if all_checked else QtCore.Qt.Unchecked)
            self.lst_cont.blockSignals(False)
    
    def _on_container_double_clicked(self, item):
        idx = self.lst_cont.row(item)
        if idx <= 0:
            return
        self._load_parameters_for_indices([idx - 1])
    
    def _load_parameters(self):
        checked_indices = []
        for i in range(1, self.lst_cont.count()):
            item = self.lst_cont.item(i)
            if item and item.checkState() == QtCore.Qt.Checked:
                checked_indices.append(i - 1)
        
        if not checked_indices:
            selected_rows = sorted({
                idx.row() - 1
                for idx in self.lst_cont.selectedIndexes()
                if idx.isValid() and idx.row() > 0
            })
            if not selected_rows:
                show_warning(self, "Выберите одну или несколько моделей.", "API")
                return
            checked_indices = selected_rows
        
        self._load_parameters_for_indices(checked_indices)
    
    def _load_parameters_for_indices(self, indices):
        if not indices:
            return
        ids = [self._containers[i].get("id") for i in indices]
        try:
            params = api_get_parameters(self._base_url, ids) or []
            combined = {}
            for p in params:
                code = (p.get("code") or "").lower()
                if code and code not in combined:
                    combined[code] = p
            self._params_all = sorted(combined.values(), key=lambda x: (x.get("name") or "").lower())
            self._apply_filter()
        except Exception as e:
            show_warning(self, f"Не удалось загрузить параметры:\n{e}", "API")
    
    def _apply_filter(self):
        text = (self.ed_filter.text() or "").lower()
        if text:
            filtered = [
                p for p in self._params_all
                if text in (p.get("name") or "").lower() or text in (p.get("code") or "").lower()
            ]
        else:
            filtered = self._params_all[:]
        self._fill_params(filtered)
    
    def _fill_params(self, params):
        self._params_shown = params[:]
        self.tbl_params.setRowCount(0)
        for p in params:
            row = self.tbl_params.rowCount()
            self.tbl_params.insertRow(row)
            name = p.get("name") or p.get("title") or ""
            code = p.get("code") or ""
            it0 = QtWidgets.QTableWidgetItem(name)
            it0.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            it1 = QtWidgets.QTableWidgetItem(code)
            it1.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            self.tbl_params.setItem(row, 0, it0)
            self.tbl_params.setItem(row, 1, it1)
    
    def _on_select(self):
        row = self.tbl_params.currentRow()
        if row < 0 or row >= len(self._params_shown):
            show_warning(self, "Выберите параметр из списка.", "API")
            return
        p = self._params_shown[row]
        self._selected_data = {
            "name": p.get("name") or p.get("title") or "",
            "code": p.get("code") or ""
        }
        self.accept()
    
    def get_selected_data(self):
        return self._selected_data

# icons and arrow resources
ARROW_DOWN_PATH = resolve_icon_path("arrow_down", ICON_DIR) or ""
ARROW_UP_PATH = resolve_icon_path("arrow_up", ICON_DIR) or ""
ARROW_LEFT_PATH = resolve_icon_path("arrow_left", ICON_DIR) or ""
ARROW_RIGHT_PATH = resolve_icon_path("arrow_right", ICON_DIR) or ""
SUN_ICON_CANDIDATES = [resolve_icon_path("sun", ICON_DIR) or ""]
MOON_ICON_CANDIDATES = [resolve_icon_path("moon", ICON_DIR) or ""]
_OPEN_RESULT_DIALOGS: set[QtWidgets.QDialog] = set()

# Native Windows dark title bar helper (best-effort; safe on non-Windows)
def _apply_native_dark_titlebar(widget: QtWidgets.QWidget, dark: bool) -> None:
    try:
        if sys.platform != "win32" or platform.system().lower() != "windows":
            return
        if widget is None or not isinstance(widget, QtWidgets.QWidget):
            return
        if not widget.isWindow():
            return
        hwnd = int(widget.winId())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36

        def _set_attr_bool(attr: int, value: bool) -> bool:
            v = ctypes.c_int(1 if value else 0)
            hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), ctypes.c_int(attr), ctypes.byref(v), ctypes.sizeof(v)
            )
            return int(hr) == 0

        def _colorref_from_hex(hex_color: str) -> wintypes.DWORD:
            s = (hex_color or "").lstrip('#')
            try:
                r = int(s[0:2], 16); g = int(s[2:4], 16); b = int(s[4:6], 16)
            except Exception:
                r, g, b = (255, 255, 255) if dark else (0, 0, 0)
            return wintypes.DWORD((r) | (g << 8) | (b << 16))

        ok = _set_attr_bool(DWMWA_USE_IMMERSIVE_DARK_MODE, dark)
        if not ok:
            _set_attr_bool(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, dark)

        try:
            # Explicit black title bar + white text in dark mode, fallback to widget colors in light
            header_bg = "#000000" if dark else getattr(widget, "_HEADER_BG", "#f5f5f5")
            fg_col = "#FFFFFF" if dark else getattr(widget, "_FG", "#222222")
            border_col = "#000000" if dark else getattr(widget, "_BORDER", "#dcdcdc")
            caption = _colorref_from_hex(header_bg)
            text = _colorref_from_hex(fg_col)
            border = _colorref_from_hex(border_col)
            for attr, val in (
                (DWMWA_CAPTION_COLOR, caption),
                (DWMWA_TEXT_COLOR, text),
                (DWMWA_BORDER_COLOR, border),
            ):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd), ctypes.c_int(attr), ctypes.byref(val), ctypes.sizeof(val)
                )
        except Exception:
            pass
    except Exception:
        pass

class _ResultDialog(QtWidgets.QDialog):
    def __init__(self, parent, text: str, title: str, icon_name: str):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(title)
        self.setMinimumWidth(320)
        flags = self.windowFlags()
        flags &= ~QtCore.Qt.WindowType.WindowContextHelpButtonHint
        flags |= QtCore.Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)

        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.setSpacing(16)
        vlayout.setContentsMargins(20, 20, 20, 20)

        hlayout = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel()
        app = QtWidgets.QApplication.instance()
        icon_path = resolve_icon_path(icon_name, ICON_DIR, app=app)
        if icon_path and os.path.exists(icon_path):
            pm = QtGui.QPixmap(icon_path)
            if not pm.isNull():
                icon_label.setPixmap(pm.scaled(48, 48, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        if icon_label.pixmap() is None or icon_label.pixmap().isNull():
            style = QtWidgets.QApplication.style()
            fallback = QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation
            if icon_name == "error":
                fallback = QtWidgets.QStyle.StandardPixmap.SP_MessageBoxCritical
            icon_label.setPixmap(style.standardIcon(fallback).pixmap(48, 48))
        hlayout.addWidget(icon_label, 0, QtCore.Qt.AlignmentFlag.AlignTop)

        msg_label = QtWidgets.QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        msg_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        hlayout.addWidget(msg_label, 1)
        vlayout.addLayout(hlayout)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok, parent=self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        ok_button = btn_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.clicked.connect(self.accept)
            ok_button.setDefault(True)
            ok_button.setAutoDefault(True)
        vlayout.addWidget(btn_box, 0, QtCore.Qt.AlignmentFlag.AlignRight)

    def closeEvent(self, event):
        event.accept()
        super().closeEvent(event)


def _show_result_dialog(parent, text: str, title: str, icon_name: str):
    print(f"[MATRIX] _show_result_dialog called: parent={parent}, title={title}", file=sys.stderr, flush=True)
    dlg = _ResultDialog(parent, text, title, icon_name)
    _OPEN_RESULT_DIALOGS.add(dlg)
    dlg.finished.connect(lambda *_args, dialog=dlg: _OPEN_RESULT_DIALOGS.discard(dialog))
    dlg.open()
    dlg.raise_()
    dlg.activateWindow()


def _popup_error(parent, text: str, title: str = "Ошибка"):
    print(f"[MATRIX] _popup_error called: parent={parent}, title={title}", file=sys.stderr, flush=True)
    _show_result_dialog(parent, text, title, "error")


def _popup_info(parent, text: str, title: str = "Информация"):
    print(f"[MATRIX] _popup_info called: parent={parent}, title={title}", file=sys.stderr, flush=True)
    _show_result_dialog(parent, text, title, "alert")


def _get_visible_parent(widget_or_window):
    print(f"[MATRIX] _get_visible_parent called: widget={widget_or_window}", file=sys.stderr, flush=True)
    
    if widget_or_window is None:
        app = QtWidgets.QApplication.instance()
        result = app.activeWindow() if app else None
        print(f"[MATRIX] _get_visible_parent returning (null case): {result}", file=sys.stderr, flush=True)
        return result
    
    # First try to find visible window through widget hierarchy
    w = widget_or_window
    while w is not None:
        parent = w.parent()
        if parent is None:
            break
        w = parent
    
    # Check if top-level parent is visible
    if w is not None and w.isWindow() and w.isVisible():
        print(f"[MATRIX] _get_visible_parent returning (visible parent): {w}", file=sys.stderr, flush=True)
        return w
    
    # Fallback: find any visible top-level window
    app = QtWidgets.QApplication.instance()
    if app:
        # Try activeWindow first
        active = app.activeWindow()
        if active and active.isVisible():
            print(f"[MATRIX] _get_visible_parent returning (activeWindow): {active}", file=sys.stderr, flush=True)
            return active
        
        # Find first visible top-level window
        for tlw in app.topLevelWidgets():
            if tlw.isWindow() and tlw.isVisible() and tlw is not widget_or_window:
                print(f"[MATRIX] _get_visible_parent returning (topLevelWidget): {tlw}", file=sys.stderr, flush=True)
                return tlw
    
    print(f"[MATRIX] _get_visible_parent returning (fallback): {widget_or_window}", file=sys.stderr, flush=True)
    return widget_or_window


# -----------------------------
# XML ШАБЛОНЫ
# -----------------------------
XML_TEMPLATE = '''<?xml version="1.0"?>
<ExportProfilesCollection xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Profiles>
    <BaseExportProfile xsi:type="CollisionsExportProfile">
      <Id>0</Id>
      <Title>{title}</Title>
      <ProfileItems>
{profile_items}
      </ProfileItems>
    </BaseExportProfile>
  </Profiles>
</ExportProfilesCollection>'''

FOLDER_TEMPLATE = '''        <BaseExportProfileItem xsi:type="CollisionsExportProfileItem">
          <Id>{folder_id}</Id>
          <ParentId xsi:nil="true" />
          <Title>{folder_title}</Title>
          <IsFolder>true</IsFolder>
          <ParentCondition1Id xsi:nil="true" />
          <ParentCondition2Id xsi:nil="true" />
          <ParentElementGuids1Id xsi:nil="true" />
          <ParentElementGuids2Id xsi:nil="true" />
          <ItemParams>{{"$type":"EstimoCore.Entities.CollisionsValidating.ValidationTypes.IntersectionValidationData, MainEstimoCore.NetFramework","Admission":{{"$type":"EstimoCore.Entities.CollisionsValidating.Admissions.LinearAdmission, MainEstimoCore.NetFramework","Value":0.0}}}}</ItemParams>
        </BaseExportProfileItem>'''

ITEM_TEMPLATE = '''        <BaseExportProfileItem xsi:type="CollisionsExportProfileItem">
          <Id>{id}</Id>
          <ParentId>{parent_id}</ParentId>
          <Title>{title}</Title>
          <IsFolder>false</IsFolder>
          <ConditionBlock1 Type="Block" LogicalOperator="And" IsNegative="false" IsEnabled="true">
            <Signal>
              <Messages />
            </Signal>
            <Condition FieldName="" FieldIsNumeric="false" Operator="Equal" Value="" TextCaseSensitive="false" TextSpaceSensitive="true" IsUndefinedFieldName="false">
              <Signal>
                <Messages>
                  <SignalMessage>
                    <Level>Info</Level>
                    <Text>Имя не указано</Text>
                  </SignalMessage>
                </Messages>
              </Signal>
            </Condition>
            <ConditionsBlocks>
{condition_block1_items}
            </ConditionsBlocks>
          </ConditionBlock1>
          <ConditionBlock2 Type="Block" LogicalOperator="And" IsNegative="false" IsEnabled="true">
            <Signal>
              <Messages />
            </Signal>
            <Condition FieldName="" FieldIsNumeric="false" Operator="Equal" Value="" TextCaseSensitive="false" TextSpaceSensitive="true" IsUndefinedFieldName="false">
              <Signal>
                <Messages>
                  <SignalMessage>
                    <Level>Info</Level>
                    <Text>Имя не указано</Text>
                  </SignalMessage>
                </Messages>
              </Signal>
            </Condition>
            <ConditionsBlocks>
{condition_block2_items}
            </ConditionsBlocks>
          </ConditionBlock2>
          <ParentCondition1Id xsi:nil="true" />
          <ParentCondition2Id xsi:nil="true" />
          <ParentElementGuids1Id xsi:nil="true" />
          <ParentElementGuids2Id xsi:nil="true" />
          <ItemParams>{{"$type":"EstimoCore.Entities.CollisionsValidating.ValidationTypes.IntersectionValidationData, MainEstimoCore.NetFramework","Admission":{{"$type":"EstimoCore.Entities.CollisionsValidating.Admissions.LinearAdmission, MainEstimoCore.NetFramework","Value":{admission_value}}}}}</ItemParams>
        </BaseExportProfileItem>'''

ITEM_TEMPLATE_DUPLICATION = '''        <BaseExportProfileItem xsi:type="CollisionsExportProfileItem">
          <Id>{id}</Id>
          <ParentId>{parent_id}</ParentId>
          <Title>{title}</Title>
          <IsFolder>false</IsFolder>
          <ConditionBlock1 Type="Block" LogicalOperator="And" IsNegative="false" IsEnabled="true">
            <Signal>
              <Messages />
            </Signal>
            <Condition FieldName="" FieldIsNumeric="false" Operator="Equal" Value="" TextCaseSensitive="false" TextSpaceSensitive="true" IsUndefinedFieldName="false">
              <Signal>
                <Messages>
                  <SignalMessage>
                    <Level>Info</Level>
                    <Text>Имя не указано</Text>
                  </SignalMessage>
                </Messages>
              </Signal>
            </Condition>
            <ConditionsBlocks>
{condition_block1_items}
            </ConditionsBlocks>
          </ConditionBlock1>
          <ConditionBlock2 Type="Block" LogicalOperator="And" IsNegative="false" IsEnabled="true">
            <Signal>
              <Messages />
            </Signal>
            <Condition FieldName="" FieldIsNumeric="false" Operator="Equal" Value="" TextCaseSensitive="false" TextSpaceSensitive="true" IsUndefinedFieldName="false">
              <Signal>
                <Messages>
                  <SignalMessage>
                    <Level>Info</Level>
                    <Text>Имя не указано</Text>
                  </SignalMessage>
                </Messages>
              </Signal>
            </Condition>
            <ConditionsBlocks>
{condition_block2_items}
            </ConditionsBlocks>
          </ConditionBlock2>
          <ParentCondition1Id xsi:nil="true" />
          <ParentCondition2Id xsi:nil="true" />
          <ParentElementGuids1Id xsi:nil="true" />
          <ParentElementGuids2Id xsi:nil="true" />
          <ItemParams>{{"$type":"EstimoCore.Entities.CollisionsValidating.ValidationTypes.DuplicationValidationData, MainEstimoCore.NetFramework","Admission":{{"$type":"EstimoCore.Entities.CollisionsValidating.Admissions.LinearAdmission, MainEstimoCore.NetFramework","Value":{admission_value}}}}}</ItemParams>
        </BaseExportProfileItem>'''

# -----------------------------
# Помощники
# -----------------------------
def normalize_name(name):
    if pd.isna(name):
        return ""
    name = str(name).strip()
    name = name.replace('Кр_', 'КР_').replace('кР_', 'КР_')
    return name

def list_sheets(xlsx_path: str) -> list[str]:
    try:
        x = pd.ExcelFile(xlsx_path)
        return list(x.sheet_names)
    except Exception:
        return []

def xml_attr_escape(s: str) -> str:
    return (s.replace('&', '&amp;')
             .replace('"', '&quot;')
             .replace('<', '&lt;')
             .replace('>', '&gt;'))


def split_filter_values(raw_value) -> list[str]:
    if raw_value is None or pd.isna(raw_value):
        return []
    text = str(raw_value).strip()
    if not text or text.lower() == "nan":
        return []
    text = text.replace(";", ",").replace("\n", ",")
    values: list[str] = []
    seen: set[str] = set()
    for item in text.split(","):
        value = normalize_name(item)
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return values


_FILTER_CONDITION_SINGLE_TEMPLATE = '''              <ConditionsBlock Type="Single" LogicalOperator="And" IsNegative="false" IsEnabled="true">
                <Signal>
                  <Messages />
                </Signal>
                <Condition FieldName="{param_field}" FieldIsNumeric="false" Operator="Equal" Value="{value}" TextCaseSensitive="false" TextSpaceSensitive="false" IsUndefinedFieldName="false">
                  <Signal>
                    <Messages />
                  </Signal>
                </Condition>
                <ConditionsBlocks />
              </ConditionsBlock>'''


_FILTER_CONDITION_GROUP_TEMPLATE = '''              <ConditionsBlock Type="Block" LogicalOperator="Or" IsNegative="false" IsEnabled="true">
                <Signal>
                  <Messages />
                </Signal>
                <Condition FieldName="" FieldIsNumeric="false" Operator="Equal" Value="" TextCaseSensitive="false" TextSpaceSensitive="false" IsUndefinedFieldName="false">
                  <Signal>
                    <Messages />
                  </Signal>
                </Condition>
                <ConditionsBlocks>
{items}
                </ConditionsBlocks>
              </ConditionsBlock>'''


def build_filter_condition_blocks_xml(param_field: str, raw_value) -> str:
    field = str(param_field or "").strip()
    values = split_filter_values(raw_value)
    if not field or not values:
        return ""

    field_xml = xml_attr_escape(field)
    items = [
        _FILTER_CONDITION_SINGLE_TEMPLATE.format(
            param_field=field_xml,
            value=xml_attr_escape(value),
        )
        for value in values
    ]
    if len(items) == 1:
        return items[0]
    return _FILTER_CONDITION_GROUP_TEMPLATE.format(items="\n".join(items))

# -----------------------------
# Worker: генерация XML в отдельном потоке
# -----------------------------
class GeneratorWorker(QtCore.QObject):
    log = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, nabory_path: str, matrix_path: str, out_path: str,
                 sheet_nabory: str, sheet_matrix: str,
                 map_a: float, map_b: float, map_c: float,
                 profile_title: str, param_field: str,
                 build_filters: bool):
        super().__init__()
        self.nabory_path = nabory_path
        self.matrix_path = matrix_path
        self.out_path = out_path
        self.sheet_nabory = sheet_nabory
        self.sheet_matrix = sheet_matrix
        self.map_a = map_a
        self.map_b = map_b
        self.map_c = map_c
        self.profile_title = profile_title or "Матрица"
        self.param_field = param_field or "Категория:\\"
        self.build_filters = bool(build_filters)

    def letter_to_value(self, letter: str) -> float:
        letter = str(letter).strip().upper()
        mapping = {"A": self.map_a, "B": self.map_b, "C": self.map_c}
        return mapping.get(letter, self.map_a)

    def run(self):
        try:
            category_map = {}
            prefix_map = {}

            self.log.emit("Чтение матрицы...")
            df_matrix = pd.read_excel(self.matrix_path, sheet_name=self.sheet_matrix, header=None)

            if self.build_filters and self.nabory_path:
                self.log.emit("Чтение файла наборов...")
                df_nabory = pd.read_excel(self.nabory_path, sheet_name=self.sheet_nabory)
                if 'Имя набора' not in df_nabory.columns:
                    raise ValueError("В файле наборов не найден столбец 'Имя набора'")
                if 'Описание' not in df_nabory.columns:
                    df_nabory['Описание'] = df_nabory['Имя набора']

                df_nabory.dropna(subset=['Имя набора'], inplace=True)
                for _, row in df_nabory.iterrows():
                    name_raw = row['Имя набора']
                    if pd.isna(name_raw):
                        continue
                    name = normalize_name(name_raw)
                    if name.startswith('Раздел'):
                        continue
                    desc = normalize_name(row.get('Описание', name))
                    prefix = name.split('_')[0] if '_' in name else 'OTHER'
                    category_map[name] = desc
                    prefix_map[name] = prefix

                self.log.emit(f"Найдено наборов: {len(category_map)}")
            else:
                self.log.emit("Файл наборов не выбран: использую названия из матрицы")

            # Helpers to format numeric codes like 1.01
            def fmt_code(v):
                if pd.isna(v):
                    return ""
                try:
                    f = float(str(v).replace(',', '.'))
                    return f"{f:.2f}"
                except Exception:
                    s = str(v).strip()
                    return s

            # Column names and their codes from rows 1 (names) and 2 (codes)
            col_names = []
            col_codes = []
            for j in range(2, len(df_matrix.columns)):
                col_names.append(normalize_name(df_matrix.iloc[1, j]))
                col_codes.append(fmt_code(df_matrix.iloc[2, j]))

            # Row names and their codes from columns 1 (names) and 0 (codes)
            row_names = []
            row_codes = []
            data_rows = []
            for i in range(3, len(df_matrix)):
                row_names.append(normalize_name(df_matrix.iloc[i, 1]))
                row_codes.append(fmt_code(df_matrix.iloc[i, 0]))
                data_rows.append([df_matrix.iloc[i, j] for j in range(2, len(df_matrix.columns))])

            # Build lookup maps name -> code (prefer non-empty)
            row_code_map = {}
            for n, c in zip(row_names, row_codes):
                if n and c and n not in row_code_map:
                    row_code_map[n] = c
            col_code_map = {}
            for n, c in zip(col_names, col_codes):
                if n and c and n not in col_code_map:
                    col_code_map[n] = c

            # Collect matrix pairs
            pairs = []  # (set1, set2, letter)
            for i, set1 in enumerate(row_names):
                if not set1:
                    continue
                for j, set2 in enumerate(col_names):
                    if not set2 or j >= len(data_rows[i]):
                        continue
                    cell_value = data_rows[i][j]
                    if pd.notna(cell_value) and str(cell_value).strip() != '':
                        pairs.append((set1, set2, str(cell_value).strip()))

            self.log.emit(f"Всего коллизий в матрице: {len(pairs)}")

            all_sets = set()
            all_sets.update([n for n in row_names if n])
            all_sets.update([n for n in col_names if n])

            if not category_map:
                for name in sorted(all_sets):
                    prefix = name.split('_')[0] if '_' in name else 'OTHER'
                    category_map[name] = name
                    prefix_map[name] = prefix
            else:
                missing_sets = []
                for name in sorted(all_sets):
                    prefix_map.setdefault(name, name.split('_')[0] if '_' in name else 'OTHER')
                    if name not in category_map:
                        missing_sets.append(name)
                if missing_sets:
                    self.log.emit(
                        "В файле наборов не найдены описания для "
                        f"{len(missing_sets)} наборов из матрицы. Для них проверки будут созданы без фильтров."
                    )

            # Group by prefixes from 'Наборы' (без номеров)
            groups = defaultdict(list)
            for name in sorted(all_sets):
                groups[prefix_map[name]].append(name)

            prefixes = sorted(groups.keys())

            # Присвоим каждому префиксу «мажорный» номер (из кода 1.01 -> 1). Берём самый частый, при равенстве — минимальный.
            prefix_majors = {}
            tmp = {}
            for name in sorted(all_sets):
                pref = prefix_map[name]
                code_val = row_code_map.get(name) or col_code_map.get(name) or ""
                major = None
                if code_val:
                    try:
                        major = int(str(code_val).split('.')[0])
                    except Exception:
                        major = None
                if major is not None:
                    tmp.setdefault(pref, []).append(major)
            for pref, lst in tmp.items():
                cnt = Counter(lst)
                if cnt:
                    max_freq = max(cnt.values())
                    candidates = [v for v, f in cnt.items() if f == max_freq]
                    prefix_majors[pref] = min(candidates)

            def format_prefix(pref: str) -> str:
                m = prefix_majors.get(pref)
                return f"{m:02d}_{pref}" if isinstance(m, int) else pref

            folder_counter = 11300
            item_counter = 6445
            profile_items = []

            def display_name(raw_name: str) -> str:
                code_val = row_code_map.get(raw_name) or col_code_map.get(raw_name) or ""
                return (code_val + "_" if code_val else "") + raw_name

            def parse_cell_value(cell_val: str) -> list[str]:
                parts = [p.strip().upper() for p in cell_val.replace('\\', '/').split('/')]
                return [p for p in parts if p]

            def get_validation_type(letter: str) -> str:
                letter = letter.strip().upper()
                if letter == 'D':
                    return 'duplication'
                elif letter in ('A', 'B', 'C'):
                    return 'intersection'
                return 'intersection'

            for i in range(len(prefixes)):
                for j in range(i, len(prefixes)):
                    p1, p2 = prefixes[i], prefixes[j]

                    items_intersection = []
                    items_duplication = []
                    added_pairs_intersection = set()
                    added_pairs_duplication = set()

                    for set1 in groups[p1]:
                        for set2 in groups[p2]:
                            found_letters = None
                            for a, b, letter in pairs:
                                if (set1 == a and set2 == b) or (set1 == b and set2 == a):
                                    found_letters = letter
                                    break
                            if not found_letters:
                                continue

                            letters = parse_cell_value(found_letters)

                            for letter in letters:
                                validation_type = get_validation_type(letter)

                                if validation_type == 'intersection':
                                    key = tuple(sorted([set1, set2])) + ('intersection',)
                                    if key in added_pairs_intersection:
                                        continue
                                    added_pairs_intersection.add(key)

                                    title = f"{display_name(set1)} ~ {display_name(set2)}"
                                    condition_block1_items = ""
                                    condition_block2_items = ""
                                    if self.build_filters:
                                        condition_block1_items = build_filter_condition_blocks_xml(
                                            self.param_field,
                                            category_map.get(set1),
                                        )
                                        condition_block2_items = build_filter_condition_blocks_xml(
                                            self.param_field,
                                            category_map.get(set2),
                                        )
                                    admission_value = self.letter_to_value(letter)

                                    item_xml = ITEM_TEMPLATE.format(
                                        id=item_counter,
                                        parent_id=folder_counter,
                                        title=title,
                                        condition_block1_items=condition_block1_items,
                                        condition_block2_items=condition_block2_items,
                                        admission_value=admission_value,
                                    )
                                    items_intersection.append(item_xml)
                                    item_counter += 1

                                elif validation_type == 'duplication':
                                    key = tuple(sorted([set1, set2])) + ('duplication',)
                                    if key in added_pairs_duplication:
                                        continue
                                    added_pairs_duplication.add(key)

                                    title = f"{display_name(set1)} ~ {display_name(set2)}"
                                    condition_block1_items = ""
                                    condition_block2_items = ""
                                    if self.build_filters:
                                        condition_block1_items = build_filter_condition_blocks_xml(
                                            self.param_field,
                                            category_map.get(set1),
                                        )
                                        condition_block2_items = build_filter_condition_blocks_xml(
                                            self.param_field,
                                            category_map.get(set2),
                                        )
                                    admission_value = 0.0

                                    item_xml = ITEM_TEMPLATE_DUPLICATION.format(
                                        id=item_counter,
                                        parent_id=folder_counter + 1,
                                        title=title,
                                        condition_block1_items=condition_block1_items,
                                        condition_block2_items=condition_block2_items,
                                        admission_value=admission_value,
                                    )
                                    items_duplication.append(item_xml)
                                    item_counter += 1

                    if items_intersection:
                        folder_title_intersection = f"{format_prefix(p1)} ~ {format_prefix(p2)} / Пересечение"
                        folder_xml = FOLDER_TEMPLATE.format(
                            folder_id=folder_counter,
                            folder_title=folder_title_intersection
                        )
                        profile_items.append(folder_xml)
                        profile_items.extend(items_intersection)
                        folder_counter += 1

                    if items_duplication:
                        folder_title_duplication = f"{format_prefix(p1)} ~ {format_prefix(p2)} / Дублирование"
                        folder_xml = FOLDER_TEMPLATE.format(
                            folder_id=folder_counter,
                            folder_title=folder_title_duplication
                        )
                        profile_items.append(folder_xml)
                        profile_items.extend(items_duplication)
                        folder_counter += 1

            full_xml = XML_TEMPLATE.format(
                profile_items="\n".join(profile_items),
                title=self.profile_title
            )

            out_dir = os.path.dirname(self.out_path) or os.getcwd()
            os.makedirs(out_dir, exist_ok=True)
            with open(self.out_path, 'w', encoding='utf-8') as f:
                f.write(full_xml)

            self.done.emit(self.out_path)
        except Exception:
            self.failed.emit(traceback.format_exc())

# -----------------------------
# Композит: секция (заголовок над рамкой + панель с контентом)
# -----------------------------
class Section(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        self.lbl = QtWidgets.QLabel(title, self)
        self.lbl.setObjectName("sectionTitle")
        self.lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.lbl.setMargin(0)

        self.frame = QtWidgets.QFrame(self)
        self.frame.setObjectName("sectionFrame")
        self.frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_l = QtWidgets.QGridLayout(self.frame)
        self.frame_l.setHorizontalSpacing(8)
        self.frame_l.setVerticalSpacing(6)
        self.frame_l.setContentsMargins(8, 8, 8, 8)

        outer.addWidget(self.lbl)
        outer.addWidget(self.frame)

# -----------------------------
# Theme toggle (from AddUser style)
# -----------------------------
def _tint_pixmap(pix: QtGui.QPixmap, color: QtGui.QColor) -> QtGui.QPixmap:
    if pix.isNull():
        return pix
    out = QtGui.QPixmap(pix.size())
    out.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(out)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    p.drawPixmap(0, 0, pix)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    p.fillRect(out.rect(), color)
    p.end()
    return out

def _white_variant_for_qss(path: str) -> str:
    if not path or not os.path.exists(path):
        return path
    try:
        base = QtGui.QPixmap(path)
        if base.isNull():
            return path
        tinted = _tint_pixmap(base, QtGui.QColor(QtCore.Qt.white))
        tmp_dir = os.path.join(tempfile.gettempdir(), "larix_qss_icons")
        os.makedirs(tmp_dir, exist_ok=True)
        name = os.path.splitext(os.path.basename(path))[0] + "_white.png"
        out_path = os.path.join(tmp_dir, name)
        tinted.save(out_path, "PNG")
        return out_path
    except Exception:
        return path

def _resolve_arrow_path(base_file: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(base_file))
    candidates = [
        os.environ.get("ARROW_DOWN_PATH") or "",
        ARROW_DOWN_PATH,
        os.path.join(base_dir, "arrow-down.png"),
        os.path.join(base_dir, "icon", "arrow-down.png"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return ""

# -----------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Larix — Матрицы")
        self.resize(900, 600)
        self._pending_theme_apply = False
        # theme state (aligned with AddUser)
        self._BG = BG
        self._FG = FG
        self._BORDER = BORDER
        self._HEADER_BG = HEADER_BG
        try:
            self._set_theme_palette(is_dark_theme(QtWidgets.QApplication.instance()))
        except Exception:
            pass
        self._apply_app_font()
        self._build_ui()
        self._apply_stylesheet()

    def changeEvent(self, event: QtCore.QEvent) -> None:
        try:
            t = event.type()
            if t in (QtCore.QEvent.StyleChange, QtCore.QEvent.PaletteChange, QtCore.QEvent.ApplicationPaletteChange):
                if not self._pending_theme_apply:
                    self._pending_theme_apply = True
                    QtCore.QTimer.singleShot(0, self._apply_theme_from_app)
        except Exception:
            pass
        super().changeEvent(event)

    def _apply_theme_from_app(self) -> None:
        self._pending_theme_apply = False
        try:
            app = QtWidgets.QApplication.instance()
            self._set_theme_palette(is_dark_theme(app))
            try:
                self._apply_stylesheet2()
            except Exception:
                self._apply_stylesheet()
        except Exception:
            pass

    def _set_theme_palette(self, dark: bool) -> None:
        if dark:
            self._BG = "#1E1E1E"
            self._FG = "#F5F5F5"
            self._BORDER = "#3A3A3A"
            self._HEADER_BG = "#2A2A2A"
        else:
            self._BG = BG
            self._FG = FG
            self._BORDER = BORDER
            self._HEADER_BG = HEADER_BG

    def _apply_app_font(self):
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)

    def _make_form_label(self, text: str, *, height: int = 34) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl.setMinimumHeight(height)
        return lbl

    def _tune_form_control(self, widget, *, height: int = 34):
        try:
            widget.setMinimumHeight(height)
        except Exception:
            pass
        try:
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                widget.setTextMargins(0, 0, 0, 0)
        except Exception:
            pass
        try:
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                widget.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                widget.lineEdit().setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                widget.lineEdit().setTextMargins(0, 0, 0, 0)
        except Exception:
            pass
        return widget

    def _tune_combo_editor(self, combo: QtWidgets.QComboBox):
        line_edit = combo.lineEdit()
        if line_edit is None:
            return
        try:
            line_edit.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        except Exception:
            pass
        try:
            line_edit.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        try:
            line_edit.setTextMargins(0, 0, 0, 0)
        except Exception:
            pass
        try:
            line_edit.setFrame(False)
        except Exception:
            pass
        try:
            line_edit.setStyleSheet("QLineEdit { border: none; background: transparent; padding: 0px; margin: 0px; }")
        except Exception:
            pass

    def _refresh_form_alignment(self):
        for attr_name in (
            "ed_title",
            "ed_matrix",
            "ed_nabory",
            "btn_matrix",
            "btn_nabory",
            "btn_select_api",
            "cb_sheet_matrix",
            "cb_sheet_nabory",
            "cmb_filter_param",
            "spin_a",
            "spin_b",
            "spin_c",
        ):
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            self._tune_form_control(widget)
        for attr_name in ("cb_sheet_matrix", "cb_sheet_nabory", "cmb_filter_param"):
            combo = getattr(self, attr_name, None)
            if combo is not None:
                self._tune_combo_editor(combo)

    def _build_ui(self):
        cw = QtWidgets.QWidget()
        self.setCentralWidget(cw)
        root = QtWidgets.QVBoxLayout(cw)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.setAlignment(QtCore.Qt.AlignTop)

        form_row_height = 34

        # Header с кнопкой назад и переключателем темы (без рамки/капсулы)
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)
        self._btn_back = create_back_button(self, icon_dir=ICON_DIR)
        self._btn_back.clicked.connect(lambda: go_to_main_menu(self))
        header.addWidget(self._btn_back)
        header.addStretch(1)
        self._theme_toggle = ThemeToggle(self)
        self._theme_toggle.setChecked(is_dark_theme(QtWidgets.QApplication.instance()))
        self._theme_toggle.toggled.connect(self._on_theme_toggled)
        header.addWidget(self._theme_toggle)
        root.addLayout(header)

        # ------ Секция Файлы ------
        self.sec_files = Section("Файлы", self)
        l = self.sec_files.frame_l

        # Матрица
        self.ed_matrix = self._tune_form_control(QtWidgets.QLineEdit(), height=form_row_height)
        self.btn_matrix = self._tune_form_control(QtWidgets.QPushButton("Выбрать..."), height=form_row_height)
        self.btn_matrix.clicked.connect(self._pick_matrix)
        l.addWidget(self._make_form_label("Матрица коллизий.xlsx", height=form_row_height), 1, 0)
        l.addWidget(self.ed_matrix, 1, 1)
        l.addWidget(self.btn_matrix, 1, 2)

        self.cb_sheet_matrix = self._tune_form_control(QtWidgets.QComboBox(), height=form_row_height)
        self.cb_sheet_matrix.setEditable(True)
        self.cb_sheet_matrix.lineEdit().setPlaceholderText("не выбрано")
        self._tune_combo_editor(self.cb_sheet_matrix)
        self.cb_sheet_matrix.setCurrentIndex(-1)
        self.cb_sheet_matrix.setFixedWidth(300)
        spm = self.cb_sheet_matrix.sizePolicy()
        spm.setHorizontalPolicy(QtWidgets.QSizePolicy.Fixed)
        self.cb_sheet_matrix.setSizePolicy(spm)
        l.addWidget(self._make_form_label("Лист:", height=form_row_height), 2, 0)
        l.addWidget(self.cb_sheet_matrix, 2, 1)

        self.cb_enable_filter = QtWidgets.QCheckBox("Включить фильтр")
        self.cb_enable_filter.setChecked(False)
        l.addWidget(self.cb_enable_filter, 3, 0, 1, 3)

        # Наборы (опционально)
        self.lbl_nabory = self._make_form_label("Наборы для коллизий.xlsx (опционально)", height=form_row_height)
        self.ed_nabory = self._tune_form_control(QtWidgets.QLineEdit(), height=form_row_height)
        self.btn_nabory = self._tune_form_control(QtWidgets.QPushButton("Выбрать..."), height=form_row_height)
        self.btn_nabory.clicked.connect(self._pick_nabory)
        l.addWidget(self.lbl_nabory, 4, 0)
        l.addWidget(self.ed_nabory, 4, 1)
        l.addWidget(self.btn_nabory, 4, 2)

        self.lbl_sheet_nabory = self._make_form_label("Лист (наборы):", height=form_row_height)
        self.cb_sheet_nabory = self._tune_form_control(QtWidgets.QComboBox(), height=form_row_height)
        self.cb_sheet_nabory.setEditable(True)
        self.cb_sheet_nabory.lineEdit().setPlaceholderText("не выбрано")
        self._tune_combo_editor(self.cb_sheet_nabory)
        self.cb_sheet_nabory.setCurrentIndex(-1)
        self.cb_sheet_nabory.setFixedWidth(300)
        spn = self.cb_sheet_nabory.sizePolicy()
        spn.setHorizontalPolicy(QtWidgets.QSizePolicy.Fixed)
        self.cb_sheet_nabory.setSizePolicy(spn)
        l.addWidget(self.lbl_sheet_nabory, 5, 0)
        l.addWidget(self.cb_sheet_nabory, 5, 1)

        self.ed_title = self._tune_form_control(QtWidgets.QLineEdit(), height=form_row_height)
        self.ed_title.setPlaceholderText("Матрица")
        l.addWidget(self._make_form_label("Название профиля", height=form_row_height), 0, 0)
        l.addWidget(self.ed_title, 0, 1, 1, 2)

        root.addWidget(self.sec_files)

        # ------ Секция Допуски ------
        self.sec_tol = Section("Допуски", self)
        p = self.sec_tol.frame_l
        p.setHorizontalSpacing(12)

        # Верхняя строка: подписи A/B/C
        lbl_a = QtWidgets.QLabel("Допуск A")
        lbl_b = QtWidgets.QLabel("Допуск B")
        lbl_c = QtWidgets.QLabel("Допуск C")
        lbl_a.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl_b.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl_c.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # Slight right offset for labels
        try:
            lbl_a.setIndent(8)
            lbl_b.setIndent(8)
            lbl_c.setIndent(8)
        except Exception:
            pass

        p.addWidget(lbl_a, 1, 0)
        p.addWidget(lbl_b, 1, 1)
        p.addWidget(lbl_c, 1, 2)

        # Нижняя строка: поля допусков
        def mk_spin(default):
            sb = QtWidgets.QDoubleSpinBox()
            sb.setRange(0.0, 999.0)
            sb.setDecimals(2)
            sb.setSingleStep(0.01)
            sb.setSuffix(" м.")
            sb.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            sb.setAlignment(QtCore.Qt.AlignLeft)
            sb.setFixedWidth(96)
            sb.setValue(default)
            return sb

        self.spin_a = mk_spin(0.10)
        self.spin_b = mk_spin(0.20)
        self.spin_c = mk_spin(0.30)

        p.addWidget(self.spin_a, 2, 0)
        p.addWidget(self.spin_b, 2, 1)
        p.addWidget(self.spin_c, 2, 2)

        # Блок параметра фильтрации (под допусками)
        lbl_filter_param = self._make_form_label("Параметр фильтрации", height=form_row_height)
        self.cmb_filter_param = self._tune_form_control(QtWidgets.QComboBox(), height=form_row_height)
        self.cmb_filter_param.setEditable(True)
        self.cmb_filter_param.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.cmb_filter_param.addItems(["Категория:\\", "Тип:\\Код по классификатору"])
        self.cmb_filter_param.setCurrentIndex(0)
        self.cmb_filter_param.setFixedWidth(200)
        line_edit = self.cmb_filter_param.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Введите значение или выберите из API")
        self._tune_combo_editor(self.cmb_filter_param)

        self.btn_select_api = self._tune_form_control(QtWidgets.QPushButton("Выбрать из API"), height=form_row_height)
        self.btn_select_api.setFixedWidth(150)
        self.btn_select_api.clicked.connect(self._on_select_from_api)
        
        p.addWidget(lbl_filter_param, 3, 0)
        p.addWidget(self.cmb_filter_param, 3, 1, 1, 1)
        p.addWidget(self.btn_select_api, 3, 2, 1, 1)
        self.lbl_filter_param = lbl_filter_param

        # Растяжение колонок равномерное
        p.setColumnStretch(0, 1)
        p.setColumnStretch(1, 1)
        p.setColumnStretch(2, 1)

        root.addWidget(self.sec_tol)

        # Панель действий - центрируем и увеличиваем кнопку
        actions = QtWidgets.QHBoxLayout()
        actions.addStretch(1)
        self.btn_generate = QtWidgets.QPushButton("Сгенерировать профиль")
        self.btn_generate.setObjectName("btn_generate")
        self.btn_generate.setMinimumHeight(48)
        self.btn_generate.setMinimumWidth(300)
        self.btn_generate.clicked.connect(self._start_generation)
        actions.addWidget(self.btn_generate)
        actions.addStretch(1)
        root.addLayout(actions)
        root.addStretch(1)
        # ������ ���������� ������ �� �������

        # Статус бар
        self.status = self.statusBar()
        self.status.showMessage("Готово")
        self._refresh_form_alignment()
        self.cb_enable_filter.toggled.connect(self._on_filter_enabled_toggled)
        self._on_filter_enabled_toggled(self.cb_enable_filter.isChecked())

    # ---------------------------------
    # Helpers
    # ---------------------------------
    def _load_logo_pixmap(self) -> QtGui.QPixmap | None:
        candidates = [LOGO_PATH, LOGO_LIGHT_PATH]
        for p in candidates:
            if p and os.path.exists(p):
                return QtGui.QPixmap(p)
        return None

    def _update_logo_for_theme(self, dark: bool) -> None:
        try:
            if not hasattr(self, "logo_lbl") or self.logo_lbl is None:
                return
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if dark:
                cands = [LOGO_DARK_PATH]
            else:
                cands = [LOGO_LIGHT_PATH]
            p = first_existing(cands)
            if not p:
                # fallback to previously defined loader
                pm = self._load_logo_pixmap()
                if pm is not None and not pm.isNull():
                    h = self.logo_lbl.pixmap().height() if self.logo_lbl.pixmap() else 52
                    self.logo_lbl.setPixmap(pm.scaledToHeight(h, QtCore.Qt.SmoothTransformation))
                return
            pm = QtGui.QPixmap(p)
            if not pm.isNull():
                h = self.logo_lbl.pixmap().height() if self.logo_lbl.pixmap() else 52
                self.logo_lbl.setPixmap(pm.scaledToHeight(h, QtCore.Qt.SmoothTransformation))
        except Exception:
            pass

    def _toggle_theme(self, checked: bool):
        if checked:
            self._BG = "#1E1E1E"; self._FG = "#F5F5F5"; self._BORDER = "#3A3A3A"; self._HEADER_BG = "#2A2A2A"
        else:
            self._BG = BG; self._FG = FG; self._BORDER = BORDER; self._HEADER_BG = HEADER_BG
        try:
            self._apply_stylesheet2()
        except Exception:
            self._apply_stylesheet()

    def _on_theme_toggled(self, dark: bool):
        app = QtWidgets.QApplication.instance()
        if app is not None:
            theme(app, dark, icon_dir=ICON_DIR)
        try:
            self._set_theme_palette(bool(dark))
        except Exception:
            pass
        try:
            self._apply_stylesheet2()
        except Exception:
            self._apply_stylesheet()

    def _apply_stylesheet2(self):
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        dark = is_dark_theme(app)
        self._set_theme_palette(dark)
        try:
            if hasattr(self, "_theme_toggle") and self._theme_toggle is not None:
                self._theme_toggle.blockSignals(True)
                self._theme_toggle.setChecked(dark, animate=False)
                self._theme_toggle.blockSignals(False)
        except Exception:
            pass
        try:
            _apply_native_dark_titlebar(self, dark)
        except Exception:
            pass
        try:
            self._refresh_form_alignment()
        except Exception:
            pass
        try:
            self._update_filter_controls_visual_state(self.cb_enable_filter.isChecked())
        except Exception:
            pass


    def _apply_stylesheet(self):
        self._apply_stylesheet2()
    # -------------------------
    # File pickers
    # -------------------------
    def _update_filter_controls_visual_state(self, enabled: bool):
        app = QtWidgets.QApplication.instance()
        dark = bool(is_dark_theme(app)) if app is not None else False

        labels = [
            self.lbl_nabory,
            self.lbl_sheet_nabory,
            self.lbl_filter_param,
        ]
        text_inputs = [
            self.ed_nabory,
            self.cmb_filter_param,
        ]
        buttons = [
            self.btn_nabory,
            self.btn_select_api,
        ]

        if enabled:
            for widget in labels + text_inputs + buttons + [self.cb_sheet_nabory]:
                widget.setStyleSheet("")
            for combo in (self.cb_sheet_nabory, self.cmb_filter_param):
                self._tune_combo_editor(combo)
            return

        label_color = "#8A8A8A" if dark else "#9A9A9A"
        field_bg = "#2A2A2A" if dark else "#F1F1F1"
        field_text = "#7E7E7E" if dark else "#8F8F8F"
        border_color = "#464646" if dark else "#D2D2D2"
        button_bg = "#303030" if dark else "#E7E7E7"

        label_qss = f"color: {label_color};"
        field_qss = (
            f"color: {field_text};"
            f"background-color: {field_bg};"
            f"border: 1px solid {border_color};"
            "border-radius: 4px;"
        )
        button_qss = (
            f"color: {label_color};"
            f"background-color: {button_bg};"
            f"border: 1px solid {border_color};"
            "border-radius: 4px;"
            "padding: 4px 10px;"
        )
        combo_qss = f"""
            QComboBox {{
                color: {field_text};
                background-color: {field_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 2px 6px;
            }}
            QComboBox::drop-down {{
                border: 0;
                background-color: {button_bg};
                width: 22px;
            }}
            QComboBox QLineEdit {{
                color: {field_text};
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
        """

        for widget in labels:
            widget.setStyleSheet(label_qss)
        for widget in buttons:
            widget.setStyleSheet(button_qss)
        self.ed_nabory.setStyleSheet(field_qss)
        self.cb_sheet_nabory.setStyleSheet(combo_qss)
        self.cmb_filter_param.setStyleSheet(combo_qss)
        for combo in (self.cb_sheet_nabory, self.cmb_filter_param):
            self._tune_combo_editor(combo)

    def _on_filter_enabled_toggled(self, checked: bool):
        enabled = bool(checked)
        controls = [
            self.lbl_nabory,
            self.ed_nabory,
            self.btn_nabory,
            self.lbl_sheet_nabory,
            self.cb_sheet_nabory,
            self.lbl_filter_param,
            self.cmb_filter_param,
            self.btn_select_api,
        ]
        for widget in controls:
            widget.setEnabled(enabled)
        self._update_filter_controls_visual_state(enabled)

    def _pick_nabory(self):
        if not self.cb_enable_filter.isChecked():
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(_get_visible_parent(self), "Выберите файл наборов", "", "Excel (*.xlsx *.xls)")
        if path:
            self.ed_nabory.setText(path)
            self._populate_sheets(path, self.cb_sheet_nabory)

    def _pick_matrix(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(_get_visible_parent(self), "Выберите файл матрицы", "", "Excel (*.xlsx *.xls)")
        if path:
            self.ed_matrix.setText(path)
            self._populate_sheets(path, self.cb_sheet_matrix)

    def _populate_sheets(self, file_path: str, combo: QtWidgets.QComboBox):
        sheets = list_sheets(file_path)
        combo.clear()
        if sheets:
            combo.addItems(sheets)
            combo.setCurrentIndex(-1)        # оставляем пустым до выбора
            combo.lineEdit().clear()         # очищаем текст
        else:
            combo.setCurrentIndex(-1)
            combo.lineEdit().clear()
    
    def _on_select_from_api(self):
        """Открывает диалог выбора из API и заполняет параметр фильтрации."""
        try:
            from Sets.ui import (
                ApiSelectDialog as SetsApiSelectDialog,
                api_get_projects as sets_api_get_projects,
                api_get_containers as sets_api_get_containers,
                api_get_parameters as sets_api_get_parameters,
            )

            dlg = SetsApiSelectDialog(
                _get_visible_parent(self),
                _runtime_api_base_url(),
                sets_api_get_projects,
                sets_api_get_containers,
                sets_api_get_parameters,
                on_import=lambda rows: self.cmb_filter_param.setCurrentText(rows[0].get("code", "")) if rows else None,
                state={},
            )
            if getattr(dlg, "exec", None):
                dlg.exec()
            else:
                dlg.exec_()
        except Exception as e:
            _popup_error(_get_visible_parent(self), f"Ошибка при выборе из API:\n{e}")

    # -------------------------
    # Generation
    # -------------------------
    def _start_generation(self):
        build_filters = self.cb_enable_filter.isChecked()
        nabory = self.ed_nabory.text().strip() if build_filters else ""
        matrix = self.ed_matrix.text().strip()
        profile_title = (self.ed_title.text() or "").strip() or "Матрица"
        param_field = ((self.cmb_filter_param.currentText() or "").strip() or "Категория:\\") if build_filters else ""

        sheet_nabory = self.cb_sheet_nabory.currentText().strip() if build_filters else ""
        sheet_matrix = self.cb_sheet_matrix.currentText().strip()

        if not os.path.exists(matrix):
            show_warning(_get_visible_parent(self), "Укажите корректный путь к файлу матрицы.", "Файл не найден")
            return
        if build_filters and nabory and not os.path.exists(nabory):
            show_warning(_get_visible_parent(self), "Укажите корректный путь к файлу наборов или оставьте поле пустым.", "Файл не найден")
            return
        if build_filters and nabory and not sheet_nabory:
            show_warning(_get_visible_parent(self), "Выберите лист в файле наборов или очистите путь к наборам.", "Не выбран лист")
            return
        if not sheet_matrix:
            show_warning(_get_visible_parent(self), "Выберите лист в матрице.", "Не выбран лист")
            return

        out, _ = QtWidgets.QFileDialog.getSaveFileName(_get_visible_parent(self), "Выберите выходной файл", "matrix.cv", "Профиль (*.cv *.xml)")
        if not out:
            return
        
        self.btn_generate.setEnabled(False)
        self.status.showMessage("Обработка...")

        self._pending_success_path: str | None = None
        self._pending_error_msg: str | None = None

        self.thread = QtCore.QThread(self)
        self.worker = GeneratorWorker(
            nabory, matrix, out,
            sheet_nabory, sheet_matrix,
            self.spin_a.value(), self.spin_b.value(), self.spin_c.value(),
            profile_title, param_field, build_filters
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._on_thread_finished)
        self.thread.start()

    def _on_done(self, out_path: str):
        self._pending_success_path = out_path
        self.status.showMessage("Готово")

    def _on_failed(self, err: str):
        self._pending_error_msg = "Произошла ошибка при генерации. Подробности в журнале."
        self.status.showMessage("Ошибка")

    def _on_thread_finished(self):
        print(f"[MATRIX] _on_thread_finished called", file=sys.stderr, flush=True)
        self.btn_generate.setEnabled(True)
        success_path = getattr(self, "_pending_success_path", None)
        error_msg = getattr(self, "_pending_error_msg", None)
        self._pending_success_path = None
        self._pending_error_msg = None
        
        print(f"[MATRIX] success_path={success_path}, error_msg={error_msg}", file=sys.stderr, flush=True)
        
        if self.thread:
            self.thread.deleteLater()
            self.thread = None
            self.worker = None
        
        if success_path:
            QtCore.QTimer.singleShot(0, lambda path=success_path: self._show_generation_result(success_path=path))
        elif error_msg:
            QtCore.QTimer.singleShot(0, lambda message=error_msg: self._show_generation_result(error_message=message))

    def _show_generation_result(self, success_path: str | None = None, error_message: str | None = None):
        parent = _get_visible_parent(self)
        print(f"[MATRIX] _show_generation_result called: parent={parent}", file=sys.stderr, flush=True)
        if success_path:
            _popup_info(parent, f"Файл создан:\n{success_path}", "Готово")
        elif error_message:
            _popup_error(parent, error_message)

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Matrix Export")

    try:
        theme(app, load_saved_theme(False), icon_dir=ICON_DIR, persist=False)
        enable_theme_sync(app, ICON_DIR)
    except Exception:
        pass

    # Иконка окна
    icon = QtGui.QIcon()
    for p in (TITLEBAR_ICON_PATH, LOGO_PATH):
        if os.path.exists(p):
            icon.addFile(p)
            break
    if not icon.isNull():
        app.setWindowIcon(icon)

    win = MainWindow()
    try:
        win._apply_stylesheet2()
    except Exception:
        try:
            win._apply_stylesheet()
        except Exception:
            pass
    win.show()
    try:
        bcol = getattr(win, "_BG", BG)
        dark = str(bcol).lower() in ("#1e1e1e", "#171717", "#202020", "#121212")
        _apply_native_dark_titlebar(win, dark)
    except Exception:
        pass
    sys.exit(app.exec_() if QT_API == "PyQt5" else app.exec())

if __name__ == "__main__":
    main()













