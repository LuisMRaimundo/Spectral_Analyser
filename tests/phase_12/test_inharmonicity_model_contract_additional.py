from __future__ import annotations

"""
Helper-level contract tests for inharmonicity_model.py.

Complements ``test_inharmonicity_model_additional.py`` with output-shape,
determinism, boundary, and helper-level matching contracts. No production
code changes. No audio, GUI, plotting, or pipeline runs.
"""

import math

import numpy as np
import pytest

from inharmonicity_model import _match_orders, fit_inharmonicity_coefficient


METHOD = "fletcher_1962_joint_f0_B_least_squares"

EXPECTED_KEYS = (
    "inharmonicity_coefficient_B",
    "inharmonicity_fit_f0_hz",
    "stretched_harmonic_predicted_freqs_hz",
    "fit_residual_std_cents",
    "fit_status",
    "method",
)


def _stiff_series(f0_hz: float, b: float, n_orders: int) -> np.ndarray:
    orders = np.arange(1, n_orders + 1, dtype=float)
    return orders * f0_hz * np.sqrt(1.0 + b * orders**2)


def _assert_insufficient_fallback(fit: dict) -> None:
    assert set(fit.keys()) == set(EXPECTED_KEYS)
    assert fit["fit_status"] == "insufficient_partials"
    assert float(fit["inharmonicity_coefficient_B"]) == 0.0
    assert math.isnan(float(fit["inharmonicity_fit_f0_hz"]))
    assert math.isnan(float(fit["fit_residual_std_cents"]))
    assert np.asarray(fit["stretched_harmonic_predicted_freqs_hz"]).size == 0
    assert fit["method"] == METHOD


# ---------------------------------------------------------------------------
# 1. Output shape and type contracts
# ---------------------------------------------------------------------------

def test_fit_result_keys_and_method_string_are_stable() -> None:
    fit = fit_inharmonicity_coefficient(_stiff_series(110.0, 0.0, 12), f0_hz=110.0)
    assert tuple(fit.keys()) == EXPECTED_KEYS
    assert fit["method"] == METHOD
    assert isinstance(fit["fit_status"], str)
    assert isinstance(fit["inharmonicity_coefficient_B"], float)
    assert isinstance(fit["inharmonicity_fit_f0_hz"], float)
    assert isinstance(fit["fit_residual_std_cents"], float)
    assert isinstance(np.asarray(fit["stretched_harmonic_predicted_freqs_hz"]), np.ndarray)


def test_fit_output_excludes_canonical_density_metric_keys() -> None:
    fit = fit_inharmonicity_coefficient(_stiff_series(110.0, 0.0, 8), f0_hz=110.0)
    forbidden = {
        "density",
        "harmonic_energy",
        "effective_partial_density",
        "body_density",
    }
    assert forbidden.isdisjoint(fit.keys())


# ---------------------------------------------------------------------------
# 2. Determinism and input stability
# ---------------------------------------------------------------------------

def test_fit_is_deterministic_for_identical_inputs() -> None:
    freqs = _stiff_series(110.0, 2e-4, 16)
    first = fit_inharmonicity_coefficient(freqs, f0_hz=110.0)
    second = fit_inharmonicity_coefficient(freqs.copy(), f0_hz=110.0)
    for key in EXPECTED_KEYS:
        if key == "stretched_harmonic_predicted_freqs_hz":
            assert np.allclose(
                np.asarray(first[key]),
                np.asarray(second[key]),
                rtol=0.0,
                atol=0.0,
            )
        else:
            assert first[key] == second[key]


def test_candidate_array_is_not_mutated() -> None:
    freqs = _stiff_series(110.0, 0.0, 10)
    original = freqs.copy()
    fit_inharmonicity_coefficient(freqs, f0_hz=110.0)
    assert np.array_equal(freqs, original)


# ---------------------------------------------------------------------------
# 3. Degenerate inputs not fully covered elsewhere
# ---------------------------------------------------------------------------

def test_single_partial_is_insufficient() -> None:
    _assert_insufficient_fallback(
        fit_inharmonicity_coefficient(np.array([110.0]), f0_hz=110.0)
    )


def test_negative_infinite_f0_returns_documented_fallback() -> None:
    _assert_insufficient_fallback(
        fit_inharmonicity_coefficient(_stiff_series(110.0, 0.0, 10), f0_hz=float("-inf"))
    )


def test_non_positive_order_cap_still_requires_three_matched_partials() -> None:
    freqs = np.array([110.0, 220.0])
    _assert_insufficient_fallback(
        fit_inharmonicity_coefficient(freqs, f0_hz=110.0, order_cap=0)
    )


# ---------------------------------------------------------------------------
# 4. Cents-window boundary and matching helper
# ---------------------------------------------------------------------------

def test_partial_outside_cents_window_prevents_three_way_fit() -> None:
    f0 = 110.0
    freqs = np.array(
        [
            f0,
            2.0 * f0,
            3.0 * f0 * (2.0 ** (100.0 / 1200.0)),
        ]
    )
    _assert_insufficient_fallback(
        fit_inharmonicity_coefficient(freqs, f0_hz=f0, cents_window=80.0)
    )


