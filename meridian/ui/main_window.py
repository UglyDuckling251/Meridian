import sys
import os
import ctypes
import webbrowser
import subprocess
import shlex
import time
import threading
import struct
import shutil
import json
import re
import html
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QGraphicsOpacityEffect, QListWidget, QListWidgetItem,
    QListView, QMenu, QFileDialog, QInputDialog, QProgressDialog, QApplication,
)
from PySide6.QtGui import (
    QPalette, QColor, QPixmap, QPainter, QImage, QRadialGradient, QCursor, QIcon,
)
from PySide6.QtCore import (
    Qt, QEvent, QTimer, QPropertyAnimation, QEasingCurve, QPointF, QSize,
)

from meridian.core.config import (
    Config, SYSTEM_EXTENSIONS, SYSTEM_NAMES, emulator_catalog_entry, SCRAPER_SOURCE_MAP,
)
from meridian.core.emulator_setup import auto_configure_emulator
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

_RETROARCH_CORE_CANDIDATES: dict[str, list[str]] = {
    "nes": ["fceumm_libretro.dll", "nestopia_libretro.dll"],
    "snes": ["snes9x_libretro.dll", "bsnes_libretro.dll"],
    "n64": ["mupen64plus_next_libretro.dll", "parallel_n64_libretro.dll"],
    "gb": ["gambatte_libretro.dll", "sameboy_libretro.dll"],
    "gbc": ["gambatte_libretro.dll", "sameboy_libretro.dll"],
    "gba": ["mgba_libretro.dll"],
    "nds": ["melonds_libretro.dll", "desmume_libretro.dll"],
    "genesis": ["genesis_plus_gx_libretro.dll", "picodrive_libretro.dll"],
    "sms": ["genesis_plus_gx_libretro.dll", "picodrive_libretro.dll"],
    "gg": ["genesis_plus_gx_libretro.dll", "picodrive_libretro.dll"],
    "saturn": ["mednafen_saturn_libretro.dll"],
    "dreamcast": ["flycast_libretro.dll"],
    "ps1": ["duckstation_libretro.dll", "pcsx_rearmed_libretro.dll"],
    "psp": ["ppsspp_libretro.dll"],
    "atari7800": ["prosystem_libretro.dll"],
    "lynx": ["handy_libretro.dll"],
    "jaguar": ["virtualjaguar_libretro.dll"],
    "tg16": ["mednafen_pce_fast_libretro.dll", "mednafen_pce_libretro.dll"],
    "ngp": ["mednafen_ngp_libretro.dll"],
    "mame": ["mame_libretro.dll", "fbneo_libretro.dll"],
}

_SYSTEM_BIOS_IDS: dict[str, list[str]] = {
    "nes": ["nes_fds_bios"],
    "gba": ["gba_bios"],
    "nds": ["nds_bios7", "nds_bios9", "nds_firmware", "dsi_bios7", "dsi_bios9", "dsi_firmware", "dsi_nand"],
    "3ds": ["n3ds_aes_keys", "n3ds_seeddb", "n3ds_boot9", "n3ds_boot11"],
    "n64": ["n64_pif"],
    "gc": ["gc_ipl"],
    "wii": ["wii_keys"],
    "wiiu": ["wiiu_keys"],
    "switch": ["switch_prod_keys", "switch_title_keys", "switch_firmware"],
    "genesis": ["sega_cd_us", "sega_cd_eu", "sega_cd_jp", "sega32x_m68k", "sega32x_master", "sega32x_slave"],
    "saturn": ["saturn_bios_jp", "saturn_bios_us_eu"],
    "dreamcast": ["dc_boot", "dc_flash", "naomi_bios", "naomi2_bios", "atomiswave_bios"],
    "ps1": ["ps1_scp1001", "ps1_scp5500", "ps1_scp5502", "ps1_scp700x"],
    "ps2": ["ps2_main", "ps2_rom1", "ps2_rom2", "ps2_erom", "ps2_nvm"],
    "ps3": ["ps3_firmware"],
    "psp": ["psp_font", "psp_flash0"],
    "psvita": ["psvita_firmware"],
    "xbox": ["xbox_bios", "xbox_eeprom"],
    "xbox360": ["xbox360_nand", "xbox360_keys"],
    "atari7800": ["atari7800_bios"],
    "lynx": ["lynx_boot"],
    "jaguar": ["jaguar_bios", "jaguar_cd_bios"],
    "tg16": ["tg16_syscard1", "tg16_syscard2", "tg16_syscard3"],
    "neogeo": ["neogeo_zip"],
    "ngp": ["ngp_bios"],
    "mame": [
        "neogeo_zip", "mame_qsound", "mame_pgm", "mame_cps3", "mame_stvbios",
        "mame_hikaru", "mame_chihiro", "mame_model2", "mame_model3",
    ],
    "3do": ["3do_panafz10", "3do_panafz1", "3do_goldstar"],
    "vectrex": ["vectrex_bios"],
    "wonderswan": ["wswan_boot"],
    "msx": ["msx_bios", "msx2_bios", "msx2ext_bios", "msx_disk"],
    "dos": ["dosbox_roms"],
    "pc": ["dosbox_roms"],
}

_REQUIRED_BIOS_IDS: set[str] = {
    "gba_bios",
    "nds_bios7",
    "nds_bios9",
    "nds_firmware",
    "switch_prod_keys",
    "wiiu_keys",
    "saturn_bios_jp",
    "saturn_bios_us_eu",
    "dc_boot",
    "dc_flash",
    "ps1_scp1001",
    "ps2_main",
    "ps3_firmware",
    "lynx_boot",
    "jaguar_bios",
    "tg16_syscard3",
    "neogeo_zip",
    "3do_panafz10",
    "vectrex_bios",
}

