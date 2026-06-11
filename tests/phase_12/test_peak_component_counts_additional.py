from __future__ import annotations

"""
Helper-level contract tests for peak_component_counts.py.

Classifies synthetic peak-list rows into harmonic (slot-based), inharmonic,
and sub-bass buckets. Protects against silent inflation/suppression of
peaklist counts vs density/fatness metrics.

No production code changes. No audio files, GUI, plotting, or pipeline runs.
"""

import math

import pandas as pd
import pytest

from constants import HARMONIC_MAX_CHECK
from peak_component_counts import classify_peaks_harmonic_inharmonic_subbass_from_df


def _peaks(
    freqs: list[float],
    amps: list[float] | None = None,
    *,
    db: list[float] | None = None,
) -> pd.DataFrame:
    data: dict[str, list[float]] = {"Frequency (Hz)": freqs}
    if amps is not None:
        data["Amplitude"] = amps
    elif db is None:
        data["Amplitude"] = [1.0] * len(freqs)
    if db is not None:
        data["Magnitude (dB)"] = db
    return pd.DataFrame(data)


def _tol_hz(expected_hz: float, tolerance_cents: float = 18.0) -> float:
    return expected_hz * (2.0 ** (tolerance_cents / 1200.0) - 1.0)


# ---------------------------------------------------------------------------
# 1. Empty / invalid inputs
# ---------------------------------------------------------------------------

def test_empty_or_invalid_f0_returns_zero_counts_and_invalid_flag() -> None:
    empty = classify_peaks_harmonic_inharmonic_subbass_from_df(None, 110.0)
    assert empty["classification_valid"] is False
    assert empty["peaklist_total_window_candidate_count"] == 0
    assert empty["f0_hz_used"] == pytest.approx(110.0)

    for bad_f0 in (0.0, -1.0, float("nan"), float("inf")):
        out = classify_peaks_harmonic_inharmonic_subbass_from_df(_peaks([220.0]), bad_f0)
        assert out["classification_valid"] is False
        assert out["peaklist_total_window_candidate_count"] == 0
        assert math.isnan(out["f0_hz_used"])


def test_empty_peak_table_sets_f0_but_invalid_when_no_rows() -> None:
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(pd.DataFrame(), 220.0)
    assert out["f0_hz_used"] == pytest.approx(220.0)
    assert out["classification_valid"] is False
    assert out["peaklist_total_window_candidate_count"] == 0


def test_missing_frequency_column_yields_invalid_zero_counts() -> None:
    df = pd.DataFrame({"Amplitude": [1.0]})
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(df, 110.0)
    assert out["classification_valid"] is False
    assert out["peaklist_total_window_candidate_count"] == 0


def test_f0_above_frequency_ceiling_yields_invalid_zero_slots() -> None:
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([500.0]), 500.0, max_freq_hz=400.0
    )
    assert out["classification_valid"] is False
    assert out["peaklist_harmonic_window_candidate_count"] == 0
    assert out["f0_hz_used"] == pytest.approx(500.0)


# ---------------------------------------------------------------------------
# 2. Basic H / I / S separation
# ---------------------------------------------------------------------------

def test_pure_harmonic_series_counts_one_slot_per_order() -> None:
    f0 = 110.0
    df = _peaks([220.0, 330.0, 440.0], [1.0, 0.8, 0.6])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["classification_valid"] is True
    assert out["peaklist_harmonic_window_candidate_count"] == 3
    assert out["peaklist_nonharmonic_window_candidate_count"] == 0
    assert out["peaklist_low_frequency_window_candidate_count"] == 0
    assert out["peaklist_total_window_candidate_count"] == 3


