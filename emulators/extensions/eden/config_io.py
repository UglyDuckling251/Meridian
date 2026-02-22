"""Read/write utilities for Eden's qt-config.ini.

Eden (Yuzu fork) stores controller settings in a Qt-style INI file where
backslash-escaped sub-keys (e.g. ``player_0_button_a\\default=false``) are
common.  Python's :mod:`configparser` cannot round-trip this format faithfully,
so we operate on raw text lines instead.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

_SECTION_RE = re.compile(r"^\[([^\]]+)\]$")


def resolve_config_path(eden_dir: str | Path) -> Path:
    """Return the path to ``qt-config.ini`` for an Eden installation."""
    return Path(eden_dir) / "user" / "config" / "qt-config.ini"


def read_controls(config_path: str | Path) -> dict[str, str]:
    """Return all key=value pairs inside the ``[Controls]`` section.

    Keys are returned verbatim (including backslash sub-keys).
    """
    path = Path(config_path)
    if not path.exists():
        return {}

    in_section = False
    controls: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        m = _SECTION_RE.match(line)
        if m:
            in_section = m.group(1) == "Controls"
            continue
        if not in_section:
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        controls[key] = val

    return controls


def patch_controls(config_path: str | Path, updates: dict[str, str]) -> None:
    """Update ``[Controls]`` keys in *config_path* atomically.

    Only keys present in *updates* are changed; everything else (including
    all other sections) is preserved byte-for-byte.  The file is written
    via temp-file-and-rename so Eden never sees a half-written config.
    """
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        original = path.read_text(encoding="utf-8", errors="replace")
    else:
        original = ""

    remaining = dict(updates)
    out_lines: list[str] = []
    in_controls = False
    controls_found = False
    remaining_inserted = False

    for raw_line in original.splitlines():
        stripped = raw_line.strip()
        m = _SECTION_RE.match(stripped)
        if m:
            if in_controls and not remaining_inserted:
                out_lines.extend(_format_updates(remaining))
                remaining.clear()
                remaining_inserted = True
            in_controls = m.group(1) == "Controls"
            if in_controls:
                controls_found = True
            out_lines.append(raw_line)
            continue

        if in_controls and "=" in stripped:
            key = stripped.partition("=")[0]
            if key in remaining:
                out_lines.append(f"{key}={remaining.pop(key)}")
                continue

        out_lines.append(raw_line)

    if in_controls and not remaining_inserted and remaining:
        out_lines.extend(_format_updates(remaining))
        remaining.clear()

    if not controls_found and remaining:
        out_lines.append("")
        out_lines.append("[Controls]")
        out_lines.extend(_format_updates(remaining))

    text = "\n".join(out_lines)
    if not text.endswith("\n"):
        text += "\n"

    fd, tmp = tempfile.mkstemp(
        suffix=".ini", dir=str(path.parent), prefix=".tmp_eden_"
    )
    try:
        os.close(fd)
        Path(tmp).write_text(text, encoding="utf-8")
        Path(tmp).replace(path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _format_updates(kvs: dict[str, str]) -> list[str]:
    return [f"{k}={v}" for k, v in kvs.items()]
