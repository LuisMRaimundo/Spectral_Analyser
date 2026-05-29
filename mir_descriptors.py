"""
Music Information Retrieval (MIR) descriptors computed from a peak-picked
spectrum: spectral moments, tristimulus, spectral flatness and rolloff,
Aures-style roughness, ERB-weighted spectral density.

References
----------
- Pollard, H. F., & Jansson, E. V. (1982). A tristimulus method for the
  specification of musical timbre. Acustica, 51(3), 162–171.
- Moore, B. C. J., & Glasberg, B. R. (1983). Suggested formulae for
  calculating auditory-filter bandwidths and excitation patterns.
  Journal of the Acoustical Society of America, 74(3), 750–753.
- Aures, W. (1985). Ein Berechnungsverfahren der Rauhigkeit. Acustica,
  58(5), 268–281.
- Peeters, G., Giordano, B. L., Susini, P., Misdariis, N., & McAdams, S.
  (2011). The Timbre Toolbox: Extracting audio descriptors from musical
  signals. Journal of the Acoustical Society of America, 130(5), 2902–2916.

See REFERENCES.md at the repository root for canonical APA-7 entries.
"""

from __future__ import annotations

from typing import Dict

import numpy as np


def _safe_prob(weights: np.ndarray) -> np.ndarray:
    w = np.asarray(weights, dtype=float)
    w = np.maximum(w, 0.0)
    s = float(np.sum(w))
    if not np.isfinite(s) or s <= 0.0:
        return np.zeros_like(w, dtype=float)
    return w / s


def _erb_rate_hz(freq_hz: np.ndarray) -> np.ndarray:
    f = np.maximum(np.asarray(freq_hz, dtype=float), 0.0)
    # Moore & Glasberg ERB-rate approximation.
    return 21.4 * np.log10(1.0 + 0.00437 * f)


def _roughness_aures_1985(
    freq_hz: np.ndarray,
    amp: np.ndarray,
    *,
    x_cutoff: float = 20.0,
) -> float:
    """Aures-style spectral roughness.

    The pairwise dissonance kernel ``x * exp(1 - x)`` (with
    ``x = |f_i - f_j| / (0.25 * min(f_i, f_j) + 24.7)``) decays to a
    negligible value for ``x`` beyond a few units (e.g. ``x = 20`` →
    ``20 * exp(-19) ≈ 1.1e-7``). Pairs whose frequency separation exceeds
    ``x_cutoff`` critical-band-widths therefore contribute nothing
    measurable to the sum.

    This implementation sorts the spectrum by frequency and, for each
    component ``i``, vectorises the inner sum over only the neighbouring
    components ``j > i`` whose separation stays under the cutoff. That
    replaces the previous Python ``O(n^2)`` double loop (which, on a full
    ~16k-bin spectrum, executed hundreds of millions of scalar
    ``min``/``max``/``abs`` calls and dominated per-note runtime) with a
    handful of numpy operations per component, while preserving the
    numerical result to ~1e-7.
    """
    f = np.asarray(freq_hz, dtype=float).ravel()
    a = np.maximum(np.asarray(amp, dtype=float), 0.0).ravel()
    if f.size < 2 or a.size != f.size:
        return 0.0

    valid = np.isfinite(f) & (f > 0.0) & np.isfinite(a)
    f = f[valid]
    a = a[valid]
    if f.size < 2:
        return 0.0

    order = np.argsort(f, kind="mergesort")
    f = f[order]
    a = a[order]

    denom = np.maximum(0.25 * f + 24.7, 1e-9)
    # For component i (the lower frequency in each pair, since f is sorted
    # ascending), contributions vanish once f_j - f_i > x_cutoff * denom_i.
    df_max = float(x_cutoff) * denom
    upper_freq = f + df_max
    # First index strictly greater than i whose frequency is still within
    # the cutoff window. searchsorted on the ascending frequency axis.
    j_end = np.searchsorted(f, upper_freq, side="right")

    n = f.size
    total = 0.0
    for i in range(n - 1):
        k = int(j_end[i])
        if k <= i + 1:
            continue
        fj = f[i + 1 : k]
        aj = a[i + 1 : k]
        x = (fj - f[i]) / denom[i]
        total += float(a[i] * np.sum(aj * (x * np.exp(1.0 - x))))
    return float(max(total, 0.0))


