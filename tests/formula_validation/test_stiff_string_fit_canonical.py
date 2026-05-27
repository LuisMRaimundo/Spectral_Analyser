"""
Formula validation: stiff-string inharmonicity fit (Fletcher 1962).

Canonical form (see docs/validation/FORMULA_VALIDATION_STATUS.md, F3):

    f_n = n * f0 * sqrt(1 + B * n^2)

This test asserts that the implementation in inharmonicity_model.py
contains the canonical structural elements: a square root, a quadratic
term in n (n^2 or n*n), and an addition of 1 inside the square root.
"""

from __future__ import annotations

import ast

from .conftest import find_calls_by_name, find_function, load_module_ast


def test_stiff_string_fit_uses_sqrt() -> None:
    tree = load_module_ast("inharmonicity_model.py")
    fn = find_function(tree, "fit_inharmonicity_coefficient")
    sqrt_calls = find_calls_by_name(fn, "sqrt")
    assert sqrt_calls, "fit_inharmonicity_coefficient must contain a sqrt(...) call."


def test_stiff_string_fit_has_quadratic_n_term() -> None:
    tree = load_module_ast("inharmonicity_model.py")
    fn = find_function(tree, "fit_inharmonicity_coefficient")
    src = ast.unparse(fn)
    # Accept either explicit power (n**2, n^2 is not Python) or multiplicative form (n * n) or numpy power.
    quadratic_indicators = ["n ** 2", "n**2", "n * n", "n*n", "obs_n * obs_n", "obs_n**2", "n2 *", "n2 ="]
    assert any(ind in src for ind in quadratic_indicators), (
        "fit_inharmonicity_coefficient must contain a quadratic-in-n term "
        "(n**2, n*n, or equivalent)."
    )


def test_stiff_string_fit_has_unit_offset_inside_sqrt() -> None:
    tree = load_module_ast("inharmonicity_model.py")
    fn = find_function(tree, "fit_inharmonicity_coefficient")
    sqrt_calls = find_calls_by_name(fn, "sqrt")
    # At least one sqrt call should contain a "+ 1" or "1 +" inside its argument expression.
    any_offset = False
    for call in sqrt_calls:
        if not call.args:
            continue
        src = ast.unparse(call.args[0])
        if "1 +" in src or "+ 1" in src or "1.0 +" in src or "+ 1.0" in src:
            any_offset = True
            break
    assert any_offset, (
        "fit_inharmonicity_coefficient: at least one sqrt(...) call must contain '1 + ...' "
        "inside its argument (the canonical 1 + B*n^2 term)."
    )
