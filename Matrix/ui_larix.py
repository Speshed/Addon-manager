# -*- coding: utf-8 -*-
"""Larix-compatible Matrix entry point.

The checkbox "Группировать по разделам" controls only section grouping
(АР/КР/ОВ/...).

Validation types are independent of that option:
- intersection checks must always be inside an "Пересечение" folder;
- duplication checks must always be inside a "Дублирование" folder.

When section grouping is enabled, the original Matrix.ui structure is kept:
    <section pair> / Пересечение
    <section pair> / Дублирование

When section grouping is disabled, section-pair folders are collapsed into:
    Пересечение
    Дублирование

The checks themselves stay separate XML items, so a matrix cell containing
both e.g. B/D keeps both IntersectionValidationData and
DuplicationValidationData for the same pair of sets.
"""

from __future__ import annotations

import os
import re

from Matrix import ui as _base


_BaseGeneratorWorker = _base.GeneratorWorker


_ITEM_BLOCK_RE = re.compile(
    r'(?P<block>[ \t]*<BaseExportProfileItem xsi:type="CollisionsExportProfileItem">\s*'
    r'.*?'
    r'</BaseExportProfileItem>)',
    re.DOTALL,
)
_ID_RE = re.compile(r'<Id>(\d+)</Id>')
_TITLE_RE = re.compile(r'<Title>(.*?)</Title>', re.DOTALL)
_FOLDER_RE = re.compile(r'<IsFolder>true</IsFolder>')
_PARENT_RE = re.compile(r'<ParentId>(\d+)</ParentId>')


def _validation_folder_type(title: str):
    text = (title or "").strip()
    if text == "Пересечение" or text.endswith("/ Пересечение"):
        return "intersection"
    if text == "Дублирование" or text.endswith("/ Дублирование"):
        return "duplication"
    return None


def _collapse_section_folders(xml_text: str) -> str:
    """Remove section grouping while preserving validation-type folders."""
    folder_id_to_type = {}
    folder_blocks = []

    for match in _ITEM_BLOCK_RE.finditer(xml_text):
        block = match.group("block")
        if not _FOLDER_RE.search(block):
            continue

        id_match = _ID_RE.search(block)
        title_match = _TITLE_RE.search(block)
        if not id_match or not title_match:
            continue

        folder_type = _validation_folder_type(title_match.group(1))
        if folder_type is None:
            continue

        folder_id_to_type[id_match.group(1)] = folder_type
        folder_blocks.append(block)

    if not folder_id_to_type:
        return xml_text

    # Folder IDs 11300+ are the range already used by Matrix.ui for generated
    # folders. All old section/type folders are removed below, so these two IDs
    # are free in the collapsed structure.
    new_parent_ids = {
        "intersection": "11300",
        "duplication": "11301",
    }

    result = xml_text

    # Point every generated check to its validation-type folder.
    for old_id, folder_type in folder_id_to_type.items():
        new_id = new_parent_ids[folder_type]
        result = re.sub(
            rf'<ParentId>{re.escape(old_id)}</ParentId>',
            f'<ParentId>{new_id}</ParentId>',
            result,
        )

    # Remove the original section/type folders.
    for block in folder_blocks:
        result = result.replace(block, "", 1)

    present_types = set(folder_id_to_type.values())
    new_folders = []
    if "intersection" in present_types:
        new_folders.append(
            _base.FOLDER_TEMPLATE.format(
                folder_id=new_parent_ids["intersection"],
                folder_title=_base.xml_text_escape("Пересечение"),
            )
        )
    if "duplication" in present_types:
        new_folders.append(
            _base.FOLDER_TEMPLATE.format(
                folder_id=new_parent_ids["duplication"],
                folder_title=_base.xml_text_escape("Дублирование"),
            )
        )

    if new_folders:
        marker = "      <ProfileItems>"
        insert = marker + "\n" + "\n".join(new_folders)
        result = result.replace(marker, insert, 1)

    return result


class GeneratorWorker(_BaseGeneratorWorker):
    """Keep validation folders regardless of section-grouping preference."""

    def __init__(
        self,
        nabory_path: str,
        matrix_path: str,
        out_path: str,
        sheet_nabory: str,
        sheet_matrix: str,
        map_a: float,
        map_b: float,
        map_c: float,
        profile_title: str,
        param_field: str,
        build_filters: bool,
        group_by_sections: bool = True,
    ):
        self._requested_group_by_sections = bool(group_by_sections)
        super().__init__(
            nabory_path,
            matrix_path,
            out_path,
            sheet_nabory,
            sheet_matrix,
            map_a,
            map_b,
            map_c,
            profile_title,
            param_field,
            build_filters,
            group_by_sections,
        )

    def _generate_one(self, sheet_matrix: str, out_path: str, profile_title: str):
        requested = self._requested_group_by_sections

        # Matrix.ui already has the correct safe logic for separate
        # intersection/duplication folders in grouped mode, including reserved
        # ParentIds when only one validation type exists. Reuse that path.
        self.group_by_sections = True
        try:
            _BaseGeneratorWorker._generate_one(
                self, sheet_matrix, out_path, profile_title
            )
        finally:
            self.group_by_sections = requested

        if requested:
            return

        with open(out_path, "r", encoding="utf-8") as fh:
            xml_text = fh.read()

        collapsed = _collapse_section_folders(xml_text)
        if collapsed != xml_text:
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(collapsed)


# MainWindow._start_generation resolves GeneratorWorker from Matrix.ui globals.
# Replace only the worker; leave the original UI untouched so the checkbox
# remains enabled and can be switched on/off normally.
_base.GeneratorWorker = GeneratorWorker
MainWindow = _base.MainWindow
