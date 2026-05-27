"""
Formula validation: effective partial density (participation ratio /
inverse Herfindahl).

Canonical form (see docs/validation/FORMULA_VALIDATION_STATUS.md, F5):

    D_eff = (sum_i P_i)^2 / sum_i(P_i^2)

This test asserts that the canonical form is documented in density.py
or in a module-level constant that documents the canonical formula.
"""

from __future__ import annotations

from .conftest import has_string_literal_containing, load_module_ast


def test_effective_partial_density_formula_documented() -> None:
    tree = load_module_ast("density.py")
    candidates = [
        "(sum_i P_i)^2 / sum_i(P_i^2)",
        "(sum_i P_i)**2 / sum_i(P_i**2)",
        "(Σ P_i)^2 / Σ(P_i^2)",
        "participation ratio",
        "inverse Herfindahl",
        "Herfindahl inverse",
    ]
    assert any(has_string_literal_containing(tree, c) for c in candidates), (
        "density.py must document the canonical effective_partial_density formula "
        "either as the literal expression or by the standard name "
        "(participation ratio / inverse Herfindahl)."
    )
