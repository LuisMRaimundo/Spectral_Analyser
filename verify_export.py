"""CLI: report provenance, invariants, counts, and cross-run comparability.

Usage::

    python verify_export.py path/to/spectral_analysis.xlsx
    python verify_export.py path/to/compiled_density_metrics.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd

from analysis_policy import EXPORT_SCHEMA_VERSION
from analysis_provenance import resolve_analysis_provenance
from data_integrity import (
    validate_header_contract_consistency,
    validate_metric_single_source,
    validate_unique_peak_bin_assignment,
)

EXCLUSIVE_ASSIGNMENT_SCHEMA = "spectral_analysis_schema_2026_08"
PRE_EXCLUSIVE_REASON = "not comparable (pre-exclusive-assignment)"


def _kv_sheet(path: Path, sheet: str) -> Dict[str, Any]:
    try:
        df = pd.read_excel(path, sheet_name=sheet)
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    cols = {str(c).strip() for c in df.columns}
    if {"Parameter", "Value"}.issubset(cols) or {"parameter", "value"}.issubset(
        {c.lower() for c in cols}
    ):
        key_col = "Parameter" if "Parameter" in df.columns else df.columns[0]
        val_col = "Value" if "Value" in df.columns else df.columns[1]
        out: Dict[str, Any] = {}
        for _, row in df.iterrows():
            key = str(row.get(key_col, "") or "").strip()
            if key:
                out[key] = row.get(val_col)
        return out
    # Wide single-row metadata
    return {str(c): df.iloc[0][c] for c in df.columns}


def _read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet)
    except Exception:
        return pd.DataFrame()


def _workbook_sheets(path: Path) -> list[str]:
    try:
        with pd.ExcelFile(path) as xf:
            return list(xf.sheet_names)
    except Exception:
        return []


def _meta_get(meta: Dict[str, Any], *names: str) -> str:
    for name in names:
        if name in meta and meta[name] is not None and str(meta[name]).strip():
            return str(meta[name]).strip()
    return ""


def assess_workbook_comparability(
    path: Path,
    *,
    current: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compare a workbook to the current exclusive-assignment / schema rule."""
    current = current or resolve_analysis_provenance()
    sheets = _workbook_sheets(path)
    meta: Dict[str, Any] = {}
    for candidate in (
        "Analysis_Metadata",
        "Per_Note_Processing_Metadata",
        "Metadata",
    ):
        if candidate in sheets:
            meta = _kv_sheet(path, candidate)
            if meta:
                break

    export_schema = _meta_get(
        meta, "export_schema_version", "EXPORT_SCHEMA_VERSION"
    )
    analysis_version = _meta_get(meta, "analysis_version")
    package_version = _meta_get(meta, "package_version")
    code_commit = _meta_get(meta, "code_commit", "git_commit")

    pre_exclusive = False
    if not export_schema:
        pre_exclusive = True
    elif export_schema != EXCLUSIVE_ASSIGNMENT_SCHEMA:
        pre_exclusive = True
    if analysis_version.startswith("4.0"):
        pre_exclusive = True

    harm = _read_sheet(path, "Harmonic Spectrum")
    if not harm.empty and "peak_bin_index" in harm.columns:
        uniq = validate_unique_peak_bin_assignment(harm)
        if not uniq.get("ok", True):
            pre_exclusive = True
    elif not harm.empty and "peak_bin_index" not in harm.columns:
        # Older Stage 1 workbooks lack exclusive-assignment identity.
        if export_schema != EXCLUSIVE_ASSIGNMENT_SCHEMA:
            pre_exclusive = True

    energy_basis = _meta_get(meta, "energy_basis")
    if pre_exclusive:
        comparable = False
        reason = PRE_EXCLUSIVE_REASON
    elif energy_basis and energy_basis not in {"psd_per_hz", "missing", ""}:
        comparable = False
        reason = "not comparable (per_bin_energy_basis)"
    elif code_commit and code_commit not in {
        str(current.get("code_commit") or ""),
        "unknown",
        "unavailable_not_recorded",
    } and str(current.get("code_commit")) not in {"unknown", ""}:
        comparable = False
        reason = "not comparable (code_commit mismatch)"
    elif export_schema == EXPORT_SCHEMA_VERSION:
        comparable = True
        reason = "comparable"
    else:
        comparable = False
        reason = "not comparable (export_schema_version mismatch)"

    return {
        "path": str(path),
        "export_schema_version": export_schema or "missing",
        "analysis_version": analysis_version or "missing",
        "package_version": package_version or "missing",
        "code_commit": code_commit or "missing",
        "code_dirty": _meta_get(meta, "code_dirty") or "missing",
        "comparable": comparable,
        "comparability_reason": reason,
        "current_code_commit": current.get("code_commit"),
        "current_analysis_version": current.get("analysis_version"),
        "current_export_schema_version": current.get("export_schema_version"),
    }


