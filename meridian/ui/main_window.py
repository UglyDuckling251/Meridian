# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

import sys
import os
import ctypes
import logging
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
import zipfile
import hashlib
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QGraphicsOpacityEffect, QListWidget, QListWidgetItem,
    QListView, QMenu, QFileDialog, QInputDialog, QProgressDialog, QApplication,
    QPlainTextEdit, QFrame,
)
from meridian.ui import dialogs as _msgbox
from PySide6.QtGui import (
    QPalette, QColor, QPixmap, QPainter, QImage, QRadialGradient, QCursor, QIcon,
    QPen, QConicalGradient, QLinearGradient,
)
from PySide6.QtCore import (
    Qt, QEvent, QTimer, QPropertyAnimation, QEasingCurve, QPointF, QSize,
    Slot, Signal, QThread,
)

from meridian.core.config import (
    Config, EmulatorEntry, SYSTEM_EXTENSIONS, SYSTEM_NAMES, emulator_catalog_entry, SCRAPER_SOURCE_MAP,
    BIOS_FILENAME_ALIASES,
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
log = logging.getLogger(__name__)
_LOGO = _ROOT / "assets" / "logo_transparent.png"
_REPO_URL = "https://github.com/UglyDuckling251/Meridian"
_SYSTEM_LOGO_SOURCE_HINT = Path(r"C:\Users\iront\Downloads\logos")
_SYSTEM_LOGO_ARCHIVE_DIR = _ROOT / "assets" / "logos"
_SYSTEM_LOGO_CACHE_BASE = _ROOT / "cache" / "logos"

_RETROARCH_CORE_CANDIDATES: dict[str, list[str]] = {
    "nes": ["fceumm_libretro.dll", "nestopia_libretro.dll", "mesen_libretro.dll"],
    "snes": ["snes9x_libretro.dll", "bsnes_libretro.dll"],
    "n64": ["mupen64plus_next_libretro.dll", "parallel_n64_libretro.dll"],
    "gb": ["gambatte_libretro.dll", "sameboy_libretro.dll", "mgba_libretro.dll"],
    "gbc": ["gambatte_libretro.dll", "sameboy_libretro.dll", "mgba_libretro.dll"],
    "gba": ["mgba_libretro.dll"],
    "nds": ["melonds_libretro.dll", "desmume_libretro.dll"],
    "genesis": ["genesis_plus_gx_libretro.dll", "picodrive_libretro.dll"],
    "sms": ["genesis_plus_gx_libretro.dll", "picodrive_libretro.dll"],
    "gg": ["genesis_plus_gx_libretro.dll", "picodrive_libretro.dll"],
    "saturn": ["mednafen_saturn_libretro.dll"],
    "dreamcast": ["flycast_libretro.dll"],
    "ps1": ["mednafen_psx_hw_libretro.dll", "swanstation_libretro.dll", "pcsx_rearmed_libretro.dll"],
    "psp": ["ppsspp_libretro.dll"],
    "atari2600": ["stella_libretro.dll"],
    "atari7800": ["prosystem_libretro.dll"],
    "lynx": ["handy_libretro.dll"],
    "jaguar": ["virtualjaguar_libretro.dll"],
    "tg16": ["mednafen_pce_fast_libretro.dll", "mednafen_pce_libretro.dll"],
    "ngp": ["mednafen_ngp_libretro.dll"],
    "neogeo": ["fbneo_libretro.dll"],
    "mame": ["mame_libretro.dll", "fbneo_libretro.dll"],
    "3do": ["opera_libretro.dll"],
    "vectrex": ["vecx_libretro.dll"],
    "wonderswan": ["mednafen_wswan_libretro.dll"],
    "msx": ["fmsx_libretro.dll", "bluemsx_libretro.dll"],
    "dos": ["dosbox_pure_libretro.dll"],
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

_BIOS_FILENAME_ALIASES = BIOS_FILENAME_ALIASES


@dataclass(frozen=True)
class _ScannedGame:
    title: str
    path: Path
    system_id: str
    emulator_name: str
    added_at: float
    hidden: bool = False


class _WorkerThread(QThread):
    """Generic background worker that runs a callable off the UI thread.

    Signals
    -------
    progress(int, str) : (value, label) – emitted by the callable via the
        callback passed as its first argument.
    result(object) : emitted once when the callable returns.
    error(str) : emitted if the callable raises.
    """
    progress = Signal(int, str)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            value = self._fn(self._emit_progress)
            self.result.emit(value)
        except Exception as exc:
            self.error.emit(str(exc))

    def _emit_progress(self, value: int, label: str = ""):
        self.progress.emit(value, label)


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


class _LogoPulse(QWidget):
    """Displays the logo with a smooth looping opacity pulse (low → opaque → low)."""

    _LOGO_H = 72
    _CYCLE_MS = 2400      # full pulse cycle duration
    _MIN_OPACITY = 0.18   # dimmest point
    _MAX_OPACITY = 0.85   # brightest point

    def __init__(self, logo_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")

        src = QPixmap(logo_path)
        if src.isNull():
            self._logo = QPixmap()
            self.setFixedSize(1, 1)
            return
        self._logo = src.scaledToHeight(
            self._LOGO_H, Qt.TransformationMode.SmoothTransformation,
        )
        white_logo = QPixmap(self._logo.size())
        white_logo.fill(Qt.GlobalColor.transparent)
        tint = QPainter(white_logo)
        tint.drawPixmap(0, 0, self._logo)
        tint.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        tint.fillRect(white_logo.rect(), QColor("#FFFFFF"))
        tint.end()
        self._logo = white_logo
        self.setFixedSize(self._logo.size())

        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        self._t = (self._t + 16.0 / self._CYCLE_MS) % 1.0
        self.update()

    def paintEvent(self, _event):
        if self._logo.isNull():
            return
        import math
        # Sine curve: 0→1→0 mapped to min→max→min opacity
        phase = 0.5 * (1.0 + math.sin(2.0 * math.pi * self._t - math.pi / 2.0))
        opacity = self._MIN_OPACITY + phase * (self._MAX_OPACITY - self._MIN_OPACITY)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setOpacity(opacity)
        p.drawPixmap(0, 0, self._logo)
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

        # Centre container for spinner + text
        container = QWidget(self._overlay)
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pulse = _LogoPulse(str(_LOGO), container)
        lay.addWidget(pulse, 0, Qt.AlignmentFlag.AlignCenter)
        self._overlay_spinner = pulse

        lbl = QLabel("Loading\u2026")
        lbl.setStyleSheet(
            "color: rgba(255,255,255,80); font-size: 10pt; background: transparent;"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

        verbose = QPlainTextEdit()
        verbose.setReadOnly(True)
        verbose.setFrameShape(QFrame.Shape.NoFrame)
        verbose.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        verbose.setMaximumBlockCount(220)
        verbose.setFixedWidth(640)
        verbose.setFixedHeight(130)
        verbose.setStyleSheet(
            "QPlainTextEdit {"
            " background: rgba(0,0,0,80);"
            " color: rgba(210,255,210,185);"
            " font-family: Consolas, 'Cascadia Mono', monospace;"
            " font-size: 8.8pt;"
            " border: 1px solid rgba(255,255,255,25);"
            " border-radius: 6px;"
            " padding: 6px;"
            "}"
        )
        verbose.setPlainText("[boot] Meridian startup initialized")
        lay.addWidget(verbose, 0, Qt.AlignmentFlag.AlignCenter)

        container.setGeometry(0, 0, self.width(), self.height())
        self._overlay_label = lbl
        self._overlay_verbose = verbose
        self._overlay_container = container

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

        # -- 0b. Ensure RetroArch is installed (required for all cores) ----
        self._set_loading_text("Checking RetroArch...")
        QApplication.processEvents()
        self._ensure_retroarch_ready()
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
            self._append_loading_verbose(f"[status] {text}")

    def _append_loading_verbose(self, line: str) -> None:
        """Append one line to the loading overlay's console panel."""
        if (
            self._overlay is not None
            and hasattr(self, "_overlay_verbose")
            and self._overlay_verbose is not None
            and line
        ):
            self._overlay_verbose.appendPlainText(line)
            sb = self._overlay_verbose.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _ensure_project_requirements(self) -> None:
        """Install/update Python dependencies during startup.

        All work runs in a daemon thread; the Qt event loop is pumped at
        ~16 ms so the loading animation keeps playing.  Nothing blocks the UI
        and no dialogs are shown — failures are logged silently.
        """
        req_file = _ROOT / "requirements.txt"

        result_holder: list = [None]

        def _run_all():
            if req_file.exists():
                try:
                    with queue_lock:
                        verbose_queue.append("[deps] checking requirements.txt")
                    with queue_lock:
                        verbose_queue.append("[deps] pip install -r requirements.txt --quiet")
                    result_holder[0] = subprocess.run(
                        [
                            sys.executable, "-m", "pip", "install",
                            "--disable-pip-version-check",
                            "--quiet",
                            "-r", str(req_file),
                        ],
                        capture_output=True, text=True,
                        timeout=600, check=False,
                    )
                    if result_holder[0] and result_holder[0].returncode == 0:
                        with queue_lock:
                            verbose_queue.append("[deps] requirements up to date")
                    else:
                        with queue_lock:
                            verbose_queue.append("[deps] requirements install returned non-zero")
                except Exception as exc:
                    with queue_lock:
                        verbose_queue.append(f"[deps] pip install failed: {exc}")
                    log.warning("pip install requirements failed: %s", exc)

        verbose_queue: list[str] = []
        queue_lock = threading.Lock()
        t = threading.Thread(target=_run_all, daemon=True)
        t.start()
        while t.is_alive():
            with queue_lock:
                pending = verbose_queue[:]
                verbose_queue.clear()
            for line in pending:
                self._append_loading_verbose(line)
            QApplication.processEvents()
            t.join(timeout=0.016)
        with queue_lock:
            pending = verbose_queue[:]
            verbose_queue.clear()
        for line in pending:
            self._append_loading_verbose(line)

    def _ensure_retroarch_ready(self) -> None:
        """Install or update RetroArch on startup as required."""
        from meridian.core.emulator_install import (
            find_retroarch_entry,
            ensure_retroarch_installed,
            update_retroarch,
        )

        ra = find_retroarch_entry(self._config.emulators)

        # Auto-install RetroArch if not present
        if not ra or not ra.path or not Path(ra.path).exists():
            self._set_loading_text("Installing RetroArch (required)...")
            QApplication.processEvents()
            result = ensure_retroarch_installed(self._config.emulators)
            if result.ok and result.entry:
                self._upsert_config_emulator(result.entry)
                self._config.save()
            elif not result.ok:
                _msgbox.warning(
                    self,
                    "RetroArch Required",
                    "Meridian requires RetroArch to run most emulator cores.\n\n"
                    f"Installation failed: {result.message}\n\n"
                    "You can try installing it manually from Settings > Emulators.",
                )
            return

        # Auto-update RetroArch if setting is enabled and version differs
        if self._config.retroarch_auto_update and ra:
            from meridian.core.config import EMULATOR_CATALOG_BY_ID
            catalog_ra = EMULATOR_CATALOG_BY_ID.get("retroarch")
            pinned = catalog_ra.preferred_version if catalog_ra else ""
            if pinned and ra.version == pinned:
                pass  # already up to date
            else:
                self._set_loading_text("Updating RetroArch...")
                QApplication.processEvents()
                result = update_retroarch(self._config.emulators)
                if result.ok and result.entry:
                    self._upsert_config_emulator(result.entry)
                    self._config.save()

    def _upsert_config_emulator(self, new_entry: EmulatorEntry) -> None:
        """Insert or update an emulator entry in the config."""
        for idx, existing in enumerate(self._config.emulators):
            same_catalog = bool(
                new_entry.catalog_id
                and new_entry.catalog_id == existing.catalog_id
            )
            same_name = new_entry.name.lower() == existing.name.lower()
            if same_catalog or same_name:
                self._config.emulators[idx] = new_entry
                return
        self._config.emulators.append(new_entry)

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
            if hasattr(self, "_overlay_spinner") and self._overlay_spinner:
                self._overlay_spinner._timer.stop()
                self._overlay_spinner = None
            self._overlay_container = None
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None
            # Play startup chime, then start ambient audio after it finishes
            from meridian.core.audio_manager import AudioManager
            duration_ms = AudioManager.instance().play_startup()
            delay = max(duration_ms, 500)  # at least 500 ms
            QTimer.singleShot(delay, self._start_ambient_after_chime)

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
        # During the first boot the ambient engine is started later by
        # _start_ambient_after_chime (after the startup sound finishes).
        if getattr(self, "_ambient_ready", False):
            self._apply_ambient_audio()

    def _start_ambient_after_chime(self) -> None:
        """Called once after the startup chime to kick off ambient audio."""
        self._ambient_ready = True
        self._apply_ambient_audio()

    def _apply_ambient_audio(self) -> None:
        """Start or stop ambient audio based on the current config."""
        from meridian.core.ambient_audio import AmbientAudioEngine
        if not hasattr(self, "_ambient_engine"):
            self._ambient_engine = AmbientAudioEngine()
        if self._config.ambient_audio_enabled:
            if self._ambient_engine.is_playing:
                self._ambient_engine.set_volume(self._config.ambient_audio_volume)
            else:
                self._ambient_engine.start(volume=self._config.ambient_audio_volume)
        else:
            self._ambient_engine.stop()

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
        icon_sz = getattr(self._config, "icon_size", 48)
        self._games_list.setIconSize(QSize(icon_sz, icon_sz))

        content_layout.addWidget(empty, 1)
        content_layout.addWidget(self._games_list, 1)
        root.addWidget(content, 1)

        # -- Vignette fade above footer --------------------------------
        vignette = QWidget()
        vignette.setFixedHeight(28)
        vignette.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        def _paint_vignette(event, w=vignette):
            p = QPainter(w)
            grad = QLinearGradient(0, 0, 0, w.height())
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(1.0, QColor(0, 0, 0, 120))
            p.fillRect(w.rect(), grad)
            p.end()

        vignette.paintEvent = _paint_vignette
        root.addWidget(vignette)

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
        self._system_logo_member_cache: dict[str, str | None] = {}
        self._system_logo_archive_ready: set[str] = set()
        self._view_mode = "list"
        _sort_map = {"Title": "title", "Platform": "platform", "Added": "added", "Played": "played"}
        self._sort_mode = _sort_map.get(getattr(self._config, "sort_default", "Title"), "title")
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

        # Rebuild the game list so row widgets pick up new theme colours
        # and density-scaled sizes.
        if self._games:
            self._refresh_games_view()

        # Re-apply audio settings — only reinitialise the mixer if the
        # channel mode actually changed, so ambient audio is not interrupted.
        from meridian.core.audio_manager import AudioManager
        amgr = AudioManager.instance()
        new_mono = config.audio_channel_mode == "Mono"
        if amgr._mono != new_mono:
            amgr.init_mixer(
                volume=config.audio_volume,
                mono=new_mono,
                mute=config.audio_mute,
            )
            # Mixer reinit killed ambient — restart if it was playing.
            if getattr(self, "_ambient_ready", False):
                self._apply_ambient_audio()
        else:
            amgr.set_volume(config.audio_volume)
            amgr.set_mute(config.audio_mute)
            # Apply ambient volume/enabled changes without a full restart.
            if getattr(self, "_ambient_ready", False):
                self._apply_ambient_audio()

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
            _msgbox.warning(
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
                _msgbox.warning(
                    self,
                    "Launch Failed",
                    "Configured emulator executable was not found.\n\n"
                    f"Configured path:\n{emulator.path}",
                )
                return

        # Early BIOS check — warn BEFORE any auto-configuration or setup
        early_missing = self._check_required_bios(game.system_id)
        if early_missing:
            bios_list = "\n".join(f"  - {name}" for name in early_missing)
            _msgbox.warning(
                self,
                "Missing Required BIOS",
                f"This system requires BIOS files that are not configured.\n\n"
                f"{bios_list}\n\n"
                "Configure them in Settings > Emulators > Configuration > BIOS Files.",
            )
            return

        # Auto-configure the emulator (BIOS, ROM paths, input, etc.)
        auto_configure_emulator(
            emulator, game.path, game.system_id, exe_path, self._config,
        )

        missing_bios = self._apply_bios_for_launch(emulator, game, exe_path)
        if missing_bios:
            _msgbox.warning(
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
            _msgbox.warning(
                self,
                "Launch Failed",
                "Unable to build launch command.\n"
                f"{hint}",
            )
            return

        # Steam Input conflict advisory (one-time)
        if not getattr(self._config, "steam_input_warning_shown", False):
            try:
                import psutil
                steam_running = any(
                    "steam" in (p.name() or "").lower()
                    for p in psutil.process_iter(["name"])
                )
                if steam_running:
                    _msgbox.information(
                        self,
                        "Steam Input Advisory",
                        "Steam is running.  Its Steam Input layer can intercept "
                        "controller events before they reach emulators.\n\n"
                        "If you experience double-input or no input, go to\n"
                        "Steam → Settings → Controller → Desktop Configuration\n"
                        "and disable Steam Input for non-Steam applications, or\n"
                        "close Steam before launching games through Meridian.",
                    )
                    self._config.steam_input_warning_shown = True
                    self._config.save()
            except Exception:
                pass

        # Release controller handles so the emulator can receive input.
        # Meridian's SDL2 raw-input registration on Windows can starve the
        # emulator's own SDL2/DirectInput layer of events.
        from meridian.core.input_manager import InputManager
        InputManager.instance().pause()

        # Pause ambient audio while emulator is running
        if hasattr(self, "_ambient_engine") and self._ambient_engine.is_playing:
            self._ambient_engine.stop()

        from meridian.core.emulator_setup import build_emulator_env
        _emu_env = build_emulator_env(self._config)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(exe_path.parent),
                env=_emu_env,
            )
            time.sleep(0.35)
            rc = proc.poll()
            if rc is not None:
                InputManager.instance().resume()
                _msgbox.warning(
                    self,
                    "Launch Failed",
                    "Emulator process exited immediately.\n\n"
                    f"Exit code: {rc}\n\n"
                    f"Command:\n{' '.join(cmd)}",
                )
                return

            if getattr(emulator, "close_meridian_on_launch", False):
                QApplication.instance().quit()
                return

            self._start_emulator_monitor(proc)
        except Exception as exc:
            InputManager.instance().resume()
            _msgbox.warning(
                self,
                "Launch Failed",
                "Failed to start emulator process.\n\n"
                f"{exc}\n\n"
                f"Command:\n{' '.join(cmd)}",
            )

    def _start_emulator_monitor(self, proc: subprocess.Popen) -> None:
        """Watch *proc* in a background thread; resume input when it exits."""
        import threading

        def _wait():
            try:
                proc.wait()
            except Exception:
                pass
            from PySide6.QtCore import QMetaObject, Qt
            try:
                QMetaObject.invokeMethod(
                    self, "_on_emulator_exited", Qt.QueuedConnection,
                )
            except Exception:
                pass

        t = threading.Thread(target=_wait, daemon=True)
        t.start()

    @Slot()
    def _on_emulator_exited(self) -> None:
        """Slot called on the main thread when the emulator process exits."""
        from meridian.core.input_manager import InputManager
        InputManager.instance().resume()
        # Resume ambient audio if enabled
        self._apply_ambient_audio()

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
                cmd = [str(exe_path), "-L", core_override, rom_path]
                self._apply_per_emulator_flags(cmd, emulator, exe_path)
                return cmd

        rendered = (
            args_template
            .replace("{rom}", rom_path)
            .replace("{core}", core_override)
        )
        rendered = rendered.strip()
        if "{core}" in args_template and not core_override:
            return []
        if not rendered:
            cmd = [str(exe_path), rom_path]
        else:
            try:
                parsed = shlex.split(rendered, posix=True)
            except Exception:
                parsed = [rom_path]
            cmd = [str(exe_path)] + parsed
        self._apply_per_emulator_flags(cmd, emulator, exe_path)
        return cmd

    def _apply_per_emulator_flags(self, cmd: list[str], emulator, exe_path: Path) -> None:
        """Inject per-emulator launch flags (fullscreen, resolution)."""
        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        emu_id = (catalog.id if catalog else emulator.display_name()).lower()
        is_retroarch = "retroarch" in emu_id or emulator.provider == "retroarch_core"

        if getattr(emulator, "fullscreen_on_launch", False):
            if is_retroarch:
                cmd.insert(1, "--fullscreen")
            elif "pcsx2" in emu_id:
                cmd.insert(1, "-fullscreen")
            elif "duckstation" in emu_id:
                cmd.insert(1, "-fullscreen")
            elif "dolphin" in emu_id:
                cmd.insert(1, "--config=Graphics.Settings.Fullscreen=True")
            elif "rpcs3" in emu_id:
                cmd.insert(1, "--fullscreen")
            else:
                cmd.insert(1, "--fullscreen")

    def _effective_args_template(self, emulator) -> str:
        args_template = (emulator.args or "").strip()
        if not args_template:
            args_template = '"{rom}"'

        name = emulator.display_name().lower()
        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        if catalog:
            name = catalog.id.lower()

        # CLI overrides so standalone emulators launch the game directly
        # without showing their own setup / game-list UI first.
        if args_template == '"{rom}"':
            _DIRECT_LAUNCH: dict[str, str] = {
                "retroarch":  '-L "{core}" "{rom}"',
                "cemu":       '-g "{rom}"',
                "pcsx2":      '-batch "{rom}"',
                "rpcs3":      '--no-gui "{rom}"',
                "xemu":       '-dvd_path "{rom}"',
                "xenia":      '"{rom}"',
                "dolphin":    '-b -e "{rom}"',
                "melonds":    '"{rom}"',
                "desmume":    '"{rom}"',
                "azahar":     '"{rom}"',
                "citra":      '"{rom}"',
                "ryubing":    '"{rom}"',
                "eden":       '"{rom}"',
                "vita3k":     '-r "{rom}"',
            }
            override = _DIRECT_LAUNCH.get(name)
            if override:
                return override

        # PCSX2 v2 (pcsx2-qt) does not support --nogui; strip it if present.
        if name in {"pcsx2"} and "--nogui" in args_template:
            args_template = args_template.replace("--nogui", "").strip()

        return args_template

    def _try_auto_install_emulator(self, emulator) -> Path | None:
        """Offer to download and install an emulator whose executable is missing."""
        catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
        if not catalog or catalog.install_strategy == "manual":
            return None
        if not catalog.windows_supported:
            return None

        if catalog.install_strategy == "retroarch_core":
            label = f"{catalog.name} (RetroArch core)"
        else:
            label = catalog.name

        reply = _msgbox.question(
            self,
            "Emulator Not Found",
            f"{label} is not installed at the configured path.\n\n"
            "Would you like to download and install it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return None

        progress = QProgressDialog(
            f"Downloading and installing {label}\u2026\n"
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
            emulator.system_overrides = result.entry.system_overrides
            if not emulator.args or emulator.args.strip() == '"{rom}"':
                emulator.args = result.entry.args
            self._config.save()
            exe = Path(result.entry.path)
            if exe.exists():
                return exe

        if result and not result.ok:
            _msgbox.warning(
                self,
                "Installation Failed",
                f"Could not install {label}.\n\n{result.message}",
            )
        return None

    def _try_auto_download_core(self, emulator, system_id: str) -> str:
        """Attempt to auto-download a RetroArch core for *system_id*."""
        candidates = _RETROARCH_CORE_CANDIDATES.get(system_id, [])
        if not candidates:
            return ""

        cores_dir = _ROOT / "emulators" / "cores"
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

        _msgbox.warning(
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

    def _check_required_bios(self, system_id: str) -> list[str]:
        """Return human-readable names of missing required BIOS files for a system.

        This is a fast config-only check that runs before any auto-configuration.
        """
        from meridian.ui.settings_dialog import _BIOS_REQUIREMENTS

        bios_ids = _SYSTEM_BIOS_IDS.get(system_id, [])
        if not bios_ids:
            return []
        bios_cfg = dict(getattr(self._config, "bios_files", {}) or {})
        missing: list[str] = []
        for bios_id in bios_ids:
            if bios_id not in _REQUIRED_BIOS_IDS:
                continue
            src_raw = str(bios_cfg.get(bios_id, "")).strip()
            if not src_raw or not Path(src_raw).exists():
                display_name = bios_id
                for entry in _BIOS_REQUIREMENTS:
                    if str(entry.get("id")) == bios_id:
                        display_name = str(entry.get("name", bios_id))
                        break
                missing.append(display_name)
        return missing

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

        # Cores live under emulators/cores/ (primary) and optionally
        # under <install_dir>/cores/ (legacy / RetroArch bundled cores).
        search_dirs: list[Path] = []
        shared_cores = _ROOT / "emulators" / "cores"
        if shared_cores.exists():
            search_dirs.append(shared_cores)
        if install_dir:
            legacy = install_dir / "cores"
            if legacy.exists() and legacy != shared_cores:
                search_dirs.append(legacy)

        if core_name:
            core_path = Path(core_name)
            if core_path.exists():
                return str(core_path)
            for d in search_dirs:
                candidate = d / core_name
                if candidate.exists():
                    return str(candidate)

        candidate_names: list[str] = []
        if core_name:
            candidate_names.append(core_name)
        candidate_names.extend(_RETROARCH_CORE_CANDIDATES.get(system_id, []))

        for cores_dir in search_dirs:
            for name in candidate_names:
                candidate = cores_dir / name
                if candidate.exists():
                    return str(candidate)

            by_lower = {p.name.lower(): p for p in cores_dir.glob("*_libretro.dll")}
            for name in candidate_names:
                found = by_lower.get(name.lower())
                if found:
                    return str(found)

        # Last resort: if exactly one core exists across all dirs, use it.
        for cores_dir in search_dirs:
            all_cores = sorted(cores_dir.glob("*_libretro.dll"))
            if len(all_cores) == 1:
                return str(all_cores[0])

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

    def open_multiplayer_settings(self) -> None:
        """Open Settings directly to Networking > Multiplayer."""
        mb = self.menuBar()
        fn = getattr(mb, "_open_settings_dialog", None)
        if callable(fn):
            fn("Networking", "Multiplayer")

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
            _msgbox.information(
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
            _msgbox.information(self, "Scrape Metadata", "No games available to scrape.")
            return
        source_name = "SteamGridDB"
        self._config.scraper_source = source_name
        source = SCRAPER_SOURCE_MAP.get(source_name)
        if not source:
            _msgbox.warning(self, "Scrape Metadata", f"Unknown scraper source: {source_name}")
            return

        creds = dict(self._config.scraper_credentials.get(source_name, {}))
        missing = [
            key for key, _label, _placeholder, _secret in source.auth_fields
            if not str(creds.get(key, "")).strip()
        ]
        if missing:
            _msgbox.warning(
                self,
                "Scrape Metadata",
                f"{source_name} requires credentials before scraping.\n"
                f"Missing fields: {', '.join(missing)}",
            )
            return

        if getattr(self, "_scrape_thread", None) and self._scrape_thread.isRunning():
            _msgbox.information(self, "Scrape Metadata", "A scrape is already in progress.")
            return

        self._scrape_progress = QProgressDialog(
            f"Scraping metadata via {source_name}...", "Cancel", 0, len(games), self,
        )
        self._scrape_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._scrape_progress.setMinimumDuration(0)
        self._scrape_progress.show()
        self._scrape_scope = scope
        self._scrape_source_name = source_name

        existing_icons = dict(self._custom_icons)
        existing_titles = dict(self._custom_titles)
        allow_overwrite = bool(getattr(self._config, "scraper_overwrite", False))

        def _do_scrape(report_progress):
            ok_count = 0
            fail_count = 0
            last_error = ""
            scraped_meta: dict[str, dict] = {}
            scraped_titles: dict[str, str] = {}
            scraped_icons: dict[str, str] = {}
            for idx, game in enumerate(games, start=1):
                report_progress(idx - 1, f"Scraping {idx}/{len(games)}: {game.title}")
                try:
                    metadata = self._scrape_game_metadata(source_name, creds, game)
                    if metadata:
                        scraped_meta[str(game.path)] = metadata
                        scraped_title = str(metadata.get("title", "")).strip()
                        if scraped_title and (allow_overwrite or str(game.path) not in existing_titles):
                            scraped_titles[str(game.path)] = scraped_title
                        art_url = metadata.get("artwork_url", "")
                        if art_url and (allow_overwrite or str(game.path) not in existing_icons):
                            local = self._download_artwork(art_url, game)
                            if local:
                                scraped_icons[str(game.path)] = local
                        ok_count += 1
                    else:
                        fail_count += 1
                except Exception as exc:
                    fail_count += 1
                    last_error = str(exc)
            return {
                "ok": ok_count, "fail": fail_count,
                "last_error": last_error,
                "meta": scraped_meta,
                "titles": scraped_titles,
                "icons": scraped_icons,
            }

        self._scrape_thread = _WorkerThread(_do_scrape, parent=self)
        self._scrape_thread.progress.connect(self._on_scrape_progress)
        self._scrape_thread.result.connect(self._on_scrape_finished)
        self._scrape_thread.start()

    @Slot(int, str)
    def _on_scrape_progress(self, value: int, label: str):
        if hasattr(self, "_scrape_progress") and self._scrape_progress:
            self._scrape_progress.setValue(value)
            self._scrape_progress.setLabelText(label)

    @Slot(object)
    def _on_scrape_finished(self, result):
        if hasattr(self, "_scrape_progress") and self._scrape_progress:
            self._scrape_progress.close()
            self._scrape_progress = None
        if not isinstance(result, dict):
            return
        self._scraped_metadata.update(result.get("meta", {}))
        self._custom_titles.update(result.get("titles", {}))
        self._custom_icons.update(result.get("icons", {}))
        self._refresh_games_view()

        ok = result.get("ok", 0)
        fail = result.get("fail", 0)
        last_error = result.get("last_error", "")
        source = getattr(self, "_scrape_source_name", "")
        scope = getattr(self, "_scrape_scope", "")
        message = (
            f"Source: {source}\n"
            f"Scope: {scope}\n"
            f"Scraped successfully: {ok}\n"
            f"Failed: {fail}"
        )
        if last_error:
            message += f"\n\nLast error:\n{last_error}"
        _msgbox.information(self, "Scrape Metadata", message)

    def _scrape_game_metadata(self, source_name: str, creds: dict, game: _ScannedGame) -> dict:
        query = self._scrape_query_for_game(game)
        return self._scrape_steamgriddb(query, creds)

    def _scrape_query_for_game(self, game: _ScannedGame) -> str:
        raw = self._display_title(game) or game.title
        cleaned = re.sub(r"\[[^\]]+\]", " ", raw)
        cleaned = re.sub(r"\([^)]+\)", " ", cleaned)
        cleaned = re.sub(r"[_\.]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or game.title

    _HTTP_UA = {"User-Agent": "Meridian/1.0 (https://github.com/meridian-app)"}

    def _http_get_json(self, url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> dict:
        merged = {**self._HTTP_UA, **(headers or {})}
        req = urllib.request.Request(url, headers=merged, method="GET")
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
        merged = {**self._HTTP_UA, **(headers or {})}
        req = urllib.request.Request(url, data=encoded, headers=merged, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as res:
            payload = res.read().decode("utf-8", errors="replace")
        obj = json.loads(payload)
        if isinstance(obj, dict):
            return obj
        return {"data": obj}

    def _http_get_text(self, url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> str:
        merged = {**self._HTTP_UA, **(headers or {})}
        req = urllib.request.Request(url, headers=merged, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read().decode("utf-8", errors="replace")

    def _scrape_screenscraper(self, query: str, creds: dict, hashes: dict | None = None) -> dict:
        username = str(creds.get("username", "")).strip()
        password = str(creds.get("password", "")).strip()
        softname = "Meridian"

        base = "https://api.screenscraper.fr/api2/jeuInfos.php"
        # Build candidate parameter sets.
        # Hash-based lookup is most accurate; title-based is the fallback.
        candidates: list[dict] = []
        if hashes and hashes.get("crc32"):
            hash_params: dict = {"crc": hashes["crc32"]}
            if hashes.get("md5"):
                hash_params["md5"] = hashes["md5"]
            candidates.append(hash_params)
        # Name-based fallbacks
        candidates += [
            {"romnom": f"{query}.zip"},
            {"romnom": query},
            {"recherche": query},
        ]
        for extra in candidates:
            params = {
                "output": "json",
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

            # The real game data lives at response.jeu, NOT at response itself
            response = data.get("response") or {}
            game = response.get("jeu") or data.get("jeu") or {}
            if not isinstance(game, dict) or not game:
                continue

            # Title: noms is a list of {region, text}; nom may also be a list
            title = ""
            noms = game.get("noms") or game.get("nom") or []
            if isinstance(noms, list):
                for region_pref in ("wor", "us", "eu", "jp", "ss"):
                    for n in noms:
                        if isinstance(n, dict) and n.get("region") == region_pref:
                            title = str(n.get("text", "")).strip()
                            if title:
                                break
                    if title:
                        break
                if not title and noms:
                    first = noms[0]
                    title = str(first.get("text", "") if isinstance(first, dict) else first).strip()
            elif isinstance(noms, dict):
                title = str(noms.get("text") or noms.get("val") or "").strip()
            else:
                title = str(noms or "").strip()

            if not title:
                title = str(game.get("nom") or "").strip()
            if not title:
                continue

            # Description: synopsis is a list of {langue, text}
            desc = ""
            synopsis = game.get("synopsis") or []
            if isinstance(synopsis, list):
                for lang_pref in ("en", ""):
                    for s in synopsis:
                        if isinstance(s, dict) and s.get("langue", "") in (lang_pref, ""):
                            desc = str(s.get("text", "")).strip()
                            if desc:
                                break
                    if desc:
                        break
            elif isinstance(synopsis, dict):
                desc = str(synopsis.get("text") or synopsis.get("synopsis") or "").strip()
            elif isinstance(synopsis, str):
                desc = synopsis.strip()

            art_url = self._extract_screenscraper_art(game)
            return {
                "title": title,
                "description": desc,
                "source": "ScreenScraper",
                "raw": game,
                "artwork_url": art_url,
            }
        return {}

    def _scrape_thegamesdb(self, query: str, creds: dict) -> dict:
        api_key = str(creds.get("api_key", "")).strip()
        params = urllib.parse.urlencode({
            "apikey": api_key,
            "name": query,
            "fields": "overview",
            "include": "boxart",
        })
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
        art_url = ""
        boxart = (data.get("include") or {}).get("boxart") or {}
        base_url = str((boxart.get("base_url") or {}).get("original", "")).strip()
        game_id = str(g0.get("id", ""))
        art_data = (boxart.get("data") or {}).get(game_id) or []
        if not isinstance(art_data, list):
            art_data = [art_data] if art_data else []
        for entry in art_data:
            if isinstance(entry, dict) and str(entry.get("side", "")).lower() == "front":
                art_url = base_url + str(entry.get("filename", ""))
                break
        if not art_url and art_data:
            entry = art_data[0]
            if isinstance(entry, dict):
                art_url = base_url + str(entry.get("filename", ""))
        return {
            "title": title,
            "description": str(overview or "").strip(),
            "source": "TheGamesDB",
            "raw": g0,
            "artwork_url": art_url,
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
            "fields name,summary,first_release_date,cover.url; "
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
        art_url = ""
        cover = g0.get("cover")
        if isinstance(cover, dict):
            cover_url = str(cover.get("url", "")).strip()
            if cover_url:
                art_url = cover_url.replace("t_thumb", "t_cover_big")
                if art_url.startswith("//"):
                    art_url = "https:" + art_url
        return {
            "title": str(g0.get("name") or query).strip(),
            "description": str(g0.get("summary") or "").strip(),
            "source": "IGDB",
            "raw": g0,
            "artwork_url": art_url,
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
        art_url = ""
        sample_cover = g0.get("sample_cover")
        if isinstance(sample_cover, dict):
            art_url = str(sample_cover.get("image", "")).strip()
        return {
            "title": str(g0.get("title") or query).strip(),
            "description": str(g0.get("description") or "").strip(),
            "source": "MobyGames",
            "raw": g0,
            "artwork_url": art_url,
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
        art_url = ""
        img_m = re.search(
            r'<img[^>]+class="[^"]*game-image[^"]*"[^>]+src="([^"]+)"',
            detail_page, flags=re.IGNORECASE,
        )
        if not img_m:
            img_m = re.search(
                r'<img[^>]+src="(https://[^"]*images\.launchbox-app\.com[^"]*)"',
                detail_page, flags=re.IGNORECASE,
            )
        if img_m:
            art_url = html.unescape(img_m.group(1))
        return {
            "title": title,
            "description": description,
            "source": "LaunchBox DB",
            "raw": {"url": detail_url},
            "artwork_url": art_url,
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
                    art_url = str(g0.get("screenshot") or g0.get("image") or g0.get("cover") or "").strip()
                    return {"title": title, "description": desc, "source": "OpenRetro", "raw": g0, "artwork_url": art_url}
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
            "artwork_url": "",
        }

    def _scrape_hasheous(self, query: str, game: _ScannedGame, hashes: dict | None = None) -> dict:
        """Hasheous: hash-based ROM identification service.

        Uses pre-computed hashes when available (passed from `_scrape_game_metadata`
        so we avoid reading the file twice). Falls back to reading the file if no
        hashes were provided, and ultimately falls back to a text search.
        """
        headers = {"Accept": "application/json"}

        # Prefer MD5 hash lookup — most accurate
        md5_hash = (hashes or {}).get("md5", "")
        if not md5_hash and game.path.exists():
            try:
                import hashlib as _hashlib
                h = _hashlib.md5()
                with open(game.path, "rb") as fh:
                    while True:
                        chunk = fh.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                md5_hash = h.hexdigest()
            except Exception:
                pass

        if md5_hash:
            try:
                data = self._http_get_json(
                    f"https://hasheous.org/api/v1/lookup/md5/{md5_hash}",
                    headers=headers,
                )
                if isinstance(data, dict) and data:
                    title = str(data.get("name") or data.get("title") or "").strip()
                    desc = str(data.get("description") or "").strip()
                    if title:
                        return {"title": title, "description": desc,
                                "source": "Hasheous", "raw": data, "artwork_url": ""}
            except Exception:
                pass

        # Text search fallback
        params = urllib.parse.urlencode({"q": query})
        try:
            data = self._http_get_json(
                f"https://hasheous.org/api/v1/search?{params}",
                headers=headers,
            )
            results = data.get("results") or data.get("data") or []
            if isinstance(results, list) and results:
                g0 = results[0] if isinstance(results[0], dict) else {}
                title = str(g0.get("name") or g0.get("title") or query).strip()
                return {"title": title, "description": "", "source": "Hasheous", "raw": g0, "artwork_url": ""}
        except Exception:
            pass
        return {}

    def _scrape_playmatch(self, query: str, creds: dict) -> dict:
        """PlayMatch: game metadata matching service."""
        api_key = str(creds.get("api_key", "")).strip()
        headers = {
            "User-Agent": "Meridian/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "",
        }
        params = urllib.parse.urlencode({"query": query})
        url = f"https://api.playmatch.gg/v1/games/search?{params}"
        try:
            data = self._http_get_json(url, headers=headers)
            results = data.get("results") or data.get("games") or data.get("data") or []
            if isinstance(results, list) and results:
                g0 = results[0] if isinstance(results[0], dict) else {}
                title = str(g0.get("name") or g0.get("title") or query).strip()
                desc = str(g0.get("description") or g0.get("summary") or "").strip()
                art_url = str(g0.get("cover") or g0.get("image") or g0.get("thumbnail") or "").strip()
                return {"title": title, "description": desc, "source": "PlayMatch", "raw": g0, "artwork_url": art_url}
        except Exception:
            pass
        return {}

    def _scrape_steamgriddb(self, query: str, creds: dict) -> dict:
        """SteamGridDB: artwork and game metadata from SGDB.

        Two-step: autocomplete search for game ID → grid image for that ID.
        """
        api_key = str(creds.get("api_key", "")).strip()
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        search_url = (
            "https://www.steamgriddb.com/api/v2/search/autocomplete/"
            + urllib.parse.quote(query)
        )
        try:
            data = self._http_get_json(search_url, headers=headers)
            results = data.get("data") or []
            if not (isinstance(results, list) and results):
                return {}
            g0 = results[0] if isinstance(results[0], dict) else {}
            title = str(g0.get("name") or g0.get("title") or query).strip()
            game_id = g0.get("id")
            art_url = ""

            if game_id:
                # Fetch portrait grid images (600×900) — best for box-art style
                for dim_param in ["?dimensions=600x900", "?dimensions=920x430", ""]:
                    try:
                        grid_data = self._http_get_json(
                            f"https://www.steamgriddb.com/api/v2/grids/game/{game_id}{dim_param}",
                            headers=headers,
                        )
                        grids = grid_data.get("data") or []
                        if isinstance(grids, list):
                            for g in grids:
                                if isinstance(g, dict):
                                    candidate = str(g.get("url") or g.get("thumb") or "").strip()
                                    if candidate:
                                        art_url = candidate
                                        break
                        if art_url:
                            break
                    except Exception:
                        continue

            return {
                "title": title,
                "description": "",
                "source": "SteamGridDB",
                "raw": g0,
                "artwork_url": art_url,
            }
        except Exception:
            pass
        return {}

    def _extract_screenscraper_art(self, game_data: dict) -> str:
        """Pull the best box art URL from a ScreenScraper jeu dict."""
        medias = game_data.get("medias") or game_data.get("media") or []
        if isinstance(medias, dict):
            medias = list(medias.values())
        if not isinstance(medias, list):
            return ""

        # Preferred media types in priority order
        type_priority = [
            "box-2D",        # standard front box art
            "box-2D-side",   # side
            "box-texture",   # 3D texture
            "mixrbv1",       # mixtured art v1
            "mixrbv2",       # mixtured art v2
            "sstitle",       # title screenshot
            "ss",            # in-game screenshot (last resort)
        ]
        # Prefer US/world region artwork
        region_priority = ("us", "wor", "eu", "jp", "")

        by_type: dict[str, list] = {}
        for m in medias:
            if not isinstance(m, dict):
                continue
            mtype = str(m.get("type", "")).lower()
            if mtype not in by_type:
                by_type[mtype] = []
            by_type[mtype].append(m)

        for mtype in type_priority:
            candidates = by_type.get(mtype, [])
            if not candidates:
                continue
            for region in region_priority:
                for m in candidates:
                    if region == "" or str(m.get("region", "")).lower() == region:
                        url = str(m.get("url", "")).strip()
                        if url:
                            return url
        # Absolute fallback: first media with any URL
        for m in medias:
            if isinstance(m, dict):
                url = str(m.get("url", "")).strip()
                if url:
                    return url
        return ""

    def _download_artwork(self, url: str, game) -> str:
        """Download an artwork image to the cache directory. Returns local path or ''."""
        if not url:
            return ""
        cache_dir = _ROOT / "cache" / "artwork"
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", game.title or "game")[:80]
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".webp" in url.lower():
            ext = ".webp"
        dest = cache_dir / f"{safe_name}_{hash(url) & 0xFFFFFFFF:08x}{ext}"
        if dest.exists() and dest.stat().st_size > 0:
            return str(dest)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Meridian/1.0"})
            with urllib.request.urlopen(req, timeout=15) as res:
                data = res.read()
            if len(data) > 100:
                dest.write_bytes(data)
                return str(dest)
        except Exception:
            pass
        return ""

    def clear_metadata_cache(self) -> None:
        cache_dir = _ROOT / "cache" / "metadata"
        try:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._scraped_metadata.clear()
            _msgbox.information(
                self,
                "Metadata Cache",
                f"Metadata cache cleared:\n{cache_dir}",
            )
        except Exception as exc:
            _msgbox.warning(
                self,
                "Metadata Cache",
                f"Failed to clear metadata cache:\n{exc}",
            )

    def scan_rom_directories(self, interactive: bool = True) -> None:
        """Scan all configured ROM paths in a background thread."""
        if getattr(self, "_scan_thread", None) and self._scan_thread.isRunning():
            return

        configured_targets = self._configured_scan_targets()
        ext_map = {
            sid: self._extensions_for_system(sid)
            for _, sid, _ in configured_targets
        }

        def _do_scan(report_progress):
            all_games: list[_ScannedGame] = []
            seen_paths: set[str] = set()
            total = len(configured_targets)
            for idx, (root_dir, system_id, emulator_name) in enumerate(configured_targets):
                report_progress(idx, f"Scanning {root_dir.name}...")
                ext_values = ext_map.get(system_id) or set()
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
                        try:
                            mtime = float(file_path.stat().st_mtime)
                        except OSError:
                            mtime = 0.0
                        all_games.append(_ScannedGame(
                            title=file_path.stem,
                            path=file_path,
                            system_id=system_id,
                            emulator_name=emulator_name,
                            added_at=mtime,
                            hidden=hidden,
                        ))
                except OSError:
                    continue
            report_progress(total, "Sorting...")
            all_games.sort(
                key=lambda g: (
                    SYSTEM_NAMES.get(g.system_id, g.system_id).lower(),
                    g.title.lower(),
                )
            )
            return all_games

        self._scan_interactive = interactive
        self._scan_thread = _WorkerThread(_do_scan, parent=self)
        self._scan_thread.result.connect(self._on_scan_finished)
        self._scan_thread.start()

    @Slot(object)
    def _on_scan_finished(self, games):
        """Handle ROM scan results from the background worker."""
        self._games = games or []

        # Restore persisted titles/icons/favorites from last session
        self._load_library_state()

        # Honour the "verify on scan" and "auto-remove missing" settings
        if getattr(self._config, "file_verify_on_scan", False):
            before = len(self._games)
            missing = [g for g in self._games if not g.path.exists()]
            if missing and getattr(self._config, "file_auto_remove_missing", False):
                missing_paths = {str(g.path) for g in missing}
                self._games = [g for g in self._games if str(g.path) not in missing_paths]
            elif missing:
                import logging as _log
                _log.getLogger(__name__).info(
                    "Scan found %d missing ROM file(s) (auto-remove is off).",
                    len(missing),
                )

        self._refresh_games_view()
        interactive = getattr(self, "_scan_interactive", False)
        if interactive:
            if self._games:
                _msgbox.information(
                    self, "Scan Complete",
                    f"Found {len(self._games)} game(s) across configured ROM paths.",
                )
            else:
                _msgbox.information(
                    self, "Scan Complete",
                    "No ROMs were found. Configure ROM directories in Settings.",
                )

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

    def _normalize_logo_key(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def _logo_set_key(self) -> str:
        val = str(getattr(self._config, "system_logo_set", "Colorful")).strip().lower()
        if val.startswith("white"):
            return "white"
        if val.startswith("black"):
            return "black"
        return "colorful"

    def _system_logo_archive_path(self) -> Path:
        return _SYSTEM_LOGO_ARCHIVE_DIR / f"console_logos_{self._logo_set_key()}.zip"

    def _system_logo_cache_dir(self) -> Path:
        return _SYSTEM_LOGO_CACHE_BASE / self._logo_set_key()

    def _logo_source_dir_for_set(self) -> Path | None:
        """Return the most likely source directory for the selected logo set."""
        root_candidates = [
            _SYSTEM_LOGO_SOURCE_HINT,
            _ROOT / "assets" / "logos" / "source",
        ]
        root = next((p for p in root_candidates if p.exists() and p.is_dir()), None)
        if root is None:
            return None
        set_key = self._logo_set_key()
        folder_aliases = {
            "colorful": ("colorful", "colourful", "color", "colour", "full set", "normal"),
            "white": ("white", "mono_white", "mono-white"),
            "black": ("black", "mono_black", "mono-black"),
        }
        wanted = folder_aliases.get(set_key, (set_key,))
        for child in root.iterdir():
            if not child.is_dir():
                continue
            n = child.name.strip().lower()
            if any(tok in n for tok in wanted):
                return child
        # If no set-specific subfolder exists, assume root contains the chosen set.
        return root

    def _ensure_system_logo_archive(self) -> Path | None:
        """Create logo archive for the selected set once, if needed."""
        archive = self._system_logo_archive_path()
        set_key = self._logo_set_key()
        if archive.exists():
            return archive
        if set_key in self._system_logo_archive_ready:
            return archive if archive.exists() else None
        self._system_logo_archive_ready.add(set_key)

        source_dir = self._logo_source_dir_for_set()
        if source_dir is None:
            return None

        img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        files = [p for p in source_dir.rglob("*") if p.is_file() and p.suffix.lower() in img_exts]
        if not files:
            return None

        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for f in files:
                arcname = str(f.relative_to(source_dir)).replace("\\", "/")
                zf.write(f, arcname)
        return archive

    def _system_logo_aliases(self, system_id: str) -> list[str]:
        name = SYSTEM_NAMES.get(system_id, system_id)
        aliases: dict[str, list[str]] = {
            "nes": ["nintendo entertainment system", "famicom", "nes"],
            "snes": ["super nintendo", "super nintendo entertainment system", "snes", "super famicom"],
            "n64": ["nintendo 64", "n64"],
            "gc": ["gamecube", "nintendo gamecube"],
            "wii": ["nintendo wii", "wii"],
            "wiiu": ["wii u", "nintendo wii u"],
            "switch": ["nintendo switch", "switch"],
            "gb": ["game boy", "nintendo game boy"],
            "gbc": ["game boy color", "nintendo game boy color"],
            "gba": ["game boy advance", "nintendo game boy advance", "gba"],
            "nds": ["nintendo ds", "nds", "ds"],
            "3ds": ["nintendo 3ds", "3ds"],
            "genesis": ["sega genesis", "mega drive", "megadrive"],
            "segacd": ["sega cd", "mega cd"],
            "sega32x": ["32x", "sega 32x"],
            "saturn": ["sega saturn", "saturn"],
            "dreamcast": ["sega dreamcast", "dreamcast"],
            "sms": ["sega master system", "master system", "sms"],
            "gg": ["game gear", "sega game gear"],
            "ps1": ["playstation", "sony playstation", "ps1", "psx"],
            "ps2": ["playstation 2", "ps2"],
            "ps3": ["playstation 3", "ps3"],
            "psp": ["playstation portable", "psp"],
            "psvita": ["playstation vita", "ps vita", "vita"],
            "xbox": ["xbox", "microsoft xbox"],
            "xbox360": ["xbox 360", "xbox360"],
            "atari2600": ["atari 2600"],
            "atari5200": ["atari 5200"],
            "atari7800": ["atari 7800"],
            "lynx": ["atari lynx", "lynx"],
            "jaguar": ["atari jaguar", "jaguar"],
            "mame": ["mame", "arcade"],
            "neogeo": ["neo geo", "neogeo"],
            "neocd": ["neo geo cd", "neocd"],
            "tg16": ["turbografx", "turbo grafx", "pc engine"],
            "pcfx": ["pc-fx", "pcfx"],
            "c64": ["commodore 64", "c64"],
            "amiga": ["commodore amiga", "amiga"],
        }
        out = aliases.get(system_id, [])[:]
        out += [name, system_id]
        return out

    def _resolve_system_logo_member(self, system_id: str) -> str | None:
        cache_key = f"{self._logo_set_key()}::{system_id}"
        if cache_key in self._system_logo_member_cache:
            return self._system_logo_member_cache[cache_key]
        archive = self._ensure_system_logo_archive()
        if archive is None or not archive.exists():
            self._system_logo_member_cache[cache_key] = None
            return None

        try:
            with zipfile.ZipFile(archive, "r") as zf:
                members = [m for m in zf.namelist() if Path(m).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}]
        except Exception:
            self._system_logo_member_cache[cache_key] = None
            return None

        candidate_keys = [self._normalize_logo_key(a) for a in self._system_logo_aliases(system_id)]
        best_member = None
        best_score = -1
        for m in members:
            stem_key = self._normalize_logo_key(Path(m).stem)
            full_key = self._normalize_logo_key(m)
            score = 0
            for k in candidate_keys:
                if not k:
                    continue
                if stem_key == k:
                    score = max(score, 300 + len(k))
                if k in stem_key:
                    score = max(score, 200 + len(k))
                if k in full_key:
                    score = max(score, 100 + len(k))
            if score > best_score:
                best_score = score
                best_member = m

        if best_score < 120:
            best_member = None
        self._system_logo_member_cache[cache_key] = best_member
        return best_member

    def _system_logo_pixmap(self, system_id: str, max_w: int = 140, max_h: int = 22) -> QPixmap | None:
        member = self._resolve_system_logo_member(system_id)
        if not member:
            return None
        archive = self._system_logo_archive_path()
        if not archive.exists():
            return None

        cache_dir = self._system_logo_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.md5(member.encode("utf-8")).hexdigest()[:12]
        ext = Path(member).suffix.lower() or ".png"
        cached = cache_dir / f"{digest}{ext}"
        if not cached.exists():
            try:
                with zipfile.ZipFile(archive, "r") as zf:
                    data = zf.read(member)
                cached.write_bytes(data)
            except Exception:
                return None
        pm = QPixmap(str(cached))
        if pm.isNull():
            return None
        return pm.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

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

        t = active_theme()
        icon_sz = getattr(self._config, "icon_size", 48)
        self._games_list.setIconSize(QSize(icon_sz, icon_sz))
        row_h = max(icon_sz + 8, 36)
        system_style = f"color: {t.fg_secondary}; font-size: 8pt;"
        show_logos = getattr(self._config, "show_system_logos", True)
        show_ext = getattr(self._config, "show_file_extensions", False)
        for game in visible_games:
            system_name = SYSTEM_NAMES.get(game.system_id, game.system_id.upper())
            display_title = self._display_title(game)
            if show_ext and game.path.suffix:
                display_title += game.path.suffix
            prefix = ""
            if str(game.path) in self._favorite_paths:
                prefix += "★ "
            if str(game.path) in self._hidden_paths:
                prefix += "◌ "

            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 4, 12, 4)
            row_layout.setSpacing(10)

            title_label = QLabel(f"{prefix}{display_title}")
            title_label.setStyleSheet("background: transparent;")
            row_layout.addWidget(title_label, 1)

            logo_pm = self._system_logo_pixmap(game.system_id, max_w=64, max_h=14) if show_logos else None
            if logo_pm is not None:
                system_label = QLabel()
                system_label.setPixmap(logo_pm)
                system_label.setFixedWidth(70)
                system_label.setStyleSheet("background: transparent;")
                system_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row_layout.addWidget(system_label)
            else:
                system_label = QLabel(system_name)
                system_label.setFixedWidth(70)
                system_label.setStyleSheet(system_style + " background: transparent;")
                system_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                row_layout.addWidget(system_label)

            item = QListWidgetItem()
            item.setToolTip(str(game.path))
            item.setData(Qt.ItemDataRole.UserRole, str(game.path))
            item.setSizeHint(QSize(0, row_h))
            if getattr(self._config, "show_game_icons", True):
                icon_path = self._custom_icons.get(str(game.path), "")
                if icon_path:
                    item.setIcon(self._scaled_icon(icon_path))
            self._games_list.addItem(item)
            self._games_list.setItemWidget(item, row_widget)

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

    def _scaled_icon(self, icon_path: str) -> QIcon:
        """Load an icon and scale it with the configured image scaling mode."""
        mode_name = getattr(self._config, "image_scaling", "Bilinear")
        if mode_name == "Nearest":
            tf = Qt.TransformationMode.FastTransformation
        else:
            tf = Qt.TransformationMode.SmoothTransformation
        sz = getattr(self._config, "icon_size", 48)
        pm = QPixmap(icon_path)
        if not pm.isNull() and (pm.width() > sz or pm.height() > sz):
            pm = pm.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio, tf)
        return QIcon(pm)

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
            if hasattr(self, "_overlay_container") and self._overlay_container:
                self._overlay_container.setGeometry(0, 0, self.width(), self.height())
            self._overlay.raise_()

    def _position_header_overlays(self):
        """Keep the legal notice and clock positioned on the menu bar."""
        # Hide header widgets while the loading overlay is visible
        loading = getattr(self, "_overlay", None) is not None
        if hasattr(self, "_legal_notice"):
            self._legal_notice.setVisible(not loading)
        if hasattr(self, "_clock_label"):
            self._clock_label.setVisible(not loading and self._config.show_clock)
        if loading:
            return

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

    # -- Library persistence -------------------------------------------

    _LIBRARY_CACHE = _ROOT / "cache" / "library_state.json"

    def _save_library_state(self) -> None:
        """Persist custom titles, custom icons, and favorites to disk."""
        state = {
            "custom_titles": self._custom_titles,
            "custom_icons": self._custom_icons,
            "favorites": sorted(self._favorite_paths),
            "hidden": sorted(self._hidden_paths),
        }
        try:
            self._LIBRARY_CACHE.parent.mkdir(parents=True, exist_ok=True)
            self._LIBRARY_CACHE.write_text(
                json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        except Exception:
            pass

    def _load_library_state(self) -> None:
        """Restore custom titles, custom icons, and favorites from disk."""
        if not self._LIBRARY_CACHE.exists():
            return
        try:
            state = json.loads(self._LIBRARY_CACHE.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                return
            loaded_titles = state.get("custom_titles") or {}
            loaded_icons = state.get("custom_icons") or {}
            loaded_favs = state.get("favorites") or []
            loaded_hidden = state.get("hidden") or []
            if isinstance(loaded_titles, dict):
                for k, v in loaded_titles.items():
                    self._custom_titles.setdefault(k, v)
            if isinstance(loaded_icons, dict):
                for k, v in loaded_icons.items():
                    self._custom_icons.setdefault(k, v)
            if isinstance(loaded_favs, list):
                self._favorite_paths.update(str(p) for p in loaded_favs)
            if isinstance(loaded_hidden, list):
                self._hidden_paths.update(str(p) for p in loaded_hidden)
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_library_state()
        if self._config.confirm_on_exit:
            reply = _msgbox.question(
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
