# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Pre-launch auto-configuration for emulators.

Before Meridian launches a game it calls :func:`auto_configure_emulator` which
writes (or patches) the emulator's own config files so that BIOS paths and ROM
directories are picked up automatically.

Each supported emulator has its own ``_setup_<name>`` helper.  Unknown
emulators are silently skipped — the existing copy-BIOS-files approach in
``MainWindow._apply_bios_for_launch`` still provides a reasonable fallback.
"""

from __future__ import annotations

import configparser
import logging
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from meridian.core.config import (
    Config,
    EmulatorCatalogEntry,
    EmulatorEntry,
    emulator_catalog_entry,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Player settings resolution
# ---------------------------------------------------------------------------

def resolve_player_settings(
    config: Config,
    emulator: EmulatorEntry | None = None,
) -> dict[str, dict]:
    """Return the effective per-player settings dict.

    Keys are player numbers as strings (``"1"`` … ``"10"``).  Each value is a
    dict with at least ``connected``, ``api``, ``device``, ``device_index``,
    ``type``, and ``bindings``.

    If *emulator* is provided and has a non-Global controller profile assigned,
    that profile's settings are used instead of the global defaults.
    """
    profile = (emulator.controller_profile or "Global") if emulator else "Global"
    if profile != "Global":
        profiles = getattr(config, "controller_profiles", None) or {}
        if profile in profiles:
            return dict(profiles[profile])
    return dict(config.input_player_settings or {})


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def auto_configure_emulator(
    emulator: EmulatorEntry,
    game_path: Path,
    system_id: str,
    exe_path: Path,
    config: Config,
) -> None:
    """Write emulator-specific config files before launch.

    Parameters
    ----------
    emulator:
        The :class:`EmulatorEntry` being launched.
    game_path:
        Absolute path to the ROM / game file.
    system_id:
        Meridian system identifier (e.g. ``"ps1"``, ``"gba"``).
    exe_path:
        Resolved path to the emulator executable.
    config:
        The current Meridian :class:`Config` (holds BIOS paths, system
        entries, etc.).
    """
    catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
    emu_id = (catalog.id if catalog else emulator.display_name()).lower()

    # All RetroArch cores use the same auto-configure handler
    is_retroarch_core = catalog and catalog.install_strategy == "retroarch_core"

    rom_dir = _rom_directory_for_system(system_id, config)
    bios_map = _bios_paths_for_system(system_id, config)
    players = resolve_player_settings(config, emulator)

    ctx = _SetupContext(
        emulator=emulator,
        emu_id=emu_id,
        game_path=game_path,
        system_id=system_id,
        exe_path=exe_path,
        config=config,
        rom_dir=rom_dir,
        bios_map=bios_map,
        player_settings=players,
    )

    _write_debug_log(ctx)

    if is_retroarch_core:
        handler = _setup_retroarch
    else:
        handler = _HANDLERS.get(emu_id)

    if handler is not None:
        log.debug("Auto-configuring '%s'%s", emu_id,
                  " (RetroArch core)" if is_retroarch_core else "")
        try:
            handler(ctx)
        except Exception:
            log.exception("Failed to auto-configure emulator '%s'", emu_id)
    else:
        log.debug("No auto-configure handler for emulator id '%s'", emu_id)

    if not is_retroarch_core:
        _run_extension_input(ctx)


# ---------------------------------------------------------------------------
# Extension-based input profile dispatch
# ---------------------------------------------------------------------------

def _run_extension_input(ctx: _SetupContext) -> None:
    """Try to load an extension for *ctx.emu_id* and call its input hook.

    Each extension lives at ``emulators.extensions.<emu_id>`` and may expose
    a ``configure_input(player_settings, exe_path, game_path)`` function.
    If the module or function doesn't exist the call is silently skipped.
    """
    import importlib

    module_name = f"emulators.extensions.{ctx.emu_id}"
    try:
        ext = importlib.import_module(module_name)
    except ModuleNotFoundError:
        log.debug("No extension module for '%s'", ctx.emu_id)
        return
    except Exception:
        log.debug("Failed to import extension '%s'", module_name, exc_info=True)
        return

    configure = getattr(ext, "configure_input", None)
    if configure is None:
        log.debug("Extension '%s' has no configure_input()", ctx.emu_id)
        return

    try:
        configure(
            player_settings=ctx.player_settings,
            exe_path=ctx.exe_path,
            game_path=ctx.game_path,
        )
        log.debug("Extension '%s' configured input profiles", ctx.emu_id)
    except Exception:
        log.debug(
            "Extension '%s' configure_input() failed",
            ctx.emu_id,
            exc_info=True,
        )


def _write_debug_log(ctx: _SetupContext) -> None:
    """Write ``meridian_input_debug.txt`` next to the emulator exe.

    This lets the user (and us) verify exactly what Meridian sees when
    it tries to configure the emulator.
    """
    try:
        handler = _HANDLERS.get(ctx.emu_id)
        lines = [
            "Meridian auto-configure debug",
            "=============================",
            f"emu_id          : {ctx.emu_id}",
            f"handler found   : {handler is not None}",
            f"exe_path        : {ctx.exe_path}",
            f"install_dir     : {ctx.install_dir}",
            f"system_id       : {ctx.system_id}",
            "",
            "Player settings",
            "---------------",
        ]
        for pnum, pdata in sorted(ctx.player_settings.items(), key=lambda t: t[0]):
            if not isinstance(pdata, dict):
                continue
            connected = pdata.get("connected", False)
            api = pdata.get("api", "Auto")
            device = pdata.get("device", "")
            dev_idx = pdata.get("device_index")
            ptype = pdata.get("type", "")
            lines.append(
                f"  P{pnum}: connected={connected}  api={api}  "
                f"device={device!r}  index={dev_idx}  type={ptype}"
            )

        debug_path = ctx.exe_path.parent / "meridian_input_debug.txt"
        debug_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass  # never fail the launch over a debug file


# ---------------------------------------------------------------------------
# Internal context
# ---------------------------------------------------------------------------

class _SetupContext:
    __slots__ = (
        "emulator", "emu_id", "game_path", "system_id", "exe_path",
        "config", "rom_dir", "bios_map", "player_settings",
    )

    def __init__(self, **kw: Any):
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def install_dir(self) -> Path:
        if self.emulator.install_dir:
            return Path(self.emulator.install_dir)
        return self.exe_path.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SYSTEM_BIOS_IDS: dict[str, list[str]] = {
    "nes": ["nes_fds_bios"],
    "gba": ["gba_bios"],
    "nds": ["nds_bios7", "nds_bios9", "nds_firmware"],
    "3ds": ["n3ds_aes_keys", "n3ds_seeddb", "n3ds_boot9", "n3ds_boot11"],
    "n64": ["n64_pif"],
    "gc": ["gc_ipl"],
    "wii": ["wii_keys"],
    "wiiu": ["wiiu_keys"],
    "switch": ["switch_prod_keys", "switch_title_keys", "switch_firmware"],
    "genesis": ["sega_cd_us", "sega_cd_eu", "sega_cd_jp"],
    "saturn": ["saturn_bios_jp", "saturn_bios_us_eu"],
    "dreamcast": ["dc_boot", "dc_flash"],
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
    "mame": ["neogeo_zip", "mame_qsound"],
    "3do": ["3do_panafz10", "3do_panafz1", "3do_goldstar"],
    "vectrex": ["vectrex_bios"],
    "wonderswan": ["wswan_boot"],
    "msx": ["msx_bios", "msx2_bios"],
}


def _rom_directory_for_system(system_id: str, config: Config) -> str:
    """Return the best ROM directory for *system_id* from the config."""
    for se in config.systems:
        if se.system_id == system_id and se.rom_directory:
            return se.rom_directory
    for emu in config.emulators:
        if emu.rom_directory:
            catalog = emulator_catalog_entry(emu.catalog_id or emu.name)
            if catalog and system_id in catalog.systems:
                return emu.rom_directory
    if config.rom_directories:
        return config.rom_directories[0]
    return ""


def _bios_paths_for_system(system_id: str, config: Config) -> dict[str, str]:
    """Return ``{bios_id: absolute_path}`` of configured BIOS files."""
    bios_cfg = dict(getattr(config, "bios_files", {}) or {})
    ids = _SYSTEM_BIOS_IDS.get(system_id, [])
    result: dict[str, str] = {}
    for bid in ids:
        raw = str(bios_cfg.get(bid, "")).strip()
        if raw and Path(raw).exists():
            result[bid] = raw
    return result


def _ensure_portable(directory: Path, marker: str = "portable.txt") -> None:
    """Create a portable-mode marker file if it doesn't exist."""
    p = directory / marker
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")