def count_validated_partials(path: Path) -> Dict[str, Any]:
    """Count validated H, confirmed I, and F-020 S members."""
    from validated_partials import is_subbass_compartment_member

    harm = _read_sheet(path, "Harmonic Spectrum")
    inh = _read_sheet(path, "Inharmonic Spectrum")
    if inh.empty:
        inh = _read_sheet(path, "Confirmed_Inharmonic_Partials")
    sub = _read_sheet(path, "Sub-bass band")
    validated_h = 0
    if not harm.empty and "include_for_density" in harm.columns:
        validated_h = int(
            harm["include_for_density"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "1.0"])
            .sum()
        )
    confirmed_i = 0
    if not inh.empty:
        status_col = (
            "inharmonic_status"
            if "inharmonic_status" in inh.columns
            else (
                "Acoustic_Interpretation_Status"
                if "Acoustic_Interpretation_Status" in inh.columns
                else None
            )
        )
        if status_col is not None:
            confirmed_i = int(
                inh[status_col]
                .astype(str)
                .str.strip()
                .isin(["confirmed_inharmonic_partial", "confirmed_partial"])
                .sum()
            )
    s_members = 0
    if not sub.empty:
        freq_col = "Frequency (Hz)" if "Frequency (Hz)" in sub.columns else None
        meta = _kv_sheet(path, "Analysis_Metadata")
        try:
            f0 = float(
                _meta_get(meta, "f0_used_for_density_hz", "f0_final_hz") or "nan"
            )
        except (TypeError, ValueError):
            f0 = float("nan")
        if freq_col is not None:
            for _, row in sub.iterrows():
                try:
                    freq = float(row.get(freq_col))
                except (TypeError, ValueError):
                    continue
                cls = str(
                    row.get("Low_Frequency_Class")
                    or row.get("low_frequency_class")
                    or ""
                )
                if is_subbass_compartment_member(
                    freq, f0_hz=f0 if f0 == f0 else 0.0, low_frequency_class=cls
                ):
                    s_members += 1
    return {
        "validated_H": validated_h,
        "confirmed_I": confirmed_i,
        "S_members": s_members,
    }


def inspect_workbook_invariants(path: Path) -> Dict[str, Any]:
    sheets = _workbook_sheets(path)
    headers_by_sheet: Dict[str, list[str]] = {}
    for name in sheets:
        df = _read_sheet(path, name)
        headers_by_sheet[name] = [str(c) for c in df.columns]
    header_inv = validate_header_contract_consistency(headers_by_sheet)
    harm = _read_sheet(path, "Harmonic Spectrum")
    peak_inv = (
        validate_unique_peak_bin_assignment(harm)
        if not harm.empty
        else {"ok": True, "failures": "", "duplicated_bins": []}
    )
    metrics_map: Dict[str, Any] = {}
    if "Metrics" in sheets:
        metrics_map = _kv_sheet(path, "Metrics")
    stage3_map: Dict[str, Any] = {}
    if "Spectral_Density_Metrics" in sheets:
        sd = _read_sheet(path, "Spectral_Density_Metrics")
        if not sd.empty:
            stage3_map = {str(c): sd.iloc[0][c] for c in sd.columns}
    single = validate_metric_single_source(metrics_map, stage3=stage3_map)
    ok = bool(
        header_inv.get("ok", True)
        and peak_inv.get("ok", True)
        and single.get("ok", True)
    )
    failures = [
        x
        for x in (
            header_inv.get("failures"),
            peak_inv.get("failures"),
            single.get("failures"),
        )
        if x
    ]
    return {
        "ok": ok,
        "header_contract": header_inv,
        "peak_bin_assignment": peak_inv,
        "metric_single_source": single,
        "failures": "; ".join(str(f) for f in failures),
    }


def format_report(path: Path) -> str:
    current = resolve_analysis_provenance()
    cmp_ = assess_workbook_comparability(path, current=current)
    inv = inspect_workbook_invariants(path)
    counts = count_validated_partials(path)
    lines = [
        f"workbook: {path}",
        f"commit: {cmp_['code_commit']}",
        f"package_version: {cmp_['package_version']}",
        f"analysis_version: {cmp_['analysis_version']}",
        f"export_schema_version: {cmp_['export_schema_version']}",
        f"current_code_commit: {cmp_['current_code_commit']}",
        f"current_analysis_version: {cmp_['current_analysis_version']}",
        f"invariants: {'ok' if inv['ok'] else 'FAIL'}"
        + (f" ({inv['failures']})" if inv.get("failures") else ""),
        f"validated_H: {counts['validated_H']}",
        f"confirmed_I: {counts['confirmed_I']}",
        f"S_members: {counts['S_members']}",
        f"comparable: {cmp_['comparability_reason']}",
    ]
    return "\n".join(lines)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Spectral_Analyser export against current code."
    )
    parser.add_argument("workbook", type=Path, help="xlsx workbook to inspect")
    args = parser.parse_args(list(argv) if argv is not None else None)
    path = Path(args.workbook)
    if not path.is_file():
        print(f"workbook not found: {path}", file=sys.stderr)
        return 2
    print(format_report(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
