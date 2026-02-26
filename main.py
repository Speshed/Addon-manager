import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect, QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPixmap

from theme_toggle import (
    ThemeToggle, is_dark_theme, theme, resolve_icon_path, nik_icon, 
    load_saved_theme, enable_theme_sync, set_back_to_menu_callback
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "icon")

def get_logo_path(is_dark=False):
    app = QApplication.instance()
    name = "logo_white" if is_dark else "logo"
    return resolve_icon_path(name, ICON_DIR, app=app, tint_in_dark=False) or ""

def get_window_icon_path():
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
                bg = "#28241f"
                border = "#b86a15"
                title_color = "#e0e0e0"
                desc_color = "#b86a15"
            elif self._hovered:
                bg = "#252220"
                border = "#8a5520"
                title_color = "#e0e0e0"
                desc_color = "#888888"
            else:
                bg = "#1e1e1e"
                border = "#404040"
                title_color = "#e0e0e0"
                desc_color = "#888888"
        else:
            if self._selected:
                bg = "#faf5ef"
                border = "#c97a1c"
                title_color = "#222222"
                desc_color = "#b86a15"
            elif self._hovered:
                bg = "#fdf8f3"
                border = "#d99030"
                title_color = "#222222"
                desc_color = "#888888"
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

    def __init__(self, is_dark=False, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._cards = []
        self._setup_ui()

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

        btn_templates = QPushButton("Скачать шаблон")
        btn_templates.setMinimumWidth(200)
        btn_templates.clicked.connect(self._download_template)
        main_layout.addWidget(btn_templates, 0, Qt.AlignCenter)

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
        self.setMinimumSize(800, 600)
        self.resize(800, 600)
        self._is_dark = load_saved_theme(False)
        self._current_module_window = None
        self._current_module_widget = None
        
        try:
            app = QApplication.instance()
            theme(app, self._is_dark, icon_dir=ICON_DIR)
            self.setWindowIcon(nik_icon("app_icon", app=app, icon_dir=ICON_DIR))
        except Exception:
            pass

        set_back_to_menu_callback(self._show_main_menu)
        self._show_main_menu()

    def _show_main_menu(self):
        if self._current_module_widget is not None:
            self._current_module_widget = None
        self._current_module_window = None

        menu = MainMenuWidget(self._is_dark, self)
        menu.mode_selected.connect(self._on_mode_selected)
        if hasattr(menu, 'theme_toggle'):
            menu.theme_toggle.toggled.connect(self._on_theme_toggled)
        self.setCentralWidget(menu)
        self._menu_widget = menu
        self.setMinimumSize(800, 600)
        self.resize(800, 600)

    def _on_theme_toggled(self, dark: bool):
        self._is_dark = dark
        app = QApplication.instance()
        if app:
            theme(app, dark, icon_dir=ICON_DIR)

    def _on_mode_selected(self, mode_id: str):
        widget, window = self._create_module_widget(mode_id)
        if widget:
            self._current_module_widget = widget
            self._current_module_window = window
            self.setCentralWidget(widget)
            self.setMinimumSize(1200, 800)
            self.resize(1400, 900)

    def _create_module_widget(self, mode_id: str):
        try:
            if mode_id == "adapters":
                sys.path.insert(0, os.path.join(BASE_DIR, "Adapters"))
                from Adapter import MainWin
                win = MainWin()
                return win.centralWidget(), win
            elif mode_id == "larix_set":
                sys.path.insert(0, os.path.join(BASE_DIR, "Larix_Set"))
                from Larix_set import ContentWidget
                return ContentWidget(), None
            elif mode_id == "matrix":
                sys.path.insert(0, os.path.join(BASE_DIR, "Matrix"))
                from matrix_ui import MainWindow
                win = MainWindow()
                return win.centralWidget(), win
            elif mode_id == "parameters":
                sys.path.insert(0, os.path.join(BASE_DIR, "Parameter"))
                from Parameters import MainWindow
                win = MainWindow()
                return win.centralWidget(), win
            elif mode_id == "viewer":
                sys.path.insert(0, os.path.join(BASE_DIR, "Viewer"))
                from Viewer import MainWindow
                win = MainWindow()
                return win.centralWidget(), win
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить модуль {mode_id}:\n{e}")
            return None, None
        return None, None

def main():
    app = QApplication(sys.argv)
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
