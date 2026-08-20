"""Resolution-invariant spectral energy (PSD integrated over Hz).

Periodogram bin power ``P_k = |A_k|²`` is not comparable across ``n_fft``:
halving the window doubles ``Δf`` and changes the residual-to-harmonic
basis. This module converts those bins to power spectral density and
integrates over Hertz (Heinzel et al., 2002; Harris, 1978).

    E = Σ P_k × Δf_k     (broadband / residual)
    E_peak = P_peak × ENBW_hz   (main-lobe equivalent)

``energy_basis = psd_per_hz``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from constants import (
    ENERGY_BASIS_PSD_PER_HZ,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
    RESIDUAL_EXCLUSION_FOOTPRINT,
)

ENERGY_BASIS = ENERGY_BASIS_PSD_PER_HZ


def bin_width_hz(sr_hz: float, n_fft: int) -> float:
    sr = float(sr_hz)
    n = int(n_fft)
    if not math.isfinite(sr) or sr <= 0.0 or n <= 0:
        return float("nan")
    return sr / float(n)


def _window_samples(window: str, n_fft: int) -> np.ndarray:
    name = str(window or "hann").strip().lower() or "hann"
    n = max(int(n_fft), 8)
    try:
        from scipy.signal import get_window

        return np.asarray(get_window(name, n, fftbins=True), dtype=float)
    except Exception:
        if name in {"hann", "hanning"}:
            return np.hanning(n)
        if name == "hamming":
            return np.hamming(n)
        if name == "blackman":
            return np.blackman(n)
        return np.ones(n, dtype=float)


def window_enbw_bins(window: str = "hann", n_fft: int = 4096) -> float:
    """Equivalent noise bandwidth in bins: N Σw² / (Σw)² (Heinzel 2002)."""
    w = _window_samples(window, n_fft)
    s = float(np.sum(w))
    if s == 0.0:
        return 1.0
    return float(w.size * np.sum(w * w) / (s * s))


def window_enbw_hz(
    window: str,
    sr_hz: float,
    n_fft: int,
) -> float:
    df = bin_width_hz(sr_hz, n_fft)
    if not math.isfinite(df):
        return float("nan")
    return float(window_enbw_bins(window, n_fft) * df)


def peak_footprint_bins(window: str = "hann", n_fft: int = 4096) -> float:
    """ENBW in bins — used only for the peak-power estimate."""
    return float(window_enbw_bins(window, n_fft))


def peak_power_footprint_bins(window: str = "hann", n_fft: int = 4096) -> float:
    """Alias of ``peak_footprint_bins`` (ENBW). Residual exclusion is separate."""
    return peak_footprint_bins(window, n_fft)


def residual_exclusion_footprint_bins(window: str = "hann") -> float:
    """Main-lobe diameter in bins used to keep skirts out of the residual.

    Blackman–Harris 4-term first nulls sit at ±4 bins
    (``RESIDUAL_EXCLUSION_FOOTPRINT`` = 8). Other named windows use their
    first-null diameter. This is *not* ENBW.
    """
    name = str(window or "hann").strip().lower().replace("-", "").replace("_", "")
    if "blackmanharris" in name:
        return float(RESIDUAL_EXCLUSION_FOOTPRINT)
    if name in {"hann", "hanning", "hamming"}:
        return 4.0
    if name == "blackman":
        return 6.0
    return float(RESIDUAL_EXCLUSION_FOOTPRINT)


def residual_exclusion_hz(
    window: str,
    sr_hz: float,
    n_fft: int,
) -> float:
    df = bin_width_hz(sr_hz, n_fft)
    if not math.isfinite(df) or df <= 0.0:
        return float("nan")
    return float(residual_exclusion_footprint_bins(window) * df)


def window_sums(window: str, n_fft: int) -> Tuple[float, float]:
    w = _window_samples(window, n_fft)
    return float(np.sum(w)), float(np.sum(w * w))


def periodogram_to_psd(
    power_bins: Sequence[float],
    *,
    sr_hz: float,
    n_fft: int,
    window: str,
) -> np.ndarray:
    """Heinzel: S(f) = |X|² / (f_s Σ w²)."""
    arr = np.asarray(power_bins, dtype=float)
    _s1, s2 = window_sums(window, n_fft)
    denom = float(sr_hz) * float(s2)
    if not math.isfinite(denom) or denom <= 0.0:
        return np.zeros_like(arr, dtype=float)
    return arr / denom


def integrate_psd(
    power_bins: Sequence[float],
    df_hz: float,
    *,
    sr_hz: float = 0.0,
    n_fft: int = 0,
    window: str = "",
) -> float:
    """Integrate periodogram bins as PSD over Hz.

    When ``sr_hz``, ``n_fft`` and ``window`` are given, ``power_bins`` are
    treated as raw |X|² and converted with Heinzel's S(f) before
    ``Σ S Δf``. Otherwise the legacy ``Σ P × Δf`` path is kept for
    already-normalised densities.
    """
    arr = np.asarray(power_bins, dtype=float)
    arr = arr[np.isfinite(arr) & (arr > 0.0)]
    if arr.size == 0:
        return 0.0
    if sr_hz and n_fft and window:
        psd = periodogram_to_psd(arr, sr_hz=sr_hz, n_fft=int(n_fft), window=window)
        try:
            df = float(df_hz)
        except (TypeError, ValueError):
            df = bin_width_hz(sr_hz, n_fft)
        if not math.isfinite(df) or df <= 0.0:
            return 0.0
        return float(np.sum(psd) * df)
    try:
        df = float(df_hz)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(df) or df <= 0.0:
        return 0.0
    return float(np.sum(arr) * df)


def peak_psd_energy(
    peak_power: float,
    enbw_hz: float,
    *,
    window: str = "",
    n_fft: int = 0,
) -> float:
    """Main-lobe energy of one peak.

    With a named window this is ``|X_peak|² / (Σ w)²`` (coherent-gain
    normalised). The ``enbw_hz`` argument is kept for callers that already
    converted the bin to PSD.
    """
    try:
        p = float(peak_power)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(p) or p <= 0.0:
        return 0.0
    if window and int(n_fft) > 0:
        s1, _s2 = window_sums(window, int(n_fft))
        if s1 > 0.0:
            return float(p / (s1 * s1))
    try:
        bw = float(enbw_hz)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(bw) or bw <= 0.0:
        return 0.0
    return float(p * bw)


def _union_length_hz(intervals: Sequence[Tuple[float, float]]) -> float:
    cleaned: List[Tuple[float, float]] = []
    for lo, hi in intervals:
        try:
            a = float(lo)
            b = float(hi)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(a) and math.isfinite(b)) or b <= a:
            continue
        cleaned.append((a, b))
    if not cleaned:
        return 0.0
    cleaned.sort()
    total = 0.0
    cur_lo, cur_hi = cleaned[0]
    for lo, hi in cleaned[1:]:
        if lo <= cur_hi:
            cur_hi = max(cur_hi, hi)
            continue
        total += cur_hi - cur_lo
        cur_lo, cur_hi = lo, hi
    total += cur_hi - cur_lo
    return float(total)


def analysis_band_regions_hz(
    freq_min_hz: float,
    freq_max_hz: float,
    peak_freqs_hz: Sequence[float],
    exclusion_hz: float,
) -> Tuple[float, float, float]:
    """Return ``(residual, excluded, analysis_band)`` on the one-sided axis.

    Invariant (fail closed): ``residual + excluded == analysis_band``.
    Overlapping exclusion footprints are merged.
    """
    try:
        f_min = float(freq_min_hz)
        f_max = float(freq_max_hz)
        excl = float(exclusion_hz)
    except (TypeError, ValueError):
        return 0.0, 0.0, 0.0
    if not (math.isfinite(f_min) and math.isfinite(f_max)) or f_max <= f_min:
        return 0.0, 0.0, 0.0
    band = float(f_max - f_min)
    if not math.isfinite(excl) or excl <= 0.0:
        return band, 0.0, band
    half = 0.5 * excl
    intervals: List[Tuple[float, float]] = []
    for raw in peak_freqs_hz:
        try:
            f0 = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(f0) or f0 <= 0.0:
            continue
        lo = max(f_min, f0 - half)
        hi = min(f_max, f0 + half)
        if hi > lo:
            intervals.append((lo, hi))
    excluded = _union_length_hz(intervals)
    if excluded > band:
        excluded = band
    residual = band - excluded
    if residual < 0.0:
        residual = 0.0
        excluded = band
    return float(residual), float(excluded), float(band)


def residual_region_hz_total(
    freq_hz: Sequence[float],
    residual_mask: Sequence[bool],
    df_hz: float,
    *,
    freq_min_hz: Optional[float] = None,
    freq_max_hz: Optional[float] = None,
    peak_freqs_hz: Optional[Sequence[float]] = None,
    exclusion_hz: Optional[float] = None,
) -> float:
    """One-sided residual width after exclusion-footprint union."""
    if (
        freq_min_hz is not None
        and freq_max_hz is not None
        and peak_freqs_hz is not None
        and exclusion_hz is not None
    ):
        residual, _excluded, _band = analysis_band_regions_hz(
            float(freq_min_hz),
            float(freq_max_hz),
            peak_freqs_hz,
            float(exclusion_hz),
        )
        return float(residual)
    try:
        df = float(df_hz)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(df) or df <= 0.0:
        return 0.0
    mask = np.asarray(residual_mask, dtype=bool)
    return float(int(np.count_nonzero(mask)) * df)


def exclude_peak_footprints(
    freq_hz: Sequence[float],
    peak_freqs_hz: Sequence[float],
    footprint_hz: float,
) -> np.ndarray:
    """True where ``freq_hz`` is outside every peak's ±½ footprint."""
    freq = np.asarray(freq_hz, dtype=float)
    keep = np.ones(freq.shape, dtype=bool)
    try:
        half = 0.5 * float(footprint_hz)
    except (TypeError, ValueError):
        return keep
    if not math.isfinite(half) or half <= 0.0:
        return keep
    for raw in peak_freqs_hz:
        try:
            f0 = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(f0) or f0 <= 0.0:
            continue
        keep &= np.abs(freq - f0) > half
    return keep


