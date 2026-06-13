from __future__ import annotations

"""
Ninth Phase 12 edge-contract layer for harmonic_peak_validation.py.

Complements test_harmonic_peak_validation_additional.py and
tests/phase_11/test_cfar_detection.py with CFAR boundary branches,
strict-vs-diagnostic classification fallbacks, malformed inputs,
and non-mutation / determinism guards.

No production code changes. No audio files, GUI, plotting, or pipeline.
"""

import math

import numpy as np
import pytest

import harmonic_peak_validation as hpv


def _flat_noise(n: int = 128, floor: float = 0.05) -> np.ndarray:
    return np.full(n, floor, dtype=float)


def _isolated_peak(n: int = 128, idx: int = 64, amp: float = 1.0, floor: float = 0.01) -> np.ndarray:
    mags = _flat_noise(n, floor)
    mags[idx] = amp
    if 0 < idx < n - 1:
        mags[idx - 1] = amp * 0.85
        mags[idx + 1] = amp * 0.85
    return mags


# ---------------------------------------------------------------------------
# 1. CFAR edge / non-detection branches
# ---------------------------------------------------------------------------


def test_cfar_rejects_edge_and_short_arrays() -> None:
    mags = _isolated_peak()
    for idx in (0, len(mags) - 1):
        detected, margin_db, threshold_db = hpv.cfar_peak_detection(mags, idx)
        assert detected is False
        assert margin_db == float("-inf")
        assert math.isnan(threshold_db)

    short = np.array([0.1, 0.2, 0.1, 0.05])
    detected, margin_db, threshold_db = hpv.cfar_peak_detection(short, 1)
    assert detected is False
    assert margin_db == float("-inf")
    assert math.isnan(threshold_db)


def test_cfar_insufficient_training_cells_returns_non_detection() -> None:
    mags = np.array([0.1, 0.2, 0.15, 0.12, 0.11, 0.09, 0.08])
    detected, margin_db, threshold_db = hpv.cfar_peak_detection(
        mags, 3, guard_bins=1, train_bins=1
    )
    assert detected is False
    assert margin_db == float("-inf")
    assert math.isnan(threshold_db)


def test_cfar_detected_implies_non_negative_margin_db() -> None:
    mags = _isolated_peak(n=256, idx=128, amp=2.0)
    detected, margin_db, threshold_db = hpv.cfar_peak_detection(mags, 128, pfa=1e-2)
    assert detected is True
    assert margin_db >= 0.0
    assert math.isfinite(threshold_db)


def test_cfar_is_deterministic_on_fixed_synthetic_spectrum() -> None:
    rng = np.random.default_rng(42)
    mags = np.sqrt(rng.exponential(1.0, 300))
    mags[150] = 1.5
    first = hpv.cfar_peak_detection(mags, 150, pfa=1e-2)
    second = hpv.cfar_peak_detection(mags, 150, pfa=1e-2)
    assert first == second


# ---------------------------------------------------------------------------
# 2. Strict vs diagnostic classification fallbacks
# ---------------------------------------------------------------------------


def test_classify_cfar_true_but_snr_below_strict_never_strict_validated() -> None:
    status, include = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=2.5,
        prominence_db=20.0,
        cfar_detected=True,
        strict_snr_db=3.0,
    )
    assert status != "strict_validated"
    assert include is False


def test_classify_cfar_true_low_prominence_falls_back_without_density_inclusion() -> None:
    status, include = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=2.0,
        cfar_detected=True,
        strict_prominence_db=3.0,
    )
    assert status == "snr_validated"
    assert include is False


def test_classify_without_cfar_uses_snr_only_significance_path() -> None:
    status_none, include_none = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=False,
        snr_db=10.0,
        prominence_db=10.0,
        cfar_detected=None,
    )
    status_false, include_false = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=False,
        snr_db=10.0,
        prominence_db=10.0,
        cfar_detected=False,
    )
    assert status_none == "strict_validated"
    assert include_none is True
    assert status_false == "snr_validated"
    assert include_false is False


def test_classify_non_finite_metrics_treated_as_unusable_for_strict() -> None:
    status, include = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=False,
        snr_db=float("nan"),
        prominence_db=float("inf"),
    )
    assert status == "below_noise_floor"
    assert include is False

    # local_peak_valid alone can still yield weak_candidate when SNR is non-finite.
    status_weak, include_weak = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=float("nan"),
        prominence_db=float("inf"),
    )
    assert status_weak == "weak_candidate"
    assert include_weak is False


def test_classify_local_peak_flag_alone_yields_weak_not_canonical() -> None:
    status, include = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=0.5,
        prominence_db=0.5,
        minimum_snr_db=3.0,
    )
    assert status == "weak_candidate"
    assert include is False


def test_classify_snr_validated_never_becomes_density_inclusion_even_with_cfar() -> None:
    status, include = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=5.0,
        prominence_db=1.0,
        cfar_detected=True,
    )
    assert status == "snr_validated"
    assert include is False


# ---------------------------------------------------------------------------
# 3. Local peak validity / metrics edge cases
# ---------------------------------------------------------------------------


