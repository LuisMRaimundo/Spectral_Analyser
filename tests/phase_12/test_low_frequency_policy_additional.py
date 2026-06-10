from __future__ import annotations

"""
Additional scientifically-motivated coverage for low_frequency_policy.py.

Public API under test:
- ``calculate_subfundamental_margin_percent`` — register-dependent guard
  margin tiers below f0;
- ``calculate_adaptive_subfundamental_cutoff_hz`` — deprecated legacy wrapper
  whose final boundary is unified with ``SubBassPolicy.upper_bound_hz``
  (single-source policy), with full audit payload;
- ``classify_low_frequency_row`` — DC / subfundamental / physical-low-band /
  not-low-frequency labels for one spectral row.

Focus areas (no production code changes):
- documented register tiers and their exact boundaries (60 / 120 / 300 Hz);
- invalid-f0 fallbacks (margin 10 %, NaN audit payload);
- parameter fallbacks (min floor, max fraction, leakage guard parsing,
  negative n_fft);
- single-source agreement with SubBassPolicy and the documented
  min(policy bound, f0 * max_fraction) composition;
- classification boundary semantics (inclusive DC edge, strict
  subfundamental edge, inclusive physical upper edge);
- non-finite / non-numeric inputs to classification;
- monotonicity of the label partition along the frequency axis and in the
  adaptive cutoff;
- determinism and Hz unit sanity.

Margins and tier boundaries asserted exactly are explicit policy constants in
the implementation (35/25/15/10 % at <60 / <120 / <300 / >=300 Hz), not
fitted values.
"""

import math

import pytest

from low_frequency_policy import (
    LOW_FREQUENCY_POLICY_VERSION,
    SUBFUNDAMENTAL_CUTOFF_SELECTION_RULE,
    calculate_adaptive_subfundamental_cutoff_hz,
    calculate_subfundamental_margin_percent,
    classify_low_frequency_row,
)
from subbass_policy import SubBassPolicy


def _classify(f_hz: object, *, cutoff_hz: object = 80.0) -> str:
    return classify_low_frequency_row(
        f_hz,  # type: ignore[arg-type]
        dc_floor_hz=20.0,
        physical_low_band_upper_hz=120.0,
        adaptive_subfundamental_cutoff_hz=cutoff_hz,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# 1. Register-margin tiers (explicit policy constants)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("f0", "expected_margin"),
    [
        (30.0, 35.0),
        (59.9, 35.0),
        (60.0, 25.0),   # tier boundary: < 60 is the 35 % tier
        (119.9, 25.0),
        (120.0, 15.0),  # tier boundary: < 120 is the 25 % tier
        (299.9, 15.0),
        (300.0, 10.0),  # tier boundary: < 300 is the 15 % tier
        (1000.0, 10.0),
    ],
)
def test_register_margin_tiers_and_boundaries(f0: float, expected_margin: float) -> None:
    assert calculate_subfundamental_margin_percent(f0) == expected_margin


@pytest.mark.parametrize("bad_f0", [0.0, -5.0, float("nan"), float("inf"), None, "abc"])
def test_invalid_f0_margin_falls_back_to_10_percent(bad_f0: object) -> None:
    assert calculate_subfundamental_margin_percent(bad_f0) == 10.0  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Adaptive cutoff: single-source policy and audit payload
# ---------------------------------------------------------------------------

def test_adaptive_cutoff_agrees_with_subbass_policy_single_source() -> None:
    # Documented unification: the final boundary is
    # min(SubBassPolicy.upper_bound_hz, f0 * max_fraction_of_f0).
    f0, sr, n_fft = 220.0, 48000.0, 4096
    out = calculate_adaptive_subfundamental_cutoff_hz(f0, sr_hz=sr, n_fft=n_fft)
    policy_bound = float(SubBassPolicy.upper_bound_hz(f0_hz=f0, sr_hz=sr, n_fft=n_fft))
    expected = min(policy_bound, f0 * float(out["max_fraction_of_f0"]))
    assert float(out["adaptive_subfundamental_cutoff_hz"]) == expected
    assert out["subfundamental_guard_valid"] is True
    assert out["subfundamental_guard_policy"] == "f0_adaptive_register_margin"
    assert out["low_frequency_policy_version"] == LOW_FREQUENCY_POLICY_VERSION
    assert out["subfundamental_cutoff_selection_rule"] == SUBFUNDAMENTAL_CUTOFF_SELECTION_RULE