def compute_mir_descriptors_from_spectrum(
    *,
    frequencies_hz: np.ndarray,
    amplitudes: np.ndarray,
    f0_hz: float | None = None,
) -> Dict[str, float]:
    freq = np.asarray(frequencies_hz, dtype=float).ravel()
    amp = np.asarray(amplitudes, dtype=float).ravel()
    ok = np.isfinite(freq) & np.isfinite(amp) & (freq > 0.0) & (amp > 0.0)
    freq = freq[ok]
    amp = amp[ok]
    if freq.size == 0:
        return {
            "spectral_centroid_hz": float("nan"),
            "spectral_spread_hz": float("nan"),
            "spectral_skewness": float("nan"),
            "spectral_kurtosis": float("nan"),
            "spectral_irregularity": float("nan"),
            "tristimulus_1_fundamental": float("nan"),
            "tristimulus_2_low_harmonics_2_to_4": float("nan"),
            "tristimulus_3_high_harmonics_5_plus": float("nan"),
            "spectral_flatness": float("nan"),
            "spectral_rolloff_hz_85": float("nan"),
            "spectral_rolloff_hz_95": float("nan"),
            "roughness_aures_1985": float("nan"),
            "erb_weighted_spectral_density": float("nan"),
        }

    power = amp * amp
    p = _safe_prob(power)
    centroid = float(np.sum(freq * p))
    spread = float(np.sqrt(max(0.0, np.sum(((freq - centroid) ** 2) * p)))
                   )
    if spread > 0.0:
        skew = float(np.sum((((freq - centroid) / spread) ** 3) * p))
        kurt = float(np.sum((((freq - centroid) / spread) ** 4) * p))
    else:
        skew = 0.0
        kurt = 0.0

    irregularity = 0.0
    if amp.size >= 2:
        irregularity = float(np.sum(np.abs(np.diff(amp))) / max(float(np.sum(amp)), 1e-12))
        irregularity = float(np.clip(irregularity, 0.0, 1.0))

    f0 = float(f0_hz) if f0_hz is not None and np.isfinite(f0_hz) and f0_hz > 0.0 else float("nan")
    t1 = t2 = t3 = float("nan")
    if np.isfinite(f0):
        n = np.rint(freq / f0).astype(int)
        valid = n >= 1
        if np.any(valid):
            n = n[valid]
            a = amp[valid]
            tot = float(np.sum(a))
            if tot > 0.0:
                t1 = float(np.sum(a[n == 1]) / tot)
                t2 = float(np.sum(a[(n >= 2) & (n <= 4)]) / tot)
                t3 = float(np.sum(a[n >= 5]) / tot)

    gmean = float(np.exp(np.mean(np.log(np.maximum(power, 1e-12)))))
    amean = float(np.mean(power))
    flatness = float(np.clip(gmean / max(amean, 1e-12), 0.0, 1.0))

    order = np.argsort(freq)
    f_sorted = freq[order]
    p_sorted = power[order]
    cumsum = np.cumsum(p_sorted)
    total = float(cumsum[-1]) if cumsum.size else 0.0
    if total > 0.0:
        r85 = float(f_sorted[np.searchsorted(cumsum, 0.85 * total, side="left")])
        r95 = float(f_sorted[np.searchsorted(cumsum, 0.95 * total, side="left")])
    else:
        r85 = float("nan")
        r95 = float("nan")

    rough_aures = _roughness_aures_1985(freq, amp)

    erb = _erb_rate_hz(freq)
    erb_bins = np.floor(erb).astype(int)
    if erb_bins.size > 0:
        unique = np.unique(erb_bins)
        erb_mass = np.array([np.sum(power[erb_bins == b]) for b in unique], dtype=float)
        q = _safe_prob(erb_mass)
        erb_weighted_density = float(1.0 / max(float(np.sum(q * q)), 1e-12))
    else:
        erb_weighted_density = float("nan")

    return {
        "spectral_centroid_hz": centroid,
        "spectral_spread_hz": spread,
        "spectral_skewness": skew,
        "spectral_kurtosis": kurt,
        "spectral_irregularity": irregularity,
        "tristimulus_1_fundamental": t1,
        "tristimulus_2_low_harmonics_2_to_4": t2,
        "tristimulus_3_high_harmonics_5_plus": t3,
        "spectral_flatness": flatness,
        "spectral_rolloff_hz_85": r85,
        "spectral_rolloff_hz_95": r95,
        "roughness_aures_1985": rough_aures,
        "erb_weighted_spectral_density": erb_weighted_density,
    }
