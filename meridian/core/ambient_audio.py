# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Procedural ambient audio engine for Meridian.

Produces a warm, soothing PS5-dashboard-style ambient pad in real time:

  - Multi-harmonic additive synthesis per voice (soft-sawtooth character,
    not pure sines) so the sound is organic rather than "MIDI-like".
  - FFT-based low-pass filter at 550 Hz removes all harshness before output.
  - Synthetic convolution reverb (exponentially-decaying stereo IR) adds
    hall-like depth and natural stereo width without CPU-heavy loops.
  - Very slow amplitude breathing (90 s main LFO) and gentle detune drift
    keep the texture alive without calling attention to itself.
  - No high-frequency shimmer; only warm low/mid-range content.

Two alternating buffers cross-fade on dedicated pygame mixer channels so
the texture evolves without clicks, gaps, or memory buildup.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Audio engine constants
# ---------------------------------------------------------------------------

_SR = 44100                  # sample rate (Hz)
_BUF_S = 18                  # seconds per synthesised chunk
_XFADE_MS = 4000             # cross-fade overlap between chunks (ms)
_BUF_N = _SR * _BUF_S       # samples per chunk

# ---------------------------------------------------------------------------
# Chord voicing  —  Cmaj7 spread over two octaves
# (C2, G2, C3, E3, G3, B3)
# Warm, open, unambiguously pleasant — similar to PS5 menu harmony.
# ---------------------------------------------------------------------------
_CHORD = [
    # (root_hz,  base_amp,  breathe_rate,  breathe_phase)
    (65.41,   0.22,   0.38,   0.00),   # C2
    (98.00,   0.16,   0.45,   1.05),   # G2
    (130.81,  0.18,   0.32,   2.10),   # C3
    (164.81,  0.13,   0.41,   3.15),   # E3
    (196.00,  0.10,   0.35,   4.20),   # G3
    (246.94,  0.08,   0.39,   5.25),   # B3
]

# Harmonic series amplitude weights for a warm, soft pad tone.
# Decays like a muted string / soft sawtooth — much richer than a pure sine.
_HARMONICS = [1.0, 0.52, 0.27, 0.14, 0.07, 0.035]

# ---------------------------------------------------------------------------
# Synthesis parameters
# ---------------------------------------------------------------------------

_LPF_CUTOFF_HZ = 550.0       # aggressive LPF — nothing harsh gets through
_LFO_BREATH_S  = 90.0        # main breathing period (slow, barely noticeable)
_LFO_DETUNE_S  = 70.0        # detune drift period
_DETUNE_DEPTH  = 0.0018      # ±0.18 % pitch drift — imperceptible, just alive
_NOISE_AMP     = 0.006       # very gentle air texture
_NOISE_CUTOFF  = 180.0       # LP cutoff for noise (just lowest air frequencies)
_REVERB_RT60_S = 1.4         # reverb decay time (seconds)
_REVERB_WET    = 0.45        # wet/dry mix for reverb
_OUTPUT_PEAK   = 0.20        # final normalized peak level (quiet and gentle)


# ---------------------------------------------------------------------------
# Pre-computed reverb impulse responses (generated once, reused per instance)
# ---------------------------------------------------------------------------

def _make_reverb_ir(length: int, seed: int) -> np.ndarray:
    """Synthetic stereo reverb IR: exponentially decaying coloured noise."""
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(length)
    # Exponential decay envelope  (–60 dB at RT60)
    decay = np.exp(-6.908 * np.arange(length) / length)
    ir *= decay
    # Gentle LPF on the IR itself so reverb tail is warm, not bright
    cutoff = 3000.0
    freqs = np.fft.rfftfreq(length, 1.0 / _SR)
    H = 1.0 / np.sqrt(1.0 + (freqs / cutoff) ** 4)
    ir_fft = np.fft.rfft(ir) * H
    ir = np.fft.irfft(ir_fft, n=length)
    # Normalise so wet level is predictable
    peak = np.max(np.abs(ir))
    if peak > 0:
        ir /= peak
    return ir.astype(np.float32)


