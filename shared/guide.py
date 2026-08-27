# -*- coding: utf-8 -*-
"""Small in-app guides for the main Larix Manager sections."""
from __future__ import annotations

import os

try:
    from PySide6 import QtWidgets, QtGui, QtCore  # type: ignore
except Exception:  # pragma: no cover - compatibility fallback
    from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore


_GUIDES = {'adapters': {'title': 'Справка — Адаптеры',
              'intro': 'Ключевые правила, которые влияют на результат адаптации и дальнейшее использование параметров.',
              'steps': (),
              'rules': ('Итоговый код формируется как «Группа параметров.Наименование параметра». Например BIM + '
                        'Стадия проекта → BIM.Стадия проекта.',
                        '«Список параметров» — возможные исходные параметры модели. Он не используется для '
                        'сопоставления с LOI.',
                        'Колонка «Параметры» — ключ автосопоставления LOI. Значение должно совпадать с названием '
                        'LOI-заголовка; итоговый адаптированный параметр при этом может называться совершенно иначе.',
                        'Если «Параметры» пусто, при импорте сопоставления используется «Наименование параметра» как '
                        'запасной ключ. Надёжнее заполнять колонку явно.',
                        'Если несколько строк имеют одинаковое значение в «Параметры», более поздняя строка заменит '
                        'более раннее сопоставление.',
                        '«Тип параметра = Число» передаётся в проверку параметров как числовой тип.'),
              'tips': ('Пример из демо: LOI «Фаза» → «Параметры = Фаза» → BIM.Стадия проекта. Название «Стадия '
                       'проекта» специально отличается от LOI.',
                       'Кнопка «Из адаптера» в фильтрах Матриц и Параметров выбирает итоговый код адаптера; колонка '
                       '«Параметры» в этом сценарии не участвует.',
                       'Один лист адаптера может содержать несколько групп параметров.')},
 'sets': {'title': 'Справка — Наборы',
          'intro': 'Нюансы структуры и фильтров, которые полезно учитывать при подготовке Excel.',
          'steps': (),
          'rules': ('Префиксы «01_...», «01.01_...», «01.01.01_...» задают уровни вложенности. Родитель определяется '
                    'по числовому префиксу.',
                    'Несколько значений в одной ячейке фильтра можно разделять запятой, точкой с запятой, переносом '
                    'строки, «|», «/» или «\\».',
                    'Строка без значений фильтра, в названии которой есть слово «Раздел», используется как раздел '
                    'структуры.',
                    'При выборе нескольких листов режим «Объединить» создаёт один профиль; без него каждый лист '
                    'становится отдельным профилем.'),
          'tips': ('Для каждого параметра из Excel поле Larix можно выбрать вручную, через API или через «Из адаптера».',
                   'Если в выбранной книге есть лист «Адаптер», окно «Из адаптера» сразу использует эту же книгу; отдельный файл выбирать не нужно.',
                   '«Из адаптера» подставляет итоговый код, например BIM.Стадия проекта. Колонка «Параметры» здесь не участвует — она нужна для автоматического сопоставления LOI в разделе «Параметры».',
                   'Листы «Набор 1» и «Набор 2» в демо подходят одновременно для Наборов и Параметров.',)},
 'matrix': {'title': 'Справка — Матрицы',
            'intro': 'Правила чтения матрицы и связи с листом наборов.',
            'steps': (),
            'rules': ('Имена в строках и столбцах матрицы должны совпадать с «Имя набора» на выбранном листе наборов.',
                      'Если набор из матрицы отсутствует на листе наборов, проверка создастся, но для этого набора не '
                      'будет сформирован фильтр.',
                      'A/B/C — пересечения с тремя настраиваемыми допусками; D — дублирование; «D/B» создаёт обе '
                      'проверки.',
                      'Пара A ↔ B рассматривается как одна и та же независимо от направления. Заполнять зеркальную '
                      'половину матрицы не требуется; конфликтующие значения в зеркальных ячейках лучше не задавать.',
                      'Используйте только A, B, C и D. Другие обозначения не создают нового типа проверки и могут быть '
                      'интерпретированы как обычное пересечение.',
                      'Несколько выбранных листов матриц всегда остаются отдельными профилями внутри одного '
                      '.cv-файла.'),
            'tips': ('Параметр фильтра можно выбрать из адаптера. В демо для этого есть «Классификатор.Код элемента».',
                     '«Из адаптера» выбирает итоговый адаптированный код; LOI-связь из колонки «Параметры» здесь не '
                     'используется.')},
 'parameters': {'title': 'Справка — Параметры',
                'intro': 'Неочевидные правила сопоставления LOI, структуры и работы с несколькими листами.',
                'steps': (),
                'rules': ('«Импорт адаптера» сопоставляет LOI по колонке «Параметры» листа адаптера. Например LOI '
                          '«Фаза» + «Параметры = Фаза» → BIM.Стадия проекта.',
                          'Название итогового параметра не обязано совпадать с LOI. «Список параметров» при таком '
                          'сопоставлении вообще не участвует.',
                          'LOI без совпадения в адаптере остаётся доступным для ручного сопоставления.',
                          'Если один и тот же LOI-заголовок встречается на нескольких выбранных листах книги, для него '
                          'используется одно общее сопоставление.',
                          'Классификационная структура: «01_Раздел» → «01.01_Подраздел» → «01.01.01_Группа». Родитель '
                          'определяется по ближайшему существующему коду.',
                          'Ручная структура: «# / ## / ###» или «1# / 2# / 3#». Если родитель уровня не найден, '
                          'приложение предупреждает и использует ближайший доступный уровень.',
                          'Обычная текстовая строка внутри классификационного раздела становится отдельным уровнем; '
                          'последующий «# ...» вкладывается уже в эту строку.',
                          'Структурный код в названии строки и столбец «Код по классификатору» независимы: первый '
                          'строит дерево, второй задаёт значение фильтра.',
                          'При нескольких листах можно создать отдельные профили или объединить все выбранные листы в '
                          'один профиль.'),
                'tips': ('В демо итоговые имена специально отличаются: «Фаза» → BIM.Стадия проекта, «Производитель» → '
                         'BIM.Изготовитель, «Комплект документации» → Larix.Комплект чертежей.',
                         'Для параметров, которые появляются только после адаптации, фильтр можно заполнить через «Из '
                         'адаптера...».')}}


