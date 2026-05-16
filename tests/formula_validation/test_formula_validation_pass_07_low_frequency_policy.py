"""Formula validation Pass 7 — low-frequency policy (docs/formula_validation/)."""

import numpy as np

import low_frequency_policy


# Case 7-01
def test_subfundamental_margin_percent_piecewise() -> None:
    assert low_frequency_policy.calculate_subfundamental_margin_percent(50.0) == 35.0
    assert low_frequency_policy.calculate_subfundamental_margin_percent(90.0) == 25.0
    assert low_frequency_policy.calculate_subfundamental_margin_percent(150.0) == 15.0
    assert low_frequency_policy.calculate_subfundamental_margin_percent(400.0) == 10.0


# Case 7-02
def test_adaptive_subfundamental_cutoff_hz_f0_100() -> None:
    d = low_frequency_policy.calculate_adaptive_subfundamental_cutoff_hz(100.0)
    assert d["subfundamental_guard_valid"] is True
    m = float(d["subfundamental_margin_percent"])
    assert m == 25.0
    pct = float(d["percentage_subfundamental_cutoff_hz"])
    assert np.isclose(pct, 100.0 * (1.0 - m / 100.0))
    assert float(d["adaptive_subfundamental_cutoff_hz"]) <= float(d["max_fraction_of_f0"]) * 100.0


# Case 7-03
def test_classify_low_frequency_row_boundaries() -> None:
    dc, ad, phys = 30.0, 40.0, 200.0
    assert (
        low_frequency_policy.classify_low_frequency_row(20.0, dc_floor_hz=dc, physical_low_band_upper_hz=phys, adaptive_subfundamental_cutoff_hz=ad)
        == "dc_or_subaudible_residual"
    )
    assert (
        low_frequency_policy.classify_low_frequency_row(35.0, dc_floor_hz=dc, physical_low_band_upper_hz=phys, adaptive_subfundamental_cutoff_hz=ad)
        == "subfundamental_residual"
    )
    assert (
        low_frequency_policy.classify_low_frequency_row(150.0, dc_floor_hz=dc, physical_low_band_upper_hz=phys, adaptive_subfundamental_cutoff_hz=ad)
        == "physical_low_frequency_residual"
    )
    assert (
        low_frequency_policy.classify_low_frequency_row(300.0, dc_floor_hz=dc, physical_low_band_upper_hz=phys, adaptive_subfundamental_cutoff_hz=ad)
        == "not_low_frequency_residual"
    )
