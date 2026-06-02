#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3 — EWSD integration for ``compiled_density_metrics_research.xlsx``.

Recomputes EWSD-R v18 from per-note ``spectral_analysis.xlsx`` workbooks under the
analysis folder and left-joins scores into ``Spectral_Density_Metrics``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Sequence

import numpy as np
import pandas as pd

from tools.ewsd_core import (
    ACOUSTIC_BALANCE_ALPHA_DEFAULT,
    INDIVIDUAL_SHEETS,
    SCRIPT_VERSION,
    add_acoustic_alignment_columns,
    add_quality_columns,
    compute_ewsd,
    list_excel_sheets,
    read_individual_workbook,
    sort_chromatically_by_octave,
)

__all__ = (
    "EWSD_RESEARCH_SCORE_COLUMNS",
    "EWSD_RESEARCH_PROVENANCE_COLUMNS",
    "compute_ewsd_dataframe_from_analysis_root",
    "discover_individual_exact_workbooks",
    "merge_ewsd_into_spectral_density_metrics",
)

EWSD_RESEARCH_SCORE_COLUMNS: tuple[str, ...] = (
    "EWSD_score_total",
    "EWSD_score_acoustic_balanced",
)

EWSD_RESEARCH_PROVENANCE_COLUMNS: tuple[str, ...] = (
    "ewsd_mode",
    "ewsd_primary_analysis_eligible",
    "ewsd_his_ratio_source",
    "ewsd_H_ratio",
    "ewsd_I_ratio",
    "ewsd_S_noise_ratio",
    "ewsd_weight_function_canonical",
    "ewsd_acoustic_balance_alpha",
    "ewsd_stage3_version",
    "ewsd_merge_status",
)

EWSD_RESEARCH_ALL_COLUMNS: tuple[str, ...] = EWSD_RESEARCH_SCORE_COLUMNS + EWSD_RESEARCH_PROVENANCE_COLUMNS

_SKIP_XLSX_NAMES = frozenset(
    {
        "compiled_density_metrics.xlsx",
        "compiled_density_metrics_research.xlsx",
        "ewsd_ratio_respecting_results.xlsx",
    }
)


def discover_individual_exact_workbooks(analysis_root: Path) -> list[Path]:
    """Return per-note workbooks that contain the full H/I component sheets."""
    root = analysis_root.expanduser().resolve()
    if not root.is_dir():
        return []

    found: list[Path] = []
    seen: set[Path] = set()

    def _maybe_add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        sheets = set(list_excel_sheets(resolved))
        if INDIVIDUAL_SHEETS.issubset(sheets):
            seen.add(resolved)
            found.append(resolved)

    for candidate in root.rglob("spectral_analysis.xlsx"):
        if candidate.name.lower() not in _SKIP_XLSX_NAMES:
            _maybe_add(candidate)

    if not found:
        for candidate in root.rglob("*.xlsx"):
            if candidate.name.lower() in _SKIP_XLSX_NAMES:
                continue
            _maybe_add(candidate)

    return sorted(found, key=lambda p: str(p).lower())