def test_subbass_cutoff_routes_low_frequencies_before_harmonic_matching() -> None:
    f0 = 110.0
    df = _peaks([50.0, 150.0], [1.0, 1.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=1000.0, subbass_cutoff_hz=200.0
    )
    assert out["peaklist_low_frequency_window_candidate_count"] == 2
    assert out["peaklist_harmonic_window_candidate_count"] == 0
    assert out["peaklist_total_window_candidate_count"] == 2


def test_interharmonic_peaks_classified_inharmonic_not_harmonic() -> None:
    f0 = 110.0
    df = _peaks([165.0, 275.0], [1.0, 1.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 0
    assert out["peaklist_nonharmonic_window_candidate_count"] == 2


def test_total_count_equals_sum_of_component_classes() -> None:
    f0 = 110.0
    df = _peaks([80.0, 220.0, 165.0], [1.0, 1.0, 1.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_total_window_candidate_count"] == (
        out["peaklist_harmonic_window_candidate_count"]
        + out["peaklist_nonharmonic_window_candidate_count"]
        + out["peaklist_low_frequency_window_candidate_count"]
    )


def test_legacy_deprecated_keys_mirror_peaklist_counts() -> None:
    f0 = 220.0
    df = _peaks([440.0, 660.0], [1.0, 0.5])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=2000.0, subbass_cutoff_hz=100.0
    )
    assert out["legacy_harmonic_peak_count_deprecated"] == out["peaklist_harmonic_window_candidate_count"]
    assert out["legacy_inharmonic_peak_count_deprecated"] == out["peaklist_nonharmonic_window_candidate_count"]
    assert out["legacy_subbass_peak_count_deprecated"] == out["peaklist_low_frequency_window_candidate_count"]


def test_classification_semantics_token_is_stable() -> None:
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([220.0]), 110.0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["classification_semantics"] == (
        "independent_peaklist_window_assignment; not part of residual-row hierarchy"
    )


# ---------------------------------------------------------------------------
# 3. Threshold / tolerance boundaries
# ---------------------------------------------------------------------------

def test_cents_tolerance_inside_classifies_harmonic_outside_inharmonic() -> None:
    f0 = 110.0
    expected = 220.0
    tol = _tol_hz(expected)
    inside = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([expected + tol * 0.5]),
        f0,
        max_freq_hz=1000.0,
        subbass_cutoff_hz=100.0,
        tolerance_cents=18.0,
    )
    outside = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([expected + tol * 1.5]),
        f0,
        max_freq_hz=1000.0,
        subbass_cutoff_hz=100.0,
        tolerance_cents=18.0,
    )
    assert inside["peaklist_harmonic_window_candidate_count"] == 1
    assert outside["peaklist_harmonic_window_candidate_count"] == 0
    assert outside["peaklist_nonharmonic_window_candidate_count"] == 1


def test_zero_cents_tolerance_requires_exact_harmonic_frequencies() -> None:
    f0 = 100.0
    exact = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([200.0]),
        f0,
        max_freq_hz=1000.0,
        subbass_cutoff_hz=50.0,
        tolerance_cents=0.0,
    )
    detuned = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([200.1]),
        f0,
        max_freq_hz=1000.0,
        subbass_cutoff_hz=50.0,
        tolerance_cents=0.0,
    )
    assert exact["peaklist_harmonic_window_candidate_count"] == 1
    assert detuned["peaklist_harmonic_window_candidate_count"] == 0


