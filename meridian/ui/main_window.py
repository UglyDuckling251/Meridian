import sys
import ctypes
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtGui import QPalette, QColor, QPixmap, QPainter, QImage
from PySide6.QtCore import Qt

from meridian.core.config import Config
from meridian.ui.menu_bar import MenuBar
from meridian.ui.style import BG_BASE, BG_SURFACE, BG_ELEVATED, BORDER, FG_SECONDARY, FG_DISABLED, ACCENT_BLUE
from meridian.ui.icons import pixmap as lucide_pixmap
from meridian.ui.credits_dialog import CreditsDialog

_ROOT = Path(__file__).resolve().parent.parent.parent
_LOGO = _ROOT / "assets" / "logo_transparent.png"
_REPO_URL = "https://github.com/UglyDuckling251/Meridian"

# Windows constants for WM_SIZING edge detection
if sys.platform == "win32":
    import ctypes.wintypes

    class _WinMsg(ctypes.Structure):
        """Mirrors the native Win32 MSG struct."""
        _fields_ = [
            ("hwnd",    ctypes.wintypes.HWND),
            ("message", ctypes.wintypes.UINT),
            ("wParam",  ctypes.wintypes.WPARAM),
            ("lParam",  ctypes.wintypes.LPARAM),
            ("time",    ctypes.wintypes.DWORD),
            ("pt",      ctypes.wintypes.POINT),
        ]

    _WM_SIZING = 0x0214

    _WMSZ_LEFT        = 1
    _WMSZ_RIGHT       = 2
    _WMSZ_TOP         = 3
    _WMSZ_TOPLEFT     = 4
    _WMSZ_TOPRIGHT    = 5
    _WMSZ_BOTTOM      = 6
    _WMSZ_BOTTOMLEFT  = 7
    _WMSZ_BOTTOMRIGHT = 8

    _EDGES_HEIGHT_DRIVEN = (_WMSZ_TOP, _WMSZ_BOTTOM)
    _EDGES_ANCHOR_LEFT   = (_WMSZ_LEFT, _WMSZ_TOPLEFT, _WMSZ_BOTTOMLEFT)
    _EDGES_ANCHOR_TOP    = (_WMSZ_TOP, _WMSZ_TOPLEFT, _WMSZ_TOPRIGHT)


