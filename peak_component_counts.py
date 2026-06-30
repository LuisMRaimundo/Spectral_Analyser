# -*- coding: utf-8 -*-
"""
Peak-based harmonic / inharmonic / subbass classification for detected spectral rows.

Adapted from Spectral_Analyser-main_7 ``audio_analysis/super_audio_analyzer`` (one
strongest local assignment per harmonic order, cents tolerance). Intended for
**peak lists** (e.g. ``filtered_list_df``), not raw FFT bin grids.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from constants import HARMONIC_MAX_CHECK


def _linear_amp_from_row(row: pd.Series, df: pd.DataFrame) -> float:
    if "Amplitude" in df.columns:
        v = row.get("Amplitude")
        if v is not None and pd.notna(v):
            return float(max(0.0, float(v)))
    if "Magnitude (dB)" in df.columns:
        v = row.get("Magnitude (dB)")
        if v is not None and pd.notna(v):
            return float(10.0 ** (float(v) / 20.0))
    return 0.0


def _peak_tuples(peaks_df: pd.DataFrame) -> List[Tuple[float, float]]:
    out: List[Tuple[float, float]] = []
    if peaks_df is None or peaks_df.empty or "Frequency (Hz)" not in peaks_df.columns:
        return out
    for _, row in peaks_df.iterrows():
        f = float(pd.to_numeric(row.get("Frequency (Hz)"), errors="coerce"))
        if not math.isfinite(f) or f <= 0.0:
            continue
        a = _linear_amp_from_row(row, peaks_df)
        if not math.isfinite(a) or a <= 0.0:
            continue
        out.append((f, a))
    return out


def classify_peaks_harmonic_inharmonic_subbass_from_df(
    peaks_df: Optional[pd.DataFrame],
    f0_hz: float,
    *,
    subbass_cutoff_hz: float = 200.0,
    tolerance_cents: float = 18.0,
    max_freq_hz: float = 20000.0,
) -> Dict[str, Any]:
    """
    Classify detected peaks into harmonic (one per n·f₀ slot, strongest wins),
    inharmonic (musical band), and sub-bass (f < ``subbass_cutoff_hz``).

    Returns slot-based **candidate** counts on the **peak list** (harmonic one row per n·f₀ slot;
    other rows classified inharmonic/subbass). These are **not** residual-row pipeline counts;
    use ``peaklist_*`` keys. Legacy integer mirrors are ``legacy_*_deprecated``.
    """
    empty: Dict[str, Any] = {
        "peaklist_harmonic_window_candidate_count": 0,
        "peaklist_nonharmonic_window_candidate_count": 0,
        "peaklist_low_frequency_window_candidate_count": 0,
        "peaklist_total_window_candidate_count": 0,
        "legacy_harmonic_peak_count_deprecated": 0,
        "legacy_inharmonic_peak_count_deprecated": 0,
        "legacy_subbass_peak_count_deprecated": 0,
        "f0_hz_used": float("nan"),
        "classification_valid": False,
        "classification_semantics": (
            "independent_peaklist_window_assignment; not part of residual-row hierarchy"
        ),
    }
    f0 = float(f0_hz)
    if not math.isfinite(f0) or f0 <= 0.0:
        return dict(empty)

    peaks = _peak_tuples(peaks_df if peaks_df is not None else pd.DataFrame())
    if not peaks:
        out = dict(empty)
        out["f0_hz_used"] = f0
        return out

    max_f = float(max_freq_hz) if math.isfinite(max_freq_hz) and max_freq_hz > 0 else 20000.0
    n_max_theory = int(math.floor(max_f / f0))
    n_slots = max(0, min(int(HARMONIC_MAX_CHECK), n_max_theory))
    if n_slots <= 0:
        out = dict(empty)
        out["f0_hz_used"] = f0
        return out

    expected = [f0 * float(n) for n in range(1, n_slots + 1)]

    harmonic_peaks_dict: Dict[int, Tuple[float, float]] = {}
    inharmonic_peaks: List[Tuple[float, float]] = []
    subbass_peaks: List[Tuple[float, float]] = []

    for freq, amp in peaks:
        if freq < float(subbass_cutoff_hz):
            subbass_peaks.append((freq, amp))
            continue

        best_n: Optional[int] = None
        best_err = float("inf")
        is_harmonic = False

        for n, expected_freq in enumerate(expected, 1):
            tol_hz = expected_freq * (2.0 ** (float(tolerance_cents) / 1200.0) - 1.0)
            err = abs(freq - expected_freq)
            if err <= tol_hz and err < best_err:
                best_err = err
                best_n = n
                is_harmonic = True

        if is_harmonic and best_n is not None:
            if best_n not in harmonic_peaks_dict:
                harmonic_peaks_dict[best_n] = (freq, amp)
            else:
                _f0, a0 = harmonic_peaks_dict[best_n]
                if amp > a0:
                    harmonic_peaks_dict[best_n] = (freq, amp)
        else:
            inharmonic_peaks.append((freq, amp))

    h_n = len(harmonic_peaks_dict)
    i_n = len(inharmonic_peaks)
    s_n = len(subbass_peaks)
    tot = int(h_n + i_n + s_n)
    return {
        "peaklist_harmonic_window_candidate_count": int(h_n),
        "peaklist_nonharmonic_window_candidate_count": int(i_n),
        "peaklist_low_frequency_window_candidate_count": int(s_n),
        "peaklist_total_window_candidate_count": tot,
        "legacy_harmonic_peak_count_deprecated": int(h_n),
        "legacy_inharmonic_peak_count_deprecated": int(i_n),
        "legacy_subbass_peak_count_deprecated": int(s_n),
        "f0_hz_used": float(f0),
        "classification_valid": True,
        "classification_semantics": (
            "independent_peaklist_window_assignment; not part of residual-row hierarchy"
        ),
    }
