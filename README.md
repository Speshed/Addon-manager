# Larix Addon Manager

Desktop-приложение на Python/PySide6 для работы с инструментами Larix и BIM-данными. В одном интерфейсе объединены управление профилями и настройками, просмотр статусов и инструменты синхронизации/экспорта данных.

## Возможности

- **Адаптеры** — настройка сопоставления параметров и формирование XML-адаптеров.
- **Наборы** — работа с наборами и профилями Larix, импорт данных из Excel/API.
- **Матрицы** — формирование матриц и профилей коллизий.
- **Параметры** — создание и проверка профилей параметров.
- **Статусы** — просмотр статусов объектов Larix.
- **BIM Sync** — получение BIM-данных и экспорт/синхронизация в CSV, Parquet, SQLite, SQL Server и сценарии Power BI.
- **Import XML** — отдельные инструменты импорта изменений из XML/Excel.
- Светлая и тёмная темы интерфейса.

## Требования

- Windows.
- Python 3.
- Зависимости из `requirements.txt`.
- Для работы с SQL Server требуется установленный совместимый ODBC Driver for SQL Server.

`pyarrow` используется для экспорта Parquet.

## Установка для разработки

```bat
py -3 -m venv .venv
.venv\Scripts\activate
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
```

## Запуск

Основная точка входа — объединённое приложение:

```bat
py -3 main.py
```

Отдельный Manager при необходимости можно запустить через:

```bat
py -3 manager_main.py
```

## Сборка EXE

Для сборки основной версии приложения используется:

```bat
build_main.bat
```

Результат сборки:

```text
dist\Larix_Main.exe
```

Каталоги `build/` и `dist/`, PyInstaller-spec-файлы, Python-кэши, логи и локальные выгрузки исключены из Git через `.gitignore`.

## Структура проекта

```text
.
├── main.py                    # Основное объединённое приложение
├── manager_main.py            # Отдельная точка входа Manager
├── build_main.bat             # Сборка Larix_Main.exe
├── requirements.txt           # Python-зависимости
├── Adapters/                  # Адаптеры
├── Sets/                      # Наборы
├── Matrix/                    # Матрицы
├── Validator/                 # Параметры / валидация
├── Viewer/                    # Статусы и Viewer
├── Sync/                      # BIM Sync и экспорт данных
├── shared/                    # Общие UI-компоненты и утилиты
├── importxml/                 # Импорт XML/Excel
├── icon/                      # Общие ресурсы интерфейса
└── docs/
    └── project-architecture.md
```

## Архитектура

Подробное описание модулей, связей и ограничений проекта находится в [`docs/project-architecture.md`](docs/project-architecture.md).

## Что не должно попадать в репозиторий

- `build/`, `dist/` и `*.spec`;
- `__pycache__/`, `*.pyc` и кэши инструментов;
- логи и HAR-файлы;
- локальные SQLite/DB-файлы;
- пользовательские выгрузки BIM Sync;
- `.env` и другие локальные файлы с настройками/секретами.

## Основной стек

Python, PySide6, pandas, requests, openpyxl, pyodbc, tenacity, pyarrow, PyInstaller.
