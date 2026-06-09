from __future__ import annotations

"""
Additional scientifically-motivated coverage for acoustic_density_core.py.

Focus areas (no production code changes):
- degenerate / empty / invalid inputs and their explicit failure statuses;
- input-representation equivalence (Power vs Amplitude vs Magnitude (dB));
- energy accounting: the h/r/s region ratios partition the significant power;
- body-band vs full-spectrum ceiling semantics;
- harmonic ORDER counting vs literal peak counting, and register dependence;
- amplitude-scaling invariance of normalized descriptors;
- row-order invariance and determinism;
- mode-forced / manual / adaptive-fallback weight provenance branches;
- QC token accumulation on zero-capacity register normalization.

Property-style and metamorphic assertions are preferred over golden values.
The only exact constants asserted are ones mathematically implied by the
implementation contract (e.g. the documented adaptive fallback weight vector
[1.0, 0.5, 0.25] normalized, effective count of a single component == 1.0).
"""

from numbers import Number

import numpy as np
import pandas as pd
import pytest

import acoustic_density_core as adc
from acoustic_density_core import (
    canonical_f0_triplet,
    compute_acoustic_density_descriptors,
    compute_descriptors_from_row_and_peaks,
)


# ---------------------------------------------------------------------------
# Shared synthetic fixtures
# ---------------------------------------------------------------------------

def _three_component_peaks() -> pd.DataFrame:
    """Spectrum with sub-bass, harmonic, and residual content for f0=110 Hz.

    Sub-bass: 50 Hz (< min(0.5*110, 80) = 55 Hz policy bound).
    Harmonics: 110/220/330/440 (orders 1-4, exact multiples).
    Residual: a dense off-harmonic cluster 680-720 Hz. The cluster keeps the
    median bin-spacing estimate small (5 Hz), so the adaptive per-partial
    tolerance floor stays at the base 35 cents and the cluster (>= 50 cents
    from the nearest n*110 prediction) is classified as non-harmonic residual.
    """
    residual_cluster = [680.0, 685.0, 690.0, 695.0, 700.0, 705.0, 710.0, 715.0, 720.0]
    return pd.DataFrame(
        {
            "frequency_hz": [50.0, 110.0, 220.0, 330.0, 440.0, *residual_cluster],
            "power": [0.10, 10.0, 6.0, 4.0, 2.5, 0.5, 0.5, 0.55, 0.6, 0.65, 0.6, 0.55, 0.5, 0.5],
        }
    )


def _harmonic_series_peaks(f0_hz: float, n_orders: int) -> pd.DataFrame:
    freqs = [float(n) * f0_hz for n in range(1, n_orders + 1)]
    powers = [1.0 / (float(n) ** 2) for n in range(1, n_orders + 1)]
    return pd.DataFrame({"frequency_hz": freqs, "power": powers})


def _is_nan(x: object) -> bool:
    try:
        return bool(np.isnan(float(x)))
    except (TypeError, ValueError):
        return False


def _assert_numeric_dicts_close(left: dict, right: dict, *, rel: float = 1e-9) -> None:
    shared = sorted(set(left.keys()) & set(right.keys()))
    for key in shared:
        lv, rv = left[key], right[key]
        if isinstance(lv, bool) or isinstance(rv, bool):
            continue
        if not isinstance(lv, Number) or not isinstance(rv, Number):
            continue
        lf, rf = float(lv), float(rv)
        if np.isnan(lf) and np.isnan(rf):
            continue
        assert lf == pytest.approx(rf, rel=rel, abs=1e-12), (
            f"numeric mismatch at {key}: {lf!r} vs {rf!r}"
        )


# ---------------------------------------------------------------------------
# 1. Degenerate / invalid inputs
# ---------------------------------------------------------------------------

def test_empty_peak_table_returns_explicit_failed_status_with_full_schema() -> None:
    out = compute_acoustic_density_descriptors(pd.DataFrame(), f0_hz=110.0)
    assert out["arithmetic_validation_status"] == "failed_missing_spectrum_or_f0"
    # Diagnostic schema must not silently disappear on the defensive path.
    assert out["inharmonicity_fit_status"] == "insufficient_partials"
    assert _is_nan(out["density_metric_raw"])
    assert out["expected_harmonic_slot_count"] == 0
    assert out["harmonic_occupancy_ratio"] == 0.0
    assert out["qc_status"] == ""


