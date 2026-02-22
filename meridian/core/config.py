# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

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
    # --- Nintendo ---
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
    ("vb",         "Virtual Boy",                             ".vb,.vboy,.zip"),
    ("nds",        "Nintendo DS",                             ".nds,.zip"),
    ("3ds",        "Nintendo 3DS",                            ".3ds,.cia,.cxi"),
    ("pokemini",   "Pokémon Mini",                            ".min,.zip"),
    # --- Sega ---
    ("genesis",    "Sega Genesis / Mega Drive",               ".bin,.md,.gen,.zip"),
    ("segacd",     "Sega CD / Mega CD",                       ".bin,.cue,.iso,.chd"),
    ("sega32x",    "Sega 32X",                                ".32x,.bin,.zip"),
    ("saturn",     "Sega Saturn",                             ".iso,.bin,.cue"),
    ("dreamcast",  "Sega Dreamcast",                          ".gdi,.cdi,.chd"),
    ("sms",        "Sega Master System",                      ".sms,.zip"),
    ("gg",         "Sega Game Gear",                          ".gg,.zip"),
    ("sg1000",     "Sega SG-1000",                            ".sg,.zip"),
    # --- Sony ---
    ("ps1",        "PlayStation",                             ".bin,.cue,.iso,.chd"),
    ("ps2",        "PlayStation 2",                           ".iso,.bin,.chd"),
    ("ps3",        "PlayStation 3",                           ".iso,.pkg"),
    ("psp",        "PlayStation Portable",                    ".iso,.cso"),
    ("psvita",     "PlayStation Vita",                        ".vpk,.mai"),
    # --- Microsoft ---
    ("xbox",       "Xbox",                                    ".iso,.xiso"),
    ("xbox360",    "Xbox 360",                                ".iso,.xex"),
    # --- Atari ---
    ("atari2600",  "Atari 2600",                              ".a26,.bin,.zip"),
    ("atari5200",  "Atari 5200",                              ".a52,.bin,.zip"),
    ("atari7800",  "Atari 7800",                              ".a78,.bin,.zip"),
    ("lynx",       "Atari Lynx",                              ".lnx,.zip"),
    ("jaguar",     "Atari Jaguar",                            ".j64,.jag,.zip"),
    ("atarist",    "Atari ST / STE / Falcon",                 ".st,.stx,.msa,.zip"),
    # --- NEC ---
    ("tg16",       "TurboGrafx-16 / PC Engine",              ".pce,.zip"),
    ("pcfx",       "NEC PC-FX",                               ".bin,.cue,.iso"),
    ("pc98",       "NEC PC-98",                                ".hdi,.fdi,.d88,.zip"),
    # --- SNK ---
    ("ngp",        "Neo Geo Pocket",                          ".ngp,.ngc,.zip"),
    ("neogeo",     "Neo Geo (Arcade)",                        ".zip"),
    ("neocd",      "Neo Geo CD",                              ".bin,.cue,.iso,.chd"),
    # --- Arcade ---
    ("mame",       "MAME (Arcade)",                           ".zip"),
    # --- Other ---
    ("3do",        "3DO Interactive",                          ".iso,.bin,.cue"),
    ("vectrex",    "Vectrex",                                 ".vec,.bin,.zip"),
    ("wonderswan", "WonderSwan / WonderSwan Color",           ".ws,.wsc,.zip"),
    ("msx",        "MSX / MSX2",                              ".rom,.mx1,.mx2,.zip"),
    ("coleco",     "ColecoVision",                            ".col,.rom,.zip"),
    ("intv",       "Intellivision",                           ".int,.rom,.zip"),
    ("odyssey2",   "Magnavox Odyssey² / Videopac",            ".bin,.zip"),
    ("channelf",   "Fairchild Channel F",                     ".bin,.chf,.zip"),
    ("c64",        "Commodore 64",                            ".d64,.t64,.prg,.crt,.zip"),
    ("amiga",      "Commodore Amiga",                         ".adf,.ipf,.hdf,.zip"),
    ("cpc",        "Amstrad CPC",                             ".dsk,.sna,.tap,.zip"),
    ("zxspec",     "ZX Spectrum",                             ".z80,.tap,.tzx,.sna,.zip"),
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
    core_filename: str = ""            # DLL filename for retroarch_core entries
    release_year: int = 0              # original release year (for sorting/display)