# ---------------------------------------------------------------------------
# 4. Non-finite, zero, and negative amplitudes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_freq",
    [float("nan"), float("inf"), -100.0, 0.0],
)
def test_non_finite_or_nonpositive_frequencies_are_skipped(bad_freq: float) -> None:
    df = _peaks([220.0, bad_freq, 330.0], [1.0, 1.0, 1.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, 110.0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 2
    assert out["peaklist_total_window_candidate_count"] == 2


def test_zero_and_negative_amplitudes_do_not_inflate_counts() -> None:
    df = _peaks([220.0, 330.0, 440.0], [-1.0, 0.0, 1.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, 110.0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 1
    assert out["peaklist_total_window_candidate_count"] == 1


def test_magnitude_db_column_converts_to_linear_amplitude() -> None:
    df = _peaks([220.0], db=[0.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, 110.0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 1


def test_amplitude_column_takes_priority_over_magnitude_db() -> None:
    df = _peaks([220.0], amps=[0.0], db=[0.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, 110.0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_total_window_candidate_count"] == 0


# ---------------------------------------------------------------------------
# 5. Duplicate / strongest-wins / order invariance
# ---------------------------------------------------------------------------

def test_competing_peaks_on_same_harmonic_order_keep_strongest_only() -> None:
    f0 = 110.0
    df = _peaks([218.0, 222.0, 330.0], [0.4, 1.0, 0.8])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 2
    assert out["peaklist_total_window_candidate_count"] == 2


def test_duplicate_inharmonic_rows_are_all_counted_without_deduplication() -> None:
    df = _peaks([165.0, 165.0, 275.0], [1.0, 2.0, 1.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, 110.0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_nonharmonic_window_candidate_count"] == 3


def test_input_row_order_does_not_change_counts() -> None:
    f0 = 110.0
    kwargs = {"max_freq_hz": 1000.0, "subbass_cutoff_hz": 100.0}
    a = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([330.0, 220.0, 110.0], [1.0, 1.0, 1.0]), f0, **kwargs
    )
    b = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks([110.0, 220.0, 330.0], [1.0, 1.0, 1.0]), f0, **kwargs
    )
    assert a == b


def test_input_dataframe_is_not_mutated() -> None:
    df = _peaks([220.0, 330.0], [1.0, 0.5])
    snapshot = df.copy()
    classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, 110.0, max_freq_hz=1000.0, subbass_cutoff_hz=100.0
    )
    pd.testing.assert_frame_equal(df, snapshot)


# ---------------------------------------------------------------------------
# 6. Frequency ceiling and HARMONIC_MAX_CHECK cap
# ---------------------------------------------------------------------------

def test_harmonic_slot_count_capped_by_harmonic_max_check() -> None:
    f0 = 20.0
    n_peaks = HARMONIC_MAX_CHECK + 10
    freqs = [f0 * n for n in range(1, n_peaks + 1)]
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks(freqs),
        f0,
        max_freq_hz=50000.0,
        subbass_cutoff_hz=10.0,
    )
    assert out["peaklist_harmonic_window_candidate_count"] == HARMONIC_MAX_CHECK


def test_high_f0_limits_harmonic_slots_under_frequency_ceiling() -> None:
    f0 = 2000.0
    df = _peaks([2000.0, 4000.0, 6000.0], [1.0, 1.0, 1.0])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=5000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 2
    assert out["peaklist_nonharmonic_window_candidate_count"] == 1
    assert out["peaklist_total_window_candidate_count"] == 3


# ---------------------------------------------------------------------------
# 7. Regression guards and determinism
# ---------------------------------------------------------------------------

def test_many_interharmonic_peaks_do_not_inflate_harmonic_slot_count() -> None:
    f0 = 110.0
    harmonic = [220.0 * n for n in range(1, 6)]
    inter = [220.0 * n + 50.0 for n in range(1, 6)]
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        _peaks(harmonic + inter),
        f0,
        max_freq_hz=2000.0,
        subbass_cutoff_hz=100.0,
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 5
    assert out["peaklist_nonharmonic_window_candidate_count"] == 5
    assert out["peaklist_harmonic_window_candidate_count"] < out["peaklist_total_window_candidate_count"]


def test_high_register_harmonics_do_not_gain_extra_slots_from_duplicates() -> None:
    f0 = 2000.0
    df = _peaks([2000.0, 2000.5, 4000.0], [1.0, 0.9, 0.8])
    out = classify_peaks_harmonic_inharmonic_subbass_from_df(
        df, f0, max_freq_hz=10000.0, subbass_cutoff_hz=100.0
    )
    assert out["peaklist_harmonic_window_candidate_count"] == 2
    assert out["peaklist_total_window_candidate_count"] == 2


def test_classify_peaks_is_deterministic() -> None:
    df = _peaks([220.0, 330.0, 165.0], [1.0, 0.5, 0.3])
    kwargs = {"max_freq_hz": 1000.0, "subbass_cutoff_hz": 100.0}
    first = classify_peaks_harmonic_inharmonic_subbass_from_df(df, 110.0, **kwargs)
    second = classify_peaks_harmonic_inharmonic_subbass_from_df(df, 110.0, **kwargs)
    assert first == second
