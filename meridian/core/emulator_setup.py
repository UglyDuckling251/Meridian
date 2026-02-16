"""
Pre-launch auto-configuration for emulators.

Before Meridian launches a game it calls :func:`auto_configure_emulator` which
writes (or patches) the emulator's own config files so that BIOS paths, ROM
directories, and controller input settings are picked up automatically.

Each supported emulator has its own ``_setup_<name>`` helper.  Unknown
emulators are silently skipped — the existing copy-BIOS-files approach in
``MainWindow._apply_bios_for_launch`` still provides a reasonable fallback.
"""

from __future__ import annotations

import configparser
import json
import logging
import os
import re
import shutil
import textwrap
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from meridian.core.config import (
    Config,
    EmulatorEntry,
    emulator_catalog_entry,
)

log = logging.getLogger(__name__)


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
        The current Meridian :class:`Config` (holds BIOS paths, input
        settings, system entries, etc.).
    """
    catalog = emulator_catalog_entry(emulator.catalog_id or emulator.name)
    emu_id = (catalog.id if catalog else emulator.display_name()).lower()

    rom_dir = _rom_directory_for_system(system_id, config)
    bios_map = _bios_paths_for_system(system_id, config)
    input_cfg = _collect_input_config(config)

    ctx = _SetupContext(
        emulator=emulator,
        emu_id=emu_id,
        game_path=game_path,
        system_id=system_id,
        exe_path=exe_path,
        config=config,
        rom_dir=rom_dir,
        bios_map=bios_map,
        input_cfg=input_cfg,
    )

    # Write a diagnostic file so the user can verify what Meridian sees.
    _write_debug_log(ctx)

    handler = _HANDLERS.get(emu_id)
    if handler is None:
        log.debug("No auto-configure handler for emulator id '%s'", emu_id)
        return

    log.debug(
        "Auto-configuring '%s': gamepad=%s driver=%s bindings=%d",
        emu_id, input_cfg.is_gamepad, input_cfg.driver,
        len(input_cfg.bindings),
    )
    try:
        handler(ctx)
    except Exception:
        log.exception("Failed to auto-configure emulator '%s'", emu_id)


def _write_debug_log(ctx: _SetupContext) -> None:
    """Write ``meridian_input_debug.txt`` next to the emulator exe.

    This lets the user (and us) verify exactly what Meridian sees when
    it tries to configure the emulator — emu-id, handler match, gamepad
    detection, bindings, and file paths.
    """
    try:
        inp = ctx.input_cfg
        handler = _HANDLERS.get(ctx.emu_id)
        lines = [
            f"Meridian auto-configure debug",
            f"=============================",
            f"emu_id          : {ctx.emu_id}",
            f"handler found   : {handler is not None}",
            f"exe_path        : {ctx.exe_path}",
            f"install_dir     : {ctx.install_dir}",
            f"system_id       : {ctx.system_id}",
            f"",
            f"--- Input Config ---",
            f"is_gamepad      : {inp.is_gamepad}",
            f"connected       : {inp.connected}",
            f"device          : {inp.device}",
            f"controller_type : {inp.controller_type}",
            f"driver          : {inp.driver}",
            f"sdl_guid        : {inp.sdl_guid or '(not detected)'}",
            f"sdl_device_index: {inp.sdl_device_index}",
            f"bindings count  : {len(inp.bindings)}",
        ]
        if inp.bindings:
            lines.append(f"")
            lines.append(f"--- Bindings ---")
            for k, v in sorted(inp.bindings.items()):
                lines.append(f"  {k:15s} = {v}")
        else:
            lines.append(f"")
            lines.append(f"*** NO BINDINGS — using SDL defaults ***")

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
        "config", "rom_dir", "bios_map", "input_cfg",
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
# Input configuration dataclass
# ---------------------------------------------------------------------------

class _InputConfig:
    """Normalized controller configuration derived from Meridian settings."""

    def __init__(self, config: Config):
        p1 = (config.input_player_settings or {}).get("1", {})
        self.connected: bool = bool(p1.get("connected", True))
        self.device: str = str(p1.get("device", "Any Available"))
        self.controller_type: str = str(p1.get("type", "Pro Controller"))
        self.bindings: dict[str, str] = dict(p1.get("bindings", {}))

        # Determine the SDL/platform driver from the type/device
        self.driver = self._detect_driver()
        # Detect the SDL GUID of the physical controller (needed by
        # Cemu, Citra, Eden, and other emulators that identify devices
        # by GUID rather than simple index).
        self.sdl_guid: str = self._detect_sdl_guid()
        self.sdl_device_index: int = self._detect_device_index()

    def _detect_driver(self) -> str:
        name = (self.device + " " + self.controller_type).lower()
        if "xinput" in name or "xbox" in name:
            return "xinput"
        if "dinput" in name:
            return "dinput"
        if "dualshock" in name or "dualsense" in name or "ds4" in name or "ds5" in name:
            return "sdl2"
        if "keyboard" in name:
            return "keyboard"
        # SDL2 is the best default for modern controllers
        return "sdl2"

    @property
    def is_gamepad(self) -> bool:
        return self.driver != "keyboard" and self.connected

    # -- Device identification ---------------------------------------------

    def _detect_sdl_guid(self) -> str:
        """Return the SDL GUID hex string for the configured controller."""
        try:
            import pygame
            if not pygame.joystick.get_init():
                return ""
            for i in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(i)
                joy.init()
                if (self.device == "Any Available"
                        or joy.get_name() == self.device):
                    return joy.get_guid()
        except Exception:
            pass
        return ""

    def _detect_device_index(self) -> int:
        """Return the SDL joystick index for the configured controller."""
        try:
            import pygame
            if not pygame.joystick.get_init():
                return 0
            for i in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(i)
                joy.init()
                if (self.device == "Any Available"
                        or joy.get_name() == self.device):
                    return i
        except Exception:
            pass
        return 0

    # -- Binding resolution ------------------------------------------------

    @staticmethod
    def _parse_binding(raw: str) -> tuple[str, int, str]:
        """Parse ``"Button 0"`` → ``("button", 0, "")``, etc."""
        raw = raw.strip()
        if raw.startswith("Button "):
            try:
                return ("button", int(raw.split()[1]), "")
            except (IndexError, ValueError):
                pass
        elif raw.startswith("Axis "):
            try:
                token = raw.split()[1]
                return ("axis", int(token[:-1]), token[-1])
            except (IndexError, ValueError):
                pass
        return ("none", 0, "")

    def resolve_button(self, name: str) -> int:
        """Return the raw SDL button index for *name* (user binding → default)."""
        raw = self.bindings.get(name, "")
        if raw:
            kind, idx, _ = self._parse_binding(raw)
            if kind == "button":
                return idx
        return _SDL_BUTTON_MAP.get(name, 0)

    def resolve_axis(self, name: str) -> tuple[int, str]:
        """Return ``(axis_index, direction)`` for *name* (user binding → default)."""
        raw = self.bindings.get(name, "")
        if raw:
            kind, idx, direction = self._parse_binding(raw)
            if kind == "axis":
                return (idx, direction)
        return _SDL_AXIS_MAP.get(name, (0, "+"))


def _collect_input_config(config: Config) -> _InputConfig:
    return _InputConfig(config)


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


# -- PPSSPP control-mapping helper (duplicate-key INI) ---------------------

def _patch_ppsspp_controls(path: Path, pad_mappings: dict[str, str]) -> None:
    """Update gamepad (device 10) control mappings in a PPSSPP INI file.

    PPSSPP allows duplicate keys (e.g. pad *and* keyboard for the same
    action) so we cannot use :mod:`configparser`.  This function replaces
    existing ``10-*`` (pad) entries while preserving keyboard and other
    device bindings.
    """
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    lines = text.splitlines()

    result: list[str] = []
    in_section = False
    found_section = False
    pad_prefix = "10-"

    for line in lines:
        stripped = line.strip()

        if stripped == "[ControlMapping]":
            found_section = True
            in_section = True
            result.append(line)
            # Inject our pad mappings at the top of the section
            for action, value in pad_mappings.items():
                result.append(f"{action} = {value}")
            continue

        if in_section:
            if stripped.startswith("["):
                in_section = False
                result.append(line)
                continue
            # Drop old pad bindings — we already wrote our new ones
            if "=" in stripped:
                _val = stripped.split("=", 1)[1].strip()
                if _val.startswith(pad_prefix):
                    continue
            result.append(line)
        else:
            result.append(line)

    if not found_section:
        result.append("")
        result.append("[ControlMapping]")
        for action, value in pad_mappings.items():
            result.append(f"{action} = {value}")

    path.parent.mkdir(parents=True, exist_ok=True)
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
# Standard XInput / SDL gamepad button indices
# =========================================================================
# These map Meridian's abstract binding names to the numeric button/axis
# indices used by SDL2 Game Controller (which XInput gamepads expose).
#
# SDL2 Game Controller standard mapping (matches Xbox layout):
#   Button 0 = A,  1 = B,  2 = X,  3 = Y
#   Button 4 = Back/Select,  5 = Guide/Home,  6 = Start
#   Button 7 = Left Stick Press,  8 = Right Stick Press
#   Button 9 = Left Shoulder (LB),  10 = Right Shoulder (RB)
#   Button 11 = DPad Up,  12 = DPad Down,  13 = DPad Left,  14 = DPad Right
#   Axis 0 = Left Stick X,  Axis 1 = Left Stick Y
#   Axis 2 = Right Stick X,  Axis 3 = Right Stick Y
#   Axis 4 = Left Trigger,   Axis 5 = Right Trigger

_SDL_BUTTON_MAP: dict[str, int] = {
    # Nintendo convention: A=east(1), B=south(0), X=north(3), Y=west(2)
    "a": 1, "b": 0, "x": 3, "y": 2,
    "minus": 4, "home": 5, "plus": 6,
    "ls_press": 7, "rs_press": 8,
    "l": 9, "r": 10,
    "dp_up": 11, "dp_down": 12, "dp_left": 13, "dp_right": 14,
    "capture": 15,
}

_SDL_AXIS_MAP: dict[str, tuple[int, str]] = {
    "ls_left": (0, "-"), "ls_right": (0, "+"),
    "ls_up": (1, "-"), "ls_down": (1, "+"),
    "rs_left": (2, "-"), "rs_right": (2, "+"),
    "rs_up": (3, "-"), "rs_down": (3, "+"),
    "zl": (4, "+"), "zr": (5, "+"),
}


# =========================================================================
# Per-emulator setup handlers
# =========================================================================

# -- RetroArch -------------------------------------------------------------

def _setup_retroarch(ctx: _SetupContext) -> None:
    """Patch retroarch.cfg with absolute paths and controller mappings."""
    cfg_path = ctx.install_dir / "retroarch.cfg"
    # Create the file if it doesn't exist (e.g. fresh install).
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if not cfg_path.exists():
        cfg_path.write_text("", encoding="utf-8")

    system_dir = str((ctx.install_dir / "system").resolve())
    patches: dict[str, str] = {
        "system_directory": system_dir,
        "input_autodetect_enable": "true",
    }

    # Use SDL2 by default — it has the best modern controller support
    inp = ctx.input_cfg
    if inp.is_gamepad:
        patches["input_driver"] = inp.driver if inp.driver != "keyboard" else "sdl2"
        patches["input_joypad_driver"] = inp.driver if inp.driver != "keyboard" else "sdl2"
    else:
        patches["input_driver"] = "sdl2"
        patches["input_joypad_driver"] = "sdl2"

    if ctx.rom_dir:
        patches["rgui_browser_directory"] = ctx.rom_dir
        patches["content_directory"] = ctx.rom_dir

    # Write gamepad button mappings for player 1 using Meridian's bindings.
    # RetroArch uses SNES naming and Meridian uses Nintendo Switch naming
    # — both place A on the east (right) and B on the south (bottom),
    # so the mapping is direct with no swap needed.
    if inp.is_gamepad:
        ra_btns = {
            "a":      str(inp.resolve_button("a")),
            "b":      str(inp.resolve_button("b")),
            "x":      str(inp.resolve_button("x")),
            "y":      str(inp.resolve_button("y")),
            "l":      str(inp.resolve_button("l")),
            "r":      str(inp.resolve_button("r")),
            "l3":     str(inp.resolve_button("ls_press")),
            "r3":     str(inp.resolve_button("rs_press")),
            "start":  str(inp.resolve_button("plus")),
            "select": str(inp.resolve_button("minus")),
            "up":     str(inp.resolve_button("dp_up")),
            "down":   str(inp.resolve_button("dp_down")),
            "left":   str(inp.resolve_button("dp_left")),
            "right":  str(inp.resolve_button("dp_right")),
        }
        for ra_name, btn_idx in ra_btns.items():
            patches[f"input_player1_{ra_name}_btn"] = btn_idx

        # Analog sticks — resolve from user bindings
        for ra_key, m_name in [
            ("l_x_plus_axis", "ls_right"), ("l_x_minus_axis", "ls_left"),
            ("l_y_plus_axis", "ls_down"),  ("l_y_minus_axis", "ls_up"),
            ("r_x_plus_axis", "rs_right"), ("r_x_minus_axis", "rs_left"),
            ("r_y_plus_axis", "rs_down"),  ("r_y_minus_axis", "rs_up"),
        ]:
            ax, d = inp.resolve_axis(m_name)
            patches[f"input_player1_{ra_key}"] = f"{d}{ax}"

        # Triggers
        zl_ax, zl_d = inp.resolve_axis("zl")
        zr_ax, zr_d = inp.resolve_axis("zr")
        patches["input_player1_l2_axis"] = f"{zl_d}{zl_ax}"
        patches["input_player1_r2_axis"] = f"{zr_d}{zr_ax}"

        patches["input_player1_joypad_index"] = "0"
        patches["input_player1_analog_dpad_mode"] = "0"

    # Ensure BIOS files are copied to the system directory
    bios_dir = Path(system_dir)
    bios_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, bios_dir)

    _patch_retroarch_cfg(cfg_path, patches)


# -- DuckStation -----------------------------------------------------------

def _setup_duckstation(ctx: _SetupContext) -> None:
    """Configure DuckStation for portable mode with BIOS, ROM paths, and input."""
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

    # Controller mapping — DuckStation uses SDL Game Controller indices
    inp = ctx.input_cfg
    if inp.is_gamepad:
        patches["Pad1"] = {
            "Type": "AnalogController",
            "Up": "SDL-0/DPadUp",
            "Down": "SDL-0/DPadDown",
            "Left": "SDL-0/DPadLeft",
            "Right": "SDL-0/DPadRight",
            "Triangle": "SDL-0/Y",
            "Circle": "SDL-0/B",
            "Cross": "SDL-0/A",
            "Square": "SDL-0/X",
            "L1": "SDL-0/LeftShoulder",
            "R1": "SDL-0/RightShoulder",
            "L2": "SDL-0/+LeftTrigger",
            "R2": "SDL-0/+RightTrigger",
            "L3": "SDL-0/LeftStick",
            "R3": "SDL-0/RightStick",
            "Select": "SDL-0/Back",
            "Start": "SDL-0/Start",
            "LLeft": "SDL-0/-LeftX",
            "LRight": "SDL-0/+LeftX",
            "LUp": "SDL-0/-LeftY",
            "LDown": "SDL-0/+LeftY",
            "RLeft": "SDL-0/-RightX",
            "RRight": "SDL-0/+RightX",
            "RUp": "SDL-0/-RightY",
            "RDown": "SDL-0/+RightY",
        }

    _patch_ini(settings_path, patches)


# -- PCSX2 ----------------------------------------------------------------

def _setup_pcsx2(ctx: _SetupContext) -> None:
    """Configure PCSX2 portable with BIOS directory and controller."""
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

    # PCSX2 v2 (pcsx2-qt) uses SDL Game Controller names
    inp = ctx.input_cfg
    if inp.is_gamepad:
        patches["Pad1"] = {
            "Type": "DualShock2",
            "Up": "SDL-0/DPadUp",
            "Down": "SDL-0/DPadDown",
            "Left": "SDL-0/DPadLeft",
            "Right": "SDL-0/DPadRight",
            "Triangle": "SDL-0/Y",
            "Circle": "SDL-0/B",
            "Cross": "SDL-0/A",
            "Square": "SDL-0/X",
            "L1": "SDL-0/LeftShoulder",
            "R1": "SDL-0/RightShoulder",
            "L2": "SDL-0/+LeftTrigger",
            "R2": "SDL-0/+RightTrigger",
            "L3": "SDL-0/LeftStick",
            "R3": "SDL-0/RightStick",
            "Select": "SDL-0/Back",
            "Start": "SDL-0/Start",
            "LLeft": "SDL-0/-LeftX",
            "LRight": "SDL-0/+LeftX",
            "LUp": "SDL-0/-LeftY",
            "LDown": "SDL-0/+LeftY",
            "RLeft": "SDL-0/-RightX",
            "RRight": "SDL-0/+RightX",
            "RUp": "SDL-0/-RightY",
            "RDown": "SDL-0/+RightY",
        }

    _patch_ini(settings_path, patches)


# -- PPSSPP ----------------------------------------------------------------

def _setup_ppsspp(ctx: _SetupContext) -> None:
    """Configure PPSSPP portable with flash0 BIOS assets and controller."""
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

    # Write gamepad control mapping.  PPSSPP uses NKCODE values with a
    # device prefix (10 = first gamepad).  The format allows duplicate keys
    # (pad + keyboard) so we use a custom patcher instead of configparser.
    inp = ctx.input_cfg
    if inp.is_gamepad:
        _patch_ppsspp_controls(ini_path, {
            "Up":       "10-19",
            "Down":     "10-20",
            "Left":     "10-21",
            "Right":    "10-22",
            "Circle":   "10-97",
            "Cross":    "10-96",
            "Square":   "10-99",
            "Triangle": "10-100",
            "Start":    "10-108",
            "Select":   "10-109",
            "L":        "10-102",
            "R":        "10-103",
            "An.Up":    "10-4001",
            "An.Down":  "10-4003",
            "An.Left":  "10-4000",
            "An.Right": "10-4002",
            "RightAn.Up":    "10-4005",
            "RightAn.Down":  "10-4007",
            "RightAn.Left":  "10-4004",
            "RightAn.Right": "10-4006",
        })


# -- Dolphin ---------------------------------------------------------------

def _setup_dolphin(ctx: _SetupContext) -> None:
    """Configure Dolphin in portable mode with ROM paths and controller."""
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
        "Core": {
            # Ensure GC Port 1 is an emulated pad; without this, mappings in
            # GCPadNew.ini can exist but remain inactive.
            "SIDevice0": "6",
        },
        "Interface": {
            "ConfirmStop": "false",
        },
    }
    if ctx.rom_dir:
        patches["General"]["ISOPath0"] = ctx.rom_dir

    _patch_ini(ini_path, patches)

    # Write GCPad controller profile for standard SDL gamepads.
    # Always overwrite so Meridian stays authoritative for input config.
    inp = ctx.input_cfg
    if inp.is_gamepad:
        gcpad_path = config_dir / "GCPadNew.ini"
        device_name = inp.device.strip()
        if not device_name or device_name.lower() == "any available":
            device_name = "Gamepad"
        gcpad_path.write_text(textwrap.dedent("""\
            [GCPad1]
            Device = SDL/0/{device_name}
            Buttons/A = `Button S`
            Buttons/B = `Button E`
            Buttons/X = `Button N`
            Buttons/Y = `Button W`
            Buttons/Z = `Shoulder R`
            Buttons/Start = `Start`
            D-Pad/Up = `Pad N`
            D-Pad/Down = `Pad S`
            D-Pad/Left = `Pad W`
            D-Pad/Right = `Pad E`
            Triggers/L = `Shoulder L`
            Triggers/R = `Trigger R`
            Triggers/L-Analog = `Full Axis 4+`
            Triggers/R-Analog = `Full Axis 5+`
            Main Stick/Up = `Left Y-`
            Main Stick/Down = `Left Y+`
            Main Stick/Left = `Left X-`
            Main Stick/Right = `Left X+`
            C-Stick/Up = `Right Y-`
            C-Stick/Down = `Right Y+`
            C-Stick/Left = `Right X-`
            C-Stick/Right = `Right X+`
        """.format(device_name=device_name)), encoding="utf-8")


# -- Cemu ------------------------------------------------------------------

def _setup_cemu(ctx: _SetupContext) -> None:
    """Configure Cemu in portable mode with keys, ROM paths, and controller."""
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

    # Generate Cemu controller profile
    inp = ctx.input_cfg
    if inp.is_gamepad:
        _write_cemu_controller_profile(ctx)


def _write_cemu_controller_profile(ctx: _SetupContext) -> None:
    """Write the active Wii U GamePad controller config for Cemu.

    Cemu's InputManager auto-loads ``controllerProfiles/controller0.xml``
    for player-index 0 (the Wii U GamePad slot).  Named profiles like
    ``meridian_gamepad.xml`` are only loaded through the GUI, so we must
    write directly to ``controller0.xml``.
    """
    # Cemu stores controller profiles as XML in controllerProfiles/
    profiles_dir = ctx.exe_path.parent / "controllerProfiles"
    if not profiles_dir.exists():
        # Try portable subdir
        profiles_dir = ctx.exe_path.parent / "portable" / "controllerProfiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    profile_path = profiles_dir / "controller0.xml"

    # Cemu SDLController.cpp builds the uuid as:
    #   m_uuid = fmt::format("{}_", guid_index) + SDL_JoystickGetGUIDString(guid)
    # i.e. "{device_index}_{sdl_guid_hex}" — index comes FIRST.
    inp = ctx.input_cfg
    cemu_uuid = "0_0"
    if inp.sdl_guid:
        cemu_uuid = f"{inp.sdl_device_index}_{inp.sdl_guid}"

    # Mapping IDs and button values taken from an actual working Cemu
    # controller config (Wii U Pro Controller type with SDLController).
    # Face buttons use the Nintendo→SDL positional swap (A=east→SDL B,
    # B=south→SDL A, etc.).  Axes use both positive AND negative
    # Buttons2 enum values.  ALL entries use <button>.
    _entries = [
        # Wii U Pro Controller face buttons — positional mapping
        (1,  1),   # A (east)   → SDL B (east)
        (2,  0),   # B (south)  → SDL A (south)
        (3,  3),   # X (north)  → SDL Y (north)
        (4,  2),   # Y (west)   → SDL X (west)
        # Shoulders
        (5,  9),   # L          → SDL LB
        (6,  10),  # R          → SDL RB
        # Triggers  (kTriggerXP=42, kTriggerYP=43)
        (7,  42),  # ZL         → kTriggerXP
        (8,  43),  # ZR         → kTriggerYP
        # Plus / Minus
        (9,  6),   # Plus       → SDL Start
        (10, 4),   # Minus      → SDL Back
        # D-Pad
        (12, 11),  # DPad Up    → SDL DPAD_UP
        (13, 12),  # DPad Down  → SDL DPAD_DOWN
        (14, 13),  # DPad Left  → SDL DPAD_LEFT
        (15, 14),  # DPad Right → SDL DPAD_RIGHT
        # Stick clicks
        (16, 7),   # L-Click    → SDL LeftStick
        (17, 8),   # R-Click    → SDL RightStick
        # Left stick axes (kAxisXP=38,XN=44,YP=39,YN=45)
        (18, 45),  # LStick Up    → kAxisYN
        (19, 39),  # LStick Down  → kAxisYP
        (20, 44),  # LStick Left  → kAxisXN
        (21, 38),  # LStick Right → kAxisXP
        # Right stick axes (kRotationXP=40,XN=46,YP=41,YN=47)
        (22, 47),  # RStick Up    → kRotationYN
        (23, 41),  # RStick Down  → kRotationYP
        (24, 46),  # RStick Left  → kRotationXN
        (25, 40),  # RStick Right → kRotationXP
    ]

    mapping_lines = "\n".join(
        f"            <entry>\n"
        f"                <mapping>{m}</mapping>\n"
        f"                <button>{b}</button>\n"
        f"            </entry>"
        for m, b in _entries
    )

    profile_xml = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <emulated_controller>
            <type>Wii U Pro Controller</type>
            <controller>
                <api>SDLController</api>
                <uuid>{cemu_uuid}</uuid>
                <display_name>{inp.device}</display_name>
                <rumble>0</rumble>
                <axis>
                    <deadzone>0.25</deadzone>
                    <range>1</range>
                </axis>
                <rotation>
                    <deadzone>0.25</deadzone>
                    <range>1</range>
                </rotation>
                <trigger>
                    <deadzone>0.15</deadzone>
                    <range>1</range>
                </trigger>
                <mappings>
        {mapping_lines}
                </mappings>
            </controller>
        </emulated_controller>
    """)

    profile_path.write_text(profile_xml, encoding="utf-8")


