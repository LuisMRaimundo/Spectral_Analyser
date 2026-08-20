"""WP2 — Stage 1–3 re-export of trombone A#2 *ff* and tuba A2 *pp*.

Usage (from repo root)::

    python -m tools.wp2_acceptance_export --out docs/validation/_wp2_raw
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

TROMBONE_AS2 = Path(
    r"D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone"
    r"\IOWA_Trombone_ff\_Sustains_Stable\IOWA_Trb.T_ff.A#2_SustainStable.aif"
)
TUBA_A2 = Path(
    r"D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp\_Sustains_Stable"
    r"\IOWA_Tub.pp.A2_SustainStable.aif"
)


def _meta_map(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for sheet in ("Analysis_Metadata", "Per_Note_Processing_Metadata", "Validation_Metrics"):
        try:
            df = pd.read_excel(path, sheet_name=sheet)
        except Exception:
            continue
        cols = {str(c).strip().lower(): str(c) for c in df.columns}
        if "parameter" in cols and "value" in cols:
            for raw_k, raw_v in zip(df[cols["parameter"]], df[cols["value"]]):
                out[str(raw_k).strip()] = raw_v
            continue
        if len(df) == 1:
            for c in df.columns:
                out[str(c)] = df.iloc[0][c]
    return out


def _pick(d: Dict[str, Any], *names: str) -> Any:
    lower = {str(k).strip().lower(): v for k, v in d.items()}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _h74_h79(harm: pd.DataFrame) -> List[Dict[str, Any]]:
    rows = []
    if harm is None or harm.empty or "Harmonic Number" not in harm.columns:
        return rows
    for rec in harm.to_dict(orient="records"):
        try:
            n = int(float(rec.get("Harmonic Number")))
        except (TypeError, ValueError):
            continue
        if n not in (74, 79):
            continue
        rows.append(
            {
                "n": n,
                "include_for_density": bool(rec.get("include_for_density")),
                "candidate_status": rec.get("candidate_status"),
                "exclusion_reason": rec.get("exclusion_reason"),
                "tolerance_limb": rec.get("tolerance_limb")
                or rec.get("frequency_refinement_method"),
            }
        )
    return rows


def run_one(audio: Path, dest: Path, *, n_fft: int, hop: int, zp: int) -> Dict[str, Any]:
    from proc_audio import AudioProcessor
    import compile_metrics as cm
    from post_compile_research_export import run_research_workbook_export

    dest.mkdir(parents=True, exist_ok=True)
    ap = AudioProcessor()
    ap.fft_policy = "fixed"
    ap.load_audio_files([str(audio)])
    ap.apply_filters_and_generate_data(
        results_directory=dest / "stage1",
        n_fft=int(n_fft),
        hop_length=int(hop),
        zero_padding=int(zp),
        window="blackmanharris",
        freq_min=20.0,
        freq_max=20000.0,
        db_min=-90.0,
        db_max=0.0,
        density_frequency_ceiling_hz=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    compiled = dest / "compiled_density_metrics.xlsx"
    cm.compile_density_metrics_with_pca(
        folder_path=dest / "stage1",
        output_path=compiled,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        weight_function="log",
    )
    research = run_research_workbook_export(
        compiled, no_charts=True, analysis_root=dest / "stage1"
    )
    wbs = list((dest / "stage1").rglob("spectral_analysis.xlsx"))
    wb = wbs[0] if wbs else None
    meta: Dict[str, Any] = _meta_map(wb) if wb else {}
    harm = pd.DataFrame()
    if wb:
        try:
            harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
        except Exception:
            harm = pd.DataFrame()
    ewsd = None
    if research and Path(research).is_file():
        try:
            sd = pd.read_excel(research, sheet_name="Spectral_Density_Metrics")
            if "EWSD_score_acoustic_balanced" in sd.columns and not sd.empty:
                ewsd = float(pd.to_numeric(sd["EWSD_score_acoustic_balanced"], errors="coerce").iloc[0])
        except Exception:
            ewsd = None
    return {
        "audio": audio.name,
        "workbook": str(wb) if wb else None,
        "research": str(research) if research else None,
        "n_fft": n_fft,
        "hop_length": hop,
        "zero_padding": zp,
        "harmonic_validated_count": _pick(meta, "harmonic_validated_count"),
        "harmonic_validated_weak_count": _pick(meta, "harmonic_validated_weak_count"),
        "harmonic_validated_strict_count": _pick(meta, "harmonic_validated_strict_count"),
        "tolerance_continuity_override_count": _pick(
            meta, "tolerance_continuity_override_count"
        ),
        "subbass_upper_bound_hz": _pick(meta, "subbass_upper_bound_hz"),
        "subbass_bound_formula": _pick(meta, "subbass_bound_formula"),
        "effective_partial_density": _pick(meta, "effective_partial_density"),
        "ci_resampling_unit": _pick(meta, "ci_resampling_unit"),
        "ci_n_resampled": _pick(meta, "ci_n_resampled"),
        "ci_bootstrap_iterations": _pick(meta, "ci_bootstrap_iterations"),
        "ci_seed": _pick(meta, "ci_seed"),
        "ci_width_flag": _pick(meta, "ci_width_flag"),
        "accepted_slots_above_body_stop": _pick(meta, "accepted_slots_above_body_stop"),
        "hop_duration_s": _pick(meta, "hop_duration_s"),
        "window_duration_s": _pick(meta, "window_duration_s"),
        "EWSD_score_acoustic_balanced": ewsd,
        "h74_h79": _h74_h79(harm),
        "ap_validated": int(getattr(ap, "harmonic_validated_count", 0) or 0),
        "ap_subbass": float(getattr(ap, "subbass_upper_bound_hz", float("nan"))),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="WP2 D1–D5 acceptance re-export")
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO / "docs" / "validation" / "_wp2_raw",
    )
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("trombone_as2_ff", TROMBONE_AS2, 8192, 1024, 2),
        ("tuba_a2_pp", TUBA_A2, 8192, 1024, 2),
    ]
    payload: Dict[str, Any] = {"commit": "38cb535", "jobs": []}
    for tag, audio, n_fft, hop, zp in jobs:
        if not audio.is_file():
            payload["jobs"].append({"tag": tag, "error": f"missing {audio}"})
            continue
        print(f"=== {tag} {audio.name} n_fft={n_fft}", flush=True)
        row = run_one(audio, args.out / tag, n_fft=n_fft, hop=hop, zp=zp)
        row["tag"] = tag
        payload["jobs"].append(row)
        print(json.dumps({k: row.get(k) for k in (
            "tag", "harmonic_validated_count", "tolerance_continuity_override_count",
            "subbass_upper_bound_hz", "effective_partial_density",
            "EWSD_score_acoustic_balanced", "ci_resampling_unit", "h74_h79",
        )}, indent=2, default=str), flush=True)
    out_json = args.out / "acceptance.json"
    out_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
