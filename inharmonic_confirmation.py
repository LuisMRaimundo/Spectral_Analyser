"""Confirmed-inharmonic partial class (Phase A).

Residual spectral rows after harmonic exclusion are *candidates*. A
candidate becomes a confirmed inharmonic partial only when it meets the
same evidential standard as harmonic acceptance: CFAR (F-043), local
prominence, temporal persistence (Phase B), leakage exclusion, and
rejection of F-007 comb members.

Statuses
--------
``confirmed_inharmonic_partial``
    All five tests pass. These rows form the I compartment.
``rejected_floor``
    CFAR (same ``P_fa`` as harmonics) fails.
``rejected_stretched_harmonic``
    Candidate lies within spacing-capped tolerance of the F-007 comb
    when the inharmonicity model is applied. Caller may reassign to H
    with ``candidate_status = strict_validated_stretched``.
``rejected_leakage``
    Candidate lies in the main-lobe / first-sidelobe footprint of an
    accepted harmonic.
``candidate_not_confirmed_partial``
    CFAR passed but prominence or persistence failed.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from constants import (
    CFAR_PFA,
    HARMONIC_VALIDATION_MAX_HARMONICS,
    INHARMONIC_MIN_PROMINENCE_DB,
    PARTIAL_PERSISTENCE_MIN_FRACTION,
)
from harmonic_peak_validation import (
    _local_peak_metrics,
    cfar_peak_detection,
    compute_spacing_capped_tolerance_hz,
)
from spectral_leakage_guards import leakage_halfwidth_hz

STATUS_CONFIRMED = "confirmed_inharmonic_partial"
STATUS_NOT_CONFIRMED = "candidate_not_confirmed_partial"
STATUS_LEAKAGE = "rejected_leakage"
STATUS_STRETCHED = "rejected_stretched_harmonic"
STATUS_FLOOR = "rejected_floor"

INHARMONIC_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_CONFIRMED,
        STATUS_NOT_CONFIRMED,
        STATUS_LEAKAGE,
        STATUS_STRETCHED,
        STATUS_FLOOR,
    }
)

CONFIRMATION_TEST_COLUMNS: tuple[str, ...] = (
    "cfar_detected_i",
    "cfar_margin_db_i",
    "local_peak_valid_i",
    "prominence_db_i",
    "temporal_persistence_i",
    "persistence_fraction",
    "not_leakage_i",
    "leakage_guarding_harmonic_order",
    "not_stretched_harmonic_i",
    "nearest_stretched_order",
    "stretched_deviation_hz",
    "inharmonic_status",
    "confirmation_failing_test",
)


def f007_frequency_hz(n: int, f0_hz: float, B: float) -> float:
    """F-007 stiff-string prediction: f_n = n * f0 * sqrt(1 + B * n^2)."""
    order = max(int(n), 1)
    f0 = float(f0_hz)
    b = float(B) if np.isfinite(float(B)) else 0.0
    if b < 0.0:
        b = 0.0
    return float(order) * f0 * float(np.sqrt(1.0 + b * float(order) * float(order)))


def nearest_stretched_harmonic(
    freq_hz: float,
    f0_hz: float,
    B: float,
    *,
    bin_spacing_hz: float = 0.0,
    max_n: int = HARMONIC_VALIDATION_MAX_HARMONICS,
) -> Optional[dict[str, Any]]:
    """Closest F-007 comb member within the spacing-capped tolerance, or None."""
    try:
        freq = float(freq_hz)
        f0 = float(f0_hz)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(freq) or freq <= 0.0 or not np.isfinite(f0) or f0 <= 0.0:
        return None
    best: Optional[dict[str, Any]] = None
    cap_n = max(1, min(int(max_n), int(HARMONIC_VALIDATION_MAX_HARMONICS)))
    for n in range(1, cap_n + 1):
        expected = f007_frequency_hz(n, f0, B)
        tol_hz, limb = compute_spacing_capped_tolerance_hz(
            n, f0, bin_spacing_hz=bin_spacing_hz
        )
        if not np.isfinite(tol_hz) or tol_hz <= 0.0:
            continue
        dev = float(freq - expected)
        if abs(dev) <= float(tol_hz):
            rec = {
                "harmonic_order": int(n),
                "expected_frequency_hz": float(expected),
                "deviation_hz": float(dev),
                "search_tol_hz": float(tol_hz),
                "tolerance_limb": limb,
            }
            if best is None or abs(dev) < abs(float(best["deviation_hz"])):
                best = rec
    return best


def _accepted_harmonic_records(
    accepted_harmonics: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in accepted_harmonics:
        try:
            freq = float(
                row.get("Frequency (Hz)", row.get("extracted_frequency_hz", float("nan")))
            )
        except (TypeError, ValueError):
            continue
        if not np.isfinite(freq) or freq <= 0.0:
            continue
        try:
            order = int(row.get("Harmonic Number", row.get("harmonic_number", 0)) or 0)
        except (TypeError, ValueError):
            order = 0
        out.append({"frequency_hz": freq, "harmonic_order": order})
    return out


def _leakage_guard(
    freq_hz: float,
    accepted: Sequence[Mapping[str, Any]],
    *,
    sr: Optional[float],
    n_fft: Optional[int],
    bin_width_hz: Optional[float],
) -> tuple[bool, Optional[int]]:
    """Return ``(not_leakage, guarding_order)``."""
    hw = float(
        leakage_halfwidth_hz(sr=sr, n_fft=n_fft, bin_width_hz=bin_width_hz)
    )
    if hw <= 0.0:
        return True, None
    best_order: Optional[int] = None
    best_dev = float("inf")
    for rec in accepted:
        dev = abs(float(freq_hz) - float(rec["frequency_hz"]))
        if dev <= hw and dev < best_dev:
            best_dev = dev
            order = int(rec.get("harmonic_order") or 0)
            best_order = order if order > 0 else None
    if best_dev <= hw:
        return False, best_order
    return True, None


def _peak_bin_index(
    freq_hz: float,
    freqs: np.ndarray,
    row: Mapping[str, Any],
) -> Optional[int]:
    for key in ("peak_bin_index", "bin_index", "Bin"):
        if key not in row:
            continue
        try:
            idx = int(row[key])
        except (TypeError, ValueError):
            continue
        if 0 <= idx < int(freqs.size):
            return idx
    if freqs.size == 0:
        return None
    idx = int(np.argmin(np.abs(freqs - float(freq_hz))))
    return idx


def confirm_inharmonic_candidate(
    row: Mapping[str, Any],
    *,
    magnitudes: np.ndarray,
    freqs: np.ndarray,
    accepted_harmonics: Sequence[Mapping[str, Any]],
    f0_hz: float,
    B: float = 0.0,
    inharmonicity_model_applied: bool = False,
    pfa: float = CFAR_PFA,
    sr: Optional[float] = None,
    n_fft: Optional[int] = None,
    persistence_fraction: Optional[float] = None,
    persistence_min_fraction: float = PARTIAL_PERSISTENCE_MIN_FRACTION,
    prominence_min_db: float = INHARMONIC_MIN_PROMINENCE_DB,
) -> dict[str, Any]:
    """Evaluate one residual candidate. Returns the candidate plus evidence."""
    out = dict(row)
    try:
        freq = float(row.get("Frequency (Hz)", row.get("frequency_hz", float("nan"))))
    except (TypeError, ValueError):
        freq = float("nan")
    mags = np.asarray(magnitudes, dtype=float)
    fr = np.asarray(freqs, dtype=float)
    bin_hz = float(fr[1] - fr[0]) if fr.size >= 2 else 0.0
    peak_idx = _peak_bin_index(freq, fr, row) if np.isfinite(freq) else None

    cfar_detected = False
    cfar_margin = float("-inf")
    if peak_idx is not None:
        cfar_detected, cfar_margin, _thr = cfar_peak_detection(
            mags, int(peak_idx), pfa=float(pfa)
        )

    local_ok = False
    prominence = float("-inf")
    if peak_idx is not None:
        is_local, _snr, prominence = _local_peak_metrics(
            mags,
            int(peak_idx),
            f0_hz=f0_hz,
            bin_spacing_hz=bin_hz,
        )
        local_ok = bool(is_local) and float(prominence) >= float(prominence_min_db)

    if persistence_fraction is None:
        try:
            persistence_fraction = float(row.get("persistence_fraction"))
        except (TypeError, ValueError):
            persistence_fraction = float("nan")
    if persistence_fraction is None or not np.isfinite(float(persistence_fraction)):
        # Phase B will populate the per-frame detector. Until then a missing
        # fraction does not veto a candidate that already passed CFAR.
        persistence_value = 1.0
        persistence_reported = float("nan")
    else:
        persistence_value = float(persistence_fraction)
        persistence_reported = persistence_value
    persistence_ok = persistence_value >= float(persistence_min_fraction)

    accepted = _accepted_harmonic_records(accepted_harmonics)
    not_leakage, guard_order = _leakage_guard(
        freq if np.isfinite(freq) else 0.0,
        accepted,
        sr=sr,
        n_fft=n_fft,
        bin_width_hz=bin_hz if bin_hz > 0.0 else None,
    )

    stretch_hit: Optional[dict[str, Any]] = None
    not_stretched = True
    if bool(inharmonicity_model_applied) and np.isfinite(freq):
        stretch_hit = nearest_stretched_harmonic(
            freq, f0_hz, B, bin_spacing_hz=bin_hz
        )
        not_stretched = stretch_hit is None

    if not cfar_detected:
        status = STATUS_FLOOR
        failing = "cfar_detected_i"
    elif not not_stretched:
        status = STATUS_STRETCHED
        failing = "not_stretched_harmonic_i"
    elif not not_leakage:
        status = STATUS_LEAKAGE
        failing = "not_leakage_i"
    elif not local_ok or not persistence_ok:
        status = STATUS_NOT_CONFIRMED
        failing = "local_peak_valid_i" if not local_ok else "temporal_persistence_i"
    else:
        status = STATUS_CONFIRMED
        failing = ""

    out["cfar_detected_i"] = bool(cfar_detected)
    out["cfar_margin_db_i"] = float(cfar_margin)
    out["local_peak_valid_i"] = bool(local_ok)
    out["prominence_db_i"] = float(prominence)
    out["temporal_persistence_i"] = bool(persistence_ok)
    out["persistence_fraction"] = persistence_reported
    out["not_leakage_i"] = bool(not_leakage)
    out["leakage_guarding_harmonic_order"] = (
        int(guard_order) if guard_order is not None else ""
    )
    out["not_stretched_harmonic_i"] = bool(not_stretched)
    out["nearest_stretched_order"] = (
        int(stretch_hit["harmonic_order"]) if stretch_hit else ""
    )
    out["stretched_deviation_hz"] = (
        float(stretch_hit["deviation_hz"]) if stretch_hit else float("nan")
    )
    out["inharmonic_status"] = status
    out["confirmation_failing_test"] = failing
    out["partial_confirmation_status"] = status
    out["Acoustic_Interpretation_Status"] = status
    if status == STATUS_STRETCHED and stretch_hit is not None:
        out["candidate_status"] = "strict_validated_stretched"
        out["exclusion_reason"] = (
            f"rejected_stretched_harmonic (n={stretch_hit['harmonic_order']}, "
            f"dev={stretch_hit['deviation_hz']:.3f} Hz)"
        )
        out["reassign_to_harmonic_order"] = int(stretch_hit["harmonic_order"])
    return out


def confirm_inharmonic_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    magnitudes: np.ndarray,
    freqs: np.ndarray,
    accepted_harmonics: Sequence[Mapping[str, Any]],
    f0_hz: float,
    B: float = 0.0,
    inharmonicity_model_applied: bool = False,
    pfa: float = CFAR_PFA,
    sr: Optional[float] = None,
    n_fft: Optional[int] = None,
    persistence_min_fraction: float = PARTIAL_PERSISTENCE_MIN_FRACTION,
    prominence_min_db: float = INHARMONIC_MIN_PROMINENCE_DB,
) -> list[dict[str, Any]]:
    """Confirm every residual candidate. See module docstring for statuses."""
    return [
        confirm_inharmonic_candidate(
            row,
            magnitudes=magnitudes,
            freqs=freqs,
            accepted_harmonics=accepted_harmonics,
            f0_hz=f0_hz,
            B=B,
            inharmonicity_model_applied=inharmonicity_model_applied,
            pfa=pfa,
            sr=sr,
            n_fft=n_fft,
            persistence_min_fraction=persistence_min_fraction,
            prominence_min_db=prominence_min_db,
        )
        for row in candidates
    ]


def confirm_inharmonic_dataframe(
    candidates: Optional[pd.DataFrame],
    **kwargs: Any,
) -> pd.DataFrame:
    """DataFrame wrapper around :func:`confirm_inharmonic_candidates`."""
    if candidates is None or not isinstance(candidates, pd.DataFrame) or candidates.empty:
        return pd.DataFrame()
    rows = confirm_inharmonic_candidates(candidates.to_dict(orient="records"), **kwargs)
    return pd.DataFrame(rows)


def confirmed_inharmonic_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in rows
        if str(r.get("inharmonic_status") or "") == STATUS_CONFIRMED
    ]


def reassign_stretched_to_harmonics(
    confirmed_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Rows rejected as F-007 comb members, ready to merge into the H list."""
    out: list[dict[str, Any]] = []
    for row in confirmed_rows:
        if str(row.get("inharmonic_status") or "") != STATUS_STRETCHED:
            continue
        rec = dict(row)
        rec["candidate_status"] = "strict_validated_stretched"
        rec["include_for_density"] = True
        try:
            rec["Harmonic Number"] = int(row.get("reassign_to_harmonic_order") or 0)
        except (TypeError, ValueError):
            rec["Harmonic Number"] = 0
        out.append(rec)
    return out
