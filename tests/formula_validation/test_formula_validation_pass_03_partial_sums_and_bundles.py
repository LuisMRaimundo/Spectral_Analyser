"""Formula validation Pass 3 — partial sums and bundles (docs/formula_validation/)."""

import math

import numpy as np
import numpy.testing as npt

import density


# Case 3-01
def test_band_partial_metric_sum_linear() -> None:
    out = density.band_partial_metric_sum([1.0, 2.0], "linear")
    npt.assert_allclose(out, 3.0, rtol=0.0, atol=1e-12)


# Case 3-02
def test_partial_metric_sums_linear_additive_total() -> None:
    h, i, s, t = density.partial_metric_sums_h_i_s_total(
        [1.0],
        [2.0],
        [3.0],
        "linear",
    )
    npt.assert_allclose(h, 1.0)
    npt.assert_allclose(i, 2.0)
    npt.assert_allclose(s, 3.0)
    npt.assert_allclose(t, 6.0)


# Case 3-03
def test_partial_metric_sums_d10_total_matches_concat_band_sum() -> None:
    ah = np.array([2.0])
    ai = np.array([1.0])
    asb = np.array([], dtype=float)
    h, i, s, t = density.partial_metric_sums_h_i_s_total(
        ah,
        ai,
        asb,
        "d10",
    )
    af = np.concatenate([ah, ai])
    t_direct = density.band_partial_metric_sum(af, "d10", frequencies_hz=None)
    npt.assert_allclose(t, t_direct, rtol=1e-12, atol=1e-12)
    assert not np.isclose(t, h + i + s), "d10 Total must follow concatenated-vector rule, not H+I+S"


# Case 3-04
def test_compute_discrete_spectral_metrics_bundle_d3() -> None:
    bundle = density.compute_discrete_spectral_metrics_bundle(np.array([1.0, 1.0]))
    expected_d3 = 2.0 * math.log(2.0)
    npt.assert_allclose(bundle["discrete_metric_d3"], expected_d3, rtol=1e-12, atol=1e-15)