def test_invalid_f0_with_valid_peaks_reports_failed_missing_f0() -> None:
    out = compute_acoustic_density_descriptors(
        _three_component_peaks(), f0_hz=float("nan")
    )
    assert out["arithmetic_validation_status"] == "failed_missing_spectrum_or_f0"
    assert out["acoustic_validation_status"] == "failed_missing_f0"
    assert _is_nan(out["f0_used_for_density_hz"])


def test_peaks_entirely_outside_frequency_range_fail_explicitly() -> None:
    peaks = pd.DataFrame({"frequency_hz": [25000.0, 30000.0], "power": [1.0, 0.5]})
    out = compute_acoustic_density_descriptors(
        peaks, f0_hz=110.0, freq_min_hz=20.0, freq_max_hz=20000.0
    )
    assert out["arithmetic_validation_status"] == "failed_no_peaks_in_frequency_range"


def test_positive_relative_threshold_yields_no_significant_peaks_status() -> None:
    # A positive dB threshold sits above the strongest peak by construction.
    out = compute_acoustic_density_descriptors(
        _three_component_peaks(), f0_hz=110.0, min_relative_db=10.0
    )
    assert out["arithmetic_validation_status"] == "failed_no_significant_peaks"


def test_missing_frequency_column_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_acoustic_density_descriptors(
            pd.DataFrame({"power": [1.0, 0.5]}), f0_hz=110.0
        )


def test_missing_amplitude_power_and_db_columns_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_acoustic_density_descriptors(
            pd.DataFrame({"frequency_hz": [110.0, 220.0], "label": ["a", "b"]}),
            f0_hz=110.0,
        )


# ---------------------------------------------------------------------------
# 2. f0 provenance policy (canonical_f0_triplet)
# ---------------------------------------------------------------------------

def test_f0_triplet_accepted_fit_is_acoustically_verified() -> None:
    t = canonical_f0_triplet(f0_final_hz=220.0, f0_fit_accepted=True)
    assert t.f0_hz == 220.0
    assert t.acoustic_f0_status == "fit_accepted_acoustically_verified"
    assert t.f0_fit_accepted is True


def test_f0_triplet_rejected_fit_uses_nominal_fallback_not_verified() -> None:
    t = canonical_f0_triplet(
        f0_final_hz=219.0, f0_initial_hz=220.0, f0_fit_accepted=False
    )
    assert t.f0_hz == 220.0  # initial takes precedence over rejected final
    assert t.acoustic_f0_status == "nominal_fallback_used_not_acoustically_verified"
    assert t.f0_fit_accepted is False


def test_f0_triplet_all_invalid_inputs_returns_explicit_missing_status() -> None:
    # Non-numeric strings exercise the defensive float() conversion guard.
    t = canonical_f0_triplet(
        f0_final_hz="not-a-number",  # type: ignore[arg-type]
        f0_initial_hz=None,
        f0_prior_hz=-5.0,
        f0_fit_accepted=True,
    )
    assert _is_nan(t.f0_hz)
    assert t.f0_source == "missing"
    assert t.acoustic_f0_status == "missing_invalid_f0"
    assert t.f0_fit_accepted is False


def test_row_wrapper_propagates_f0_provenance() -> None:
    peaks = _three_component_peaks()
    out = compute_descriptors_from_row_and_peaks(
        {"f0_final_hz": 110.0, "f0_fit_accepted": True}, peaks
    )
    assert out["f0_used_for_density_hz"] == 110.0
    assert out["acoustic_f0_status"] == "fit_accepted_acoustically_verified"
    assert out["arithmetic_validation_status"] == "passed"

    out_missing = compute_descriptors_from_row_and_peaks({}, peaks)
    assert out_missing["acoustic_f0_status"] == "missing_invalid_f0"
    assert out_missing["arithmetic_validation_status"] == "failed_missing_spectrum_or_f0"


