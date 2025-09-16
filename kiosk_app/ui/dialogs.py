from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from ..theme import THEME_DEFAULT


class ExitPwdDialog(QDialog):
    def __init__(self, theme: dict, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Пароль")
        self.setAttribute(Qt.WA_StyledBackground, True)
        surface = theme.get("surface", "#ffffff") if theme else THEME_DEFAULT.get("surface", "#ffffff")
        self.setStyleSheet(
            "QDialog{background:%s; border-radius:12px;}"
            "QLabel{font-size:16px;}"
            "QLineEdit{font-size:18px; padding:10px 12px; border:1px solid rgba(0,0,0,0.2); border-radius:8px;}"
            "QPushButton{font-size:16px; padding:8px 14px;}"
            % surface
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Введите пароль для выхода")
        title.setStyleSheet("font-weight:700; font-size:18px;")
        layout.addWidget(title)

        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        self.edit.setPlaceholderText("Пароль")
        layout.addWidget(self.edit)

        row = QHBoxLayout()
        self.cb = QCheckBox("Показать пароль")
        self.cb.stateChanged.connect(self._toggle_password)
        row.addWidget(self.cb)
        row.addStretch()
        layout.addLayout(row)

        self.err = QLabel("")
        self.err.setStyleSheet("color:#dc2626; font-size:14px;")
        layout.addWidget(self.err)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.resize(420, 200)

    def _toggle_password(self) -> None:
        self.edit.setEchoMode(QLineEdit.Normal if self.cb.isChecked() else QLineEdit.Password)

    def password(self) -> str:
        return self.edit.text() or ""

    def show_error(self, message: str) -> None:
        self.err.setText(message or "")
        if message:
            try:
                QMessageBox.warning(self, "Ошибка", message)
            except Exception:
                pass


def install_password_dialog_patch(theme_provider: Callable[[], dict] | None = None) -> None:
    """Override :func:`QInputDialog.getText` with a themed password dialog."""

    original_get_text = getattr(QInputDialog, "getText", None)

    def _patched(parent, title, label, mode=QLineEdit.Normal):  # type: ignore[override]
        theme = THEME_DEFAULT
        if theme_provider is not None:
            try:
                provided = theme_provider()
                if isinstance(provided, dict):
                    theme = provided
            except Exception:
                pass
        dialog = ExitPwdDialog(theme, parent)
        ok = dialog.exec() == QDialog.Accepted
        return dialog.password(), ok

    try:
        QInputDialog.getText = staticmethod(_patched)
    except Exception:
        if original_get_text is not None:
            QInputDialog.getText = original_get_text  # type: ignore[assignment]
