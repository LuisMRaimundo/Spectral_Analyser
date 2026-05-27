"""
Formula validation: canonical H/I/S weighted density formula.

Canonical form (see docs/validation/FORMULA_VALIDATION_STATUS.md, F1):

    density_metric_raw = D_H * w_H + D_I * w_I + D_S * w_S

This test asserts that the canonical formula string declared in
metric_contract.py is structurally consistent with the documented form.
"""

from __future__ import annotations

import re

from .conftest import has_string_literal_containing, load_module_ast


def test_density_formula_string_present_in_metric_contract() -> None:
    tree = load_module_ast("metric_contract.py")
    # The canonical formula string should be declared verbatim somewhere in metric_contract.py.
    # Accept either the compact form or a structurally equivalent form with spaces.
    candidates = [
        "D_H*w_H + D_I*w_I + D_S*w_S",
        "D_H * w_H + D_I * w_I + D_S * w_S",
    ]
    assert any(has_string_literal_containing(tree, c) for c in candidates), (
        "metric_contract.py must declare the canonical density formula string. "
        "Expected one of: " + ", ".join(repr(c) for c in candidates)
    )


def test_density_formula_has_three_terms() -> None:
    tree = load_module_ast("metric_contract.py")
    # Locate any string literal containing 'D_H' and 'w_H'; verify it has three additive terms.
    found = False
    for c in (
        "D_H*w_H + D_I*w_I + D_S*w_S",
        "D_H * w_H + D_I * w_I + D_S * w_S",
    ):
        if has_string_literal_containing(tree, c):
            terms = re.split(r"\s*\+\s*", c)
            assert len(terms) == 3, "Canonical density formula must have exactly three additive terms."
            found = True
    assert found, "Canonical density formula string not found in metric_contract.py."
