"""R2 — one exported EWSD / core_H, same function as Stage-3.

Stage-1 Metrics ``core_*_energy_ratio`` is the component (ΣA² H/I/S)
partition. ``EWSD_score_acoustic_balanced`` is ``compute_ewsd`` after
``add_acoustic_alignment_columns``, the same path Stage-3 merges.
``energy_weighted_component_density_diagnostic`` is a different
construct and is not EWSD.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
import sys

if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

SINGLE_SOURCE_ATOL = 1e-9

METRIC_PATHS: tuple[dict[str, str], ...] = (
    {
        "path": "descriptor_his",
        "function": "acoustic_density_core.compute_acoustic_density_descriptors",
        "columns": "harmonic_energy_ratio / residual_energy_ratio / subbass_energy_ratio",
        "consumers": "Stage-1 extras; pies; not export core_H after R2",
    },
    {
        "path": "diagnostic_ewsd_alias",
        "function": "acoustic_density_core.compute_acoustic_density_descriptors",
        "columns": "energy_weighted_component_density_diagnostic",
        "consumers": "Metrics diagnostic only; not EWSD",
    },
    {
        "path": "component_his",
        "function": "proc_audio.AudioProcessor (ΣA² H/I/S)",
        "columns": "component_*_energy_ratio",
        "consumers": "export core_*; Stage-3 SDM core_*",
    },
    {
        "path": "stage1_core_h",
        "function": "proc_audio.AudioProcessor._build_main_metrics_export_row",
        "columns": "core_harmonic_energy_ratio",
        "consumers": "compile; eval; verify_export",
    },
    {
        "path": "stage1_ewsd",
        "function": "tools.canonical_note_metrics.stamp_stage1_ewsd",
        "columns": "EWSD_score_acoustic_balanced",
        "consumers": "Metrics; eval B1; verify_export",
    },
    {
        "path": "stage3_core_h",
        "function": "tools.export_research_density_workbook (component_* renormalised)",
        "columns": "core_harmonic_energy_ratio",
        "consumers": "compiled Spectral_Density_Metrics",
    },
    {
        "path": "stage3_ewsd",
        "function": "tools.ewsd_research_integration.compute_ewsd_dataframe_from_analysis_root",
        "columns": "EWSD_score_acoustic_balanced",
        "consumers": "SDM; Stage3_Diagnostics",
    },
    {
        "path": "density_sums",
        "function": "compile_metrics.extract_density_component_sum",
        "columns": "harmonic_density_sum / inharmonic_density_sum / subbass_density_sum",
        "consumers": "Density_Metrics; research SDM",
    },
)


def _finite(value: Any) -> Optional[float]:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    return x


def canonical_core_energy_ratios(
    harmonic: Any,
    residual: Any,
    subbass: Any,
) -> Dict[str, float]:
    """Renormalise a H/R/S triple. Stage-1 and Stage-3 share this."""
    h = _finite(harmonic)
    r = _finite(residual)
    s = _finite(subbass)
    if h is None:
        h = float("nan")
    if r is None:
        r = float("nan")
    if s is None:
        s = float("nan")
    total = 0.0
    n = 0
    for v in (h, r, s):
        if math.isfinite(v):
            total += v
            n += 1
    if n == 0 or total <= 0.0:
        return {
            "core_harmonic_energy_ratio": float("nan"),
            "core_residual_energy_ratio": float("nan"),
            "core_subbass_energy_ratio": float("nan"),
        }
    return {
        "core_harmonic_energy_ratio": h / total if math.isfinite(h) else float("nan"),
        "core_residual_energy_ratio": r / total if math.isfinite(r) else float("nan"),
        "core_subbass_energy_ratio": s / total if math.isfinite(s) else float("nan"),
    }


def core_ratios_from_component_his(
    component_h: Any,
    component_i: Any,
    component_s: Any,
) -> Dict[str, float]:
    """Export core_* is the component ΣA² partition (I is the residual)."""
    return canonical_core_energy_ratios(component_h, component_i, component_s)


def values_agree(a: Any, b: Any, *, atol: float = SINGLE_SOURCE_ATOL) -> bool:
    fa, fb = _finite(a), _finite(b)
    if fa is None and fb is None:
        return True
    if fa is None or fb is None:
        return False
    return abs(fa - fb) <= atol


def compute_stage3_ewsd_row(analysis_root: Path) -> pd.DataFrame:
    from tools.ewsd_research_integration import compute_ewsd_dataframe_from_analysis_root

    return compute_ewsd_dataframe_from_analysis_root(
        Path(analysis_root),
        frequency_ceiling_hz=20000.0,
        include_uncertainty=False,
    )


def stamp_stage1_ewsd(workbook: Path) -> Dict[str, Any]:
    """Write Stage-3 EWSD onto the Stage-1 Metrics sheet."""
    workbook = Path(workbook)
    payload: Dict[str, Any] = {
        "workbook": str(workbook),
        "ok": False,
        "EWSD_score_acoustic_balanced": float("nan"),
        "ewsd_stamp_status": "not_computed",
    }
    if not workbook.is_file():
        payload["ewsd_stamp_status"] = "missing_workbook"
        return payload
    try:
        ewsd = compute_stage3_ewsd_row(workbook.parent)
    except Exception as exc:
        payload["ewsd_stamp_status"] = f"compute_failed:{exc}"
        return payload
    if ewsd is None or ewsd.empty:
        payload["ewsd_stamp_status"] = "note_not_in_ewsd_output"
        _patch_metrics(workbook, payload)
        return payload
    row = ewsd.iloc[0]
    score = _finite(row.get("ewsd_score_acoustic_balanced", row.get("EWSD_score_acoustic_balanced")))
    payload["EWSD_score_acoustic_balanced"] = float("nan") if score is None else float(score)
    payload["ewsd_primary_analysis_eligible"] = bool(row.get("ewsd_primary_analysis_eligible", False))
    payload["ewsd_stamp_status"] = "stamped"
    payload["ok"] = True
    _patch_metrics(workbook, payload)
    return payload


def _patch_metrics(workbook: Path, updates: Mapping[str, Any]) -> None:
    keep = {
        "EWSD_score_acoustic_balanced": updates.get("EWSD_score_acoustic_balanced"),
        "ewsd_stamp_status": updates.get("ewsd_stamp_status"),
        "ewsd_primary_analysis_eligible": updates.get("ewsd_primary_analysis_eligible"),
    }
    metrics = pd.read_excel(workbook, sheet_name="Metrics")
    if {"Parameter", "Value"}.issubset(set(metrics.columns.astype(str))):
        keys = metrics["Parameter"].astype(str)
        for name, value in keep.items():
            if value is None:
                continue
            mask = keys.eq(name)
            if mask.any():
                metrics.loc[mask, "Value"] = value
            else:
                metrics = pd.concat(
                    [metrics, pd.DataFrame({"Parameter": [name], "Value": [value]})],
                    ignore_index=True,
                )
    else:
        for name, value in keep.items():
            if value is None:
                continue
            metrics[name] = value
    with pd.ExcelWriter(
        workbook,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace",
    ) as writer:
        metrics.to_excel(writer, sheet_name="Metrics", index=False)


def read_metrics_map(workbook: Path) -> Dict[str, Any]:
    df = pd.read_excel(workbook, sheet_name="Metrics")
    if {"Parameter", "Value"}.issubset(set(df.columns.astype(str))):
        return {
            str(r["Parameter"]).strip(): r["Value"]
            for _, r in df.iterrows()
            if str(r["Parameter"]).strip()
        }
    if df.empty:
        return {}
    return {str(c): df.iloc[0][c] for c in df.columns}
