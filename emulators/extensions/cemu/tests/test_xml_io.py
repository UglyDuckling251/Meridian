"""Tests for Cemu XML serialization round-trip."""

import textwrap
from pathlib import Path

import pytest

from emulators.extensions.cemu.models import (
    AxisSettings,
    CemuProfile,
    ControllerEntry,
    MappingEntry,
)
from emulators.extensions.cemu.xml_io import parse_xml, to_xml, write_xml


# ── Fixtures ─────────────────────────────────────────────────────────────

def _sample_profile() -> CemuProfile:
    return CemuProfile(
        emulated_type="Wii U GamePad",
        profile_name="TestProfile",
        controllers=[
            ControllerEntry(
                api="SDLController",
                uuid="0",
                display_name="DualSense Wireless Controller",
                rumble=0.5,
                motion=True,
                axis=AxisSettings(0.15, 1.0),
                rotation=AxisSettings(0.2, 1.0),
                trigger=AxisSettings(0.25, 1.0),
                mappings=[
                    MappingEntry(1, 0),
                    MappingEntry(2, 1),
                    MappingEntry(7, 42),
                    MappingEntry(12, 11),
                ],
            ),
        ],
    )


CANONICAL_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <emulated_controller>
      <type>Wii U GamePad</type>
      <profile>RoundTrip</profile>
      <controller>
        <api>SDLController</api>
        <uuid>0</uuid>
        <display_name>Test Pad</display_name>
        <rumble>0</rumble>
        <motion>false</motion>
        <axis>
          <deadzone>0.15</deadzone>
          <range>1</range>
        </axis>
        <rotation>
          <deadzone>0.15</deadzone>
          <range>1</range>
        </rotation>
        <trigger>
          <deadzone>0.25</deadzone>
          <range>1</range>
        </trigger>
        <mappings>
          <entry>
            <mapping>1</mapping>
            <button>0</button>
          </entry>
          <entry>
            <mapping>2</mapping>
            <button>1</button>
          </entry>
        </mappings>
      </controller>
    </emulated_controller>
