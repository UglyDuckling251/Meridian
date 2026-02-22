"""Tests for the Meridian <-> Cemu adapter conversion."""

import pytest

from emulators.extensions.cemu.adapter import (
    cemu_to_meridian_bindings,
    meridian_player_to_cemu,
    meridian_players_to_cemu,
)
from emulators.extensions.cemu.models import (
    AXIS_X_NEG,
    AXIS_X_POS,
    AXIS_Y_NEG,
    AXIS_Y_POS,
    ROTATION_X_NEG,
    ROTATION_X_POS,
    ROTATION_Y_NEG,
    ROTATION_Y_POS,
    TRIGGER_X_NEG,
    TRIGGER_X_POS,
    TRIGGER_Y_NEG,
    TRIGGER_Y_POS,
    CemuProfile,
    ControllerEntry,
    MappingEntry,
)


# ── Sample Meridian player data ──────────────────────────────────────────

CONNECTED_PLAYER = {
    "connected": True,
    "api": "Auto",
    "device": "DualSense Wireless Controller",
    "device_index": 0,
    "device_guid": "030057564c050000e60c000000016800",
    "type": "Wii U GamePad",
    "bindings": {
        "a": "Button 1",
        "b": "Button 0",
        "x": "Button 3",
        "y": "Button 2",
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
        "ls_click": "Button 7",
        "rs_click": "Button 8",
        "motion": "Gyro",
    },
}

DISCONNECTED_PLAYER = {
    "connected": False,
    "api": "Auto",
    "device": "Any Available",
    "device_index": None,
    "type": "Pro Controller",
    "bindings": {},
}

PRO_DUALSENSE_PLAYER = {
    "connected": True,
    "api": "DirectInput",
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
        "home": "Button 15",
        "dp_up": "Button 11",
        "dp_down": "Button 12",
        "dp_left": "Button 13",
        "dp_right": "Button 14",
        "ls_up": "Axis 1-",
        "ls_down": "Axis 1+",
        "ls_left": "Axis 0-",
        "ls_right": "Axis 0+",
        "ls_press": "Button 7",
        "rs_up": "Axis 3-",
        "rs_down": "Axis 3+",
        "rs_left": "Axis 2-",
        "rs_right": "Axis 2+",
        "rs_press": "Button 8",
    },
}


