from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import export_research_density_workbook as research_export


def _write_compiled_workbook(path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["D3"],
            "source_file_name": ["Clar.-ord-D3-ff-N-T31u_Sustains.wav"],
            "density_metric_raw": [0.42],
            "density_metric_normalized": [1.0],
            "harmonic_density_sum": [1.0],
            "inharmonic_density_sum": [0.1],
            "subbass_density_sum": [0.01],
            "component_harmonic_energy_ratio": [0.85],
            "component_inharmonic_energy_ratio": [0.14],
            "component_subbass_energy_ratio": [0.01],
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
            "density_salience_threshold_db": [-45.0],
            "density_frequency_ceiling_hz": [5000.0],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_research_export_infers_metadata_and_handles_non_git_repo(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled_workbook(compiled)
    output = tmp_path / "compiled_density_metrics_research.xlsx"
    out = research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=True,
    )
    assert out.exists()

    sdm = pd.read_excel(out, sheet_name="Spectral_Density_Metrics")
    meta = pd.read_excel(out, sheet_name="Metadata")
    row = sdm.iloc[0]
    assert str(row["Instrument"]).strip().lower() == "clarinet"
    assert str(row["Dynamic"]).strip().lower() == "ff"
    assert str(row["Technique"]).strip().lower() == "ord"
    assert str(row["metadata_inference_status"]).strip() != ""
    assert str(row["f0_final_source"]).strip() == "nominal_guided"
    assert sdm["amplitude_mass_chart_file"].dtype == object
    assert sdm["energy_ratio_chart_file"].dtype == object
    if "git_commit" in meta.columns:
        git_commit = str(meta.loc[0, "git_commit"]).strip()
    else:
        key_col = str(meta.columns[0])
        val_col = str(meta.columns[1]) if len(meta.columns) > 1 else str(meta.columns[0])
        key_map = {str(k).strip(): v for k, v in zip(meta[key_col], meta[val_col], strict=False)}
        git_commit = str(key_map.get("git_commit", "")).strip()
    assert git_commit in {"unavailable_not_a_git_repository", "unavailable_not_recorded"} or git_commit != ""
