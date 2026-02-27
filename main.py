import sys
import os
import importlib
import urllib.request
import urllib.error
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect, QPushButton, QFileDialog, QMessageBox, QLineEdit, QStyle
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QSize, QObject, QThread, Slot, QEvent
from PySide6.QtGui import QColor, QCursor, QPainter, QPixmap, QIcon

from shared.theme_toggle import (
    ThemeToggle, is_dark_theme, theme, resolve_icon_path,
    load_saved_theme, enable_theme_sync, set_back_to_menu_callback,
    apply_dark_titlebar,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "icon")
LOGO_LIGHT_REL = os.path.join("icon", "Manager-scaled.png")
LOGO_DARK_REL = os.path.join("icon", "Manager-scaled_white.png")
TITLEBAR_ICON_REL = os.path.join("icon", "logo.ico")
DEFAULT_API_BASE_URL = "http://localhost:5000"
_ACTIVE_API_CHECK_THREADS = set()


def _load_symbol_from_dir(module_dir: str, module_name: str, symbol_name: str):
    mod_dir = os.path.join(BASE_DIR, module_dir)
    if mod_dir not in sys.path:
        sys.path.insert(0, mod_dir)
    module = importlib.import_module(module_name)
    return getattr(module, symbol_name)


def _track_api_check_thread(thread: QThread) -> None:
    if thread is None:
        return
    _ACTIVE_API_CHECK_THREADS.add(thread)

    def _drop_ref() -> None:
        try:
            _ACTIVE_API_CHECK_THREADS.discard(thread)
        except Exception:
            pass

    try:
        thread.finished.connect(_drop_ref)
    except Exception:
        pass


def _shutdown_api_check_threads() -> None:
    for t in list(_ACTIVE_API_CHECK_THREADS):
        try:
            if t is not None and t.isRunning():
                t.quit()
                t.wait(3000)
        except Exception:
            pass
        try:
            _ACTIVE_API_CHECK_THREADS.discard(t)
        except Exception:
            pass


def _normalize_api_base_url(url: str) -> str:
    s = (url or "").strip()
    if not s:
        return DEFAULT_API_BASE_URL
    if "://" not in s:
        s = "http://" + s
    return s.rstrip("/")