_BIOS_FILENAME_ALIASES: dict[str, list[str]] = {
    "nes_fds_bios": ["disksys.rom"],
    "gba_bios": ["gba_bios.bin"],
    "nds_bios7": ["bios7.bin"],
    "nds_bios9": ["bios9.bin"],
    "nds_firmware": ["firmware.bin"],
    "dsi_bios7": ["dsi_bios7.bin"],
    "dsi_bios9": ["dsi_bios9.bin"],
    "dsi_firmware": ["dsi_firmware.bin"],
    "dsi_nand": ["dsi_nand.bin"],
    "n3ds_aes_keys": ["aes_keys.txt"],
    "n3ds_seeddb": ["seeddb.bin"],
    "n3ds_boot9": ["boot9.bin"],
    "n3ds_boot11": ["boot11.bin"],
    "gc_ipl": ["IPL.bin"],
    "wii_keys": ["keys.bin"],
    "wiiu_keys": ["keys.txt"],
    "switch_prod_keys": ["prod.keys"],
    "switch_title_keys": ["title.keys"],
    "saturn_bios_jp": ["sega_101.bin"],
    "saturn_bios_us_eu": ["mpr-17933.bin"],
    "dc_boot": ["dc_boot.bin"],
    "dc_flash": ["dc_flash.bin"],
    "ps1_scp1001": ["scph1001.bin", "scph5501.bin"],
    "ps1_scp5500": ["scph5500.bin"],
    "ps1_scp5502": ["scph5502.bin"],
    "ps1_scp700x": ["scph7001.bin", "scph7003.bin", "scph7502.bin"],
    "ps2_main": ["scph10000.bin"],
    "ps2_rom1": ["rom1.bin"],
    "ps2_rom2": ["rom2.bin"],
    "ps2_erom": ["erom.bin"],
    "ps2_nvm": ["nvm.bin"],
    "ps3_firmware": ["PS3UPDAT.PUP"],
    "atari7800_bios": ["7800 BIOS (U).rom"],
    "lynx_boot": ["lynxboot.img"],
    "jaguar_bios": ["jagboot.rom"],
    "jaguar_cd_bios": ["jagcd.bin"],
    "tg16_syscard1": ["syscard1.pce"],
    "tg16_syscard2": ["syscard2.pce"],
    "tg16_syscard3": ["syscard3.pce"],
    "neogeo_zip": ["neogeo.zip"],
    "mame_qsound": ["qsound.zip"],
    "mame_pgm": ["pgm.zip"],
    "mame_cps3": ["cps3.zip"],
    "mame_stvbios": ["stvbios.zip"],
    "mame_hikaru": ["hikaru.zip"],
    "mame_chihiro": ["chihiro.zip"],
    "mame_model2": ["model2.zip"],
    "mame_model3": ["model3.zip"],
    "3do_panafz10": ["panafz10.bin"],
    "3do_panafz1": ["panafz1.bin"],
    "3do_goldstar": ["goldstar.bin"],
    "vectrex_bios": ["bios.bin"],
    "wswan_boot": ["wswanboot.bin"],
    "msx_bios": ["MSX.ROM"],
    "msx2_bios": ["MSX2.ROM"],
    "msx2ext_bios": ["MSX2EXT.ROM"],
    "msx_disk": ["DISK.ROM"],
}


