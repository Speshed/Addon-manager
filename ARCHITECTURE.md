# Addon Manager - Архитектура приложения

## Обзор

Addon Manager - десктопное приложение на Python/PySide6 для управления адаптерами, параметрами, профилями BIM-моделирования и синхронизацией nativeId. Приложение поддерживает светлую/тёмную тему и предоставляет модульную структуру для различных задач.

---

## Структура файлов

```
Addon manager/
├── main.py                    # Точка входа, диалог выбора режима
├── theme_toggle.py            # Компоненты темы и навигации
├── Excel_template.py          # Экспорт данных в Excel
├── ARCHITECTURE.md            # Этот файл
│
├── icon/                      # Иконки приложения (общие)
│   ├── Manager-scaled.png     # Логотип (светлый)
│   ├── Manager-scaled_white.png # Логотип (тёмный)
│   ├── sun.png / moon.png     # Иконки переключателя темы
│   └── ...                    # Прочие иконки UI
│
├── Adapters/
│   ├── __init__.py
│   └── Adapter.py             # Редактор адаптеров
│
├── Parameter/
│   ├── __init__.py
│   ├── Parameters.py          # Управление параметрами
│   └── icon/                  # Иконки модуля параметров
│
├── Matrix/
│   ├── __init__.py
│   └── matrix_ui.py           # Генератор матриц коллизий
│
├── Larix_Set/
│   ├── __init__.py
│   └── Larix_set.py           # Настройка профилей Larix
│
└── Viewer/
    ├── __init__.py
    ├── Viewer.py              # BIM Sync Tool (синхронизация nativeId)
    └── icon/                  # Иконки модуля Viewer
```

---

## Модули

### 1. main.py — Точка входа
**Назначение:** Диалог выбора режима работы

**Классы:**
- `ModeCard` — Карточка режима с анимацией hover/selection
- `AnimatableShadowEffect` — Анимированная тень для карточек
- `ModeSelectDialog` — Диалог с 5 режимами работы
- `run_module()` — Запуск выбранного модуля через subprocess

**Режимы:**
| ID | Название | Модуль |
|----|----------|--------|
| `adapters` | Адаптеры | `Adapters/Adapter.py` |
| `larix_set` | Larix Set | `Larix_Set/Larix_set.py` |
| `matrix` | Matrix | `Matrix/matrix_ui.py` |
| `parameters` | Параметры | `Parameter/Parameters.py` |
| `viewer` | Viewer | `Viewer/Viewer.py` |

---

### 2. theme_toggle.py — Общие компоненты
**Назначение:** Переиспользуемые UI-компоненты для всех модулей

**Компоненты:**
- `ThemeToggle` — Анимированный переключатель светлая/тёмная тема
- `create_back_button()` — Кнопка возврата в главное меню
- `go_to_main_menu()` — Навигация обратно в main.py
- `apply_theme()` — Применение темы к приложению
- `is_dark_theme()` — Проверка текущей темы
- `LIGHT_QSS` / `get_dark_qss()` — Стили для тем
- `resolve_icon_path()` — Разрешение пути к иконке с учётом темы
- `nik_icon()` — Получение иконки с авто-тонированием
- `_ensure_white_copy()` / `_ensure_black_copy()` — Создание тонированных копий иконок
- `_tint_pixmap()` — Тонирование QPixmap указанным цветом

**Цветовая палитра (PALETTE):**
- Акцент: `#F7921E` (оранжевый)
- Hover: `#FFA74B`
- Selected: `#FFC37A`
- Soft hover: `#FFE3C2`

**Поведение иконок:**
- Иконки автоматически тонируются под тему (белый для тёмной, чёрный для светлой)
- Исключения (не тонируются): logo, ok, none, warning, refresh, gear, folder

---

### 3. Excel_template.py — Экспорт в Excel
**Назначение:** Генерация Excel-файлов с форматированием