def _check_api_connection(base_url: str, timeout_sec: float = 2.0) -> bool:
    test_urls = [
        f"{base_url}/api/project/projects",
        f"{base_url}/health",
        f"{base_url}/api/health",
    ]
    for u in test_urls:
        try:
            req = urllib.request.Request(u, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                code = int(getattr(resp, "status", 0) or 0)
                if 200 <= code < 400:
                    return True
        except Exception:
            pass
    return False


class ApiCheckWorker(QObject):
    finished = Signal(int, str, bool)

    def __init__(self, seq: int, base_url: str):
        super().__init__()
        self._seq = int(seq)
        self._base_url = str(base_url or "")

    @Slot()
    def run(self):
        ok = _check_api_connection(self._base_url)
        self.finished.emit(self._seq, self._base_url, ok)

def get_logo_path(is_dark=False):
    rel = LOGO_DARK_REL if is_dark else LOGO_LIGHT_REL
    direct = os.path.join(BASE_DIR, rel)
    if os.path.exists(direct):
        return direct
    app = QApplication.instance()
    fallback_name = "logo_white" if is_dark else "logo"
    return resolve_icon_path(fallback_name, ICON_DIR, app=app, tint_in_dark=False) or ""

def get_window_icon_path():
    direct = os.path.join(BASE_DIR, TITLEBAR_ICON_REL)
    if os.path.exists(direct):
        return direct
    app = QApplication.instance()
    return resolve_icon_path("app_icon", ICON_DIR, app=app, tint_in_dark=False) or ""

class AnimatableShadowEffect(QGraphicsDropShadowEffect):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blur_radius = 0
        self._offset_y = 0
        self.setColor(QColor(0, 0, 0, 60))
        self.setBlurRadius(0)
        self.setOffset(0, 0)

    def getBlurRadiusAnim(self):
        return self._blur_radius

    def setBlurRadiusAnim(self, value):
        self._blur_radius = value
        self.setBlurRadius(value)

    def getOffsetY(self):
        return self._offset_y

    def setOffsetY(self, value):
        self._offset_y = value
        self.setOffset(0, int(value))

    animBlurRadius = Property(float, getBlurRadiusAnim, setBlurRadiusAnim)
    animOffsetY = Property(float, getOffsetY, setOffsetY)

class ModeCard(QFrame):
    clicked = Signal(str)

    def __init__(self, mode_id, title, description, is_dark=False, parent=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self._title_text = title
        self._desc_text = description
        self._is_dark = is_dark
        self._hovered = False
        self._selected = False

        self.setMinimumHeight(90)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(110)

        self._shadow = AnimatableShadowEffect(self)
        self.setGraphicsEffect(self._shadow)

        self._pos_anim = QPropertyAnimation(self, b"pos", self)
        self._pos_anim.setDuration(180)
        self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._blur_anim = QPropertyAnimation(self._shadow, b"animBlurRadius", self)
        self._blur_anim.setDuration(180)
        self._blur_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._offset_anim = QPropertyAnimation(self._shadow, b"animOffsetY", self)
        self._offset_anim.setDuration(180)
        self._offset_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._original_pos = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-size: 12pt; font-weight: 600;")
        layout.addWidget(self._title_label)

        self._desc_label = QLabel(description)
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self._desc_label)

        self._update_style()

    def set_selected(self, selected):
        self._selected = selected
        self._update_style()

    def is_selected(self):
        return self._selected

    def _update_style(self):
        if self._is_dark:
            if self._selected:
                bg = "#3a2b1a"
                border = "#E07E12"
                title_color = "#e0e0e0"
                desc_color = "#FFC37A"
            elif self._hovered:
                bg = "#FFE3C2"
                border = "#FFA74B"
                title_color = "#000000"
                desc_color = "#000000"
            else:
                bg = "#1e1e1e"
                border = "#404040"
                title_color = "#e0e0e0"
                desc_color = "#888888"
        else:
            if self._selected:
                bg = "#FFC37A"
                border = "#E07E12"
                title_color = "#000000"
                desc_color = "#000000"
            elif self._hovered:
                bg = "#FFE3C2"
                border = "#FFA74B"
                title_color = "#000000"
                desc_color = "#000000"
            else:
                bg = "#ffffff"
                border = "#e0e0e0"
                title_color = "#222222"
                desc_color = "#888888"

        self.setStyleSheet(f"""
            ModeCard {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 12px;
            }}
        """)
        self._title_label.setStyleSheet(f"font-size: 12pt; font-weight: 600; color: {title_color}; background: transparent;")
        self._desc_label.setStyleSheet(f"font-size: 9pt; color: {desc_color}; background: transparent;")

    def _animate_to(self, hover_in):
        if self._original_pos is None:
            self._original_pos = self.pos()

        if hover_in:
            target_pos = self._original_pos - QPoint(0, 8)
            self._pos_anim.setStartValue(self.pos())
            self._pos_anim.setEndValue(target_pos)

            self._blur_anim.setStartValue(self._shadow.getBlurRadiusAnim())
            self._blur_anim.setEndValue(25)

            self._offset_anim.setStartValue(self._shadow.getOffsetY())
            self._offset_anim.setEndValue(8)
        else:
            target_pos = self._original_pos
            self._pos_anim.setStartValue(self.pos())
            self._pos_anim.setEndValue(target_pos)

            self._blur_anim.setStartValue(self._shadow.getBlurRadiusAnim())
            self._blur_anim.setEndValue(0)

            self._offset_anim.setStartValue(self._shadow.getOffsetY())
            self._offset_anim.setEndValue(0)

        self._pos_anim.start()
        self._blur_anim.start()
        self._offset_anim.start()

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
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.mode_id)
        super().mousePressEvent(event)

