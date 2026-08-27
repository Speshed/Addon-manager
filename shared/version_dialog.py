# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable, Mapping, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
)


class VersionHistoryWidget(QWidget):
    """Read-only in-app page with the complete version history."""

    back_requested = Signal()

    def __init__(self, history: Iterable[Mapping[str, Any]], parent=None):
        super().__init__(parent)
        self._history = tuple(history or ())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 30)
        layout.setSpacing(16)

        header = QHBoxLayout()
        self.back_button = QPushButton("← Назад")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("История версий")
        title.setStyleSheet("font-size: 16pt; font-weight: 600;")
        header.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addStretch(1)
        layout.addLayout(header)

        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setAcceptRichText(False)
        self.text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text.setPlainText(self._build_text())
        self.text.moveCursor(QTextCursor.MoveOperation.Start)
        layout.addWidget(self.text, 1)

    def _build_text(self) -> str:
        blocks = []
        for release in self._history:
            version = str(release.get("version", "")).strip()
            date = str(release.get("date", "")).strip()
            changes = [
                str(item).strip()
                for item in release.get("changes", ())
                if str(item).strip()
            ]

            heading = f"Версия {version}" if version else "Версия"
            if date:
                heading += f" — {date}"

            lines = [heading]
            for change in changes:
                lines.append(f"• {change}")
            blocks.append("\n".join(lines))

        if not blocks:
            return "История версий пока не заполнена."
        return "\n\n\n".join(blocks)
