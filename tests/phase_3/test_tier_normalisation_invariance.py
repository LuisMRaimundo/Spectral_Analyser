from __future__ import annotations

import numpy as np
import pytest

from spectral_normalization import n_fft_normalization_factor


def _synthetic_sustained_sinusoid(sr: int, seconds: float, freq_hz: float) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=float) / float(sr)
    return np.sin(2.0 * np.pi * float(freq_hz) * t)


def _one_frame_spectrum_amplitude_mass(signal: np.ndarray, n_fft: int) -> float:
    frame = signal[:n_fft]
    if frame.size < n_fft:
        padded = np.zeros(n_fft, dtype=float)
        padded[: frame.size] = frame
        frame = padded
    spectrum = np.fft.rfft(frame)
    magnitude = np.abs(spectrum)
    # Rooted L1 amplitude mass scales approximately with sqrt(n_fft),
    # matching the "amplitude" normalization law used for cross-tier correction.
    return float(np.sqrt(np.sum(magnitude)))


def test_tier_normalized_amplitude_sum_is_fft_invariant_within_2_percent() -> None:
    sr = 48000
    # Choose a tone exactly on FFT bins for both 4096 and 8192.
    signal = _synthetic_sustained_sinusoid(sr=sr, seconds=2.0, freq_hz=468.75)

    raw_4096 = _one_frame_spectrum_amplitude_mass(signal, n_fft=4096)
    raw_8192 = _one_frame_spectrum_amplitude_mass(signal, n_fft=8192)

    norm_4096 = raw_4096 * n_fft_normalization_factor(
        n_fft=4096, n_fft_reference=8192, kind="amplitude"
    )
    norm_8192 = raw_8192 * n_fft_normalization_factor(
        n_fft=8192, n_fft_reference=8192, kind="amplitude"
    )

    assert norm_4096 == pytest.approx(norm_8192, rel=0.02, abs=0.0)
