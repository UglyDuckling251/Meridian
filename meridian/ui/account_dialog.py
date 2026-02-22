# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Ariam account dialog for Meridian.

Provides Sign In and Create Account tabs.  Ariam is a unified account
system shared across multiple projects — this dialog is UI-only for now.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox,
)

from meridian.ui.style import active_theme


class AccountDialog(QDialog):
    """Modal dialog for Ariam account sign-in and registration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ariam Account")
        self.setFixedSize(420, 440)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("accountHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 16)
        header_layout.setSpacing(4)

        title = QLabel("Ariam")
        title.setObjectName("accountTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        subtitle = QLabel("One account for everything.")
        subtitle.setObjectName("accountSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle)

        root.addWidget(header)

        # Tabs: Sign In / Create Account
        self._tabs = QTabWidget()
        self._tabs.setObjectName("subTabs")
        self._tabs.addTab(self._build_sign_in_tab(), "Sign In")
        self._tabs.addTab(self._build_create_tab(), "Create Account")
        root.addWidget(self._tabs, 1)

    # ------------------------------------------------------------------
    # Sign In tab
    # ------------------------------------------------------------------

    def _build_sign_in_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self._login_email = QLineEdit()
        self._login_email.setPlaceholderText("Email or username")
        form.addRow("Account:", self._login_email)

        self._login_pass = QLineEdit()
        self._login_pass.setPlaceholderText("Password")
        self._login_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self._login_pass)

        layout.addLayout(form)

        self._chk_remember = QCheckBox("Remember me")
        self._chk_remember.setEnabled(False)
        layout.addWidget(self._chk_remember)

        btn_login = QPushButton("Sign In")
        btn_login.setObjectName("primaryButton")
        btn_login.setEnabled(False)
        layout.addWidget(btn_login)

        forgot = QLabel(
            f'<a href="#" style="color:{active_theme().accent_primary}; text-decoration:none;">'
            f"Forgot password?</a>"
        )
        forgot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(forgot)

        layout.addStretch()
        return tab

    # ------------------------------------------------------------------
    # Create Account tab
    # ------------------------------------------------------------------

    def _build_create_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self._reg_user = QLineEdit()
        self._reg_user.setPlaceholderText("Choose a username")
        form.addRow("Username:", self._reg_user)

        self._reg_email = QLineEdit()
        self._reg_email.setPlaceholderText("you@example.com")
        form.addRow("Email:", self._reg_email)

        self._reg_pass = QLineEdit()
        self._reg_pass.setPlaceholderText("Password")
        self._reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self._reg_pass)

        self._reg_confirm = QLineEdit()
        self._reg_confirm.setPlaceholderText("Confirm password")
        self._reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirm:", self._reg_confirm)

        layout.addLayout(form)

        self._chk_terms = QCheckBox("I agree to the Terms of Service")
        self._chk_terms.setEnabled(False)
        layout.addWidget(self._chk_terms)

        btn_create = QPushButton("Create Account")
        btn_create.setObjectName("primaryButton")
        btn_create.setEnabled(False)
        layout.addWidget(btn_create)

        layout.addStretch()
        return tab