# ---------------------------------------------------------------------------
# 3. Input-representation equivalence (Power vs Amplitude vs dB)
# ---------------------------------------------------------------------------

def test_power_amplitude_and_db_representations_are_equivalent() -> None:
    freqs = [110.0, 220.0, 330.0, 500.0]
    amps = np.array([1.0, 0.6, 0.3, 0.1], dtype=float)
    powers = amps**2
    dbs = 20.0 * np.log10(amps)

    via_power = compute_acoustic_density_descriptors(
        pd.DataFrame({"Frequency (Hz)": freqs, "Power": powers}),
        f0_hz=110.0,
        f0_fit_accepted=True,
    )
    via_amp = compute_acoustic_density_descriptors(
        pd.DataFrame({"frequency_hz": freqs, "Amplitude": amps}),
        f0_hz=110.0,
        f0_fit_accepted=True,
    )
    via_db = compute_acoustic_density_descriptors(
        pd.DataFrame({"freq_hz": freqs, "Magnitude (dB)": dbs}),
        f0_hz=110.0,
        f0_fit_accepted=True,
    )

    _assert_numeric_dicts_close(via_power, via_amp, rel=1e-9)
    _assert_numeric_dicts_close(via_power, via_db, rel=1e-6)


# ---------------------------------------------------------------------------
# 4. Energy accounting and component consistency
# ---------------------------------------------------------------------------

def test_region_energy_ratios_partition_significant_power() -> None:
    out = compute_acoustic_density_descriptors(
        _three_component_peaks(), f0_hz=110.0, f0_fit_accepted=True
    )
    assert out["arithmetic_validation_status"] == "passed"
    h = out["harmonic_energy_ratio"]
    r = out["residual_energy_ratio"]
    s = out["subbass_energy_ratio"]
    for ratio in (h, r, s):
        assert 0.0 <= ratio <= 1.0
    assert h + r + s == pytest.approx(1.0, abs=1e-12)
    # All three regions are populated by construction.
    assert h > 0.0 and r > 0.0 and s > 0.0
    # Nonnegative density/energy outputs.
    for key in (
        "harmonic_body_energy_sum_body_ceiling",
        "inharmonic_body_energy_sum_body_ceiling",
        "subbass_rumble_energy_sum",
        "harmonic_full_spectrum_energy_sum_20khz",
        "inharmonic_full_spectrum_energy_sum_20khz",
        "final_note_density_count_based",
        "final_note_density_salience_weighted",
        "effective_partial_density",
    ):
        assert float(out[key]) >= 0.0
    assert 0.0 <= out["spectral_entropy"] <= 1.0


def test_single_partial_has_zero_entropy_and_unit_effective_count() -> None:
    peaks = pd.DataFrame({"frequency_hz": [220.0], "power": [4.0]})
    out = compute_acoustic_density_descriptors(peaks, f0_hz=220.0, f0_fit_accepted=True)
    assert out["arithmetic_validation_status"] == "passed"
    # Canonical: H(single component) = 0; participation ratio of one = 1.
    assert out["spectral_entropy"] == 0.0
    assert out["effective_partial_density"] == pytest.approx(1.0, abs=1e-12)
    assert out["detected_harmonic_slot_count"] == 1


# ---------------------------------------------------------------------------
# 5. Frequency ceiling / body-band vs full-spectrum semantics
# ---------------------------------------------------------------------------

