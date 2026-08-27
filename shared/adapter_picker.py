# -*- coding: utf-8 -*-
"""Reusable UI for selecting parameters produced by a Larix Excel adapter."""
from __future__ import annotations

import os

try:
    from PySide6 import QtCore, QtWidgets
except Exception:
    from PyQt5 import QtCore, QtWidgets  # type: ignore

from shared.adapter_excel import list_adapter_sheets, prefer_adapter_sheet, read_adapter_parameters
from shared.dialogs import apply_dialog_icon, wire_dialog_button_box


def _exec(dialog) -> int:
    fn = getattr(dialog, "exec", None) or getattr(dialog, "exec_", None)
    return fn() if fn else 0


class AdapterParameterPickerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Выбор параметра из адаптера")
        self.resize(720, 560)
        apply_dialog_icon(self)

        self._path = ""
        self._parameters = []
        self._selected_code = ""

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        file_row = QtWidgets.QHBoxLayout()
        file_row.addWidget(QtWidgets.QLabel("Excel-файл:"))
        self.ed_path = QtWidgets.QLineEdit()
        self.ed_path.setReadOnly(True)
        file_row.addWidget(self.ed_path, 1)
        self.btn_file = QtWidgets.QPushButton("Выбрать файл")
        file_row.addWidget(self.btn_file)
        root.addLayout(file_row)

        sheet_row = QtWidgets.QHBoxLayout()
        sheet_row.addWidget(QtWidgets.QLabel("Лист адаптера:"))
        self.cmb_sheet = QtWidgets.QComboBox()
        sheet_row.addWidget(self.cmb_sheet, 1)
        root.addLayout(sheet_row)

        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Поиск параметра...")
        root.addWidget(self.ed_search)

        self.list_params = QtWidgets.QListWidget()
        self.list_params.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        root.addWidget(self.list_params, 1)

        self.lbl_info = QtWidgets.QLabel("Выберите Excel-файл с адаптером.")
        self.lbl_info.setWordWrap(True)
        root.addWidget(self.lbl_info)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.btn_ok = buttons.button(QtWidgets.QDialogButtonBox.Ok)
        if self.btn_ok is not None:
            self.btn_ok.setText("Выбрать")
            self.btn_ok.setEnabled(False)
        wire_dialog_button_box(buttons, self._accept, self.reject)
        root.addWidget(buttons)

        self.btn_file.clicked.connect(self._pick_file)
        self.cmb_sheet.currentTextChanged.connect(self._load_sheet)
        self.ed_search.textChanged.connect(self._apply_filter)
        self.list_params.itemSelectionChanged.connect(self._selection_changed)
        self.list_params.itemDoubleClicked.connect(lambda _item: self._accept())

        if initial_path and os.path.isfile(initial_path):
            self._set_file(initial_path)

    def _pick_file(self):
        start_dir = os.path.dirname(self._path) if self._path else ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выбор адаптера", start_dir, "Excel (*.xlsx *.xlsm)")
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._path = os.path.abspath(path)
        self.ed_path.setText(self._path)
        self.cmb_sheet.blockSignals(True)
        self.cmb_sheet.clear()
        try:
            sheets = list_adapter_sheets(self._path)
        except Exception as exc:
            self.cmb_sheet.blockSignals(False)
            self._parameters = []
            self._fill_list()
            self.lbl_info.setText(f"Не удалось открыть файл: {exc}")
            return
        self.cmb_sheet.addItems(sheets)
        preferred = prefer_adapter_sheet(sheets)
        if preferred:
            self.cmb_sheet.setCurrentText(preferred)
        self.cmb_sheet.blockSignals(False)
        self._load_sheet(self.cmb_sheet.currentText())

    def _load_sheet(self, sheet_name: str):
        self._parameters = []
        if not self._path or not sheet_name:
            self._fill_list()
            return
        try:
            self._parameters = read_adapter_parameters(self._path, sheet_name)
            if self._parameters:
                self.lbl_info.setText(f"Найдено параметров: {len(self._parameters)}")
            else:
                self.lbl_info.setText("На выбранном листе параметры не найдены.")
        except Exception as exc:
            self.lbl_info.setText(f"Не удалось прочитать адаптер: {exc}")
        self._fill_list()

    def _apply_filter(self, _text: str):
        self._fill_list()

    def _fill_list(self):
        query = (self.ed_search.text() or "").strip().casefold()
        current = self._selected_code
        self.list_params.clear()
        for param in self._parameters:
            haystack = f"{param.code} {param.name} {param.group} {param.source_key}".casefold()
            if query and query not in haystack:
                continue
            item = QtWidgets.QListWidgetItem(param.code)
            item.setData(QtCore.Qt.UserRole, param.code)
            suffix = "число" if param.is_numeric else "текст"
            source = f" • {param.source_key}" if param.source_key else ""
            item.setToolTip(f"{param.code} • {suffix}{source}")
            self.list_params.addItem(item)
            if current and current == param.code:
                item.setSelected(True)
                self.list_params.setCurrentItem(item)
        self._selection_changed()

    def _selection_changed(self):
        item = self.list_params.currentItem()
        self._selected_code = str(item.data(QtCore.Qt.UserRole) or "") if item else ""
        if self.btn_ok is not None:
            self.btn_ok.setEnabled(bool(self._selected_code))

    def _accept(self):
        item = self.list_params.currentItem()
        if item is None:
            return
        self._selected_code = str(item.data(QtCore.Qt.UserRole) or "").strip()
        if self._selected_code:
            self.accept()

    def selected_code(self) -> str:
        return self._selected_code


def pick_adapter_parameter(parent=None, initial_path: str = "") -> str:
    dlg = AdapterParameterPickerDialog(parent, initial_path=initial_path)
    if _exec(dlg) == QtWidgets.QDialog.Accepted:
        return dlg.selected_code()
    return ""


def choose_adapter_sheet(parent=None, initial_path: str = "", title: str = "Выбор адаптера") -> tuple[str, str]:
    """Choose an Excel file and one adapter sheet; prefer the common 'Адаптер' sheet."""
    start_dir = os.path.dirname(initial_path) if initial_path and os.path.isfile(initial_path) else ""
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, title, start_dir, "Excel (*.xlsx *.xlsm)")
    if not path:
        return "", ""
    try:
        sheets = list_adapter_sheets(path)
    except Exception:
        return "", ""
    if not sheets:
        return "", ""
    preferred = prefer_adapter_sheet(sheets)
    if len(sheets) == 1:
        return path, sheets[0]
    selected, ok = QtWidgets.QInputDialog.getItem(parent, "Выбор листа", "Лист адаптера:", sheets, sheets.index(preferred) if preferred in sheets else 0, False)
    if not ok or not selected:
        return "", ""
    return path, str(selected)
