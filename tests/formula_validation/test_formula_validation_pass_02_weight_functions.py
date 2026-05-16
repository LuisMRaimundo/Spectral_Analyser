"""Formula validation Pass 2 — weight functions (docs/formula_validation/)."""

import math

import numpy as np
import numpy.testing as npt

import density


# Case 2-01
def test_weight_function_linear() -> None:
    assert density.WeightFunction.linear(4.0) == 4.0


# Case 2-02
def test_weight_function_sqrt_squared_cubic() -> None:
    assert density.WeightFunction.sqrt(4.0) == 2.0
    assert density.WeightFunction.squared(4.0) == 16.0
    assert density.WeightFunction.cubic(4.0) == 64.0


# Case 2-03
def test_weight_function_cbrt_negative() -> None:
    assert density.WeightFunction.cbrt(-8.0) == -2.0


# Case 2-04
def test_weight_function_logarithmic() -> None:
    out = density.WeightFunction.logarithmic(4.0)
    npt.assert_allclose(out, math.log(5.0), rtol=1e-12, atol=1e-15)


# Case 2-05
def test_weight_function_exponential() -> None:
    out = density.WeightFunction.exponential(4.0)
    npt.assert_allclose(out, math.exp(4.0) - 1.0, rtol=1e-12, atol=1e-15)


# Case 2-06
def test_weight_function_inverse_log() -> None:
    out = density.WeightFunction.inverse_log(4.0)
    expected = 1.0 / (math.log1p(4.0) + 1e-10)
    npt.assert_allclose(out, expected, rtol=0.0, atol=1e-12)


# Case 2-07
def test_get_weight_function_sum_and_d2_alias_linear() -> None:
    f_sum = density.get_weight_function("sum")
    f_d2 = density.get_weight_function("d2")
    f_lin = density.get_weight_function("linear")
    x = 3.0
    assert f_sum(x) == f_lin(x)
    assert f_d2(x) == f_lin(x)
