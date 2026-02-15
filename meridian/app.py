from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from meridian.ui.main_window import MainWindow
from meridian.ui.style import build_stylesheet

_ROOT = Path(__file__).resolve().parent.parent
_LOGO = _ROOT / "assets" / "logo.png"


class MeridianApp:
    """Top-level application controller for Meridian."""

    def __init__(self, argv: list[str]):
        self._qt = QApplication(argv)
        self._qt.setApplicationName("Meridian")
        self._qt.setOrganizationName("Meridian")
        self._qt.setWindowIcon(QIcon(str(_LOGO)))
        self._qt.setStyleSheet(build_stylesheet())
        self._window = MainWindow()

    def run(self) -> int:
        """Show the main window and enter the Qt event loop."""
        self._window.show()
        return self._qt.exec()
