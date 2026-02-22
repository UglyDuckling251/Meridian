"""Convert between Meridian player settings and Cemu controller profiles.

Meridian stores per-player input configuration as dictionaries with keys
like ``connected``, ``api``, ``device``, ``device_index``, ``type``, and
``bindings`` (a ``{name: value}`` map).  This module translates those to
and from :class:`CemuProfile` objects.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .models import (
    AxisSettings,
    CemuProfile,
    ControllerEntry,
    MappingEntry,
    SDL_AXIS_TO_BUTTONS2,
)

log = logging.getLogger(__name__)


def _resolve_di_device(
    device_name: str,
    device_index: int | None = None,
) -> tuple[str, str] | None:
    """Find the DirectInput instance + product GUID for *device_name*.

    Returns ``(instance_guid, product_guid)`` or ``None``.
    """
    try:
        from ._windevice import find_device
        dev = find_device(device_name, preferred_index=device_index)
        if dev is not None:
            return dev.instance_guid, dev.product_guid
    except Exception:
        log.debug("DI device lookup failed for %r", device_name, exc_info=True)
    return None

# ── Meridian binding name -> Cemu emulated-button mapping ID ─────────────

_BIND_TO_MAPPING: dict[str, int] = {
    # --- Face buttons (all layouts) ---
    "a": 1,  "b": 2,  "x": 3,  "y": 4,
    "cross": 1,  "circle": 2,  "square": 3,  "triangle": 4,

    # --- Shoulders / triggers ---
    "l": 5,   "r": 6,   "zl": 7,  "zr": 8,
    "lb": 5,  "rb": 6,  "lt": 7,  "rt": 8,        # Xbox
    "l1": 5,  "r1": 6,  "l2": 7,  "r2": 8,        # DualShock / DualSense
    "sl": 5,  "sr": 6,                              # Joy-Con single
    "sl_l": 5, "sr_l": 6, "sl_r": 5, "sr_r": 6,   # Joy-Con L+R
    "l_zl": 7,                                       # Joy-Con single
    "z": 7,                                          # N64

    # --- Menu buttons ---
    "plus": 9,   "minus": 10,   "home": 11,
    "start": 9,  "back": 10,    "guide": 11,       # Xbox
    "options": 9, "share": 10,  "ps": 11,           # DualShock / DualSense
    "create": 10,                                    # DualSense
    "plus_minus": 9,                                 # Joy-Con single

    # --- D-Pad ---
    "dp_up": 12,  "dp_down": 13,  "dp_left": 14,  "dp_right": 15,

    # --- Left stick ---
    "ls_down": 16,  "ls_up": 17,  "ls_left": 18,  "ls_right": 19,
    "ls_click": 24, "ls_press": 24, "l3": 24,

    # --- Right stick ---
    "rs_down": 20,  "rs_up": 21,  "rs_left": 22,  "rs_right": 23,
    "rs_click": 25, "rs_press": 25, "r3": 25,
}

# Cemu uses different mapping-slot ordering for Pro Controller stick fields.
_PRO_STICK_BIND_TO_MAPPING: dict[str, int] = {
    "ls_click": 16, "ls_press": 16, "l3": 16,
    "rs_click": 17, "rs_press": 17, "r3": 17,
    "ls_up": 18, "ls_down": 19, "ls_left": 20, "ls_right": 21,
    "rs_up": 22, "rs_down": 23, "rs_left": 24, "rs_right": 25,
}

# Reverse: Cemu mapping ID -> canonical Meridian binding name.
# Uses the Pro Controller names as canonical since those match Cemu's own naming.
_MAPPING_TO_BIND: dict[int, str] = {
    1: "a",  2: "b",  3: "x",  4: "y",
    5: "l",  6: "r",  7: "zl", 8: "zr",
    9: "plus", 10: "minus", 11: "home",
    12: "dp_up", 13: "dp_down", 14: "dp_left", 15: "dp_right",
    16: "ls_down", 17: "ls_up", 18: "ls_left", 19: "ls_right",
    20: "rs_down", 21: "rs_up", 22: "rs_left", 23: "rs_right",
    24: "ls_click", 25: "rs_click",
}

_PRO_MAPPING_TO_BIND: dict[int, str] = {
    1: "a",  2: "b",  3: "x",  4: "y",
    5: "l",  6: "r",  7: "zl", 8: "zr",
    9: "plus", 10: "minus", 11: "home",
    12: "dp_up", 13: "dp_down", 14: "dp_left", 15: "dp_right",
    16: "ls_click", 17: "rs_click",
    18: "ls_up", 19: "ls_down", 20: "ls_left", 21: "ls_right",
    22: "rs_up", 23: "rs_down", 24: "rs_left", 25: "rs_right",
}

# ── Meridian emulated-type -> Cemu type string ──────────────────────────

_TYPE_MAP: dict[str, str] = {
    "Wii U GamePad":       "Wii U GamePad",
    "GamePad":             "Wii U GamePad",
    "Gamepad":             "Wii U GamePad",
    "Pro Controller":      "Wii U Pro Controller",
    "Wii U Pro Controller":"Wii U Pro Controller",
    "Classic Controller":  "Wii U Classic Controller",
    "Wii U Classic Controller": "Wii U Classic Controller",
    "Wiimote":             "Wiimote",
}

# Meridian API -> Cemu API
_API_MAP: dict[str, str] = {
    "Auto":            "DirectInput",
    "SDLController":   "SDLController",
    "SDL":             "SDLController",
    "XInput":          "XInput",
    "DirectInput":     "DirectInput",
    "Keyboard":        "Keyboard",
    "DSU":             "DSUController",
    "DSUController":   "DSUController",
}

# ── Binding value parsing ────────────────────────────────────────────────

_RE_BUTTON = re.compile(r'^Button\s+(\d+)$', re.IGNORECASE)
_RE_AXIS   = re.compile(r'^Axis\s+(\d+)([+-])$', re.IGNORECASE)
_RE_HAT    = re.compile(r'^Hat\s+(\d+)\s+(Up|Down|Left|Right)$', re.IGNORECASE)


def _normalize_directinput_binding(
    device_name: str,
    bind_name: str,
    bind_value: str,
) -> str:
    """Normalize Meridian DirectInput values to Cemu's expected DI layout.

    Meridian currently records DualSense DirectInput controls in a pygame-style
    layout that does not match Cemu's DirectInput numbering.  Translate those
    values so generated Cemu profiles match what Cemu's own input UI produces.
    """
    if "dualsense" not in device_name.lower():
        return bind_value

    value = bind_value.strip()

    # Cemu expects D-Pad as hat directions for DirectInput controllers.
    if bind_name == "dp_up":
        return "Hat 0 Up"
    if bind_name == "dp_down":
        return "Hat 0 Down"
    if bind_name == "dp_left":
        return "Hat 0 Left"
    if bind_name == "dp_right":
        return "Hat 0 Right"

    axis_match = _RE_AXIS.match(value)
    if axis_match:
        axis_idx = int(axis_match.group(1))
        sign = axis_match.group(2)

        # Triggers are exposed as buttons in Cemu's DirectInput backend.
        if bind_name == "zl" and axis_idx == 4:
            return "Button 6"
        if bind_name == "zr" and axis_idx == 5:
            return "Button 7"

        # Left Y axis is inverted between Meridian DI capture and Cemu DI.
        if bind_name in {"ls_up", "ls_down"} and axis_idx == 1:
            sign = "+" if sign == "-" else "-"

        # Right stick on DualSense DI uses Z/RZ in Cemu (axes 4/5).
        if bind_name in {"rs_left", "rs_right"} and axis_idx == 2:
            axis_idx = 4
        if bind_name in {"rs_up", "rs_down"} and axis_idx == 3:
            axis_idx = 5
            sign = "+" if sign == "-" else "-"

        return f"Axis {axis_idx}{sign}"

    button_match = _RE_BUTTON.match(value)
    if not button_match:
        return value

    btn = int(button_match.group(1))
    button_map: dict[int, int] = {
        0: 1,
        1: 2,
        2: 0,
        3: 3,
        4: 8,
        6: 9,
        7: 10,
        8: 11,
        9: 4,
        10: 5,
    }
    mapped = button_map.get(btn, btn)
    return f"Button {mapped}"


def _parse_binding_value(value: str) -> int | None:
    """Convert a Meridian binding value to a Cemu Buttons2 integer.

    Returns ``None`` for values that have no Cemu equivalent (e.g. "Gyro").
    """
    value = value.strip()

    m = _RE_BUTTON.match(value)
    if m:
        return int(m.group(1))

    m = _RE_AXIS.match(value)
    if m:
        axis_idx = int(m.group(1))
        direction = m.group(2)
        pair = SDL_AXIS_TO_BUTTONS2.get(axis_idx)
        if pair is None:
            log.warning("Unknown SDL axis index %d", axis_idx)
            return None
        return pair[0] if direction == "+" else pair[1]

    m = _RE_HAT.match(value)
    if m:
        hat_dir = m.group(2).lower()
        hat_buttons = {"up": 34, "down": 35, "left": 36, "right": 37}
        return hat_buttons.get(hat_dir)

    if value.lower() in ("gyro", "motion", "none", ""):
        return None

    log.debug("Unrecognised Meridian binding value: %r", value)
    return None


# ── Public conversion functions ──────────────────────────────────────────

def meridian_player_to_cemu(
    player_data: dict[str, Any],
    *,
    profile_name: str = "",
) -> CemuProfile | None:
    """Build a :class:`CemuProfile` from a single Meridian player dict.

    Returns ``None`` if the player is not connected or has no bindings.
    """
    if not player_data.get("connected"):
        return None

    bindings: dict[str, str] = player_data.get("bindings") or {}
    if not bindings:
        return None

    meridian_api = str(player_data.get("api", "Auto"))
    api = _API_MAP.get(meridian_api, "DirectInput")
    device = str(player_data.get("device", ""))
    device_index = player_data.get("device_index")
    device_guid = str(player_data.get("device_guid", "")).strip()

    uuid = "0"
    product_guid = ""

    if api == "DirectInput":
        di_dev = _resolve_di_device(
            device,
            device_index if isinstance(device_index, int) else None,
        )
        if di_dev is not None:
            uuid = di_dev[0]
            product_guid = di_dev[1]
        elif device_guid:
            uuid = device_guid
    elif api == "SDLController" and device_guid:
        uuid = device_guid
    elif api == "XInput":
        uuid = str(device_index) if device_index not in (None, "None") else "0"
    elif device_index not in (None, "None"):
        uuid = str(device_index)

    ptype = str(player_data.get("type", "Wii U GamePad"))
    emulated_type = _TYPE_MAP.get(ptype, "Wii U GamePad")
    bind_to_mapping = _BIND_TO_MAPPING
    if emulated_type == "Wii U Pro Controller":
        bind_to_mapping = {**_BIND_TO_MAPPING, **_PRO_STICK_BIND_TO_MAPPING}

    mappings: list[MappingEntry] = []
    has_motion = False

    for bind_name, bind_value in bindings.items():
        name_lower = bind_name.lower().strip()

        if name_lower == "motion":
            if bind_value and bind_value.lower() not in ("none", ""):
                has_motion = True
            continue

        mapping_id = bind_to_mapping.get(name_lower)
        if mapping_id is None:
            log.debug("Skipping unknown Meridian binding %r", bind_name)
            continue

        value = str(bind_value)
        if api == "DirectInput" and emulated_type == "Wii U Pro Controller":
            value = _normalize_directinput_binding(device, name_lower, value)

        button = _parse_binding_value(value)
        if button is None:
            continue

        mappings.append(MappingEntry(mapping_id=mapping_id, button=button))

    if not mappings:
        return None

    controller = ControllerEntry(
        api=api,
        uuid=uuid,
        display_name=device or "Meridian Controller",
        product_guid=product_guid,
        motion=has_motion,
        mappings=mappings,
    )

    return CemuProfile(
        emulated_type=emulated_type,
        profile_name=profile_name,
        controllers=[controller],
    )


def meridian_players_to_cemu(
    player_settings: dict[str, dict],
    *,
    name_prefix: str = "meridian_player",
) -> dict[int, CemuProfile]:
    """Convert a full Meridian player-settings dict to per-player Cemu profiles.

    Returns ``{1: profile, 2: profile, ...}`` only for connected players.
    """
    results: dict[int, CemuProfile] = {}
    for player_num_str, pdata in sorted(player_settings.items()):
        if not isinstance(pdata, dict):
            continue
        try:
            idx = int(player_num_str)
        except (ValueError, TypeError):
            continue
        profile = meridian_player_to_cemu(
            pdata,
            profile_name=f"{name_prefix}{idx}",
        )
        if profile is not None:
            results[idx] = profile
    return results


def cemu_to_meridian_bindings(
    profile: CemuProfile,
) -> dict[str, str]:
    """Extract Meridian-style bindings from the first controller in *profile*.

    Returns ``{binding_name: binding_value}`` (e.g. ``{"a": "Button 1"}``).
    """
    if not profile.controllers:
        return {}
    ctrl = profile.controllers[0]
    result: dict[str, str] = {}

    mapping_to_bind = _MAPPING_TO_BIND
    if profile.emulated_type == "Wii U Pro Controller":
        mapping_to_bind = _PRO_MAPPING_TO_BIND

    for m in ctrl.mappings:
        bind_name = mapping_to_bind.get(m.mapping_id)
        if bind_name is None:
            continue
        result[bind_name] = _button_to_meridian_value(m.button)

    if ctrl.motion:
        result["motion"] = "Gyro"

    return result


def _button_to_meridian_value(button: int) -> str:
    """Convert a Cemu Buttons2 value back to Meridian binding string."""
    if button <= 31:
        return f"Button {button}"

    for axis_idx, (pos, neg) in SDL_AXIS_TO_BUTTONS2.items():
        if button == pos:
            return f"Axis {axis_idx}+"
        if button == neg:
            return f"Axis {axis_idx}-"

    hat_map = {34: "Hat 0 Up", 35: "Hat 0 Down", 36: "Hat 0 Left", 37: "Hat 0 Right"}
    if button in hat_map:
        return hat_map[button]

    return f"Button {button}"
