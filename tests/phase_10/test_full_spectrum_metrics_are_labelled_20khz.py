from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import export_research_density_workbook as research_export


def _write_compiled(path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["A5"],
            "density_metric_raw": [0.6],
            "density_body_weighted_sum_body_ceiling": [0.6],
            "density_full_spectrum_weighted_sum_20khz": [1.1],
            "harmonic_full_spectrum_energy_sum_20khz": [0.8],
            "inharmonic_full_spectrum_energy_sum_20khz": [0.3],
            "high_frequency_spectral_activity_sum": [0.25],
            "spectral_extension_index_20khz": [1.8],
            "brightness_or_upper_spectral_activity_index_20khz": [0.23],
            "harmonic_density_sum": [0.4],
            "inharmonic_density_sum": [0.15],
            "subbass_density_sum": [0.05],
            "component_harmonic_energy_ratio": [0.6],
            "component_inharmonic_energy_ratio": [0.3],
            "component_subbass_energy_ratio": [0.1],
        }
    )
    meta = pd.DataFrame({"analysis_version": ["test"], "weight_function": ["log"]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_full_spectrum_metrics_are_labelled_20khz(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled(compiled)
    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(compiled, output_path=output, overwrite=True, no_charts=True)
    meta = pd.read_excel(output, sheet_name="Metadata")
    kcol = str(meta.columns[0])
    vcol = str(meta.columns[1]) if len(meta.columns) > 1 else str(meta.columns[0])
    mapping = {str(k): str(v).lower() for k, v in zip(meta[kcol], meta[vcol], strict=False)}
    for key in (
        "density_full_spectrum_weighted_sum_20khz_definition",
        "harmonic_full_spectrum_energy_sum_20khz_definition",
        "inharmonic_full_spectrum_energy_sum_20khz_definition",
        "brightness_or_upper_spectral_activity_index_20khz_definition",
    ):
        assert "20" in mapping.get(key, "")
