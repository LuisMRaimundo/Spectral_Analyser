"""Research export must merge satellite sheets on Note when sample_id is absent."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import export_research_density_workbook as research_export


def test_research_export_merges_diagnostic_metrics_without_sample_id(tmp_path: Path) -> None:
    note = "D3"
    density = pd.DataFrame(
        {
            "Note": [note],
            "source_file_name": ["clarinet-D3-mf.wav"],
            "sample_id": ["spectral_analysis__0633d398f642"],
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
            "acoustic_f0_status": ["nominal_guided_acoustically_verified"],
            "f0_fit_accepted": [True],
        }
    )
    diagnostic = pd.DataFrame(
        {
            "Note": [note],
            "f0_used_for_density_hz": [146.83],
            "n_fft": [8192],
            "hop_length": [512],
            "window_type": ["hann"],
        }
    )
    meta = pd.DataFrame({"analysis_version": ["test"], "weight_function": ["log"]})
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    with pd.ExcelWriter(compiled, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        diagnostic.to_excel(writer, sheet_name="Diagnostic_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)

    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=True,
        include_ewsd=False,
    )

    sdm = pd.read_excel(output, sheet_name="Spectral_Density_Metrics")
    settings = pd.read_excel(output, sheet_name="Analysis_Settings_By_Note")
    assert pd.notna(sdm.loc[0, "f0_used_for_density_hz"])
    assert float(sdm.loc[0, "f0_used_for_density_hz"]) == 146.83
    assert pd.notna(settings.loc[0, "n_fft"])
    assert int(settings.loc[0, "n_fft"]) == 8192
