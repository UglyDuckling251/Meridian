"""
Persistent application configuration for Meridian.

Settings are stored as a JSON file in the OS-appropriate config directory
(``%APPDATA%/Meridian`` on Windows).  The module exposes a single
:class:`Config` instance that the rest of the app imports.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from PySide6.QtCore import QStandardPaths


# -- Defaults --------------------------------------------------------------

_APP_DIR_NAME = "Meridian"
_CONFIG_FILE  = "settings.json"


def _config_dir() -> Path:
    """Return (and create) the per-user config directory."""
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation,
    )
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


# -- Known systems ---------------------------------------------------------

KNOWN_SYSTEMS: list[tuple[str, str, str]] = [
    # (id, display_name, common_extensions)
    ("nes",        "Nintendo Entertainment System (NES)",     ".nes,.zip"),
    ("snes",       "Super Nintendo (SNES)",                   ".sfc,.smc,.zip"),
    ("n64",        "Nintendo 64",                             ".n64,.z64,.v64,.zip"),
    ("gc",         "Nintendo GameCube",                       ".iso,.gcm,.ciso"),
    ("wii",        "Nintendo Wii",                            ".iso,.wbfs,.ciso"),
    ("wiiu",       "Nintendo Wii U",                          ".wud,.wux,.rpx"),
    ("switch",     "Nintendo Switch",                         ".nsp,.xci"),
    ("gb",         "Game Boy",                                ".gb,.zip"),
    ("gbc",        "Game Boy Color",                          ".gbc,.zip"),
    ("gba",        "Game Boy Advance",                        ".gba,.zip"),
    ("nds",        "Nintendo DS",                             ".nds,.zip"),
    ("3ds",        "Nintendo 3DS",                            ".3ds,.cia,.cxi"),
    ("genesis",    "Sega Genesis / Mega Drive",               ".bin,.md,.gen,.zip"),
    ("saturn",     "Sega Saturn",                             ".iso,.bin,.cue"),
    ("dreamcast",  "Sega Dreamcast",                          ".gdi,.cdi,.chd"),
    ("sms",        "Sega Master System",                      ".sms,.zip"),
    ("gg",         "Sega Game Gear",                          ".gg,.zip"),
    ("ps1",        "PlayStation",                             ".bin,.cue,.iso,.chd"),
    ("ps2",        "PlayStation 2",                           ".iso,.bin,.chd"),
    ("ps3",        "PlayStation 3",                           ".iso,.pkg"),
    ("psp",        "PlayStation Portable",                    ".iso,.cso"),
    ("psvita",     "PlayStation Vita",                        ".vpk,.mai"),
    ("xbox",       "Xbox",                                    ".iso,.xiso"),
    ("xbox360",    "Xbox 360",                                ".iso,.xex"),
    ("atari2600",  "Atari 2600",                              ".a26,.bin,.zip"),
    ("atari7800",  "Atari 7800",                              ".a78,.bin,.zip"),
    ("lynx",       "Atari Lynx",                              ".lnx,.zip"),
    ("jaguar",     "Atari Jaguar",                            ".j64,.jag,.zip"),
    ("tg16",       "TurboGrafx-16 / PC Engine",              ".pce,.zip"),
    ("ngp",        "Neo Geo Pocket",                          ".ngp,.ngc,.zip"),
    ("neogeo",     "Neo Geo (Arcade)",                        ".zip"),
    ("mame",       "MAME (Arcade)",                           ".zip"),
    ("3do",        "3DO Interactive",                          ".iso,.bin,.cue"),
    ("vectrex",    "Vectrex",                                 ".vec,.bin,.zip"),
    ("wonderswan", "WonderSwan / WonderSwan Color",           ".ws,.wsc,.zip"),
    ("msx",        "MSX / MSX2",                              ".rom,.mx1,.mx2,.zip"),
    ("dos",        "MS-DOS",                                  ".exe,.com,.bat"),
    ("pc",         "PC (Windows)",                            ".exe,.lnk,.url"),
]

SYSTEM_NAMES: dict[str, str] = {sid: name for sid, name, _ in KNOWN_SYSTEMS}
SYSTEM_EXTENSIONS: dict[str, str] = {sid: ext for sid, _, ext in KNOWN_SYSTEMS}


# -- Emulator catalog (available emulators per system) ---------------------
# Each entry: (emulator_name, homepage_url, [supported_system_ids])

EMULATOR_CATALOG: list[tuple[str, str, list[str]]] = [
    ("RetroArch",   "https://www.retroarch.com/",
     ["nes", "snes", "n64", "gb", "gbc", "gba", "nds", "genesis", "sms", "gg",
      "saturn", "dreamcast", "ps1", "psp", "atari2600", "atari7800", "lynx",
      "jaguar", "tg16", "ngp", "neogeo", "mame", "3do", "vectrex", "wonderswan", "msx"]),
    ("Dolphin",     "https://dolphin-emu.org/",
     ["gc", "wii"]),
    ("Cemu",        "https://cemu.info/",
     ["wiiu"]),
    ("Ryujinx",     "https://ryujinx.org/",
     ["switch"]),
    ("melonDS",     "https://melonds.kuribo64.net/",
     ["nds"]),
    ("Lime3DS",     "https://github.com/Lime3DS/Lime3DS",
     ["3ds"]),
    ("mGBA",        "https://mgba.io/",
     ["gb", "gbc", "gba"]),
    ("DeSmuME",     "https://desmume.org/",
     ["nds"]),
    ("Snes9x",      "https://www.snes9x.com/",
     ["snes"]),
    ("PCSX2",       "https://pcsx2.net/",
     ["ps2"]),
    ("RPCS3",       "https://rpcs3.net/",
     ["ps3"]),
    ("PPSSPP",      "https://www.ppsspp.org/",
     ["psp"]),
    ("DuckStation", "https://github.com/stenzek/duckstation",
     ["ps1"]),
    ("Xemu",        "https://xemu.app/",
     ["xbox"]),
    ("Xenia",       "https://xenia.jp/",
     ["xbox360"]),
    ("Flycast",     "https://github.com/flyinghead/flycast",
     ["dreamcast"]),
    ("MAME",        "https://www.mamedev.org/",
     ["mame", "neogeo", "atari2600", "atari7800", "3do", "vectrex"]),
    ("Mednafen",    "https://mednafen.github.io/",
     ["nes", "snes", "gb", "gbc", "gba", "genesis", "saturn", "ps1", "tg16",
      "ngp", "lynx", "wonderswan"]),
    ("Vita3K",      "https://vita3k.org/",
     ["psvita"]),
    ("DOSBox-X",    "https://dosbox-x.com/",
     ["dos"]),
    ("Ares",        "https://ares-emu.net/",
     ["nes", "snes", "n64", "gb", "gbc", "gba", "genesis", "sms", "gg",
      "saturn", "tg16", "ngp", "wonderswan", "msx"]),
]


def emulators_for_system(system_id: str) -> list[tuple[str, str]]:
    """Return [(name, url)] of emulators that support the given system."""
    result = []
    for name, url, systems in EMULATOR_CATALOG:
        if system_id in systems:
            result.append((name, url))
    return result


# -- Emulator entry --------------------------------------------------------

@dataclass
class EmulatorEntry:
    """One configured emulator."""
    name: str = ""
    path: str = ""
    args: str = '"{rom}"'

    def display_name(self) -> str:
        return self.name or "(unnamed)"


# -- System entry ----------------------------------------------------------

@dataclass
class SystemEntry:
    """Configuration for one game system / console."""
    system_id: str = ""
    rom_directory: str = ""
    emulator_name: str = ""
    enabled: bool = True


# -- Config data -----------------------------------------------------------

@dataclass
class Config:
    """All user-facing settings.  Serialises to / from JSON."""

    # General
    start_maximized: bool = False
    confirm_on_exit: bool = True

    # Legacy flat ROM directories (kept for backwards compat)
    rom_directories: list[str] = field(default_factory=list)

    # Emulators (global registry of available emulators)
    emulators: list[EmulatorEntry] = field(default_factory=list)

    # Per-system configuration
    systems: list[SystemEntry] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> Config:
        """Load from disk, returning defaults if the file is missing or bad."""
        path = _config_dir() / _CONFIG_FILE
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            emulators = [
                EmulatorEntry(**e) for e in raw.pop("emulators", [])
            ]
            systems = [
                SystemEntry(**s) for s in raw.pop("systems", [])
            ]
            return cls(**raw, emulators=emulators, systems=systems)
        except Exception:
            return cls()

    def save(self) -> None:
        """Write current settings to disk."""
        path = _config_dir() / _CONFIG_FILE
        data = asdict(self)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def add_rom_directory(self, directory: str) -> bool:
        """Add a directory if not already present.  Returns True if added."""
        normed = str(Path(directory).resolve())
        if normed not in self.rom_directories:
            self.rom_directories.append(normed)
            return True
        return False

    def remove_rom_directory(self, index: int) -> None:
        if 0 <= index < len(self.rom_directories):
            self.rom_directories.pop(index)

    def add_emulator(self, entry: EmulatorEntry) -> None:
        self.emulators.append(entry)

    def remove_emulator(self, index: int) -> None:
        if 0 <= index < len(self.emulators):
            self.emulators.pop(index)

    def emulator_names(self) -> list[str]:
        """Return a list of all configured emulator display names."""
        return [e.display_name() for e in self.emulators]
