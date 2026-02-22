# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Settings dialog for Meridian  (Edit > Settings).

Layout
------
Left sidebar with main categories, right panel with subcategory tabs.
Each subcategory tab contains placeholder controls that will be wired
to real functionality as the project matures.

All changes are staged in a *copy* of the Config and only written to
disk when the user clicks Save.
"""

from __future__ import annotations

import copy
import shutil
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths, Slot, QTimer
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QCheckBox, QListWidget, QListWidgetItem, QStackedWidget,
    QTabWidget, QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QSlider, QFileDialog, QDialogButtonBox, QGroupBox, QMessageBox, QProgressDialog,
    QScrollArea, QLayout, QPlainTextEdit,
)

from PySide6.QtWidgets import QApplication

from meridian.ui import dialogs as _msgbox
from meridian.core.config import (
    Config, EmulatorEntry, SystemEntry,
    KNOWN_SYSTEMS, SYSTEM_NAMES, emulators_for_system, EMULATOR_CATALOG, EmulatorCatalogEntry,
    emulator_catalog_entry,
    SCRAPER_SOURCES, SCRAPER_SOURCE_NAMES, SCRAPER_SOURCE_MAP,
    SCRAPER_CONTENT_LABELS, SCRAPER_ARTWORK_LABELS,
)
from meridian.core.emulator_install import install_emulator, emulators_root
from meridian.ui.icons import icon as lucide_icon, pixmap as lucide_pixmap
from meridian.ui.style import (
    active_theme, set_theme, set_density, build_stylesheet, THEME_NAMES, THEMES,
)

_ROOT = Path(__file__).resolve().parents[2]
_LOGO_TRANSPARENT = _ROOT / "assets" / "logo_transparent.png"


# ======================================================================
# Category / subcategory definitions
# ======================================================================

_CATEGORIES: list[tuple[str, list[str]]] = [
    ("General",        ["General", "UI", "Hotkeys", "About"]),
    ("Graphics",       ["Display", "Rendering"]),
    ("Performance",    ["System", "Cache"]),
    ("Audio",          ["Output", "Mixer"]),
    ("Input",          ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5",
                        "Player 6", "Player 7", "Player 8", "Player 9", "Player 10",
                        "Adv. Settings"]),
    ("Emulators",      ["Installed", "Browse & Download", "Configuration"]),
    ("Networking",     ["Multiplayer", "Updates"]),
    ("Tools",          ["Scraper", "RetroAchievements", "File Management", "Clock"]),
    ("Adv. Settings",  ["Debug", "Experimental"]),
]

_APP_VERSION = "0.1.0-dev"

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

_BIOS_REQUIREMENTS: list[dict[str, object]] = [
    # Nintendo
    {"id": "nes_fds_bios", "name": "Famicom Disk System BIOS", "systems": ["nes"], "required": False, "hint": "disksys.rom"},
    {"id": "gba_bios", "name": "Game Boy Advance BIOS", "systems": ["gba"], "required": True, "hint": "gba_bios.bin"},
    {"id": "nds_bios7", "name": "Nintendo DS BIOS7", "systems": ["nds"], "required": True, "hint": "bios7.bin"},
    {"id": "nds_bios9", "name": "Nintendo DS BIOS9", "systems": ["nds"], "required": True, "hint": "bios9.bin"},
    {"id": "nds_firmware", "name": "Nintendo DS Firmware", "systems": ["nds"], "required": True, "hint": "firmware.bin"},
    {"id": "dsi_bios7", "name": "Nintendo DSi BIOS7", "systems": ["nds"], "required": False, "hint": "dsi_bios7.bin"},
    {"id": "dsi_bios9", "name": "Nintendo DSi BIOS9", "systems": ["nds"], "required": False, "hint": "dsi_bios9.bin"},
    {"id": "dsi_firmware", "name": "Nintendo DSi Firmware", "systems": ["nds"], "required": False, "hint": "dsi_firmware.bin"},
    {"id": "dsi_nand", "name": "Nintendo DSi NAND", "systems": ["nds"], "required": False, "hint": "dsi_nand.bin"},
    {"id": "n64_pif", "name": "Nintendo 64 PIF ROM", "systems": ["n64"], "required": False, "hint": "pifdata.bin"},
    {"id": "gc_ipl", "name": "GameCube IPL BIOS", "systems": ["gc"], "required": False, "hint": "IPL.bin / gc-ipl.bin"},
    {"id": "wii_keys", "name": "Wii Common Keys", "systems": ["wii"], "required": False, "hint": "keys.bin"},
    {"id": "wiiu_keys", "name": "Wii U Keys", "systems": ["wiiu"], "required": True, "hint": "keys.txt"},
    {"id": "switch_prod_keys", "name": "Nintendo Switch Prod Keys", "systems": ["switch"], "required": True, "hint": "prod.keys"},
    {"id": "switch_title_keys", "name": "Nintendo Switch Title Keys", "systems": ["switch"], "required": False, "hint": "title.keys"},
    {"id": "switch_firmware", "name": "Nintendo Switch Firmware", "systems": ["switch"], "required": True, "hint": "firmware .zip archive or folder of .nca files"},
    {"id": "n3ds_aes_keys", "name": "Nintendo 3DS AES Keys", "systems": ["3ds"], "required": False, "hint": "aes_keys.txt"},
    {"id": "n3ds_seeddb", "name": "Nintendo 3DS Seed Database", "systems": ["3ds"], "required": False, "hint": "seeddb.bin"},
    {"id": "n3ds_boot9", "name": "Nintendo 3DS boot9", "systems": ["3ds"], "required": False, "hint": "boot9.bin"},
    {"id": "n3ds_boot11", "name": "Nintendo 3DS boot11", "systems": ["3ds"], "required": False, "hint": "boot11.bin"},

    # Sega
    {"id": "sega_cd_us", "name": "Sega CD BIOS (USA)", "systems": ["genesis"], "required": False, "hint": "bios_CD_U.bin"},
    {"id": "sega_cd_eu", "name": "Sega CD BIOS (Europe)", "systems": ["genesis"], "required": False, "hint": "bios_CD_E.bin"},
    {"id": "sega_cd_jp", "name": "Sega CD BIOS (Japan)", "systems": ["genesis"], "required": False, "hint": "bios_CD_J.bin"},
    {"id": "sega32x_m68k", "name": "Sega 32X BIOS (M68K)", "systems": ["genesis"], "required": False, "hint": "32X_G_BIOS.BIN"},
    {"id": "sega32x_master", "name": "Sega 32X BIOS (Master SH2)", "systems": ["genesis"], "required": False, "hint": "32X_M_BIOS.BIN"},
    {"id": "sega32x_slave", "name": "Sega 32X BIOS (Slave SH2)", "systems": ["genesis"], "required": False, "hint": "32X_S_BIOS.BIN"},
    {"id": "saturn_bios_jp", "name": "Sega Saturn BIOS (JP)", "systems": ["saturn"], "required": True, "hint": "sega_101.bin"},
    {"id": "saturn_bios_us_eu", "name": "Sega Saturn BIOS (US/EU)", "systems": ["saturn"], "required": True, "hint": "mpr-17933.bin"},
    {"id": "dc_boot", "name": "Dreamcast Boot ROM", "systems": ["dreamcast"], "required": True, "hint": "dc_boot.bin"},
    {"id": "dc_flash", "name": "Dreamcast Flash ROM", "systems": ["dreamcast"], "required": True, "hint": "dc_flash.bin"},
    {"id": "naomi_bios", "name": "Naomi BIOS", "systems": ["dreamcast", "mame"], "required": False, "hint": "naomi.zip"},
    {"id": "naomi2_bios", "name": "Naomi 2 BIOS", "systems": ["dreamcast", "mame"], "required": False, "hint": "naomi2.zip"},
    {"id": "atomiswave_bios", "name": "Atomiswave BIOS", "systems": ["dreamcast", "mame"], "required": False, "hint": "awbios.zip"},

    # Sony
    {"id": "ps1_scp1001", "name": "PlayStation BIOS (USA)", "systems": ["ps1"], "required": True, "hint": "scph1001.bin / scph5501.bin"},
    {"id": "ps1_scp5500", "name": "PlayStation BIOS (Japan)", "systems": ["ps1"], "required": False, "hint": "scph5500.bin"},
    {"id": "ps1_scp5502", "name": "PlayStation BIOS (Europe)", "systems": ["ps1"], "required": False, "hint": "scph5502.bin"},
    {"id": "ps1_scp700x", "name": "PlayStation BIOS (7xxx Series)", "systems": ["ps1"], "required": False, "hint": "scph7001.bin / scph7003.bin / scph7502.bin"},
    {"id": "ps2_main", "name": "PlayStation 2 BIOS", "systems": ["ps2"], "required": True, "hint": "SCPH-xxxxx.bin"},
    {"id": "ps2_rom1", "name": "PlayStation 2 ROM1", "systems": ["ps2"], "required": False, "hint": "rom1.bin"},
    {"id": "ps2_rom2", "name": "PlayStation 2 ROM2", "systems": ["ps2"], "required": False, "hint": "rom2.bin"},
    {"id": "ps2_erom", "name": "PlayStation 2 EROM", "systems": ["ps2"], "required": False, "hint": "erom.bin"},
    {"id": "ps2_nvm", "name": "PlayStation 2 NVM", "systems": ["ps2"], "required": False, "hint": "nvm.bin"},
    {"id": "ps3_firmware", "name": "PlayStation 3 Firmware", "systems": ["ps3"], "required": True, "hint": "PS3UPDAT.PUP"},
    {"id": "psp_font", "name": "PSP Font Assets", "systems": ["psp"], "required": False, "hint": "flash0/font/..."},
    {"id": "psp_flash0", "name": "PSP Flash0 Assets", "systems": ["psp"], "required": False, "hint": "flash0/..."},
    {"id": "psvita_firmware", "name": "PS Vita Firmware Files", "systems": ["psvita"], "required": False, "hint": "os0:/vs0: dumps"},

    # Microsoft
    {"id": "xbox_bios", "name": "Original Xbox BIOS", "systems": ["xbox"], "required": False, "hint": "Complex_4627.bin / evox.bin"},
    {"id": "xbox_eeprom", "name": "Original Xbox EEPROM", "systems": ["xbox"], "required": False, "hint": "eeprom.bin"},
    {"id": "xbox360_nand", "name": "Xbox 360 NAND", "systems": ["xbox360"], "required": False, "hint": "nanddump.bin"},
    {"id": "xbox360_keys", "name": "Xbox 360 Keys", "systems": ["xbox360"], "required": False, "hint": "keys.txt"},

    # Atari
    {"id": "atari7800_bios", "name": "Atari 7800 BIOS", "systems": ["atari7800"], "required": False, "hint": "7800 BIOS (U).rom"},
    {"id": "lynx_boot", "name": "Atari Lynx Boot ROM", "systems": ["lynx"], "required": True, "hint": "lynxboot.img"},
    {"id": "jaguar_bios", "name": "Atari Jaguar BIOS", "systems": ["jaguar"], "required": True, "hint": "jagboot.rom / j64bios.bin"},
    {"id": "jaguar_cd_bios", "name": "Atari Jaguar CD BIOS", "systems": ["jaguar"], "required": False, "hint": "jagcd.bin"},

    # NEC / Hudson
    {"id": "tg16_syscard1", "name": "TurboGrafx-16 System Card v1", "systems": ["tg16"], "required": False, "hint": "syscard1.pce"},
    {"id": "tg16_syscard2", "name": "TurboGrafx-16 System Card v2", "systems": ["tg16"], "required": False, "hint": "syscard2.pce"},
    {"id": "tg16_syscard3", "name": "TurboGrafx-16 System Card v3", "systems": ["tg16"], "required": True, "hint": "syscard3.pce"},

    # SNK
    {"id": "neogeo_zip", "name": "Neo Geo BIOS", "systems": ["neogeo", "mame"], "required": True, "hint": "neogeo.zip"},
    {"id": "ngp_bios", "name": "Neo Geo Pocket BIOS", "systems": ["ngp"], "required": False, "hint": "ngp_bios.ngp / ngpcbios.rom"},

    # Arcade
    {"id": "mame_qsound", "name": "Capcom QSound BIOS", "systems": ["mame"], "required": False, "hint": "qsound.zip"},
    {"id": "mame_pgm", "name": "PGM BIOS", "systems": ["mame"], "required": False, "hint": "pgm.zip"},
    {"id": "mame_cps3", "name": "CPS-3 BIOS", "systems": ["mame"], "required": False, "hint": "cps3.zip"},
    {"id": "mame_stvbios", "name": "ST-V BIOS", "systems": ["mame"], "required": False, "hint": "stvbios.zip"},
    {"id": "mame_hikaru", "name": "Sega Hikaru BIOS", "systems": ["mame"], "required": False, "hint": "hikaru.zip"},
    {"id": "mame_chihiro", "name": "Sega Chihiro BIOS", "systems": ["mame"], "required": False, "hint": "chihiro.zip"},
    {"id": "mame_model2", "name": "Sega Model 2 BIOS", "systems": ["mame"], "required": False, "hint": "model2.zip"},
    {"id": "mame_model3", "name": "Sega Model 3 BIOS", "systems": ["mame"], "required": False, "hint": "model3.zip"},

    # Sega CD / 32X (dedicated system IDs)
    {"id": "segacd_bios_us", "name": "Sega CD BIOS (USA)", "systems": ["segacd"], "required": True, "hint": "bios_CD_U.bin"},
    {"id": "segacd_bios_eu", "name": "Sega CD BIOS (Europe)", "systems": ["segacd"], "required": False, "hint": "bios_CD_E.bin"},
    {"id": "segacd_bios_jp", "name": "Sega CD BIOS (Japan)", "systems": ["segacd"], "required": False, "hint": "bios_CD_J.bin"},
    {"id": "sega32x_bios_m68k", "name": "Sega 32X BIOS (M68K)", "systems": ["sega32x"], "required": True, "hint": "32X_G_BIOS.BIN"},
    {"id": "sega32x_bios_msh2", "name": "Sega 32X BIOS (Master SH2)", "systems": ["sega32x"], "required": True, "hint": "32X_M_BIOS.BIN"},
    {"id": "sega32x_bios_ssh2", "name": "Sega 32X BIOS (Slave SH2)", "systems": ["sega32x"], "required": True, "hint": "32X_S_BIOS.BIN"},

    # NEC
    {"id": "pcfx_bios", "name": "PC-FX BIOS", "systems": ["pcfx"], "required": True, "hint": "pcfx.rom"},
    {"id": "pc98_bios_font", "name": "PC-98 Font ROM", "systems": ["pc98"], "required": False, "hint": "font.bmp / font.rom"},

    # SNK
    {"id": "neocd_bios", "name": "Neo Geo CD BIOS", "systems": ["neocd"], "required": True, "hint": "neocd.bin / neocdz.zip"},

    # Atari
    {"id": "atari5200_bios", "name": "Atari 5200 BIOS", "systems": ["atari5200"], "required": True, "hint": "5200.rom"},
    {"id": "atarist_tos", "name": "Atari ST TOS ROM", "systems": ["atarist"], "required": True, "hint": "tos.img"},

    # ColecoVision / Intellivision
    {"id": "coleco_bios", "name": "ColecoVision BIOS", "systems": ["coleco"], "required": True, "hint": "coleco.rom"},
    {"id": "intv_exec_bios", "name": "Intellivision Exec BIOS", "systems": ["intv"], "required": True, "hint": "exec.bin"},
    {"id": "intv_grom_bios", "name": "Intellivision GROM BIOS", "systems": ["intv"], "required": True, "hint": "grom.bin"},

    # Magnavox / Fairchild
    {"id": "odyssey2_bios", "name": "Odyssey² BIOS", "systems": ["odyssey2"], "required": True, "hint": "o2rom.bin"},
    {"id": "channelf_bios_sl1", "name": "Channel F BIOS (SL31253)", "systems": ["channelf"], "required": True, "hint": "sl31253.bin"},
    {"id": "channelf_bios_sl2", "name": "Channel F BIOS (SL31254)", "systems": ["channelf"], "required": True, "hint": "sl31254.bin"},

    # Commodore
    {"id": "c64_kernal", "name": "Commodore 64 Kernal ROM", "systems": ["c64"], "required": False, "hint": "kernal.bin"},
    {"id": "c64_basic", "name": "Commodore 64 BASIC ROM", "systems": ["c64"], "required": False, "hint": "basic.bin"},
    {"id": "c64_chargen", "name": "Commodore 64 Character ROM", "systems": ["c64"], "required": False, "hint": "chargen.bin"},
    {"id": "amiga_kick13", "name": "Amiga Kickstart 1.3 ROM", "systems": ["amiga"], "required": True, "hint": "kick31.rom / amiga-os-13.rom"},
    {"id": "amiga_kick31", "name": "Amiga Kickstart 3.1 ROM", "systems": ["amiga"], "required": False, "hint": "kick31.rom / amiga-os-31.rom"},

    # Other systems
    {"id": "3do_panafz10", "name": "3DO BIOS (FZ-10)", "systems": ["3do"], "required": True, "hint": "panafz10.bin"},
    {"id": "3do_panafz1", "name": "3DO BIOS (FZ-1)", "systems": ["3do"], "required": False, "hint": "panafz1.bin"},
    {"id": "3do_goldstar", "name": "3DO BIOS (GoldStar)", "systems": ["3do"], "required": False, "hint": "goldstar.bin"},
    {"id": "vectrex_bios", "name": "Vectrex BIOS", "systems": ["vectrex"], "required": True, "hint": "bios.bin"},
    {"id": "wswan_boot", "name": "WonderSwan Boot ROM", "systems": ["wonderswan"], "required": False, "hint": "wswanboot.bin"},
    {"id": "msx_bios", "name": "MSX BIOS", "systems": ["msx"], "required": False, "hint": "MSX.ROM"},
    {"id": "msx2_bios", "name": "MSX2 BIOS", "systems": ["msx"], "required": False, "hint": "MSX2.ROM"},
    {"id": "msx2ext_bios", "name": "MSX2 Extension BIOS", "systems": ["msx"], "required": False, "hint": "MSX2EXT.ROM"},
    {"id": "msx_disk", "name": "MSX Disk BIOS", "systems": ["msx"], "required": False, "hint": "DISK.ROM"},
    {"id": "dosbox_roms", "name": "DOSBox ROM Set", "systems": ["dos", "pc"], "required": False, "hint": "dosbox/*.rom"},
]


_SYSTEM_COMPANY_ORDER: list[str] = [
    "Nintendo",
    "Sega",
    "Sony",
    "Microsoft",
    "Atari",
    "NEC",
    "SNK",
    "Commodore",
    "Amstrad",
    "Sinclair",
    "Coleco",
    "Mattel",
    "Magnavox / Philips",
    "Fairchild",
    "MSX",
    "Arcade",
    "PC / DOS",
    "Other",
]


def _system_company(system_id: str) -> str:
    if system_id in {"nes", "snes", "n64", "gc", "wii", "wiiu", "switch",
                      "gb", "gbc", "gba", "vb", "nds", "3ds", "pokemini"}:
        return "Nintendo"
    if system_id in {"genesis", "segacd", "sega32x", "saturn", "dreamcast",
                      "sms", "gg", "sg1000"}:
        return "Sega"
    if system_id in {"ps1", "ps2", "ps3", "psp", "psvita"}:
        return "Sony"
    if system_id in {"xbox", "xbox360"}:
        return "Microsoft"
    if system_id in {"atari2600", "atari5200", "atari7800", "lynx", "jaguar", "atarist"}:
        return "Atari"
    if system_id in {"tg16", "pcfx", "pc98"}:
        return "NEC"
    if system_id in {"ngp", "neogeo", "neocd"}:
        return "SNK"
    if system_id in {"mame"}:
        return "Arcade"
    if system_id in {"dos", "pc"}:
        return "PC / DOS"
    if system_id in {"c64", "amiga"}:
        return "Commodore"
    if system_id in {"cpc"}:
        return "Amstrad"
    if system_id in {"zxspec"}:
        return "Sinclair"
    if system_id in {"coleco"}:
        return "Coleco"
    if system_id in {"intv"}:
        return "Mattel"
    if system_id in {"odyssey2"}:
        return "Magnavox / Philips"
    if system_id in {"channelf"}:
        return "Fairchild"
    if system_id in {"msx"}:
        return "MSX"
    return "Other"


# ======================================================================
# Main dialog
# ======================================================================

class SettingsDialog(QDialog):
    """Modal settings dialog with sidebar + subcategory tabs."""

    MIN_W, MIN_H = 960, 600

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.resize(1020, 660)

        self._cfg = copy.deepcopy(config)
        self._original_cfg = copy.deepcopy(config)
        self._dirty = False
        self._core_update_cache: dict[str, bool] = {}
        self._building = True   # suppress _mark_dirty during construction
        self._build_ui()
        self._building = False
        self._dirty = False     # reset in case construction triggered it
        self._sidebar.setCurrentRow(0)
        self._check_core_updates_async()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # -- Sidebar ---------------------------------------------------
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("settingsSidebar")
        self._sidebar.setFixedWidth(160)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for cat_name, _ in _CATEGORIES:
            item = QListWidgetItem(cat_name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._sidebar.addItem(item)

        self._sidebar.currentRowChanged.connect(self._on_category_changed)
        body.addWidget(self._sidebar)

        # -- Right panel (stacked pages) -------------------------------
        self._pages = QStackedWidget()
        self._pages.setObjectName("settingsPages")

        self._page_builders = {
            "General":       self._page_general,
            "Graphics":      self._page_graphics,
            "Performance":   self._page_performance,
            "Audio":         self._page_audio,
            "Input":         self._page_input,
            "Emulators":     self._page_emulators,
            "Networking":    self._page_networking,
            "Tools":         self._page_tools,
            "Adv. Settings": self._page_advanced,
        }

        # Pages are built lazily on first visit — only empty shells now.
        self._page_shells: list[QWidget] = []
        for _ in _CATEGORIES:
            shell = QWidget()
            shell_layout = QVBoxLayout(shell)
            shell_layout.setContentsMargins(0, 0, 0, 0)
            shell_layout.setSpacing(0)
            self._pages.addWidget(shell)
            self._page_shells.append(shell)

        body.addWidget(self._pages, 1)
        root.addLayout(body, 1)

        # -- Bottom button bar -----------------------------------------
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(12, 8, 12, 10)
        btn_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("cancelButton")
        btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancel)

        btn_bar.addSpacing(6)

        self._btn_save = QPushButton("Save")
        self._btn_save.setObjectName("primaryButton")
        self._btn_save.setEnabled(False)
        self._btn_save.setCursor(Qt.CursorShape.ArrowCursor)
        self._btn_save.clicked.connect(self._on_save)
        btn_bar.addWidget(self._btn_save)

        root.addLayout(btn_bar)

    def _make_page(self, cat_name: str, sub_tabs: list[str]) -> QWidget:
        """Build one right-side page with subcategory tabs.

        Individual sub-tabs are constructed lazily the first time they are
        selected, so opening a category with many tabs (e.g. Input with 10
        player tabs) only pays the cost for the first visible tab.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setObjectName("subTabs")
        builder_fn = self._page_builders.get(cat_name)

        # Add lightweight shells — real content is built on first visit.
        shells: list[QWidget] = []
        for sub_name in sub_tabs:
            shell = QWidget()
            sl = QVBoxLayout(shell)
            sl.setContentsMargins(0, 0, 0, 0)
            tabs.addTab(shell, sub_name)
            shells.append(shell)

        def _on_sub_tab(index: int) -> None:
            shell = shells[index]
            if shell.layout().count() == 0:
                was = self._building
                self._building = True
                content = (
                    builder_fn(sub_tabs[index])
                    if builder_fn
                    else _placeholder(sub_tabs[index])
                )
                shell.layout().addWidget(self._wrap_subtab_content(content))
                self._building = was

        tabs.currentChanged.connect(_on_sub_tab)
        _on_sub_tab(0)          # build the first sub-tab immediately

        layout.addWidget(tabs)
        return page

    def _wrap_subtab_content(self, content: QWidget) -> QWidget:
        """Wrap tab content in a scroll area so larger pages never collapse."""
        if isinstance(content, QScrollArea):
            return content
        if content.layout() is not None:
            content.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    # ------------------------------------------------------------------
    # Sidebar slot
    # ------------------------------------------------------------------

    def _on_category_changed(self, index: int):
        shell = self._page_shells[index]
        if shell.layout().count() == 0:
            # First visit — build the real content now.
            was_building = self._building
            self._building = True
            cat_name, sub_tabs = _CATEGORIES[index]
            page = self._make_page(cat_name, sub_tabs)
            shell.layout().addWidget(page)
            self._building = was_building
        self._pages.setCurrentIndex(index)

    def navigate_to(self, category_name: str, sub_tab: str | None = None) -> None:
        """Jump to a specific settings category/sub-tab."""
        cat_index = next(
            (idx for idx, (name, _subs) in enumerate(_CATEGORIES) if name == category_name),
            -1,
        )
        if cat_index < 0:
            return
        self._sidebar.setCurrentRow(cat_index)

        if not sub_tab:
            return
        shell = self._page_shells[cat_index]
        if shell.layout().count() == 0:
            return
        page = shell.layout().itemAt(0).widget()
        if page is None:
            return
        tabs = page.findChild(QTabWidget, "subTabs")
        if tabs is None:
            return
        for idx in range(tabs.count()):
            if tabs.tabText(idx) == sub_tab:
                tabs.setCurrentIndex(idx)
                return

    # ------------------------------------------------------------------
    # Page builders — each returns content widget for a subcategory tab
    # ------------------------------------------------------------------

    # -- General -------------------------------------------------------

    def _page_general(self, sub: str) -> QWidget:
        if sub == "General":
            return self._general_general()
        if sub == "UI":
            return self._general_ui()
        if sub == "Hotkeys":
            return self._general_hotkeys()
        if sub == "About":
            return self._general_about()
        return _placeholder(sub)

    def _general_general(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Startup")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        self._chk_maximized = QCheckBox("Start maximized")
        self._chk_maximized.setChecked(self._cfg.start_maximized)
        self._chk_maximized.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_maximized)
        self._chk_confirm_exit = QCheckBox("Confirm before exit")
        self._chk_confirm_exit.setChecked(self._cfg.confirm_on_exit)
        self._chk_confirm_exit.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_confirm_exit)
        layout.addWidget(grp)

        grp2 = QGroupBox("Behaviour")
        g2 = QVBoxLayout(grp2)
        g2.setSpacing(8)
        self._chk_confirm_stop = QCheckBox("Confirm before stopping emulation")
        self._chk_confirm_stop.setChecked(True)
        self._chk_confirm_stop.toggled.connect(self._mark_dirty)
        g2.addWidget(self._chk_confirm_stop)
        self._chk_hide_mouse = QCheckBox("Hide mouse cursor on inactivity")
        self._chk_hide_mouse.setChecked(True)
        self._chk_hide_mouse.toggled.connect(self._mark_dirty)
        g2.addWidget(self._chk_hide_mouse)
        layout.addWidget(grp2)

        layout.addStretch()
        return w

    def _general_ui(self) -> QWidget:
        from PySide6.QtWidgets import QScrollArea

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        # -- Appearance ------------------------------------------------
        grp = QGroupBox("Appearance")
        g = QFormLayout(grp)
        g.setSpacing(12)
        g.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(THEME_NAMES)
        idx = THEME_NAMES.index(self._cfg.theme) if self._cfg.theme in THEME_NAMES else 0
        self._theme_combo.setCurrentIndex(idx)
        self._theme_combo.currentTextChanged.connect(self._mark_dirty)
        g.addRow("Theme:", self._theme_combo)

        self._logo_set_combo = QComboBox()
        self._logo_set_combo.addItems(["Colorful", "White", "Black"])
        self._logo_set_combo.setCurrentText(getattr(self._cfg, "system_logo_set", "Colorful"))
        self._logo_set_combo.currentTextChanged.connect(self._mark_dirty)
        g.addRow("Console logos:", self._logo_set_combo)

        # Language (moved from General tab)
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("English")
        self._lang_combo.setEnabled(False)
        g.addRow("Language:", self._lang_combo)

        layout.addWidget(grp)

        # -- Typography ------------------------------------------------
        grp_type = QGroupBox("Typography")
        g_t = QFormLayout(grp_type)
        g_t.setSpacing(10)
        g_t.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Font — populated from assets/fonts/ subdirectories
        self._font_combo = QComboBox()
        bundled = _get_bundled_font_names()
        self._font_combo.addItems(bundled)
        if self._cfg.font_family in bundled:
            self._font_combo.setCurrentText(self._cfg.font_family)
        elif bundled:
            self._font_combo.setCurrentIndex(0)
        self._font_combo.currentTextChanged.connect(self._mark_dirty)
        g_t.addRow("Font:", self._font_combo)

        # Font size
        self._fontsize_combo = QComboBox()
        self._fontsize_combo.addItems(["Small", "Medium", "Large", "Extra Large"])
        self._fontsize_combo.setCurrentText(self._cfg.font_size_label)
        self._fontsize_combo.currentTextChanged.connect(self._mark_dirty)
        g_t.addRow("Size:", self._fontsize_combo)

        # Bold
        self._chk_bold = QCheckBox("Bold text")
        self._chk_bold.setChecked(self._cfg.bold_text)
        self._chk_bold.toggled.connect(self._mark_dirty)
        g_t.addRow("", self._chk_bold)

        layout.addWidget(grp_type)

        # -- Accessibility ---------------------------------------------
        grp_a11y = QGroupBox("Accessibility")
        g_a = QVBoxLayout(grp_a11y)
        g_a.setSpacing(10)

        self._chk_reduced = QCheckBox("Reduced motion")
        self._chk_reduced.setChecked(self._cfg.reduced_motion)
        self._chk_reduced.toggled.connect(self._mark_dirty)
        g_a.addWidget(self._chk_reduced)

        self._chk_high_contrast = QCheckBox("High contrast mode")
        self._chk_high_contrast.setChecked(self._cfg.high_contrast)
        self._chk_high_contrast.toggled.connect(self._mark_dirty)
        g_a.addWidget(self._chk_high_contrast)

        layout.addWidget(grp_a11y)

        # -- Background ------------------------------------------------
        grp_bg = QGroupBox("Background")
        g_bg = QFormLayout(grp_bg)
        g_bg.setSpacing(10)
        g_bg.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._bg_type_combo = QComboBox()
        self._bg_type_combo.addItems(["None", "Image", "Animation"])
        self._bg_type_combo.setCurrentText(self._cfg.bg_type)
        self._bg_type_combo.currentTextChanged.connect(self._on_bg_type_changed)
        g_bg.addRow("Type:", self._bg_type_combo)

        # Single detail row that swaps between Image and Animation
        self._bg_detail_label = QLabel()
        self._bg_detail_stack = QStackedWidget()

        # Page 0 — Image import
        self._bg_image_widget = QWidget()
        img_row = QHBoxLayout(self._bg_image_widget)
        img_row.setContentsMargins(0, 0, 0, 0)
        img_row.setSpacing(6)
        self._bg_image_path = QLineEdit(self._cfg.bg_image_path)
        self._bg_image_path.setPlaceholderText("No image selected")
        self._bg_image_path.setReadOnly(True)
        self._bg_image_path.textChanged.connect(self._mark_dirty)
        img_row.addWidget(self._bg_image_path, 1)
        self._bg_import_btn = QPushButton("Import...")
        self._bg_import_btn.setFixedWidth(80)
        self._bg_import_btn.clicked.connect(self._on_import_bg_image)
        img_row.addWidget(self._bg_import_btn)
        self._bg_detail_stack.addWidget(self._bg_image_widget)

        # Page 1 — Animation selector
        self._bg_anim_combo = QComboBox()
        self._bg_anim_combo.addItems([
            "Waves", "Starscape", "1998",
        ])
        if self._cfg.bg_animation:
            self._bg_anim_combo.setCurrentText(self._cfg.bg_animation)
        self._bg_anim_combo.currentTextChanged.connect(self._mark_dirty)
        self._bg_detail_stack.addWidget(self._bg_anim_combo)

        g_bg.addRow(self._bg_detail_label, self._bg_detail_stack)

        layout.addWidget(grp_bg)

        # Set initial visibility
        self._on_bg_type_changed(self._cfg.bg_type)

        # Lock font combo when 1998 theme is selected
        self._theme_combo.currentTextChanged.connect(self._on_theme_selection_changed)
        self._on_theme_selection_changed(self._theme_combo.currentText())

        # -- Game Display ----------------------------------------------
        grp_display = QGroupBox("Game Display")
        g_d = QVBoxLayout(grp_display)
        g_d.setSpacing(10)

        self._chk_show_game_icons = QCheckBox("Show game icons / box art in list")
        self._chk_show_game_icons.setChecked(self._cfg.show_game_icons)
        self._chk_show_game_icons.toggled.connect(self._mark_dirty)
        g_d.addWidget(self._chk_show_game_icons)

        self._chk_show_system_logos = QCheckBox("Show console logos alongside games")
        self._chk_show_system_logos.setChecked(self._cfg.show_system_logos)
        self._chk_show_system_logos.toggled.connect(self._mark_dirty)
        g_d.addWidget(self._chk_show_system_logos)

        self._chk_show_ext = QCheckBox("Show file extensions in game titles")
        self._chk_show_ext.setChecked(self._cfg.show_file_extensions)
        self._chk_show_ext.toggled.connect(self._mark_dirty)
        g_d.addWidget(self._chk_show_ext)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Default sort:"))
        self._combo_default_sort = QComboBox()
        self._combo_default_sort.addItems(["Title", "Platform", "Added", "Played"])
        self._combo_default_sort.setCurrentText(self._cfg.sort_default)
        self._combo_default_sort.currentTextChanged.connect(self._mark_dirty)
        sort_row.addWidget(self._combo_default_sort, 1)
        g_d.addLayout(sort_row)

        layout.addWidget(grp_display)

        layout.addStretch()

        # Wrap in scroll area so content isn't cramped
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(scroll_content)

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return outer

    def _mark_dirty(self, *_args):
        """Enable the Save button when any setting is changed."""
        if self._building:
            return
        if not self._dirty:
            self._dirty = True
            self._btn_save.setEnabled(True)

    def _on_bg_type_changed(self, bg_type: str):
        """Swap the detail row between Image / Animation / hidden."""
        show = bg_type in ("Image", "Animation")
        self._bg_detail_label.setVisible(show)
        self._bg_detail_stack.setVisible(show)
        if bg_type == "Image":
            self._bg_detail_label.setText("Image:")
            self._bg_detail_stack.setCurrentIndex(0)
        elif bg_type == "Animation":
            self._bg_detail_label.setText("Animation:")
            self._bg_detail_stack.setCurrentIndex(1)
        self._mark_dirty()

    _FONT_LOCKED_THEMES = ("1998", "Console")

    def _on_theme_selection_changed(self, theme_name: str):
        """Lock the font combo when a theme with a locked font is active."""
        is_locked = theme_name in self._FONT_LOCKED_THEMES
        self._font_combo.setEnabled(not is_locked)
        if is_locked:
            theme_font = THEMES[theme_name].font_family
            self._font_combo.setToolTip(
                f'Font is locked to "{theme_font}" by the {theme_name} theme'
            )
        else:
            self._font_combo.setToolTip("")

    def _on_import_bg_image(self):
        """Open a file dialog to select a background image."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if path:
            self._bg_image_path.setText(path)
            self._mark_dirty()

    def _general_hotkeys(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Global Hotkeys")
        g = QFormLayout(grp)
        g.setSpacing(8)
        for label, default in [
            ("Toggle Fullscreen:", "F11"),
            ("Open Settings:", "Ctrl+,"),
            ("Search:", "Ctrl+K"),
            ("Quick Launch:", "Enter"),
        ]:
            le = QLineEdit(default)
            le.setReadOnly(True)
            le.setEnabled(False)
            g.addRow(label, le)
        layout.addWidget(grp)

        layout.addStretch()
        return w

    def _general_about(self) -> QWidget:
        """About page — system specs, Meridian version, environment info."""
        import platform
        import sys

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # -- Meridian --------------------------------------------------
        grp_app = QGroupBox("Meridian")
        g_app = QFormLayout(grp_app)
        g_app.setSpacing(6)
        g_app.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        g_app.addRow("Version:", QLabel(f"<b>{_APP_VERSION}</b>"))
        g_app.addRow("License:", QLabel("AGPL-3.0-or-later"))
        g_app.addRow("Python:", QLabel(platform.python_version()))
        try:
            import PySide6
            qt_ver = PySide6.__version__
        except Exception:
            qt_ver = "Unknown"
        g_app.addRow("Qt / PySide6:", QLabel(qt_ver))
        layout.addWidget(grp_app)

        # -- System specs ----------------------------------------------
        grp_sys = QGroupBox("System")
        g_sys = QFormLayout(grp_sys)
        g_sys.setSpacing(6)
        g_sys.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        g_sys.addRow("OS:", QLabel(f"{platform.system()} {platform.release()} ({platform.machine()})"))
        g_sys.addRow("Platform:", QLabel(platform.platform()))

        try:
            import psutil
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024 ** 3)
            g_sys.addRow("RAM:", QLabel(f"{total_gb:.1f} GB"))
            g_sys.addRow("CPU:", QLabel(platform.processor() or "Unknown"))
            g_sys.addRow("CPU Cores:", QLabel(f"{psutil.cpu_count(logical=False) or '?'} physical, "
                                              f"{psutil.cpu_count(logical=True) or '?'} logical"))
        except ImportError:
            g_sys.addRow("CPU:", QLabel(platform.processor() or "Unknown"))

        layout.addWidget(grp_sys)

        # -- Paths -----------------------------------------------------
        grp_paths = QGroupBox("Paths")
        g_paths = QFormLayout(grp_paths)
        g_paths.setSpacing(6)
        g_paths.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        g_paths.addRow("Project root:", self._selectable_label(str(project_root)))
        g_paths.addRow("Config file:", self._selectable_label(str(project_root / "config.json")))
        g_paths.addRow("Cache:", self._selectable_label(str(project_root / "cache")))
        g_paths.addRow("Python:", self._selectable_label(sys.executable))
        layout.addWidget(grp_paths)

        layout.addStretch()
        return w

    @staticmethod
    def _selectable_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setWordWrap(True)
        return lbl

    # -- Graphics ------------------------------------------------------

    def _page_graphics(self, sub: str) -> QWidget:
        if sub == "Display":
            return self._graphics_display()
        if sub == "Rendering":
            return self._graphics_rendering()
        return _placeholder(sub)

    def _graphics_display(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Window")
        g = QVBoxLayout(grp)
        g.setSpacing(8)

        self._chk_remember_geom = QCheckBox("Remember window size and position")
        self._chk_remember_geom.setChecked(self._cfg.remember_window_geometry)
        self._chk_remember_geom.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_remember_geom)

        self._chk_borderless = QCheckBox("Use borderless window in fullscreen")
        self._chk_borderless.setChecked(self._cfg.borderless_fullscreen)
        self._chk_borderless.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_borderless)

        layout.addWidget(grp)

        grp_anim = QGroupBox("Animations")
        g_a = QFormLayout(grp_anim)
        g_a.setSpacing(8)
        g_a.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._combo_anim_speed = QComboBox()
        self._combo_anim_speed.addItems(["Slow", "Normal", "Fast", "Instant"])
        self._combo_anim_speed.setCurrentText(self._cfg.ui_animation_speed)
        self._combo_anim_speed.currentTextChanged.connect(self._mark_dirty)
        g_a.addRow("Animation speed:", self._combo_anim_speed)

        self._chk_smooth_scroll = QCheckBox("Smooth scrolling")
        self._chk_smooth_scroll.setChecked(self._cfg.smooth_scrolling)
        self._chk_smooth_scroll.toggled.connect(self._mark_dirty)
        g_a.addRow("", self._chk_smooth_scroll)

        self._combo_transition = QComboBox()
        self._combo_transition.addItems(["Fade", "Slide", "None"])
        self._combo_transition.setCurrentText(self._cfg.list_transition_style)
        self._combo_transition.currentTextChanged.connect(self._mark_dirty)
        g_a.addRow("List transition:", self._combo_transition)

        layout.addWidget(grp_anim)
        layout.addStretch()
        return w

    def _graphics_rendering(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Rendering")
        g = QVBoxLayout(grp)
        g.setSpacing(8)

        self._chk_vsync = QCheckBox("Enable VSync")
        self._chk_vsync.setChecked(self._cfg.vsync)
        self._chk_vsync.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_vsync)

        self._chk_gpu_ui = QCheckBox("Use GPU-accelerated UI rendering")
        self._chk_gpu_ui.setChecked(self._cfg.gpu_accelerated_ui)
        self._chk_gpu_ui.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_gpu_ui)

        hint = QLabel("Changes to VSync and GPU rendering take effect on next launch.")
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        g.addWidget(hint)

        layout.addWidget(grp)

        grp_q = QGroupBox("Quality")
        g_q = QFormLayout(grp_q)
        g_q.setSpacing(8)
        g_q.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._combo_text_render = QComboBox()
        self._combo_text_render.addItems(["Subpixel", "Greyscale", "None"])
        self._combo_text_render.setCurrentText(self._cfg.text_rendering)
        self._combo_text_render.currentTextChanged.connect(self._mark_dirty)
        g_q.addRow("Text anti-aliasing:", self._combo_text_render)

        self._combo_image_scale = QComboBox()
        self._combo_image_scale.addItems(["Nearest", "Bilinear", "Smooth"])
        self._combo_image_scale.setCurrentText(self._cfg.image_scaling)
        self._combo_image_scale.currentTextChanged.connect(self._mark_dirty)
        g_q.addRow("Image scaling:", self._combo_image_scale)

        self._combo_icon_size = QComboBox()
        for sz in [32, 48, 64, 96]:
            self._combo_icon_size.addItem(f"{sz} px", sz)
        idx = self._combo_icon_size.findData(self._cfg.icon_size)
        self._combo_icon_size.setCurrentIndex(idx if idx >= 0 else 1)
        self._combo_icon_size.currentIndexChanged.connect(self._mark_dirty)
        g_q.addRow("Game icon size:", self._combo_icon_size)

        layout.addWidget(grp_q)
        layout.addStretch()
        return w

    # -- Performance ---------------------------------------------------

    def _page_performance(self, sub: str) -> QWidget:
        if sub == "System":
            return self._perf_system()
        if sub == "Cache":
            return self._perf_cache()
        return _placeholder(sub)

    def _perf_system(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # -- CPU -------------------------------------------------------
        grp_cpu = QGroupBox("CPU")
        g_cpu = QVBoxLayout(grp_cpu)
        g_cpu.setSpacing(8)

        self._chk_limit_bg_cpu = QCheckBox("Limit background CPU usage")
        self._chk_limit_bg_cpu.setChecked(self._cfg.limit_background_cpu)
        self._chk_limit_bg_cpu.toggled.connect(self._mark_dirty)
        g_cpu.addWidget(self._chk_limit_bg_cpu)

        row_threads = QHBoxLayout()
        row_threads.addWidget(QLabel("Concurrent scan threads:"))
        self._spin_threads = QSpinBox()
        self._spin_threads.setRange(1, 16)
        self._spin_threads.setValue(self._cfg.scan_threads)
        self._spin_threads.valueChanged.connect(self._mark_dirty)
        row_threads.addWidget(self._spin_threads)
        row_threads.addStretch()
        g_cpu.addLayout(row_threads)

        row_fgfps = QHBoxLayout()
        row_fgfps.addWidget(QLabel("Foreground animation FPS:"))
        self._spin_fg_fps = QSpinBox()
        self._spin_fg_fps.setRange(15, 144)
        self._spin_fg_fps.setValue(self._cfg.foreground_fps)
        self._spin_fg_fps.setSuffix(" fps")
        self._spin_fg_fps.valueChanged.connect(self._mark_dirty)
        row_fgfps.addWidget(self._spin_fg_fps)
        row_fgfps.addStretch()
        g_cpu.addLayout(row_fgfps)

        row_bgfps = QHBoxLayout()
        row_bgfps.addWidget(QLabel("Background animation FPS:"))
        self._spin_bg_fps = QSpinBox()
        self._spin_bg_fps.setRange(5, 60)
        self._spin_bg_fps.setValue(self._cfg.background_fps)
        self._spin_bg_fps.setSuffix(" fps")
        self._spin_bg_fps.valueChanged.connect(self._mark_dirty)
        row_bgfps.addWidget(self._spin_bg_fps)
        row_bgfps.addStretch()
        g_cpu.addLayout(row_bgfps)

        layout.addWidget(grp_cpu)

        # -- GPU -------------------------------------------------------
        grp_gpu = QGroupBox("GPU")
        g_gpu = QFormLayout(grp_gpu)
        g_gpu.setSpacing(8)
        g_gpu.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._combo_gpu_backend = QComboBox()
        self._combo_gpu_backend.addItems(["Auto", "OpenGL", "Software"])
        self._combo_gpu_backend.setCurrentText(self._cfg.gpu_backend)
        self._combo_gpu_backend.currentTextChanged.connect(self._mark_dirty)
        g_gpu.addRow("Render backend:", self._combo_gpu_backend)

        hint_gpu = QLabel("Changing the render backend requires a restart.")
        hint_gpu.setObjectName("sectionLabel")
        hint_gpu.setWordWrap(True)
        g_gpu.addRow("", hint_gpu)

        layout.addWidget(grp_gpu)

        # -- Artwork loading -------------------------------------------
        grp_load = QGroupBox("Artwork Loading")
        g_load = QVBoxLayout(grp_load)
        g_load.setSpacing(8)

        self._chk_lazy_load = QCheckBox("Lazy-load artwork (load thumbnails as they scroll into view)")
        self._chk_lazy_load.setChecked(self._cfg.lazy_load_artwork)
        self._chk_lazy_load.toggled.connect(self._mark_dirty)
        g_load.addWidget(self._chk_lazy_load)

        self._chk_prefetch = QCheckBox("Pre-fetch adjacent artwork (smoother scrolling, more memory)")
        self._chk_prefetch.setChecked(self._cfg.prefetch_adjacent)
        self._chk_prefetch.toggled.connect(self._mark_dirty)
        g_load.addWidget(self._chk_prefetch)

        self._chk_preload_emu = QCheckBox("Pre-load emulator configurations at startup")
        self._chk_preload_emu.setChecked(self._cfg.preload_emulator_configs)
        self._chk_preload_emu.toggled.connect(self._mark_dirty)
        g_load.addWidget(self._chk_preload_emu)

        row_img = QHBoxLayout()
        row_img.addWidget(QLabel("Max images in memory:"))
        self._spin_max_imgs = QSpinBox()
        self._spin_max_imgs.setRange(50, 2000)
        self._spin_max_imgs.setSingleStep(50)
        self._spin_max_imgs.setValue(self._cfg.max_loaded_images)
        self._spin_max_imgs.valueChanged.connect(self._mark_dirty)
        row_img.addWidget(self._spin_max_imgs)
        row_img.addStretch()
        g_load.addLayout(row_img)

        layout.addWidget(grp_load)

        layout.addStretch()
        return w

    def _perf_cache(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Metadata Cache")
        g = QVBoxLayout(grp)
        g.setSpacing(8)

        self._chk_cache_art = QCheckBox("Cache box art thumbnails")
        self._chk_cache_art.setChecked(self._cfg.cache_box_art)
        self._chk_cache_art.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_cache_art)

        self._chk_cache_meta = QCheckBox("Cache scraped metadata locally")
        self._chk_cache_meta.setChecked(self._cfg.cache_metadata)
        self._chk_cache_meta.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_cache_meta)

        row_max = QHBoxLayout()
        row_max.addWidget(QLabel("Max cache size:"))
        self._spin_cache_mb = QSpinBox()
        self._spin_cache_mb.setRange(64, 4096)
        self._spin_cache_mb.setSingleStep(64)
        self._spin_cache_mb.setValue(self._cfg.cache_max_mb)
        self._spin_cache_mb.setSuffix(" MB")
        self._spin_cache_mb.valueChanged.connect(self._mark_dirty)
        row_max.addWidget(self._spin_cache_mb)
        row_max.addStretch()
        g.addLayout(row_max)

        btn_clear = QPushButton("Clear Cache")
        btn_clear.setFixedWidth(120)
        btn_clear.clicked.connect(self._on_clear_cache)
        g.addWidget(btn_clear)

        layout.addWidget(grp)

        # -- Thumbnails ------------------------------------------------
        grp_thumb = QGroupBox("Thumbnails")
        g_t = QFormLayout(grp_thumb)
        g_t.setSpacing(8)
        g_t.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._combo_thumb_res = QComboBox()
        self._combo_thumb_res.addItems(["Low", "Medium", "High"])
        self._combo_thumb_res.setCurrentText(self._cfg.thumbnail_resolution)
        self._combo_thumb_res.currentTextChanged.connect(self._mark_dirty)
        g_t.addRow("Thumbnail resolution:", self._combo_thumb_res)

        layout.addWidget(grp_thumb)

        layout.addStretch()
        return w

    def _on_clear_cache(self):
        _msgbox.information(
            self, "Clear Cache",
            "Cache clearing is not yet implemented.\n"
            "This will remove all cached thumbnails and metadata.",
        )

    # -- Audio ---------------------------------------------------------

    def _page_audio(self, sub: str) -> QWidget:
        if sub == "Output":
            return self._audio_output()
        if sub == "Mixer":
            return self._audio_mixer()
        return _placeholder(sub)

    def _audio_output(self) -> QWidget:
        """Output / input device selection and channel mode."""
        from meridian.core.audio_manager import AudioManager

        amgr = AudioManager.instance()
        amgr.refresh_devices()

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # -- Devices ---------------------------------------------------
        grp_dev = QGroupBox("Devices")
        g_dev = QFormLayout(grp_dev)
        g_dev.setSpacing(10)
        g_dev.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self._audio_out_combo = QComboBox()
        self._audio_out_combo.addItem("Default")
        self._audio_out_combo.addItems(amgr.output_device_names())
        saved_out = self._cfg.audio_output_device
        idx = self._audio_out_combo.findText(saved_out)
        if idx >= 0:
            self._audio_out_combo.setCurrentIndex(idx)
        self._audio_out_combo.setToolTip(
            "Audio output device used for game audio"
        )
        self._audio_out_combo.currentIndexChanged.connect(self._mark_dirty)
        g_dev.addRow("Output device:", self._audio_out_combo)

        self._audio_in_combo = QComboBox()
        self._audio_in_combo.addItem("None")
        self._audio_in_combo.addItems(amgr.input_device_names())
        saved_in = self._cfg.audio_input_device
        idx_in = self._audio_in_combo.findText(saved_in)
        if idx_in >= 0:
            self._audio_in_combo.setCurrentIndex(idx_in)
        self._audio_in_combo.setToolTip(
            "Audio input device (microphone) for voice chat"
        )
        self._audio_in_combo.currentIndexChanged.connect(self._mark_dirty)
        g_dev.addRow("Input device:", self._audio_in_combo)

        # Refresh button
        btn_refresh_audio = QPushButton(" Refresh ")
        btn_refresh_audio.setToolTip("Re-scan audio devices")

        def _on_audio_refresh():
            amgr.refresh_devices()
            for combo, items, prefix in [
                (self._audio_out_combo, amgr.output_device_names(), "Default"),
                (self._audio_in_combo, amgr.input_device_names(), "None"),
            ]:
                cur = combo.currentText()
                combo.blockSignals(True)
                combo.clear()
                combo.addItem(prefix)
                combo.addItems(items)
                i = combo.findText(cur)
                combo.setCurrentIndex(max(i, 0))
                combo.blockSignals(False)

        btn_refresh_audio.clicked.connect(_on_audio_refresh)
        g_dev.addRow("", btn_refresh_audio)

        layout.addWidget(grp_dev)

        # -- Channel mode ----------------------------------------------
        grp_ch = QGroupBox("Channel Mode")
        g_ch = QFormLayout(grp_ch)
        g_ch.setSpacing(10)
        g_ch.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self._audio_channel_combo = QComboBox()
        self._audio_channel_combo.addItems(["Stereo", "Mono"])
        ch_idx = self._audio_channel_combo.findText(self._cfg.audio_channel_mode)
        if ch_idx >= 0:
            self._audio_channel_combo.setCurrentIndex(ch_idx)
        self._audio_channel_combo.currentIndexChanged.connect(self._mark_dirty)
        g_ch.addRow("Output mode:", self._audio_channel_combo)

        layout.addWidget(grp_ch)

        layout.addStretch()
        return w

    def _audio_mixer(self) -> QWidget:
        """Volume, mute, and background behaviour."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # -- Master volume ---------------------------------------------
        grp_vol = QGroupBox("Volume")
        g_vol = QVBoxLayout(grp_vol)
        g_vol.setSpacing(10)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(8)
        vol_row.addWidget(QLabel("Master volume:"))
        self._audio_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._audio_vol_slider.setRange(0, 100)
        self._audio_vol_slider.setValue(self._cfg.audio_volume)
        self._audio_vol_slider.valueChanged.connect(self._mark_dirty)
        vol_row.addWidget(self._audio_vol_slider, 1)
        self._audio_vol_label = QLabel(f"{self._cfg.audio_volume} %")
        self._audio_vol_label.setFixedWidth(40)
        self._audio_vol_slider.valueChanged.connect(
            lambda v: self._audio_vol_label.setText(f"{v} %")
        )
        vol_row.addWidget(self._audio_vol_label)
        g_vol.addLayout(vol_row)

        self._chk_mute = QCheckBox("Mute all audio")
        self._chk_mute.setChecked(self._cfg.audio_mute)
        self._chk_mute.toggled.connect(self._mark_dirty)
        g_vol.addWidget(self._chk_mute)

        layout.addWidget(grp_vol)

        # -- Behaviour -------------------------------------------------
        grp_beh = QGroupBox("Behaviour")
        g_beh = QVBoxLayout(grp_beh)
        g_beh.setSpacing(8)

        self._chk_mute_bg = QCheckBox("Mute audio when Meridian is in the background")
        self._chk_mute_bg.setChecked(self._cfg.audio_mute_background)
        self._chk_mute_bg.toggled.connect(self._mark_dirty)
        g_beh.addWidget(self._chk_mute_bg)

        self._chk_mute_unfocused = QCheckBox(
            "Mute audio when emulator window loses focus"
        )
        self._chk_mute_unfocused.setChecked(self._cfg.audio_mute_unfocused_emu)
        self._chk_mute_unfocused.toggled.connect(self._mark_dirty)
        g_beh.addWidget(self._chk_mute_unfocused)

        layout.addWidget(grp_beh)

        # Ambient audio
        grp_ambient = QGroupBox("Ambient Audio")
        g_amb = QVBoxLayout(grp_ambient)
        g_amb.setSpacing(8)
        self._chk_ambient_enabled = QCheckBox("Enable procedural ambient background audio")
        self._chk_ambient_enabled.setChecked(self._cfg.ambient_audio_enabled)
        self._chk_ambient_enabled.toggled.connect(self._mark_dirty)
        g_amb.addWidget(self._chk_ambient_enabled)

        amb_vol_row = QHBoxLayout()
        amb_vol_row.addWidget(QLabel("Volume:"))
        self._ambient_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._ambient_vol_slider.setRange(0, 100)
        self._ambient_vol_slider.setValue(self._cfg.ambient_audio_volume)
        self._ambient_vol_slider.valueChanged.connect(self._mark_dirty)
        amb_vol_row.addWidget(self._ambient_vol_slider, 1)
        self._ambient_vol_label = QLabel(f"{self._cfg.ambient_audio_volume}%")
        self._ambient_vol_label.setFixedWidth(36)
        self._ambient_vol_slider.valueChanged.connect(
            lambda v: self._ambient_vol_label.setText(f"{v}%")
        )
        amb_vol_row.addWidget(self._ambient_vol_label)
        g_amb.addLayout(amb_vol_row)

        hint = QLabel("Generates an evolving, seamless ambient pad. No files needed.")
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        g_amb.addWidget(hint)
        layout.addWidget(grp_ambient)

        layout.addStretch()
        return w

    # -- Input ---------------------------------------------------------

    def _page_input(self, sub: str) -> QWidget:
        # Initialise the InputManager once for all player tabs.
        if not hasattr(self, "_input_mgr"):
            from meridian.core.input_manager import InputManager
            self._input_mgr = InputManager.instance()
            self._input_mgr.ensure_ready()
        if not hasattr(self, "_input_player_controls"):
            self._input_player_controls: dict[int, dict[str, object]] = {}
        if not hasattr(self, "_input_profile_edit_seq"):
            self._input_profile_edit_seq: dict[int, int] = {}
            self._input_profile_edit_counter = 0

        if sub.startswith("Player "):
            return self._input_player(int(sub.split()[1]))
        if sub == "Adv. Settings":
            return self._input_adv_settings()
        return _placeholder(sub)

    @staticmethod
    def _base_device_name(label: str) -> str:
        """Strip optional ' [#N]' suffix from a device label."""
        if label.endswith("]") and " [#" in label:
            return label.rsplit(" [#", 1)[0]
        return label

    @staticmethod
    def _controller_matches_api(controller, api_filter: str) -> bool:
        api = str(getattr(controller, "api_type", "SDL") or "SDL")
        if api_filter == "SDL":
            return api == "SDL"
        if api_filter == "XInput":
            return api == "XInput"
        if api_filter == "DirectInput":
            return api == "DirectInput"
        return True

    def _populate_input_device_combo(
        self,
        combo: QComboBox,
        mgr,
        *,
        api_filter: str = "SDL",
        saved_text: str = "Any Available",
        saved_index: int | None = None,
    ) -> None:
        """Fill an input device combo with stable index-backed entries."""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("None", None)
        combo.addItem("Keyboard + Mouse", "keyboard")
        combo.addItem("Any Available", "any")

        ctrls = [c for c in mgr.controllers() if self._controller_matches_api(c, api_filter)]
        name_counts: dict[str, int] = {}
        for c in ctrls:
            name_counts[c.name] = name_counts.get(c.name, 0) + 1
        for c in ctrls:
            label = c.name
            if name_counts.get(c.name, 0) > 1:
                label = f"{c.name} [#{c.index + 1}]"
            combo.addItem(label, c.index)

        target_idx = -1
        if isinstance(saved_index, int) and saved_index >= 0:
            target_idx = combo.findData(saved_index)
        if target_idx < 0 and saved_text:
            target_idx = combo.findText(saved_text)
        if target_idx < 0 and saved_text:
            base_saved = self._base_device_name(saved_text)
            for i in range(combo.count()):
                if self._base_device_name(combo.itemText(i)) == base_saved:
                    target_idx = i
                    break
        if target_idx < 0:
            target_idx = combo.findText("Any Available")
        combo.setCurrentIndex(target_idx if target_idx >= 0 else 0)
        combo.blockSignals(False)

    def _input_player(self, num: int) -> QWidget:
        """Build a controller-mapping tab as a vertical list of sections."""
        from PySide6.QtWidgets import QScrollArea

        saved_input = self._cfg.input_player_settings.get(str(num), {})
        saved_bindings = saved_input.get("bindings", {})
        defs = saved_bindings if saved_bindings else (_PLAYER1_BINDINGS if num == 1 else {})
        mgr = self._input_mgr

        bindings: dict[str, _BindButton] = {}

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        # Container for everything below the top bar — disabled when
        # the player is disconnected.
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)

        # -- Top bar: Connected · API · Device · Type ------------------
        top = QHBoxLayout()
        top.setSpacing(8)

        chk = QCheckBox("Connected")
        chk.setChecked(bool(saved_input.get("connected", num == 1)))

        def _has_any_binding(bind_map: dict[str, _BindButton]) -> bool:
            for btn in bind_map.values():
                val = btn.text().strip()
                if val and val != "Listening …":
                    return True
            return False

        def _note_profile_edited() -> None:
            self._input_profile_edit_counter += 1
            self._input_profile_edit_seq[num] = self._input_profile_edit_counter

        def _latest_profile_seed(exclude_num: int) -> tuple[str, dict[str, str]] | None:
            """Return (type, bindings) from the latest profile with bindings."""
            candidates: list[tuple[int, int, str, dict[str, str]]] = []

            # Prefer in-UI unsaved edits first.
            controls = getattr(self, "_input_player_controls", {})
            for pnum, widget_map in controls.items():
                if pnum == exclude_num:
                    continue
                typ = widget_map.get("type")
                bmap = widget_map.get("bindings")
                if not isinstance(typ, QComboBox) or not isinstance(bmap, dict):
                    continue
                extracted: dict[str, str] = {}
                for key, btn in bmap.items():
                    if not hasattr(btn, "text"):
                        continue
                    val = btn.text().strip()
                    if val and val != "Listening …":
                        extracted[key] = val
                if extracted:
                    seq = int(self._input_profile_edit_seq.get(int(pnum), 0))
                    candidates.append((seq, int(pnum), typ.currentText(), extracted))

            # Include persisted values as fallback.
            for pnum_str, pdata in (self._cfg.input_player_settings or {}).items():
                try:
                    pnum = int(pnum_str)
                except (TypeError, ValueError):
                    continue
                if pnum == exclude_num:
                    continue
                if any(c[1] == pnum for c in candidates):
                    continue
                if not isinstance(pdata, dict):
                    continue
                raw_bindings = pdata.get("bindings") or {}
                if not isinstance(raw_bindings, dict) or not raw_bindings:
                    continue
                extracted = {
                    str(k): str(v).strip()
                    for k, v in raw_bindings.items()
                    if str(v).strip()
                }
                if not extracted:
                    continue
                seq = int(self._input_profile_edit_seq.get(pnum, 0))
                ptype = str(pdata.get("type", "Pro Controller"))
                candidates.append((seq, pnum, ptype, extracted))

            if not candidates:
                return None

            # If any profile has an explicit edit sequence, pick latest edited.
            with_seq = [c for c in candidates if c[0] > 0]
            if with_seq:
                _, _, src_type, src_bindings = max(with_seq, key=lambda c: c[0])
                return src_type, src_bindings

            # Otherwise prefer the highest player number that has bindings.
            _, _, src_type, src_bindings = max(candidates, key=lambda c: c[1])
            return src_type, src_bindings

        def _on_connected(on: bool):
            body.setEnabled(on)
            api.setEnabled(on)
            dev.setEnabled(on)
            tcombo.setEnabled(on)
            btn_refresh.setEnabled(on)

            if on and not _has_any_binding(bindings):
                seed = _latest_profile_seed(exclude_num=num)
                if seed is not None:
                    src_type, src_bindings = seed
                    idx = tcombo.findText(src_type)
                    if idx >= 0:
                        tcombo.setCurrentIndex(idx)
                    for key, btn in bindings.items():
                        btn.set_binding(src_bindings.get(key, ""))
                    _note_profile_edited()
            self._mark_dirty()

        chk.toggled.connect(_on_connected)
        top.addWidget(chk)

        top.addWidget(QLabel("API:"))
        api = QComboBox()
        api.addItems(["XInput", "DirectInput", "SDL"])
        api.setMinimumWidth(90)
        saved_api = str(saved_input.get("api", "SDL"))
        if saved_api == "Auto":
            saved_api = "SDL"
        api.setCurrentIndex(max(api.findText(saved_api), 0))
        api.currentIndexChanged.connect(self._mark_dirty)
        top.addWidget(api)

        top.addWidget(QLabel("Device:"))
        dev = QComboBox()
        saved_device = str(saved_input.get("device", "Any Available"))
        saved_device_index = saved_input.get("device_index")
        if not isinstance(saved_device_index, int):
            saved_device_index = None
        self._populate_input_device_combo(
            dev,
            mgr,
            api_filter=api.currentText(),
            saved_text=saved_device,
            saved_index=saved_device_index,
        )
        dev.setMinimumWidth(100)
        dev.currentIndexChanged.connect(self._mark_dirty)
        top.addWidget(dev, 1)

        btn_refresh = QPushButton(" Refresh ")
        btn_refresh.setToolTip("Re-scan for controllers")

        def _on_refresh():
            mgr.refresh()
            current_text = dev.currentText()
            data = dev.currentData()
            current_index = data if isinstance(data, int) and data >= 0 else None
            self._populate_input_device_combo(
                dev,
                mgr,
                api_filter=api.currentText(),
                saved_text=current_text,
                saved_index=current_index,
            )

        btn_refresh.clicked.connect(_on_refresh)
        top.addWidget(btn_refresh)

        def _on_api_changed():
            current_text = dev.currentText()
            data = dev.currentData()
            current_index = data if isinstance(data, int) and data >= 0 else None
            self._populate_input_device_combo(
                dev,
                mgr,
                api_filter=api.currentText(),
                saved_text=current_text,
                saved_index=current_index,
            )

        api.currentIndexChanged.connect(_on_api_changed)

        top.addWidget(QLabel("Type:"))
        tcombo = QComboBox()
        tcombo.addItems([
            "Pro Controller", "Gamepad", "Xbox Controller", "DualShock",
            "DualSense", "GameCube", "N64 Controller",
            "Joy-Con (L+R)", "Joy-Con (Single)",
            "Wii Remote", "Wii Remote + Nunchuk", "Classic Controller",
            "Fight Stick", "Steering Wheel", "Custom",
        ])
        tcombo.setMinimumWidth(110)
        saved_type = str(saved_input.get("type", "Pro Controller"))
        tcombo.setCurrentIndex(max(tcombo.findText(saved_type), 0))
        tcombo.currentIndexChanged.connect(self._mark_dirty)
        top.addWidget(tcombo, 1)

        layout.addLayout(top)

        # Device getter — bind buttons use this to decide what to listen to
        def _get_device() -> str:
            return dev.currentText()

        def _get_device_index() -> int | None:
            data = dev.currentData()
            if isinstance(data, int) and data >= 0:
                return data
            return None

        # -- Dynamic binding section that rebuilds when type changes ---
        binds_container = QWidget()
        binds_layout = QVBoxLayout(binds_container)
        binds_layout.setContentsMargins(0, 0, 0, 0)
        binds_layout.setSpacing(6)

        def _rebuild_bindings():
            """Clear and rebuild the binding rows for the selected type."""
            # Preserve any existing bindings before clearing
            old_values: dict[str, str] = {}
            for key, btn in bindings.items():
                val = btn.text().strip()
                if val and val != "Listening \u2026":
                    old_values[key] = val
            bindings.clear()

            while binds_layout.count():
                item = binds_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    _clear_layout(item.layout())

            type_name = tcombo.currentText()
            sections = _CONTROLLER_LAYOUTS.get(type_name, _CONTROLLER_LAYOUTS["Pro Controller"])

            for section_title, bind_defs in sections:
                binds_layout.addWidget(_section_label(section_title))
                for key, label in bind_defs:
                    saved_val = old_values.get(key) or defs.get(key, "")
                    btn = _BindButton(
                        saved_val,
                        device_fn=_get_device,
                        device_index_fn=_get_device_index,
                    )
                    btn.binding_changed.connect(lambda _v: (_note_profile_edited(), self._mark_dirty()))
                    bindings[key] = btn
                    binds_layout.addLayout(_bind_row(label, btn))

            # Motion / Vibration / Extras (shared across all types)
            binds_layout.addWidget(_section_label("Motion, Vibration & Extras"))
            motion_val = old_values.get("motion") or defs.get("motion", "")
            motion_btn = _BindButton(
                motion_val, device_fn=_get_device, device_index_fn=_get_device_index,
            )
            motion_btn.binding_changed.connect(lambda _v: (_note_profile_edited(), self._mark_dirty()))
            bindings["motion"] = motion_btn
            binds_layout.addLayout(_bind_row("Motion", motion_btn))

            gyro_ok = any(c.has_gyro for c in mgr.controllers())
            accel_ok = any(c.has_accel for c in mgr.controllers())
            parts: list[str] = []
            if gyro_ok:
                parts.append("Gyro detected")
            if accel_ok:
                parts.append("Accelerometer detected")
            hint_text = " \u00b7 ".join(parts) if parts else "No motion sensors detected"
            sensor_hint = QLabel(hint_text)
            sensor_hint.setObjectName("sectionLabel")
            sensor_hint.setContentsMargins(8, 0, 0, 0)
            binds_layout.addWidget(sensor_hint)

            binds_layout.addLayout(_check_row("Motion controls", True))

            def _on_vibration_cfg():
                _VibrationConfigDialog(parent=self).exec()
            binds_layout.addLayout(
                _check_configure_row("Vibration", True, _on_vibration_cfg)
            )

            def _on_mouse_pan_cfg():
                _MousePanningConfigDialog(parent=self).exec()
            binds_layout.addLayout(
                _check_configure_row("Mouse panning", False, _on_mouse_pan_cfg)
            )

        tcombo.currentIndexChanged.connect(lambda _: _rebuild_bindings())
        tcombo.currentIndexChanged.connect(lambda _i: (_note_profile_edited(), self._mark_dirty()))
        _rebuild_bindings()

        bl = body_layout
        bl.addWidget(binds_container)
        bl.addStretch()

        # -- Bottom bar ------------------------------------------------
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        bottom.addStretch()

        btn_def = QPushButton(" Defaults ")

        def _on_defaults():
            target = _PLAYER1_BINDINGS if num == 1 else {}
            for key, btn in bindings.items():
                btn.set_binding(target.get(key, ""))
            _note_profile_edited()
            self._mark_dirty()

        btn_def.clicked.connect(_on_defaults)
        bottom.addWidget(btn_def)

        btn_clr = QPushButton(" Clear ")

        def _on_clear():
            for btn in bindings.values():
                btn.set_binding("")
            _note_profile_edited()
            self._mark_dirty()

        btn_clr.clicked.connect(_on_clear)
        bottom.addWidget(btn_clr)

        btn_reset = QPushButton(" Reset Profile ")

        def _on_reset_profile():
            # Reset profile-level settings and clear all mappings.
            chk.setChecked(False)

            api_idx = api.findText("SDL")
            api.setCurrentIndex(api_idx if api_idx >= 0 else 0)

            dev_idx = dev.findText("Any Available")
            dev.setCurrentIndex(dev_idx if dev_idx >= 0 else 0)

            type_idx = tcombo.findText("Pro Controller")
            tcombo.setCurrentIndex(type_idx if type_idx >= 0 else 0)

            for btn in bindings.values():
                btn.set_binding("")

            _note_profile_edited()
            self._mark_dirty()

        btn_reset.clicked.connect(_on_reset_profile)
        bottom.addWidget(btn_reset)

        bl.addLayout(bottom)

        layout.addWidget(body, 1)

        # Set initial enabled state based on the Connected checkbox
        body.setEnabled(chk.isChecked())
        api.setEnabled(chk.isChecked())
        dev.setEnabled(chk.isChecked())
        tcombo.setEnabled(chk.isChecked())
        btn_refresh.setEnabled(chk.isChecked())
        self._input_player_controls[num] = {
            "connected": chk,
            "api": api,
            "device": dev,
            "type": tcombo,
            "bindings": bindings,
        }

        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(scroll_content)

        outer = QWidget()
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)
        return outer

    def _input_adv_settings(self) -> QWidget:
        """Advanced input settings — keyboard navigation, global options."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp_opts = QGroupBox("Global Input Options")
        g_opts = QVBoxLayout(grp_opts)
        g_opts.setSpacing(8)

        self._chk_gamepad_nav = QCheckBox("Enable gamepad navigation in UI")
        self._chk_gamepad_nav.setChecked(bool(getattr(self._cfg, "input_gamepad_nav", False)))
        self._chk_gamepad_nav.toggled.connect(self._mark_dirty)
        g_opts.addWidget(self._chk_gamepad_nav)

        self._chk_global_vibration = QCheckBox("Global vibration / haptic feedback")
        self._chk_global_vibration.setChecked(bool(getattr(self._cfg, "input_vibration", True)))
        self._chk_global_vibration.toggled.connect(self._mark_dirty)
        g_opts.addWidget(self._chk_global_vibration)

        self._chk_global_motion = QCheckBox("Global motion controls")
        self._chk_global_motion.setChecked(bool(getattr(self._cfg, "input_motion", True)))
        self._chk_global_motion.toggled.connect(self._mark_dirty)
        g_opts.addWidget(self._chk_global_motion)

        self._chk_input_on_focus = QCheckBox("Only accept input when window is focused")
        self._chk_input_on_focus.setChecked(bool(getattr(self._cfg, "input_focus_only", True)))
        self._chk_input_on_focus.toggled.connect(self._mark_dirty)
        g_opts.addWidget(self._chk_input_on_focus)

        layout.addWidget(grp_opts)

        grp_kb = QGroupBox("Keyboard Navigation")
        g_kb = QFormLayout(grp_kb)
        g_kb.setSpacing(8)
        for label, default in [
            ("Navigate Up:", "Up / W"),
            ("Navigate Down:", "Down / S"),
            ("Navigate Left:", "Left / A"),
            ("Navigate Right:", "Right / D"),
            ("Select:", "Enter"),
            ("Back:", "Escape"),
        ]:
            le = QLineEdit(default)
            le.setReadOnly(True)
            le.setEnabled(False)
            g_kb.addRow(label, le)
        layout.addWidget(grp_kb)

        grp_adv = QGroupBox("Advanced")
        g_adv = QVBoxLayout(grp_adv)
        g_adv.setSpacing(8)
        g_adv.addWidget(_disabled_check("Use raw input (lower latency)"))
        g_adv.addWidget(_disabled_check("Combine Joy-Cons into single controller"))
        g_adv.addWidget(_disabled_check("Enable analogue triggers for GC adapter"))
        layout.addWidget(grp_adv)

        layout.addStretch()
        return w

    def _collect_input_player_settings(self) -> dict[str, dict[str, object]]:
        merged = copy.deepcopy(self._cfg.input_player_settings)
        controls = getattr(self, "_input_player_controls", {})
        for num, widget_map in controls.items():
            chk = widget_map.get("connected")
            api = widget_map.get("api")
            dev = widget_map.get("device")
            typ = widget_map.get("type")
            if not isinstance(chk, QCheckBox):
                continue
            if not isinstance(api, QComboBox):
                continue
            if not isinstance(dev, QComboBox):
                continue
            if not isinstance(typ, QComboBox):
                continue
            bindings_map: dict[str, str] = {}
            bind_buttons = widget_map.get("bindings")
            if isinstance(bind_buttons, dict):
                for key, btn in bind_buttons.items():
                    if hasattr(btn, "text"):
                        val = btn.text().strip()
                        if val:
                            bindings_map[key] = val
            merged[str(num)] = {
                "connected": chk.isChecked(),
                "api": api.currentText(),
                "device": dev.currentText(),
                "device_index": (
                    int(dev.currentData())
                    if isinstance(dev.currentData(), int) and dev.currentData() >= 0
                    else None
                ),
                "device_guid": (
                    self._input_mgr.get_device_guid(int(dev.currentData()))
                    if isinstance(dev.currentData(), int) and dev.currentData() >= 0
                    else ""
                ),
                "type": typ.currentText(),
                "bindings": bindings_map,
            }
        return merged

    # -- Emulators -----------------------------------------------------

    def _page_emulators(self, sub: str) -> QWidget:
        if sub == "Installed":
            return self._emu_installed()
        if sub == "Browse & Download":
            return self._emu_browse()
        if sub == "Configuration":
            return self._emu_config()
        return _placeholder(sub)

    def _emu_installed(self) -> QWidget:
        """Shows installed emulators with filter, sort, and action buttons."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Filter + Sort + Update All row
        controls = QHBoxLayout()
        controls.setSpacing(6)

        lbl_filter = QLabel("Filter:")
        lbl_filter.setFixedWidth(46)
        controls.addWidget(lbl_filter)
        self._inst_filter = QComboBox()
        self._inst_filter.addItem("All Systems", "")
        for sid, name, _ in KNOWN_SYSTEMS:
            self._inst_filter.addItem(name, sid)
        self._inst_filter.currentIndexChanged.connect(self._refresh_installed_cards)
        controls.addWidget(self._inst_filter, 1)

        controls.addSpacing(10)

        lbl_sort = QLabel("Sort:")
        lbl_sort.setFixedWidth(36)
        controls.addWidget(lbl_sort)
        self._inst_sort = QComboBox()
        self._inst_sort.addItem("Title", "title")
        self._inst_sort.addItem("Brand", "brand")
        self._inst_sort.currentIndexChanged.connect(self._refresh_installed_cards)
        controls.addWidget(self._inst_sort, 1)

        self._inst_sort_asc = True
        self._inst_sort_btn = QPushButton()
        self._inst_sort_btn.setIcon(lucide_icon("arrow-up", 14, active_theme().fg_primary))
        self._inst_sort_btn.setFixedSize(28, 28)
        self._inst_sort_btn.setToolTip("Ascending — click to toggle")
        self._inst_sort_btn.clicked.connect(self._on_inst_sort_direction)
        controls.addWidget(self._inst_sort_btn)
        layout.addLayout(controls)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        t = active_theme()
        self._btn_update_all = QPushButton("  Update All")
        self._btn_update_all.setIcon(lucide_icon("refresh-cw", 14, t.accent_primary))
        self._btn_update_all.clicked.connect(self._on_update_all_cores)
        self._btn_update_all.setEnabled(False)
        self._btn_update_all.setToolTip("Checking for updates...")
        btn_row.addWidget(self._btn_update_all)
        btn_add = QPushButton("  Add Manually...")
        btn_add.setIcon(lucide_icon("plus", 14, t.fg_primary))
        btn_add.clicked.connect(self._on_add_emulator)
        btn_row.addWidget(btn_add)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        from PySide6.QtWidgets import QScrollArea

        self._installed_content = QWidget()
        self._installed_layout = QVBoxLayout(self._installed_content)
        self._installed_layout.setContentsMargins(0, 0, 0, 0)
        self._installed_layout.setSpacing(4)
        self._installed_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._installed_content)
        layout.addWidget(scroll, 1)

        self._installed_cards: list[QWidget] = []
        self._refresh_installed_cards()

        return w

    def _on_inst_sort_direction(self):
        self._inst_sort_asc = not self._inst_sort_asc
        icon_name = "arrow-up" if self._inst_sort_asc else "arrow-down"
        tip = "Ascending" if self._inst_sort_asc else "Descending"
        self._inst_sort_btn.setIcon(lucide_icon(icon_name, 14, active_theme().fg_primary))
        self._inst_sort_btn.setToolTip(f"{tip} — click to toggle")
        self._refresh_installed_cards()

    def _on_update_all_cores(self):
        """Update every installed RetroArch core in one batch."""
        from meridian.core.emulator_install import update_retroarch_core

        cores_to_update: list[tuple[EmulatorEntry, EmulatorCatalogEntry]] = []
        for entry in self._cfg.emulators:
            cat = emulator_catalog_entry(entry.catalog_id or entry.name)
            if cat and cat.install_strategy == "retroarch_core":
                cores_to_update.append((entry, cat))

        if not cores_to_update:
            _msgbox.information(self, "Update All", "No installed cores to update.")
            return

        progress = QProgressDialog(
            f"Updating {len(cores_to_update)} core(s)...", "", 0, len(cores_to_update), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()

        import threading

        ok_count = 0
        fail_count = 0
        for idx, (entry, cat) in enumerate(cores_to_update):
            progress.setValue(idx)
            progress.setLabelText(f"Updating {cat.name}...")
            QApplication.processEvents()

            self._batch_update_result = None

            def _worker(_cat=cat):
                self._batch_update_result = update_retroarch_core(_cat, self._cfg.emulators)

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            while t.is_alive():
                QApplication.processEvents()
                t.join(timeout=0.05)

            result = self._batch_update_result
            if result and result.ok:
                ok_count += 1
                self._core_update_cache[cat.id] = False
            else:
                fail_count += 1
        progress.setValue(len(cores_to_update))

        from meridian.core.audio_manager import AudioManager
        AudioManager.instance().play_notification()
        self._update_update_all_button()
        self._refresh_installed_cards()
        _msgbox.information(
            self, "Update All",
            f"Updated {ok_count} core(s).\n"
            + (f"Failed: {fail_count}" if fail_count else "All cores up to date."),
        )

    def _insert_installed_card(self, entry: EmulatorEntry):
        """One installed emulator card with tags, version, and action buttons."""
        catalog = emulator_catalog_entry(entry.catalog_id or entry.name)
        is_core = catalog and catalog.install_strategy == "retroarch_core"
        t = active_theme()
        tag_style = (
            f"background: {t.accent_primary}; color: #fff; border-radius: 3px;"
            f" padding: 2px 8px; font-size: 7pt;"
        )

        card = QWidget()
        card.setObjectName("playerSlot")
        row = QHBoxLayout(card)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)

        check_icon = QLabel()
        check_icon.setPixmap(lucide_pixmap("circle-check", 16, t.accent_secondary))
        check_icon.setFixedSize(20, 20)
        row.addWidget(check_icon)

        info = QVBoxLayout()
        info.setSpacing(4)

        # Name
        name_lbl = QLabel(f"<b>{entry.display_name()}</b>")
        info.addWidget(name_lbl)

        # Tags row (brand + systems) — above version
        if catalog and catalog.systems:
            tags_layout = QHBoxLayout()
            tags_layout.setContentsMargins(0, 0, 0, 0)
            tags_layout.setSpacing(4)
            brand = _system_company(catalog.systems[0])
            if brand:
                bl = QLabel(brand)
                bl.setStyleSheet(tag_style)
                tags_layout.addWidget(bl)
            if catalog.release_year:
                yl = QLabel(str(catalog.release_year))
                yl.setStyleSheet(tag_style)
                tags_layout.addWidget(yl)
            for sid in catalog.systems[:4]:
                sl = QLabel(SYSTEM_NAMES.get(sid, sid))
                sl.setStyleSheet(tag_style)
                tags_layout.addWidget(sl)
            if len(catalog.systems) > 4:
                ml = QLabel(f"+{len(catalog.systems) - 4}")
                ml.setStyleSheet(tag_style)
                tags_layout.addWidget(ml)
            tags_layout.addStretch()
            info.addLayout(tags_layout)

        # Version: "Core: <version>" for cores, plain version for standalone
        if is_core:
            ver = f"Core: {entry.version}" if entry.version else f"Core: {catalog.core_filename if catalog else 'N/A'}"
        else:
            ver = entry.version or "N/A"
        ver_lbl = QLabel(ver)
        ver_lbl.setObjectName("sectionLabel")
        info.addWidget(ver_lbl)

        row.addLayout(info, 1)

        # Action buttons
        btn_settings = QPushButton()
        btn_settings.setIcon(lucide_icon("settings", 14, t.fg_primary))
        btn_settings.setFixedSize(28, 28)
        btn_settings.setToolTip("Emulator settings")
        btn_settings.clicked.connect(lambda _, e=entry: self._on_emu_settings(e))
        row.addWidget(btn_settings)

        btn_update = QPushButton()
        btn_update.setFixedSize(28, 28)
        if is_core and catalog:
            has_update = self._core_update_cache.get(catalog.id, False)
            if has_update:
                btn_update.setEnabled(True)
                btn_update.setIcon(lucide_icon("refresh-cw", 14, t.accent_primary))
                btn_update.setToolTip("Update available — click to update")
                btn_update.setStyleSheet(
                    f"QPushButton {{ border: 1px solid {t.accent_primary}; border-radius: 4px; }}"
                    f"QPushButton:hover {{ background: {t.accent_primary}; }}"
                )
                btn_update.clicked.connect(
                    lambda _, e=entry, c=catalog: self._on_update_core(e, c)
                )
            else:
                btn_update.setEnabled(False)
                btn_update.setIcon(lucide_icon("refresh-cw", 14, t.fg_disabled))
                btn_update.setToolTip("Core is up to date")
        else:
            btn_update.setEnabled(False)
            btn_update.setIcon(lucide_icon("refresh-cw", 14, t.fg_disabled))
            btn_update.setToolTip("Updates not available for standalone emulators")
        row.addWidget(btn_update)

        btn_delete = QPushButton()
        btn_delete.setIcon(lucide_icon("trash-2", 14, t.fg_primary))
        btn_delete.setFixedSize(28, 28)
        btn_delete.setToolTip("Remove emulator")
        btn_delete.clicked.connect(
            lambda _, c=card, e=entry: self._on_delete_installed(c, e)
        )
        row.addWidget(btn_delete)

        idx = self._installed_layout.count() - 1
        self._installed_layout.insertWidget(idx, card)
        self._installed_cards.append(card)

    def _check_core_updates_async(self):
        """Check for core updates in a background thread, then refresh cards."""
        import threading

        def _worker():
            from meridian.core.emulator_install import core_has_update
            results: dict[str, bool] = {}
            for entry in self._cfg.emulators:
                cat = emulator_catalog_entry(entry.catalog_id or entry.name)
                if cat and cat.install_strategy == "retroarch_core":
                    try:
                        results[cat.id] = core_has_update(cat, self._cfg.emulators)
                    except Exception:
                        results[cat.id] = False
            self._core_update_cache = results
            try:
                from PySide6.QtCore import QMetaObject, Qt as QtConst
                QMetaObject.invokeMethod(
                    self, "_refresh_installed_cards", QtConst.QueuedConnection,
                )
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _update_update_all_button(self):
        """Enable/disable the Update All button based on available updates."""
        if not hasattr(self, "_btn_update_all"):
            return
        any_updates = any(self._core_update_cache.values())
        self._btn_update_all.setEnabled(any_updates)
        t = active_theme()
        if any_updates:
            count = sum(1 for v in self._core_update_cache.values() if v)
            self._btn_update_all.setToolTip(f"{count} update(s) available")
            self._btn_update_all.setIcon(lucide_icon("refresh-cw", 14, t.accent_primary))
        else:
            self._btn_update_all.setToolTip("All emulators are up to date")
            self._btn_update_all.setIcon(lucide_icon("refresh-cw", 14, t.fg_disabled))

    def _on_emu_settings(self, entry: EmulatorEntry):
        """Open per-emulator settings dialog."""
        dlg = _EmulatorSettingsDialog(entry, self._cfg, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_installed_cards()
            self._mark_dirty()

    def _on_update_core(self, entry: EmulatorEntry, catalog: EmulatorCatalogEntry):
        """Re-download a RetroArch core to get the latest nightly build."""
        import threading
        from meridian.core.emulator_install import update_retroarch_core

        progress = QProgressDialog(f"Updating {catalog.name} core...", "", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        self._update_result = None

        def _worker():
            self._update_result = update_retroarch_core(catalog, self._cfg.emulators)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        while thread.is_alive():
            QApplication.processEvents()
            thread.join(timeout=0.05)

        progress.close()

        result = self._update_result
        from meridian.core.audio_manager import AudioManager
        if result and result.ok:
            self._core_update_cache[catalog.id] = False
            AudioManager.instance().play_notification()
            _msgbox.information(self, "Core Updated", result.message)
            self._refresh_installed_cards()
        else:
            _msgbox.warning(self, "Core Update Failed", result.message if result else "Unknown error.")

    def _on_delete_installed(self, card: QWidget, entry: EmulatorEntry):
        catalog = emulator_catalog_entry(entry.catalog_id or entry.name)
        is_core = catalog and catalog.install_strategy == "retroarch_core"

        if is_core:
            label = f"Remove {entry.display_name()} core?"
            detail = "The core DLL will be deleted. RetroArch itself will not be affected."
        else:
            label = f"Delete {entry.display_name()} and all installed files from disk?"
            detail = ""

        confirm = _msgbox.question(
            self,
            "Delete Emulator",
            f"{label}\n{detail}".strip(),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        if is_core and catalog:
            from meridian.core.emulator_install import delete_retroarch_core
            ok, err = delete_retroarch_core(catalog, self._cfg.emulators)
        else:
            ok, err = self._delete_emulator_files(entry)

        if not ok:
            _msgbox.warning(
                self,
                "Delete failed",
                f"{entry.display_name()} was removed from Meridian settings, "
                f"but some files could not be deleted:\n{err}",
            )

        if entry in self._cfg.emulators:
            self._cfg.emulators.remove(entry)
        if card in self._installed_cards:
            self._installed_cards.remove(card)
        card.setParent(None)
        card.deleteLater()
        self._mark_dirty()
        if hasattr(self, "_browse_filter"):
            self._populate_browse_catalog(self._browse_filter.currentData() or "")
        if not self._cfg.emulators:
            self._show_installed_empty_state()

    def _delete_emulator_files(self, entry: EmulatorEntry) -> tuple[bool, str]:
        """Delete installed emulator artifacts from disk when possible."""
        errors: list[str] = []
        removed_any = False
        roots_to_delete: list[Path] = []

        if entry.install_dir:
            roots_to_delete.append(Path(entry.install_dir))

        if entry.path:
            exe_path = Path(entry.path)
            if exe_path.exists():
                emu_root = emulators_root().resolve()
                try:
                    exe_resolved = exe_path.resolve()
                    if emu_root in exe_resolved.parents:
                        roots_to_delete.append(exe_resolved.parent)
                    elif exe_resolved.is_file():
                        exe_resolved.unlink()
                        removed_any = True
                except Exception as exc:
                    errors.append(str(exc))

        seen: set[str] = set()
        unique_roots: list[Path] = []
        for root in roots_to_delete:
            key = str(root)
            if key not in seen:
                seen.add(key)
                unique_roots.append(root)

        for root in unique_roots:
            try:
                if root.exists():
                    shutil.rmtree(root)
                    removed_any = True
            except Exception as exc:
                errors.append(f"{root}: {exc}")

        if errors:
            return False, "; ".join(errors)
        if not removed_any:
            return True, "No local files were present."
        return True, ""

    def _emu_browse(self) -> QWidget:
        """Browse emulators by console with download buttons."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Filter + Sort row — same row, aligned labels
        controls = QHBoxLayout()
        controls.setSpacing(6)

        lbl_filter = QLabel("Filter:")
        lbl_filter.setFixedWidth(46)
        controls.addWidget(lbl_filter)
        self._browse_filter = QComboBox()
        self._browse_filter.addItem("All Systems", "")
        for sid, name, _ in KNOWN_SYSTEMS:
            self._browse_filter.addItem(name, sid)
        self._browse_filter.currentIndexChanged.connect(self._on_browse_filter)
        controls.addWidget(self._browse_filter, 1)

        controls.addSpacing(10)

        lbl_sort = QLabel("Sort:")
        lbl_sort.setFixedWidth(36)
        controls.addWidget(lbl_sort)
        self._browse_sort = QComboBox()
        self._browse_sort.addItem("Title", "title")
        self._browse_sort.addItem("Brand", "brand")
        self._browse_sort.addItem("Release Year", "year")
        self._browse_sort.currentIndexChanged.connect(self._on_browse_sort_changed)
        controls.addWidget(self._browse_sort, 1)

        self._browse_sort_asc = True
        self._browse_sort_btn = QPushButton()
        self._browse_sort_btn.setIcon(lucide_icon("arrow-up", 14, active_theme().fg_primary))
        self._browse_sort_btn.setFixedSize(28, 28)
        self._browse_sort_btn.setToolTip("Ascending — click to toggle")
        self._browse_sort_btn.clicked.connect(self._on_browse_sort_direction)
        controls.addWidget(self._browse_sort_btn)
        layout.addLayout(controls)

        # Catalog scroll area
        from PySide6.QtWidgets import QScrollArea

        self._browse_content = QWidget()
        self._browse_layout = QVBoxLayout(self._browse_content)
        self._browse_layout.setContentsMargins(0, 0, 0, 0)
        self._browse_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._browse_content)
        layout.addWidget(scroll, 1)

        self._populate_browse_catalog("")
        return w

    def _populate_browse_catalog(self, filter_system: str):
        """Rebuild the catalog list, optionally filtered and sorted."""
        from meridian.core.emulator_install import check_core_installed

        while self._browse_layout.count():
            item = self._browse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        installed_names = {e.name for e in self._cfg.emulators}
        installed_ids = {e.catalog_id for e in self._cfg.emulators if e.catalog_id}

        # Build filtered list
        entries: list[EmulatorCatalogEntry] = []
        for entry in EMULATOR_CATALOG:
            if entry.id == "retroarch":
                continue
            if not entry.windows_supported or entry.install_strategy == "manual":
                continue
            if filter_system and filter_system not in entry.systems:
                continue
            entries.append(entry)

        # Sort
        sort_key = getattr(self, "_browse_sort", None)
        sort_mode = sort_key.currentData() if sort_key else "title"
        ascending = getattr(self, "_browse_sort_asc", True)

        if sort_mode == "brand":
            entries.sort(
                key=lambda e: (
                    _system_company(e.systems[0]) if e.systems else "",
                    e.name.lower(),
                ),
                reverse=not ascending,
            )
        elif sort_mode == "year":
            entries.sort(
                key=lambda e: (e.release_year or 9999, e.name.lower()),
                reverse=not ascending,
            )
        else:
            entries.sort(key=lambda e: e.name.lower(), reverse=not ascending)

        t = active_theme()
        tag_style = (
            f"background: {t.accent_primary}; color: #fff; border-radius: 3px;"
            f" padding: 2px 8px; font-size: 7pt;"
        )

        for entry in entries:
            card = QWidget()
            card.setObjectName("playerSlot")
            row = QHBoxLayout(card)
            row.setContentsMargins(10, 8, 10, 8)
            row.setSpacing(10)

            info = QVBoxLayout()
            info.setSpacing(4)

            # Name
            name_lbl = QLabel(f"<b>{entry.name}</b>")
            info.addWidget(name_lbl)

            # Tags row — above version
            tags_layout = QHBoxLayout()
            tags_layout.setContentsMargins(0, 0, 0, 0)
            tags_layout.setSpacing(4)

            brand = _system_company(entry.systems[0]) if entry.systems else ""
            if brand:
                bl = QLabel(brand)
                bl.setStyleSheet(tag_style)
                tags_layout.addWidget(bl)

            if entry.release_year:
                yl = QLabel(str(entry.release_year))
                yl.setStyleSheet(tag_style)
                tags_layout.addWidget(yl)

            for sid in entry.systems[:5]:
                sl = QLabel(SYSTEM_NAMES.get(sid, sid))
                sl.setStyleSheet(tag_style)
                tags_layout.addWidget(sl)
            if len(entry.systems) > 5:
                ml = QLabel(f"+{len(entry.systems) - 5}")
                ml.setStyleSheet(tag_style)
                tags_layout.addWidget(ml)

            tags_layout.addStretch()
            info.addLayout(tags_layout)

            # Version — below tags
            if entry.install_strategy == "retroarch_core":
                ver_text = f"Core: {entry.core_filename}"
            elif entry.preferred_version:
                ver_text = entry.preferred_version
            else:
                ver_text = "Latest stable"
            ver_lbl = QLabel(ver_text)
            ver_lbl.setObjectName("sectionLabel")
            info.addWidget(ver_lbl)

            row.addLayout(info, 1)

            is_installed = (
                entry.id in installed_ids
                or entry.name in installed_names
                or (entry.install_strategy == "retroarch_core"
                    and check_core_installed(entry, self._cfg.emulators))
            )

            if is_installed:
                installed_lbl = QLabel()
                installed_lbl.setPixmap(lucide_pixmap("circle-check", 16, t.accent_secondary))
                installed_lbl.setToolTip("Installed")
                row.addWidget(installed_lbl)
            else:
                btn_dl = QPushButton()
                btn_dl.setIcon(lucide_icon("download", 14, t.fg_primary))
                btn_dl.setFixedSize(28, 28)
                btn_dl.setToolTip(f"Install {entry.name}")
                btn_dl.setEnabled(True)
                btn_dl.clicked.connect(lambda _, e=entry, b=btn_dl: self._on_install_catalog_entry(e, b))
                row.addWidget(btn_dl)

            self._browse_layout.addWidget(card)

        self._browse_layout.addStretch()

    def _on_browse_filter(self, index: int):
        self._repopulate_browse()

    def _on_browse_sort_changed(self, index: int):
        self._repopulate_browse()

    def _on_browse_sort_direction(self):
        self._browse_sort_asc = not self._browse_sort_asc
        icon_name = "arrow-up" if self._browse_sort_asc else "arrow-down"
        tip = "Ascending" if self._browse_sort_asc else "Descending"
        self._browse_sort_btn.setIcon(lucide_icon(icon_name, 14, active_theme().fg_primary))
        self._browse_sort_btn.setToolTip(f"{tip} — click to toggle")
        self._repopulate_browse()

    def _repopulate_browse(self):
        sid = self._browse_filter.currentData() or ""
        self._populate_browse_catalog(sid)

    def _on_install_catalog_entry(self, catalog_entry: EmulatorCatalogEntry, btn: QPushButton):
        import threading

        btn.setEnabled(False)
        progress = QProgressDialog(f"Installing {catalog_entry.name}...", "", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        self._install_result = None

        def _worker():
            self._install_result = install_emulator(catalog_entry, self._cfg.emulators)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        # Keep the event loop alive while the worker runs so the UI stays
        # responsive (progress dialog animates, window doesn't go white).
        while thread.is_alive():
            QApplication.processEvents()
            thread.join(timeout=0.05)

        progress.close()
        btn.setEnabled(True)

        result = self._install_result
        if result is None or not result.ok:
            _msgbox.warning(self, "Install failed", result.message if result else "Unknown error.")
            return

        if result.entry:
            self._upsert_emulator(result.entry)
            self._mark_dirty()

        self._refresh_installed_cards()
        self._populate_browse_catalog(self._browse_filter.currentData() or "")

        from meridian.core.audio_manager import AudioManager
        AudioManager.instance().play_notification()
        _msgbox.information(self, "Install complete", result.message)

    def _upsert_emulator(self, new_entry: EmulatorEntry) -> None:
        for idx, existing in enumerate(self._cfg.emulators):
            same_catalog = bool(new_entry.catalog_id and new_entry.catalog_id == existing.catalog_id)
            same_name = new_entry.name.lower() == existing.name.lower()
            if same_catalog or same_name:
                self._cfg.emulators[idx] = new_entry
                return
        self._cfg.emulators.append(new_entry)

    @Slot()
    def _refresh_installed_cards(self):
        if not hasattr(self, "_installed_layout"):
            return
        while self._installed_layout.count():
            item = self._installed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._installed_layout.addStretch()
        self._installed_cards = []

        # Filter
        filter_sid = ""
        if hasattr(self, "_inst_filter"):
            filter_sid = self._inst_filter.currentData() or ""
        visible: list[EmulatorEntry] = []
        for e in self._cfg.emulators:
            if e.catalog_id == "retroarch" or e.name.lower() == "retroarch":
                continue
            if filter_sid:
                cat = emulator_catalog_entry(e.catalog_id or e.name)
                if cat and filter_sid not in cat.systems:
                    continue
                elif not cat:
                    continue
            visible.append(e)

        # Sort
        sort_mode = "title"
        ascending = True
        if hasattr(self, "_inst_sort"):
            sort_mode = self._inst_sort.currentData() or "title"
            ascending = getattr(self, "_inst_sort_asc", True)

        if sort_mode == "brand":
            def _brand_key(e: EmulatorEntry) -> tuple:
                cat = emulator_catalog_entry(e.catalog_id or e.name)
                company = _system_company(cat.systems[0]) if cat and cat.systems else ""
                return (company, e.display_name().lower())
            visible.sort(key=_brand_key, reverse=not ascending)
        else:
            visible.sort(key=lambda e: e.display_name().lower(), reverse=not ascending)

        for entry in visible:
            self._insert_installed_card(entry)
        if not visible:
            self._show_installed_empty_state()
        self._refresh_system_emulator_controls()
        self._update_update_all_button()

    def _show_installed_empty_state(self):
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(12, 20, 12, 20)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if _LOGO_TRANSPARENT.exists():
            pm = QPixmap(str(_LOGO_TRANSPARENT))
            if not pm.isNull():
                logo_lbl.setPixmap(
                    pm.scaledToHeight(56, Qt.TransformationMode.SmoothTransformation)
                )
        empty_layout.addWidget(logo_lbl)

        msg = QLabel("Whoops! Nothing's here but us snowmen.")
        msg.setObjectName("sectionLabel")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        empty_layout.addWidget(msg)

        sub = QLabel("Install emulators from Browse & Download or add one manually.")
        sub.setObjectName("sectionLabel")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        empty_layout.addWidget(sub)

        idx = self._installed_layout.count() - 1
        self._installed_layout.insertWidget(idx, empty)

    def _emu_config(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Quick Defaults")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        row_all = QHBoxLayout()
        row_all.setSpacing(8)
        row_all.addWidget(QLabel("Set emulator for all consoles:"))
        self._all_systems_emulator_combo = QComboBox()
        row_all.addWidget(self._all_systems_emulator_combo, 1)
        btn_apply_all = QPushButton("Apply to All")
        btn_apply_all.clicked.connect(self._on_apply_emulator_all)
        row_all.addWidget(btn_apply_all)
        g.addLayout(row_all)
        hint = QLabel("Only installed emulators appear. Unsupported consoles are set to None.")
        hint.setObjectName("sectionLabel")
        g.addWidget(hint)
        layout.addWidget(grp)

        grp2 = QGroupBox("Per-Console Emulator")
        g2_root = QVBoxLayout(grp2)
        g2_root.setSpacing(10)

        # Scrollable long list of all known consoles, grouped by company.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        section_host = QWidget()
        section_layout = QVBoxLayout(section_host)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(10)

        self._sys_emu_combos: dict[str, QComboBox] = {}
        self._sys_core_combos: dict[str, QComboBox] = {}
        self._sys_core_labels: dict[str, QLabel] = {}
        self._ensure_system_entries()
        grouped: dict[str, list[tuple[str, str]]] = {name: [] for name in _SYSTEM_COMPANY_ORDER}
        for system_id, display_name, _ext in KNOWN_SYSTEMS:
            grouped.setdefault(_system_company(system_id), []).append((system_id, display_name))

        for company in _SYSTEM_COMPANY_ORDER:
            systems = grouped.get(company, [])
            if not systems:
                continue
            sec = QGroupBox(company)
            sec_form = QFormLayout(sec)
            sec_form.setSpacing(8)
            for system_id, display_name in systems:
                emu_combo = QComboBox()
                emu_combo.currentIndexChanged.connect(
                    lambda _=None, sid=system_id: self._on_system_emulator_changed(sid)
                )
                core_combo = QComboBox()
                core_combo.currentIndexChanged.connect(
                    lambda _=None, sid=system_id: self._on_system_core_changed(sid)
                )
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)
                row_layout.addWidget(emu_combo, 1)
                core_lbl = QLabel("Core:")
                row_layout.addWidget(core_lbl)
                row_layout.addWidget(core_combo, 1)
                sec_form.addRow(f"{display_name}:", row)
                self._sys_emu_combos[system_id] = emu_combo
                self._sys_core_combos[system_id] = core_combo
                self._sys_core_labels[system_id] = core_lbl
            section_layout.addWidget(sec)

        section_layout.addStretch()
        scroll.setWidget(section_host)
        g2_root.addWidget(scroll, 1)
        grp2.setMinimumHeight(220)
        layout.addWidget(grp2, 2)

        grp3 = QGroupBox("Launch")
        g3 = QVBoxLayout(grp3)
        g3.setSpacing(8)
        g3.addWidget(_disabled_check("Confirm before launching game"))
        g3.addWidget(_disabled_check("Track play time"))
        layout.addWidget(grp3)

        grp_bios = QGroupBox("BIOS Files")
        bios_layout = QVBoxLayout(grp_bios)
        bios_layout.setSpacing(8)
        bios_hint = QLabel(
            "Configure BIOS files used by your emulators. "
            "Required entries are needed for normal boot; optional entries may improve compatibility."
        )
        bios_hint.setObjectName("sectionLabel")
        bios_hint.setWordWrap(True)
        bios_layout.addWidget(bios_hint)

        self._bios_path_inputs: dict[str, QLineEdit] = {}
        bios_scroll = QScrollArea()
        bios_scroll.setWidgetResizable(True)
        bios_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        bios_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bios_host = QWidget()
        bios_sections_layout = QVBoxLayout(bios_host)
        bios_sections_layout.setContentsMargins(0, 0, 0, 0)
        bios_sections_layout.setSpacing(10)

        grouped_bios: dict[str, list[dict[str, object]]] = {name: [] for name in _SYSTEM_COMPANY_ORDER}
        for bios in _BIOS_REQUIREMENTS:
            systems_raw = [str(s) for s in bios.get("systems", [])]
            company = _system_company(systems_raw[0]) if systems_raw else "Other"
            grouped_bios.setdefault(company, []).append(bios)

        for company in _SYSTEM_COMPANY_ORDER:
            bios_items = grouped_bios.get(company, [])
            if not bios_items:
                continue
            sec = QGroupBox(company)
            sec_form = QFormLayout(sec)
            sec_form.setSpacing(8)
            sec_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            for bios in bios_items:
                bios_id = str(bios["id"])
                name = str(bios["name"])
                systems = [SYSTEM_NAMES.get(str(s), str(s).upper()) for s in bios.get("systems", [])]
                required = bool(bios.get("required", False))
                if required:
                    requirement_html = '<span style="color: #CC3333; font-weight: 600;">Required</span>'
                else:
                    requirement_html = "Optional"
                row_label_widget = QLabel(f"{name} ({requirement_html}) — {', '.join(systems)}")
                row_label_widget.setTextFormat(Qt.TextFormat.RichText)

                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)
                path_edit = QLineEdit(str(self._cfg.bios_files.get(bios_id, "")))
                path_edit.setPlaceholderText(str(bios.get("hint", "BIOS file path")))
                path_edit.textChanged.connect(self._mark_dirty)
                self._bios_path_inputs[bios_id] = path_edit
                row_layout.addWidget(path_edit, 1)
                btn_browse = QPushButton("Import...")
                btn_browse.setFixedWidth(84)
                btn_browse.clicked.connect(
                    lambda _=None, key=bios_id: self._on_import_bios_file(key)
                )
                row_layout.addWidget(btn_browse)
                sec_form.addRow(row_label_widget, row)
            bios_sections_layout.addWidget(sec)

        bios_sections_layout.addStretch()
        bios_scroll.setWidget(bios_host)
        bios_layout.addWidget(bios_scroll, 1)
        grp_bios.setMinimumHeight(220)
        layout.addWidget(grp_bios, 2)

        self._refresh_system_emulator_controls()

        layout.addStretch()
        return w

    def _ensure_system_entries(self):
        known_ids = [sid for sid, _, _ in KNOWN_SYSTEMS]
        by_id = {s.system_id: s for s in self._cfg.systems}
        for sid in known_ids:
            if sid not in by_id:
                self._cfg.systems.append(SystemEntry(system_id=sid))
        order = {sid: idx for idx, sid in enumerate(known_ids)}
        self._cfg.systems.sort(key=lambda s: order.get(s.system_id, 9999))

    def _system_entry(self, system_id: str) -> SystemEntry:
        for entry in self._cfg.systems:
            if entry.system_id == system_id:
                return entry
        entry = SystemEntry(system_id=system_id)
        self._cfg.systems.append(entry)
        return entry

    def _installed_independent_emulators(self) -> list[EmulatorEntry]:
        """Return all installed emulators (including cores, excluding the
        RetroArch base entry which is managed automatically)."""
        result: list[EmulatorEntry] = []
        for item in self._cfg.emulators:
            if item.catalog_id == "retroarch" or item.name.lower() == "retroarch":
                continue
            result.append(item)
        return result

    def _emulator_supports_system(self, item: EmulatorEntry, system_id: str) -> bool:
        if item.catalog_id == "retroarch" or item.name.lower() == "retroarch":
            return False
        catalog = emulator_catalog_entry(item.catalog_id or item.name)
        if catalog:
            return system_id in catalog.systems
        return True

    def _available_emulators_for_system(self, system_id: str) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for item in self._installed_independent_emulators():
            if self._emulator_supports_system(item, system_id):
                options.append((item.display_name(), item.display_name()))
        if not options:
            return [("None", "")]
        options.sort(key=lambda x: x[0].lower())
        return [("None", "")] + options

    def _retroarch_entry(self) -> EmulatorEntry | None:
        for item in self._cfg.emulators:
            if item.catalog_id == "retroarch" or item.name.lower() == "retroarch":
                return item
        return None

    def _available_retroarch_cores(self, system_id: str) -> list[str]:
        retro = self._retroarch_entry()
        cores: list[str] = []
        if retro:
            current = retro.system_overrides.get(system_id, "")
            if current:
                cores.append(current)
            for candidate in _RETROARCH_CORE_CANDIDATES.get(system_id, []):
                if candidate not in cores:
                    cores.append(candidate)
            # Scan the shared cores directory
            cores_dir = emulators_root() / "cores"
            if cores_dir.exists():
                for dll in cores_dir.glob("*_libretro.dll"):
                    name = dll.name
                    if name not in cores:
                        cores.append(name)
        return cores

    def _refresh_system_emulator_controls(self):
        if not hasattr(self, "_all_systems_emulator_combo"):
            return
        all_options = [("None", "")]
        for item in self._installed_independent_emulators():
            all_options.append((item.display_name(), item.display_name()))
        seen: set[str] = set()
        self._all_systems_emulator_combo.blockSignals(True)
        self._all_systems_emulator_combo.clear()
        for label, value in all_options:
            if value in seen:
                continue
            seen.add(value)
            self._all_systems_emulator_combo.addItem(label, value)
        self._all_systems_emulator_combo.blockSignals(False)

        for sid, combo in getattr(self, "_sys_emu_combos", {}).items():
            sys_entry = self._system_entry(sid)
            options = self._available_emulators_for_system(sid)
            current_value = sys_entry.emulator_name
            combo.blockSignals(True)
            combo.clear()
            for label, value in options:
                combo.addItem(label, value)
            idx = combo.findData(current_value)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
            self._sync_core_combo_for_system(sid)

    def _sync_core_combo_for_system(self, system_id: str):
        emu_combo = self._sys_emu_combos.get(system_id)
        core_combo = self._sys_core_combos.get(system_id)
        core_label = self._sys_core_labels.get(system_id)
        if not emu_combo or not core_combo or not core_label:
            return
        selected_name = str(emu_combo.currentData() or "")

        # Check if the selected emulator is a core or the base RetroArch entry
        selected_emu = None
        for e in self._cfg.emulators:
            if e.display_name().lower() == selected_name.lower():
                selected_emu = e
                break

        is_retroarch_base = selected_name.lower() == "retroarch"
        is_core = False
        if selected_emu:
            cat = emulator_catalog_entry(selected_emu.catalog_id or selected_emu.name)
            is_core = cat and cat.install_strategy == "retroarch_core"

        # Only show core dropdown for base RetroArch entry (not for individual cores)
        show_core = is_retroarch_base and not is_core
        core_combo.blockSignals(True)
        core_combo.clear()
        core_label.setVisible(show_core)
        core_combo.setVisible(show_core)
        if show_core:
            retro = self._retroarch_entry()
            current = ""
            if retro:
                current = retro.system_overrides.get(system_id, "")
            cores = self._available_retroarch_cores(system_id)
            if not cores:
                cores = ["(no cores found)"]
            for item in cores:
                core_combo.addItem(item, item)
            idx = core_combo.findData(current)
            core_combo.setCurrentIndex(idx if idx >= 0 else 0)
        core_combo.blockSignals(False)

    def _on_apply_emulator_all(self):
        selected = str(self._all_systems_emulator_combo.currentData() or "")
        for sid, combo in self._sys_emu_combos.items():
            idx = combo.findData(selected)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            self._on_system_emulator_changed(sid)
        self._mark_dirty()

    def _on_system_emulator_changed(self, system_id: str):
        combo = self._sys_emu_combos.get(system_id)
        if not combo:
            return
        sys_entry = self._system_entry(system_id)
        sys_entry.emulator_name = str(combo.currentData() or "")
        self._sync_core_combo_for_system(system_id)
        self._mark_dirty()

    def _on_system_core_changed(self, system_id: str):
        combo = self._sys_core_combos.get(system_id)
        retro = self._retroarch_entry()
        if not combo or not retro:
            return
        core = str(combo.currentData() or "")
        if not core or core.startswith("("):
            return

        ok, message = self._ensure_retroarch_core_installed(retro, core)
        if not ok:
            _msgbox.warning(self, "RetroArch Core", message)
            return

        retro.system_overrides[system_id] = core
        self._mark_dirty()

    def _ensure_retroarch_core_installed(self, retro: EmulatorEntry, core_dll: str) -> tuple[bool, str]:
        """Ensure selected RetroArch core DLL exists; download if missing."""
        import threading as _threading

        cores_dir = emulators_root() / "cores"
        cores_dir.mkdir(parents=True, exist_ok=True)
        target = cores_dir / core_dll
        if target.exists():
            return True, ""

        progress = QProgressDialog(f"Downloading core {core_dll}...", "", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        result_holder: list[tuple[bool, str]] = [(False, "Thread did not complete")]

        def _worker():
            core_zip_url = f"https://buildbot.libretro.com/nightly/windows/x86_64/latest/{core_dll}.zip"
            tmp_zip = emulators_root() / "_downloads" / f"{core_dll}.zip"
            tmp_zip.parent.mkdir(parents=True, exist_ok=True)
            try:
                req = urllib.request.Request(core_zip_url, headers={"User-Agent": "Meridian/1.0"}, method="GET")
                with urllib.request.urlopen(req, timeout=60) as res:
                    tmp_zip.write_bytes(res.read())
                with zipfile.ZipFile(tmp_zip, "r") as zf:
                    zf.extractall(cores_dir)
                if not target.exists():
                    result_holder[0] = (False, f"Downloaded archive but {core_dll} was not found after extraction.")
                else:
                    result_holder[0] = (True, "")
            except Exception as exc:
                result_holder[0] = (False, f"Failed to download/install core {core_dll}: {exc}")
            finally:
                try:
                    tmp_zip.unlink(missing_ok=True)
                except Exception:
                    pass

        t = _threading.Thread(target=_worker, daemon=True)
        t.start()
        while t.is_alive():
            QApplication.processEvents()
            t.join(timeout=0.05)
        progress.close()
        return result_holder[0]

    def _bios_storage_dir(self) -> Path:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation,
        )
        path = Path(base) / "bios"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _on_import_bios_file(self, bios_id: str) -> None:
        from meridian.core.config import BIOS_FILENAME_ALIASES

        le = getattr(self, "_bios_path_inputs", {}).get(bios_id)
        if not le:
            return

        accepted_names = BIOS_FILENAME_ALIASES.get(bios_id, [])
        if accepted_names:
            exts = sorted({Path(n).suffix for n in accepted_names if Path(n).suffix})
            ext_filter = " ".join(f"*{e}" for e in exts) if exts else "*.*"
            names_str = ", ".join(accepted_names)
            file_filter = f"BIOS files ({ext_filter});;All Files (*.*)"
        else:
            file_filter = "All Files (*.*)"
            names_str = ""

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import BIOS File",
            le.text().strip() or "",
            file_filter,
        )
        if not path:
            return

        src = Path(path)
        if accepted_names:
            if src.name not in accepted_names:
                lower_aliases = {n.lower(): n for n in accepted_names}
                if src.name.lower() not in lower_aliases:
                    _msgbox.warning(
                        self,
                        "Invalid BIOS File",
                        f"The selected file \"{src.name}\" is not a recognized "
                        f"BIOS filename for this entry.\n\n"
                        f"Expected: {names_str}",
                    )
                    return

        ext = src.suffix.lower() or ".bin"
        dest = self._bios_storage_dir() / f"{bios_id}{ext}"
        try:
            shutil.copy2(src, dest)
        except Exception as exc:
            _msgbox.warning(
                self,
                "Import BIOS File",
                f"Failed to import BIOS file:\n{exc}",
            )
            return
        le.setText(str(dest))
        _msgbox.information(
            self,
            "BIOS Imported",
            f"Imported to Meridian BIOS storage:\n{dest}\n\n"
            "You can now delete the original source file if desired.",
        )

    # -- Networking ----------------------------------------------------

    def _page_networking(self, sub: str) -> QWidget:
        if sub == "Multiplayer":
            return self._net_multiplayer()
        if sub == "Updates":
            return self._net_updates()
        return _placeholder(sub)

    def _net_multiplayer(self) -> QWidget:
        return _coming_soon_page("Multiplayer", "Netplay and online multiplayer features")

    def _net_updates(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp_ra = QGroupBox("RetroArch")
        g_ra = QVBoxLayout(grp_ra)
        g_ra.setSpacing(8)
        self._chk_retroarch_auto_update = QCheckBox(
            "Automatically update RetroArch on startup"
        )
        self._chk_retroarch_auto_update.setChecked(self._cfg.retroarch_auto_update)
        self._chk_retroarch_auto_update.toggled.connect(self._mark_dirty)
        g_ra.addWidget(self._chk_retroarch_auto_update)
        ra_hint = QLabel(
            "RetroArch is required for most emulator cores. "
            "When enabled, Meridian will check for and install updates "
            "each time it starts."
        )
        ra_hint.setObjectName("sectionLabel")
        ra_hint.setWordWrap(True)
        g_ra.addWidget(ra_hint)
        layout.addWidget(grp_ra)

        grp = QGroupBox("Meridian Updates")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        self._chk_updates_startup = QCheckBox("Check for updates on startup")
        self._chk_updates_startup.setChecked(self._cfg.updates_check_on_startup)
        self._chk_updates_startup.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_updates_startup)

        self._chk_updates_prerelease = QCheckBox("Include pre-release versions")
        self._chk_updates_prerelease.setChecked(self._cfg.updates_include_prerelease)
        self._chk_updates_prerelease.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_updates_prerelease)

        btn = QPushButton("Check Now")
        btn.clicked.connect(self._on_check_updates_now)
        btn.setFixedWidth(120)
        g.addWidget(btn)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    def _on_multiplayer_toggled(self, enabled: bool) -> None:
        self._mark_dirty()

    def _on_check_updates_now(self) -> None:
        _msgbox.information(
            self,
            "Check for Updates",
            "Manual update checks are not available yet.\n"
            "The selected update preferences will be saved.",
        )

    # -- Tools ---------------------------------------------------------

    def _page_tools(self, sub: str) -> QWidget:
        if sub == "Scraper":
            return self._tools_scraper()
        if sub == "RetroAchievements":
            return self._tools_retroachievements()
        if sub == "File Management":
            return self._tools_files()
        if sub == "Clock":
            return self._tools_clock()
        return _placeholder(sub)

    def _tools_scraper(self) -> QWidget:
        """Dynamic scraper config — adapts UI to the selected source."""
        from PySide6.QtWidgets import QScrollArea

        w = QWidget()
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # -- Active source selector ------------------------------------
        grp_src = QGroupBox("Scraper Source")
        g_src = QVBoxLayout(grp_src)
        g_src.setSpacing(8)

        hint = QLabel(
            "SteamGridDB is Meridian's scraper source for metadata and artwork."
        )
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        g_src.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("Active source:"))
        self._scraper_combo = QComboBox()
        self._scraper_combo.addItems(SCRAPER_SOURCE_NAMES)
        idx = SCRAPER_SOURCE_NAMES.index("SteamGridDB") if "SteamGridDB" in SCRAPER_SOURCE_NAMES else 0
        self._scraper_combo.setCurrentIndex(idx)
        self._scraper_combo.setEnabled(False)
        row.addWidget(self._scraper_combo, 1)
        g_src.addLayout(row)

        self._scraper_url_label = QLabel()
        self._scraper_url_label.setObjectName("sectionLabel")
        self._scraper_url_label.setWordWrap(True)
        self._scraper_url_label.setOpenExternalLinks(True)
        g_src.addWidget(self._scraper_url_label)

        layout.addWidget(grp_src)

        # -- API Credentials (stacked per source) ----------------------
        self._scraper_cred_group = QGroupBox("API Credentials")
        cred_layout = QVBoxLayout(self._scraper_cred_group)
        cred_layout.setSpacing(8)

        self._scraper_cred_stack = QStackedWidget()
        self._scraper_cred_inputs: dict[str, dict[str, QLineEdit]] = {}
        self._scraper_test_btns: dict[str, QPushButton] = {}

        t_theme = active_theme()
        _plug_normal_color = t_theme.fg_disabled

        for src in SCRAPER_SOURCES:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(8)

            plug_btn = QPushButton()
            plug_btn.setFixedSize(26, 26)
            plug_btn.setFlat(True)
            plug_btn.setToolTip("Test connection")
            plug_btn.setIcon(lucide_icon("plug", 14, _plug_normal_color))
            plug_btn.setObjectName("linkButton")
            plug_btn.clicked.connect(self._on_test_scraper_connection)
            self._scraper_test_btns[src.name] = plug_btn

            field_inputs: dict[str, QLineEdit] = {}
            if not src.auth_fields:
                no_cred_row = QWidget()
                nc_lay = QHBoxLayout(no_cred_row)
                nc_lay.setContentsMargins(0, 0, 0, 0)
                nc_lay.setSpacing(6)
                lbl = QLabel("No credentials required for this source.")
                lbl.setObjectName("sectionLabel")
                nc_lay.addWidget(lbl, 1)
                nc_lay.addWidget(plug_btn)
                page_layout.addWidget(no_cred_row)
            else:
                form = QWidget()
                form_layout = QFormLayout(form)
                form_layout.setSpacing(8)
                form_layout.setContentsMargins(0, 0, 0, 0)
                stored = self._cfg.scraper_credentials.get(src.name, {})
                num_fields = len(src.auth_fields)
                for i, (key, label, placeholder, is_secret) in enumerate(src.auth_fields):
                    le = QLineEdit()
                    le.setPlaceholderText(placeholder)
                    if is_secret:
                        le.setEchoMode(QLineEdit.EchoMode.Password)
                    le.setText(stored.get(key, ""))
                    le.textChanged.connect(self._mark_dirty)
                    le.textChanged.connect(lambda _, sn=src.name: self._update_scraper_test_btn(sn))
                    if i == num_fields - 1:
                        field_wrap = QWidget()
                        fw_lay = QHBoxLayout(field_wrap)
                        fw_lay.setContentsMargins(0, 0, 0, 0)
                        fw_lay.setSpacing(4)
                        fw_lay.addWidget(le, 1)
                        fw_lay.addWidget(plug_btn)
                        form_layout.addRow(label, field_wrap)
                    else:
                        form_layout.addRow(label, le)
                    field_inputs[key] = le
                page_layout.addWidget(form)

            page_layout.addStretch()
            self._scraper_cred_inputs[src.name] = field_inputs
            self._scraper_cred_stack.addWidget(page)

        cred_layout.addWidget(self._scraper_cred_stack)
        layout.addWidget(self._scraper_cred_group)

        # Active test button — tracks whichever source is currently selected
        first_src = SCRAPER_SOURCE_NAMES[0] if SCRAPER_SOURCE_NAMES else ""
        self._scraper_test_btn = self._scraper_test_btns.get(first_src)

        # -- Content to Fetch ------------------------------------------
        grp_content = QGroupBox("Content to Fetch")
        g_c = QVBoxLayout(grp_content)
        g_c.setSpacing(6)

        self._scraper_content_checks: dict[str, QCheckBox] = {}
        for cid, label in SCRAPER_CONTENT_LABELS.items():
            chk = QCheckBox(label)
            chk.setChecked(self._cfg.scraper_content.get(cid, False))
            chk.toggled.connect(self._mark_dirty)
            g_c.addWidget(chk)
            self._scraper_content_checks[cid] = chk

        layout.addWidget(grp_content)

        # -- Artwork to Fetch ------------------------------------------
        grp_art = QGroupBox("Artwork to Fetch")
        g_a = QVBoxLayout(grp_art)
        g_a.setSpacing(6)

        self._scraper_artwork_checks: dict[str, QCheckBox] = {}
        for aid, label in SCRAPER_ARTWORK_LABELS.items():
            chk = QCheckBox(label)
            chk.setChecked(self._cfg.scraper_artwork.get(aid, False))
            chk.toggled.connect(self._mark_dirty)
            g_a.addWidget(chk)
            self._scraper_artwork_checks[aid] = chk

        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Max image resolution:"))
        self._scraper_res_combo = QComboBox()
        self._scraper_res_combo.addItems(["Original", "1080p", "720p", "480p"])
        self._scraper_res_combo.setCurrentText(self._cfg.scraper_max_resolution)
        self._scraper_res_combo.currentTextChanged.connect(self._mark_dirty)
        res_row.addWidget(self._scraper_res_combo, 1)
        g_a.addLayout(res_row)

        layout.addWidget(grp_art)

        # -- Behaviour -------------------------------------------------
        grp_beh = QGroupBox("Behaviour")
        g_b = QVBoxLayout(grp_beh)
        g_b.setSpacing(6)

        self._chk_auto_scrape = QCheckBox("Auto-scrape when new ROMs are found")
        self._chk_auto_scrape.setChecked(self._cfg.scraper_auto_scrape)
        self._chk_auto_scrape.toggled.connect(self._mark_dirty)
        g_b.addWidget(self._chk_auto_scrape)

        self._chk_overwrite = QCheckBox("Overwrite existing metadata")
        self._chk_overwrite.setChecked(self._cfg.scraper_overwrite)
        self._chk_overwrite.toggled.connect(self._mark_dirty)
        g_b.addWidget(self._chk_overwrite)

        self._chk_prefer_local = QCheckBox("Prefer local files over remote")
        self._chk_prefer_local.setChecked(self._cfg.scraper_prefer_local)
        self._chk_prefer_local.toggled.connect(self._mark_dirty)
        g_b.addWidget(self._chk_prefer_local)

        self._scraper_region_widget = QWidget()
        region_row = QHBoxLayout(self._scraper_region_widget)
        region_row.setContentsMargins(0, 0, 0, 0)
        region_row.setSpacing(6)
        region_row.addWidget(QLabel("Region priority:"))
        self._scraper_region_combo = QComboBox()
        self._scraper_region_combo.addItems(["USA", "Europe", "Japan", "World"])
        self._scraper_region_combo.setCurrentText(self._cfg.scraper_region_priority)
        self._scraper_region_combo.currentTextChanged.connect(self._mark_dirty)
        region_row.addWidget(self._scraper_region_combo, 1)
        g_b.addWidget(self._scraper_region_widget)

        self._scraper_rate_note = QLabel()
        self._scraper_rate_note.setObjectName("sectionLabel")
        self._scraper_rate_note.setWordWrap(True)
        g_b.addWidget(self._scraper_rate_note)

        layout.addWidget(grp_beh)

        layout.addStretch()

        # Wire source selector and trigger initial state
        self._scraper_combo.currentTextChanged.connect(
            self._on_scraper_source_changed
        )
        self._on_scraper_source_changed(self._scraper_combo.currentText())

        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(scroll_content)

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return outer

    def _on_scraper_source_changed(self, source_name: str):
        """Adapt all scraper UI sections to the newly selected source."""
        src = SCRAPER_SOURCE_MAP.get(source_name)
        if not src:
            return

        # Source URL
        t = active_theme()
        self._scraper_url_label.setText(
            f'<a href="{src.url}" style="color:{t.accent_primary};">'
            f'{src.url}</a>'
        )

        # Credential page
        idx = SCRAPER_SOURCE_NAMES.index(source_name)
        self._scraper_cred_stack.setCurrentIndex(idx)

        # Content checkboxes: enable supported, disable unsupported
        for cid, chk in self._scraper_content_checks.items():
            supported = cid in src.content
            chk.setEnabled(supported)
            if not supported:
                chk.setChecked(False)
                chk.setToolTip(f"Not available with {source_name}")
            else:
                chk.setToolTip("")

        # Artwork checkboxes: enable supported, disable unsupported
        for aid, chk in self._scraper_artwork_checks.items():
            supported = aid in src.artwork
            chk.setEnabled(supported)
            if not supported:
                chk.setChecked(False)
                chk.setToolTip(f"Not available with {source_name}")
            else:
                chk.setToolTip("")

        # Region priority
        self._scraper_region_widget.setVisible(src.supports_region_priority)

        # Rate-limit note
        if src.rate_limit_note:
            self._scraper_rate_note.setText(src.rate_limit_note)
            self._scraper_rate_note.setVisible(True)
        else:
            self._scraper_rate_note.setVisible(False)

        # Track active test button and refresh its state
        self._scraper_test_btn = self._scraper_test_btns.get(source_name)
        self._update_scraper_test_btn(source_name)
        self._mark_dirty()

    def _update_scraper_test_btn(self, source_name: str | None = None):
        """Enable the plug button for the given source (or the active source)."""
        if source_name is None:
            source_name = self._scraper_combo.currentText()
        src = SCRAPER_SOURCE_MAP.get(source_name)
        btn = self._scraper_test_btns.get(source_name) if hasattr(self, "_scraper_test_btns") else None
        if not btn:
            return
        if not src:
            btn.setEnabled(False)
            return
        if not src.auth_fields:
            btn.setEnabled(True)
            return
        inputs = self._scraper_cred_inputs.get(source_name, {})
        all_filled = all(le.text().strip() for le in inputs.values())
        btn.setEnabled(all_filled)

    def _on_test_scraper_connection(self):
        """Test the current scraper source's API connectivity.

        The plug-icon button turns green on success or red on failure,
        then resets to its normal colour after 2 seconds.
        """
        import urllib.request
        import urllib.parse
        import threading

        source_name = self._scraper_combo.currentText()
        src = SCRAPER_SOURCE_MAP.get(source_name)
        if not src:
            return

        btn = self._scraper_test_btns.get(source_name)
        if not btn:
            return

        btn.setEnabled(False)
        btn.setIcon(lucide_icon("plug", 14, active_theme().fg_disabled))
        QApplication.processEvents()

        inputs = self._scraper_cred_inputs.get(source_name, {})
        creds = {k: le.text().strip() for k, le in inputs.items()}

        result_holder: list = [None]

        def _worker():
            try:
                result_holder[0] = self._test_scraper_source(src, creds)
            except Exception as exc:
                result_holder[0] = (False, str(exc))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        while t.is_alive():
            QApplication.processEvents()
            t.join(timeout=0.016)

        ok, detail = result_holder[0] if result_holder[0] else (False, "No response")

        if ok:
            btn.setIcon(lucide_icon("plug", 14, "#2ecc71"))
            btn.setToolTip(f"Connected — {detail}")
        else:
            btn.setIcon(lucide_icon("plug", 14, "#e05252"))
            btn.setToolTip(f"Failed — {detail}")

        def _reset():
            if not btn or not hasattr(self, "_scraper_test_btns"):
                return
            t2 = active_theme()
            btn.setIcon(lucide_icon("plug", 14, t2.fg_disabled))
            btn.setToolTip("Test connection")
            self._update_scraper_test_btn(source_name)

        QTimer.singleShot(2000, _reset)

    def _test_scraper_source(
        self, src, creds: dict
    ) -> tuple[bool, str]:
        """Verify API connectivity and credentials. Returns (ok, detail_message).

        For sources that support hash-based matching, the test performs an
        actual hash lookup so the full scrape pipeline is validated.
        """
        import urllib.request
        import urllib.parse
        import json

        timeout = 12
        _UA = {"User-Agent": "Meridian/1.0"}

        def _get(url: str, headers: dict | None = None) -> tuple[int, str]:
            merged = {**_UA, **(headers or {})}
            req = urllib.request.Request(url, headers=merged, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.status, res.read().decode("utf-8", errors="replace")

        def _post(url: str, data: str = "", headers: dict | None = None) -> tuple[int, str]:
            merged = {**_UA, **(headers or {})}
            req = urllib.request.Request(
                url, data=data.encode("utf-8"), headers=merged, method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.status, res.read().decode("utf-8", errors="replace")

        # ── ScreenScraper ─────────────────────────────────────────────────
        if src.id == "screenscraper":
            # ssuserInfos validates credentials AND returns account info.
            params = urllib.parse.urlencode({
                "output": "json",
                "softname": "Meridian",
                "ssid": creds.get("username", ""),
                "sspassword": creds.get("password", ""),
            })
            try:
                status, body = _get(
                    f"https://api.screenscraper.fr/api2/ssuserInfos.php?{params}"
                )
                if status == 200:
                    try:
                        obj = json.loads(body)
                        ssuser = (obj.get("response") or {}).get("ssuser") or {}
                        uid = ssuser.get("id") or ssuser.get("login")
                        if uid:
                            req_today = ssuser.get("requeststoday", "?")
                            req_max = ssuser.get("maxrequestsperday", "?")
                            return True, f"Logged in as '{uid}'  ({req_today}/{req_max} requests today)"
                    except Exception:
                        pass
                    # body parsed but no user — likely bad credentials
                    if "wrongpassword" in body.lower() or "error" in body.lower():
                        return False, "Wrong username or password"
                    return True, "ScreenScraper reachable (verify credentials)"
                return False, f"HTTP {status}"
            except Exception as exc:
                return False, str(exc)

        # ── TheGamesDB ───────────────────────────────────────────────────
        if src.id == "thegamesdb":
            api_key = creds.get("api_key", "")
            params = urllib.parse.urlencode({"apikey": api_key, "name": "Mario", "fields": "id"})
            try:
                status, body = _get(f"https://api.thegamesdb.net/v1.1/Games/ByGameName?{params}")
                if status == 200:
                    try:
                        obj = json.loads(body)
                        remaining = (obj.get("extra") or {}).get("remaining_monthly_allowance")
                        if remaining is not None:
                            return True, f"TheGamesDB OK  ({remaining} requests remaining)"
                    except Exception:
                        pass
                    return True, "TheGamesDB OK"
                if status == 403:
                    return False, "Invalid API key"
                return False, f"HTTP {status}"
            except Exception as exc:
                return False, str(exc)

        # ── IGDB (Twitch OAuth) ──────────────────────────────────────────
        if src.id == "igdb":
            token_params = urllib.parse.urlencode({
                "client_id": creds.get("client_id", ""),
                "client_secret": creds.get("client_secret", ""),
                "grant_type": "client_credentials",
            })
            try:
                status, body = _post(f"https://id.twitch.tv/oauth2/token?{token_params}")
                obj = json.loads(body)
                token = obj.get("access_token", "")
                if token:
                    # Quick IGDB game search to verify the token actually works
                    hdrs = {
                        "Client-ID": creds.get("client_id", ""),
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Content-Type": "text/plain",
                    }
                    s2, b2 = _post(
                        "https://api.igdb.com/v4/games",
                        data='search "Mario"; fields name; limit 1;',
                        headers=hdrs,
                    )
                    if s2 == 200:
                        return True, "IGDB authenticated and query successful"
                    return True, "IGDB token obtained (query check failed)"
                msg = obj.get("message") or obj.get("error") or "Auth failed"
                return False, str(msg)
            except Exception as exc:
                return False, str(exc)

        # ── MobyGames ────────────────────────────────────────────────────
        if src.id == "mobygames":
            api_key = creds.get("api_key", "")
            params = urllib.parse.urlencode({"api_key": api_key, "title": "Mario", "limit": "1"})
            try:
                status, body = _get(f"https://api.mobygames.com/v1/games?{params}")
                if status == 200:
                    return True, "MobyGames OK"
                if status == 401:
                    return False, "Invalid API key"
                if status == 429:
                    return False, "Rate limited (free tier: 1 request / 5 s)"
                return False, f"HTTP {status}"
            except Exception as exc:
                return False, str(exc)

        # ── SteamGridDB ──────────────────────────────────────────────────
        if src.id == "steamgriddb":
            api_key = creds.get("api_key", "")
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
            try:
                status, body = _get(
                    f"https://www.steamgriddb.com/api/v2/search/autocomplete/"
                    f"{urllib.parse.quote('Mario')}",
                    headers=headers,
                )
                if status == 200:
                    return True, "SteamGridDB OK"
                if status == 401:
                    return False, "Invalid API key"
                return False, f"HTTP {status}"
            except Exception as exc:
                return False, str(exc)

        # ── PlayMatch ────────────────────────────────────────────────────
        if src.id == "playmatch":
            api_key = creds.get("api_key", "")
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
            params = urllib.parse.urlencode({"query": "Mario"})
            try:
                status, body = _get(
                    f"https://api.playmatch.gg/v1/games/search?{params}",
                    headers=headers,
                )
                if status == 200:
                    return True, "PlayMatch OK"
                if status == 401:
                    return False, "Invalid API key"
                return False, f"HTTP {status}"
            except Exception as exc:
                return False, str(exc)

        # ── Hasheous (hash-based — test with a real MD5 lookup) ──────────
        if src.id == "hasheous":
            # Use the MD5 of the well-known Donkey Kong (NES) to verify the
            # hash endpoint responds correctly (404 = not in DB but API works).
            test_md5 = "d0b6c6c6c6c6c6c6c6c6c6c6c6c6c6c6"  # deliberately unknown
            try:
                status, body = _get(
                    f"https://hasheous.org/api/v1/lookup/md5/{test_md5}",
                    headers={"Accept": "application/json"},
                )
                if status in (200, 404):
                    return True, "Hasheous reachable (hash endpoint responding)"
                return False, f"HTTP {status}"
            except Exception:
                pass
            # Fallback: plain reachability check
            try:
                status, _ = _get("https://hasheous.org/")
                return (status < 500), f"Hasheous {'reachable' if status < 500 else 'error'} (HTTP {status})"
            except Exception as exc:
                return False, str(exc)

        # ── No-auth sources — simple reachability ────────────────────────
        try:
            status, _ = _get(src.url)
            if status < 400:
                return True, f"{src.name} reachable (HTTP {status})"
            return False, f"HTTP {status}"
        except Exception as exc:
            return False, str(exc)

    def _tools_retroachievements(self) -> QWidget:
        return _coming_soon_page("RetroAchievements", "Achievement tracking and integration")

    def _tools_files(self) -> QWidget:
        """ROM integrity, duplicate detection, and library cleanup."""
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── Library Integrity ─────────────────────────────────────────────
        grp_int = QGroupBox("Library Integrity")
        g_int = QVBoxLayout(grp_int)
        g_int.setSpacing(8)

        lbl_int = QLabel(
            "Check that every ROM in your library still exists on disk. "
            "Missing files are listed below and can be removed from the library."
        )
        lbl_int.setObjectName("sectionLabel")
        lbl_int.setWordWrap(True)
        g_int.addWidget(lbl_int)

        row_int = QHBoxLayout()
        self._btn_verify_files = QPushButton("Verify Files")
        self._btn_verify_files.setFixedWidth(130)
        self._btn_verify_files.clicked.connect(self._on_file_verify)
        row_int.addWidget(self._btn_verify_files)
        self._btn_remove_missing = QPushButton("Remove Missing")
        self._btn_remove_missing.setFixedWidth(130)
        self._btn_remove_missing.setEnabled(False)
        self._btn_remove_missing.clicked.connect(self._on_remove_missing_files)
        row_int.addWidget(self._btn_remove_missing)
        row_int.addStretch()
        g_int.addLayout(row_int)

        self._file_verify_log = QPlainTextEdit()
        self._file_verify_log.setReadOnly(True)
        self._file_verify_log.setMaximumHeight(110)
        self._file_verify_log.setPlaceholderText("Click 'Verify Files' to check your library…")
        g_int.addWidget(self._file_verify_log)

        layout.addWidget(grp_int)

        # ── Duplicate Detection ───────────────────────────────────────────
        grp_dupe = QGroupBox("Duplicate Detection")
        g_dupe = QVBoxLayout(grp_dupe)
        g_dupe.setSpacing(8)

        lbl_dupe = QLabel(
            "Find likely duplicate ROMs using filename and file size "
            "(no hashing)."
        )
        lbl_dupe.setObjectName("sectionLabel")
        lbl_dupe.setWordWrap(True)
        g_dupe.addWidget(lbl_dupe)

        row_dupe = QHBoxLayout()
        self._btn_find_dupes = QPushButton("Find Duplicates")
        self._btn_find_dupes.setFixedWidth(130)
        self._btn_find_dupes.clicked.connect(self._on_find_duplicates)
        row_dupe.addWidget(self._btn_find_dupes)
        row_dupe.addStretch()
        g_dupe.addLayout(row_dupe)

        self._dupe_log = QPlainTextEdit()
        self._dupe_log.setReadOnly(True)
        self._dupe_log.setMaximumHeight(120)
        self._dupe_log.setPlaceholderText("Duplicate groups will appear here…")
        g_dupe.addWidget(self._dupe_log)

        layout.addWidget(grp_dupe)

        # ── Auto-Scan Behaviour ───────────────────────────────────────────
        grp_auto = QGroupBox("Auto-Scan Behaviour")
        g_auto = QVBoxLayout(grp_auto)
        g_auto.setSpacing(6)

        self._chk_verify_scan = QCheckBox("Verify files exist on every library scan")
        self._chk_verify_scan.setChecked(self._cfg.file_verify_on_scan)
        self._chk_verify_scan.toggled.connect(self._mark_dirty)
        g_auto.addWidget(self._chk_verify_scan)

        self._chk_auto_remove = QCheckBox("Auto-remove missing files from library")
        self._chk_auto_remove.setChecked(self._cfg.file_auto_remove_missing)
        self._chk_auto_remove.toggled.connect(self._mark_dirty)
        g_auto.addWidget(self._chk_auto_remove)

        layout.addWidget(grp_auto)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(scroll_content)

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return outer

    # ── File Management handlers ──────────────────────────────────────────

    def _fm_games(self):
        """Return the current game list from the parent main window."""
        return list(getattr(self.parent(), "_games", []))

    def _on_file_verify(self):
        """Check that all ROM files in the library exist on disk."""
        games = self._fm_games()
        if not games:
            self._file_verify_log.setPlainText(
                "No games in library. Run a library scan first (File > Scan)."
            )
            return

        self._btn_verify_files.setEnabled(False)
        self._file_verify_log.setPlainText(f"Verifying {len(games)} files…")
        QApplication.processEvents()

        missing = [str(g.path) for g in games if not g.path.exists()]
        valid = len(games) - len(missing)

        if missing:
            lines = [f"✓ {valid} valid   ✗ {len(missing)} missing\n", "Missing files:"]
            lines += [f"  • {p}" for p in missing[:60]]
            if len(missing) > 60:
                lines.append(f"  … and {len(missing) - 60} more")
            self._file_verify_log.setPlainText("\n".join(lines))
            self._btn_remove_missing.setEnabled(True)
            self._fm_missing_paths = set(missing)
        else:
            self._file_verify_log.setPlainText(f"✓ All {valid} ROM files are present.")
            self._btn_remove_missing.setEnabled(False)
            self._fm_missing_paths = set()

        self._btn_verify_files.setEnabled(True)

    def _on_remove_missing_files(self):
        """Remove library entries whose files no longer exist on disk."""
        missing = getattr(self, "_fm_missing_paths", set())
        if not missing:
            return
        main_win = self.parent()
        if not main_win or not hasattr(main_win, "_games"):
            return
        before = len(main_win._games)
        main_win._games = [g for g in main_win._games if str(g.path) not in missing]
        removed = before - len(main_win._games)
        if hasattr(main_win, "_refresh_games_view"):
            main_win._refresh_games_view()
        self._file_verify_log.setPlainText(
            f"Removed {removed} missing ROM(s) from the library view.\n"
            "Re-scan to restore if files reappear."
        )
        self._btn_remove_missing.setEnabled(False)
        self._fm_missing_paths = set()

    def _on_find_duplicates(self):
        """Find likely duplicate ROMs by (filename, size)."""
        import threading as _threading

        games = self._fm_games()
        if not games:
            self._dupe_log.setPlainText("No games in library. Run a library scan first.")
            return

        self._btn_find_dupes.setEnabled(False)
        self._dupe_log.setPlainText(f"Scanning {len(games)} ROMs for duplicates…")
        QApplication.processEvents()

        result_holder: list = [None]

        def _worker():
            dupe_map: dict[tuple[str, int], list] = {}
            for g in games:
                try:
                    stat = g.path.stat()
                    key = (g.path.name.lower(), int(stat.st_size))
                    dupe_map.setdefault(key, []).append(g)
                except Exception:
                    pass
            return {k: grp for k, grp in dupe_map.items() if len(grp) > 1}

        t = _threading.Thread(
            target=lambda: result_holder.__setitem__(0, _worker()), daemon=True
        )
        t.start()
        while t.is_alive():
            QApplication.processEvents()
            t.join(timeout=0.05)

        dupes: dict = result_holder[0] or {}
        if not dupes:
            self._dupe_log.setPlainText("✓ No duplicate ROMs found.")
        else:
            lines = [f"Found {len(dupes)} duplicate group(s):\n"]
            for (name, size), group in dupes.items():
                lines.append(f"  {name} [{size} bytes]  ({len(group)} copies):")
                for g in group:
                    lines.append(f"    • {g.path}")
            self._dupe_log.setPlainText("\n".join(lines))

        self._btn_find_dupes.setEnabled(True)

    def _tools_clock(self) -> QWidget:
        """Real-time clock settings — system, timezone, or manual."""
        import zoneinfo

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Real-Time Clock")
        g = QVBoxLayout(grp)
        g.setSpacing(10)

        hint = QLabel(
            "Configure the clock source used by emulators that depend "
            "on a real-time clock (e.g. Pok\u00e9mon day/night cycle)."
        )
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        g.addWidget(hint)

        # Source selector
        src_row = QHBoxLayout()
        src_row.setSpacing(8)
        src_row.addWidget(QLabel("Source:"))
        self._clock_source = QComboBox()
        self._clock_source.addItems([
            "System clock",
            "Selected timezone",
            "Fixed time",
        ])
        idx = self._clock_source.findText(self._cfg.clock_source)
        if idx >= 0:
            self._clock_source.setCurrentIndex(idx)
        self._clock_source.currentIndexChanged.connect(self._on_clock_source)
        self._clock_source.currentIndexChanged.connect(self._mark_dirty)
        src_row.addWidget(self._clock_source, 1)
        g.addLayout(src_row)

        # -- Timezone picker (visible when "Selected timezone") --------
        self._clock_tz_row = QHBoxLayout()
        self._clock_tz_row_widget = QWidget()
        tz_inner = QHBoxLayout(self._clock_tz_row_widget)
        tz_inner.setContentsMargins(0, 0, 0, 0)
        tz_inner.setSpacing(8)
        tz_inner.addWidget(QLabel("Timezone:"))
        self._clock_tz_combo = QComboBox()
        self._clock_tz_combo.setEditable(True)
        try:
            zones = sorted(zoneinfo.available_timezones())
        except Exception:
            zones = ["UTC"]
        self._clock_tz_combo.addItems(zones)
        saved_tz = self._cfg.clock_timezone or "UTC"
        idx = self._clock_tz_combo.findText(saved_tz)
        if idx >= 0:
            self._clock_tz_combo.setCurrentIndex(idx)
        self._clock_tz_combo.currentTextChanged.connect(self._mark_dirty)
        tz_inner.addWidget(self._clock_tz_combo, 1)
        g.addWidget(self._clock_tz_row_widget)

        # -- Fixed time pickers (visible when "Fixed time") ------------
        self._clock_fixed_widget = QWidget()
        fixed = QHBoxLayout(self._clock_fixed_widget)
        fixed.setContentsMargins(0, 0, 0, 0)
        fixed.setSpacing(12)

        fixed.addWidget(QLabel("Date:"))
        self._clock_date = QLineEdit(self._cfg.clock_fixed_date)
        self._clock_date.setPlaceholderText("YYYY-MM-DD")
        self._clock_date.textChanged.connect(self._mark_dirty)
        fixed.addWidget(self._clock_date, 1)

        fixed.addWidget(QLabel("Time:"))
        self._clock_time = QLineEdit(self._cfg.clock_fixed_time)
        self._clock_time.setPlaceholderText("HH:MM:SS")
        self._clock_time.textChanged.connect(self._mark_dirty)
        fixed.addWidget(self._clock_time, 1)

        g.addWidget(self._clock_fixed_widget)

        layout.addWidget(grp)

        # -- Display options -------------------------------------------
        grp2 = QGroupBox("Display")
        g2 = QVBoxLayout(grp2)
        g2.setSpacing(8)

        self._chk_clock_show = QCheckBox("Show clock in header")
        self._chk_clock_show.setChecked(self._cfg.show_clock)
        self._chk_clock_show.toggled.connect(self._mark_dirty)
        g2.addWidget(self._chk_clock_show)

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(8)
        fmt_row.addWidget(QLabel("Format:"))
        self._clock_fmt = QComboBox()
        self._clock_fmt.addItems(["12-hour", "24-hour"])
        fidx = self._clock_fmt.findText(self._cfg.clock_format)
        if fidx >= 0:
            self._clock_fmt.setCurrentIndex(fidx)
        self._clock_fmt.currentIndexChanged.connect(self._mark_dirty)
        fmt_row.addWidget(self._clock_fmt, 1)
        g2.addLayout(fmt_row)

        layout.addWidget(grp2)

        layout.addStretch()

        # Set initial visibility
        self._on_clock_source(self._clock_source.currentIndex())

        return w

    def _on_clock_source(self, index: int) -> None:
        """Show/hide clock sub-settings based on the selected source."""
        self._clock_tz_row_widget.setVisible(index == 1)   # timezone
        self._clock_fixed_widget.setVisible(index == 2)     # fixed time

    # -- Advanced ------------------------------------------------------

    def _page_advanced(self, sub: str) -> QWidget:
        if sub == "Debug":
            return self._adv_debug()
        if sub == "Experimental":
            return self._adv_experimental()
        return _placeholder(sub)

    def _adv_debug(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Logging")
        g = QVBoxLayout(grp)
        g.setSpacing(8)

        self._chk_debug_logging = QCheckBox("Enable debug logging")
        self._chk_debug_logging.setChecked(self._cfg.debug_logging)
        self._chk_debug_logging.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_debug_logging)

        self._chk_debug_emu_stdout = QCheckBox("Log emulator stdout / stderr to file")
        self._chk_debug_emu_stdout.setChecked(self._cfg.debug_log_emulator_stdout)
        self._chk_debug_emu_stdout.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_debug_emu_stdout)

        row_level = QHBoxLayout()
        row_level.addWidget(QLabel("Log level:"))
        self._combo_log_level = QComboBox()
        self._combo_log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._combo_log_level.setCurrentText(self._cfg.debug_log_level)
        self._combo_log_level.currentTextChanged.connect(self._mark_dirty)
        row_level.addWidget(self._combo_log_level)
        row_level.addStretch()
        g.addLayout(row_level)

        hint = QLabel("Verbose logging may impact performance. Changes take effect on next launch.")
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        g.addWidget(hint)

        layout.addWidget(grp)

        grp_diag = QGroupBox("Diagnostics")
        g_d = QVBoxLayout(grp_diag)
        g_d.setSpacing(8)

        self._chk_debug_fps = QCheckBox("Show FPS counter overlay")
        self._chk_debug_fps.setChecked(self._cfg.debug_show_fps)
        self._chk_debug_fps.toggled.connect(self._mark_dirty)
        g_d.addWidget(self._chk_debug_fps)

        self._chk_debug_borders = QCheckBox("Show widget debug borders")
        self._chk_debug_borders.setChecked(self._cfg.debug_show_widget_borders)
        self._chk_debug_borders.toggled.connect(self._mark_dirty)
        g_d.addWidget(self._chk_debug_borders)

        row_btns = QHBoxLayout()
        row_btns.setSpacing(8)

        btn_log = QPushButton("Open Log File")
        btn_log.setFixedWidth(130)
        btn_log.clicked.connect(self._on_open_log_file)
        row_btns.addWidget(btn_log)

        btn_crash = QPushButton("Open Crash Log")
        btn_crash.setFixedWidth(130)
        btn_crash.clicked.connect(self._on_open_crash_log)
        row_btns.addWidget(btn_crash)

        row_btns.addStretch()
        g_d.addLayout(row_btns)

        layout.addWidget(grp_diag)
        layout.addStretch()
        return w

    def _on_open_log_file(self):
        import os
        from pathlib import Path
        log_dir = Path(__file__).resolve().parent.parent.parent / "cache"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "meridian_debug.log"
        if log_file.exists():
            os.startfile(str(log_file))
        else:
            _msgbox.information(self, "Log File", "No debug log file found yet.\nEnable debug logging in the settings above to generate one.")

    def _on_open_crash_log(self):
        import os
        from pathlib import Path
        log_file = Path(__file__).resolve().parent.parent.parent / "cache" / "latest.log"
        if log_file.exists():
            os.startfile(str(log_file))
        else:
            _msgbox.information(self, "Crash Log", "No crash log found. This means Meridian has not encountered any unhandled exceptions.")

    def _adv_experimental(self) -> QWidget:
        return _coming_soon_page(
            "Experimental Features",
            "GPU-accelerated rendering, predictive ROM scanning, cloud save "
            "sync, and other cutting-edge features are under active development."
        )

    # ------------------------------------------------------------------
    # Emulator callbacks
    # ------------------------------------------------------------------

    def _on_add_emulator(self):
        dlg = _EmulatorEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            entry = dlg.result_entry()
            self._upsert_emulator(entry)
            self._refresh_installed_cards()
            self._populate_browse_catalog(self._browse_filter.currentData() or "")
            self._mark_dirty()

    def _on_edit_emulator(self):
        _msgbox.information(
            self,
            "Edit Emulator",
            "Use the emulator card settings button to edit an installed emulator.",
        )

    def _on_remove_emulator(self):
        _msgbox.information(
            self,
            "Remove Emulator",
            "Use the trash icon on an emulator card to remove it.",
        )

    # ------------------------------------------------------------------
    # Save / cancel
    # ------------------------------------------------------------------

    def _on_save(self):
        # Only read widgets from pages that have actually been built.
        # Unvisited pages keep whatever values were in the original config.

        # General  (page 0)
        if hasattr(self, "_chk_maximized"):
            self._cfg.start_maximized = self._chk_maximized.isChecked()
            self._cfg.confirm_on_exit = self._chk_confirm_exit.isChecked()

        # UI  (page 0, sub-tab 1)
        if hasattr(self, "_theme_combo"):
            self._cfg.theme = self._theme_combo.currentText()
            self._cfg.system_logo_set = self._logo_set_combo.currentText()
        if hasattr(self, "_chk_show_game_icons"):
            self._cfg.show_game_icons = self._chk_show_game_icons.isChecked()
            self._cfg.show_system_logos = self._chk_show_system_logos.isChecked()
            self._cfg.show_file_extensions = self._chk_show_ext.isChecked()
            self._cfg.sort_default = self._combo_default_sort.currentText()
        if hasattr(self, "_theme_combo"):
            self._cfg.font_family = self._font_combo.currentText()
            self._cfg.font_size_label = self._fontsize_combo.currentText()
            self._cfg.bold_text = self._chk_bold.isChecked()
            self._cfg.reduced_motion = self._chk_reduced.isChecked()
            self._cfg.high_contrast = self._chk_high_contrast.isChecked()
            # Background
            self._cfg.bg_type = self._bg_type_combo.currentText()
            self._cfg.bg_image_path = self._bg_image_path.text()
            self._cfg.bg_animation = self._bg_anim_combo.currentText()

        # Graphics  (page 1)
        if hasattr(self, "_chk_remember_geom"):
            self._cfg.remember_window_geometry = self._chk_remember_geom.isChecked()
            self._cfg.borderless_fullscreen = self._chk_borderless.isChecked()
        if hasattr(self, "_combo_anim_speed"):
            self._cfg.ui_animation_speed = self._combo_anim_speed.currentText()
            self._cfg.smooth_scrolling = self._chk_smooth_scroll.isChecked()
            self._cfg.list_transition_style = self._combo_transition.currentText()
        if hasattr(self, "_chk_vsync"):
            self._cfg.vsync = self._chk_vsync.isChecked()
            self._cfg.gpu_accelerated_ui = self._chk_gpu_ui.isChecked()
        if hasattr(self, "_combo_text_render"):
            self._cfg.text_rendering = self._combo_text_render.currentText()
            self._cfg.image_scaling = self._combo_image_scale.currentText()
            self._cfg.icon_size = self._combo_icon_size.currentData() or 48

        # Performance  (page 2)
        if hasattr(self, "_chk_limit_bg_cpu"):
            self._cfg.limit_background_cpu = self._chk_limit_bg_cpu.isChecked()
            self._cfg.scan_threads = self._spin_threads.value()
            self._cfg.background_fps = self._spin_bg_fps.value()
            self._cfg.gpu_backend = self._combo_gpu_backend.currentText()
        if hasattr(self, "_spin_fg_fps"):
            self._cfg.foreground_fps = self._spin_fg_fps.value()
        if hasattr(self, "_chk_lazy_load"):
            self._cfg.lazy_load_artwork = self._chk_lazy_load.isChecked()
            self._cfg.prefetch_adjacent = self._chk_prefetch.isChecked()
            self._cfg.preload_emulator_configs = self._chk_preload_emu.isChecked()
            self._cfg.max_loaded_images = self._spin_max_imgs.value()
        if hasattr(self, "_chk_cache_art"):
            self._cfg.cache_box_art = self._chk_cache_art.isChecked()
            self._cfg.cache_metadata = self._chk_cache_meta.isChecked()
            self._cfg.cache_max_mb = self._spin_cache_mb.value()
            self._cfg.thumbnail_resolution = self._combo_thumb_res.currentText()

        # Audio  (page 3)
        if hasattr(self, "_audio_out_combo"):
            self._cfg.audio_output_device = self._audio_out_combo.currentText()
            self._cfg.audio_input_device = self._audio_in_combo.currentText()
            self._cfg.audio_channel_mode = self._audio_channel_combo.currentText()
        if hasattr(self, "_audio_vol_slider"):
            self._cfg.audio_volume = self._audio_vol_slider.value()
            self._cfg.audio_mute = self._chk_mute.isChecked()
            self._cfg.audio_mute_background = self._chk_mute_bg.isChecked()
            self._cfg.audio_mute_unfocused_emu = self._chk_mute_unfocused.isChecked()
        if hasattr(self, "_chk_ambient_enabled"):
            self._cfg.ambient_audio_enabled = self._chk_ambient_enabled.isChecked()
            self._cfg.ambient_audio_volume = self._ambient_vol_slider.value()

        # Input  (page 4)
        if hasattr(self, "_input_player_controls"):
            self._cfg.input_player_settings = self._collect_input_player_settings()
        if hasattr(self, "_chk_gamepad_nav"):
            self._cfg.input_gamepad_nav = self._chk_gamepad_nav.isChecked()
            self._cfg.input_vibration = self._chk_global_vibration.isChecked()
            self._cfg.input_motion = self._chk_global_motion.isChecked()
            self._cfg.input_focus_only = self._chk_input_on_focus.isChecked()

        # Emulator BIOS files  (page 5 / Emulators > Configuration)
        if hasattr(self, "_bios_path_inputs"):
            bios_paths: dict[str, str] = {}
            for bios_id, le in self._bios_path_inputs.items():
                path = le.text().strip()
                if path:
                    bios_paths[bios_id] = path
            self._cfg.bios_files = bios_paths

        # Networking  (page 6)
        if hasattr(self, "_chk_multiplayer_enabled"):
            self._cfg.multiplayer_enabled = self._chk_multiplayer_enabled.isChecked()
            self._cfg.multiplayer_username = self._net_username.text().strip() or "Player"
            self._cfg.multiplayer_port = self._net_port.value()
            self._cfg.multiplayer_directory_url = self._net_directory_url.text().strip()
            self._cfg.multiplayer_preferred_region = self._net_region.currentText()
            self._cfg.multiplayer_auto_refresh_seconds = self._net_auto_refresh.value()
            self._cfg.multiplayer_show_full_rooms = self._chk_show_full_rooms.isChecked()
        if hasattr(self, "_chk_retroarch_auto_update"):
            self._cfg.retroarch_auto_update = self._chk_retroarch_auto_update.isChecked()
        if hasattr(self, "_chk_updates_startup"):
            self._cfg.updates_check_on_startup = self._chk_updates_startup.isChecked()
            self._cfg.updates_include_prerelease = self._chk_updates_prerelease.isChecked()

        # Scraper  (page 7)
        if hasattr(self, "_scraper_combo"):
            self._cfg.scraper_source = self._scraper_combo.currentText()
            creds: dict[str, dict[str, str]] = {}
            for src_name, fields in self._scraper_cred_inputs.items():
                if fields:
                    creds[src_name] = {k: le.text() for k, le in fields.items()}
            self._cfg.scraper_credentials = creds
            self._cfg.scraper_content = {
                cid: chk.isChecked()
                for cid, chk in self._scraper_content_checks.items()
            }
            self._cfg.scraper_artwork = {
                aid: chk.isChecked()
                for aid, chk in self._scraper_artwork_checks.items()
            }
            self._cfg.scraper_max_resolution = self._scraper_res_combo.currentText()
            self._cfg.scraper_auto_scrape = self._chk_auto_scrape.isChecked()
            self._cfg.scraper_overwrite = self._chk_overwrite.isChecked()
            self._cfg.scraper_prefer_local = self._chk_prefer_local.isChecked()
            self._cfg.scraper_region_priority = self._scraper_region_combo.currentText()

        # File Management  (Tools > File Management)
        if hasattr(self, "_chk_verify_scan"):
            self._cfg.file_verify_on_scan = self._chk_verify_scan.isChecked()
        if hasattr(self, "_chk_auto_remove"):
            self._cfg.file_auto_remove_missing = self._chk_auto_remove.isChecked()

        # Clock  (page 7 — Tools > Clock)
        if hasattr(self, "_chk_clock_show"):
            self._cfg.show_clock = self._chk_clock_show.isChecked()
            self._cfg.clock_source = self._clock_source.currentText()
            self._cfg.clock_timezone = self._clock_tz_combo.currentText()
            self._cfg.clock_fixed_date = self._clock_date.text()
            self._cfg.clock_fixed_time = self._clock_time.text()
            self._cfg.clock_format = self._clock_fmt.currentText()

        # Debug  (page 8)
        if hasattr(self, "_chk_debug_logging"):
            self._cfg.debug_logging = self._chk_debug_logging.isChecked()
            self._cfg.debug_show_fps = self._chk_debug_fps.isChecked()
            self._cfg.debug_log_emulator_stdout = self._chk_debug_emu_stdout.isChecked()
            self._cfg.debug_log_level = self._combo_log_level.currentText()
            self._cfg.debug_show_widget_borders = self._chk_debug_borders.isChecked()

        # Only rebuild the stylesheet when a visual setting actually changed —
        # re-applying an identical stylesheet can still cause Qt to re-layout
        # and shift font metrics / density.
        o = self._original_cfg
        visual_changed = (
            self._cfg.theme != o.theme
            or self._cfg.ui_scale != o.ui_scale
            or self._cfg.font_family != o.font_family
            or self._cfg.font_size_label != o.font_size_label
            or self._cfg.bold_text != o.bold_text
            or self._cfg.high_contrast != o.high_contrast
        )
        if visual_changed:
            set_theme(self._cfg.theme)
            set_density(self._cfg.ui_scale)
            app = QApplication.instance()
            if app:
                app.setStyleSheet(build_stylesheet(
                    bold=self._cfg.bold_text,
                    font_size_label=self._cfg.font_size_label,
                    font_override=self._cfg.font_family,
                    high_contrast=self._cfg.high_contrast,
                ))

        # Apply rendering settings (text AA, animation speed)
        from meridian.app import apply_rendering_settings
        apply_rendering_settings(self._cfg)

        self._cfg.save()
        self._original_cfg = copy.deepcopy(self._cfg)
        self._dirty = False
        self._btn_save.setEnabled(False)

        # Push background / palette changes to the main window live
        main_window = self.parent()
        if main_window and hasattr(main_window, 'apply_config'):
            main_window.apply_config(self._cfg)

    def saved_config(self) -> Config:
        return self._cfg


# ======================================================================
# Emulator add / edit sub-dialog
# ======================================================================

class _EmulatorEditDialog(QDialog):
    """Small modal for adding or editing a single emulator entry."""

    def __init__(self, entry: EmulatorEntry | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Emulator" if entry else "Add Emulator")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self._txt_name = QLineEdit()
        self._txt_name.setPlaceholderText("e.g. RetroArch, Dolphin, PCSX2")
        form.addRow("Name:", self._txt_name)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._txt_path = QLineEdit()
        self._txt_path.setPlaceholderText("Path to emulator executable")
        path_row.addWidget(self._txt_path, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._on_browse)
        path_row.addWidget(btn_browse)
        form.addRow("Executable:", path_row)

        self._txt_args = QLineEdit()
        self._txt_args.setPlaceholderText('e.g. -L "cores/bsnes.dll" "{rom}"')
        form.addRow("Arguments:", self._txt_args)

        hint = QLabel(
            '<span style="color:#6E7A8A; font-size:8pt;">'
            "Use <b>{rom}</b> as a placeholder for the ROM file path.</span>"
        )
        form.addRow("", hint)
        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primaryButton")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("cancelButton")
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        if entry:
            self._txt_name.setText(entry.name)
            self._txt_path.setText(entry.path)
            self._txt_args.setText(entry.args)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Emulator Executable",
            "", "Executables (*.exe);;All Files (*)",
        )
        if path:
            self._txt_path.setText(path)

    def _on_ok(self):
        if not self._txt_name.text().strip():
            _msgbox.warning(self, "Validation", "Emulator name is required.")
            self._txt_name.setFocus()
            return
        if not self._txt_path.text().strip():
            _msgbox.warning(self, "Validation", "Executable path is required.")
            self._txt_path.setFocus()
            return
        self.accept()

    def result_entry(self) -> EmulatorEntry:
        return EmulatorEntry(
            name=self._txt_name.text().strip(),
            path=self._txt_path.text().strip(),
            args=self._txt_args.text().strip() or '"{rom}"',
        )


# ======================================================================
# Per-emulator settings dialog  (cog icon)
# ======================================================================

class _EmulatorSettingsDialog(QDialog):
    """Settings for one specific installed emulator."""

    def __init__(self, entry: EmulatorEntry, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{entry.display_name()} \u2014 Settings")
        self.setMinimumSize(520, 520)

        self._entry = entry
        self._cfg = config

        catalog = emulator_catalog_entry(entry.catalog_id or entry.name)
        self._is_retroarch_core = bool(
            catalog and catalog.install_strategy == "retroarch_core"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # -- Paths -----------------------------------------------------
        grp_paths = QGroupBox("Paths")
        g_p = QFormLayout(grp_paths)
        g_p.setSpacing(8)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._txt_exe = QLineEdit(entry.path)
        self._txt_exe.setPlaceholderText("Path to executable")
        path_row.addWidget(self._txt_exe, 1)
        btn_b = QPushButton("Browse...")
        btn_b.setFixedWidth(80)
        btn_b.clicked.connect(self._on_browse_exe)
        path_row.addWidget(btn_b)
        g_p.addRow("Executable:", path_row)

        self._txt_args = QLineEdit(entry.args)
        self._txt_args.setPlaceholderText('"{rom}"')
        g_p.addRow("Launch args:", self._txt_args)

        rom_row = QHBoxLayout()
        rom_row.setSpacing(6)
        self._txt_rom_dir = QLineEdit(entry.rom_directory)
        self._txt_rom_dir.setPlaceholderText("Default ROM directory for this emulator (optional)")
        rom_row.addWidget(self._txt_rom_dir, 1)
        btn_b2 = QPushButton("Browse...")
        btn_b2.setFixedWidth(80)
        btn_b2.clicked.connect(self._on_browse_rom_dir)
        rom_row.addWidget(btn_b2)
        g_p.addRow("ROM directory:", rom_row)

        layout.addWidget(grp_paths)

        # -- Graphics --------------------------------------------------
        grp_gfx = QGroupBox("Graphics")
        g_g = QVBoxLayout(grp_gfx)
        g_g.setSpacing(8)

        self._chk_fullscreen = QCheckBox("Pass fullscreen flag on launch")
        self._chk_fullscreen.setChecked(entry.fullscreen_on_launch)
        g_g.addWidget(self._chk_fullscreen)

        self._chk_exclusive_fs = QCheckBox("Use exclusive fullscreen")
        self._chk_exclusive_fs.setChecked(entry.exclusive_fullscreen)
        g_g.addWidget(self._chk_exclusive_fs)

        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Resolution override:"))
        self._combo_resolution = QComboBox()
        self._combo_resolution.addItems(["Default", "720p", "1080p", "1440p", "4K"])
        self._combo_resolution.setCurrentText(entry.resolution_override)
        res_row.addWidget(self._combo_resolution, 1)
        g_g.addLayout(res_row)

        layout.addWidget(grp_gfx)

        # -- Input / Controls ------------------------------------------
        grp_input = QGroupBox("Input / Controls")
        g_i = QVBoxLayout(grp_input)
        g_i.setSpacing(8)

        if self._is_retroarch_core:
            note = QLabel(
                "All RetroArch cores share the same controller profile "
                "because they all run through RetroArch."
            )
            note.setObjectName("sectionLabel")
            note.setWordWrap(True)
            g_i.addWidget(note)

        profile_row = QHBoxLayout()
        profile_row.setSpacing(6)
        profile_row.addWidget(QLabel("Controller profile:"))
        self._combo_profile = QComboBox()
        self._refresh_profile_combo()
        profile_row.addWidget(self._combo_profile, 1)

        btn_edit = QPushButton("Edit\u2026")
        btn_edit.setFixedWidth(60)
        btn_edit.setToolTip("Edit the selected controller profile")
        btn_edit.clicked.connect(self._on_edit_profile)
        profile_row.addWidget(btn_edit)

        btn_new = QPushButton("New\u2026")
        btn_new.setFixedWidth(60)
        btn_new.setToolTip("Create a new controller profile")
        btn_new.clicked.connect(self._on_new_profile)
        profile_row.addWidget(btn_new)

        btn_del = QPushButton("Delete")
        btn_del.setFixedWidth(60)
        btn_del.setToolTip("Delete the selected controller profile")
        btn_del.clicked.connect(self._on_delete_profile)
        profile_row.addWidget(btn_del)
        self._btn_del_profile = btn_del

        g_i.addLayout(profile_row)

        profile_hint = QLabel(
            "\u201cGlobal\u201d uses the bindings from Settings \u2192 Input. "
            "Custom profiles let you set per-emulator controller mappings."
        )
        profile_hint.setObjectName("sectionLabel")
        profile_hint.setWordWrap(True)
        g_i.addWidget(profile_hint)

        layout.addWidget(grp_input)

        # -- Behaviour -------------------------------------------------
        grp_beh = QGroupBox("Behaviour")
        g_b = QVBoxLayout(grp_beh)
        g_b.setSpacing(8)

        self._chk_close_meridian = QCheckBox("Close Meridian while running")
        self._chk_close_meridian.setChecked(entry.close_meridian_on_launch)
        g_b.addWidget(self._chk_close_meridian)

        self._chk_auto_save = QCheckBox("Auto-save state on exit")
        self._chk_auto_save.setChecked(entry.auto_save_state)
        g_b.addWidget(self._chk_auto_save)

        layout.addWidget(grp_beh)

        layout.addStretch()

        # -- Buttons ---------------------------------------------------
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("cancelButton")
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._combo_profile.currentIndexChanged.connect(self._on_profile_selection_changed)
        self._on_profile_selection_changed()

    # -- Profile combo helpers -----------------------------------------

    def _refresh_profile_combo(self):
        self._combo_profile.blockSignals(True)
        self._combo_profile.clear()
        self._combo_profile.addItem("Global")
        for name in sorted(self._cfg.controller_profiles.keys()):
            self._combo_profile.addItem(name)

        current = self._entry.controller_profile or "Global"
        if self._is_retroarch_core and current == "Global":
            current = "RetroArch"
        idx = self._combo_profile.findText(current)
        if idx < 0:
            if self._is_retroarch_core:
                self._cfg.controller_profiles.setdefault("RetroArch", {})
                self._combo_profile.addItem("RetroArch")
                idx = self._combo_profile.findText("RetroArch")
            else:
                idx = 0
        self._combo_profile.setCurrentIndex(idx)
        self._combo_profile.blockSignals(False)

    def _on_profile_selection_changed(self):
        name = self._combo_profile.currentText()
        self._btn_del_profile.setEnabled(name != "Global")

    # -- Profile management --------------------------------------------

    def _on_edit_profile(self):
        name = self._combo_profile.currentText()
        if name == "Global":
            data = copy.deepcopy(self._cfg.input_player_settings)
        else:
            data = copy.deepcopy(self._cfg.controller_profiles.get(name, {}))

        dlg = _ControllerProfileEditorDialog(name, data, self._cfg, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.profile_data()
            if name == "Global":
                self._cfg.input_player_settings = result
            else:
                self._cfg.controller_profiles[name] = result

    def _on_new_profile(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "New Controller Profile", "Profile name:",
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if name == "Global":
            _msgbox.warning(self, "Invalid Name", '"Global" is reserved.')
            return
        if name in self._cfg.controller_profiles:
            _msgbox.warning(
                self, "Duplicate",
                f'A profile named "{name}" already exists.',
            )
            return
        self._cfg.controller_profiles[name] = copy.deepcopy(
            self._cfg.input_player_settings
        )
        self._refresh_profile_combo()
        idx = self._combo_profile.findText(name)
        if idx >= 0:
            self._combo_profile.setCurrentIndex(idx)

    def _on_delete_profile(self):
        name = self._combo_profile.currentText()
        if name == "Global":
            return
        confirm = _msgbox.question(
            self,
            "Delete Profile",
            f'Delete controller profile "{name}"?\n\n'
            "Emulators using it will revert to Global.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._cfg.controller_profiles.pop(name, None)
        for emu in self._cfg.emulators:
            if emu.controller_profile == name:
                emu.controller_profile = "Global"
        self._refresh_profile_combo()

    # -- Browse helpers ------------------------------------------------

    def _on_browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Emulator Executable",
            "", "Executables (*.exe);;All Files (*)",
        )
        if path:
            self._txt_exe.setText(path)

    def _on_browse_rom_dir(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Default ROM Directory",
            self._txt_rom_dir.text().strip() or "",
        )
        if path:
            self._txt_rom_dir.setText(path)

    # -- Save ----------------------------------------------------------

    def _on_save(self):
        self._entry.path = self._txt_exe.text().strip()
        self._entry.args = self._txt_args.text().strip() or '"{rom}"'
        self._entry.rom_directory = self._txt_rom_dir.text().strip()
        self._entry.fullscreen_on_launch = self._chk_fullscreen.isChecked()
        self._entry.exclusive_fullscreen = self._chk_exclusive_fs.isChecked()
        self._entry.resolution_override = self._combo_resolution.currentText()
        self._entry.close_meridian_on_launch = self._chk_close_meridian.isChecked()
        self._entry.auto_save_state = self._chk_auto_save.isChecked()

        chosen_profile = self._combo_profile.currentText()
        self._entry.controller_profile = chosen_profile

        if self._is_retroarch_core:
            for emu in self._cfg.emulators:
                cat = emulator_catalog_entry(emu.catalog_id or emu.name)
                if cat and cat.install_strategy == "retroarch_core":
                    emu.controller_profile = chosen_profile

        self.accept()


# ======================================================================
# Controller profile editor dialog
# ======================================================================


class _ControllerProfileEditorDialog(QDialog):
    """Full controller profile editor with per-player tabs.

    Mirrors the main Input page but operates on a standalone profile dict
    instead of the global ``input_player_settings``.
    """

    _MAX_PLAYERS = 4

    def __init__(
        self,
        profile_name: str,
        profile_data: dict,
        config: Config,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Controller Profile \u2014 {profile_name}")
        self.setMinimumSize(700, 540)
        self.resize(760, 580)

        self._name = profile_name
        self._data = profile_data
        self._cfg = config

        from meridian.core.input_manager import InputManager
        self._input_mgr = InputManager.instance()
        self._input_mgr.ensure_ready()

        self._player_controls: dict[int, dict[str, object]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(
            f"Editing bindings for profile <b>{profile_name}</b>. "
            "Changes take effect when you save."
        )
        header.setObjectName("sectionLabel")
        header.setWordWrap(True)
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.setObjectName("subTabs")
        for p in range(1, self._MAX_PLAYERS + 1):
            tabs.addTab(self._build_player_tab(p), f"Player {p}")
        layout.addWidget(tabs, 1)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("cancelButton")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def profile_data(self) -> dict:
        """Return the edited profile data (call after ``Accepted``)."""
        result = copy.deepcopy(self._data)
        for num, ctrl_map in self._player_controls.items():
            chk = ctrl_map.get("connected")
            api = ctrl_map.get("api")
            dev = ctrl_map.get("device")
            typ = ctrl_map.get("type")
            if not all(isinstance(w, (QCheckBox, QComboBox)) for w in [chk, api, dev, typ]):
                continue
            bindings_map: dict[str, str] = {}
            bind_buttons = ctrl_map.get("bindings")
            if isinstance(bind_buttons, dict):
                for key, btn in bind_buttons.items():
                    if hasattr(btn, "text"):
                        val = btn.text().strip()
                        if val and val != "Listening \u2026":
                            bindings_map[key] = val
            result[str(num)] = {
                "connected": chk.isChecked(),
                "api": api.currentText(),
                "device": dev.currentText(),
                "device_index": (
                    int(dev.currentData())
                    if isinstance(dev.currentData(), int) and dev.currentData() >= 0
                    else None
                ),
                "type": typ.currentText(),
                "bindings": bindings_map,
            }
        return result

    # -- Player tab builder --------------------------------------------

    def _build_player_tab(self, num: int) -> QWidget:
        saved = self._data.get(str(num), {})
        saved_bindings = saved.get("bindings", {})
        defs = saved_bindings if saved_bindings else (
            _PLAYER1_BINDINGS if num == 1 else {}
        )
        mgr = self._input_mgr

        bindings: dict[str, _BindButton] = {}

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)

        chk = QCheckBox("Connected")
        chk.setChecked(bool(saved.get("connected", num == 1)))

        def _on_connected(on: bool):
            body.setEnabled(on)
        chk.toggled.connect(_on_connected)
        top.addWidget(chk)

        top.addWidget(QLabel("API:"))
        api = QComboBox()
        api.addItems(["XInput", "DirectInput", "SDL"])
        api.setMinimumWidth(80)
        saved_api = str(saved.get("api", "SDL"))
        if saved_api == "Auto":
            saved_api = "SDL"
        api.setCurrentIndex(max(api.findText(saved_api), 0))
        top.addWidget(api)

        top.addWidget(QLabel("Device:"))
        dev = QComboBox()
        dev.addItem("None", None)
        dev.addItem("Keyboard + Mouse", "keyboard")
        dev.addItem("Any Available", "any")
        for c in mgr.controllers():
            dev.addItem(c.name, c.index)
        saved_dev = str(saved.get("device", "Any Available"))
        idx = dev.findText(saved_dev)
        dev.setCurrentIndex(idx if idx >= 0 else dev.findText("Any Available"))
        dev.setMinimumWidth(100)
        top.addWidget(dev, 1)

        top.addWidget(QLabel("Type:"))
        tcombo = QComboBox()
        tcombo.addItems([
            "Pro Controller", "Gamepad", "Xbox Controller", "DualShock",
            "DualSense", "GameCube", "N64 Controller",
            "Joy-Con (L+R)", "Joy-Con (Single)",
            "Wii Remote", "Wii Remote + Nunchuk", "Classic Controller",
            "Fight Stick", "Steering Wheel", "Custom",
        ])
        tcombo.setMinimumWidth(100)
        saved_type = str(saved.get("type", "Pro Controller"))
        tcombo.setCurrentIndex(max(tcombo.findText(saved_type), 0))
        top.addWidget(tcombo, 1)

        layout.addLayout(top)

        def _get_device() -> str:
            return dev.currentText()

        def _get_device_index() -> int | None:
            data = dev.currentData()
            return data if isinstance(data, int) and data >= 0 else None

        binds_container = QWidget()
        binds_layout = QVBoxLayout(binds_container)
        binds_layout.setContentsMargins(0, 0, 0, 0)
        binds_layout.setSpacing(6)

        def _rebuild():
            old_values: dict[str, str] = {}
            for key, btn in bindings.items():
                val = btn.text().strip()
                if val and val != "Listening \u2026":
                    old_values[key] = val
            bindings.clear()
            while binds_layout.count():
                item = binds_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    _clear_layout(item.layout())

            type_name = tcombo.currentText()
            sections = _CONTROLLER_LAYOUTS.get(
                type_name, _CONTROLLER_LAYOUTS["Pro Controller"]
            )
            for section_title, bind_defs in sections:
                binds_layout.addWidget(_section_label(section_title))
                for key, label in bind_defs:
                    saved_val = old_values.get(key) or defs.get(key, "")
                    btn = _BindButton(
                        saved_val,
                        device_fn=_get_device,
                        device_index_fn=_get_device_index,
                    )
                    bindings[key] = btn
                    binds_layout.addLayout(_bind_row(label, btn))

        tcombo.currentIndexChanged.connect(lambda _: _rebuild())
        _rebuild()

        body_layout.addWidget(binds_container)
        body_layout.addStretch()

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        bottom.addStretch()
        btn_def = QPushButton(" Defaults ")

        def _on_defaults():
            target = _PLAYER1_BINDINGS if num == 1 else {}
            for key, btn in bindings.items():
                btn.set_binding(target.get(key, ""))
        btn_def.clicked.connect(_on_defaults)
        bottom.addWidget(btn_def)

        btn_clr = QPushButton(" Clear ")

        def _on_clear():
            for btn in bindings.values():
                btn.set_binding("")
        btn_clr.clicked.connect(_on_clear)
        bottom.addWidget(btn_clr)
        body_layout.addLayout(bottom)

        layout.addWidget(body, 1)
        body.setEnabled(chk.isChecked())

        self._player_controls[num] = {
            "connected": chk,
            "api": api,
            "device": dev,
            "type": tcombo,
            "bindings": bindings,
        }

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(scroll_content)
        return scroll


# ======================================================================
# Helpers
# ======================================================================

def _placeholder(name: str) -> QWidget:
    """Fallback empty tab."""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(20, 20, 20, 20)
    lbl = QLabel(f"{name} settings will appear here.")
    lbl.setObjectName("sectionLabel")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)
    return w


def _coming_soon_page(title: str, description: str) -> QWidget:
    """Page placeholder for features that are not yet implemented."""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(40, 40, 40, 40)
    layout.addStretch()

    icon_lbl = QLabel("🚧")
    icon_lbl.setStyleSheet("font-size: 32pt; background: transparent;")
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_lbl)

    heading = QLabel(f"<b>{title}</b>")
    heading.setStyleSheet("font-size: 14pt; background: transparent;")
    heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(heading)

    sub = QLabel("Coming Soon")
    sub.setObjectName("sectionLabel")
    sub.setStyleSheet("font-size: 11pt; background: transparent;")
    sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(sub)

    desc = QLabel(description)
    desc.setObjectName("sectionLabel")
    desc.setWordWrap(True)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc)

    layout.addStretch()
    return w


def _disabled_check(text: str, checked: bool = False) -> QCheckBox:
    """Create a disabled checkbox placeholder."""
    cb = QCheckBox(text)
    cb.setChecked(checked)
    cb.setEnabled(False)
    return cb


# ======================================================================
# Controller mapping helpers
# ======================================================================

_PLAYER1_BINDINGS: dict[str, str] = {
    "ls_up": "Axis 1-", "ls_down": "Axis 1+",
    "ls_left": "Axis 0-", "ls_right": "Axis 0+",
    "ls_press": "Button 7",
    "rs_up": "Axis 3-", "rs_down": "Axis 3+",
    "rs_left": "Axis 2-", "rs_right": "Axis 2+",
    "rs_press": "Button 8",
    "dp_up": "Button 11", "dp_down": "Button 12",
    "dp_left": "Button 13", "dp_right": "Button 14",
    "a": "Button 1", "b": "Button 0",
    "x": "Button 3", "y": "Button 2",
    "l": "Button 9", "r": "Button 10",
    "zl": "Axis 4+", "zr": "Axis 5+",
    "minus": "Button 4", "plus": "Button 6",
    "capture": "Button 15", "home": "Button 5",
    "motion": "Gyro",
}


# Per-controller-type button layouts.
# Each entry is a list of (section_title, [(bind_key, display_label), ...]).
_CONTROLLER_LAYOUTS: dict[str, list[tuple[str, list[tuple[str, str]]]]] = {
    "Pro Controller": [
        ("Face Buttons", [("a", "A"), ("b", "B"), ("x", "X"), ("y", "Y")]),
        ("Shoulders", [("l", "L"), ("r", "R"), ("zl", "ZL"), ("zr", "ZR")]),
        ("Menu", [("plus", "Start / +"), ("minus", "Select / \u2212"), ("home", "Home"), ("capture", "Capture")]),
        ("Left Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right"), ("ls_press", "Pressed")]),
        ("Right Stick", [("rs_up", "Up"), ("rs_down", "Down"), ("rs_left", "Left"), ("rs_right", "Right"), ("rs_press", "Pressed")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
    "Xbox Controller": [
        ("Face Buttons", [("a", "A"), ("b", "B"), ("x", "X"), ("y", "Y")]),
        ("Shoulders", [("lb", "LB"), ("rb", "RB"), ("lt", "LT"), ("rt", "RT")]),
        ("Menu", [("start", "Menu"), ("back", "View"), ("guide", "Xbox")]),
        ("Left Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right"), ("ls_press", "LS Click")]),
        ("Right Stick", [("rs_up", "Up"), ("rs_down", "Down"), ("rs_left", "Left"), ("rs_right", "Right"), ("rs_press", "RS Click")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
    "DualShock": [
        ("Face Buttons", [("cross", "Cross"), ("circle", "Circle"), ("square", "Square"), ("triangle", "Triangle")]),
        ("Shoulders", [("l1", "L1"), ("r1", "R1"), ("l2", "L2"), ("r2", "R2")]),
        ("Menu", [("options", "Options"), ("share", "Share"), ("ps", "PS"), ("touchpad", "Touchpad")]),
        ("Left Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right"), ("l3", "L3")]),
        ("Right Stick", [("rs_up", "Up"), ("rs_down", "Down"), ("rs_left", "Left"), ("rs_right", "Right"), ("r3", "R3")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
    "DualSense": [
        ("Face Buttons", [("cross", "Cross"), ("circle", "Circle"), ("square", "Square"), ("triangle", "Triangle")]),
        ("Shoulders", [("l1", "L1"), ("r1", "R1"), ("l2", "L2 (Adaptive)"), ("r2", "R2 (Adaptive)")]),
        ("Menu", [("options", "Options"), ("create", "Create"), ("ps", "PS"), ("touchpad", "Touchpad"), ("mute", "Mute")]),
        ("Left Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right"), ("l3", "L3")]),
        ("Right Stick", [("rs_up", "Up"), ("rs_down", "Down"), ("rs_left", "Left"), ("rs_right", "Right"), ("r3", "R3")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
    "GameCube": [
        ("Face Buttons", [("a", "A"), ("b", "B"), ("x", "X"), ("y", "Y"), ("z", "Z")]),
        ("Shoulders", [("l", "L (Analog)"), ("r", "R (Analog)")]),
        ("Menu", [("start", "Start")]),
        ("Control Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right")]),
        ("C-Stick", [("cs_up", "Up"), ("cs_down", "Down"), ("cs_left", "Left"), ("cs_right", "Right")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
    "Joy-Con (L+R)": [
        ("Face Buttons", [("a", "A"), ("b", "B"), ("x", "X"), ("y", "Y")]),
        ("Shoulders", [("l", "L"), ("r", "R"), ("zl", "ZL"), ("zr", "ZR"), ("sl_l", "SL (L)"), ("sr_l", "SR (L)"), ("sl_r", "SL (R)"), ("sr_r", "SR (R)")]),
        ("Menu", [("plus", "+"), ("minus", "\u2212"), ("home", "Home"), ("capture", "Capture")]),
        ("Left Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right"), ("ls_press", "Pressed")]),
        ("Right Stick", [("rs_up", "Up"), ("rs_down", "Down"), ("rs_left", "Left"), ("rs_right", "Right"), ("rs_press", "Pressed")]),
    ],
    "Joy-Con (Single)": [
        ("Buttons (Horizontal)", [("a", "Right"), ("b", "Down"), ("x", "Up"), ("y", "Left"), ("sl", "SL"), ("sr", "SR")]),
        ("Shoulders", [("l_zl", "L / ZL")]),
        ("Menu", [("plus_minus", "+  /  \u2212")]),
        ("Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right"), ("ls_press", "Pressed")]),
    ],
    "Wii Remote": [
        ("Buttons", [("a", "A"), ("b", "B (Trigger)"), ("one", "1"), ("two", "2"), ("plus", "+"), ("minus", "\u2212"), ("home", "Home")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
    "Wii Remote + Nunchuk": [
        ("Wii Remote", [("a", "A"), ("b", "B (Trigger)"), ("one", "1"), ("two", "2"), ("plus", "+"), ("minus", "\u2212"), ("home", "Home")]),
        ("Nunchuk", [("c", "C"), ("z", "Z")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
        ("Nunchuk Stick", [("ns_up", "Up"), ("ns_down", "Down"), ("ns_left", "Left"), ("ns_right", "Right")]),
    ],
    "Classic Controller": [
        ("Face Buttons", [("a", "a"), ("b", "b"), ("x", "x"), ("y", "y")]),
        ("Shoulders", [("l", "L"), ("r", "R"), ("zl", "ZL"), ("zr", "ZR")]),
        ("Menu", [("plus", "+"), ("minus", "\u2212"), ("home", "Home")]),
        ("Left Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right")]),
        ("Right Stick", [("rs_up", "Up"), ("rs_down", "Down"), ("rs_left", "Left"), ("rs_right", "Right")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
    "N64 Controller": [
        ("Face Buttons", [("a", "A"), ("b", "B")]),
        ("C Buttons", [("c_up", "C-Up"), ("c_down", "C-Down"), ("c_left", "C-Left"), ("c_right", "C-Right")]),
        ("Shoulders", [("l", "L"), ("r", "R"), ("z", "Z")]),
        ("Menu", [("start", "Start")]),
        ("Control Stick", [("ls_up", "Up"), ("ls_down", "Down"), ("ls_left", "Left"), ("ls_right", "Right")]),
        ("D-Pad", [("dp_up", "Up"), ("dp_down", "Down"), ("dp_left", "Left"), ("dp_right", "Right")]),
    ],
}

# Aliases so every Type combo entry resolves to a layout
_CONTROLLER_LAYOUTS["Gamepad"] = _CONTROLLER_LAYOUTS["Pro Controller"]
_CONTROLLER_LAYOUTS["Fight Stick"] = _CONTROLLER_LAYOUTS["Gamepad"]
_CONTROLLER_LAYOUTS["Steering Wheel"] = _CONTROLLER_LAYOUTS["Gamepad"]
_CONTROLLER_LAYOUTS["Custom"] = _CONTROLLER_LAYOUTS["Pro Controller"]


def _qt_key_name(key: int) -> str | None:
    """Convert a Qt key constant to a short human-readable name."""
    _SPECIAL: dict[int, str] = {
        Qt.Key.Key_Space: "Space", Qt.Key.Key_Return: "Enter",
        Qt.Key.Key_Enter: "Enter", Qt.Key.Key_Tab: "Tab",
        Qt.Key.Key_Backspace: "Backspace", Qt.Key.Key_Delete: "Delete",
        Qt.Key.Key_Insert: "Insert", Qt.Key.Key_Home: "Home",
        Qt.Key.Key_End: "End", Qt.Key.Key_PageUp: "Page Up",
        Qt.Key.Key_PageDown: "Page Down",
        Qt.Key.Key_Up: "Up", Qt.Key.Key_Down: "Down",
        Qt.Key.Key_Left: "Left", Qt.Key.Key_Right: "Right",
        Qt.Key.Key_Shift: "Shift", Qt.Key.Key_Control: "Ctrl",
        Qt.Key.Key_Alt: "Alt", Qt.Key.Key_Meta: "Meta",
        Qt.Key.Key_CapsLock: "Caps Lock",
        Qt.Key.Key_NumLock: "Num Lock",
        Qt.Key.Key_Minus: "-", Qt.Key.Key_Equal: "=",
        Qt.Key.Key_BracketLeft: "[", Qt.Key.Key_BracketRight: "]",
        Qt.Key.Key_Semicolon: ";", Qt.Key.Key_Apostrophe: "'",
        Qt.Key.Key_Comma: ",", Qt.Key.Key_Period: ".",
        Qt.Key.Key_Slash: "/", Qt.Key.Key_Backslash: "\\",
        Qt.Key.Key_QuoteLeft: "`",
    }
    if key in _SPECIAL:
        return _SPECIAL[key]
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
        return f"F{key - Qt.Key.Key_F1 + 1}"
    if 0x20 <= key <= 0x7E:
        return chr(key).upper()
    return None


_MOUSE_NAMES: dict[Qt.MouseButton, str] = {
    Qt.MouseButton.LeftButton: "Mouse Left",
    Qt.MouseButton.RightButton: "Mouse Right",
    Qt.MouseButton.MiddleButton: "Mouse Middle",
    Qt.MouseButton.BackButton: "Mouse 4",
    Qt.MouseButton.ForwardButton: "Mouse 5",
}


class _BindButton(QPushButton):
    """Push-button that captures the next input when clicked.

    Supports three input sources simultaneously during capture:

    * **Controller** — polled via :class:`InputManager` at 30 Hz, filtered
      to match the device selected in the Device dropdown.
    * **Keyboard** — any key except *Escape* (which cancels).
    * **Mouse** — any button (armed after a short delay so the initial
      click does not self-trigger).

    Only one ``_BindButton`` can be in capture mode at a time.
    """

    from PySide6.QtCore import Signal
    binding_changed = Signal(str)

    _active: _BindButton | None = None

    def __init__(
        self,
        text: str = "",
        device_fn: object | None = None,
        device_index_fn: object | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._device_fn = device_fn or (lambda: "Any Available")
        self._device_index_fn = device_index_fn or (lambda: None)
        self._saved = text
        self._capturing = False
        self._mouse_armed = False
        self._timer: object | None = None
        self.setFixedHeight(22)
        self.clicked.connect(self._toggle)

    # -- public API --------------------------------------------------------

    def set_binding(self, text: str) -> None:
        """Programmatically set the binding (used by Defaults / Clear)."""
        if self._capturing:
            self._cancel()
        self._saved = text
        self.setText(text)

    # -- capture lifecycle -------------------------------------------------

    def _toggle(self) -> None:
        if self._capturing:
            self._cancel()
        else:
            self._start()

    def _start(self) -> None:
        from PySide6.QtCore import QTimer
        from meridian.core.input_manager import InputManager

        device = self._device_fn()
        if device == "None":
            return

        if _BindButton._active is not None and _BindButton._active is not self:
            _BindButton._active._cancel()
        _BindButton._active = self

        mgr = InputManager.instance()
        if not mgr.ensure_ready():
            return
        mgr.drain_events()

        self._capturing = True
        self._mouse_armed = False
        self._saved = self.text()
        self.setText("Listening \u2026")
        self.setFocus()

        # Install app-wide event filter for mouse capture
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        QTimer.singleShot(200, self._arm_mouse)

        # Controller polling timer
        self._timer = QTimer()
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def _arm_mouse(self) -> None:
        if self._capturing:
            self._mouse_armed = True

    def _accept(self, text: str) -> None:
        """Write the captured binding and finish."""
        self.setText(text)
        self._finish()
        self.binding_changed.emit(text)

    def _poll(self) -> None:
        from meridian.core.input_manager import InputManager

        device = self._device_fn()
        if device in ("None", "Keyboard + Mouse"):
            return

        mgr = InputManager.instance()
        device_idx: int | None = None
        if device != "Any Available":
            chosen = self._device_index_fn()
            if isinstance(chosen, int) and chosen >= 0:
                device_idx = chosen
            else:
                # Backwards compatibility for older saved configs that only
                # persisted a device name.
                device_idx = mgr.index_for_name(device)
            if device_idx is None:
                return

        result = mgr.poll_binding(device_index=device_idx)
        if result is not None:
            self._accept(result)

    def _cancel(self) -> None:
        self.setText(self._saved)
        self._finish()

    def _finish(self) -> None:
        self._capturing = False
        self._mouse_armed = False
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        if _BindButton._active is self:
            _BindButton._active = None

    # -- keyboard capture --------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if self._capturing:
            if event.key() == Qt.Key.Key_Escape:
                self._cancel()
                return
            name = _qt_key_name(event.key())
            if name:
                self._accept(f"Key: {name}")
                return
        super().keyPressEvent(event)

    # -- mouse capture (global event filter) -------------------------------

    def eventFilter(self, obj, event) -> bool:
        from PySide6.QtCore import QEvent
        if self._capturing and self._mouse_armed:
            if event.type() == QEvent.Type.MouseButtonPress:
                name = _MOUSE_NAMES.get(event.button())
                if name:
                    self._accept(name)
                    return True
        return super().eventFilter(obj, event)


# ======================================================================
# Configuration sub-dialogs  (Vibration / Mouse-panning)
# ======================================================================

class _VibrationConfigDialog(QDialog):
    """Small dialog to configure vibration strength with a live test button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vibration Settings")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        row = QHBoxLayout()
        self._strength = QSlider(Qt.Orientation.Horizontal)
        self._strength.setRange(0, 100)
        self._strength.setValue(100)
        row.addWidget(self._strength, 1)
        self._str_lbl = QLabel("100 %")
        self._str_lbl.setFixedWidth(40)
        self._strength.valueChanged.connect(
            lambda v: self._str_lbl.setText(f"{v} %")
        )
        row.addWidget(self._str_lbl)
        form.addRow("Strength:", row)

        # Test button — hold to rumble at the current strength
        self._test_btn = QPushButton("Hold to Test")
        self._test_btn.setToolTip(
            "Press and hold to vibrate the controller at the current strength"
        )
        self._test_btn.pressed.connect(self._start_rumble)
        self._test_btn.released.connect(self._stop_rumble)
        form.addRow("", self._test_btn)

        layout.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    # -- rumble helpers ----------------------------------------------------

    def _start_rumble(self) -> None:
        strength = self._strength.value() / 100.0
        try:
            from meridian.core.input_manager import InputManager
            mgr = InputManager.instance()
            for idx, joy in mgr._joysticks.items():
                joy.rumble(strength, strength, 0)
        except Exception:
            pass

    def _stop_rumble(self) -> None:
        try:
            from meridian.core.input_manager import InputManager
            mgr = InputManager.instance()
            for idx, joy in mgr._joysticks.items():
                joy.stop_rumble()
        except Exception:
            pass

    def reject(self) -> None:
        self._stop_rumble()
        super().reject()

    def accept(self) -> None:
        self._stop_rumble()
        super().accept()


class _MousePanningConfigDialog(QDialog):
    """Small dialog to configure mouse-panning parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mouse Panning Settings")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        def _slider_field(lo, hi, val):
            row = QHBoxLayout()
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(lo, hi)
            s.setValue(val)
            row.addWidget(s, 1)
            lbl = QLabel(f"{val} %")
            lbl.setFixedWidth(40)
            s.valueChanged.connect(lambda v: lbl.setText(f"{v} %"))
            row.addWidget(lbl)
            return row, s

        r1, self._h_sens = _slider_field(1, 200, 100)
        form.addRow("Sensitivity (H):", r1)

        r2, self._v_sens = _slider_field(1, 200, 100)
        form.addRow("Sensitivity (V):", r2)

        r3, self._deadzone = _slider_field(0, 100, 0)
        form.addRow("Deadzone counterweight:", r3)

        r4, self._decay = _slider_field(0, 100, 50)
        form.addRow("Stick decay:", r4)

        layout.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)


# ======================================================================
# Row-builder helpers  (used by _input_player)
# ======================================================================

def _clear_layout(layout):
    """Recursively remove all items from a layout."""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


def _section_label(text: str) -> QWidget:
    """Section header with a horizontal rule."""
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 6, 0, 2)
    row.setSpacing(8)

    lbl = QLabel(f"<b>{text}</b>")
    lbl.setObjectName("sectionLabel")
    row.addWidget(lbl)

    line = QWidget()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {active_theme().border};")
    row.addWidget(line, 1)

    return w


def _bind_row(label: str, btn: _BindButton) -> QHBoxLayout:
    """One row: text label + a :class:`_BindButton`."""
    row = QHBoxLayout()
    row.setContentsMargins(8, 0, 0, 0)
    row.setSpacing(8)

    lbl = QLabel(label)
    lbl.setFixedWidth(90)
    row.addWidget(lbl)
    row.addWidget(btn, 1)

    return row


def _spin_row(label: str, value: int, suffix: str) -> QHBoxLayout:
    """One row: label + spin box."""
    row = QHBoxLayout()
    row.setContentsMargins(8, 0, 0, 0)
    row.setSpacing(8)

    lbl = QLabel(label)
    lbl.setFixedWidth(90)
    row.addWidget(lbl)

    spin = QSpinBox()
    spin.setRange(0, 100)
    spin.setValue(value)
    spin.setSuffix(suffix)
    spin.setFixedHeight(22)
    row.addWidget(spin, 1)

    return row


def _slider_row(label: str, value: int, maximum: int) -> QHBoxLayout:
    """One row: label + slider + live percentage readout."""
    row = QHBoxLayout()
    row.setContentsMargins(8, 0, 0, 0)
    row.setSpacing(8)

    lbl = QLabel(label)
    lbl.setFixedWidth(90)
    row.addWidget(lbl)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, maximum)
    slider.setValue(value)
    row.addWidget(slider, 1)

    pct = QLabel(f"{value}%")
    pct.setFixedWidth(32)
    pct.setObjectName("sectionLabel")
    slider.valueChanged.connect(lambda v: pct.setText(f"{v}%"))
    row.addWidget(pct)

    return row


def _check_row(label: str, checked: bool) -> QHBoxLayout:
    """One row: enabled checkbox."""
    row = QHBoxLayout()
    row.setContentsMargins(8, 0, 0, 0)
    row.setSpacing(8)

    chk = QCheckBox(label)
    chk.setChecked(checked)
    chk.setFixedHeight(18)
    row.addWidget(chk)
    row.addStretch()

    return row


def _check_configure_row(
    label: str, checked: bool, on_configure,
) -> QHBoxLayout:
    """One row: checkbox + a "Configure …" button on the right."""
    row = QHBoxLayout()
    row.setContentsMargins(8, 0, 0, 0)
    row.setSpacing(8)

    chk = QCheckBox(label)
    chk.setChecked(checked)
    row.addWidget(chk)
    row.addStretch()

    btn = QPushButton(" Configure\u2026 ")
    btn.setMaximumHeight(18)
    btn.setStyleSheet("QPushButton { padding: 0px 6px; }")
    btn.clicked.connect(on_configure)
    row.addWidget(btn)

    return row


def _combo_row(label: str, items: list[str], index: int) -> QHBoxLayout:
    """One row: label + combo-box."""
    row = QHBoxLayout()
    row.setContentsMargins(8, 0, 0, 0)
    row.setSpacing(8)

    lbl = QLabel(label)
    lbl.setFixedWidth(90)
    row.addWidget(lbl)

    combo = QComboBox()
    combo.addItems(items)
    combo.setCurrentIndex(index)
    combo.setFixedHeight(22)
    row.addWidget(combo, 1)

    return row


def _get_bundled_font_names() -> list[str]:
    """Scan assets/fonts/ subdirectories and return font family names."""
    fonts_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
    if not fonts_dir.exists():
        return ["Ubuntu"]
    names = []
    for subdir in sorted(fonts_dir.iterdir()):
        if subdir.is_dir() and any(subdir.glob("*.ttf")):
            # Derive a display name from the directory name
            name = subdir.name.replace("-", " ").replace("_", " ").title()
            # Try to match the actual font family name from the filename
            for ttf in subdir.glob("*-Regular.ttf"):
                name = ttf.stem.rsplit("-", 1)[0].replace("_", " ")
                break
            for ttf in subdir.glob("*Regular.ttf"):
                name = ttf.stem.replace("Regular", "").replace("-", "").replace("_", " ").strip()
                if not name:
                    name = subdir.name.replace("-", " ").replace("_", " ").title()
                break
            names.append(name)
    return names if names else ["Ubuntu"]


def _detect_controllers() -> list[str]:
    """Return names of currently connected game controllers."""
    from meridian.core.input_manager import InputManager
    mgr = InputManager.instance()
    mgr.ensure_ready()
    return mgr.controller_names()