class MainMenuWidget(QWidget):
    mode_selected = Signal(str)
    api_base_changed = Signal(str)

    def __init__(self, is_dark=False, api_base_url=DEFAULT_API_BASE_URL, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._api_base_url = _normalize_api_base_url(api_base_url)
        self._api_is_connected = False
        self._api_check_seq = 0
        self._api_check_silent = True
        self._api_check_thread = None
        self._api_check_worker = None
        self._api_check_busy = False
        self._api_check_timeout = QTimer(self)
        self._api_check_timeout.setSingleShot(True)
        self._api_check_timeout.timeout.connect(self._on_api_check_timeout)
        self._cards = []
        self._setup_ui()
        QTimer.singleShot(0, self._connect_current_api_silent)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(16)

        toggle_row = QHBoxLayout()
        toggle_row.addStretch(1)
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.setChecked(bool(self._is_dark), animate=False)
        self.theme_toggle.toggled.connect(self._on_theme_toggled)
        toggle_row.addWidget(self.theme_toggle, 0, Qt.AlignRight)
        main_layout.addLayout(toggle_row)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignCenter)
        self._update_logo()
        main_layout.addWidget(self._logo_label)

        title_label = QLabel("Выберите режим работы")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: 600;")
        main_layout.addWidget(title_label)

        cards_data = [
            ("adapters", "Адаптеры", "Создание адаптеров"),
            ("larix_set", "Наборы", "Создание наборов"),
            ("matrix", "Матрицы", "Создание матриц"),
            ("parameters", "Параметры", "Создание профиля проверок параметров"),
            ("viewer", "Статусы", "Загрузка статусов из Larix Viewer"),
        ]

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(20)
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(20)
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(20)
        row3_layout.setAlignment(Qt.AlignCenter)

        for i, (mode_id, title, desc) in enumerate(cards_data):
            card = ModeCard(mode_id, title, desc, self._is_dark, self)
            card.clicked.connect(self._on_card_clicked)
            self._cards.append(card)
            if mode_id == "viewer":
                card.setFixedSize(260, 80)
                try:
                    lay = card.layout()
                    if lay is not None:
                        lay.setContentsMargins(14, 10, 14, 10)
                        lay.setSpacing(6)
                except Exception:
                    pass
                row3_layout.addStretch(1)
                row3_layout.addWidget(card, 0, Qt.AlignCenter)
                row3_layout.addStretch(1)
            elif i < 2:
                row1_layout.addWidget(card)
            elif i < 4:
                row2_layout.addWidget(card)

        main_layout.addLayout(row1_layout)
        main_layout.addLayout(row2_layout)
        main_layout.addLayout(row3_layout)
        main_layout.addStretch()

        btn_templates = QPushButton("Скачать шаблон Excel")
        btn_templates.setMinimumWidth(200)
        btn_templates.clicked.connect(self._download_template)
        main_layout.addWidget(btn_templates, 0, Qt.AlignCenter)

        api_row = QHBoxLayout()
        api_row.addStretch(1)
        api_row.addWidget(QLabel("Сервер API:"))
        self.api_base_edit = QLineEdit(self._api_base_url)
        self.api_base_edit.setFixedWidth(260)
        self.api_base_edit.setClearButtonEnabled(False)
        self.api_base_edit.setPlaceholderText(DEFAULT_API_BASE_URL)
        self.api_base_edit.textChanged.connect(self._on_api_base_text_changed)
        self.api_base_edit.editingFinished.connect(self._on_api_base_edited)
        self._api_status_icon = QLabel(self.api_base_edit)
        self._api_status_icon.setFixedSize(16, 16)
        self._api_status_icon.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.api_base_edit.installEventFilter(self)
        api_row.addWidget(self.api_base_edit)

        self.btn_api_connect = QPushButton("Подключить")
        self.btn_api_connect.clicked.connect(self._on_api_connect_clicked)
        self.btn_api_connect.setProperty("secondary", True)
        api_row.addWidget(self.btn_api_connect)
        self._set_connect_button_icon()

        self._set_api_status_icon(False)

        api_row.addStretch(1)
        main_layout.addLayout(api_row)

    def _on_api_base_edited(self):
        value = _normalize_api_base_url(self.api_base_edit.text())
        self._api_base_url = value
        self.api_base_edit.setText(value)

    def _set_api_status_icon(self, connected: bool):
        self._api_is_connected = bool(connected)
        app = QApplication.instance()
        key = "ok" if connected else "none"
        path = resolve_icon_path(key, ICON_DIR, app=app)
        tip = (
            "Подключено к API"
            if connected
            else "Нет подключения к API. Измените адрес и нажмите 'Подключить'."
        )
        if path and os.path.exists(path):
            icon = QIcon(path)
        else:
            std = QStyle.SP_DialogApplyButton if connected else QStyle.SP_DialogCancelButton
            icon = self.style().standardIcon(std)
        pm = icon.pixmap(16, 16)
        self._api_status_icon.setPixmap(pm)
        self._api_status_icon.setToolTip(tip)
        self._api_status_icon.setStatusTip(tip)
        self._position_api_status_icon()

    def _position_api_status_icon(self):
        e = self.api_base_edit
        x = max(0, e.width() - 16 - 8)
        y = max(0, (e.height() - 16) // 2)
        self._api_status_icon.move(x, y)
        self._api_status_icon.raise_()

    def eventFilter(self, obj, event):
        try:
            if obj is getattr(self, "api_base_edit", None) and event is not None:
                t = event.type()
                if t in (QEvent.Resize, QEvent.Move, QEvent.Show):
                    self._position_api_status_icon()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _set_connect_button_icon(self):
        app = QApplication.instance()
        icon_path = resolve_icon_path("login", ICON_DIR, app=app)
        if icon_path and os.path.exists(icon_path):
            self.btn_api_connect.setIcon(QIcon(icon_path))
            self.btn_api_connect.setIconSize(QSize(16, 16))

    def _on_api_base_text_changed(self, _text: str):
        self._set_api_status_icon(False)

    def _set_connect_ui_busy(self, busy: bool):
        try:
            self._api_check_busy = bool(busy)
            self.btn_api_connect.setEnabled(not busy)
            self.btn_api_connect.setText("Проверка..." if busy else "Подключить")
            if not busy:
                self._set_connect_button_icon()
        except Exception:
            pass

    def _start_api_check(self, silent: bool):
        value = _normalize_api_base_url(self.api_base_edit.text())
        self._api_base_url = value
        self.api_base_edit.setText(value)

        self._api_check_seq += 1
        seq = self._api_check_seq
        self._api_check_silent = bool(silent)
        self._set_connect_ui_busy(True)
        self._api_check_timeout.start(9000)

        thread = QThread()
        worker = ApiCheckWorker(seq, value)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_api_check_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_api_check_thread_finished)
        self._api_check_worker = worker
        self._api_check_thread = thread
        _track_api_check_thread(thread)
        thread.start()

    def _on_api_check_finished(self, seq: int, value: str, ok: bool):
        if seq != self._api_check_seq:
            return
        self._api_check_timeout.stop()
        self._set_connect_ui_busy(False)
        self._set_api_status_icon(ok)
        self._api_check_worker = None
        self._api_check_thread = None
        if ok:
            self.api_base_changed.emit(value)
        elif not self._api_check_silent:
            QMessageBox.warning(self, "Сервер API", f"Не удалось подключиться к {value}")

    def _on_api_check_timeout(self):
        if not self._api_check_busy:
            return
        self._set_connect_ui_busy(False)
        self._set_api_status_icon(False)
        t = self._api_check_thread
        if t is not None:
            try:
                if t.isRunning():
                    t.quit()
                    t.wait(1000)
            except Exception:
                pass
        self._api_check_worker = None
        self._api_check_thread = None

    def _on_api_check_thread_finished(self):
        # Safety net: if worker ended without delivering result, do not keep UI in "Проверка...".
        if self._api_check_busy:
            self._api_check_timeout.stop()
            self._set_connect_ui_busy(False)

    def _connect_current_api_silent(self):
        self._start_api_check(silent=True)

    def _on_api_connect_clicked(self):
        self._start_api_check(silent=False)

    def _on_theme_toggled(self, checked: bool) -> None:
        self._is_dark = bool(checked)
        self._apply_theme()

    def _apply_theme(self):
        try:
            app = QApplication.instance()
            if app is not None:
                theme(app, bool(self._is_dark), icon_dir=ICON_DIR)
        except Exception:
            pass
        for card in self._cards:
            try:
                card._is_dark = bool(self._is_dark)
                card._update_style()
            except Exception:
                pass
        self._update_logo()
        try:
            self._set_connect_button_icon()
            self._set_api_status_icon(self._api_is_connected)
        except Exception:
            pass

    def _update_logo(self):
        logo_path = get_logo_path(self._is_dark)
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            self._logo_label.setPixmap(pix.scaledToHeight(64, Qt.SmoothTransformation))
        else:
            self._logo_label.setText("Larix Manager")
            self._logo_label.setStyleSheet("font-size: 18pt; font-weight: bold;")

    def _on_card_clicked(self, mode_id):
        for card in self._cards:
            card.set_selected(card.mode_id == mode_id)
        QTimer.singleShot(150, lambda: self.mode_selected.emit(mode_id))

    def _download_template(self):
        try:
            from Excel_template import export_common_excel
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить модуль шаблонов:\n{e}")
            return
        fn, _ = QFileDialog.getSaveFileName(
            self,
            "Скачать шаблон Excel",
            "Шаблон Excel.xlsx",
            "Excel (*.xlsx)",
        )
        if not fn:
            return
        if not fn.lower().endswith(".xlsx"):
            fn += ".xlsx"
        try:
            export_common_excel("", fn)
            QMessageBox.information(self, "Готово", f"Шаблон Excel сохранён:\n{fn}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Larix Manager")
        self.setMinimumSize(860, 700)
        self.resize(920, 740)
        self._is_dark = load_saved_theme(False)
        self._api_base_url = _normalize_api_base_url(os.environ.get("LARIX_API_BASE_URL", DEFAULT_API_BASE_URL))
        os.environ["LARIX_API_BASE_URL"] = self._api_base_url
        self._current_module_window = None
        self._current_module_widget = None
        
        try:
            app = QApplication.instance()
            theme(app, self._is_dark, icon_dir=ICON_DIR)
            icon_path = get_window_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
            apply_dark_titlebar(self, self._is_dark)
        except Exception:
            pass

        set_back_to_menu_callback(self._show_main_menu)
        self._show_main_menu()

    def _center_on_screen(self):
        try:
            screen = self.windowHandle().screen() if self.windowHandle() else QApplication.primaryScreen()
            if screen is None:
                return
            geo = screen.availableGeometry()
            frm = self.frameGeometry()
            frm.moveCenter(geo.center())
            self.move(frm.topLeft())
        except Exception:
            pass

    def _show_main_menu(self):
        if self._current_module_widget is not None:
            self._current_module_widget = None
        self._current_module_window = None
        self.setWindowTitle("Larix Manager")

        menu = MainMenuWidget(self._is_dark, self._api_base_url, self)
        menu.mode_selected.connect(self._on_mode_selected)
        menu.api_base_changed.connect(self._on_api_base_changed)
        if hasattr(menu, 'theme_toggle'):
            menu.theme_toggle.toggled.connect(self._on_theme_toggled)
        self.setCentralWidget(menu)
        self._menu_widget = menu
        self.setMinimumSize(860, 700)
        self.resize(920, 740)
        self._center_on_screen()

    def _on_theme_toggled(self, dark: bool):
        self._is_dark = dark
        app = QApplication.instance()
        if app:
            theme(app, dark, icon_dir=ICON_DIR)
        try:
            apply_dark_titlebar(self, dark)
        except Exception:
            pass

    def _on_api_base_changed(self, value: str):
        self._api_base_url = _normalize_api_base_url(value)
        os.environ["LARIX_API_BASE_URL"] = self._api_base_url

    def _on_mode_selected(self, mode_id: str):
        widget, window = self._create_module_widget(mode_id)
        if widget:
            self._current_module_widget = widget
            self._current_module_window = window
            self.setCentralWidget(widget)
            module_titles = {
                "adapters": "Larix Manager - Редактор адаптера",
                "larix_set": "Larix Manager - Создание наборов",
                "matrix": "Larix Manager - Матрица коллизий",
                "parameters": "Larix Manager - Профиль проверок параметров",
                "viewer": "Larix Manager - Создание статусов",
            }
            title = module_titles.get(mode_id, "Larix Manager")
            try:
                if window is not None:
                    wt = (window.windowTitle() or "").strip()
                    if wt:
                        title = wt
                elif widget is not None:
                    wt = (widget.windowTitle() or "").strip()
                    if wt:
                        title = wt
            except Exception:
                pass
            self.setWindowTitle(title)
            target_w, target_h = 1120, 760
            min_w, min_h = 900, 620
            try:
                if window is not None:
                    ws = window.size()
                    if ws.width() > 0 and ws.height() > 0:
                        target_w = ws.width()
                        target_h = ws.height()
                    ms = window.minimumSize()
                    if ms.width() > 0 and ms.height() > 0:
                        min_w = ms.width()
                        min_h = ms.height()
                elif widget is not None:
                    hs = widget.sizeHint()
                    if hs.width() > 0 and hs.height() > 0:
                        target_w = hs.width()
                        target_h = hs.height()
            except Exception:
                pass
            self.setMinimumSize(max(760, min_w), max(560, min_h))
            self.resize(max(900, target_w), max(620, target_h))
            self._center_on_screen()

    def _create_module_widget(self, mode_id: str):
        try:
            if mode_id == "adapters":
                MainWin = _load_symbol_from_dir("Adapters", "Adapter", "MainWin")
                win = MainWin()
                return win.centralWidget(), win
            elif mode_id == "larix_set":
                ContentWidget = _load_symbol_from_dir("Larix_Set", "Larix_set", "ContentWidget")
                return ContentWidget(), None
            elif mode_id == "matrix":
                MainWindow = _load_symbol_from_dir("Matrix", "matrix_ui", "MainWindow")
                win = MainWindow()
                return win.centralWidget(), win
            elif mode_id == "parameters":
                MainWindow = _load_symbol_from_dir("Parameter", "Parameters", "MainWindow")
                win = MainWindow()
                return win.centralWidget(), win
            elif mode_id == "viewer":
                MainWindow = _load_symbol_from_dir("Viewer", "Viewer", "MainWindow")
                win = MainWindow()
                return win.centralWidget(), win
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить модуль {mode_id}:\n{e}")
            return None, None
        return None, None

def main():
    app = QApplication(sys.argv)
    try:
        app.aboutToQuit.connect(_shutdown_api_check_threads)
    except Exception:
        pass
    try:
        enable_theme_sync(app, ICON_DIR)
    except Exception:
        pass
    
    window = MainWindow()
    window.show()
    
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    else:
        sys.exit(app.exec_())

if __name__ == "__main__":
    main()
