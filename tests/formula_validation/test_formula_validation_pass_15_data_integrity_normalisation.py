"""Formula validation Pass 15 — data integrity normalisation (validation plan only)."""

from __future__ import annotations

import math

import numpy as np
import numpy.testing as npt
import pandas as pd

import data_integrity as di


# Case MF-1
def test_metric_float_or_nan() -> None:
    npt.assert_allclose(di.metric_float_or_nan(3.14), 3.14, rtol=0.0, atol=0.0)
    assert math.isnan(di.metric_float_or_nan(None))
    assert math.isnan(di.metric_float_or_nan("not_a_number"))


# Case MI-1
def test_metric_int_or_nan() -> None:
    assert di.metric_int_or_nan(8.9) == 8
    v = di.metric_int_or_nan(None)
    assert v is pd.NA or bool(pd.isna(v)) is True


# Case MR-1
def test_metric_ratio_or_nan() -> None:
    npt.assert_allclose(di.metric_ratio_or_nan(10, 2), 5.0, rtol=0.0, atol=0.0)
    assert math.isnan(di.metric_ratio_or_nan(1.0, 0.0))
    assert math.isnan(di.metric_ratio_or_nan(1.0, float("nan")))


# Case IQR-1
def test_calculate_iqr_bounds_matches_numpy_percentile() -> None:
    data = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    Q1, Q3, lo, hi = di.calculate_iqr_bounds(data, 1.5)
    q1 = float(np.percentile(data, 25))
    q3 = float(np.percentile(data, 75))
    iqr = q3 - q1
    npt.assert_allclose(Q1, q1, rtol=0.0, atol=1e-12)
    npt.assert_allclose(Q3, q3, rtol=0.0, atol=1e-12)
    npt.assert_allclose(lo, q1 - 1.5 * iqr, rtol=0.0, atol=1e-12)
    npt.assert_allclose(hi, q3 + 1.5 * iqr, rtol=0.0, atol=1e-12)


# Case IQR-2
def test_calculate_iqr_bounds_empty() -> None:
    out = di.calculate_iqr_bounds(np.array([]), 1.5)
    assert out == (0.0, 0.0, 0.0, 0.0)


# Case DO-1
def test_detect_outliers_flags_extreme() -> None:
    data = np.array([0.0, 1.0, 2.0, 3.0, 100.0])
    outliers = di.detect_outliers(data, return_mask=False)
    assert 100.0 in outliers


# Case RN-IQR-1
def test_robust_normalize_iqr_affine_no_clip() -> None:
    data = np.array([0.0, 5.0, 10.0])
    _q1, _q3, lower_bound, upper_bound = di.calculate_iqr_bounds(
        data[np.isfinite(data)], 1.5
    )
    out = di.robust_normalize(data, method="iqr", clip_range=None, iqr_multiplier=1.5)
    manual = (data - lower_bound) / (upper_bound - lower_bound)
    finite = np.isfinite(data)
    npt.assert_allclose(out[finite], manual[finite], rtol=0.0, atol=1e-12)


# Case RN-PCT-1
def test_robust_normalize_percentile_midpoint() -> None:
    data = np.linspace(0.0, 100.0, 21)
    p5 = float(np.percentile(data[np.isfinite(data)], 5))
    p95 = float(np.percentile(data[np.isfinite(data)], 95))
    out = di.robust_normalize(
        data,
        method="percentile",
        clip_range=None,
        percentile_low=5.0,
        percentile_high=95.0,
    )
    idx = 10
    assert float(data[idx]) == 50.0
    manual = (50.0 - p5) / (p95 - p5)
    npt.assert_allclose(float(out[idx]), manual, rtol=1e-9, atol=0.0)


# Case RN-RZ-1
def test_robust_normalize_robust_zscore_at_median() -> None:
    data = np.array([-1.0, 0.0, 1.0])
    out = di.robust_normalize(data, method="robust_zscore", clip_range=None)
    npt.assert_allclose(float(out[1]), 0.5, rtol=1e-9, atol=0.0)


# Case RN-FB-1
def test_robust_normalize_unknown_method_minmax() -> None:
    data = np.array([1.0, 2.0, 4.0])
    out = di.robust_normalize(data, method="not_a_real_method", clip_range=None)
    npt.assert_allclose(float(out[1]), 1.0 / 3.0, rtol=1e-12, atol=0.0)


# Case RN-CLIP-1
def test_robust_normalize_clip_to_unit_interval() -> None:
    base = np.linspace(0.0, 100.0, 21)
    data = np.append(base, np.array([200.0]))
    out = di.robust_normalize(
        data,
        method="percentile",
        clip_range=(0.0, 1.0),
        percentile_low=5.0,
        percentile_high=95.0,
    )
    vals = out[np.isfinite(out)]
    assert bool((vals >= -1e-12).all()) is True
    assert bool((vals <= 1.0 + 1e-12).all()) is True


# Case RN-NAN-1
def test_robust_normalize_all_nonfinite_is_nan() -> None:
    data = np.array([np.nan, np.inf, -np.inf], dtype=float)
    out = di.robust_normalize(data, method="iqr")
    assert bool(np.isnan(out).all()) is True


# Case GRS-1
def test_global_reference_scaler_percentile_fit_transform() -> None:
    scaler = di.GlobalReferenceScaler()
    reference = np.linspace(0.0, 10.0, 11)
    scaler.fit(reference, method="percentile")
    assert scaler.reference_stats is not None
    p5 = float(np.percentile(reference[np.isfinite(reference)], 5))
    p95 = float(np.percentile(reference[np.isfinite(reference)], 95))
    npt.assert_allclose(float(scaler.reference_stats["p5"]), p5, rtol=1e-12, atol=0.0)
    npt.assert_allclose(float(scaler.reference_stats["p95"]), p95, rtol=1e-12, atol=0.0)
    transformed = scaler.transform(np.array([5.0]), clip_range=None)
    npt.assert_allclose(
        float(transformed[0]),
        (5.0 - p5) / (p95 - p5),
        rtol=1e-9,
        atol=0.0,
    )


# Case GRS-2
def test_global_reference_scaler_unfitted_delegates_to_robust_normalize() -> None:
    scaler = di.GlobalReferenceScaler()
    data = np.array([0.0, 5.0, 10.0])
    out = scaler.transform(data, clip_range=(0.0, 1.0))
    ref = di.robust_normalize(data, method="iqr", clip_range=(0.0, 1.0))
    npt.assert_allclose(out, ref, rtol=0.0, atol=1e-12)


# Case VMV-1
def test_validate_metric_value_in_range() -> None:
    ok, msg = di.validate_metric_value(0.5, "m", expected_range=(0.0, 1.0))
    assert ok is True
    assert msg is None


# Case VMV-2
def test_validate_metric_value_out_of_range() -> None:
    ok, msg = di.validate_metric_value(1.5, "m", expected_range=(0.0, 1.0))
    assert ok is False
    assert msg is not None


# Case VMA-1
def test_validate_metric_array_outlier_fraction_fails() -> None:
    values = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 1000.0])
    ok, msg, _stats = di.validate_metric_array(
        values, "m", expected_range=None, max_outlier_fraction=0.1
    )
    assert ok is False
    assert msg is not None


# Case VMA-2
def test_validate_metric_array_passes() -> None:
    values = np.linspace(1.0, 5.0, 20)
    ok, msg, _stats = di.validate_metric_array(
        values, "m", expected_range=None, max_outlier_fraction=0.1
    )
    assert ok is True
    assert msg is None


# Case VAP-1
def test_validate_audio_parameters_valid_and_nyquist_formulas() -> None:
    n_fft = 4096
    hop = 256
    sr = 48000
    sig = 8192
    ok, msg = di.validate_audio_parameters(n_fft, hop, sr, sig)
    assert ok is True
    assert msg is None
    npt.assert_allclose(sr / 2.0, 24000.0, rtol=0.0, atol=0.0)
    npt.assert_allclose(sr / float(n_fft), 48000.0 / 4096.0, rtol=0.0, atol=1e-12)


# Case VAP-2
def test_validate_audio_parameters_n_fft_too_small() -> None:
    ok, msg = di.validate_audio_parameters(32, 16, 44100, 65536)
    assert ok is False
    assert msg is not None


# Case NL-1
def test_normalize_log_transform_two_point_endpoints() -> None:
    data = np.array([[1.0, 3.0]])
    out = di.normalize_log_transform(data, clip_range=None)
    flat = out.ravel()
    finite = flat[np.isfinite(flat)]
    npt.assert_allclose(np.sort(finite), [0.0, 1.0], rtol=0.0, atol=1e-9)