# -- melonDS ---------------------------------------------------------------

def _setup_melonds(ctx: _SetupContext) -> None:
    """Configure melonDS with BIOS paths and controller."""
    _ensure_portable(ctx.exe_path.parent)

    bios_dir = ctx.exe_path.parent / "bios"
    bios_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, bios_dir)

    toml_path = ctx.exe_path.parent / "melonDS.toml"
    ini_path = ctx.exe_path.parent / "melonDS.ini"

    bios_dir_str = str(bios_dir.resolve()).replace("\\", "/")

    inp = ctx.input_cfg

    if toml_path.exists():
        _patch_melonds_toml(toml_path, bios_dir_str, ctx.rom_dir)
        # Write joystick button mappings using user bindings
        if inp.is_gamepad:
            _patch_melonds_toml_joystick(toml_path, inp)
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
        # Write joystick button mappings for INI format
        if inp.is_gamepad:
            patches[""]["Joy_A"]      = str(inp.resolve_button("a"))
            patches[""]["Joy_B"]      = str(inp.resolve_button("b"))
            patches[""]["Joy_X"]      = str(inp.resolve_button("x"))
            patches[""]["Joy_Y"]      = str(inp.resolve_button("y"))
            patches[""]["Joy_Select"] = str(inp.resolve_button("minus"))
            patches[""]["Joy_Start"]  = str(inp.resolve_button("plus"))
            patches[""]["Joy_Up"]     = str(inp.resolve_button("dp_up"))
            patches[""]["Joy_Down"]   = str(inp.resolve_button("dp_down"))
            patches[""]["Joy_Left"]   = str(inp.resolve_button("dp_left"))
            patches[""]["Joy_Right"]  = str(inp.resolve_button("dp_right"))
            patches[""]["Joy_L"]      = str(inp.resolve_button("l"))
            patches[""]["Joy_R"]      = str(inp.resolve_button("r"))
            patches[""]["JoystickID"] = "0"
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


