# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Audio device management for Meridian.

Uses ``sounddevice`` (PortAudio) to enumerate input/output devices and
``pygame.mixer`` to control playback volume, channel mode, and muting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_SOUNDS_DIR = Path(__file__).resolve().parents[2] / "assets" / "sounds"


@dataclass
class AudioDeviceInfo:
    """One audio device reported by the system."""
    index: int
    name: str
    is_output: bool
    is_input: bool
    channels: int
    sample_rate: float


class AudioManager:
    """Singleton that enumerates audio hardware and drives pygame.mixer."""

    _instance: AudioManager | None = None

    def __init__(self) -> None:
        self._output_devices: list[AudioDeviceInfo] = []
        self._input_devices: list[AudioDeviceInfo] = []
        self._mixer_ready = False
        self._muted = False
        self._volume = 1.0          # 0.0 – 1.0
        self._mono = False

    @classmethod
    def instance(cls) -> AudioManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- Device enumeration ------------------------------------------------

    def refresh_devices(self) -> None:
        """Query the OS for available audio devices via sounddevice."""
        self._output_devices.clear()
        self._input_devices.clear()

        try:
            import sounddevice as sd
            for dev in sd.query_devices():
                info = AudioDeviceInfo(
                    index=dev["index"],
                    name=dev["name"],
                    is_output=dev["max_output_channels"] > 0,
                    is_input=dev["max_input_channels"] > 0,
                    channels=max(
                        dev["max_output_channels"],
                        dev["max_input_channels"],
                    ),
                    sample_rate=dev["default_samplerate"],
                )
                if info.is_output:
                    self._output_devices.append(info)
                if info.is_input:
                    self._input_devices.append(info)
        except Exception:
            pass

    def output_device_names(self) -> list[str]:
        return [d.name for d in self._output_devices]

    def input_device_names(self) -> list[str]:
        return [d.name for d in self._input_devices]

    # -- Mixer control -----------------------------------------------------

    def init_mixer(
        self,
        volume: int = 100,
        mono: bool = False,
        mute: bool = False,
    ) -> None:
        """Initialise (or re-initialise) pygame.mixer with the given settings."""
        try:
            import pygame
            channels = 1 if mono else 2
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.mixer.init(channels=channels)
            self._mixer_ready = True
            self._mono = mono
            self.set_volume(volume)
            self.set_mute(mute)
        except Exception:
            self._mixer_ready = False

    def set_volume(self, percent: int) -> None:
        """Set master volume (0-100).  Respects mute state."""
        self._volume = max(0, min(100, percent)) / 100.0
        self._apply_volume()

    def set_mute(self, muted: bool) -> None:
        """Toggle global mute without changing the volume slider value."""
        self._muted = muted
        self._apply_volume()

    def set_channel_mode(self, mono: bool) -> None:
        """Switch between mono and stereo (requires mixer re-init)."""
        if mono != self._mono:
            vol = round(self._volume * 100)
            self.init_mixer(volume=vol, mono=mono, mute=self._muted)

    def _apply_volume(self) -> None:
        """Push the effective volume to pygame.mixer."""
        if not self._mixer_ready:
            return
        try:
            import pygame
            effective = 0.0 if self._muted else self._volume
            # pygame.mixer.music is the most common playback channel
            pygame.mixer.music.set_volume(effective)
        except Exception:
            pass

    @property
    def is_muted(self) -> bool:
        return self._muted

    # -- Sound effects -----------------------------------------------------

    def play_sound(self, name: str) -> int:
        """Play a short sound effect from ``assets/sounds/<name>.mp3``.

        The sound respects the current volume and mute state.
        Returns the duration in milliseconds (0 if not played).
        """
        if not self._mixer_ready or self._muted:
            return 0
        path = _SOUNDS_DIR / f"{name}.mp3"
        if not path.exists():
            return 0
        try:
            import pygame
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(self._volume)
            sound.play()
            return int(sound.get_length() * 1000)
        except Exception:
            return 0

    def play_startup(self) -> int:
        """Play the startup chime. Returns duration in milliseconds."""
        return self.play_sound("startup")

    def play_notification(self) -> None:
        """Play the notification / task-complete chime."""
        self.play_sound("notification")

    def apply_config(self, cfg) -> None:
        """Convenience: read all audio fields from a Config and apply them."""
        self.set_volume(cfg.audio_volume)
        self.set_mute(cfg.audio_mute)
        self.set_channel_mode(cfg.audio_channel_mode == "Mono")
