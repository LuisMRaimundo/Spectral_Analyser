"""Formula validation Pass 1 — density metrics (docs/formula_validation/)."""

import math

import numpy as np
import numpy.testing as npt

import density


# Case 1-01
def test_spectral_entropy_uniform_two_bins() -> None:
    power = np.array([1.0, 1.0])
    out = density.compute_spectral_entropy(power)
    npt.assert_allclose(out, 1.0, rtol=0.0, atol=1e-15)


# Case 1-02
def test_spectral_entropy_single_survivor() -> None:
    power = np.array([1.0, 0.0, 0.0])
    out = density.compute_spectral_entropy(power)
    npt.assert_allclose(out, 0.0, rtol=0.0, atol=1e-15)


# Case 1-03
def test_effective_partial_density_three_ones() -> None:
    powers = np.array([1.0, 1.0, 1.0])
    out = density.effective_partial_density_from_powers(powers)
    npt.assert_allclose(out, 3.0, rtol=0.0, atol=1e-12)


# Case 1-04
def test_spectral_neff_two_equal_amps() -> None:
    v = np.array([1.0, 1.0])
    out = density._spectral_neff_from_filtered_linear_amplitudes(v)
    npt.assert_allclose(out, 2.0, rtol=0.0, atol=1e-12)


# Case 1-05
def test_discrete_d3() -> None:
    values = np.array([1.0, 2.0])
    out = density._apply_discrete_spectral_metrics("d3", values, None)
    expected = math.log1p(1.0) + math.log1p(2.0)
    npt.assert_allclose(out, expected, rtol=1e-12, atol=1e-15)


# Case 1-06
def test_discrete_d10() -> None:
    values = np.array([1.0, 1.0])
    out = density._apply_discrete_spectral_metrics("d10", values, None)
    expected = 2.0 * math.log(2.0)
    npt.assert_allclose(out, expected, rtol=1e-12, atol=1e-15)


# Case 1-07
def test_discrete_d17() -> None:
    values = np.array([1.0, 1.0])
    out = density._apply_discrete_spectral_metrics("d17", values, None)
    expected = (math.log(3.0)) ** 2
    npt.assert_allclose(out, expected, rtol=1e-12, atol=1e-15)


# Case 1-08
def test_rolloff_compensated_harmonic_density_minimal() -> None:
    amplitudes = np.array([1.0])
    frequencies_hz = np.array([100.0])
    fundamental_freq_hz = 100.0
    result = density.compute_rolloff_compensated_harmonic_density(
        amplitudes,
        frequencies_hz,
        fundamental_freq_hz,
        weight_function="logarithmic",
    )
    d = float(result["rolloff_compensated_harmonic_density"])
    expected = math.log1p(1.0 / (1.0 + 1e-12))
    npt.assert_allclose(d, expected, rtol=0.0, atol=1e-9)
    assert result["rolloff_compensated_harmonic_density_status"] == "computed"