class MainWindow(QMainWindow):
    """
    Primary application window for Meridian.

    - Title bar is forced to white (light) via the Windows DWM API.
    - Aspect ratio is locked to 16:9 at all times, enforced through the
      native WM_SIZING message so the window never renders at a wrong ratio.
    """

    ASPECT_RATIO = 16.0 / 9.0
    MIN_WIDTH = 960
    MIN_HEIGHT = 540
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720

    def __init__(self):
        super().__init__()
        self._config = Config.load()
        self._init_window()
        self._init_title_bar()
        self._init_menu_bar()
        self._init_central_widget()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("Meridian")
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

    def _init_title_bar(self):
        """Use the Windows DWM API to force a light (white) title bar."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(0)          # 0 = light / white title bar
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
        except Exception:
            pass

    def _init_menu_bar(self):
        self.setMenuBar(MenuBar(self._config, parent=self))

    def _init_central_widget(self):
        """Build the central area: empty state + footer."""
        central = QWidget()
        central.setAutoFillBackground(True)
        palette = central.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(BG_BASE))
        central.setPalette(palette)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Empty state (shown when no games/emulators) ---------------
        empty = QWidget()
        empty.setObjectName("emptyState")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(16)

        # Logo — solid tint matching the text colour
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if _LOGO.exists():
            pm = _tint_pixmap(str(_LOGO), QColor(FG_SECONDARY), 56)
            logo_label.setPixmap(pm)
        empty_layout.addWidget(logo_label)

        msg = QLabel("Whoops. Nothing's here but us snowmen.")
        msg.setObjectName("emptyMessage")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(msg)

        root.addWidget(empty, 1)

        # -- Footer ----------------------------------------------------
        # Use a QWidget with two overlapping layouts so the connection
        # icon is always in the absolute center regardless of text widths.
        footer = QWidget()
        footer.setObjectName("footer")

        # Layer 1: left version + right buttons
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 0, 10, 0)
        footer_layout.setSpacing(8)

        version_label = QLabel("N/A")
        version_label.setObjectName("footerVersion")
        footer_layout.addWidget(version_label)

        footer_layout.addStretch()

        btn_repo = QPushButton("Repository")
        btn_repo.setObjectName("footerButton")
        btn_repo.setFlat(True)
        btn_repo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_repo.clicked.connect(lambda: webbrowser.open(_REPO_URL))
        footer_layout.addWidget(btn_repo)

        btn_credits = QPushButton("Credits")
        btn_credits.setObjectName("footerButton")
        btn_credits.setFlat(True)
        btn_credits.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_credits.clicked.connect(self._on_credits)
        footer_layout.addWidget(btn_credits)

        # Layer 2: connection icon pinned to absolute center
        self._conn_icon = QLabel(footer)
        self._conn_icon.setPixmap(lucide_pixmap("wifi-off", 14, FG_DISABLED))
        self._conn_icon.setToolTip("Not connected")
        self._conn_icon.setFixedSize(20, 20)
        self._conn_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Position will be updated on resize
        footer.resizeEvent = lambda e, f=footer: self._center_conn_icon(f)

        root.addWidget(footer)

        self.setCentralWidget(central)

    def _center_conn_icon(self, footer: QWidget):
        """Keep the connection icon at the exact center of the footer."""
        x = (footer.width() - self._conn_icon.width()) // 2
        y = (footer.height() - self._conn_icon.height()) // 2
        self._conn_icon.move(x, y)

    def _on_credits(self):
        CreditsDialog(parent=self).exec()

    # ------------------------------------------------------------------
    # 16:9 aspect-ratio lock  (flicker-free, via native WM_SIZING)
    # ------------------------------------------------------------------

    def nativeEvent(self, eventType, message):
        """Intercept WM_SIZING to enforce 16:9 *before* the OS resizes the window."""
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            msg = _WinMsg.from_address(int(message))
            if msg.message == _WM_SIZING:
                self._constrain_sizing_rect(msg)
                return True, 0
        return super().nativeEvent(eventType, message)

    def _constrain_sizing_rect(self, msg):
        """Modify the proposed RECT in-place so the window stays 16:9."""
        rect = ctypes.wintypes.RECT.from_address(msg.lParam)
        edge = msg.wParam

        # Frame overhead (title bar + window borders)
        frame_w = self.frameGeometry().width()  - self.geometry().width()
        frame_h = self.frameGeometry().height() - self.geometry().height()

        # Proposed client-area size
        client_w = (rect.right - rect.left) - frame_w
        client_h = (rect.bottom - rect.top) - frame_h

        # Decide which dimension is "driving" based on which edge is dragged
        if edge in _EDGES_HEIGHT_DRIVEN:
            client_w = round(client_h * self.ASPECT_RATIO)
        else:
            client_h = round(client_w / self.ASPECT_RATIO)

        # Enforce minimums
        if client_w < self.MIN_WIDTH:
            client_w = self.MIN_WIDTH
            client_h = round(client_w / self.ASPECT_RATIO)
        if client_h < self.MIN_HEIGHT:
            client_h = self.MIN_HEIGHT
            client_w = round(client_h * self.ASPECT_RATIO)

        new_w = client_w + frame_w
        new_h = client_h + frame_h

        # Anchor the rect so the edge the user is NOT dragging stays fixed
        if edge in _EDGES_ANCHOR_LEFT:
            rect.left = rect.right - new_w
        else:
            rect.right = rect.left + new_w

        if edge in _EDGES_ANCHOR_TOP:
            rect.top = rect.bottom - new_h
        else:
            rect.bottom = rect.top + new_h


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _tint_pixmap(path: str, color: QColor, width: int) -> QPixmap:
    """Load an image, scale it, and tint all visible pixels to *color*."""
    img = QImage(path)
    img = img.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
    img = img.convertToFormat(QImage.Format.Format_ARGB32)

    for y in range(img.height()):
        for x in range(img.width()):
            px = img.pixelColor(x, y)
            if px.alpha() > 0:
                img.setPixelColor(x, y, QColor(
                    color.red(), color.green(), color.blue(), px.alpha()
                ))

    return QPixmap.fromImage(img)
