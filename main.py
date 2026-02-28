import sys
import os
import importlib
import urllib.request
import urllib.error
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect, QPushButton, QFileDialog, QMessageBox, QLineEdit, QStyle, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QSize, QObject, QThread, Slot, QEvent
from PySide6.QtGui import QColor, QCursor, QPainter, QPixmap, QIcon, QImage

from shared.theme_toggle import (
    ThemeToggle, is_dark_theme, theme, resolve_icon_path,
    load_saved_theme, enable_theme_sync, set_back_to_menu_callback,
    apply_dark_titlebar,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "icon")
LOGO_LIGHT_REL = os.path.join("icon", "Manager-scaled.png")
LOGO_DARK_REL = os.path.join("icon", "Manager-scaled_white.png")
VIEWER_LOGO_LIGHT_REL = os.path.join("icon", "Larix Viewer_black.png")
VIEWER_LOGO_DARK_REL = os.path.join("icon", "Larix Viewer_white.png")
TITLEBAR_ICON_REL = os.path.join("icon", "logo.ico")
DEFAULT_API_BASE_URL = "http://localhost:5000"
MANAGER_LOGO_HEIGHT = 64
VIEWER_LOGO_HEIGHT = 64
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


def get_viewer_logo_path(is_dark=False):
    rel = VIEWER_LOGO_DARK_REL if is_dark else VIEWER_LOGO_LIGHT_REL
    direct = os.path.join(BASE_DIR, rel)
    if os.path.exists(direct):
        return direct
    return ""