**Функции:**
- `export_common_excel()` — Экспорт данных в формат Excel
- Встроенные JSON-шаблоны для наборов матриц и параметров

**Данные:**
- Наборы для матриц (АР, КР, ВИС, ГП, НИС)
- Матрица коллизий
- Коды классификатора
- Параметры LOI

---

### 4. Adapters/Adapter.py — Редактор адаптеров
**Назначение:** Создание и редактирование адаптеров для связи атрибутов с параметрами моделей

**Классы:**
- `MainWin` — Главное окно редактора
- `AdapterDoc` — Документ адаптера (XML-сериализация)
- `Binding` — Привязка параметра к атрибуту
- `BindingQueue` — Очередь привязок для атрибута
- `TransformSettings` — Настройки преобразования данных
- `TransformDialog` — Диалог настройки преобразований
- `ModelFilterDialog` — Фильтр по моделям
- `RowDragTable` — Таблица с drag&drop строк

**API функции:**
- `api_get_projects()` — Получение списка проектов
- `api_get_containers()` — Получение контейнеров проекта
- `api_get_params_for_container()` — Параметры контейнера
- `api_get_global_component()` — Глобальный компонент

**Формат данных:** XML (`Adapter.xml`)

---

### 5. Parameter/Parameters.py — Управление параметрами
**Назначение:** Генерация профилей валидации параметров из Excel

**Классы:**
- `ThemeSwitch` — Переключатель темы (локальный)
- `_MappingRow` — Строка сопоставления параметров

**Функции:**
- `excel_to_pv_profile()` — Генерация PV-профиля из Excel
- `fetch_api_param_types()` — Получение типов параметров из API
- `fetch_global_component()` — Загрузка глобального компонента
- `save_session_mapping_json()` / `load_session_mapping_json()` — Сохранение/загрузка маппинга

**Режимы:**
- `MODE_CATEGORY` — По категориям
- `MODE_CLASSIFIER` — По классификатору
- `MODE_BOTH` — Комбинированный

---

### 6. Matrix/matrix_ui.py — Генератор матриц коллизий
**Назначение:** Создание профилей коллизий из Excel-матриц

**Классы:**
- `MainWindow` — Главное окно
- `Section` — Композитная секция UI
- `GeneratorWorker` — Worker для генерации в отдельном потоке (QThread)

**XML-шаблоны:**
- `XML_TEMPLATE` — Корневой шаблон профиля
- `FOLDER_TEMPLATE` — Шаблон папки
- `ITEM_TEMPLATE` — Шаблон элемента коллизии

