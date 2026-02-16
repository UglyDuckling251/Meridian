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
from typing import Any

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


@dataclass(frozen=True)
class EmulatorCatalogEntry:
    """Catalog metadata used by the UI and installer pipeline."""
    id: str
    name: str
    homepage_url: str
    systems: list[str]
    release_provider: str = "github"
    release_source: str = ""           # github owner/repo or URL
    install_strategy: str = "archive"  # archive/exe/retroarch_core/manual
    install_subdir: str = ""
    exe_candidates: list[str] = field(default_factory=list)
    default_args: str = '"{rom}"'
    asset_include: list[str] = field(default_factory=list)
    asset_exclude: list[str] = field(default_factory=list)
    preferred_version: str = ""        # optional pinned version label
    preferred_download_url: str = ""   # optional pinned direct asset URL
    windows_supported: bool = True
    notes: str = ""


EMULATOR_CATALOG: list[EmulatorCatalogEntry] = [
    EmulatorCatalogEntry(
        id="retroarch",
        name="RetroArch",
        homepage_url="https://github.com/libretro/RetroArch",
        systems=["nes", "snes", "n64", "gb", "gbc", "gba", "nds", "genesis", "sms", "gg",
                 "saturn", "dreamcast", "ps1", "psp", "atari2600", "atari7800", "lynx",
                 "jaguar", "tg16", "ngp", "neogeo", "mame", "3do", "vectrex", "wonderswan", "msx"],
        release_provider="direct",
        release_source="https://buildbot.libretro.com/stable/1.22.2/windows/x86_64/RetroArch-Win64-setup.exe",
        install_strategy="installer",
        install_subdir="retroarch",
        exe_candidates=["retroarch.exe"],
        default_args='-L "{core}" "{rom}"',
        asset_include=["win64", ".exe"],
        asset_exclude=["debug", "symbols", "source"],
        preferred_version="1.22.2",
        preferred_download_url="https://buildbot.libretro.com/stable/1.22.2/windows/x86_64/RetroArch-Win64-setup.exe",
    ),
    EmulatorCatalogEntry(
        id="mednafen",
        name="Mednafen",
        homepage_url="https://mednafen.github.io/",
        systems=["nes", "snes", "gb", "gbc", "gba", "genesis", "saturn", "ps1", "tg16",
                 "ngp", "lynx", "wonderswan"],
        release_provider="direct",
        release_source="https://mednafen.github.io/releases/files/mednafen-1.32.1-win64.zip",
        install_strategy="archive",
        install_subdir="mednafen",
        exe_candidates=["mednafen.exe"],
        asset_include=["win", ".zip"],
        preferred_version="1.32.1",
        preferred_download_url="https://mednafen.github.io/releases/files/mednafen-1.32.1-win64.zip",
    ),
    EmulatorCatalogEntry(
        id="fceux",
        name="FCEUX",
        homepage_url="https://github.com/TASEmulators/fceux",
        systems=["nes"],
        release_provider="direct",
        release_source="https://github.com/TASEmulators/fceux/releases/download/v2.6.6/fceux-2.6.6-win64.zip",
        install_strategy="archive",
        install_subdir="fceux",
        exe_candidates=["fceux.exe"],
        asset_include=["win", ".zip"],
        preferred_version="2.6.6",
        preferred_download_url="https://github.com/TASEmulators/fceux/releases/download/v2.6.6/fceux-2.6.6-win64.zip",
    ),
    EmulatorCatalogEntry(
        id="nestopia_ue",
        name="Nestopia UE",
        homepage_url="https://github.com/0ldsk00l/nestopia",
        systems=["nes"],
        release_provider="direct",
        release_source="https://github.com/0ldsk00l/nestopia/releases/download/1.53.2/nestopia_1.53.2-win32.zip",
        install_strategy="archive",
        install_subdir="nestopia-ue",
        exe_candidates=["nestopia.exe"],
        asset_include=["win", ".zip"],
        preferred_version="1.53.2",
        preferred_download_url="https://github.com/0ldsk00l/nestopia/releases/download/1.53.2/nestopia_1.53.2-win32.zip",
    ),
    EmulatorCatalogEntry(
        id="mesen",
        name="Mesen",
        homepage_url="https://github.com/SourMesen/Mesen2",
        systems=["nes"],
        release_provider="direct",
        release_source="https://github.com/SourMesen/Mesen2/releases/download/2.1.1/Mesen_2.1.1_Windows.zip",
        install_strategy="archive",
        install_subdir="mesen",
        exe_candidates=["Mesen.exe"],
        asset_include=["win", ".zip"],
        preferred_version="2.1.1",
        preferred_download_url="https://github.com/SourMesen/Mesen2/releases/download/2.1.1/Mesen_2.1.1_Windows.zip",
    ),
    EmulatorCatalogEntry(
        id="snes9x",
        name="Snes9x",
        homepage_url="https://github.com/snes9xgit/snes9x",
        systems=["snes"],
        release_source="snes9xgit/snes9x",
        install_strategy="archive",
        install_subdir="snes9x",
        exe_candidates=["snes9x-x64.exe", "snes9x.exe"],
        asset_include=["win", "x64", ".zip"],
        asset_exclude=["libretro"],
    ),
    EmulatorCatalogEntry(
        id="bsnes",
        name="bsnes",
        homepage_url="https://github.com/bsnes-emu/bsnes",
        systems=["snes"],
        release_source="bsnes-emu/bsnes",
        install_strategy="archive",
        install_subdir="bsnes",
        exe_candidates=["bsnes.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="higan",
        name="higan",
        homepage_url="https://github.com/higan-emu/higan",
        systems=["snes"],
        release_source="higan-emu/higan",
        install_strategy="manual",
        install_subdir="higan",
        exe_candidates=["higan.exe"],
        asset_include=["win", ".zip"],
        notes="No reliable Windows release asset feed; install manually.",
    ),
    EmulatorCatalogEntry(
        id="mesen_s",
        name="Mesen-S",
        homepage_url="https://github.com/SourMesen/Mesen-S",
        systems=["snes"],
        release_source="SourMesen/Mesen-S",
        install_strategy="archive",
        install_subdir="mesen-s",
        exe_candidates=["Mesen-S.exe", "MesenS.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="mupen64plus_core",
        name="Mupen64Plus (Core)",
        homepage_url="https://github.com/mupen64plus/mupen64plus-core",
        systems=["n64"],
        release_source="mupen64plus/mupen64plus-core",
        install_strategy="manual",
        install_subdir="mupen64plus-core",
        windows_supported=False,
        notes="Core library; not a standalone frontend executable.",
    ),
    EmulatorCatalogEntry(
        id="dolphin",
        name="Dolphin",
        homepage_url="https://dolphin-emu.org/",
        systems=["gc", "wii"],
        release_provider="direct",
        release_source="https://dl.dolphin-emu.org/releases/2512/dolphin-2512-x64.7z",
        install_strategy="archive",
        install_subdir="dolphin",
        exe_candidates=["Dolphin.exe"],
        asset_include=["dolphin", "x64", ".7z"],
        asset_exclude=["debug", "symbols", "source"],
        preferred_version="2512",
        preferred_download_url="https://dl.dolphin-emu.org/releases/2512/dolphin-2512-x64.7z",
    ),
    EmulatorCatalogEntry(
        id="cemu",
        name="Cemu",
        homepage_url="https://github.com/cemu-project/Cemu",
        systems=["wiiu"],
        release_source="cemu-project/Cemu",
        install_strategy="archive",
        install_subdir="cemu",
        exe_candidates=["Cemu.exe"],
        asset_include=["windows", "x64", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="decaf",
        name="Decaf",
        homepage_url="https://github.com/decaf-emu/decaf-emu",
        systems=["wiiu"],
        release_source="decaf-emu/decaf-emu",
        install_strategy="archive",
        install_subdir="decaf",
        exe_candidates=["decaf-qt.exe", "decaf.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="ryujinx",
        name="Ryujinx",
        homepage_url="https://github.com/Ryujinx-NX/Ryujinx",
        systems=["switch"],
        release_source="Ryujinx-NX/Ryujinx",
        install_strategy="archive",
        install_subdir="ryujinx",
        exe_candidates=["Ryujinx.exe"],
        asset_include=["windows", "x86_64", ".zip"],
        asset_exclude=["pdb", "symbols", "debug"],
        notes="Original Ryujinx is discontinued. Use Ryubing instead.",
    ),
    EmulatorCatalogEntry(
        id="ryubing",
        name="Ryubing",
        homepage_url="https://git.ryujinx.app/ryubing/ryujinx",
        systems=["switch"],
        release_provider="direct",
        release_source="https://git.ryujinx.app/api/v4/projects/1/packages/generic/Ryubing/1.3.3/ryujinx-1.3.3-win_x64.zip",
        install_strategy="archive",
        install_subdir="ryubing",
        exe_candidates=["Ryujinx.exe"],
        asset_include=["win", "x64", ".zip"],
        asset_exclude=["pdb", "symbols", "debug"],
        preferred_version="1.3.3",
        preferred_download_url="https://git.ryujinx.app/api/v4/projects/1/packages/generic/Ryubing/1.3.3/ryujinx-1.3.3-win_x64.zip",
    ),
    EmulatorCatalogEntry(
        id="eden",
        name="Eden",
        homepage_url="https://github.com/eden-emulator/Releases",
        systems=["switch"],
        release_source="eden-emulator/Releases",
        install_strategy="archive",
        install_subdir="eden",
        exe_candidates=["eden.exe", "eden-qt.exe", "yuzu.exe"],
        asset_include=["windows", "msvc", ".zip"],
        asset_exclude=["mingw", "arm64", "aarch64", "pgo"],
    ),
    EmulatorCatalogEntry(
        id="sameboy",
        name="SameBoy",
        homepage_url="https://github.com/LIJI32/SameBoy",
        systems=["gb", "gbc"],
        release_source="LIJI32/SameBoy",
        install_strategy="archive",
        install_subdir="sameboy",
        exe_candidates=["sameboy.exe", "SameBoy.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="mgba",
        name="mGBA",
        homepage_url="https://github.com/mgba-emu/mgba",
        systems=["gb", "gbc", "gba"],
        release_source="mgba-emu/mgba",
        install_strategy="archive",
        install_subdir="mgba",
        exe_candidates=["mGBA.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="desmume",
        name="DeSmuME",
        homepage_url="https://github.com/TASEmulators/desmume",
        systems=["nds"],
        release_source="TASEmulators/desmume",
        install_strategy="archive",
        install_subdir="desmume",
        exe_candidates=["desmume.exe", "DeSmuME.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="melonds",
        name="melonDS",
        homepage_url="https://github.com/melonDS-emu/melonDS",
        systems=["nds"],
        release_source="melonDS-emu/melonDS",
        install_strategy="archive",
        install_subdir="melonds",
        exe_candidates=["melonDS.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="citra",
        name="Citra",
        homepage_url="https://archive.org/details/citra-emu_202403",
        systems=["3ds"],
        release_provider="direct",
        release_source="https://archive.org/download/citra-emu_202403/citra-windows-msvc-20240303-0ff3440_nightly.zip",
        install_strategy="archive",
        install_subdir="citra",
        exe_candidates=["citra-qt.exe", "citra.exe"],
        asset_include=["citra", "windows", ".zip"],
        asset_exclude=["source", "symbols", "debug"],
        preferred_version="20240303-0ff3440_nightly",
        preferred_download_url="https://archive.org/download/citra-emu_202403/citra-windows-msvc-20240303-0ff3440_nightly.zip",
    ),
    EmulatorCatalogEntry(
        id="flycast",
        name="Flycast",
        homepage_url="https://github.com/flyinghead/flycast",
        systems=["dreamcast"],
        release_source="flyinghead/flycast",
        install_strategy="archive",
        install_subdir="flycast",
        exe_candidates=["flycast.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="duckstation",
        name="DuckStation",
        homepage_url="https://github.com/stenzek/duckstation",
        systems=["ps1"],
        release_source="stenzek/duckstation",
        install_strategy="archive",
        install_subdir="duckstation",
        exe_candidates=["duckstation-qt-x64-ReleaseLTCG.exe", "duckstation-qt.exe"],
        asset_include=["windows", "x64", ".zip", ".7z"],
        asset_exclude=["pdb", "symbols", "debug", "arm64", "aarch64"],
    ),
    EmulatorCatalogEntry(
        id="pcsx2",
        name="PCSX2",
        homepage_url="https://github.com/PCSX2/pcsx2",
        systems=["ps2"],
        release_source="PCSX2/pcsx2",
        install_strategy="archive",
        install_subdir="pcsx2",
        exe_candidates=["pcsx2-qt.exe"],
        asset_include=["windows", ".7z"],
        asset_exclude=["symbols", "pdb"],
    ),
    EmulatorCatalogEntry(
        id="rpcs3",
        name="RPCS3",
        homepage_url="https://github.com/RPCS3/rpcs3",
        systems=["ps3"],
        release_source="RPCS3/rpcs3",
        install_strategy="archive",
        install_subdir="rpcs3",
        exe_candidates=["rpcs3.exe"],
        asset_include=["windows", ".7z", ".zip"],
        asset_exclude=["symbols", "pdb", "debug"],
    ),
    EmulatorCatalogEntry(
        id="ppsspp",
        name="PPSSPP",
        homepage_url="https://www.ppsspp.org/",
        systems=["psp"],
        release_provider="direct",
        release_source="https://www.ppsspp.org/files/1_19_3/ppsspp_win.zip",
        install_strategy="archive",
        install_subdir="ppsspp",
        exe_candidates=["PPSSPPWindows64.exe", "PPSSPPWindows.exe", "PPSSPPQt.exe"],
        asset_include=["ppsspp", "win", ".zip"],
        asset_exclude=["android", "ios", "source", "symbols", "debug"],
        preferred_version="1.19.3",
        preferred_download_url="https://www.ppsspp.org/files/1_19_3/ppsspp_win.zip",
    ),
    EmulatorCatalogEntry(
        id="vita3k",
        name="Vita3K",
        homepage_url="https://github.com/Vita3K/Vita3K",
        systems=["psvita"],
        release_source="Vita3K/Vita3K",
        install_strategy="archive",
        install_subdir="vita3k",
        exe_candidates=["Vita3K.exe"],
        asset_include=["windows", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="xemu",
        name="Xemu",
        homepage_url="https://github.com/xemu-project/xemu",
        systems=["xbox"],
        release_source="xemu-project/xemu",
        install_strategy="archive",
        install_subdir="xemu",
        exe_candidates=["xemu.exe"],
        asset_include=["windows", "x86_64", ".zip"],
        asset_exclude=["arm64", "pdb", "dbg", "debug", "macos", "appimage"],
    ),
    EmulatorCatalogEntry(
        id="xenia",
        name="Xenia",
        homepage_url="https://github.com/xenia-canary/xenia-canary-releases",
        systems=["xbox360"],
        release_source="xenia-canary/xenia-canary-releases",
        install_strategy="archive",
        install_subdir="xenia",
        exe_candidates=["xenia_canary.exe", "xenia.exe"],
        asset_include=["windows", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="stella",
        name="Stella",
        homepage_url="https://github.com/stella-emu/stella",
        systems=["atari2600"],
        release_source="stella-emu/stella",
        install_strategy="archive",
        install_subdir="stella",
        exe_candidates=["Stella.exe", "stella.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="mame",
        name="MAME",
        homepage_url="https://github.com/mamedev/mame",
        systems=["mame"],
        release_source="mamedev/mame",
        install_strategy="manual",
        install_subdir="mame",
        exe_candidates=["mame.exe", "mame64.exe"],
        asset_include=["win", "64", ".zip"],
        notes="Official binary packages are not reliably published through this GitHub repository.",
    ),
    EmulatorCatalogEntry(
        id="dosbox_staging",
        name="DOSBox Staging",
        homepage_url="https://github.com/dosbox-staging/dosbox-staging",
        systems=["dos", "pc"],
        release_source="dosbox-staging/dosbox-staging",
        install_strategy="archive",
        install_subdir="dosbox-staging",
        exe_candidates=["dosbox.exe"],
        asset_include=["win", "x64", ".zip"],
    ),
    # RetroArch core packages requested explicitly
    EmulatorCatalogEntry(
        id="genesis_plus_gx_core",
        name="Genesis Plus GX (Libretro Core)",
        homepage_url="https://github.com/libretro/Genesis-Plus-GX",
        systems=["genesis", "sms", "gg"],
        release_source="libretro/Genesis-Plus-GX",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="picodrive_core",
        name="PicoDrive (Libretro Core)",
        homepage_url="https://github.com/libretro/picodrive",
        systems=["genesis", "sms", "gg"],
        release_source="libretro/picodrive",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="beetle_saturn_core",
        name="Beetle Saturn (Libretro Core)",
        homepage_url="https://github.com/libretro/beetle-saturn-libretro",
        systems=["saturn"],
        release_source="libretro/beetle-saturn-libretro",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="prosystem_core",
        name="ProSystem (Libretro Core)",
        homepage_url="https://github.com/libretro/prosystem-libretro",
        systems=["atari7800"],
        release_source="libretro/prosystem-libretro",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="handy_core",
        name="Handy (Libretro Core)",
        homepage_url="https://github.com/libretro/handy-libretro",
        systems=["lynx"],
        release_source="libretro/handy-libretro",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="virtual_jaguar_core",
        name="Virtual Jaguar (Libretro Core)",
        homepage_url="https://github.com/libretro/virtualjaguar-libretro",
        systems=["jaguar"],
        release_source="libretro/virtualjaguar-libretro",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="beetle_pce_core",
        name="Beetle PCE (Mednafen Core)",
        homepage_url="https://github.com/libretro/beetle-pce-libretro",
        systems=["tg16"],
        release_source="libretro/beetle-pce-libretro",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="beetle_pce_fast_core",
        name="Beetle PCE Fast",
        homepage_url="https://github.com/libretro/beetle-pce-fast-libretro",
        systems=["tg16"],
        release_source="libretro/beetle-pce-fast-libretro",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
    EmulatorCatalogEntry(
        id="beetle_neopop_core",
        name="Beetle NeoPop",
        homepage_url="https://github.com/libretro/beetle-ngp-libretro",
        systems=["ngp"],
        release_source="libretro/beetle-ngp-libretro",
        install_strategy="retroarch_core",
        install_subdir="retroarch-cores",
        windows_supported=True,
    ),
]

EMULATOR_CATALOG_BY_ID: dict[str, EmulatorCatalogEntry] = {e.id: e for e in EMULATOR_CATALOG}
EMULATOR_CATALOG_BY_NAME: dict[str, EmulatorCatalogEntry] = {e.name: e for e in EMULATOR_CATALOG}


def emulators_for_system(system_id: str) -> list[tuple[str, str]]:
    """Return [(name, url)] of emulators that support the given system."""
    result = []
    for entry in EMULATOR_CATALOG:
        if entry.install_strategy == "retroarch_core":
            continue
        if system_id in entry.systems:
            result.append((entry.name, entry.homepage_url))
    return result


def emulator_catalog_entry(identifier: str) -> EmulatorCatalogEntry | None:
    """Look up a catalog entry by id or display name."""
    return EMULATOR_CATALOG_BY_ID.get(identifier) or EMULATOR_CATALOG_BY_NAME.get(identifier)


def systems_without_installable_emulator() -> list[str]:
    """Return system IDs that currently have no Windows-installable catalog entry."""
    coverage: dict[str, bool] = {sid: False for sid, _, _ in KNOWN_SYSTEMS}
    for item in EMULATOR_CATALOG:
        if item.install_strategy == "retroarch_core":
            continue
        if not item.windows_supported:
            continue
        for system_id in item.systems:
            if system_id in coverage:
                coverage[system_id] = True
    return [sid for sid, installed in coverage.items() if not installed]


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
    rom_directory: str = ""
    catalog_id: str = ""
    version: str = ""
    install_dir: str = ""
    provider: str = ""
    system_overrides: dict[str, str] = field(default_factory=dict)

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

    # Input
    # { "1": {"connected": bool, "device": str, "type": str}, ... }
    input_player_settings: dict = field(default_factory=dict)
    # Named controller profiles:
    # { "Profile Name": { "1": {"connected": bool, "device": str, "type": str}, ... }, ... }
    controller_profiles: dict = field(default_factory=dict)
    active_controller_profile: str = ""

    # BIOS file paths
    # { "<bios_id>": "C:/path/to/bios.bin", ... }
    bios_files: dict = field(default_factory=dict)

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
                _safe_dataclass_from_dict(EmulatorEntry, e) for e in raw.pop("emulators", [])
                if isinstance(e, dict)
            ]
            systems = [
                _safe_dataclass_from_dict(SystemEntry, s) for s in raw.pop("systems", [])
                if isinstance(s, dict)
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


def _safe_dataclass_from_dict(dataclass_type: type, value: dict[str, Any]):
    """Build dataclass instance while ignoring unknown serialized keys."""
    known = {f.name for f in fields(dataclass_type)}
    filtered = {k: v for k, v in value.items() if k in known}
    return dataclass_type(**filtered)
