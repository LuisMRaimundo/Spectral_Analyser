"""
Formula validation: FFT-length normalisation factor (Phase 8).

Canonical form (see docs/validation/FORMULA_VALIDATION_STATUS.md, F2):

    peak_amplitude_sum:     factor = N_ref / N
    peak_power_sum:         factor = (N_ref / N)^2
    broadband_amplitude_l2: factor = sqrt(N_ref / N)
    broadband_power_l2:     factor = N_ref / N

This test asserts that the implementation in spectral_normalization.py
returns the symbolically correct expression for each quantity_kind.
"""

from __future__ import annotations

import ast

from .conftest import find_function, load_module_ast


def _function_returns_expression_for_branch(
    fn: ast.FunctionDef, branch_string: str
) -> ast.expr | None:
    """Walk the AST of fn and return the Return.value that follows a branch matching branch_string."""
    found_branch: ast.If | None = None
    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare):
                comparators = test.comparators
                for c in comparators:
                    if isinstance(c, ast.Constant) and c.value == branch_string:
                        found_branch = node
                        break
            if found_branch is node:
                break
    if found_branch is None:
        return None
    for sub in ast.walk(found_branch):
        if isinstance(sub, ast.Return) and sub.value is not None:
            return sub.value
    return None


def test_peak_amplitude_sum_returns_ratio() -> None:
    tree = load_module_ast("spectral_normalization.py")
    fn = find_function(tree, "n_fft_normalization_factor")
    expr = _function_returns_expression_for_branch(fn, "peak_amplitude_sum")
    assert expr is not None, "peak_amplitude_sum branch not found."
    # Expect Call to float(ratio) — i.e. a Call whose argument names 'ratio'.
    src = ast.unparse(expr)
    assert "ratio" in src and "ratio * ratio" not in src and "sqrt" not in src, (
        f"peak_amplitude_sum must return ratio (linear), got: {src}"
    )


def test_peak_power_sum_returns_ratio_squared() -> None:
    tree = load_module_ast("spectral_normalization.py")
    fn = find_function(tree, "n_fft_normalization_factor")
    expr = _function_returns_expression_for_branch(fn, "peak_power_sum")
    assert expr is not None, "peak_power_sum branch not found."
    src = ast.unparse(expr)
    assert "ratio * ratio" in src or "ratio**2" in src, (
        f"peak_power_sum must return ratio*ratio (quadratic), got: {src}"
    )


def test_broadband_amplitude_l2_returns_sqrt_ratio() -> None:
    tree = load_module_ast("spectral_normalization.py")
    fn = find_function(tree, "n_fft_normalization_factor")
    expr = _function_returns_expression_for_branch(fn, "broadband_amplitude_l2")
    assert expr is not None, "broadband_amplitude_l2 branch not found."
    src = ast.unparse(expr)
    assert "sqrt(ratio)" in src, (
        f"broadband_amplitude_l2 must return sqrt(ratio), got: {src}"
    )


def test_broadband_power_l2_returns_ratio() -> None:
    tree = load_module_ast("spectral_normalization.py")
    fn = find_function(tree, "n_fft_normalization_factor")
    expr = _function_returns_expression_for_branch(fn, "broadband_power_l2")
    assert expr is not None, "broadband_power_l2 branch not found."
    src = ast.unparse(expr)
    assert "ratio" in src and "sqrt" not in src and "ratio * ratio" not in src, (
        f"broadband_power_l2 must return ratio (linear), got: {src}"
    )
