"""
Credits dialog for Meridian.

Displays developers, supporters, and acknowledgements.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
    QPushButton,
)

from meridian.ui.style import ACCENT_BLUE, ACCENT_GREEN, FG_SECONDARY, BG_SURFACE, BORDER
from meridian.ui.icons import pixmap as lucide_pixmap


class CreditsDialog(QDialog):
    """Modal credits dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Credits")
        self.setFixedSize(460, 500)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Header ----------------------------------------------------
        header = QWidget()
        header.setObjectName("creditsHeader")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(24, 20, 24, 16)
        h_layout.setSpacing(6)

        title = QLabel("Meridian")
        title.setObjectName("creditsTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(title)

        subtitle = QLabel("Built with care for the emulation community.")
        subtitle.setObjectName("creditsSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(subtitle)

        root.addWidget(header)

        # -- Scrollable body -------------------------------------------
        scroll_content = QWidget()
        body = QVBoxLayout(scroll_content)
        body.setContentsMargins(28, 20, 28, 20)
        body.setSpacing(18)

        # Developers
        body.addWidget(self._section_header("code", "Developers"))
        body.addWidget(self._person("UglyDuckling251", "Creator & lead developer"))

        # Supporters
        body.addWidget(self._section_header("heart", "Supporters"))
        body.addWidget(self._note("No supporters yet. Be the first!"))

        # Acknowledgements
        body.addWidget(self._section_header("users", "Acknowledgements"))
        for name, desc in [
            ("ES-DE", "Inspiration for the frontend concept"),
            ("Playnite", "Inspiration for PC game library integration"),
            ("LaunchBox / Big Box", "Inspiration for UI and metadata approach"),
            ("Pegasus Frontend", "Inspiration for customisable theming"),
            ("RetroArch / libretro", "Multi-system emulation core"),
            ("Lucide Icons", "Icon set used throughout the UI (ISC license)"),
            ("Qt / PySide6", "Application framework"),
            ("pygame", "Controller detection"),
        ]:
            body.addWidget(self._person(name, desc))

        # Legal
        body.addWidget(self._section_header("external-link", "Legal"))
        body.addWidget(self._note(
            "Meridian is licensed under the GNU Affero General Public License v3.0. "
            "Meridian does not include, distribute, or provide any means to download "
            "copyrighted game content."
        ))

        body.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        # -- Close button ----------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 8, 12, 10)
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _section_header(icon_name: str, text: str) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(lucide_pixmap(icon_name, 14, ACCENT_BLUE))
        icon_lbl.setFixedSize(18, 18)
        row.addWidget(icon_lbl)

        lbl = QLabel(f"<b>{text}</b>")
        lbl.setStyleSheet(f"color: {ACCENT_BLUE}; font-size: 9pt;")
        row.addWidget(lbl, 1)

        return w

    @staticmethod
    def _person(name: str, desc: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(22, 0, 0, 0)
        layout.setSpacing(1)

        n = QLabel(name)
        n.setStyleSheet("font-weight: 600;")
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