class TestMeridianPlayerToCemu:
    def test_connected_player_produces_profile(self):
        profile = meridian_player_to_cemu(CONNECTED_PLAYER, profile_name="P1")
        assert profile is not None
        assert profile.emulated_type == "Wii U GamePad"
        assert profile.profile_name == "P1"
        assert len(profile.controllers) == 1

        ctrl = profile.controllers[0]
        assert ctrl.api == "DirectInput"
        assert ctrl.uuid  # DI GUID resolved at runtime or fallback to SDL GUID
        assert ctrl.display_name == "DualSense Wireless Controller"
        assert ctrl.motion is True

    def test_disconnected_player_returns_none(self):
        assert meridian_player_to_cemu(DISCONNECTED_PLAYER) is None

    def test_empty_bindings_returns_none(self):
        p = {**CONNECTED_PLAYER, "bindings": {}}
        assert meridian_player_to_cemu(p) is None

    def test_button_bindings_mapped_correctly(self):
        profile = meridian_player_to_cemu(CONNECTED_PLAYER, profile_name="T")
        ctrl = profile.controllers[0]
        by_id = {m.mapping_id: m.button for m in ctrl.mappings}

        assert by_id[1] == 1     # a -> Button 1
        assert by_id[2] == 0     # b -> Button 0
        assert by_id[3] == 3     # x -> Button 3
        assert by_id[4] == 2     # y -> Button 2
        assert by_id[5] == 9     # l -> Button 9
        assert by_id[6] == 10    # r -> Button 10
        assert by_id[11] == 5    # home -> Button 5
        assert by_id[24] == 7    # ls_click -> Button 7
        assert by_id[25] == 8    # rs_click -> Button 8

    def test_axis_bindings_mapped_correctly(self):
        profile = meridian_player_to_cemu(CONNECTED_PLAYER, profile_name="T")
        ctrl = profile.controllers[0]
        by_id = {m.mapping_id: m.button for m in ctrl.mappings}

        assert by_id[7] == TRIGGER_X_NEG    # zl -> Axis 4-
        assert by_id[8] == TRIGGER_Y_NEG    # zr -> Axis 5-
        assert by_id[16] == AXIS_Y_POS      # ls_down -> Axis 1+
        assert by_id[17] == AXIS_Y_NEG      # ls_up -> Axis 1-
        assert by_id[18] == AXIS_X_NEG      # ls_left -> Axis 0-
        assert by_id[19] == AXIS_X_POS      # ls_right -> Axis 0+
        assert by_id[20] == ROTATION_Y_POS  # rs_down -> Axis 3+
        assert by_id[21] == ROTATION_Y_NEG  # rs_up -> Axis 3-
        assert by_id[22] == ROTATION_X_NEG  # rs_left -> Axis 2-
        assert by_id[23] == ROTATION_X_POS  # rs_right -> Axis 2+

    def test_type_mapping(self):
        p = {**CONNECTED_PLAYER, "type": "Pro Controller"}
        profile = meridian_player_to_cemu(p, profile_name="T")
        assert profile.emulated_type == "Wii U Pro Controller"

    def test_api_auto_becomes_directinput(self):
        p = {**CONNECTED_PLAYER, "api": "Auto"}
        profile = meridian_player_to_cemu(p, profile_name="T")
        assert profile.controllers[0].api == "DirectInput"

    def test_pro_dualsense_directinput_normalized_for_cemu(self):
        profile = meridian_player_to_cemu(PRO_DUALSENSE_PLAYER, profile_name="P")
        ctrl = profile.controllers[0]
        by_id = {m.mapping_id: m.button for m in ctrl.mappings}

        # Face/shoulder/menu match the known-good Cemu layout.
        assert by_id[1] == 2
        assert by_id[2] == 1
        assert by_id[3] == 0
        assert by_id[4] == 3
        assert by_id[5] == 4
        assert by_id[6] == 5
        assert by_id[7] == 6
        assert by_id[8] == 7
        assert by_id[9] == 9
        assert by_id[10] == 8

        # Pro-controller stick slots and DirectInput axis remap.
        assert by_id[16] == 10  # ls_click
        assert by_id[17] == 11  # rs_click
        assert by_id[18] == AXIS_Y_POS
        assert by_id[19] == AXIS_Y_NEG
        assert by_id[20] == AXIS_X_NEG
        assert by_id[21] == AXIS_X_POS
        assert by_id[22] == TRIGGER_Y_POS
        assert by_id[23] == TRIGGER_Y_NEG
        assert by_id[24] == TRIGGER_X_NEG
        assert by_id[25] == TRIGGER_X_POS

        # D-Pad is emitted as hat directions.
        assert by_id[12] == 34
        assert by_id[13] == 35
        assert by_id[14] == 36
        assert by_id[15] == 37


class TestMeridianPlayersToCemu:
    def test_multi_player_dict(self):
        players = {
            "1": CONNECTED_PLAYER,
            "2": DISCONNECTED_PLAYER,
            "3": DISCONNECTED_PLAYER,
        }
        results = meridian_players_to_cemu(players)
        assert 1 in results
        assert 2 not in results

    def test_custom_name_prefix(self):
        players = {"1": CONNECTED_PLAYER}
        results = meridian_players_to_cemu(players, name_prefix="cemu_")
        assert results[1].profile_name == "cemu_1"


class TestCemuToMeridianBindings:
    def test_buttons_converted(self):
        profile = CemuProfile(
            controllers=[
                ControllerEntry(
                    mappings=[
                        MappingEntry(1, 0),   # A -> Button 0
                        MappingEntry(2, 1),   # B -> Button 1
                        MappingEntry(12, 11), # dp_up -> Button 11
                    ],
                ),
            ],
        )
        bindings = cemu_to_meridian_bindings(profile)
        assert bindings["a"] == "Button 0"
        assert bindings["b"] == "Button 1"
        assert bindings["dp_up"] == "Button 11"

    def test_axes_converted(self):
        profile = CemuProfile(
            controllers=[
                ControllerEntry(
                    mappings=[
                        MappingEntry(17, AXIS_Y_NEG),       # ls_up
                        MappingEntry(23, ROTATION_X_POS),    # rs_right
                        MappingEntry(7, TRIGGER_X_POS),      # zl
                    ],
                ),
            ],
        )
        bindings = cemu_to_meridian_bindings(profile)
        assert bindings["ls_up"] == "Axis 1-"
        assert bindings["rs_right"] == "Axis 2+"
        assert bindings["zl"] == "Axis 4+"

    def test_motion_flag(self):
        profile = CemuProfile(
            controllers=[ControllerEntry(motion=True, mappings=[MappingEntry(1, 0)])],
        )
        bindings = cemu_to_meridian_bindings(profile)
        assert bindings.get("motion") == "Gyro"

    def test_empty_profile(self):
        profile = CemuProfile()
        assert cemu_to_meridian_bindings(profile) == {}