def _fftconv(signal: np.ndarray, ir_fft: np.ndarray, fft_sz: int) -> np.ndarray:
    """FFT-based overlap-add convolution (single channel)."""
    S = np.fft.rfft(signal.astype(np.float64), n=fft_sz)
    out = np.fft.irfft(S * ir_fft, n=fft_sz)
    return out[: len(signal)]


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class AmbientAudioEngine:
    """Endless procedural ambient audio — warm, soothing, PS5-dashboard style."""

    def __init__(self) -> None:
        self._playing = False
        self._volume = 0.3
        self._phase = 0.0         # continuous time (seconds), for phase continuity
        self._drift = 0.0         # slow-evolving modulation offset
        self._ch_a = None
        self._ch_b = None
        self._snd_a = None
        self._snd_b = None
        self._active: str = "a"
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Build reverb infrastructure once per instance
        ir_len = int(_SR * _REVERB_RT60_S)
        ir_l = _make_reverb_ir(ir_len, seed=0)
        ir_r = _make_reverb_ir(ir_len, seed=1)
        self._fft_sz = 1 << int(np.ceil(np.log2(_BUF_N + ir_len - 1)))
        self._ir_fft_l = np.fft.rfft(ir_l.astype(np.float64), n=self._fft_sz)
        self._ir_fft_r = np.fft.rfft(ir_r.astype(np.float64), n=self._fft_sz)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, volume: int = 30) -> None:
        """Begin ambient playback.  *volume* is 0–100."""
        if self._playing:
            return
        self._volume = max(0, min(100, volume)) / 100.0
        self._stop.clear()
        self._playing = True
        try:
            import pygame
            if not pygame.mixer.get_init():
                self._playing = False
                return
            n_ch = max(pygame.mixer.get_num_channels(), 8)
            pygame.mixer.set_num_channels(n_ch)
            self._ch_a = pygame.mixer.Channel(n_ch - 2)
            self._ch_b = pygame.mixer.Channel(n_ch - 1)

            buf = self._render()
            self._snd_a = pygame.mixer.Sound(buffer=buf)
            self._snd_a.set_volume(self._volume)
            self._ch_a.play(self._snd_a, loops=-1, fade_ms=_XFADE_MS)
            self._active = "a"

            self._thread = threading.Thread(target=self._bg_loop, daemon=True)
            self._thread.start()
        except Exception:
            log.exception("Ambient audio start failed")
            self._playing = False

    def stop(self) -> None:
        """Fade out and stop ambient playback."""
        if not self._playing:
            return
        self._stop.set()
        self._playing = False
        try:
            if self._ch_a:
                self._ch_a.fadeout(_XFADE_MS)
            if self._ch_b:
                self._ch_b.fadeout(_XFADE_MS)
        except Exception:
            pass

    def set_volume(self, percent: int) -> None:
        """Adjust ambient volume (0–100) while playing."""
        self._volume = max(0, min(100, percent)) / 100.0
        for s in (self._snd_a, self._snd_b):
            if s:
                try:
                    s.set_volume(self._volume)
                except Exception:
                    pass

    @property
    def is_playing(self) -> bool:
        return self._playing

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _bg_loop(self) -> None:
        import pygame
        while not self._stop.is_set():
            wait = max(2.0, _BUF_S - (_XFADE_MS / 1000.0) - 2.0)
            if self._stop.wait(timeout=wait):
                break
            try:
                buf = self._render()
                snd = pygame.mixer.Sound(buffer=buf)
                snd.set_volume(self._volume)
                with self._lock:
                    if self._active == "a":
                        self._snd_b = snd
                        self._ch_a.fadeout(_XFADE_MS)
                        self._ch_b.play(self._snd_b, loops=-1, fade_ms=_XFADE_MS)
                        self._active = "b"
                    else:
                        self._snd_a = snd
                        self._ch_b.fadeout(_XFADE_MS)
                        self._ch_a.play(self._snd_a, loops=-1, fade_ms=_XFADE_MS)
                        self._active = "a"
            except Exception:
                log.exception("Ambient buffer swap failed")
                break

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def _render(self) -> bytes:
        """
        Generate one buffer of warm ambient PCM audio.

        Pipeline:
          1. Multi-harmonic additive synthesis per chord voice
          2. FFT low-pass filter  (≤ 550 Hz — removes all harshness)
          3. Very quiet filtered-noise air texture
          4. FFT convolution reverb  (stereo-decorrelated, long tail)
          5. Dry/wet mix + final normalisation + boundary fades
        """
        n = _BUF_N
        t = np.linspace(self._phase, self._phase + _BUF_S,
                        n, endpoint=False, dtype=np.float64)
        self._drift += 0.04
        d = self._drift

        # ── 1. Pad: additive harmonic synthesis ──────────────────────────
        # Each chord tone is rendered as a stack of harmonics with
        # exponentially decaying amplitudes (warm soft-sawtooth character).
        # Slow detune drift and amplitude breathing keep it alive without
        # ever calling attention to itself.
        mono_dry = np.zeros(n, dtype=np.float64)

        for freq, base_amp, b_rate, b_phase in _CHORD:
            # Very slow detune drift (barely audible, avoids static quality)
            detune = 1.0 + _DETUNE_DEPTH * np.sin(
                2 * np.pi * t / (_LFO_DETUNE_S * (1.0 + b_rate * 0.4)) + d
            )
            # Slow amplitude breathing — each voice breathes independently
            breath = base_amp * (
                0.65 + 0.35 * np.sin(
                    2 * np.pi * t / _LFO_BREATH_S * b_rate + b_phase + d * 0.5
                )
            )
            # Sum harmonics: fundamental + decaying overtone series
            for h_idx, h_amp in enumerate(_HARMONICS, start=1):
                harmonic_freq = freq * h_idx
                # Skip harmonics that will be entirely cut by the LPF anyway
                if harmonic_freq > _LPF_CUTOFF_HZ * 1.5:
                    break
                mono_dry += breath * h_amp * np.sin(
                    2 * np.pi * harmonic_freq * detune * t
                )

        # ── 2. FFT-based low-pass filter ──────────────────────────────────
        # A 6th-order Butterworth-like response centred at 550 Hz.
        # This is the key step that removes the "computery / MIDI sine" quality:
        # harsh upper harmonics are rolled off, leaving only warmth.
        spectrum = np.fft.rfft(mono_dry)
        freqs = np.fft.rfftfreq(n, 1.0 / _SR)
        H_lp = 1.0 / np.sqrt(1.0 + (freqs / _LPF_CUTOFF_HZ) ** 6)
        mono_dry = np.fft.irfft(spectrum * H_lp, n=n)

        # ── 3. Very quiet air/room noise texture ─────────────────────────
        rng = np.random.default_rng(seed=int(self._phase * 41) & 0x7FFFFFFF)
        noise = rng.standard_normal(n) * _NOISE_AMP
        # LP-filter the noise to only the lowest frequencies (pure air, no hiss)
        noise_spec = np.fft.rfft(noise)
        H_noise = 1.0 / np.sqrt(1.0 + (freqs / _NOISE_CUTOFF) ** 4)
        noise = np.fft.irfft(noise_spec * H_noise, n=n)

        dry_l = mono_dry + noise
        dry_r = mono_dry + noise  # will be decorrelated by the stereo reverb

        # ── 4. Convolution reverb (stereo-decorrelated) ───────────────────
        # Independent L/R impulse responses create natural stereo width
        # and a spacious hall character without any explicit panning code.
        wet_l = _fftconv(dry_l, self._ir_fft_l, self._fft_sz)
        wet_r = _fftconv(dry_r, self._ir_fft_r, self._fft_sz)

        left  = (1.0 - _REVERB_WET) * dry_l + _REVERB_WET * wet_l
        right = (1.0 - _REVERB_WET) * dry_r + _REVERB_WET * wet_r

        # ── 5. Normalise + boundary cosine fades for seamless looping ─────
        peak = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-8)
        left  = left  / peak * _OUTPUT_PEAK
        right = right / peak * _OUTPUT_PEAK

        fade_n = min(8192, n // 4)
        fade_in  = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_n) / fade_n))
        fade_out = fade_in[::-1]
        for ch in (left, right):
            ch[:fade_n]  *= fade_in
            ch[-fade_n:] *= fade_out

        # Convert to interleaved int16 stereo
        l16 = (left  * 32767).astype(np.int16)
        r16 = (right * 32767).astype(np.int16)
        stereo = np.column_stack([l16, r16])

        self._phase += _BUF_S
        return stereo.tobytes()