def _trim_transparent_pixmap(pm: QPixmap) -> QPixmap:
    if pm.isNull():
        return pm
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    for y in range(h):
        for x in range(w):
            if img.pixelColor(x, y).alpha() > 0:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x < min_x or max_y < min_y:
        return pm
    return QPixmap.fromImage(img.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1))

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

    def __init__(self, mode_id, title, description, is_dark=False, parent=None, icon_name=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self._title_text = title
        self._desc_text = description
        self._is_dark = is_dark
        self._icon_name = icon_name
        self._icon_cache = {}
        self._hovered = False
        self._selected = False

        self.setMinimumHeight(140)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(156)

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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFixedHeight(54)
        layout.addWidget(self._icon_label, 0, Qt.AlignCenter)

        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("font-size: 10pt; font-weight: 600;")
        layout.addWidget(self._title_label)

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
                title_color = "#ffd6a6"
            elif self._hovered:
                bg = "#2f2620"
                border = "#FFA74B"
                title_color = "#ffc989"
            else:
                bg = "#1e1e1e"
                border = "#404040"
                title_color = "#e0e0e0"
        else:
            if self._selected:
                bg = "#FFC37A"
                border = "#E07E12"
                title_color = "#000000"
            elif self._hovered:
                bg = "#FFE3C2"
                border = "#FFA74B"
                title_color = "#000000"
            else:
                bg = "#ffffff"
                border = "#e0e0e0"
                title_color = "#222222"

        self.setStyleSheet(f"""
            ModeCard {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 12px;
            }}
        """)
        self._title_label.setStyleSheet(f"font-size: 11pt; font-weight: 600; color: {title_color}; background: transparent;")
        self._icon_label.setStyleSheet("background-color: transparent; border: none;")
        self._update_icon()

    def _update_icon(self):
        if not self._icon_name:
            self._icon_label.setPixmap(QPixmap())
            self._icon_label.setVisible(False)
            return

        icon_source = self._icon_name
        if not os.path.isabs(icon_source):
            icon_source = os.path.join(ICON_DIR, icon_source)
        app = QApplication.instance()
        icon_path = resolve_icon_path(icon_source, ICON_DIR, app=app, tint_in_dark=False)
        if icon_path and os.path.exists(icon_path):
            cache_key = (icon_path, bool(self._is_dark))
            pix = self._icon_cache.get(cache_key)
            if pix is None:
                pix = self._prepare_icon_pixmap(icon_path)
                self._icon_cache[cache_key] = pix
            if not pix.isNull():
                self._icon_label.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self._icon_label.setVisible(True)
                return

        self._icon_label.setPixmap(QPixmap())
        self._icon_label.setVisible(False)

    def _prepare_icon_pixmap(self, icon_path: str) -> QPixmap:
        pm = QPixmap(icon_path)
        if pm.isNull():
            return QPixmap()

        original_pm = pm
        img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
        width, height = img.width(), img.height()
        dark = bool(self._is_dark)
        icon_base = os.path.basename(icon_path).strip().lower()
        preserve_shape_icons = {"parameters.png", "status.png", "sync.png"}
        preserve_shape = icon_base in preserve_shape_icons

        if not preserve_shape:
            # Remove border-connected near-monochrome background blocks.
            self._erase_border_connected_background(img)

        # Remove near-white residue when safe; in dark theme recolor icon glyph to white.
        for y in range(height):
            for x in range(width):
                c = img.pixelColor(x, y)
                if c.alpha() == 0:
                    continue
                r, g, b = c.red(), c.green(), c.blue()
                maxc = max(r, g, b)
                minc = min(r, g, b)
                is_light_bg = (maxc >= 242 and (maxc - minc) <= 18)
                if (not preserve_shape) and is_light_bg:
                    c.setAlpha(0)
                    img.setPixelColor(x, y, c)
                    continue
                if dark:
                    img.setPixelColor(x, y, QColor(255, 255, 255, c.alpha()))
        if not preserve_shape:
            img = self._trim_transparent_bounds(img)
        out = QPixmap.fromImage(img)
        if out.isNull():
            return original_pm

        # Safety fallback: only if everything became transparent.
        out_img = out.toImage().convertToFormat(QImage.Format_ARGB32)
        opaque = 0
        for y in range(out_img.height()):
            for x in range(out_img.width()):
                if out_img.pixelColor(x, y).alpha() > 0:
                    opaque += 1
        if opaque == 0:
            return original_pm
        return out

    def _erase_border_connected_background(self, img: QImage) -> None:
        width, height = img.width(), img.height()
        if width <= 0 or height <= 0:
            return

        from collections import deque
        visited = set()

        def color_distance(c1: QColor, c2: QColor) -> int:
            return abs(c1.red() - c2.red()) + abs(c1.green() - c2.green()) + abs(c1.blue() - c2.blue())

        # Seeds from the border; remove only contiguous regions close to border seed color.
        seeds = []
        for x in range(width):
            seeds.append((x, 0))
            seeds.append((x, height - 1))
        for y in range(height):
            seeds.append((0, y))
            seeds.append((width - 1, y))

        threshold = 28
        for sx, sy in seeds:
            if (sx, sy) in visited:
                continue
            seed_color = img.pixelColor(sx, sy)
            if seed_color.alpha() == 0:
                visited.add((sx, sy))
                continue
            sr, sg, sb = seed_color.red(), seed_color.green(), seed_color.blue()
            smax, smin = max(sr, sg, sb), min(sr, sg, sb)
            is_seed_white = (smax >= 242 and (smax - smin) <= 16)
            is_seed_black = (smax <= 28 and (smax - smin) <= 16)
            if not (is_seed_white or is_seed_black):
                visited.add((sx, sy))
                continue

            q = deque()
            q.append((sx, sy))
            while q:
                x, y = q.popleft()
                if (x, y) in visited:
                    continue
                visited.add((x, y))
                cur = img.pixelColor(x, y)
                if cur.alpha() == 0:
                    continue
                if color_distance(cur, seed_color) > threshold:
                    continue

                cur.setAlpha(0)
                img.setPixelColor(x, y, cur)

                if x > 0:
                    q.append((x - 1, y))
                if x + 1 < width:
                    q.append((x + 1, y))
                if y > 0:
                    q.append((x, y - 1))
                if y + 1 < height:
                    q.append((x, y + 1))

    def _trim_transparent_bounds(self, img: QImage) -> QImage:
        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return img

        min_x, min_y = w, h
        max_x, max_y = -1, -1
        for y in range(h):
            for x in range(w):
                if img.pixelColor(x, y).alpha() > 0:
                    if x < min_x:
                        min_x = x
                    if y < min_y:
                        min_y = y
                    if x > max_x:
                        max_x = x
                    if y > max_y:
                        max_y = y

        if max_x < min_x or max_y < min_y:
            return img
        return img.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

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


class PageSwitchSlider(QFrame):
    page_clicked = Signal(str)

    def __init__(self, is_dark=False, parent=None):
        super().__init__(parent)
        self._is_dark = bool(is_dark)
        self._active_page = "manager"
        self.setObjectName("pageSwitchSlider")
        self.setFixedHeight(44)
        self._thumb = QFrame(self)
        self._thumb.setObjectName("pageSwitchThumb")
        self._thumb.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._thumb_anim = QPropertyAnimation(self._thumb, b"geometry", self)
        self._thumb_anim.setDuration(220)
        self._thumb_anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)

        self._btn_manager = QPushButton("Manager", self)
        self._btn_viewer = QPushButton("Viewer", self)
        for b in (self._btn_manager, self._btn_viewer):
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setFlat(True)
            b.setMinimumHeight(38)
            layout.addWidget(b, 1)

        self._btn_manager.clicked.connect(lambda: self._on_clicked("manager"))
        self._btn_viewer.clicked.connect(lambda: self._on_clicked("viewer"))
        self._update_style()
        QTimer.singleShot(0, self._sync_thumb_no_animation)

    def _on_clicked(self, page_id: str):
        self.set_active_page(page_id, animate=True)
        self.page_clicked.emit(self._active_page)

    def set_active_page(self, page_id: str, animate: bool = False):
        self._active_page = "viewer" if str(page_id).strip().lower() == "viewer" else "manager"
        self._update_style()
        self._move_thumb(animated=bool(animate))

    def set_theme(self, is_dark: bool):
        self._is_dark = bool(is_dark)
        self._update_style()
        self._sync_thumb_no_animation()

    def _update_style(self):
        if self._is_dark:
            frame_bg = "#1e1e1e"
            frame_border = "#404040"
            active_bg = "#FFC37A"
            active_text = "#000000"
            inactive_text = "#e0e0e0"
        else:
            frame_bg = "#ffffff"
            frame_border = "#d0d0d0"
            active_bg = "#FFC37A"
            active_text = "#000000"
            inactive_text = "#222222"

        self.setStyleSheet(
            f"QFrame#pageSwitchSlider {{ background-color: {frame_bg}; border: 2px solid {frame_border}; border-radius: 22px; }}"
            f"QFrame#pageSwitchThumb {{ background-color: {active_bg}; border: none; border-radius: 18px; }}"
        )

        if self._active_page == "manager":
            manager_style = f"background-color: transparent; color: {active_text}; border: none; border-radius: 18px; font-size: 11pt; font-weight: 600;"
            viewer_style = f"background-color: transparent; color: {inactive_text}; border: none; border-radius: 18px; font-size: 11pt; font-weight: 500;"
        else:
            manager_style = f"background-color: transparent; color: {inactive_text}; border: none; border-radius: 18px; font-size: 11pt; font-weight: 500;"
            viewer_style = f"background-color: transparent; color: {active_text}; border: none; border-radius: 18px; font-size: 11pt; font-weight: 600;"

        self._btn_manager.setStyleSheet(manager_style)
        self._btn_viewer.setStyleSheet(viewer_style)
        self._btn_manager.raise_()
        self._btn_viewer.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_thumb_no_animation()

    def _target_thumb_geometry(self):
        btn = self._btn_viewer if self._active_page == "viewer" else self._btn_manager
        return btn.geometry()

    def _sync_thumb_no_animation(self):
        target = self._target_thumb_geometry()
        if target.width() > 0 and target.height() > 0:
            self._thumb.setGeometry(target)
            self._btn_manager.raise_()
            self._btn_viewer.raise_()

    def _move_thumb(self, animated: bool):
        target = self._target_thumb_geometry()
        if target.width() <= 0 or target.height() <= 0:
            return
        self._btn_manager.raise_()
        self._btn_viewer.raise_()
        if animated:
            current = self._thumb.geometry()
            if current.width() <= 0 or current.height() <= 0:
                self._thumb.setGeometry(target)
                return
            self._thumb_anim.stop()
            self._thumb_anim.setStartValue(current)
            self._thumb_anim.setEndValue(target)
            self._thumb_anim.start()
        else:
            self._thumb_anim.stop()
            self._thumb.setGeometry(target)


