import sys

from PySide6.QtWidgets import QApplication

from shared.app_common import (
    AppMainWindow,
    ICON_DIR,
    _shutdown_api_check_threads,
    get_logo_path,
)
from shared.theme_toggle import enable_theme_sync
from shared.version import APP_VERSION, APP_VERSION_DATE, VERSION_HISTORY


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

MANAGER_MODULE_TITLES = {
    "adapters": "Larix — Создание адаптеров",
    "larix_set": "Larix — Создание наборов",
    "matrix": "Larix — Создание матриц",
    "parameters": "Larix — Проверка параметров",
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
        module_titles=MANAGER_MODULE_TITLES,
        show_template_download=True,
        app_version=APP_VERSION,
        app_version_date=APP_VERSION_DATE,
        app_version_history=VERSION_HISTORY,
    )
    window.show()

    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
