"""File-system repository for Cemu controller profiles and game profiles.

All public functions accept a *cemu_dir* argument — the root of a Cemu
installation (the directory containing ``Cemu.exe``).  Profile resolution
follows Cemu's own logic:

1. ``<cemu_dir>/portable/controllerProfiles/`` (portable mode — preferred)
2. ``<cemu_dir>/controllerProfiles/``          (fallback)
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from .models import CemuProfile
from .xml_io import parse_xml, write_xml


# ── Helpers ──────────────────────────────────────────────────────────────

_RESERVED_NAMES = {f"controller{i}" for i in range(10)}
_FILENAME_RE = re.compile(r'^[A-Za-z0-9_ .()-]+$')


def _is_valid_profile_name(name: str) -> bool:
    if not name or not _FILENAME_RE.match(name):
        return False
    return name.lower() not in _RESERVED_NAMES


def _sanitize_profile_name(name: str) -> str:
    """Return a safe filename stem from *name*, raising on empty input."""
    cleaned = re.sub(r'[^\w .()-]', '_', name).strip()
    if not cleaned:
        raise ValueError("Profile name is empty after sanitization")
    if cleaned.lower() in _RESERVED_NAMES:
        cleaned = f"profile_{cleaned}"
    return cleaned


def resolve_profile_dir(cemu_dir: str | Path) -> Path:
    """Return the active ``controllerProfiles`` directory for *cemu_dir*.

    Creates the directory if it doesn't exist.
    """
    base = Path(cemu_dir)
    portable = base / "portable" / "controllerProfiles"
    if portable.exists() or (base / "portable").exists():
        portable.mkdir(parents=True, exist_ok=True)
        return portable
    fallback = base / "controllerProfiles"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def resolve_game_profile_dir(cemu_dir: str | Path) -> Path:
    """Return the ``gameProfiles`` directory, creating it if needed."""
    d = Path(cemu_dir) / "gameProfiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Profile CRUD ─────────────────────────────────────────────────────────

def list_profiles(cemu_dir: str | Path) -> list[str]:
    """Return sorted profile names found in *cemu_dir*."""
    profiles_dir = resolve_profile_dir(cemu_dir)
    names: list[str] = []
    for p in profiles_dir.glob("*.xml"):
        stem = p.stem
        if _is_valid_profile_name(stem):
            names.append(stem)
    return sorted(names)


def load_profile(cemu_dir: str | Path, name: str) -> CemuProfile:
    """Load a named profile from *cemu_dir*.

    Raises :class:`FileNotFoundError` if the profile doesn't exist.
    """
    profiles_dir = resolve_profile_dir(cemu_dir)
    xml_path = profiles_dir / f"{name}.xml"
    if not xml_path.exists():
        raise FileNotFoundError(f"Profile {name!r} not found at {xml_path}")
    return parse_xml(xml_path)


def save_profile(
    profile: CemuProfile,
    cemu_dir: str | Path,
    name: str | None = None,
) -> Path:
    """Save *profile* into *cemu_dir*.

    If *name* is ``None``, ``profile.profile_name`` is used.  The profile is
    written atomically (temp file + rename) so Cemu never sees a partial file.

    Returns the path written.
    """
    resolved_name = _sanitize_profile_name(name or profile.profile_name)
    if not profile.profile_name:
        profile = CemuProfile(
            emulated_type=profile.emulated_type,
            profile_name=resolved_name,
            controllers=list(profile.controllers),
        )

    profiles_dir = resolve_profile_dir(cemu_dir)
    dest = profiles_dir / f"{resolved_name}.xml"

    fd, tmp_path = tempfile.mkstemp(
        suffix=".xml", dir=str(profiles_dir), prefix=".tmp_"
    )
    try:
        os.close(fd)
        write_xml(profile, tmp_path)
        tmp = Path(tmp_path)
        tmp.replace(dest)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return dest


def delete_profile(cemu_dir: str | Path, name: str) -> bool:
    """Delete a profile by name.  Returns ``True`` if it existed."""
    profiles_dir = resolve_profile_dir(cemu_dir)
    xml_path = profiles_dir / f"{name}.xml"
    if xml_path.exists():
        xml_path.unlink()
        return True
    return False


def import_profile(
    source: str | Path,
    cemu_dir: str | Path,
    name: str | None = None,
) -> CemuProfile:
    """Import an XML file from *source* into *cemu_dir*.

    If *name* is ``None``, the stem of the source file is used.
    Returns the parsed :class:`CemuProfile`.
    """
    src = Path(source)
    profile = parse_xml(src)
    resolved_name = name or src.stem
    save_profile(profile, cemu_dir, resolved_name)
    return profile


# ── Controller slot files ─────────────────────────────────────────────────

def activate_profile(
    profile: CemuProfile,
    slot: int,
    cemu_dir: str | Path,
) -> Path:
    """Write *profile* as the active controller for *slot* (0-based).

    Cemu loads ``controller0.xml`` through ``controller7.xml`` at startup.
    This writes the full profile content to ``controller<slot>.xml`` so
    Cemu picks it up as the active controller.

    Returns the path to the written slot file.
    """
    if not 0 <= slot <= 7:
        raise ValueError(f"slot must be 0-7, got {slot}")

    profiles_dir = resolve_profile_dir(cemu_dir)
    dest = profiles_dir / f"controller{slot}.xml"

    fd, tmp_path = tempfile.mkstemp(
        suffix=".xml", dir=str(profiles_dir), prefix=".tmp_"
    )
    try:
        os.close(fd)
        write_xml(profile, tmp_path)
        tmp = Path(tmp_path)
        tmp.replace(dest)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return dest


def deactivate_slot(slot: int, cemu_dir: str | Path) -> bool:
    """Remove the active controller file for *slot* (0-based).

    Returns ``True`` if a slot file existed and was removed.
    """
    if not 0 <= slot <= 7:
        raise ValueError(f"slot must be 0-7, got {slot}")
    profiles_dir = resolve_profile_dir(cemu_dir)
    slot_path = profiles_dir / f"controller{slot}.xml"
    if slot_path.exists():
        slot_path.unlink()
        return True
    return False


# ── Game-profile controller assignment ───────────────────────────────────

def apply_profile_to_game(
    title_id: str,
    player_profiles: dict[int, str],
    cemu_dir: str | Path,
) -> Path:
    """Write or patch a game profile to assign controller profiles.

    *player_profiles* maps 1-based player indices to profile names, e.g.
    ``{1: "Meridian_P1", 2: "Meridian_P2"}``.

    Returns the path to the written game-profile ``.ini``.
    """
    clean_tid = title_id.replace("-", "").strip()
    gp_dir = resolve_game_profile_dir(cemu_dir)
    ini_path = gp_dir / f"{clean_tid}.ini"

    existing_lines: list[str] = []
    if ini_path.exists():
        existing_lines = ini_path.read_text(encoding="utf-8").splitlines()

    # Always clear existing controller assignments first so disconnected
    # players are removed from game profiles on next launch.
    controller_key_re = re.compile(r"^controller[1-9]\d*$", re.IGNORECASE)
    kept: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped:
            key = stripped.split("=", 1)[0].strip().lower()
            if controller_key_re.match(key):
                continue
        kept.append(line)

    insert: list[str] = []
    for player_idx in sorted(player_profiles):
        pname = player_profiles[player_idx]
        insert.append(f"controller{player_idx} = {pname}")

    final_lines = insert + kept
    ini_path.write_text("\n".join(final_lines) + "\n", encoding="utf-8")
    return ini_path
