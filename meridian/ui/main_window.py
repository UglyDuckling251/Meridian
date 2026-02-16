import sys
import ctypes
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QGraphicsOpacityEffect, QStackedLayout,
)
from PySide6.QtGui import (
    QPalette, QColor, QPixmap, QPainter, QImage, QRadialGradient, QCursor,
)
from PySide6.QtCore import (
    Qt, QEvent, QTimer, QPropertyAnimation, QEasingCurve, QPointF,
)

from meridian.core.config import Config
from meridian.ui.menu_bar import MenuBar
from meridian.ui.style import active_theme
from meridian.ui.icons import pixmap as lucide_pixmap
from meridian.ui.credits_dialog import CreditsDialog
from meridian.ui.background import BackgroundWidget

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

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


class _CursorGlow(QWidget):
    """Transparent overlay that paints a soft radial glow under the cursor.

    The widget covers its parent, is invisible to mouse events
    (``WA_TransparentForMouseEvents``), and repaints at ~60 fps only
    while the parent window is active.
    """

    RADIUS = 35
    OPACITY = 10          # 0-255 — barely perceptible

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._pos = QPointF(-200, -200)

        self._timer = QTimer(self)
        self._timer.setInterval(16)          # ~60 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        gpos = QCursor.pos()
        lpos = self.mapFromGlobal(gpos)
        self._pos = QPointF(lpos)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = active_theme()
        center_color = QColor(t.accent_primary)
        center_color.setAlpha(self.OPACITY)
        edge_color = QColor(t.accent_primary)
        edge_color.setAlpha(0)

        grad = QRadialGradient(self._pos, self.RADIUS)
        grad.setColorAt(0.0, center_color)
        grad.setColorAt(1.0, edge_color)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawEllipse(self._pos, self.RADIUS, self.RADIUS)
        p.end()


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
        self._init_loading_overlay()

        # Kick off background services on the next event-loop tick so the
        # window is painted (with the black overlay) before any blocking work.
        QTimer.singleShot(0, self._init_services)

    # -- Loading overlay ---------------------------------------------------

    def _init_loading_overlay(self) -> None:
        """Create a black overlay that covers the entire window during init."""
        self._overlay = QWidget(self)
        self._overlay.setStyleSheet("background: black;")
        self._overlay.setGeometry(0, 0, self.width(), self.height())

        lbl = QLabel("Loading\u2026", self._overlay)
        lbl.setStyleSheet(
            "color: rgba(255,255,255,80); font-size: 10pt; background: transparent;"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setGeometry(0, 0, self.width(), self.height())

        self._overlay_label = lbl

        # Force the overlay above every sibling (menu bar labels, glow, etc.)
        self._overlay.raise_()

    def _raise_overlay(self) -> None:
        """Ensure the loading overlay sits above all other child widgets."""
        if self._overlay is not None:
            self._overlay.raise_()

    def _init_services(self) -> None:
        """Pre-load every heavy library and initialise background services.

        Runs while the black loading overlay is visible so the user never
        sees a stutter caused by a lazy first-import later on.
        """
        from PySide6.QtWidgets import QApplication

        self._raise_overlay()

        # -- 1. Heavy library imports (cached by Python for all later use) --
        import pygame                                   # noqa: F401
        QApplication.processEvents()

        import sounddevice                              # noqa: F401
        QApplication.processEvents()

        import zoneinfo                                 # noqa: F401
        QApplication.processEvents()

        import subprocess                               # noqa: F401
        import ctypes.util                              # noqa: F401

        # -- 2. InputManager (pygame joystick + SDL2 sensors) ---------------
        from meridian.core.input_manager import InputManager
        InputManager.instance().ensure_ready()
        QApplication.processEvents()

        # -- 3. AudioManager (pygame.mixer) ---------------------------------
        from meridian.core.audio_manager import AudioManager
        AudioManager.instance().refresh_devices()
        QApplication.processEvents()

        self._apply_audio_config()
        QApplication.processEvents()

        # -- All done — fade out the overlay --------------------------------
        self._fade_out_overlay()

    def _fade_out_overlay(self) -> None:
        """Animate the overlay from opaque to invisible, then remove it."""
        self._overlay_opacity = QGraphicsOpacityEffect(self._overlay)
        self._overlay.setGraphicsEffect(self._overlay_opacity)
        anim = QPropertyAnimation(self._overlay_opacity, b"opacity", self)
        anim.setDuration(400)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _on_finished():
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None

        anim.finished.connect(_on_finished)
        anim.start()
        # prevent GC while animating
        self._overlay_anim = anim

    def _apply_audio_config(self) -> None:
        """Initialise the audio mixer from the current config."""
        from meridian.core.audio_manager import AudioManager
        amgr = AudioManager.instance()
        amgr.init_mixer(
            volume=self._config.audio_volume,
            mono=self._config.audio_channel_mode == "Mono",
            mute=self._config.audio_mute,
        )

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
        t = active_theme()

        # Legal notice — pinned to the top-right of the menu bar
        self._legal_notice = QLabel("Ensure all ROMs are obtained legally!", self)
        self._legal_notice.setStyleSheet(
            f"color: {t.fg_disabled}; font-size: 8pt; background: transparent;"
        )
        self._legal_notice.adjustSize()
        self._legal_notice.raise_()

        # Clock — centered in the menu bar, hidden until enabled in settings
        self._clock_label = QLabel(self)
        self._clock_label.setStyleSheet(
            f"color: {t.fg_disabled}; font-size: 8pt; background: transparent;"
        )
        self._clock_label.hide()

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._apply_clock_config()

    def _init_central_widget(self):
        """Build the central area: background + empty state + footer."""
        central = QWidget()
        central.setAutoFillBackground(True)

        # Background layer (behind all content)
        self._bg_widget = BackgroundWidget(central)
        self._bg_widget.setGeometry(0, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self._bg_widget.lower()
        # Apply saved background
        self._bg_widget.set_mode(
            self._config.bg_type,
            self._config.bg_image_path,
            self._config.bg_animation,
            self._config.reduced_motion,
        )
        palette = central.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(active_theme().bg_base))
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
        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if _LOGO.exists():
            pm = _tint_pixmap(str(_LOGO), QColor(active_theme().fg_secondary), 56)
            self._logo_label.setPixmap(pm)
        empty_layout.addWidget(self._logo_label)

        msg = QLabel("Whoops. Nothing's here but us snowmen.")
        msg.setObjectName("emptyMessage")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(msg)

        # Cursor glow — lives inside the content area only
        self._cursor_glow = _CursorGlow(empty)
        self._cursor_glow.setGeometry(0, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self._cursor_glow.raise_()

        root.addWidget(empty, 1)

        # -- Footer ----------------------------------------------------
        footer = QWidget()
        footer.setObjectName("footer")

        # Main layout: version | resource labels | stretch | buttons
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 0, 10, 0)
        footer_layout.setSpacing(8)

        version_label = QLabel("N/A")
        version_label.setObjectName("footerVersion")
        version_label.setFixedWidth(40)
        footer_layout.addWidget(version_label)

        # Resource monitor labels (fixed position after version)
        self._lbl_cpu = QLabel("CPU --")
        self._lbl_gpu = QLabel("GPU --")
        self._lbl_mem = QLabel("MEM --")
        for lbl in (self._lbl_cpu, self._lbl_gpu, self._lbl_mem):
            lbl.setObjectName("footerResource")
            lbl.setFixedWidth(62)
            footer_layout.addWidget(lbl)

        footer_layout.addStretch()

        btn_repo = QPushButton("Repository")
        btn_repo.setObjectName("linkButton")
        btn_repo.setFlat(True)
        btn_repo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_repo.clicked.connect(lambda: webbrowser.open(_REPO_URL))
        footer_layout.addWidget(btn_repo)

        btn_credits = QPushButton("Credits")
        btn_credits.setObjectName("footerButton")
        btn_credits.setFlat(True)
        btn_credits.clicked.connect(self._on_credits)
        footer_layout.addWidget(btn_credits)

        # Connection icon pinned to absolute center
        self._conn_icon = QLabel(footer)
        self._conn_icon.setPixmap(lucide_pixmap("wifi-off", 14, active_theme().fg_disabled))
        self._conn_icon.setToolTip("Not connected")
        self._conn_icon.setFixedSize(20, 20)
        self._conn_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.resizeEvent = lambda e, f=footer: self._center_conn_icon(f)

        root.addWidget(footer)

        # Resource monitor timer (updates every 2 s)
        self._res_timer = QTimer(self)
        self._res_timer.setInterval(2000)
        self._res_timer.timeout.connect(self._update_resource_labels)
        self._res_timer.start()
        self._update_resource_labels()

        # Keep background widget sized to central widget
        _orig_resize = central.resizeEvent
        def _on_central_resize(event, _orig=_orig_resize):
            self._bg_widget.setGeometry(0, 0, central.width(), central.height())
            if _orig:
                _orig(event)
        central.resizeEvent = _on_central_resize

        # Keep cursor glow sized to the content area
        self._content_area = empty
        _orig_empty_resize = empty.resizeEvent
        def _on_empty_resize(event, _orig=_orig_empty_resize):
            self._cursor_glow.setGeometry(0, 0, empty.width(), empty.height())
            if _orig:
                _orig(event)
        empty.resizeEvent = _on_empty_resize

        self.setCentralWidget(central)

    def _center_conn_icon(self, footer: QWidget):
        """Keep the connection icon at the exact center of the footer."""
        x = (footer.width() - self._conn_icon.width()) // 2
        y = (footer.height() - self._conn_icon.height()) // 2
        self._conn_icon.move(x, y)

    # ------------------------------------------------------------------
    # Resource monitor
    # ------------------------------------------------------------------

    @staticmethod
    def _usage_color(percent: float) -> str:
        """Return a hex colour for a 0-100 % usage value."""
        if percent < 40:
            return "#4CAF50"   # green
        if percent < 75:
            return "#FFC107"   # amber
        return "#F44336"       # red

    def _update_resource_labels(self):
        """Poll CPU / GPU / MEM usage and recolour the footer labels."""
        if _HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory().percent
        else:
            cpu = mem = -1.0

        if cpu >= 0:
            cc = self._usage_color(cpu)
            self._lbl_cpu.setText(f"CPU {cpu:.0f}%")
            self._lbl_cpu.setStyleSheet(
                f"QLabel {{ color: {cc}; background: transparent; font-size: 8pt; }}"
            )
        else:
            self._lbl_cpu.setText("CPU --")

        if mem >= 0:
            mc = self._usage_color(mem)
            self._lbl_mem.setText(f"MEM {mem:.0f}%")
            self._lbl_mem.setStyleSheet(
                f"QLabel {{ color: {mc}; background: transparent; font-size: 8pt; }}"
            )
        else:
            self._lbl_mem.setText("MEM --")

        # GPU: best-effort via nvidia-smi (NVIDIA only); placeholder otherwise
        gpu = self._read_gpu_percent()
        if gpu >= 0:
            gc = self._usage_color(gpu)
            self._lbl_gpu.setText(f"GPU {gpu:.0f}%")
            self._lbl_gpu.setStyleSheet(
                f"QLabel {{ color: {gc}; background: transparent; font-size: 8pt; }}"
            )
        else:
            t = active_theme()
            self._lbl_gpu.setText("GPU --")
            self._lbl_gpu.setStyleSheet(
                f"QLabel {{ color: {t.fg_disabled}; background: transparent; font-size: 8pt; }}"
            )

    @staticmethod
    def _read_gpu_percent() -> float:
        """Try to read GPU utilisation.  Returns -1 if unavailable."""
        try:
            import subprocess
            kwargs: dict = dict(
                capture_output=True, text=True, timeout=2,
            )
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                **kwargs,
            )
            if r.returncode == 0 and r.stdout.strip():
                return float(r.stdout.strip().split("\n")[0])
        except Exception:
            pass
        return -1.0

    def apply_config(self, config: Config):
        """Re-apply settings that affect the main window (background, palette)."""
        self._config = config
        t = active_theme()

        self._bg_widget.set_mode(
            config.bg_type,
            config.bg_image_path,
            config.bg_animation,
            config.reduced_motion,
        )

        # Apply animation FPS from performance settings
        self._bg_widget.set_fps(config.background_fps)

        # Refresh the base palette in case the theme changed
        central = self.centralWidget()
        if central:
            palette = central.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor(t.bg_base))
            central.setPalette(palette)

        # Re-tint the logo and connection icon for the new theme
        if _LOGO.exists():
            self._logo_label.setPixmap(
                _tint_pixmap(str(_LOGO), QColor(t.fg_secondary), 56)
            )
        self._conn_icon.setPixmap(
            lucide_pixmap("wifi-off", 14, t.fg_disabled)
        )
        if hasattr(self, "_legal_notice"):
            self._legal_notice.setStyleSheet(
                f"color: {t.fg_disabled}; font-size: 8pt; background: transparent;"
            )
        if hasattr(self, "_clock_label"):
            self._clock_label.setStyleSheet(
                f"color: {t.fg_disabled}; font-size: 8pt; background: transparent;"
            )
            self._apply_clock_config()

        # Re-apply audio settings (volume, mute, channel mode)
        self._apply_audio_config()

    def _on_credits(self):
        CreditsDialog(parent=self).exec()

    # ------------------------------------------------------------------
    # Close guard
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_header_overlays()
        if self._overlay is not None:
            self._overlay.setGeometry(0, 0, self.width(), self.height())
            self._overlay_label.setGeometry(0, 0, self.width(), self.height())
            self._overlay.raise_()

    def _position_header_overlays(self):
        """Keep the legal notice and clock positioned on the menu bar."""
        mb = self.menuBar()
        mb_h = mb.height()

        if hasattr(self, "_legal_notice"):
            x = self.width() - self._legal_notice.width() - 10
            y = (mb_h - self._legal_notice.height()) // 2
            self._legal_notice.move(x, max(y, 0))
            self._legal_notice.raise_()

        if hasattr(self, "_clock_label") and self._clock_label.isVisible():
            self._clock_label.adjustSize()
            x = (self.width() - self._clock_label.width()) // 2
            y = (mb_h - self._clock_label.height()) // 2
            self._clock_label.move(x, max(y, 0))
            self._clock_label.raise_()

    # -- Header clock ------------------------------------------------------

    def _apply_clock_config(self):
        """Start or stop the clock based on the current config."""
        if self._config.show_clock:
            self._clock_label.show()
            self._update_clock()
            self._clock_timer.start()
        else:
            self._clock_label.hide()
            self._clock_timer.stop()

    def _update_clock(self):
        """Refresh the clock label text."""
        from datetime import datetime, timezone

        cfg = self._config
        use_24 = cfg.clock_format == "24-hour"
        fmt = "%H:%M:%S" if use_24 else "%I:%M:%S %p"

        try:
            if cfg.clock_source == "Selected timezone":
                import zoneinfo
                tz = zoneinfo.ZoneInfo(cfg.clock_timezone)
                now = datetime.now(tz)
            elif cfg.clock_source == "Fixed time":
                d = cfg.clock_fixed_date or "2000-01-01"
                t = cfg.clock_fixed_time or "12:00:00"
                now = datetime.fromisoformat(f"{d}T{t}")
            else:
                now = datetime.now()
        except Exception:
            now = datetime.now()

        self._clock_label.setText(now.strftime(fmt))
        self._position_header_overlays()

    def closeEvent(self, event):
        if self._config.confirm_on_exit:
            reply = QMessageBox.question(
                self,
                "Exit Meridian",
                "Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()

    def changeEvent(self, event):
        """Throttle background animations and mute audio when the window
        loses focus (if the respective options are enabled)."""
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            active = self.isActiveWindow()

            # Background CPU throttle
            if self._config.limit_background_cpu and self._bg_widget:
                if active:
                    self._bg_widget.set_fps(self._config.background_fps)
                else:
                    self._bg_widget.set_fps(5)

            # Cursor glow — pause when unfocused to save CPU
            if hasattr(self, "_cursor_glow"):
                if active:
                    self._cursor_glow._timer.start()
                else:
                    self._cursor_glow._timer.stop()
                    self._cursor_glow.update()

            # Background audio mute
            if self._config.audio_mute_background:
                from meridian.core.audio_manager import AudioManager
                amgr = AudioManager.instance()
                if active:
                    amgr.set_mute(self._config.audio_mute)
                else:
                    amgr.set_mute(True)

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
