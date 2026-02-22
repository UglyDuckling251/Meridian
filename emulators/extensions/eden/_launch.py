"""Launch-time hook for the Eden extension.

Called automatically by Meridian's extension dispatch when Eden is
launched.  Converts Meridian player settings to Eden qt-config.ini
control entries and writes them to disk.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .adapter import meridian_players_to_eden
from .config_io import patch_controls, resolve_config_path

log = logging.getLogger(__name__)


def configure_input(
    player_settings: dict[str, dict],
    exe_path: Path,
    game_path: Path | None = None,
) -> None:
    """Write Eden controller config from Meridian player settings.

    Standard extension entry point invoked by
    ``emulator_setup._run_extension_input``.
    """
    eden_dir = exe_path.parent
    config_path = resolve_config_path(eden_dir)

    profiles = meridian_players_to_eden(player_settings)

    all_updates: dict[str, str] = {}
    active_slots: set[int] = set()

    for eden_idx, entries in profiles.items():
        active_slots.add(eden_idx)
        all_updates.update(entries)
        log.debug(
            "Converted player %d -> Eden player_%d (%d keys)",
            eden_idx + 1, eden_idx, len(entries),
        )

    # Mark disconnected players as not connected.
    for player_num_str, pdata in player_settings.items():
        try:
            idx = int(player_num_str)
        except (TypeError, ValueError):
            continue
        if not 1 <= idx <= 10:
            continue
        if not isinstance(pdata, dict):
            continue
        eden_idx = idx - 1
        if eden_idx in active_slots:
            continue
        prefix = f"player_{eden_idx}"
        all_updates[f"{prefix}_connected\\default"] = "false"
        all_updates[f"{prefix}_connected"] = "false"

    if not all_updates:
        log.debug("No Eden control entries to write")
        return

    try:
        patch_controls(config_path, all_updates)
        log.debug(
            "Wrote %d Eden control entries to %s",
            len(all_updates), config_path,
        )
    except Exception:
        log.debug("Failed to patch Eden config", exc_info=True)
