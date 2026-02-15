import sys
import ctypes

from PySide6.QtWidgets import QMainWindow, QWidget
from PySide6.QtGui import QPalette, QColor

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
        self._init_window()
        self._init_title_bar()
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

    def _init_central_widget(self):
        """Set up the central widget with a dark background (canvas for future UI)."""
        central = QWidget()
        central.setAutoFillBackground(True)

        palette = central.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 24))
        central.setPalette(palette)

        self.setCentralWidget(central)

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
