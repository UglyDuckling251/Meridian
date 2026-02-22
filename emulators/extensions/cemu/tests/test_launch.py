"""Tests for the launch-time configure_input hook."""

import tempfile
from pathlib import Path

import pytest

from emulators.extensions.cemu._launch import configure_input, _extract_title_id
from emulators.extensions.cemu.repository import resolve_profile_dir
from emulators.extensions.cemu.xml_io import parse_xml


def _make_player_settings() -> dict[str, dict]:
    return {
        "1": {
            "connected": True,
            "api": "SDLController",
            "device": "Xbox Controller",
            "device_index": 0,
            "type": "Wii U GamePad",
            "bindings": {
                "a": "Button 0",
                "b": "Button 1",
                "x": "Button 2",
                "y": "Button 3",
                "dp_up": "Hat 0 Up",
                "dp_down": "Hat 0 Down",
                "ls_up": "Axis 1-",
                "ls_down": "Axis 1+",
            },
        },
        "2": {"connected": False, "bindings": {}},
    }


class TestConfigureInput:
    def test_creates_profile_xml(self, tmp_path: Path) -> None:
        cemu_dir = tmp_path / "cemu"
        exe = cemu_dir / "Cemu.exe"
        cemu_dir.mkdir()
        exe.touch()

        configure_input(
            player_settings=_make_player_settings(),
            exe_path=exe,
        )

        profile_dir = resolve_profile_dir(cemu_dir)
        xmls = sorted(profile_dir.glob("*.xml"))
        names = {x.stem for x in xmls}
        assert "meridian_player1" in names, f"Expected named profile, got {names}"
        assert "controller0" in names, f"Expected slot file, got {names}"

        profile = parse_xml(profile_dir / "meridian_player1.xml")
        assert profile.emulated_type == "Wii U GamePad"
        assert len(profile.controllers) == 1
        assert len(profile.controllers[0].mappings) == 8

        slot = parse_xml(profile_dir / "controller0.xml")
        assert slot.profile_name == "meridian_player1"
        assert len(slot.controllers) == 1

    def test_applies_to_game_profile(self, tmp_path: Path) -> None:
        cemu_dir = tmp_path / "cemu"
        exe = cemu_dir / "Cemu.exe"
        cemu_dir.mkdir()
        exe.touch()
        game = tmp_path / "0005000010101234.rpx"
        game.touch()

        configure_input(
            player_settings=_make_player_settings(),
            exe_path=exe,
            game_path=game,
        )

        gp_dir = cemu_dir / "gameProfiles"
        inis = list(gp_dir.glob("*.ini"))
        assert len(inis) == 1
        content = inis[0].read_text()
        assert "meridian_player1" in content

    def test_no_connected_players_is_noop(self, tmp_path: Path) -> None:
        cemu_dir = tmp_path / "cemu"
        exe = cemu_dir / "Cemu.exe"
        cemu_dir.mkdir()
        exe.touch()

        configure_input(
            player_settings={"1": {"connected": False, "bindings": {}}},
            exe_path=exe,
        )

        profile_dir = cemu_dir / "controllerProfiles"
        assert not profile_dir.exists() or not list(profile_dir.glob("*.xml"))

    def test_disconnect_removes_previous_active_slot(self, tmp_path: Path) -> None:
        cemu_dir = tmp_path / "cemu"
        exe = cemu_dir / "Cemu.exe"
        cemu_dir.mkdir()
        exe.touch()

        # First launch: players 1 and 2 connected.
        psettings = _make_player_settings()
        psettings["2"] = {
            "connected": True,
            "api": "SDLController",
            "device": "Pad2",
            "device_index": 1,
            "type": "Wii U GamePad",
            "bindings": {
                "a": "Button 0",
            },
        }
        configure_input(player_settings=psettings, exe_path=exe)
        profile_dir = resolve_profile_dir(cemu_dir)
        assert (profile_dir / "controller1.xml").exists()
        assert (profile_dir / "meridian_player2.xml").exists()

        # Second launch: player 2 disconnected -> slot 1 should be removed.
        psettings["2"] = {"connected": False, "bindings": {}}
        configure_input(player_settings=psettings, exe_path=exe)
        assert not (profile_dir / "controller1.xml").exists()
        assert not (profile_dir / "meridian_player2.xml").exists()


class TestExtractTitleId:
    def test_from_filename(self, tmp_path: Path) -> None:
        game = tmp_path / "0005000010101234.rpx"
        tid = _extract_title_id(game, tmp_path)
        assert tid == "0005000010101234"

    def test_from_cache_xml(self, tmp_path: Path) -> None:
        cache = tmp_path / "title_list_cache.xml"
        game_path = tmp_path / "games" / "mario.rpx"
        cache.write_text(
            '<?xml version="1.0"?>\n'
            "<TitleList>\n"
            "  <Entry>\n"
            f"    <path>{game_path}</path>\n"
            "    <title_id>00050000AABBCCDD</title_id>\n"
            "  </Entry>\n"
            "</TitleList>\n",
            encoding="utf-8",
        )
        tid = _extract_title_id(game_path, tmp_path)
        assert tid == "00050000AABBCCDD"

    def test_returns_empty_when_unknown(self, tmp_path: Path) -> None:
        game = tmp_path / "some_game.rpx"
        tid = _extract_title_id(game, tmp_path)
        assert tid == ""
