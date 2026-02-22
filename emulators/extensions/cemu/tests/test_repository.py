"""Tests for the Cemu profile file repository."""

import pytest

from emulators.extensions.cemu.models import (
    CemuProfile,
    ControllerEntry,
    MappingEntry,
)
from emulators.extensions.cemu.repository import (
    apply_profile_to_game,
    delete_profile,
    import_profile,
    list_profiles,
    load_profile,
    resolve_profile_dir,
    save_profile,
)
from emulators.extensions.cemu.xml_io import write_xml


def _make_profile(name: str = "Test") -> CemuProfile:
    return CemuProfile(
        emulated_type="Wii U GamePad",
        profile_name=name,
        controllers=[
            ControllerEntry(
                api="SDLController",
                uuid="0",
                display_name="Pad",
                mappings=[MappingEntry(1, 0), MappingEntry(2, 1)],
            ),
        ],
    )


class TestResolveProfileDir:
    def test_portable_preferred(self, tmp_path):
        (tmp_path / "portable").mkdir()
        result = resolve_profile_dir(tmp_path)
        assert "portable" in str(result)
        assert result.exists()

    def test_fallback_without_portable(self, tmp_path):
        result = resolve_profile_dir(tmp_path)
        assert result.name == "controllerProfiles"
        assert result.exists()


class TestSaveLoadList:
    def test_save_and_load(self, tmp_path):
        profile = _make_profile("SaveTest")
        save_profile(profile, tmp_path, "SaveTest")
        loaded = load_profile(tmp_path, "SaveTest")
        assert loaded.profile_name == "SaveTest"
        assert len(loaded.controllers) == 1
        assert len(loaded.controllers[0].mappings) == 2

    def test_save_infers_name_from_profile(self, tmp_path):
        profile = _make_profile("Inferred")
        path = save_profile(profile, tmp_path)
        assert path.stem == "Inferred"

    def test_save_sanitizes_reserved_names(self, tmp_path):
        profile = _make_profile("controller0")
        path = save_profile(profile, tmp_path, "controller0")
        assert "profile_" in path.stem

    def test_list_profiles(self, tmp_path):
        save_profile(_make_profile("Alpha"), tmp_path, "Alpha")
        save_profile(_make_profile("Beta"), tmp_path, "Beta")
        names = list_profiles(tmp_path)
        assert names == ["Alpha", "Beta"]

    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_profile(tmp_path, "NoSuchProfile")

    def test_delete_profile(self, tmp_path):
        save_profile(_make_profile("Doomed"), tmp_path, "Doomed")
        assert delete_profile(tmp_path, "Doomed") is True
        assert delete_profile(tmp_path, "Doomed") is False
        assert "Doomed" not in list_profiles(tmp_path)


class TestImportProfile:
    def test_import_from_file(self, tmp_path):
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        src_file = src_dir / "Imported.xml"
        write_xml(_make_profile("Imported"), src_file)

        dest_dir = tmp_path / "cemu"
        dest_dir.mkdir()
        profile = import_profile(src_file, dest_dir)
        assert profile.profile_name == "Imported"
        assert "Imported" in list_profiles(dest_dir)


class TestApplyProfileToGame:
    def test_writes_controller_assignments(self, tmp_path):
        ini_path = apply_profile_to_game(
            "0005000010143500",
            {1: "Meridian_P1", 2: "Meridian_P2"},
            tmp_path,
        )
        assert ini_path.exists()
        text = ini_path.read_text(encoding="utf-8")
        assert "controller1 = Meridian_P1" in text
        assert "controller2 = Meridian_P2" in text

    def test_preserves_existing_content(self, tmp_path):
        gp_dir = tmp_path / "gameProfiles"
        gp_dir.mkdir(parents=True)
        ini = gp_dir / "ABCDEF1234567890.ini"
        ini.write_text("# Some game\n\n[Graphics]\ngraphics_api = 1\n", encoding="utf-8")

        apply_profile_to_game("ABCDEF1234567890", {1: "P1"}, tmp_path)
        text = ini.read_text(encoding="utf-8")
        assert "controller1 = P1" in text
        assert "[Graphics]" in text
        assert "graphics_api = 1" in text

    def test_replaces_existing_controller_lines(self, tmp_path):
        gp_dir = tmp_path / "gameProfiles"
        gp_dir.mkdir(parents=True)
        ini = gp_dir / "1234567890123456.ini"
        ini.write_text("controller1 = OldProfile\n", encoding="utf-8")

        apply_profile_to_game("1234567890123456", {1: "NewProfile"}, tmp_path)
        text = ini.read_text(encoding="utf-8")
        assert "OldProfile" not in text
        assert "controller1 = NewProfile" in text

    def test_removes_disconnected_controller_assignments(self, tmp_path):
        gp_dir = tmp_path / "gameProfiles"
        gp_dir.mkdir(parents=True)
        ini = gp_dir / "ABCDEFABCDEFABCD.ini"
        ini.write_text(
            "controller1 = OldP1\n"
            "controller2 = OldP2\n"
            "other = keepme\n",
            encoding="utf-8",
        )

        apply_profile_to_game("ABCDEFABCDEFABCD", {1: "NewP1"}, tmp_path)
        text = ini.read_text(encoding="utf-8")
        assert "controller1 = NewP1" in text
        assert "controller2 =" not in text
        assert "other = keepme" in text