def test_partials_above_body_ceiling_count_in_full_spectrum_not_body_band() -> None:
    # f0 = 6 kHz with 5 exact harmonics: orders 4-5 (24/30 kHz) lie above the
    # 20 kHz body ceiling but inside the extended full-spectrum window.
    f0 = 6000.0
    peaks = pd.DataFrame(
        {
            "frequency_hz": [6000.0, 12000.0, 18000.0, 24000.0, 30000.0],
            "power": [1.0, 0.5, 0.25, 0.12, 0.06],
        }
    )
    out = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=f0,
        f0_fit_accepted=True,
        freq_max_hz=40000.0,
        full_spectrum_max_hz=40000.0,
    )
    body_e = float(out["harmonic_body_energy_sum_body_ceiling"])
    full_e = float(out["harmonic_full_spectrum_energy_sum_20khz"])
    hf = float(out["high_frequency_spectral_activity_sum"])
    assert full_e > body_e > 0.0
    # Energy above the body ceiling is exactly the full/body difference
    # (no inharmonic content in this synthetic).
    assert hf == pytest.approx(full_e - body_e, rel=1e-12)
    # Full-spectrum candidate count sees every harmonic order; the
    # density-ceiling expected count is bounded by floor(20000/6000) = 3.
    assert out["full_spectrum_harmonic_candidate_count_20khz"] == 5
    assert out["expected_harmonic_order_count_up_to_density_ceiling_hz"] == 3
    assert out["salient_harmonic_order_count_up_to_density_ceiling_hz"] <= 3
    assert float(out["brightness_or_upper_spectral_activity_index_20khz"]) > 0.0
    assert np.isfinite(float(out["spectral_extension_index_20khz"]))


def test_band_window_excluding_every_harmonic_order_yields_zero_expected_slots() -> None:
    # In [8 kHz, 13 kHz] no integer multiple of f0 = 7 kHz exists
    # (1*f0 < 8 kHz < 13 kHz < 2*f0), so the expected slot grid is empty.
    peaks = pd.DataFrame({"frequency_hz": [9000.0], "power": [1.0]})
    out = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=7000.0,
        f0_fit_accepted=True,
        freq_min_hz=8000.0,
        freq_max_hz=13000.0,
    )
    assert out["arithmetic_validation_status"] == "passed"
    assert out["expected_harmonic_slot_count"] == 0
    assert out["harmonic_occupancy_ratio"] == 0.0


# ---------------------------------------------------------------------------
# 6. Harmonic order vs literal peak count; register dependence
# ---------------------------------------------------------------------------

def test_duplicate_peaks_on_same_order_count_once_as_harmonic_order() -> None:
    # Two peaks within tolerance of order 1 (440 and 442 Hz, ~7.9 cents apart)
    # plus one at order 2: order-based counters must report 2, not 3.
    peaks = pd.DataFrame(
        {"frequency_hz": [440.0, 442.0, 880.0], "power": [1.0, 0.8, 0.5]}
    )
    out = compute_acoustic_density_descriptors(peaks, f0_hz=440.0, f0_fit_accepted=True)
    assert out["detected_harmonic_slot_count"] == 2
    assert out["full_spectrum_harmonic_candidate_count_20khz"] == 2


def test_low_register_admits_more_harmonic_orders_under_same_ceiling() -> None:
    ceiling = 2000.0
    low = compute_acoustic_density_descriptors(
        _harmonic_series_peaks(100.0, 20),
        f0_hz=100.0,
        f0_fit_accepted=True,
        salient_harmonic_ceiling_hz=ceiling,
        density_frequency_ceiling_hz=ceiling,
    )
    high = compute_acoustic_density_descriptors(
        _harmonic_series_peaks(500.0, 4),
        f0_hz=500.0,
        f0_fit_accepted=True,
        salient_harmonic_ceiling_hz=ceiling,
        density_frequency_ceiling_hz=ceiling,
    )
    # Theoretical capacity scales as floor(ceiling / f0).
    assert low["expected_harmonic_order_count_up_to_body_ceiling"] == 20
    assert high["expected_harmonic_order_count_up_to_body_ceiling"] == 4
    # Detected salient order counts respect the capacity ordering.
    low_n = low["salient_harmonic_order_count_up_to_body_ceiling"]
    high_n = high["salient_harmonic_order_count_up_to_body_ceiling"]
    assert low_n > high_n
    assert low_n <= 20 and high_n <= 4


# ---------------------------------------------------------------------------
# 7. Scaling / ordering invariance and determinism
# ---------------------------------------------------------------------------

