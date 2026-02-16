"""
Persistent application configuration for Meridian.

Settings are stored as a JSON file in the OS-appropriate config directory
(``%APPDATA%/Meridian`` on Windows).  The module exposes a single
:class:`Config` instance that the rest of the app imports.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, asdict
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


# -- Scraper source profiles -----------------------------------------------

@dataclass
class ScraperSourceInfo:
    """Describes a scraper source's API requirements and capabilities."""
    id: str
    name: str
    url: str
    auth_fields: list       # [(key, label, placeholder, is_secret), ...]
    content: list[str]      # content IDs this source can fetch
    artwork: list[str]      # artwork IDs this source can fetch
    supports_hash: bool = False
    supports_region_priority: bool = False
    supports_resolution: bool = True
    rate_limit_note: str = ""


SCRAPER_CONTENT_LABELS: dict[str, str] = {
    "title":        "Game title",
    "description":  "Description / summary",
    "storyline":    "Storyline",
    "genre":        "Genre",
    "release_date": "Release date",
    "developer":    "Developer",
    "publisher":    "Publisher",
    "players":      "Number of players",
    "rating":       "Rating",
    "region":       "Region",
    "language":     "Language",
    "themes":       "Themes / keywords",
}

SCRAPER_ARTWORK_LABELS: dict[str, str] = {
    "front_box":     "Front box art",
    "back_box":      "Back box art",
    "3d_box":        "3D box art",
    "screenshots":   "In-game screenshots",
    "title_screen":  "Title screen",
    "fan_art":       "Fan art",
    "banner":        "Banner",
    "marquee":       "Marquee / wheel art",
    "video_snaps":   "Video snaps",
    "manual":        "Manual",
    "disc_art":      "Disc art",
    "clear_logo":    "Clear logo",
    "promo_art":     "Promotional art",
}

SCRAPER_SOURCES: list[ScraperSourceInfo] = [
    ScraperSourceInfo(
        id="screenscraper",
        name="ScreenScraper",
        url="https://screenscraper.fr",
        auth_fields=[
            ("username", "Username:", "ScreenScraper username", False),
            ("password", "Password:", "ScreenScraper password", True),
        ],
        content=["title", "description", "genre", "release_date",
                 "developer", "publisher", "players", "rating",
                 "region", "language"],
        artwork=["front_box", "back_box", "3d_box", "screenshots",
                 "title_screen", "fan_art", "marquee", "video_snaps",
                 "manual"],
        supports_hash=True,
        supports_region_priority=True,
    ),
    ScraperSourceInfo(
        id="thegamesdb",
        name="TheGamesDB",
        url="https://thegamesdb.net",
        auth_fields=[
            ("api_key", "API Key:", "TheGamesDB developer API key", True),
        ],
        content=["title", "description", "genre", "release_date",
                 "developer", "publisher", "players", "rating"],
        artwork=["front_box", "back_box", "screenshots",
                 "fan_art", "banner", "clear_logo"],
    ),
    ScraperSourceInfo(
        id="igdb",
        name="IGDB",
        url="https://igdb.com",
        auth_fields=[
            ("client_id", "Twitch Client ID:", "Twitch application Client ID", False),
            ("client_secret", "Client Secret:", "Twitch application Client Secret", True),
        ],
        content=["title", "description", "storyline", "genre", "release_date",
                 "developer", "publisher", "players", "rating", "themes"],
        artwork=["front_box", "screenshots", "fan_art", "video_snaps"],
    ),
    ScraperSourceInfo(
        id="launchbox",
        name="LaunchBox DB",
        url="https://gamesdb.launchbox-app.com",
        auth_fields=[],
        content=["title", "description", "genre", "release_date",
                 "developer", "publisher", "players", "rating"],
        artwork=["front_box", "back_box", "3d_box", "screenshots",
                 "fan_art", "banner", "disc_art", "clear_logo"],
    ),
    ScraperSourceInfo(
        id="mobygames",
        name="MobyGames",
        url="https://mobygames.com",
        auth_fields=[
            ("api_key", "API Key:", "MobyGames API key", True),
        ],
        content=["title", "description", "genre", "release_date",
                 "developer", "publisher", "rating"],
        artwork=["front_box", "back_box", "screenshots", "promo_art"],
        rate_limit_note="Free tier limited to 720 requests/hour (1 per 5 seconds).",
    ),
    ScraperSourceInfo(
        id="openretro",
        name="OpenRetro",
        url="https://openretro.org",
        auth_fields=[],
        content=["title", "description", "genre", "release_date",
                 "developer", "publisher"],
        artwork=["front_box", "screenshots"],
        rate_limit_note="Limited database coverage. Best suited for Amiga and classic computer games.",
    ),
]

