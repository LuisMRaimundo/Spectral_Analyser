# -*- coding: utf-8 -*-
"""
Harmonic-order validation: peak table → :func:`harmonic_alignment.compute_harmonic_alignment_metrics`.

``harmonic_validation_status`` follows harmonic-order cents + match-ratio tiers only; low
collapsed-energy share is reported separately and does not downgrade an ``excellent`` tier.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from constants import HARMONIC_VALIDATION_MAX_HARMONICS
from harmonic_alignment import compute_harmonic_alignment_metrics


def _slot_count_aliases(*, expected: int, matched: int) -> Dict[str, int]:
    e = max(0, int(expected))
    m = max(0, int(matched))
    if m > e:
        m = e
    return {
        "harmonic_slot_expected_count": e,
        "harmonic_slot_matched_count": m,
        "harmonic_slot_missing_count": int(e - m),
    }


def validate_harmonic_series_matched(
    f0_hz: float,
    peaks_df: pd.DataFrame,
    *,
    max_freq_hz: float,
    sample_rate: Optional[float] = None,
    n_fft: Optional[int] = None,
    match_tolerance_cents: Optional[float] = None,
    max_harmonics: int = HARMONIC_VALIDATION_MAX_HARMONICS,
    subbass_cutoff_hz: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Run :func:`harmonic_alignment.compute_harmonic_alignment_metrics` and map to audit keys.

    ``match_tolerance_cents`` overrides adaptive per-order tolerance when set; ``None`` uses adaptive.
    ``subbass_cutoff_hz`` partitions candidates below cutoff as subbass (optional).
    """
    f0 = float(f0_hz)
    out: Dict[str, Any] = {
        "fundamental_freq": f0,
        "validation_backend": "harmonic_order_alignment_cents_v2",
        "external_validation": False,
    }

    if peaks_df is None or peaks_df.empty or not math.isfinite(f0) or f0 <= 0:
        out["harmonic_validation_status"] = "invalid"
        out["error"] = "empty_peaks_or_invalid_f0"
        out["is_valid"] = False
        out["n_peaks_in_pool"] = 0
        out.update(_slot_count_aliases(expected=0, matched=0))
        return out

    if "Frequency (Hz)" not in peaks_df.columns:
        out["harmonic_validation_status"] = "invalid"
        out["error"] = "missing_Frequency_Hz_column"
        out["is_valid"] = False
        out["n_peaks_in_pool"] = 0
        out.update(_slot_count_aliases(expected=0, matched=0))
        return out

    ha = compute_harmonic_alignment_metrics(
        f0,
        peaks_df,
        sample_rate=sample_rate,
        n_fft=n_fft,
        max_frequency_hz=float(max_freq_hz) if math.isfinite(max_freq_hz) else 20000.0,
        min_peak_amplitude=None,
        tolerance_cents=match_tolerance_cents,
        max_harmonics=int(max_harmonics),
        subbass_cutoff_hz=subbass_cutoff_hz,
    )

    n_slots = int(ha.get("harmonic_alignment_expected_count", 0) or 0)
    matched_count = int(ha.get("harmonic_alignment_matched_count", 0) or 0)
    matches = ha.get("harmonic_alignment_matches") or []
    inh_preview = ha.get("harmonic_alignment_inharmonic_candidates_preview")
    if not isinstance(inh_preview, list):
        inh_preview = ha.get("harmonic_alignment_non_harmonic_candidates_preview") or []

    n_pool = 0
    try:
        n_pool = int(len(peaks_df))
    except Exception:
        n_pool = 0

    signed: List[float] = []
    for m in matches:
        if isinstance(m, dict) and "error_cents" in m:
            c = float(m["error_cents"])
            if math.isfinite(c):
                signed.append(c)
    rms_c = float(np.sqrt(np.mean(np.square(np.asarray(signed, dtype=float))))) if signed else float("nan")

    st_align = str(
        ha.get("harmonic_order_alignment_status", ha.get("harmonic_alignment_status", "failed"))
    )
    if st_align in ("excellent", "good"):
        hv_status = "ok"
    elif st_align == "warning":
        hv_status = "warning"
    else:
        hv_status = "invalid"

    reasons: List[str] = []
    if bool(ha.get("harmonic_alignment_low_collapsed_energy_diagnostic")):
        reasons.append("low_collapsed_representative_energy_share_diagnostic_only")

    mean_abs = ha.get("harmonic_alignment_mean_abs_error_cents")
    med_abs = ha.get("harmonic_alignment_median_abs_error_cents")
    mx_abs = ha.get("harmonic_alignment_max_abs_error_cents")
    missing_ratio = 1.0 - float(ha.get("harmonic_alignment_coverage_ratio", 0.0) or 0.0)
    n_outside = int(ha.get("non_harmonic_candidate_count", ha.get("inharmonic_candidate_count", 0)) or 0)
    nh_peak_ratio = float(ha.get("non_harmonic_candidate_peak_ratio", 0.0) or 0.0)
    inh_e_ratio = float(
        ha.get("non_harmonic_candidate_energy_ratio", ha.get("inharmonic_candidate_energy_ratio", 0.0)) or 0.0
    )

    out.update(
        {
            **_slot_count_aliases(expected=int(n_slots), matched=int(matched_count)),
            "harmonic_match_count": int(matched_count),
            "harmonic_match_ratio": float(ha.get("harmonic_alignment_coverage_ratio", 0.0) or 0.0),
            "missing_harmonic_count": int(n_slots - matched_count),
            "missing_harmonic_ratio": float(missing_ratio),
            "non_harmonic_candidate_count": int(n_outside),
            # Deprecated ambiguous alias — same integer as ``non_harmonic_candidate_count`` for this
            # peak-table pool; prefer ``outside_harmonic_window_peak_candidate_count``.
            "inharmonic_candidate_count": int(n_outside),
            "non_harmonic_candidate_peak_ratio": float(nh_peak_ratio),
            "unmatched_spectral_row_count": int(n_outside),
            "outside_harmonic_window_candidate_count": int(n_outside),
            "outside_harmonic_window_candidate_row_count": int(n_outside),
            "outside_harmonic_window_peak_candidate_count": int(n_outside),
            "mean_abs_harmonic_deviation_cents": mean_abs,
            "median_abs_harmonic_deviation_cents": med_abs,
            "max_abs_harmonic_deviation_cents": mx_abs,
            "rms_harmonic_deviation_cents": rms_c,
            "harmonic_validation_status": hv_status,
            "harmonic_validation_reasons": reasons,
            "harmonic_matches": list(matches)[:40],
            "non_harmonic_candidates_preview": list(inh_preview)[:20],
            "is_valid": bool(hv_status == "ok"),
            "n_peaks_in_pool": int(n_pool),
            "inharmonic_candidate_energy_ratio": float(inh_e_ratio),
            "non_harmonic_candidate_energy_ratio": float(inh_e_ratio),
            "outside_harmonic_window_candidate_energy_ratio": float(inh_e_ratio),
        }
    )
    for k, v in ha.items():
        if k not in out:
            out[k] = v
    return out