def _patch_melonds_toml_joystick(path: Path, inp: _InputConfig) -> None:
    """Write ``[Instance0.Joystick]`` button mappings into a melonDS TOML.

    Uses a section-scoped approach: splits the file into lines, locates
    the ``[Instance0.Joystick]`` section, and replaces values only
    within that section — avoiding incorrect matches in the Keyboard or
    other sections that share the same key names.
    """
    text = path.read_text(encoding="utf-8", errors="replace")

    joy_map = {
        "A":      str(inp.resolve_button("a")),
        "B":      str(inp.resolve_button("b")),
        "X":      str(inp.resolve_button("x")),
        "Y":      str(inp.resolve_button("y")),
        "Select": str(inp.resolve_button("minus")),
        "Start":  str(inp.resolve_button("plus")),
        "Up":     str(inp.resolve_button("dp_up")),
        "Down":   str(inp.resolve_button("dp_down")),
        "Left":   str(inp.resolve_button("dp_left")),
        "Right":  str(inp.resolve_button("dp_right")),
        "L":      str(inp.resolve_button("l")),
        "R":      str(inp.resolve_button("r")),
    }

    section_header = "[Instance0.Joystick]"
    lines = text.splitlines()

    # Find the section boundaries
    sec_start: int | None = None
    sec_end: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == section_header:
            sec_start = i
        elif sec_start is not None and line.strip().startswith("["):
            sec_end = i
            break
    if sec_start is not None and sec_end is None:
        sec_end = len(lines)

    if sec_start is not None:
        # Replace values ONLY inside the [Instance0.Joystick] section
        remaining = dict(joy_map)
        for i in range(sec_start + 1, sec_end):
            stripped = lines[i].strip()
            if "=" in stripped:
                lhs = stripped.split("=", 1)[0].strip()
                if lhs in remaining:
                    lines[i] = f"{lhs} = {remaining.pop(lhs)}"
        # Append any keys that weren't found in the section
        insert_at = sec_end
        for key, value in remaining.items():
            lines.insert(insert_at, f"{key} = {value}")
            insert_at += 1
    else:
        # Section doesn't exist — append it
        lines.append("")
        lines.append(section_header)
        for key, value in joy_map.items():
            lines.append(f"{key} = {value}")

    text = "\n".join(lines)

    # Ensure JoystickID is set (in [Instance0], not inside Joystick)
    jid_pattern = r'^(\s*JoystickID\s*=\s*)([^\n]+)'
    text, n = re.subn(jid_pattern, r'\g<1>0', text, count=1, flags=re.MULTILINE)
    if n == 0:
        text = text.rstrip() + "\nJoystickID = 0\n"

    path.write_text(text + "\n", encoding="utf-8")


