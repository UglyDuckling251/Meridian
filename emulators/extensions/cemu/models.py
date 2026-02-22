"""Typed data models for Cemu 2.6 controller profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Emulated controller types recognised by Cemu ─────────────────────────

EMULATED_TYPES: set[str] = {
    "Wii U GamePad",
    "Wii U Pro Controller",
    "Wii U Classic Controller",
    "Wii U Classic Controller Pro",
    "Wiimote",
}

# ── Input APIs supported by Cemu ─────────────────────────────────────────

CONTROLLER_APIS: set[str] = {
    "SDLController",
    "XInput",
    "DirectInput",
    "DSUController",
    "Keyboard",
}

# ── Mapping ID constants (VPAD / GamePad, 1-27) ─────────────────────────
# These mirror Cemu's internal emulated-button IDs.

MAPPING_A            = 1
MAPPING_B            = 2
MAPPING_X            = 3
MAPPING_Y            = 4
MAPPING_L            = 5
MAPPING_R            = 6
MAPPING_ZL           = 7
MAPPING_ZR           = 8
MAPPING_PLUS         = 9
MAPPING_MINUS        = 10
MAPPING_HOME         = 11
MAPPING_DPAD_UP      = 12
MAPPING_DPAD_DOWN    = 13
MAPPING_DPAD_LEFT    = 14
MAPPING_DPAD_RIGHT   = 15
MAPPING_LSTICK_DOWN  = 16   # Y-axis positive
MAPPING_LSTICK_UP    = 17   # Y-axis negative
MAPPING_LSTICK_LEFT  = 18   # X-axis negative
MAPPING_LSTICK_RIGHT = 19   # X-axis positive
MAPPING_RSTICK_DOWN  = 20
MAPPING_RSTICK_UP    = 21
MAPPING_RSTICK_LEFT  = 22
MAPPING_RSTICK_RIGHT = 23
MAPPING_LSTICK_PRESS = 24
MAPPING_RSTICK_PRESS = 25
MAPPING_MAX          = 27

MAPPING_NAMES: dict[int, str] = {
    MAPPING_A: "A", MAPPING_B: "B", MAPPING_X: "X", MAPPING_Y: "Y",
    MAPPING_L: "L", MAPPING_R: "R", MAPPING_ZL: "ZL", MAPPING_ZR: "ZR",
    MAPPING_PLUS: "Plus", MAPPING_MINUS: "Minus", MAPPING_HOME: "Home",
    MAPPING_DPAD_UP: "D-Pad Up", MAPPING_DPAD_DOWN: "D-Pad Down",
    MAPPING_DPAD_LEFT: "D-Pad Left", MAPPING_DPAD_RIGHT: "D-Pad Right",
    MAPPING_LSTICK_DOWN: "L-Stick Down", MAPPING_LSTICK_UP: "L-Stick Up",
    MAPPING_LSTICK_LEFT: "L-Stick Left", MAPPING_LSTICK_RIGHT: "L-Stick Right",
    MAPPING_RSTICK_DOWN: "R-Stick Down", MAPPING_RSTICK_UP: "R-Stick Up",
    MAPPING_RSTICK_LEFT: "R-Stick Left", MAPPING_RSTICK_RIGHT: "R-Stick Right",
    MAPPING_LSTICK_PRESS: "L-Stick Press", MAPPING_RSTICK_PRESS: "R-Stick Press",
}

# ── Cemu Buttons2 enum (physical input encoding) ────────────────────────
# These are the uint64 values Cemu stores in the <button> tag of its XML.
# Buttons 0-31 map directly to SDL_GameControllerButton indices.

BUTTON_ZL       = 32
BUTTON_ZR       = 33
BUTTON_UP       = 34
BUTTON_DOWN     = 35
BUTTON_LEFT     = 36
BUTTON_RIGHT    = 37
AXIS_X_POS      = 38   # Left stick X+
AXIS_Y_POS      = 39   # Left stick Y+
ROTATION_X_POS  = 40   # Right stick X+
ROTATION_Y_POS  = 41   # Right stick Y+
TRIGGER_X_POS   = 42   # Left trigger +
TRIGGER_Y_POS   = 43   # Right trigger +
AXIS_X_NEG      = 44   # Left stick X-
AXIS_Y_NEG      = 45   # Left stick Y-
ROTATION_X_NEG  = 46   # Right stick X-
ROTATION_Y_NEG  = 47   # Right stick Y-
TRIGGER_X_NEG   = 48   # Left trigger -
TRIGGER_Y_NEG   = 49   # Right trigger -

# SDL axis index -> (positive Buttons2 value, negative Buttons2 value)
SDL_AXIS_TO_BUTTONS2: dict[int, tuple[int, int]] = {
    0: (AXIS_X_POS,     AXIS_X_NEG),
    1: (AXIS_Y_POS,     AXIS_Y_NEG),
    2: (ROTATION_X_POS, ROTATION_X_NEG),
    3: (ROTATION_Y_POS, ROTATION_Y_NEG),
    4: (TRIGGER_X_POS,  TRIGGER_X_NEG),
    5: (TRIGGER_Y_POS,  TRIGGER_Y_NEG),
}


# ── Low-level data models ────────────────────────────────────────────────

@dataclass
class AxisSettings:
    """Deadzone / range pair used for axis, rotation, and trigger groups."""
    deadzone: float = 0.15
    range: float = 1.0

    def validate(self) -> None:
        if not (0.0 <= self.deadzone <= 1.0):
            raise ValueError(f"deadzone must be 0.0-1.0, got {self.deadzone}")
        if not (0.0 < self.range <= 2.0):
            raise ValueError(f"range must be >0.0 and <=2.0, got {self.range}")


@dataclass
class MappingEntry:
    """Single emulated-button <-> physical-input binding.

    *mapping_id* is the Cemu emulated-controller button ID (1-27 for VPAD).
    *button* is the physical controller button/axis flag-bit as Cemu stores it.
    """
    mapping_id: int
    button: int

    def validate(self) -> None:
        if self.mapping_id < 1 or self.mapping_id > MAPPING_MAX:
            raise ValueError(
                f"mapping_id must be 1-{MAPPING_MAX}, got {self.mapping_id}"
            )


@dataclass
class ControllerEntry:
    """One physical controller bound inside an emulated-controller profile."""
    api: str = "SDLController"
    uuid: str = "0"
    display_name: str = ""
    product_guid: str = ""
    rumble: float = 0.0
    motion: bool = False
    axis: AxisSettings = field(default_factory=AxisSettings)
    rotation: AxisSettings = field(default_factory=AxisSettings)
    trigger: AxisSettings = field(
        default_factory=lambda: AxisSettings(deadzone=0.25, range=1.0)
    )
    mappings: list[MappingEntry] = field(default_factory=list)

    def validate(self) -> None:
        if self.api and self.api not in CONTROLLER_APIS:
            raise ValueError(f"Unknown controller API {self.api!r}")
        self.axis.validate()
        self.rotation.validate()
        self.trigger.validate()
        seen: set[int] = set()
        for m in self.mappings:
            m.validate()
            if m.mapping_id in seen:
                raise ValueError(
                    f"Duplicate mapping_id {m.mapping_id} in controller"
                )
            seen.add(m.mapping_id)


@dataclass
class CemuProfile:
    """Complete Cemu 2.6 controller profile.

    Corresponds to one XML file inside ``controllerProfiles/``.
    """
    emulated_type: str = "Wii U GamePad"
    profile_name: str = ""
    controllers: list[ControllerEntry] = field(default_factory=list)

    def validate(self) -> None:
        if self.emulated_type not in EMULATED_TYPES:
            raise ValueError(
                f"Unknown emulated controller type {self.emulated_type!r}"
            )
        for c in self.controllers:
            c.validate()

    # ── Convenience factories ────────────────────────────────────────

    @classmethod
    def gamepad(
        cls,
        name: str = "",
        *,
        api: str = "SDLController",
        uuid: str = "0",
        display_name: str = "",
        mappings: list[MappingEntry] | None = None,
        **controller_kw: Any,
    ) -> CemuProfile:
        """Shorthand to build a *Wii U GamePad* profile with one controller."""
        ctrl = ControllerEntry(
            api=api,
            uuid=uuid,
            display_name=display_name,
            mappings=mappings or [],
            **controller_kw,
        )
        return cls(
            emulated_type="Wii U GamePad",
            profile_name=name,
            controllers=[ctrl],
        )

    @classmethod
    def pro_controller(
        cls,
        name: str = "",
        *,
        api: str = "SDLController",
        uuid: str = "0",
        display_name: str = "",
        mappings: list[MappingEntry] | None = None,
        **controller_kw: Any,
    ) -> CemuProfile:
        """Shorthand to build a *Wii U Pro Controller* profile."""
        ctrl = ControllerEntry(
            api=api,
            uuid=uuid,
            display_name=display_name,
            mappings=mappings or [],
            **controller_kw,
        )
        return cls(
            emulated_type="Wii U Pro Controller",
            profile_name=name,
            controllers=[ctrl],
        )