class GuideDialog(QtWidgets.QDialog):
    def __init__(self, topic: str, parent=None):
        super().__init__(parent)
        cfg = _GUIDES.get(topic) or _GUIDES["parameters"]
        self.setWindowTitle(cfg["title"])
        self.resize(720, 560)
        self.setModal(False)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QtWidgets.QLabel(cfg["title"])
        f = title.font()
        f.setPointSize(max(14, f.pointSize() + 4))
        f.setBold(True)
        title.setFont(f)
        root.addWidget(title)

        browser = QtWidgets.QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setFrameShape(QtWidgets.QFrame.NoFrame)
        steps = "".join(f"<li>{s}</li>" for s in cfg.get("steps", ()))
        rules = "".join(f"<li>{s}</li>" for s in cfg.get("rules", ()))
        tips = "".join(f"<li>{s}</li>" for s in cfg.get("tips", ()))
        parts = [
            "<div style='font-size: 11pt; line-height: 1.45'>",
            f"<p>{cfg['intro']}</p>",
            "<h3>Как пользоваться</h3>",
            f"<ol>{steps}</ol>",
        ]
        if rules:
            parts.extend(("<h3>Правила и важные моменты</h3>", f"<ul>{rules}</ul>"))
        if tips:
            parts.extend(("<h3>Полезно знать</h3>", f"<ul>{tips}</ul>"))
        parts.append("</div>")
        browser.setHtml("".join(parts))
        root.addWidget(browser, 1)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        close_btn = buttons.button(QtWidgets.QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Закрыть")
        buttons.rejected.connect(self.close)
        buttons.accepted.connect(self.close)
        root.addWidget(buttons)


def _find_info_icon(icon_dir: str) -> str:
    for name in ("circle-info.png", "circle-info.ico", "info.png"):
        p = os.path.join(icon_dir, name)
        if os.path.exists(p):
            return p
    return ""


def create_guide_button(parent, topic: str, *, icon_dir: str) -> QtWidgets.QPushButton:
    """Create the shared «Справка» button for a main section."""
    btn = QtWidgets.QPushButton("Справка", parent)
    btn.setObjectName("guideInfoButton")
    btn.setToolTip("Как пользоваться этим разделом")
    # Keep this as a regular application button so it inherits the same
    # border, background, hover and pressed states as the rest of the UI.
    btn.setMinimumHeight(34)
    btn.setMinimumWidth(108)
    btn.setFlat(False)
    btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
    icon_path = _find_info_icon(icon_dir)
    if icon_path:
        btn.setIcon(QtGui.QIcon(icon_path))
        btn.setIconSize(QtCore.QSize(18, 18))
    else:
        try:
            btn.setIcon(parent.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation))
            btn.setIconSize(QtCore.QSize(18, 18))
        except Exception:
            pass

    def _open():
        dlg = GuideDialog(topic, parent)
        # Keep a reference so a modeless dialog cannot be garbage-collected.
        setattr(parent, "_larix_guide_dialog", dlg)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    btn.clicked.connect(_open)
    return btn