class MainMenuWidget(QWidget):
    mode_selected = Signal(str)
    api_base_changed = Signal(str)

    def __init__(self, is_dark=False, api_base_url=DEFAULT_API_BASE_URL, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._current_page = "manager"
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

        manager_cards_data = [
            ("adapters", "Адаптеры", "", "adapter.png"),
            ("larix_set", "Наборы", "", "set.png"),
            ("matrix", "Матрицы", "", "matrix.png"),
            ("parameters", "Параметры", "", "parameters.png"),
        ]
        viewer_cards_data = [
            ("viewer", "Статусы", "", "status.png"),
            ("bim_sync", "BIM Sync", "", "sync.png"),
        ]

        self._pages_stack = QStackedWidget(self)
        self._pages_stack.addWidget(self._build_cards_page(manager_cards_data))
        self._pages_stack.addWidget(self._build_cards_page(viewer_cards_data))
        main_layout.addWidget(self._pages_stack, 1)

        page_switch_row = QHBoxLayout()
        page_switch_row.addStretch(1)
        self._page_switch = PageSwitchSlider(self._is_dark, self)
        self._page_switch.setFixedWidth(420)
        self._page_switch.page_clicked.connect(lambda pid: self._set_active_page(pid, animate=True))
        page_switch_row.addWidget(self._page_switch)
        page_switch_row.addStretch(1)
        main_layout.addLayout(page_switch_row)

        self._set_active_page("manager", animate=False)

        self._download_template_link = QLabel("<a href='download'>Скачать шаблон Excel</a>")
        self._download_template_link.setTextFormat(Qt.RichText)
        self._download_template_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self._download_template_link.setOpenExternalLinks(False)
        self._download_template_link.setCursor(QCursor(Qt.PointingHandCursor))
        self._download_template_link.linkActivated.connect(lambda _link: self._download_template())
        main_layout.addWidget(self._download_template_link, 0, Qt.AlignCenter)
        self._update_template_link_style()

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

    def _build_cards_page(self, cards_data):
        page = QWidget(self)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 12, 0, 0)
        page_layout.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(22)
        row.addStretch(1)
        for item in cards_data:
            mode_id, title, desc = item[:3]
            icon_name = item[3] if len(item) > 3 else None
            card = ModeCard(mode_id, title, desc, self._is_dark, self, icon_name=icon_name)
            card.setFixedSize(168, 156)
            card.clicked.connect(self._on_card_clicked)
            self._cards.append(card)
            row.addWidget(card)
        row.addStretch(1)
        page_layout.addLayout(row)

        page_layout.addStretch(1)
        return page

    def _set_active_page(self, page_id: str, animate: bool = False):
        normalized = "viewer" if str(page_id).strip().lower() == "viewer" else "manager"
        self._current_page = normalized
        if hasattr(self, "_pages_stack"):
            self._pages_stack.setCurrentIndex(1 if normalized == "viewer" else 0)
        try:
            if hasattr(self, "_page_switch"):
                self._page_switch.set_active_page(normalized, animate=bool(animate))
        except Exception:
            pass
        self._update_logo()

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
        try:
            if hasattr(self, "_page_switch"):
                self._page_switch.set_theme(bool(self._is_dark))
        except Exception:
            pass
        self._update_logo()
        self._update_template_link_style()
        try:
            self._set_connect_button_icon()
            self._set_api_status_icon(self._api_is_connected)
        except Exception:
            pass

    def _update_template_link_style(self):
        color = "#e0e0e0" if self._is_dark else "#303030"
        self._download_template_link.setStyleSheet("QLabel { font-size: 11pt; background: transparent; }")
        self._download_template_link.setText(
            f"<a href='download' style='color: {color}; text-decoration: underline;'>Скачать шаблон Excel</a>"
        )

    def _update_logo(self):
        if getattr(self, "_current_page", "manager") == "viewer":
            logo_path = get_viewer_logo_path(self._is_dark)
            fallback_text = "Larix Viewer"
            target_h = VIEWER_LOGO_HEIGHT
        else:
            logo_path = get_logo_path(self._is_dark)
            fallback_text = "Larix Manager"
            target_h = MANAGER_LOGO_HEIGHT
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = _trim_transparent_pixmap(pix)
            self._logo_label.setStyleSheet("")
            self._logo_label.setText("")
            self._logo_label.setPixmap(pix.scaledToHeight(target_h, Qt.SmoothTransformation))
        else:
            self._logo_label.setPixmap(QPixmap())
            self._logo_label.setText(fallback_text)
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


