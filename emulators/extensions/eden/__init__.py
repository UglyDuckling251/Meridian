"""Eden controller-profile extension for Meridian.

Converts Meridian player settings to Eden's qt-config.ini control entries
at launch time.  All operations are pure Python with no external dependencies.
"""

from ._launch import configure_input
from .adapter import meridian_player_to_eden, meridian_players_to_eden
from .config_io import patch_controls, read_controls, resolve_config_path

__all__ = [
    "configure_input",
    "meridian_player_to_eden",
    "meridian_players_to_eden",
    "patch_controls",
    "read_controls",
    "resolve_config_path",
]
