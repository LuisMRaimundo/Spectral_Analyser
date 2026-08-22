"""Per-column formula_id / formula_version stamps.

F-048 / F-049 already carried formula IDs. MIR descriptors did not, and
three incompatible F-037 generations shipped under package 4.4.0.
Every exported column now has a stamp. Bump a column's
``formula_version`` when its arithmetic changes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

PACKAGE_FORMULA_VERSION = "4.5.0"
DISSONANCE_FORMULA_VERSION = "4.6.0"
SPECTRAL_MASS_FORMULA_VERSION = "1.0"

MIR_VALUE_COLUMNS: Tuple[str, ...] = (
    "spectral_centroid_hz",
    "spectral_spread_hz",
    "spectral_skewness",
    "spectral_kurtosis",
    "spectral_irregularity",
    "tristimulus_1_fundamental",
    "tristimulus_2_low_harmonics_2_to_4",
    "tristimulus_3_high_harmonics_5_plus",
    "spectral_flatness",
    "spectral_rolloff_hz_85",
    "spectral_rolloff_hz_95",
    "roughness_parncutt_kernel",
    "roughness_aures_1985",
    "roughness_pairs_excluded_above_validity",
    "erb_weighted_spectral_density",
)

MIR_STAMPS: Dict[str, Tuple[str, str]] = {
    "spectral_centroid_hz": ("F-027", PACKAGE_FORMULA_VERSION),
    "spectral_spread_hz": ("F-028", PACKAGE_FORMULA_VERSION),
    "spectral_skewness": ("F-029", PACKAGE_FORMULA_VERSION),
    "spectral_kurtosis": ("F-030", PACKAGE_FORMULA_VERSION),
    "spectral_irregularity": ("F-031", PACKAGE_FORMULA_VERSION),
    "tristimulus_1_fundamental": ("F-032", PACKAGE_FORMULA_VERSION),
    "tristimulus_2_low_harmonics_2_to_4": ("F-033", PACKAGE_FORMULA_VERSION),
    "tristimulus_3_high_harmonics_5_plus": ("F-034", PACKAGE_FORMULA_VERSION),
    "spectral_flatness": ("F-035", PACKAGE_FORMULA_VERSION),
    "spectral_rolloff_hz_85": ("F-036", PACKAGE_FORMULA_VERSION),
    "spectral_rolloff_hz_95": ("F-036", PACKAGE_FORMULA_VERSION),
    "roughness_parncutt_kernel": ("F-037", PACKAGE_FORMULA_VERSION),
    "roughness_aures_1985": ("F-037", PACKAGE_FORMULA_VERSION),
    "roughness_pairs_excluded_above_validity": ("F-037", PACKAGE_FORMULA_VERSION),
    "erb_weighted_spectral_density": ("F-039", PACKAGE_FORMULA_VERSION),
}

DISSONANCE_VALUE_COLUMNS: Tuple[str, ...] = (
    "sethares_dissonance",
    "hutchinson_knopoff_dissonance",
    "vassilakis_dissonance",
    "hutchinson_knopoff_legacy_mean_pair_scaled",
    "selected_dissonance_value",
    "dissonance_metric_mode",
)

DISSONANCE_STAMPS: Dict[str, Tuple[str, str]] = {
    "sethares_dissonance": ("COL:sethares_dissonance", DISSONANCE_FORMULA_VERSION),
    "hutchinson_knopoff_dissonance": (
        "COL:hutchinson_knopoff_dissonance",
        DISSONANCE_FORMULA_VERSION,
    ),
    "vassilakis_dissonance": ("COL:vassilakis_dissonance", DISSONANCE_FORMULA_VERSION),
    "hutchinson_knopoff_legacy_mean_pair_scaled": (
        "COL:hutchinson_knopoff_legacy_mean_pair_scaled",
        DISSONANCE_FORMULA_VERSION,
    ),
    "selected_dissonance_value": (
        "COL:selected_dissonance_value",
        DISSONANCE_FORMULA_VERSION,
    ),
    "dissonance_metric_mode": ("COL:dissonance_metric_mode", DISSONANCE_FORMULA_VERSION),
}

SPECTRAL_MASS_VALUE_COLUMNS: Tuple[str, ...] = (
    "spectral_mass",
    "spectral_mass_count",
    "spectral_mass_count_blend",
    "spectral_mass_level_exponent",
)

SPECTRAL_MASS_STAMPS: Dict[str, Tuple[str, str]] = {
    "spectral_mass": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
    "spectral_mass_count": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
    "spectral_mass_count_blend": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
    "spectral_mass_level_exponent": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
}

_INDEX_ROW = re.compile(
    r"^\|\s*(F-\d+)\s*\|.*?\| `([^`]+)`\s*\|",
    re.MULTILINE,
)
_ROOT = Path(__file__).resolve().parent


def mir_stamp_fields() -> Dict[str, str]:
    """Companion export fields for every MIR value column."""
    out: Dict[str, str] = {}
    for col, (fid, ver) in MIR_STAMPS.items():
        out[f"{col}_formula_id"] = fid
        out[f"{col}_formula_version"] = ver
    return out


def dissonance_stamp_fields() -> Dict[str, str]:
    """Companion export fields for dissonance value columns."""
    out: Dict[str, str] = {}
    for col, (fid, ver) in DISSONANCE_STAMPS.items():
        out[f"{col}_formula_id"] = fid
        out[f"{col}_formula_version"] = ver
    return out


def _index_column_map() -> Dict[str, str]:
    text = (_ROOT / "docs" / "METRIC_FORMULA_INDEX.md").read_text(encoding="utf-8")
    mapping: Dict[str, str] = {}
    for fid, cols in _INDEX_ROW.findall(text):
        for col in re.split(r"[,/]| and ", cols):
            name = col.strip().strip("`")
            if name and not name.startswith("*"):
                mapping.setdefault(name, fid)
    return mapping


def _contract_stamps() -> Dict[str, Tuple[str, str]]:
    from metric_contract import build_metric_contracts

    out: Dict[str, Tuple[str, str]] = {}
    for name, definition in build_metric_contracts().items():
        fid = str(getattr(definition, "formula_id", "") or "").strip()
        ver = str(getattr(definition, "formula_version", "") or "").strip()
        if not fid:
            found = re.findall(r"F-\d+", definition.formula)
            fid = found[0] if found else f"COL:{name}"
        if not ver:
            ver = PACKAGE_FORMULA_VERSION
        out[name] = (fid, ver)
    return out


def exported_column_names() -> List[str]:
    from compile_metrics import DENSITY_METRICS_MAIN_COLUMNS, PHASE5_ALL_DESCRIPTOR_COLUMNS

    names = list(DENSITY_METRICS_MAIN_COLUMNS)
    for col in PHASE5_ALL_DESCRIPTOR_COLUMNS:
        if col not in names:
            names.append(col)
    for col in MIR_VALUE_COLUMNS:
        if col not in names:
            names.append(col)
        names.append(f"{col}_formula_id")
        names.append(f"{col}_formula_version")
    for col in DISSONANCE_VALUE_COLUMNS:
        if col not in names:
            names.append(col)
        names.append(f"{col}_formula_id")
        names.append(f"{col}_formula_version")
    for col in SPECTRAL_MASS_VALUE_COLUMNS:
        if col not in names:
            names.append(col)
    names.append("spectral_mass_formula_id")
    names.append("spectral_mass_formula_version")
    return names


def column_stamp(column: str) -> Tuple[str, str]:
    if column in MIR_STAMPS:
        return MIR_STAMPS[column]
    if column in DISSONANCE_STAMPS:
        return DISSONANCE_STAMPS[column]
    if column in SPECTRAL_MASS_STAMPS:
        return SPECTRAL_MASS_STAMPS[column]
    if column.endswith("_formula_id"):
        return ("META", PACKAGE_FORMULA_VERSION)
    if column.endswith("_formula_version"):
        return ("META", PACKAGE_FORMULA_VERSION)
    contracts = _contract_stamps()
    if column in contracts:
        return contracts[column]
    index = _index_column_map()
    if column in index:
        return (index[column], PACKAGE_FORMULA_VERSION)
    return (f"COL:{column}", PACKAGE_FORMULA_VERSION)


def build_column_registry() -> Dict[str, Dict[str, str]]:
    registry: Dict[str, Dict[str, str]] = {}
    for col in exported_column_names():
        fid, ver = column_stamp(col)
        registry[col] = {"formula_id": fid, "formula_version": ver}
    return registry


def write_audit_markdown(path: Path | None = None) -> Path:
    registry = build_column_registry()
    dest = path or (_ROOT / "docs" / "validation" / "COLUMN_VERSIONING_AUDIT.md")
    lacked = [
        name
        for name, row in registry.items()
        if row["formula_id"].startswith("COL:")
    ]
    lines = [
        "# Column formula-version audit",
        "",
        f"Package formula-version generation: **{PACKAGE_FORMULA_VERSION}**.",
        "Before this generation, only a few fields (`density_formula_version`,",
        "`obs_w_formula_version`, EWSD/ACD formula-ID strings) carried a",
        "per-column version. MIR descriptors, including three incompatible",
        "F-037 kernels, shipped under `package_version=4.4.0` with no",
        "per-column stamp.",
        "",
        f"- Exported columns inventoried: **{len(registry)}**",
        f"- Columns that lacked a contracted F-id (first-stamped as `COL:<name>`): "
        f"**{len(lacked)}**",
        "- MIR value columns now export `<name>_formula_id` and",
        "  `<name>_formula_version` from `metric_contract` / `MIR_STAMPS`.",
        "- CI: `tests/phase_33/test_column_formula_versions.py` fails if any",
        "  compiled/MIR export column is missing a non-empty stamp.",
        "",
        "A `COL:<name>` id is a first-generation stamp, not a claim that the",
        "column has a numbered formula in `METRIC_FORMULA_INDEX.md`. Bump",
        "`formula_version` when that column's arithmetic changes.",
        "",
        "## Registry",
        "",
        "| Column | formula_id | formula_version |",
        "|---|---|---|",
    ]
    for name in sorted(registry):
        row = registry[name]
        lines.append(
            f"| `{name}` | `{row['formula_id']}` | `{row['formula_version']}` |"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sidecar = dest.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {"package_formula_version": PACKAGE_FORMULA_VERSION, "columns": registry},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest
