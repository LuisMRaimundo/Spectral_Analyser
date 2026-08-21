"""
Formula validation: balanced component density (Hill q=1 / F-056).

Canonical form (see docs/validation/FORMULA_VALIDATION_STATUS.md, F-056):

    P_i = A_i ** 2
    p_i = P_i / sum(P)          # skip components with P_i == 0
    D1  = exp( - sum(p_i * ln(p_i)) )
"""

from __future__ import annotations

from .conftest import has_string_literal_containing, load_module_ast


def test_balanced_component_density_formula_documented() -> None:
    tree = load_module_ast("tools/balanced_density.py")
    required = [
        "P_i = A_i ** 2",
        "exp( - sum(p_i * ln(p_i)) )",
        "diagnostic_low_frequency_residual_not_partial",
        "defined",
    ]
    for token in required:
        assert has_string_literal_containing(tree, token), token