_ROOT = Path(__file__).resolve().parents[2]
def build_emulator_env(config: Config | None = None) -> dict[str, str]:
    """Return an environment dict with SDL controller hints for subprocesses.

    Passing this to ``subprocess.Popen(env=...)`` ensures every SDL2-based
    emulator (current *and* future) can detect gamepads the moment it starts.
    """
    env = dict(os.environ)
    env["SDL_GAMECONTROLLER_ALLOW_BACKGROUND_EVENTS"] = "1"
    env["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

    return env

# -- INI-file helpers (RetroArch key = "value" format) ----------------------

def _patch_retroarch_cfg(path: Path, patches: dict[str, str]) -> None:
    """Update specific keys in an existing retroarch.cfg in-place.

    Preserves all existing keys and their order; only changes values that
    differ from *patches*.  New keys are appended at the end.
    """
    existing_lines: list[str] = []
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    remaining = dict(patches)
    result: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                result.append(f'{key} = "{remaining.pop(key)}"')
                continue
        result.append(line)

    for key, value in sorted(remaining.items()):
        result.append(f'{key} = "{value}"')

    path.write_text("\n".join(result) + "\n", encoding="utf-8")


# -- Standard INI-file helpers ---------------------------------------------

def _patch_ini(path: Path, patches: dict[str, dict[str, str]]) -> None:
    """Patch a standard INI file.  *patches* is ``{section: {key: value}}``."""
    cfg = configparser.RawConfigParser()
    cfg.optionxform = str  # type: ignore[assignment]  # preserve case
    if path.exists():
        cfg.read(str(path), encoding="utf-8")

    for section, kvs in patches.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for key, value in kvs.items():
            cfg.set(section, key, value)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        cfg.write(fh)


# ---------------------------------------------------------------------------
# BIOS copy helper
# ---------------------------------------------------------------------------

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
    "psp_font": ["ppge_atlas.zim"],
    "psp_flash0": ["flash0.zip"],
    "atari7800_bios": ["7800 BIOS (U).rom"],
    "lynx_boot": ["lynxboot.img"],
    "jaguar_bios": ["jagboot.rom"],
    "jaguar_cd_bios": ["jagcd.bin"],
    "tg16_syscard1": ["syscard1.pce"],
    "tg16_syscard2": ["syscard2.pce"],
    "tg16_syscard3": ["syscard3.pce"],
    "neogeo_zip": ["neogeo.zip"],
    "mame_qsound": ["qsound.zip"],
    "3do_panafz10": ["panafz10.bin"],
    "3do_panafz1": ["panafz1.bin"],
    "3do_goldstar": ["goldstar.bin"],
    "vectrex_bios": ["bios.bin"],
    "wswan_boot": ["wswanboot.bin"],
    "msx_bios": ["MSX.ROM"],
    "msx2_bios": ["MSX2.ROM"],
    "msx2ext_bios": ["MSX2EXT.ROM"],
    "msx_disk": ["DISK.ROM"],
    "xbox_bios": ["mcpx_1.0.bin", "complex_4627.bin"],
    "xbox_eeprom": ["eeprom.bin"],
    "psvita_firmware": ["PSVUPDAT.PUP"],
    "ngp_bios": ["ngp_bios.bin"],
    "n64_pif": ["pifdata.bin"],
}