def _core(cid: str, name: str, systems: list[str], dll: str, url: str = "", year: int = 0) -> EmulatorCatalogEntry:
    """Shorthand factory for RetroArch core catalog entries."""
    return EmulatorCatalogEntry(
        id=cid, name=name, homepage_url=url or f"https://github.com/libretro/{cid.replace('_core', '')}",
        systems=systems, install_strategy="retroarch_core", core_filename=dll, release_year=year,
    )


EMULATOR_CATALOG: list[EmulatorCatalogEntry] = [
    # =================================================================
    # RetroArch — required base (hidden from UI, auto-managed)
    # =================================================================
    EmulatorCatalogEntry(
        id="retroarch",
        name="RetroArch",
        homepage_url="https://github.com/libretro/RetroArch",
        systems=[],
        release_provider="direct",
        release_source="https://buildbot.libretro.com/stable/1.22.2/windows/x86_64/RetroArch.7z",
        install_strategy="archive",
        install_subdir="retroarch",
        exe_candidates=["retroarch.exe"],
        default_args='-L "{core}" "{rom}"',
        asset_include=["win64", ".7z"],
        asset_exclude=["debug", "symbols", "source", "setup"],
        preferred_version="1.22.2",
        preferred_download_url="https://buildbot.libretro.com/stable/1.22.2/windows/x86_64/RetroArch.7z",
    ),

    # === NES / Famicom ===
    _core("fceumm_core",      "FCEUmm",          ["nes"],             "fceumm_libretro.dll"),
    _core("nestopia_core",    "Nestopia UE",      ["nes"],             "nestopia_libretro.dll"),
    _core("mesen_core",       "Mesen",            ["nes"],             "mesen_libretro.dll"),
    _core("quicknes_core",    "QuickNES",         ["nes"],             "quicknes_libretro.dll"),
    _core("bnes_core",        "bnes",             ["nes"],             "bnes_libretro.dll"),
    # === SNES / Super Famicom ===
    _core("snes9x_core",           "Snes9x",               ["snes"],  "snes9x_libretro.dll"),
    _core("snes9x2010_core",       "Snes9x 2010",          ["snes"],  "snes9x2010_libretro.dll"),
    _core("bsnes_core",            "bsnes",                 ["snes"],  "bsnes_libretro.dll"),
    _core("bsnes_hd_core",         "bsnes-hd beta",        ["snes"],  "bsnes_hd_beta_libretro.dll"),
    _core("bsnes_jg_core",         "bsnes-jg",             ["snes"],  "bsnes_jg_libretro.dll"),
    _core("bsnes_mercury_core",    "bsnes-mercury",        ["snes"],  "bsnes_mercury_accuracy_libretro.dll"),
    _core("beetle_supafaust_core", "Beetle Supafaust",     ["snes"],  "mednafen_supafaust_libretro.dll"),
    _core("mesen_s_core",          "Mesen-S",              ["snes", "gb", "gbc"], "mesen-s_libretro.dll"),
    # === Nintendo 64 ===
    _core("mupen64plus_next_core", "Mupen64Plus-Next",     ["n64"],   "mupen64plus_next_libretro.dll"),
    _core("parallel_n64_core",     "ParaLLEl N64",         ["n64"],   "parallel_n64_libretro.dll"),
    # === Game Boy / Game Boy Color ===
    _core("gambatte_core",   "Gambatte",         ["gb", "gbc"],       "gambatte_libretro.dll"),
    _core("sameboy_core",    "SameBoy",          ["gb", "gbc"],       "sameboy_libretro.dll"),
    _core("gearboy_core",    "Gearboy",          ["gb", "gbc"],       "gearboy_libretro.dll"),
    _core("tgbdual_core",    "TGB Dual",         ["gb", "gbc"],       "tgbdual_libretro.dll"),
    # === Game Boy Advance ===
    _core("mgba_core",       "mGBA",             ["gb", "gbc", "gba"], "mgba_libretro.dll"),
    _core("vbam_core",       "VBA-M",            ["gba"],              "vbam_libretro.dll"),
    _core("vba_next_core",   "VBA Next",         ["gba"],              "vba_next_libretro.dll"),
    _core("gpsp_core",       "gpSP",             ["gba"],              "gpsp_libretro.dll"),
    _core("meteor_core",     "Meteor",           ["gba"],              "meteor_libretro.dll"),
    _core("beetle_gba_core", "Beetle GBA",       ["gba"],              "mednafen_gba_libretro.dll"),
    # === Virtual Boy ===
    _core("beetle_vb_core",  "Beetle VB",        ["vb"],               "mednafen_vb_libretro.dll"),
    # === Nintendo DS ===
    _core("melonds_ds_core", "melonDS DS",       ["nds"],              "melonds_ds_libretro.dll"),
    _core("melonds_core",    "melonDS",          ["nds"],              "melonds_libretro.dll"),
    _core("desmume_core",    "DeSmuME",          ["nds"],              "desmume_libretro.dll"),
    _core("desmume2015_core","DeSmuME 2015",     ["nds"],              "desmume2015_libretro.dll"),
    # === Nintendo 3DS ===
    _core("citra_core",      "Citra",            ["3ds"],              "citra_libretro.dll"),
    _core("citra_canary_core","Citra Canary",    ["3ds"],              "citra_canary_libretro.dll"),
    # === GameCube / Wii ===
    _core("dolphin_core",    "Dolphin",          ["gc", "wii"],        "dolphin_libretro.dll"),
    # === Pokémon Mini ===
    _core("pokemini_core",   "PokéMini",         ["pokemini"],         "pokemini_libretro.dll"),
    # === Sega Genesis / Mega Drive / SMS / Game Gear / SG-1000 / CD / 32X ===
    _core("genesis_plus_gx_core", "Genesis Plus GX", ["genesis", "sms", "gg", "segacd", "sg1000"], "genesis_plus_gx_libretro.dll"),
    _core("picodrive_core",       "PicoDrive",       ["genesis", "sms", "gg", "segacd", "sega32x", "sg1000"], "picodrive_libretro.dll"),
    _core("blastem_core",         "BlastEm",         ["genesis"],       "blastem_libretro.dll"),
    _core("gearsystem_core",     "Gearsystem",      ["sms", "gg", "sg1000"], "gearsystem_libretro.dll"),
    _core("smsplus_core",        "SMS Plus GX",     ["sms", "gg"],     "smsplus_libretro.dll"),
    # === Sega Saturn ===
    _core("beetle_saturn_core",   "Beetle Saturn",   ["saturn"],        "mednafen_saturn_libretro.dll"),
    _core("kronos_core",         "Kronos",          ["saturn"],        "kronos_libretro.dll"),
    _core("yabasanshiro_core",   "YabaSanshiro",    ["saturn"],        "yabasanshiro_libretro.dll"),
    _core("yabause_core",        "Yabause",         ["saturn"],        "yabause_libretro.dll"),
    # === Sega Dreamcast / NAOMI ===
    _core("flycast_core",        "Flycast",         ["dreamcast"],     "flycast_libretro.dll"),
    # === PlayStation ===
    _core("beetle_psx_hw_core",  "Beetle PSX HW",   ["ps1"],           "mednafen_psx_hw_libretro.dll"),
    _core("beetle_psx_core",     "Beetle PSX",       ["ps1"],           "mednafen_psx_libretro.dll"),
    _core("swanstation_core",    "SwanStation",      ["ps1"],           "swanstation_libretro.dll"),
    _core("pcsx_rearmed_core",   "PCSX ReARMed",    ["ps1"],           "pcsx_rearmed_libretro.dll"),
    _core("duckstation_core",    "DuckStation",      ["ps1"],           "duckstation_libretro.dll"),
    # === PlayStation 2 ===
    _core("lrps2_core",          "LRPS2",           ["ps2"],           "lrps2_libretro.dll"),
    # === PlayStation Portable ===
    _core("ppsspp_core",         "PPSSPP",           ["psp"],           "ppsspp_libretro.dll"),
    # === Atari 2600 ===
    _core("stella_core",         "Stella",           ["atari2600"],     "stella_libretro.dll"),
    _core("stella2014_core",     "Stella 2014",      ["atari2600"],     "stella2014_libretro.dll"),
    # === Atari 5200 / 8-bit ===
    _core("atari800_core",       "Atari800",         ["atari5200"],     "atari800_libretro.dll"),
    _core("a5200_core",          "a5200",            ["atari5200"],     "a5200_libretro.dll"),
    # === Atari 7800 ===
    _core("prosystem_core",      "ProSystem",        ["atari7800"],     "prosystem_libretro.dll"),
    # === Atari Lynx ===
    _core("handy_core",          "Handy",            ["lynx"],          "handy_libretro.dll"),
    _core("beetle_lynx_core",    "Beetle Lynx",      ["lynx"],          "mednafen_lynx_libretro.dll"),
    # === Atari Jaguar ===
    _core("virtual_jaguar_core", "Virtual Jaguar",   ["jaguar"],        "virtualjaguar_libretro.dll"),
    # === Atari ST / STE / Falcon ===
    _core("hatari_core",         "Hatari",           ["atarist"],       "hatari_libretro.dll"),
    # === TurboGrafx-16 / PC Engine ===
    _core("beetle_pce_fast_core","Beetle PCE Fast",  ["tg16"],          "mednafen_pce_fast_libretro.dll"),
    _core("beetle_pce_core",     "Beetle PCE",       ["tg16"],          "mednafen_pce_libretro.dll"),
    _core("beetle_sgx_core",     "Beetle SuperGrafx",["tg16"],          "mednafen_supergrafx_libretro.dll"),
    # === NEC PC-FX ===
    _core("beetle_pcfx_core",    "Beetle PC-FX",     ["pcfx"],          "mednafen_pcfx_libretro.dll"),
    # === NEC PC-98 ===
    _core("np2kai_core",         "Neko Project II Kai", ["pc98"],       "np2kai_libretro.dll"),
    # === Neo Geo Pocket / Color ===
    _core("beetle_neopop_core",  "Beetle NeoPop",    ["ngp"],           "mednafen_ngp_libretro.dll"),
    _core("race_core",           "RACE",             ["ngp"],           "race_libretro.dll"),
    # === Neo Geo (Arcade) ===
    _core("fbneo_core",          "FinalBurn Neo",    ["neogeo", "mame"],"fbneo_libretro.dll"),
    _core("geolith_core",        "Geolith",          ["neogeo"],        "geolith_libretro.dll"),
    # === Neo Geo CD ===
    _core("neocd_core",          "NeoCD",            ["neocd"],         "neocd_libretro.dll"),
    # === Arcade / MAME ===
    _core("mame_core",           "MAME (Current)",   ["mame"],          "mame_libretro.dll"),
    _core("mame2003_plus_core",  "MAME 2003-Plus",   ["mame"],          "mame2003_plus_libretro.dll"),
    _core("mame2003_core",       "MAME 2003",        ["mame"],          "mame2003_libretro.dll"),
    _core("mame2010_core",       "MAME 2010",        ["mame"],          "mame2010_libretro.dll"),
    # === 3DO ===
    _core("opera_core",          "Opera",            ["3do"],           "opera_libretro.dll"),
    # === Vectrex ===
    _core("vecx_core",           "vecx",             ["vectrex"],       "vecx_libretro.dll"),
    # === WonderSwan / WonderSwan Color ===
    _core("beetle_wswan_core",   "Beetle Cygne",     ["wonderswan"],    "mednafen_wswan_libretro.dll"),
    # === MSX / MSX2 ===
    _core("fmsx_core",           "fMSX",             ["msx"],           "fmsx_libretro.dll"),
    _core("bluemsx_core",        "blueMSX",          ["msx", "coleco", "sg1000"], "bluemsx_libretro.dll"),
    # === ColecoVision ===
    _core("gearcoleco_core",     "Gearcoleco",       ["coleco"],        "gearcoleco_libretro.dll"),
    # === Intellivision ===
    _core("freeintv_core",       "FreeIntv",         ["intv"],          "freeintv_libretro.dll"),
    # === Magnavox Odyssey² / Videopac ===
    _core("o2em_core",           "O2EM",             ["odyssey2"],      "o2em_libretro.dll"),
    # === Fairchild Channel F ===
    _core("freechaf_core",       "FreeChaF",         ["channelf"],      "freechaf_libretro.dll"),
    # === Commodore 64 ===
    _core("vice_x64_core",       "VICE x64",         ["c64"],           "vice_x64_libretro.dll"),
    _core("vice_x64sc_core",     "VICE x64sc",       ["c64"],           "vice_x64sc_libretro.dll"),
    # === Commodore Amiga ===
    _core("puae_core",           "PUAE",             ["amiga"],         "puae_libretro.dll"),
    _core("puae2021_core",       "PUAE 2021",        ["amiga"],         "puae2021_libretro.dll"),
    # === Amstrad CPC ===
    _core("cap32_core",          "Caprice32",        ["cpc"],           "cap32_libretro.dll"),
    _core("crocods_core",        "CrocoDS",          ["cpc"],           "crocods_libretro.dll"),
    # === ZX Spectrum ===
    _core("fuse_core",           "Fuse",             ["zxspec"],        "fuse_libretro.dll"),
    # === DOS ===
    _core("dosbox_pure_core",    "DOSBox Pure",      ["dos", "pc"],     "dosbox_pure_libretro.dll"),
    _core("dosbox_svn_core",     "DOSBox-SVN",       ["dos", "pc"],     "dosbox_svn_libretro.dll"),

    # =================================================================
    # Standalone emulators (only for systems without good cores)
    # =================================================================
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
    # === Sony PS2 (standalone) ===
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
    # === Sony PS1 (standalone) ===
    EmulatorCatalogEntry(
        id="duckstation",
        name="DuckStation",
        homepage_url="https://github.com/stenzek/duckstation",
        systems=["ps1"],
        release_provider="direct",
        release_source="https://github.com/stenzek/duckstation/releases/download/latest/duckstation-windows-x64-release.zip",
        install_strategy="archive",
        install_subdir="duckstation",
        exe_candidates=[
            "duckstation-qt-x64-ReleaseLTCG.exe",
            "duckstation-qt.exe",
            "duckstation-nogui-x64-ReleaseLTCG.exe",
        ],
        asset_include=["windows", "x64", ".zip"],
        asset_exclude=["arm64", "symbols", "debug"],
        preferred_version="latest",
        preferred_download_url="https://github.com/stenzek/duckstation/releases/download/latest/duckstation-windows-x64-release.zip",
    ),
    # === Sony PS3 (standalone) ===
    EmulatorCatalogEntry(
        id="rpcs3",
        name="RPCS3",
        homepage_url="https://github.com/RPCS3/rpcs3",
        systems=["ps3"],
        release_source="RPCS3/rpcs3-binaries-win",
        install_strategy="archive",
        install_subdir="rpcs3",
        exe_candidates=["rpcs3.exe"],
        asset_include=["win64", ".7z"],
        asset_exclude=["symbols", "pdb", "debug"],
    ),
    # === Nintendo Wii U (standalone) ===
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
    # === Nintendo 3DS (standalone) ===
    EmulatorCatalogEntry(
        id="azahar",
        name="Azahar",
        homepage_url="https://github.com/azahar-emu/azahar",
        systems=["3ds"],
        release_source="azahar-emu/azahar",
        install_strategy="archive",
        install_subdir="azahar",
        exe_candidates=["azahar-qt.exe", "azahar.exe"],
        default_args='"{rom}"',
        asset_include=["windows", "msvc", ".zip"],
        asset_exclude=["installer", "msys2", "source", "android", "macos", "docker"],
    ),
    EmulatorCatalogEntry(
        id="citra_standalone",
        name="Citra (Standalone)",
        homepage_url="https://archive.org/details/citra-emu_202403",
        systems=["3ds"],
        release_provider="direct",
        release_source="https://archive.org/download/citra-emu_202403/citra-windows-msvc-20240303-0ff3440_nightly.zip",
        install_strategy="archive",
        install_subdir="citra",
        exe_candidates=["citra-qt.exe", "citra.exe"],
        asset_include=["citra", "windows", ".zip"],
        preferred_version="20240303-nightly",
        preferred_download_url="https://archive.org/download/citra-emu_202403/citra-windows-msvc-20240303-0ff3440_nightly.zip",
        notes="Discontinued. Consider using Azahar instead.",
    ),
    # === Nintendo DS (standalone) ===
    EmulatorCatalogEntry(
        id="melonds_standalone",
        name="melonDS (Standalone)",
        homepage_url="https://github.com/melonDS-emu/melonDS",
        systems=["nds"],
        release_source="melonDS-emu/melonDS",
        install_strategy="archive",
        install_subdir="melonds",
        exe_candidates=["melonDS.exe"],
        asset_include=["win", ".zip"],
    ),
    EmulatorCatalogEntry(
        id="desmume_standalone",
        name="DeSmuME (Standalone)",
        homepage_url="https://github.com/TASEmulators/desmume",
        systems=["nds"],
        release_source="TASEmulators/desmume",
        install_strategy="archive",
        install_subdir="desmume",
        exe_candidates=["desmume.exe", "DeSmuME.exe"],
        asset_include=["win", ".zip"],
    ),
    # === Xbox (standalone) ===
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
    # === Xbox 360 (standalone) ===
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
]

