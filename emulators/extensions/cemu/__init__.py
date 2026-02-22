"""Cemu controller-profile extension for Meridian.

Programmatic API for creating, importing, saving, loading, and applying
Cemu 2.6 controller profiles.  All operations are pure Python with no
external dependencies beyond the standard library.

Quick start::

    from emulators.extensions.cemu import (
        create_profile,
        save_profile,
        load_profile,
        list_profiles,
        import_profile,
        apply_profile_to_game,
    )

    profile = create_profile(
        name="MyProfile",
        emulated_type="Wii U GamePad",
        api="SDLController",
        uuid="0",
        display_name="DualSense Wireless Controller",
        mappings={1: 0, 2: 1, 3: 2, 4: 3},   # mapping_id -> button
    )
    save_profile(profile, cemu_dir="path/to/cemu")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    CONTROLLER_APIS,
    EMULATED_TYPES,
    MAPPING_NAMES,
    SDL_AXIS_TO_BUTTONS2,
    AxisSettings,
    CemuProfile,
    ControllerEntry,
    MappingEntry,
)
from .xml_io import parse_xml, to_xml, write_xml
from .repository import (
    activate_profile,
    apply_profile_to_game,
    delete_profile,
    list_profiles,
    load_profile,
    resolve_profile_dir,
    save_profile,
)
from .repository import import_profile as _repo_import
from .adapter import (
    cemu_to_meridian_bindings,
    meridian_player_to_cemu,
    meridian_players_to_cemu,
)
from ._launch import configure_input

__all__ = [
    # Models
    "CemuProfile",
    "ControllerEntry",
    "MappingEntry",
    "AxisSettings",
    "EMULATED_TYPES",
    "CONTROLLER_APIS",
    "MAPPING_NAMES",
    "SDL_AXIS_TO_BUTTONS2",
    # Launch hook
    "configure_input",
    # Core operations
    "create_profile",
    "import_profile",
    "save_profile",
    "load_profile",
    "list_profiles",
    "delete_profile",
    "activate_profile",
    "apply_profile_to_game",
    "resolve_profile_dir",
    # XML
    "parse_xml",
    "to_xml",
    "write_xml",
    # Adapter
    "meridian_player_to_cemu",
    "meridian_players_to_cemu",
    "cemu_to_meridian_bindings",
]


# ── Convenience factory ──────────────────────────────────────────────────

def create_profile(
    name: str = "",
    *,
    emulated_type: str = "Wii U GamePad",
    api: str = "SDLController",
    uuid: str = "0",
    display_name: str = "",
    rumble: float = 0.0,
    motion: bool = False,
    axis_deadzone: float = 0.15,
    axis_range: float = 1.0,
    rotation_deadzone: float = 0.15,
    rotation_range: float = 1.0,
    trigger_deadzone: float = 0.25,
    trigger_range: float = 1.0,
    mappings: dict[int, int] | list[MappingEntry] | None = None,
) -> CemuProfile:
    """Build a complete :class:`CemuProfile` with one physical controller.

    *mappings* accepts either a ``{mapping_id: button}`` dict or a list of
    :class:`MappingEntry` objects.

    Example::

        profile = create_profile(
            name="Player1",
            display_name="Xbox Controller",
            mappings={1: 0, 2: 1, 3: 2, 4: 3},
        )
    """
    if isinstance(mappings, dict):
        mapping_list = [
            MappingEntry(mapping_id=mid, button=btn)
            for mid, btn in mappings.items()
        ]
    elif mappings is not None:
        mapping_list = list(mappings)
    else:
        mapping_list = []

    controller = ControllerEntry(
        api=api,
        uuid=uuid,
        display_name=display_name,
        rumble=rumble,
        motion=motion,
        axis=AxisSettings(deadzone=axis_deadzone, range=axis_range),
        rotation=AxisSettings(deadzone=rotation_deadzone, range=rotation_range),
        trigger=AxisSettings(deadzone=trigger_deadzone, range=trigger_range),
        mappings=mapping_list,
    )

    return CemuProfile(
        emulated_type=emulated_type,
        profile_name=name,
        controllers=[controller],
    )


def import_profile(
    source: str | Path,
    cemu_dir: str | Path,
    name: str | None = None,
) -> CemuProfile:
    """Import an existing Cemu profile XML into *cemu_dir*.

    If *source* is a path to a file it is parsed and re-saved into the target
    Cemu installation's ``controllerProfiles`` directory.  If *name* is
    ``None`` the source filename stem is used.

    Returns the parsed :class:`CemuProfile`.
    """
    return _repo_import(source, cemu_dir, name)