_SCALE_INVARIANT_KEYS = (
    "harmonic_energy_ratio",
    "residual_energy_ratio",
    "subbass_energy_ratio",
    "harmonic_occupancy_ratio",
    "spectral_entropy",
    "effective_partial_density",
    "pure_observation_w_h",
    "pure_observation_w_i",
    "pure_observation_w_s",
    "final_note_density_count_based",
    "salient_harmonic_coverage_up_to_body_ceiling",
)


def test_uniform_power_scaling_preserves_normalized_descriptors() -> None:
    peaks = _three_component_peaks()
    scaled = peaks.copy()
    scaled["power"] = scaled["power"] * 1e3

    base = compute_acoustic_density_descriptors(peaks, f0_hz=110.0, f0_fit_accepted=True)
    amp = compute_acoustic_density_descriptors(scaled, f0_hz=110.0, f0_fit_accepted=True)

    for key in _SCALE_INVARIANT_KEYS:
        assert float(base[key]) == pytest.approx(float(amp[key]), rel=1e-9), key
    # Raw energy sums scale linearly with input power.
    assert float(amp["harmonic_full_spectrum_energy_sum_20khz"]) == pytest.approx(
        1e3 * float(base["harmonic_full_spectrum_energy_sum_20khz"]), rel=1e-9
    )


def test_extra_columns_and_column_order_do_not_change_descriptors() -> None:
    # NOTE: row order is intentionally NOT permuted here. The implementation
    # treats the input as a frequency-ascending spectrum table (QIFFT
    # local-maxima refinement over adjacent rows), so row ordering is part of
    # the input contract. Column ordering and extra metadata columns, however,
    # must be irrelevant to the permissive column reader.
    peaks = _three_component_peaks()
    decorated = peaks.copy()
    decorated["note_label"] = "A2"
    decorated["include_for_density"] = True
    decorated = decorated[["include_for_density", "power", "note_label", "frequency_hz"]]

    base = compute_acoustic_density_descriptors(peaks, f0_hz=110.0, f0_fit_accepted=True)
    deco = compute_acoustic_density_descriptors(decorated, f0_hz=110.0, f0_fit_accepted=True)
    _assert_numeric_dicts_close(base, deco, rel=1e-12)


def test_repeated_identical_calls_are_deterministic() -> None:
    peaks = _three_component_peaks()
    a = compute_acoustic_density_descriptors(peaks, f0_hz=110.0, f0_fit_accepted=True)
    b = compute_acoustic_density_descriptors(peaks, f0_hz=110.0, f0_fit_accepted=True)
    shared = sorted(set(a.keys()) & set(b.keys()))
    for key in shared:
        av, bv = a[key], b[key]
        if not isinstance(av, Number) or isinstance(av, bool):
            continue
        af, bf = float(av), float(bv)
        if np.isnan(af) and np.isnan(bf):
            continue
        assert af == bf, f"non-deterministic output at {key}"


# ---------------------------------------------------------------------------
# 8. Density-weight provenance branches (mode-forced / manual / adaptive)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("mode", "expected_weights", "count_key"),
    [
        ("harmonic_only", (1.0, 0.0, 0.0), "salient_harmonic_order_count_up_to_density_ceiling_hz"),
        ("inharmonic_only", (0.0, 1.0, 0.0), "salient_inharmonic_log_bin_count_up_to_density_ceiling_hz"),
        ("subbass_only", (0.0, 0.0, 1.0), "salient_subbass_particle_count"),
    ],
)
def test_mode_forced_component_weights(
    mode: str, expected_weights: tuple[float, float, float], count_key: str
) -> None:
    out = compute_acoustic_density_descriptors(
        _three_component_peaks(),
        f0_hz=110.0,
        f0_fit_accepted=True,
        density_summation_mode=mode,
    )
    assert out["density_weight_origin"] == "mode_forced_component"
    w = (
        out["harmonic_density_weight"],
        out["inharmonic_density_weight"],
        out["subbass_density_weight"],
    )
    assert w == expected_weights
    # Pure-observation aliases mirror the forced triplet on this branch.
    assert (
        out["pure_observation_w_h"],
        out["pure_observation_w_i"],
        out["pure_observation_w_s"],
    ) == expected_weights
    # Count-based density collapses to exactly the selected component count.
    assert float(out["final_note_density_count_based"]) == pytest.approx(
        float(out[count_key]), abs=1e-12
    )


