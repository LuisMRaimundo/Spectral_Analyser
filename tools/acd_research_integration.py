#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3 — ACD integration for ``compiled_density_metrics_research.xlsx``.

Recomputes Auditory Component Density (ACD v1.0) from per-note
``spectral_analysis.xlsx`` workbooks. Ratios are derived from compartment
energy, not from Excel H/I/S columns. Sub-bass is not aggregated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

import numpy as np
import pandas as pd

from tools.acd_stage3_contract import (
    STAGE3_ACD_STATUS_OK,
    AcdStage3MergeResult,
    assess_acd_merge_result,
    build_acd_diagnostics,
    enforce_acd_fail_closed,
)
from tools.ewsd_core import (
    INDIVIDUAL_SHEETS,
    file_sha256,
    infer_note_from_filename,
    list_excel_sheets,
    read_first_row_as_dict,
    standardise_component_table,
)
from tools.ewsd_research_integration import discover_individual_exact_workbooks
from tools.spectral_density_hill import (
    ERB_FRACTION_DEFAULT,
    MODULE_REVISION,
    compute_density_compartment,
    compute_note_density,
)

ACD_RESEARCH_SCORE_COLUMNS: tuple[str, ...] = (
    "ACD_score",
    "ACD_magnitude_per_component",
    "ACD_D0",
    "ACD_D1",
    "ACD_D2",
    "ACD_Dinf",
    "ACD_evenness_D2_over_D0",
)

ACD_RESEARCH_RATIO_COLUMNS: tuple[str, ...] = (
    "ACD_r_harmonic",
    "ACD_r_inharmonic",
    "ACD_r_subbass",
    "ACD_D2_harmonic",
    "ACD_D2_inharmonic",
    "ACD_D2_subbass",
)

ACD_RESEARCH_COUNT_COLUMNS: tuple[str, ...] = (
    "ACD_count_raw_harmonic",
    "ACD_count_raw_inharmonic",
    "ACD_count_raw_subbass",
    "ACD_count_merged_harmonic",
    "ACD_count_merged_inharmonic",
    "ACD_count_merged_subbass",
)

ACD_RESEARCH_PROVENANCE_COLUMNS: tuple[str, ...] = (
    "ACD_erb_fraction",
    "ACD_include_for_density_applied",
    "ACD_status",
    "ACD_version",
    "acd_merge_status",
)

ACD_RESEARCH_ALL_COLUMNS: tuple[str, ...] = (
    ACD_RESEARCH_SCORE_COLUMNS
    + ACD_RESEARCH_RATIO_COLUMNS
    + ACD_RESEARCH_COUNT_COLUMNS
    + ACD_RESEARCH_PROVENANCE_COLUMNS
)

_FAMILY_SHEETS = (
    ("harmonic", "Harmonic Spectrum", "harmonic"),
    ("inharmonic", "Inharmonic Spectrum", "nonharmonic_residual"),
    ("subbass", "Sub-bass band", "subbass_residual"),
)


def _empty_acd_row(note: str, reason: str, *, include_for_density: bool, erb_fraction: float) -> dict[str, Any]:
    row: dict[str, Any] = {
        "Note": note,
        "ACD_score": np.nan,
        "ACD_magnitude_per_component": np.nan,
        "ACD_D0": np.nan,
        "ACD_D1": np.nan,
        "ACD_D2": np.nan,
        "ACD_Dinf": np.nan,
        "ACD_evenness_D2_over_D0": np.nan,
        "ACD_r_harmonic": np.nan,
        "ACD_r_inharmonic": np.nan,
        "ACD_r_subbass": np.nan,
        "ACD_D2_harmonic": np.nan,
        "ACD_D2_inharmonic": np.nan,
        "ACD_D2_subbass": np.nan,
        "ACD_count_raw_harmonic": np.nan,
        "ACD_count_raw_inharmonic": np.nan,
        "ACD_count_raw_subbass": np.nan,
        "ACD_count_merged_harmonic": np.nan,
        "ACD_count_merged_inharmonic": np.nan,
        "ACD_count_merged_subbass": np.nan,
        "ACD_erb_fraction": float(erb_fraction),
        "ACD_include_for_density_applied": bool(include_for_density),
        "ACD_status": reason,
        "ACD_version": MODULE_REVISION,
        "acd_merge_status": "computed",
    }
    return row