SCRAPER_SOURCE_NAMES: list[str] = [s.name for s in SCRAPER_SOURCES]
SCRAPER_SOURCE_MAP: dict[str, ScraperSourceInfo] = {s.name: s for s in SCRAPER_SOURCES}


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

    # UI / Appearance
    theme: str = "Default"
    ui_scale: int = 3                  # 1-5 density
    font_family: str = "Ubuntu"
    font_size_label: str = "Medium"    # Small / Medium / Large / Extra Large
    bold_text: bool = False
    reduced_motion: bool = False
    high_contrast: bool = False

    # Background
    bg_type: str = "None"              # None / Image / Animation
    bg_image_path: str = ""
    bg_animation: str = ""             # e.g. "Waves"

    # Graphics — Display
    remember_window_geometry: bool = False
    borderless_fullscreen: bool = False

    # Graphics — Rendering  (vsync + gpu_accel are applied at startup)
    vsync: bool = True
    gpu_accelerated_ui: bool = False

    # Performance — CPU
    limit_background_cpu: bool = False
    scan_threads: int = 4              # 1-16
    background_fps: int = 30           # animation fps when window unfocused

    # Performance — GPU
    gpu_backend: str = "Auto"          # Auto / OpenGL / Software

    # Performance — Cache
    cache_box_art: bool = True
    cache_metadata: bool = True
    cache_max_mb: int = 512            # max disk cache in MB
    thumbnail_resolution: str = "Medium"  # Low / Medium / High

    # Scraper
    scraper_source: str = "ScreenScraper"
    scraper_credentials: dict = field(default_factory=dict)  # {source_name: {key: value}}
    scraper_content: dict = field(default_factory=lambda: {
        "title": True, "description": True, "genre": True,
        "release_date": True, "developer": True, "publisher": True,
        "players": True, "rating": True,
    })
    scraper_artwork: dict = field(default_factory=lambda: {
        "front_box": True, "back_box": True, "screenshots": True,
        "title_screen": True,
    })
    scraper_max_resolution: str = "Original"
    scraper_auto_scrape: bool = False
    scraper_overwrite: bool = False
    scraper_prefer_local: bool = False
    scraper_hash_matching: bool = True
    scraper_region_priority: str = "USA"

    # Audio
    audio_output_device: str = "Default"
    audio_input_device: str = "None"
    audio_channel_mode: str = "Stereo"    # Stereo / Mono
    audio_volume: int = 100               # 0-100
    audio_mute: bool = False
    audio_mute_background: bool = True
    audio_mute_unfocused_emu: bool = False

    # Clock
    show_clock: bool = False
    clock_source: str = "System clock"   # System clock / Selected timezone / Fixed time
    clock_timezone: str = "UTC"
    clock_fixed_date: str = ""
    clock_fixed_time: str = ""
    clock_format: str = "12-hour"        # 12-hour / 24-hour

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
        """Load from disk, returning defaults if the file is missing or bad.

        Unknown keys in the JSON (left over from older versions) are
        silently ignored so that adding or removing Config fields never
        causes a crash.
        """
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
            # Drop keys the current Config doesn't know about
            known = {f.name for f in fields(cls)}
            raw = {k: v for k, v in raw.items() if k in known}
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
