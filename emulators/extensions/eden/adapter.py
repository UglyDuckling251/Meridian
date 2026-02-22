"""Convert Meridian player settings to Eden qt-config.ini control entries.

Meridian stores per-player input as dictionaries with ``connected``, ``api``,
``device``, ``device_index``, ``device_guid``, ``type``, and ``bindings``.
This module converts those to the key=value pairs Eden writes under
``[Controls]``.

Eden (Yuzu fork) uses SDL engine strings of the form::

    "engine:sdl,guid:<GUID>,port:<N>,pad:<N>,button:<N>"
    "engine:sdl,guid:<GUID>,port:<N>,pad:<N>,axis:<N>,threshold:0.500000,direction:+"
"""

from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

# ── Meridian binding name -> Eden config key suffix ──────────────────────
# Appended to ``player_{N}_`` to form the full INI key.

_BIND_TO_EDEN_KEY: dict[str, str] = {
    # Face buttons
    "a": "button_a", "b": "button_b", "x": "button_x", "y": "button_y",
    "cross": "button_a", "circle": "button_b",
    "square": "button_x", "triangle": "button_y",

    # Shoulders / triggers
    "l": "button_l", "r": "button_r", "zl": "button_zl", "zr": "button_zr",
    "lb": "button_l", "rb": "button_r", "lt": "button_zl", "rt": "button_zr",
    "l1": "button_l", "r1": "button_r", "l2": "button_zl", "r2": "button_zr",

    # Menu
    "plus": "button_plus", "minus": "button_minus", "home": "button_home",
    "capture": "button_screenshot",
    "start": "button_plus", "back": "button_minus", "guide": "button_home",
    "options": "button_plus", "share": "button_minus", "create": "button_minus",
    "ps": "button_home",

    # D-Pad
    "dp_up": "button_dup", "dp_down": "button_ddown",
    "dp_left": "button_dleft", "dp_right": "button_dright",

    # Stick clicks
    "ls_press": "button_lstick", "ls_click": "button_lstick", "l3": "button_lstick",
    "rs_press": "button_rstick", "rs_click": "button_rstick", "r3": "button_rstick",
}

# Stick direction bindings that contribute axis info for compound stick entries.
_STICK_DIRECTION_KEYS = frozenset({
    "ls_up", "ls_down", "ls_left", "ls_right",
    "rs_up", "rs_down", "rs_left", "rs_right",
})

# ── Eden controller type enum ───────────────────────────────────────────

_EDEN_TYPE: dict[str, int] = {
    "Pro Controller": 0,
    "Dual Joycons": 1,
    "Left Joycon": 2,
    "Right Joycon": 3,
    "Handheld": 4,
    "GameCube Controller": 5,
}

# ── Binding value parsing ────────────────────────────────────────────────

_RE_BUTTON = re.compile(r"^Button\s+(\d+)$", re.IGNORECASE)
_RE_AXIS = re.compile(r"^Axis\s+(\d+)([+-])$", re.IGNORECASE)
_RE_HAT = re.compile(r"^Hat\s+(\d+)\s+(Up|Down|Left|Right)$", re.IGNORECASE)

_HAT_TO_BUTTON: dict[str, int] = {
    "up": 11, "down": 12, "left": 13, "right": 14,
}


def _build_sdl_base(guid: str, port: int, pad: int) -> str:
    return f"engine:sdl,guid:{guid},port:{port},pad:{pad}"


def _binding_to_eden_value(
    bind_value: str, guid: str, port: int, pad: int,
) -> str | None:
    """Convert a single Meridian binding value to a quoted Eden input string.

    Returns ``None`` for unsupported values (gyro, empty, etc.).
    """
    value = bind_value.strip()
    if not value or value.lower() in ("none", "gyro", "motion"):
        return None

    base = _build_sdl_base(guid, port, pad)

    m = _RE_BUTTON.match(value)
    if m:
        return f'"{base},button:{m.group(1)}"'

    m = _RE_AXIS.match(value)
    if m:
        axis_idx = m.group(1)
        direction = m.group(2)
        return (
            f'"{base},axis:{axis_idx},'
            f'threshold:0.500000,direction:{direction}"'
        )

    m = _RE_HAT.match(value)
    if m:
        hat_dir = m.group(2).lower()
        btn = _HAT_TO_BUTTON.get(hat_dir)
        if btn is not None:
            return f'"{base},button:{btn}"'

    log.debug("Unsupported Meridian binding value for Eden: %r", value)
    return None