""")


# ── Tests ────────────────────────────────────────────────────────────────

class TestParseXml:
    def test_canonical_format(self):
        profile = parse_xml(CANONICAL_XML)
        assert profile.emulated_type == "Wii U GamePad"
        assert profile.profile_name == "RoundTrip"
        assert len(profile.controllers) == 1
        ctrl = profile.controllers[0]
        assert ctrl.api == "SDLController"
        assert ctrl.uuid == "0"
        assert ctrl.display_name == "Test Pad"
        assert len(ctrl.mappings) == 2
        assert ctrl.mappings[0].mapping_id == 1
        assert ctrl.mappings[0].button == 0

    def test_old_format_with_nested_mapping(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <emulated_controller>
              <type>Wii U GamePad</type>
              <controller>
                <api>SDLController</api>
                <uuid>0</uuid>
                <display_name>Pad</display_name>
                <rumble>0</rumble>
                <axis><deadzone>0.15</deadzone><range>1</range></axis>
                <rotation><deadzone>0.15</deadzone><range>1</range></rotation>
                <trigger><deadzone>0.5</deadzone><range>1</range></trigger>
                <mappings>
                  <entry>
                    <mapping><device>0</device><button>0</button></mapping>
                    <entry>1</entry>
                  </entry>
                  <entry>
                    <mapping><device>0</device><button>1</button></mapping>
                    <entry>2</entry>
                  </entry>
                </mappings>
              </controller>
            </emulated_controller>
        """)
        profile = parse_xml(xml)
        assert len(profile.controllers) == 1
        mappings = profile.controllers[0].mappings
        assert len(mappings) == 2
        assert mappings[0].mapping_id == 1
        assert mappings[0].button == 0
        assert mappings[1].mapping_id == 2
        assert mappings[1].button == 1

    def test_flat_controller_format(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <emulated_controller>
              <type>Wii U GamePad</type>
              <controller>SDLController</controller>
              <mappings>
                <entry>
                  <mapping>1</mapping>
                  <button>0</button>
                </entry>
              </mappings>
            </emulated_controller>
        """)
        profile = parse_xml(xml)
        assert len(profile.controllers) == 1
        assert profile.controllers[0].api == "SDLController"
        assert profile.controllers[0].mappings[0].button == 0

    def test_axis_tag_variant(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <emulated_controller>
              <type>Wii U GamePad</type>
              <controller>SDLController</controller>
              <mappings>
                <entry>
                  <mapping>7</mapping>
                  <axis>42</axis>
                </entry>
              </mappings>
            </emulated_controller>
        """)
        profile = parse_xml(xml)
        assert profile.controllers[0].mappings[0].button == 42

    def test_bare_axis_settings(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <emulated_controller>
              <type>Wii U GamePad</type>
              <controller>
                <api>SDLController</api>
                <uuid>0</uuid>
                <display_name>Pad</display_name>
                <rumble>0</rumble>
                <axis><deadzone>0.15</deadzone><range>1</range></axis>
                <rotation>0</rotation>
                <trigger>0.25</trigger>
                <mappings/>
              </controller>
            </emulated_controller>
        """)
        profile = parse_xml(xml)
        ctrl = profile.controllers[0]
        assert ctrl.rotation.deadzone == 0.0
        assert ctrl.trigger.deadzone == 0.25

    def test_invalid_root_raises(self):
        with pytest.raises(ValueError, match="Expected <emulated_controller>"):
            parse_xml("<root/>")

    def test_from_file(self, tmp_path):
        p = tmp_path / "test.xml"
        p.write_text(CANONICAL_XML, encoding="utf-8")
        profile = parse_xml(p)
        assert profile.profile_name == "RoundTrip"


class TestToXml:
    def test_round_trip(self):
        original = _sample_profile()
        xml_str = to_xml(original)
        restored = parse_xml(xml_str)

        assert restored.emulated_type == original.emulated_type
        assert restored.profile_name == original.profile_name
        assert len(restored.controllers) == len(original.controllers)

        for orig_c, rest_c in zip(original.controllers, restored.controllers):
            assert rest_c.api == orig_c.api
            assert rest_c.uuid == orig_c.uuid
            assert rest_c.display_name == orig_c.display_name
            assert rest_c.rumble == orig_c.rumble
            assert rest_c.motion == orig_c.motion
            assert rest_c.axis.deadzone == orig_c.axis.deadzone
            assert rest_c.rotation.deadzone == orig_c.rotation.deadzone
            assert rest_c.trigger.deadzone == orig_c.trigger.deadzone
            assert len(rest_c.mappings) == len(orig_c.mappings)
            for om, rm in zip(orig_c.mappings, rest_c.mappings):
                assert rm.mapping_id == om.mapping_id
                assert rm.button == om.button

    def test_write_xml_creates_file(self, tmp_path):
        profile = _sample_profile()
        out = write_xml(profile, tmp_path / "out.xml")
        assert out.exists()
        reloaded = parse_xml(out)
        assert reloaded.profile_name == "TestProfile"

    def test_empty_profile_name_omits_tag(self):
        profile = CemuProfile(profile_name="")
        xml = to_xml(profile)
        assert "<profile>" not in xml

    def test_mappings_sorted_in_output(self):
        profile = CemuProfile(
            controllers=[
                ControllerEntry(
                    mappings=[
                        MappingEntry(10, 5),
                        MappingEntry(1, 0),
                        MappingEntry(5, 3),
                    ],
                ),
            ],
        )
        xml = to_xml(profile)
        mapping_positions = []
        for line in xml.splitlines():
            if "<mapping>" in line:
                val = int(line.strip().replace("<mapping>", "").replace("</mapping>", ""))
                mapping_positions.append(val)
        assert mapping_positions == [1, 5, 10]
