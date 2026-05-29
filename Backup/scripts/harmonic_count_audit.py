from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


TARGET_COLUMNS = [
    "expected_harmonic_order_count_up_to_body_ceiling",
    "salient_harmonic_order_count_up_to_body_ceiling",
    "harmonic_peak_candidate_count",
    "harmonic_occupancy_detected_order_count",
    "harmonic_bin_count",
    "Harmonic Count (relative)",
    "Harmonic Ceiling (relative)",
]


def _to_float(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return x if math.isfinite(x) else float("nan")


def _normalize_note(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip().replace("♯", "#").replace("♭", "b")


def _try_read_sheet(path: Path, sheet: str) -> Optional[pd.DataFrame]:
    try:
        return pd.read_excel(path, sheet_name=sheet)
    except Exception:
        return None


def _audit_from_compiled_density_metrics(path: Path, dataset_label: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    df = _try_read_sheet(path, "Diagnostic_Metrics")
    if df is None or df.empty:
        return out

    for _, r in df.iterrows():
        note = _normalize_note(r.get("Note"))
        f0 = _to_float(r.get("f0_used_for_density_hz"))
        ceiling = _to_float(r.get("density_frequency_ceiling_hz"))
        theoretical = (
            int(math.floor(ceiling / f0))
            if math.isfinite(f0) and f0 > 0 and math.isfinite(ceiling) and ceiling > 0
            else None
        )
        row: Dict[str, Any] = {
            "dataset": dataset_label,
            "source_kind": "compiled_density_metrics:Diagnostic_Metrics",
            "note": note,
            "f0_hz": f0,
            "frequency_ceiling_hz": ceiling,
            "theoretical_max_floor": theoretical,
        }
        for c in TARGET_COLUMNS:
            row[c] = r.get(c) if c in df.columns else None
        out.append(row)
    return out


def _audit_from_legacy_per_note(path: Path, dataset_label: str) -> Optional[Dict[str, Any]]:
    df = _try_read_sheet(path, "Metrics")
    if df is None or df.empty:
        return None
    r = df.iloc[0]
    note = _normalize_note(r.get("Note"))
    f0 = _to_float(r.get("Lowest Harmonic (Hz)"))
    ceiling = _to_float(r.get("Highest Harmonic (Hz)"))
    theoretical = (
        int(math.floor(ceiling / f0))
        if math.isfinite(f0) and f0 > 0 and math.isfinite(ceiling) and ceiling > 0
        else None
    )
    row: Dict[str, Any] = {
        "dataset": dataset_label,
        "source_kind": "legacy_per_note:Metrics",
        "note": note,
        "f0_hz": f0,
        "frequency_ceiling_hz": ceiling,
        "theoretical_max_floor": theoretical,
        "expected_harmonic_order_count_up_to_body_ceiling": None,
        "salient_harmonic_order_count_up_to_body_ceiling": None,
        "harmonic_peak_candidate_count": None,
        "harmonic_occupancy_detected_order_count": None,
        "harmonic_bin_count": None,
        "Harmonic Count (relative)": r.get("Harmonic Count (relative)"),
        "Harmonic Ceiling (relative)": r.get("Harmonic Ceiling (relative)"),
        "Harmonic Count": r.get("Harmonic Count"),
        "Harmonic Count (N)": r.get("Harmonic Count (N)"),
    }
    return row


def _collect_rows(dataset_root: Path, dataset_label: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    analysis = dataset_root / "_Sustains" / "analysis_results"

    compiled = analysis / "compiled_density_metrics.xlsx"
    if compiled.exists():
        rows.extend(_audit_from_compiled_density_metrics(compiled, dataset_label))

    # Legacy per-note exports (one workbook per note).
    for p in analysis.rglob("spectral_analysis.xlsx"):
        item = _audit_from_legacy_per_note(p, dataset_label)
        if item is not None:
            rows.append(item)
    return rows


def _violation_count(df: pd.DataFrame, field: str) -> int:
    if field not in df.columns:
        return 0
    a = pd.to_numeric(df[field], errors="coerce")
    b = pd.to_numeric(df["theoretical_max_floor"], errors="coerce")
    mask = a.notna() & b.notna() & (a > b)
    return int(mask.sum())


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit harmonic-count semantics vs physical ceilings.")
    parser.add_argument(
        "--dataset",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Dataset label and path, e.g. ds1=C:\\path\\to\\flauta_pp",
    )
    parser.add_argument(
        "--out-csv",
        default="harmonic_count_audit_rows.csv",
        help="Output CSV path for per-note audit rows.",
    )
    args = parser.parse_args()

    all_rows: List[Dict[str, Any]] = []
    for spec in args.dataset:
        if "=" not in spec:
            raise SystemExit(f"Invalid --dataset format: {spec!r}. Expected LABEL=PATH.")
        label, raw_path = spec.split("=", 1)
        root = Path(raw_path)
        if not root.exists():
            raise SystemExit(f"Dataset path not found: {root}")
        all_rows.extend(_collect_rows(root, label))

    if not all_rows:
        raise SystemExit("No audit rows collected.")

    df = pd.DataFrame(all_rows)
    df.to_csv(args.out_csv, index=False)

    print(f"rows_written={len(df)} csv={Path(args.out_csv).resolve()}")
    for field in [
        "expected_harmonic_order_count_up_to_body_ceiling",
        "salient_harmonic_order_count_up_to_body_ceiling",
        "harmonic_occupancy_detected_order_count",
        "harmonic_bin_count",
        "harmonic_peak_candidate_count",
        "Harmonic Count",
        "Harmonic Count (N)",
        "Harmonic Count (relative)",
    ]:
        if field in df.columns:
            print(f"violations[{field}]={_violation_count(df, field)}")


if __name__ == "__main__":
    main()
