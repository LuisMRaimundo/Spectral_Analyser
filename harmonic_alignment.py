# -*- coding: utf-8 -*-
"""
Harmonic-order alignment in cents (round-assignment + tolerance + collapse).

Operates on a peak table (``Frequency (Hz)`` rows), not raw STFT bins unless the caller
passes bin-rows as candidates (then set ``harmonic_alignment_candidate_basis`` in output).

Terminology:
- **Collapsed harmonic representatives**: at most one strongest-energy peak per matched
  harmonic order ``n`` after round(f/f0) assignment and cents tolerance.
- **Harmonic-region candidates**: peaks at or above the subbass cutoff that fall inside at
  least one harmonic tolerance window around some ``n·f₀``.
- **Inharmonic candidates**: peaks at or above the subbass cutoff that fall outside *all*
  harmonic tolerance windows (outside-window candidates, not a value judgment on validity).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from constants import (
    HARMONIC_ALIGNMENT_EXCELLENT_MAX_MEAN_ABS_CENTS,
    HARMONIC_ALIGNMENT_EXCELLENT_MAX_P95_ABS_CENTS,
    HARMONIC_ALIGNMENT_EXCELLENT_MAX_WEIGHTED_MEAN_ABS_CENTS,
    HARMONIC_ALIGNMENT_EXCELLENT_MIN_ORDER_MATCH_RATIO,
    HARMONIC_ALIGNMENT_GOOD_MAX_MEAN_ABS_CENTS,
    HARMONIC_ALIGNMENT_GOOD_MAX_WEIGHTED_MEAN_ABS_CENTS,
    HARMONIC_ALIGNMENT_GOOD_MIN_ORDER_MATCH_RATIO,
    HARMONIC_VALIDATION_MAX_HARMONICS,
)


def _linear_amp_and_energy(row: pd.Series, df: pd.DataFrame) -> Tuple[float, float]:
    amp = 0.0
    if "Amplitude_linear" in df.columns and pd.notna(row.get("Amplitude_linear")):
        amp = float(row["Amplitude_linear"])
    elif "Amplitude" in df.columns and pd.notna(row.get("Amplitude")):
        amp = float(row["Amplitude"])
    elif "Magnitude_dB" in df.columns and pd.notna(row.get("Magnitude_dB")):
        amp = float(10.0 ** (float(row["Magnitude_dB"]) / 20.0))
    elif "Magnitude (dB)" in df.columns and pd.notna(row.get("Magnitude (dB)")):
        amp = float(10.0 ** (float(row["Magnitude (dB)"]) / 20.0))
    amp = float(max(amp, 0.0))
    return amp, amp * amp


def _cents(obs_hz: float, exp_hz: float) -> float:
    if obs_hz <= 0 or exp_hz <= 0:
        return float("nan")
    return float(1200.0 * math.log2(obs_hz / exp_hz))


def _adaptive_tolerance_cents(expected_hz: float, sample_rate: Optional[float], n_fft: Optional[int]) -> float:
    if (
        sample_rate is None
        or n_fft is None
        or not math.isfinite(float(sample_rate))
        or not math.isfinite(float(n_fft))
        or float(sample_rate) <= 0
        or float(n_fft) <= 0
    ):
        return 18.0
    bin_w = float(sample_rate) / float(n_fft)
    if expected_hz <= 0:
        return 18.0
    hi = expected_hz + bin_w / 2.0
    bw_cents = 1200.0 * math.log2(hi / expected_hz)
    if not math.isfinite(bw_cents) or bw_cents < 0:
        bw_cents = 0.0
    return float(max(18.0, 2.0 * bw_cents))


def _tolerance_for_order(
    n: int,
    f0: float,
    *,
    sample_rate: Optional[float],
    n_fft: Optional[int],
    tolerance_cents: Optional[float],
) -> float:
    if tolerance_cents is not None:
        return float(tolerance_cents)
    return _adaptive_tolerance_cents(f0 * float(n), sample_rate, n_fft)


def _in_any_harmonic_window(
    f_hz: float,
    f0: float,
    n_slots: int,
    max_f: float,
    *,
    sample_rate: Optional[float],
    n_fft: Optional[int],
    tolerance_cents: Optional[float],
) -> bool:
    for n in range(1, n_slots + 1):
        exp = f0 * float(n)
        if exp > max_f + 1e-9:
            break
        tol = _tolerance_for_order(n, f0, sample_rate=sample_rate, n_fft=n_fft, tolerance_cents=tolerance_cents)
        if math.isfinite(abs(_cents(f_hz, exp))) and abs(_cents(f_hz, exp)) <= tol:
            return True
    return False


def compute_harmonic_alignment_metrics(
    f0_hz: float,
    detected_peaks: Union[pd.DataFrame, List[Dict[str, Any]], None],
    *,
    sample_rate: Optional[float] = None,
    n_fft: Optional[int] = None,
    max_frequency_hz: float = 20000.0,
    min_peak_amplitude: Optional[float] = None,
    tolerance_cents: Optional[float] = None,
    max_harmonics: int = HARMONIC_VALIDATION_MAX_HARMONICS,
    subbass_cutoff_hz: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Round-based harmonic order ``n = round(f/f0)``, cents gate, strongest collapse per ``n``,
    partition of candidates into subbass / harmonic-region / inharmonic (by union windows).
    """
    f0 = float(f0_hz)
    out: Dict[str, Any] = {
        "harmonic_alignment_validation_backend": "harmonic_order_alignment_cents_v2",
        "external_validation": False,
        "harmonic_alignment_candidate_basis": "peak_table_rows",
    }

    def _empty_payload(status: str = "failed") -> None:
        nan = float("nan")
        z = 0.0
        out.update(
            {
                "matched_harmonic_orders": 0,
                "total_expected_harmonic_orders": 0,
                "harmonic_order_match_ratio": z,
                "mean_abs_cents_error": nan,
                "weighted_mean_abs_cents_error": nan,
                "median_abs_cents_error": nan,
                "p95_abs_cents_error": nan,
                "max_abs_cents_error": nan,
                "harmonic_representative_count": 0,
                "harmonic_region_candidate_count": 0,
                "inharmonic_candidate_count": 0,
                "subbass_candidate_count": 0,
                "harmonic_representative_energy": z,
                "harmonic_region_candidate_energy": z,
                "inharmonic_candidate_energy": z,
                "subbass_candidate_energy": z,
                "harmonic_region_energy_ratio": z,
                "collapsed_representative_energy_ratio": z,
                "inharmonic_candidate_energy_ratio": z,
                "subbass_candidate_energy_ratio": z,
                "harmonic_alignment_low_collapsed_energy_diagnostic": False,
                "harmonic_alignment_energy_diagnostic_message": None,
                "harmonic_alignment_mean_abs_error_cents": nan,
                "harmonic_alignment_weighted_mean_abs_error_cents": nan,
                "harmonic_alignment_median_abs_error_cents": nan,
                "harmonic_alignment_p95_abs_error_cents": nan,
                "harmonic_alignment_max_abs_error_cents": nan,
                "harmonic_alignment_matched_count": 0,
                "harmonic_alignment_expected_count": 0,
                "harmonic_alignment_coverage_ratio": z,
                "harmonic_alignment_energy_coverage_ratio": z,
                "harmonic_order_alignment_status": status,
                "harmonic_order_alignment_weighted_status": status,
                "harmonic_order_alignment_match_ratio": z,
                "harmonic_order_alignment_mean_abs_error_cents": nan,
                "harmonic_order_alignment_weighted_mean_abs_error_cents": nan,
                "harmonic_order_alignment_median_abs_error_cents": nan,
                "harmonic_order_alignment_p95_abs_error_cents": nan,
                "harmonic_representative_energy_status": "failed",
                "non_harmonic_candidate_count": 0,
                "non_harmonic_candidate_peak_ratio": z,
                "non_harmonic_candidate_energy_ratio": z,
                "harmonic_alignment_tolerance_cents_used": nan,
                "harmonic_alignment_status": status,
                "harmonic_alignment_matches": [],
                "harmonic_alignment_non_harmonic_candidates_preview": [],
                "harmonic_alignment_inharmonic_candidates_preview": [],
            }
        )

    if detected_peaks is None or not math.isfinite(f0) or f0 <= 0:
        _empty_payload("failed")
        return out

    if isinstance(detected_peaks, pd.DataFrame):
        if detected_peaks.empty or "Frequency (Hz)" not in detected_peaks.columns:
            _empty_payload("failed")
            return out
        pool: List[Dict[str, Any]] = []
        for _, row in detected_peaks.iterrows():
            f_hz = float(pd.to_numeric(row.get("Frequency (Hz)"), errors="coerce"))
            if not math.isfinite(f_hz) or f_hz <= 0:
                continue
            amp, en = _linear_amp_and_energy(row, detected_peaks)
            if min_peak_amplitude is not None and amp < float(min_peak_amplitude):
                continue
            pool.append({"pool_id": len(pool), "f_hz": f_hz, "amp": amp, "energy": en})
    elif isinstance(detected_peaks, list):
        pool = []
        for p in detected_peaks:
            if not isinstance(p, dict):
                continue
            f_hz = float(p.get("f_hz", float("nan")))
            if not math.isfinite(f_hz) or f_hz <= 0:
                continue
            amp = float(p.get("amplitude_linear", p.get("amp", 0.0)) or 0.0)
            if min_peak_amplitude is not None and amp < float(min_peak_amplitude):
                continue
            en = amp * amp
            pool.append({"pool_id": len(pool), "f_hz": f_hz, "amp": max(amp, 0.0), "energy": en})
    else:
        _empty_payload("failed")
        return out

    if not pool:
        _empty_payload("failed")
        return out

    max_f = float(max_frequency_hz) if math.isfinite(max_frequency_hz) and max_frequency_hz > 0 else 20000.0
    n_slots = max(0, min(int(max_harmonics), int(math.floor(max_f / f0))))
    f_sub = float(subbass_cutoff_hz) if subbass_cutoff_hz is not None and math.isfinite(float(subbass_cutoff_hz)) else -1.0

    if n_slots <= 0:
        _empty_payload("failed")
        return out

    # --- Partition: subbass | harmonic-region | inharmonic (mutually exclusive) ---
    subbass: List[Dict[str, Any]] = []
    region: List[Dict[str, Any]] = []
    inharmonic: List[Dict[str, Any]] = []
    for p in pool:
        f_hz = float(p["f_hz"])
        if f_hz < f_sub:
            subbass.append(p)
            continue
        if _in_any_harmonic_window(f_hz, f0, n_slots, max_f, sample_rate=sample_rate, n_fft=n_fft, tolerance_cents=tolerance_cents):
            region.append(p)
        else:
            inharmonic.append(p)

    e_sub = float(sum(p["energy"] for p in subbass))
    e_region = float(sum(p["energy"] for p in region))
    e_inh = float(sum(p["energy"] for p in inharmonic))
    e_total = e_sub + e_region + e_inh

    # --- Round + cents match, then collapse strongest per order ---
    buckets: Dict[int, List[Dict[str, Any]]] = {}
    for p in pool:
        f_hz = float(p["f_hz"])
        if f_hz < f_sub:
            continue
        n_round = int(round(f_hz / f0))
        if n_round < 1 or n_round > n_slots:
            continue
        exp = f0 * float(n_round)
        if exp > max_f + 1e-9:
            continue
        tol = _tolerance_for_order(n_round, f0, sample_rate=sample_rate, n_fft=n_fft, tolerance_cents=tolerance_cents)
        ace = abs(_cents(f_hz, exp))
        if math.isfinite(ace) and ace <= tol:
            buckets.setdefault(n_round, []).append(p)

    collapsed: Dict[int, Dict[str, Any]] = {}
    for n, plist in buckets.items():
        best = max(plist, key=lambda x: float(x["energy"]))
        f_hz = float(best["f_hz"])
        exp = f0 * float(n)
        ce = _cents(f_hz, exp)
        collapsed[n] = {
            "n": n,
            "observed_hz": f_hz,
            "expected_hz": float(exp),
            "error_cents": float(ce),
            "abs_error_cents": float(abs(ce)),
            "energy": float(best["energy"]),
            "tolerance_cents": float(
                _tolerance_for_order(n, f0, sample_rate=sample_rate, n_fft=n_fft, tolerance_cents=tolerance_cents)
            ),
        }

    matched_list = [collapsed[k] for k in sorted(collapsed.keys())]
    matched_count = len(matched_list)
    if matched_count > n_slots:
        # Invariant violation: re-collapse by recomputing from unique orders only
        matched_list = [collapsed[k] for k in sorted(set(collapsed.keys()))]
        matched_count = len(matched_list)

    abs_errs = [float(v["abs_error_cents"]) for v in matched_list if math.isfinite(v["abs_error_cents"])]
    energies_m = [float(v["energy"]) for v in matched_list if math.isfinite(v.get("energy", float("nan")))]

    def _mean(a: List[float]) -> float:
        return float(np.mean(np.asarray(a, dtype=float))) if a else float("nan")

    def _median(a: List[float]) -> float:
        return float(np.median(np.asarray(a, dtype=float))) if a else float("nan")

    def _p95(a: List[float]) -> float:
        return float(np.percentile(np.asarray(a, dtype=float), 95)) if a else float("nan")

    mean_abs = _mean(abs_errs)
    med_abs = _median(abs_errs)
    mx_abs = float(np.max(abs_errs)) if abs_errs else float("nan")
    p95_abs = _p95(abs_errs)
    w_mean = float("nan")
    if abs_errs and energies_m and sum(energies_m) > 0:
        w = np.asarray(energies_m, dtype=float)
        e = np.asarray(abs_errs, dtype=float)
        w_mean = float(np.sum(w * e) / np.sum(w))

    e_rep = float(sum(energies_m)) if energies_m else 0.0
    ratio_orders = float(matched_count / n_slots) if n_slots > 0 else 0.0

    def _ratio(num: float, den: float) -> float:
        return float(num / den) if den > 0 else 0.0

    r_region = _ratio(e_region, e_total)
    r_rep = _ratio(e_rep, e_total)
    r_inh = _ratio(e_inh, e_total)
    r_sub = _ratio(e_sub, e_total)

    # --- Alignment status (unweighted mean abs cents + p95 + order match only) ---
    if matched_count == 0:
        status_unweighted = "failed"
    elif (
        ratio_orders >= HARMONIC_ALIGNMENT_EXCELLENT_MIN_ORDER_MATCH_RATIO
        and math.isfinite(mean_abs)
        and mean_abs <= HARMONIC_ALIGNMENT_EXCELLENT_MAX_MEAN_ABS_CENTS
        and math.isfinite(p95_abs)
        and p95_abs <= HARMONIC_ALIGNMENT_EXCELLENT_MAX_P95_ABS_CENTS
    ):
        status_unweighted = "excellent"
    elif (
        ratio_orders >= HARMONIC_ALIGNMENT_GOOD_MIN_ORDER_MATCH_RATIO
        and math.isfinite(mean_abs)
        and mean_abs <= HARMONIC_ALIGNMENT_GOOD_MAX_MEAN_ABS_CENTS
    ):
        status_unweighted = "good"
    else:
        status_unweighted = "warning"

    # --- Weighted alignment status (explicit; uses energy-weighted mean abs cents) ---
    if matched_count == 0:
        status_weighted = "failed"
    elif (
        ratio_orders >= HARMONIC_ALIGNMENT_EXCELLENT_MIN_ORDER_MATCH_RATIO
        and math.isfinite(w_mean)
        and w_mean <= HARMONIC_ALIGNMENT_EXCELLENT_MAX_WEIGHTED_MEAN_ABS_CENTS
        and math.isfinite(p95_abs)
        and p95_abs <= HARMONIC_ALIGNMENT_EXCELLENT_MAX_P95_ABS_CENTS
    ):
        status_weighted = "excellent"
    elif (
        ratio_orders >= HARMONIC_ALIGNMENT_GOOD_MIN_ORDER_MATCH_RATIO
        and math.isfinite(w_mean)
        and w_mean <= HARMONIC_ALIGNMENT_GOOD_MAX_WEIGHTED_MEAN_ABS_CENTS
    ):
        status_weighted = "good"
    else:
        status_weighted = "warning"

    # --- Representative / candidate energy diagnostic (never changes alignment status) ---
    if r_rep >= 0.55 or (r_rep >= 0.35 and r_inh <= 0.45):
        energy_status = "ok"
    elif r_rep >= 0.22:
        energy_status = "acceptable"
    else:
        energy_status = "warning"

    low_cov = bool(status_unweighted == "excellent" and r_rep < 0.5)
    diag_msg = None
    if low_cov:
        diag_msg = (
            "Energy coverage diagnostic: low collapsed-representative coverage; "
            "harmonic_order_alignment_status is unchanged (alignment uses cents + order match only)."
        )

    tols_used = [float(v["tolerance_cents"]) for v in matched_list]
    tol_used = float(np.mean(tols_used)) if tols_used else float("nan")
    if tolerance_cents is not None:
        tol_used = float(tolerance_cents)

    inh_ratio_count = float(len(inharmonic) / max(1, len([p for p in pool if p["f_hz"] >= f_sub])))

    out.update(
        {
            "fundamental_freq": f0,
            "matched_harmonic_orders": int(matched_count),
            "total_expected_harmonic_orders": int(n_slots),
            "harmonic_order_match_ratio": float(ratio_orders),
            "mean_abs_cents_error": mean_abs,
            "weighted_mean_abs_cents_error": w_mean,
            "median_abs_cents_error": med_abs,
            "p95_abs_cents_error": p95_abs,
            "max_abs_cents_error": mx_abs,
            "harmonic_representative_count": int(matched_count),
            "harmonic_region_candidate_count": int(len(region)),
            "inharmonic_candidate_count": int(len(inharmonic)),
            "subbass_candidate_count": int(len(subbass)),
            "harmonic_representative_energy": float(e_rep),
            "harmonic_region_candidate_energy": float(e_region),
            "inharmonic_candidate_energy": float(e_inh),
            "subbass_candidate_energy": float(e_sub),
            "harmonic_region_energy_ratio": float(r_region),
            "collapsed_representative_energy_ratio": float(r_rep),
            "inharmonic_candidate_energy_ratio": float(r_inh),
            "subbass_candidate_energy_ratio": float(r_sub),
            "harmonic_alignment_low_collapsed_energy_diagnostic": bool(low_cov),
            "harmonic_alignment_energy_diagnostic_message": diag_msg,
            "harmonic_alignment_mean_abs_error_cents": mean_abs,
            "harmonic_alignment_weighted_mean_abs_error_cents": w_mean,
            "harmonic_alignment_median_abs_error_cents": med_abs,
            "harmonic_alignment_p95_abs_error_cents": p95_abs,
            "harmonic_alignment_max_abs_error_cents": mx_abs,
            "harmonic_alignment_matched_count": int(matched_count),
            "harmonic_alignment_expected_count": int(n_slots),
            "harmonic_alignment_coverage_ratio": float(ratio_orders),
            "harmonic_alignment_energy_coverage_ratio": float(r_rep),
            "harmonic_alignment_tolerance_cents_used": tol_used,
            # Canonical alignment fields (unweighted vs weighted explicit)
            "harmonic_order_alignment_status": status_unweighted,
            "harmonic_order_alignment_weighted_status": status_weighted,
            "harmonic_order_alignment_match_ratio": float(ratio_orders),
            "harmonic_order_alignment_mean_abs_error_cents": mean_abs,
            "harmonic_order_alignment_weighted_mean_abs_error_cents": w_mean,
            "harmonic_order_alignment_median_abs_error_cents": med_abs,
            "harmonic_order_alignment_p95_abs_error_cents": p95_abs,
            "harmonic_representative_energy_status": energy_status,
            "collapsed_representative_energy_share": float(r_rep),
            "non_harmonic_candidate_energy_ratio": float(r_inh),
            "non_harmonic_candidate_count": int(len(inharmonic)),
            "non_harmonic_candidate_peak_ratio": float(inh_ratio_count),
            "harmonic_region_candidate_rows": int(len(region)),
            "non_harmonic_candidate_rows": int(len(inharmonic)),
            "alignment_candidate_harmonic_orders_matched": int(matched_count),
            "alignment_candidate_harmonic_orders_total": int(n_slots),
            "energy_collapsed_representatives_count": int(matched_count),
            "expected_harmonic_orders_below_nyquist": int(n_slots),
            # Back-compat: primary published alignment tier = unweighted cents + orders
            "harmonic_alignment_status": status_unweighted,
            "harmonic_alignment_matches": matched_list[:40],
            "harmonic_alignment_non_harmonic_candidates_preview": [
                {"f_hz": p["f_hz"], "energy": p["energy"]} for p in inharmonic[:20]
            ],
            "harmonic_alignment_inharmonic_candidates_preview": [
                {"f_hz": p["f_hz"], "energy": p["energy"]} for p in inharmonic[:20]
            ],
        }
    )
    assert int(matched_count) <= int(n_slots), "collapsed harmonic representatives exceed expected orders"
    return out
