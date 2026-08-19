"""D6.1 — swap-window and n_fft sweep for trombone G3 / G#3 / A#2.

Usage (from repo root)::

    python -m tools.diagnose_resolution_dependence --out docs/validation/_d61_raw
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

TROMBONE_FF = Path(
    r"D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone"
    r"\IOWA_Trombone_ff\_Sustains_Stable"
)


def _audio(note: str) -> Path:
    return TROMBONE_FF / f"IOWA_Trb.T_ff.{note}_SustainStable.aif"


def _pick(df: pd.DataFrame, *names: str) -> Optional[float]:
    if df is None or df.empty:
        return None
    lower = {str(c).strip().lower(): str(c) for c in df.columns}
    for name in names:
        col = lower.get(name.lower())
        if col is None:
            continue
        val = pd.to_numeric(df.iloc[0][col], errors="coerce")
        try:
            out = float(val)
        except (TypeError, ValueError):
            continue
        if out == out:
            return out
    return None


def _bin_counts(wb: Path) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for sheet, key in (
        ("Harmonic Spectrum", "harmonic_bins"),
        ("Inharmonic Spectrum", "inharmonic_bins"),
        ("Sub-bass band", "subbass_bins"),
        ("Complete Spectrum", "complete_bins"),
    ):
        try:
            df = pd.read_excel(wb, sheet_name=sheet)
        except Exception:
            out[key] = 0
            continue
        out[key] = int(len(df))
    return out


def run_one(
    audio: Path,
    n_fft: int,
    hop_length: int,
    out_dir: Path,
) -> Dict[str, Any]:
    from proc_audio import AudioProcessor
    import compile_metrics as cm
    from post_compile_research_export import run_research_workbook_export

    out_dir.mkdir(parents=True, exist_ok=True)
    ap = AudioProcessor()
    ap.load_audio_files([str(audio)])
    ap.apply_filters_and_generate_data(
        results_directory=out_dir / "stage1",
        n_fft=int(n_fft),
        hop_length=int(hop_length),
        zero_padding=2,
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
    compiled = out_dir / "compiled_density_metrics.xlsx"
    cm.compile_density_metrics_with_pca(
        folder_path=out_dir / "stage1",
        output_path=compiled,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        weight_function="log",
    )
    research = run_research_workbook_export(
        compiled, no_charts=True, analysis_root=out_dir / "stage1"
    )
    row: Dict[str, Any] = {
        "audio": audio.name,
        "n_fft": int(n_fft),
        "hop_length": int(hop_length),
        "compiled": str(compiled),
        "research": str(research) if research else None,
    }
    try:
        dm = pd.read_excel(compiled, sheet_name="Density_Metrics")
    except Exception:
        dm = pd.DataFrame()
    row["harmonic_density_sum"] = _pick(dm, "harmonic_density_sum")
    row["inharmonic_density_sum"] = _pick(dm, "inharmonic_density_sum")
    row["subbass_density_sum"] = _pick(dm, "subbass_density_sum")
    row["harmonic_energy_sum"] = _pick(dm, "harmonic_energy_sum")
    row["inharmonic_energy_sum"] = _pick(dm, "inharmonic_energy_sum")
    row["subbass_energy_sum"] = _pick(dm, "subbass_energy_sum")
    row["effective_partial_density"] = _pick(dm, "effective_partial_density")
    row["harmonic_energy_ratio"] = _pick(dm, "harmonic_energy_ratio", "component_harmonic_energy_ratio")
    row["residual_energy_ratio"] = _pick(
        dm, "residual_energy_ratio", "component_residual_noise_energy_ratio"
    )
    if research and Path(research).is_file():
        try:
            sd = pd.read_excel(research, sheet_name="Spectral_Density_Metrics")
        except Exception:
            sd = pd.DataFrame()
        row["EWSD_score_acoustic_balanced"] = _pick(
            sd, "EWSD_score_acoustic_balanced"
        )
        row["EWSD_score_total"] = _pick(sd, "EWSD_score_total")
        row["core_harmonic_energy_ratio"] = _pick(sd, "core_harmonic_energy_ratio")
        if row["harmonic_density_sum"] is None:
            row["harmonic_density_sum"] = _pick(sd, "harmonic_density_sum")
        if row["subbass_density_sum"] is None:
            row["subbass_density_sum"] = _pick(sd, "subbass_density_sum")
    wbs = list((out_dir / "stage1").rglob("spectral_analysis.xlsx"))
    if wbs:
        row.update(_bin_counts(wbs[0]))
        try:
            val = pd.read_excel(wbs[0], sheet_name="Validation_Metrics")
            row["residual_noise_energy_sum"] = _pick(val, "residual_noise_energy_sum")
            row["n_fft_export"] = _pick(val, "n_fft")
        except Exception:
            pass
    return row


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="D6.1 resolution-dependence diagnosis")
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO / "docs" / "validation" / "_d61_raw",
    )
    parser.add_argument("--sweep-note", default="G3")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("G3", 8192, 1024, "g3_native_8192"),
        ("G3", 4096, 512, "g3_swap_4096"),
        ("G#3", 4096, 512, "gs3_native_4096"),
        ("G#3", 8192, 1024, "gs3_swap_8192"),
    ]
    for n_fft in (2048, 4096, 8192, 16384):
        jobs.append((args.sweep_note, n_fft, n_fft // 8, f"sweep_{args.sweep_note}_{n_fft}"))

    results: List[Dict[str, Any]] = []
    for note, n_fft, hop, tag in jobs:
        audio = _audio(note)
        if not audio.is_file():
            results.append({"note": note, "error": f"missing {audio}", "tag": tag})
            continue
        dest = args.out / tag
        print(f"=== {tag}: {audio.name} n_fft={n_fft} hop={hop}", flush=True)
        try:
            row = run_one(audio, n_fft, hop, dest)
            row["note"] = note
            row["tag"] = tag
            results.append(row)
            print(json.dumps({k: row.get(k) for k in (
                "note", "n_fft", "EWSD_score_acoustic_balanced",
                "core_harmonic_energy_ratio", "harmonic_density_sum",
                "subbass_density_sum", "effective_partial_density",
            )}, indent=2), flush=True)
        except Exception as exc:
            results.append({"note": note, "tag": tag, "error": str(exc)})
            print(f"FAILED {tag}: {exc}", flush=True)

    payload = {"jobs": results}
    out_json = args.out / "diagnosis.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