# -- Ryubing / Ryujinx ----------------------------------------------------

def _setup_ryubing(ctx: _SetupContext) -> None:
    """Configure Ryubing/Ryujinx with keys paths and controller."""
    publish_dir = ctx.install_dir / "publish"
    exe_dir = publish_dir if publish_dir.exists() else ctx.exe_path.parent

    portable_dir = exe_dir / "portable"
    portable_dir.mkdir(parents=True, exist_ok=True)

    # Copy prod.keys and title.keys
    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})
    for bios_id, filename in [
        ("switch_prod_keys", "prod.keys"),
        ("switch_title_keys", "title.keys"),
    ]:
        src = str(bios_cfg.get(bios_id, "")).strip()
        if src and Path(src).exists():
            # Different Ryujinx/Ryubing builds may read from either
            # portable/system or <exe-dir>/system.
            for system_dir in [portable_dir / "system", exe_dir / "system"]:
                system_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, system_dir / filename)
                except Exception:
                    pass

    # Provision firmware for portable builds from a file or directory.
    # Accepts:
    #   - directory containing *.nca
    #   - directory containing .../Contents/registered/*.nca
    #   - zip archive with *.nca files
    fw_src = str(bios_cfg.get("switch_firmware", "")).strip()
    if fw_src:
        _provision_ryujinx_firmware(Path(fw_src), portable_dir)

    # Always write / merge controller config so Meridian stays authoritative.
    inp = ctx.input_cfg
    if inp.is_gamepad:
        input_entry = {
            "left_joycon_stick": {
                "joystick": "Left",
                "invert_stick_x": False,
                "invert_stick_y": False,
                "rotate90_cw": False,
                "stick_button": "LeftStick",
            },
            "right_joycon_stick": {
                "joystick": "Right",
                "invert_stick_x": False,
                "invert_stick_y": False,
                "rotate90_cw": False,
                "stick_button": "RightStick",
            },
            "left_joycon": {
                "button_minus": "Minus",
                "button_l": "LeftShoulder",
                "button_zl": "LeftTrigger",
                "button_sl": "Unbound",
                "button_sr": "Unbound",
                "dpad_up": "DpadUp",
                "dpad_down": "DpadDown",
                "dpad_left": "DpadLeft",
                "dpad_right": "DpadRight",
            },
            "right_joycon": {
                "button_plus": "Plus",
                "button_r": "RightShoulder",
                "button_zr": "RightTrigger",
                "button_sl": "Unbound",
                "button_sr": "Unbound",
                "button_x": "X",
                "button_b": "B",
                "button_y": "Y",
                "button_a": "A",
            },
            "version": 1,
            "backend": "GamepadSDL2",
            "id": f"{inp.sdl_device_index}-{inp.sdl_guid}" if inp.sdl_guid else "0",
            "controller_type": "ProController",
            "player_index": "Player1",
            "deadzone_left": 0.1,
            "deadzone_right": 0.1,
            "range_left": 1.0,
            "range_right": 1.0,
            "trigger_threshold": 0.5,
            "motion": {
                "motion_backend": "GamepadDriver",
                "sensitivity": 100,
                "gyro_deadzone": 1,
                "enable_motion": True,
            },
            "rumble": {
                "strong_rumble": 1.0,
                "weak_rumble": 1.0,
                "enable_rumble": True,
            },
        }
        config_candidates = [
            portable_dir / "Config" / "Config.json",
            portable_dir / "Config.json",
        ]
        for config_json in config_candidates:
            _merge_ryujinx_input_config(config_json, input_entry)


