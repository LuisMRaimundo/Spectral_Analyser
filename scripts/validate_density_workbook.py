#!/usr/bin/env python3
"""
Validate a compiled density workbook (structure, allow-list, metadata vs sheets).

Usage:
    python scripts/validate_density_workbook.py path/to/compiled_density_metrics.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Repo root (parent of scripts/)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from compile_metrics import (  # noqa: E402
    DENSITY_METRICS_ALLOWED_COLUMNS,
    density_metric_column_is_forbidden,
    validate_compiled_density_workbook,
)
from metadata_sanitizer import (  # noqa: E402
    list_publication_path_violations_in_excel,
    publication_redaction_enabled,
    string_fails_publication_scan,
)


def _meta_dict(path: Path) -> dict:
    am = pd.read_excel(path, sheet_name="Analysis_Metadata")
    if "Parameter" in am.columns and "Value" in am.columns:
        return {str(r["Parameter"]): r["Value"] for _, r in am.iterrows()}
    return am.iloc[0].to_dict()


def _mget(meta: dict, key: str) -> str:
    return str(meta.get(key, "") or "").lower()


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate compiled density Excel workbook.")
    ap.add_argument("workbook", type=Path, help="Path to .xlsx")
    args = ap.parse_args()
    path: Path = args.workbook

    print(f"=== Density workbook validation ===\nFile: {path.resolve()}\n")

    checks: list[tuple[str, bool, str]] = []

    if not path.is_file():
        checks.append(("File exists", False, "not found"))
        _print_checks(checks)
        print("\nWorkbook validation failed: file not found.")
        return 1

    try:
        xl = pd.ExcelFile(path)
        names = list(xl.sheet_names)
    except Exception as e:
        checks.append(("Open Excel", False, str(e)))
        _print_checks(checks)
        print(f"\nWorkbook validation failed: {e}")
        return 1

    checks.append(("Sheet: Density_Metrics", "Density_Metrics" in names, ""))
    checks.append(("Sheet: Analysis_Metadata", "Analysis_Metadata" in names, ""))

    meta: dict = {}
    try:
        meta = _meta_dict(path)
        checks.append(("Read Analysis_Metadata", True, ""))
    except Exception as e:
        checks.append(("Read Analysis_Metadata", False, str(e)))

    if publication_redaction_enabled():
        pub_v = list_publication_path_violations_in_excel(path)
        checks.append(("Publication: no local absolute paths (all sheets)", not pub_v, "; ".join(pub_v)))
        try:
            am_df = pd.read_excel(path, sheet_name="Analysis_Metadata")
            am_blob = am_df.to_csv(index=False)
            ok_am = not string_fails_publication_scan(am_blob)
            checks.append(("Publication: Analysis_Metadata text scan", ok_am, "forbidden path substring"))
        except Exception as e:
            checks.append(("Publication: Analysis_Metadata text scan", False, str(e)))
        if "Per_Note_Processing_Metadata" in names:
            try:
                pn_blob = pd.read_excel(path, sheet_name="Per_Note_Processing_Metadata").to_csv(index=False)
                ok_pn = not string_fails_publication_scan(pn_blob)
                checks.append(("Publication: Per_Note_Processing_Metadata text scan", ok_pn, ""))
            except Exception as e:
                checks.append(("Publication: Per_Note_Processing_Metadata text scan", False, str(e)))

    if "Density_Metrics" in names:
        dm = pd.read_excel(path, sheet_name="Density_Metrics")
        bad_allow = [str(c) for c in dm.columns if str(c) not in DENSITY_METRICS_ALLOWED_COLUMNS]
        checks.append(
            (
                "Density_Metrics allow-list",
                not bad_allow,
                f"extra columns: {bad_allow[:8]}" + (" …" if len(bad_allow) > 8 else ""),
            )
        )
        bad_forbid = [str(c) for c in dm.columns if density_metric_column_is_forbidden(str(c))]
        checks.append(
            (
                "Density_Metrics forbidden patterns",
                not bad_forbid,
                "; ".join(bad_forbid[:6]) + (" …" if len(bad_forbid) > 6 else ""),
            )
        )
        if "harmonic_order_count" in dm.columns:
            checks.append(("Density_Metrics has harmonic_order_count", True, ""))
        if {"harmonic_energy_ratio", "inharmonic_energy_ratio", "subbass_energy_ratio"} <= set(dm.columns):
            ssum = (
                pd.to_numeric(dm["harmonic_energy_ratio"], errors="coerce").fillna(0.0)
                + pd.to_numeric(dm["inharmonic_energy_ratio"], errors="coerce").fillna(0.0)
                + pd.to_numeric(dm["subbass_energy_ratio"], errors="coerce").fillna(0.0)
            )
            ok = bool((ssum - 1.0).abs().max() <= 0.05)
            checks.append(("Energy ratios sum ~1", ok, "tolerance 0.05"))
        if "effective_partial_density" in dm.columns:
            v = pd.to_numeric(dm["effective_partial_density"], errors="coerce")
            vn = v.dropna()
            if vn.empty:
                checks.append(("effective_partial_density finite non-negative", False, "all NaN"))
            else:
                arr = vn.to_numpy(dtype=float, copy=False)
                ok = bool((arr >= 0).all() and np.isfinite(arr).all())
                checks.append(("effective_partial_density finite non-negative", ok, ""))

    st = _mget(meta, "debug_counts_export_status")
    if "exported" in st:
        checks.append(("Debug_Counts present", "Debug_Counts" in names, "metadata requests export"))

    pn = _mget(meta, "per_note_metadata_export_status")
    if "exported" in pn:
        checks.append(
            (
                "Per_Note_Processing_Metadata present",
                "Per_Note_Processing_Metadata" in names,
                "metadata requests export",
            )
        )

    dst = _mget(meta, "dissonance_export_status")
    if "exported" in dst:
        checks.append(("Dissonance_Metrics present", "Dissonance_Metrics" in names, "metadata requests export"))

    pst = _mget(meta, "pca_export_status")
    if pst == "exported":
        for s in ("PCA_Scores", "PCA_Loadings", "PCA_Explained_Variance"):
            checks.append((f"PCA sheet: {s}", s in names, ""))
    elif pst and pst != "exported":
        for s in ("PCA_Scores", "PCA_Loadings", "PCA_Explained_Variance"):
            checks.append((f"PCA skipped: no {s}", s not in names, ""))

    vst = _mget(meta, "validation_export_status")
    if "exported" in vst:
        checks.append(("Validation_Metrics present", "Validation_Metrics" in names, ""))

    extra = validate_compiled_density_workbook(path)
    checks.append(("Aggregate validator", not extra, "; ".join(extra[:5]) + (" …" if len(extra) > 5 else "")))

    if "Per_Note_Processing_Metadata" in names:
        try:
            pn_df = pd.read_excel(path, sheet_name="Per_Note_Processing_Metadata")
        except Exception as e:
            checks.append(("Read Per_Note_Processing_Metadata", False, str(e)))
        else:
            req = ("batch_harmonic_energy_ratio", "batch_inharmonic_energy_ratio", "batch_subbass_energy_ratio")
            if all(c in pn_df.columns for c in req):
                h = pd.to_numeric(pn_df["batch_harmonic_energy_ratio"], errors="coerce")
                i_ = pd.to_numeric(pn_df["batch_inharmonic_energy_ratio"], errors="coerce")
                s_ = pd.to_numeric(pn_df["batch_subbass_energy_ratio"], errors="coerce")
                sm = h + i_ + s_
                ok_bn = bool(sm.notna().any() and (sm - 1.0).abs().max() <= 0.02)
                checks.append(("Per_Note batch H+I+S sum ~1", ok_bn, f"max err {(sm-1.0).abs().max() if sm.notna().any() else 'n/a'}"))
                ok_nn = bool(
                    sm.notna().any()
                    and ((h.fillna(0) >= -1e-9) & (i_.fillna(0) >= -1e-9) & (s_.fillna(0) >= -1e-9)).all()
                    and np.isfinite(sm.to_numpy(dtype=float, copy=False)).all()
                )
                checks.append(("Per_Note batch ratios non-negative finite", ok_nn, ""))
            if "model_harmonic_weight" in pn_df.columns and "model_inharmonic_weight" in pn_df.columns:
                mh = pd.to_numeric(pn_df["model_harmonic_weight"], errors="coerce")
                mi = pd.to_numeric(pn_df["model_inharmonic_weight"], errors="coerce")
                msum = mh + mi
                m_ok = mh.notna() & mi.notna()
                if m_ok.any():
                    ok_m = bool((msum[m_ok] - 1.0).abs().max() <= 0.02)
                    checks.append(("Per_Note model weights sum ~1", ok_m, ""))
                if m_ok.any() and "model_weights_source" in pn_df.columns:
                    src = pn_df.loc[m_ok, "model_weights_source"].astype(str).str.strip()
                    checks.append(("Per_Note model_weights_source present", bool(src.str.len().gt(0).all()), ""))
                if m_ok.any() and "model_weight_denominator" in pn_df.columns:
                    den = pn_df.loc[m_ok, "model_weight_denominator"].astype(str).str.strip().str.lower()
                    checks.append(
                        (
                            "Per_Note model_weight_denominator",
                            bool(den.eq("harmonic_plus_inharmonic").all()),
                            "",
                        )
                    )

    _print_checks(checks)

    failed = [c for c in checks if not c[1]]
    if failed:
        problems = [f"{n}: {d or 'failed'}" for n, _, d in failed]
        print("\nWorkbook validation failed: " + "; ".join(problems))
        return 1

    print("\nWorkbook validation passed.")
    return 0


def _print_checks(rows: list[tuple[str, bool, str]]) -> None:
    for name, ok, detail in rows:
        tag = "PASS" if ok else "FAIL"
        tail = f" — {detail}" if detail else ""
        print(f"[{tag}] {name}{tail}")


if __name__ == "__main__":
    raise SystemExit(main())
