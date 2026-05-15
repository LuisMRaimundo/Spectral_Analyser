# -*- coding: utf-8 -*-
"""Debug_Counts invariant validation — semantic hardening only (no clamping)."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import pandas as pd

DEBUG_COUNTS_SEMANTICS = (
    "hierarchical residual counts are separate from independent peaklist window counts"
)
DEBUG_COUNTS_SOURCE_POLICY = (
    "hierarchical_counts_derived_from_same_residual_pipeline; peaklist_counts_kept_separately"
)


def len_or_none(df: Any) -> Optional[int]:
    """Return ``len(df)`` as int, or ``None`` if ``df`` is missing or not sized."""
    if df is None:
        return None
    try:
        return int(len(df))
    except Exception:
        return None


def _as_int_count(x: Any) -> Optional[int]:
    if x is None:
        return None
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        if pd.isna(x):
            return None
        return int(x)
    except Exception:
        try:
            if pd.isna(x):
                return None
        except Exception:
            pass
        return None


def validate_debug_count_invariants(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Debug_Counts hierarchy for residual-pipeline fields.

    Does not repair by clamping. On failure, sets ``debug_counts_invariant_status``
    to ``failed`` and lists reasons in ``debug_counts_invariant_failures``.
    """
    residual = _as_int_count(row.get("residual_spectral_row_count"))
    candidate = _as_int_count(row.get("nonharmonic_candidate_row_count"))
    retained = _as_int_count(row.get("retained_nonharmonic_peak_candidate_count"))
    exported = _as_int_count(row.get("exported_nonharmonic_peak_candidate_count"))
    acc_peak = _as_int_count(row.get("accepted_inharmonic_peak_count"))
    acc_partial = _as_int_count(row.get("accepted_inharmonic_partial_count"))

    failures: list[str] = []

    if residual is not None and candidate is not None and candidate > residual:
        failures.append("nonharmonic_candidate_row_count_exceeds_residual_spectral_row_count")

    if candidate is not None and retained is not None and retained > candidate:
        failures.append("retained_nonharmonic_peak_candidate_count_exceeds_nonharmonic_candidate_row_count")

    if retained is not None and exported is not None and exported != retained:
        failures.append("exported_nonharmonic_peak_candidate_count_differs_from_retained_count")

    if retained is not None and acc_peak is not None and acc_peak > retained:
        failures.append("accepted_inharmonic_peak_count_exceeds_retained_nonharmonic_peak_candidate_count")

    if acc_peak is not None and acc_partial is not None and acc_partial > acc_peak:
        failures.append("accepted_inharmonic_partial_count_exceeds_accepted_inharmonic_peak_count")

    if failures:
        row["debug_counts_invariant_status"] = "failed"
        row["debug_counts_invariant_failures"] = ";".join(failures)
    else:
        row["debug_counts_invariant_status"] = "passed"
        row["debug_counts_invariant_failures"] = ""

    row["debug_counts_semantics"] = DEBUG_COUNTS_SEMANTICS
    row["debug_counts_source_policy"] = DEBUG_COUNTS_SOURCE_POLICY
    return row
