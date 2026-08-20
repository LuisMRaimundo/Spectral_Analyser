"""Planted harmonic / stiff-string / bell constructs plus a noise floor.

SNR is the per-partial peak-to-floor ratio (dB). That keeps N, B, EPD, and
confirmed-I recoverable at 10 dB: the weakest intended partial is still the
stated margin above the floor, rather than vanishing under an H1-only SNR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Literal, Optional, Sequence

import numpy as np

from inharmonic_confirmation import f007_frequency_hz
from validated_partials import participation_ratio_from_amplitudes

CONSTRUCT_SNR_LEVELS_DB: tuple[int, ...] = (10, 20, 30, 40)
Family = Literal["harmonic", "stiff", "bell"]
FloorKind = Literal["white", "pink"]


@dataclass(frozen=True)
class PlantedPartial:
    frequency_hz: float
    amplitude: float
    family: Literal["H", "I"]
    order: Optional[int] = None


@dataclass(frozen=True)
class ConstructSpec:
    name: str
    family: Family
    f0_hz: float
    snr_db: float
    floor_kind: FloorKind = "white"
    n_harmonic: int = 0
    b_true: float = 0.0
    confirmed_i_true: int = 0
    roll_off: float = 0.75
    planted: tuple[PlantedPartial, ...] = field(default_factory=tuple)
    sr: float = 44100.0
    n_fft: int = 8192

    @property
    def true_epd(self) -> float:
        amps = [p.amplitude for p in self.planted]
        return participation_ratio_from_amplitudes(amps)


def _harmonic_amps(n: int, roll_off: float) -> List[float]:
    return [float(roll_off ** (k - 1)) for k in range(1, n + 1)]


def _build_planted(
    *,
    family: Family,
    f0_hz: float,
    n_harmonic: int,
    b_true: float,
    roll_off: float,
    bell_count: int = 10,
) -> tuple[tuple[PlantedPartial, ...], int]:
    planted: List[PlantedPartial] = []
    for n, amp in enumerate(_harmonic_amps(n_harmonic, roll_off), start=1):
        freq = f007_frequency_hz(n, f0_hz, b_true)
        planted.append(PlantedPartial(freq, amp, "H", n))
    confirmed_i = 0
    if family == "bell":
        # Mid-gap inharmonic set: (n + 0.5)·f0, outside the F-007 comb.
        for k in range(bell_count):
            freq = float((k + 1) * f0_hz + 0.5 * f0_hz)
            planted.append(
                PlantedPartial(freq, float(roll_off ** k) * 0.85, "I", None)
            )
        confirmed_i = bell_count
    return tuple(planted), confirmed_i


def make_construct(
    family: Family,
    snr_db: float,
    *,
    floor_kind: FloorKind = "white",
) -> ConstructSpec:
    if family == "harmonic":
        f0, n_h, b, roll = 220.0, 8, 0.0, 0.75
    elif family == "stiff":
        f0, n_h, b, roll = 110.0, 12, 2.0e-4, 0.80
    elif family == "bell":
        f0, n_h, b, roll = 220.0, 3, 0.0, 0.85
    else:
        raise ValueError(f"unknown family: {family}")
    planted, confirmed_i = _build_planted(
        family=family,
        f0_hz=f0,
        n_harmonic=n_h,
        b_true=b,
        roll_off=roll,
    )
    return ConstructSpec(
        name=f"{family}_snr{int(snr_db)}_{floor_kind}",
        family=family,
        f0_hz=f0,
        snr_db=float(snr_db),
        floor_kind=floor_kind,
        n_harmonic=n_h,
        b_true=b,
        confirmed_i_true=confirmed_i,
        roll_off=roll,
        planted=planted,
    )


def iter_constructs(
    snr_levels: Sequence[float] = CONSTRUCT_SNR_LEVELS_DB,
    families: Sequence[Family] = ("harmonic", "stiff", "bell"),
    floor_kind: FloorKind = "white",
) -> Iterable[ConstructSpec]:
    for family in families:
        for snr in snr_levels:
            yield make_construct(family, float(snr), floor_kind=floor_kind)


def plant_spectrum(
    spec: ConstructSpec,
    *,
    floor: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(freqs, magnitudes)`` with planted peaks at ``spec.snr_db``."""
    freqs = np.fft.rfftfreq(int(spec.n_fft), 1.0 / float(spec.sr))
    if spec.floor_kind == "pink":
        mags = np.maximum(floor / np.sqrt(np.maximum(freqs, 1.0)), 1e-6)
    else:
        mags = np.full(freqs.shape, float(floor), dtype=float)
    gain = 10.0 ** (float(spec.snr_db) / 20.0)
    # Weak floor ripples (0.3 dB) must not confirm as partials.
    for freq in (3017.0, 5023.0, 7039.0, 9041.0, 11047.0, 13057.0):
        if any(abs(freq - p.frequency_hz) < 40.0 for p in spec.planted):
            continue
        idx = int(np.argmin(np.abs(freqs - freq)))
        idx = max(2, min(int(mags.size) - 3, idx))
        peak = float(mags[idx]) * (10.0 ** (0.3 / 20.0))
        mags[idx] = peak
        mags[idx - 1] = 0.45 * peak
        mags[idx + 1] = 0.45 * peak
    min_amp = min((p.amplitude for p in spec.planted), default=1.0)
    for partial in spec.planted:
        idx = int(np.argmin(np.abs(freqs - float(partial.frequency_hz))))
        idx = max(2, min(int(mags.size) - 3, idx))
        peak = float(mags[idx]) * gain * (float(partial.amplitude) / float(min_amp))
        mags[idx] = peak
        mags[idx - 1] = 0.45 * peak
        mags[idx + 1] = 0.45 * peak
    return freqs, mags


def synthesize_waveform(
    spec: ConstructSpec,
    *,
    duration_s: float = 0.75,
    seed: int = 0,
) -> np.ndarray:
    """Unit-scale time-domain construct plus a floor at the stated SNR."""
    n = int(round(float(spec.sr) * float(duration_s)))
    t = np.arange(n, dtype=float) / float(spec.sr)
    y = np.zeros(n, dtype=float)
    for partial in spec.planted:
        y += float(partial.amplitude) * np.sin(
            2.0 * np.pi * float(partial.frequency_hz) * t
        )
    signal_rms = float(np.sqrt(np.mean(y * y))) if n else 0.0
    rng = np.random.default_rng(int(seed))
    if spec.floor_kind == "pink":
        spectrum = rng.normal(0.0, 1.0, n)
        spec_f = np.fft.rfft(spectrum)
        freqs = np.fft.rfftfreq(n, 1.0 / float(spec.sr))
        spec_f /= np.sqrt(np.maximum(freqs, 1.0))
        noise = np.fft.irfft(spec_f, n=n)
    else:
        noise = rng.normal(0.0, 1.0, n)
    noise_rms = float(np.sqrt(np.mean(noise * noise))) or 1.0
    target = signal_rms / (10.0 ** (float(spec.snr_db) / 20.0)) if signal_rms else 0.0
    y = y + noise * (target / noise_rms)
    peak = float(np.max(np.abs(y))) or 1.0
    return (y / peak).astype(np.float64)