def test_partial_within_cents_window_allows_ok_fit() -> None:
    f0 = 110.0
    freqs = np.array(
        [
            f0,
            2.0 * f0,
            3.0 * f0 * (2.0 ** (79.0 / 1200.0)),
            4.0 * f0,
        ]
    )
    fit = fit_inharmonicity_coefficient(freqs, f0_hz=f0, cents_window=80.0)
    assert fit["fit_status"] == "ok"
    assert float(fit["inharmonicity_coefficient_B"]) == pytest.approx(0.0, abs=1e-9)


def test_match_orders_skips_duplicate_peak_index() -> None:
    freqs = np.array([110.0, 110.0, 220.0, 330.0, 440.0])
    matched_f, matched_n = _match_orders(
        freqs,
        f0_anchor=110.0,
        b_anchor=0.0,
        cap=10,
        cents_window=80.0,
    )
    assert matched_f.size == 4
    assert matched_n.tolist() == [1.0, 2.0, 3.0, 4.0]
    assert np.count_nonzero(np.isclose(matched_f, 110.0)) == 1


def test_match_orders_empty_frequency_list_returns_empty_arrays() -> None:
    matched_f, matched_n = _match_orders(
        np.array([]),
        f0_anchor=110.0,
        b_anchor=0.0,
        cap=5,
        cents_window=80.0,
    )
    assert matched_f.size == 0
    assert matched_n.size == 0


# ---------------------------------------------------------------------------
# 5. Residual acceptance gate contract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("cents_window", "max_allowed_residual"),
    [
        (80.0, 40.0),
        (30.0, 25.0),
        (100.0, 50.0),
    ],
)
def test_ok_status_requires_residual_within_documented_gate(
    cents_window: float, max_allowed_residual: float
) -> None:
    fit = fit_inharmonicity_coefficient(
        _stiff_series(110.0, 0.0, 20),
        f0_hz=110.0,
        cents_window=cents_window,
    )
    assert fit["fit_status"] == "ok"
    assert float(fit["fit_residual_std_cents"]) <= max_allowed_residual


# ---------------------------------------------------------------------------
# 6. Register and stretch edge contracts
# ---------------------------------------------------------------------------

def test_low_register_pure_harmonics_remain_non_inharmonic() -> None:
    f0 = 27.5
    fit = fit_inharmonicity_coefficient(
        _stiff_series(f0, 0.0, 16),
        f0_hz=f0,
    )
    assert fit["fit_status"] == "ok"
    assert float(fit["inharmonicity_coefficient_B"]) < 1e-9


def test_very_high_f0_harmonics_fit_with_finite_diagnostics() -> None:
    f0 = 2000.0
    fit = fit_inharmonicity_coefficient(
        np.arange(1, 16, dtype=float) * f0,
        f0_hz=f0,
    )
    assert fit["fit_status"] == "ok"
    assert float(fit["inharmonicity_fit_f0_hz"]) == pytest.approx(f0, rel=1e-9)
    assert math.isfinite(float(fit["fit_residual_std_cents"]))


def test_small_numerical_noise_does_not_inflate_inharmonicity_coefficient() -> None:
    f0 = 110.0
    pure = _stiff_series(f0, 0.0, 20)
    noisy = pure * (2.0 ** (np.random.default_rng(0).uniform(-0.01, 0.01, pure.size) / 1200.0))
    fit = fit_inharmonicity_coefficient(noisy, f0_hz=f0)
    assert fit["fit_status"] == "ok"
    assert float(fit["inharmonicity_coefficient_B"]) < 1e-6


def test_extreme_stretch_can_be_rejected_without_plausible_b() -> None:
    b_extreme = 1e-3
    freqs = _stiff_series(110.0, b_extreme, 24)
    fit = fit_inharmonicity_coefficient(freqs, f0_hz=110.0)
    assert fit["fit_status"] == "rejected_poor_fit"
    assert float(fit["inharmonicity_coefficient_B"]) == 0.0


# ---------------------------------------------------------------------------
# 7. Thesis-critical regression guards
# ---------------------------------------------------------------------------

def test_invalid_partial_set_does_not_return_ok_with_finite_fit_f0() -> None:
    fit = fit_inharmonicity_coefficient(
        np.array([float("nan"), 0.0, -10.0]),
        f0_hz=110.0,
    )
    _assert_insufficient_fallback(fit)


def test_exact_harmonic_partial_at_prediction_yields_near_zero_residual() -> None:
    f0 = 110.0
    fit = fit_inharmonicity_coefficient(
        np.arange(1, 11, dtype=float) * f0,
        f0_hz=f0,
    )
    assert fit["fit_status"] == "ok"
    assert float(fit["fit_residual_std_cents"]) == pytest.approx(0.0, abs=1e-9)
    assert float(fit["inharmonicity_coefficient_B"]) < 1e-9