def _stick_axes_from_bindings(
    bindings: dict[str, str],
    up_key: str,
    left_key: str,
) -> tuple[int, int] | None:
    """Extract ``(axis_x, axis_y)`` from individual stick-direction bindings."""
    axis_x: int | None = None
    axis_y: int | None = None

    m = _RE_AXIS.match((bindings.get(left_key) or "").strip())
    if m:
        axis_x = int(m.group(1))
    m = _RE_AXIS.match((bindings.get(up_key) or "").strip())
    if m:
        axis_y = int(m.group(1))

    if axis_x is not None and axis_y is not None:
        return (axis_x, axis_y)
    return None


# ── Public conversion functions ──────────────────────────────────────────

def meridian_player_to_eden(
    player_data: dict[str, Any],
    *,
    eden_index: int,
) -> dict[str, str] | None:
    """Convert a single Meridian player dict to Eden INI key/value pairs.

    *eden_index* is the 0-based Eden player slot.
    Returns ``None`` if the player is not connected or has no bindings.
    The returned dict maps full INI keys (e.g. ``player_0_button_a``) to
    their serialized values.
    """
    if not player_data.get("connected"):
        return None

    bindings: dict[str, str] = player_data.get("bindings") or {}
    if not bindings:
        return None

    device_guid = str(player_data.get("device_guid", "")).strip()
    device_index = player_data.get("device_index")
    port = int(device_index) if isinstance(device_index, int) else eden_index
    pad = port
    guid = device_guid or "0"

    has_motion = False
    motion_val = (bindings.get("motion") or "").strip().lower()
    if motion_val and motion_val not in ("none", ""):
        has_motion = True

    prefix = f"player_{eden_index}"
    result: dict[str, str] = {}

    # Controller type
    ptype = str(player_data.get("type", "Pro Controller"))
    eden_type = _EDEN_TYPE.get(ptype, 0)
    result[f"{prefix}_type\\default"] = "false"
    result[f"{prefix}_type"] = str(eden_type)

    # Connected
    result[f"{prefix}_connected\\default"] = "false"
    result[f"{prefix}_connected"] = "true"

    # Vibration
    result[f"{prefix}_vibration_enabled\\default"] = "false"
    result[f"{prefix}_vibration_enabled"] = "true"

    # Button bindings
    for bind_name, bind_value in bindings.items():
        name_lower = bind_name.lower().strip()

        if name_lower == "motion" or name_lower in _STICK_DIRECTION_KEYS:
            continue

        eden_key = _BIND_TO_EDEN_KEY.get(name_lower)
        if eden_key is None:
            continue

        eden_val = _binding_to_eden_value(bind_value, guid, port, pad)
        if eden_val is None:
            continue

        full_key = f"{prefix}_{eden_key}"
        result[f"{full_key}\\default"] = "false"
        result[full_key] = eden_val

    # Analog sticks — compose compound entries from individual axis bindings.
    for stick_name, up_key, left_key, default_x, default_y in [
        ("lstick", "ls_up", "ls_left", 0, 1),
        ("rstick", "rs_up", "rs_left", 2, 3),
    ]:
        axes = _stick_axes_from_bindings(bindings, up_key, left_key)
        ax, ay = axes if axes else (default_x, default_y)
        base = _build_sdl_base(guid, port, pad)
        stick_val = (
            f'"{base},axis_x:{ax},axis_y:{ay},'
            f'deadzone:0.150000,range:1.000000,threshold:0.500000"'
        )
        full_key = f"{prefix}_{stick_name}"
        result[f"{full_key}\\default"] = "false"
        result[full_key] = stick_val

    # Motion
    if has_motion:
        base = _build_sdl_base(guid, port, pad)
        result[f"{prefix}_motionleft\\default"] = "false"
        result[f"{prefix}_motionleft"] = f'"{base},motion:0"'
        result[f"{prefix}_motionright\\default"] = "false"
        result[f"{prefix}_motionright"] = f'"{base},motion:1"'

    return result


def meridian_players_to_eden(
    player_settings: dict[str, dict],
) -> dict[int, dict[str, str]]:
    """Convert all Meridian player settings to per-player Eden INI entries.

    Returns ``{eden_index: {key: value, ...}}`` for connected players only.
    """
    results: dict[int, dict[str, str]] = {}
    for player_num_str, pdata in sorted(player_settings.items()):
        if not isinstance(pdata, dict):
            continue
        try:
            idx = int(player_num_str)
        except (ValueError, TypeError):
            continue
        eden_idx = idx - 1
        if eden_idx < 0 or eden_idx > 9:
            continue
        entries = meridian_player_to_eden(pdata, eden_index=eden_idx)
        if entries is not None:
            results[eden_idx] = entries
    return results