EMULATOR_CATALOG_BY_ID: dict[str, EmulatorCatalogEntry] = {e.id: e for e in EMULATOR_CATALOG}
EMULATOR_CATALOG_BY_NAME: dict[str, EmulatorCatalogEntry] = {e.name: e for e in EMULATOR_CATALOG}


def emulators_for_system(system_id: str) -> list[tuple[str, str]]:
    """Return [(name, url)] of emulators that support the given system.

    Includes both standalone emulators and RetroArch cores.
    """
    result = []
    for entry in EMULATOR_CATALOG:
        if entry.id == "retroarch":
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
        if item.id == "retroarch":
            continue
        if not item.windows_supported:
            continue
        if item.install_strategy == "manual":
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
        id="steamgriddb",
        name="SteamGridDB",
        url="https://www.steamgriddb.com",
        auth_fields=[
            ("api_key", "API Key:", "SteamGridDB API key", True),
        ],
        content=["title"],
        artwork=["front_box", "banner", "clear_logo", "fan_art", "screenshots"],
        rate_limit_note="SteamGridDB is the active metadata/artwork source in Meridian.",
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

    # Per-emulator settings
    fullscreen_on_launch: bool = False
    exclusive_fullscreen: bool = False
    resolution_override: str = "Default"   # Default / 720p / 1080p / 1440p / 4K
    close_meridian_on_launch: bool = False
    auto_save_state: bool = False
    controller_profile: str = "Global"     # name of the controller profile to use

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
    system_logo_set: str = "Colorful"  # Colorful / White / Black

    # Game Display
    show_game_icons: bool = True
    show_system_logos: bool = True
    show_file_extensions: bool = False
    sort_default: str = "Title"          # Title / Platform / Added / Played

    # Background
    bg_type: str = "None"              # None / Image / Animation
    bg_image_path: str = ""
    bg_animation: str = ""             # e.g. "Waves"

    # Graphics — Display
    remember_window_geometry: bool = False
    borderless_fullscreen: bool = False
    ui_animation_speed: str = "Normal"   # Slow / Normal / Fast / Instant
    smooth_scrolling: bool = True
    list_transition_style: str = "Fade"  # Fade / Slide / None

    # Graphics — Rendering  (vsync + gpu_accel are applied at startup)
    vsync: bool = True
    gpu_accelerated_ui: bool = False
    text_rendering: str = "Subpixel"     # Subpixel / Greyscale / None
    image_scaling: str = "Bilinear"      # Nearest / Bilinear / Smooth
    icon_size: int = 48                  # 32 / 48 / 64 / 96

    # Performance — CPU
    limit_background_cpu: bool = False
    scan_threads: int = 4              # 1-16
    background_fps: int = 30           # animation fps when window unfocused
    foreground_fps: int = 60           # animation fps when window focused
    lazy_load_artwork: bool = True
    prefetch_adjacent: bool = True     # pre-load art for items near viewport

    # Performance — GPU
    gpu_backend: str = "Auto"          # Auto / OpenGL / Software

    # Performance — Memory
    max_loaded_images: int = 200       # evict beyond this count
    preload_emulator_configs: bool = True

    # Performance — Cache
    cache_box_art: bool = True
    cache_metadata: bool = True
    cache_max_mb: int = 512            # max disk cache in MB
    thumbnail_resolution: str = "Medium"  # Low / Medium / High

    # Scraper
    scraper_source: str = "SteamGridDB"
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
    scraper_region_priority: str = "USA"

    # RetroArch
    retroarch_auto_update: bool = True   # update RetroArch + cores on startup

    # Networking
    multiplayer_enabled: bool = False
    multiplayer_username: str = "Player"
    multiplayer_port: int = 55435
    multiplayer_directory_url: str = ""
    multiplayer_show_full_rooms: bool = True
    multiplayer_preferred_region: str = "Any"
    multiplayer_auto_refresh_seconds: int = 30
    updates_check_on_startup: bool = False
    updates_include_prerelease: bool = False

    # Audio
    audio_output_device: str = "Default"
    audio_input_device: str = "None"
    audio_channel_mode: str = "Stereo"    # Stereo / Mono
    audio_volume: int = 100               # 0-100
    audio_mute: bool = False
    audio_mute_background: bool = True
    audio_mute_unfocused_emu: bool = False
    ambient_audio_enabled: bool = False
    ambient_audio_volume: int = 30      # 0-100

    # File Management
    file_verify_on_scan: bool = False          # check files exist on each scan
    file_auto_remove_missing: bool = False     # drop missing files from library automatically

    # Debug
    debug_logging: bool = False
    debug_show_fps: bool = False
    debug_log_emulator_stdout: bool = False
    debug_log_level: str = "WARNING"     # DEBUG / INFO / WARNING / ERROR
    debug_show_widget_borders: bool = False

    # Input
    input_gamepad_nav: bool = False
    input_vibration: bool = True
    input_motion: bool = True
    input_focus_only: bool = True
    # { "1": {"connected": bool, "api": str, "device": str, "type": str}, ... }
    input_player_settings: dict = field(default_factory=dict)

    steam_input_warning_shown: bool = False # one-shot advisory re Steam Input

    # Named controller profiles (profile_name -> player_settings dict)
    # "Global" is a virtual name that references input_player_settings above.
    # { "RetroArch": { "1": { "connected": true, ... }, "2": ... }, ... }
    controller_profiles: dict = field(default_factory=dict)

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