def energy_provenance(
    *,
    sr_hz: float,
    n_fft: int,
    window: str = "hann",
    hop_length: int = FIXED_HOP_LENGTH_DEFAULT,
) -> Dict[str, Any]:
    df = bin_width_hz(sr_hz, n_fft)
    enbw = window_enbw_hz(window, sr_hz, n_fft)
    foot = peak_power_footprint_bins(window, n_fft)
    excl = residual_exclusion_footprint_bins(window)
    return {
        "energy_basis": ENERGY_BASIS,
        "window_enbw_hz": enbw if math.isfinite(enbw) else float("nan"),
        "peak_footprint_bins": foot,
        "peak_power_footprint_bins": foot,
        "residual_exclusion_footprint_bins": excl,
        "bin_width_hz": df if math.isfinite(df) else float("nan"),
        "n_fft": int(n_fft) if int(n_fft) > 0 else None,
        "hop_length": int(hop_length) if int(hop_length) > 0 else None,
        "window_type": str(window or "hann"),
    }


def is_rfft_grid(
    freq_hz: Sequence[float],
    sr_hz: float,
    n_fft: int,
) -> bool:
    """True when ``freq_hz`` is a dense FFT axis (possibly band-limited)."""
    freq = np.asarray(freq_hz, dtype=float)
    freq = freq[np.isfinite(freq) & (freq >= 0.0)]
    n = int(n_fft)
    sr = float(sr_hz)
    if freq.size < 8 or n < 8 or not math.isfinite(sr) or sr <= 0.0:
        return False
    df = bin_width_hz(sr, n)
    if not math.isfinite(df) or df <= 0.0:
        return False
    step = float(np.median(np.diff(np.sort(freq))))
    if not math.isfinite(step) or step <= 0.0:
        return False
    return abs(step - df) <= 0.35 * df


def hop_for_policy(
    *,
    fft_policy: str,
    n_fft: int,
    fixed_hop_length: int = FIXED_HOP_LENGTH_DEFAULT,
) -> int:
    policy = str(fft_policy or "fixed").strip().lower()
    if policy == "fixed":
        return int(fixed_hop_length or FIXED_HOP_LENGTH_DEFAULT)
    n = int(n_fft) if int(n_fft) > 0 else int(FIXED_N_FFT_DEFAULT)
    return max(1, n // 8)
