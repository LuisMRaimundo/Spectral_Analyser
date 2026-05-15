"""Formula validation Pass 11 — density extended metrics (validation plan only)."""

import numpy as np
import numpy.testing as npt
import pandas as pd

import density


# Case NF-1
def test_estimate_noise_floor_percentile() -> None:
    psd = np.array([1.0, 2.0, 3.0, 4.0])
    out = density.estimate_noise_floor(psd, 50.0)
    npt.assert_allclose(out, 2.5, rtol=0.0, atol=1e-12)


# Case PSD-1
def test_physical_spectral_density_two_partials() -> None:
    amplitudes = np.array([1.0, 2.0])
    frequencies = np.array([100.0, 200.0])
    out = density.physical_spectral_density(amplitudes, frequencies)
    expected = (25.0 / 17.0) / 2.0
    npt.assert_allclose(out, expected, rtol=1e-12, atol=1e-12)


# Case PSD-2
def test_physical_spectral_density_equal_three() -> None:
    amplitudes = np.array([1.0, 1.0, 1.0])
    frequencies = np.array([100.0, 200.0, 300.0])
    out = density.physical_spectral_density(amplitudes, frequencies)
    npt.assert_allclose(out, 1.0, rtol=0.0, atol=1e-12)


# Case BARK-1
def test_hz_to_bark_1000hz() -> None:
    f = np.array([1000.0])
    ref = 13.0 * np.arctan(0.00076 * f) + 3.5 * np.arctan((f / 7500.0) ** 2)
    out = density._hz_to_bark(f)
    npt.assert_allclose(out[0], ref[0], rtol=1e-12, atol=1e-12)


# Case HD-1
def test_calculate_harmonic_density_count_only() -> None:
    harmonic_amplitudes = np.array([1.0, 1e-4])
    out = density.calculate_harmonic_density(
        harmonic_amplitudes,
        threshold_db=-60.0,
        max_expected_harmonics=2,
        include_amp_factor=False,
    )
    npt.assert_allclose(out, 0.5, rtol=0.0, atol=1e-12)


# Case HD-2
def test_calculate_harmonic_density_with_amp_blend() -> None:
    harmonic_amplitudes = np.array([1.0, 1e-4])
    expected = (1.0 - 0.2) * 0.5 + 0.2 * np.tanh(1.0)
    out = density.calculate_harmonic_density(
        harmonic_amplitudes,
        threshold_db=-60.0,
        max_expected_harmonics=2,
        include_amp_factor=True,
        amp_weight=0.2,
    )
    npt.assert_allclose(out, expected, rtol=1e-12, atol=1e-12)


# Case ID-1
def test_calculate_inharmonic_density_delegates() -> None:
    a = np.array([1.0, 1e-4])
    thr = -60.0
    nmax = 7
    inh = density.calculate_inharmonic_density(a, threshold_db=thr, max_expected_partials=nmax)
    har = density.calculate_harmonic_density(
        a, threshold_db=thr, max_expected_harmonics=nmax
    )
    npt.assert_allclose(inh, har, rtol=0.0, atol=1e-15)


# Case HR-1
def test_calculate_harmonic_richness() -> None:
    harmonic_df = pd.DataFrame({"Amplitude": [1.0, 1.0]})
    out = density.calculate_harmonic_richness(
        harmonic_df,
        max_expected_harmonics=100,
        amplitude_weight=0.2,
    )
    expected = 0.8 * 0.02 + 0.2 * np.tanh(1.0)
    npt.assert_allclose(out, expected, rtol=1e-12, atol=1e-12)


# Case HEPD-1
def test_compute_harmonic_effective_power_density() -> None:
    res = density.compute_harmonic_effective_power_density(amplitudes=np.array([1.0, 2.0]))
    assert res["harmonic_effective_power_density_status"] == "computed"
    npt.assert_allclose(res["harmonic_effective_power_density"], 1.25, rtol=0.0, atol=1e-12)
    npt.assert_allclose(
        res["harmonic_effective_power_density_normalized_by_harmonic_count"],
        1.25 / 2.0,
        rtol=0.0,
        atol=1e-12,
    )
    npt.assert_allclose(res["harmonic_effective_power_density_total_power"], 5.0, rtol=0.0, atol=1e-12)