# -- BIOS filename aliases (shared between settings UI and launch logic) ----

BIOS_FILENAME_ALIASES: dict[str, list[str]] = {
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
    "ngp_bios": ["ngp_bios.ngp", "ngpcbios.rom"],
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
    "segacd_bios_us": ["bios_CD_U.bin"],
    "segacd_bios_eu": ["bios_CD_E.bin"],
    "segacd_bios_jp": ["bios_CD_J.bin"],
    "sega32x_bios_m68k": ["32X_G_BIOS.BIN"],
    "sega32x_bios_msh2": ["32X_M_BIOS.BIN"],
    "sega32x_bios_ssh2": ["32X_S_BIOS.BIN"],
    "pcfx_bios": ["pcfx.rom"],
    "pc98_bios_font": ["font.bmp", "font.rom"],
    "neocd_bios": ["neocd.bin", "neocdz.zip"],
    "atari5200_bios": ["5200.rom"],
    "atarist_tos": ["tos.img"],
    "coleco_bios": ["coleco.rom"],
    "intv_exec_bios": ["exec.bin"],
    "intv_grom_bios": ["grom.bin"],
    "odyssey2_bios": ["o2rom.bin"],
    "channelf_bios_sl1": ["sl31253.bin"],
    "channelf_bios_sl2": ["sl31254.bin"],
    "n64_pif": ["pifdata.bin"],
    "xbox_bios": ["Complex_4627.bin", "evox.bin"],
    "xbox_eeprom": ["eeprom.bin"],
    "psp_font": ["flash0"],
    "psp_flash0": ["flash0"],
    "sega_cd_us": ["bios_CD_U.bin"],
    "sega_cd_eu": ["bios_CD_E.bin"],
    "sega_cd_jp": ["bios_CD_J.bin"],
    "sega32x_m68k": ["32X_G_BIOS.BIN"],
    "sega32x_master": ["32X_M_BIOS.BIN"],
    "sega32x_slave": ["32X_S_BIOS.BIN"],
}


def _safe_dataclass_from_dict(dataclass_type: type, value: dict[str, Any]):
    """Build dataclass instance while ignoring unknown serialized keys."""
    known = {f.name for f in fields(dataclass_type)}
    filtered = {k: v for k, v in value.items() if k in known}
    return dataclass_type(**filtered)
