"""
Formula validation: Jensen–Shannon divergence (Lin 1991).

Canonical form (see docs/validation/FORMULA_VALIDATION_STATUS.md, F6):

    m = 0.5 * (p + q)
    JS(p, q) = 0.5 * (KL(p, m) + KL(q, m))

This test asserts that _js_divergence in adaptive_density_engine.py
contains the symmetric mean construction and a 0.5-scaled KL sum.
"""

from __future__ import annotations

import ast

from .conftest import find_function, load_module_ast


def test_js_divergence_has_symmetric_mean() -> None:
    tree = load_module_ast("adaptive_density_engine.py")
    fn = find_function(tree, "_js_divergence")
    src = ast.unparse(fn)
    assert "0.5 * (p + q)" in src, (
        "_js_divergence must compute the symmetric mean as 0.5 * (p + q)."
    )


def test_js_divergence_has_half_scaled_kl_sum() -> None:
    tree = load_module_ast("adaptive_density_engine.py")
    fn = find_function(tree, "_js_divergence")
    src = ast.unparse(fn)
    assert "0.5 * (kl_pm + kl_qm)" in src, (
        "_js_divergence must return 0.5 * (kl_pm + kl_qm) — the canonical "
        "Jensen-Shannon form."
    )