# Case HEPM-1
def test_compute_harmonic_effective_power_mass() -> None:
    harmonic_df = pd.DataFrame({"Amplitude": [1.0, 2.0]})
    res = density.compute_harmonic_effective_power_mass(harmonic_df)
    assert res["harmonic_effective_power_mass_status"] == "computed"
    npt.assert_allclose(res["harmonic_effective_power_mass"], 5.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(res["harmonic_effective_power_mean"], 2.5, rtol=0.0, atol=1e-12)
    npt.assert_allclose(res["harmonic_effective_power_rms"], np.sqrt(2.5), rtol=0.0, atol=1e-12)
    assert res["harmonic_effective_power_component_count"] == 2


# Case SBPT-1
def test_compute_subbass_protection_tolerance_hz_above_floor() -> None:
    out = density.compute_subbass_protection_tolerance_hz(48000, 4096)
    npt.assert_allclose(out, 4.0 * 48000.0 / 4096.0, rtol=0.0, atol=1e-9)


# Case SBPT-2
def test_compute_subbass_protection_tolerance_hz_floor() -> None:
    out = density.compute_subbass_protection_tolerance_hz(8000, 65536)
    npt.assert_allclose(out, 12.0, rtol=0.0, atol=1e-12)


# Case ALFRP-1
def test_aggregate_low_frequency_residual_peak_power_sum_all_bins() -> None:
    complete = pd.DataFrame(
        {"Frequency (Hz)": [40.0, 100.0, 150.0], "Amplitude": [0.1, 0.2, 0.15]}
    )
    harmonic = pd.DataFrame({"Frequency (Hz)": [100.0]})
    out = density.aggregate_low_frequency_residual_peak_power(
        complete,
        harmonic,
        subbass_hz=200.0,
        subbass_lower_hz=30.0,
        freq_match_tol_hz=12.0,
        low_band_mode="sum_all_bins",
    )
    npt.assert_allclose(out, 0.0325, rtol=0.0, atol=1e-12)


# Case ALFRP-2
def test_aggregate_low_frequency_residual_peak_power_local_maxima() -> None:
    complete = pd.DataFrame(
        {"Frequency (Hz)": [40.0, 80.0, 120.0], "Amplitude": [0.1, 0.3, 0.1]}
    )
    harmonic = pd.DataFrame({"Frequency (Hz)": [500.0]})
    out = density.aggregate_low_frequency_residual_peak_power(
        complete,
        harmonic,
        subbass_hz=200.0,
        subbass_lower_hz=30.0,
        freq_match_tol_hz=12.0,
        low_band_mode="local_maxima",
    )
    npt.assert_allclose(out, 0.09, rtol=0.0, atol=1e-12)


# Case PDECB-1
def test_partial_density_effective_components_bundle_two_strong() -> None:
    d, _diag = density.partial_density_effective_components_bundle(
        harmonic_amplitudes=np.array([1.0, 1.0]),
        inharmonic_amplitudes=None,
        ground_noise_power=None,
        inharmonic_mode="aggregate",
        min_db_relative=-60.0,
    )
    npt.assert_allclose(d, 2.0, rtol=0.0, atol=1e-12)


# Case PDECB-2
def test_partial_density_effective_components_bundle_weak_merge() -> None:
    d, _diag = density.partial_density_effective_components_bundle(
        harmonic_amplitudes=np.array([1.0, 1e-4]),
        min_db_relative=-60.0,
    )
    npt.assert_allclose(d, 1.0, rtol=1e-6, atol=1e-9)


# Case CDM-1
def test_calculate_combined_density_metric_log_identity() -> None:
    out = density.calculate_combined_density_metric(0.5, 0.5, 0.8, 0.2, True)
    npt.assert_allclose(out, 0.5, rtol=0.0, atol=1e-12)


# Case CDM-2
def test_calculate_combined_density_metric_weight_renorm() -> None:
    expected = np.expm1(0.4 * np.log1p(0.25) + 0.6 * np.log1p(0.25))
    out = density.calculate_combined_density_metric(0.25, 0.25, 4.0, 6.0, True)
    npt.assert_allclose(out, expected, rtol=1e-12, atol=1e-12)


# Case CDM-3
def test_calculate_combined_density_metric_linear() -> None:
    out = density.calculate_combined_density_metric(0.1, 0.3, 0.8, 0.2, False)
    npt.assert_allclose(out, 0.14, rtol=0.0, atol=1e-12)


# Case SD-1
def test_spectral_density_small_hill_q1_and_proximity() -> None:
    freqs_hz = np.array([100.0, 200.0])
    amps = np.array([1.0, 1.0])
    res = density.spectral_density(freqs_hz, amps, f0_hz=None, max_peaks_per_band=0)
    npt.assert_allclose(res["R_norm"], 1.0, rtol=0.0, atol=1e-12)
    sigma = 500.0
    sigma_sq = 2.0 * sigma**2
    k12 = float(np.exp(-(100.0**2) / sigma_sq))
    p_num = 2.0 * 0.25 * k12
    p_den = 0.5
    p_norm_expected = min(p_num / p_den, 1.0)
    npt.assert_allclose(res["P_norm"], p_norm_expected, rtol=1e-12, atol=1e-12)
    assert res.get("D_harm") is None


# Case SD-2
def test_spectral_density_renyi_q2() -> None:
    freqs_hz = np.array([100.0, 200.0])
    amps = np.array([1.0, 1.0])
    res = density.spectral_density(freqs_hz, amps, f0_hz=None, max_peaks_per_band=0, q=2.0)
    npt.assert_allclose(res["R_norm"], 1.0, rtol=0.0, atol=1e-12)