def _provision_ryujinx_firmware(source: Path, portable_dir: Path) -> None:
    """Copy/extract Switch firmware NCA files into portable bis layout."""
    try:
        if not source.exists():
            return

        registered_dirs = [
            portable_dir / "bis" / "system" / "Contents" / "registered",
            # Some forks/builds also probe this sibling layout.
            portable_dir / "system" / "Contents" / "registered",
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
                            except Exception:
                                continue
            except Exception:
                return

        if source.is_file() and source.suffix.lower() == ".nca":
            for dest_dir in registered_dirs:
                try:
                    shutil.copy2(source, dest_dir / source.name)
                except Exception:
                    continue
            return

        if source.is_dir():
            # Try all likely roots and aggregate files, do not stop at first
            # partial hit (some dumps contain mixed/partial layouts).
            candidate_dirs = [
                source / "registered",
                source / "Contents" / "registered",
                source / "system" / "Contents" / "registered",
                source / "bis" / "system" / "Contents" / "registered",
                source,
            ]
            seen: set[str] = set()
            for cand in candidate_dirs:
                key = str(cand.resolve()) if cand.exists() else str(cand)
                if key in seen:
                    continue
                seen.add(key)
                if cand.exists():
                    _copy_nca_tree(cand)
    except Exception:
        pass


def _merge_ryujinx_input_config(config_json: Path, input_entry: dict[str, Any]) -> None:
    """Merge gamepad config into a Ryujinx/Ryubing Config.json variant."""
    try:
        config_json.parent.mkdir(parents=True, exist_ok=True)
        if config_json.exists():
            data = json.loads(config_json.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        else:
            data = {}

        data.setdefault("version", 70)
        data["enable_keyboard"] = False
        data["enable_mouse"] = False
        data["input_config"] = [input_entry]

        config_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


# -- Eden ------------------------------------------------------------------

def _setup_eden(ctx: _SetupContext) -> None:
    """Configure Eden (Yuzu fork) with keys paths."""
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


# -- Citra -----------------------------------------------------------------

def _setup_citra(ctx: _SetupContext) -> None:
    """Configure Citra with BIOS and gamepad profile."""
    sysdata_dir = ctx.exe_path.parent / "user" / "sysdata"
    sysdata_dir.mkdir(parents=True, exist_ok=True)
    _copy_bios_to_dir(ctx, sysdata_dir)

    inp = ctx.input_cfg
    if not inp.is_gamepad:
        return

    qt_ini = ctx.exe_path.parent / "user" / "config" / "qt-config.ini"
    if not qt_ini.exists():
        return

    guid = inp.sdl_guid or "00000000000000000000000000000000"
    port = str(inp.sdl_device_index)

    def _citra_digital_expr(binding_name: str) -> str:
        raw = str(inp.bindings.get(binding_name, "")).strip()
        if raw.startswith("Button "):
            try:
                idx = int(raw.split()[1])
                return f"button:{idx},engine:sdl,guid:{guid},port:{port}"
            except Exception:
                pass
        if raw.startswith("Axis "):
            try:
                token = raw.split()[1]
                axis = int(token[:-1])
                direction = token[-1]
                threshold = "0.5" if direction == "+" else "-0.5"
                return (
                    f"axis:{axis},direction:{direction},engine:sdl,"
                    f"guid:{guid},port:{port},threshold:{threshold}"
                )
            except Exception:
                pass
        if raw.startswith("Hat "):
            try:
                parts = raw.split()
                hat_idx = int(parts[1])
                dirs = (parts[2] if len(parts) >= 3 else "").lower().split("+")
                for d in dirs:
                    if d in ("up", "down", "left", "right"):
                        return (
                            f"direction:{d},engine:sdl,guid:{guid},"
                            f"hat:{hat_idx},port:{port}"
                        )
            except Exception:
                pass
        # Fallback to the normalized SDL defaults.
        btn_idx = inp.resolve_button(binding_name)
        return f"button:{btn_idx},engine:sdl,guid:{guid},port:{port}"

    def _citra_analog_expr(x_neg_name: str, x_pos_name: str, y_neg_name: str, y_pos_name: str) -> str:
        x_neg_axis, _ = inp.resolve_axis(x_neg_name)
        x_pos_axis, _ = inp.resolve_axis(x_pos_name)
        y_neg_axis, _ = inp.resolve_axis(y_neg_name)
        y_pos_axis, _ = inp.resolve_axis(y_pos_name)

        # Citra stores analog maps in analog_from_button encoded format.
        # Keep this stable and SDL-backed to avoid keyboard-only defaults.
        return (
            "down:axis${y_pos}$1direction$0+$1engine$0sdl$1guid$0{guid}$1port$0{port}$1threshold$00.5,"
            "engine:analog_from_button,"
            "left:axis${x_neg}$1direction$0-$1engine$0sdl$1guid$0{guid}$1port$0{port}$1threshold$0-0.5,"
            "modifier:code$068$1engine$0keyboard,modifier_scale:0.500000,"
            "right:axis${x_pos}$1direction$0+$1engine$0sdl$1guid$0{guid}$1port$0{port}$1threshold$00.5,"
            "up:axis${y_neg}$1direction$0-$1engine$0sdl$1guid$0{guid}$1port$0{port}$1threshold$0-0.5"
        ).format(
            # Citra's parser expects zero-padded axis indices in this encoded
            # analog_from_button grammar (e.g. axis$00, axis$01).
            x_neg=f"{x_neg_axis:02d}",
            x_pos=f"{x_pos_axis:02d}",
            y_neg=f"{y_neg_axis:02d}",
            y_pos=f"{y_pos_axis:02d}",
            guid=guid,
            port=port,
        )

    controls_patch = {
        "profile\\default": "false",
        "profile": "0",
        "profiles\\size": "1",
        "profiles\\1\\name\\default": "false",
        "profiles\\1\\name": "Meridian SDL2",
        "profiles\\1\\button_a\\default": "false",
        "profiles\\1\\button_a": f"\"{_citra_digital_expr('a')}\"",
        "profiles\\1\\button_b\\default": "false",
        "profiles\\1\\button_b": f"\"{_citra_digital_expr('b')}\"",
        "profiles\\1\\button_x\\default": "false",
        "profiles\\1\\button_x": f"\"{_citra_digital_expr('x')}\"",
        "profiles\\1\\button_y\\default": "false",
        "profiles\\1\\button_y": f"\"{_citra_digital_expr('y')}\"",
        "profiles\\1\\button_up\\default": "false",
        "profiles\\1\\button_up": f"\"{_citra_digital_expr('dp_up')}\"",
        "profiles\\1\\button_down\\default": "false",
        "profiles\\1\\button_down": f"\"{_citra_digital_expr('dp_down')}\"",
        "profiles\\1\\button_left\\default": "false",
        "profiles\\1\\button_left": f"\"{_citra_digital_expr('dp_left')}\"",
        "profiles\\1\\button_right\\default": "false",
        "profiles\\1\\button_right": f"\"{_citra_digital_expr('dp_right')}\"",
        "profiles\\1\\button_l\\default": "false",
        "profiles\\1\\button_l": f"\"{_citra_digital_expr('l')}\"",
        "profiles\\1\\button_r\\default": "false",
        "profiles\\1\\button_r": f"\"{_citra_digital_expr('r')}\"",
        "profiles\\1\\button_start\\default": "false",
        "profiles\\1\\button_start": f"\"{_citra_digital_expr('plus')}\"",
        "profiles\\1\\button_select\\default": "false",
        "profiles\\1\\button_select": f"\"{_citra_digital_expr('minus')}\"",
        "profiles\\1\\button_zl\\default": "false",
        "profiles\\1\\button_zl": f"\"{_citra_digital_expr('zl')}\"",
        "profiles\\1\\button_zr\\default": "false",
        "profiles\\1\\button_zr": f"\"{_citra_digital_expr('zr')}\"",
        "profiles\\1\\circle_pad\\default": "false",
        "profiles\\1\\circle_pad": f"\"{_citra_analog_expr('ls_left', 'ls_right', 'ls_up', 'ls_down')}\"",
        "profiles\\1\\c_stick\\default": "false",
        "profiles\\1\\c_stick": f"\"{_citra_analog_expr('rs_left', 'rs_right', 'rs_up', 'rs_down')}\"",
        "profiles\\1\\motion_device\\default": "true",
        "profiles\\1\\motion_device": "\"engine:motion_emu,update_period:100,sensitivity:0.01,tilt_clamp:90.0\"",
        "profiles\\1\\touch_device\\default": "true",
        "profiles\\1\\touch_device": "engine:emu_window",
        "profiles\\1\\use_touch_from_button\\default": "true",
        "profiles\\1\\use_touch_from_button": "false",
        "profiles\\1\\touch_from_button_map\\default": "true",
        "profiles\\1\\touch_from_button_map": "0",
        "profiles\\1\\udp_input_address\\default": "true",
        "profiles\\1\\udp_input_address": "127.0.0.1",
        "profiles\\1\\udp_input_port\\default": "true",
        "profiles\\1\\udp_input_port": "26760",
        "profiles\\1\\udp_pad_index\\default": "true",
        "profiles\\1\\udp_pad_index": "0",
    }
    _patch_ini(qt_ini, {"Controls": controls_patch})


# -- RPCS3 -----------------------------------------------------------------

def _setup_rpcs3(ctx: _SetupContext) -> None:
    """Configure RPCS3 with firmware path and controller."""
    dev_flash = ctx.exe_path.parent / "dev_flash"
    dev_flash.mkdir(parents=True, exist_ok=True)

    bios_cfg = dict(getattr(ctx.config, "bios_files", {}) or {})
    fw_src = str(bios_cfg.get("ps3_firmware", "")).strip()
    if fw_src and Path(fw_src).exists():
        try:
            shutil.copy2(fw_src, ctx.exe_path.parent / "PS3UPDAT.PUP")
        except Exception:
            pass

    # RPCS3 stores pad config in config/input_configs/global/Default.yml.
    # Always overwrite so Meridian stays authoritative for input config.
    inp = ctx.input_cfg
    if inp.is_gamepad:
        pad_dir = ctx.exe_path.parent / "config" / "input_configs" / "global"
        pad_dir.mkdir(parents=True, exist_ok=True)
        pad_path = pad_dir / "Default.yml"
        pad_path.write_text(textwrap.dedent("""\
            Player 1 Input:
              Handler: XInput
              Device: XInput Pad #0
              Config:
                Left Stick Left: LS X-
                Left Stick Down: LS Y+
                Left Stick Right: LS X+
                Left Stick Up: LS Y-
                Right Stick Left: RS X-
                Right Stick Down: RS Y+
                Right Stick Right: RS X+
                Right Stick Up: RS Y-
                Start: Start
                Select: Back
                PS Button: Guide
                Square: X
                Cross: A
                Circle: B
                Triangle: Y
                Left: Left
                Down: Down
                Right: Right
                Up: Up
                R1: RB
                R2: RT
                R3: RS
                L1: LB
                L2: LT
                L3: LS
        """), encoding="utf-8")


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


# -- mGBA ------------------------------------------------------------------

# mGBA-Qt encodes SDL button/axis as high-bit-tagged integers:
#   Button N → 0x4000_0000 | N
#   Axis A dir D → 0x8000_0000 | (A << 1) | D   (D: 0 = negative, 1 = positive)
_MGBA_BTN  = 0x4000_0000
_MGBA_AXIS = 0x8000_0000


def _setup_mgba(ctx: _SetupContext) -> None:
    """Configure mGBA in portable mode with controller mapping."""
    _ensure_portable(ctx.install_dir, marker="portable.ini")

    qt_ini = ctx.exe_path.parent / "qt.ini"
    inp = ctx.input_cfg
    if not inp.is_gamepad:
        return

    # Build mappings for GBA and GB platforms using Meridian bindings.
    gba = {
        "platform.gba.A":      _MGBA_BTN | inp.resolve_button("a"),
        "platform.gba.B":      _MGBA_BTN | inp.resolve_button("b"),
        "platform.gba.L":      _MGBA_BTN | inp.resolve_button("l"),
        "platform.gba.R":      _MGBA_BTN | inp.resolve_button("r"),
        "platform.gba.Select": _MGBA_BTN | inp.resolve_button("minus"),
        "platform.gba.Start":  _MGBA_BTN | inp.resolve_button("plus"),
        "platform.gba.Up":     _MGBA_BTN | inp.resolve_button("dp_up"),
        "platform.gba.Down":   _MGBA_BTN | inp.resolve_button("dp_down"),
        "platform.gba.Left":   _MGBA_BTN | inp.resolve_button("dp_left"),
        "platform.gba.Right":  _MGBA_BTN | inp.resolve_button("dp_right"),
    }
    gb = {
        "platform.gb.A":      gba["platform.gba.A"],
        "platform.gb.B":      gba["platform.gba.B"],
        "platform.gb.Select": gba["platform.gba.Select"],
        "platform.gb.Start":  gba["platform.gba.Start"],
        "platform.gb.Up":     gba["platform.gba.Up"],
        "platform.gb.Down":   gba["platform.gba.Down"],
        "platform.gb.Left":   gba["platform.gba.Left"],
        "platform.gb.Right":  gba["platform.gba.Right"],
    }
    patches: dict[str, dict[str, str]] = {
        "ports.1": {k: str(v) for k, v in {**gba, **gb}.items()},
    }
    _patch_ini(qt_ini, patches)


# -- DeSmuME ---------------------------------------------------------------

def _setup_desmume(ctx: _SetupContext) -> None:
    """Configure DeSmuME with controller button indices."""
    # DeSmuME stores its config in DeSmuME.ini (DirectInput indices).
    # For XInput gamepads the DInput button indices match SDL standard.
    ini_path = ctx.exe_path.parent / "DeSmuME.ini"
    inp = ctx.input_cfg
    if not inp.is_gamepad:
        return

    patches: dict[str, dict[str, str]] = {
        "Controls": {
            "Joy_A":      str(inp.resolve_button("a")),
            "Joy_B":      str(inp.resolve_button("b")),
            "Joy_X":      str(inp.resolve_button("x")),
            "Joy_Y":      str(inp.resolve_button("y")),
            "Joy_L":      str(inp.resolve_button("l")),
            "Joy_R":      str(inp.resolve_button("r")),
            "Joy_Select": str(inp.resolve_button("minus")),
            "Joy_Start":  str(inp.resolve_button("plus")),
            "Joy_Up":     str(inp.resolve_button("dp_up")),
            "Joy_Down":   str(inp.resolve_button("dp_down")),
            "Joy_Left":   str(inp.resolve_button("dp_left")),
            "Joy_Right":  str(inp.resolve_button("dp_right")),
        },
    }
    _patch_ini(ini_path, patches)


# -- Mednafen --------------------------------------------------------------

def _setup_mednafen(ctx: _SetupContext) -> None:
    """Set up Mednafen base directory structure.

    Mednafen's input config uses per-device GUIDs that are assigned
    interactively at first run (Alt+Shift+1 in-game).  We set up the
    directory and ROM path; controller mapping is handled by Mednafen's
    own auto-configuration or the user's first-run setup.
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

    FCEUX on Windows uses DirectInput with device GUIDs, making it
    difficult to auto-configure input from an external tool.  We set up
    the base config; the user configures input once through FCEUX's
    Options > Gamepad dialog.  SDL Game Controller auto-detect handles
    most recognized gamepads.
    """
    cfg_path = ctx.exe_path.parent / "fceux.cfg"
    if not cfg_path.exists():
        cfg_path.write_text("", encoding="utf-8")

    _copy_bios_to_dir(ctx, ctx.exe_path.parent)

    inp = ctx.input_cfg
    if inp.is_gamepad:
        # Write SDL-style gamepad config (used by FCEUX SDL/Qt builds).
        text = cfg_path.read_text(encoding="utf-8", errors="replace")
        sdl_keys = {
            "SDL.Input.GamePad.0.DeviceType": "Gamepad",
            "SDL.Input.GamePad.0.DeviceNum":  "0",
            "SDL.Input.GamePad.0.A":          f"g0b{inp.resolve_button('a')}",
            "SDL.Input.GamePad.0.B":          f"g0b{inp.resolve_button('b')}",
            "SDL.Input.GamePad.0.Select":     f"g0b{inp.resolve_button('minus')}",
            "SDL.Input.GamePad.0.Start":      f"g0b{inp.resolve_button('plus')}",
            "SDL.Input.GamePad.0.Up":         f"g0b{inp.resolve_button('dp_up')}",
            "SDL.Input.GamePad.0.Down":       f"g0b{inp.resolve_button('dp_down')}",
            "SDL.Input.GamePad.0.Left":       f"g0b{inp.resolve_button('dp_left')}",
            "SDL.Input.GamePad.0.Right":      f"g0b{inp.resolve_button('dp_right')}",
            "SDL.Input.GamePad.0.TurboA":     "",
            "SDL.Input.GamePad.0.TurboB":     "",
        }
        for key, value in sdl_keys.items():
            pattern = rf'^(\s*{re.escape(key)}\s*=\s*)(.*)$'
            repl = rf'\g<1>{value}'
            text, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
            if n == 0:
                text += f"\n{key} = {value}"
        cfg_path.write_text(text + "\n", encoding="utf-8")


# -- Mesen -----------------------------------------------------------------

def _setup_mesen(ctx: _SetupContext) -> None:
    """Configure Mesen 2 controller mapping via settings.json."""
    settings_path = ctx.exe_path.parent / "settings.json"

    inp = ctx.input_cfg
    if not inp.is_gamepad:
        return

    # Mesen 2 uses SDL scancodes in its JSON config.  Build an input
    # profile for Player 1 with the user's Meridian bindings.
    # Mesen uses raw SDL2 button indices prefixed by the device index.
    mesen_input = {
        "type": "SnesController",
        "mapping1": {
            "a":      f"Pad0 But{inp.resolve_button('a')}",
            "b":      f"Pad0 But{inp.resolve_button('b')}",
            "x":      f"Pad0 But{inp.resolve_button('x')}",
            "y":      f"Pad0 But{inp.resolve_button('y')}",
            "l":      f"Pad0 But{inp.resolve_button('l')}",
            "r":      f"Pad0 But{inp.resolve_button('r')}",
            "select": f"Pad0 But{inp.resolve_button('minus')}",
            "start":  f"Pad0 But{inp.resolve_button('plus')}",
            "up":     f"Pad0 But{inp.resolve_button('dp_up')}",
            "down":   f"Pad0 But{inp.resolve_button('dp_down')}",
            "left":   f"Pad0 But{inp.resolve_button('dp_left')}",
            "right":  f"Pad0 But{inp.resolve_button('dp_right')}",
        },
    }

    if settings_path.exists():
        try:
            data = json.loads(
                settings_path.read_text(encoding="utf-8")
            )
            # Merge input config into the existing settings
            data.setdefault("input", {})["port1"] = mesen_input
            settings_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8",
            )
        except Exception:
            pass
    else:
        settings_path.write_text(
            json.dumps({"input": {"port1": mesen_input}}, indent=2),
            encoding="utf-8",
        )


# -- Snes9x ---------------------------------------------------------------

def _setup_snes9x(ctx: _SetupContext) -> None:
    """Configure Snes9x with controller mapping.

    The Windows GUI version stores joystick mappings in snes9x.conf.
    We write the config using DirectInput button indices which match
    SDL standard for XInput gamepads.
    """
    conf_path = ctx.exe_path.parent / "snes9x.conf"

    inp = ctx.input_cfg
    if not inp.is_gamepad:
        return

    # Snes9x Unix/X11 format: J<dev>:B<n> = Joypad1 <Button>
    # Maps user's physical buttons to SNES actions (same naming
    # convention as Meridian — A=east, B=south, X=north, Y=west).
    mappings = {
        f"J00:B{inp.resolve_button('a')}":     "Joypad1 A",
        f"J00:B{inp.resolve_button('b')}":     "Joypad1 B",
        f"J00:B{inp.resolve_button('x')}":     "Joypad1 X",
        f"J00:B{inp.resolve_button('y')}":     "Joypad1 Y",
        f"J00:B{inp.resolve_button('l')}":     "Joypad1 L",
        f"J00:B{inp.resolve_button('r')}":     "Joypad1 R",
        f"J00:B{inp.resolve_button('minus')}": "Joypad1 Select",
        f"J00:B{inp.resolve_button('plus')}":  "Joypad1 Start",
        "J00:Axis1": "Joypad1 Axis Up/Down T=50%",
        "J00:Axis0": "Joypad1 Axis Left/Right T=50%",
    }

    text = conf_path.read_text(encoding="utf-8", errors="replace") if conf_path.exists() else ""

    # Check if there's a controls section; if not, look for one to add to
    section_marker = "[Unix/X11 Controls]"
    if section_marker not in text:
        text = text.rstrip() + f"\n\n{section_marker}\n"
    for key, value in mappings.items():
        pattern = rf'^(\s*{re.escape(key)}\s*=\s*)(.*)$'
        repl = rf'\g<1>{value}'
        text, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
        if n == 0:
            text += f"\n{key} = {value}"
    conf_path.write_text(text + "\n", encoding="utf-8")


# -- SameBoy ---------------------------------------------------------------

def _setup_sameboy(ctx: _SetupContext) -> None:
    """Configure SameBoy for portable use.

    SameBoy uses SDL Game Controller for input and auto-detects
    recognized gamepads.  No explicit input config is needed.
    """
    _copy_bios_to_dir(ctx, ctx.exe_path.parent)


# -- Stella ----------------------------------------------------------------

def _setup_stella(ctx: _SetupContext) -> None:
    """Configure Stella (Atari 2600) for portable use.

    Stella uses SDL Game Controller which auto-detects most modern
    gamepads.  We set up the base directory; controller mapping is
    handled automatically by SDL.
    """
    _copy_bios_to_dir(ctx, ctx.exe_path.parent)


# -- Xenia -----------------------------------------------------------------

def _setup_xenia(ctx: _SetupContext) -> None:
    """Configure Xenia for portable use.

    Xenia uses XInput natively — Xbox / XInput-compatible controllers
    work out of the box with no configuration needed.
    """
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
