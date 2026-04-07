import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from shared.app_common import (
    AppMainWindow, get_logo_path, get_window_icon_path,
    _shutdown_api_check_threads, ICON_DIR, DEFAULT_API_BASE_URL,
    enable_theme_sync,
)
from shared.theme_toggle import theme, apply_dark_titlebar, load_saved_theme

APP_VERSION = "1.0.0"
APP_VERSION_DATE = "03.03.2026"
APP_VERSION_CHANGES = [
    "Разделение на два отдельных приложения: Manager и Viewer.",
]

MANAGER_CARDS = [
    ("adapters", "Адаптеры", "", "adapter.png"),
    ("larix_set", "Наборы", "", "set.png"),
    ("matrix", "Матрицы", "", "matrix.png"),
    ("parameters", "Параметры", "", "parameters.png"),
]

MANAGER_MODULE_LOADERS = {
    "adapters": ("Adapters", "ui", "MainWin", True),
    "larix_set": ("Sets", "ui", "ContentWidget", False),
    "matrix": ("Matrix", "ui", "MainWindow", True),
    "parameters": ("Validator", "ui", "MainWindow", True),
}


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

    window = AppMainWindow(
        app_title="Larix Plugin Manager",
        cards_data=MANAGER_CARDS,
        logo_func=get_logo_path,
        logo_height=64,
        module_loaders=MANAGER_MODULE_LOADERS,
        bim_sync=False,
        show_template_download=True,
        app_version=APP_VERSION,
        app_version_date=APP_VERSION_DATE,
        app_version_changes=APP_VERSION_CHANGES,
    )
    window.show()

    if hasattr(app, "exec"):
        sys.exit(app.exec())
    else:
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
