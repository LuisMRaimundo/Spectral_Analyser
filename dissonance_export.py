"""
Canonical dissonance export helpers (separate from density / effective_partial_density).

Maps legacy Excel / in-memory column names to stable snake_case fields used on
``Dissonance_Metrics`` and related sheets.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from dissonance_models import list_available_models

MODEL_SLUGS: Tuple[str, ...] = tuple(list_available_models())

CANONICAL_VALUE_BY_SLUG: Dict[str, str] = {
    "sethares": "sethares_dissonance",
    "hutchinson-knopoff": "hutchinson_knopoff_dissonance",
    "vassilakis": "vassilakis_dissonance",
}

OPTIONAL_EXTRA_FIELDS: Tuple[str, ...] = (
    "pairwise_dissonance",
    "total_dissonance",
    "mean_dissonance_per_pair",
    "dissonance_partial_count",
    "dissonance_pair_count",
)

# Copied onto ``Dissonance_Metrics`` as audit columns when present on the compiled frame.
DISSONANCE_AUDIT_COPY_COLUMNS: Tuple[str, ...] = (
    "dissonance_partial_cap",
    "dissonance_partial_count_before_cap",
    "dissonance_partial_count_after_cap",
    "dissonance_pair_count_after_cap",
    "dissonance_cap_computation_note",
)


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").strip().lower()).strip()


def legacy_column_to_model_slug(column: str) -> Optional[str]:
    """
    Map a legacy column label to a model slug in MODEL_SLUGS, or None if not a model scalar.
    """
    raw = str(column).strip()
    rlow = raw.lower()
    for extra in OPTIONAL_EXTRA_FIELDS:
        if rlow == extra.lower():
            return None

    if rlow == "sethares_dissonance":
        return "sethares"
    if rlow == "hutchinson_knopoff_dissonance":
        return "hutchinson-knopoff"
    if rlow == "vassilakis_dissonance":
        return "vassilakis"

    n = _norm_key(raw)
    if "dissonance" not in n:
        return None

    if "sethares" in n:
        return "sethares"
    if "vassilakis" in n:
        return "vassilakis"
    if "hutchinson" in n and "knopoff" in n:
        return "hutchinson-knopoff"
    if "hutchinson-knopoff" in raw.lower().replace(" ", ""):
        return "hutchinson-knopoff"
    return None


def _slug_from_selected_model_label(label: str) -> Optional[str]:
    t = (label or "").strip().lower()
    for s in MODEL_SLUGS:
        if t == s or t.replace("_", "-") == s:
            return s
    if "sethares" in t:
        return "sethares"
    if "vassilakis" in t:
        return "vassilakis"
    if "hutchinson" in t and "knopoff" in t:
        return "hutchinson-knopoff"
    return None


def collect_dissonance_scalar_columns(df: pd.DataFrame) -> List[str]:
    """Column names in df that carry per-note scalar dissonance for at least one model."""
    out: List[str] = []
    for c in df.columns:
        if legacy_column_to_model_slug(str(c)) is not None:
            out.append(str(c))
    return out


def infer_dissonance_compare_from_frame(df: pd.DataFrame) -> bool:
    """True if two or more model-specific dissonance columns have any non-null numeric values."""
    d, _ = build_canonical_dissonance_frame(df)
    if d.empty:
        return False
    hits = 0
    for slug in MODEL_SLUGS:
        k = CANONICAL_VALUE_BY_SLUG[slug]
        if k not in d.columns:
            continue
        if pd.to_numeric(d[k], errors="coerce").notna().any():
            hits += 1
    return hits >= 2


def build_canonical_dissonance_frame(
    base_df: pd.DataFrame,
    *,
    selected_model: Optional[str] = None,
    dissonance_enabled: Optional[bool] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Build one row per input row with canonical dissonance columns.

    Returns (dissonance_metrics_df, audit dict with available_models list etc.).
    """
    if base_df is None or base_df.empty or "Note" not in base_df.columns:
        return pd.DataFrame(), {"available_dissonance_models": [], "has_numeric_dissonance": False}

    rows: List[Dict[str, Any]] = []
    available: set[str] = set()

    for _, row in base_df.iterrows():
        out: Dict[str, Any] = {"Note": row["Note"]}
        for col in base_df.columns:
            if col == "Note":
                continue
            cl = str(col)
            slug = legacy_column_to_model_slug(cl)
            if slug:
                key = CANONICAL_VALUE_BY_SLUG[slug]
                val = pd.to_numeric(row[col], errors="coerce")
                if pd.notna(val):
                    out[key] = float(val)
                    available.add(slug)
                continue
            clow = cl.lower()
            matched_extra = False
            for extra in OPTIONAL_EXTRA_FIELDS:
                if clow == extra.lower() or _norm_key(cl) == _norm_key(extra):
                    v = pd.to_numeric(row[col], errors="coerce")
                    if pd.notna(v):
                        out[extra] = float(v)
                    matched_extra = True
                    break
            if matched_extra:
                continue

        sel = selected_model
        if sel is None and "selected_dissonance_model" in base_df.columns:
            v = row.get("selected_dissonance_model")
            if pd.notna(v) and str(v).strip():
                sel = str(v).strip()
        if sel is None and "dissonance_model" in base_df.columns:
            v = row.get("dissonance_model")
            if pd.notna(v) and str(v).strip():
                sel = str(v).strip()

        slug_sel = _slug_from_selected_model_label(sel) if sel else None
        if slug_sel:
            out["selected_dissonance_model"] = slug_sel
            canon = CANONICAL_VALUE_BY_SLUG.get(slug_sel)
            if canon and canon in out:
                out["selected_dissonance_value"] = out[canon]
            else:
                # Try legacy column on same row
                for c in base_df.columns:
                    if legacy_column_to_model_slug(str(c)) == slug_sel:
                        v = pd.to_numeric(row[c], errors="coerce")
                        if pd.notna(v):
                            out["selected_dissonance_value"] = float(v)
                            break

        for audit_k in DISSONANCE_AUDIT_COPY_COLUMNS:
            if audit_k not in base_df.columns:
                continue
            v = row.get(audit_k)
            if pd.notna(v) or (isinstance(v, str) and v.strip() != ""):
                out[audit_k] = v

        rows.append(out)

    diss_df = pd.DataFrame(rows)
    has_numeric = False
    for slug in MODEL_SLUGS:
        k = CANONICAL_VALUE_BY_SLUG[slug]
        if k in diss_df.columns and pd.to_numeric(diss_df[k], errors="coerce").notna().any():
            has_numeric = True
            break
    for extra in OPTIONAL_EXTRA_FIELDS:
        if extra in diss_df.columns and pd.to_numeric(diss_df[extra], errors="coerce").notna().any():
            has_numeric = True
            break

    audit = {
        "available_dissonance_models": sorted(available),
        "has_numeric_dissonance": bool(has_numeric),
        "dissonance_enabled_inferred": bool(dissonance_enabled)
        if dissonance_enabled is not None
        else bool(has_numeric),
    }
    return diss_df, audit