**Параметры:**
- Допуски A/B/C (в метрах)
- Параметр фильтрации (по умолчанию `Категория:\`)

---

### 7. Larix_Set/Larix_set.py — Настройка профилей
**Назначение:** Управление профилями и синхронизация

**Встроенные компоненты стиля (nik_style):**
- `Palette` — Цветовая палитра
- `SyncBadgeTreeDelegate` — Делегат с badge синхронизации
- `TreeBranchProxyStyle` — Стиль веток дерева
- `StatusIndicator` — Индикатор статуса
- `compose_badged_icon()` — Создание иконки с badge

**Иконки:**
- Полный реестр PNG-иконок из Dekstop-manager
- Автоматическое перекрашивание под тему

---

### 8. Viewer/Viewer.py — BIM Sync Tool
**Назначение:** Синхронизация nativeId между внешним Viewer API и локальным сервером

**Классы:**
- `MainWindow` — Главное окно синхронизации
- `ThemeSwitch` — Локальный переключатель темы (наследует QAbstractButton)

**Функции:**
- `api_get()` — Универсальный GET-запрос с обработкой ошибок
- `normalize_name()` — Нормализация имени для сопоставления (удаление расширений, регистра, спецсимволов)
- `apply_themed_icon()` — Применение тонированной иконки к виджету
- `apply_themed_icon_with_arrow()` — Иконка с hover-эффектом
- `set_header_logo()` — Установка логотипа в заголовок
- `show_error_dialog()` — Диалог ошибки

**Алгоритм синхронизации (start_sync):**
1. Получение nativeId из внешнего Viewer API по выбранному атрибуту
2. Загрузка элементов из локальных контейнеров
3. Сопоставление элементов по nativeId
4. Создание параметра (если не существует)
5. Обновление значений параметров через batch-запросы (по 50 элементов)

**UI компоненты:**
- Секция авторизации (токен Bearer)
- Секция моделей вьювера (проект → модели с чекбоксами)
- Секция атрибутов (схема → атрибут)
- Секция локальных контейнеров с подсветкой совпадений
- Автоматическая сортировка контейнеров по совпадению имён

**Специфичные иконки Viewer:**
- `1.png`, `2.png` — Нумерация
- `extend.png` — Расширение
- `arrow-oba.png` — Стрелка
- `navigation.png`, `move.png`, `compare.png` — Навигация

---

## Навигация между модулями

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│              (ModeSelectDialog)                     │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────┬───────┼───────┬───────┐
        │       │       │       │       │
        ▼       ▼       ▼       ▼       ▼
┌───────────┐┌───────────┐┌───────────┐┌───────────┐┌───────────┐
│ Adapters  ││  Matrix   ││ Parameter ││ Larix_Set ││  Viewer   │
│           ││           ││           ││           ││           │
│ [← Back]  ││ [← Back]  ││ [← Back]  ││ [← Back]  ││ [← Back]  │
└─────┬─────┘└─────┬─────┘└─────┬─────┘└─────┬─────┘└─────┬─────┘
      │            │            │            │            │
      └────────────┴────────────┴────────────┴────────────┘
                              │
                              ▼
                      go_to_main_menu()
                      → main.py
```

---

## Зависимости

### Обязательные:
- Python 3.10+
- PySide6 (или PyQt5 как fallback)

### Опциональные:
- `pandas` — Работа с Excel
- `openpyxl` — Экспорт в Excel
- `requests` — HTTP-запросы к API

---

## API endpoints

### Локальный сервер (Base URL: http://localhost:5000)

```
GET /api/project/projects                    — Список проектов
GET /api/imcContainer/getProjectImcContainers/{id} — Контейнеры проекта
GET /api/imcParameterDefinition/imcParameterDefinitions?containerIds=... — Параметры
GET /api/globalComponent/globalComponent/{id} — Глобальный компонент
GET /api/imcElement/imcElements/{containerId} — Элементы контейнера
PUT /api/imcElement/imcElements              — Batch-обновление элементов
```

### Внешний Viewer API (Base URL: https://bwv.testing.bim-info.ru)

```
GET /api/projects/all                        — Список всех проектов
GET /api/jimc/projectid?projectId={id}      — Модели проекта (jimc)
GET /api/attribute-schema/projectid-jimcid   — Схемы атрибутов
GET /api/attribute/attributeschemaid-jimcid  — Атрибуты схемы
GET /api/attribute-value/jimcid-attributeid  — Значения атрибута (с nativeId)
```

---

## Форматы файлов

| Расширение | Описание |
|------------|----------|
| `.xml` | Адаптеры, профили валидации |
| `.cv` | Профили коллизий (XML-формат) |
| `.xlsx/.xls` | Исходные данные Excel |
| `.json` | Маппинги параметров |

---

## Ключевые паттерны

1. **Тема:** Все модули используют `theme_toggle.py` для единообразного UI
2. **Навигация:** Кнопка "Назад" через `create_back_button()` + `go_to_main_menu()`
3. **Сериализация:** XML для адаптеров и профилей
4. **Асинхронность:** `QThread` + `GeneratorWorker` для длительных операций
5. **Стилизация:** QSS с PNG-иконками, адаптивными под тему
6. **Сопоставление имён:** `normalize_name()` для нечёткого сравнения названий моделей и контейнеров
