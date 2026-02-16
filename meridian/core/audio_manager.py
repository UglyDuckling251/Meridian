"""
Audio device management for Meridian.

Uses ``sounddevice`` (PortAudio) to enumerate input/output devices and
``pygame.mixer`` to control playback volume, channel mode, and muting.
"""

from __future__ import annotations

from dataclasses import dataclass


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

    def apply_config(self, cfg) -> None:
        """Convenience: read all audio fields from a Config and apply them."""
        self.set_volume(cfg.audio_volume)
        self.set_mute(cfg.audio_mute)
        self.set_channel_mode(cfg.audio_channel_mode == "Mono")