def _first_finite_from_frame(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[float]:
    for col in candidates:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        v = s.dropna()
        if not v.empty and np.isfinite(float(v.iloc[0])):
            return float(v.iloc[0])
    return None


def compute_ewsd_dataframe_from_analysis_root(
    analysis_root: Path,
    *,
    ratio_source: str = "auto_excel_required",
    use_excel_weight_function: bool = True,
    weight_function: str = "auto_from_excel",
    basis: str = "amplitude",
    frequency_ceiling_hz: Optional[float] = None,
    threshold_db_relative: Optional[float] = None,
    aggregate_subbass: bool = True,
    apply_anti_concentration: bool = True,
    acoustic_balance_alpha: float = ACOUSTIC_BALANCE_ALPHA_DEFAULT,
) -> pd.DataFrame:
    """Run EWSD-R v18 on all individual-exact workbooks under ``analysis_root``."""
    workbooks = discover_individual_exact_workbooks(analysis_root)
    rows: list[dict[str, Any]] = []
    for wb_path in workbooks:
        cset = read_individual_workbook(
            wb_path,
            requested_weight_function=weight_function,
            use_excel_weight_function=use_excel_weight_function,
            ratio_source=ratio_source,
            manual_h=None,
            manual_i=None,
            manual_s=None,
            basis=basis,
            frequency_ceiling_hz=frequency_ceiling_hz,
            aggregate_subbass=aggregate_subbass,
        )
        if cset is not None:
            rows.append(compute_ewsd(cset, threshold_db_relative, apply_anti_concentration))

    if not rows:
        return pd.DataFrame()

    result = sort_chromatically_by_octave(pd.DataFrame(rows))
    result = add_acoustic_alignment_columns(
        result,
        frequency_ceiling_hz,
        acoustic_balance_alpha=acoustic_balance_alpha,
    )
    result = add_quality_columns(result)
    if "ewsd_score" in result.columns and "EWSD_score_total" not in result.columns:
        result["EWSD_score_total"] = pd.to_numeric(result["ewsd_score"], errors="coerce")
    return result


def _dedupe_ewsd_by_note(ewsd: pd.DataFrame) -> pd.DataFrame:
    if ewsd.empty or "Note" not in ewsd.columns:
        return ewsd
    out = ewsd.copy()
    out["Note"] = out["Note"].astype(str).str.strip()
    out = out[out["Note"].ne("") & out["Note"].str.lower().ne("nan")]

    mode = out.get("mode", pd.Series("", index=out.index)).astype(str)
    eligible = out.get("primary_analysis_eligible", pd.Series(False, index=out.index)).astype(bool)
    quality = pd.to_numeric(out.get("row_quality_score_0_100"), errors="coerce").fillna(-1.0)

    out["_ewsd_pick_priority"] = (
        eligible.astype(int) * 1000
        + mode.eq("individual_exact").astype(int) * 100
        + quality
    )
    out = out.sort_values(["Note", "_ewsd_pick_priority"], ascending=[True, False], kind="mergesort")
    out = out.drop_duplicates(subset=["Note"], keep="first")
    return out.drop(columns=["_ewsd_pick_priority"], errors="ignore")


def _prepare_ewsd_merge_frame(ewsd: pd.DataFrame) -> pd.DataFrame:
    if ewsd.empty:
        return pd.DataFrame(columns=["Note", *EWSD_RESEARCH_ALL_COLUMNS])

    frame = _dedupe_ewsd_by_note(ewsd)
    merge = pd.DataFrame({"Note": frame["Note"].astype(str).str.strip()})
    merge["EWSD_score_total"] = pd.to_numeric(frame.get("ewsd_score"), errors="coerce")
    merge["EWSD_score_acoustic_balanced"] = pd.to_numeric(
        frame.get("ewsd_score_acoustic_balanced"), errors="coerce"
    )
    merge["ewsd_mode"] = frame.get("mode", pd.Series(np.nan, index=frame.index)).astype(str)
    merge["ewsd_primary_analysis_eligible"] = frame.get(
        "primary_analysis_eligible", pd.Series(False, index=frame.index)
    ).astype(bool)
    merge["ewsd_his_ratio_source"] = frame.get("his_ratio_source", np.nan)
    merge["ewsd_H_ratio"] = pd.to_numeric(frame.get("analysis_ratio_weight_harmonic"), errors="coerce")
    merge["ewsd_I_ratio"] = pd.to_numeric(
        frame.get("analysis_ratio_weight_nonharmonic_residual"), errors="coerce"
    )
    merge["ewsd_S_noise_ratio"] = pd.to_numeric(
        frame.get("analysis_ratio_weight_noise_subbass"), errors="coerce"
    )
    merge["ewsd_weight_function_canonical"] = frame.get("weight_function_canonical", np.nan)
    merge["ewsd_acoustic_balance_alpha"] = pd.to_numeric(
        frame.get("ewsd_acoustic_balance_alpha"), errors="coerce"
    ).fillna(ACOUSTIC_BALANCE_ALPHA_DEFAULT)
    merge["ewsd_stage3_version"] = SCRIPT_VERSION
    merge["ewsd_merge_status"] = np.where(
        merge["ewsd_mode"].eq("individual_exact"),
        "merged_individual_exact",
        "merged_non_exact_mode",
    )
    return merge


def _init_empty_ewsd_columns(sd: pd.DataFrame, status: str) -> pd.DataFrame:
    out = sd.copy()
    for col in EWSD_RESEARCH_ALL_COLUMNS:
        if col not in out.columns:
            if col == "ewsd_primary_analysis_eligible":
                out[col] = False
            elif col == "ewsd_stage3_version":
                out[col] = SCRIPT_VERSION
            elif col == "ewsd_acoustic_balance_alpha":
                out[col] = ACOUSTIC_BALANCE_ALPHA_DEFAULT
            else:
                out[col] = np.nan
    out["ewsd_merge_status"] = status
    return out


def merge_ewsd_into_spectral_density_metrics(
    sd: pd.DataFrame,
    merged: pd.DataFrame,
    compiled_workbook: Path,
    warnings: List[str],
    *,
    include_ewsd: bool = True,
    acoustic_balance_alpha: float = ACOUSTIC_BALANCE_ALPHA_DEFAULT,
) -> pd.DataFrame:
    """
    Left-join EWSD scores and provenance columns into ``Spectral_Density_Metrics``.

    EWSD is recomputed from per-note Excel under ``compiled_workbook.parent``.
    """
    if not include_ewsd or sd is None or sd.empty or "Note" not in sd.columns:
        return sd

    analysis_root = Path(compiled_workbook).expanduser().resolve().parent
    freq_ceiling = _first_finite_from_frame(
        sd if "density_frequency_ceiling_hz" in sd.columns else merged,
        ("density_frequency_ceiling_hz",),
    )
    if freq_ceiling is None:
        freq_ceiling = _first_finite_from_frame(
            merged,
            ("density_frequency_ceiling_hz", "density_frequency_ceiling"),
        )

    try:
        ewsd_raw = compute_ewsd_dataframe_from_analysis_root(
            analysis_root,
            frequency_ceiling_hz=freq_ceiling,
            acoustic_balance_alpha=acoustic_balance_alpha,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Stage 3 EWSD computation failed: {exc}")
        return _init_empty_ewsd_columns(sd, "ewsd_computation_failed")

    if ewsd_raw.empty:
        warnings.append(
            "Stage 3 EWSD skipped: no per-note workbooks with Harmonic Spectrum + "
            "Inharmonic Spectrum found under analysis folder."
        )
        return _init_empty_ewsd_columns(sd, "no_per_note_workbooks_found")

    ewsd_merge = _prepare_ewsd_merge_frame(ewsd_raw)
    out = sd.copy()
    out["Note"] = out["Note"].astype(str).str.strip()

    for col in EWSD_RESEARCH_ALL_COLUMNS:
        if col in out.columns:
            out = out.drop(columns=[col])

    out = out.merge(ewsd_merge, on="Note", how="left", validate="m:1")
    missing = out["EWSD_score_total"].isna()
    out.loc[missing, "ewsd_merge_status"] = "note_not_in_ewsd_output"

    n_merged = int((~missing).sum())
    n_eligible = int(out.get("ewsd_primary_analysis_eligible", pd.Series(False)).astype(bool).sum())
    warnings.append(
        f"Stage 3 EWSD merged {n_merged}/{len(out)} notes from {len(discover_individual_exact_workbooks(analysis_root))} "
        f"per-note workbook(s); {n_eligible} row(s) ewsd_primary_analysis_eligible=True."
    )
    return out