def test_is_local_peak_valid_rejects_array_edges() -> None:
    mags = _isolated_peak()
    for idx in (0, len(mags) - 1):
        valid, snr = hpv._is_local_peak_valid(mags, idx)
        assert valid is False
        assert snr == float("-inf")


def test_is_local_peak_valid_does_not_mutate_input_magnitudes() -> None:
    mags = _isolated_peak()
    snap = mags.copy()
    _ = hpv._is_local_peak_valid(mags, 64, threshold_db=3.0, saddle_window=10)
    np.testing.assert_array_equal(mags, snap)


def test_local_peak_metrics_edge_index_returns_negative_infinity_triple() -> None:
    mags = _isolated_peak(n=20, idx=10)
    local_ok, snr_db, prom_db = hpv._local_peak_metrics(mags, 0)
    assert local_ok is False
    assert snr_db == float("-inf")
    assert prom_db == float("-inf")


def test_local_peak_metrics_does_not_mutate_input() -> None:
    mags = _isolated_peak()
    snap = mags.copy()
    _ = hpv._local_peak_metrics(mags, 64, saddle_window=10)
    np.testing.assert_array_equal(mags, snap)


def test_prominence_saddle_window_invalid_inputs_fallback_to_ten() -> None:
    assert hpv._prominence_saddle_window_bins(f0_hz=float("nan"), bin_spacing_hz=10.0) == 10
    assert hpv._prominence_saddle_window_bins(f0_hz=440.0, bin_spacing_hz=0.0) == 10
    assert hpv._prominence_saddle_window_bins(f0_hz=-1.0, bin_spacing_hz=10.0) == 10


def test_prominence_saddle_window_respects_max_bins_cap() -> None:
    win = hpv._prominence_saddle_window_bins(f0_hz=5000.0, bin_spacing_hz=1.0, max_bins=64)
    assert win == 64


# ---------------------------------------------------------------------------
# 4. Harmonic inclusion audit diagnostic labels
# ---------------------------------------------------------------------------


def test_harmonic_inclusion_audit_off_frequency_status() -> None:
    reason = hpv._harmonic_inclusion_audit_exclusion_reason(
        include_for_density=False,
        expected_frequency_hz=880.0,
        frequency_deviation_hz=45.0,
        candidate_status="off_frequency",
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=10.0,
    )
    assert reason.startswith("off_frequency (deviation=")


def test_harmonic_inclusion_audit_snr_below_threshold() -> None:
    reason = hpv._harmonic_inclusion_audit_exclusion_reason(
        include_for_density=False,
        expected_frequency_hz=440.0,
        frequency_deviation_hz=0.0,
        candidate_status="weak_candidate",
        local_peak_valid=True,
        snr_db=2.0,
        prominence_db=10.0,
    )
    assert reason.startswith("snr_below_3dB")


def test_harmonic_inclusion_audit_not_local_maximum_when_other_gates_pass() -> None:
    reason = hpv._harmonic_inclusion_audit_exclusion_reason(
        include_for_density=False,
        expected_frequency_hz=440.0,
        frequency_deviation_hz=0.0,
        candidate_status="weak_candidate",
        local_peak_valid=False,
        snr_db=10.0,
        prominence_db=10.0,
    )
    assert reason == "not_local_maximum"


def test_harmonic_inclusion_audit_rejected_by_validation_fallback() -> None:
    reason = hpv._harmonic_inclusion_audit_exclusion_reason(
        include_for_density=False,
        expected_frequency_hz=440.0,
        frequency_deviation_hz=0.0,
        candidate_status="rejected_bad_f0",
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=10.0,
    )
    assert reason == "rejected_by_validation (status=rejected_bad_f0)"


# ---------------------------------------------------------------------------
# 5. Refinement malformed-input contracts
# ---------------------------------------------------------------------------


def test_refine_candidate_mismatched_lengths_returns_nan_amplitude() -> None:
    out = hpv._refine_candidate_to_interpolated_peak(
        candidate_freq_hz=440.0,
        complete_magnitudes=np.array([1.0, 0.5]),
        complete_freqs=np.array([100.0, 200.0, 300.0]),
    )
    assert math.isnan(out["peak_amplitude_raw"])
    assert out["subbin_interpolation_valid"] is False


def test_refine_candidate_none_inputs_preserve_default_schema() -> None:
    out = hpv._refine_candidate_to_interpolated_peak(
        candidate_freq_hz=261.63,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert set(out.keys()) == {
        "peak_bin_index",
        "bin_center_frequency_hz",
        "interpolated_frequency_hz",
        "subbin_offset_bins",
        "subbin_interpolation_valid",
        "peak_amplitude_raw",
        "peak_magnitude_db",
    }
    assert math.isnan(out["peak_amplitude_raw"])


def test_classify_and_cfar_helpers_idempotent_on_repeated_calls() -> None:
    mags = _isolated_peak()
    cls_a = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=10.0,
        cfar_detected=True,
    )
    cls_b = hpv._classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=10.0,
        cfar_detected=True,
    )
    assert cls_a == cls_b
    cfar_a = hpv.cfar_peak_detection(mags, 64)
    cfar_b = hpv.cfar_peak_detection(mags, 64)
    assert cfar_a == cfar_b