def test_adaptive_cutoff_default_parameters_and_hz_units() -> None:
    f0 = 220.0
    out = calculate_adaptive_subfundamental_cutoff_hz(f0)
    # Documented defaults.
    assert float(out["min_floor_hz"]) == 20.0
    assert float(out["max_fraction_of_f0"]) == 0.95
    # Hz sanity: the guard sits strictly below f0 and above DC.
    cutoff = float(out["adaptive_subfundamental_cutoff_hz"])
    assert 0.0 < cutoff < f0
    # Effective margin follows the exported selection-rule formula exactly.
    assert float(out["effective_subfundamental_margin_percent"]) == pytest.approx(
        100.0 * (1.0 - cutoff / f0), rel=1e-12
    )
    # Percentage line follows the register margin exactly.
    margin = calculate_subfundamental_margin_percent(f0)
    assert float(out["subfundamental_margin_percent"]) == margin
    assert float(out["percentage_subfundamental_cutoff_hz"]) == pytest.approx(
        f0 * (1.0 - margin / 100.0), rel=1e-12
    )


@pytest.mark.parametrize("bad_f0", [0.0, -10.0, float("nan"), float("inf"), None, "abc"])
def test_invalid_f0_returns_documented_nan_payload(bad_f0: object) -> None:
    out = calculate_adaptive_subfundamental_cutoff_hz(bad_f0)  # type: ignore[arg-type]
    assert out["subfundamental_guard_valid"] is False
    assert out["subfundamental_guard_policy"] == "invalid_f0"
    assert out["subfundamental_cutoff_selected_by"] == "none_invalid_f0"
    for key in (
        "f0_final_hz",
        "subfundamental_margin_percent",
        "percentage_subfundamental_cutoff_hz",
        "adaptive_subfundamental_cutoff_hz",
        "effective_subfundamental_margin_percent",
    ):
        assert math.isnan(float(out[key])), key
    assert out["low_frequency_policy_version"] == LOW_FREQUENCY_POLICY_VERSION


@pytest.mark.parametrize("bad_floor", [float("nan"), -5.0])
def test_invalid_min_floor_falls_back_to_20_hz(bad_floor: float) -> None:
    out = calculate_adaptive_subfundamental_cutoff_hz(220.0, min_floor_hz=bad_floor)
    assert float(out["min_floor_hz"]) == 20.0


@pytest.mark.parametrize("bad_frac", [float("nan"), 0.0, -1.0])
def test_invalid_max_fraction_falls_back_to_095(bad_frac: float) -> None:
    out = calculate_adaptive_subfundamental_cutoff_hz(220.0, max_fraction_of_f0=bad_frac)
    assert float(out["max_fraction_of_f0"]) == 0.95


def test_leakage_guard_recording_and_invalid_parsing() -> None:
    valid = calculate_adaptive_subfundamental_cutoff_hz(220.0, leakage_guard_cutoff_hz=30.0)
    assert float(valid["leakage_guard_cutoff_hz"]) == 30.0
    # The final boundary stays single-sourced (policy bound caps it), so a
    # leakage candidate below the percentage line cannot raise the cutoff.
    base = calculate_adaptive_subfundamental_cutoff_hz(220.0)
    assert float(valid["adaptive_subfundamental_cutoff_hz"]) == float(
        base["adaptive_subfundamental_cutoff_hz"]
    )
    for bad in ("abc", float("nan"), -10.0, 0.0):
        out = calculate_adaptive_subfundamental_cutoff_hz(
            220.0, leakage_guard_cutoff_hz=bad  # type: ignore[arg-type]
        )
        assert math.isnan(float(out["leakage_guard_cutoff_hz"])), bad


def test_negative_n_fft_is_clamped_and_equivalent_to_unset() -> None:
    with_neg = calculate_adaptive_subfundamental_cutoff_hz(220.0, n_fft=-10)
    without = calculate_adaptive_subfundamental_cutoff_hz(220.0)
    assert float(with_neg["adaptive_subfundamental_cutoff_hz"]) == float(
        without["adaptive_subfundamental_cutoff_hz"]
    )


