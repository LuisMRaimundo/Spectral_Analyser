"""CI gate: every exported column ships with a formula stamp."""
from __future__ import annotations

from metric_formula_versions import (
    PACKAGE_FORMULA_VERSION,
    build_column_registry,
    exported_column_names,
    mir_stamp_fields,
)


def test_every_exported_column_has_formula_stamp() -> None:
    registry = build_column_registry()
    missing = [c for c in exported_column_names() if c not in registry]
    assert not missing, f"export columns missing from formula registry: {missing}"
    blank = [
        c
        for c, row in registry.items()
        if not row.get("formula_id") or not row.get("formula_version")
    ]
    assert not blank, f"export columns with empty formula stamp: {blank}"


def test_mir_stamps_are_f_ids_at_package_version() -> None:
    stamps = mir_stamp_fields()
    assert stamps["roughness_parncutt_kernel_formula_id"] == "F-037"
    assert stamps["roughness_parncutt_kernel_formula_version"] == PACKAGE_FORMULA_VERSION
    assert PACKAGE_FORMULA_VERSION == "4.5.0"


def test_new_column_without_stamp_is_rejected() -> None:
    """The gate is the completeness of exported_column_names vs registry."""
    names = set(exported_column_names())
    registry = build_column_registry()
    assert names <= set(registry)
