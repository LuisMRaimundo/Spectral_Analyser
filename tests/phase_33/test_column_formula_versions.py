"""CI gate: every exported column ships with a formula stamp."""
from __future__ import annotations

import json
from pathlib import Path

from metric_formula_versions import (
    PACKAGE_FORMULA_VERSION,
    SURFACE_CLASSES,
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


def test_every_exported_column_has_surface_class() -> None:
    registry = build_column_registry()
    missing = [c for c, row in registry.items() if row.get("class") not in SURFACE_CLASSES]
    assert not missing
    payload = json.loads(
        (Path(__file__).resolve().parents[2] / "metrics_dictionary.json").read_text(
            encoding="utf-8"
        )
    )
    surface = payload["column_surface"]
    assert set(surface) == set(registry)
    for name, row in surface.items():
        assert row["class"] == registry[name]["class"]
