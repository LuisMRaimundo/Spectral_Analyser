# -*- coding: utf-8 -*-
"""
Spectral leakage (window sidelobe) guards for harmonic vs inharmonic classification.

Used to widen exclusion zones around detected harmonic frequencies so that STFT
energy spread from finite windows is not mis-labelled as inharmonic partials.

See ``identify_inharmonic_partials`` in ``density.py`` and peak-based batch energy
in ``audio_analysis/super_audio_analyzer.py``.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np

# Generic STFT main-lobe width order (bins); overridden when callers pass measured width.
DEFAULT_MAIN_LOBE_WIDTH_BINS = 4.0


def leakage_halfwidth_hz(
    *,
    sr: Optional[float] = None,
    n_fft: Optional[int] = None,
    bin_width_hz: Optional[float] = None,
    main_lobe_bins: Optional[float] = None,
) -> float:
    """
    Half-width in Hz for a symmetric guard around each harmonic frequency.

    Uses ``0.5 * main_lobe_bins * bin_width`` so that total diameter in bins
    matches ``main_lobe_bins`` when ``bin_width`` is STFT bin spacing.

    Provide either ``bin_width_hz`` **or** both ``sr`` and ``n_fft`` (effective
    padded FFT size). Returns ``0.0`` if geometry cannot be resolved.
    """
    ml = (
        float(main_lobe_bins)
        if main_lobe_bins is not None and float(main_lobe_bins) > 0.0
        else DEFAULT_MAIN_LOBE_WIDTH_BINS
    )
    if bin_width_hz is not None and float(bin_width_hz) > 0.0:
        bw = float(bin_width_hz)
    elif sr is not None and n_fft is not None and float(sr) > 0.0 and int(n_fft) > 0:
        bw = float(sr) / float(int(n_fft))
    else:
        return 0.0
    return 0.5 * ml * bw


def filter_inharmonic_peak_candidates(
    inharmonic_candidates: Sequence[Tuple[float, float]],
    harmonic_rep_frequencies_hz: Sequence[float],
    *,
    leakage_halfwidth_hz: float,
) -> List[Tuple[float, float]]:
    """
    Drop peak candidates that lie within ``leakage_halfwidth_hz`` of any
    harmonic representative frequency (measured peak locations), treating them
    as window leakage rather than inharmonic partials.
    """
    if leakage_halfwidth_hz <= 0.0 or not inharmonic_candidates:
        return list(inharmonic_candidates)
    if not harmonic_rep_frequencies_hz:
        return list(inharmonic_candidates)
    hf = np.asarray(list(harmonic_rep_frequencies_hz), dtype=float)
    hf = hf[np.isfinite(hf)]
    if hf.size == 0:
        return list(inharmonic_candidates)
    lh = float(leakage_halfwidth_hz)
    out: List[Tuple[float, float]] = []
    for f, a in inharmonic_candidates:
        ff = float(f)
        if not np.isfinite(ff):
            continue
        if np.any(np.abs(hf - ff) <= lh):
            continue
        out.append((ff, float(a)))
    return out
