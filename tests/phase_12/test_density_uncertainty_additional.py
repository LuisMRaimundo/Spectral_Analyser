from __future__ import annotations

"""
Additional scientifically-motivated coverage for density_uncertainty.py.

Public API under test:
- ``bootstrap_note_density_final`` — transform-aware bootstrap CI for
  ``note_density_final`` (weight transform applied inside each resample,
  optional joint ratio propagation);
- ``bootstrap_density_ci`` — bootstrap CI over pre-weighted per-partial
  contributions;
- ``nfft_sensitivity`` — dispersion across analysis resolutions.

Complements tests/phase_11/test_density_uncertainty.py (which covers ratio
propagation ordering, spread/sample-size monotonicity, and the end-to-end
compiled CI columns). This file targets:

- degenerate-distribution baseline (identical partials -> zero spread,
  CI collapses onto the exact point estimate);
- canonical weight-function algebra inside the bootstrap (linear / log /
  power / unknown-key fallback) and exact H/I/S band additivity;
- ci-parameter validation and n_boot clamping boundaries;
- empty bands, all-zero energy, and the zero-energy ratio-propagation
  fallback;
- non-finite and non-positive input sanitisation (exact equivalence with
  pre-filtered input under a fixed seed);
- fixed-seed determinism and seed-independence of the point estimate;
- exact linear scaling of point/CI with amplitude scale (relative
  uncertainty invariant);
- CI-mass monotonicity (wider mass -> wider interval);
- nfft_sensitivity non-finite filtering and the zero-mean NaN guard.

Exact assertions are used only for canonical arithmetic implied directly by
the documented formulas (D = Σφ(A), point = Σ r·D, degenerate resamples).
"""

import math

import numpy as np
import pytest

from density_uncertainty import (
    bootstrap_density_ci,
    bootstrap_note_density_final,
    nfft_sensitivity,
)


_CI_KEYS = (
    "point_estimate",
    "bootstrap_mean",
    "bootstrap_std",
    "ci_low",
    "ci_high",
    "relative_uncertainty",
    "n_boot",
    "ci_mass",
)


# ---------------------------------------------------------------------------
# 1. Zero-uncertainty baseline (degenerate distribution)
# ---------------------------------------------------------------------------

def test_identical_partials_collapse_to_zero_spread() -> None:
    # Resampling identical values can only reproduce them: the bootstrap
    # distribution is a point mass at the deterministic metric.
    bands = {"H": ([5.0] * 10, 1.0)}
    out = bootstrap_note_density_final(bands, weight_function="linear", n_boot=200, seed=3)
    assert out["point_estimate"] == pytest.approx(50.0, abs=1e-12)
    assert out["bootstrap_std"] == 0.0
    assert out["ci_low"] == out["ci_high"] == pytest.approx(50.0, abs=1e-12)
    assert out["relative_uncertainty"] == 0.0

    contrib = bootstrap_density_ci({"H": ([2.0] * 8, 1.0)}, n_boot=200, seed=3)
    assert contrib["point_estimate"] == pytest.approx(16.0, abs=1e-12)
    assert contrib["bootstrap_std"] == 0.0
    assert contrib["ci_low"] == contrib["ci_high"] == pytest.approx(16.0, abs=1e-12)


# ---------------------------------------------------------------------------
# 2. Canonical weight-function algebra and H/I/S additivity
# ---------------------------------------------------------------------------

def test_point_estimate_follows_documented_weight_transforms() -> None:
    amps = [1.0, 2.0, 3.0]
    r = 0.5
    bands = {"H": (amps, r)}
    s = 6.0
    linear = bootstrap_note_density_final(bands, weight_function="linear", n_boot=1, seed=0)
    assert linear["point_estimate"] == pytest.approx(r * s, rel=1e-12)
    log = bootstrap_note_density_final(bands, weight_function="log", n_boot=1, seed=0)
    assert log["point_estimate"] == pytest.approx(r * math.log10(1.0 + s), rel=1e-12)
    power = bootstrap_note_density_final(bands, weight_function="power", n_boot=1, seed=0)
    assert power["point_estimate"] == pytest.approx(r * (1.0 + 4.0 + 9.0), rel=1e-12)
    # Unknown weight keys fall back to the linear sum (documented).
    exotic = bootstrap_note_density_final(bands, weight_function="d17", n_boot=1, seed=0)
    assert exotic["point_estimate"] == pytest.approx(linear["point_estimate"], rel=1e-12)


