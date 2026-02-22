"""Tests for the launch-time configure_input hook."""

import tempfile
from pathlib import Path

import pytest

from emulators.extensions.eden._launch import configure_input
from emulators.extensions.eden.config_io import read_controls, resolve_config_path


def _make_player_settings() -> dict[str, dict]:
    return {
        "1": {
            "connected": True,
            "api": "SDL",
            "device": "DualSense Wireless Controller",
            "device_index": 0,
            "device_guid": "030057564c050000e60c000000016800",
            "type": "Pro Controller",
            "bindings": {
                "a": "Button 1",
                "b": "Button 0",
                "x": "Button 2",
                "y": "Button 3",
                "l": "Button 9",
                "r": "Button 10",
                "zl": "Axis 4-",
                "zr": "Axis 5-",
                "plus": "Button 6",
                "minus": "Button 4",
                "home": "Button 5",
                "dp_up": "Button 11",
                "dp_down": "Button 12",
                "dp_left": "Button 13",
                "dp_right": "Button 14",
                "ls_up": "Axis 1-",
                "ls_down": "Axis 1+",
                "ls_left": "Axis 0-",
                "ls_right": "Axis 0+",
                "rs_up": "Axis 3-",
                "rs_down": "Axis 3+",
                "rs_left": "Axis 2-",
                "rs_right": "Axis 2+",
                "ls_press": "Button 7",
                "rs_press": "Button 8",
                "motion": "Gyro",
            },
        },
        "2": {"connected": False, "bindings": {}},
    }


def _setup_eden(tmp_path: Path) -> Path:
    eden_dir = tmp_path / "eden"
    eden_dir.mkdir()
    exe = eden_dir / "eden.exe"
    exe.touch()
    config_dir = eden_dir / "user" / "config"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "qt-config.ini"
    config_file.write_text(
        "[Controls]\n"
        "enable_raw_input\\default=true\n"
        "enable_raw_input=false\n"
        "player_0_connected\\default=true\n"
        "player_0_connected=false\n",
        encoding="utf-8",
    )
    return exe


class TestConfigureInput:
    def test_writes_player_controls(self, tmp_path: Path) -> None:
        exe = _setup_eden(tmp_path)

        configure_input(
            player_settings=_make_player_settings(),
            exe_path=exe,
        )

        config_path = resolve_config_path(exe.parent)
        controls = read_controls(config_path)
        assert controls["player_0_connected"] == "true"
        assert "button:1" in controls.get("player_0_button_a", "")
        assert "axis_x:0" in controls.get("player_0_lstick", "")
        assert "motion:0" in controls.get("player_0_motionleft", "")

    def test_disconnected_player_marked_false(self, tmp_path: Path) -> None:
        exe = _setup_eden(tmp_path)

        configure_input(
            player_settings=_make_player_settings(),
            exe_path=exe,
        )

        config_path = resolve_config_path(exe.parent)
        controls = read_controls(config_path)
        assert controls["player_1_connected"] == "false"

    def test_preserves_non_player_settings(self, tmp_path: Path) -> None:
        exe = _setup_eden(tmp_path)

        configure_input(
            player_settings=_make_player_settings(),
            exe_path=exe,
        )

        config_path = resolve_config_path(exe.parent)
        controls = read_controls(config_path)
        assert controls["enable_raw_input"] == "false"

    def test_no_connected_players_is_noop(self, tmp_path: Path) -> None:
        exe = _setup_eden(tmp_path)

        configure_input(
            player_settings={"1": {"connected": False, "bindings": {}}},
            exe_path=exe,
        )

        config_path = resolve_config_path(exe.parent)
        controls = read_controls(config_path)
        assert controls["player_0_connected"] == "false"

    def test_two_connected_players(self, tmp_path: Path) -> None:
        exe = _setup_eden(tmp_path)
        psettings = _make_player_settings()
        psettings["2"] = {
            "connected": True,
            "api": "SDL",
            "device": "DualSense #2",
            "device_index": 1,
            "device_guid": "030057564c050000e60c000000016800",
            "type": "Pro Controller",
            "bindings": {
                "a": "Button 1",
                "b": "Button 0",
                "ls_up": "Axis 1-",
                "ls_left": "Axis 0-",
                "rs_up": "Axis 3-",
                "rs_left": "Axis 2-",
            },
        }

        configure_input(player_settings=psettings, exe_path=exe)

        config_path = resolve_config_path(exe.parent)
        controls = read_controls(config_path)
        assert controls["player_0_connected"] == "true"
        assert controls["player_1_connected"] == "true"
        assert "port:1" in controls.get("player_1_button_a", "")

    def test_creates_config_if_missing(self, tmp_path: Path) -> None:
        eden_dir = tmp_path / "eden"
        eden_dir.mkdir()
        exe = eden_dir / "eden.exe"
        exe.touch()

        configure_input(
            player_settings=_make_player_settings(),
            exe_path=exe,
        )

        config_path = resolve_config_path(eden_dir)
        assert config_path.exists()
        controls = read_controls(config_path)
        assert controls["player_0_connected"] == "true"

    def test_guid_in_output(self, tmp_path: Path) -> None:
        exe = _setup_eden(tmp_path)

        configure_input(
            player_settings=_make_player_settings(),
            exe_path=exe,
        )

        config_path = resolve_config_path(exe.parent)
        controls = read_controls(config_path)
        assert "guid:030057564c050000e60c000000016800" in controls.get(
            "player_0_button_a", ""
        )
