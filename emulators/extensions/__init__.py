"""Meridian emulator extensions.

Each sub-package (e.g. ``cemu``, ``dolphin``) may expose a standard
``configure_input`` function that Meridian calls at launch time::

    def configure_input(
        player_settings: dict[str, dict],
        exe_path: Path,
        game_path: Path | None = None,
    ) -> None:
        ...

``player_settings`` is the Meridian per-player dict (keys ``"1"``…``"10"``).
``exe_path`` is the resolved path to the emulator executable.
``game_path`` is the ROM/game being launched (may be ``None``).

The dispatch is automatic — see
:func:`meridian.core.emulator_setup._run_extension_input`.
"""