def test_point_estimate_is_exact_weighted_sum_over_separate_bands() -> None:
    # note_density_final = r_H*D_H + r_I*D_I + r_S*D_S, with each band kept
    # separately accounted for.
    bands = {
        "H": ([1.0, 2.0], 0.7),
        "I": ([0.5], 0.2),
        "S": ([0.25, 0.25], 0.1),
    }
    out = bootstrap_note_density_final(bands, weight_function="linear", n_boot=1, seed=0)
    expected = 0.7 * 3.0 + 0.2 * 0.5 + 0.1 * 0.5
    assert out["point_estimate"] == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# 3. Parameter validation and boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_ci", [0.0, 1.0, -0.1, 1.5])
def test_invalid_ci_mass_raises_value_error_in_both_apis(bad_ci: float) -> None:
    with pytest.raises(ValueError, match="ci"):
        bootstrap_note_density_final({"H": ([1.0], 1.0)}, ci=bad_ci)
    with pytest.raises(ValueError, match="ci"):
        bootstrap_density_ci({"H": ([1.0], 1.0)}, ci=bad_ci)


def test_n_boot_is_clamped_to_at_least_one_resample() -> None:
    out = bootstrap_density_ci({"H": ([1.0, 2.0], 1.0)}, n_boot=0, seed=0)
    assert out["n_boot"] == 1
    # With a single resample the std is the documented 0.0 (no ddof=1 sample).
    assert out["bootstrap_std"] == 0.0
    assert out["ci_low"] == out["ci_high"] == out["bootstrap_mean"]


# ---------------------------------------------------------------------------
# 4. Degenerate inputs
# ---------------------------------------------------------------------------

def test_empty_band_contributes_zero_and_does_not_crash() -> None:
    out = bootstrap_density_ci(
        {"H": ([1.0, 2.0], 0.8), "I": ([], 0.2)}, n_boot=100, seed=0
    )
    assert out["point_estimate"] == pytest.approx(0.8 * 3.0, rel=1e-12)
    assert out["ci_low"] <= out["point_estimate"] <= out["ci_high"]


def test_all_bands_empty_yield_zero_point_and_nan_relative_uncertainty() -> None:
    for propagate in (False, True):
        out = bootstrap_note_density_final(
            {"H": ([], 0.7), "I": ([], 0.2), "S": ([], 0.1)},
            n_boot=50,
            seed=0,
            propagate_ratio_uncertainty=propagate,
        )
        assert out["point_estimate"] == 0.0
        assert out["bootstrap_std"] == 0.0
        assert out["ci_low"] == out["ci_high"] == 0.0
        assert math.isnan(out["relative_uncertainty"])


def test_all_zero_amplitudes_follow_the_empty_band_path() -> None:
    # Non-positive amplitudes are filtered (a > 0), so an all-zero band is
    # equivalent to an empty band, including under ratio propagation
    # (zero total resampled energy -> documented 0.0 fallback).
    out = bootstrap_note_density_final(
        {"H": ([0.0, 0.0], 1.0)},
        n_boot=50,
        seed=0,
        propagate_ratio_uncertainty=True,
    )
    assert out["point_estimate"] == 0.0
    assert out["ci_low"] == out["ci_high"] == 0.0
    assert math.isnan(out["relative_uncertainty"])


# ---------------------------------------------------------------------------
# 5. Non-finite / non-positive sanitisation
# ---------------------------------------------------------------------------

def test_non_finite_contributions_are_filtered_exactly() -> None:
    clean = bootstrap_density_ci({"H": ([1.0, 2.0, 3.0], 1.0)}, n_boot=500, seed=9)
    dirty = bootstrap_density_ci(
        {"H": ([1.0, 2.0, float("nan"), float("inf"), 3.0], 1.0)}, n_boot=500, seed=9
    )
    assert clean == dirty


def test_non_positive_amplitudes_are_filtered_exactly() -> None:
    clean = bootstrap_note_density_final({"H": ([1.0, 2.0], 1.0)}, n_boot=500, seed=9)
    dirty = bootstrap_note_density_final(
        {"H": ([1.0, -5.0, 0.0, 2.0], 1.0)}, n_boot=500, seed=9
    )
    assert clean == dirty


# ---------------------------------------------------------------------------
# 6. Determinism and seed semantics
# ---------------------------------------------------------------------------

def test_fixed_seed_is_fully_reproducible() -> None:
    bands = {"H": ([1.0, 1.5, 2.0, 0.7], 0.8), "I": ([0.2, 0.3], 0.2)}
    a = bootstrap_note_density_final(bands, n_boot=400, seed=42)
    b = bootstrap_note_density_final(bands, n_boot=400, seed=42)
    assert a == b
    c = bootstrap_density_ci(bands, n_boot=400, seed=42)
    d = bootstrap_density_ci(bands, n_boot=400, seed=42)
    assert c == d