@dataclass(frozen=True)
class _ScannedGame:
    title: str
    path: Path
    system_id: str
    emulator_name: str
    added_at: float
    hidden: bool = False

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
        self._set_loading_text("Checking project requirements...")
        QApplication.processEvents()

        # -- 0. Ensure runtime dependencies are installed/updated ----------
        self._ensure_project_requirements()
        QApplication.processEvents()
        self._set_loading_text("Loading libraries...")
        QApplication.processEvents()

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
        self._set_loading_text("Starting Meridian...")
        self._fade_out_overlay()
        QTimer.singleShot(0, lambda: self.scan_rom_directories(interactive=False))

    def _set_loading_text(self, text: str) -> None:
        """Update loading overlay text if the overlay is present."""
        if self._overlay is not None and self._overlay_label is not None:
            self._overlay_label.setText(text)

    def _ensure_project_requirements(self) -> None:
        """Install/update dependencies from requirements.txt during startup."""
        req_file = _ROOT / "requirements.txt"
        if not req_file.exists():
            return

        # Best-effort update: keep startup resilient if network/pip is unavailable.
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--disable-pip-version-check",
            "--upgrade",
            "-r", str(req_file),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            err = err[-700:] if err else "Unknown pip error."
            QMessageBox.warning(
                self,
                "Dependency update failed",
                "Meridian could not update/install some project requirements.\n\n"
                f"pip output:\n{err}",
            )

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
        """Build the central area: background + game list + footer."""
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

        # -- Content area (empty state + games list) -------------------
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

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
        self._empty_message = msg
        msg.setObjectName("emptyMessage")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(msg)

        # Cursor glow — lives inside the content area only
        self._cursor_glow = _CursorGlow(empty)
        self._cursor_glow.setGeometry(0, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self._cursor_glow.raise_()

        self._games_list = QListWidget()
        self._games_list.setObjectName("gamesList")
        self._games_list.setAlternatingRowColors(True)
        self._games_list.itemDoubleClicked.connect(self._on_game_activated)
        self._games_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._games_list.customContextMenuRequested.connect(self._on_games_context_menu)
        self._games_list.hide()
        self._games_list.setViewMode(QListView.ViewMode.ListMode)

        content_layout.addWidget(empty, 1)
        content_layout.addWidget(self._games_list, 1)
        root.addWidget(content, 1)

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
        self._games: list[_ScannedGame] = []
        self._favorite_paths: set[str] = set()
        self._hidden_paths: set[str] = set()
        self._custom_titles: dict[str, str] = {}
        self._custom_icons: dict[str, str] = {}
        self._play_time_minutes: dict[str, int] = {}
        self._updates_by_game: dict[str, list[str]] = {}
        self._dlc_by_game: dict[str, list[str]] = {}
        self._scraped_metadata: dict[str, dict] = {}
        self._view_mode = "list"
        self._sort_mode = "title"
        self._show_favorites_only = False
        self._show_hidden_games = False

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
        self.scan_rom_directories(interactive=False)

    def _on_credits(self):
        CreditsDialog(parent=self).exec()

    def _on_game_activated(self, item: QListWidgetItem) -> None:
        game_path = item.data(Qt.ItemDataRole.UserRole)
        if not game_path:
            return
        game = self._game_for_path(str(game_path))
        if game is None:
            return
        self._launch_game(game)

    def _launch_game(self, game: _ScannedGame) -> None:
        emulator = self._resolve_emulator_for_game(game)
        if emulator is None:
            QMessageBox.warning(
                self,
                "Launch Failed",
                "No emulator is configured for this game/system.\n"
                "Set one in Settings > Emulators > Configuration.",
            )
            return

        exe_path = self._resolve_launch_executable(emulator)
        if exe_path is None:
            exe_path = self._try_auto_install_emulator(emulator)
            if exe_path is None:
                QMessageBox.warning(
                    self,
                    "Launch Failed",
                    "Configured emulator executable was not found.\n\n"
                    f"Configured path:\n{emulator.path}",
                )
                return

        # Auto-configure the emulator (BIOS, ROM paths, input, etc.)
        auto_configure_emulator(emulator, game.path, game.system_id, exe_path, self._config)

        missing_bios = self._apply_bios_for_launch(emulator, game, exe_path)
        if missing_bios:
            QMessageBox.warning(
                self,
                "Missing Required BIOS",
                "Required BIOS files are missing for this system.\n\n"
                + "\n".join(f"- {item}" for item in missing_bios),
            )
            return

        cmd = self._build_launch_command(emulator, game, exe_path)
        if not cmd and "{core}" in self._effective_args_template(emulator):
            core_path = self._try_auto_download_core(emulator, game.system_id)
            if core_path:
                cmd = self._build_launch_command(emulator, game, exe_path)

        if not cmd:
            hint = "Check emulator arguments and required core/setup state."
            if "{core}" in self._effective_args_template(emulator):
                hint = (
                    "No compatible RetroArch core was found for this system.\n"
                    "Install a core in Settings > Emulators, then retry."
                )
            QMessageBox.warning(
                self,
                "Launch Failed",
                "Unable to build launch command.\n"
                f"{hint}",
            )
            return

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(exe_path.parent),
            )
            time.sleep(0.35)
            rc = proc.poll()
            if rc is not None:
                QMessageBox.warning(
                    self,
                    "Launch Failed",
                    "Emulator process exited immediately.\n\n"
                    f"Exit code: {rc}\n\n"
                    f"Command:\n{' '.join(cmd)}",
                )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Launch Failed",
                "Failed to start emulator process.\n\n"
                f"{exc}\n\n"
                f"Command:\n{' '.join(cmd)}",
            )

    def _resolve_emulator_for_game(self, game: _ScannedGame):
        name = (game.emulator_name or "").strip()
        if name and name.lower() != "unassigned":
            for entry in self._config.emulators:
                if entry.display_name().lower() == name.lower():
                    return entry

        for system in self._config.systems:
            if system.system_id != game.system_id:
                continue
            wanted = (system.emulator_name or "").strip().lower()
            if not wanted:
                continue
            for entry in self._config.emulators:
                if entry.display_name().lower() == wanted:
                    return entry

        for entry in self._config.emulators:
            catalog = emulator_catalog_entry(entry.catalog_id or entry.name)
            if catalog and game.system_id in catalog.systems:
                return entry
        return None

    def _resolve_launch_executable(self, emulator) -> Path | None:
        configured = Path(emulator.path)
        if configured.exists() and self._is_compatible_executable(configured):
            return configured

        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        preferred_names = [n.lower() for n in (catalog.exe_candidates if catalog else [])]

        install_dir = Path(emulator.install_dir) if emulator.install_dir else configured.parent
        search_dirs = [install_dir]

        # Also probe the default emulators directory for this catalog entry.
        if catalog and catalog.install_subdir:
            default_dir = _ROOT / "emulators" / catalog.install_subdir
            if default_dir != install_dir:
                search_dirs.append(default_dir)

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            exe_files = list(search_dir.rglob("*.exe"))
            if preferred_names:
                ranked = [p for p in exe_files if p.name.lower() in preferred_names]
                if ranked:
                    exe_files = ranked + [p for p in exe_files if p not in ranked]
            for path in exe_files:
                if self._is_compatible_executable(path):
                    return path

        return configured if configured.exists() and self._is_compatible_executable(configured) else None

    def _build_launch_command(self, emulator, game: _ScannedGame, exe_path: Path) -> list[str]:
        rom_path = str(game.path)
        args_template = self._effective_args_template(emulator).strip()
        if not args_template:
            args_template = '"{rom}"'

        core_override = ""
        if "{core}" in args_template:
            core_override = self._resolve_core_placeholder(emulator, game.system_id)
            if core_override:
                # Build explicit argv for RetroArch-style templates.
                return [str(exe_path), "-L", core_override, rom_path]

        rendered = (
            args_template
            .replace("{rom}", rom_path)
            .replace("{core}", core_override)
        )
        rendered = rendered.strip()
        if "{core}" in args_template and not core_override:
            # RetroArch-style templates require an explicit core.
            return []
        if not rendered:
            return [str(exe_path), rom_path]
        try:
            parsed = shlex.split(rendered, posix=True)
        except Exception:
            parsed = [rom_path]
        return [str(exe_path)] + parsed

    def _effective_args_template(self, emulator) -> str:
        args_template = (emulator.args or "").strip()
        if not args_template:
            args_template = '"{rom}"'

        name = emulator.display_name().lower()
        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        if catalog:
            name = catalog.id.lower()

        # Better defaults for emulators that otherwise just open to setup UI.
        if args_template == '"{rom}"':
            if name in {"retroarch"}:
                return '-L "{core}" "{rom}"'
            if name in {"cemu"}:
                return '-g "{rom}"'
            if name in {"pcsx2"}:
                return '-batch "{rom}"'

        # PCSX2 v2 (pcsx2-qt) does not support --nogui; strip it if present.
        if name in {"pcsx2"} and "--nogui" in args_template:
            args_template = args_template.replace("--nogui", "").strip()

        return args_template

    def _try_auto_install_emulator(self, emulator) -> Path | None:
        """Offer to download and install an emulator whose executable is missing."""
        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        if not catalog or catalog.install_strategy in ("manual", "retroarch_core"):
            return None
        if not catalog.windows_supported:
            return None

        reply = QMessageBox.question(
            self,
            "Emulator Not Found",
            f"{emulator.display_name()} is not installed at the configured path.\n\n"
            "Would you like to download and install it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return None

        progress = QProgressDialog(
            f"Downloading and installing {catalog.name}\u2026\n"
            "This may take a moment.",
            None, 0, 0, self,
        )
        progress.setWindowTitle("Installing Emulator")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()

        result_holder: list = [None]

        def _worker():
            from meridian.core.emulator_install import install_emulator as _install
            result_holder[0] = _install(catalog, self._config.emulators)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        while t.is_alive():
            QApplication.processEvents()
            t.join(timeout=0.05)

        progress.close()

        result = result_holder[0]
        if result and result.ok and result.entry:
            emulator.path = result.entry.path
            emulator.install_dir = result.entry.install_dir
            emulator.version = result.entry.version
            if not emulator.args or emulator.args.strip() == '"{rom}"':
                emulator.args = result.entry.args
            self._config.save()
            exe = Path(result.entry.path)
            if exe.exists():
                return exe

        if result and not result.ok:
            QMessageBox.warning(
                self,
                "Installation Failed",
                f"Could not install {catalog.name}.\n\n{result.message}",
            )
        return None

    def _try_auto_download_core(self, emulator, system_id: str) -> str:
        """Attempt to auto-download a RetroArch core for *system_id*."""
        candidates = _RETROARCH_CORE_CANDIDATES.get(system_id, [])
        if not candidates:
            return ""

        install_dir = (
            Path(emulator.install_dir) if emulator.install_dir
            else Path(emulator.path).parent
        )
        cores_dir = install_dir / "cores"
        dll_name = candidates[0]

        progress = QProgressDialog(
            f"Downloading RetroArch core:\n{dll_name}",
            None, 0, 0, self,
        )
        progress.setWindowTitle("Installing Core")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()

        result_holder: list = [None]

        def _worker():
            from meridian.core.emulator_install import download_single_retroarch_core
            result_holder[0] = download_single_retroarch_core(dll_name, cores_dir)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        while t.is_alive():
            QApplication.processEvents()
            t.join(timeout=0.05)

        progress.close()

        core_path = result_holder[0]
        if core_path:
            emulator.system_overrides[system_id] = dll_name
            if emulator.args.strip() == '"{rom}"':
                emulator.args = '-L "{core}" "{rom}"'
            self._config.save()
            return str(core_path)

        QMessageBox.warning(
            self,
            "Core Download Failed",
            f"Failed to download RetroArch core: {dll_name}\n\n"
            "You can try installing it manually in Settings > Emulators.",
        )
        return ""

    def _is_compatible_executable(self, path: Path) -> bool:
        if sys.platform != "win32":
            return path.exists()
        machine = self._pe_machine_type(path)
        if machine is None:
            return True
        arch = (ctypes.sizeof(ctypes.c_void_p) * 8)
        # x86 process can only load x86 images; x64 process cannot launch arm64.
        if arch == 32:
            return machine in {0x014C}  # I386
        return machine in {0x8664, 0x014C}  # AMD64 or I386

    @staticmethod
    def _pe_machine_type(path: Path) -> int | None:
        try:
            with path.open("rb") as f:
                dos = f.read(64)
                if len(dos) < 64 or dos[:2] != b"MZ":
                    return None
                pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
                f.seek(pe_offset)
                sig = f.read(6)
                if len(sig) < 6 or sig[:4] != b"PE\x00\x00":
                    return None
                machine = struct.unpack_from("<H", sig, 4)[0]
                return int(machine)
        except Exception:
            return None

    def _apply_bios_for_launch(self, emulator, game: _ScannedGame, exe_path: Path) -> list[str]:
        """Stage configured BIOS files into likely emulator lookup locations."""
        bios_cfg = dict(getattr(self._config, "bios_files", {}) or {})
        bios_ids = _SYSTEM_BIOS_IDS.get(game.system_id, [])
        if not bios_ids:
            return []

        target_dirs = self._bios_target_dirs(emulator, exe_path)
        missing_required: list[str] = []
        for bios_id in bios_ids:
            src_raw = str(bios_cfg.get(bios_id, "")).strip()
            if not src_raw:
                if bios_id in _REQUIRED_BIOS_IDS:
                    missing_required.append(bios_id)
                continue
            src = Path(src_raw)
            if not src.exists():
                if bios_id in _REQUIRED_BIOS_IDS:
                    missing_required.append(f"{bios_id} (file missing)")
                continue

            aliases = _BIOS_FILENAME_ALIASES.get(bios_id, [src.name])
            for dest_dir in target_dirs:
                for alias in aliases:
                    try:
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest_dir / alias)
                    except Exception:
                        continue

        # Cemu uses a "portable" directory marker to keep data next to the exe.
        # Without it, a fresh install looks for keys.txt in user AppData instead.
        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        emu_id = catalog.id.lower() if catalog else emulator.display_name().lower()
        if "cemu" in emu_id:
            try:
                (exe_path.parent / "portable").mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        return missing_required

    def _bios_target_dirs(self, emulator, exe_path: Path) -> list[Path]:
        install_dir = Path(emulator.install_dir) if emulator.install_dir else exe_path.parent
        name = emulator.display_name().lower()
        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        if catalog:
            name = catalog.id.lower()

        dirs: list[Path] = []
        # Always include the directory containing the actual executable.
        dirs.append(exe_path.parent)
        # Common default locations used by many emulators.
        dirs.extend([install_dir, install_dir / "bios", install_dir / "system"])

        if "retroarch" in name:
            system_dir = install_dir / "system"
            dirs.extend(
                [
                    system_dir,
                    system_dir / "dc",
                    system_dir / "PPSSPP",
                    system_dir / "dolphin-emu" / "Sys",
                ]
            )
        if "pcsx2" in name:
            dirs.extend([install_dir / "bios", install_dir / "resources" / "bios"])
        if "duckstation" in name:
            dirs.extend([install_dir / "bios"])
        if "melonds" in name:
            dirs.extend([install_dir, install_dir / "bios"])
        if "cemu" in name:
            dirs.extend([exe_path.parent, exe_path.parent / "mlc01"])
            # Cemu non-portable mode stores keys in user data directories.
            if sys.platform == "win32":
                for env_var in ("LOCALAPPDATA", "APPDATA"):
                    env_path = os.environ.get(env_var, "")
                    if env_path:
                        dirs.append(Path(env_path) / "Cemu")

        # De-duplicate while preserving order.
        unique: list[Path] = []
        seen: set[str] = set()
        for d in dirs:
            key = str(d.resolve()) if d.exists() else str(d)
            if key in seen:
                continue
            seen.add(key)
            unique.append(d)
        return unique

    def _resolve_core_placeholder(self, emulator, system_id: str) -> str:
        core_name = str(emulator.system_overrides.get(system_id, "") or "").strip()
        install_dir = Path(emulator.install_dir) if emulator.install_dir else None
        cores_dir = (install_dir / "cores") if install_dir else None

        if core_name:
            core_path = Path(core_name)
            if core_path.exists():
                return str(core_path)
            if cores_dir:
                candidate = cores_dir / core_name
                if candidate.exists():
                    return str(candidate)

        candidate_names: list[str] = []
        if core_name:
            candidate_names.append(core_name)
        candidate_names.extend(_RETROARCH_CORE_CANDIDATES.get(system_id, []))

        if cores_dir and cores_dir.exists():
            # Direct exact-name matches first.
            for name in candidate_names:
                candidate = cores_dir / name
                if candidate.exists():
                    return str(candidate)

            # Case-insensitive match fallback.
            by_lower = {p.name.lower(): p for p in cores_dir.glob("*_libretro.dll")}
            for name in candidate_names:
                found = by_lower.get(name.lower())
                if found:
                    return str(found)

            # Last resort: if there is exactly one core, use it.
            all_cores = sorted(cores_dir.glob("*_libretro.dll"))
            if len(all_cores) == 1:
                return str(all_cores[0])

        # If a name is set but cannot be resolved, still return it so the
        # emulator can attempt resolution relative to its own runtime paths.
        return core_name

    def _on_games_context_menu(self, pos) -> None:
        item = self._games_list.itemAt(pos)
        if item is None:
            return
        game_path = item.data(Qt.ItemDataRole.UserRole)
        if not game_path:
            return
        game = self._game_for_path(str(game_path))
        if game is None:
            return

        menu = QMenu(self)
        is_fav = str(game_path) in self._favorite_paths

        rename_action = menu.addAction("Rename")
        icon_action = menu.addAction("Change Icon")
        menu.addSeparator()
        update_action = menu.addAction("Add Update")
        dlc_action = menu.addAction("Add DLC")
        menu.addSeparator()
        fav_action = menu.addAction("Unfavorite" if is_fav else "Favorite")
        menu.addSeparator()

        total_minutes = int(self._play_time_minutes.get(str(game.path), 0))
        info_play = menu.addAction(f"Total Play Time: {self._format_minutes(total_minutes)}")
        info_emu = menu.addAction(f"Emulator: {game.emulator_name or 'Unassigned'}")
        system_name = SYSTEM_NAMES.get(game.system_id, game.system_id.upper())
        info_system = menu.addAction(
            f"System/Brand: {system_name} / {self._system_brand(game.system_id)}"
        )
        info_play.setEnabled(False)
        info_emu.setEnabled(False)
        info_system.setEnabled(False)

        selected = menu.exec(self._games_list.mapToGlobal(pos))
        if selected == rename_action:
            current_title = self._display_title(game)
            new_title, ok = QInputDialog.getText(
                self,
                "Rename Game",
                "Display name:",
                text=current_title,
            )
            if ok:
                value = new_title.strip()
                path_key = str(game.path)
                if not value or value == game.title:
                    self._custom_titles.pop(path_key, None)
                else:
                    self._custom_titles[path_key] = value
                self._refresh_games_view()
            return
        if selected == icon_action:
            icon_path, _ = QFileDialog.getOpenFileName(
                self,
                "Choose Game Icon",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.webp *.ico)",
            )
            if icon_path:
                self._custom_icons[str(game.path)] = icon_path
                self._refresh_games_view()
            return
        if selected == update_action:
            update_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Update Package",
                "",
                "All Files (*.*)",
            )
            if update_path:
                self._updates_by_game.setdefault(str(game.path), []).append(update_path)
            return
        if selected == dlc_action:
            dlc_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select DLC Package",
                "",
                "All Files (*.*)",
            )
            if dlc_path:
                self._dlc_by_game.setdefault(str(game.path), []).append(dlc_path)
            return
        if selected == fav_action:
            path_key = str(game_path)
            if is_fav:
                self._favorite_paths.discard(path_key)
            else:
                self._favorite_paths.add(path_key)
            self._refresh_games_view()
            return

    def set_view_mode(self, mode: str) -> None:
        self._view_mode = "grid" if mode == "grid" else "list"
        if self._view_mode == "grid":
            self._games_list.setViewMode(QListView.ViewMode.IconMode)
            self._games_list.setGridSize(QSize(320, 40))
        else:
            self._games_list.setViewMode(QListView.ViewMode.ListMode)
            self._games_list.setGridSize(QSize())
        self._refresh_games_view()

    def set_sort_mode(self, mode: str) -> None:
        if mode in {"title", "platform", "added", "played", "count"}:
            self._sort_mode = mode
        self._refresh_games_view()

    def set_show_favorites_only(self, enabled: bool) -> None:
        self._show_favorites_only = bool(enabled)
        self._refresh_games_view()

    def set_show_hidden_games(self, enabled: bool) -> None:
        self._show_hidden_games = bool(enabled)
        self._refresh_games_view()

    def select_all_games(self) -> None:
        if not self._games_list.isVisible():
            return
        self._games_list.selectAll()

    def deselect_all_games(self) -> None:
        self._games_list.clearSelection()

    def scrape_metadata_library(self) -> None:
        self._run_metadata_scrape(self._games, "library")

    def scrape_selected_metadata(self) -> None:
        selected = self._games_list.selectedItems()
        if not selected:
            QMessageBox.information(
                self,
                "Scrape Selected Metadata",
                "No games selected. Select one or more games first.",
            )
            return
        selected_games: list[_ScannedGame] = []
        for item in selected:
            game_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
            game = self._game_for_path(game_path)
            if game:
                selected_games.append(game)
        self._run_metadata_scrape(selected_games, "selection")

    def _run_metadata_scrape(self, games: list[_ScannedGame], scope: str) -> None:
        if not games:
            QMessageBox.information(self, "Scrape Metadata", "No games available to scrape.")
            return
        source_name = self._config.scraper_source
        source = SCRAPER_SOURCE_MAP.get(source_name)
        if not source:
            QMessageBox.warning(self, "Scrape Metadata", f"Unknown scraper source: {source_name}")
            return

        creds = dict(self._config.scraper_credentials.get(source_name, {}))
        missing = [
            key for key, _label, _placeholder, _secret in source.auth_fields
            if not str(creds.get(key, "")).strip()
        ]
        if missing:
            QMessageBox.warning(
                self,
                "Scrape Metadata",
                f"{source_name} requires credentials before scraping.\n"
                f"Missing fields: {', '.join(missing)}",
            )
            return

        progress = QProgressDialog(f"Scraping metadata via {source_name}...", "", 0, len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()

        ok_count = 0
        fail_count = 0
        last_error = ""
        for idx, game in enumerate(games, start=1):
            progress.setValue(idx - 1)
            progress.setLabelText(f"Scraping {idx}/{len(games)}: {game.title}")
            QApplication.processEvents()
            try:
                metadata = self._scrape_game_metadata(source_name, creds, game)
                if metadata:
                    self._scraped_metadata[str(game.path)] = metadata
                    # Use scraped title unless user already chose a custom one.
                    scraped_title = str(metadata.get("title", "")).strip()
                    if scraped_title and str(game.path) not in self._custom_titles:
                        self._custom_titles[str(game.path)] = scraped_title
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception as exc:
                fail_count += 1
                last_error = str(exc)

        progress.setValue(len(games))
        self._refresh_games_view()

        message = (
            f"Source: {source_name}\n"
            f"Scope: {scope}\n"
            f"Scraped successfully: {ok_count}\n"
            f"Failed: {fail_count}"
        )
        if last_error:
            message += f"\n\nLast error:\n{last_error}"
        QMessageBox.information(self, "Scrape Metadata", message)

    def _scrape_game_metadata(self, source_name: str, creds: dict, game: _ScannedGame) -> dict:
        query = self._scrape_query_for_game(game)
        if source_name == "ScreenScraper":
            return self._scrape_screenscraper(query, creds)
        if source_name == "TheGamesDB":
            return self._scrape_thegamesdb(query, creds)
        if source_name == "IGDB":
            return self._scrape_igdb(query, creds)
        if source_name == "LaunchBox DB":
            return self._scrape_launchbox(query)
        if source_name == "MobyGames":
            return self._scrape_mobygames(query, creds)
        if source_name == "OpenRetro":
            return self._scrape_openretro(query)
        raise RuntimeError(f"{source_name} scraping adapter is not implemented yet.")

    def _scrape_query_for_game(self, game: _ScannedGame) -> str:
        raw = self._display_title(game) or game.title
        cleaned = re.sub(r"\[[^\]]+\]", " ", raw)
        cleaned = re.sub(r"\([^)]+\)", " ", cleaned)
        cleaned = re.sub(r"[_\.]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or game.title

    def _http_get_json(self, url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> dict:
        req = urllib.request.Request(url, headers=headers or {}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as res:
            payload = res.read().decode("utf-8", errors="replace")
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
        return {"data": data}

    def _http_post_json(
        self,
        url: str,
        data: str,
        headers: dict[str, str] | None = None,
        timeout: int = 15,
    ) -> dict:
        encoded = data.encode("utf-8")
        req = urllib.request.Request(
            url,
            data=encoded,
            headers=headers or {},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            payload = res.read().decode("utf-8", errors="replace")
        obj = json.loads(payload)
        if isinstance(obj, dict):
            return obj
        return {"data": obj}

    def _http_get_text(self, url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> str:
        req = urllib.request.Request(url, headers=headers or {}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read().decode("utf-8", errors="replace")

    def _scrape_screenscraper(self, query: str, creds: dict) -> dict:
        username = str(creds.get("username", "")).strip()
        password = str(creds.get("password", "")).strip()
        devid = str(creds.get("devid", "Meridian")).strip() or "Meridian"
        devpassword = str(creds.get("devpassword", "meridian")).strip() or "meridian"
        softname = "Meridian"

        base = "https://api.screenscraper.fr/gameinfos.php"
        candidates = [
            {"romnom": query},
            {"game": query},
            {"search": query},
        ]
        for extra in candidates:
            params = {
                "output": "json",
                "devid": devid,
                "devpassword": devpassword,
                "softname": softname,
                "ssid": username,
                "sspassword": password,
            }
            params.update(extra)
            url = f"{base}?{urllib.parse.urlencode(params)}"
            try:
                data = self._http_get_json(url)
            except Exception:
                continue
            game = data.get("response") or data.get("jeu") or data.get("game") or data
            if not isinstance(game, dict):
                continue
            title = (
                str(game.get("nom") or game.get("name") or query).strip()
            )
            desc = ""
            synopsis = game.get("synopsis")
            if isinstance(synopsis, list) and synopsis:
                first = synopsis[0]
                if isinstance(first, dict):
                    desc = str(first.get("text") or first.get("synopsis") or "").strip()
            elif isinstance(synopsis, dict):
                desc = str(synopsis.get("text") or synopsis.get("synopsis") or "").strip()
            elif isinstance(synopsis, str):
                desc = synopsis.strip()
            if title:
                return {"title": title, "description": desc, "source": "ScreenScraper", "raw": game}
        return {}

    def _scrape_thegamesdb(self, query: str, creds: dict) -> dict:
        api_key = str(creds.get("api_key", "")).strip()
        params = urllib.parse.urlencode({"apikey": api_key, "name": query})
        url = f"https://api.thegamesdb.net/v1.1/Games/ByGameName?{params}"
        data = self._http_get_json(url)
        games = (data.get("data") or {}).get("games") or []
        if not games:
            return {}
        g0 = games[0]
        title = str(g0.get("game_title") or g0.get("name") or query).strip()
        overview = g0.get("overview")
        if isinstance(overview, dict):
            overview = overview.get("en") or next(iter(overview.values()), "")
        return {
            "title": title,
            "description": str(overview or "").strip(),
            "source": "TheGamesDB",
            "raw": g0,
        }

    def _scrape_igdb(self, query: str, creds: dict) -> dict:
        client_id = str(creds.get("client_id", "")).strip()
        client_secret = str(creds.get("client_secret", "")).strip()
        token_params = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }
        )
        token_url = f"https://id.twitch.tv/oauth2/token?{token_params}"
        token_obj = self._http_post_json(token_url, data="")
        access_token = str(token_obj.get("access_token", "")).strip()
        if not access_token:
            raise RuntimeError("IGDB authentication failed: no access token returned.")

        body = (
            f'search "{query}"; '
            "fields name,summary,first_release_date; "
            "limit 1;"
        )
        headers = {
            "Client-ID": client_id,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "text/plain",
        }
        result = self._http_post_json("https://api.igdb.com/v4/games", data=body, headers=headers)
        games = result.get("data")
        if not isinstance(games, list):
            games = result if isinstance(result, list) else []
        if not games:
            return {}
        g0 = games[0]
        return {
            "title": str(g0.get("name") or query).strip(),
            "description": str(g0.get("summary") or "").strip(),
            "source": "IGDB",
            "raw": g0,
        }

    def _scrape_mobygames(self, query: str, creds: dict) -> dict:
        api_key = str(creds.get("api_key", "")).strip()
        params = urllib.parse.urlencode({"api_key": api_key, "title": query})
        url = f"https://api.mobygames.com/v1/games?{params}"
        data = self._http_get_json(url)
        games = data.get("games") or data.get("data") or []
        if not games:
            return {}
        g0 = games[0] if isinstance(games, list) else {}
        return {
            "title": str(g0.get("title") or query).strip(),
            "description": str(g0.get("description") or "").strip(),
            "source": "MobyGames",
            "raw": g0,
        }

    def _scrape_launchbox(self, query: str) -> dict:
        headers = {"User-Agent": "Meridian/1.0"}
        search_url = (
            "https://gamesdb.launchbox-app.com/games/results?"
            + urllib.parse.urlencode({"name": query})
        )
        page = self._http_get_text(search_url, headers=headers)
        m = re.search(r'href="(/games/details/[^"]+)"', page, flags=re.IGNORECASE)
        if not m:
            return {}
        detail_url = urllib.parse.urljoin("https://gamesdb.launchbox-app.com", m.group(1))
        detail_page = self._http_get_text(detail_url, headers=headers)

        title = ""
        tm = re.search(r"<title>(.*?)</title>", detail_page, flags=re.IGNORECASE | re.DOTALL)
        if tm:
            title = html.unescape(re.sub(r"\s+", " ", tm.group(1))).strip()
            title = re.sub(r"\s*\|\s*LaunchBox.*$", "", title, flags=re.IGNORECASE).strip()

        description = ""
        dm = re.search(
            r'<meta\s+name="description"\s+content="([^"]*)"',
            detail_page,
            flags=re.IGNORECASE,
        )
        if dm:
            description = html.unescape(dm.group(1)).strip()

        if not title:
            h1m = re.search(r"<h1[^>]*>(.*?)</h1>", detail_page, flags=re.IGNORECASE | re.DOTALL)
            if h1m:
                title = html.unescape(re.sub(r"<[^>]+>", "", h1m.group(1))).strip()

        if not title:
            return {}
        return {
            "title": title,
            "description": description,
            "source": "LaunchBox DB",
            "raw": {"url": detail_url},
        }

    def _scrape_openretro(self, query: str) -> dict:
        headers = {"User-Agent": "Meridian/1.0"}
        # Try JSON API style path first (used by some OpenRetro tooling).
        try:
            api_url = (
                "https://openretro.org/api/v1/search.json?"
                + urllib.parse.urlencode({"q": query})
            )
            data = self._http_get_json(api_url, headers=headers)
            results = data.get("results") or data.get("games") or data.get("data") or []
            if isinstance(results, list) and results:
                g0 = results[0] if isinstance(results[0], dict) else {}
                title = str(g0.get("name") or g0.get("title") or query).strip()
                desc = str(g0.get("description") or "").strip()
                if title:
                    return {"title": title, "description": desc, "source": "OpenRetro", "raw": g0}
        except Exception:
            pass

        # Fallback: parse website search result page.
        search_url = "https://openretro.org/list?" + urllib.parse.urlencode({"search": query})
        page = self._http_get_text(search_url, headers=headers)
        m = re.search(r'href="(/game/[^"]+)"', page, flags=re.IGNORECASE)
        if not m:
            return {}
        detail_url = urllib.parse.urljoin("https://openretro.org", m.group(1))
        detail_page = self._http_get_text(detail_url, headers=headers)

        title = ""
        tm = re.search(r"<title>(.*?)</title>", detail_page, flags=re.IGNORECASE | re.DOTALL)
        if tm:
            title = html.unescape(re.sub(r"\s+", " ", tm.group(1))).strip()
            title = re.sub(r"\s*-\s*OpenRetro.*$", "", title, flags=re.IGNORECASE).strip()
        if not title:
            h1m = re.search(r"<h1[^>]*>(.*?)</h1>", detail_page, flags=re.IGNORECASE | re.DOTALL)
            if h1m:
                title = html.unescape(re.sub(r"<[^>]+>", "", h1m.group(1))).strip()

        desc = ""
        dm = re.search(
            r'<meta\s+name="description"\s+content="([^"]*)"',
            detail_page,
            flags=re.IGNORECASE,
        )
        if dm:
            desc = html.unescape(dm.group(1)).strip()
        if not title:
            return {}
        return {
            "title": title,
            "description": desc,
            "source": "OpenRetro",
            "raw": {"url": detail_url},
        }

    def clear_metadata_cache(self) -> None:
        cache_dir = _ROOT / "cache" / "metadata"
        try:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._scraped_metadata.clear()
            QMessageBox.information(
                self,
                "Metadata Cache",
                f"Metadata cache cleared:\n{cache_dir}",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Metadata Cache",
                f"Failed to clear metadata cache:\n{exc}",
            )

    def scan_rom_directories(self, interactive: bool = True) -> None:
        """Scan all configured ROM paths and list every discovered game."""
        self._games = self._scan_all_games()
        self._refresh_games_view()
        if interactive:
            if self._games:
                QMessageBox.information(
                    self,
                    "Scan Complete",
                    f"Found {len(self._games)} game(s) across configured ROM paths.",
                )
            else:
                QMessageBox.information(
                    self,
                    "Scan Complete",
                    "No ROMs were found. Configure ROM directories in Settings.",
                )

    def _scan_all_games(self) -> list[_ScannedGame]:
        all_games: list[_ScannedGame] = []
        seen_paths: set[str] = set()
        configured_targets = self._configured_scan_targets()

        for root_dir, system_id, emulator_name in configured_targets:
            ext_values = self._extensions_for_system(system_id)
            if not ext_values:
                continue
            try:
                for file_path in root_dir.rglob("*"):
                    if not file_path.is_file():
                        continue
                    if file_path.suffix.lower() not in ext_values:
                        continue
                    resolved = str(file_path.resolve())
                    if resolved in seen_paths:
                        continue
                    seen_paths.add(resolved)
                    hidden = any(part.startswith(".") for part in file_path.parts)
                    stat = file_path.stat()
                    all_games.append(
                        _ScannedGame(
                            title=file_path.stem,
                            path=file_path,
                            system_id=system_id,
                            emulator_name=emulator_name,
                            added_at=float(stat.st_mtime),
                            hidden=hidden,
                        )
                    )
            except OSError:
                # Ignore inaccessible directories and continue scanning.
                continue

        all_games.sort(
            key=lambda g: (
                SYSTEM_NAMES.get(g.system_id, g.system_id).lower(),
                g.title.lower(),
            )
        )
        return all_games

    def _configured_scan_targets(self) -> list[tuple[Path, str, str]]:
        targets: list[tuple[Path, str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        emulators_by_name = {e.display_name().lower(): e for e in self._config.emulators}

        for system_entry in self._config.systems:
            system_id = (system_entry.system_id or "").strip()
            if not system_id:
                continue
            emu_name = (system_entry.emulator_name or "").strip()
            if system_entry.rom_directory:
                self._append_target(
                    targets,
                    seen,
                    Path(system_entry.rom_directory),
                    system_id,
                    emu_name or "Unassigned",
                )
            if emu_name:
                emu = emulators_by_name.get(emu_name.lower())
                if emu and emu.rom_directory:
                    self._append_target(
                        targets,
                        seen,
                        Path(emu.rom_directory),
                        system_id,
                        emu_name,
                    )

        for raw_dir in self._config.rom_directories:
            root = Path(raw_dir)
            for system_id in SYSTEM_EXTENSIONS:
                self._append_target(targets, seen, root, system_id, "Unassigned")

        for emulator in self._config.emulators:
            if not emulator.rom_directory:
                continue
            emu_name = emulator.display_name()
            catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
            system_ids = list(catalog.systems) if catalog else list(SYSTEM_EXTENSIONS.keys())
            for system_id in system_ids:
                self._append_target(
                    targets,
                    seen,
                    Path(emulator.rom_directory),
                    system_id,
                    emu_name or "Unassigned",
                )

        return targets

    def _append_target(
        self,
        targets: list[tuple[Path, str, str]],
        seen: set[tuple[str, str, str]],
        root: Path,
        system_id: str,
        emulator_name: str,
    ) -> None:
        try:
            normalized = str(root.resolve())
        except Exception:
            return
        key = (normalized.lower(), system_id, emulator_name.lower())
        if key in seen:
            return
        seen.add(key)
        if not root.exists() or not root.is_dir():
            return
        targets.append((root, system_id, emulator_name))

    @staticmethod
    def _extensions_for_system(system_id: str) -> set[str]:
        raw = SYSTEM_EXTENSIONS.get(system_id, "")
        values: set[str] = set()
        for ext in raw.split(","):
            ext = ext.strip().lower()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = "." + ext
            values.add(ext)
        return values

    def _refresh_games_view(self) -> None:
        self._games_list.clear()
        visible_games = self._visible_games()
        if not visible_games:
            self._games_list.hide()
            self._content_area.show()
            if self._show_favorites_only:
                self._empty_message.setText("No favorite games match the current view.")
            else:
                self._empty_message.setText("Whoops. Nothing's here but us snowmen.")
            return

        for game in visible_games:
            system_name = SYSTEM_NAMES.get(game.system_id, game.system_id.upper())
            emu_name = game.emulator_name or "Unassigned"
            display_title = self._display_title(game)
            prefix = ""
            if str(game.path) in self._favorite_paths:
                prefix += "★ "
            if str(game.path) in self._hidden_paths:
                prefix += "◌ "
            item = QListWidgetItem(f"{prefix}{display_title}  [{system_name}]  -  {emu_name}")
            item.setToolTip(str(game.path))
            item.setData(Qt.ItemDataRole.UserRole, str(game.path))
            icon_path = self._custom_icons.get(str(game.path), "")
            if icon_path:
                item.setIcon(QIcon(icon_path))
            self._games_list.addItem(item)

        self._content_area.hide()
        self._games_list.show()

    def _visible_games(self) -> list[_ScannedGame]:
        games = list(self._games)
        if not self._show_hidden_games:
            games = [
                g for g in games
                if (str(g.path) not in self._hidden_paths) and (not g.hidden)
            ]
        if self._show_favorites_only:
            games = [g for g in games if str(g.path) in self._favorite_paths]
        return self._sort_games(games)

    def _sort_games(self, games: list[_ScannedGame]) -> list[_ScannedGame]:
        if self._sort_mode == "platform":
            return sorted(
                games,
                key=lambda g: (
                    SYSTEM_NAMES.get(g.system_id, g.system_id).lower(),
                    g.title.lower(),
                ),
            )
        if self._sort_mode == "added":
            return sorted(games, key=lambda g: g.added_at, reverse=True)
        # Placeholders until playback tracking is implemented.
        if self._sort_mode in {"played", "count"}:
            return sorted(games, key=lambda g: self._display_title(g).lower())
        return sorted(games, key=lambda g: self._display_title(g).lower())

    def _game_for_path(self, game_path: str) -> _ScannedGame | None:
        for game in self._games:
            if str(game.path) == game_path:
                return game
        return None

    def _display_title(self, game: _ScannedGame) -> str:
        path_key = str(game.path)
        if path_key in self._custom_titles:
            return self._custom_titles[path_key]
        scraped = self._scraped_metadata.get(path_key, {})
        scraped_title = str(scraped.get("title", "")).strip()
        return scraped_title or game.title

    @staticmethod
    def _format_minutes(total_minutes: int) -> str:
        hours = max(total_minutes, 0) // 60
        minutes = max(total_minutes, 0) % 60
        return f"{hours}H {minutes}M"

    def _system_brand(self, system_id: str) -> str:
        if system_id in {"nes", "snes", "n64", "gc", "wii", "wiiu", "switch", "gb", "gbc", "gba", "nds", "3ds"}:
            return "Nintendo"
        if system_id in {"genesis", "saturn", "dreamcast", "sms", "gg"}:
            return "Sega"
        if system_id in {"ps1", "ps2", "ps3", "psp", "psvita"}:
            return "Sony"
        if system_id in {"xbox", "xbox360"}:
            return "Microsoft"
        if system_id in {"atari2600", "atari7800", "lynx", "jaguar"}:
            return "Atari"
        if system_id in {"tg16"}:
            return "NEC"
        if system_id in {"ngp", "neogeo"}:
            return "SNK"
        if system_id in {"mame"}:
            return "Arcade"
        return "Other"

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