def test_adaptive_cutoff_is_deterministic() -> None:
    a = calculate_adaptive_subfundamental_cutoff_hz(146.83, sr_hz=44100.0, n_fft=8192)
    b = calculate_adaptive_subfundamental_cutoff_hz(146.83, sr_hz=44100.0, n_fft=8192)
    assert set(a.keys()) == set(b.keys())
    for key, va in a.items():
        vb = b[key]
        if isinstance(va, float) and math.isnan(va):
            assert isinstance(vb, float) and math.isnan(vb), key
        else:
            assert va == vb, key


def test_cutoff_scales_with_register_but_respects_80_hz_perceptual_cap() -> None:
    # SubBassPolicy bound = min(f0/2, 80): low registers scale with f0,
    # higher registers saturate at the fixed perceptual sub-bass edge.
    low = calculate_adaptive_subfundamental_cutoff_hz(60.0)
    mid = calculate_adaptive_subfundamental_cutoff_hz(120.0)
    high = calculate_adaptive_subfundamental_cutoff_hz(880.0)
    c_low = float(low["adaptive_subfundamental_cutoff_hz"])
    c_mid = float(mid["adaptive_subfundamental_cutoff_hz"])
    c_high = float(high["adaptive_subfundamental_cutoff_hz"])
    assert c_low == pytest.approx(30.0)   # f0/2 binds below 160 Hz
    assert c_mid == pytest.approx(60.0)
    assert c_high == pytest.approx(80.0)  # perceptual cap binds above 160 Hz
    assert c_low < c_mid <= c_high <= 80.0


# ---------------------------------------------------------------------------
# 3. Row classification: boundary semantics
# ---------------------------------------------------------------------------

def test_classification_boundary_semantics() -> None:
    # DC edge is inclusive: f <= dc_floor -> DC bucket.
    assert _classify(10.0) == "dc_or_subaudible_residual"
    assert _classify(20.0) == "dc_or_subaudible_residual"
    # Strictly between DC floor and the adaptive cutoff -> subfundamental.
    assert _classify(20.0001) == "subfundamental_residual"
    assert _classify(79.999) == "subfundamental_residual"
    # The adaptive cutoff itself is NOT subfundamental (strict <).
    assert _classify(80.0) == "physical_low_frequency_residual"
    # Physical band upper edge is inclusive.
    assert _classify(120.0) == "physical_low_frequency_residual"
    assert _classify(120.0001) == "not_low_frequency_residual"


@pytest.mark.parametrize("bad_f", ["abc", None, float("nan"), float("inf")])
def test_non_numeric_or_non_finite_frequency_is_not_low_frequency(bad_f: object) -> None:
    assert _classify(bad_f) == "not_low_frequency_residual"


def test_invalid_adaptive_cutoff_treats_guard_as_unbounded() -> None:
    # Documented fallback: a non-finite/non-numeric cutoff becomes +inf, so
    # everything above the DC floor (within the band) is subfundamental.
    for bad_cutoff in ("abc", float("nan"), None):
        assert _classify(50.0, cutoff_hz=bad_cutoff) == "subfundamental_residual"
        assert _classify(119.0, cutoff_hz=bad_cutoff) == "subfundamental_residual"
    # The DC bucket still takes precedence.
    assert _classify(15.0, cutoff_hz=float("nan")) == "dc_or_subaudible_residual"


def test_label_partition_is_monotone_along_the_frequency_axis() -> None:
    # Sweeping upward must traverse the labels in band order without
    # revisiting an earlier bucket.
    order = {
        "dc_or_subaudible_residual": 0,
        "subfundamental_residual": 1,
        "physical_low_frequency_residual": 2,
        "not_low_frequency_residual": 3,
    }
    freqs = [5.0, 15.0, 20.0, 25.0, 50.0, 79.0, 80.0, 100.0, 120.0, 121.0, 500.0]
    ranks = [order[_classify(f)] for f in freqs]
    assert ranks == sorted(ranks)


def test_raising_adaptive_cutoff_only_grows_the_subfundamental_set() -> None:
    freqs = [25.0, 40.0, 60.0, 75.0, 90.0, 110.0]
    low_cut = {f for f in freqs if _classify(f, cutoff_hz=50.0) == "subfundamental_residual"}
    high_cut = {f for f in freqs if _classify(f, cutoff_hz=100.0) == "subfundamental_residual"}
    assert low_cut.issubset(high_cut)
    assert len(high_cut) > len(low_cut)


def test_classification_is_deterministic() -> None:
    for f in (10.0, 20.0, 50.0, 80.0, 120.0, 200.0):
        assert _classify(f) == _classify(f)
