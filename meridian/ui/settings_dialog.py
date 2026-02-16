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

from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QCheckBox, QListWidget, QListWidgetItem, QStackedWidget,
    QTabWidget, QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QSlider, QFileDialog, QDialogButtonBox, QGroupBox, QMessageBox, QProgressDialog, QInputDialog,
    QScrollArea, QLayout,
)

from PySide6.QtWidgets import QApplication

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


# ======================================================================
# Category / subcategory definitions
# ======================================================================

_CATEGORIES: list[tuple[str, list[str]]] = [
    ("General",        ["General", "UI", "Hotkeys"]),
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
    {"id": "switch_firmware", "name": "Nintendo Switch Firmware", "systems": ["switch"], "required": False, "hint": "firmware/*.nca"},
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
    "NEC / Hudson",
    "SNK",
    "Arcade",
    "PC / DOS",
    "Other",
]


def _system_company(system_id: str) -> str:
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
        return "NEC / Hudson"
    if system_id in {"ngp", "neogeo"}:
        return "SNK"
    if system_id in {"mame"}:
        return "Arcade"
    if system_id in {"dos", "pc"}:
        return "PC / DOS"
    return "Other"


# ======================================================================
# Main dialog
# ======================================================================

class SettingsDialog(QDialog):
    """Modal settings dialog with sidebar + subcategory tabs."""

    MIN_W, MIN_H = 740, 520

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.resize(820, 560)

        self._cfg = copy.deepcopy(config)
        self._original_cfg = copy.deepcopy(config)
        self._dirty = False
        self._building = True   # suppress _mark_dirty during construction
        self._build_ui()
        self._building = False
        self._dirty = False     # reset in case construction triggered it
        self._sidebar.setCurrentRow(0)

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
            "Waves", "Starscape",
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
        g_d.addWidget(_disabled_check("Show game titles under cover art", True))
        g_d.addWidget(_disabled_check("Show platform badges", True))
        layout.addWidget(grp_display)

        layout.addStretch()

        # Wrap in scroll area so content isn't cramped
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
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
        self._chk_remember_geom.setEnabled(False)   # not wired yet
        self._chk_remember_geom.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_remember_geom)

        self._chk_borderless = QCheckBox("Use borderless window in fullscreen")
        self._chk_borderless.setChecked(self._cfg.borderless_fullscreen)
        self._chk_borderless.setEnabled(False)   # not wired yet
        self._chk_borderless.toggled.connect(self._mark_dirty)
        g.addWidget(self._chk_borderless)

        layout.addWidget(grp)
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
        self._combo_gpu_backend.setEnabled(False)  # not wired yet
        self._combo_gpu_backend.currentTextChanged.connect(self._mark_dirty)
        g_gpu.addRow("Render backend:", self._combo_gpu_backend)

        hint_gpu = QLabel("Changing the render backend requires a restart.")
        hint_gpu.setObjectName("sectionLabel")
        hint_gpu.setWordWrap(True)
        g_gpu.addRow("", hint_gpu)

        layout.addWidget(grp_gpu)

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

        # -- Actions ---------------------------------------------------
        grp_actions = QGroupBox("Actions")
        g_a = QVBoxLayout(grp_actions)
        g_a.setSpacing(8)

        btn_clear = QPushButton("Clear Cache")
        btn_clear.setFixedWidth(120)
        btn_clear.clicked.connect(self._on_clear_cache)
        g_a.addWidget(btn_clear)

        layout.addWidget(grp_actions)

        layout.addStretch()
        return w

    def _on_clear_cache(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
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

        if sub.startswith("Player "):
            return self._input_player(int(sub.split()[1]))
        if sub == "Adv. Settings":
            return self._input_adv_settings()
        return _placeholder(sub)

    def _input_player(self, num: int) -> QWidget:
        """Build a controller-mapping tab as a vertical list of sections."""
        from PySide6.QtWidgets import QScrollArea

        saved_input = self._cfg.input_player_settings.get(str(num), {})
        saved_bindings = saved_input.get("bindings", {})
        defs = saved_bindings if saved_bindings else (_PLAYER1_BINDINGS if num == 1 else {})
        mgr = self._input_mgr
        detected = mgr.controller_names()

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

        # -- Top bar: Connected · Device · Type ------------------------
        top = QHBoxLayout()
        top.setSpacing(8)

        chk = QCheckBox("Connected")
        chk.setChecked(bool(saved_input.get("connected", num == 1)))

        def _on_connected(on: bool):
            body.setEnabled(on)
            self._mark_dirty()

        chk.toggled.connect(_on_connected)
        top.addWidget(chk)

        top.addWidget(QLabel("Device:"))
        dev = QComboBox()
        dev.addItems(["None", "Keyboard + Mouse", "Any Available"] + detected)
        saved_device = str(saved_input.get("device", "Any Available"))
        if saved_device and dev.findText(saved_device) < 0:
            dev.addItem(saved_device)
        dev.setCurrentIndex(max(dev.findText(saved_device), 0))
        dev.setMinimumWidth(100)
        dev.currentIndexChanged.connect(self._mark_dirty)
        top.addWidget(dev, 1)

        btn_refresh = QPushButton(" Refresh ")
        btn_refresh.setToolTip("Re-scan for controllers")

        def _on_refresh():
            mgr.refresh()
            current = dev.currentText()
            dev.blockSignals(True)
            dev.clear()
            dev.addItems(
                ["None", "Keyboard + Mouse", "Any Available"]
                + mgr.controller_names()
            )
            idx = dev.findText(current)
            dev.setCurrentIndex(max(idx, 0))
            dev.blockSignals(False)

        btn_refresh.clicked.connect(_on_refresh)
        top.addWidget(btn_refresh)

        top.addWidget(QLabel("Type:"))
        tcombo = QComboBox()
        tcombo.addItems([
            "Pro Controller", "Gamepad", "Xbox Controller", "DualShock",
            "DualSense", "Joy-Con (L+R)", "Joy-Con (Single)",
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

        def add_bind(key: str, label: str) -> QHBoxLayout:
            btn = _BindButton(defs.get(key, ""), device_fn=_get_device)
            btn.binding_changed.connect(self._mark_dirty)
            bindings[key] = btn
            return _bind_row(label, btn)

        # All editable content goes inside body so it can be
        # enabled / disabled as a single unit via the Connected checkbox.
        bl = body_layout

        # -- Section 1: Buttons ----------------------------------------
        bl.addWidget(_section_label("Buttons"))
        bl.addLayout(add_bind("a", "A"))
        bl.addLayout(add_bind("b", "B"))
        bl.addLayout(add_bind("x", "X"))
        bl.addLayout(add_bind("y", "Y"))
        bl.addLayout(add_bind("l", "L"))
        bl.addLayout(add_bind("r", "R"))
        bl.addLayout(add_bind("zl", "ZL"))
        bl.addLayout(add_bind("zr", "ZR"))
        bl.addLayout(add_bind("plus", "Start / +"))
        bl.addLayout(add_bind("minus", "Select / \u2212"))
        bl.addLayout(add_bind("home", "Home"))
        bl.addLayout(add_bind("capture", "Capture"))

        # -- Section 2: Left Stick -------------------------------------
        bl.addWidget(_section_label("Left Stick"))
        bl.addLayout(add_bind("ls_up", "Up"))
        bl.addLayout(add_bind("ls_down", "Down"))
        bl.addLayout(add_bind("ls_left", "Left"))
        bl.addLayout(add_bind("ls_right", "Right"))
        bl.addLayout(add_bind("ls_press", "Pressed"))
        bl.addLayout(_spin_row("Range", 95 if defs else 100, "%"))
        bl.addLayout(_slider_row("Deadzone", 15 if defs else 0, 50))

        # -- Section 3: Right Stick ------------------------------------
        bl.addWidget(_section_label("Right Stick"))
        bl.addLayout(add_bind("rs_up", "Up"))
        bl.addLayout(add_bind("rs_down", "Down"))
        bl.addLayout(add_bind("rs_left", "Left"))
        bl.addLayout(add_bind("rs_right", "Right"))
        bl.addLayout(add_bind("rs_press", "Pressed"))
        bl.addLayout(_spin_row("Range", 95 if defs else 100, "%"))
        bl.addLayout(_slider_row("Deadzone", 15 if defs else 0, 50))

        # -- Section 4: D-Pad ------------------------------------------
        bl.addWidget(_section_label("D-Pad"))
        bl.addLayout(add_bind("dp_up", "Up"))
        bl.addLayout(add_bind("dp_down", "Down"))
        bl.addLayout(add_bind("dp_left", "Left"))
        bl.addLayout(add_bind("dp_right", "Right"))

        # -- Section 5: Motion, Vibration & Extras ---------------------
        bl.addWidget(_section_label("Motion, Vibration & Extras"))

        # Single motion binding — the runtime uses all gyro axes automatically
        bl.addLayout(add_bind("motion", "Motion"))

        # Sensor availability hint
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
        bl.addWidget(sensor_hint)

        bl.addLayout(_check_row("Motion controls", True))

        # Vibration + Configure
        def _on_vibration_cfg():
            _VibrationConfigDialog(parent=self).exec()

        bl.addLayout(
            _check_configure_row("Vibration", True, _on_vibration_cfg)
        )

        # Mouse panning + Configure
        def _on_mouse_pan_cfg():
            _MousePanningConfigDialog(parent=self).exec()

        bl.addLayout(
            _check_configure_row("Mouse panning", False, _on_mouse_pan_cfg)
        )

        # Console Mode
        bl.addLayout(_combo_row(
            "Console Mode", ["Docked", "Handheld"], 0,
        ))

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
            self._mark_dirty()

        btn_def.clicked.connect(_on_defaults)
        bottom.addWidget(btn_def)

        btn_clr = QPushButton(" Clear ")

        def _on_clear():
            for btn in bindings.values():
                btn.set_binding("")
            self._mark_dirty()

        btn_clr.clicked.connect(_on_clear)
        bottom.addWidget(btn_clr)

        bl.addLayout(bottom)

        layout.addWidget(body, 1)

        # Set initial enabled state based on the Connected checkbox
        body.setEnabled(chk.isChecked())
        self._input_player_controls[num] = {
            "connected": chk,
            "device": dev,
            "type": tcombo,
            "bindings": bindings,
        }

        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
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

        grp_profiles = QGroupBox("Controller Profiles")
        g_profiles = QVBoxLayout(grp_profiles)
        g_profiles.setSpacing(8)
        self._controller_profiles = copy.deepcopy(self._cfg.controller_profiles)
        self._active_controller_profile = self._cfg.active_controller_profile or ""

        profile_row = QHBoxLayout()
        profile_row.setSpacing(8)
        profile_row.addWidget(QLabel("Profile:"))
        self._input_profile_combo = QComboBox()
        self._input_profile_combo.addItem("(Current Unsaved)", "")
        for name in sorted(self._controller_profiles.keys(), key=str.lower):
            self._input_profile_combo.addItem(name, name)
        if self._active_controller_profile:
            idx = self._input_profile_combo.findData(self._active_controller_profile)
            self._input_profile_combo.setCurrentIndex(idx if idx >= 0 else 0)
        profile_row.addWidget(self._input_profile_combo, 1)
        g_profiles.addLayout(profile_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_save_profile = QPushButton("Save Current as Profile...")
        btn_save_profile.clicked.connect(self._on_save_controller_profile)
        btn_row.addWidget(btn_save_profile)
        btn_load_profile = QPushButton("Load Selected")
        btn_load_profile.clicked.connect(self._on_load_controller_profile)
        btn_row.addWidget(btn_load_profile)
        btn_delete_profile = QPushButton("Delete Selected")
        btn_delete_profile.clicked.connect(self._on_delete_controller_profile)
        btn_row.addWidget(btn_delete_profile)
        btn_row.addStretch()
        g_profiles.addLayout(btn_row)

        profile_hint = QLabel(
            "Profiles store controller connected/device/type assignments for Player 1-10."
        )
        profile_hint.setObjectName("sectionLabel")
        profile_hint.setWordWrap(True)
        g_profiles.addWidget(profile_hint)
        layout.addWidget(grp_profiles)

        grp_opts = QGroupBox("Global Input Options")
        g_opts = QVBoxLayout(grp_opts)
        g_opts.setSpacing(8)
        g_opts.addWidget(_disabled_check("Enable gamepad navigation in UI"))
        g_opts.addWidget(_disabled_check("Global vibration feedback"))
        g_opts.addWidget(_disabled_check("Global motion controls"))
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
            dev = widget_map.get("device")
            typ = widget_map.get("type")
            if not isinstance(chk, QCheckBox):
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
                "device": dev.currentText(),
                "type": typ.currentText(),
                "bindings": bindings_map,
            }
        return merged

    def _apply_input_player_settings(self, settings_map: dict[str, dict[str, object]]) -> None:
        self._cfg.input_player_settings = copy.deepcopy(settings_map)
        controls = getattr(self, "_input_player_controls", {})
        for num, widget_map in controls.items():
            saved = settings_map.get(str(num), {})
            chk = widget_map.get("connected")
            dev = widget_map.get("device")
            typ = widget_map.get("type")
            if isinstance(chk, QCheckBox):
                chk.setChecked(bool(saved.get("connected", num == 1)))
            if isinstance(dev, QComboBox):
                wanted = str(saved.get("device", "Any Available"))
                if wanted and dev.findText(wanted) < 0:
                    dev.addItem(wanted)
                dev.setCurrentIndex(max(dev.findText(wanted), 0))
            if isinstance(typ, QComboBox):
                wanted_type = str(saved.get("type", "Pro Controller"))
                dev_idx = typ.findText(wanted_type)
                typ.setCurrentIndex(dev_idx if dev_idx >= 0 else 0)
            # Restore bindings to the UI bind buttons so they aren't
            # lost when _collect_input_player_settings runs on save.
            saved_bindings = saved.get("bindings")
            bind_buttons = widget_map.get("bindings")
            if isinstance(saved_bindings, dict) and isinstance(bind_buttons, dict):
                for key, btn in bind_buttons.items():
                    if hasattr(btn, "set_binding"):
                        btn.set_binding(str(saved_bindings.get(key, "")))

    def _on_save_controller_profile(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "Save Controller Profile",
            "Profile name:",
            text=self._active_controller_profile or "",
        )
        if not ok:
            return
        profile_name = name.strip()
        if not profile_name:
            return
        snapshot = self._collect_input_player_settings()
        self._controller_profiles[profile_name] = snapshot
        self._active_controller_profile = profile_name
        self._refresh_input_profile_combo()
        self._mark_dirty()

    def _on_load_controller_profile(self) -> None:
        if not hasattr(self, "_input_profile_combo"):
            return
        profile_name = str(self._input_profile_combo.currentData() or "")
        if not profile_name:
            return
        snapshot = self._controller_profiles.get(profile_name)
        if not isinstance(snapshot, dict):
            return
        self._apply_input_player_settings(snapshot)
        self._active_controller_profile = profile_name
        self._mark_dirty()

    def _on_delete_controller_profile(self) -> None:
        if not hasattr(self, "_input_profile_combo"):
            return
        profile_name = str(self._input_profile_combo.currentData() or "")
        if not profile_name:
            return
        self._controller_profiles.pop(profile_name, None)
        if self._active_controller_profile == profile_name:
            self._active_controller_profile = ""
        self._refresh_input_profile_combo()
        self._mark_dirty()

    def _refresh_input_profile_combo(self) -> None:
        if not hasattr(self, "_input_profile_combo"):
            return
        combo = self._input_profile_combo
        current = self._active_controller_profile
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(Current Unsaved)", "")
        for name in sorted(self._controller_profiles.keys(), key=str.lower):
            combo.addItem(name, name)
        idx = combo.findData(current)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

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
        """Shows installed emulators with settings/delete/update buttons."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        lbl = QLabel("Installed emulators:")
        lbl.setObjectName("sectionLabel")
        layout.addWidget(lbl)

        from PySide6.QtWidgets import QScrollArea

        self._installed_content = QWidget()
        self._installed_layout = QVBoxLayout(self._installed_content)
        self._installed_layout.setContentsMargins(0, 0, 0, 0)
        self._installed_layout.setSpacing(4)
        self._installed_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._installed_content)
        layout.addWidget(scroll, 1)

        # Add manually button
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_add = QPushButton("Add Manually...")
        btn_add.clicked.connect(self._on_add_emulator)
        btn_row.addWidget(btn_add)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Populate existing installed emulators
        self._installed_cards: list[QWidget] = []
        for entry in self._cfg.emulators:
            self._insert_installed_card(entry)

        if not self._cfg.emulators:
            self._show_installed_empty_state()

        return w

    def _insert_installed_card(self, entry: EmulatorEntry):
        """One installed emulator card: name, path, cog/delete/update icons."""
        card = QWidget()
        card.setObjectName("playerSlot")
        row = QHBoxLayout(card)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)

        # Installed indicator
        check_icon = QLabel()
        check_icon.setPixmap(lucide_pixmap("circle-check", 16, active_theme().accent_secondary))
        check_icon.setFixedSize(20, 20)
        row.addWidget(check_icon)

        # Name + path
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(f"<b>{entry.display_name()}</b>")
        info.addWidget(name_lbl)
        if entry.path:
            path_lbl = QLabel(entry.path)
            path_lbl.setObjectName("sectionLabel")
            info.addWidget(path_lbl)
        if entry.version:
            version_lbl = QLabel(f"Version: {entry.version}")
            version_lbl.setObjectName("sectionLabel")
            info.addWidget(version_lbl)
        row.addLayout(info, 1)

        # Action buttons (icon-only)
        btn_settings = QPushButton()
        btn_settings.setIcon(lucide_icon("settings", 14, active_theme().fg_primary))
        btn_settings.setFixedSize(28, 28)
        btn_settings.setToolTip("Emulator settings")
        btn_settings.clicked.connect(lambda _, e=entry: self._on_emu_settings(e))
        row.addWidget(btn_settings)

        btn_update = QPushButton()
        btn_update.setIcon(lucide_icon("refresh-cw", 14, active_theme().fg_primary))
        btn_update.setFixedSize(28, 28)
        btn_update.setToolTip("Check for updates")
        btn_update.setEnabled(False)
        row.addWidget(btn_update)

        btn_delete = QPushButton()
        btn_delete.setIcon(lucide_icon("trash-2", 14, active_theme().fg_primary))
        btn_delete.setFixedSize(28, 28)
        btn_delete.setToolTip("Remove emulator")
        btn_delete.clicked.connect(
            lambda _, c=card, e=entry: self._on_delete_installed(c, e)
        )
        row.addWidget(btn_delete)

        idx = self._installed_layout.count() - 1
        self._installed_layout.insertWidget(idx, card)
        self._installed_cards.append(card)

    def _on_emu_settings(self, entry: EmulatorEntry):
        """Open per-emulator settings dialog."""
        dlg = _EmulatorSettingsDialog(entry, self._cfg, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_installed_cards()
            self._mark_dirty()

    def _on_delete_installed(self, card: QWidget, entry: EmulatorEntry):
        confirm = QMessageBox.question(
            self,
            "Delete Emulator",
            f"Delete {entry.display_name()} and all installed files from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, err = self._delete_emulator_files(entry)
        if not ok:
            QMessageBox.warning(
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

        # Filter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_row.addWidget(QLabel("Filter by system:"))
        self._browse_filter = QComboBox()
        self._browse_filter.addItem("All Systems", "")
        for sid, name, _ in KNOWN_SYSTEMS:
            self._browse_filter.addItem(name, sid)
        self._browse_filter.currentIndexChanged.connect(self._on_browse_filter)
        filter_row.addWidget(self._browse_filter, 1)
        layout.addLayout(filter_row)

        # Catalog scroll area
        from PySide6.QtWidgets import QScrollArea

        self._browse_content = QWidget()
        self._browse_layout = QVBoxLayout(self._browse_content)
        self._browse_layout.setContentsMargins(0, 0, 0, 0)
        self._browse_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._browse_content)
        layout.addWidget(scroll, 1)

        self._populate_browse_catalog("")
        return w

    def _populate_browse_catalog(self, filter_system: str):
        """Rebuild the catalog list, optionally filtered to one system."""
        # Clear existing
        while self._browse_layout.count():
            item = self._browse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        installed_names = {e.name for e in self._cfg.emulators}
        installed_ids = {e.catalog_id for e in self._cfg.emulators if e.catalog_id}

        for entry in EMULATOR_CATALOG:
            # Core-only entries are configured through RetroArch itself.
            if entry.install_strategy == "retroarch_core":
                continue
            # Only show installers that can be executed from Meridian.
            if not entry.windows_supported or entry.install_strategy == "manual":
                continue
            if filter_system and filter_system not in entry.systems:
                continue

            card = QWidget()
            card.setObjectName("playerSlot")
            row = QHBoxLayout(card)
            row.setContentsMargins(10, 6, 10, 6)
            row.setSpacing(10)

            # Info
            info = QVBoxLayout()
            info.setSpacing(1)
            name_lbl = QLabel(f"<b>{entry.name}</b>")
            info.addWidget(name_lbl)

            system_names = [SYSTEM_NAMES.get(s, s) for s in entry.systems[:5]]
            suffix = f" +{len(entry.systems) - 5} more" if len(entry.systems) > 5 else ""
            platforms = QLabel(", ".join(system_names) + suffix)
            platforms.setObjectName("sectionLabel")
            platforms.setWordWrap(True)
            info.addWidget(platforms)

            if entry.preferred_version:
                version_lbl = QLabel(f"Pinned version: {entry.preferred_version}")
                version_lbl.setObjectName("sectionLabel")
                info.addWidget(version_lbl)

            row.addLayout(info, 1)

            if entry.id in installed_ids or entry.name in installed_names:
                installed_lbl = QLabel()
                installed_lbl.setPixmap(lucide_pixmap("circle-check", 16, active_theme().accent_secondary))
                installed_lbl.setToolTip("Installed")
                row.addWidget(installed_lbl)
            else:
                btn_dl = QPushButton()
                btn_dl.setIcon(lucide_icon("download", 14, active_theme().fg_primary))
                btn_dl.setFixedSize(28, 28)
                btn_dl.setToolTip(f"Install {entry.name}")
                btn_dl.setEnabled(True)
                btn_dl.clicked.connect(lambda _, e=entry, b=btn_dl: self._on_install_catalog_entry(e, b))
                row.addWidget(btn_dl)

            self._browse_layout.addWidget(card)

        self._browse_layout.addStretch()

    def _on_browse_filter(self, index: int):
        sid = self._browse_filter.currentData() or ""
        self._populate_browse_catalog(sid)

    def _on_install_catalog_entry(self, catalog_entry: EmulatorCatalogEntry, btn: QPushButton):
        btn.setEnabled(False)
        progress = QProgressDialog(f"Installing {catalog_entry.name}...", "", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()
        try:
            result = install_emulator(catalog_entry, self._cfg.emulators)
        finally:
            progress.close()
            btn.setEnabled(True)

        if not result.ok:
            QMessageBox.warning(self, "Install failed", result.message)
            return

        if result.entry:
            self._upsert_emulator(result.entry)
            self._mark_dirty()

        self._refresh_installed_cards()
        self._populate_browse_catalog(self._browse_filter.currentData() or "")
        QMessageBox.information(self, "Install complete", result.message)

    def _upsert_emulator(self, new_entry: EmulatorEntry) -> None:
        for idx, existing in enumerate(self._cfg.emulators):
            same_catalog = bool(new_entry.catalog_id and new_entry.catalog_id == existing.catalog_id)
            same_name = new_entry.name.lower() == existing.name.lower()
            if same_catalog or same_name:
                self._cfg.emulators[idx] = new_entry
                return
        self._cfg.emulators.append(new_entry)

    def _refresh_installed_cards(self):
        if not hasattr(self, "_installed_layout"):
            return
        while self._installed_layout.count():
            item = self._installed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._installed_layout.addStretch()
        self._installed_cards = []
        for entry in self._cfg.emulators:
            self._insert_installed_card(entry)
        if not self._cfg.emulators:
            self._show_installed_empty_state()
        self._refresh_system_emulator_controls()

    def _show_installed_empty_state(self):
        empty = QLabel("No emulators installed. Use Browse & Download or Add Manually.")
        empty.setObjectName("sectionLabel")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setWordWrap(True)
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
                requirement = "Required" if required else "Optional"
                row_label = f"{name} ({requirement})"

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
                sec_form.addRow(row_label + f" — {', '.join(systems)}", row)
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
        result: list[EmulatorEntry] = []
        for item in self._cfg.emulators:
            catalog = emulator_catalog_entry(item.catalog_id or item.name)
            if catalog and catalog.install_strategy == "retroarch_core":
                continue
            result.append(item)
        return result

    def _emulator_supports_system(self, item: EmulatorEntry, system_id: str) -> bool:
        catalog = emulator_catalog_entry(item.catalog_id or item.name)
        if catalog:
            if catalog.install_strategy == "retroarch_core":
                return False
            return system_id in catalog.systems
        # Manually added entries are considered user-managed and selectable.
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
            if retro.install_dir:
                cores_dir = Path(retro.install_dir) / "cores"
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
        is_retroarch = selected_name.lower() == "retroarch"
        core_combo.blockSignals(True)
        core_combo.clear()
        core_label.setVisible(is_retroarch)
        core_combo.setVisible(is_retroarch)
        if is_retroarch:
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
            QMessageBox.warning(self, "RetroArch Core", message)
            return

        retro.system_overrides[system_id] = core
        self._mark_dirty()

    def _ensure_retroarch_core_installed(self, retro: EmulatorEntry, core_dll: str) -> tuple[bool, str]:
        """Ensure selected RetroArch core DLL exists; download if missing."""
        retro_root = Path(retro.install_dir) if retro.install_dir else Path(retro.path).parent
        if not retro_root.exists():
            return False, "RetroArch install directory was not found."

        cores_dir = retro_root / "cores"
        cores_dir.mkdir(parents=True, exist_ok=True)
        target = cores_dir / core_dll
        if target.exists():
            return True, ""

        core_zip_url = f"https://buildbot.libretro.com/nightly/windows/x86_64/latest/{core_dll}.zip"
        progress = QProgressDialog(f"Downloading core {core_dll}...", "", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        tmp_zip = emulators_root() / "_downloads" / f"{core_dll}.zip"
        tmp_zip.parent.mkdir(parents=True, exist_ok=True)
        try:
            req = urllib.request.Request(core_zip_url, headers={"User-Agent": "Meridian/1.0"}, method="GET")
            with urllib.request.urlopen(req, timeout=60) as res:
                tmp_zip.write_bytes(res.read())
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                zf.extractall(cores_dir)
            if not target.exists():
                return False, f"Downloaded archive but {core_dll} was not found after extraction."
            return True, ""
        except Exception as exc:
            return False, f"Failed to download/install core {core_dll}: {exc}"
        finally:
            progress.close()
            try:
                tmp_zip.unlink(missing_ok=True)
            except Exception:
                pass

    def _bios_storage_dir(self) -> Path:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation,
        )
        path = Path(base) / "bios"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _on_import_bios_file(self, bios_id: str) -> None:
        le = getattr(self, "_bios_path_inputs", {}).get(bios_id)
        if not le:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import BIOS File",
            le.text().strip() or "",
            "All Files (*.*)",
        )
        if path:
            src = Path(path)
            ext = src.suffix.lower() or ".bin"
            dest = self._bios_storage_dir() / f"{bios_id}{ext}"
            try:
                shutil.copy2(src, dest)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Import BIOS File",
                    f"Failed to import BIOS file:\n{exc}",
                )
                return
            le.setText(str(dest))
            QMessageBox.information(
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
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Netplay")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Enable multiplayer features"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Username:"))
        le = QLineEdit()
        le.setPlaceholderText("Player")
        le.setEnabled(False)
        row.addWidget(le, 1)
        g.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Default port:"))
        spin = QSpinBox()
        spin.setRange(1024, 65535)
        spin.setValue(55435)
        spin.setEnabled(False)
        row2.addWidget(spin)
        row2.addStretch()
        g.addLayout(row2)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    def _net_updates(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Updates")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Check for updates on startup"))
        g.addWidget(_disabled_check("Include pre-release versions"))

        btn = QPushButton("Check Now")
        btn.setEnabled(False)
        btn.setFixedWidth(120)
        g.addWidget(btn)

        layout.addWidget(grp)
        layout.addStretch()
        return w

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
            "Select one source for all metadata and artwork. "
            "Each source has different capabilities and credential "
            "requirements — the settings below adapt automatically."
        )
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        g_src.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("Active source:"))
        self._scraper_combo = QComboBox()
        self._scraper_combo.addItems(SCRAPER_SOURCE_NAMES)
        cur = self._cfg.scraper_source
        idx = SCRAPER_SOURCE_NAMES.index(cur) if cur in SCRAPER_SOURCE_NAMES else 0
        self._scraper_combo.setCurrentIndex(idx)
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

        for src in SCRAPER_SOURCES:
            page = QWidget()
            form = QFormLayout(page)
            form.setSpacing(8)
            form.setContentsMargins(0, 0, 0, 0)

            field_inputs: dict[str, QLineEdit] = {}
            if not src.auth_fields:
                lbl = QLabel("No credentials required for this source.")
                lbl.setObjectName("sectionLabel")
                form.addRow(lbl)
            else:
                stored = self._cfg.scraper_credentials.get(src.name, {})
                for key, label, placeholder, is_secret in src.auth_fields:
                    le = QLineEdit()
                    le.setPlaceholderText(placeholder)
                    if is_secret:
                        le.setEchoMode(QLineEdit.EchoMode.Password)
                    le.setText(stored.get(key, ""))
                    le.textChanged.connect(self._mark_dirty)
                    form.addRow(label, le)
                    field_inputs[key] = le

            self._scraper_cred_inputs[src.name] = field_inputs
            self._scraper_cred_stack.addWidget(page)

        cred_layout.addWidget(self._scraper_cred_stack)

        btn_row = QHBoxLayout()
        self._scraper_test_btn = QPushButton("Test Connection")
        self._scraper_test_btn.setFixedWidth(140)
        self._scraper_test_btn.setEnabled(False)
        btn_row.addWidget(self._scraper_test_btn)
        btn_row.addStretch()
        cred_layout.addLayout(btn_row)

        layout.addWidget(self._scraper_cred_group)

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

        self._chk_hash_matching = QCheckBox(
            "Hash ROMs for accurate matching (CRC32 / MD5 / SHA1)"
        )
        self._chk_hash_matching.setChecked(self._cfg.scraper_hash_matching)
        self._chk_hash_matching.toggled.connect(self._mark_dirty)
        g_b.addWidget(self._chk_hash_matching)

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

        # Hash matching
        self._chk_hash_matching.setEnabled(src.supports_hash)
        if not src.supports_hash:
            self._chk_hash_matching.setChecked(False)
            self._chk_hash_matching.setToolTip(
                f"{source_name} does not support hash-based matching"
            )
        else:
            self._chk_hash_matching.setToolTip("")

        # Region priority
        self._scraper_region_widget.setVisible(src.supports_region_priority)

        # Rate-limit note
        if src.rate_limit_note:
            self._scraper_rate_note.setText(src.rate_limit_note)
            self._scraper_rate_note.setVisible(True)
        else:
            self._scraper_rate_note.setVisible(False)

        self._mark_dirty()

    def _tools_retroachievements(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("RetroAchievements Account")
        g = QFormLayout(grp)
        g.setSpacing(8)

        le_user = QLineEdit()
        le_user.setPlaceholderText("RetroAchievements username")
        le_user.setEnabled(False)
        g.addRow("Username:", le_user)

        le_key = QLineEdit()
        le_key.setPlaceholderText("API key")
        le_key.setEchoMode(QLineEdit.EchoMode.Password)
        le_key.setEnabled(False)
        g.addRow("API Key:", le_key)

        layout.addWidget(grp)

        grp2 = QGroupBox("Integration")
        g2 = QVBoxLayout(grp2)
        g2.setSpacing(8)
        g2.addWidget(_disabled_check("Enable RetroAchievements"))
        g2.addWidget(_disabled_check("Show achievement notifications"))
        g2.addWidget(_disabled_check("Hardcore mode"))
        g2.addWidget(_disabled_check("Display achievement badges in game grid"))
        layout.addWidget(grp2)

        grp3 = QGroupBox("Data")
        g3 = QVBoxLayout(grp3)
        g3.setSpacing(8)
        g3.addWidget(_disabled_check("Sync progress on launch"))
        g3.addWidget(_disabled_check("Cache achievement icons locally"))

        row = QHBoxLayout()
        btn = QPushButton("Test Connection")
        btn.setEnabled(False)
        row.addWidget(btn)
        row.addStretch()
        g3.addLayout(row)

        layout.addWidget(grp3)
        layout.addStretch()
        return w

    def _tools_files(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("File Management")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Verify ROM integrity on scan"))
        g.addWidget(_disabled_check("Remove missing ROMs from library"))
        g.addWidget(_disabled_check("Hash ROMs for scraper matching (CRC32)"))

        row = QHBoxLayout()
        btn_open = QPushButton("Open App Data Directory")
        btn_open.setEnabled(False)
        row.addWidget(btn_open)
        row.addStretch()
        g.addLayout(row)

        layout.addWidget(grp)
        layout.addStretch()
        return w

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

        grp = QGroupBox("Diagnostics")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Enable debug logging"))
        g.addWidget(_disabled_check("Show FPS counter"))
        g.addWidget(_disabled_check("Log emulator stdout"))

        row = QHBoxLayout()
        btn = QPushButton("Open Log File")
        btn.setEnabled(False)
        row.addWidget(btn)
        row.addStretch()
        g.addLayout(row)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    def _adv_experimental(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Experimental Features")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("GPU-accelerated game grid"))
        g.addWidget(_disabled_check("Predictive ROM scanning"))
        g.addWidget(_disabled_check("Cloud save sync"))

        lbl = QLabel("These features are unstable and may cause issues.")
        lbl.setObjectName("sectionLabel")
        g.addWidget(lbl)

        layout.addWidget(grp)
        layout.addStretch()
        return w

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
        QMessageBox.information(
            self,
            "Edit Emulator",
            "Use the emulator card settings button to edit an installed emulator.",
        )

    def _on_remove_emulator(self):
        QMessageBox.information(
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
        if hasattr(self, "_chk_vsync"):
            self._cfg.vsync = self._chk_vsync.isChecked()
            self._cfg.gpu_accelerated_ui = self._chk_gpu_ui.isChecked()

        # Performance  (page 2)
        if hasattr(self, "_chk_limit_bg_cpu"):
            self._cfg.limit_background_cpu = self._chk_limit_bg_cpu.isChecked()
            self._cfg.scan_threads = self._spin_threads.value()
            self._cfg.background_fps = self._spin_bg_fps.value()
            self._cfg.gpu_backend = self._combo_gpu_backend.currentText()
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

        # Input  (page 4)
        if hasattr(self, "_input_player_controls"):
            self._cfg.input_player_settings = self._collect_input_player_settings()
        if hasattr(self, "_controller_profiles"):
            self._cfg.controller_profiles = copy.deepcopy(self._controller_profiles)
            self._cfg.active_controller_profile = str(
                getattr(self, "_active_controller_profile", "")
            )

        # Emulator BIOS files  (page 5 / Emulators > Configuration)
        if hasattr(self, "_bios_path_inputs"):
            bios_paths: dict[str, str] = {}
            for bios_id, le in self._bios_path_inputs.items():
                path = le.text().strip()
                if path:
                    bios_paths[bios_id] = path
            self._cfg.bios_files = bios_paths

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
            self._cfg.scraper_hash_matching = self._chk_hash_matching.isChecked()
            self._cfg.scraper_region_priority = self._scraper_region_combo.currentText()

        # Clock  (page 7 — Tools > Clock)
        if hasattr(self, "_chk_clock_show"):
            self._cfg.show_clock = self._chk_clock_show.isChecked()
            self._cfg.clock_source = self._clock_source.currentText()
            self._cfg.clock_timezone = self._clock_tz_combo.currentText()
            self._cfg.clock_fixed_date = self._clock_date.text()
            self._cfg.clock_fixed_time = self._clock_time.text()
            self._cfg.clock_format = self._clock_fmt.currentText()

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
            QMessageBox.warning(self, "Validation", "Emulator name is required.")
            self._txt_name.setFocus()
            return
        if not self._txt_path.text().strip():
            QMessageBox.warning(self, "Validation", "Executable path is required.")
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
        self.setWindowTitle(f"{entry.display_name()} — Settings")
        self.setMinimumSize(480, 380)

        self._entry = entry
        self._cfg = config

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
        g_g.addWidget(_disabled_check("Pass fullscreen flag on launch"))
        g_g.addWidget(_disabled_check("Use exclusive fullscreen"))

        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Resolution override:"))
        combo = QComboBox()
        combo.addItems(["Default", "720p", "1080p", "1440p", "4K"])
        combo.setEnabled(False)
        res_row.addWidget(combo, 1)
        g_g.addLayout(res_row)

        layout.addWidget(grp_gfx)

        # -- Behaviour -------------------------------------------------
        grp_beh = QGroupBox("Behaviour")
        g_b = QVBoxLayout(grp_beh)
        g_b.setSpacing(8)
        g_b.addWidget(_disabled_check("Close Meridian while running"))
        g_b.addWidget(_disabled_check("Auto-save state on exit"))
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

    def _on_save(self):
        self._entry.path = self._txt_exe.text().strip()
        self._entry.args = self._txt_args.text().strip() or '"{rom}"'
        self._entry.rom_directory = self._txt_rom_dir.text().strip()
        self.accept()


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
    # SDL2 Game Controller standard:
    #   Axis 0 = Left X,  Axis 1 = Left Y  (positive = right / down)
    #   Axis 2 = Right X, Axis 3 = Right Y (positive = right / down)
    #   Axis 4 = Left Trigger, Axis 5 = Right Trigger (positive = pressed)
    "ls_up": "Axis 1-", "ls_down": "Axis 1+",
    "ls_left": "Axis 0-", "ls_right": "Axis 0+",
    "ls_press": "Button 7",
    "rs_up": "Axis 3-", "rs_down": "Axis 3+",
    "rs_left": "Axis 2-", "rs_right": "Axis 2+",
    "rs_press": "Button 8",
    "dp_up": "Button 11", "dp_down": "Button 12",
    "dp_left": "Button 13", "dp_right": "Button 14",
    # Nintendo layout: A=east(1), B=south(0), X=north(3), Y=west(2)
    "a": "Button 1", "b": "Button 0",
    "x": "Button 3", "y": "Button 2",
    "l": "Button 9", "r": "Button 10",
    "zl": "Axis 4+", "zr": "Axis 5+",
    "minus": "Button 4", "plus": "Button 6",
    "capture": "Button 15", "home": "Button 5",
    "motion": "Gyro",
}


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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._device_fn = device_fn or (lambda: "Any Available")
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
