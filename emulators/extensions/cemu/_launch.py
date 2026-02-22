"""Launch-time hook for the Cemu extension.

Called automatically by Meridian's extension dispatch when Cemu is
launched.  Converts Meridian player settings to Cemu XML profiles,
writes them to disk, and assigns them to the game being launched.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .adapter import meridian_players_to_cemu
from .models import CemuProfile, ControllerEntry
from .repository import (
    activate_profile,
    apply_profile_to_game,
    delete_profile,
    deactivate_slot,
    resolve_profile_dir,
    save_profile,
)
from .xml_io import parse_xml

log = logging.getLogger(__name__)


def configure_input(
    player_settings: dict[str, dict],
    exe_path: Path,
    game_path: Path | None = None,
) -> None:
    """Write Cemu controller profiles from Meridian player settings.

    This is the standard extension entry point invoked by
    ``emulator_setup._run_extension_input``.
    """
    cemu_dir = exe_path.parent
    profiles = meridian_players_to_cemu(player_settings)

    player_profile_map: dict[int, str] = {}
    active_slots: set[int] = set()
    for player_idx, profile in profiles.items():
        try:
            slot = player_idx - 1
            active_slots.add(slot)
            merged = _merge_with_existing(slot, profile, cemu_dir)
            save_profile(merged, cemu_dir)
            activate_profile(merged, slot, cemu_dir)
            player_profile_map[player_idx] = merged.profile_name
            log.debug(
                "Wrote Cemu profile %r for player %d (slot %d) api=%s uuid=%s",
                merged.profile_name,
                player_idx,
                slot,
                merged.controllers[0].api if merged.controllers else "?",
                merged.controllers[0].uuid if merged.controllers else "?",
            )
        except Exception:
            log.debug(
                "Failed to write Cemu profile for player %d",
                player_idx,
                exc_info=True,
            )

    # Ensure disconnected players are fully removed from active Cemu slots.
    # We only touch slots represented in current player settings.
    for player_num, pdata in player_settings.items():
        try:
            idx = int(player_num)
        except (TypeError, ValueError):
            continue
        if not 1 <= idx <= 8:
            continue
        if not isinstance(pdata, dict):
            continue
        slot = idx - 1
        if slot in active_slots:
            continue
        try:
            deactivate_slot(slot, cemu_dir)
            delete_profile(cemu_dir, f"meridian_player{idx}")
        except Exception:
            log.debug("Failed to deactivate Cemu slot %d", slot, exc_info=True)

    if player_profile_map and game_path:
        title_id = _extract_title_id(game_path, cemu_dir)
        if title_id:
            try:
                apply_profile_to_game(title_id, player_profile_map, cemu_dir)
                log.debug("Assigned profiles to game %s", title_id)
            except Exception:
                log.debug("Failed to assign game profile", exc_info=True)


def _merge_with_existing(
    slot: int, new_profile: CemuProfile, cemu_dir: Path,
) -> CemuProfile:
    """Merge Meridian mappings into an existing slot file's device connection.

    If ``controller{slot}.xml`` exists and has a valid device connection
    (API + UUID), preserve that connection and only replace the mappings,
    emulated type, and profile name.  This avoids clobbering a working
    device pairing that the user (or Cemu's UI) established.
    """
    profile_dir = resolve_profile_dir(cemu_dir)
    slot_path = profile_dir / f"controller{slot}.xml"

    if not slot_path.exists():
        return new_profile

    try:
        existing = parse_xml(slot_path)
    except Exception:
        return new_profile

    if not existing.controllers or not new_profile.controllers:
        return new_profile

    old_ctrl = existing.controllers[0]
    new_ctrl = new_profile.controllers[0]

    if not old_ctrl.uuid or old_ctrl.uuid == "0":
        return new_profile

    merged_ctrl = ControllerEntry(
        api=old_ctrl.api,
        uuid=old_ctrl.uuid,
        display_name=old_ctrl.display_name or new_ctrl.display_name,
        product_guid=old_ctrl.product_guid or new_ctrl.product_guid,
        rumble=old_ctrl.rumble,
        motion=new_ctrl.motion,
        axis=old_ctrl.axis,
        rotation=old_ctrl.rotation,
        trigger=old_ctrl.trigger,
        mappings=new_ctrl.mappings,
    )

    return CemuProfile(
        emulated_type=new_profile.emulated_type,
        profile_name=new_profile.profile_name,
        controllers=[merged_ctrl],
    )


def _extract_title_id(game_path: Path, cemu_dir: Path) -> str:
    """Best-effort extraction of a Wii U Title ID from the game path or cache."""
    stem = game_path.stem
    tid_match = re.match(r"[0-9a-fA-F]{16}", stem)
    if tid_match:
        return tid_match.group(0)

    for cache_xml in [
        cemu_dir / "portable" / "title_list_cache.xml",
        cemu_dir / "title_list_cache.xml",
    ]:
        if not cache_xml.exists():
            continue
        try:
            cache_tree = ET.parse(str(cache_xml))
            for entry in cache_tree.iter("Entry"):
                path_el = entry.find("path")
                tid_el = entry.find("title_id")
                if path_el is not None and tid_el is not None:
                    cached_path = (path_el.text or "").strip()
                    if cached_path and Path(cached_path) == game_path:
                        return (tid_el.text or "").strip()
        except Exception:
            continue

    return ""