def compute_acd_row_from_workbook(
    path: Path,
    *,
    basis: str = "amplitude",
    frequency_ceiling_hz: Optional[float] = None,
    include_only_for_density: bool = False,
    erb_fraction: float = ERB_FRACTION_DEFAULT,
    merge_within_erb: bool = True,
) -> dict[str, Any]:
    sheets = list_excel_sheets(path)
    if not INDIVIDUAL_SHEETS.issubset(set(sheets)):
        return _empty_acd_row(
            infer_note_from_filename(path),
            "missing_required_sheets",
            include_for_density=include_only_for_density,
            erb_fraction=erb_fraction,
        )
    meta = read_first_row_as_dict(path, "Metrics") if "Metrics" in sheets else {}
    note = infer_note_from_filename(path)
    if meta.get("Note") is not None and str(meta.get("Note")).strip():
        note = str(meta.get("Note")).strip()

    compartments = {}
    try:
        for export_name, sheet_name, std_type in _FAMILY_SHEETS:
            raw = (
                pd.read_excel(path, sheet_name=sheet_name)
                if sheet_name in sheets
                else pd.DataFrame()
            )
            table = standardise_component_table(
                raw,
                std_type,
                basis,
                frequency_ceiling_hz,
                include_only_for_density=include_only_for_density,
            )
            amps = (
                table["basis_value"].to_numpy(dtype=float)
                if not table.empty
                else np.array([], dtype=float)
            )
            freqs = (
                table["frequency_hz"].to_numpy(dtype=float)
                if not table.empty and "frequency_hz" in table.columns
                else (np.array([], dtype=float) if amps.size == 0 else None)
            )
            compartments[export_name] = compute_density_compartment(
                amps,
                freqs,
                merge_within_erb=merge_within_erb,
                erb_fraction=erb_fraction,
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        row = _empty_acd_row(
            note,
            f"read_error:{exc}",
            include_for_density=include_only_for_density,
            erb_fraction=erb_fraction,
        )
        row["source_sha256"] = file_sha256(path)
        return row

    note_metrics = compute_note_density(compartments, q=2.0)
    row = _empty_acd_row(
        note,
        str(note_metrics.get("ACD_status", "empty")),
        include_for_density=include_only_for_density,
        erb_fraction=erb_fraction,
    )
    row["ACD_score"] = note_metrics.get("ACD_score", np.nan)
    row["ACD_magnitude_per_component"] = note_metrics.get("ACD_magnitude_per_component", np.nan)
    row["ACD_D0"] = note_metrics.get("ACD_D0", np.nan)
    row["ACD_D1"] = note_metrics.get("ACD_D1", np.nan)
    row["ACD_D2"] = note_metrics.get("ACD_D2", np.nan)
    row["ACD_Dinf"] = note_metrics.get("ACD_Dinf", np.nan)
    row["ACD_evenness_D2_over_D0"] = note_metrics.get("ACD_evenness_D2_over_D0", np.nan)
    row["ACD_r_harmonic"] = note_metrics.get("r_harmonic", np.nan)
    row["ACD_r_inharmonic"] = note_metrics.get("r_inharmonic", np.nan)
    row["ACD_r_subbass"] = note_metrics.get("r_subbass", np.nan)
    row["ACD_D2_harmonic"] = note_metrics.get("D2_harmonic", np.nan)
    row["ACD_D2_inharmonic"] = note_metrics.get("D2_inharmonic", np.nan)
    row["ACD_D2_subbass"] = note_metrics.get("D2_subbass", np.nan)
    row["ACD_count_raw_harmonic"] = note_metrics.get("count_raw_harmonic", np.nan)
    row["ACD_count_raw_inharmonic"] = note_metrics.get("count_raw_inharmonic", np.nan)
    row["ACD_count_raw_subbass"] = note_metrics.get("count_raw_subbass", np.nan)
    row["ACD_count_merged_harmonic"] = note_metrics.get("count_merged_harmonic", np.nan)
    row["ACD_count_merged_inharmonic"] = note_metrics.get("count_merged_inharmonic", np.nan)
    row["ACD_count_merged_subbass"] = note_metrics.get("count_merged_subbass", np.nan)
    row["source_sha256"] = file_sha256(path)
    return row


def compute_acd_dataframe_from_analysis_root(
    analysis_root: Path,
    *,
    basis: str = "amplitude",
    frequency_ceiling_hz: Optional[float] = None,
    include_only_for_density: bool = False,
    erb_fraction: float = ERB_FRACTION_DEFAULT,
    merge_within_erb: bool = True,
) -> pd.DataFrame:
    workbooks = discover_individual_exact_workbooks(analysis_root)
    rows = [
        compute_acd_row_from_workbook(
            path,
            basis=basis,
            frequency_ceiling_hz=frequency_ceiling_hz,
            include_only_for_density=include_only_for_density,
            erb_fraction=erb_fraction,
            merge_within_erb=merge_within_erb,
        )
        for path in workbooks
    ]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _prepare_acd_merge_frame(acd: pd.DataFrame) -> pd.DataFrame:
    if acd.empty:
        return pd.DataFrame(columns=["Note", *ACD_RESEARCH_ALL_COLUMNS])
    frame = acd.copy()
    frame["Note"] = frame["Note"].astype(str).str.strip()
    keep = ["Note", *ACD_RESEARCH_ALL_COLUMNS]
    present = [c for c in keep if c in frame.columns]
    return frame[present].drop_duplicates(subset=["Note"], keep="first")


def _init_empty_acd_columns(sd: pd.DataFrame, status: str) -> pd.DataFrame:
    out = sd.copy()
    for col in ACD_RESEARCH_ALL_COLUMNS:
        if col not in out.columns:
            if col == "ACD_include_for_density_applied":
                out[col] = False
            elif col == "ACD_version":
                out[col] = MODULE_REVISION
            elif col == "ACD_status":
                out[col] = status
            else:
                out[col] = np.nan
    out["acd_merge_status"] = status
    return out


def merge_acd_stage3(
    sd: pd.DataFrame,
    compiled_workbook: Path,
    warnings: List[str],
    *,
    include_acd: bool = True,
    fail_closed: bool = False,
    analysis_root: Optional[Path] = None,
    include_only_for_density: bool = False,
    erb_fraction: float = ERB_FRACTION_DEFAULT,
    frequency_ceiling_hz: Optional[float] = None,
) -> AcdStage3MergeResult:
    if not include_acd or sd is None or sd.empty or "Note" not in sd.columns:
        empty = sd if sd is not None else pd.DataFrame()
        diag, diag_summary = build_acd_diagnostics(empty, analysis_root="", n_workbooks=0)
        return AcdStage3MergeResult(empty, diag, diag_summary, STAGE3_ACD_STATUS_OK, tuple(warnings))

    if analysis_root is not None:
        analysis_root = Path(analysis_root).expanduser().resolve()
    else:
        analysis_root = Path(compiled_workbook).expanduser().resolve().parent

    global_status = "merged"
    stage_messages: list[str] = list(warnings)
    try:
        acd_raw = compute_acd_dataframe_from_analysis_root(
            analysis_root,
            frequency_ceiling_hz=frequency_ceiling_hz,
            include_only_for_density=include_only_for_density,
            erb_fraction=erb_fraction,
        )
    except (OSError, ValueError, KeyError, pd.errors.ParserError) as exc:
        stage_messages.append(f"Stage 3 ACD computation failed: {exc}")
        out = _init_empty_acd_columns(sd, "acd_computation_failed")
        global_status = "acd_computation_failed"
    else:
        if acd_raw.empty:
            stage_messages.append("Stage 3 ACD skipped: no per-note workbooks found.")
            out = _init_empty_acd_columns(sd, "no_per_note_workbooks_found")
            global_status = "no_per_note_workbooks_found"
        else:
            acd_merge = _prepare_acd_merge_frame(acd_raw)
            out = sd.copy()
            out["Note"] = out["Note"].astype(str).str.strip()
            for col in ACD_RESEARCH_ALL_COLUMNS:
                if col in out.columns:
                    out = out.drop(columns=[col])
            out = out.merge(acd_merge, on="Note", how="left", validate="m:1")
            missing = out["ACD_score"].isna() & out.get("ACD_status", pd.Series("", index=out.index)).isna()
            # ACD_score may be legitimately NaN (empty note). Use merge key presence.
            if "ACD_version" in out.columns:
                missing = out["ACD_version"].isna()
            out.loc[missing, "acd_merge_status"] = "note_not_in_acd_output"
            out.loc[~missing, "acd_merge_status"] = out.loc[~missing, "acd_merge_status"].fillna(
                "merged_individual_exact"
            )
            n_merged = int((~missing).sum())
            stage_messages.append(
                f"Stage 3 ACD merged {n_merged}/{len(out)} notes "
                f"(include_only_for_density={include_only_for_density})."
            )

    n_workbooks = len(discover_individual_exact_workbooks(analysis_root))
    diagnostics, diagnostics_summary = build_acd_diagnostics(
        out, analysis_root=str(analysis_root), n_workbooks=n_workbooks
    )
    status = assess_acd_merge_result(
        out, include_acd=True, global_status=global_status, messages=stage_messages
    )
    result = AcdStage3MergeResult(out, diagnostics, diagnostics_summary, status, tuple(stage_messages))
    if fail_closed:
        enforce_acd_fail_closed(result)
    return result
