# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Silent QMessageBox wrappers for Meridian.

On Windows, QMessageBox.information / warning / question / critical all
internally call MessageBeep(), which plays the OS system sound regardless
of any custom audio the app plays.  Setting QMessageBox.Icon.NoIcon is the
only way to suppress that call; these helpers do so while manually restoring
the correct visual icon via QStyle standard pixmaps — so the dialogs look
identical but never produce an unwanted system beep.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QApplication, QStyle


def _box(
    parent,
    std_pixmap: QStyle.StandardPixmap,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton | None = None,
) -> QMessageBox:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.NoIcon)   # suppresses Windows MessageBeep()
    box.setWindowTitle(title)
    box.setText(text)
    icon = QApplication.style().standardIcon(std_pixmap)
    box.setIconPixmap(icon.pixmap(32, 32))
    box.setStandardButtons(buttons)
    if default_button is not None:
        box.setDefaultButton(default_button)
    return box


def information(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
) -> QMessageBox.StandardButton:
    return _box(
        parent,
        QStyle.StandardPixmap.SP_MessageBoxInformation,
        title, text, buttons,
    ).exec()


def warning(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
) -> QMessageBox.StandardButton:
    return _box(
        parent,
        QStyle.StandardPixmap.SP_MessageBoxWarning,
        title, text, buttons,
    ).exec()


def critical(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
) -> QMessageBox.StandardButton:
    return _box(
        parent,
        QStyle.StandardPixmap.SP_MessageBoxCritical,
        title, text, buttons,
    ).exec()


def question(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = (
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    ),
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.No,
) -> QMessageBox.StandardButton:
    return _box(
        parent,
        QStyle.StandardPixmap.SP_MessageBoxQuestion,
        title, text, buttons, default_button,
    ).exec()