def test_point_estimate_is_seed_independent() -> None:
    bands = {"H": ([1.0, 1.5, 2.0, 0.7], 1.0)}
    p1 = bootstrap_note_density_final(bands, n_boot=200, seed=1)["point_estimate"]
    p2 = bootstrap_note_density_final(bands, n_boot=200, seed=999)["point_estimate"]
    assert p1 == p2


# ---------------------------------------------------------------------------
# 7. Scale behaviour and CI-mass monotonicity
# ---------------------------------------------------------------------------

def test_linear_weight_scales_point_and_ci_exactly_with_amplitude_scale() -> None:
    base_amps = [1.0, 1.4, 0.6, 2.2]
    s = 1e3
    base = bootstrap_note_density_final(
        {"H": (base_amps, 1.0)}, weight_function="linear", n_boot=500, seed=5
    )
    scaled = bootstrap_note_density_final(
        {"H": ([a * s for a in base_amps], 1.0)},
        weight_function="linear",
        n_boot=500,
        seed=5,
    )
    # Same seed and same band size -> identical resampling indices, so the
    # linear-weight outputs scale exactly and the relative width is invariant.
    assert scaled["point_estimate"] == pytest.approx(s * base["point_estimate"], rel=1e-12)
    assert scaled["ci_low"] == pytest.approx(s * base["ci_low"], rel=1e-12)
    assert scaled["ci_high"] == pytest.approx(s * base["ci_high"], rel=1e-12)
    assert scaled["relative_uncertainty"] == pytest.approx(
        base["relative_uncertainty"], rel=1e-12
    )


def test_wider_ci_mass_gives_equal_or_wider_interval() -> None:
    rng = np.random.default_rng(8)
    bands = {"H": (list(rng.uniform(0.5, 2.0, 40)), 1.0)}
    narrow = bootstrap_note_density_final(bands, n_boot=2000, seed=2, ci=0.5)
    wide = bootstrap_note_density_final(bands, n_boot=2000, seed=2, ci=0.99)
    assert narrow["ci_mass"] == 0.5 and wide["ci_mass"] == 0.99
    width_narrow = narrow["ci_high"] - narrow["ci_low"]
    width_wide = wide["ci_high"] - wide["ci_low"]
    assert width_narrow >= 0.0
    assert width_wide >= width_narrow
    # Identical seed and data -> identical bootstrap distribution, so the
    # point and mean agree across masses.
    assert narrow["point_estimate"] == wide["point_estimate"]
    assert narrow["bootstrap_mean"] == wide["bootstrap_mean"]


# ---------------------------------------------------------------------------
# 8. Schema stability
# ---------------------------------------------------------------------------

def test_returned_schema_keys_are_stable() -> None:
    out = bootstrap_note_density_final({"H": ([1.0, 2.0], 1.0)}, n_boot=10, seed=0)
    for key in _CI_KEYS + ("uncertainty_sources",):
        assert key in out, key
    assert out["uncertainty_sources"] == "partials"
    out_full = bootstrap_note_density_final(
        {"H": ([1.0, 2.0], 1.0)}, n_boot=10, seed=0, propagate_ratio_uncertainty=True
    )
    assert out_full["uncertainty_sources"] == "partials+ratios"
    out_ci = bootstrap_density_ci({"H": ([1.0, 2.0], 1.0)}, n_boot=10, seed=0)
    assert set(out_ci.keys()) == set(_CI_KEYS)


# ---------------------------------------------------------------------------
# 9. nfft_sensitivity guards
# ---------------------------------------------------------------------------

def test_nfft_sensitivity_ignores_non_finite_values() -> None:
    out = nfft_sensitivity({4096: float("nan"), 8192: 100.0, 16384: float("inf")})
    assert out["n"] == 1
    assert out["mean"] == 100.0
    assert out["std"] == 0.0
    assert math.isnan(out["coefficient_of_variation"])

    all_bad = nfft_sensitivity({4096: float("nan"), 8192: float("inf")})
    assert all_bad["n"] == 0
    for key in ("mean", "std", "min", "max", "coefficient_of_variation", "relative_range"):
        assert math.isnan(all_bad[key]), key


def test_nfft_sensitivity_zero_mean_keeps_nan_relative_measures() -> None:
    # Symmetric values around zero: dispersion exists but the relative
    # measures are undefined (|mean| ~ 0) and stay at the documented NaN.
    out = nfft_sensitivity({4096: -5.0, 8192: 5.0})
    assert out["n"] == 2
    assert out["mean"] == pytest.approx(0.0, abs=1e-12)
    assert out["std"] > 0.0 and math.isfinite(out["std"])
    assert math.isnan(out["coefficient_of_variation"])
    assert math.isnan(out["relative_range"])
