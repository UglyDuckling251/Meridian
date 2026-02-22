"""Tests for the Eden config I/O utilities."""

from pathlib import Path

import pytest

from emulators.extensions.eden.config_io import (
    patch_controls,
    read_controls,
    resolve_config_path,
)


SAMPLE_CONFIG = """\
[DisabledAddOns]
size=0


[Controls]
enable_raw_input\\default=true
enable_raw_input=false
player_0_connected\\default=true
player_0_connected=true
player_0_button_a\\default=false
player_0_button_a="engine:sdl,guid:abc,port:0,pad:0,button:1"


[UI]
theme=dark
"""


class TestResolveConfigPath:
    def test_basic(self, tmp_path: Path) -> None:
        p = resolve_config_path(tmp_path / "eden")
        assert p == tmp_path / "eden" / "user" / "config" / "qt-config.ini"


class TestReadControls:
    def test_reads_controls_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        controls = read_controls(cfg)
        assert controls["enable_raw_input"] == "false"
        assert controls["player_0_connected"] == "true"
        assert "theme" not in controls

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        controls = read_controls(tmp_path / "missing.ini")
        assert controls == {}

    def test_reads_default_flags(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        controls = read_controls(cfg)
        assert controls["player_0_connected\\default"] == "true"
        assert controls["player_0_button_a\\default"] == "false"


class TestPatchControls:
    def test_updates_existing_key(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        patch_controls(cfg, {"player_0_connected": "false"})

        controls = read_controls(cfg)
        assert controls["player_0_connected"] == "false"

    def test_preserves_other_keys(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        patch_controls(cfg, {"player_0_connected": "false"})

        controls = read_controls(cfg)
        assert controls["enable_raw_input"] == "false"
        text = cfg.read_text(encoding="utf-8")
        assert "theme=dark" in text

    def test_adds_new_key(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        patch_controls(cfg, {"player_1_connected": "true"})

        controls = read_controls(cfg)
        assert controls["player_1_connected"] == "true"

    def test_preserves_other_sections(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        patch_controls(cfg, {"player_0_connected": "false"})

        text = cfg.read_text(encoding="utf-8")
        assert "[DisabledAddOns]" in text
        assert "[UI]" in text
        assert "theme=dark" in text

    def test_creates_controls_section_if_missing(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text("[UI]\ntheme=dark\n", encoding="utf-8")

        patch_controls(cfg, {"player_0_connected": "true"})

        controls = read_controls(cfg)
        assert controls["player_0_connected"] == "true"
        text = cfg.read_text(encoding="utf-8")
        assert "[Controls]" in text
        assert "[UI]" in text

    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config" / "qt-config.ini"

        patch_controls(cfg, {"player_0_connected": "true"})

        assert cfg.exists()
        controls = read_controls(cfg)
        assert controls["player_0_connected"] == "true"

    def test_updates_default_flag(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        patch_controls(cfg, {
            "player_0_connected\\default": "false",
            "player_0_connected": "false",
        })

        controls = read_controls(cfg)
        assert controls["player_0_connected\\default"] == "false"
        assert controls["player_0_connected"] == "false"

    def test_multiple_updates(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")

        patch_controls(cfg, {
            "player_0_connected": "false",
            "player_0_button_a": '"engine:sdl,guid:xyz,port:0,pad:0,button:5"',
            "player_0_button_b\\default": "false",
            "player_0_button_b": '"engine:sdl,guid:xyz,port:0,pad:0,button:4"',
        })

        controls = read_controls(cfg)
        assert controls["player_0_connected"] == "false"
        assert "button:5" in controls["player_0_button_a"]
        assert "button:4" in controls["player_0_button_b"]

    def test_controls_as_last_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text("[Controls]\nfoo=bar\n", encoding="utf-8")

        patch_controls(cfg, {"player_0_connected": "true"})

        controls = read_controls(cfg)
        assert controls["foo"] == "bar"
        assert controls["player_0_connected"] == "true"
