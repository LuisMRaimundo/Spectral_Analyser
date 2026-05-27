"""
Formula validation: sub-bass upper bound (Zwicker & Fastl 1990).

Canonical form (see docs/validation/FORMULA_VALIDATION_STATUS.md, F4):

    upper_bound_hz = min(f0_hz * 0.5, 80.0)

This test asserts that SubBassPolicy.upper_bound_hz implements exactly
this formula.
"""

from __future__ import annotations

import ast

from .conftest import find_calls_by_name, load_module_ast


def test_subbass_policy_uses_min_of_half_f0_and_80() -> None:
    tree = load_module_ast("subbass_policy.py")
    # Locate the min(...) call inside the module.
    min_calls = find_calls_by_name(tree, "min")
    assert min_calls, "subbass_policy.py must contain a min(...) call."
    matched = False
    for call in min_calls:
        if len(call.args) != 2:
            continue
        a, b = call.args
        a_src = ast.unparse(a)
        b_src = ast.unparse(b)
        has_half = ("0.5" in a_src and "f0" in a_src) or ("0.5" in b_src and "f0" in b_src)
        has_eighty = "80.0" in a_src or "80.0" in b_src or "80" in a_src or "80" in b_src
        if has_half and has_eighty:
            matched = True
            break
    assert matched, (
        "SubBassPolicy.upper_bound_hz must compute min(f0 * 0.5, 80.0) — "
        "canonical form per Zwicker & Fastl (1990) intersection with sub-fundamental guard."
    )
