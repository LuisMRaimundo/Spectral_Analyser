"""
Shared utilities for formula-validation tests.

Each test in this directory uses Python's `ast` module to extract the
symbolic structure of a specific function or expression and asserts that
the structure matches a canonical form documented in
`docs/validation/FORMULA_VALIDATION_STATUS.md`.

These tests complement, not replace, the numerical regression tests
under `tests/phase_*`. They detect symbolic-structure drift that could
escape numerical testing — e.g. a refactored formula that produces the
same outputs on the tested inputs but no longer implements the
documented canonical form.

References
----------
See `docs/validation/FORMULA_VALIDATION_STATUS.md` for the canonical
form of each formula tested in this directory.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module_ast(module_filename: str) -> ast.Module:
    """Parse a top-level repository module into an AST.

    Parameters
    ----------
    module_filename
        File name relative to the repository root (e.g. ``"density.py"``).
    """
    path = REPO_ROOT / module_filename
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path))


def iter_function_defs(tree: ast.AST) -> Iterable[ast.FunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            yield node


def find_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for fn in iter_function_defs(tree):
        if fn.name == name:
            return fn
    raise AssertionError(f"Function {name!r} not found in AST.")


def count_node_type(tree: ast.AST, node_type: type) -> int:
    return sum(1 for n in ast.walk(tree) if isinstance(n, node_type))


def find_calls_by_name(tree: ast.AST, callable_name: str) -> list[ast.Call]:
    """Return every Call node whose callee attribute or name matches callable_name."""
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == callable_name:
                out.append(node)
            elif isinstance(func, ast.Attribute) and func.attr == callable_name:
                out.append(node)
    return out


def has_string_literal_containing(tree: ast.AST, substring: str) -> bool:
    """Detect whether any string literal in the AST contains the given substring."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if substring in node.value:
                return True
    return False