def test_unknown_mode_keeps_manual_weights_with_explicit_origin() -> None:
    out = compute_acoustic_density_descriptors(
        _three_component_peaks(),
        f0_hz=110.0,
        f0_fit_accepted=True,
        density_summation_mode="manual_fixed",
        harmonic_density_weight=0.7,
        inharmonic_density_weight=0.2,
        subbass_density_weight=0.1,
    )
    assert out["density_weight_origin"] == "manual_or_mode_default"
    assert out["harmonic_density_weight"] == 0.7
    assert out["inharmonic_density_weight"] == 0.2
    assert out["subbass_density_weight"] == 0.1
    assert float(out["final_note_density_salience_weighted"]) >= 0.0


def test_adaptive_mode_with_zero_prior_still_yields_valid_weights() -> None:
    peaks = _three_component_peaks()
    zero_prior = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=110.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
        harmonic_density_weight=0.0,
        inharmonic_density_weight=0.0,
        subbass_density_weight=0.0,
    )
    default_prior = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=110.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
    )
    # Pure observation is prior-independent even for an all-zero prior.
    for key in ("pure_observation_w_h", "pure_observation_w_i", "pure_observation_w_s"):
        assert float(zero_prior[key]) == pytest.approx(float(default_prior[key]), abs=1e-12)
    # The legacy smoothed triplet must remain a finite simplex (internal
    # default prior replaces the degenerate all-zero one).
    smoothed = (
        float(zero_prior["smoothed_w_h_legacy"]),
        float(zero_prior["smoothed_w_i_legacy"]),
        float(zero_prior["smoothed_w_s_legacy"]),
    )
    assert all(np.isfinite(v) and v >= 0.0 for v in smoothed)
    assert sum(smoothed) == pytest.approx(1.0, abs=1e-9)


def test_adaptive_zero_capacity_register_falls_back_with_qc_tokens() -> None:
    # f0 = 1 kHz with a density ceiling below f0 and a raised frequency floor:
    # every register-normalization denominator (harmonic slots, residual log
    # bins, sub-bass particles) is zero, so the adaptive observation cannot be
    # formed and the documented fallback weight vector [1.0, 0.5, 0.25]
    # (normalized) must be used, with explicit QC tokens for all three bands.
    peaks = pd.DataFrame(
        {"frequency_hz": [1000.0, 2000.0, 3000.0], "power": [1.0, 0.5, 0.25]}
    )
    out = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=1000.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
        freq_min_hz=200.0,
        density_frequency_ceiling_hz=150.0,
    )
    assert out["density_weight_origin"] == "adaptive_fallback_default"
    assert float(out["pure_observation_w_h"]) == pytest.approx(1.0 / 1.75, rel=1e-12)
    assert float(out["pure_observation_w_i"]) == pytest.approx(0.5 / 1.75, rel=1e-12)
    assert float(out["pure_observation_w_s"]) == pytest.approx(0.25 / 1.75, rel=1e-12)
    assert (
        float(out["pure_observation_w_h"])
        + float(out["pure_observation_w_i"])
        + float(out["pure_observation_w_s"])
    ) == pytest.approx(1.0, abs=1e-12)
    qc = str(out["qc_status"])
    assert "register_normalization_denominator_zero_harmonic" in qc
    assert "register_normalization_denominator_zero_inharmonic" in qc
    assert "register_normalization_denominator_zero_subbass" in qc
    # Tokens are comma-joined without duplication.
    tokens = [t for t in qc.split(",") if t]
    assert len(tokens) == len(set(tokens)) == 3


def test_qc_status_token_accumulation_is_idempotent() -> None:
    # Pure string utility behind qc_status accumulation: appending an existing
    # token must not duplicate it, and joining stays comma-separated.
    assert adc._append_qc_status("", "tok_a") == "tok_a"
    assert adc._append_qc_status("tok_a", "tok_b") == "tok_a,tok_b"
    assert adc._append_qc_status("tok_a,tok_b", "tok_b") == "tok_a,tok_b"
