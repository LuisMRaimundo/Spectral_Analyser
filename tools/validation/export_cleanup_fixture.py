"""Export the committed research-export regression fixture (D3).

Writes Stage 2 compiled + Stage 3 research workbooks for the same synthetic
note used by ``tests/phase_11/test_research_export_includes_ewsd.py``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from tools.export_research_density_workbook import export_research_workbook


def write_per_note_workbook(path: Path, *, note: str = "D3") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [146.83, 293.66, 440.0],
            "Amplitude_raw": [1.0, 0.7, 0.5],
            "Magnitude (dB)": [0.0, -3.0, -6.0],
            "include_for_density": [True, True, True],
        }
    )
    inharmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [220.0, 330.0],
            "Amplitude_raw": [0.15, 0.10],
            "Magnitude (dB)": [-16.0, -20.0],
        }
    )
    subbass = pd.DataFrame(
        {
            "Frequency (Hz)": [55.0],
            "Amplitude_raw": [0.05],
            "Magnitude (dB)": [-26.0],
        }
    )
    metrics = pd.DataFrame(
        {
            "Note": [note],
            "weight_function": ["log"],
            "pure_observation_w_h": [0.80],
            "pure_observation_w_i": [0.15],
            "pure_observation_w_s": [0.05],
            "component_harmonic_energy_ratio": [0.80],
            "component_inharmonic_energy_ratio": [0.15],
            "component_subbass_energy_ratio": [0.05],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metrics.to_excel(writer, sheet_name="Metrics", index=False)


def write_compiled_workbook(path: Path, *, note: str = "D3") -> None:
    density = pd.DataFrame(
        {
            "Note": [note],
            "source_file_name": ["Viola-D3-mf.wav"],
            "density_metric_raw": [0.42],
            "density_metric_normalized": [1.0],
            "harmonic_density_sum": [1.0],
            "inharmonic_density_sum": [0.1],
            "subbass_density_sum": [0.01],
            "component_harmonic_energy_ratio": [0.80],
            "component_inharmonic_energy_ratio": [0.15],
            "component_subbass_energy_ratio": [0.05],
            "density_frequency_ceiling_hz": [20000.0],
            "f0_final_hz": [146.83],
            "f0_source": ["nominal_guided"],
            "f0_final_source": ["nominal_guided"],
            "acoustic_f0_status": ["nominal_guided_acoustically_verified"],
            "f0_fit_accepted": [True],
        }
    )
    meta = pd.DataFrame(
        {
            "analysis_version": ["test"],
            "weight_function": ["log"],
            "density_salience_threshold_db": [-60.0],
            "density_frequency_ceiling_hz": [20000.0],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def export_cleanup_fixture(
    dest: Path, *, work_dir: Path, rebuild_inputs: bool = False
) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    note_wb = work_dir / "D3" / "spectral_analysis.xlsx"
    compiled = work_dir / "compiled_density_metrics.xlsx"
    # Reuse frozen inputs so EWSD bootstrap seed (from source_sha256) stays put.
    if rebuild_inputs or not note_wb.is_file():
        write_per_note_workbook(note_wb)
    if rebuild_inputs or not compiled.is_file():
        write_compiled_workbook(compiled)
    export_research_workbook(
        input_path=compiled,
        output_path=dest,
        overwrite=True,
        no_charts=True,
        include_ewsd=True,
    )
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dest")
    parser.add_argument(
        "--work-dir",
        default="",
        help="scratch folder for per-note + compiled workbooks",
    )
    parser.add_argument(
        "--rebuild-inputs",
        action="store_true",
        help="rewrite the frozen compiled/per-note inputs (changes bootstrap seed)",
    )
    args = parser.parse_args()
    dest = Path(args.dest)
    work = Path(args.work_dir) if args.work_dir else dest.parent / "_cleanup_fixture_work"
    out = export_cleanup_fixture(
        dest, work_dir=work, rebuild_inputs=args.rebuild_inputs
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    sys.exit(main())