class BimSyncHostWidget(QWidget):
    def __init__(self, is_dark=False, parent=None):
        super().__init__(parent)
        self._is_dark = bool(is_dark)
        self._content_layout = QVBoxLayout(self)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._embedded_widget = None
        self._embedded_window = None

    def open_initial_mode(self) -> bool:
        return self._open_mode_dialog(initial=True)

    def _open_mode_dialog(self, initial: bool = False) -> bool:
        try:
            ModeSelectDialog = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "ModeSelectDialog")
            dialog = ModeSelectDialog(is_dark=self._is_dark, parent=self.window())
            if dialog.exec() != dialog.DialogCode.Accepted:
                return False
            self._is_dark = bool(getattr(dialog, "is_dark", self._is_dark))
            mode_id = str(getattr(dialog, "selected_mode", "") or "").strip().lower()
            return self._load_mode(mode_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть выбор режима BIM Sync:\n{e}")
            return False

    def _clear_embedded(self):
        if self._embedded_widget is not None:
            self._content_layout.removeWidget(self._embedded_widget)
            self._embedded_widget.setParent(None)
            self._embedded_widget = None
        self._embedded_window = None

    def _load_mode(self, mode_id: str) -> bool:
        try:
            if mode_id == "powerbi":
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "PowerBiExportWindow")
                win = WindowClass("csv")
            elif mode_id == "parquet":
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "PowerBiExportWindow")
                win = WindowClass("parquet")
            elif mode_id == "sqlite":
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "PowerBiExportWindow")
                win = WindowClass("sqlite")
            else:
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "BimSyncWindow")
                win = WindowClass()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить режим BIM Sync:\n{e}")
            return False

        try:
            if self._is_dark and hasattr(win, "_toggle_theme"):
                win._toggle_theme(True)
                if hasattr(win, "theme_toggle"):
                    win.theme_toggle.setChecked(True)
        except Exception:
            pass

        try:
            if hasattr(win, "back_requested"):
                win.back_requested.connect(self._handle_back_requested)
        except Exception:
            pass

        embedded = None
        try:
            embedded = win.takeCentralWidget() if hasattr(win, "takeCentralWidget") else None
        except Exception:
            embedded = None
        if embedded is None:
            try:
                embedded = win.centralWidget()
                if embedded is not None:
                    embedded.setParent(None)
            except Exception:
                embedded = None
        if embedded is None:
            QMessageBox.critical(self, "Ошибка", "Не удалось встроить интерфейс BIM Sync.")
            return False

        self._clear_embedded()
        self._embedded_window = win
        self._embedded_widget = embedded
        self._content_layout.addWidget(embedded)
        try:
            self.setWindowTitle((win.windowTitle() or "Larix BIM Sync").strip())
            self.setMinimumSize(win.minimumSize())
        except Exception:
            pass
        self.updateGeometry()
        return True

    def _handle_back_requested(self):
        if self._embedded_window is None:
            return
        try:
            self._is_dark = bool(getattr(self._embedded_window, "is_dark_theme", self._is_dark))
        except Exception:
            pass
        if not self._open_mode_dialog(initial=False):
            return

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Larix Manager")
        self.setMinimumSize(860, 640)
        self.resize(920, 700)
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
        self.setMinimumSize(860, 640)
        self.resize(920, 700)
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
        if mode_id == "bim_sync":
            self._open_bim_sync_dialog()
            return
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
                "bim_sync": "Larix Manager - BIM Sync",
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

    def _open_bim_sync_dialog(self):
        try:
            ModeSelectWidget = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "ModeSelectWidget")
            widget = ModeSelectWidget(is_dark=self._is_dark, parent=self)
            widget.mode_selected.connect(self._on_bim_sync_mode_selected)
            widget.back_requested.connect(self._show_main_menu)
            
            self._current_module_widget = widget
            self._current_module_window = None
            self.setCentralWidget(widget)
            self.setWindowTitle("Larix Manager - BIM Sync")
            self.setMinimumSize(600, 400)
            self.resize(700, 500)
            self._center_on_screen()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть BIM Sync:\n{e}")

    def _on_bim_sync_mode_selected(self, mode_id):
        try:
            mode_id = str(mode_id or "").strip().lower()
            if not mode_id:
                return
            
            self._is_dark = bool(getattr(self._current_module_widget, "is_dark", self._is_dark))
            
            if mode_id == "powerbi":
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "PowerBiExportWindow")
                win = WindowClass("csv")
            elif mode_id == "parquet":
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "PowerBiExportWindow")
                win = WindowClass("parquet")
            elif mode_id == "sqlite":
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "PowerBiExportWindow")
                win = WindowClass("sqlite")
            else:
                WindowClass = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "BimSyncWindow")
                win = WindowClass()
            
            if self._is_dark and hasattr(win, "_toggle_theme"):
                win._toggle_theme(True)
                if hasattr(win, "theme_toggle"):
                    win.theme_toggle.setChecked(True)
            
            if hasattr(win, "back_requested"):
                win.back_requested.connect(self._on_bim_sync_back)
            
            widget = win.takeCentralWidget() if hasattr(win, "takeCentralWidget") else None
            if widget is None:
                widget = win.centralWidget()
            if widget is None:
                QMessageBox.critical(self, "Ошибка", "Не удалось загрузить интерфейс BIM Sync.")
                return
            
            self._current_module_widget = widget
            self._current_module_window = win
            self.setCentralWidget(widget)
            self.setWindowTitle((win.windowTitle() or "Larix Manager - BIM Sync").strip())
            try:
                self.setMinimumSize(win.minimumSize())
                self.resize(win.size())
            except Exception:
                pass
            self._center_on_screen()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить режим BIM Sync:\n{e}")

    def _on_bim_sync_back(self):
        self._open_bim_sync_dialog()

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
            elif mode_id == "bim_sync":
                BimSyncWindow = _load_symbol_from_dir("viewer subd", "bim_sync_gui", "BimSyncWindow")
                win = BimSyncWindow()
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