def _copy_bios_to_dir(ctx: _SetupContext, dest_dir: Path) -> None:
    """Copy all configured BIOS files for the current system into *dest_dir*."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for bios_id, src_path in ctx.bios_map.items():
        src = Path(src_path)
        if not src.exists():
            continue
        aliases = _BIOS_FILENAME_ALIASES.get(bios_id, [src.name])
        for alias in aliases:
            try:
                dest = dest_dir / alias
                if dest.exists() and dest.stat().st_size == src.stat().st_size:
                    continue
                shutil.copy2(src, dest)
            except Exception:
                continue


# =========================================================================
# Per-emulator setup handlers
# =========================================================================


# -- RetroArch -------------------------------------------------------------


def _setup_retroarch(ctx: _SetupContext) -> None:
    """Patch retroarch.cfg with absolute BIOS / ROM paths."""
    cfg_path = ctx.install_dir / "retroarch.cfg"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if not cfg_path.exists():
        cfg_path.write_text("", encoding="utf-8")

    system_dir = str((ctx.install_dir / "system").resolve())
    patches: dict[str, str] = {
        "system_directory": system_dir,
    }

    if ctx.rom_dir:
        patches["rgui_browser_directory"] = ctx.rom_dir
        patches["content_directory"] = ctx.rom_dir

    bios_dir = Path(system_dir)
    bios_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, bios_dir)

    _patch_retroarch_cfg(cfg_path, patches)


# -- DuckStation -----------------------------------------------------------


def _setup_duckstation(ctx: _SetupContext) -> None:
    """Configure DuckStation for portable mode with BIOS and ROM paths."""
    _ensure_portable(ctx.exe_path.parent)

    bios_dir = ctx.exe_path.parent / "bios"
    bios_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, bios_dir)

    settings_path = ctx.exe_path.parent / "settings.ini"
    patches: dict[str, dict[str, str]] = {
        "BIOS": {
            "SearchDirectory": str(bios_dir.resolve()),
        },
        "Main": {
            "SettingsVersion": "3",
        },
        "AutoUpdater": {
            "CheckAtStartup": "false",
        },
    }
    if ctx.rom_dir:
        patches["GameList"] = {
            "RecursivePaths": ctx.rom_dir,
        }

    _patch_ini(settings_path, patches)


# -- PCSX2 ----------------------------------------------------------------


def _setup_pcsx2(ctx: _SetupContext) -> None:
    """Configure PCSX2 portable with BIOS directory."""
    _ensure_portable(ctx.exe_path.parent, marker="portable.ini")

    bios_dir = ctx.exe_path.parent / "bios"
    bios_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, bios_dir)

    inis_dir = ctx.exe_path.parent / "inis"
    inis_dir.mkdir(parents=True, exist_ok=True)
    settings_path = inis_dir / "PCSX2.ini"

    patches: dict[str, dict[str, str]] = {
        "Folders": {
            "Bios": str(bios_dir.resolve()),
            "UseDefaultBios": "false",
        },
        "UI": {
            "SettingsVersion": "1",
        },
        "AutoUpdater": {
            "CheckAtStartup": "false",
        },
    }
    if ctx.rom_dir:
        patches["GameList"] = {
            "RecursivePaths": ctx.rom_dir,
        }

    _patch_ini(settings_path, patches)


# -- PPSSPP ----------------------------------------------------------------

def _setup_ppsspp(ctx: _SetupContext) -> None:
    """Configure PPSSPP portable with flash0 BIOS assets."""
    memstick = ctx.install_dir / "memstick"
    memstick.mkdir(parents=True, exist_ok=True)

    flash0_dir = ctx.install_dir / "assets" / "flash0"
    flash0_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, flash0_dir)

    ini_path = memstick / "PSP" / "SYSTEM" / "ppsspp.ini"
    ini_path.parent.mkdir(parents=True, exist_ok=True)

    patches: dict[str, dict[str, str]] = {
        "General": {
            "CheckForNewVersion": "false",
        },
    }
    if ctx.rom_dir:
        patches["General"]["CurrentDirectory"] = ctx.rom_dir

    if ini_path.exists():
        _patch_ini(ini_path, patches)
    else:
        _patch_ini(ini_path, patches)


# -- Dolphin ---------------------------------------------------------------


def _setup_dolphin(ctx: _SetupContext) -> None:
    """Configure Dolphin in portable mode with ROM paths."""
    _ensure_portable(ctx.exe_path.parent)

    user_dir = ctx.exe_path.parent / "User"
    config_dir = user_dir / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)

    gc_dir = user_dir / "GC"
    gc_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, gc_dir)

    wii_dir = user_dir / "Wii"
    wii_dir.mkdir(parents=True, exist_ok=True)

    ini_path = config_dir / "Dolphin.ini"
    patches: dict[str, dict[str, str]] = {
        "General": {
            "ISOPaths": "1",
        },
        "Core": {},
        "Interface": {
            "ConfirmStop": "false",
        },
    }
    if ctx.rom_dir:
        patches["General"]["ISOPath0"] = ctx.rom_dir

    _patch_ini(ini_path, patches)


# -- Cemu ------------------------------------------------------------------

def _setup_cemu(ctx: _SetupContext) -> None:
    """Configure Cemu in portable mode with keys, ROM paths, and input profiles."""
    portable_dir = ctx.exe_path.parent / "portable"
    portable_dir.mkdir(parents=True, exist_ok=True)

    # Copy keys.txt to all expected locations
    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})
    keys_src = str(bios_cfg.get("wiiu_keys", "")).strip()
    if keys_src and Path(keys_src).exists():
        for dest in [
            ctx.exe_path.parent / "keys.txt",
            portable_dir / "keys.txt",
            ctx.exe_path.parent / "mlc01" / "keys.txt",
        ]:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(keys_src, dest)
            except Exception:
                pass

    # Patch settings.xml if it exists
    settings_xml = ctx.exe_path.parent / "settings.xml"
    if not settings_xml.exists():
        settings_xml = portable_dir / "settings.xml"

    if settings_xml.exists() and ctx.rom_dir:
        try:
            tree = ET.parse(str(settings_xml))
            root = tree.getroot()
            gp = root.find("GamePaths")
            if gp is None:
                gp = ET.SubElement(root, "GamePaths")
            existing = {(e.text or "").strip() for e in gp.findall("Entry")}
            if ctx.rom_dir not in existing:
                entry_el = ET.SubElement(gp, "Entry")
                entry_el.text = ctx.rom_dir
            tree.write(str(settings_xml), encoding="unicode", xml_declaration=True)
        except Exception:
            pass

    # Input profiles are now handled by the Cemu extension via
    # _run_extension_input() — no emulator-specific wiring needed here.


# -- melonDS ---------------------------------------------------------------

def _setup_melonds(ctx: _SetupContext) -> None:
    """Configure melonDS with BIOS paths."""
    _ensure_portable(ctx.exe_path.parent)

    bios_dir = ctx.exe_path.parent / "bios"
    bios_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, bios_dir)

    toml_path = ctx.exe_path.parent / "melonDS.toml"
    ini_path = ctx.exe_path.parent / "melonDS.ini"

    bios_dir_str = str(bios_dir.resolve()).replace("\\", "/")

    if toml_path.exists():
        _patch_melonds_toml(toml_path, bios_dir_str, ctx.rom_dir)
    elif ini_path.exists():
        patches: dict[str, dict[str, str]] = {
            "": {
                "BIOS9Path": bios_dir_str + "/bios9.bin",
                "BIOS7Path": bios_dir_str + "/bios7.bin",
                "FirmwarePath": bios_dir_str + "/firmware.bin",
            },
        }
        if ctx.rom_dir:
            patches[""]["LastROMFolder"] = ctx.rom_dir
        _patch_ini(ini_path, patches)


def _patch_melonds_toml(path: Path, bios_dir: str, rom_dir: str) -> None:
    """Best-effort patch for melonDS TOML config."""
    text = path.read_text(encoding="utf-8", errors="replace")

    replacements = {
        "BIOS9Path": f"{bios_dir}/bios9.bin",
        "BIOS7Path": f"{bios_dir}/bios7.bin",
        "FirmwarePath": f"{bios_dir}/firmware.bin",
    }
    if rom_dir:
        replacements["LastROMFolder"] = rom_dir

    for key, value in replacements.items():
        escaped = value.replace("\\", "\\\\")
        pattern = rf'^(\s*{re.escape(key)}\s*=\s*)(".*?"|\'.*?\'|[^\n]+)'
        replacement = rf'\g<1>"{escaped}"'
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
        if count == 0:
            text += f'\n{key} = "{escaped}"\n'

    path.write_text(text, encoding="utf-8")


# -- Ryubing / Ryujinx ----------------------------------------------------

def _setup_ryubing(ctx: _SetupContext) -> None:
    """Configure Ryubing/Ryujinx with keys and firmware paths.

    Keys are written once to ``portable/system/``.
    Firmware NCA files are only extracted if the registered directory is
    empty — they are never re-extracted on subsequent launches, which
    prevents the "files appearing in multiple places" problem.
    """
    publish_dir = ctx.install_dir / "publish"
    exe_dir = publish_dir if publish_dir.exists() else ctx.exe_path.parent

    portable_dir = exe_dir / "portable"
    portable_dir.mkdir(parents=True, exist_ok=True)
    log.debug("Ryubing portable dir: %s", portable_dir)

    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})

    # Keys go to portable/system/ ONLY (Ryujinx portable mode reads from here)
    system_dir = portable_dir / "system"
    system_dir.mkdir(parents=True, exist_ok=True)
    for bios_id, filename in [
        ("switch_prod_keys", "prod.keys"),
        ("switch_title_keys", "title.keys"),
    ]:
        src = str(bios_cfg.get(bios_id, "")).strip()
        if not src:
            continue
        src_path = Path(src)
        if not src_path.exists():
            log.warning("Switch %s path set but file not found: %s", bios_id, src)
            continue
        dest = system_dir / filename
        try:
            if not dest.exists() or dest.stat().st_mtime < src_path.stat().st_mtime:
                shutil.copy2(src_path, dest)
                log.debug("Copied %s -> %s", src, dest)
        except Exception:
            log.debug("Failed to copy %s to %s", src, dest)

    fw_src = str(bios_cfg.get("switch_firmware", "")).strip()
    if fw_src:
        registered_dir = portable_dir / "bis" / "system" / "Contents" / "registered"
        existing_ncas = list(registered_dir.glob("*.nca")) if registered_dir.exists() else []
        if existing_ncas:
            log.debug(
                "Ryubing firmware already provisioned (%d NCA files present), skipping",
                len(existing_ncas),
            )
        else:
            _provision_ryujinx_firmware(Path(fw_src), portable_dir)
    else:
        log.warning("No switch_firmware BIOS path configured")



def _provision_ryujinx_firmware(source: Path, portable_dir: Path) -> None:
    """Copy/extract Switch firmware NCA files into portable bis layout."""
    try:
        if not source.exists():
            log.warning("Switch firmware source does not exist: %s", source)
            return

        registered_dirs = [
            portable_dir / "bis" / "system" / "Contents" / "registered",
        ]
        for rd in registered_dirs:
            rd.mkdir(parents=True, exist_ok=True)

        def _copy_nca_tree(src_dir: Path) -> int:
            copied = 0
            for nca in src_dir.rglob("*.nca"):
                try:
                    for dest_dir in registered_dirs:
                        dest = dest_dir / nca.name
                        if dest.exists() and dest.stat().st_size == nca.stat().st_size:
                            continue
                        shutil.copy2(nca, dest)
                        copied += 1
                except Exception:
                    continue
            return copied

        if source.is_file() and source.suffix.lower() == ".zip":
            extracted = 0
            try:
                with zipfile.ZipFile(source, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        if not info.filename.lower().endswith(".nca"):
                            continue
                        name = Path(info.filename).name
                        if not name:
                            continue
                        for dest_dir in registered_dirs:
                            dest = dest_dir / name
                            try:
                                with zf.open(info, "r") as src_fh, open(dest, "wb") as dst_fh:
                                    shutil.copyfileobj(src_fh, dst_fh)
                                extracted += 1
                            except Exception:
                                continue
            except Exception:
                log.exception("Failed to extract firmware zip: %s", source)
                return
            log.info("Extracted %d NCA files from firmware zip to %s",
                     extracted, registered_dirs[0])
            return

        if source.is_file() and source.suffix.lower() == ".nca":
            for dest_dir in registered_dirs:
                try:
                    shutil.copy2(source, dest_dir / source.name)
                except Exception:
                    continue
            return

        if source.is_dir():
            candidate_dirs = [
                source / "registered",
                source / "Contents" / "registered",
                source / "system" / "Contents" / "registered",
                source / "bis" / "system" / "Contents" / "registered",
                source,
            ]
            seen: set[str] = set()
            total = 0
            for cand in candidate_dirs:
                key = str(cand.resolve()) if cand.exists() else str(cand)
                if key in seen:
                    continue
                seen.add(key)
                if cand.exists():
                    total += _copy_nca_tree(cand)
            log.info("Copied %d NCA files from firmware directory to %s",
                     total, registered_dirs[0])
    except Exception:
        log.exception("Failed to provision Switch firmware from %s", source)


# -- Eden ------------------------------------------------------------------

def _setup_eden(ctx: _SetupContext) -> None:
    """Configure Eden (Yuzu fork) with keys."""
    user_dir = ctx.exe_path.parent / "user"
    keys_dir = user_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})
    for bios_id, filename in [
        ("switch_prod_keys", "prod.keys"),
        ("switch_title_keys", "title.keys"),
    ]:
        src = str(bios_cfg.get(bios_id, "")).strip()
        if src and Path(src).exists():
            try:
                shutil.copy2(src, keys_dir / filename)
            except Exception:
                pass

# -- Azahar (Citra fork) ---------------------------------------------------

def _setup_azahar(ctx: _SetupContext) -> None:
    """Configure Azahar with BIOS files.

    Azahar uses the same directory layout as Citra: BIOS files
    (``aes_keys.txt``, ``seeddb.bin``, etc.) go into ``user/sysdata``.
    """
    sysdata_dir = ctx.exe_path.parent / "user" / "sysdata"
    sysdata_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, sysdata_dir)

# -- Citra -----------------------------------------------------------------

def _setup_citra(ctx: _SetupContext) -> None:
    """Configure Citra with BIOS files."""
    sysdata_dir = ctx.exe_path.parent / "user" / "sysdata"
    sysdata_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, sysdata_dir)

# -- RPCS3 -----------------------------------------------------------------

def _setup_rpcs3(ctx: _SetupContext) -> None:
    """Configure RPCS3 with firmware path."""
    dev_flash = ctx.exe_path.parent / "dev_flash"
    dev_flash.mkdir(parents=True, exist_ok=True)

    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})
    fw_src = str(bios_cfg.get("ps3_firmware", "")).strip()
    if fw_src and Path(fw_src).exists():
        try:
            shutil.copy2(fw_src, ctx.exe_path.parent / "PS3UPDAT.PUP")
        except Exception:
            pass



# -- xemu ------------------------------------------------------------------

def _setup_xemu(ctx: _SetupContext) -> None:
    """Configure xemu with Xbox BIOS."""
    xemu_dir = ctx.exe_path.parent
    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})

    for bios_id, dest_name in [
        ("xbox_bios", "mcpx_1.0.bin"),
        ("xbox_eeprom", "eeprom.bin"),
    ]:
        src = str(bios_cfg.get(bios_id, "")).strip()
        if src and Path(src).exists():
            try:
                shutil.copy2(src, xemu_dir / dest_name)
            except Exception:
                pass

    if os.name == "nt":
        appdata = os.environ.get("LOCALAPPDATA", "")
        if appdata:
            xemu_data = Path(appdata) / "xemu" / "xemu"
            xemu_data.mkdir(parents=True, exist_ok=True)
            for bios_id, dest_name in [
                ("xbox_bios", "mcpx_1.0.bin"),
                ("xbox_eeprom", "eeprom.bin"),
            ]:
                src = str(bios_cfg.get(bios_id, "")).strip()
                if src and Path(src).exists():
                    try:
                        shutil.copy2(src, xemu_data / dest_name)
                    except Exception:
                        pass


# -- Flycast ---------------------------------------------------------------

def _setup_flycast(ctx: _SetupContext) -> None:
    """Configure Flycast with Dreamcast BIOS files."""
    data_dir = ctx.exe_path.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, data_dir)


# -- Vita3K ----------------------------------------------------------------

def _setup_vita3k(ctx: _SetupContext) -> None:
    """Copy PS Vita firmware into Vita3K data dir."""
    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})
    fw = str(bios_cfg.get("psvita_firmware", "")).strip()
    if fw and Path(fw).exists():
        try:
            shutil.copy2(fw, ctx.exe_path.parent / Path(fw).name)
        except Exception:
            pass


def _setup_mgba(ctx: _SetupContext) -> None:
    """Configure mGBA in portable mode."""
    _ensure_portable(ctx.install_dir, marker="portable.ini")


# -- DeSmuME ---------------------------------------------------------------

def _setup_desmume(ctx: _SetupContext) -> None:
    """Configure DeSmuME base files only."""


# -- Mednafen --------------------------------------------------------------

def _setup_mednafen(ctx: _SetupContext) -> None:
    """Set up Mednafen base directory structure.

    We set up the directory and ROM path only.
    """
    cfg_path = ctx.exe_path.parent / "mednafen.cfg"
    if not cfg_path.exists():
        return  # Mednafen creates this on first run

    # Copy BIOS files into the Mednafen firmware directory
    fw_dir = ctx.exe_path.parent / "firmware"
    fw_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, fw_dir)

    # Patch a few quality-of-life settings
    text = cfg_path.read_text(encoding="utf-8", errors="replace")
    replacements: dict[str, str] = {
        "filesys.path_firmware": str(fw_dir.resolve()),
    }
    for key, value in replacements.items():
        escaped = value.replace("\\", "\\\\")
        pattern = rf'^(\s*{re.escape(key)}\s+)(\S.*)'
        repl = rf'\g<1>{escaped}'
        text, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
        if n == 0:
            text += f"\n{key} {escaped}\n"
    cfg_path.write_text(text, encoding="utf-8")


# -- FCEUX -----------------------------------------------------------------

def _setup_fceux(ctx: _SetupContext) -> None:
    """Configure FCEUX for portable use.

    FCEUX on Windows uses DirectInput with device GUIDs.  We only set up
    base files and leave input handling to the emulator.
    """
    cfg_path = ctx.exe_path.parent / "fceux.cfg"
    if not cfg_path.exists():
        cfg_path.write_text("", encoding="utf-8")

    _copy_bios_to_dir(ctx, ctx.exe_path.parent)


# -- Mesen -----------------------------------------------------------------

def _setup_mesen(ctx: _SetupContext) -> None:
    """Configure Mesen base files only."""


# -- Snes9x ---------------------------------------------------------------

def _setup_snes9x(ctx: _SetupContext) -> None:
    """Configure Snes9x base files only."""


# -- SameBoy ---------------------------------------------------------------

def _setup_sameboy(ctx: _SetupContext) -> None:
    """Configure SameBoy for portable use.
    """
    _copy_bios_to_dir(ctx, ctx.exe_path.parent)


# -- Stella ----------------------------------------------------------------

def _setup_stella(ctx: _SetupContext) -> None:
    """Configure Stella (Atari 2600) for portable use.
    """
    _copy_bios_to_dir(ctx, ctx.exe_path.parent)


# -- Xenia -----------------------------------------------------------------

def _setup_xenia(ctx: _SetupContext) -> None:
    """Configure Xenia for portable use."""
    portable_toml = ctx.exe_path.parent / "portable.toml"
    if not portable_toml.exists():
        portable_toml.write_text("", encoding="utf-8")


# -- DOSBox Staging --------------------------------------------------------

def _setup_dosbox_staging(ctx: _SetupContext) -> None:
    """Configure DOSBox Staging for portable use.

    DOSBox Staging uses SDL Game Controller which auto-detects most
    modern gamepads.  We ensure a portable conf directory exists.
    """
    conf_dir = ctx.exe_path.parent / "conf"
    conf_dir.mkdir(parents=True, exist_ok=True)


# -- Decaf -----------------------------------------------------------------

def _setup_decaf(ctx: _SetupContext) -> None:
    """Configure Decaf (Wii U) with keys file."""
    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})
    keys_src = str(bios_cfg.get("wiiu_keys", "")).strip()
    if keys_src and Path(keys_src).exists():
        try:
            shutil.copy2(keys_src, ctx.exe_path.parent / "keys.txt")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

_HANDLERS: dict[str, Any] = {
    "retroarch": _setup_retroarch,
    "duckstation": _setup_duckstation,
    "pcsx2": _setup_pcsx2,
    "ppsspp": _setup_ppsspp,
    "dolphin": _setup_dolphin,
    "cemu": _setup_cemu,
    "melonds": _setup_melonds,
    "ryubing": _setup_ryubing,
    "ryujinx": _setup_ryubing,
    "eden": _setup_eden,
    "azahar": _setup_azahar,
    "citra": _setup_citra,
    "rpcs3": _setup_rpcs3,
    "xemu": _setup_xemu,
    "flycast": _setup_flycast,
    "vita3k": _setup_vita3k,
    # --- Newly covered emulators ---
    "mgba": _setup_mgba,
    "desmume": _setup_desmume,
    "mednafen": _setup_mednafen,
    "fceux": _setup_fceux,
    "mesen": _setup_mesen,
    "mesen_s": _setup_mesen,
    "snes9x": _setup_snes9x,
    "bsnes": _setup_snes9x,  # bsnes shares the same conf style
    "sameboy": _setup_sameboy,
    "stella": _setup_stella,
    "xenia": _setup_xenia,
    "dosbox_staging": _setup_dosbox_staging,
    "decaf": _setup_decaf,
}
