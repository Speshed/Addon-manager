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

import pandas as pd
from collections import defaultdict, Counter

# ----- Style constants (Adapter Editor) -----
BG = "#FFFFFF"
FG = "#222222"
ACCENT = "#F7921E"
ACCENT_HOVER = "#FFA74B"
BORDER = "#dcdcdc"
HEADER_BG = "#f5f5f5"

# ---- resource helpers (as in AddUser) ----
def rsrc_path(*segments: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *segments)

def first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

ICON_DIR = rsrc_path("icon")
LOGO_PATH = resolve_icon_path("logo", ICON_DIR, tint_in_dark=False) or ""

# icons and arrow resources
ARROW_DOWN_PATH = resolve_icon_path("arrow_down", ICON_DIR, tint_in_dark=False) or ""
ARROW_UP_PATH = resolve_icon_path("arrow_up", ICON_DIR, tint_in_dark=False) or ""
ARROW_LEFT_PATH = resolve_icon_path("arrow_left", ICON_DIR, tint_in_dark=False) or ""
ARROW_RIGHT_PATH = resolve_icon_path("arrow_right", ICON_DIR, tint_in_dark=False) or ""
SUN_ICON_CANDIDATES = [resolve_icon_path("sun", ICON_DIR, tint_in_dark=False) or ""]
MOON_ICON_CANDIDATES = [resolve_icon_path("moon", ICON_DIR, tint_in_dark=False) or ""]

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
              <ConditionsBlock Type="Single" LogicalOperator="And" IsNegative="false" IsEnabled="true">
                <Signal>
                  <Messages />
                </Signal>
                <Condition FieldName="{param_field}" FieldIsNumeric="false" Operator="Equal" Value="{value1}" TextCaseSensitive="false" TextSpaceSensitive="false" IsUndefinedFieldName="false">
                  <Signal>
                    <Messages />
                  </Signal>
                </Condition>
                <ConditionsBlocks />
              </ConditionsBlock>
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
              <ConditionsBlock Type="Single" LogicalOperator="And" IsNegative="false" IsEnabled="true">
                <Signal>
                  <Messages />
                </Signal>
                <Condition FieldName="{param_field}" FieldIsNumeric="false" Operator="Equal" Value="{value2}" TextCaseSensitive="false" TextSpaceSensitive="false" IsUndefinedFieldName="false">
                  <Signal>
                    <Messages />
                  </Signal>
                </Condition>
                <ConditionsBlocks />
              </ConditionsBlock>
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
              <ConditionsBlock Type="Single" LogicalOperator="And" IsNegative="false" IsEnabled="true">
                <Signal>
                  <Messages />
                </Signal>
                <Condition FieldName="{param_field}" FieldIsNumeric="false" Operator="Equal" Value="{value1}" TextCaseSensitive="false" TextSpaceSensitive="false" IsUndefinedFieldName="false">
                  <Signal>
                    <Messages />
                  </Signal>
                </Condition>
                <ConditionsBlocks />
              </ConditionsBlock>
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
              <ConditionsBlock Type="Single" LogicalOperator="And" IsNegative="false" IsEnabled="true">
                <Signal>
                  <Messages />
                </Signal>
                <Condition FieldName="{param_field}" FieldIsNumeric="false" Operator="Equal" Value="{value2}" TextCaseSensitive="false" TextSpaceSensitive="false" IsUndefinedFieldName="false">
                  <Signal>
                    <Messages />
                  </Signal>
                </Condition>
                <ConditionsBlocks />
              </ConditionsBlock>
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
                 profile_title: str, param_field: str):
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

    def letter_to_value(self, letter: str) -> float:
        letter = str(letter).strip().upper()
        mapping = {"A": self.map_a, "B": self.map_b, "C": self.map_c}
        return mapping.get(letter, self.map_a)

    def run(self):
        try:
            self.log.emit("Чтение файла наборов...")
            df_nabory = pd.read_excel(self.nabory_path, sheet_name=self.sheet_nabory)
            if 'Имя набора' not in df_nabory.columns:
                raise ValueError("В файле наборов не найден столбец 'Имя набора'")
            if 'Описание' not in df_nabory.columns:
                df_nabory['Описание'] = df_nabory['Имя набора']

            df_nabory.dropna(subset=['Имя набора'], inplace=True)
            category_map = {}
            prefix_map = {}

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

            self.log.emit("Чтение матрицы...")
            df_matrix = pd.read_excel(self.matrix_path, sheet_name=self.sheet_matrix, header=None)

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

            # Group by prefixes from 'Наборы' (без номеров)
            groups = defaultdict(list)
            for name in category_map.keys():
                groups[prefix_map[name]].append(name)

            prefixes = sorted(groups.keys())

            # Присвоим каждому префиксу «мажорный» номер (из кода 1.01 -> 1). Берём самый частый, при равенстве — минимальный.
            prefix_majors = {}
            tmp = {}
            for name in category_map.keys():
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

            param_field_xml = xml_attr_escape(self.param_field)

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
                                    value1 = category_map.get(set1, set1)
                                    value2 = category_map.get(set2, set2)
                                    admission_value = self.letter_to_value(letter)

                                    item_xml = ITEM_TEMPLATE.format(
                                        id=item_counter,
                                        parent_id=folder_counter,
                                        title=title,
                                        value1=value1,
                                        value2=value2,
                                        admission_value=admission_value,
                                        param_field=param_field_xml
                                    )
                                    items_intersection.append(item_xml)
                                    item_counter += 1

                                elif validation_type == 'duplication':
                                    key = tuple(sorted([set1, set2])) + ('duplication',)
                                    if key in added_pairs_duplication:
                                        continue
                                    added_pairs_duplication.add(key)

                                    title = f"{display_name(set1)} ~ {display_name(set2)}"
                                    value1 = category_map.get(set1, set1)
                                    value2 = category_map.get(set2, set2)
                                    admission_value = 0.0

                                    item_xml = ITEM_TEMPLATE_DUPLICATION.format(
                                        id=item_counter,
                                        parent_id=folder_counter + 1,
                                        title=title,
                                        value1=value1,
                                        value2=value2,
                                        admission_value=admission_value,
                                        param_field=param_field_xml
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
        outer.setSpacing(6)

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
        self.frame_l.setContentsMargins(10, 10, 10, 10)

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
        self.setWindowTitle("Матрица коллизий - Генератор профилей")
        self.resize(960, 628)
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

    def _build_ui(self):
        cw = QtWidgets.QWidget()
        self.setCentralWidget(cw)
        root = QtWidgets.QVBoxLayout(cw)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

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

        # Server/Host section (for future API usage)
        self.sec_server = Section("Сервер", self)
        sl = self.sec_server.frame_l
        self.ed_host = QtWidgets.QLineEdit("http://127.0.0.1")
        self.spin_port = QtWidgets.QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(5000)
        self.spin_port.setFixedWidth(100)
        # Keep arrows visible but visually match Host input
        try:
            self.spin_port.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
            self.spin_port.setAlignment(QtCore.Qt.AlignLeft)
        except Exception:
            pass
        sl.addWidget(QtWidgets.QLabel("Host:"), 0, 0)
        sl.addWidget(self.ed_host, 0, 1)
        sl.addWidget(QtWidgets.QLabel("Порт:"), 0, 2)
        sl.addWidget(self.spin_port, 0, 3)
        root.addWidget(self.sec_server)

        # ------ Секция Файлы ------
        self.sec_files = Section("Файлы", self)
        l = self.sec_files.frame_l

        # Наборы
        self.ed_nabory = QtWidgets.QLineEdit()
        self.btn_nabory = QtWidgets.QPushButton("Выбрать...")
        self.btn_nabory.clicked.connect(self._pick_nabory)
        l.addWidget(QtWidgets.QLabel("Наборы для коллизий.xlsx"), 1, 0)
        l.addWidget(self.ed_nabory, 1, 1)
        l.addWidget(self.btn_nabory, 1, 2)

        self.cb_sheet_nabory = QtWidgets.QComboBox()
        self.cb_sheet_nabory.setEditable(True)
        self.cb_sheet_nabory.lineEdit().setPlaceholderText("не выбрано")
        self.cb_sheet_nabory.setCurrentIndex(-1)
        self.cb_sheet_nabory.setFixedWidth(160)
        spn = self.cb_sheet_nabory.sizePolicy()
        spn.setHorizontalPolicy(QtWidgets.QSizePolicy.Fixed)
        self.cb_sheet_nabory.setSizePolicy(spn)
        l.addWidget(QtWidgets.QLabel("Лист:"), 2, 0)
        l.addWidget(self.cb_sheet_nabory, 2, 1)

        # Матрица
        self.ed_matrix = QtWidgets.QLineEdit()
        self.btn_matrix = QtWidgets.QPushButton("Выбрать...")
        self.btn_matrix.clicked.connect(self._pick_matrix)
        l.addWidget(QtWidgets.QLabel("Матрица коллизий.xlsx"), 3, 0)
        l.addWidget(self.ed_matrix, 3, 1)
        l.addWidget(self.btn_matrix, 3, 2)

        self.cb_sheet_matrix = QtWidgets.QComboBox()
        self.cb_sheet_matrix.setEditable(True)
        self.cb_sheet_matrix.lineEdit().setPlaceholderText("не выбрано")
        self.cb_sheet_matrix.setCurrentIndex(-1)
        self.cb_sheet_matrix.setFixedWidth(160)
        spm = self.cb_sheet_matrix.sizePolicy()
        spm.setHorizontalPolicy(QtWidgets.QSizePolicy.Fixed)
        self.cb_sheet_matrix.setSizePolicy(spm)
        l.addWidget(QtWidgets.QLabel("Лист:"), 4, 0)
        l.addWidget(self.cb_sheet_matrix, 4, 1)

        # Выход
        self.ed_output = QtWidgets.QLineEdit()
        self.btn_output = QtWidgets.QPushButton("Выбрать...")
        self.btn_output.clicked.connect(self._pick_output)
        l.addWidget(QtWidgets.QLabel("Выходной файл (.cv/.xml)"), 5, 0)
        l.addWidget(self.ed_output, 5, 1)
        l.addWidget(self.btn_output, 5, 2)

        # Название профиля
        self.ed_title = QtWidgets.QLineEdit()
        self.ed_title.setPlaceholderText("Матрица")
        l.addWidget(QtWidgets.QLabel("Название профиля"), 0, 0)
        l.addWidget(self.ed_title, 0, 1, 1, 2)

        root.addWidget(self.sec_files)

        # ------ Секция Допуски ------
        self.sec_tol = Section("Допуски", self)
        p = self.sec_tol.frame_l
        p.setHorizontalSpacing(12)

        # Параметр фильтрации
        lbl_param = QtWidgets.QLabel("Параметр фильтрации")
        self.cb_param = QtWidgets.QComboBox()
        self.cb_param.setEditable(True)
        # Предустановки
        self.cb_param.addItems(["Категория:\\"])
        self.cb_param.setEditText("Категория:\\")  # по умолчанию правильный вариант с обратным слэшем
        self.cb_param.setFixedWidth(200)
        p.addWidget(lbl_param, 3, 0)
        p.addWidget(self.cb_param, 3, 1, 1, 2)

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

        # Нижняя строка: поля
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
        # ������ ���������� ������ �� �������

        # Статус бар
        self.status = self.statusBar()
        self.status.showMessage("Готово")

    # ---------------------------------
    # Helpers
    # ---------------------------------
    def _load_logo_pixmap(self) -> QtGui.QPixmap | None:
        candidates = [
            LOGO_PATH,
            os.path.join(os.path.dirname(sys.argv[0]), "Manager-scaled.png"),
            os.path.join(os.path.dirname(__file__), "Manager-scaled.png"),
        ]
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
                cands = [
                    rsrc_path("icon", "Manager-scaled_white.png"),
                    os.path.join(base_dir, "icon", "Manager-scaled_white.png"),
                    os.path.join(base_dir, "Manager-scaled_white.png"),
                ]
            else:
                cands = [
                    rsrc_path("icon", "Manager-scaled.png"),
                    os.path.join(base_dir, "icon", "Manager-scaled.png"),
                    os.path.join(base_dir, "Manager-scaled.png"),
                ]
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
        bcol = getattr(self, "_BG", BG)
        fcol = getattr(self, "_FG", FG)
        dark = str(bcol).lower() in ("#1e1e1e", "#171717", "#202020", "#121212")

        arrow_path = _resolve_arrow_path(__file__)
        arrow_url = _white_variant_for_qss(arrow_path) if dark else (arrow_path or "arrow-down.png")
        arrow_url = (arrow_url or "arrow-down.png").replace("\\", "/")
        spin_up = ARROW_UP_PATH or ""
        spin_down = ARROW_DOWN_PATH or ""
        if dark:
            if spin_up:
                spin_up = _white_variant_for_qss(spin_up)
            if spin_down:
                spin_down = _white_variant_for_qss(spin_down)
        spin_up = (spin_up or "arrow-up.png").replace("\\", "/")
        spin_down = (spin_down or "arrow-down.png").replace("\\", "/")

        css = []
        css.append("QPushButton#btn_login, QPushButton#btn_generate { font-size: 16px; }")
        css.append(f"QWidget {{ color: {fcol}; background: {bcol}; font-family: 'Segoe UI'; font-size: 10pt; }}")

        # Header bar and sections
        # no framed header bar
        css.append(f"QLabel#sectionTitle {{ font-size: 10pt; font-weight: 600; background: {bcol}; padding: 0 8px; border-radius: 6px; color: {fcol}; }}")
        css.append(f"QFrame#sectionFrame {{ margin-top: 8px; border: none; border-radius: 10px; background: {bcol}; }}")
        css.append("QStatusBar::item { border: none; }")

        # Tables: remove default grid lines / frames
        css.append("QTableView, QTableWidget { border: none; gridline-color: transparent; }")

        # Buttons: rounded with hover/pressed highlight (slightly orange on hover)
        hover_bg = "#FFE3C2"
        pressed_bg = "#E07E12"
        css.append(f"QPushButton {{ border: 1px solid {self._BORDER}; border-radius: 10px; padding: 8px 12px; background: {bcol}; }}")
        css.append(f"QPushButton:hover {{ background: {hover_bg}; border-color: {ACCENT_HOVER}; }}")
        css.append(f"QPushButton:pressed {{ background: {pressed_bg}; border-color: {ACCENT}; color: #ffffff; }}")
        css.append(f"QToolButton {{ border: 1px solid {self._BORDER}; border-radius: 10px; padding: 6px 8px; background: {bcol}; }}")
        css.append(f"QToolButton:hover {{ background: {hover_bg}; border-color: {ACCENT_HOVER}; }}")
        css.append(f"QToolButton:pressed {{ background: {pressed_bg}; border-color: {ACCENT}; color: #ffffff; }}")
        # In dark theme, ensure hover text is black on buttons
        if dark:
            css.append("QPushButton:hover { color: #000000; }")
            css.append("QToolButton:hover { color: #000000; }")
            css.append("QPushButton#btn_generate:hover:!disabled { color: #000000; }")

        # Text selection color (not blue; light orange)
        sel_bg = "#FFC37A"; sel_fg = "#222222"
        css.append(f"QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox {{ selection-background-color: {sel_bg}; selection-color: {sel_fg}; }}")

        # Inputs: rounded, same look (Host/Port/Tolerance)
        css.append(f"QLineEdit, QComboBox, QAbstractSpinBox {{ border: 1px solid {self._BORDER}; border-radius: 8px; padding: 6px 8px; background: {bcol}; }}")

        # ComboBox down arrow
        css.append("QComboBox { padding-right: 26px; }")
        css.append("QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 22px; border: none; background: transparent; margin-right: 4px; }")
        css.append(f'QComboBox::down-arrow {{ image: url("{arrow_url}"); width: 12px; height: 12px; }}')

        # SpinBox arrows (incl. Port)
        css.append("QAbstractSpinBox { padding-right: 28px; }")
        css.append("QAbstractSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none; background: transparent; margin-right: 2px; }")
        css.append("QAbstractSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none; background: transparent; margin-right: 2px; }")
        css.append(f'QAbstractSpinBox::up-arrow {{ image: url("{spin_up}"); width: 10px; height: 10px; }}')
        css.append(f'QAbstractSpinBox::down-arrow {{ image: url("{spin_down}"); width: 10px; height: 10px; }}')

        # Apply
        self.setStyleSheet("".join(css))

        # Native Windows title bar in dark mode
        try:
            _apply_native_dark_titlebar(self, dark)
        except Exception:
            pass


    def _apply_stylesheet(self):
        bcol = getattr(self, "_BG", BG)
        fcol = getattr(self, "_FG", FG)
        arrow_path = _resolve_arrow_path(__file__)
        dark = str(bcol).lower() in ("#1e1e1e", "#171717", "#202020", "#121212")
        arrow_url = _white_variant_for_qss(arrow_path) if dark else (arrow_path or "arrow-down.png")
        arrow_url = (arrow_url or "arrow-down.png").replace("\\", "/")

        css = []
        css.append("QPushButton#btn_login, QPushButton#btn_generate { font-size: 16px; }")
        css.append(f"QWidget {{ color: {fcol}; background: {bcol}; font-family: 'Segoe UI'; font-size: 10pt; }}")
        # no framed header bar
        css.append(f"QLabel#sectionTitle {{ font-size: 10pt; font-weight: 600; background: {bcol}; padding: 0 8px; border-radius: 6px; color: {fcol}; }}")
        css.append(f"QFrame#sectionFrame {{ margin-top: 8px; border: none; border-radius: 8px; background: {bcol}; }}")
        css.append("QStatusBar::item { border: none; }")
        css.append(f"QLineEdit, QComboBox {{ border: 1px solid {self._BORDER}; border-radius: 6px; padding: 6px 8px; background: {bcol}; }}")
        css.append("QComboBox { padding-right: 26px; }")
        css.append("QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 22px; border: none; background: transparent; margin-right: 4px; }")
        css.append(f'QComboBox::down-arrow {{ image: url("{arrow_url}"); width: 12px; height: 12px; }}')
        css.append(f"QPushButton {{ background: {bcol}; color: {fcol}; border: 1px solid {self._BORDER}; border-radius: 12px; padding: 8px 16px; }}")
        css.append("QPushButton:hover { background: #FFE3C2; border-color: #FFA74B; color: #000000; }")
        css.append("QPushButton:pressed { background: #FFC37A; border-color: #E07E12; }")
        css.append("QPushButton:disabled { background: #f0f0f0; color: #9b9b9b; border-color: #e6e6e6; }")
        css.append("QPushButton#btn_generate { background: #F7921E; color: #FFFFFF; border: 1px solid #F7921E; border-radius: 12px; padding: 10px 18px; }")
        css.append("QPushButton#btn_generate:hover:!disabled { background: #FFA74B; border-color: #FFA74B; color: #000000; }")
        css.append("QTableView, QTableWidget { border: none; gridline-color: transparent; }")
        css.append("QToolButton#inlineToolAdd, QToolButton#inlineToolDel { background: transparent; border: 1px solid " + self._BORDER + "; border-radius: 10px; padding: 2px; }")
        css.append("QToolButton#inlineToolAdd:hover, QToolButton#inlineToolDel:hover { background: #FFE3C2; border-color: #FFA74B; }")
        css.append("QTableCornerButton::section { background: " + self._HEADER_BG + "; border: 1px solid " + self._BORDER + "; }")
        css.append("QTableView::item:selected, QTableWidget::item:selected { background: #FFC37A; color: #222222; }")
        css.append(f"QHeaderView::section {{ background: {self._HEADER_BG}; color: {fcol}; border: 1px solid {self._BORDER}; padding: 6px; font-weight: 600; }}")
        corner_bg = self._HEADER_BG
        corner_border = self._BORDER
        css.append(f"QTableCornerButton::section {{ background: {corner_bg}; border: 1px solid {corner_border}; }}")
        # Generate button: pale by default, bright orange on hover
        css.append("QPushButton#btn_generate { background: #FFE3C2; color: #000000; border: 1px solid #FFA74B; border-radius: 12px; padding: 10px 18px; }")
        css.append("QPushButton#btn_generate:hover:!disabled { background: #F7921E; border-color: #F7921E; color: #FFFFFF; }")
        scrollbar_bg = "#252525" if dark else "#FFFFFF"
        scrollbar_handle = "#F7921E" if dark else "#FFC37A"
        scrollbar_handle_hover = "#FFA74B"
        scrollbar_handle_pressed = "#E07E12"
        arrow_up = ARROW_UP_PATH.replace("\\", "/") if ARROW_UP_PATH else ""
        arrow_down = ARROW_DOWN_PATH.replace("\\", "/") if ARROW_DOWN_PATH else ""
        arrow_left = ARROW_LEFT_PATH.replace("\\", "/") if ARROW_LEFT_PATH else ""
        arrow_right = ARROW_RIGHT_PATH.replace("\\", "/") if ARROW_RIGHT_PATH else ""
        if dark:
            if ARROW_UP_PATH:
                arrow_up = _white_variant_for_qss(ARROW_UP_PATH).replace("\\", "/")
            if ARROW_DOWN_PATH:
                arrow_down = _white_variant_for_qss(ARROW_DOWN_PATH).replace("\\", "/")
            if ARROW_LEFT_PATH:
                arrow_left = _white_variant_for_qss(ARROW_LEFT_PATH).replace("\\", "/")
            if ARROW_RIGHT_PATH:
                arrow_right = _white_variant_for_qss(ARROW_RIGHT_PATH).replace("\\", "/")
        css.append(f"QScrollBar:horizontal, QScrollBar:vertical {{ background: {scrollbar_bg}; border-radius: 8px; }}")
        css.append("QScrollBar:horizontal { height: 16px; margin: 0px 14px; }")
        css.append("QScrollBar:vertical { width: 16px; margin: 14px 0px; }")
        css.append(f"QScrollBar::handle:horizontal {{ background: {scrollbar_handle}; border-radius: 10px; min-width: 24px; max-width: 24px; margin: 2px 3px; }}")
        css.append(f"QScrollBar::handle:horizontal:hover {{ background: {scrollbar_handle_hover}; }}")
        css.append(f"QScrollBar::handle:horizontal:pressed {{ background: {scrollbar_handle_pressed}; }}")
        css.append(f"QScrollBar::handle:vertical {{ background: {scrollbar_handle}; border-radius: 10px; min-height: 24px; max-height: 24px; margin: 3px 2px; }}")
        css.append(f"QScrollBar::handle:vertical:hover {{ background: {scrollbar_handle_hover}; }}")
        css.append(f"QScrollBar::handle:vertical:pressed {{ background: {scrollbar_handle_pressed}; }}")
        css.append("QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 12px; height: 12px; border-radius: 6px; background: transparent; subcontrol-origin: margin; margin: 0; image: none; }")
        css.append("QScrollBar::sub-line:horizontal { subcontrol-position: left center; }")
        css.append("QScrollBar::add-line:horizontal { subcontrol-position: right center; }")
        css.append("QScrollBar::add-line:horizontal:hover, QScrollBar::sub-line:horizontal:hover { background: rgba(0, 0, 0, 0.08); }")
        css.append("QScrollBar::add-line:horizontal:pressed, QScrollBar::sub-line:horizontal:pressed { background: #F7921E; }")
        css.append("QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { width: 12px; height: 12px; border-radius: 6px; background: transparent; subcontrol-origin: margin; margin: 0; image: none; }")
        css.append("QScrollBar::sub-line:vertical { subcontrol-position: top center; }")
        css.append("QScrollBar::add-line:vertical { subcontrol-position: bottom center; }")
        css.append("QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover { background: rgba(0, 0, 0, 0.08); }")
        css.append("QScrollBar::add-line:vertical:pressed, QScrollBar::sub-line:vertical:pressed { background: #F7921E; }")
        css.append("QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal, QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical { background: transparent; border: none; width: 16px; height: 16px; margin: 0; }")
        if arrow_left:
            css.append(f'QScrollBar::left-arrow:horizontal {{ image: url("{arrow_left}"); }}')
        if arrow_right:
            css.append(f'QScrollBar::right-arrow:horizontal {{ image: url("{arrow_right}"); }}')
        if arrow_up:
            css.append(f'QScrollBar::up-arrow:vertical {{ image: url("{arrow_up}"); }}')
        if arrow_down:
            css.append(f'QScrollBar::down-arrow:vertical {{ image: url("{arrow_down}"); }}')
        css.append("QScrollBar::groove:horizontal, QScrollBar::groove:vertical { subcontrol-origin: margin; }")
        css.append("QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { border: none; }")
        self.setStyleSheet("".join(css))
    # -------------------------
    # File pickers
    # -------------------------
    def _pick_nabory(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите файл наборов", "", "Excel (*.xlsx *.xls)")
        if path:
            self.ed_nabory.setText(path)
            self._populate_sheets(path, self.cb_sheet_nabory)

    def _pick_matrix(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите файл матрицы", "", "Excel (*.xlsx *.xls)")
        if path:
            self.ed_matrix.setText(path)
            self._populate_sheets(path, self.cb_sheet_matrix)

    def _pick_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Выберите выходной файл", "matrix.cv", "Профиль (*.cv *.xml)")
        if path:
            self.ed_output.setText(path)

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

    # -------------------------
    # Generation
    # -------------------------
    def _start_generation(self):
        nabory = self.ed_nabory.text().strip()
        matrix = self.ed_matrix.text().strip()
        out = self.ed_output.text().strip()
        profile_title = (self.ed_title.text() or "").strip() or "Матрица"
        param_field = (self.cb_param.currentText() or "").strip() or "Категория:\\"

        # Host/port selection (informational for now)
        host = (getattr(self, 'ed_host', QtWidgets.QLineEdit('http://127.0.0.1')).text() or '').strip()
        port = int(getattr(self, 'spin_port', QtWidgets.QSpinBox()).value() or 5000)
        sheet_nabory = self.cb_sheet_nabory.currentText().strip()
        sheet_matrix = self.cb_sheet_matrix.currentText().strip()

        if not os.path.exists(nabory):
            QtWidgets.QMessageBox.warning(self, "Файл не найден", "Укажите корректный путь к файлу наборов.")
            return
        if not os.path.exists(matrix):
            QtWidgets.QMessageBox.warning(self, "Файл не найден", "Укажите корректный путь к файлу матрицы.")
            return
        if not out:
            QtWidgets.QMessageBox.warning(self, "Не задан выходной файл", "Укажите путь сохранения .cv/.xml")
            return
        if not sheet_nabory:
            QtWidgets.QMessageBox.warning(self, "Не выбран лист", "Выберите лист в файле наборов.")
            return
        if not sheet_matrix:
            QtWidgets.QMessageBox.warning(self, "Не выбран лист", "Выберите лист в матрице.")
            return

        # log removed
        
        self.btn_generate.setEnabled(False)
        self.status.showMessage("Обработка...")

        self.thread = QtCore.QThread(self)
        self.worker = GeneratorWorker(
            nabory, matrix, out,
            sheet_nabory, sheet_matrix,
            self.spin_a.value(), self.spin_b.value(), self.spin_c.value(),
            profile_title, param_field
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(lambda: self.btn_generate.setEnabled(True))
        self.thread.start()


    def _on_done(self, out_path: str):
        
        self.status.showMessage("Готово")
        QtWidgets.QMessageBox.information(self, "Готово", f"Файл создан:\n{out_path}")

    def _on_failed(self, err: str):
        
        self.status.showMessage("Ошибка")
        QtWidgets.QMessageBox.critical(self, "Ошибка", "Произошла ошибка при генерации. Подробности в журнале.")

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
    for p in (LOGO_PATH,
              os.path.join(os.path.dirname(sys.argv[0]), "Manager-scaled.png"),
              os.path.join(os.path.dirname(__file__), "Manager-scaled.png")):
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













