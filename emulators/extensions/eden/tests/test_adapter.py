"""Tests for the Meridian <-> Eden adapter conversion."""

import pytest

from emulators.extensions.eden.adapter import (
    meridian_player_to_eden,
    meridian_players_to_eden,
    _binding_to_eden_value,
    _stick_axes_from_bindings,
)


CONNECTED_PLAYER: dict = {
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
        "capture": "Button 15",
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
}

DISCONNECTED_PLAYER: dict = {
    "connected": False,
    "bindings": {},
}


class TestBindingToEdenValue:
    def test_button(self) -> None:
        val = _binding_to_eden_value("Button 1", "abc", 0, 0)
        assert val == '"engine:sdl,guid:abc,port:0,pad:0,button:1"'

    def test_axis_positive(self) -> None:
        val = _binding_to_eden_value("Axis 0+", "abc", 0, 0)
        assert val is not None
        assert "axis:0" in val
        assert "direction:+" in val

    def test_axis_negative(self) -> None:
        val = _binding_to_eden_value("Axis 4-", "abc", 1, 1)
        assert val is not None
        assert "axis:4" in val
        assert "direction:-" in val
        assert "port:1" in val

    def test_hat(self) -> None:
        val = _binding_to_eden_value("Hat 0 Up", "abc", 0, 0)
        assert val == '"engine:sdl,guid:abc,port:0,pad:0,button:11"'

    def test_hat_down(self) -> None:
        val = _binding_to_eden_value("Hat 0 Down", "abc", 0, 0)
        assert val == '"engine:sdl,guid:abc,port:0,pad:0,button:12"'

    def test_gyro_returns_none(self) -> None:
        assert _binding_to_eden_value("Gyro", "abc", 0, 0) is None

    def test_empty_returns_none(self) -> None:
        assert _binding_to_eden_value("", "abc", 0, 0) is None

    def test_none_string_returns_none(self) -> None:
        assert _binding_to_eden_value("None", "abc", 0, 0) is None


class TestStickAxes:
    def test_extracts_axes(self) -> None:
        bindings = {"ls_up": "Axis 1-", "ls_left": "Axis 0-"}
        axes = _stick_axes_from_bindings(bindings, "ls_up", "ls_left")
        assert axes == (0, 1)

    def test_returns_none_when_missing(self) -> None:
        assert _stick_axes_from_bindings({}, "ls_up", "ls_left") is None

    def test_partial_returns_none(self) -> None:
        bindings = {"ls_up": "Axis 1-"}
        assert _stick_axes_from_bindings(bindings, "ls_up", "ls_left") is None


class TestMeridianPlayerToEden:
    def test_connected_player_produces_entries(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert result["player_0_connected"] == "true"
        assert result["player_0_type"] == "0"

    def test_button_bindings(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert "button:1" in result["player_0_button_a"]
        assert "button:0" in result["player_0_button_b"]
        assert "button:2" in result["player_0_button_x"]

    def test_trigger_bindings(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert "axis:4" in result["player_0_button_zl"]
        assert "direction:-" in result["player_0_button_zl"]

    def test_dpad_bindings(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert "button:11" in result["player_0_button_dup"]
        assert "button:14" in result["player_0_button_dright"]

    def test_stick_entries(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert "axis_x:0" in result["player_0_lstick"]
        assert "axis_y:1" in result["player_0_lstick"]
        assert "axis_x:2" in result["player_0_rstick"]
        assert "axis_y:3" in result["player_0_rstick"]

    def test_motion_entries(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert "motion:0" in result["player_0_motionleft"]
        assert "motion:1" in result["player_0_motionright"]

    def test_default_flags(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert result["player_0_button_a\\default"] == "false"
        assert result["player_0_connected\\default"] == "false"
        assert result["player_0_lstick\\default"] == "false"

    def test_guid_and_port(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert "guid:030057564c050000e60c000000016800" in result["player_0_button_a"]
        assert "port:0" in result["player_0_button_a"]

    def test_disconnected_returns_none(self) -> None:
        assert meridian_player_to_eden(DISCONNECTED_PLAYER, eden_index=0) is None

    def test_no_bindings_returns_none(self) -> None:
        p = {"connected": True, "bindings": {}}
        assert meridian_player_to_eden(p, eden_index=0) is None

    def test_player_index_offset(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=1)
        assert result is not None
        assert "player_1_button_a" in result
        assert "port:0" in result["player_1_button_a"]

    def test_hat_bindings_for_dpad(self) -> None:
        player = {
            "connected": True,
            "api": "SDL",
            "device": "Xbox Controller",
            "device_index": 0,
            "device_guid": "abc",
            "type": "Pro Controller",
            "bindings": {
                "a": "Button 0",
                "dp_up": "Hat 0 Up",
                "dp_down": "Hat 0 Down",
                "dp_left": "Hat 0 Left",
                "dp_right": "Hat 0 Right",
                "ls_up": "Axis 1-",
                "ls_left": "Axis 0-",
                "rs_up": "Axis 3-",
                "rs_left": "Axis 2-",
            },
        }
        result = meridian_player_to_eden(player, eden_index=0)
        assert result is not None
        assert "button:11" in result["player_0_button_dup"]
        assert "button:12" in result["player_0_button_ddown"]
        assert "button:13" in result["player_0_button_dleft"]
        assert "button:14" in result["player_0_button_dright"]

    def test_no_motion_omits_motion_keys(self) -> None:
        player = dict(CONNECTED_PLAYER)
        player["bindings"] = {
            k: v for k, v in CONNECTED_PLAYER["bindings"].items()
            if k != "motion"
        }
        result = meridian_player_to_eden(player, eden_index=0)
        assert result is not None
        assert "player_0_motionleft" not in result

    def test_stick_click_bindings(self) -> None:
        result = meridian_player_to_eden(CONNECTED_PLAYER, eden_index=0)
        assert result is not None
        assert "button:7" in result["player_0_button_lstick"]
        assert "button:8" in result["player_0_button_rstick"]

    def test_fallback_guid(self) -> None:
        player = dict(CONNECTED_PLAYER)
        player["device_guid"] = ""
        result = meridian_player_to_eden(player, eden_index=0)
        assert result is not None
        assert "guid:0" in result["player_0_button_a"]


class TestMeridianPlayersToEden:
    def test_converts_connected_players(self) -> None:
        players = {
            "1": CONNECTED_PLAYER,
            "2": DISCONNECTED_PLAYER,
        }
        results = meridian_players_to_eden(players)
        assert 0 in results
        assert 1 not in results

    def test_index_mapping(self) -> None:
        players = {"1": CONNECTED_PLAYER, "3": CONNECTED_PLAYER}
        results = meridian_players_to_eden(players)
        assert 0 in results
        assert 2 in results
        assert "player_0_button_a" in results[0]
        assert "player_2_button_a" in results[2]

    def test_out_of_range_skipped(self) -> None:
        players = {"0": CONNECTED_PLAYER, "11": CONNECTED_PLAYER}
        results = meridian_players_to_eden(players)
        assert len(results) == 0

    def test_non_dict_data_skipped(self) -> None:
        players = {"1": "not a dict"}
        results = meridian_players_to_eden(players)
        assert len(results) == 0
