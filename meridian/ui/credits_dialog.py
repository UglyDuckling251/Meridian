# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Credits dialog for Meridian.

Displays developers, supporters, acknowledgements, and legal notices.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
    QPushButton,
)

from meridian.ui.style import active_theme
from meridian.ui.icons import pixmap as lucide_pixmap

_APP_VERSION = "0.1.0-dev"


class CreditsDialog(QDialog):
    """Modal credits dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Credits — Meridian")
        self.setFixedSize(520, 580)
        self._build_ui()

    def _build_ui(self):
        t = active_theme()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Header --------------------------------------------------------
        header = QWidget()
        header.setObjectName("creditsHeader")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(24, 20, 24, 16)
        h_layout.setSpacing(6)

        title = QLabel("Meridian")
        title.setObjectName("creditsTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(title)

        ver = QLabel(f"Version {_APP_VERSION}")
        ver.setObjectName("sectionLabel")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(ver)

        subtitle = QLabel("A fully customizable, all-in-one frontend for\n"
                          "organizing and playing your ROM collection.")
        subtitle.setObjectName("creditsSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        h_layout.addWidget(subtitle)

        root.addWidget(header)

        # -- Scrollable body -----------------------------------------------
        scroll_content = QWidget()
        body = QVBoxLayout(scroll_content)
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(18)

        # ── Developers ────────────────────────────────────────────────
        body.addWidget(self._section("code", "Developers", t))
        body.addWidget(self._person("UglyDuckling251", "Creator & lead developer"))

        # ── Supporters ────────────────────────────────────────────────
        body.addWidget(self._section("heart", "Supporters", t))
        body.addWidget(self._note("No supporters yet — be the first!"))

        # ── Inspiration ───────────────────────────────────────────────
        body.addWidget(self._section("monitor", "Inspiration", t))
        for name, desc in [
            ("ES-DE", "Frontend concept and system-centric design"),
            ("Playnite", "PC game library integration approach"),
            ("LaunchBox / Big Box", "UI layout and metadata presentation"),
            ("Pegasus Frontend", "Customisable theming architecture"),
            ("PlayStation 5 UI", "Ambient audio and visual polish direction"),
        ]:
            body.addWidget(self._person(name, desc))

        # ── Emulators & Cores ─────────────────────────────────────────
        body.addWidget(self._section("gamepad-2", "Emulators & Cores", t))
        for name, desc in [
            ("RetroArch / libretro", "Multi-system emulation platform and core ecosystem"),
            ("PCSX2", "PlayStation 2 emulation"),
            ("RPCS3", "PlayStation 3 emulation"),
            ("Cemu", "Wii U emulation"),
            ("Ryubing / Ryujinx", "Nintendo Switch emulation"),
            ("Eden", "Nintendo Switch emulation (Yuzu fork)"),
            ("Dolphin", "GameCube and Wii emulation"),
            ("Azahar / Citra", "Nintendo 3DS emulation"),
            ("melonDS / DeSmuME", "Nintendo DS emulation"),
            ("Xemu", "Original Xbox emulation"),
            ("Xenia", "Xbox 360 emulation"),
            ("Vita3K", "PlayStation Vita emulation"),
            ("DuckStation", "PlayStation 1 emulation"),
            ("mGBA", "Game Boy Advance emulation"),
        ]:
            body.addWidget(self._person(name, desc))

        # ── Libraries & Tools ─────────────────────────────────────────
        body.addWidget(self._section("package", "Libraries & Tools", t))
        for name, desc in [
            ("Qt / PySide6", "Application framework (LGPL-3.0)"),
            ("pygame", "Audio mixer and controller detection (LGPL-2.1)"),
            ("NumPy", "Procedural audio synthesis"),
            ("psutil", "System information (BSD-3-Clause)"),
            ("sounddevice", "Audio device enumeration (MIT)"),
            ("py7zr", "7-Zip archive support (LGPL-2.1)"),
            ("7-Zip (7za)", "Archive extraction fallback (LGPL-2.1 + BSD-3-Clause)"),
        ]:
            body.addWidget(self._person(name, desc))

        # ── Assets ────────────────────────────────────────────────────
        body.addWidget(self._section("zap", "Assets", t))
        for name, desc in [
            ("Lucide Icons", "Icon set (ISC license) — lucide.dev"),
            ("Ubuntu Font", "Default typeface (Ubuntu Font Licence 1.0)"),
            ("Roboto", "Bundled typeface (SIL Open Font License 1.1)"),
            ("Work Sans", "Bundled typeface (SIL Open Font License 1.1)"),
        ]:
            body.addWidget(self._person(name, desc))

        # ── Legal ─────────────────────────────────────────────────────
        body.addWidget(self._section("info", "Legal", t))
        body.addWidget(self._note(
            "Meridian is free software licensed under the "
            "GNU Affero General Public License v3.0 (AGPL-3.0-or-later).\n\n"
            "Meridian does not include, distribute, or provide any means "
            "to download copyrighted game ROMs, BIOS files, firmware, "
            "encryption keys, or any other proprietary content. Users must "
            "legally obtain all such files themselves.\n\n"
            "All emulator names, logos, and trademarks are the property of "
            "their respective owners. Meridian is not affiliated with or "
            "endorsed by any emulator project.\n\n"
            "Bundled fonts:\n"
            "  • Ubuntu — Ubuntu Font Licence 1.0 (assets/fonts/ubuntu/UFL.txt)\n"
            "  • Roboto — SIL Open Font License 1.1 (assets/fonts/roboto/OFL.txt)\n"
            "  • Work Sans — SIL Open Font License 1.1 (assets/fonts/work-sans/OFL.txt)\n\n"
            "Lucide Icons — ISC License (github.com/lucide-icons/lucide)\n\n"
            "© 2025-2026 Meridian Contributors. All rights reserved."
        ))

        body.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        # -- Close button --------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 8, 12, 10)
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.setObjectName("cancelButton")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _section(icon_name: str, text: str, theme) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(lucide_pixmap(icon_name, 14, theme.accent_primary))
        icon_lbl.setFixedSize(18, 18)
        row.addWidget(icon_lbl)
        lbl = QLabel(text)
        lbl.setObjectName("creditsSectionHeader")
        row.addWidget(lbl, 1)
        return w

    @staticmethod
    def _person(name: str, desc: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(22, 0, 0, 0)
        layout.setSpacing(1)
        n = QLabel(name)
        n.setObjectName("creditsPersonName")
        layout.addWidget(n)
        d = QLabel(desc)
        d.setObjectName("sectionLabel")
        d.setWordWrap(True)
        layout.addWidget(d)
        return w

    @staticmethod
    def _note(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        lbl.setWordWrap(True)
        lbl.setContentsMargins(22, 0, 0, 0)
        return lbl
