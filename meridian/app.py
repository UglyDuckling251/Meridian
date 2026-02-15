from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QColor

from meridian.ui.main_window import MainWindow


class MeridianApp:
    """Top-level application controller for Meridian."""

    def __init__(self, argv: list[str]):
        self._qt = QApplication(argv)
        self._qt.setApplicationName("Meridian")
        self._qt.setOrganizationName("Meridian")
        self._qt.setWindowIcon(self._create_icon())
        self._window = MainWindow()

    @staticmethod
    def _create_icon() -> QIcon:
        """Create a solid black square icon used for the title bar and taskbar."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0))
        return QIcon(pixmap)

    def run(self) -> int:
        """Show the main window and enter the Qt event loop."""
        self._window.show()
        return self._qt.exec()