def build_dissonance_model_comparison_long(diss_df: pd.DataFrame) -> pd.DataFrame:
    """Long-format comparison: Note, Model, Dissonance_Value."""
    long_rows: List[Dict[str, Any]] = []
    for _, row in diss_df.iterrows():
        note = row.get("Note")
        for slug in MODEL_SLUGS:
            key = CANONICAL_VALUE_BY_SLUG[slug]
            if key not in row.index:
                continue
            v = pd.to_numeric(row[key], errors="coerce")
            if pd.isna(v):
                continue
            long_rows.append(
                {
                    "Note": note,
                    "Model": slug,
                    "Dissonance_Value": float(v),
                }
            )
    return pd.DataFrame(long_rows)


def build_dissonance_correlation_matrix(
    diss_df: pd.DataFrame,
    *,
    min_samples: int = 10,
) -> Optional[pd.DataFrame]:
    """Pairwise correlation matrix between canonical model columns (wide), if enough samples."""
    cols = [CANONICAL_VALUE_BY_SLUG[s] for s in MODEL_SLUGS if CANONICAL_VALUE_BY_SLUG[s] in diss_df.columns]
    if len(cols) < 2:
        return None
    X = diss_df[cols].apply(pd.to_numeric, errors="coerce")
    if len(X) < int(min_samples):
        return None
    usable: List[str] = []
    for c in cols:
        if int(X[c].notna().sum()) < int(min_samples):
            continue
        if float(X[c].std(skipna=True) or 0.0) <= 1e-15:
            continue
        usable.append(c)
    if len(usable) < 2:
        return None
    return X[usable].corr()


def dissonance_columns_present_in_density_sheet(density_df: pd.DataFrame) -> List[str]:
    """Return any dissonance-like column names erroneously present on Density_Metrics."""
    bad: List[str] = []
    for c in density_df.columns:
        n = str(c).lower()
        if "dissonance" in n:
            bad.append(str(c))
    return bad
